# Billing with Dodo Payments: setup, testing, operations

Design and reasons: [payment.md](../payment.md). This page is the runbook. Code: `apps/api/app/billing.py`, routes in `apps/api/app/main.py` (search "billing"), founder tool `apps/api/scripts/billing.py`, page `/app/billing`.

## How it works

```text
User (signed in)          Founder (your machine)           Dodo                       Walkthru API
/app/billing
  Request access  ───────▶ scripts/billing.py list
                           scripts/billing.py approve ID
                           (checks the Dodo product price,
                            writes an offer, 24 h window)
  Pay $15 ──────────────────────────────────────────────────────────────────────────▶ POST /billing/offers/{id}/checkout
                                                          ◀── checkout session ──────  (server picks product, email, metadata)
  pays on Dodo's page ───────────────────────────────────▶
                                                          ── signed webhook ────────▶ POST /webhooks/dodo
                                                                                        verify signature, timestamp, business
                                                                                        re-fetch payment from Dodo's API
                                                                                        match offer: user, product, amount
                                                                                        insert ONE entitlements row
  back on /app/billing: polls GET /billing until the pass shows (the redirect itself grants nothing)
```

Refunds and disputes arrive as webhooks too and end the pass.

## One-time setup (test mode)

### 1. Dodo dashboard (make sure the **Test mode** toggle is on)

1. **Products > Create**, five times. Each is a **one-time payment** (not a subscription), currency **USD**, tax category **SaaS**, pay-what-you-want **off**, no discount:

   | Product name | Price | Env variable |
   |---|---:|---|
   | Walkthru Launch Pack (30 days) | $9.00 | `DODO_PRODUCT_LAUNCH` |
   | Walkthru Pro, founding (30 days) | $15.00 | `DODO_PRODUCT_PRO_FOUNDING` |
   | Walkthru Pro (30 days) | $19.00 | `DODO_PRODUCT_PRO` |
   | Walkthru Plus, founding (30 days) | $39.00 | `DODO_PRODUCT_PLUS_FOUNDING` |
   | Walkthru Plus (30 days) | $49.00 | `DODO_PRODUCT_PLUS` |

   Copy each `pdt_...` id. Do not share the products' own payment links: Walkthru only sells through checkouts it creates for an approved offer.
2. **Developer > API Keys > Create**. Copy the key (shown once) into `DODO_PAYMENTS_API_KEY`.
3. **Settings > Business**: copy the business id (`bus_...`) into `DODO_PAYMENTS_BUSINESS_ID`.
4. **Developer > Webhooks > Add endpoint** (after step 3 below gives you a public URL):
   - URL: `https://YOUR-API/webhooks/dodo`
   - Events: `payment.succeeded`, `payment.failed`, `refund.succeeded`, `dispute.opened`, `dispute.accepted`, `dispute.lost`
   - Copy the **signing secret** (`whsec_...`) into `DODO_PAYMENTS_WEBHOOK_KEY`.
5. Turn on two-factor sign-in for the Dodo account (payment.md, administrator controls).

### 2. Keys into `apps/api/.env`

Open `apps/api/.env` (copy the Dodo block from the repo's `.env.example` if it is missing) and paste:

```
DODO_PAYMENTS_API_KEY=...
DODO_PAYMENTS_WEBHOOK_KEY=whsec_...
DODO_PAYMENTS_BUSINESS_ID=bus_...
DODO_PAYMENTS_ENVIRONMENT=test_mode
DODO_PRODUCT_LAUNCH=pdt_...
DODO_PRODUCT_PRO_FOUNDING=pdt_...
DODO_PRODUCT_PRO=pdt_...
DODO_PRODUCT_PLUS_FOUNDING=pdt_...
DODO_PRODUCT_PLUS=pdt_...
```

Nothing Dodo-related goes into `apps/web/.env`: the browser never sees a Dodo key. On Render, set the same names in the service's Environment tab (`render.yaml` lists them).

### 3. Database and a public webhook address

```
cd apps/api
.venv/Scripts/python -m pip install -e ".[dev]"      # adds dodopayments and standardwebhooks
.venv/Scripts/python -m app.db                       # adds the billing tables (idempotent)
.venv/Scripts/python scripts/billing.py products     # every line should say ok
```

Dodo cannot reach `localhost`. For local testing run a tunnel to the API and use its address in step 1.4:

```
cloudflared tunnel --url http://localhost:8010       # prints https://something.trycloudflare.com
```

The tunnel address changes every time it starts; update the Dodo endpoint when it does. After deploy, use the Render URL instead.

## Testing a real test-mode payment (no real money)

1. Sign in on the web app, open **Plan & billing**, request Pro.
2. On your machine: `scripts/billing.py list`, then `scripts/billing.py approve REQUEST_ID --founding`.
3. Refresh **Plan & billing**: the offer shows. Press **Pay $15.00**, pay on Dodo's page with the test card `4242 4242 4242 4242`, any future expiry (for example 06/32), CVC `123`. Other test cards: [Dodo's testing page](https://docs.dodopayments.com/miscellaneous/testing-process).
4. You land back on **Plan & billing**; within seconds it says the Pro pass is active, and the dashboard shows 40 runs.
5. `scripts/billing.py show YOUR_EMAIL` shows the offer as `paid` with its payment id.
6. Refund test: refund the payment in the Dodo dashboard. The pass ends and the account is back on Free.

Checks worth doing once: pay with a declining test card (nothing changes); resend the webhook from Dodo's dashboard (the API answers `duplicate` or `already granted`, and no second pass appears); open `/app/billing?offer=...&status=succeeded` by hand without paying (nothing changes).

## Switching plans for free while developing

Unchanged and independent of Dodo. `scripts/grant_plan.py` writes a pass directly (source `dev`):

```
.venv/Scripts/python scripts/grant_plan.py you@example.com pro      # Pro for 30 days, 40 runs
.venv/Scripts/python scripts/grant_plan.py you@example.com plus 7   # Plus for 7 days
.venv/Scripts/python scripts/grant_plan.py you@example.com launch   # Launch Pack
.venv/Scripts/python scripts/grant_plan.py you@example.com --revoke # back to Free now (also ends Dodo passes)
.venv/Scripts/python scripts/grant_plan.py you@example.com --show
```

The newest-ending active pass wins, so `--revoke` first when switching down (Plus to Pro).

## Founder operations

| Task | Command |
|---|---|
| See pending requests and open offers | `scripts/billing.py list` |
| Approve at list price / founding price / fewer runs | `approve ID`, `approve ID --founding`, `approve ID --runs 20` |
| Offer without a request | `scripts/billing.py offer EMAIL pro --founding` |
| Reject | `scripts/billing.py reject ID --reason "..."` |
| Withdraw an unpaid offer | `scripts/billing.py cancel OFFER_ID` |
| Check product prices in Dodo | `scripts/billing.py products` |

Every approval, rejection, offer and cancellation is written to `admin_audit_log`. Every webhook is stored once in `billing_events` with its result. A result containing "refund this payment" (someone paid twice, or paid a withdrawn offer) needs a manual refund in the Dodo dashboard.

## Going live

1. Dodo live-mode verification approved.
2. In **live** mode repeat setup step 1 (products, API key, webhook with the production URL). Live ids and secrets differ from test ones.
3. Replace all Dodo values on Render and set `DODO_PAYMENTS_ENVIRONMENT=live_mode`. Run `scripts/billing.py products` against live.
4. One real $9 purchase by the founder, then a refund, before the first customer.

## What is not built yet

- payment.md's cost ledger and per-run reservation (provider-cost limits). Today a pass is limited by its run count and the plan limits in `app/plans.py`; the cost ledger matters once Claude is switched on for paid runs.
- Automatic subscriptions (V2 gate in payment.md).
- A web admin page. Approvals stay on the command line on purpose: there is no admin endpoint to attack.
