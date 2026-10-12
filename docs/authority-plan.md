# Authority and backlinks, prelaunch advisory mode (R-S17a)

Implemented locally 2026-10-07. Code:

- `apps/api/app/scans/authority.py` (plan, counts, text);
- `authority=authority.build(...)` in `app/agent/report.py` and `Report.authority` in `schema.py`;
- the Authority chapter status in `report_chapters.py` and `reportChapters.ts`;
- `fix_prompt._authority_brief` (`section=authority`) and MCP `get_report(section="authority")`;
- `apps/web/src/components/AuthorityPlan.tsx`.

No fetch, link index, mention search, model call, dependency, migration or outreach.

This is the **advisory mode** only. Supplied link or mention exports, licensed link data and measured mode are not built, so tactics that need them stay "Needs input". The slice counts as partial, like R-S17.

## The plan

The plan is built from the R-S17 page map, which is the audited pages' own copy, and stored as `report.authority`. It never creates findings or changes a score. Legacy reports without a map get no plan, and their chapter stays **Not measured**.

Twelve tactics, always in this order, each with one state:

| Tactic | State in advisory mode | What it needs or builds on |
|---|---|---|
| Recover lost links | Needs input | A backlink history export with the last-seen date for each link. No history means loss is unverified. |
| Unlinked mentions | Needs input | A dated page naming the product without a link. An AI answer is not such a page. |
| Free tools | Advisory brief, or not applicable when no page states a topic | The shallowest audited page's main topic, quoted |
| Listicle outreach | Needs input | A real current list with its criteria, plus true product facts |
| Competitor links | Needs input | Authorized or licensed link data for named competitors. Links are never transferred or guaranteed. |
| Broken link building | Needs input | A verified dead link and a matching working page |
| Fix outdated guides | Needs input | A dated guide with a wrong passage, plus primary evidence |
| Statistics page | Needs input | The owner's own data with method, sample size and dates. Walkthru never supplies statistics. |
| Reporter outreach | Needs input | A genuine open request, its deadline, consent and an attributable quote |
| Infographics | Advisory brief, or not applicable without a page of three or more sections | That page's section headings, quoted |
| Article to video | Advisory brief, or not applicable as above | One scene per section heading |
| Link exchanges | Not recommended | Google's link spam policy. Paid placements are marked `rel="sponsored"`. |

Each tactic carries these fields:

- `target` and `source`: an audited page, "audited in this report". Both are `null` when the tactic needs input.
- `brief`, `reader_benefit`, `prerequisites` and `missing`.
- `effort` and `measurement`: referring pages or uses after 90 days, from the owner's own data. No rank change is promised.
- `policy`.

The plan also carries:

- **`rules`:** nothing is sent, posted, registered or placed; drafts need a factual and rights review; links do not guarantee citations or rank.
- **`separate`:** GEO readiness, AI citations and backlinks are three different things. A mention or memory answer is not a citation, and a failed or missing sample is not zero visibility.

## Where it appears

- **Web report:** the Authority and backlinks chapter shows **Advisory, no link data** with a count summary. Advisory briefs are cards with source, needs and measurement behind a disclosure. The other tactics are listed with what they need, the exchange policy links to Google's policy, and a "Kept separate" block closes the chapter. Contents shows the same label, and print expands the disclosures.
- **Prompt:** `fix-prompt?section=authority` returns an **authority plan**, not a repair batch. Its rules: no email, messages, posts, profiles, publishing or link placement; drafts only when the owner asks; never invent publishers, mentions, lists, requests, links or statistics; paid placements marked sponsored; no exchanges; no promised rankings, traffic or citations.
- **MCP:** `get_report(section="authority")` returns the same text (`authority.lines`), with the existing owner access checks. Reading a stored report makes no fresh request, so no admission is needed.
- **Parity:** the web and API chapter summaries match exactly, through the shared `authority-advisory` fixture case.

## Verification (2026-10-07)

- **API** (`tests/test_authority.py`, 9 tests):
  - twelve ordered tactics with explicit states and no link data; legacy reports get no plan;
  - needs-input tactics have no target, source or brief;
  - advisory briefs use only audited pages and their own words;
  - not applicable without material;
  - exchanges never advisory, with a sponsored note and a policy source;
  - backlinks, GEO and citations kept distinct;
  - chapter status only with a plan;
  - the prompt is an owner plan, not a send or publish task;
  - MCP returns the same text.

  Shared fixtures gained `"authority": null`, and the chapter fixture gained `authority-advisory`. Contract, chapter, assertion, opportunity and MCP suites: 82 passed.
- **Web:** 52 node tests passed, including parity, plus TypeScript, Vite build and lint.
- **Browser:** the actual `ReportView` with a real plan from the builder, in isolated headless Edge, passed 12/12 checks with no console errors:
  - status, Contents label and quoted briefs;
  - needs-input wording with no invented counts;
  - the exchange policy link and the "Kept separate" block;
  - no em dashes;
  - closed disclosures, plus print expansion and restore;
  - the legacy fallback;
  - no overflow at 320 and 768 px.

  Artifacts are in ignored `evals/results/authority-plan/`.

## Not built

- **Supplied exports or licensed link data**, so lost links, unlinked mentions, competitor, broken-link and listicle opportunities never become "supported". This needs an upload path or approved provider, plus a budget decision.
- **Verification of other sites' pages** (dead links, outdated passages): that is fresh research and needs R-S9 admission and owner policy.
- **Drafts of pitches, tool specs, storyboards or media briefs:** these are separately scoped, with a factual and rights review.
- **Any outreach, publishing or placement:** excluded by design.
