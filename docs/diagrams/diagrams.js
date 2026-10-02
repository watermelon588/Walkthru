// Diagram specs for sketch.html. Coordinates are hand-placed on the canvas (w x h). Node: {id, x, y, w, h, label,
// sub | items, fill, shape: rect|ellipse|diamond|db, dashed}. Edge: {from, to, fs/ts: 'side:fraction', via, label}.
const DIAGRAMS = {
  'langgraph-persona': {
    w: 1600, h: 1010,
    title: 'persona_session: the LangGraph agent loop',
    subtitle: 'apps/api/app/agent/persona.py  ·  one HTTP call = one graph step  ·  the LLM is called only inside decide, so resume never repeats a model call',
    groups: [{ x: 500, y: 170, w: 680, h: 730, label: 'StateGraph(SessionState)', color: '#1971c2' }],
    nodes: [
      { id: 'start', x: 700, y: 118, w: 140, h: 50, label: 'START', shape: 'ellipse', fill: 'gray', size: 18 },
      { id: 'decide', x: 560, y: 210, w: 420, h: 180, label: 'decide', fill: 'blue', items: [
        'system prompt: persona + goal checklist', 'history + masked page snapshot', '→ LLM structured output: PersonaStep',
        '"done" unconfirmed? re-ask once (NOT_CONFIRMED)', '_enforce(step): code safety gate'] },
      { id: 'act', x: 560, y: 465, w: 420, h: 150, label: 'act   ⏸ interrupt()', fill: 'yellow', items: [
        'returns the step to the HTTP caller, then sleeps', 'wakes on Command(resume=observation)', 'records result_url, errors, notices, evidence'] },
      { id: 'check', x: 560, y: 690, w: 420, h: 160, label: 'check', fill: 'green', items: [
        'safe_stop / done / give_up from the step', 'bot wall or CAPTCHA note → stop, never solve', 'checkpoint url_contains reached → done',
        'step budget · same action x3 · page revisited x3'] },
      { id: 'end', x: 700, y: 932, w: 140, h: 50, label: 'END', shape: 'ellipse', fill: 'gray', size: 18 },
      { id: 'llm', x: 40, y: 190, w: 380, h: 200, label: 'model chain (decide only)', fill: 'violet', items: [
        'Claude Haiku 4.5 on Vertex (Pro, Plus)', '→ Groq gpt-oss-120b → 20b → qwen3', '→ Gemini 3.5 Flash → 3.1 Flash-Lite',
        'max_retries=0: a 429 falls through in ms', 'circuit breaker: 3 fails → 60 s open', 'optional TypeSafe Jev for bounded picks'] },
      { id: 'ext', x: 40, y: 450, w: 340, h: 185, label: 'Chrome extension', fill: 'orange', items: [
        'snapshot: ≤120 numbered elements', 'PII masked before upload', 'runs the action in your real tab', 'safety.ts mirrors the server rules', '≤8 masked JPEG screenshots'] },
      { id: 'db', x: 40, y: 700, w: 340, h: 170, label: 'Postgres checkpointer', shape: 'db', fill: 'teal', sub: 'schema walkthru_checkpoints\nthread_id = run_id\nsaved at every interrupt()\nAPI stays stateless' },
      { id: 'n1', x: 1210, y: 175, w: 360, h: 245, label: '_enforce(): code, not prompt', fill: 'yellow', hatch: true, items: [
        'element not on page → scroll instead', 'visitor mode: a form, like, follow,', '   post, buy or cart → stop by design',
        'pay / delete / cancel → safe_stop', 'send: verified domain, once, owner', '   confirms in the side panel', 'empty "type" → test identity value'] },
      { id: 'n2', x: 1210, y: 450, w: 360, h: 200, label: 'progress is evidence-based', fill: 'pink', hatch: true, items: [
        'goal planner turns the goal into', '   1-4 checkpoints (one LLM call)', 'plan_done moves only when the last',
        '   action visibly worked (URL changed', '   or a confirmation appeared)'] },
      { id: 'n3', x: 1210, y: 680, w: 360, h: 220, label: 'terminal statuses', fill: 'gray', hatch: true, items: [
        'done · safe_stop          → site OK', 'gave_up · stuck · budget  → site problem', 'looping · agent_lost      → our limit',
        'captcha · bot_wall        → site protection', 'stopped                   → owner pressed Stop', '(report never blames the site for ours)'] },
    ],
    edges: [
      { from: 'start', to: 'decide', fs: 'b', ts: 't' },
      { from: 'decide', to: 'act', fs: 'b', ts: 't', label: 'click · type · scroll · back', dx: 0 },
      { from: 'act', to: 'check', fs: 'b', ts: 't', label: 'observation in' },
      { from: 'decide', to: 'check', fs: 'r:0.3', ts: 'r:0.3', via: [[1075, 264], [1075, 738]], label: 'done / give_up', at: 0, dy: -15, dx: 15 },
      { from: 'check', to: 'decide', fs: 'r:0.8', ts: 'r:0.8', via: [[1135, 818], [1135, 354]], label: 'status = running', at: 0, dy: 16, dx: 20 },
      { from: 'check', to: 'end', fs: 'b', ts: 't', label: 'any terminal status' },
      { from: 'decide', to: 'llm', fs: 'l:0.5', ts: 'r:0.5', label: 'PersonaStep', both: true },
      { from: 'act', to: 'ext', fs: 'l:0.3', ts: 'r:0.32', label: 'next action', dy: -14, dashed: true },
      { from: 'ext', to: 'act', fs: 'r:0.78', ts: 'l:0.85', label: 'observation', dy: 16, dashed: true },
      { from: 'db', to: 'act', start: [380, 785], end: [500, 785], dashed: true, label: 'state', dy: -14, both: true },
    ],
  },

  'langgraph-report': {
    w: 1600, h: 910,
    title: 'report graph: deterministic scans fan out, the model writes last',
    subtitle: 'apps/api/app/agent/report.py  ·  used for finished journeys and for Instant Scans  ·  blue = plain code, violet = model call',
    nodes: [
      { id: 'start', x: 40, y: 420, w: 120, h: 50, label: 'START', shape: 'ellipse', fill: 'gray', size: 18 },
      { id: 'fi', x: 250, y: 130, w: 360, h: 120, label: 'first_impression', fill: 'violet', sub: 'model call · FirstImpression schema\nwhat a stranger gets in five seconds' },
      { id: 'acc', x: 250, y: 285, w: 360, h: 110, label: 'accessibility_scan', fill: 'blue', sub: 'axe-core WCAG A/AA from the real tab,\nserver basics for an Instant Scan' },
      { id: 'site', x: 250, y: 430, w: 360, h: 220, label: 'site_scan', fill: 'blue', items: [
        'assert_public(), then one bounded crawl', '10 pages free · 50 paid · robots.txt', 'seo · seo_depth · geo · geo_depth',
        'security · csp · tls · secrets', 'libraries (retire.js) · takeover · backend', 'email DNS: SPF · DKIM · DMARC'] },
      { id: 'stack', x: 250, y: 715, w: 360, h: 110, label: 'stack_scan', fill: 'blue', sub: 'framework + backend fingerprint,\nso fixes match your framework' },
      { id: 'perf', x: 700, y: 500, w: 300, h: 120, label: 'performance_scan', fill: 'blue', sub: 'PageSpeed Insights (mobile)\n+ Core Web Vitals from the tab' },
      { id: 'syn', x: 1080, y: 300, w: 330, h: 200, label: 'synthesize', fill: 'violet', items: [
        'one model call: Synthesis schema', 'careful-writer chain (Groq →', '   OpenRouter Nemotron → Gemini)', 'summary · UX findings · top fixes'] },
      { id: 'end', x: 1450, y: 375, w: 120, h: 50, label: 'END', shape: 'ellipse', fill: 'gray', size: 18 },
      { id: 'ground', x: 1060, y: 560, w: 500, h: 260, label: 'then plain code (it cannot invent)', fill: 'yellow', hatch: true, items: [
        'grounded_ux(): a UX finding must point at a real', '   step and its evidence, or it is dropped', 'code findings are added verbatim, sorted by severity',
        'launch_ready(): ux 30 · security 20 · geo 20 ·', '   seo 15 · speed 15; ignored findings still count', 'agent_ready(): can an AI agent use this site?', 'unmeasured areas say "not measured", never 0'] },
    ],
    edges: [
      { from: 'start', to: 'fi', fs: 'r', ts: 'l' }, { from: 'start', to: 'acc', fs: 'r', ts: 'l' },
      { from: 'start', to: 'site', fs: 'r', ts: 'l' }, { from: 'start', to: 'stack', fs: 'r', ts: 'l' },
      { from: 'site', to: 'perf', fs: 'r:0.5', ts: 'l', label: 'crawled pages' },
      { from: 'fi', to: 'syn', fs: 'r', ts: 'l:0.2' }, { from: 'acc', to: 'syn', fs: 'r', ts: 'l:0.45' },
      { from: 'perf', to: 'syn', fs: 'r', ts: 'l:0.75' },
      { from: 'stack', to: 'syn', fs: 'r', ts: 'l:0.95', via: [[1040, 770], [1040, 490]] },
      { from: 'syn', to: 'end', fs: 'r:0.475', ts: 'l' },
      { from: 'syn', to: 'ground', fs: 'b:0.4', ts: 't:0.33', dashed: true },
    ],
    texts: [{ x: 40, y: 880, text: 'Every scan fails soft: a scan that errors marks its area "unavailable" and the report still ships.', size: 16, color: '#495057', anchor: 'start' }],
  },

  'architecture': {
    w: 1600, h: 1070,
    title: 'Walkthru: browser on your machine, brain on the server',
    subtitle: 'no Chromium on our servers  ·  logged-in pages work without sharing a password  ·  the API is stateless between calls',
    groups: [
      { x: 30, y: 150, w: 440, h: 880, label: 'your machine', color: '#e8590c' },
      { x: 530, y: 150, w: 520, h: 880, label: 'Walkthru API · FastAPI + LangGraph', color: '#1971c2' },
      { x: 1110, y: 150, w: 460, h: 420, label: 'Supabase', color: '#0c8599' },
    ],
    nodes: [
      { id: 'web', x: 60, y: 190, w: 380, h: 150, label: 'web app', fill: 'blue', items: ['React 19 · Vite · Tailwind v4 · GSAP', 'Vercel, strict CSP', 'dashboard · reports · teams · keys'] },
      { id: 'ext', x: 60, y: 400, w: 380, h: 250, label: 'Chrome extension · MV3 · WXT', fill: 'orange', items: [
        'side panel: site, goal, test user', 'background: session, retries, keys', 'page script: snapshot · redact ·', '   axe-core · Core Web Vitals',
        'execute with safety.ts gates', 'JPEG evidence → Storage (own JWT)'] },
      { id: 'tab', x: 60, y: 690, w: 380, h: 110, label: 'your site, in a real tab', fill: 'white', dashed: true, sub: 'cookies and logins never leave the browser' },
      { id: 'editor', x: 60, y: 850, w: 380, h: 150, label: 'Claude Code · Cursor', fill: 'pink', items: ['any MCP client', 'scan → fix → PR → verify, from the editor'] },
      { id: 'routes', x: 560, y: 190, w: 460, h: 170, label: 'HTTP edge', fill: 'gray', items: [
        'require_user: Supabase JWT, hashed cache', 'limits: Postgres window per route', 'idempotency ledger on run mutations', 'CORS: web origin + extension only'] },
      { id: 'graphs', x: 560, y: 390, w: 220, h: 170, label: 'LangGraph', fill: 'blue', items: ['persona_session', 'report graph', 'goal planner'] },
      { id: 'scans', x: 800, y: 390, w: 220, h: 170, label: 'scanners', fill: 'blue', items: ['SSRF-safe fetch', 'SEO · GEO · security', 'a11y · perf · email'] },
      { id: 'mcp', x: 560, y: 590, w: 220, h: 150, label: '/mcp', fill: 'pink', items: ['24 tools', 'Bearer wt_ key', 'Plus plan'] },
      { id: 'jobs', x: 800, y: 590, w: 220, h: 150, label: 'jobs', fill: 'green', items: ['Postgres queue', 'SKIP LOCKED leases', 'retries + backoff'] },
      { id: 'teams', x: 560, y: 770, w: 220, h: 150, label: 'teams + Scout', fill: 'yellow', items: ['roles, invites', 'findings board', '@Scout answers'] },
      { id: 'billing', x: 800, y: 770, w: 220, h: 150, label: 'billing · watch', fill: 'yellow', items: ['Dodo webhooks', 'weekly re-scan', 'deploy hooks'] },
      { id: 'pg', x: 1140, y: 190, w: 400, h: 210, label: 'Postgres', shape: 'db', fill: 'teal', sub: 'RLS on every table\nruns · teams · jobs · rate limits\nrun_requests (idempotency)\nwalkthru_checkpoints (private)' },
      { id: 'auth', x: 1140, y: 430, w: 120, h: 120, label: 'Auth', fill: 'teal', size: 18, sub: 'Google\nGitHub\nmagic link' },
      { id: 'storage', x: 1280, y: 430, w: 130, h: 120, label: 'Storage', fill: 'teal', size: 18, sub: 'evidence\nprivate\n1 h URLs' },
      { id: 'rt', x: 1430, y: 430, w: 120, h: 120, label: 'Realtime', fill: 'teal', size: 18, sub: 'team\nnudges' },
      { id: 'llm', x: 1140, y: 610, w: 410, h: 140, label: 'model providers', fill: 'violet', items: ['Claude Haiku 4.5 · Vertex (paid tiers)', 'Groq gpt-oss · OpenRouter · Gemini', 'per-provider circuit breaker'] },
      { id: 'out', x: 1140, y: 790, w: 410, h: 210, label: 'outside services', fill: 'gray', items: [
        'your site: passive reads only', 'PageSpeed Insights · DNS', 'GitHub App: repo-scoped fix PRs', 'Resend: report + invite email', 'Dodo Payments: signed webhooks'] },
    ],
    edges: [
      { from: 'web', to: 'pg', start: [250, 190], via: [[250, 122], [1340, 122]], end: [1340, 190], label: 'reads its own rows under RLS (publishable key)', at: 1, dashed: true },
      { from: 'web', to: 'routes', fs: 'r:0.5', ts: 'l:0.3', label: 'writes' },
      { from: 'web', to: 'ext', fs: 'b', ts: 't', label: 'session handoff', dashed: true },
      { from: 'ext', to: 'routes', fs: 'r:0.15', ts: 'l:0.7', label: 'runs API', both: true },
      { from: 'ext', to: 'tab', fs: 'b', ts: 't', label: 'snapshot · act', both: true },
      { from: 'editor', to: 'mcp', fs: 'r:0.4', ts: 'l:0.5', via: [[500, 910], [500, 665]], label: 'MCP', at: 1 },
      { from: 'routes', to: 'pg', fs: 'r:0.3', ts: 'l:0.25', label: 'secret key' },
      { from: 'jobs', to: 'llm', fs: 'r:0.5', ts: 'l:0.43', label: 'structured output' },
      { from: 'scans', to: 'out', fs: 'r:0.8', ts: 'l:0.3', via: [[1080, 526], [1080, 853]], label: 'passive reads', lp: [1080, 590] },
      { from: 'billing', to: 'out', fs: 'r:0.5', ts: 'l:0.65' },
    ],
    texts: [{ x: 790, y: 975, text: 'all durable state lives in Postgres', size: 15, color: '#495057' }],
  },

  'run-step-sequence': seq(),

  'mcp': {
    w: 1600, h: 960,
    title: 'Remote MCP server: your coding agent drives Walkthru',
    subtitle: 'apps/api/app/mcp_server.py  ·  streamable HTTP at /mcp, stateless JSON  ·  same plan checks, limits and grounding as the web API',
    nodes: [
      { id: 'editor', x: 40, y: 150, w: 320, h: 200, label: 'Claude Code · Cursor', fill: 'pink', items: ['any MCP client', 'one HTTP request per tool call', 'key from Settings → API keys', 'shown once, revocable'] },
      { id: 'gate', x: 430, y: 140, w: 390, h: 250, label: 'Endpoint (ASGI gate)', fill: 'gray', items: [
        '1  no wt_ prefix → 401', '2  SHA-256(key) → owner, else 401', '3  require_plus(owner) → 402', '4  limits.apply("mcp", key id) → 429',
        '5  record last use, bind user to logs', '6  contextvar user → MCPServer'] },
      { id: 'server', x: 880, y: 140, w: 680, h: 80, label: 'MCPServer("Walkthru")  ·  24 tools', fill: 'violet' },
      { id: 't1', x: 880, y: 245, w: 215, h: 200, label: 'reports', fill: 'blue', size: 18, itemSize: 14, lh: 20, items: ['scan_site', 'get_report', 'list_runs', 'rerun', 'compare_sites', 'share_report', 'get_plan'] },
      { id: 't2', x: 1112, y: 245, w: 215, h: 200, label: 'findings', fill: 'green', size: 18, itemSize: 14, lh: 20, items: ['get_finding', 'verify_finding', 'accept_finding', 'reopen_finding', 'get_fix_prompt'] },
      { id: 't3', x: 1345, y: 245, w: 215, h: 200, label: 'ownership', fill: 'yellow', size: 18, itemSize: 14, lh: 20, items: ['get_site_verification', '', 'meta tag for <head>,', 'checked once deployed;', 'unlocks owner-only', 'security checks'] },
      { id: 't4', x: 880, y: 465, w: 215, h: 180, label: 'GitHub', fill: 'orange', size: 18, itemSize: 14, lh: 20, items: ['list_github_repos', 'open_fix_pull_request', '', 'preview first,', 'confirm=true opens it'] },
      { id: 't5', x: 1112, y: 465, w: 215, h: 180, label: 'AI answers', fill: 'violet', size: 18, itemSize: 14, lh: 20, items: ['list_ai_answer_sites', 'track_ai_answers', 'get_ai_answers', 'set_ai_prompts', 'check_ai_answers_now'] },
      { id: 't6', x: 1345, y: 465, w: 215, h: 180, label: 'weekly watch', fill: 'teal', size: 18, itemSize: 14, lh: 20, items: ['list_watched_sites', 'watch_site', 'check_watched_site_now', 'create_deploy_hook'] },
      { id: 'guard', x: 40, y: 420, w: 360, h: 230, label: 'guarantees', fill: 'yellow', hatch: true, items: [
        'every run id is checked against the', '   key owner, else "no run with that id"', 'ToolError text reaches the agent;', '   other errors stay hidden',
        '50 MCP scans a day per Plus user', 'instructions: never invent findings'] },
      { id: 'gh', x: 440, y: 440, w: 380, h: 210, label: 'Walkthru GitHub App', fill: 'orange', hatch: true, items: [
        'stores the installation id only', 'token minted per action, one repo', 'recipes.json: headers, llms.txt, ai.txt', 'creates or appends, never rewrites', 'never merges: you review'] },
      { id: 'l1', x: 60, y: 760, w: 240, h: 70, label: 'scan_site', fill: 'blue', size: 19 },
      { id: 'l2', x: 360, y: 760, w: 240, h: 70, label: 'get_fix_prompt', fill: 'green', size: 19 },
      { id: 'l3', x: 660, y: 760, w: 240, h: 70, label: 'agent edits code', fill: 'white', size: 19, dashed: true },
      { id: 'l4', x: 960, y: 760, w: 260, h: 70, label: 'open_fix_pull_request', fill: 'orange', size: 19 },
      { id: 'l5', x: 1280, y: 760, w: 280, h: 70, label: 'deploy → verify_finding', fill: 'green', size: 19 },
    ],
    edges: [
      { from: 'editor', to: 'gate', fs: 'r:0.3', ts: 'l:0.24', label: 'POST /mcp', dy: -14 },
      { from: 'gate', to: 'server', fs: 'r:0.15', ts: 'l:0.5' },
      { from: 't4', to: 'gh', fs: 'l:0.6', ts: 'r:0.45', label: 'fix PR' },
      { from: 'l1', to: 'l2' }, { from: 'l2', to: 'l3' }, { from: 'l3', to: 'l4' }, { from: 'l4', to: 'l5' },
      { from: 'l5', to: 'l1', fs: 'b', ts: 'b', via: [[1420, 890], [180, 890]], label: 'rerun compares by fingerprint: fixed · still broken · new', at: 1 },
    ],
    texts: [{ x: 40, y: 725, text: 'the editor loop', size: 22, anchor: 'start', weight: 700 }],
  },

  'security-layers': layers(),

  'teams': {
    w: 1600, h: 960,
    title: 'Team workspaces: API writes, RLS reads, Realtime nudges',
    subtitle: 'apps/api/app/teams.py  ·  docs/team-collaboration.md  ·  no new dependencies: stdlib + supabase-js Realtime',
    nodes: [
      { id: 'browser', x: 40, y: 160, w: 340, h: 290, label: 'browser (React)', fill: 'blue', items: ['/app/team/:id/:tab', '/join#CODE', 'shared report page', 'supabase-js Realtime', 'no socket? poll: chat 5 s,', '   page 30 s'] },
      { id: 'api', x: 500, y: 160, w: 560, h: 330, label: 'API · app/teams.py', fill: 'yellow', items: [
        'membership + role read on every request', '   (never cached, never from the client)', 'non-member → 404: an id reveals nothing',
        "owner's plan ended → read-only, writes 402", 'invite codes: 120 random bits, shown once,', '   stored as SHA-256; email invites single-use',
        'links: email-domain lock, max uses, expiry', 'bidi + zero-width characters stripped', 'client_id unique → a retried send lands once'] },
      { id: 'pg', x: 1160, y: 160, w: 400, h: 350, label: 'Postgres', shape: 'db', fill: 'teal', items: [
        'teams · team_members', 'team_invites (API only)', 'team_runs · team_findings', 'team_messages · team_events', 'RLS: is_team_member(team)', '     shared_with_me(run)',
        'team_join(): seats under a lock', 'team_transfer(): one transaction'] },
      { id: 'rt', x: 1160, y: 580, w: 400, h: 100, label: 'Realtime publication', fill: 'teal', sub: 'postgres_changes, members only (RLS)' },
      { id: 'scout', x: 500, y: 560, w: 560, h: 200, label: '@Scout in team chat', fill: 'pink', items: [
        'plain-code retrieval, no embeddings: question', '   words + named site pick findings and reports', 'one Gemini Flash-Lite call, its own key and quota',
        '50 answers per workspace a day · no tools', 'reads only what members can already read'] },
      { id: 'roles', x: 40, y: 520, w: 340, h: 250, label: 'roles', fill: 'gray', items: ['viewer: read, chat, comment', 'member: + share, triage', 'admin: + invite, roles, rename', 'owner: + hand over, delete', '3 seats · 3 owned workspaces', '30 invites/day · 30 msgs/min'] },
      { id: 'b1', x: 40, y: 840, w: 300, h: 76, label: 'report shared', fill: 'blue', size: 18 },
      { id: 'b2', x: 400, y: 840, w: 330, h: 76, label: 'fingerprint', fill: 'gray', size: 18, sub: 'site origin + rule id' },
      { id: 'b3', x: 790, y: 840, w: 380, h: 76, label: 'triage', fill: 'yellow', size: 18, sub: "open · in progress · fixed · won't fix" },
      { id: 'b4', x: 1230, y: 840, w: 330, h: 76, label: 'rerun still has it', fill: 'red', size: 18, sub: '"Found again after a fix"' },
    ],
    edges: [
      { from: 'browser', to: 'api', fs: 'r:0.3', ts: 'l:0.26', label: 'writes (JWT)', dy: -14 },
      { from: 'api', to: 'pg', fs: 'r:0.3', ts: 'l:0.28', label: 'secret key' },
      { from: 'browser', to: 'pg', start: [210, 160], via: [[210, 124], [1360, 124]], end: [1360, 160], label: 'select under RLS: reports, findings, chat · screenshots via signed URLs', at: 1, dashed: true },
      { from: 'pg', to: 'rt', fs: 'b', ts: 't' },
      { from: 'rt', to: 'browser', fs: 'b', ts: 'r:0.85', via: [[1360, 800], [450, 800], [450, 406]], label: 'nudge → refetch through the API', at: 1, dashed: true },
      { from: 'api', to: 'scout', fs: 'b:0.5', ts: 't:0.5', label: '@Scout mention → job queue' },
      { from: 'b1', to: 'b2' }, { from: 'b2', to: 'b3' }, { from: 'b3', to: 'b4' },
    ],
  },
};

// One observe call, end to end, as a hand-drawn sequence diagram.
function seq() {
  const lanes = { panel: [110, 'side panel +\nbackground'], page: [360, 'page script\n(your tab)'], api: [630, 'FastAPI\n/observe'], pg: [890, 'Postgres'], lg: [1150, 'LangGraph\nthread'], llm: [1430, 'model chain'] };
  const fills = { panel: 'orange', page: 'orange', api: 'yellow', pg: 'teal', lg: 'blue', llm: 'violet' };
  const msgs = [
    ['panel', 'page', 'snapshot(): elements, text, axe, vitals'],
    ['page', 'panel', 'Observation (PII masked in the page)', 1],
    ['panel', 'api', 'POST /runs/{id}/observe · Idempotency-Key'],
    ['api', 'api', 'require_user · rate limit · body hash'],
    ['api', 'pg', 'claim key (per-account advisory lock)'],
    ['api', 'api', 'kill switch · blocked host · signed-in?'],
    ['api', 'lg', 'invoke(Command(resume=obs))'],
    ['lg', 'pg', 'load checkpoint (thread_id = run_id)'],
    ['lg', 'lg', 'act → check → decide'],
    ['lg', 'llm', 'prompt → PersonaStep'],
    ['llm', 'lg', 'structured output (fallbacks)', 1],
    ['lg', 'lg', '_enforce() → interrupt()'],
    ['lg', 'pg', 'save checkpoint'],
    ['lg', 'api', '__interrupt__: next action', 1],
    ['api', 'pg', 'complete claim (reply kept 24 h)'],
    ['api', 'panel', '{ status: running, action }', 1],
    ['panel', 'page', 'execute action (safety.ts) · JPEG → Storage'],
  ];
  const nodes = Object.entries(lanes).map(([id, [x, label]]) => ({ id, x: x - 100, y: 115, w: 200, h: 66, label, fill: fills[id], size: 18 }));
  const lines = Object.values(lanes).map(([x]) => ({ pts: [[x, 181], [x, 1080]] }));
  const edges = msgs.map(([a, b, label, back], i) => {
    const y = 225 + i * 51, xa = lanes[a][0], xb = lanes[b][0];
    if (a === b) return { from: a, to: b, start: [xa, y - 10], via: [[xa + 60, y - 10], [xa + 60, y + 14]], end: [xa + 4, y + 14], label, lp: [xa + 72, y + 2], anchor: 'start', labelColor: '#1e1e1e' };
    return { from: a, to: b, start: [xa, y], end: [xb, y], label, dashed: !!back, dy: -13, at: 0, labelColor: back ? '#2f9e44' : '#1971c2' };
  });
  return { w: 1600, h: 1100, title: 'one agent step, end to end', subtitle: 'POST /runs/{id}/observe  ·  no database transaction stays open while the model runs  ·  a browser action is never retried, only the HTTP request',
    nodes, lines, edges };
}

// Defense in depth, outside (the browser) to inside (the data).
function layers() {
  const bands = [
    ['1 · extension', 'in your browser', 'orange', [
      'host access requested per site (optional_host_permissions)', 'PII masked in the page: emails, 8+ digit numbers, keys', 'typed values never leave the tab; screenshots hide fields',
      'never reads cookies, storage, history or other tabs', 'externally_connectable: only the web origin hands a session', 'at most 8 JPEGs, uploaded under your own JWT']],
    ['2 · session + transport', 'every request', 'yellow', [
      '30 s one-use challenge links web app and extension', 'JWT checked; SHA-256-keyed cache ≤300 s, never past expiry', 'Idempotency-Key bound to a body hash, 409 on reuse',
      'CORS: the web origin and the extension only', "web CSP: script-src 'self', frame-ancestors 'none'", 'rate limits in Postgres: address, account, route, key']],
    ['3 · run policy', 'before a run starts', 'green', [
      'blocklist: banking, trading, gov, health, webmail, social', 'goal rules run on NFKC-folded, zero-width-free text', 'bulk goals refused ("like every post", "20 accounts")',
      'owner mode needs domain proof: meta tag, file or DNS TXT', 'logged-in pages need a verified domain', 'proof re-checked at every run']],
    ['4 · every step', 'decided in code', 'blue', [
      '_enforce(): pay, delete, cancel → safe stop', 'send only on a verified domain, once, owner confirms', 'blocked host reached or signed-in unverified → stop',
      'kill switches re-read mid-run (account or host)', '20 journeys/h per host · 12/h per user and host', '5 refusals a day → automatic pause · 90-day audit log']],
    ['5 · scanner', 'server-side reads', 'violet', [
      'SSRF guard: resolve once, pin the IP, refuse private', 'IPv4 inside IPv6 (mapped, 6to4, Teredo, NAT64) refused', 'cloud metadata IPs refused · every redirect re-checked',
      '2 concurrent requests per host · 30 scans/host/hour', 'exposed files, JS keys, source maps: verified only', 'robots.txt honoured · WalkthruBot UA + opt-out page']],
    ['6 · data', 'at rest', 'teal', [
      'RLS on every table; browsers get select only', 'private evidence bucket · 1 h signed URLs · 30-day purge', 'API keys, deploy hooks, invite codes stored as SHA-256',
      'agent checkpoints in a private, non-REST schema', 'export everything · delete: files first, rows last', 'runs never train models; models see masked text only']],
    ['7 · supply chain + ops', 'how we ship', 'red', [
      'requirements.lock pinned · migrations checksummed', 'CI: npm audit, pip-audit, gitleaks on every push', 'licence check before reuse (no AGPL, no unlicensed)',
      'admin panel on 127.0.0.1 only: password + TOTP', 'production refuses to start without durable checkpoints', 'secrets only in env files that are never committed']],
  ];
  const nodes = bands.flatMap(([label, sub, fill, items], i) => {
    const y = 120 + i * 132;
    return [
      { id: `l${i}`, x: 40, y, w: 300, h: 118, label, sub, fill, size: 21 },
      { id: `b${i}`, x: 360, y, w: 1200, h: 118, label: '', fill: 'white', items, cols: 2, lh: 30 },
    ];
  });
  return { w: 1600, h: 1060, title: 'Defense in depth: a prompt is never the safety boundary', subtitle: 'outside (your browser) to inside (the data)  ·  every rule below is code with tests, not an instruction to the model', nodes };
}

