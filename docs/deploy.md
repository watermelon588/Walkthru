# Deploying the v0.5 friends beta

Web on Vercel (free), API on Render (free), database and sign-in on Supabase (existing project), extension as a zip your friends load themselves. About 45 minutes the first time.

## 0. Before anything goes online (10 minutes, Supabase dashboard)

1. **SQL editor:** run the last block of `apps/api/schema.sql` (drops `runs.email`, see docs/decisions.md 2026-09-25). Until then, emails already stored on 5 public reports stay readable with the public key.
2. **Authentication > Users:** the repo is public and older commits contain the passwords of `walkthru.tester@example.com` and `walkthru.delete-check@example.com`. Delete the delete-check user, and set a new password for the tester (then put it in `apps/api/.env` as `TEST_USER_PASSWORD`).
3. **Project Settings > API:** rotate the secret key (shared in chat on 2026-09-18). Use the new one in step 1 below.

## 1. API on Render

1. render.com > New > **Blueprint** > connect the GitHub repo. It reads `render.yaml` (free plan, `apps/api`, health check `/health`).
2. Fill the environment variables it asks for:

   | Variable | Value |
   |---|---|
   | `WEB_URL` | your Vercel address from step 2, like `https://walkthru.vercel.app` (no trailing slash). Put a placeholder first and update it after step 2. |
   | `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY` | from Supabase > Project Settings > API |
   | `GROQ_API_KEY`, `GOOGLE_API_KEY`, `OPENROUTER_API_KEY` | the same keys as `apps/api/.env` |
   | `PAGESPEED_API_KEY` | optional (mobile speed findings) |
   | `RESEND_API_KEY`, `RESEND_FROM` | leave empty: without your own domain Resend cannot mail other people, and "Email me" opens the user's mail app instead |

   Payments: the `DODO_*` variables, filled in by [docs/billing.md](billing.md). Leave them empty and checkout simply stays off.

   Never set `ALLOW_LOCAL_SCANS` in production.
3. Deploy, then open `https://YOUR-API.onrender.com/health`. It should say `{"status":"ok"}`.

**Free-tier behaviour to expect:** the API sleeps after 15 idle minutes and takes about a minute to wake, so a friend's first scan of the day is slow. Optional: a free cron (cron-job.org) calling `/health` every 10 minutes keeps it awake and uses about 744 of the 750 free hours a month. A redeploy or restart ends any test that is mid-run (it closes with a partial report); do not redeploy while friends are testing.

## 2. Web on Vercel

1. vercel.com > Add New > Project > import the repo. **Root Directory: `apps/web`**. Framework: Vite (detected).
2. Environment variables:

   | Variable | Value |
   |---|---|
   | `VITE_SUPABASE_URL` | Supabase URL |
   | `VITE_SUPABASE_ANON_KEY` | Supabase publishable key (safe to expose) |
   | `VITE_API_URL` | `https://YOUR-API.onrender.com` |
   | `VITE_EXTENSION_ID` | `cilngbcfpoojecjoiklimnjnomjglcdo` (fixed by the key in `apps/extension/wxt.config.ts`) |
3. Deploy. `apps/web/vercel.json` adds the page routing and security headers (CSP, nosniff, referrer policy, no framing).
4. Back in Render, set `WEB_URL` to the Vercel address and redeploy the API (CORS and report links use it).

## 3. Supabase sign-in for the new address

Authentication > URL Configuration:
- **Site URL:** your Vercel address.
- **Redirect URLs:** add `https://YOUR-SITE.vercel.app/**` (keep the localhost ones for development).

**Magic links will hit a wall:** Supabase's built-in mailer sends only a few emails an hour for the whole project. With several friends signing in, links stop arriving ("email rate limit exceeded"). Two fixes, pick one:
- **GitHub sign-in (recommended, free, no domain):** GitHub > Settings > Developer settings > OAuth Apps > New. Homepage: your Vercel address. Callback: `https://YOUR-PROJECT.supabase.co/auth/v1/callback`. Paste the Client ID and secret into Supabase > Authentication > Providers > GitHub and enable it.
- Your own SMTP in Supabase (needs a domain).

## 4. The extension zip for friends

```
cd apps/extension
copy .env.beta.example .env.beta     # fill in the four values
npm run zip:beta                     # writes .output/extension-0.1.0-chrome-beta.zip
```

Send that zip. Friends: unzip, open `chrome://extensions`, turn on Developer mode, Load unpacked, pick the unzipped folder, pin the bird. Then sign in on the website, open the dashboard and press **Connect extension**. The fixed key means every copy has the id the website expects. For a Chrome Web Store upload later, remove `key` from `wxt.config.ts` and update `VITE_EXTENSION_ID` to the store's id.

## 5. Smoke test after deploy (10 minutes)

1. Landing page loads, no errors in the browser console.
2. Instant Scan of a real site from the landing page opens its public report.
3. Sign in, see the dashboard and your runs left.
4. Connect extension, run one test on your own site, open the report.
5. Share: the copied `/r/` link opens in a private window.
6. Email me: your mail app opens with the report link.
7. Signed in, go back to the landing page: the nav says Dashboard.
