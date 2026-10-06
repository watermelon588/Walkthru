# Variant 3: Markup

Preview: `/variants?v=markup`. Source: `apps/web/src/variants/Markup.tsx`, `markup.css`.

## The idea

A Walkthru report is a careful second reading of your site. Markup turns the home page into that reading: a proof sheet on blueprint paper where a reviewer circles things, underlines them, ticks boxes and stamps approvals. The hero is the real dashboard capture taped to the page and annotated by hand. It is calm, precise and honest, and it shows the product doing its job instead of describing it.

**Vibe:** design review, architect's proof, an editor's red pen (here, a lime highlighter). Thoughtful and trustworthy.
**Who it flatters:** careful builders and agencies who hand reports to clients and need them to look credible.

## Design principles

1. **Show the product being read.** Real captures get circles, crop marks and margin notes; the checklist ticks itself; the run log gets circled where the user leaves.
2. **One highlighter.** Lime is the only accent and it always means "this matters": key words, the drop-off sentence, the Pro price, tape.
3. **Ink on paper.** Navy ink for text and every drawn mark; a faint blueprint grid behind everything; sheets of slightly brighter paper with soft shadows.
4. **Hand and machine side by side.** Handwriting only for annotations, never for interface text. Interface stays in clean sans and mono.
5. **Quiet layout, busy margins.** The grid is calm and editorial; personality lives in the notes, tape and stamps.

## Typography

| Role | Face | Settings |
| --- | --- | --- |
| Display | Schibsted Grotesk (Google Fonts, variable) | weight 650, tracking -0.04em, leading 0.98 |
| Body | Geist Variable | 400 to 600 |
| Labels, numbers, nav | IBM Plex Mono | 11.5px, uppercase, tracking 0.06em |
| Annotations only | Caveat | 600, 1.1 to 1.9rem, slight rotation |

Scale: hero `clamp(2.7rem, 5vw, 4.9rem)`, section display `clamp(2.4rem, 5vw, 4.4rem)`.

## Color palette

| Token | Hex | Role |
| --- | --- | --- |
| `--mk-paper` | `#f5f6f1` | Page (cool off-white) |
| `--mk-sheet` | `#fcfcf9` | Paper sheets, inputs |
| `--mk-grid` | `rgb(43 61 110 / 0.07)` | 28px blueprint grid |
| `--mk-ink` | `#1c2230` | Text, drawn marks, primary button |
| `--mk-muted` | `#5a6172` | Secondary text (5.7:1 on paper) |
| `--mk-line` | `rgb(28 34 48 / 0.16)` | Hairlines, sheet borders |
| `--mk-lime` | `#d6f548` | Highlighter, tape, focus ring, button hover |

Lime is never used for text; text on lime stays ink (12.9:1).

## Shape and material

- One radius: 0.5rem for sheets, inputs and buttons (0.3rem for images inside sheets).
- Sheets: 1px hairline border, soft navy shadow, slight rotation (-1.2 to 0.8deg) for captures.
- Tape: translucent lime strips with `mix-blend-mode: multiply`.
- Drawn marks: 2.4px navy strokes with round caps, `vector-effect: non-scaling-stroke` so they stay crisp at any size.

## Assets

From `apps/web/design/source-images` (copied to `apps/web/public/variants/markup/`):

| File | Used for |
| --- | --- |
| `line-laptop.jpg`, `line-walk.jpg`, `line-monitor.jpg`, `line-juggle.jpg` (illustration) | One line drawing per step, multiplied onto the paper |
| `spotlight.jpg` (info/7d572469) | Checklist sheet, cropped to the lime spotlight (third-party title and footer text are cropped out) |
| `figures.jpg` (doodles/a908d91b) | Closing sheet |
| `iceberg.jpg`, `who-cares.jpg`, `birds.jpg`, `line-reading.jpg` | Copied as alternates, not on the page |

From the live site: `hero-dashboard.webp` (real signed-in dashboard), the four real report captures, the five persona photos (greyscale), the mark (Scout walks the steps path).

## Page structure

1. **Nav**: thin ruled bar, mono links, ink CTA.
2. **Hero**: headline with "launch check" highlighted, subline, scan form. Right: the real dashboard capture taped on a sheet, then marked up: the headline underlined, runs left circled with an arrow, the pipeline bracketed in lime, three handwritten notes.
3. **Checklist**: one sheet; "Every scan checks 21 things." and 21 boxes that tick as you scroll.
4. **How it works**: four step sheets in two staggered columns joined by a dashed path; a solid line draws along it and Scout walks the route.
5. **Field report**: the quickinvoice run as a log; the last row gets highlighted, circled, and a note says "this is where they leave".
6. **Report**: sticky list of the four parts; each real capture sits on a sheet with crop marks and a handwritten note.
7. **Test users**: five index cards with tape and handwritten names, fanned out from one pile.
8. **Safety**: four rubber stamps (one per promise) that thud onto the sheet.
9. **Pricing**: four form-like sheets with dashed rules; Pro gets tape and a highlighted price.
10. **FAQ**: one sheet; the question gets highlighted when opened.
11. **Closing**: "Get a second reading." with the scan form and loose ink figures.

## Motion

Gated on `prefers-reduced-motion: no-preference`. With reduced motion every mark, tick and highlight is simply present.

| Moment | What moves | Why |
| --- | --- | --- |
| Page scroll | ScrollSmoother, `smooth: 1.1` (lighter, precise) | Calm, paper-like glide |
| Hero | Lines rise from masks, highlighter sweeps, the sheet settles, then each annotation draws itself (DrawSVG) and the notes appear in turn | You watch the review happen |
| Checklist | 21 ticks draw in sequence, scrubbed to scroll | Coverage you can count |
| Steps | Path draws with scroll; Scout follows it (MotionPath) | The journey of a test user, literally walked |
| Field report | Rows arrive, the last is highlighted, circled and annotated | Lands the drop-off moment |
| Report | Crop marks and notes draw as each capture enters | Each part is "checked" |
| Test users | Cards fan out from a single pile, scrubbed | Many visitors from one tool |
| Safety | Stamps thud (scale 2.4 to 1 with `power4.in`) one after another | Promises feel signed off |
| FAQ | Highlighter sweeps under the opened question (CSS) | Feedback on interaction |

## If this became the whole product

- The report view becomes literally marked up: findings as margin notes pointing at the evidence screenshot, highlighter for the top fix, stamps for "Launch ready".
- Dashboard on the grid paper with sheets for runs; mono for metadata.
- Strongest fit with what the product already is (evidence, screenshots, reviews), and the gentlest change from today's silver-and-ink design.
- Risk: handwriting can feel gimmicky if it spreads into the interface. Keep Caveat for annotations only.

## Notes

- Fonts load from Google Fonts for the preview; self-host before production.
- No new libraries: DrawSVG, MotionPath and SplitText ship in the installed `gsap` package.
- Hand-drawn circles are generated by a small `scribble()` function (a wobbling ellipse that overshoots), so every circle looks drawn, not geometric.
