<!-- /founder:go-to-market · 2026-09-24 · input: Walkthru, the launch check for apps built with AI (journeys in owner's Chrome, SEO, GEO, passive security). Solo technical founder, launch 2026-10-20, $0-$500/mo budget. Output is a section of a co-founder briefing PDF. -->

# Go-to-market: Walkthru

Full version with context: chapter 17 of `Walkthru-Briefing.pdf` (source `docs/briefing/walkthru-briefing.html`).

Assumption: no paying users and no product analytics yet; funnel numbers come from the Supabase `runs` table.

## 1. Launch readiness
- **Minimum to launch:** Instant Scan on a real domain, extension on the Chrome Web Store, one public demo report, the SPEC.md pricing page, paid passes through Dodo. Plus can wait.
- **Enough users:** yes. Lovable alone was near 8 million users by late 2025 ([Wikipedia](https://en.wikipedia.org/wiki/Lovable_(company))).
- **Biggest risk:** the install step. Measure it with experiment A2 before launch.

## 2. Pre-launch (now to 10-20)
- Experiments A1 (5 paid of 100 scans at $9), A2 (5 of 20 beta users finish a run in 48 h), A3 (GEO headline gets 1.5x scan starts). Details in `founder/validate-idea.md`.
- Posts: Indie Hackers data post ("I scanned 30 AI-built apps; 22 are invisible to ChatGPT"); X build-in-public before/after rerun; r/SideProject tool post with the build story; Lovable and Bolt communities guide on SPA rendering for AI crawlers; dev.to "7 things AI crawlers need from your site".
- Waitlist only for Plus (watch and MCP, November).
- Assets: 60 to 90 s demo video (URL, "AI sees 6 words", journey, fix prompt, rerun); one public demo report; 3 beta quotes with permission: [Quote from a beta user].

## 3. Launch day (Tue 10-20)
- **Show HN:** usable without sign-up, which HN favours ([HN FAQ](https://news.ycombinator.com/newsfaq.html)). Title: "Show HN: Walkthru, a launch check that shows what ChatGPT sees on your site". Founder answers technical comments for 3 hours. Never ask for upvotes.
- **Product Hunt:** 12:01 am Pacific; no hunter needed; gallery from the real report, demo video, founding-price offer, maker comment.
- **Reddit:** r/SaaS allows self-promotion once every 60 days, use its weekly share thread ([OneUp](https://oneup.today/blogs/reddit-self-promotion-rules-saas)). r/SideProject and r/indiehackers with a story, not a pitch.
- **X:** 5-post thread: GEO shock screenshot, how the test user works, safety rules, before/after rerun, link.

## 4. First 90 days: channels
| # | Channel | CAC | Time | First action |
|---|---|---|---|---|
| 1 | Free scans posted in founder communities | Estimate: $0, about 1 h per customer | Days | Scan 10 of this week's launches, send owners their report |
| 2 | Badge and public-report backlinks | $0 | Weeks to months | Ship V8, ask every beta user to add the badge |
| 3 | Show HN, Product Hunt | $0 | One-day spike | Draft Show HN text and PH gallery |
| 4 | GEO search content | Estimate: $0, writing time | 2 to 3 months | One guide with a free-scan call to action |
| 5 | Agency outreach | Estimate: $0 to $50 | 1 to 2 months | 20 agencies get a free report of one client site |

- Content: "What ChatGPT sees on 30 AI-built apps"; Lovable/Bolt SEO and GEO checklist; "Why your Supabase signup emails never arrive"; security headers for Vercel apps in 5 minutes; "An AI tried to sign up to 20 Product Hunt launches".
- Partnerships: template and course creators in the Lovable, Bolt and Cursor ecosystems; MCP directories once V20 ships.
- Product-specific tactic: a weekly "Launch Ready" leaderboard of launches, with owners' permission.

## 5. Metrics (Estimates)
| Metric | D30 | D60 | D90 | Tool | If below |
|---|---|---|---|---|---|
| Instant Scans per week | 150 | 300 | 500 | Supabase `runs` | More public scans; test GEO headline |
| Scan to signup | 15% | 20% | 25% | Supabase | Make the locked fix prompt more visible |
| Install to finished run | 25% | 35% | 40% | `runs` by user | Onboarding video; cloud runner |
| Paying customers | 5 | 15 | 30 | Dodo | Interview 5 non-payers |
| Paid users rerunning within 14 days | 40% | 50% | 60% | Runs with a comparison | Rerun reminder email; ship watch |

## 6. Budget ($0 to $500)
- Free: community posts, launches, content, badge loop, outreach.
- Pay for: domain (about $15/yr), Chrome Web Store ($5), Claude comparison (about $2), later Supabase Pro ($25/mo).
- Best spend under $200: $100 on the A3 Reddit headline test, because it sets the landing headline every later visitor sees.

Saved to `founder/go-to-market.md`. Next: `/landing-page`, `/metrics-dashboard`.
