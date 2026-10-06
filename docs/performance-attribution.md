# Performance attribution contract (R-S18)

Completed implementation: 2026-10-06. Scope: the existing mobile PageSpeed Insights request and saved `site_audit.mobile_vitals` report JSON. No migration, dependency, additional provider request or model call.

## Measurement sources

- `source=pagespeed_insights`, `device=mobile`, `retrieved_at`, `analysis_at` and `request_duration_ms` describe the request and receipt. Receipt time is not the field collection date.
- `lab.source=lighthouse_lab` describes one synthetic run, with requested/final URL, Lighthouse version, fetch time, reported emulated device, throttling method/settings and total lab duration. Lab LCP, CLS, FCP, TBT and Speed Index live under `lab.metrics`. A runtime error invalidates lab score/metrics/audits; an individual audit error invalidates its metric and cannot support a resource fix.
- The existing top-level `lcp_ms`, `cls` and `inp_ms` remain CrUX population p75 values from `loadingExperience`, separate from lab metrics. `field_source=crux_p75`, `field_url`, `field_scope=url|origin` and `field_status=complete|partial|unavailable` explain coverage. An origin ID on a requested inner page is labelled as origin evidence. `originLoadingExperience` is never silently substituted for missing URL metrics. Missing metrics remain null; a good lab score does not establish healthy field vitals.
- Journey `diagnostics.web_vitals` remain observations during a single browser visit, with the diagnostic capture time. They are not population p75, lab results, finalized whole-visit measurements or resource attribution. No new DOM capture is added.

Legacy reports with only the six previous summary fields remain readable. Their absent lab context is explicitly unknown. `checks.performance=complete` still means some measurement was available within scope, not complete field coverage or an application performance certificate.

## Bounded audit evidence

Read at most 100 performance-category audit references plus known core metric and older attribution IDs. Current Lighthouse `metricSavings`, legacy opportunity tables and nested checklist/subitem tables are supported. Retain at most 12 relevant audits and five unique resource/element rows per audit; each details walk visits at most 80 containers and five nesting levels, and each list examines at most 40 items. Attribution-bearing audits are retained ahead of metric/pass rows. `audits_omitted` counts additional parsed relevant audits; `resources_truncated` flags omitted details. This is a bounded sample, not a complete Lighthouse report.

Audit fields include ID/title/description/display value, score/mode, numeric value/unit, bounded run warnings, explicit errors, estimated opportunity milliseconds/bytes and estimated LCP/FCP/TBT metric savings. Resource rows keep URL and/or CSS selector plus permitted timing/transfer numbers. Node HTML, snippets, node text, screenshots, private values and arbitrary trace payloads are excluded. Text/locators use the existing 160-character public-context masking; URLs drop credentials, query strings and fragments. This can shorten a locator and does not establish causal certainty.

Opportunity savings are estimates, not measured speed or conversion gains, and must not be summed as independent gains. Fixes point to a retained failing/opportunity audit and its measured resource/element, followed by a comparable rerun. Without attribution the fix explicitly calls for inspection, rather than inventing an image optimization. Both full and chat fix prompts bypass the generic `perf.*` image recipe for new PSI/CrUX findings. Legacy recipes remain compatible. CSV and MCP use the same finding details/fix/evidence; raw account/report JSON retains the additive measurements.

## Report display

The shared private/public/team report body shows measurements in the Performance chapter. It separates lab from field p75, shows partial/unavailable coverage and measurement context, and offers a keyboard-accessible native disclosure for retained audits/resources. The existing PDF path expands this disclosure then restores it. Browser journey diagnostics label their separate source. All layout uses existing tokens; no motion or new accent is introduced.

## Primary signatures checked

Reviewed read-only on 2026-10-06:

- [PageSpeed v5 runPagespeed response](https://developers.google.com/speed/docs/insights/v5/reference/pagespeedapi/runpagespeed): Lighthouse audit map, auditRefs, URLs, timestamps, config settings and separate loading/origin experiences.
- [PSI lab and field interpretation](https://developers.google.com/speed/docs/insights/v5/about): CrUX p75, trailing 28-day population collection, unavailable samples and lab variability.
- [Current Lighthouse audit result types](https://github.com/GoogleChrome/lighthouse/blob/main/types/lhr/audit-result.d.ts): score modes, explicit errors and estimated `metricSavings`.
- [Current Lighthouse settings types](https://github.com/GoogleChrome/lighthouse/blob/main/types/lhr/settings.d.ts): form factor and reported throttling fields/units.

No upstream source code was copied. Existing HTTPX/free-quota integration remains in place. Without `PAGESPEED_API_KEY`, or when PSI does not provide field data, coverage stays unavailable. Direct CrUX integration and live provider connectivity are separate prerequisites, not activated by this slice.

## Verification

- Final dedicated performance attribution suite: **18 passed**, including PSI v5 and current Lighthouse metricSavings, partial/absent field data, audit/runtime errors, nested detail bounds, public-value masking and full/chat fix-prompt resource parity. Initial wider performance/browser/trust suite: **42 passed** before the final additional prompt/error regressions.
- Web: **51 tests passed**, including the concurrent assertion tests; TypeScript/Vite production build and zero-warning lint passed. Existing bundle/dynamic-import warnings remain.
- Actual isolated headless Edge: **84/84 checks passed**, zero console errors/warnings. Lab-only, partial field, unavailable and legacy reports; owner/public controls; 320/768/1440 widths; keyboard audit disclosure; print expansion/restoration; resource/element and numeric audit values; bounded lab warnings; estimate labels and absent-field honesty. Mobile/desktop screenshots inspected.
- Final current affected performance/scan/browser/report/trust/chapter/contract/fix-prompt/MCP suite: **112 passed**, one existing warning, exit 0 in 41.03 seconds. Whole API Ruff passed.
- Broad offline runs: first **963 passed, 19 existing PostgREST skipped, one shared chapter fixture failure** (394.39 s); second **972 passed, 19 existing skips, the same fixture failure** (386.14 s). The coordinated R-S6 owner added report defaults and then an assertion fixture case while those runs held earlier imported source, so the shared fixture snapshot changed during verification. Final fresh consumer selection above includes the current chapter fixture and passes. Neither broad run is claimed as fully green, and neither failure was excluded. A full release run against a stable combined R-S6/R-S18 snapshot remains a later gate. Superseded duplicate focused runs were stopped; all test/browser helpers started by this R-S18 session have exited.

Ignored local artifacts: `evals/results/restructure-session-18/`. Hosted/live-provider/native-installed-extension acceptance remains separate. This slice does not certify causation or deployment.
