import { Link } from 'react-router'
import { brand } from '../brand'
import { contact } from '../content'
import { DocLayout, type DocSection } from '../components/DocLayout'
import { EVIDENCE_RETENTION_DAYS } from '../lib/runs'

const permissions = [
  ['sidePanel', 'Shows the test controls and live steps beside the page.'],
  ['activeTab and tabs', 'Reads the address of the tab you start a test in, and follows it as the test user navigates.'],
  ['scripting', 'Adds the page reader and Scout to that tab when a test starts. Nothing runs on other tabs.'],
  ['Screenshot access (asked once)', 'Chrome only allows screenshots of a tab with broad site access. It is requested when you first start a test, and used only for the tab under test.'],
] as const

const sections: DocSection[] = [
  {
    id: 'principles',
    title: 'How we think about it',
    body: (
      <ul>
        <li><strong>Your browser, your session.</strong> Tests run in the tab you are already signed in to. You never give us a password for your site.</li>
        <li><strong>Least data.</strong> The extension sends a masked text outline of the page, not the page itself.</li>
        <li><strong>Rules in code.</strong> Safe mode, site boundaries and step limits are enforced by deterministic code on both the extension and the server, not by the AI.</li>
        <li><strong>Passive checks only.</strong> We never send attack payloads to your site.</li>
      </ul>
    ),
  },
  {
    id: 'extension',
    title: 'Extension permissions',
    body: (
      <>
        <p>Every permission the extension asks for, and why:</p>
        <dl>
          {permissions.map(([name, why]) => (
            <div key={name}>
              <dt><code>{name}</code></dt>
              <dd>{why}</dd>
            </div>
          ))}
        </dl>
        <p>A run stops if the test user leaves the site you started on, after 12 steps or after 4 minutes.</p>
      </>
    ),
  },
  {
    id: 'scanning',
    title: 'What our scanner does',
    body: (
      <>
        <p>The security check is a hygiene review, not a penetration test. It reads response headers, https redirects and, on verified domains only, a handful of well-known public paths and your JavaScript bundles, using ordinary page requests. It follows at most 10 same-site links (50 on paid plans) while honouring <code>robots.txt</code>.</p>
        <p>Checks for exposed files and keys leaked into JavaScript only run on domains whose owner has <Link to="/docs#verify">verified them</Link>. The scanner refuses private and local network addresses, and re-checks every redirect before following it.</p>
      </>
    ),
  },
  {
    id: 'data',
    title: 'Protecting your data',
    body: (
      <ul>
        <li>Production web and API traffic uses HTTPS. Private API calls require your signed-in session; public scans and shared reports have separate access rules.</li>
        <li>Database rows are protected by row-level security, so each account can only read its own runs.</li>
        <li>Screenshots are stored privately and shown through links that expire after an hour. They are deleted after {EVIDENCE_RETENTION_DAYS} days.</li>
        <li>Deleting your account removes stored files first, then run history, then the account, so nothing is left behind unreachable.</li>
        <li>API keys for the MCP server and deploy-hook URLs are shown once and stored only as SHA-256 fingerprints. Each key can reach only its owner's runs, every call re-checks the plan, and a key can be revoked at once from the MCP page. Deploy hooks run at most one check every 10 minutes.</li>
      </ul>
    ),
  },
  {
    id: 'disclosure',
    title: 'Report a vulnerability',
    body: (
      <>
        <p>If you find a security problem in {brand.name}, email <a href={`mailto:${contact.security}`}>{contact.security}</a> with the steps to reproduce it and the impact you expect. We will confirm we received it within three business days and keep you updated until it is fixed.</p>
        <p>Please test only against your own account, avoid touching other people's data, and give us a reasonable time to fix the issue before sharing it. We will not take action against good-faith research that follows these rules.</p>
      </>
    ),
  },
]

export default function Security() {
  return (
    <DocLayout
      title="Security"
      lead={`${brand.name} drives a real browser on sites you care about. Here is exactly what it can touch, what it cannot, and how to reach us if something looks wrong.`}
      updated="2026-09-25"
      sections={sections}
    />
  )
}
