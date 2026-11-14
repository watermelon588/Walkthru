# Implementation Plan: Assemble (multi-cursor page rebuild component)

_Written 2026-11-11. Status: T0 to T9 built by 2026-11-13 (approach changed after T0, see "T0 spike result"); waiting on Checkpoint B. T10 to T14 and a Plus video export were added the same day. Left: T15 package README, and a real signed-in check of the live stage and the export. Working name "Assemble"; "Swarm" is avoided because it is both the reference extension's name and a competitor's._

## Overview

A standalone, framework-free component that blanks a page (or one region of it) and lets a crew of coloured multiplayer cursors rebuild it: dragging out boxes with size badges, typing text with a caret, drawing rules with a pen, pulling ruler guides, and alt-dragging duplicates of repeated rows. When it finishes the real content is back, pixel for pixel. It ships as one small script that works on any site (portfolio, Walkthru landing) and as the opening reveal of the in-app live-run stage.

## Reference research

Sources: `swarm-rebuild.mp4` (53 s, 1898x866, reviewed at 1 fps plus full-size stills), the Chrome Web Store listing, the installed extension's files (v1.1.0), and the project README.

### What the video shows

| Time | What happens |
|---|---|
| 0 to 1 s | Real page fades out to its own background colour. Cursors already drifting. Dark HUD pill at bottom centre: "Scanning page..." |
| 1 to 2 s | Blank canvas. Only the logo/avatar stays, small and centred. About 18 cursors gather round it in two tight flocks; dormant task spots show as small coloured crosses |
| 2 to 3 s | First tasks: crosshair cursors drag out grey placeholder boxes. Each has a 1px blue outline, four white corner handles and a blue size badge under it ("215 x 215"). The image box shows an image glyph, then the photo pops in. HUD now reads avatars, "11 agents", "0 / 191 layers", progress bar, Tour, 1x, sound, close |
| 3 to 7 s | Headline is typed letter by letter by several cursors at once (I-beam cursor, blinking caret, blue text frame). Wrong states appear on purpose: overlapping letters, red frames, then a fix. Button fills blue, then its label is typed |
| 7 to 11 s | Viewport is done, so work stops: HUD says "scroll to keep building", idle cursors wander. User switches 1x to 2x and turns sound on |
| 11 to 17 s | User scrolls. Work unlocks top down. Stat tiles: the first is built, then alt-dragged three times as red-outlined copies with red distance badges ("160", "265", "581"), then each copy's text is retyped to its real value |
| 17 to 21 s | Project rows: one master row built, duplicated down the list (red outlines, spacing badge "216"), images swapped, titles and paragraphs retyped. Agent count climbs 12 to 16 as scrolling speeds up |
| 22 to 36 s | Tour mode auto-scrolls. Dark rulers appear on the top and left edges with pixel ticks; red and dashed blue guides are dragged out of them and text snaps to the guide. Dividers are drawn with a pen cursor between two dots. Agents reach 25 |
| 37 to 41 s | Last section. HUD becomes "Rebuilt by 26 agents in 38.3s", with "Go live" and "Replay" |
| 41 to 49 s | All cursors form one flock that chases the real mouse like a school of fish |
| 49 to 52 s | Close: overlay goes, real page is there, unchanged |

### How the extension does it

- One dependency-free content script (about 3,800 lines, 150 KB) plus an 80-line background worker. Permissions: `activeTab`, `scripting`. Nothing leaves the browser.
- **Snapshot.** Walks the live DOM (including open shadow roots) and builds a blueprint: rectangles, text blocks, lines/borders, media, repeated-sibling groups (one master plus duplicates) and guide positions. A hidden scroll pass first wakes lazy content. Caps: 4,000 layers, 40,000 px tall.
- **Blank.** A fixed full-viewport layer inside a shadow root covers the page in the page's own background colour. The real page is untouched underneath.
- **Rebuild.** Each layer is a styled clone placed at its measured position and revealed in stages (grey box, then outline, then content; text by character count). Each cursor runs a small generator script per task (move, click, drag box, type, draw line, drag guide, duplicate). A scheduler unlocks tasks top down as the viewport reaches them; children wait for parents, duplicates wait for their master. Agents: 8 minimum, 48 maximum, scaled by backlog and scroll speed.
- **Chrome.** Cursors, selection outlines, badges, rulers and guides are one overlay layer. Sound is synthesised with Web Audio (no audio files), panned by cursor x position.
- **Pixels the DOM cannot give back** (WebGL canvas, playing video, cross-origin iframes) are cropped from a tab screenshot taken at click time. Only an extension can do that.

### Licence finding (blocks code reuse)

The repo (`DhvanilPatel/swarm-cursors`) has **no licence**; its README says "None yet" and that large parts of the engine are adapted from Joel Califa's Swarm site, which is also unlicensed. AGENTS.md forbids copying code from unlicensed repos. So this is a **clean-room build**: we use the observed behaviour and the general technique described above, and write every line ourselves. No code, constants tables, names list or sound patches are copied. The visual vocabulary (selection handles, size badges, rulers) is generic design-tool language, but our cursor shape, palette, HUD and sounds are our own.

## T0 spike result (2026-11-12): change of approach

Run with `node packages/assemble/spike/run.mjs <outDir> <url...>` at 1440x900, reduced motion, on the portfolio (`portfolio-web-six-psi-43.vercel.app`) and the Walkthru landing (`localhost:5173`).

| Approach | Site | Layers | Snapshot | Hero pixels wrong | Full page wrong |
|---|---|---|---|---|---|
| A. Styled clones in an overlay, curated property list | Portfolio | 195 | 304 ms | 14.9% | 7.8% |
| A. Styled clones, every computed property | Portfolio | 307 | 837 ms | 2.3% | 1.6% |
| A. Styled clones (either list) | Walkthru | 242 | 217 to 1,535 ms | 0.9% | 7.1% |
| **B. Reveal the real elements in place** | Portfolio | 1,076 | **27 ms** | **0%** | same as page vs itself |
| **B. Reveal the real elements in place** | Walkthru | 240 | **25 ms** | **0%** | **0%** |

- **Approach A fails** both acceptance bars. Flattening loses everything an ancestor contributes: stacking order (the portfolio photo sits between two text layers), blend modes (the nav vanished), clipping, transforms. It is also 4 to 30 times over the 50 ms budget because of style copying.
- **Approach B passes.** Nothing is cloned. One stylesheet hides tagged real elements with `visibility` (a revealed child inside a hidden parent shows, so every layer is independent), and the engine reveals them as cursors "build" them. Text is typed by clipping the real element to the caret position measured with a `Range`. The finished page is the real page, so it is right by construction; removing the attributes restores it exactly (0% difference after destroy). Canvas, video and iframes need no special case.
- Found for T1: (1) an element that both paints a box and holds text (buttons, pills) has its background clipped while typing, so those need box-then-text handling; (2) headlines split into per-word spans must be merged into one text layer at the nearest block ancestor; (3) elements at `opacity: 0` are counted as layers and should be skipped until the page shows them.
- Cost: hidden content leaves the accessibility tree for the few seconds of the rebuild. Reduced-motion users never get blanked, and the component is never used on load without a user action on the founder's sites.

Decisions 3, 4 and 9 below are rewritten to match.

## Architecture decisions

1. **Vanilla TypeScript, zero runtime dependencies, shipped as a custom element.** `<assemble-stage>` plus a programmatic `assemble(target, options)`. This is the only stack that drops into every site the founder has (React 19, plain HTML, anything else) with one script tag. A 15-line React wrapper lives in `apps/web`. Target size: under 25 KB gzipped.
2. **Own fixed-step simulation loop, not GSAP.** GSAP timelines fit choreography known in advance. Here hundreds of tasks are scheduled at run time, can be interrupted by scroll, change speed live (1x/2x/3x) and must replay deterministically. One `requestAnimationFrame` loop stepping generator-based agent scripts does that in a few hundred lines and keeps the package dependency-free. GSAP stays in use for the rest of the site.
3. **Reveal the real page in place, one canvas for chrome.** (Changed after T0.) Content is never cloned: real elements are tagged with a `data-asm` attribute, hidden by one injected stylesheet, and revealed as they are built; text is typed with `clip-path` on the real element. The grey placeholder boxes, cursors, outlines, badges, guides and rulers are drawn on a single DPR-aware `<canvas>` above the page. Short-lived clones are allowed only for alt-drag duplicate ghosts and for typing labels inside painted elements.
4. **Shadow root isolation for our own UI.** The canvas and HUD sit in a closed shadow root so host CSS cannot leak in or out. The only things added to the host page are the `data-asm` attributes, one `<style>` and a temporary inline `clip-path`, all removed on destroy.
5. **Two blueprint sources behind one type.**
   - `fromDOM(element)`: walks a live element. Used on the founder's own sites.
   - `fromFrame({ image, boxes })`: a screenshot plus element rectangles. Used on the in-app run stage, where the page is a JPEG and the rectangles come from the snapshot `inject.js` already produces. Boxes are drawn the same way; content is revealed by clipping the image per box. No text typing in this mode (we do not have the text as text), boxes and image regions only.
6. **Region or full page.** `target` can be `document.body` or any element, so it can wrap a hero mock, a report card or the stage.
7. **Seeded randomness.** One seed drives every random choice, so tests are deterministic and a replay is identical.
8. **Reduced motion and accessibility are in v1, not later.** Under `prefers-reduced-motion` the component does a 200 ms cross-fade and never blanks. During a rebuild the hidden content is out of the accessibility tree for a few seconds, so the canvas is `aria-hidden`, the HUD is a labelled toolbar that announces "Rebuilding page" and offers Skip, Esc always exits, and focus returns to where it was. Sound is off until the user turns it on.
9. **Canvas, video and iframes are ordinary layers.** (Changed after T0.) Because the real element is revealed, they need no screenshot and no placeholder.
10. **Lives in this repo as `packages/assemble/`**, built with Vite library mode (already installed) to one ESM file and one IIFE file. No npm publish until a second site needs a versioned copy; until then other sites load the built file.

## How it will look (design direction)

Everything is a token/option so each site keeps its own identity.

- **Cursors:** our own arrow (not Figma's), 1.5 px white stroke, soft shadow, name chip on hover only. Tool states: arrow, crosshair, I-beam, pen, hand. Movement is a critically damped spring toward the target with a slight arc and overshoot settle, so paths curve like a hand, never straight lines.
- **Palette:** an option. Default is a 10-hue set tuned for light and dark pages. In Walkthru the cursors use the test users' existing colours and the outline colour is `ink`, so no new accent is introduced.
- **Selection chrome:** 1 px outline, 6 px square handles, badge in monospace tabular numerals; duplicates use the secondary outline colour with a distance badge.
- **Typing:** variable rhythm (bursts and short pauses), caret blinks only when idle, occasional typo and backspace at a low rate (off in Walkthru product surfaces).
- **HUD:** one pill, bottom centre: stacked agent avatars, `N agents`, `built / total layers`, progress, Tour, speed, sound, close. End state: "Rebuilt by N agents in S s", Replay, Done.
- **Sound (optional):** soft synthesised ticks for typing and a low thock on placement, stereo-panned by cursor position, a two-note chord on completion. Written from scratch.
- **Finale:** boids flock (separation, alignment, cohesion) that follows the pointer for a few seconds, then cursors leave by the nearest edge.
- **Timing budget:** a normal viewport rebuilds in 6 to 9 s at 1x. A `duration` option compresses the whole run (the live stage uses about 2.5 s).

## Where Walkthru uses it

| Place | Mode | Notes |
|---|---|---|
| In-app live run stage (`SessionPlayer`, T9 of `docs/in-app-runner-plan.md`) | `fromFrame` | Plays once while the first frame of a session loads, about 2.5 s. The builder cursors then leave and the test user's cursor stays. From then on the cursor is the measured pointer only, as decision 4 of the runner plan requires. The rebuild is presentation; step data is never invented |
| Landing hero or a "watch it work" block | `fromDOM` on a region | Plays once when scrolled into view, Replay button, never loops |
| Founder's portfolio and other sites | `fromDOM` on `body` | Script tag plus a trigger button or key |

Two things need the founder's sign-off because they touch DESIGN.md: this is a new motion pattern (DESIGN.md lists the approved loops and says not to add others), and it shows several cursor colours at once. Proposal: it is a one-shot reveal, not a loop, and colours come from test users. DESIGN.md gets a short section when Phase 4 lands.

## Public API (target)

```ts
assemble(target: Element, {
  source?: 'dom' | { image: string; boxes: Box[] },
  agents?: number | { min: number; max: number },
  palette?: string[], names?: string[],
  speed?: 1 | 2 | 3, duration?: number, seed?: number,
  scroll?: 'follow' | 'tour' | 'none',
  hud?: boolean, sound?: boolean, rulers?: boolean, typos?: boolean,
  onProgress?(built: number, total: number): void, onDone?(): void,
}): { replay(): void; setSpeed(n): void; destroy(): void }
```

## Task list

Sizes: S = 1 to 2 files, M = 3 to 5 files. Each task leaves `packages/assemble` building, with `node --test` green and oxlint at 0 warnings.

### Phase 0: Spike (fail fast)

- [x] **T0. Fidelity spike.** Done 2026-11-12, see "T0 spike result". Clone approach rejected, reveal-in-place adopted: 0% hero difference on both sites, snapshot 25 to 27 ms for 240 and 1,076 layers. Spike files in `packages/assemble/spike/` are throwaway and go when T1 lands.

### Phase 1: Engine core

**Phase 1 status (2026-11-12): T1 to T4 built, waiting on Checkpoint A.** `packages/assemble/` (`src/blueprint.ts`, `stage.ts`, `sim.ts`, `chrome.ts`, `index.ts`), 5.4 KB gzipped, no dependencies. Checks: `npm test` (6 scheduler tests), `npm run build && npm run test:browser -- <url...>` (headless Chrome: fixture layers, 0% pixel difference after a run on the fixture, the portfolio and the Walkthru landing, nothing left on the page, same seed gives the same event log, 2x speed gives 0.5x frames), `npm run typecheck`, `npm run lint`. Simulation cost is 0.4 to 2 ms per frame in headless Chrome; frame rate on a real screen has not been profiled yet. `node test/record.mjs <out.mp4> <url> [seconds] [speed]` records a frame-exact video. Differences from the task text below: the hide stylesheet and tags are applied once (no `MutationObserver` yet); boxes larger than half the viewport are shown at once instead of being drawn; the spike folder is deleted. Known rough edges: a visually hidden skip link flashes when it is "built"; a 900-layer page takes minutes at 1x until repeated groups (T6) and agent scaling (T8) land; reduced motion currently skips the effect entirely (the cross-fade is T10).

**Phases 2 and 3 status (2026-11-13): T5 to T9 built, waiting on Checkpoint B.** Bundle is 9.6 KB gzipped. Added: pen lines for dividers and one-sided borders (T5); repeated siblings (3 or more alike in a row) built once then alt-dragged as copies, with only their text retyped (T6); edge rulers and up to three guides at shared left edges (T7); `scroll: 'follow' | 'tour' | 'none'`, more agents with a bigger backlog or faster scrolling, "scroll to keep building" hint (T8); HUD pill with agent avatars, counts, progress, Tour, speed, close, and an end state "Rebuilt by N agents in S s" with Replay and Done (T9). Tour pans continuously while nothing in view is waiting. Elements faded out below the fold (scroll reveals, including the opacity plus visibility pair GSAP uses) are now built instead of skipped. Checks: 8 unit tests; browser tests cover line and copy detection, follow-mode waiting, tour to the end, HUD summary, Replay, close mid-run, and 0% pixel difference on the fixture, portfolio and landing. Recordings: full landing (279 layers) in about 45 s at 1x, full portfolio (810 layers) in about 38 s at 2x. Differences from the task text: a copy in flight is an outline with a distance badge, not a picture of the original (no cloning); text does not visibly snap to guides; the shadow root is open so tests can reach the HUD; HUD has no sound button until T11. Not done: frame-rate profiling on a real screen, Firefox and Safari, phone widths, real mouse and keyboard use of the HUD (only scripted clicks were tested).

**Live-run stage (2026-11-13): image mode built and hooked into `SessionPlayer`, ahead of T10 to T13 at the founder's request.** This is T12's screenshot source and T14, done differently from the plan: no element rectangles are needed from the runner. `regions.ts` finds the content blocks in the saved frame itself (background colour, then recursive cuts along the widest empty rows and columns; a coloured band is placed first and its contents found against its own colour; capped at 48 blocks). `assembleImage(host, src)` lays those blocks out as tiles over a blank layer inside the stage and runs the normal engine on them: sparse blocks are typed in line by line, solid ones are drawn as boxes, cursors stay inside the stage (`bounds`). When it ends the layer is removed and the player's own `<img>` is underneath, untouched. In `SessionPlayer` it plays once each time a frame for a new page address arrives (not on scrolls or later views of the same page), under the test user's cursor, which still moves only to measured points. Reduced motion skips it. If the frame's pixels cannot be read (no CORS header) it falls back to a 4 by 3 grid of tiles. `apps/web` imports the package source through a Vite alias (`assemble`), so there is still no new dependency. Checks: 4 region tests, an image-mode browser test (blocks found, nothing outside the stage touched, stage identical afterwards), web build, lint and 65 web tests. A recording of image mode on a landing-page screenshot takes about 4 s. Not done: it has not been watched on a real signed-in live run (the in-app browser is not signed in), and DESIGN.md has no entry for it yet (open question 3).

**T10 to T13 and the video export (2026-11-13).** Bundle 12.5 KB gzipped.
- Founder requests: cursors are 1.3 times larger (`cursorScale`); they are called "scouts" in the pill (`noun`).
- T10: after the summary, on a whole-page run, the scouts return as a flock that follows the mouse until Done or Esc (steer to a spot round the pointer, keep apart from neighbours, arrows turn to face their heading). Reduced motion: the effect is skipped entirely; the planned cross-fade was dropped because the page is already on screen and there is nothing to fade between.
- T11: `sound.ts`, synthesised with Web Audio (keystroke ticks, a low thump when something lands, a soft note for pen strokes, two notes at the end), panned by position, off until the pill's Sound button is pressed.
- T12: `<assemble-stage>` custom element (`auto`, `src`, `speed`, `seed`, `sound` attributes, `.play()`), defined automatically when the bundle loads. Image mode was already done for the live stage.
- T13: `apps/web/src/components/ScoutsRebuild.tsx` wraps a picture and plays image mode once when it is on screen, with a Replay button. Used on the landing hero's dashboard picture.
- Video export (new, Plus): `lib/sessionVideo.ts` and `components/SessionVideoExport.tsx`. Under "Watch the visit again" in a report, Plus accounts get "Export video": the saved frames, the measured cursor and click ring, what the test user said, a "Tested with Walkthru" badge and the owner's brand name badge when report branding is set, drawn to a 1280x720 canvas and recorded with MediaRecorder. MP4 where the browser records it (current Chrome, Edge, Safari), WebM otherwise. Made in the browser, nothing uploaded, no dependency. It records in real time. Other plans see a line pointing to billing; signed-out share pages see nothing. The gate is in the page, not the API (the frames are the user's own either way).
- Checks: package 12 unit tests plus browser tests for the flock, the Sound button and the custom element; web build, lint and 69 tests (4 new for the storyboard, wrapping, format choice and file name). Seen in the in-app browser: the landing hero rebuild, and a real 9.7 s MP4 produced by the exporter from sample frames. Not seen: the Export video button on a real Plus report (the in-app browser is not signed in), sound by ear, Firefox, Safari, phones.

- [ ] **T1. Package and blueprint type.** `packages/assemble/` with Vite library build, `Blueprint` types, `fromDOM` (rects, text blocks merged at the nearest block ancestor, painted boxes, lines, media, skip rules for hidden, zero-size and `opacity: 0` nodes, caps). M.
  - Accept: unit tests on fixture HTML give the expected layers, order and parent links; a per-word-span headline is one text layer; a button is a box layer plus a label.
- [ ] **T2. Stage and reveal.** Hide stylesheet and `data-asm` tagging, per-layer reveal states (hidden, placeholder box on the canvas, shown, text by character via `clip-path`), label typing inside painted elements. M.
  - Accept: revealing every layer by hand gives 0% pixel difference from the untouched page on both spike sites; destroy restores scroll, focus, attributes and inline styles exactly.
- [ ] **T3. Simulation loop and scheduler.** Seeded RNG, fixed-step loop, task queue with top-down unlocking, parent-before-child, agent count scaling with backlog. S.
  - Accept: same seed gives the same event log in tests; no task starts before its parent; speed 2x halves wall time within 5%.
- [ ] **T4. Cursors and two tools.** Canvas chrome layer, spring-driven cursor movement, `drawBox` (crosshair, outline, handles, size badge) and `typeText` (I-beam, caret, rhythm). M.
  - Accept: the portfolio hero rebuilds end to end in the browser at 60 fps with 16 agents (checked in the performance panel, no long frames over 16 ms on the dev laptop).

### Checkpoint A

- [ ] Founder watches the hero rebuild on the portfolio and on the Walkthru landing and approves the cursor, outline and typing feel before more tools are added.

### Phase 2: Full tool set

- [ ] **T5. Pen lines and media.** Dividers and borders drawn between two points; image box with glyph, then the image; placeholders for canvas, video, iframes. S.
- [ ] **T6. Repeated groups.** Detect repeated siblings, build one master, alt-drag duplicates with distance badges, then retype the differing text and swap media. M.
  - Accept: a list of 5 similar rows produces 1 build and 4 duplicate tasks; a list of unlike rows produces none.
- [ ] **T7. Rulers and guides.** Edge rulers, guides dragged out at shared left edges, text snapping to a guide. S.
- [ ] **T8. Scroll modes.** `follow` (work unlocks as the user scrolls, faster scroll calls more agents, idle wander when the viewport is done), `tour` (auto-scroll at build pace), `none` (region mode). S.

### Phase 3: Finish

- [ ] **T9. HUD and controls.** Pill with counts, progress, Tour, speed, sound, close; end state with Replay and Done; Esc exits; keyboard reachable with visible focus. S.
- [ ] **T10. Finale and reduced motion.** Pointer-following flock, edge exit; reduced-motion path (cross-fade only); visibility pause when the tab is hidden. S.
- [ ] **T11. Sound.** Web Audio synth for type, place, snap and finish, panned, off by default, created only after a user gesture. S.
- [ ] **T12. Custom element and `fromFrame`.** `<assemble-stage>` wrapper with attributes mapped to options; image-plus-boxes source with clipped reveal. S.

### Checkpoint B

- [ ] Full run on the portfolio matches the reference beat for beat (scan, logo gather, boxes, typing, duplicates, guides, HUD end state, flock), in Chrome, Edge, Firefox and Safari-class WebKit, plus a phone-width check.
- [ ] Bundle under 25 KB gzipped, no runtime dependencies.

### Phase 4: Walkthru integration

- [ ] **T13. React wrapper and landing block.** `components/Assemble.tsx`; one-shot play on scroll into view on the landing page, tokens for palette and outline. S.
- [ ] **T14. Live-run stage reveal.** Hook `fromFrame` into `SessionPlayer` for the first frame of a session. Depends on T5 and T9 of the runner plan (per-step frames, element rectangles, the player). S.
- [ ] **T15. Docs.** DESIGN.md section, `packages/assemble/README.md` with the script-tag snippet, CURRENT_STATE.md. S.

### Checkpoint: complete

- [ ] `npm run build` and `npm run lint` green in `apps/web`; package tests green; founder approves the landing block and the stage reveal.

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| The page re-renders or animates while it is being rebuilt (React updates, marquees, scroll reveals) | Medium | Layers are re-measured when they are picked up, not only at snapshot; tags are re-applied through one `MutationObserver`; a removed element just drops its task |
| The host page already uses `visibility` or `clip-path` on a layer | Low | Previous inline values are saved and restored; our rule only matches our own attribute |
| Jank on long pages | Medium | Only build layers near the viewport; one canvas for chrome; transform, opacity and clip-path only; layer and height caps |
| Reads as a copy of the extension | Medium | Clean-room code, own cursor, palette, HUD, sounds and naming; no shared assets or text |
| Decorative cursors in a product that sells honest evidence | Medium | In the live stage it plays once as a loading reveal, is visually distinct from the test user's cursor, and never appears in reports or replays of steps |
| The live-stage hook depends on the cloud runner, which is not built | Low | Phases 0 to 3 and T13 do not depend on it; T14 waits |
| Motion sickness, focus traps | Medium | Reduced-motion path, Esc, `aria-hidden` overlay, real DOM stays accessible |

## Order and size

T0, then T1 to T4, checkpoint A, T5 to T8 (T5, T7 and T8 are independent of each other), T9 to T12, checkpoint B, then T13 and T15; T14 when the runner's player exists. Rough size: Phase 0 half a day, Phase 1 two days, Phase 2 two days, Phase 3 one and a half days, Phase 4 one day without T14.

## Open questions for the founder

1. **Name.** "Assemble" is a placeholder. Any preference?
2. **Home.** `packages/assemble/` inside this repo (proposed), or its own repo from day one so the portfolio can pull it without touching Walkthru?
3. **Design rule change.** OK to add this as a one-shot reveal in DESIGN.md, with cursor colours taken from test users?
4. **Live stage.** Agree that the rebuild is only the opening reveal and that step cursors stay measured?
5. **Sound and typos.** Keep both for the portfolio and off inside Walkthru?
