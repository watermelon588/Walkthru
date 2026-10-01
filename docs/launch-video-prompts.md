# Walkthru launch video: three 60-second variants

_Written 2026-10-01 from the product (SPEC.md, DESIGN.md, `apps/web/src/content.ts`, the Docs page, the API and extension code) and the four references in `Desktop/video reference/walkthru/`. Each variant is a complete prompt: paste it into a video agent, or run it through `/brag` (see "Can brag build this?" at the end)._

## What the references taught us (and what we take from each)

| Reference | What it does | What we borrow | What we leave |
|---|---|---|---|
| `reference1.mp4` (Base44, 50 s) | Warm off-white canvas, tiny centred type, a prompt box that becomes an app, floating UI cards, iridescent heat-map gradients, a dark terminal (`git push origin main`), a security shield grid, ends on a small logo | Calm canvas, real UI as the hero, terminal beats, the "scan heat" gradient, the shield grid as a security moment | Bike photography and lifestyle footage |
| `reference2.mp4` (Shapes, 67 s) | Geometric colour wipes, nested shape "portals", a mascot face inside the AI chat, a spinning wheel of feature names, metric cards, a "Done!" card | A shape system cut from our own mascot, the feature wheel, the mascot living inside the product, colour-coded sections | Stock HR photography, the face mascot |
| `reference3.mp4` (Edge, 89 s) | Editorial manifesto: one word per frame, serif and condensed type, handwritten notes, strike-throughs ("Not in 2050. But now!"), collage, registration marks | Manifesto pacing, the strike-through reversal, handwritten annotations, one bold word at a time | Climate footage, vintage engravings of people |
| `brand.mp4` (2.8 s) | Scout, the ink bird, in a looping walk cycle on light grey | Scout is in every variant, every beat that shows "the agent working" | Nothing: this is the identity |

## The brand rules every variant keeps

- **Scout is the agent.** Not a logo stamp at the end: Scout is the AI test user. When the product works, Scout walks. Black ink (`#1b1b1f`), round head, white eye ring, pointed beak, V-shaped tail, thin stick legs with three-toed feet. Walk cycle from `brand.mp4`.
- **Canvas:** `bg #f4f4f5`, `surface #e9e9eb`, `ink #1b1b1f`, hairlines `#dedee2`, brand accent `#4d7274`. Light mode. Lots of air.
- **Type:** Geist (sans) for words, Geist Mono for anything the machine says (actions, URLs, tool calls, scores). Headlines extra-light, tight tracking (-0.035em). Variant C may add one editorial serif for contrast.
- **Signal colours (video only, approved by the founder for this film).** Colour always means something, never decoration:
  - **Coral `#FF5A4E`:** where a stranger got stuck (UX, journeys)
  - **Cobalt `#2F5BFF`:** Google and AI search readiness (SEO, GEO)
  - **Acid lime `#C6F432` on ink:** security hygiene
  - **Sun `#FFC93C`:** growth (compare, AI answers, weekly watch)
  - **Ink:** Scout and the agent loop
- **Copy rules:** no em dashes on screen, plain verbs, short lines. Real claims only. Never promise rankings or AI citations ("readiness", "whether AI names you", never "get cited"). Security is "passive, never an attack".
- **Motion:** fast in, then hold long enough to read (short label 0.8 s settled, about 0.3 s per word for sentences). Transform and opacity. Snappy eases (expo out on entries, quick cuts on beats).

## The message (all three variants)

**This is not a scanner. It is a stranger on call.** Before every launch, an AI test user walks into your app the way a real stranger would, thinks out loud, gets stuck where they would get stuck, and hands your coding agent the fixes. Then it checks again.

Audiences we speak to by name: **indie hackers** shipping with Cursor, Lovable, Bolt and v0; **startup founders** before launch day; **agencies** handing sites to clients.

The facts every variant may use (all true in the product today):

- **Instant Scan:** paste a URL, about 20 seconds, no install. SEO, AI search readiness, passive security.
- **AI test users:** 5 personas (first-time visitor, phone user, small-business buyer, skeptical developer, your logged-in user). Each turns a goal into a checklist, then walks it.
- **Agentic loop:** the Chrome extension snapshots the page (a text outline of buttons, links, headings, errors), masks emails and typed values in the browser, the server decides every click, the extension acts, the test user thinks aloud. Up to 30 steps.
- **Safe by design:** runs in the tab you are already signed into (no passwords shared); never clicks delete, cancel or pay; asks before submitting forms.
- **One ranked report:** where they got stuck (with the step and the test user's words), a **Launch Ready score 0 to 100**, fixes ranked, a **live badge**.
- **21 real checks**, including robots.txt and AI crawlers, llms.txt, structured data, Core Web Vitals, Content-Security-Policy, HSTS, keys in JavaScript bundles, Supabase row access, subdomain takeover, vulnerable libraries, SPF and DMARC.
- **Fix prompt for your coding agent**, **MCP server** (Claude Code, Cursor: `scan_site`, `get_fix_prompt`, `verify_finding`, `open_fix_pull_request`), **GitHub fix pull requests**.
- **Rerun and compare:** fixed, new, still broken. **Compare with 3 competitors**, side by side.
- **AI answer tracking:** whether AI assistants name or cite you for the questions your buyers ask.
- **Weekly watch and deploy hooks:** re-checks after every deploy, emails only when something changed.
- **Team workspaces** with Scout answering in the thread. **Branded PDF** for agencies.
- **Free to start:** $0, no card.

---

## Variant A: "Ship Friday." (product-led, after reference 1)

**One-line idea:** the 60 seconds between "it works on my machine" and "a stranger tried it". Calm, premium, the product is the hero, and the agent loop is shown as real machinery.

**Format:** 1920x1080, 60 s, 30 fps. Optional 1080x1920 cut (same beats, UI stacked).
**Feel:** reference 1's calm canvas and floating UI, plus a dark "machine room" for the agent loop. Signal colours arrive only when a finding appears.
**Music:** minimal electronic, 112 to 118 BPM, soft kick from 0:08, drop at 0:22, breakdown at 0:44, one clean hit on the logo.

### Prompt

> Create a 60-second 16:9 launch film for **Walkthru**, the launch check for apps built with AI. Visual language: a calm, premium, light canvas (`#f4f4f5`), ink type (`#1b1b1f`) in Geist extra-light with Geist Mono for machine output, generous whitespace, real product UI floating in thin browser frames with soft ink shadows, and an iridescent "scan heat" gradient (cobalt into coral into sun) that washes across UI only while Walkthru is scanning. The mascot **Scout**, a black ink bird with a white eye ring and stick legs, is the AI test user: whenever the product is working, Scout walks. Colour means something: coral = where a stranger got stuck, cobalt = Google and AI search, acid lime on ink = security, sun = growth. No stock lifestyle footage. Every frame shows the product or the agent at work.
>
> **0:00 to 0:04, hook.** Empty canvas. Tiny centred Geist text types on: `/  You shipped it  /`. A cursor clicks a black pill button **Deploy**. Hard cut to ink: Geist Mono `→ git push origin main` with `main` highlighted in a cobalt block. Sound: one key click, one sub thud.
>
> **0:04 to 0:08, the problem.** Back on light. One line, one word at a time: **"But has a stranger tried it?"** The word "stranger" holds. Scout walks in from the left edge and stops under the word, head tilted up at it.
>
> **0:08 to 0:13, the reveal.** Scout hops onto a URL field that grows from the line: `quickinvoice.app`. The pill **Scan my site** presses. A thin progress hairline races. Counter in Geist Mono: `20 s · no install`. The iridescent scan heat sweeps across a floating homepage capture; small chips pop out of it and settle in a row: `robots.txt and AI crawlers`, `llms.txt`, `Structured data`, `Content-Security-Policy`, `HSTS`, `Keys in JavaScript bundles`, `Supabase row access`, `Subdomain takeover`.
>
> **0:13 to 0:24, the agent loop (the centrepiece).** Cut to a split screen. Left: a real Chrome tab with the Walkthru side panel open. Right: a dark machine room (ink background) showing the loop as a living diagram, four nodes on a ring, each lighting as it runs: **Snapshot → Decide → Act → Think aloud**. Between tab and machine room, a line of masked text streams across: `button "Get started" · link "Pricing" · input [email ••••@••••]`, with the mask animating on (label: *Masked in your browser*). The server node decides; a cursor shaped like Scout's footprint clicks **Get started** in the tab. Think-aloud bubbles in Geist Mono appear above Scout, who now walks along the top edge of the browser frame step by step:
> `Step 3 · Clicked "Get started"` · *"Get started and Book a demo look the same."*
> `Step 5 · Typed email and business name` · *"It wants a tax ID before I have seen anything."*
> `Step 6 · Clicked "Create account"` · *"Nothing happened. No error. I would leave now."*
> On step 6 the whole frame flashes coral once and a coral pin drops on the button: **Stuck here.** A small badge in the corner of the tab: `Safe mode · never clicks delete, cancel or pay`. Another: `Your tab · no password shared`.
>
> **0:24 to 0:32, the report.** Pull back: the report assembles from flying cards onto the canvas. A big Geist Mono counter rolls up to **Launch Ready 64 / 100**. Three ranked fix cards stack with coloured spines: coral "Create account fails silently", cobalt "AI crawlers blocked in robots.txt", lime "No Content-Security-Policy". Each card shows its evidence line in mono (a step, a URL, a header). Caption: **Every finding cites a step, a URL or a header.**
>
> **0:32 to 0:42, hand it to your coding agent.** Cut to a dark terminal titled `claude`. Typed: `> fix what Walkthru found`. Tool calls stream in mono, each with a tiny Scout icon: `walkthru · get_fix_prompt`, `walkthru · open_fix_pull_request (preview)`. A GitHub pull-request card slides in: **Walkthru: fix 3 findings**, files `vercel.json`, `robots.txt`, `llms.txt`, green "+42". Then `walkthru · verify_finding sec.csp.missing` returns **Fixed.** in lime.
>
> **0:42 to 0:50, rerun, and it keeps watching.** Back to light. The score counter rolls from 64 to **91**. A three-column strip writes itself: **Fixed 3 · New 0 · Still broken 1**. A ring of small cards orbits the score, each one a growth feature in sun: **Compare with 3 competitors**, **Is AI naming you?** (a mini AI-answer card with a brand chip lit), **Weekly watch**, **Deploy hook**. The shield grid from the security check (a field of small shield outlines) fills, then resolves into one lime shield.
>
> **0:50 to 0:56, who it is for.** Three quick title cards, each with Scout in a different pose: **Indie hackers** · *Ship Friday. Sleep Friday.* / **Founders** · *Launch with a stranger's honest eyes.* / **Agencies** · *Hand every client a report with a badge.*
>
> **0:56 to 1:00, end card.** Scout walks to centre, stops, turns to camera. The wordmark **Walkthru** sets beside Scout (32 px mark ratio, same as the site nav). Line under it: **See where strangers get stuck.** Pill button: **Scan my site · free**. Final hit on the beat; Scout blinks once.

### Voiceover (optional, about 120 words)

> You shipped it. It works on your machine. But has a stranger tried it?
> Paste your link. Twenty seconds later, Walkthru has read it like Google, like AI search, and like an attacker would, without ever attacking.
> Then Scout, your AI test user, walks into your app. It sees what a stranger sees, decides every click, and thinks out loud, right up to the moment it would leave.
> One report. Every finding grounded in a step, a URL or a header. Hand it straight to your coding agent, open the pull request, and check it again.
> Built for indie hackers, founders and agencies who launch for real.
> Walkthru. See where strangers get stuck.

### Asset catalog, variant A

| # | Asset | Format and spec | Status | Who |
|---|---|---|---|---|
| A1 | Scout walk cycle with transparency | WebM VP9 with alpha, or ProRes 4444 `.mov`, or PNG sequence (24 to 30 fps, 1 to 2 loops), 1080 px tall minimum | `brand.mp4` exists but has a grey background | **You**: export with alpha from the source animation. If you cannot, I can key the grey out, with softer edges. |
| A2 | Scout poses (stills) | Transparent PNG or SVG, 2048 px: looking up, tilted head, hopping, pointing with a wing, sitting, facing camera, blink frame | Only the walking mark exists | **You** (preferred, keeps the hand-drawn line) or I draft poses from the SVG for your approval |
| A3 | Scout mark (vector) | SVG | **Exists**: `apps/web/src/assets/brand/walkthru-mark.svg` | Me |
| A4 | Wordmark lockup | SVG: bird + "Walkthru" in Geist | Rendered by `<Logo />` in code | Me (exported from the site) |
| A5 | Fonts | Geist Variable, Geist Mono Variable | **Exists** (`@fontsource` in `apps/web`) | Me |
| A6 | Homepage of a sample app to scan | 2560x1600 PNG, or live HTML | `evals/fixtures/easy` and `hard` exist; `quickinvoice.app` copy exists in `content.ts` | Me (I build it in HTML) or **you** if you want a real customer site (with permission) |
| A7 | Chrome tab with the Walkthru side panel mid-run | 2560x1600 PNG at 2x, or screen recording 10 s | `extension-panel.png` exists (placeholder quality) | **You**: record a real run on the hard fixture. I can rebuild it in HTML from the extension code if not. |
| A8 | Report page: score, stuck point, ranked fixes | 2560x1600 PNG at 2x | `report.png`, `stuck-closeup.png`, `seo.png`, `security.png` exist (mock renders) | Me: re-render at 2x from `apps/web/design/mocks`, or **you** capture a real report |
| A9 | Terminal with Claude Code calling Walkthru MCP tools | Screen recording 8 to 10 s, dark theme, 2x | Not captured | **You** (real is stronger), or I build it in HTML |
| A10 | GitHub pull-request card | PNG at 2x | Not captured | I build it in HTML (no GitHub branding beyond the octicon), or **you** capture a real fix PR |
| A11 | Rerun strip, compare, AI answers and watch mini cards | HTML | Pages exist in the app | Me (built from the real components) |
| A12 | Music | WAV or MP3, 60 s, 112 to 118 BPM, licensed for commercial use | None | **You** pick (Artlist, Epidemic, Uppbeat), or I use a brag bundled track |
| A13 | Voiceover | WAV 48 kHz | None | Kokoro TTS through brag (free, local), or **you** record or use ElevenLabs and send the WAV |
| A14 | SFX | Key click, sub thud, soft whoosh, chime for "Fixed" | brag bundles SFX | Me |

---

## Variant B: "Every stranger, every shape." (bold colour and character, after reference 2)

**One-line idea:** Scout's body is the design system. Every transition is cut from Scout's own shapes (the round head, the triangle beak, the V tail, the eye ring), and each colour opens a door into one of the things Walkthru checks. Loud, joyful, unmistakably ours.

**Format:** 1920x1080, 60 s, 30 fps.
**Feel:** reference 2's geometric wipes and feature wheel, but every shape is a piece of Scout. Large flat colour fields, white cards, ink type.
**Music:** bouncy, percussive indie-pop or funk-tech, 120 to 126 BPM, claps on every shape wipe, a stop-time gap before the score reveal.

### Prompt

> Create a bold, colourful 60-second 16:9 launch film for **Walkthru**. Design system: the mascot **Scout** (a black ink bird) is the shape language. Build every transition from Scout's geometry: the **eye ring** (a circle with a white centre), the **beak** (a sharp triangle), the **tail** (a V), the **head** (a perfect dome) and the **three-toed footprint**. These shapes grow, nest and wipe across the frame like reference 2's shape portals. Base canvas off-white `#f4f4f5`, ink `#1b1b1f`, Geist type (extra-light headlines, mono for machine output). Signal colours as large flat fields: coral `#FF5A4E` (stuck), cobalt `#2F5BFF` (AI search), acid lime `#C6F432` (security), sun `#FFC93C` (growth). White product cards float on the colour fields with soft shadows.
>
> **0:00 to 0:03, hook.** Huge Geist word, out of focus, snaps sharp: **"Who"**. It shrinks into a small sentence: *Who tried your app before you launched it?* Five tiny circles (future personas) pop in around the line.
>
> **0:03 to 0:08, the answer.** The eye ring of Scout fills the screen from a dot and becomes a portal: concentric rings in cobalt, coral, sun, lime, ink, nesting inward. At the centre, Scout walks in a small circle and stops. Word: **"Strangers."** The rings snap shut into Scout's eye.
>
> **0:08 to 0:16, meet the test users.** Five shape-framed portraits (grayscale photography, from the site) slide in as a row, each framed in a different Scout shape and colour: **First-time visitor** (dome, sun) *30 seconds of patience*, **Phone user** (triangle, coral) *one thumb, bad signal*, **Small-business buyer** (V, cobalt) *wants price and proof*, **Skeptical developer** (eye ring, lime) *reads the details*, **Your logged-in user** (footprint, ink) *inside the tab you are signed into*. Each one gets a mono label as it lands. Clap on each.
>
> **0:16 to 0:26, the agent at work.** A big coral triangle (the beak) slices the frame diagonally and reveals a tilted 3D browser window with the Walkthru side panel. Scout is now the cursor: it walks across the page and pecks at buttons. Above it, a white chat bubble with Scout's eye ring as the avatar types the think-aloud: *"Two buttons, same look. Trying the first one."* then *"It wants a tax ID already."* then *"Nothing happened. I would leave."* A small loop badge spins in the corner: **Snapshot → Decide → Act → Think aloud**, with a tiny label **The server decides every click.** Two white pill chips drift past: **No password shared** and **Never clicks delete or pay**.
>
> **0:26 to 0:34, the feature wheel.** Hard cut to full cobalt. A giant rotating wheel of feature names in white Geist (like reference 2's word wheel), with the active word bold and a pointer: *Instant Scan, AI test users, SEO, AI search readiness, llms.txt, Structured data, Core Web Vitals, Content-Security-Policy, Keys in bundles, Supabase row access, Subdomain takeover, Fix prompt, MCP server, GitHub fix PRs, Rerun, Compare, AI answers, Weekly watch, Team workspace, Branded PDF*. It lands on **Launch Ready**. Stop-time gap in the music.
>
> **0:34 to 0:42, the score.** A white card carousel on cobalt, like reference 2's metric cards: **64 / 100 Launch Ready** (a dome gauge filling in sun), **3 fixes first** (three coloured dots), **1 stuck point** (coral pin). The centre card flips to show the fixes in mono with their evidence. Then the gauge animates from 64 to **91** while a small strip writes: **Fixed 3 · New 0 · Still broken 1**.
>
> **0:42 to 0:50, it works where you work.** A sun field. Three shape windows open side by side: a terminal (Claude Code calling `verify_finding`, answering **Fixed.**), a GitHub PR card (**Walkthru: fix 3 findings**), and a team chat thread where **Scout** answers a teammate's question inside the workspace. Then a lime field fills with a grid of small shields, one lighting per security check, until all light: **Passive checks. Never an attack.**
>
> **0:50 to 0:56, for you.** Three quick colour-flip cards: coral **Indie hackers**, cobalt **Founders**, sun **Agencies**. Under each, one line: *Ship with Cursor, Lovable, Bolt or v0. Launch checked.* / *Your first honest user, before launch day.* / *Every client gets a report and a live badge.*
>
> **0:56 to 1:00, end card.** All colour fields collapse into Scout's eye ring, which shrinks into Scout's actual eye. Pull back: Scout on white, mid-step, then still. Wordmark **Walkthru** beside it. Line: **See where strangers get stuck.** Pill: **Scan my site · free**. One clap.

### Voiceover (optional, about 110 words, upbeat)

> Who tried your app before you launched it?
> Strangers. Five of them. A first-time visitor, a phone user, a buyer, a skeptic, and someone already signed in.
> Each one walks your real app in your own browser. It decides every click, thinks out loud, and tells you exactly where it gave up.
> Then Walkthru checks everything else. Google, AI search, security headers, leaked keys, all passive.
> You get one score, the fixes ranked, and a prompt your coding agent can apply.
> Rerun. Watch the score climb.
> For indie hackers, founders and agencies.
> Walkthru. See where strangers get stuck.

### Asset catalog, variant B

| # | Asset | Format and spec | Status | Who |
|---|---|---|---|---|
| B1 | Scout walk cycle with transparency | Same as A1 | Grey background only | **You** (alpha export) or me (key) |
| B2 | **Layered Scout SVG** (head, eye ring, beak, body, tail, each leg as separate paths) | SVG with named groups | The existing SVG is one shape | **You**, ideally from the source file. Needed to build the shape system and to make Scout peck and act like a cursor. |
| B3 | Scout pecking or clicking pose, and a chat-avatar crop of the eye | PNG or SVG | None | **You** or me from B2 |
| B4 | Five persona portraits | Grayscale JPG, 1600 px square, model released | Filenames in `content.ts` (`persona-owner.jpg` and so on) | **You**: send the files the site uses, or new licensed photos. Without them I use Scout silhouettes. |
| B5 | Tilted browser with side panel | Same as A7 | Placeholder only | **You** record, or me in HTML |
| B6 | Report score and fixes cards | HTML | Real components exist | Me |
| B7 | Terminal, PR card, team chat with Scout | HTML or screen recordings | Team chat exists in the app | Me in HTML, or **you** capture real ones |
| B8 | Shield grid | HTML/SVG | None | Me |
| B9 | Music | WAV, 120 to 126 BPM, percussive, licensed | None | **You** or a brag track |
| B10 | Voiceover | WAV | None | Kokoro via brag, or **you** |
| B11 | Fonts | Geist, Geist Mono | Exist | Me |

---

## Variant C: "Not a scanner." (manifesto, after reference 3)

**One-line idea:** an editorial manifesto with the pacing of reference 3, one bold word at a time on paper-white, where the product appears only as proof. The reversal at the heart of it: *"Launch and hope"* gets struck through and rewritten as *"Launch checked."* This is the variant that says Walkthru is more than a product: it is a new habit, a ritual before every launch.

**Format:** 1920x1080, 60 s, 25 fps (a slightly filmic cadence).
**Feel:** paper-white with faint registration marks and crop marks in the corners, ink type, handwritten annotations in ink, strike-throughs drawn by hand, one signal colour per beat as a full-bleed field. Scout is the narrator who walks across the page between words.
**Music:** sparse piano or plucked strings over a soft pulse, 90 BPM, swelling into a full beat at 0:36.
**Type:** Geist for everything, with an optional editorial serif (Instrument Serif or Fraunces, both open source) for italic emphasis words only, and one hand-lettered annotation font (Caveat or a scanned real hand).

### Prompt

> Create a 60-second editorial manifesto film for **Walkthru**. Paper-white canvas (`#f4f4f5`) with faint hairline registration marks, crop marks and tiny mono metadata in the corners (`WALKTHRU / LAUNCH CHECK / 2026`). Ink type (`#1b1b1f`). Mostly one word or one short phrase per frame, mixing Geist extra-light with a few heavy condensed words that fill the frame. Handwritten ink annotations circle, underline and strike things through, drawn on in real time. Each section gets one full-bleed signal colour: coral `#FF5A4E` for stuck, cobalt `#2F5BFF` for AI search, acid lime `#C6F432` on ink for security, sun `#FFC93C` for growth. **Scout** (the black ink bird) is the narrator: it walks across the page between words, stops to look at them, pecks at the important ones.
>
> **0:00 to 0:05.** Scout walks in from the left on a blank page and stops. Handwritten in the corner: *ready?* One word fades up, small: **"You"**. Then: *"You built it with AI."* "AI" gets a hand-drawn circle.
>
> **0:05 to 0:10.** *"In a weekend."* (handwritten note: *impressive*). Then giant condensed, filling the frame: **SHIPPED.** A hand-drawn arrow points down to a tiny line: *but nobody has tried it yet.*
>
> **0:10 to 0:16.** A coral full-bleed field. Huge word: **STRANGERS** with a cut-out window in the letters showing a blurred browser tab. Line: *They do not read your docs. They have thirty seconds. They leave without telling you.*
>
> **0:16 to 0:24.** Back to paper. A manifesto line builds word by word, each word swapping in on the beat: **"We are not a scanner."** (handwritten: *not just*) **"We are not a test script."** Then the turn, larger: **"We are a stranger on call."** Scout walks under the line and taps "stranger" with its beak.
>
> **0:24 to 0:34, the proof (product as collage).** A collage of real product pieces pinned to the page with paper-tape corners, each arriving with a mono caption and a small hand-drawn label: the side panel mid-run (*it decides every click*), a think-aloud bubble *"Nothing happened. No error. I would leave now."* (*its words, not ours*), a coral pin on a button (*stuck here*), a masked input `[email ••••@••••]` (*masked in your browser*), the safe-mode badge (*never clicks delete or pay*). Scout hops from piece to piece like it is walking the flow. Ink line connecting them forms the loop: **Snapshot → Decide → Act → Think aloud.**
>
> **0:34 to 0:42, the reversal (after reference 3's "Not in 2050. But now!").** A full sun field with a large paper circle in the middle, framed by half-moon shapes (reference 3's composition). Inside the circle: **Launch and hope.** A hand-drawn line strikes it through. Handwritten under it, then set in Geist: **Launch checked.** The music opens up to the full beat here.
>
> **0:42 to 0:50, everything it checks, as a list that never stops.** Cobalt field. A tall column of checks scrolls fast in white Geist with one word held bold at a time, and handwritten ticks appear: *Can a stranger get in? ✓ Can Google and AI search read you? ✓ Are you leaking anything? ✓*. Then a rapid run of real ones: robots.txt and AI crawlers, llms.txt, structured data, Core Web Vitals, Content-Security-Policy, HSTS, keys in bundles, Supabase row access, subdomain takeover, SPF and DMARC. Lime flash: **Passive. Never an attack.**
>
> **0:50 to 0:56, the habit.** Paper again. Three lines, each one word changing: *Before every launch.* / *After every deploy.* / *Every week, while you sleep.* (handwritten note: *weekly watch*). Then the audience names stamp on like ink stamps: **INDIE HACKERS. FOUNDERS. AGENCIES.**
>
> **0:56 to 1:00.** Scout walks to centre and stops, faces camera. The wordmark **Walkthru** sets next to it. One line: **See where strangers get stuck.** Tiny mono under it: `walkthru.dev · free to start`. A last handwritten word in the corner: *go.*

### Voiceover (optional, about 115 words, calm and deliberate)

> You built it with AI. In a weekend. You shipped it.
> But nobody has tried it yet.
> Strangers do not read your docs. They have thirty seconds, and they leave without telling you why.
> So we are not a scanner. We are not a test script. We are a stranger on call.
> One that walks your real app, decides every click, and says out loud where it got lost. One that checks what Google, AI search and an attacker would see, without ever attacking.
> Launch and hope is over.
> Launch checked. Before every launch. After every deploy.
> Walkthru. See where strangers get stuck.

### Asset catalog, variant C

| # | Asset | Format and spec | Status | Who |
|---|---|---|---|---|
| C1 | Scout walk cycle with transparency | Same as A1 | Grey background only | **You** (alpha) or me (key) |
| C2 | Scout pecking, looking up, facing camera | PNG or SVG | None | **You** or me from a layered SVG (B2) |
| C3 | Handwriting | A scanned real hand (yours?) for 10 words: *ready? impressive, not just, its words not ours, stuck here, weekly watch, go.*, or the Caveat font | None | **You** (much better if real) or I use Caveat |
| C4 | Paper texture (optional) | Subtle paper grain PNG, 4K, tileable | None | Me (generated grain) or **you** |
| C5 | Product collage pieces | PNGs at 2x: side panel mid-run, think-aloud bubble, stuck pin on a button, masked input, safe-mode badge | Placeholders exist | Me from the real components, or **you** capture a real run |
| C6 | Editorial serif (optional) | Instrument Serif or Fraunces (OFL, free) | Not in the repo | Me (only if you approve this one-off font in the video) |
| C7 | Music | Sparse piano or strings into a beat at 0:36, 90 BPM, licensed | None | **You** or a brag track |
| C8 | Voiceover | WAV, calm, deliberate, slight warmth | None | **You** (this variant is best with a human or ElevenLabs voice) or Kokoro |

---

## Can brag build this? (checked against the `/brag` skill)

**Yes, with two caveats.** `/brag` hands the composition to Hyperframes, which builds the video as HTML, CSS and JavaScript animation and renders it to MP4. Everything in these prompts that is type, shapes, gradients, UI, terminals, charts, counters, the agent-loop diagram and the shield grid is a natural fit. Real product UI can be rebuilt from our own components, so it stays exactly on brand.

| Need | brag / Hyperframes | Note |
|---|---|---|
| 60-second runtime | Possible with `--duration 60` | brag's own rule is 15 to 25 s "unless there is a reason". A launch film is the reason; I would also cut a 20 s version from the same composition for social. |
| Kinetic type, shape wipes, nested portals, word wheel, strike-throughs | Yes | Pure HTML/CSS/GSAP |
| Product UI, terminal, PR card, report, score counters | Yes | Rebuilt from our components, or your screenshots and recordings dropped in |
| Scout walking | Yes, as a video layer | Needs A1 (transparent walk cycle). With only `brand.mp4` I can key out the grey, but edges will be softer. |
| Scout acting (pecking, pointing, being the cursor) | Partly | Needs the layered SVG (B2) to rig, or a few pose drawings (A2). Without them Scout walks, stops and turns only. |
| Voiceover | Yes, `--voice` | Kokoro text-to-speech, local and free, decent but synthetic. For a launch film, a human or ElevenLabs voice is better: send the WAV and it is synced in. |
| Music and SFX | Yes | brag bundles tracks and SFX and can beat-sync any track you give it |
| Photoreal footage (reference 1's bikes, reference 3's nature) | No | Not needed: these prompts deliberately avoid stock footage. If you want some, the Higgsfield skill can generate clips (needs your Higgsfield account). |
| Rendering | Yes, locally | Node 22 and Chrome are on this machine; a 60 s 1080p render takes a few minutes |

## What I need from you, in order of impact

1. **Scout with transparency** (A1): the walk cycle exported with alpha. Highest impact on all three variants.
2. **Layered Scout source** (B2): the original file with head, eye, beak, tail and legs separable. Unlocks Scout as a character and the whole shape system of variant B.
3. **A real recorded run** (A7): 10 to 20 s screen recording of the extension driving a tab (the hard fixture on `:8102` is perfect, it gets stuck on purpose).
4. **A real terminal clip** (A9): Claude Code or Cursor calling the Walkthru MCP tools.
5. **Music choice** and **voice choice** (human, ElevenLabs, or Kokoro).
6. **Persona photos** (B4) if you want variant B's portraits, and **your handwriting** (C3) for variant C.

Everything else (fonts, the vector mark, the report, the UI cards, the shield grid, the loop diagram, the gradients) I build from the codebase.
