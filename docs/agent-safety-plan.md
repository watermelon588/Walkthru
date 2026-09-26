# Agent safety, permission and trust plan

> **IMPORTANT: FIX BEFORE DEPLOYMENT (launch gate).** Written 2026-09-25 after a test run: the agent was told to like five posts on Instagram with the founder's logged-in account. Items 1 to 8 are built (2026-09-26); the founder's legal review, Unlisted publish and a real-browser red-team pass remain (status below). Every item marked **GATE** must ship, with its tests, before the extension goes to the Chrome Web Store or the product is launched. Work through it minutely; do not shortcut any GATE item.

## 1. The problem, plainly

- **Anyone can install a Chrome Web Store extension.** Walkthru's extension runs in the user's own browser, with the user's cookies and logins, on any tab they open.
- **We cannot prove who owns a website from a URL.** A paying customer is not proof either.
- **Prompt rules are not a safety boundary.** A page can carry text like "ignore your instructions", and a user can phrase a goal to slip past a prompt. Only deterministic code the model cannot talk its way past is a boundary.
- **The risks are real.** Without limits, the agent could be pointed at:
  - banking, trading, social, government or webmail sites;
  - "like 50 posts", "add stock X to my cart", "sign up 100 accounts";
  - sites that did not agree to be tested.

  That gets users banned by those platforms, gets sites to block us, gets the extension reported and removed, and exposes us legally.
- **What happened on Instagram:**
  - The agent could not see the Like button, because its snapshot drops icon-only buttons and never re-reads the page after scrolling.
  - It then blamed the site.
  - Separately, "like" was never blocked, because safe mode did not cover social actions.

  Three bugs, all ours.

## 2. How others handle this

Descriptions below are from their public documentation and launch posts; recheck before quoting them in marketing.

| Who | What they do | What we take |
|---|---|---|
| Security scanners (Detectify, Intruder, Probely, HostedScan) and load testers (loader.io, k6 Cloud) | They prove domain ownership (DNS TXT record, a file at a known path, or a meta tag) before any active test. Unverified targets get passive checks only, or nothing. | Ownership proof decides what the agent may do. We already have meta tag and well-known file verification (`security.verification_token`); add DNS TXT. |
| Google Search Console, Bing Webmaster | Same three proofs, re-checked over time; a proof that disappears revokes access. | Re-check verification periodically and before each logged-in run, not only once. |
| Browser agents (OpenAI Operator / ChatGPT agent, Anthropic Claude for Chrome, Perplexity Comet) | Per-site permission; blocked site categories (financial services and similar high-risk categories, as announced at launch); a confirmation before consequential actions; "take over" for logins and CAPTCHAs, which a human solves; prompt-injection defences in the harness, not only in the prompt. | A server-side blocklist of categories, human take-over for CAPTCHAs and logins, confirmation gates in code, and page text treated as untrusted data. |
| Test automation SaaS (QA Wolf, Mabl, Ghost Inspector, Checkly) | They test the customer's own apps; terms of service say the customer must own or be authorised for the target; staging URLs are encouraged. | An acceptable use policy with the same wording, plus a staging-first product flow. |
| Every serious crawler (Googlebot, Ahrefs, Common Crawl) | An identifiable user agent, robots.txt respected, a public bot page with opt-out and a contact. | Our server-side scans get a public "Walkthru bot" page with an opt-out list we honour. |

**The common rule:** full power on sites you prove you own; read-only visitor behaviour everywhere else; certain categories blocked outright; enforced by the server, not by the model.

## 3. Target design: three site modes, decided by the server

The API decides the mode when a run starts (`POST /runs`) and returns it to the extension. The extension cannot pick its own mode. Every step is checked again against the mode in `persona._enforce` (server) and `execute.ts` (extension); both must agree, and the server wins.

| Mode | When | The agent may | The agent may not |
|---|---|---|---|
| **Owner** | The run's host is a domain the user verified (DNS TXT, meta tag or well-known file), re-checked in the last 24 hours and after redirects | Everything a real visitor does, including logged-in pages, typing into forms, and one confirmed send per run | Pay, delete, cancel, transfer money, change security settings (the existing destructive list) |
| **Visitor** (default) | Any other public site | Navigate same-origin, scroll, read, click links, open menus, tabs and accordions, type into a site search box | Type into any other field, submit a form, log in, or act while the page shows a signed-in state; any social or commerce write action |
| **Blocked** | The host is on the blocklist (section 4) | Nothing; the run is refused before it starts, with a clear message | Everything |

The web app, side panel and Settings must explain the modes up front ("Verify your domain to test sign-up forms and logged-in pages").

## 4. Blocklist and goal rules (**GATE**)

**Blocked categories**, as a server-side list in `apps/api/app/agent/policy.py` plus a data file, refused on any mode unless the user has verified that exact domain:

- banking and payments;
- brokerage, trading and crypto exchanges;
- government and tax;
- healthcare portals;
- webmail;
- social networks (write actions);
- dating;
- adult;
- gambling;
- password managers and identity providers.

The seed list is the big platforms by name (instagram.com, facebook.com, x.com, linkedin.com, tiktok.com, reddit.com, youtube.com, gmail.com, outlook.com, paypal.com, stripe.com, robinhood.com, zerodha.com, coinbase.com, binance.com and others), then extend it by category.

**Popular-site rule:** any host in a top-sites list (for example the Tranco top 10,000, a free research list with a permissive licence; check it before use) runs in Visitor mode only, even if it is not blocked, unless the user verifies it.

**Goal rules**, applied in code before the planner model sees the goal:
- Refuse goals that ask to buy, trade, invest, transfer, like, follow, comment, post, share, repost, subscribe, vote, message or review on anything other than an Owner-mode site.
- Refuse bulk goals ("50 accounts", "every post").
- The planner's own refusal stays as a second layer.

**Action gate**, the one the model cannot bypass. Extend `safety.py` and `execute.ts` with:
- **social verbs:** like, follow, unfollow, comment, post, share, repost, retweet, subscribe, vote, react, message, send request, connect;
- **commerce verbs:** add to cart, buy, checkout, place order, trade, invest, bid.

In Visitor mode, typing is allowed only into `input[type=search]` or a field whose role or label says search.

**Signed-in detection in Visitor mode:** if the page shows a sign-out control or an account menu, stop the run with "This page shows you are signed in. Verify your domain to test signed-in pages."

**Tests:**
- One fixture per rule.
- A test that no prompt text (goal or page text) can produce a click on a blocked control. Feed injected page text and assert that the executor refuses the action.

## 5. The extension is public: why that is acceptable, and what to lock (**GATE**)

- **Anyone can install it; that is fine.** The extension has no intelligence of its own. It needs a Walkthru account session, and every step goes through our API, which applies the mode, the blocklist, plan limits and rate limits. A modified copy of the extension still has to talk to our API, so the server-side rules are the real boundary.
- **Lock it down:**
  - `externally_connectable` only for our web app's domain (already set);
  - the fixed extension key (already set);
  - API CORS limited to our origins and the extension id;
  - no API route usable without a signed-in user.
- **During beta, publish as Unlisted** in the Chrome Web Store: only people with the link can install it. Go Public at launch.
- **Kill switches:**
  - a server flag that disables journeys globally, per user or per target domain in seconds;
  - the extension checks `GET /runs/policy` at start and obeys it.

## 6. Abuse and reputation (**GATE** for the first three)

1. **Per-target limits:**
   - at most N journeys per hour against one unverified host across all users (start with 20), and per user (start with 5);
   - a minimum pace of one action a second with small human-like pauses.
2. **Audit log per run:**
   - user, host, mode, goal and each action type, with target labels but no typed values;
   - kept 90 days for abuse investigations and disclosed in the privacy policy.
3. **Abuse contact and opt-out:**
   - `/bot` page and `abuse@` address;
   - site owners can ask for their domain to be blocked; the blocklist honours it within 24 hours.
4. **Server-side scans** (Instant Scan, watch, compare) already:
   - use an identifiable user agent;
   - respect robots.txt;
   - cap pages;
   - run passive checks only on unverified hosts;
   - are SSRF-safe.

   Add the `/bot` page link to that user agent.
5. **Automatic suspension:**
   - an account that trips the goal rules or blocklist repeatedly (for example 5 refusals in a day) gets journeys paused pending review;
   - notify the founder.

## 7. CAPTCHAs, bot walls and blocks (**GATE**)

- **Never solve or bypass** a CAPTCHA or bot wall (existing rule), and never rotate IPs or disguise the browser.
- **Detect and stop**, with status `blocked` (new) or `captcha`:
  - reCAPTCHA, hCaptcha and Turnstile widgets (already detected);
  - Cloudflare "Just a moment";
  - Akamai, DataDome and PerimeterX challenge pages;
  - HTTP 403 or 429 on navigation;
  - "Access denied" pages.
- **Human take-over:** the side panel says "A CAPTCHA appeared. Solve it yourself in this tab, then press Continue." The human solves it; the agent resumes. Only the user acts; we never automate it.
- **Report wording:**
  - "The site stopped automated testing at step N (a Cloudflare challenge). This is the site's bot protection, not a usability problem."
  - For verified owners: "Allowlist Walkthru's test sessions, or test your staging URL."
  - It never becomes a UX finding.

## 8. Honest failure wording (**GATE**)

A run that ends because the agent could not find or use a control is reported as Walkthru's limitation, not the site's fault:
- **Status `agent_lost`:** "Walkthru could not identify the control for this step (it may be an unlabelled icon). This may not affect people."
- **Wording rules:** the report writer is told to use this wording; `grounded_ux` drops UX findings that blame the site for an element the snapshot never listed.
- **Accessibility finding:** we still report an unlabelled icon button as one, because it is a real barrier for screen readers, but we do not call it a journey failure.

## 9. Perception: see what a person sees (**GATE** items 1 to 3)

1. **Labels for icon buttons:** read `aria-label`, `aria-labelledby`, `<title>` and `aria-label` inside `svg` and `img`, `data-testid`, and nearby visually hidden text. Instagram's Like, Comment and Share then read correctly.
2. **Viewport first:**
   - take visible elements top to bottom first, then a margin below the fold, then the rest, still capped at 120;
   - re-snapshot after every scroll or DOM change;
   - ids refer to the current snapshot only.
3. **Real scrolling:**
   - `scroll` scrolls the viewport smoothly by one screen (or to a target element) and waits for lazy-loaded content to settle (network idle or DOM stable, up to 2 s) before the next snapshot;
   - infinite feeds work.
4. **Vision fallback:**
   - when the goal names a control and nothing in the snapshot matches, send one masked screenshot to a vision model (Gemini Flash free tier) to point at the target;
   - the answer is mapped back to an element by coordinates and must still pass the action gate.
5. **Model tier:** Pro and Plus move to Claude Haiku 4.5 (already wired, `CLAUDE_VERTEX_PROJECT`) when revenue allows. The perception fixes come first; a better model on a broken snapshot only fails more expensively.
6. **Fixtures:**
   - an infinite feed with icon-only Like buttons;
   - a bot-wall page;
   - a signed-in page.

   Recall and false-alarm checks go in `evals/`.

## 10. A visible test user in the browser (after the GATE items)

Show what the agent is doing, honestly, so it reads as a person testing the site:
- **A cursor overlay** (Scout's pointer) that glides to the target, shows a click ripple, and moves with the scroll. It is drawn in a closed shadow root so the page cannot read or restyle it.
- **Smooth scrolling** and short human pauses (300 to 900 ms) between steps.
- **A thin banner:** "Walkthru test user is exploring this page. Your typing is paused." The user can stop at any time.
- **Hidden for screenshots:** the overlay is hidden while screenshots are captured (as Scout is today), so evidence shows the site, not our UI.
- **Reduced motion:** honours `prefers-reduced-motion` (no glide, instant highlight).
- **Honesty:** the overlay only visualises real actions; it never fakes activity.

## 11. Errors, toasts and logs (**GATE**)

One table of stop reasons, shared by the API, the side panel, the report and the docs. Each reason has:
- a code;
- a plain side-panel message (toast plus panel text);
- a report line;
- a log level.

| Code | Side panel | Report |
|---|---|---|
| `blocked_site` | "Walkthru does not run on banking, trading, social or similar sites. Test your own site instead." | Run refused before it started. |
| `visitor_mode_limit` | "Typing and sending are for sites you verified. Verify this domain to test forms." | The step was skipped; the journey continued where possible. |
| `signed_in_unverified` | "This page shows you are signed in. Verify your domain to test signed-in pages." | Run stopped at step N. |
| `bot_wall` / `captcha` | "The site asked for a human check. Solve it and press Continue, or stop." | "The site stopped automated testing (a bot check)." |
| `agent_lost` | "Scout could not find the control for this step." | Section 8 wording. |
| `rate_limited` | "Too many tests on this site right now. Try again in an hour." | Not started. |
| `goal_refused` | The refusal reason in one sentence. | Not started. |

Logs:
- structured JSON: run id, user id hash, host, mode, code, step;
- never page text, typed values or tokens;
- kept 30 days, and 90 for the audit log.

## 12. Privacy and trust: what we promise, and must prove (**GATE**)

**Technical facts to keep true, and to test:**
- The extension never reads cookies, `localStorage`, `sessionStorage`, IndexedDB, passwords or tokens of the sites it visits, and never sends them anywhere.
- Add a test that fails if the extension code calls `chrome.cookies` or `document.cookie`, or reads storage of the page.
- Typed values and form contents are masked before any snapshot or screenshot leaves the browser (existing redaction and field masking, keep the tests).
- Screenshots are private, deleted after 30 days, and only for the run's owner, their team, or a public link they create.
- Chrome permissions:
  - host permission is optional and requested only for the tested tab;
  - no `cookies`, `history`, `webRequest` or `<all_urls>` background access.
- The extension talks only to our API and our Supabase project.

**Pages to update:**
- **Privacy policy:** what the extension reads (masked page outline, control labels, screenshots of the tested tab), what it never reads (cookies, tokens, passwords, field values), the audit log and its retention, processors.
- **Terms:**
  - an acceptable use policy: test only sites you own or are authorised to test;
  - no third-party accounts, no bulk actions, no evading bot protection;
  - we may refuse, pause or suspend;
  - you are responsible for your authorisation.
- **Security page:**
  - the architecture in plain words, and the three modes;
  - a list of blocked categories;
  - how to report abuse.
- **Chrome Web Store listing:** the single-purpose statement, the "Limited Use" data disclosure, and a privacy practices form that matches the privacy policy.
- **Docs:** "Why can't Walkthru test Instagram?" and "Verify your domain" with DNS, meta and file steps.

**Consider publishing the extension source** (read-only) so anyone can check the claims; it is small and holds no secrets.

**Get a lawyer to review** the terms and acceptable use policy before launch. This plan is not legal advice.

## 13. Build order

| # | Item | Size | GATE |
|---|---|---|---|
| 1 | `policy.py`: modes, blocklist, popular-site rule, goal rules; `POST /runs` returns the mode; refusal codes (**done 2026-09-26**, see the status note) | M | Yes |
| 2 | Action gate: social and commerce verbs, Visitor-mode typing rule, signed-in detection (server and extension, with tests) (**done 2026-09-26**) | M | Yes |
| 3 | DNS TXT verification, re-check within 24 hours and after redirects (**done 2026-09-26**) | S | Yes |
| 4 | Snapshot: icon labels, viewport first, re-snapshot after scroll, smooth scroll with settle wait; feed fixture (**done 2026-09-26**) | M | Yes |
| 5 | Honest failure (`agent_lost`), bot-wall detection and take-over, stop-reason table in API, side panel and report (**done 2026-09-26**) | M | Yes |
| 6 | Per-target and per-user rate limits in Postgres (joins SD-2.1), audit log, kill switch and policy endpoint (**done 2026-09-26**) | M | Yes |
| 7 | Privacy, terms, security and bot pages; Chrome Web Store disclosures; the no-cookies test (**built 2026-09-26; founder legal review open**) | S | Yes |
| 8 | Unlisted Chrome Web Store beta; abuse contact; auto-suspension (**contact and suspension built 2026-09-26; unlisted publish is the founder's**) | S | Yes |
| 9 | Vision fallback | M | No, first update after launch |
| 10 | Cursor overlay, human pacing, banner | S to M | No |
| 11 | Claude Haiku for Pro and Plus | S (switch) | Revenue-gated |

**Status of item 1 (built 2026-09-26):**
- `apps/api/app/agent/policy.py` and `blocklist.json` (10 categories plus an empty "site owner opt-out" list). A listed entry matches the host and its subdomains, so `gov.uk` or the `bank` TLD covers every site under it.
- `POST /runs` checks, in code and before the goal planner's model call, without using a run:
  - a blocked `site`, or a tested tab already on a blocked host: 403 `blocked_site`, unless the user verified that exact host;
  - bulk goals, on any site: 422 `goal_refused`;
  - social and commerce goals (like, follow, share, post, comment, message, buy, add to cart, checkout, pay, trade, donate and similar) on an unverified site: 422 `goal_refused`;
  - a signed-in (`logged_in`) test on an unverified domain: 403 `visitor_mode_limit`.

  The message is the plain `detail`; the code is in the `X-Walkthru-Code` header (exposed to CORS). Goal text is NFKC-folded and invisible characters are dropped first.
- The reply and the run state carry `mode` (`owner` or `visitor`). `verified` stays for the extension's existing send confirmation.
- `POST /runs/{id}/observe`: when the tested tab reaches a blocked host (a share link out to Facebook, a payment page on a bank), the run stops truthfully with the reason in the report and `code: blocked_site`.
- The side panel says logged-in tests need a verified domain.
- Tests: `apps/api/tests/test_policy.py` (goal wording that must and must not match, host matching, the Instagram goal, refusals before any model call, mid-run stop).
- **Popular-site rule: not built, on purpose.** Every unverified host already runs in Visitor mode, so a top-sites list would change nothing, and it would add a data licence to check. Revisit only if Owner mode ever stops requiring verification.
- **Known limits:** the goal rules read English only, and wording can always be found that they miss. They save a model call and give a clear message; the real boundary is item 2 (the per-step action gate in `persona._enforce` and `execute.ts`), which does not depend on how the goal was worded.

**Status of items 2 to 8 (built 2026-09-26 by Claude Code, local):**
- **Item 2, the action gate.** `persona._enforce` (server) and `execute.ts` (extension) share one rule set (`safety.py` and `safety.ts`, identical verb lists). In Visitor mode: typing only into a search box; no pressing a button whose label starts with a social or commerce verb ("Like", "123 Likes. Follow", "Add to cart", even as a link); no form submit except the site's search (extension). The server never asks for such a step: it ends the run on purpose with `safe_stop` and code `visitor_mode_limit` ("Everything up to here worked"). **Deviation:** the plan's table said "the step was skipped; the journey continued where possible". A skipped step has nothing honest to continue with (the next page needs the form filled), so the run stops truthfully instead. A page showing a sign-out control or an account menu is refused at start and stops a running journey (`signed_in_unverified`); "My account" alone does not count, because logged-out shops show it. The test user's prompt says what a visitor may do, so it does not waste steps. Tests: `tests/test_action_gate.py` (injected page text included) and the extension's visitor-mode test.
- **Item 3.** A DNS TXT record `_walkthru.<host>` holding `walkthru-verification=<token>` (read over DNS-over-HTTPS) verifies a domain, next to the meta tag and the file. Every proof is checked again at every run start and after redirects, never cached. Settings and the docs show all three.
- **Item 4.** Icon-only controls read by `aria-label`, `aria-labelledby`, an inner svg label or `<title>`, image alt, `title` or `data-testid`. Menu items, switches, checkboxes, options and `summary` count as controls. Visible controls are numbered first (top to bottom), then the next screen down, then the rest, still capped at 120. Scrolling is smooth by one screen (instant with reduced motion), and every snapshot first waits up to 2 s for the page to stop changing. Fixtures: `evals/fixtures/hard/feed.html` (infinite feed, icon-only Like, injected text), `challenge.html` (bot wall), `account.html` (signed in), unlinked so crawls do not change.
- **Item 5.** One table, `policy.STOP_REASONS`: code, side panel message, report line. Finished and stopped replies carry `code` and `message`; the side panel shows the message as sent. New statuses `bot_wall` and `agent_lost` (a give-up or stuck run where the model picked elements that were not on the page). Bot walls (Cloudflare, Akamai, DataDome, PerimeterX, 403 and 429 pages) and CAPTCHAs pause the run: the person solves it in the tab and presses OK, or the run stops. Reports never turn bot checks, visitor-mode stops or Walkthru's own misses into UX findings.
- **Item 6.** `run_audit` (started and refused journeys, mode, goal, actions with control labels, never typed values; 90 days, purged by the retention job) and `run_blocks` (kill switches: global, one account, one host with its subdomains; checked at start and at every step, cached 10 s). Limits on unverified hosts: 20 journeys an hour per host across all users, and 12 per user per host. **Deviation:** the plan said start at 5 per user, but one Plus test set is up to 6 journeys on one page, so 5 would break a paid feature; 12 is two full sets. `GET /runs/policy` answers the extension before a test. Five goal or site refusals in a day pause the account and add an "abuse" line to the founder's admin panel, which also pauses and resumes runs for everyone or one site.
- **Item 7.** Privacy (what the extension reads and never reads, the safety log), Terms (acceptable use, modes), Security (modes, blocked categories, abuse and opt-out), a `/bot` page, docs "Why can't Walkthru test Instagram?", `docs/chrome-web-store.md` with the store answers, and `apps/extension/tests/privacy.test.ts` (fails on cookie, storage, history or request APIs, or broader permissions). Opted-out and paused domains are refused for scans too.
- **Item 8.** `abuse@` contact on the Security and bot pages; automatic suspension (item 6).
- **Still open, the founder's:** a lawyer's review of Terms and Privacy; the contact domain (the pages still say walkthru.dev); publishing Unlisted; a real-browser red-team pass with the extension on the hard fixture (`/feed.html`, `/challenge.html`, `/account.html`, a bulk goal, an Instagram goal), which unit tests cannot replace.

**Done means:**
- every GATE row has its tests;
- a red-team pass on the hard fixture (injected page text, blocked verbs, bulk goals, signed-in pages, a bot wall) passes;
- the founder reviews the legal pages.
