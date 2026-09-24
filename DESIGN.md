# Design

Premium, light, minimal. Thin type, quiet colour, real photography, slow deliberate motion. Light mode only (founder decision).

## Brand
- Name **Walkthru**, tagline **"See where strangers get stuck."**, description, logo: all in `apps/web/src/brand.ts`. Import from there, never hardcode the name.
- Logo: the walking bird (`src/assets/brand/walkthru-mark.png`, ink on transparent), rendered by `<Logo />` in Shared.tsx. Top nav shows the bird only (`<Logo withName={false} />`, 32px). Footer and login show bird + name. Favicon and touch icon are generated from the same mark (`public/favicon.png`, `public/apple-touch-icon.png`).
- Other logo options the founder made (penguin, frog, face) are kept in `apps/web/design/brand-source/`.

## Tokens
Defined in `apps/web/src/index.css` as CSS variables, exposed as Tailwind colours.

| Token | Value | Use |
|---|---|---|
| `bg` | #f4f4f5 | Page background |
| `surface` | #e9e9eb | Bands, side panels, placeholder slots |
| `ink` | #1b1b1f | Headings, body, primary button fill |
| `muted` | #63636b | Secondary text (passes AA on bg) |
| `line` | #dedee2 | Hairlines, borders |
| `accent` | #4d7274 | Icons, small highlights only. Never large fills. |
| `danger` | #a33b3b | Form errors |

One accent only. No new colours without updating this file.

## Typography
- Geist Variable (sans) and Geist Mono Variable, self-hosted via @fontsource.
- Headlines: `font-extralight` / `font-light`, tight tracking (`-0.035em` on h1). H1 up to `md:text-7xl`, h2 `text-3xl md:text-5xl`.
- Body: regular weight, `text-muted`, `leading-relaxed`, max ~60ch.
- Mono only for machine output (actions, URLs, file paths).

## Shape and layout
- Buttons: pills (`rounded-full`). Primary = `bg-ink text-bg`. Ghost = `border-line`.
- Frames, cards, photos: `rounded-2xl`. Inputs: `rounded-xl`.
- Container: `max-w-7xl`, gutters `px-5 md:px-10`. Sections `py-20` to `py-32`.
- Hairline grids (`gap-px bg-line`) instead of heavy cards for pricing-style tables.

## Motion (GSAP + @gsap/react)
- Shared hook `useReveal` (`src/lib/motion.ts`): headline words rise (`.word`), hero blocks fade (`.hero-fade`), sections fade up on scroll (`.reveal`).
- Landing: the "how it works" timeline line draws with scroll.
- Every animation sits inside `gsap.matchMedia('(prefers-reduced-motion: no-preference)')`. Animate transform and opacity only.
- Motion must explain something (order, attention, feedback). No decorative loops.

## Imagery
- Photos: real, muted, people in context. Test-user portraits are shown in grayscale.
- Product screenshots (.png): keep their natural shape (no forced crop), `rounded-lg` to match the mock window corners, soft ink-tinted shadow. Rendered trimmed flush by `render.sh`, so edges line up with text columns.
- Placeholders are rendered from `apps/web/design/mocks/*.html` (`bash design/mocks/render.sh`). Replace with real captures, same filenames, once the product exists.
- `<Asset>` shows a labelled slot if a file is missing, so layout never breaks.

## Headings
No eyebrow labels above headings in the app (craft floor). A section heading carries its own name, with one light Phosphor icon in `text-accent` for report sections. The printed report keeps its cover kicker.

## Copy rules
No em dashes. Plain verbs. Button labels 1 to 4 words. One label per intent ("Scan my site" everywhere for the free scan).

## Landing page composition (final)
Chosen from four explored variants (A Porcelain, B Mist, C Silver, D Graphite) on 2026-09-18:
1. Hero (Silver): headline, subtext, CTAs, product screenshot
2. How it works (Silver): drawing timeline + eye-with-desktop-icons graphic (`agent-eye.jpg`)
3. Quote (Porcelain content): full-bleed band, reader photo fading into the surface colour behind the quote (breaks the run of split sections)
4. Report (Silver): sticky list + screenshots
5. Test users (Graphite): 5 grayscale portraits
6. Safety (Mist band): "Tests your dashboard without your password."
7. Pricing, FAQ, Closing with scan form
8. Footer: brand + about line, Product / Get started / Legal columns, AI disclaimer

## Pages
| Page | Path | Notes |
|---|---|---|
| Landing | `/` | `src/pages/Landing.tsx` |
| Login | `/login` | Split layout: form left, full-height photo right on desktop (`public/assets/login.jpg`: blurred figure in a lounge chair on light grey, desaturated to match the palette). Google, GitHub, email magic link. |
| App shell | `/app/*` | Desktop: 15rem left sidebar on `bg` with a hairline, active item on `surface`. Phones: sticky top bar and a native `<dialog>` drawer with the same navigation. |
| Dashboard | `/app` | Operate mode: a greeting, then state before history. One hairline band holds the plan meter (runs left is the largest number on the page, with a usage bar that turns danger at 20% or less), the latest Launch Ready score and Scout. Run rows show kind icon (a thinking orb while running), high-severity count, status, score chip and time. Instant Scan sits last as a surface band. Numbers count up and rows settle in once when data lands (reduced motion: static). |
| Profile & settings | `/app/settings` | Authenticated personal or business profile stored in Supabase Auth metadata. Shows the signed-in identity, provider status and one focused profile form. |
| Report | `/app/runs/:id`, `/r/:id` | Canonical launch-readiness report. Summary first, then a three-pane journey replay, technical checks, prioritized fixes and all findings. Private and public views share the same report body. Print styles produce the PDF rather than a second renderer. |
| Docs | `/docs` | Read mode. `DocLayout`: title, lead, sticky "On this page" index (collapsible on phones), `.prose-doc` body at ~68ch. Same layout for `/privacy`, `/terms`, `/security`. |
| Not found | `*` | Scout in its stopped state, one line of copy, Home and Docs actions. |
| Agent identity lab | `/agent-lab` | Five draggable SVG birds with attached names and activity labels. Prototype only, not linked from the production navigation. |

## Evidence workspace
- Desktop journey replay uses three panes: chronological steps, the selected evidence frame and a compact inspector. On smaller screens they stack in that order.
- The image is evidence, not decoration. Use `object-contain`, preserve the captured viewport ratio and show explicit loading, unavailable and legacy-run states.
- Replay controls are quiet circular buttons with accessible names. The selected step uses the existing surface token; do not add a timeline accent colour.
- Never show typed values in activity logs or report inspectors. Captures temporarily hide Scout and visually mask form controls.
- Technical checks stay separate from human-journey findings so the reader can tell observed behavior from deterministic SEO and security checks.
- Priorities use ordered `P01`, `P02` labels. The report remains useful in print, with navigation/actions hidden and evidence blocks kept together where possible.

## Agent identity exploration
- The original walking-bird logo now has a lab-only vector source at `src/assets/brand/walkthru-mark.svg`. The production logo remains unchanged.
- Two treatments live in `src/components/AgentBird.tsx`: Scout uses the solid mark and Trace uses the outline mark. The lab shows the original Scout plus three colour-only Scout copies, for five birds total.
- The lab palette adds graphite, teal, cobalt, rust and plum as identity-study colours. These are isolated from the production page palette.
- Every bird can be dragged directly with a pointer or moved with arrow keys. There is no visible container around the bird, name or activity.
- All five birds use the confirmed GSAP Observe motion, which gently shifts the whole bird while it watches. Animated parts overlap beneath the body so joints stay visually connected. `prefers-reduced-motion` keeps every version static.

## Agent identity in product
- Production uses the solid Scout bird, its name and one short activity line. It has no card, border or decorative container.
- Place Scout where its state clarifies the product: beside the landing hero product view, above sign-in, beside dashboard controls, in report headers, in the extension header and at the bottom-right of the page currently under test. Do not repeat it in global navigation or unrelated content sections.
- The tested-page version lives in a closed shadow root so page styles cannot break it and the test agent cannot include its own status UI in a snapshot. Evaluation fixtures stay untouched; Scout appears there only while the extension runs an evaluation.
- State colours reuse the core palette: ink for ready or acting, accent for observing or complete, danger for stopped or failed. Changes fade rather than snap.
- GSAP Observe is the single motion language: slow body attention, a small connected tail counter-shift and an occasional blink. State text fades between actions. All motion stops under `prefers-reduced-motion`.

## Launch Ready badge
- A 20px pill for other people's sites: "Walkthru" on ink, "Launch Ready NN" on accent (85 and up), muted (60 to 84) or danger (under 60). Verdana, because Geist is not available on the sites that embed it. The SVG carries hex copies of the tokens for the same reason.
- The owner's report shows it with copy buttons; strangers on the public report see only the score.
