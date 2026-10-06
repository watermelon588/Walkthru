# Variant 2: Darkroom

Preview: `/variants?v=darkroom`. Source: `apps/web/src/variants/Darkroom.tsx`, `darkroom.css`.

## The idea

A test user is an observer. Darkroom shoots the product like a film about observation: black and white photography, grain, one red signal that marks what matters. The hero is a live scanner (a red band reads the frame top to bottom), the steps hand the light from one to the next, and the test user's words light up as you read them. It is serious, cinematic and premium, the opposite of a cheerful SaaS page.

**Vibe:** editorial poster meets film title sequence. Swiss grid, darkroom red light, quiet confidence.
**Who it flatters:** agencies and founders who want the product to feel like a professional instrument.

## Design principles

1. **Monochrome first, red only for signal.** Photos are always greyscale. Red marks the one thing to look at: the headline highlight, step numbers, the reading line, the moment the user gives up, the primary button.
2. **Type is the architecture.** Huge uppercase Archivo sets the grid; images sit against it, not behind it.
3. **Motion reveals, it does not decorate.** Each animation is a way of looking: scanning, opening an eye, focusing on one step, reading word by word.
4. **Darkness with depth.** Near-black, a panel tone, a faint tone for unread words, film grain over everything.
5. **No rounded corners.** Every edge is square; buttons are flat blocks.

## Typography

| Role | Face | Settings |
| --- | --- | --- |
| Display | Archivo (Google Fonts, variable width 62 to 125%, weight 100 to 900) | weight 820, uppercase, tracking -0.02em, leading 0.86 |
| Titles (steps, test users, transcript) | Archivo | weight 700, `font-stretch: 75%`, uppercase, leading 0.9 |
| Body | Geist Variable | 400 to 650 |
| Labels, numbers, nav | Geist Mono | 12px, uppercase, tracking 0.08em |

The width axis is the star: the hero letters snap open from 62% to 100% width on load and widen to 125% under the pointer; the closing line stretches from condensed to extended as it scrolls in.

Scale: hero `clamp(3rem, 8.4vw, 9.4rem)`, section display `clamp(2.4rem, 5.4vw, 5.6rem)`, transcript `clamp(2.2rem, 5.6vw, 6rem)`.

## Color palette

| Token | Hex | Role |
| --- | --- | --- |
| `--dr-bg` | `#0b0b0c` | Page |
| `--dr-panel` | `#151517` | Image wells |
| `--dr-ink` | `#eceae4` | Text (warm off-white, never pure white) |
| `--dr-muted` | `#8f8d87` | Secondary text (5.9:1 on bg) |
| `--dr-faint` | `#3a3a3d` | Unread transcript words, inactive steps |
| `--dr-line` | `rgb(236 234 228 / 0.13)` | Hairlines |
| `--dr-red` | `#ff3b21` | Signal: buttons, highlight bar, numbers, reading line |

Red on black is 5.5:1; black text on the red highlight is 5.5:1.

## Assets

From `apps/web/design/source-images` (copied to `apps/web/public/variants/dark/`):

| File | Used for |
| --- | --- |
| `walkers.jpg` (visual/15c1d4e4) | WebGL hero texture; transcript background |
| `eye.jpg` (visual/ac225fd3) | The eye opening section |
| `work-cap.jpg`, `work-train.jpg`, `trackpad.jpg` (real-img) and `desk-face.jpg` (visual/b38b0bbb) | One photo per step |
| `crowd.jpg` (visual/71abf928) | Test users opener (crowd in 3D glasses, one figure in red) |
| `red-book.jpg` (visual/a70828b5) | Safety section |
| `collage.jpg` (illustration/1b2d0f73) | Closing |
| `red-blur.jpg`, `red-bar.jpg`, `red-faces.jpg`, `chair.jpg` | Copied as alternates, not on the page |

From the live site: the four real report captures, the five persona photos (greyscale), the mark (inverted).

## Page structure

1. **Nav**: thin bar, mono links, red block CTA. A 3px red reading line runs down the left edge for the whole page.
2. **Hero**: full-bleed WebGL scanner behind a giant uppercase headline; "built with AI." sits on a red bar. Subline and an underline-style scan form below a hairline.
3. **The eye**: a greyscale eye that opens (clip widens, photo settles) under "Your browser clicks. Our agent thinks." with the second sentence in red.
4. **Steps**: pinned split screen. Four step titles on the left; the active one lights up and shows its text, the photo on the right wipes to the next and a red frame moves to a new detail.
5. **Every scan checks**: a quiet four-column index of the 21 checks (no marquee on this page).
6. **Transcript**: pinned; the test user's last two thoughts light up word by word, "I would leave now." in red.
7. **Report**: pinned; vertical scroll pans four real captures sideways, each with a red index and caption.
8. **Test users**: the crowd image, then five huge typographic rows; a greyscale portrait follows the pointer over the row you hover.
9. **Safety**: the red-book photo beside the headline and four points under red rules.
10. **Pricing**: four columns joined by hairlines; Pro gets a red top edge and a red price.
11. **FAQ**: sticky title, hairline accordion.
12. **Closing**: "SCAN MY SITE" stretches to full width, the form underneath.

## Motion

All of it is gated on `prefers-reduced-motion: no-preference`; reduced motion gets a still frame of the shader and static sections.

| Moment | What moves | Why |
| --- | --- | --- |
| Page scroll | ScrollSmoother, `smooth: 1.3` (heavier, filmic) | Weight; the page feels like a camera move |
| Hero scanner | Raw WebGL fragment shader: greyscale, contrast, chromatic split and red glow inside a band sweeping down every ~14s, a lens that follows the pointer, animated grain, vignette. Pauses off screen and in hidden tabs; plain photo if WebGL is unavailable | The product reads your site; the hero shows reading |
| Hero type | SplitText chars open from 62% width; red bar wipes in; letters widen near the pointer | Kinetic type as the main visual |
| Scroll away | Hero copy drifts up and fades | Hand-off to the next scene |
| Eye | Clip-path opens, image scale 1.35 to 1 | Literal "fresh eyes" |
| Steps | Pinned timeline; title color, height of the body, clip-path wipe of the photo, red frame position | One step in focus at a time |
| Transcript | Pinned, words go faint to ink, the last sentence to red | You read at the user's pace; the drop-off lands |
| Report | Pinned horizontal pan | Many parts, one report |
| Test users | Portrait follows the pointer with `quickTo` | Puts a face to each visitor without a grid of photos |
| Reading line | Red line scales with page progress | Quiet orientation |
| Closing | `font-stretch` 62% to 125% scrubbed | A last kinetic beat on the CTA |

## If this became the whole product

- Dark app shell, greyscale screenshots, red reserved for "needs your attention" (high-severity findings, failed steps, the run button).
- Reports read like case files: big uppercase section titles, mono metadata, hairline tables.
- Risk: a fully dark product is a strong commitment (print and PDF exports need a light print stylesheet, which the app already has). Red must stay rare or it stops meaning anything.

## Notes

- Fonts load from Google Fonts for the preview; self-host before production.
- No new libraries: the shader is about 60 lines of raw WebGL, no three.js.
- Film grain is a fixed SVG-noise overlay on a non-scrolling layer, so it costs no repaint on scroll.
