# trywalkthru.com: domain, email and deployment walkthrough

Prepared 2026-10-03. This is a follow-along plan, not a record of a completed deployment.
The founder confirmed **trywalkthru.com**, purchased at Hostinger. This supersedes the earlier domain spelling in chat.

## Production architecture discussion update, 2026-10-04

**Latest direction:** founder accepts the Cloudflare/frontend plus production-server direction and asks for a reliable Google Cloud backend. Target Compute Engine for the current Python API and background worker design; exact resources/region depend on budget and measured requirements. Supplied Google Cloud screenshots now confirm **₹28,797 of unused general trial credit**, **90 days remaining**, ending **3 January 2027**, and show project **Walkthru** on the Compute Engine API enablement screen. This supersedes the earlier ambiguous $5 discussion. No API enablement, VM creation or paid billing upgrade has been performed by this agent.

Cloudflare serves the same built JavaScript, images, fonts and styles as other static hosts. GSAP and ScrollTrigger execute in the visitor's browser, including the existing reduced-motion behavior. CDN delivery does not replace animation code; verify motion, fonts/assets and security headers on the deployed build.

### Google Cloud budget and reliability check

**Cost-sensitive revision after the VM form:** start with **`e2-small` (2 GB RAM), Sydney, regular/on-demand**, rather than the earlier 4 GB draft. This is a practical pilot candidate, not a measured minimum or confirmed production capacity. Models are called remotely and browser execution is in the user's extension. Start with one Uvicorn process and one supervised queue worker (`JOB_WORKERS=0` on API, `JOB_WORKERS=1` on standalone worker), durable Postgres checkpoints, and a 20 GB balanced boot disk. Queue-worker limits do not independently cap every API scan/crawl path; verify concurrent requests before opening a broad beta. Add a small swap file only as an emergency buffer; sustained swap is a resize signal.

Planning comparison (USD, always on, approximately 730 hours/month and 2,160 hours/90 days, no committed-use discount):

| Configuration | Monthly fixed baseline | 90-day fixed baseline |
| --- | --- | --- |
| Sydney e2-medium, 4 GB, 20 GB balanced disk | about $40-43 | about $118-127 |
| Sydney e2-small, 2 GB, 20 GB balanced disk | about $22-25 | about $65-74 |
| Iowa e2-small, 2 GB, 20 GB balanced disk | about $17.87 | about $52.97 |
| Eligible US e2-micro, 1 GB, 20 GB standard disk | about $3.65 with free compute/disk allowance | about $10.79 with applicable monthly allowances |

Sydney ranges are provisional projections from the founder's approximately $36/month medium VM form estimate and the shared-core size pricing relationship; exact updated small-instance/disk quote must be checked in the console. Iowa uses the official displayed on-demand small rate $0.016752855/hour plus balanced disk $0.000136986/GiB/hour and in-use IPv4 $0.005/hour (one free hour/month). These baselines exclude outbound traffic, snapshots, chargeable logging, other services, tax and currency/account adjustments. Traffic to the Australia database is not covered by the US free-tier outbound allowance. Do not label the US VM fully free. [VM pricing](https://cloud.google.com/products/compute/pricing/general-purpose), [Disk pricing](https://cloud.google.com/compute/disks-image-pricing), [IPv4 pricing](https://cloud.google.com/vpc/network-pricing).

Keep the current Sydney DB and colocate the pilot VM: moving only the API to Iowa saves roughly $15-22 over the full trial but introduces a cross-continent database round trip on repeated API/agent/checkpoint operations. Benchmark before accepting that tradeoff. A 1 GB US VM is the lowest-cost experiment, not the recommended customer-facing baseline without load measurements. Review CPU, memory, swap and job latency after the initial pilot; resize to medium only if necessary. Supported E2 resizing requires stopping/editing/restarting the VM; region moves require a separate migration. [Resizing](https://docs.cloud.google.com/compute/docs/instances/changing-machine-type-of-stopped-instance).

Unused trial credit still expires after 90 days. Saving credits does not extend time. Use the trial to establish affordable operating costs and reproducible deployment: dependencies locked, Python 3.12 environment, separate service/env configuration, state in Supabase, stable API domain, restart/recovery checks and a redeployment runbook. Review continued hosting by **1 December 2026** and complete any planned migration by **20 December**, ahead of the shown **3 January 2027** expiry. These are planning dates, not scheduled reminders. No new provider or paid activation.

- Check the intended project's Cloud Billing account, available general credit and any credit expiry before provisioning. Gemini API in AI Studio prepaid credit is separate and cannot pay Compute Engine costs. [Google Cloud UPI/payment distinctions](https://docs.cloud.google.com/billing/docs/resources/upi-payment-india).
- Use the confirmed trial credit for backend setup and testing. Trial resources stop when the trial expires or credit is exhausted unless upgraded to paid billing. Decide continued hosting before **3 January 2027**, with an earlier check if credit is running low. Upgrading changes billing behavior; it is a separate decision from enabling the API or preparing the VM. [Trial conditions](https://docs.cloud.google.com/free/docs/free-cloud-features).
- Eligible Compute Engine free-tier usage includes a non-preemptible `e2-micro` in `us-west1`, `us-central1` or `us-east1`, with 30 GB-months standard persistent disk. Asia regions and larger VMs are outside this compute allowance. [Google Cloud free-tier rules](https://docs.cloud.google.com/free/docs/free-cloud-features).
- In-use external IPv4 for a standard VM currently costs $0.005/hour with one free hour/month, about $3.65 for a 730-hour month. This is the IP component, not a complete server quote. Storage type, snapshots, network usage, logging and taxes/currency/account details may change the total. [Network pricing](https://cloud.google.com/vpc/network-pricing).
- An `e2-micro` is a small-budget candidate, not confirmed production capacity. Choose based on concurrent runs, memory/CPU measurements and latency to the existing Supabase region. A US free-tier VM may add latency to the existing Australia-region database. Use regular rather than Spot/preemptible compute for the primary backend.
- Prepare separate supervised API and job-worker processes, durable Postgres checkpoints, queued-job recovery, controlled ingress with HTTPS, safe logs, availability checks, a backup/recovery process and release rollback. Prove the deployed restart/client/worker tests from the existing checkpoint/idempotency guides. Single-VM recovery improves reliability but does not provide automatic regional/multi-server failover.
- Cloud Run is an alternative managed runtime, but the existing continuously polling job threads need always-allocated CPU/minimum-instance configuration or a job-scheduling redesign. Do not deploy request-only scale-to-zero defaults and assume periodic jobs will keep running. [Cloud Run background execution](https://docs.cloud.google.com/run/docs/configuring/billing-settings).

**Next screen:** in project **Walkthru**, click **Enable** on the Compute Engine API page. This enables VM management without itself creating a VM. Then open **Compute Engine > VM instances > Create instance** and inspect machine, region, disk and monthly estimate before clicking the final Create button. Keep trial billing for now; confirm the project's billing linkage during setup. No paid billing upgrade, Cloudflare Workers upgrade or model has been activated.

**Founder explicitly excludes Render.** Its beta steps below are historical reference and must not be followed for the current setup. The working frontend target is Cloudflare; Supabase and Hostinger business inbox remain intended. Confirm the Google Cloud account and exact resource budget before provisioning or DNS changes.

The recorded roadmap's production API/worker host is a Google Cloud VM; the older handoff mentioned Oracle. Cloudflare can manage DNS and proxy HTTPS to that server without hosting its Python processes. The recommended route for the existing code is Cloudflare frontend plus an always-on Linux VM behind Cloudflare, with `APP_ENV=production`, `CHECKPOINTER=postgres`, Supabase and verified worker/restart behavior. This recommendation is not founder approval of a provider or paid plan.

If the backend must execute on Cloudflare itself, evaluate **Cloudflare Containers**. It runs Linux container images and is a closer fit than native Python Workers for this API's psycopg pool, job threads and periodic scheduler. Python Workers support FastAPI, but compatibility of the whole dependency/runtime stack remains untested; moving to Workers would require separate validation/adaptation. [Python packages](https://developers.cloudflare.com/workers/languages/python/packages/), [Containers lifecycle](https://developers.cloudflare.com/containers/concepts/architecture/).

Containers requires Workers Paid, currently $5/month base plus metered container resources and other applicable usage. Its sleep/start/restart lifecycle must be coordinated with periodic and queued jobs; persistent customer state stays in Supabase. It has not been configured or production-verified for this repo. [Containers pricing](https://developers.cloudflare.com/containers/platform/pricing/).

## Starting point and order

Read against `AGENTS.md`, `handoff.md`, the latest `CURRENT_STATE.md`, `ARCHITECTURE.md`, `SKILLS.md`, the V0 sessions in `tasks/todo.md`, `docs/deploy.md`, `docs/checkpoints-and-request-logs.md`, `docs/run-idempotency.md`, `render.yaml`, `.env.example`, `apps/web/vercel.json` and the extension build configuration.

Proceed in the founder's order: domain and inbox, frontend, backend, then connected sign-in/email/extension acceptance. The frontend can be published first with its intended API address configured, but scans and API-backed features will only work after backend deployment.

| Address | Intended purpose | Provider |
| --- | --- | --- |
| `trywalkthru.com` | Primary website and dashboard | Frontend host selected below |
| `www.trywalkthru.com` | Redirect to the primary website | Frontend host |
| `api.trywalkthru.com` | FastAPI API and `/mcp` | Production host pending: always-on VM or evaluated Cloudflare Containers; Render excluded |
| `hello@trywalkthru.com` | Business inbox and customer replies | Hostinger if its trial/renewal works for the founder |
| `notify.trywalkthru.com` | Application sending domain | Resend |
| `noreply@notify.trywalkthru.com` | Reports, invitations and sign-in email | Resend API / Supabase SMTP |

Buying the domain does not require buying Hostinger website hosting. DNS tells visitors which hosting service to use. Website records and email records can coexist.

## 1. Hostinger domain and business inbox

1. In Hostinger, open **Domains > trywalkthru.com > Manage**. Check that the registration is active and complete any registrant email verification requested by Hostinger.
2. Review the domain expiry/renewal setting. Keep the domain locked; enable account two-factor authentication if available.
3. Open **DNS / Nameservers**. Record the current nameservers and save a copy of the existing DNS records before editing. Leave Hostinger nameservers in place for now.
4. Open **Emails**, find the domain and check the offer's duration, included mailboxes, renewal price and automatic-renewal setting. The founder's account-specific checkout now confirms **12 months free, two mailboxes, total ₹0**. It says an annual Starter Business Email subscription will be charged automatically afterward at the then-available price, which is not shown. This supersedes the generic 30-day domain trial in the public documentation. Turn off the email subscription's auto-renew after activation if avoiding an unknown renewal charge; keep the domain's renewal setting separate. Activation/cancellation are not yet verified. [General Hostinger email limits](https://www.hostinger.com/support/4625828-parameters-and-limits-of-hostinger-email/).
5. If the offer and eventual renewal are acceptable, activate it and create `hello@trywalkthru.com`. Start with one mailbox. Use `support@trywalkthru.com` as an alias if the plan includes aliases, rather than purchasing another mailbox immediately.
6. Set a unique mailbox password directly in Hostinger. Keep credentials private.

**Recommendation:** the included mailbox is useful for business correspondence if you accept its expiry/renewal terms. It is optional for deploying the app. Resend handles automated app mail; it does not replace a normal business inbox in this setup. If avoiding recurring inbox costs, choose a receiving/forwarding provider separately before publishing a support address.

### The supplied screenshot

It reports **SPF needs attention**, **DKIM connected**, and **DMARC connected**. It does not show MX status, nameservers, actual TXT values, or the offer price. Those remain unverified. Public DNS-over-HTTPS lookups were unavailable from this execution environment; no live DNS result is claimed.

1. Expand the SPF row to inspect the required record and any existing value.
2. If Hostinger is your only current mail provider and the domain uses Hostinger nameservers, click **Set up automatically**. Review the proposed email-record changes, then confirm. Hostinger's documentation calls this **Connect automatically** and says it adds MX, SPF and DKIM records. [Automatic email connection](https://www.hostinger.com/support/8671304-set-up-a-domain-for-hostinger-email-automatically/).
3. If another provider already handles mail, compare the existing records first. Do not overwrite that provider's MX records just to clear a warning.
4. Recheck SPF, DKIM, DMARC and MX. Preserve the existing working DMARC record; inspect its policy rather than replacing it unnecessarily.
5. Keep exactly one SPF policy beginning `v=spf1` at each DNS name. Do not add a second root SPF policy beside an existing one. Copy Hostinger's actual required value; do not guess it.
6. Allow propagation, potentially up to 24 hours per Hostinger's guidance. Send from the mailbox to your personal inbox and reply back. Inspect message authentication results where the recipient provides them.

**Exit:** registration verified, renewal understood, DNS records saved, mail delivered in both directions, and authentication checked. No website A/CNAME records need to be guessed before selecting its host.

## 2. Choose the frontend host

The repository's existing setup targets Vercel, but the older claim that it is free for this SaaS needs correction. Vercel restricts Hobby to non-commercial personal use; advertising a product for sale is included in commercial use. Use an eligible commercial plan if selecting Vercel. Do not activate a paid plan until the founder chooses it. [Vercel fair-use rules](https://vercel.com/docs/limits/fair-use-guidelines).

Cloudflare Pages is a candidate free static-hosting route for this Vite app, within its allowances. It requires translating the existing Vercel headers and deciding who manages DNS. This guide offers it as a choice, not an already approved architecture change. [Pages product](https://www.cloudflare.com/en-in/developer-platform/products/pages/), [Pages limits](https://developers.cloudflare.com/pages/platform/limits/).

### Vercel route

1. Sign in and import the existing GitHub repository `watermelon588/Walkthru` using the reviewed release branch/commit. Select an eligible account plan.
2. Set **Root Directory** to `apps/web`, framework to **Vite**, build command to `npm run build`, output directory to `dist`; install with the existing lockfile (`npm ci`).
3. Add these production build variables:

   | Variable | Value |
   | --- | --- |
   | `VITE_SUPABASE_URL` | Existing Supabase project URL |
   | `VITE_SUPABASE_ANON_KEY` | Existing public/publishable key |
   | `VITE_API_URL` | `https://api.trywalkthru.com` |
   | `VITE_EXTENSION_ID` | ID matching the extension you will distribute |

4. For the current unpacked beta, the configured extension ID is `cilngbcfpoojecjoiklimnjnomjglcdo`. Store distribution requires matching the actual store ID and packaging. Keep Supabase secret/service keys and model/email/payment keys out of frontend variables.
5. Deploy. The current `vercel.json` supplies SPA routing and security headers. Test `/`, `/login` and a direct route refresh. API-backed controls will remain unavailable until step 3.
6. Open **Project > Settings > Domains** and add `trywalkthru.com` and `www.trywalkthru.com`. Make the root the primary address and redirect `www` to it.
7. In Hostinger's DNS editor, add the exact root **A** and `www` **CNAME** values shown by Vercel. Resolve conflicting website records only at those names; preserve email and verification records. Keep Hostinger nameservers. Wait for Vercel to report valid configuration and issue HTTPS. [Vercel custom-domain setup](https://vercel.com/docs/domains/set-up-custom-domain).

Do not copy generic Vercel IP/CNAME examples when the project dashboard recommends different values. DNS propagation and SSL issuance are separate checks.

### Cloudflare Pages route, if selected

1. Create a Pages project using Git integration with the same reviewed repository/branch. Set root `apps/web`, build `npm run build`, output `dist`, and the same four public variables above. Choose a build Node version compatible with the locked Vite version.
2. Before publishing, prepare `apps/web/public/_headers` carrying the existing security header values from `vercel.json`. Cloudflare does not interpret `vercel.json`. This preparation is still pending; no application file was changed by writing this guide. [Pages headers](https://developers.cloudflare.com/pages/configuration/headers/).
3. Verify SPA deep links. Pages supplies SPA fallback when the output has no top-level `404.html`; verify this behavior on the actual build. [Serving Pages](https://developers.cloudflare.com/pages/configuration/serving-pages/).
4. To serve the **root** `trywalkthru.com` on Pages, add the domain as a Cloudflare zone. Copy and verify all Hostinger MX/TXT/DKIM/DMARC and verification records before changing nameservers at Hostinger to Cloudflare's assigned pair. If DNSSEC is enabled, coordinate disabling the old delegation and enabling the new one after activation.
5. Hostinger remains the registrar and can remain the mailbox provider; DNS edits then happen in Cloudflare. Keep email-related records DNS-only. Add both domains through Pages **Custom domains** and configure `www` to redirect to the root, preserving path and query.
6. If retaining Hostinger nameservers instead, Pages supports a custom **subdomain** via CNAME, such as `www.trywalkthru.com`; serving the root requires the separate DNS arrangement above. [Pages custom domains](https://developers.cloudflare.com/pages/configuration/custom-domains/).

**Exit:** chosen host serves HTTPS, canonical-domain redirect works, direct route refresh works, security headers are present, and business mail still works.

## 3. Backend deployment

### Prepare the release

1. Check the latest V0-S2/S5/S6 acceptance items in `tasks/todo.md`: durable restart recovery, installed Chrome acceptance, release checks and rollback remain open. Prepare a reviewed release commit and matching extension artifact.
2. Confirm the historical Supabase credential rotations were completed; rotate any outstanding exposed credentials privately. Do not blindly import a dated `.env.render` export containing old keys or development settings.
3. Run the release checks from `AGENTS.md` with locked installs: API pytest/Ruff, web tests/build/lint, extension tests/type check/lint/build. Record skipped tests and unresolved failures rather than treating previous session counts as a current release check.
4. Inspect migration status against the intended database. Latest state says 0001-0003 were applied to the connected development database; independently verify the deployment database. Use the existing runner, never edit applied migrations. Production backup/maintenance approval applies before changing a live database.

### Historical Render setup for an initial limited beta, excluded by founder

**Do not follow these steps for the current deployment.** The founder rejected Render on 2026-10-04; retain this section only as context for the existing blueprint. Use the production architecture discussion above to choose and prepare the actual target.

1. Open Render **New > Blueprint**, connect the reviewed repository/branch, and inspect the `walkthru-api` service from `render.yaml`. Free service use must be treated as a limited beta. Render explicitly recommends paid instances for production. It sleeps after 15 idle minutes, can restart, and does not provide free-service shell access. [Render free-service behavior](https://render.com/docs/free).
2. Existing root is `apps/api`; the build command is:

   ```text
   pip install -r requirements.lock && pip install . --no-deps
   ```

3. Existing start command is:

   ```text
   uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers
   ```

4. The blueprint currently sets **CHECKPOINTER=memory**, which is a historical beta default. Before a production deployment, prepare/review an override or blueprint revision with the following settings; `APP_ENV=production` deliberately refuses memory mode:

   | Variable | Value / source |
   | --- | --- |
   | `WEB_URL` | `https://trywalkthru.com`, no trailing slash |
   | `APP_ENV` | `production` |
   | `CHECKPOINTER` | `postgres` |
   | `DATABASE_URL` | Private intended-database session/direct connection with `sslmode=require` |
   | `CHECKPOINT_DATABASE_URL` | Same database's session/direct connection, or reuse `DATABASE_URL` |
   | `SUPABASE_URL` | Existing project URL |
   | `SUPABASE_PUBLISHABLE_KEY` | Existing public key |
   | `SUPABASE_SECRET_KEY` | Current rotated server-only key |
   | `GROQ_API_KEY`, `GOOGLE_API_KEY`, `OPENROUTER_API_KEY` | Existing approved free-provider keys, optional fallbacks as configured |
   | `PAGESPEED_API_KEY` | Existing optional key |
   | `JOB_WORKERS` | Initially `2`, matching the existing beta blueprint; measure resource use |
   | `RESEND_API_KEY`, `RESEND_FROM`, `FOUNDER_EMAIL` | Add after email verification in step 4 |

5. Choose the Supabase **session pooler on port 5432**, not transaction pooling on 6543. The founder's local network is IPv4-only. Follow the checkpoint guide's migration prerequisites and synthetic two-process restart drill. Keep total process/pool connections within the database allowance. [Checkpoint activation](checkpoints-and-request-logs.md).
6. Leave `ALLOW_LOCAL_SCANS` unset, paid-model switches off, and checkout disabled for this non-pricing V0 rollout. Do not publish the founder admin panel; it stays on the founder's machine. Trace/export settings require their own privacy review.
7. Deploy and inspect sanitized logs for checkpoint initialization and worker activity. Check `/health`, but its 200 is insufficient to prove database/RPC/provider readiness: it catches some queued-job stalls and can still return OK on a database failure. The fuller readiness work remains V0-S2.
8. In Render **Settings > Custom Domains**, add `api.trywalkthru.com`. At the current authoritative DNS provider, add **CNAME `api`** targeting the exact Render service hostname, with no `https://` or path. Verify the domain and HTTPS in Render. If using Cloudflare DNS initially keep this API record DNS-only. [Render custom domains](https://render.com/docs/custom-domains).
9. Verify API CORS from `https://trywalkthru.com`, run/report links, database RPC availability, queued-job completion, and resume across restart before inviting customers. Sleeping free instances also delay periodic jobs, watch and citation work; memory persistence and external pings are not a production durability solution.

If the free beta cannot meet these checks, select an always-on host within the founder's approved budget. The architecture mentions a later Google Cloud VM; VM account, instance, region, budget and deployment access must be confirmed before giving machine-specific commands. No paid hosting or model has been activated by this plan.

## 4. Resend application mail and Supabase sign-in

This can be configured after domain/inbox setup and before backend rollout; testing app sign-in waits for the frontend URL.

1. Open/create Resend on its free plan, review the current allowance, and add **`notify.trywalkthru.com`** as the sending domain. A sending subdomain separates its reputation from business correspondence. [Resend domains](https://resend.com/docs/dashboard/domains/introduction), [current pricing/allowances](https://resend.com/pricing).
2. Copy the exact Resend SPF/return-path MX and DKIM records to the authoritative DNS editor. For that subdomain, the return-path name may be `send.notify`; use the displayed name and avoid appending the root twice. Preserve Hostinger's **root MX** and root SPF. A return-path MX on a subdomain serves a different purpose from receiving business email at the root. Do not enable Resend inbound mail on the root for this setup.
3. Verify the sending domain in Resend. Inspect existing DMARC alignment/policy before adding a subdomain override. Keep open/click tracking disabled for authentication mail.
4. Create a sending API key limited to this domain where supported. Enter it privately in backend configuration, with:

   ```text
   RESEND_FROM=Walkthru <noreply@notify.trywalkthru.com>
   FOUNDER_EMAIL=hello@trywalkthru.com
   ```

   If the Hostinger mailbox is not active, use the founder's functioning inbox for `FOUNDER_EMAIL`. Reply delivery to `noreply@notify...` is not configured; business replies go to the published `hello@...` inbox. Adding an app-wide Reply-To would be a small subsequent code change, not an existing feature claimed here.

5. In Supabase **Authentication > Email / SMTP Settings**, enable custom SMTP:

   | Setting | Value |
   | --- | --- |
   | Sender name | `Walkthru` |
   | Sender email | `noreply@notify.trywalkthru.com` |
   | Host | `smtp.resend.com` |
   | Port | `465` |
   | Username | `resend` |
   | Password | Private Resend API key |

   The SMTP connection is made by **Supabase**, while the API sends via Resend HTTPS. These settings do not require SMTP access from Render. [Resend Supabase instructions](https://resend.com/docs/send-with-supabase-smtp).

6. Supabase's default email service is unsuitable for public sign-in: its current restrictions include team-authorized recipients and two emails/hour. Custom SMTP still has rate limits, initially 30/hour; align them with the sender quota rather than removing them. [Supabase SMTP behavior](https://supabase.com/docs/guides/auth/auth-smtp).
7. In **Authentication > URL Configuration**, set Site URL to `https://trywalkthru.com`. Add the actual redirect targets used by the app: `/app` and `/join` on that origin. Preserve deliberate localhost development entries and inspect any existing provider callback paths. Avoid a blanket production preview-domain wildcard. Test invitation sign-in because it must return to `/join`.
8. Google/GitHub providers are reported enabled by the latest local state; verify their configured clients and real callbacks rather than recreating them from old docs. For the existing Supabase project the provider callback remains `https://YOUR-PROJECT.supabase.co/auth/v1/callback`; the new frontend domain does not replace it. Update app homepage/authorized-origin settings where required by the provider.
9. Complete one real magic-link receipt/callback and both real OAuth callbacks with the founder entering credentials directly. Confirm new links no longer send users to localhost.

## 5. Rebuild and accept the extension

1. Fill the existing private `apps/extension/.env.beta` with:

   ```text
   VITE_API_URL=https://api.trywalkthru.com
   VITE_WEB_URL=https://trywalkthru.com
   VITE_SUPABASE_URL=<existing public project URL>
   VITE_SUPABASE_ANON_KEY=<existing public key>
   ```

2. From `apps/extension`, run `npm run zip:beta`. Check the generated manifest's `externally_connectable` matches exactly `https://trywalkthru.com/*` and the website's extension ID matches the distributed build. Redirect `www` to the root before connection.
3. Install/reload the matching build in Chrome, sign in on the website and select **Connect extension**. The old localhost build cannot be assumed to connect to the new domain.
4. On an owned, controlled fixture, verify the complete installed-extension journey, stop/retry behavior, private/public report access, screenshots, exports and logout/account switching. Include a deployed API restart and queued-job recovery. Do not use an unrelated production site as a scan target.
5. Expand invitations after V0-S2/S5/S6/S7 exit checks pass. Restore the previous compatible release/configuration if acceptance fails; keep the migration ledger and checkpoint schema intact. Record actual URLs, commit, artifacts and canary evidence in `CURRENT_STATE.md`.

## Current follow-along checkpoint

- [x] Founder supplied the final domain and Hostinger email screenshot.
- [x] Repository setup and current provider guidance reviewed; walkthrough prepared.
- [x] Account-specific offer confirmed: 12 months free, two mailboxes, ₹0 now, automatic annual renewal afterward at an undisclosed price.
- [ ] Trial activated and email auto-renew disabled or renewal price accepted.
- [ ] Nameservers and actual SPF/MX/DKIM/DMARC records inspected.
- [ ] Business inbox setup and two-way delivery confirmed.
- [ ] Frontend provider selected; no paid plan activated.
- [ ] Frontend deployed and custom-domain HTTPS verified.
- [ ] Durable API deployment/readiness/restart acceptance completed.
- [ ] Application mail, real sign-in callbacks and installed extension verified.

**Founder steering:** defer the email-offer discussion and choose frontend hosting after email/domain setup. Follow one screen at a time.

**Next:** discuss and select the production architecture before further hosting/account/DNS changes. Screenshots now show `hello@trywalkthru.com` exists; mailbox delivery and SPF/DKIM repair remain unconfirmed. Render is excluded. Email subscription auto-renew cancellation remains unverified.
