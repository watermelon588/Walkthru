# Walkthru payments, access and cost-safety decision

**Status:** Accepted for the V1 launch process  
**Decision date:** 2026-09-23  
**Implementation status:** Designed, not yet implemented. T14 remains the implementation task.  
**Scope:** Founder-gated paid access, Dodo Payments, internal usage credits, model-cost controls and the path to self-serve billing.

## Executive decision

Walkthru V1 will **not** offer instant, public access to paid AI capacity.

- Free access remains available within the published free limits.
- A user who wants paid access submits a request.
- The founder reviews capacity, intended use and abuse risk.
- Only an approved user receives a private, expiring checkout link.
- A successful, verified Dodo Payments webhook activates a fixed 30-day entitlement with limited Walkthru credits.
- Payment alone never grants unlimited model access.
- Every run must pass both the user's credit limit and Walkthru's internal provider-cost limits before any paid model call is made.
- V1 paid access does not auto-renew. The user requests another access period after expiry. This keeps capacity and cash exposure under founder control.
- V2 may introduce instant self-serve subscriptions only after real demand, cost and abuse data prove that the controls work.

This is intentionally a concierge paid beta, not a normal open SaaS subscription launch.

## Why this decision exists

The founder does not currently have a credit card and cannot safely finance unknown model usage before revenue exists. Dodo also does not split a customer's payment directly between Walkthru and Google, Anthropic or OpenAI. Dodo collects customer money for Walkthru; Walkthru remains responsible for paying its model providers.

The founder-gated design solves the immediate operational problem:

1. Walkthru controls how many paid customers can enter.
2. Provider balance can be funded in small steps rather than speculatively.
3. Each approved user has a known maximum usage liability.
4. The founder can observe real token consumption and attack patterns before opening self-serve purchases.
5. A payment cannot race ahead of available model capacity because checkout is created only after approval.

It does not eliminate the need for a small provider balance. There can be a delay between a customer paying Dodo and the payout reaching the founder's bank. Walkthru must maintain a small operating float or delay activation until enough provider balance is available.

## V1 customer journey

```text
Free user
   |
   v
Request paid access
   |
   v
pending_review
   |
   +---- rejected / waitlisted
   |
   v
Founder approves an exact offer
plan + price + credits + 30-day expiry + maximum paid-model budget
   |
   v
approved_to_purchase
   |
   v
Private one-use Dodo checkout link, bound to that user and offer
   |
   v
Dodo payment succeeds
   |
   v
Signed, idempotent webhook activates entitlement
   |
   v
active for 30 days, bounded by credits and cost limits
   |
   +---- usage exhausted -> exhausted
   +---- 30 days elapsed -> expired
   +---- fraud/refund/admin action -> suspended or revoked
```

The browser redirect after checkout is only a confirmation screen. It is never trusted to activate access. Only a verified server-to-server webhook can do that.

## V1 commercial rules

### Free

- Open to eligible users without founder approval.
- Uses the free/low-cost provider pool and the existing deterministic checks.
- Enforced monthly run, step, concurrency and rate limits.
- Free usage can be paused globally if provider quota is unavailable.

### Paid access

- Request-only and capacity-limited.
- Approval is tied to one authenticated Walkthru user and email.
- The offer specifies plan, price, credit grant, provider-cost allowance, activation window and expiry.
- V1 uses a **one-time 30-day access pass**, even if the UI calls it a monthly Pro access period. There is no automatic renewal in V1.
- Unused V1 credits expire at the end of the access period and do not roll over. This must be stated before checkout.
- Overage is disabled. A zero balance fails closed and offers a new access request. It never creates a surprise bill.
- The founder can suspend future runs but cannot erase already-consumed ledger entries.

### What “limited premium access” means

Paid users are eligible for premium routing, but not every model call must use the most expensive model. Walkthru uses deterministic code and the least expensive model that clears the quality gate, then escalates uncertain browser decisions and high-value report synthesis to the approved premium model.

Two limits apply at the same time:

1. **Customer limit:** remaining Walkthru run credits and the plan's step/site limits.
2. **Financial limit:** remaining per-user, daily and global provider-cost allowance.

The stricter limit wins. A marketing run allowance is a maximum, not permission to exceed the financial safety gate.

## Current prices and Dodo fee calculation

The current product source of truth is [SPEC.md](SPEC.md): Launch Pack $9, Pro $15/month and Team $39/month. The landing page currently shows the same prices. There is no defined “Plus” plan today. This document does not silently rename plans or change public pricing.

Dodo's published Standard price on 2026-09-23 is **4% + $0.40 per successful transaction**, with no fixed setup fee. The calculation is:

```text
Dodo transaction fee = price × 0.04 + $0.40
Net after transaction fee = price - Dodo transaction fee
```

| Offer | Gross price | Standard Dodo fee | Net after transaction fee |
|---|---:|---:|---:|
| Launch Pack | $9.00 | $0.76 | $8.24 |
| Current Pro | $15.00 | $1.00 | $14.00 |
| Possible $19 founding Pro | $19.00 | $1.16 | $17.84 |
| Current Team | $39.00 | $1.96 | $37.04 |

These are exact calculations using the published standard transaction rate, but they are **not final bank receipts**. Refund fees, disputes, payout fees, tax treatment, currency conversion and any account-specific pricing can change the final amount.

Additional published Dodo costs to account for:

- Refund processing: $1 per refund.
- Dispute handling: $30 per dispute, in addition to lost transaction funds where applicable.
- Payout below $1,000: $5.
- USD SWIFT payout for a non-US business: $25 where that route is used.
- Non-USD settlement can include standard FX conversion.
- Usage-based billing event ingestion is currently listed at $1 per million events. This is negligible at V1 scale, but Walkthru will still maintain its own authoritative ledger.

Dodo's default payout schedule is twice monthly. Eligible balances from the 1st to 15th are initiated on the 18th; balances from the 16th to month-end are initiated on the 4th of the following month. Bank arrival is usually another 1 to 2 business days. The documented minimum is $50 equivalent overall, with INR wallet guidance also showing Rs 1,000. Therefore, customer money is not available instantly to pay the model provider.

Sources:

- [Dodo Payments pricing](https://dodopayments.com/pricing)
- [Dodo payout structure](https://docs.dodopayments.com/features/payouts/payout-structure)
- [Dodo credit-based and usage-based billing](https://docs.dodopayments.com/developer-resources/billing-deconstructions/openai)
- [Dodo webhook security and idempotency](https://docs.dodopayments.com/developer-resources/webhooks)

### If a Plus plan is added later

Its exact Dodo transaction deduction is `price × 4% + $0.40`. The plan must not be implemented or advertised until the founder approves its price and entitlements and both SPEC.md and the landing-page content are updated together.

## Unit economics and safe allowances

Walkthru's existing engineering goal is:

- Free run cost no more than $0.02.
- Paid run cost no more than $0.20.

The $0.20 figure is an evaluation ceiling, not a sustainable average for every included run:

| Offer | Net after Dodo transaction fee | Published maximum runs | Cost if every run costs $0.20 | Result before hosting/payout costs |
|---|---:|---:|---:|---:|
| Launch Pack | $8.24 | 20 | $4.00 | $4.24 remains |
| Current Pro | $14.00 | 60 | $12.00 | $2.00 remains |
| Current Team | $37.04 | 250 | $50.00 | **$12.96 loss** |

Consequences:

- Team cannot be sold with 250 premium-cost runs under the current economics.
- Pro is too thin if the average run approaches $0.20.
- The existing run counts are viable only if most work stays deterministic/free/cheap and premium escalation is selective.
- T17B and paid-model evaluation must measure the real average and p95 cost before any self-serve launch.

### V1 cost-allocation rule

Until measured data supports a different figure, the maximum internal provider-cost allowance for an approved offer is **25% of net revenue after the standard Dodo transaction fee**.

| Offer | Provisional maximum provider spend for its access period |
|---|---:|
| $9 Launch Pack | $2.06 |
| $15 Pro | $3.50 |
| $19 founding Pro scenario | $4.46 |
| $39 Team | $9.26 |

This is an internal safety ceiling, not a promise that the customer owns provider dollars. Customers own Walkthru entitlements, not Google or Anthropic credits. Taxes, payout fees, refunds and infrastructure still come from the remaining amount.

The founder may grant fewer credits for V1 than the public maximum, but the exact grant must be shown before payment. Walkthru must not sell an offer whose worst-case reserved cost exceeds its remaining global provider budget.

## Model-provider decision for paid access

The paid-model choice remains subject to the postponed real-browser evaluation. The billing architecture must not hard-code a provider.

The leading card-free route is:

1. Create a dedicated Google Cloud project for production model inference.
2. Use eligible Indian Google Cloud Billing with INR and UPI.
3. Use pay-as-you-go, not Provisioned Throughput.
4. Access Claude through Google Cloud's managed partner-model API when it wins the evaluation.
5. Keep Gemini and lower-cost routes available for bounded work and fallback.

Google states that qualified Indian organizations can make manual UPI payments or set UPI as the primary method for recurring payments. It normally asks for an initial prepayment of about Rs 500 to Rs 1,000. Eligibility must be verified on the founder's actual billing account before promising paid access.

Current Google Cloud partner-model pricing must be checked again at implementation time. As a reference snapshot on 2026-09-23, Google lists Claude Sonnet 4.6 at $3.30 per million input tokens and $16.50 per million output tokens for contexts up to 200k. Token volume can vary materially by site, journey length, retries, screenshots and report output.

Sources:

- [Google Cloud UPI payments in India](https://docs.cloud.google.com/billing/docs/resources/upi-payment-india)
- [Claude models on Google Cloud](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/partner-models/claude)
- [Google Cloud partner-model pricing](https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing)

Consumer ChatGPT, Claude or Gemini subscriptions do not provide API capacity for Walkthru. They cannot replace server-side API billing.

## Initial founder cash requirement

### Minimum practical launch cash

| Item | Expected initial cash requirement | Notes |
|---|---:|---|
| Google Cloud billing activation/prepayment | Rs 500 to Rs 1,000 | Official typical UPI prepayment guidance; confirm account eligibility. |
| Chrome Web Store developer registration | $5 one-time | Already identified in the project launch checklist. |
| Domain | Registrar-specific, commonly about $10 to $20/year | Do not treat this estimate as a quote. |
| Dodo setup | $0 fixed setup fee on Standard | Transaction fees apply only when a transaction succeeds. |
| Supabase, Vercel, Oracle, Resend | $0 while within chosen free allowances | Monitor quotas and current terms. |
| Optional API VPS | About $5/month | Only if Oracle Always Free is not suitable. |

The smallest realistic starting float is therefore the Google prepayment plus store/domain expenses. The founder should not approve paid offers whose reserved provider liability exceeds the funded provider balance.

### Ongoing variable costs

- Dodo transaction, payout, refund, dispute and FX fees.
- Model tokens actually consumed.
- Hosting after free allowances are exceeded.
- Email, storage and bandwidth after free allowances are exceeded.
- Taxes and local compliance, which require advice appropriate to the founder's jurisdiction.

No document can guarantee a fixed future maintenance cost because provider pricing and customer usage change. The control system limits exposure rather than predicting it perfectly.

## Proposed T14 architecture

This is a design for the future implementation. It does not authorize a production schema migration by itself.

### Server-side records

| Record | Purpose | Important properties |
|---|---|---|
| `access_requests` | User asks for paid access | user id, requested use, state, timestamps |
| `approved_offers` | Founder-created immutable offer | user id, plan, gross price, credits, provider budget, expiry, checkout token hash, approval actor |
| `billing_events` | Dodo webhook audit and idempotency | unique webhook id, event type, raw-body hash, processing state |
| `entitlements` | Current authority to use paid features | user id, offer id, state, start, expiry, remaining credits |
| `credit_ledger` | Append-only credit truth | grant, reserve, consume, release, refund, expiry; idempotency key |
| `cost_ledger` | Estimated and actual provider cost | run id, provider, model, input/output tokens, price snapshot, reserved/actual cost |
| `admin_audit_log` | Founder actions | actor, action, target, previous/new state, timestamp |

Balances are derived from append-only ledger entries. Client-provided balance, price, plan, role or provider-cost values are never trusted.

### API boundaries

```text
POST /billing/access-requests
  Authenticated user creates one pending request. Strict rate limit.

POST /admin/billing/access-requests/{id}/approve
  Founder-only. Creates an immutable offer and one-use checkout capability.

POST /billing/offers/{id}/checkout
  Authenticated approved user only. Server selects allowlisted Dodo product/price.

POST /webhooks/dodo
  Public endpoint. Raw-body signature verification, timestamp validation,
  idempotency and monotonic state transitions.

GET /billing/entitlement
  Returns user-safe entitlement and usage information, never internal provider secrets.
```

### Run reservation protocol

Before the first paid model request, one database transaction must:

1. Lock the active entitlement.
2. Verify status and expiry.
3. Verify remaining run credits.
4. Verify the per-user daily and access-period provider budgets.
5. Verify the platform daily and monthly provider budgets.
6. Verify the maximum number of concurrent runs.
7. Append a credit and estimated-cost reservation.

Only after commit may the model call start. After the run, actual tokens and provider pricing are written and unused reservation is released. A crashed run is reconciled by a bounded background job. Repeating the same run or event id cannot consume or grant twice.

If the ledger or cost service is unavailable, premium inference fails closed. It does not “temporarily allow” an unmetered run.

## Abuse and billion-dollar-bill prevention

There is no absolute zero-risk promise with a metered cloud provider. In-flight requests, delayed billing data and compromised administrator credentials can create some overage. The goal is defense in depth and a deliberately small blast radius.

### Payment and entitlement controls

- No public paid checkout route in V1.
- Approval bound to the authenticated user, exact server-side product and price.
- Checkout capability is random, hashed at rest, one-use and expires within 24 hours.
- Activation only from a verified `payment.succeeded` webhook.
- Verify the exact raw webhook body, signature, timestamp and business/account identifiers.
- Unique `webhook-id` prevents duplicate grants; event state handles out-of-order delivery.
- Refund, dispute or chargeback suspends unused entitlement and creates compensating ledger entries.
- Never store card or UPI credentials. Dodo hosts payment handling.

### Account and administrator controls

- Supabase authentication plus server-side ownership checks on every billing route.
- Founder/admin identity is server-side, not a client-editable metadata flag.
- MFA for founder, Dodo, Supabase and Google Cloud accounts.
- No shared administrator account.
- Every approval, suspension and manual credit adjustment is audited.
- Admin routes have a stricter rate limit and are not accessible from the extension.

### Application usage controls

- One active paid run per user in V1.
- Per-user daily run limit in addition to access-period credits.
- Existing same-origin, step, time, CAPTCHA and safe-mode limits remain mandatory.
- Strict maximum prompt size, output tokens, retry count and report-generation count.
- Screenshots are bounded and never blindly converted into repeated model calls.
- Every provider request carries a Walkthru run id for reconciliation.
- Circuit breaker opens on cost-ledger mismatch, provider anomalies or unusual failure rate.
- Global kill switch disables premium routing without disabling deterministic/free reports.

### Google Cloud controls

- A dedicated production inference project with no unrelated resources.
- Least-privilege service account restricted to required inference APIs and models.
- Credentials remain server-side in a production secret store and are rotated after any suspected exposure.
- Pay-as-you-go only. Do not purchase Provisioned Throughput in V1.
- Set the lowest workable project/model request quota and concurrency.
- Use a service-specific spend-cap budget if the founder's project supports it.
- Also configure alerts at 25%, 50%, 75%, 90% and 100% of the small monthly budget.
- Programmatic budget notification should trip the Walkthru premium-model kill switch.

Google explicitly warns that alerts-only budgets do not cap spending. Spend-cap budgets are a preview feature for eligible services, enforcement is not instantaneous and in-flight calls may still finish. Therefore, Google billing controls are the last line of defense, not the primary ledger.

Sources:

- [Google Cloud budgets and alert limitations](https://docs.cloud.google.com/billing/docs/how-to/budgets)
- [Google Cloud spend-cap budgets](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps)
- [Vertex AI quotas](https://cloud.google.com/vertex-ai/docs/quotas)

### Initial production caps

The exact numbers must be derived from the T17B/paid-model benchmark, funded balance and approved seat count. Until then:

- Zero public paid seats.
- Approve users in very small batches.
- Never approve aggregate provider liability above the funded Google Cloud balance.
- Keep at least a 2x buffer between reserved provider liability and immediately available provider funds.
- Stop new approvals if actual p95 run cost breaches the approved estimate by 20%.
- Review usage daily while any V1 paid entitlement is active.

## Refunds, expiry and failure behavior

- Failed checkout grants nothing.
- Processing checkout remains pending and grants nothing.
- Successful payment with an internal activation failure creates an alert and retryable reconciliation item; it must not create a second charge.
- A provider outage does not consume a completed run credit if no meaningful run was delivered.
- Reserved credits are released for safely classified infrastructure failures.
- Customer-requested refunds follow the disclosed policy; successful refunds revoke the corresponding unused entitlement.
- At 30 days, the entitlement expires automatically even if credits remain.
- The user can still view previously generated reports after expiry unless removed under the data-retention policy.

## Monitoring and founder operating routine

The V1 dashboard needs a private billing operations view showing:

- Requests awaiting review.
- Approved but unpaid offers.
- Active seats, expiry and remaining credits.
- Reserved versus actual provider cost by user and run.
- Daily and monthly total model cost.
- Failed or duplicate webhooks.
- Ledger reconciliation failures.
- Refunds, disputes and suspicious activity.
- Premium-model kill-switch state.

Founder routine while paid seats are active:

1. Review cost and anomaly alerts daily.
2. Reconcile Dodo payments, entitlements and the internal ledger at least weekly.
3. Compare provider invoice usage with `cost_ledger` at least weekly.
4. Increase seat count only after the previous cohort's p95 cost and abuse rate are understood.
5. Rotate secrets and suspend premium routing immediately on unexplained cost growth.

## Testing gates before the first paid user

- Dodo test-mode checkout completes only for an approved offer.
- Changing client price, plan, user id or credit grant is rejected.
- Forged, stale and malformed webhooks are rejected.
- Duplicate and out-of-order webhooks never grant twice.
- Checkout success redirect without webhook grants nothing.
- Concurrent run starts cannot overspend the same credits.
- Expired, suspended, exhausted and refunded access fails closed.
- Failed provider call releases the correct reservation exactly once.
- Global budget exhaustion blocks premium calls.
- Premium kill switch works without a deployment.
- Admin actions require the founder role and appear in the audit log.
- Database RLS prevents users reading another user's request, entitlement or ledger.
- A full refund/dispute reconciliation test passes in Dodo test mode.
- A chaos test simulates a process crash between reservation, provider call and reconciliation.

## V2 self-serve release gate

Instant purchase may replace founder approval only when all of the following are true:

- At least 10 paid access periods have completed with reconciled billing.
- At least 30 days of production cost data exists.
- Real average and p95 run costs preserve the target gross margin for every plan.
- There are no unresolved ledger mismatches.
- Abuse limits and automated suspension have been tested in production-like conditions.
- Spend cap or equivalent provider-side protection is active.
- Refund, dispute, renewal and cancellation paths have passed test mode and a controlled live test.
- Legal pages clearly disclose billing, expiry, rollover, privacy and refund behavior.
- The founder explicitly approves revised self-serve pricing and entitlements.

## Rejected approaches

### Public self-serve paid access in V1

Rejected because payment volume, provider cost and abuse patterns are not known yet.

### Turn on provider billing manually after every customer payment

Rejected because it is slow, error-prone and unnecessary. Billing is configured once; Walkthru controls access with entitlements and cost limits.

### Split each payment automatically into founder money and user-owned provider credits

Rejected because Dodo credits are Walkthru entitlements, not transferable Google, Anthropic or OpenAI balances. Provider accounts are separate commercial relationships.

### Unlimited premium-model usage

Rejected because a fixed subscription price with unbounded variable cost can create unlimited liability.

### Trust a Google Cloud budget alert as the only cap

Rejected because alerts-only budgets do not stop usage and billing data can be delayed.

### Buy provisioned model capacity for V1

Rejected because it creates fixed costs before demand is proven.

## Decisions still requiring explicit founder approval

This document finalizes the **gated V1 operating model**. It does not silently change pricing or the paid model. Before T14 production implementation, the founder must explicitly approve:

1. Keep current $15 Pro or change it to the discussed $19 founding Pro price.
2. Whether Launch Pack and Team remain visible while paid access is request-only.
3. Exact V1 credit grants per approved offer after benchmark cost data exists.
4. The paid provider/model after the real-browser evaluation.
5. Refund policy and legal wording.
6. The initial funded provider balance and platform-wide daily/monthly caps.

Until those are approved, checkout stays disabled and free access remains the only public path.
