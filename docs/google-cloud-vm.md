# Current backend on a Google Cloud VM

Prepared 2026-10-12 against the current checkout. This is a follow-along runbook, not evidence of a live deployment. It supersedes the Render instructions in `deploy.md`. Domain: `trywalkthru.com`; API: `api.trywalkthru.com`. Supabase keeps the database, auth and evidence storage; Hostinger keeps the business inbox. The frontend can remain on its separately selected host.

## 1. Create the VM

In Google Cloud Console select the **Walkthru** project, check its linked billing account and remaining trial credit, then open **Compute Engine > VM instances > Create instance**. Enable the Compute Engine API if prompted.

| Setting | Initial choice |
| --- | --- |
| Name | `walkthru-api` |
| Region | `australia-southeast1` (Sydney), provided Supabase is still in the recorded Sydney region |
| Zone | An available Sydney zone; record the chosen zone |
| Machine series/type | E2, shared-core, `e2-small`, 2 GB RAM |
| Provisioning | Standard/on-demand, not Spot |
| Operating system | Ubuntu 24.04 LTS, x86/64, ordinary image rather than Ubuntu Pro |
| Boot disk | 20 GB balanced persistent disk |
| Public web ingress | Allow HTTP and HTTPS (80 and 443) |
| GPU / additional disks | None |
| Service account | None for this key-based HTTP/Supabase deployment; Vertex/model activation is separate |
| Availability | Automatic restart enabled; deletion protection enabled |

This is a limited-pilot starting point, not a measured production minimum. E2 small exposes two shared vCPUs but provides 0.5 sustained fractional vCPU in aggregate, with bursts. The models run remotely and the interactive browser runs in the owner's extension; the VM runs Python API, scanning, queues and scheduling. Review RSS, CPU, connection usage and concurrent run latency before a wider launch. Resize to `e2-medium` if 2 GB is insufficient rather than relying on sustained swap.

Review the console quote before Create. VM compute, disk, IPv4, outbound traffic and optional services are separate cost components. The old screenshot's 90 remaining days is historical: check today's balance and expiry. Trial credit does not extend the expiry date. An alerts-only billing budget is not a spending cutoff. Do not buy a commitment or upgrade billing just to create this pilot.

Sources: [VM creation](https://docs.cloud.google.com/compute/docs/instances/create-start-instance), [E2 specifications](https://docs.cloud.google.com/compute/docs/general-purpose-machines#e2_shared-core), [pricing](https://cloud.google.com/products/compute/pricing/general-purpose), [trial conditions](https://docs.cloud.google.com/free/docs/free-cloud-features), [budget alerts](https://docs.cloud.google.com/billing/docs/how-to/budgets).

## 2. Give it a stable address and connect

After the VM starts, open **VPC network > IP addresses**, find its external IPv4 and promote it to a regional static address named `walkthru-api-ip`. Keep it attached to this VM. Record the address and zone. Reserved addresses are billable; release an unused address when retiring the deployment. [Static address instructions](https://docs.cloud.google.com/vpc/docs/reserve-static-external-ip-address).

Connect with the VM's SSH button. Before public launch, restrict SSH to an authorized administration path. IAP is the preferred option: allow TCP 22 from `35.235.240.0/20` to this VM's network tag, grant the administrator the required IAP/Compute permissions, test `gcloud compute ssh walkthru-api --zone=YOUR_ZONE --tunnel-through-iap`, then remove any broader SSH rule affecting this VM. Keep your current session until the restricted path works. Public ports are 80/443, not 8010/5432/8020. [IAP requirements](https://docs.cloud.google.com/iap/docs/using-tcp-forwarding).

On the VM:

```bash
sudo apt-get update
sudo apt-get install -y python3-venv git nginx certbot python3-certbot-nginx
python3 --version
```

Ubuntu 24.04 supplies Python 3.12, matching the lockfile's target. Nginx and Certbot are VM packages for the HTTPS reverse proxy, not new Python application dependencies. Keep normal OS security updates enabled.

## 3. Install the published release

```bash
sudo adduser --system --group --home /opt/walkthru --no-create-home walkthru
sudo install -d -o walkthru -g walkthru /opt/walkthru
sudo -u walkthru git clone https://github.com/watermelon588/Walkthru.git /opt/walkthru/repo
cd /opt/walkthru/repo
sudo -u walkthru git rev-parse HEAD
```

Compare the printed commit to the release published in this setup session. Pin that full commit, rather than accepting later unrelated work:

```bash
sudo -u walkthru git checkout --detach YOUR_VERIFIED_COMMIT
cd /opt/walkthru/repo/apps/api
sudo -u walkthru python3 -m venv .venv
sudo -u walkthru .venv/bin/python -m pip install -r requirements.lock
sudo -u walkthru .venv/bin/python -m pip install -e . --no-deps
```

Do not run `dev.py`, install local admin credentials on the VM, or launch the private founder admin panel. No local PostgreSQL server, Redis, GPU or server browser is required by this deployment path. Linux installation and live capacity are checked on the VM; local Windows tests do not establish those outcomes.

## 4. Set private production configuration

```bash
sudo install -d -m 0750 -o root -g walkthru /etc/walkthru
sudo install -m 0640 -o root -g walkthru /dev/null /etc/walkthru/api.env
sudo nano /etc/walkthru/api.env
```

Fill this file directly on the VM. Replace placeholders; never commit this file or paste its contents into chat. For connection URLs use URL-encoded passwords and single-quoted values. Systemd reads this file; manual checks below use python-dotenv rather than evaluating it as shell code.

```dotenv
APP_ENV=production
CHECKPOINTER=postgres
WEB_URL=https://trywalkthru.com
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLISHABLE_KEY
SUPABASE_SECRET_KEY=YOUR_SERVER_SECRET_KEY
DATABASE_URL='YOUR_SUPABASE_SESSION_CONNECTION_STRING_WITH_SSLMODE_REQUIRE'
CHECKPOINT_DATABASE_URL='THE_SAME_SESSION_CONNECTION_STRING'
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

`WEB_URL` must be the actual browser frontend origin, without a trailing slash. If the frontend currently uses a preview domain, use that origin until its custom domain is connected. The API permits that configured browser origin; do not assume a second preview origin is automatically allowed.

Keep `JOB_WORKERS` and `RETENTION_JOB` out of this common environment file: their different API/worker values belong in the service units below. Systemd environment-file values otherwise take precedence over `Environment=` settings.

From Supabase **Connect**, choose the **session pooler, port 5432**, with `sslmode=require`. Do not use transaction pooling on 6543 for checkpoints. The session pooler works from an IPv4 VM. Keep the private checkpoint schema out of exposed API schemas. [Supabase connections](https://supabase.com/docs/guides/database/connecting-to-postgres), [repository checkpoint contract](checkpoints-and-request-logs.md).

Use existing approved free provider/model configuration. Leave optional integrations absent unless already approved and verified. Do not copy your entire development `.env`: omit `ALLOW_LOCAL_SCANS`, test accounts, private admin credentials, dev URLs and unapproved paid keys. Add Resend/other application settings individually when those integrations are ready. Hostinger inbox settings do not belong in this API file.

## 5. Check the schema before starting services

The baseline API needs migrations 0001 through 0003, with matching applied checksums. Migrations 0004/0005/0006 in this release are proposed receipt/reservation/admission storage, not an instruction to activate them. Keep their flags off for this initial deployment.

```bash
cd /opt/walkthru/repo/apps/api
sudo -u walkthru .venv/bin/python -c "from dotenv import load_dotenv; load_dotenv('/etc/walkthru/api.env'); from app.migrate import main; main(['status'])"
```

Review the output against the intended Supabase project. The existing status command creates its migration-ledger table if absent; it does not apply pending numbered migrations. Do not run unqualified `python -m app.migrate` as a setup shortcut: it applies every pending migration, including the proposed ones.

If 0001 through 0003 are already applied and unchanged, proceed. If they are pending, take a backup and use a stopped-service maintenance window. The following explicitly limits the existing checksum-aware runner to the reviewed baseline files; it does not edit applied SQL or apply 0004 onward:

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

Only perform that mutation after the project, backup and pending baseline are confirmed. A checksum mismatch or conflicting checkpoint schema requires investigation, not editing SQL or bypassing the runner. New receipt/ledger activation is a separate reviewed step.

## 6. Supervise one API process and one worker

Create `/etc/systemd/system/walkthru-api.service` with `sudo nano`:

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

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now walkthru-worker walkthru-api
sudo systemctl status walkthru-api walkthru-worker --no-pager
curl --fail http://127.0.0.1:8010/health
```

`RETENTION_JOB=1` remains on the API because the current code also starts its separate citation scheduler there. `JOB_WORKERS=0` prevents duplicate general job threads in the API. The standalone worker runs general report/retention/watch scheduling; its imports disable the API's extra schedulers. Keep one API process initially. Worker count alone does not cap concurrent scans/crawls.

`/health` is useful for a stalled queue but catches database errors internally, so a 200 alone is not database readiness. Verify the schema/checkpoint startup logs, a signed-in plan read and a completed queued report as well.

## 7. Connect DNS and HTTPS

At the domain's **active DNS provider**, add only this website record:

| Type | Name | Value |
| --- | --- | --- |
| A | `api` | The VM's reserved static IPv4 |

Keep the existing Hostinger MX/SPF/DKIM/DMARC records. If DNS is in Cloudflare, leave this API record **DNS only** initially. There is no need to change nameservers just to add a subdomain.

Create `/etc/nginx/sites-available/walkthru-api`:

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
sudo ln -s /etc/nginx/sites-available/walkthru-api /etc/nginx/sites-enabled/walkthru-api
sudo nginx -t
sudo systemctl reload nginx
```

Wait until `api.trywalkthru.com` resolves to this VM and port 80 reaches Nginx, then:

```bash
sudo certbot --nginx -d api.trywalkthru.com --redirect
curl --fail https://api.trywalkthru.com/health
sudo certbot renew --dry-run
```

Use an email address you monitor when Certbot asks. Keep 80 available for certificate HTTP validation/redirect and 443 for the API. Backend port 8010 stays loopback-only. Nginx overwrites incoming forwarded addresses, and Uvicorn trusts only the loopback proxy. Buffering is off for the MCP streaming endpoint. [Ubuntu Nginx](https://ubuntu.com/server/docs/how-to/web-services/install-nginx/).

Cloudflare proxying is optional. Enabling it later requires trusted Cloudflare real-client-IP handling in Nginx, otherwise address limits see Cloudflare rather than individual visitors. Use verified origin TLS and Full (strict) if proxying; never Flexible. The DNS-only HTTPS setup works independently of frontend hosting.

## 8. Accept the deployment and record the release

1. Set the frontend and extension production API URL to `https://api.trywalkthru.com`, rebuild/redeploy them and reload the installed extension. Reconcile the Supabase Site URL/redirect URLs with the actual frontend domain.
2. Sign in through the frontend: verify plan/history reads and CORS. Complete one owner-authorized test and ensure its report leaves the queue. Verify evidence access using the intended owner permissions.
3. Follow the synthetic start/resume drill in [checkpoints](checkpoints-and-request-logs.md), loading `/etc/walkthru/api.env` via python-dotenv for each command. Verify an API restart preserves state, and test current-client replay from [run idempotency](run-idempotency.md).
4. Reboot the VM once at an idle test window, reconnect and check both services, HTTPS and a fresh authorized report. Record commit, region/type, startup results, queue latency and any failures. An installed-extension run across restart remains required; local tests do not replace it.
5. Inspect `free -h`, `df -h`, service memory and `journalctl -u walkthru-api -u walkthru-worker --since '15 minutes ago' --no-pager`. Do not paste private logs without redaction. Cap log retention for the small disk and add uptime/cost alerts.

One VM is a recoverable pilot host, not multi-zone high availability. Before public launch confirm adequate concurrent capacity, Supabase backup/recovery and trial continuity. Never keep large disposable test clusters on this boot disk.

## 9. Update or roll back

At an idle maintenance window, record the running commit and stop API/worker. Fetch the reviewed release, pin its SHA, install its locked dependencies, review migration status, and restart both services. Recheck HTTPS, authenticated reads, a queued report and restart behavior. Preserve configuration outside Git. For rollback choose a code release compatible with the applied schema and pending checkpoints; restore matching dependencies. Do not automatically run down migrations or roll back to public-schema checkpoint storage.

The immediate follow-along checkpoint is **VM creation**. DNS, credentials, schema activation and deployed acceptance remain later steps until the VM exists and the founder supplies its non-secret setup details.
