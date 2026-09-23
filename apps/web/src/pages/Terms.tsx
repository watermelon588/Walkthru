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
        <p>Only scan or test sites you own or have permission to test. You agree not to:</p>
        <ul>
          <li>use {brand.name} to attack, overload or gain unauthorised access to any system;</li>
          <li>try to get around safe mode, CAPTCHAs, rate limits or plan limits;</li>
          <li>point test users at payment, deletion or messaging flows on accounts that hold real customer data;</li>
          <li>resell or copy the service, or use reports to build a competing product.</li>
        </ul>
        <p>We may pause or end accounts that break these rules.</p>
      </>
    ),
  },
  {
    id: 'safe-mode',
    title: 'Safe mode and your data',
    body: (
      <>
        <p>Safe mode blocks paying, deleting and cancelling, asks before submitting forms on logged-in pages, and only sends messages on verified domains after you approve. It reduces risk; it does not remove it. Test dashboards with a test account and sample data.</p>
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
      updated="2026-09-24"
      sections={sections}
    />
  )
}
