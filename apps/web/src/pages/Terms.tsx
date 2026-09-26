import { Link } from 'react-router'
import { brand } from '../brand'
import { contact } from '../content'
import { DocLayout, type DocSection } from '../components/DocLayout'

const sections: DocSection[] = [
  {
    id: 'agreement',
    title: 'Agreement',
    body: <p>These terms apply when you use {brand.name}, its website, dashboard and Chrome extension. By signing in or running a scan you agree to them. If you use {brand.name} for a company, you agree on its behalf.</p>,
  },
  {
    id: 'service',
    title: 'The service',
    body: (
      <>
        <p>{brand.name} sends AI test users through websites, reads public pages for SEO and passive security hygiene, and turns the results into reports. Test users are AI. Their findings are informed suggestions, not guarantees that a site will work, rank or convert.</p>
        <p>We are improving {brand.name} quickly. Features may change, and we will tell you before removing something you pay for.</p>
      </>
    ),
  },
  {
    id: 'account',
    title: 'Your account',
    body: <p>Keep your sign-in secure and tell us if you think someone else is using your account. You are responsible for what happens under it, including runs started from your connected extension.</p>,
  },
  {
    id: 'acceptable-use',
    title: 'Sites you may test',
    body: (
      <>
        <p>Only test, watch or run deep checks on sites you own or have permission to test. Competitor comparison is the one exception: it reads the public pages of other sites with the same passive requests a search engine makes, never logs in, never submits forms and never runs the checks reserved for verified domains. You agree not to:</p>
        <ul>
          <li>use {brand.name} to attack, overload or gain unauthorised access to any system;</li>
          <li>point test users at sites you do not own or are not authorised to test, including banking, trading, social, government, webmail and similar sites, or at accounts that belong to someone else;</li>
          <li>run bulk or repeated actions (many sign-ups, every post, dozens of messages), or like, follow, post, message or buy on a site you have not verified;</li>
          <li>try to get around safe mode, visitor mode, bot protection, CAPTCHAs, rate limits or plan limits;</li>
          <li>point test users at payment, deletion or messaging flows on accounts that hold real customer data;</li>
          <li>use competitor comparison to overload a site, or on pages that are not public;</li>
          <li>share your API keys or deploy hooks. You are responsible for what is done with them; revoke any key you think has leaked;</li>
          <li>resell or copy the service, or use reports to build a competing product.</li>
        </ul>
        <p>You are responsible for having permission to test every site you point {brand.name} at. We may refuse a run, pause test runs for an account or a site, or end accounts that break these rules. An account that keeps aiming test users at refused goals or sites is paused automatically until we review it.</p>
      </>
    ),
  },
  {
    id: 'safe-mode',
    title: 'Safe mode and your data',
    body: (
      <>
        <p>On a site you have not <Link to="/docs#verify">verified</Link>, a test user acts as a visitor: it reads, clicks links and menus and uses the site's search, but never fills in other forms, signs in, likes, follows, posts, messages, buys or adds to a cart. On a verified domain it may do what a real visitor does, and safe mode still blocks paying, deleting and cancelling, asks before submitting forms on logged-in pages, and only sends messages after you approve. Banking, trading, social, webmail and similar sites are refused unless you verified that exact domain.</p>
        <p>These limits reduce risk; they do not remove it. Test dashboards with a test account and sample data.</p>
        <p>You remain responsible for your sites and for any action you approve during a run.</p>
      </>
    ),
  },
  {
    id: 'content',
    title: 'Your content',
    body: <p>You own your runs and reports. You give us permission to store and process them only to provide {brand.name} to you, as described in the <Link to="/privacy">privacy policy</Link>. When you create a public link, anyone with it can view that report until you delete the run.</p>,
  },
  {
    id: 'plans',
    title: 'Plans and payment',
    body: <p>The free plan is free. Paid access is offered at checkout with its price, credits and duration shown before you pay. Payments are handled by our payment provider; we never see your card number. Unused credits expire at the end of the period shown at checkout.</p>,
  },
  {
    id: 'disclaimers',
    title: 'Disclaimers and liability',
    body: (
      <>
        <p>{brand.name} is provided as is. We work hard to keep it accurate and available, but we do not promise it will be uninterrupted or error free, or that it will find every problem on your site.</p>
        <p>To the extent the law allows, we are not liable for indirect or consequential losses, and our total liability is limited to the amount you paid us in the 12 months before the claim.</p>
      </>
    ),
  },
  {
    id: 'ending',
    title: 'Ending your account',
    body: <p>You can delete your account at any time from <Link to="/app/settings">Settings</Link>. Deletion is permanent and removes your runs, reports and screenshots.</p>,
  },
  {
    id: 'changes',
    title: 'Changes and contact',
    body: <p>We may update these terms. If a change matters, we will update the date above and tell signed-in users before it takes effect. Questions go to <a href={`mailto:${contact.hello}`}>{contact.hello}</a>.</p>,
  },
]

export default function Terms() {
  return (
    <DocLayout
      title="Terms of service"
      lead={`The rules for using ${brand.name}, written to be read. The short version: only test sites you are allowed to test, and treat findings as advice.`}
      updated="2026-09-26"
      sections={sections}
    />
  )
}
