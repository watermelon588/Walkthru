# Variant 1: Fresh Eyes

Preview: `/variants?v=fresh` (switcher at the bottom of the page). Source: `apps/web/src/variants/FreshEyes.tsx`, `fresh.css`.

## The idea

Walkthru sells a stranger's point of view. Fresh Eyes makes that literal: the page is a zine made by curious people, built from the doodle library (faces, a long-legged walking cat, a skateboarding bird, a one-eyed black bird). It is loud, warm and a little funny, and it treats a dry category (QA, SEO, security) as something approachable. The product proof (real report captures, real checks) sits inside that playful frame, so it never feels like a toy.

**Vibe:** indie zine, sticker wall, a friend's sketchbook. Confident, hand-made, never corporate.
**Who it flatters:** indie developers and small teams who ship fast and hate enterprise tone.

## Design principles

1. **Doodles carry the identity, the product carries the proof.** Every illustrative moment is a supplied doodle; every claim is backed by a real capture or the real check list.
2. **Two colors, used as blocks.** Cobalt and lemon appear as whole surfaces (cards, a full section, the closing band), not as thin accents. Paper is the rest.
3. **Things feel physical.** Stickers have die-cut white borders and drop onto the page, buttons have a hard bottom edge and press down, polaroids can be picked up and moved.
4. **One idea per section, one layout family per section.** Sticker hero, tilted marquee band, horizontal pan, chat thread, sticky stack, draggable table, bento, tickets, accordion, closing band. No two sections share a layout.
5. **Plain words.** Headlines from the existing copy, shortened only where the type needed it.

## Typography

| Role | Face | Settings |
| --- | --- | --- |
| Display (hero, closing, prices) | Bricolage Grotesque (Google Fonts, variable) | weight 780, `opsz` 96, `wdth` 88, tracking -0.032em, leading 0.9 |
| Section titles | Bricolage Grotesque | weight 750, `opsz` 72, `wdth` 88, tracking -0.035em, leading 0.95 |
| Body, buttons, labels | Geist Variable (already in the app) | 400 to 600 |
| Run actions, step numbers | Geist Mono | 12 to 14px |

Scale: hero `clamp(3.2rem, 8vw, 7.6rem)`, section titles `clamp(2.4rem, 5vw, 4.5rem)`, body 18 to 20px in the hero, 16px elsewhere. Bricolage's optical-size axis keeps the heavy display cut crisp at big sizes and readable at card sizes.

## Color palette

| Token | Hex | Role |
| --- | --- | --- |
| `--fx-paper` | `#f3f0e6` | Page background (matches the doodles' paper) |
| `--fx-paper-2` | `#e9e4d6` | Pricing band, hover fills, track of the steps bar |
| `--fx-ink` | `#15151c` | Text, borders (2px everywhere), footer |
| `--fx-muted` | `#575763` | Secondary text (AA on paper) |
| `--fx-cobalt` | `#2342e8` | Primary block color, primary button, run section |
| `--fx-cobalt-deep` | `#1a31b8` | Button edge, chips on cobalt |
| `--fx-lemon` | `#ffe14d` | Secondary block color, nav CTA, highlight bubble, closing band |

Contrast: white on cobalt 7.0:1, ink on lemon 14:1, muted on paper 6.2:1.

## Shape and material

- Pills for every interactive control; 2rem radius for cards and sections; stickers 1.1rem outer, 0.7rem inner.
- 2px ink borders are the line weight of the page (nav, inputs, cards, accordion).
- Shadows are cobalt-tinted, never grey (`0 22px 40px -18px rgb(26 49 184 / 0.45)`).
- Buttons have a solid 4px bottom edge in a darker shade and drop 2px on press.

## Assets

From `apps/web/design/source-images` (copied to `apps/web/public/variants/fresh/`, originals untouched):

| File | Used for |
| --- | --- |
| `faces-cobalt.jpg` (doodles/5ad38434) | Hero sticker |
| `cat-walk.jpg` (doodles/1d7e5f42) | Hero sticker |
| `people.jpg` (doodles/18230a5b) | Hero sticker |
| `rooster.jpg` (doodles/9d62b6a5) | Hero sticker |
| `laptop.jpg`, `objects.jpg`, `trip.jpg` (doodles) and `scout.jpg` (illustration/7c196a8e) | One per step card |
| `cry.jpg` (doodles/f7cd6138) | The run section, pops in when the user gives up |
| `faces-bw.jpg` (doodles/c040a8bf) | Safety bento background |
| `skate-bird.jpg` (doodles/7f0ab3de) | Rolls across the closing band |
| `heads.jpg` (doodles/cfe6228d) | Copied for later use, not on the page yet |

From the live site: the four real report captures and the five persona photos (shown as lemon or cobalt duotones), plus the Walkthru mark.

## Page structure

1. **Nav**: floating pill bar, paper with blur, lemon "Scan my site".
2. **Hero**: headline with a hand-drawn lemon squiggle under "Fresh eyes", 17-word subline, inline scan form, link to the sample report. Right: four doodle stickers on a table.
3. **Checks band**: the 21 real checks as sticker chips on a lemon strip tilted -2deg (the page's only marquee).
4. **How it works**: pinned; scrolling moves four big cards (cobalt and lemon alternate) sideways, a progress bar fills underneath.
5. **Hear a stranger think**: full cobalt section, pinned; the quickinvoice run plays as a chat thread, the last bubble turns lemon and the crying face pops in.
6. **Report**: four cards in a real sticky stack (white, lemon, cobalt, paper), each with a real capture.
7. **Test users**: five duotone polaroids scattered on a table; drag them around on desktop, swipe them on phones.
8. **Safety**: bento of five cells (one big ink cell with the headline, four colored cells).
9. **Pricing**: four tickets, Pro in cobalt with a lemon button.
10. **FAQ**: bordered accordion, the plus turns lemon and rotates when open.
11. **Closing**: full lemon band, giant headline, scan form, skateboarding bird rolls in.
12. **Footer**: ink.

## Motion

Every animation has a job; all of it is skipped under `prefers-reduced-motion` (the page is fully readable static).

| Moment | What moves | Why |
| --- | --- | --- |
| Page scroll | GSAP ScrollSmoother, `smooth: 1.2`; hero stickers get `data-speed` parallax | Weight and depth; the page feels like paper sliding |
| Hero load | Words rise with a springy `back.out`, squiggle draws, stickers drop in with `elastic.out` | Sets the playful tone in the first second |
| Pointer | Stickers follow the cursor at different depths (`quickTo`) | The table feels physical |
| Steps | Pinned horizontal pan, bar fills with progress | Four steps read as one journey |
| Run thread | Pinned, scrubbed: action chip slides in, bubble pops from its tail | The core story: you watch a stranger get stuck |
| Report | Sticky stack: each card shrinks and tilts as the next lands | One report, many layers |
| Polaroids | GSAP Draggable, tilt follows drag speed | Invites play with the five test users |
| Closing | Bird skates across with scroll | A last smile before the CTA |
| Buttons | 2px press, tickets lift and tilt on hover | Tactile feedback |

## If this became the whole product

- App shell on paper with a 2px ink sidebar border, pills for navigation, cobalt for the primary action.
- Findings as cards with a colored edge (lemon for medium, cobalt for info, a third red reserved for high severity only).
- Doodles for empty states and onboarding; real captures stay untouched inside report views.
- Risk: loud color blocks can tire on dense data screens. Keep the dashboard mostly paper and ink, color for status and moments.

## Notes

- Fonts load from Google Fonts for the preview; self-host with `@font-face` before production.
- New libraries: none. GSAP ScrollSmoother, SplitText and Draggable ship in the `gsap` package already installed (all free since GSAP 3.13).
- The scan form is live: it runs the real Instant Scan, same as the current home page.
