# Walkthru live deployment: trywalkthru.com

Prepared **1 November 2026**, from this checkout and the earlier VM/billing screenshots. This is a follow-along guide, not confirmation that anything has been deployed or that financial protections are installed. Domain confirmed by the founder: **trywalkthru.com**.

## Read this first: protecting your money

**Your earlier console showed a Paid account with remaining trial credits. Do not assume Google will automatically stop everything when those credits expire.** Upgrading preserves eligible remaining credit only until its original expiry; uncovered usage and usage after credit exhaustion can be billed. [Google trial and upgrade terms](https://docs.cloud.google.com/free/docs/free-cloud-features).

The historical credit screenshot showed **₹28,796.63 available until 3 January 2027**. That is not a live balance check. Starting the VM again does not start another three-month trial. Check the current account, credit eligibility, balance and expiry before starting resources.

There is **no honest zero-charge guarantee for a running paid Google Cloud account** based on budget emails or canceling UPI AutoPay. For your situation, use the safeguards in section 3 before starting the VM, and retire the project while credits remain. If any possibility of an uncovered bill is unacceptable, keep the VM stopped and billing disabled instead of resuming this paid account.

## 1. What we are deploying

| Part | Service | Public address |
| --- | --- | --- |
| Frontend, including animations | Cloudflare Pages, static Vite build | `https://trywalkthru.com` |
| API and background worker | Existing Google Cloud Compute Engine VM | `https://api.trywalkthru.com` |
| Database, sign-in, evidence storage, realtime | Existing Supabase project | Its existing Supabase URL |
| Browser agent | Production-configured Chrome extension | Runs in the user's browser |
| Business inbox | Existing Hostinger Email | `hello@trywalkthru.com` |
| Registration | Hostinger | Keep ownership and domain renewal here |
| Authoritative DNS | Cloudflare Free zone | Records for web, API and Hostinger email |
| Founder admin | Your own computer only | Never expose port 8020 or deploy the admin service |

Cloudflare serves the frontend files; React and GSAP execute in the visitor's browser. Moving these files to Pages does not remove animations. Browser/device performance and asset sizes still matter. We are not porting the Python backend to Cloudflare Workers.

Pages is the selected simple route for this existing static application. Cloudflare now recommends Workers for new projects in its framework documentation, but Pages remains documented and supports this deployment. Choose the **Pages Git integration**, not a Workers template or Python Worker. [Cloudflare framework guidance](https://developers.cloudflare.com/pages/framework-guides/).

### Earlier VM decision, recovered from our discussion

| Item | Historical successful configuration |
| --- | --- |
| Project | `walkthru-509719` |
| VM | `walkthru-api` |
| Region / zone | Sydney: `australia-southeast1` / `australia-southeast1-a` |
| Machine | `e2-small`, 2 GB RAM, shared CPU |
| OS | Ubuntu 24.04 LTS Minimal, x86-64 |
| Disk | 20 GB balanced persistent disk |
| Last visible IP | `34.40.189.170`, historical only; verify again |
| Old console estimate | US$20.05/month, not a current or complete total |

The earlier Singapore attempt and Ubuntu 26.04 selection were not the final successful VM. **Inspect and reuse the existing Sydney VM first.** Creating another VM can duplicate compute, disk and address costs.

An `e2-small` is a pilot starting point, not a measured production minimum or high-availability setup. It supplies shared CPU rather than two dedicated cores. The VM does not need a GPU, local Postgres, Redis or Chromium for this architecture. Check current Supabase region before deciding to move regions; the API-to-database connection matters for latency. [E2 specifications](https://docs.cloud.google.com/compute/docs/general-purpose-machines#e2_shared-core).

### Where to run commands

- **Your Windows PowerShell:** repository checks, frontend and extension builds.
- **Google Cloud Shell:** `gcloud` resource/billing commands below. Backslash line continuation is Bash syntax, not PowerShell syntax.
- **VM SSH terminal:** Ubuntu installation, files under `/etc`, systemd and Nginx commands.
- Replace `YOUR_...` placeholders before running. Never paste passwords, tokens, `.env` files or UPI details into chat.

## 2. Inspect the existing account and stopped VM

In Google Cloud Console, select **Walkthru / walkthru-509719**.

1. Open Billing and confirm which account is linked to this project.
2. Read account status: Free Trial or Paid. Our earlier evidence says Paid.
3. Open **Credits**, expand the available credit and record current remaining amount, end date and eligible usage. The expired historical row is not an additional balance.
4. Open Reports and Transactions. Check both gross usage and credits, plus any actual amount due. A ₹0 display can lag new usage.
5. Inspect all projects linked to that billing account. Other projects can consume the same credit pool.
6. Do not buy AI Studio credits or activate Vertex/paid models for this deployment. AI Studio prepay is a different purchase from VM hosting.

In **Cloud Shell**, these inspection commands do not start or create a VM:

```bash
gcloud config set project walkthru-509719
gcloud billing projects describe walkthru-509719
gcloud compute instances list --project=walkthru-509719
gcloud compute instances describe walkthru-api --project=walkthru-509719 --zone=australia-southeast1-a --format='yaml(name,status,machineType,zone,scheduling,networkInterfaces,disks,serviceAccounts)'
gcloud compute disks list --project=walkthru-509719
gcloud compute addresses list --project=walkthru-509719
gcloud compute snapshots list --project=walkthru-509719
gcloud compute resource-policies list --project=walkthru-509719
```

If the instance is absent or the zone differs, use the inventory result rather than repeatedly retrying the old name/zone. `TERMINATED` means stopped, not deleted. Review orphan disks, addresses and snapshots from failed creation attempts before adding resources. Do not delete anything until its ownership and backup value are understood.

**Checkpoint:** know today's credit balance/expiry, billing status, existing resources and actual VM zone before continuing.

## 3. Install financial safeguards before starting

### 3.1 Set an absolute automatic VM stop date

Use an absolute date comfortably before the confirmed credit expiry, not a new 90-day duration. For the historical **3 January 2027** expiry, **31 December 2026 at 00:00 UTC** is a conservative example. If today's console shows a different expiry, choose a different date at least 48 to 72 hours earlier.

Google supports a native VM termination timestamp with the action STOP. Set it while the existing VM is stopped; the allowed future window is 30 seconds to 120 days. This is a date guard, **not a remaining-credit detector**. [VM runtime limits](https://docs.cloud.google.com/compute/docs/instances/limit-vm-runtime).

Cloud Shell, only after confirming the example date fits your actual credit:

```bash
gcloud compute instances set-scheduling walkthru-api \
  --project=walkthru-509719 \
  --zone=australia-southeast1-a \
  --termination-time=2026-12-31T00:00:00Z \
  --instance-termination-action=STOP

gcloud compute instances describe walkthru-api \
  --project=walkthru-509719 \
  --zone=australia-southeast1-a \
  --format='yaml(status,scheduling)'
```

Verify the saved `terminationTime` and `instanceTerminationAction: STOP`. If this fails, resolve it before starting; a rejected command has installed no protection. The corresponding UI is VM Edit > availability/scheduling advanced settings > time limit > date > Stop. [Command reference](https://docs.cloud.google.com/sdk/gcloud/reference/compute/instances/set-scheduling).

An absolute timestamp persists across ordinary stop/start operations; a duration resets when started. A passed absolute deadline must be reviewed before restarting. Allow for termination delay, and do not schedule the cutoff at the last second of credit validity.

### 3.2 Create conservative budget alerts

Billing > **Budgets & alerts / Budgets & caps** > Create budget:

1. Scope an operational budget to `walkthru-509719`, all its services.
2. Use a custom date range covering the remaining credit period if available, otherwise a monthly budget that you review at each month boundary.
3. Track gross consumption by excluding credits from budget calculations; otherwise credits can mask consumption as zero. Review the displayed cost-treatment settings rather than accepting defaults blindly.
4. Choose an amount well below remaining usable credit, allowing for other projects and a large reserve. Do not enter the full original ₹28,796.63 merely because it appeared in an old screenshot.
5. Send actual-spend alerts at 50%, 80%, 90%, 100%, and a forecast alert if offered, to an inbox you check daily.
6. Make a separate billing-account-wide alert if other projects share that account.

These are alerts, not a Compute Engine shutdown. Costs and notifications can arrive late. [Budget setup and cost treatment](https://docs.cloud.google.com/billing/docs/how-to/budgets).

Google also offers **spend-cap budgets for eligible services**, but its current documentation excludes ongoing fixed usage of persistent compute/storage resources from being paused. Do not mistake a Gemini/Cloud Run spend cap for protection that stops this VM and disk. [Spend-cap scope and limitations](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps).

### 3.3 Optional automatic response to rising spend

For a balance-related second guard, Google documents **budget notification > Pub/Sub > Cloud Run function > disable billing on the project**. This is stronger than only stopping the instance, but it can disrupt services or lose data, uses extra managed services, and is delayed. It is not installed by writing this guide and is not a guaranteed hard rupee cap. [Official automatic billing-disable walkthrough](https://docs.cloud.google.com/billing/docs/how-to/disable-billing-with-notifications).

If we add it during the follow-along session:

1. Use the project's all-services budget and a trigger threshold far below the remaining usable credit, not exactly at exhaustion.
2. Create the notification topic and the function using the current official walkthrough and its supported runtime.
3. Pin its target to **only `walkthru-509719`**. Use a dedicated identity with only the required billing-assignment removal permission on this project, not the VM's service account with account-wide administration.
4. Validate the budget identity, amount/currency and actual-cost threshold before unlinking. Ignore unrelated budgets and forecast-only messages. Handle repeated deliveries safely.
5. Test event handling in a non-destructive dry-run path, then explicitly exercise real unlinking during a backed-up maintenance window. A log saying "would stop" is not an installed cutoff.
6. Confirm billing becomes disabled and relevant resources stop; record how to recover deliberately. Review the function's own charges and protection if it shares this project.

Use this only as a redundant safeguard. Do not depend on a newly written, untested script to protect your bank account.

### 3.4 The actual exit plan

**Before the chosen cutoff, while credits remain:** back up necessary data/configuration, stop public work, retire billable resources and disable billing on this project. Review every other linked project too. Detailed commands are in section 13.

Stopping the VM alone can leave disk, address and snapshot charges. Canceling a ₹15,000 UPI mandate does not stop cloud resources or cancel already incurred charges; the mandate amount is not a cloud spending limit. Review the bank's mandate details separately. Do not re-authorize payment just because the console prompts you without first understanding the paid account exposure.

**Checkpoint:** saved absolute stop timestamp, working alerts, a clear retirement date, and acceptance that remaining-credit automation has reporting delays. If zero exposure is essential, do not start a paid-account deployment.

## 4. Prepare the exact release on your computer

Current local HEAD at guide preparation: `2725be4`. There are **uncommitted F1-F6/application and audit changes**. Deploying that old GitHub commit will not include those local fixes. This guide has not fetched or certified today's remote `main`, committed, or pushed anything.

From the repository root in PowerShell:

```powershell
git status --short
git fetch origin
git branch --show-current
git log -1 --oneline
git rev-list --left-right --count HEAD...origin/main
git diff --stat
```

Review and publish the intended changes in clean commits before deployment. Do not force-push, reset away work, add `.env`, or blindly stage every file. Record the full release SHA after the reviewed push and confirm it exists on origin. Pin the backend and extension to that release; verify the Cloudflare deployment's commit as well.

Run the checks appropriate to the final published release:

```powershell
# From repository root, run each directory's block separately.
cd apps/web
npm ci
npm run build
npm run lint
npm test
```

```powershell
# From repository root
cd apps/extension
npm ci
npm run build
npm test
npx tsc --noEmit
npm run lint
```

```powershell
# From repository root; existing API virtual environment
cd apps/api
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
```

Use supported Node 22.12+ or a tested Node 24 release for the web/extension builds. Do not use an old Node 18 default. [Vite requirements](https://vite.dev/guide/).

The [live audit](LIVE_BETA_AUDIT_2026-10-31.md) still records incomplete difficult journeys, the optional-suite validation defect, Instant Scan account/history loss, missing keyword/authority output, citation identity mistakes, PDF limitations and unverified cross-account integrations. Publishing infrastructure does not fix those. Start with a small, explicitly informed pilot; this guide does not overturn the audit's public-beta warning. Dodo and paid LLM activation remain outside this deployment.

## 5. Move DNS safely without breaking Hostinger email

For the Pages apex domain, make Cloudflare authoritative DNS while Hostinger remains the registrar and mail provider. [Pages custom-domain requirements](https://developers.cloudflare.com/pages/configuration/custom-domains/).

1. In Hostinger, export the DNS zone if offered; otherwise record every full record, priority and TTL. Capture nameservers and current DNSSEC state too.
2. Add `trywalkthru.com` to Cloudflare using the **Free** zone plan.
3. Compare Cloudflare's imported records against Hostinger. Automatic scanning can miss records. Preserve verification tokens, MX, SPF, DKIM, DMARC, mail/autodiscover records, CAA and any existing application records that are still needed.
4. If DNSSEC is enabled with Hostinger's old DNS, remove/disable that old DNSSEC delegation before switching nameservers. After Cloudflare becomes active, enable Cloudflare DNSSEC and publish its new DS values at Hostinger as instructed. Leaving an old DS can make the domain fail to resolve. [Cloudflare nameserver procedure](https://developers.cloudflare.com/dns/zone-setups/full-setup/setup/).
5. At Hostinger Domains > `trywalkthru.com` > nameservers, enter **the two nameservers Cloudflare assigned to this zone**. Do not copy someone else's nameservers.
6. Wait until Cloudflare marks the zone Active. Check public DNS rather than changing records repeatedly while propagation is pending.
7. After the change, manage DNS in Cloudflare, not Hostinger's now-inactive DNS editor.

Email records to preserve exactly, with values from your account:

| Record | Treatment |
| --- | --- |
| Hostinger MX and priorities | Copy unchanged |
| Root SPF TXT | Preserve one SPF policy; merge authorized senders if needed, never create a second SPF policy |
| Hostinger and any existing sender's DKIM selectors | Copy full names and targets; CNAMEs must be DNS only |
| `_dmarc` TXT | Preserve the actual policy |
| Mail/autodiscover CNAME or A records | Preserve and leave DNS only |
| Provider verification TXT | Preserve |

The earlier email screenshot showed incomplete SPF/DKIM verification. A nameserver change does not fix that by itself. Recheck Hostinger's exact requested records after migration; never guess the truncated screenshot values. Do an inbox send-and-reply check yourself, including SPF/DKIM/DMARC results in message headers. No bulk email is needed.

Cloudflare zone exports provide a recovery copy after migration. [DNS import/export](https://developers.cloudflare.com/dns/manage-dns-records/how-to/import-and-export/).

## 6. Resume the VM, or create one only if absent

### Existing VM: preferred route

After section 3 passes, start the existing stopped VM in Console or Cloud Shell:

```bash
gcloud compute instances start walkthru-api --project=walkthru-509719 --zone=australia-southeast1-a
```

Connect with SSH. Inspect any prior install before replacing it:

```bash
sudo systemctl status walkthru-api walkthru-worker nginx --no-pager
sudo ls -ld /opt/walkthru/repo /etc/walkthru
```

Missing services/directories are normal if we previously only created a VM. Existing services/configuration must be backed up and updated deliberately; do not re-create the user, overwrite secrets or re-clone into the same directory blindly.

### If no VM exists

Console > Compute Engine > VM instances > Create instance:

| Setting | Choose |
| --- | --- |
| Name | `walkthru-api` |
| Region | Sydney if Supabase remains Sydney; verify first |
| Zone | `australia-southeast1-a` if available; record any replacement |
| Machine | E2 > `e2-small` |
| Provisioning | Standard, not Spot |
| OS | Ubuntu 24.04 LTS x86-64, ordinary image, not Ubuntu Pro |
| Disk | 20 GB balanced persistent disk |
| Network | Default VPC if present; IPv4; allow HTTP/HTTPS |
| Service account | None required for the existing key-based Supabase/free-provider route |
| Extras | No GPU, extra disks, load balancer, paid marketplace image or commitment |
| Runtime limit | Absolute date and STOP action from section 3 |
| Deletion protection | Enabled, with retirement procedure documented |

Review the **current console quote** before Create. That estimate may omit IPv4, egress, snapshots and variable logs. Don't add snapshots/Ops Agent merely because they are preselected; decide what we need and price it. Keep OS security updates enabled. [Compute pricing](https://cloud.google.com/products/compute/pricing/general-purpose), [network/IP pricing](https://cloud.google.com/vpc/network-pricing).

An upgrade to `e2-medium` is a later response to measured RAM/CPU/queue pressure, not a prerequisite. A single small VM remains a single point of failure.

### Stable IP and network access

VPC network > IP addresses > find the VM's **current** external IPv4 > reserve/promote it as `walkthru-api-ip`. Do not assume the historical IP survived stopping. Static addresses are billable and must be released when no longer needed. [Reserve an address](https://docs.cloud.google.com/vpc/docs/reserve-static-external-ip-address).

Allow public TCP 80/443 to the VM's HTTP/HTTPS tags. Do not expose 8010, 8020 or 5432. Restrict SSH to an authorized path; preferred IAP permits TCP22 from `35.235.240.0/20` with the required IAP/Compute permissions. Test IAP before removing broader SSH access so you do not lock yourself out. [IAP requirements](https://docs.cloud.google.com/iap/docs/using-tcp-forwarding).

Add this Cloudflare DNS record:

| Type | Name | Target | Proxy |
| --- | --- | --- | --- |
| A | `api` | Verified reserved VM IPv4 | **DNS only**, gray cloud |

Keep the API DNS only initially: long model/report requests and MCP streaming should not depend on Cloudflare proxy timeouts. This also avoids treating all proxied users as a shared client IP without a separately verified real-IP configuration. Nginx will still provide HTTPS.

## 7. Install the backend release

Run these commands inside VM SSH. For an existing installation, skip user/directory/clone creation and use the controlled update procedure in section 12 instead.

```bash
sudo apt-get update
sudo apt-get install -y python3-venv git nginx certbot python3-certbot-nginx
python3 --version

sudo adduser --system --group --home /opt/walkthru --no-create-home walkthru
sudo install -d -o walkthru -g walkthru /opt/walkthru
sudo -u walkthru git clone https://github.com/watermelon588/Walkthru.git /opt/walkthru/repo
cd /opt/walkthru/repo
sudo -u walkthru git checkout --detach YOUR_VERIFIED_RELEASE_SHA
sudo -u walkthru git rev-parse HEAD

cd /opt/walkthru/repo/apps/api
sudo -u walkthru python3 -m venv .venv
sudo -u walkthru .venv/bin/python -m pip install -r requirements.lock
sudo -u walkthru .venv/bin/python -m pip install -e . --no-deps
```

Ubuntu 24.04 uses Python 3.12, matching this lockfile's target. If the repository is private, provision a read-only repository deploy key for the `walkthru` service user first. Never put a GitHub personal token in a clone URL, shell history or shared guide.

Do not run `dev.py`, fixture servers, the founder admin setup, or `python -m admin` on this server. Installing the repository does not mean starting every module in it.

### Production secrets

```bash
sudo install -d -m 0750 -o root -g walkthru /etc/walkthru
if ! sudo test -f /etc/walkthru/api.env; then
  sudo install -m 0640 -o root -g walkthru /dev/null /etc/walkthru/api.env
fi
sudo nano /etc/walkthru/api.env
```

Fill locally on the VM, replacing placeholders. Do not overwrite an existing file without a secure backup.

```dotenv
APP_ENV=production
WEB_URL=https://trywalkthru.com
CHECKPOINTER=postgres
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLIC_PUBLISHABLE_KEY
SUPABASE_SECRET_KEY=YOUR_SERVER_ONLY_SECRET_KEY
DATABASE_URL='YOUR_SESSION_POOLER_CONNECTION_STRING_WITH_SSLMODE_REQUIRE'
CHECKPOINT_DATABASE_URL='YOUR_SESSION_POOLER_CONNECTION_STRING_WITH_SSLMODE_REQUIRE'
GROQ_API_KEY=YOUR_EXISTING_APPROVED_FREE_KEY
GOOGLE_API_KEY=YOUR_EXISTING_APPROVED_FREE_KEY
OPENROUTER_API_KEY=YOUR_EXISTING_APPROVED_FREE_KEY_IF_USED
LANGSMITH_TRACING=false
LANGCHAIN_TRACING_V2=false
PROVIDER_USAGE=off
RESERVATIONS=off
CONTROLLER_CANDIDATE=
CLAUDE_VERTEX_PROJECT=
ANTHROPIC_API_KEY=
DODO_PAYMENTS_API_KEY=
WARMUP=0
```

Remove optional key lines if unused; never leave placeholder strings as real credentials. Keep existing approved **free** provider/model choices. Do not assume a key with billing enabled remains free merely because the environment variable has the same name. Review quotas and free model availability in each provider dashboard. Billing/Vertex/paid model activation is a separate decision.

Use Supabase **Connect > session pooler, port 5432**, with `sslmode=require`, not transaction pooler 6543, for this checkpoint path. URL-encode special characters in the password. Keep the private `walkthru_checkpoints` schema out of exposed API schemas. [Supabase connection modes](https://supabase.com/docs/guides/database/connecting-to-postgres), [repository checkpoint contract](docs/checkpoints-and-request-logs.md).

Keep `JOB_WORKERS` and `RETENTION_JOB` **out of this shared env file**; otherwise EnvironmentFile overrides the separate values in the service units below. Do not copy the entire development `.env`: leave out local-scan overrides, test accounts, founder-admin secrets and localhost URLs.

Hostinger's business inbox does not automatically configure application emails. Supabase Auth delivery, optional report delivery and business inbox mail are separate integrations. If their mail provider is not configured, mark delivery unavailable rather than claiming email works.

### Database migration checkpoint

```bash
cd /opt/walkthru/repo/apps/api
sudo -u walkthru .venv/bin/python -c "from dotenv import load_dotenv; load_dotenv('/etc/walkthru/api.env'); from app.migrate import main; main(['status'])"
```

The status command can create its migration ledger if absent. Baseline migrations **0001 through 0003** are required; 0004 onward in this checkout are proposed optional usage/reservation/admission storage. **Do not run bare `python -m app.migrate`: it applies all pending migrations.** Keep optional flags off.

If the baseline is already applied and checksums match, proceed. If pending, back up the correct Supabase project and use a maintenance window. Only then apply the baseline with the checksum-aware runner:

```bash
sudo -u walkthru .venv/bin/python - <<'PY'
from dotenv import load_dotenv
load_dotenv('/etc/walkthru/api.env')
from pathlib import Path
from tempfile import TemporaryDirectory
from shutil import copy2
from app import migrate
with TemporaryDirectory(prefix='walkthru-baseline-') as folder:
    for name in ('0001_initial.sql', '0002_agent_checkpoints.sql', '0003_run_idempotency.sql'):
        copy2(migrate.DIRECTORY / name, Path(folder) / name)
    with migrate.connect() as conn:
        migrate.up(conn, Path(folder))
PY
```

Checksum/schema conflicts require investigation. Never edit applied SQL or bypass checks to make startup green. Supabase RLS, storage policies and private evidence delivery must retain their existing configuration.

## 8. Keep API and worker running with systemd

Create `/etc/systemd/system/walkthru-api.service` using `sudo nano`:

```ini
[Unit]
Description=Walkthru API
Wants=network-online.target
After=network-online.target

[Service]
User=walkthru
Group=walkthru
WorkingDirectory=/opt/walkthru/repo/apps/api
EnvironmentFile=/etc/walkthru/api.env
Environment=JOB_WORKERS=0
Environment=RETENTION_JOB=1
ExecStart=/opt/walkthru/repo/apps/api/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --workers 1 --proxy-headers --forwarded-allow-ips=127.0.0.1
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/walkthru-worker.service`:

```ini
[Unit]
Description=Walkthru job worker
Wants=network-online.target
After=network-online.target

[Service]
User=walkthru
Group=walkthru
WorkingDirectory=/opt/walkthru/repo/apps/api
EnvironmentFile=/etc/walkthru/api.env
Environment=JOB_WORKERS=1
Environment=RETENTION_JOB=0
ExecStart=/opt/walkthru/repo/apps/api/.venv/bin/python -m app.jobs
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now walkthru-worker walkthru-api
sudo systemctl status walkthru-api walkthru-worker --no-pager
curl --fail http://127.0.0.1:8010/health
curl --fail http://127.0.0.1:8010/ready
sudo journalctl -u walkthru-api -u walkthru-worker -n 80 --no-pager
```

Keep one API process and one worker initially. The API's `RETENTION_JOB=1` also enables its separate citation scheduler; the worker handles general queued jobs. Simply starting Uvicorn without the worker leaves important work unprocessed. Worker count alone does not limit every scan/crawl path.

`/health` is liveness; `/ready` checks bounded database/job reads in the locally fixed release. Neither proves checkpoint writes, provider calls, tenant isolation or successful job processing. If `/ready` is absent, verify that you deployed the intended fixes rather than the old SHA.

## 9. Put HTTPS in front of the API

Ensure `api.trywalkthru.com` resolves to the reserved VM address. Create `/etc/nginx/sites-available/walkthru-api`:

```nginx
server {
    listen 80;
    server_name api.trywalkthru.com;
    client_max_body_size 1m;

    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 180s;
        proxy_send_timeout 180s;
        proxy_buffering off;
    }
}
```

```bash
sudo ln -sfn /etc/nginx/sites-available/walkthru-api /etc/nginx/sites-enabled/walkthru-api
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d api.trywalkthru.com --redirect
sudo certbot renew --dry-run
curl --fail https://api.trywalkthru.com/health
curl --fail https://api.trywalkthru.com/ready
```

Certbot needs public DNS and port 80 reachable for this route. Follow its prompts for your email and terms. Do not disable TLS verification to work around a certificate error. Check renewal timer status after issuance. [Certbot Nginx instructions](https://certbot.eff.org/instructions?ws=nginx&os=pip).

The API record remains DNS only; its encryption comes from Nginx's certificate. If later proxying any origin through Cloudflare, use Full (strict), never Flexible for this HTTPS setup. Do not add a Cache Everything rule to API/auth/report routes.

## 10. Deploy the frontend to Cloudflare Pages

### Carry security headers over from Vercel

`apps/web/vercel.json` is not Cloudflare configuration. Before publishing the release, create **`apps/web/public/_headers`** with the equivalent current headers below. This guide provides the content; it has not created that application file.

```text
/*
  Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https:; font-src 'self' data:; connect-src 'self' https: wss:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
```

This preserves the existing CSP rather than silently weakening it during migration. Its existing broad HTTPS/WSS connection policy can be tightened after inventorying all actual integrations. Vite copies public files into `dist`; verify `_headers` exists there after build. [Pages header syntax](https://developers.cloudflare.com/pages/configuration/headers/).

Pages supplies SPA fallback when there is no top-level `404.html`, so `/app/team` and report deep links should load directly. Do not add a conflicting 404 page or assume Vercel's rewrites are read. Check deep links after deployment. [Pages routing behavior](https://developers.cloudflare.com/pages/configuration/serving-pages/).

### Create the Pages project

Cloudflare Dashboard > **Workers & Pages > Create application > Pages > Connect to Git**. Labels may vary; choose the Pages Git-connected project, not Workers deployment.

Authorize only the intended GitHub repository. Configure:

| Field | Value |
| --- | --- |
| Repository | `watermelon588/Walkthru` |
| Production branch | The reviewed release branch, normally `main` |
| Project name | `walkthru-web`, or another available name |
| Root directory | `apps/web` |
| Framework preset | Vite / React, or None with the explicit settings below |
| Build command | `npm ci && npm run build` |
| Output directory | `dist`, relative to `apps/web` |
| Build Node version | `NODE_VERSION=22` with resolved version >=22.12; verify build log |

Cloudflare can perform dependency installation automatically before the build; the explicit `npm ci` ensures the app lockfile is honored. Do not change the root to the repository root without adjusting both command and output path. [Pages build configuration](https://developers.cloudflare.com/pages/configuration/build-configuration/), [build image/version controls](https://developers.cloudflare.com/pages/configuration/build-image/).

Set these **production build variables**:

```dotenv
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_SUPABASE_ANON_KEY=YOUR_PUBLIC_ANON_OR_COMPATIBLE_PUBLISHABLE_KEY
VITE_API_URL=https://api.trywalkthru.com
VITE_EXTENSION_ID=cilngbcfpoojecjoiklimnjnomjglcdo
```

All `VITE_` values become public browser code. Never put Supabase secret/service-role keys, database URLs, model keys, admin credentials or SMTP passwords here. The code's frontend variable name remains `VITE_SUPABASE_ANON_KEY` even when using a compatible newer publishable key.

Check build success, recorded Git SHA, Node version and browser rendering at the assigned Pages URL. Its signed-in API flow is not expected to work automatically: production API CORS is configured for `https://trywalkthru.com`, not every preview domain. Do not broaden CORS to `*` to fix a preview.

### Attach the purchased domain

1. Pages project > **Custom domains > Set up a custom domain** > `trywalkthru.com`.
2. Let Pages create the required apex record in the active Cloudflare zone. Resolve any old apex parking A/AAAA/CNAME conflict deliberately; never delete email TXT/MX records.
3. Wait for certificate/domain status Active. Do not invent an apex A record pointing at Google: the frontend lives on Pages, not on the VM.
4. Add `www.trywalkthru.com` as a supported domain if desired, then create a Cloudflare Redirect Rule from `www` to `https://trywalkthru.com`, preserving path/query. Use the apex as the one canonical app origin.
5. Verify the apex and `www` behavior, HTTPS, `/login`, `/app`, `/app/team`, and a report deep link on a fresh navigation.

Attach the domain through the Pages project before manually adding a CNAME. Merely creating DNS without the Pages association can fail. [Pages custom domains](https://developers.cloudflare.com/pages/configuration/custom-domains/).

After changing build variables, redeploy: they are baked into the frontend, not read dynamically from the VM.

## 11. Configure Supabase sign-in and the live extension

### Supabase Auth

In the existing Supabase project:

1. Auth > URL configuration > Site URL: `https://trywalkthru.com`.
2. Add the exact allowed redirect `https://trywalkthru.com/app`. Current `Login.tsx` uses `${location.origin}/app` for magic links and OAuth.
3. Keep required development redirects only if still used; do not introduce unrestricted wildcard domains.
4. In Google OAuth settings, use the callback URL Supabase actually displays, ordinarily its `/auth/v1/callback` endpoint. Do not replace it with the VM address. Update authorized origins only where the provider flow requires them.
5. Verify a new magic-link/OAuth sign-in returns to the live apex with the correct account and plan. Use an actual second account for cross-account access checks.

[Supabase redirect configuration](https://supabase.com/docs/guides/auth/redirect-urls).

The API must use the same Supabase project as the frontend. Keep RLS and evidence storage policies intact. Business inbox mail at Hostinger does not automatically change Supabase Auth SMTP settings. Supabase default mail restrictions can prevent arbitrary pilot users signing in; verify the actual project's delivery settings and test recipient eligibility. [Supabase custom SMTP](https://supabase.com/docs/guides/auth/auth-smtp).

### Build the extension for the actual production origin

An extension compiled for localhost will not automatically switch to the live API. In `apps/extension/.env.production.local`, add only these public values:

```dotenv
VITE_API_URL=https://api.trywalkthru.com
VITE_WEB_URL=https://trywalkthru.com
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_SUPABASE_ANON_KEY=YOUR_PUBLIC_ANON_OR_COMPATIBLE_PUBLISHABLE_KEY
```

Confirm that this local environment file is ignored by Git before filling it. From `apps/extension`, PowerShell:

```powershell
npm ci
npm run build
```

Check `.output/chrome-mv3/manifest.json`: `externally_connectable.matches` must contain `https://trywalkthru.com/*`, not localhost. Check compiled output is using the live API; do not include server secrets.

For a small unpacked pilot, Chrome > Extensions > Developer mode > Load unpacked > this build output, or reload the existing extension. The current public manifest key fixes its ID to **`cilngbcfpoojecjoiklimnjnomjglcdo`**; that must match the web variable. Replacing this build also changes its environment, so preserve your existing local development build separately if you still need it.

For general public distribution, prepare a Chrome Web Store release: review permissions/privacy/disclosures, remove the development fixed key as instructed in `wxt.config.ts`, use the actual assigned store ID, update the web variable and redeploy. An unpacked build is not a store release or an automatic update channel.

In the live dashboard: sign in > Connect extension > open an owned test site > open the side panel. Verify account handoff and the live API origin before starting a run.

## 12. Acceptance, operation, updates and rollback

### Live deployment checks

These are real environment acceptance checks, not a claim that earlier feature audit defects vanished:

| Check | What must happen |
| --- | --- |
| Backend readiness | Public HTTPS `/health` and `/ready` succeed; logs show persistent checkpointer initialized |
| Worker | A real queued report completes; no repeated crash/retry loop |
| Auth and plan | New live login lands at `/app`; actual account/plan appears |
| Extension | Live domain handoff succeeds; side panel talks to live API |
| Genuine journey | On an owned, verified site, run an authorized task; history retains it and outcome/stop reason match actual behavior |
| Evidence | Signed/private screenshots load for owner and do not become public through caching |
| Reports | Sections, exports, share controls and citations reflect actual evidence; audit gaps stay explicit |
| Instant Scan | Confirm signed-in ownership/history; the known audit bug must be fixed or disclosed |
| Teams | A second consenting account tests permitted and denied access; do not substitute owner-only clicks |
| MCP | Approved temporary key works in a real client, then is revoked and rejected; do not create a key without approval |
| Persistence | Controlled API restart retains a pending workflow; worker resumes queued work without duplicate charging |
| Email | Auth delivery and any enabled report delivery actually arrive; Hostinger inbox send/reply succeeds |
| Cost controls | Absolute STOP timestamp still saved; alerts scoped correctly; credit report reviewed |

Do not submit payment forms, bypass CAPTCHAs, write destructive target data, run active security probes or test a domain without ownership verification. Dodo and paid model calls are excluded. If a known defect prevents acceptance, record the limitation and narrow the pilot rather than calling it passed.

### Daily checks during the pilot

```bash
sudo systemctl status walkthru-api walkthru-worker nginx --no-pager
sudo journalctl -u walkthru-api -u walkthru-worker --since '1 hour ago' --no-pager
free -h
df -h
curl --fail https://api.trywalkthru.com/ready
```

Check gross costs, remaining credits, error frequency, queue completion time, memory and disk use. Avoid verbose request-body logging or new paid tracing. Bound journal storage, for example with a reviewed journald drop-in `SystemMaxUse=200M`; rotate Nginx logs with Ubuntu's packaged logrotate policy. Do not fill a 20 GB disk with debug output.

Provider free quotas can fail before Google credits run out. Handle that as an unavailable model/integration, never an automatic paid fallback. Paid plan pricing and payment integration do not need to be activated to host an explicitly limited pilot.

### Deploying an update

1. Review/publish a release and record the old/new full SHAs. Run checks first.
2. Pause new journeys and wait for current writes/jobs to settle, or use a maintenance window. Do not kill active work casually.
3. On the VM, `git fetch origin` as `walkthru`, stop the API/worker, checkout the reviewed SHA, install its locked Python requirements and editable package. Do not run all migrations as part of a generic update script.
4. Restart worker/API, check logs, readiness and a real job. Keep the absolute VM stop date unchanged.
5. Deploy the matching frontend commit and rebuild/distribute the matching extension when its contract changes. Existing tabs/extensions may still contain older builds.

Rollback uses the recorded previous SHA and its compatible locked environment, plus Pages' previous successful deployment. Rebuild the extension from that release when needed. Back up before schema changes; code rollback is not a database rollback. Never run migration `down` blindly or restore a database in a way that discards newer user work.

## 13. Emergency stop and final retirement

### A. Stop compute quickly

Cloud Shell:

```bash
gcloud compute instances stop walkthru-api --project=walkthru-509719 --zone=australia-southeast1-a
gcloud compute instances describe walkthru-api --project=walkthru-509719 --zone=australia-southeast1-a --format='value(status)'
```

Wait for `TERMINATED`. This interrupts the backend. It does **not** prove all charges have stopped: disks, static IPs, snapshots and other resources need review. [VM stop behavior](https://docs.cloud.google.com/compute/docs/instances/stop-start-instance).

### B. Disable this project's billing to end the paid deployment

Use this intentionally after securing required backups. It disrupts project services and can lead to resource/data loss. It affects the Google project, not the separate Hostinger/Cloudflare/Supabase accounts. It cannot erase charges already incurred.

Console: Billing > Account management / My projects > locate **`walkthru-509719`** > menu > **Disable billing**. If billing assignment is locked, resolve the lock/required permissions through the console first.

Equivalent Cloud Shell action, **do not run during normal setup**:

```bash
gcloud billing projects unlink walkthru-509719
gcloud billing projects describe walkthru-509719
```

Verify billing is disabled and no billing account remains linked. Check all other linked projects separately. [Disable billing procedure](https://docs.cloud.google.com/billing/docs/how-to/modify-project), [unlink command](https://docs.cloud.google.com/sdk/gcloud/reference/billing/projects/unlink).

### C. Retire remaining resources and payment exposure

1. Export the release SHA, essential configuration securely, required logs and any Google-hosted data before deletion. A snapshot retained in Google can itself remain billable.
2. Delete only verified disposable VM/disks/snapshots/addresses/policies after backup. Deletion protection must be explicitly disabled to delete the VM. Stopping a VM does not release a reserved address.
3. Confirm resource inventory and every linked project's billing state; closing the billing account is an additional option if you will not use it for anything else, with account-wide consequences.
4. Review final usage/transactions after reporting catches up. Resolve any existing amount due; canceling AutoPay does not waive it.
5. Review/cancel the UPI mandate in your payment app only as a separate payment instruction. Do not treat mandate cancellation as cloud retirement.
6. Put the frontend into a clear maintenance/unavailable state, or point it to the replacement backend after configuration and acceptance. Avoid leaving users starting runs against a stopped API.

### Dates to record now

| Item | Fill from live account |
| --- | --- |
| Verified eligible remaining credit | __________ |
| Verified expiry date/time | __________ |
| Saved native VM stop timestamp | __________ |
| Planned backup + billing-disable date, before expiry | __________ |
| Gross-consumption budget threshold and reserve | __________ |
| Other projects consuming this billing account | __________ |
| Published release SHA / prior rollback SHA | __________ |

## 14. Follow-along order for our deployment session

1. Confirm today's credits/billing status and inspect the stopped VM.
2. Save and verify the automatic STOP date; configure conservative alerts and agree the retirement boundary.
3. Publish the reviewed release, including the required Pages header file; record its SHA.
4. Back up DNS, migrate the zone to Cloudflare, preserve and verify Hostinger email records.
5. Resume the existing VM, confirm its address and prepare the backend.
6. Check the database baseline, start API/worker, then connect `api` DNS and HTTPS.
7. Deploy Pages, bind the apex domain, configure Supabase redirects.
8. Build the live extension and exercise the actual signed-in workflow.
9. Keep the initial pilot small, keep audit limitations visible, and monitor credit use daily.
10. Back up and disable the paid project before the cutoff, even if the app is working well.

For the first step, provide only non-secret information: **current credit amount/expiry, Paid versus Free Trial status, and the VM's current status/zone**. We do not need your payment credentials or secret keys in chat.

## Related repository documents

- [Existing backend runbook](docs/google-cloud-vm.md): installation details; this guide adds the complete frontend/domain/financial exit path and uses the newer `/ready` endpoint.
- [Live acceptance audit](LIVE_BETA_AUDIT_2026-10-31.md): what passed, failed or remains unverified.
- [Recorded F1-F6 changes](docs/prelaunch-fixes-2026-10-31.md).
- [Checkpoint and logging contract](docs/checkpoints-and-request-logs.md).
- [Current state](CURRENT_STATE.md), [architecture](ARCHITECTURE.md).

**Session boundary:** creating this guide did not start a VM, change billing or AutoPay, set a cutoff, migrate DNS, deploy code, activate paid services, commit/push changes, or close local development services. Each step above still needs to be performed and verified during deployment.
