"""V10 billing (payment.md): only a signed, verified Dodo payment for an approved offer grants a pass, exactly once."""

import base64
import json
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from standardwebhooks import Webhook

from app import billing, db, plans
from app.main import app
from tests.conftest import USER

SECRET = "whsec_" + base64.b64encode(b"walkthru-test-webhook-secret-32b").decode()
BUSINESS = "bus_test123"
OTHER_USER = "00000000-0000-0000-0000-000000000002"


@pytest.fixture(autouse=True)
def dodo_env(monkeypatch):
    monkeypatch.setenv("DODO_PAYMENTS_API_KEY", "test-key")
    monkeypatch.setenv("DODO_PAYMENTS_WEBHOOK_KEY", SECRET)
    monkeypatch.setenv("DODO_PAYMENTS_BUSINESS_ID", BUSINESS)
    monkeypatch.setenv("DODO_PAYMENTS_ENVIRONMENT", "test_mode")
    for (plan, founding) in billing.PRICES:
        monkeypatch.setenv(billing.product_env(plan, founding), f"pdt_{plan}{'_f' if founding else ''}")


class FakeDodo:
    """Dodo's API as the tests need it: payments to look up, checkout sessions to record."""

    def __init__(self):
        self.payments_by_id: dict[str, SimpleNamespace] = {}
        self.sessions: list[dict] = []
        self.payments = SimpleNamespace(retrieve=lambda pid: self.payments_by_id[pid])
        self.checkout_sessions = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.sessions.append(kw)
        return SimpleNamespace(session_id="cks_1", checkout_url="https://test.checkout.dodopayments.com/session/cks_1")

    def pay(self, offer, payment_id="pay_1", **over):
        p = SimpleNamespace(
            payment_id=payment_id, business_id=BUSINESS, status="succeeded", created_at=datetime.now(UTC),
            metadata={"offer_id": offer["id"], "user_id": str(offer["user_id"])}, currency="USD",
            total_amount=offer["price_cents"], tax=0, discounts=None, discount_id=None, refunds=[], disputes=[],
            product_cart=[SimpleNamespace(product_id=offer["product_id"], quantity=1)],
        )
        for k, v in over.items():
            setattr(p, k, v)
        self.payments_by_id[payment_id] = p
        return p


@pytest.fixture(autouse=True)
def dodo(monkeypatch):
    fake = FakeDodo()
    monkeypatch.setattr(billing, "client", lambda: fake)
    return fake


@pytest.fixture(autouse=True)
def billing_db(monkeypatch, passes):
    """In-memory billing tables with the same uniqueness rules as schema.sql."""
    t = {"requests": {}, "offers": {}, "events": {}, "audit": []}

    def create_access_request(user_id, plan, note):
        if any(r["user_id"] == user_id and r["status"] == "pending" for r in t["requests"].values()):
            raise db.Conflict("access_requests")
        row = {"id": str(uuid.uuid4()), "user_id": user_id, "plan": plan, "note": note, "status": "pending", "created_at": datetime.now(UTC).isoformat(), "decided_at": None}
        t["requests"][row["id"]] = row
        return row

    def mark_offer(offer_id, from_status, values):
        o = t["offers"].get(offer_id)
        if not o or o["status"] != from_status:
            return False
        o.update(values)
        return True

    def record_billing_event(webhook_id, event_type, object_id, body_sha256):
        return t["events"].setdefault(webhook_id, {"webhook_id": webhook_id, "event_type": event_type, "object_id": object_id, "processed_at": None})

    def grant_paid_entitlement(row):
        if any(p.get("offer_id") == row["offer_id"] for p in passes):
            return False
        passes.append(row | {"revoked_at": None})
        return True

    def revoke_entitlement(payment_id, reason):
        hit = [p for p in passes if p.get("payment_id") == payment_id and not p.get("revoked_at")]
        for p in hit:
            p |= {"revoked_at": datetime.now(UTC).isoformat(), "revoked_reason": reason}
        return hit

    monkeypatch.setattr(db, "create_access_request", create_access_request)
    monkeypatch.setattr(db, "access_requests_for_user", lambda user_id, limit=20: [r for r in t["requests"].values() if r["user_id"] == user_id])
    monkeypatch.setattr(db, "get_offer", t["offers"].get)
    monkeypatch.setattr(db, "offers_for_user", lambda user_id, limit=20: [o for o in t["offers"].values() if o["user_id"] == user_id])
    monkeypatch.setattr(db, "mark_offer", mark_offer)
    monkeypatch.setattr(db, "record_billing_event", record_billing_event)
    monkeypatch.setattr(db, "finish_billing_event", lambda webhook_id, result: t["events"][webhook_id].update(processed_at="now", result=result))
    monkeypatch.setattr(db, "grant_paid_entitlement", grant_paid_entitlement)
    monkeypatch.setattr(db, "revoke_entitlement", revoke_entitlement)
    monkeypatch.setattr(db, "offer_for_payment", lambda pid: next((o for o in t["offers"].values() if o.get("payment_id") == pid), None))
    return t


def offer(billing_db, plan="pro", founding=False, user_id=USER, hours=24, status="approved"):
    row = billing.offer_terms(plan, founding) | {
        "id": str(uuid.uuid4()), "user_id": user_id, "status": status, "payment_id": None, "paid_at": None,
        "checkout_expires_at": (datetime.now(UTC) + timedelta(hours=hours)).isoformat(), "created_at": datetime.now(UTC).isoformat()}
    billing_db["offers"][row["id"]] = row
    return row


def send(client, event_type, data, webhook_id="msg_1", secret=SECRET, business=BUSINESS, when=None):
    body = json.dumps({"business_id": business, "type": event_type, "timestamp": datetime.now(UTC).isoformat(), "data": data})
    when = when or datetime.now(UTC)
    sig = Webhook(secret).sign(webhook_id, when, body)
    headers = {"webhook-id": webhook_id, "webhook-timestamp": str(int(when.timestamp())), "webhook-signature": sig, "content-type": "application/json"}
    return client.post("/webhooks/dodo", content=body, headers=headers)


def pro_passes(passes):
    return [p for p in passes if p.get("source") == "dodo" and not p.get("revoked_at")]


# ---------- checkout ----------


def test_checkout_uses_the_offer_terms_and_the_account_email(billing_db, dodo):
    o = offer(billing_db)
    r = TestClient(app).post(f"/billing/offers/{o['id']}/checkout")
    assert r.status_code == 200
    assert r.json()["checkout_url"].startswith("https://test.checkout.dodopayments.com/")
    s = dodo.sessions[0]
    assert s["product_cart"] == [{"product_id": "pdt_pro", "quantity": 1}]
    assert s["customer"] == {"email": "tester@example.com"}
    assert s["metadata"] == {"offer_id": o["id"], "user_id": USER}
    assert s["feature_flags"]["allow_discount_code"] is False


def test_checkout_for_someone_elses_offer_is_unknown(billing_db, dodo):
    o = offer(billing_db, user_id=OTHER_USER)
    assert TestClient(app).post(f"/billing/offers/{o['id']}/checkout").status_code == 404
    assert dodo.sessions == []


def test_checkout_for_expired_paid_or_cancelled_offer_is_refused(billing_db, dodo):
    for o in (offer(billing_db, hours=-1), offer(billing_db, status="paid"), offer(billing_db, status="cancelled")):
        assert TestClient(app).post(f"/billing/offers/{o['id']}/checkout").status_code == 410
    assert dodo.sessions == []


def test_checkout_rejects_a_non_uuid_offer_id():
    assert TestClient(app).post("/billing/offers/abc&user_id=x/checkout").status_code in (404, 422)


def test_checkout_without_dodo_keys_says_payments_are_off(billing_db, monkeypatch):
    monkeypatch.setattr(billing, "client", lambda: (_ for _ in ()).throw(billing.NotConfigured("set DODO_PAYMENTS_API_KEY")))
    o = offer(billing_db)
    assert TestClient(app).post(f"/billing/offers/{o['id']}/checkout").status_code == 503


def test_checkout_redirect_alone_grants_nothing(billing_db, passes):
    o = offer(billing_db)
    c = TestClient(app)
    c.post(f"/billing/offers/{o['id']}/checkout")
    c.get(f"/billing?offer={o['id']}&status=succeeded&payment_id=pay_fake")
    assert pro_passes(passes) == []
    assert c.get("/me/plan").json()["plan"] == "free"


# ---------- access requests ----------


def test_access_request_takes_only_plan_and_note(billing_db):
    c = TestClient(app)
    assert c.post("/billing/access-requests", json={"plan": "pro", "price_cents": 1}).status_code == 422
    assert c.post("/billing/access-requests", json={"plan": "enterprise"}).status_code == 422
    r = c.post("/billing/access-requests", json={"plan": "pro", "note": "testing my SaaS signup"})
    assert r.status_code == 200 and r.json()["status"] == "pending"
    assert c.post("/billing/access-requests", json={"plan": "plus"}).status_code == 409  # one pending at a time


def test_billing_status_hides_product_ids(billing_db):
    offer(billing_db)
    body = TestClient(app).get("/billing").json()
    assert body["offers"][0]["plan"] == "pro" and body["offers"][0]["open"] is True
    assert "product_id" not in json.dumps(body) and "approved_by" not in json.dumps(body)


# ---------- webhooks: authenticity ----------


def test_valid_payment_grants_exactly_one_pass(billing_db, dodo, passes):
    o = offer(billing_db)
    dodo.pay(o)
    c = TestClient(app)
    r = send(c, "payment.succeeded", {"payment_id": "pay_1"})
    assert r.status_code == 200 and r.json()["result"] == "granted"
    assert len(pro_passes(passes)) == 1
    assert billing_db["offers"][o["id"]]["status"] == "paid"
    me = c.get("/me/plan").json()
    assert me["plan"] == "pro" and me["runs_allowed"] == plans.PLANS["pro"].runs


def test_redelivered_webhook_changes_nothing(billing_db, dodo, passes):
    o = offer(billing_db)
    dodo.pay(o)
    c = TestClient(app)
    send(c, "payment.succeeded", {"payment_id": "pay_1"})
    assert send(c, "payment.succeeded", {"payment_id": "pay_1"}).json()["result"] == "duplicate"
    assert send(c, "payment.succeeded", {"payment_id": "pay_1"}, webhook_id="msg_2").json()["result"] == "already granted"
    assert len(pro_passes(passes)) == 1


def test_forged_signature_is_refused(billing_db, dodo, passes):
    o = offer(billing_db)
    dodo.pay(o)
    forged = "whsec_" + base64.b64encode(b"attacker-secret-attacker-secret!").decode()
    assert send(TestClient(app), "payment.succeeded", {"payment_id": "pay_1"}, secret=forged).status_code == 401
    assert pro_passes(passes) == [] and billing_db["events"] == {}


def test_missing_or_garbage_signature_headers_are_refused(billing_db):
    c = TestClient(app)
    assert c.post("/webhooks/dodo", content=b"{}").status_code == 401
    bad = {"webhook-id": "m", "webhook-timestamp": "x", "webhook-signature": "nonsense"}
    assert c.post("/webhooks/dodo", content=b"{}", headers=bad).status_code == 401
    bad |= {"webhook-timestamp": str(int(datetime.now(UTC).timestamp())), "webhook-signature": "v1,!!!notbase64"}
    assert c.post("/webhooks/dodo", content=b"{}", headers=bad).status_code == 401


def test_stale_webhook_is_refused(billing_db, dodo, passes):
    o = offer(billing_db)
    dodo.pay(o)
    old = datetime.now(UTC) - timedelta(minutes=10)
    assert send(TestClient(app), "payment.succeeded", {"payment_id": "pay_1"}, when=old).status_code == 401
    assert pro_passes(passes) == []


def test_other_business_is_refused(billing_db, dodo, passes):
    o = offer(billing_db)
    dodo.pay(o)
    assert send(TestClient(app), "payment.succeeded", {"payment_id": "pay_1"}, business="bus_other").status_code == 401
    assert pro_passes(passes) == []


def test_oversized_body_is_refused():
    assert TestClient(app).post("/webhooks/dodo", content=b"x" * 300_000).status_code == 413


def test_webhook_body_is_not_trusted_only_dodos_api(billing_db, dodo, passes):
    """A correctly signed event whose payment Dodo says failed grants nothing."""
    o = offer(billing_db)
    dodo.pay(o, status="failed")
    assert send(TestClient(app), "payment.succeeded", {"payment_id": "pay_1", "status": "succeeded"}).json()["result"].startswith("rejected")
    assert pro_passes(passes) == []


# ---------- webhooks: payment must match the offer ----------


@pytest.mark.parametrize("change", [
    {"total_amount": 100},
    {"product_cart": [SimpleNamespace(product_id="pdt_launch", quantity=1)]},
    {"product_cart": [SimpleNamespace(product_id="pdt_pro", quantity=2)]},
    {"discount_id": "dsc_1"},
    {"business_id": "bus_other"},
    {"created_at": datetime.now(UTC) + timedelta(days=2)},
])
def test_payment_that_does_not_match_the_offer_grants_nothing(billing_db, dodo, passes, change):
    o = offer(billing_db)
    dodo.pay(o, **change)
    assert send(TestClient(app), "payment.succeeded", {"payment_id": "pay_1"}).json()["result"].startswith("rejected")
    assert pro_passes(passes) == []
    assert billing_db["offers"][o["id"]]["status"] == "approved"


def test_metadata_pointing_at_another_users_offer_grants_nothing(billing_db, dodo, passes):
    theirs = offer(billing_db, user_id=OTHER_USER)
    dodo.pay(theirs, metadata={"offer_id": theirs["id"], "user_id": USER})
    assert send(TestClient(app), "payment.succeeded", {"payment_id": "pay_1"}).json()["result"] == "rejected: offer does not match"
    assert passes == []


def test_tax_on_top_of_the_price_is_accepted(billing_db, dodo, passes):
    o = offer(billing_db)
    dodo.pay(o, total_amount=o["price_cents"] + 342, tax=342)
    assert send(TestClient(app), "payment.succeeded", {"payment_id": "pay_1"}).json()["result"] == "granted"


def test_second_payment_for_a_paid_offer_does_not_grant_twice(billing_db, dodo, passes):
    o = offer(billing_db)
    dodo.pay(o, "pay_1")
    dodo.pay(o, "pay_2")
    c = TestClient(app)
    send(c, "payment.succeeded", {"payment_id": "pay_1"})
    assert "refund this payment" in send(c, "payment.succeeded", {"payment_id": "pay_2"}, webhook_id="msg_2").json()["result"]
    assert len(pro_passes(passes)) == 1


# ---------- refunds and disputes ----------


def test_refund_revokes_the_pass(billing_db, dodo, passes):
    o = offer(billing_db)
    dodo.pay(o)
    c = TestClient(app)
    send(c, "payment.succeeded", {"payment_id": "pay_1"})
    assert send(c, "refund.succeeded", {"payment_id": "pay_1", "refund_id": "ref_1"}, webhook_id="msg_2").json()["result"] == "revoked (refund)"
    assert pro_passes(passes) == []
    assert billing_db["offers"][o["id"]]["status"] == "refunded"


def test_dispute_revokes_the_pass(billing_db, dodo, passes):
    o = offer(billing_db)
    dodo.pay(o)
    c = TestClient(app)
    send(c, "payment.succeeded", {"payment_id": "pay_1"})
    send(c, "dispute.opened", {"payment_id": "pay_1", "dispute_id": "dsp_1"}, webhook_id="msg_2")
    assert pro_passes(passes) == []


def test_refund_arriving_before_the_payment_event_grants_nothing(billing_db, dodo, passes):
    o = offer(billing_db)
    dodo.pay(o, refunds=[SimpleNamespace(status="succeeded")])
    c = TestClient(app)
    assert send(c, "refund.succeeded", {"payment_id": "pay_1"}, webhook_id="msg_2").json()["result"] == "no active pass (refund)"
    assert send(c, "payment.succeeded", {"payment_id": "pay_1"}).json()["result"] == "rejected: already refunded or disputed"
    assert pro_passes(passes) == []


def test_revoked_pass_is_not_the_active_plan(billing_db, dodo, passes, monkeypatch):
    o = offer(billing_db)
    dodo.pay(o)
    c = TestClient(app)
    send(c, "payment.succeeded", {"payment_id": "pay_1"})
    send(c, "refund.succeeded", {"payment_id": "pay_1"}, webhook_id="msg_2")
    assert c.get("/me/plan").json()["plan"] == "free"


# ---------- failures retry, never half-grant ----------


def test_database_outage_asks_dodo_to_retry_and_the_retry_grants_once(billing_db, dodo, passes, monkeypatch):
    o = offer(billing_db)
    dodo.pay(o)
    real = db.grant_paid_entitlement

    def down(row):
        raise db.DatabaseUnavailable("down")

    monkeypatch.setattr(db, "grant_paid_entitlement", down)
    c = TestClient(app)
    assert send(c, "payment.succeeded", {"payment_id": "pay_1"}).status_code == 500
    monkeypatch.setattr(db, "grant_paid_entitlement", real)
    assert send(c, "payment.succeeded", {"payment_id": "pay_1"}).json()["result"] == "granted"  # same webhook id, not yet processed
    assert len(pro_passes(passes)) == 1


@pytest.mark.parametrize("key", [None, "whsec_not*base64"])
def test_unconfigured_webhook_asks_for_a_retry(monkeypatch, key):
    if key is None:
        monkeypatch.delenv("DODO_PAYMENTS_WEBHOOK_KEY")
    else:
        monkeypatch.setenv("DODO_PAYMENTS_WEBHOOK_KEY", key)
    r = TestClient(app).post("/webhooks/dodo", content=b"{}", headers={"webhook-id": "m", "webhook-timestamp": "1", "webhook-signature": "v1,x"})
    assert r.status_code == 503


# ---------- server-side terms ----------


def test_offer_terms_come_from_the_server():
    assert billing.offer_terms("pro", True)["price_cents"] == 1500
    assert billing.offer_terms("plus", False)["price_cents"] == 4900
    with pytest.raises(ValueError):
        billing.offer_terms("launch", True)  # no founding Launch Pack
    with pytest.raises(ValueError):
        billing.offer_terms("pro", False, runs=500)  # never more runs than the plan


def test_environment_never_defaults_to_live(monkeypatch):
    monkeypatch.delenv("DODO_PAYMENTS_ENVIRONMENT")
    assert billing.environment() == "test_mode"
    monkeypatch.setenv("DODO_PAYMENTS_ENVIRONMENT", "production")
    with pytest.raises(billing.NotConfigured):
        billing.environment()


# ---------- contract with the real SDK (no network: a mocked transport answers) ----------


def test_real_sdk_builds_the_checkout_request_and_parses_the_payment(billing_db, passes, monkeypatch):
    import httpx
    from dodopayments import DodoPayments

    o = offer(billing_db)
    seen = []
    payment = {
        "payment_id": "pay_real", "business_id": BUSINESS, "brand_id": "brd_1", "status": "succeeded", "created_at": datetime.now(UTC).isoformat(),
        "currency": "USD", "total_amount": o["price_cents"], "tax": 0, "settlement_amount": 1400, "settlement_currency": "USD",
        "metadata": {"offer_id": o["id"], "user_id": USER}, "product_cart": [{"product_id": o["product_id"], "quantity": 1}],
        "refunds": [], "disputes": [], "digital_products_delivered": False, "is_update_payment_method": False, "retry_attempt": 0,
        "payment_provider": "dodo", "billing": {"country": "IN", "city": None, "state": None, "street": None, "zipcode": None},
        "customer": {"customer_id": "cus_1", "email": "tester@example.com", "name": "T"},
    }

    def answer(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/checkouts":
            return httpx.Response(200, json={"session_id": "cks_1", "checkout_url": "https://test.checkout.dodopayments.com/session/cks_1"})
        return httpx.Response(200, json=payment)

    sdk = DodoPayments(bearer_token="test-key", environment="test_mode", http_client=httpx.Client(transport=httpx.MockTransport(answer)))
    monkeypatch.setattr(billing, "client", lambda: sdk)
    c = TestClient(app)
    assert c.post(f"/billing/offers/{o['id']}/checkout").status_code == 200
    sent = json.loads(seen[0].content)
    assert seen[0].url.host == "test.dodopayments.com" and seen[0].headers["authorization"] == "Bearer test-key"
    assert sent["product_cart"] == [{"product_id": "pdt_pro", "quantity": 1}] and sent["metadata"]["offer_id"] == o["id"]
    assert send(c, "payment.succeeded", {"payment_id": "pay_real"}).json()["result"] == "granted"
    assert seen[-1].url.path == "/payments/pay_real"


def test_founder_hears_about_each_access_request(monkeypatch, billing_db):
    from app import deliver, main

    sent = []
    monkeypatch.setattr(main, "_billing_hits", {})  # earlier tests used up this user's hourly requests
    monkeypatch.setenv("FOUNDER_EMAIL", "founder@example.com")
    monkeypatch.setattr(deliver, "send_access_request", lambda *a: sent.append(a) or True)
    with TestClient(main.app) as c:
        assert c.post("/billing/access-requests", json={"plan": "plus", "note": "my SaaS"}).status_code == 200
    assert sent and sent[0][0] == "founder@example.com" and sent[0][2:4] == ("plus", "my SaaS")
