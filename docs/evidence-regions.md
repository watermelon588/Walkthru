# Truthful visual evidence (R-S19)

Implemented locally 2026-10-07. Code:

- **Extension:** `issueRegions()` in `apps/extension/lib/snapshot.ts`; the `evidence_capture` reply in `entrypoints/inject.ts`; the `regions` argument in `lib/evidence.ts` and `sidepanel/run.ts`.
- **API:** `EvidenceRegion` and `StepEvidence.regions` in `apps/api/app/agent/schema.py`, with evidence stored without defaults in `main.py`.
- **Web:** `RegionOverlay` and the frame labels in `apps/web/src/components/EvidenceTimeline.tsx`.

No migration, dependency, permission or new storage.

## Issue locations on real frames

When a step's screenshot is taken, the content script first switches on capture mode, which masks form values as before. It then measures, in that same document, the **visible error messages**: the same selector the observation already uses for `errors` (`role="alert"`, `aria-invalid`, assertive live regions, error and invalid classes).

Each one in the viewport becomes a box in **fractions of the captured viewport**, clipped to it: `{kind: "error", x, y, w, h}`. Rules:

- at most 10 boxes, duplicates once;
- off-screen, hidden or empty elements are left out;
- **boxes only, no text**, so a shared report never gains page content from them.

The screenshot follows immediately. Measuring and capturing are not one atomic browser call, so a page that changes within those milliseconds could shift. The caption says the boxes were "measured in this frame just before capture".

The API accepts only boxes that lie inside the frame (`x + w`, `y + h` ≤ 1). Unknown fields such as a text label are refused, and so are more than 10 boxes. Evidence without boxes is stored exactly as before.

Boxes are **drawn over** the frame, never into it. The stored JPEG is unchanged, so redaction is intact and the boxes can be turned off. The overlay is an SVG whose viewBox is the captured viewport size. `preserveAspectRatio="xMidYMid meet"` centres it exactly like the image's `object-contain`, so each box lands where it was measured at any width, on screen and in print.

**Show error locations** toggles them, and the caption counts them: "1 visible error message marked". The image alt text in print includes the count. The boxes use the danger token and do not animate.

## Not a recording

- The replay header says: "N screenshots captured at the moments shown, not a continuous recording."
- Each frame shows its capture time and its offset from the first frame (for example "+12 s").
- Print says the frames "are not a continuous recording" and explains the red boxes.
- Play steps through frames on demand, at most 8 per run (`MAX_SCREENSHOTS`).

There is no video, no clip export and no tab recording.

## Access, retention and size

- Boxes live inside the step's `evidence` record.
- The 30-day purge strips the whole `evidence` record (`retention.strip_evidence`), so the boxes go with the screenshot.
- Expired or unloadable frames show "Screenshot unavailable" and draw no boxes.
- Images stay in the private `run-evidence` bucket behind short-lived signed links, exactly as before. The boxes are a few numbers per frame, with no new storage or egress.

## Treatments and before/after

No suggested fix is drawn on a frame. A before/after claim needs the R-S13 matched rerun ("Since your last run"); the replay never presents one frame as proof of a fix.

## Verification (2026-10-07)

- **Extension** (`tests/regions.test.ts`, 3 tests): fractions and clipping, with off-screen, hidden and empty elements left out and no text included; at most 10 boxes, duplicates once; the saved evidence carries the boxes for that capture, and evidence without boxes has no `regions` key. Full extension suite: 177 passed/1 opt-in skip, tsc, lint and the WXT build.
- **API:** `test_evidence_regions_are_kept_with_their_frame_and_refused_outside_it` (round trip through `/observe`; a box outside the frame and a text label both get 422) and `test_purging_a_frame_also_drops_its_error_boxes`. The existing evidence round-trip test still passes unchanged (no `regions` key when none were measured).
- **Real layout:** the extension's own `issueRegions()` ran in Edge on a scrolled page. Viewport screenshots (what `captureVisibleTab` saves) at 1280×800 @1×, @2× and 390×844 @3× showed every predicted box covering the error's red pixels, and off-screen errors left out.
- **Web:** the actual `EvidenceTimeline` in isolated headless Edge with a synthetic 1440×900 frame passed 14/14 checks with no console errors:
  - the box within 1.5 px of the measured spot, on screen, in print and at 320/768 px;
  - the count, toggle and "over, not into" wording, and the toggle hiding boxes while keeping the frame;
  - the "not a continuous recording" labels and the +0 s / +12 s offsets;
  - the danger token;
  - a frame without boxes shows no toggle;
  - expired evidence draws no boxes;
  - no overflow.

  Web 52 tests, tsc, build and lint passed. Artifacts are in ignored `evals/results/evidence-regions/`.

## Not built

- **Clip or video export** of the frames: it needs a media encoder dependency or new permission, so it is a later, licence-reviewed sub-session.
- **Highlighting the acted-on element:** the frame is taken after the action, so that element may no longer be there. It needs a before-action capture, which costs a frame from the cap of 8.
- **Boxes for other issue kinds:** accessibility nodes and layout shifts need their own same-frame measurement.
- **A real installed-extension run** that inspects a stored frame from a live site.
