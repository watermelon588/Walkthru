# Keyword and content direction, prelaunch advisory mode (R-S17)

Implemented locally 2026-10-07. Code: `apps/api/app/scans/opportunities.py` (map), `app/scans/seo_guidance.py` (rule registry), the recalibrated checks in `app/scans/seo.py`, `recipes.json`, the Keywords chapter in `report_chapters.py`/`reportChapters.ts`, `apps/web/src/components/KeywordMap.tsx`, the content brief in `fix_prompt.py` and MCP `get_report(section="keywords")`.

This is the **prelaunch advisory** mode only. Owner search evidence needs a read-only Search Console connection (R-S16, after R-S9). Licensed external demand needs a separate budget decision. Neither is built.

## What the map is

A page/intent map built only from the audited public pages' own copy during the existing crawl. There is no extra fetch, model call or provider. It is stored as `report.opportunities` and never creates findings or changes a score: missing search data before launch is expected, not a defect.

| Field | Source and rule |
|---|---|
| `mode`, `demand_data` | Always `prelaunch_advisory` and `none` here |
| `primary_intent` | The page's first `h1`, else its title, quoted exactly and labelled with its source. A hypothesis to confirm, not demand. Pages with neither get none. |
| `supporting` | Up to five `h2` texts, quoted |
| `current` | Quoted title, meta description and `h1`s |
| `proposed` | Rearranges the page's own words only. A missing title takes its `h1`. A title duplicated across pages becomes `"<h1> \| <title>"`. A missing description takes the first sentence of its first paragraph. The outline is its existing headings. Script and style text is ignored. |
| `gaps` | Missing title/`h1`/description/sections, a shared title, no inbound link from another audited page |
| `internal_links` | Audited pages that link here, and up to three suggested sources: the homepage when it doesn't link, plus pages whose text shares two or more words with the intent |
| `next_action`, `effort` | One concrete step, low or medium |
| `overlaps` | Pages sharing a main topic, with a note to decide which page answers it before calling it competition |
| `excluded_noindex` | Pages asking not to be indexed are left out |

There are no volume, difficulty, rank, position, traffic, click, impression or CTR fields; a test enforces this. Pages are ordered by the size of their gaps, then crawl order, up to ten.

## Where it appears

- **Web report:** the Keywords and content chapter shows status **Advisory, no search data**, a count summary, the basis and measurement plan, and one card per page. Each card shows the quoted intent hypothesis and next action, with quoted copy, proposals, gaps and links behind a disclosure. The Contents list shows the same label, and print expands the disclosures. Reports without a map keep **Not measured**.
- **Keywords chapter prompt:** `fix-prompt?section=keywords` and MCP `get_fix_prompt(section="keywords")` return a **content brief**, not a repair batch. Its rules: use only facts already on the site, add no claims, numbers, names, reviews or citations, ask the owner before publishing, and promise no rankings, traffic or citations.
- **MCP:** `get_report(section="keywords")` returns the same text as the brief (`opportunities.lines`).
- **Parity:** web and API chapter statuses are checked by the shared `keyword-advisory` fixture case.

## Recalibrated SEO advice

Google's current guidance (reviewed 2026-10-06):

- **Titles** have no length limit, and title links are truncated to fit the device. [Title links](https://developers.google.com/search/docs/appearance/title-link).
- **Meta descriptions** have no length limit, and snippets come mostly from page content. [Snippets](https://developers.google.com/search/docs/appearance/snippet).
- **Headings** have no ideal count, and their order doesn't matter for Search. [SEO starter guide](https://developers.google.com/search/docs/fundamentals/seo-starter-guide).

The changes keep the finding titles, so rule IDs and owners' ignored findings are preserved:

| Rule | Severity | Now |
|---|---|---|
| `seo.missing_page_title` | high (unchanged) | Recommended; no length target in the fix |
| `seo.page_title_is_too_short` | medium to low | Advisory |
| `seo.page_title_is_too_long` | low | Advisory: no limit, may be truncated; put key words first |
| `seo.missing_meta_description` | high to medium | Advisory: snippets usually come from page text |
| `seo.meta_description_is_too_short` / `_too_long` | low | Advisory |
| `seo.no_hn_heading` | medium to low | Advisory: helps visitors and screen-reader users |
| `seo.more_than_one_hn_heading` | low | Advisory, optional |

`seo_guidance.RULES` records each rule's status, source and review date. Fix prompts and MCP `get_finding` add a `Guidance (advisory, reviewed ...)` line for these rules. Recipes no longer say "120 to 160", "30 to 60" or "keep one h1 per page".

## Verification

- `tests/test_opportunities.py`, 10 tests:
  - The mode is explicit and no demand-number fields exist.
  - Proposals use only words from the source pages, and script text is never read.
  - Gap priority, inbound and suggested links, duplicate titles, overlaps and noindex exclusion.
  - A page with no readable topic gets no invented intent.
  - The checks are advisory with registered sources.
  - Guidance lines appear and the recipes are corrected.
  - The chapter shows advisory only when a map exists.
  - The keywords prompt is a content brief, not a repair batch.
  - MCP returns the same map text.
  - A real crawl carries the map.
- Shared chapter fixture regenerated with the `keyword-advisory` case. Python and TypeScript parity pass: web 51.
- Keywords chapter in isolated headless Edge: 9/9 checks, no console errors (status, contents label, quoted intent, no demand numbers, closed disclosure, print expansion and restore, fallback, 320/768 widths). Artifacts are in ignored `evals/results/keyword-map/`.
- Final full offline API: 1,104 passed, 19 existing PostgREST-dependent skips.

## Not built (later slices)

- Search Console measured mode (R-S16), and CTR, trend, near-page-one, brand/nonbrand and cannibalization analysis from real queries.
- An owner business brief (product, audience, conversion) to check intents against.
- Approved external research.
- Jev-assisted intent classification: it was not benchmarked, and the deterministic route covers this mode.
- Earned-link and citation opportunities (R-S17a).
