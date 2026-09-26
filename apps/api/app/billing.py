"""Dodo Payments for founder-approved 30-day passes (payment.md, V10).

Flow: a user requests access -> the founder approves an exact offer (scripts/billing.py) -> the user opens a Dodo
checkout for that offer -> a signed `payment.succeeded` webhook grants one pass. The browser redirect after checkout
never grants anything.

Trust rules:
- Price, product, runs and days come from the offer the founder approved, never from the browser.
- A webhook counts only with a valid Standard Webhooks signature, a fresh timestamp and our business id.
- The payment is then fetched again from Dodo's API, and only that answer decides the grant.
- Each webhook id is processed once, and each offer can grant at most one pass (unique `entitlements.offer_id`).
- Refunds and disputes revoke the pass; a payment already refunded or disputed grants nothing.
"""

import hashlib
import logging
import os
import re
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from urllib.parse import urlsplit

from app import db
from app.plans import PLANS

log = logging.getLogger("walkthru.billing")

# The only prices Walkthru sells (SPEC.md "Plans"), in US cents. `founding` is the first-50-customers price.
PRICES = {
    ("launch", False): 900,
    ("pro", True): 1500,
    ("pro", False): 1900,
    ("plus", True): 3900,
    ("plus", False): 4900,
}
CURRENCY = "USD"
PASS_DAYS = 30
CHECKOUT_HOURS = 24  # payment.md: a checkout capability expires within 24 hours
FOUNDING_SEATS = 50
ENVIRONMENTS = ("test_mode", "live_mode")
_ID = re.compile(r"^[A-Za-z0-9_-]{1,100}$")  # Dodo ids (pay_..., cks_..., pdt_...)
REVOKING_EVENTS = {"refund.succeeded": "refund", "dispute.opened": "dispute", "dispute.lost": "dispute", "dispute.accepted": "dispute"}


class NotConfigured(Exception):
    """Dodo keys are missing: checkout and webhooks stay off, free access keeps working."""


def product_env(plan: str, founding: bool) -> str:
    return f"DODO_PRODUCT_{plan.upper()}{'_FOUNDING' if founding else ''}"


def product_id(plan: str, founding: bool) -> str:
    value = os.environ.get(product_env(plan, founding), "").strip()
    if not _ID.match(value):
        raise NotConfigured(f"set {product_env(plan, founding)} to the Dodo product id")
    return value


def environment() -> str:
    # Explicit on purpose: the SDK falls back to live mode when no environment is given.
    env = os.environ.get("DODO_PAYMENTS_ENVIRONMENT", "test_mode").strip()
    if env not in ENVIRONMENTS:
        raise NotConfigured("DODO_PAYMENTS_ENVIRONMENT must be test_mode or live_mode")
    return env


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise NotConfigured(f"set {name}")
    return value


def configured() -> bool:
    try:
        client()
        _required("DODO_PAYMENTS_WEBHOOK_KEY")
        _required("DODO_PAYMENTS_BUSINESS_ID")
        return True
    except NotConfigured:
        return False


@lru_cache(maxsize=1)
def client():
    from dodopayments import DodoPayments

    return DodoPayments(bearer_token=_required("DODO_PAYMENTS_API_KEY"), environment=environment(), timeout=20.0, max_retries=2)


def offer_terms(plan: str, founding: bool, runs: int | None = None) -> dict:
    """The server-side terms of an offer. Raises ValueError for anything Walkthru does not sell."""
    if (plan, founding) not in PRICES:
        raise ValueError(f"no {'founding ' if founding else ''}price for plan {plan!r}")
    allowance = PLANS[plan].runs
    runs = allowance if runs is None else runs
    if not 0 < runs <= allowance:
        raise ValueError(f"runs must be between 1 and {allowance} for {plan}")
    return {"plan": plan, "founding": founding, "price_cents": PRICES[(plan, founding)], "currency": CURRENCY,
            "product_id": product_id(plan, founding), "runs": runs, "days": PASS_DAYS}


def check_product(offer: dict) -> None:
    """Confirm the Dodo product behind an offer charges exactly the offer price, once, with no customer-set amount."""
    product = client().products.retrieve(offer["product_id"])
    price = product.price
    problems = []
    if product.is_recurring or getattr(price, "type", "") != "one_time_price":
        problems.append("it must be a one-time product, not a subscription")
    if price.price != offer["price_cents"] or str(price.currency) != offer["currency"]:
        problems.append(f"its price is {price.price} {price.currency}, the offer needs {offer['price_cents']} {offer['currency']}")
    if getattr(price, "pay_what_you_want", False):
        problems.append("pay what you want must be off")
    if getattr(price, "discount", 0) or getattr(price, "discount_bps", 0):
        problems.append("its built-in discount must be 0")
    if getattr(price, "purchasing_power_parity", False):
        problems.append("purchasing power parity must be off")
    if problems:
        raise ValueError(f"Dodo product {offer['product_id']}: " + "; ".join(problems))


def offer_open(offer: dict, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    return offer["status"] == "approved" and datetime.fromisoformat(offer["checkout_expires_at"]) > now


def public_offer(offer: dict) -> dict:
    """What the owner sees: no product ids, no approver."""
    return {k: offer[k] for k in ("id", "plan", "founding", "price_cents", "currency", "runs", "days", "status", "checkout_expires_at", "paid_at", "created_at")} | {
        "open": offer_open(offer)}


def create_checkout(offer: dict, user: dict, return_url: str) -> str:
    """A Dodo checkout session for exactly this offer. Returns the hosted checkout URL."""
    session = client().checkout_sessions.create(
        product_cart=[{"product_id": offer["product_id"], "quantity": 1}],
        customer={"email": user["email"]},
        metadata={"offer_id": offer["id"], "user_id": user["id"]},
        return_url=return_url,
        feature_flags={"allow_discount_code": False, "allow_currency_selection": False, "allow_customer_editing_email": False},
    )
    url = session.checkout_url or ""
    parts = urlsplit(url)
    if parts.scheme != "https" or not (parts.hostname or "").endswith(".dodopayments.com"):
        raise RuntimeError("Dodo returned an unexpected checkout address")
    return url


# ---------- webhooks ----------


class InvalidWebhook(Exception):
    pass


def verify(body: bytes, headers: dict[str, str]) -> dict:
    """Standard Webhooks signature and 5-minute timestamp check, then our business id. Returns the event."""
    from standardwebhooks import Webhook, WebhookVerificationError

    try:
        hook = Webhook(_required("DODO_PAYMENTS_WEBHOOK_KEY"))
    except ValueError as e:  # not base64: our configuration is wrong, not the sender
        raise NotConfigured("DODO_PAYMENTS_WEBHOOK_KEY is not a valid whsec_ secret") from e
    try:
        event = hook.verify(body, headers)
    except (WebhookVerificationError, ValueError, TypeError) as e:  # malformed headers raise ValueError
        raise InvalidWebhook(str(e) or "bad signature") from e
    if not isinstance(event, dict) or not isinstance(event.get("data"), dict) or not isinstance(event.get("type"), str):
        raise InvalidWebhook("unexpected payload")
    if event.get("business_id") != _required("DODO_PAYMENTS_BUSINESS_ID"):
        raise InvalidWebhook("wrong business")
    return event


def handle(body: bytes, headers: dict[str, str]) -> str:
    """Process one verified webhook exactly once. Raises on transient failure so Dodo retries it."""
    event = verify(body, headers)
    webhook_id = headers.get("webhook-id", "")
    data = event["data"]
    object_id = data.get("payment_id") if isinstance(data.get("payment_id"), str) else None
    stored = db.record_billing_event(webhook_id, event["type"], object_id, hashlib.sha256(body).hexdigest())
    if stored.get("processed_at"):
        return "duplicate"
    if event["type"] == "payment.succeeded":
        result = activate(object_id)
    elif event["type"] in REVOKING_EVENTS:
        result = revoke(object_id, REVOKING_EVENTS[event["type"]])
    else:
        result = "ignored"
    db.finish_billing_event(webhook_id, result)
    log.info("dodo webhook %s %s -> %s", event["type"], object_id, result)
    return result


def _refunded_or_disputed(payment) -> bool:
    return any(r.status in ("succeeded", "pending", "review") for r in payment.refunds or []) or bool(payment.disputes)


def activate(payment_id: str | None) -> str:
    """Grant the pass for a succeeded payment, using only what Dodo's API says about it."""
    if not payment_id or not _ID.match(payment_id):
        return "rejected: no payment id"
    payment = client().payments.retrieve(payment_id)
    if payment.business_id != _required("DODO_PAYMENTS_BUSINESS_ID"):
        return "rejected: wrong business"
    if payment.status != "succeeded":
        return f"rejected: payment status {payment.status}"
    meta = payment.metadata or {}
    offer_id, user_id = str(meta.get("offer_id", "")), str(meta.get("user_id", ""))
    if not re.fullmatch(r"[0-9a-f-]{36}", offer_id):
        return "rejected: no offer in metadata"
    offer = db.get_offer(offer_id)
    if not offer or str(offer["user_id"]) != user_id:
        return "rejected: offer does not match"
    if offer["status"] == "paid":
        if offer.get("payment_id") == payment_id:
            _grant(offer, payment_id)  # finishes a grant a crash interrupted; a no-op otherwise
            return "already granted"
        log.warning("second payment %s for offer %s: refund it in Dodo", payment_id, offer_id)
        return "rejected: offer already paid, refund this payment"
    if offer["status"] != "approved":
        log.warning("payment %s for %s offer %s: refund it in Dodo", payment_id, offer["status"], offer_id)
        return f"rejected: offer {offer['status']}, refund this payment"
    if payment.created_at > datetime.fromisoformat(offer["checkout_expires_at"]):
        return "rejected: paid after the offer expired, refund this payment"
    cart = [(item.product_id, item.quantity) for item in payment.product_cart or []]
    if cart != [(offer["product_id"], 1)]:
        return "rejected: products do not match the offer"
    if payment.discounts or payment.discount_id:
        return "rejected: a discount was applied"
    if str(payment.currency) == offer["currency"] and payment.total_amount not in (offer["price_cents"], offer["price_cents"] + (payment.tax or 0)):
        return "rejected: amount does not match the offer"
    if _refunded_or_disputed(payment):
        db.mark_offer(offer_id, "approved", {"status": "refunded", "payment_id": payment_id})
        return "rejected: already refunded or disputed"
    _grant(offer, payment_id)
    db.mark_offer(offer_id, "approved", {"status": "paid", "payment_id": payment_id, "paid_at": datetime.now(UTC).isoformat()})
    return "granted"


def _grant(offer: dict, payment_id: str) -> None:
    now = datetime.now(UTC)
    db.grant_paid_entitlement({
        "user_id": offer["user_id"], "plan": offer["plan"], "starts_at": now.isoformat(),
        "expires_at": (now + timedelta(days=offer["days"])).isoformat(), "runs_granted": offer["runs"],
        "source": "dodo", "offer_id": offer["id"], "payment_id": payment_id})
    from app import notify

    notify.pass_granted(offer["user_id"], offer["plan"], offer["days"], paid=True)


def revoke(payment_id: str | None, reason: str) -> str:
    """Refund or dispute: end the pass bought with this payment. A payment with no pass yet is blocked by activate()."""
    if not payment_id or not _ID.match(payment_id):
        return "rejected: no payment id"
    revoked = db.revoke_entitlement(payment_id, reason)
    offer = db.offer_for_payment(payment_id)
    if offer and offer["status"] == "paid":
        db.mark_offer(offer["id"], "paid", {"status": "refunded"})
    return f"revoked ({reason})" if revoked else f"no active pass ({reason})"
