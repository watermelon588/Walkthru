# Implementation Plan: Assemble (multi-cursor page rebuild component)

_Written 2026-11-11. Status: plan only, nothing built. Waiting for the founder's go-ahead. Working name "Assemble"; "Swarm" is avoided because it is both the reference extension's name and a competitor's._

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

## Architecture decisions

1. **Vanilla TypeScript, zero runtime dependencies, shipped as a custom element.** `<assemble-stage>` plus a programmatic `assemble(target, options)`. This is the only stack that drops into every site the founder has (React 19, plain HTML, anything else) with one script tag. A 15-line React wrapper lives in `apps/web`. Target size: under 25 KB gzipped.
2. **Own fixed-step simulation loop, not GSAP.** GSAP timelines fit choreography known in advance. Here hundreds of tasks are scheduled at run time, can be interrupted by scroll, change speed live (1x/2x/3x) and must replay deterministically. One `requestAnimationFrame` loop stepping generator-based agent scripts does that in a few hundred lines and keeps the package dependency-free. GSAP stays in use for the rest of the site.
3. **DOM clones for content, one canvas for chrome.** Content layers are positioned clones with computed styles inlined, so text stays crisp and uses the site's real fonts; reveal uses `opacity`, `clip-path` and text slicing only. Cursors, outlines, badges, guides and rulers are drawn on a single DPR-aware `<canvas>` (up to 48 moving cursors with trails is cheaper there than 48 DOM nodes plus hundreds of outline nodes).
4. **Shadow root isolation.** All of it sits in a closed shadow root so host CSS cannot leak in or out.
5. **Two blueprint sources behind one type.**
   - `fromDOM(element)`: walks a live element. Used on the founder's own sites.
   - `fromFrame({ image, boxes })`: a screenshot plus element rectangles. Used on the in-app run stage, where the page is a JPEG and the rectangles come from the snapshot `inject.js` already produces. Boxes are drawn the same way; content is revealed by clipping the image per box. No text typing in this mode (we do not have the text as text), boxes and image regions only.
6. **Region or full page.** `target` can be `document.body` or any element, so it can wrap a hero mock, a report card or the stage.
7. **Seeded randomness.** One seed drives every random choice, so tests are deterministic and a replay is identical.
8. **Reduced motion and accessibility are in v1, not later.** Under `prefers-reduced-motion` the component does a 200 ms cross-fade and never blanks. The real DOM stays in the accessibility tree the whole time (the overlay is `aria-hidden`, the HUD is a labelled toolbar, Esc always exits, focus returns to where it was). Sound is off until the user turns it on.
9. **Skip what the DOM cannot give back.** Canvas, video and cross-origin iframes are shown as a placeholder box that cross-fades to the live element at the end. No screenshot API in a plain page, and we do not add one.
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

- [ ] **T0. Clone fidelity spike.** A throwaway page that snapshots the portfolio hero and the Walkthru landing hero, hides the original and shows the clones.
  - Accept: side-by-side screenshots differ by under 1% of pixels on both; web fonts, gradients, SVG icons and `object-fit` images hold; snapshot of a 200-layer page takes under 50 ms.
  - If it fails on some element type, that type becomes a placeholder box (decision 9), not a reason to stop.

### Phase 1: Engine core

- [ ] **T1. Package and blueprint type.** `packages/assemble/` with Vite library build, `Blueprint` types, `fromDOM` (rects, text blocks, lines, media, skip rules, caps). M.
  - Accept: unit tests on fixture HTML give the expected layers, order and parent links; hidden and zero-size nodes are skipped.
- [ ] **T2. Stage and reveal.** Shadow-root overlay in the page background colour, mounted clones, per-layer reveal states (empty, box, content, text by character). M.
  - Accept: stepping every layer to "content" by hand reproduces the page; destroy restores scroll, focus and the DOM exactly.
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
| Clones do not match the page (pseudo-elements, complex CSS, web components) | High | T0 spike first; inline computed styles including `::before`/`::after`; anything unsupported becomes a placeholder that cross-fades to the real element at the end, so the final frame is always right |
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
