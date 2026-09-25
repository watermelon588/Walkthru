import { Link } from 'react-router'
import { brand } from '../brand'
import { contact } from '../content'
import { DocLayout, type DocSection } from '../components/DocLayout'
import { EVIDENCE_RETENTION_DAYS, MCP_URL, PERSONA_LABEL } from '../lib/runs'

const personas = [
  ['first_timer', 'Has never heard of your product, skims and gets impatient fast. Catches unclear headlines and too many steps.'],
  ['phone_user', 'On a small screen, taps big obvious things and hates long forms. Catches cramped layouts and tiny targets.'],
  ['buyer', 'Deciding whether to pay. Looks for pricing, trust and what happens next. Catches hidden costs and missing proof.'],
  ['skeptic', 'A cautious developer who reads error messages, checks links and distrusts vague copy. Catches silent failures.'],
] as const

const sections: DocSection[] = [
  {
    id: 'overview',
    title: 'Overview',
    body: (
      <>
        <p>{brand.name} shows you where a first-time visitor would get stuck on your site. There are two ways to use it.</p>
        <dl>
          <dt>Instant Scan</dt>
          <dd>Paste an address and get a report in about 20 seconds. No account and no install. It reads your public pages and checks first impression, SEO basics and passive security headers.</dd>
          <dt>Test runs</dt>
          <dd>An AI test user works through a real goal, like signing up, in your own browser tab. The Chrome extension clicks and types; our server decides every step and notes where the test user got confused.</dd>
        </dl>
        <p>Both end in the same report: what happened, the evidence, and the fixes worth doing first.</p>
      </>
    ),
  },
  {
    id: 'instant-scan',
    title: 'Run an Instant Scan',
    body: (
      <>
        <ol>
          <li>Go to the <Link to="/#scan">scan form</Link> on the home page, or the Instant Scan panel in your dashboard.</li>
          <li>Enter your address, like <code>yoursite.com</code>.</li>
          <li>Select <strong>Scan my site</strong>. The report opens when it is ready.</li>
        </ol>
        <p>The scan follows up to 10 same-site links from your homepage, honours <code>robots.txt</code> and only sends ordinary page requests. Pages that are built entirely by JavaScript are marked as checked "before JavaScript runs", so you know what was and was not measured.</p>
        <p>Each network address can run five Instant Scans an hour. Scan reports get a public link so you can share them.</p>
      </>
    ),
  },
  {
    id: 'install',
    title: 'Install the extension',
    body: (
      <>
        <p>Test runs need the {brand.name} Chrome extension. During the beta you load it yourself: download the zip you were sent, unzip it, open <code>chrome://extensions</code>, turn on Developer mode and choose Load unpacked.</p>
        <ol>
          <li>Add {brand.name} to Chrome and pin the bird to your toolbar.</li>
          <li><Link to="/login">Sign in</Link> to your dashboard with Google, GitHub or an email link.</li>
          <li>On the dashboard, select <strong>Connect extension</strong>. This hands your session to the extension so it can start runs as you. Nothing else receives it.</li>
        </ol>
        <p>The extension only acts on the tab you start a test in. See <Link to="/security#extension">extension permissions</Link> for what each permission is used for.</p>
      </>
    ),
  },
  {
    id: 'run-a-test',
    title: 'Run a test',
    body: (
      <>
        <ol>
          <li>Open the site you want tested in a normal Chrome tab. If the goal needs an account, sign in to your site first.</li>
          <li>Select the bird in the toolbar. The side panel opens beside the page.</li>
          <li>Write a goal in plain words and pick a test user.</li>
          <li>Tick <strong>This is a logged-in page</strong> when testing a dashboard or account area. The test user will ask you before submitting any form there.</li>
          <li>Select <strong>Start test</strong>. The first time, Chrome asks for permission to capture screenshots of the tested tab.</li>
        </ol>
        <p>You will see each step and the test user's thoughts in the panel, and Scout, the {brand.name} bird, in the corner of the page. A free run stops after 12 steps; paid plans allow up to 30. Runs also stop when the goal is reached, after 4 minutes, or if the test user leaves your site. Select <strong>Stop</strong> at any time; the steps so far still become a report.</p>
      </>
    ),
  },
  {
    id: 'test-users',
    title: 'Choose a test user',
    body: (
      <>
        <p>Each test user behaves like a real kind of visitor, so they get stuck in different places. Try more than one on the same goal.</p>
        <dl>
          {personas.map(([key, body]) => (
            <div key={key}>
              <dt>{PERSONA_LABEL[key]}</dt>
              <dd>{body}</dd>
            </div>
          ))}
        </dl>
        <p>On the Plus plan you can also describe your own test users in <Link to="/app/settings#test-users">Settings</Link> (up to 10), and tick several in the extension. They run one after another on the same goal, each starting on the same page, and every report of the set shows them side by side with the problems more than one of them hit. Each test user uses one run.</p>
      </>
    ),
  },
  {
    id: 'goals',
    title: 'Write a good goal',
    body: (
      <>
        <p>A goal is what a real visitor came to do. Keep it to one outcome the test user can recognise when it happens.</p>
        <ul>
          <li><strong>Good:</strong> "Sign up for a free account", "Find the price of the Pro plan", "Send a message through the contact form".</li>
          <li><strong>Too vague:</strong> "Test the site", "Check everything".</li>
          <li><strong>Too many goals:</strong> "Sign up, create a project, invite a teammate and upgrade". Split this into separate runs.</li>
        </ul>
      </>
    ),
  },
  {
    id: 'safe-mode',
    title: 'Safe mode',
    body: (
      <>
        <p>Safe mode is always on. It is enforced in code, not left to the AI.</p>
        <ul>
          <li>Never clicks buttons that pay, delete or cancel.</li>
          <li>Never opens <code>mailto:</code> or <code>tel:</code> links. It records them as working contact methods.</li>
          <li>On logged-in pages, asks you in the side panel before submitting any form.</li>
          <li>Buttons that send or invite only run on a <a href="#verify">verified domain</a>, after you approve in the side panel, and at most once per run. Everywhere else the run ends as "Stopped before sending".</li>
          <li>Stops at a CAPTCHA. It never tries to solve one.</li>
        </ul>
        <p>For dashboard tests we still recommend a test account with sample data.</p>
      </>
    ),
  },
  {
    id: 'verify',
    title: 'Verify your domain',
    body: (
      <>
        <p>Verifying proves you own a site. It unlocks the full security check (exposed files and backups, keys leaked into JavaScript, public source maps and subdomain takeover) and lets approved send actions run during tests.</p>
        <ol>
          <li>Open <Link to="/app/settings#verify">Settings</Link> and copy your verification tag.</li>
          <li>Add it to the <code>&lt;head&gt;</code> of your homepage, or put the token alone in a file at <code>/.well-known/walkthru.txt</code>.</li>
          <li>Run a new scan or test. Verification is checked each time.</li>
        </ol>
        <pre><code>{'<meta name="walkthru-verification" content="your-token">'}</code></pre>
        <p>The token is tied to your account, so one tag verifies every site you add it to.</p>
      </>
    ),
  },
  {
    id: 'reports',
    title: 'Read a report',
    body: (
      <>
        <p>Every report leads with a summary and three numbers: findings by severity, the outcome, and the peak confusion (0 to 3) with the step where it first appeared.</p>
        <ul>
          <li><strong>Journey replay</strong> steps through what the test user saw and did, with screenshots and per-step accessibility and speed checks.</li>
          <li><strong>Launch checks</strong> show SEO, security, accessibility and performance, kept apart from what the test user observed.</li>
          <li><strong>Fix these first</strong> lists the fixes in priority order, P01 first.</li>
          <li><strong>All findings</strong> are marked high, medium or low, each with a suggested fix and the evidence behind it.</li>
        </ul>
        <p>From a report you can share a public link, export findings as CSV, save a PDF, email it to yourself or delete the run.</p>
        <p>On the Plus plan, add your name, logo and color under <Link to="/app/settings#branding">Settings, Branded PDF reports</Link>. Save PDF then prints your cover page and color with no Walkthru branding, ready to hand to a client. The report on screen does not change.</p>
        <p>If a run was interrupted, for example because the tab closed, it stays "Running". Select <strong>End and report</strong> to keep its steps and build a partial report.</p>
      </>
    ),
  },
  {
    id: 'watch',
    title: 'Weekly watch and deploy hooks',
    body: (
      <>
        <p>On the Plus plan, <Link to="/app/watch">Watch</Link> rechecks up to five of your sites every week: SEO, AI search readiness and passive security, the same checks as an Instant Scan. The first check sets a baseline; after that you hear from us only when something changed, for example a deploy that blocked AI crawlers, dropped structured data or reintroduced a missing header, and when a fix landed.</p>
        <p>To check right after every deploy, create a deploy hook for the site and send a POST to its URL from a Netlify deploy notification or a step at the end of your CI:</p>
        <pre><code>{'curl -X POST https://YOUR-WALKTHRU-API/hooks/deploy/wh_...'}</code></pre>
        <p>A site is checked at most once every 10 minutes, so a burst of deploys costs one check. Journeys are not part of watch; run those from the extension.</p>
      </>
    ),
  },
  {
    id: 'compare',
    title: 'Competitor side by side',
    body: (
      <>
        <p>On paid plans, <Link to="/app/compare">Compare</Link> runs your site and up to three competitors through the same checks and puts the results in one table: Launch Ready score, AI search readiness, SEO, security hygiene, speed and accessibility, findings and the first impression. The best value in each row is highlighted, and each site links to its full report.</p>
        <p>Competitors get public, passive checks only, the same way a search engine reads a page. Exposed-file and leaked-key checks never run on a site you have not verified. Each site counts toward your daily scan limit.</p>
      </>
    ),
  },
  {
    id: 'mcp',
    title: 'Connect your editor (MCP)',
    body: (
      <>
        <p>On the Plus plan, Claude Code, Cursor and other MCP clients can use Walkthru directly: scan a site, read a report, pull the fix prompt into the codebase they are editing, and rerun after the fixes.</p>
        <ol>
          <li>Open the <Link to="/app/mcp">MCP page</Link> and create an API key. Copy it right away: it is shown once.</li>
          <li>Add the server to your editor with the command or file that page shows you, for example in Claude Code:</li>
        </ol>
        <pre><code>{`claude mcp add --transport http walkthru ${MCP_URL} --header "Authorization: Bearer wt_..."`}</code></pre>
        <p>Tools: <code>scan_site</code>, <code>get_report</code>, <code>get_fix_prompt</code>, <code>get_finding</code>, <code>verify_finding</code>, <code>rerun</code> and <code>list_runs</code>. After fixing one finding, <code>verify_finding</code> re-checks just that finding on its pages, which is faster than a full rerun. They follow the same limits and honesty rules as the website, and each key can reach only your own runs. Journeys still run from the Chrome extension; <code>rerun</code> repeats the server-side checks.</p>
        <p>Revoke a key in Settings the moment you stop using it or think it leaked.</p>
      </>
    ),
  },
  {
    id: 'team',
    title: 'Team workspaces',
    body: (
      <>
        <p>On the Plus plan, <Link to="/app/team">Team</Link> gives your team, or your client, one shared place: the reports you share, a findings board where each problem gets a status and an owner, comment threads on reports and findings, and a chat that stays with the work. People you invite do not need a plan of their own.</p>
        <ul>
          <li><strong>Roles.</strong> The owner runs the workspace on their Plus plan. Admins invite and manage people. Members share reports and triage findings. Viewers read, chat and comment, which suits clients.</li>
          <li><strong>Invite by email</strong> for one person: the invitation works only for that address, once they confirm it, for 7 days. Or make an <strong>invite link</strong> with a code people can type, a number of uses, an end date and, if you like, your company's email domain.</li>
          <li><strong>Share a report</strong> with Share to workspace on its page, or turn on auto-share in the workspace settings so every new run, scan and watch check lands there.</li>
          <li><strong>Ask Scout.</strong> Write <code>@Scout</code> and a question in the chat, for example "what is still open on shop.example.com?". Scout answers in the thread from this workspace's shared reports, findings and recent messages only, and says which report it used. It is an AI answer, so check the report before acting on it. Up to 50 questions a workspace a day.</li>
          <li><strong>Findings board.</strong> One row per problem and site across all shared reports. A finding marked fixed that shows up again in a later report is flagged "Found again after a fix".</li>
        </ul>
        <p>A workspace has 3 seats, counting open email invitations. If the owner's Plus plan ends, the workspace stays readable but pauses chat, sharing, triage and invitations until the owner renews or hands it to a member on Plus. Reports someone shared stay when they leave; deleting a run removes it everywhere.</p>
      </>
    ),
  },
  {
    id: 'your-data',
    title: 'Your data',
    body: (
      <>
        <ul>
          <li>Emails, long numbers and typed values are masked in your browser before anything is sent.</li>
          <li>Screenshots mask form fields and are deleted {EVIDENCE_RETENTION_DAYS} days after each run.</li>
          <li>Runs and reports are kept until you delete them. Export or delete everything from <Link to="/app/settings">Settings</Link>.</li>
        </ul>
        <p>Full details are in the <Link to="/privacy">privacy policy</Link>.</p>
      </>
    ),
  },
  {
    id: 'troubleshooting',
    title: 'Troubleshooting',
    body: (
      <dl>
        <dt>The side panel says "Not connected"</dt>
        <dd>Open your dashboard in the same Chrome profile and select Connect extension.</dd>
        <dt>"Session expired"</dt>
        <dd>Sign in to the dashboard again and reconnect the extension.</dd>
        <dt>"Extension not found" on the dashboard</dt>
        <dd>Check that the extension is installed and enabled in <code>chrome://extensions</code>, then reload the dashboard.</dd>
        <dt>Screenshots were not captured</dt>
        <dd>Chrome's screenshot permission was declined. Start a new test and allow it. The run itself still works without screenshots.</dd>
        <dt>A run is stuck on "Running"</dt>
        <dd>Open it from the dashboard and select End and report.</dd>
        <dt>Still stuck?</dt>
        <dd>Email <a href={`mailto:${contact.hello}`}>{contact.hello}</a> with the report link and we will take a look.</dd>
      </dl>
    ),
  },
]

export default function Docs() {
  return (
    <DocLayout
      title="Documentation"
      lead={`Everything you need to run your first scan, test a real flow and act on the report.`}
      sections={sections}
    />
  )
}
