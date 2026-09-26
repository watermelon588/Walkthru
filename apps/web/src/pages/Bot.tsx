import { Link } from 'react-router'
import { brand } from '../brand'
import { contact } from '../content'
import { DocLayout, type DocSection } from '../components/DocLayout'

const sections: DocSection[] = [
  {
    id: 'who',
    title: 'What visited your site',
    body: (
      <>
        <p>Requests with <code>WalkthruBot</code> in the user agent come from {brand.name}'s scanner. It runs when someone asks for an Instant Scan, a weekly check or a competitor comparison of a public site.</p>
        <p>It reads public pages the way a search engine does: it honours <code>robots.txt</code>, follows at most 10 same-site links (50 for paid plans), sends only ordinary read requests, and never logs in, submits forms or sends attack payloads. Deeper checks, like looking for exposed files, only run on domains whose owner has verified them.</p>
      </>
    ),
  },
  {
    id: 'test-users',
    title: 'Test users in a browser',
    body: (
      <p>Test users run in a person's own Chrome, through the {brand.name} extension, so they look like that person's browser. On a site its owner has not verified they act as a visitor: they read, click links and use the site's search, and never fill in forms, sign in, like, post or buy. They never solve CAPTCHAs or get around bot protection. <Link to="/security#modes">How the modes work</Link>.</p>
    ),
  },
  {
    id: 'opt-out',
    title: 'Keep us off your site',
    body: (
      <>
        <p>To stop the scanner, disallow it in <code>robots.txt</code>:</p>
        <pre><code>{'User-agent: WalkthruBot\nDisallow: /'}</code></pre>
        <p>To keep test users off too, or to report misuse, email <a href={`mailto:${contact.abuse}`}>{contact.abuse}</a> with your domain. We add it to our blocklist within 24 hours; after that {brand.name} refuses every scan and test of it.</p>
      </>
    ),
  },
]

export default function Bot() {
  return (
    <DocLayout
      title="Walkthru bot"
      lead={`How ${brand.name}'s scanner and test users behave on your site, and how to opt out.`}
      updated="2026-09-26"
      sections={sections}
    />
  )
}
