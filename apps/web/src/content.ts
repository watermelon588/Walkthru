// All marketing copy for the site. Edit here, not in components.
import {
  CursorClickIcon,
  DeviceMobileIcon,
  EyeSlashIcon,
  HandPalmIcon,
  ListNumbersIcon,
  LockKeyIcon,
  PlusIcon,
  ReceiptIcon,
  ShieldCheckIcon,
  SquaresFourIcon,
  StorefrontIcon,
  UserPlusIcon,
} from '@phosphor-icons/react'

export const hero = {
  title: 'The launch check for apps built with AI.',
  sub: 'AI test users try your signup and dashboard in your own browser. One report adds SEO, AI search readiness and security, with the fixes ranked.',
  primary: 'Scan my site',
  secondary: 'See a sample report',
}

export const steps = [
  { icon: PlusIcon, title: 'Scan your site', body: 'Paste your address for a free Instant Scan: SEO, AI search readiness and security in about 20 seconds.' },
  { icon: UserPlusIcon, title: 'Give a test user a goal', body: 'Open your site, click the bird and pick who tests it. Walkthru turns your goal into a checklist first.' },
  { icon: CursorClickIcon, title: 'Watch it try', body: 'The extension drives your real tab. Our server decides every click and notes what confused it.' },
  { icon: ListNumbersIcon, title: 'Fix, then rerun', body: 'Get one ranked report. Paid runs include a prompt for your coding agent. Rerun to see what is fixed, new and still broken.' },
]

// Sample run for a made-up app, quickinvoice.app
export const run = [
  { action: 'Opened quickinvoice.app', thought: 'The headline says "Streamline fiscal workflows". Not sure this is for me.' },
  { action: 'Clicked "Get started"', thought: 'The "Get started" and "Book a demo" buttons look the same. I will try the first one.' },
  { action: 'Typed email and business name', thought: 'It wants a tax ID before I have seen anything. I do not have that handy.' },
  { action: 'Clicked "Create account"', thought: 'Nothing happened. No error message. I would leave now.' },
]

export const personas = [
  { icon: StorefrontIcon, img: 'persona-owner.jpg', name: 'The first-time visitor', who: 'Has never heard of you. About 30 seconds of patience.', catches: 'Unclear headlines, jargon, a hidden sign-up.' },
  { icon: DeviceMobileIcon, img: 'persona-phone.jpg', name: 'The phone user', who: 'Small screen, one thumb, bad signal.', catches: 'Broken menus, tiny buttons, slow pages.' },
  { icon: ReceiptIcon, img: 'persona-buyer.jpg', name: 'The small-business buyer', who: 'Wants price and proof before signing up.', catches: 'Hidden pricing, missing trust signals.' },
  { icon: UserPlusIcon, img: 'persona-signup.jpg', name: 'The skeptical developer', who: 'Reads the details before trusting you.', catches: 'Vague claims, silent errors, broken links.' },
  { icon: SquaresFourIcon, img: 'persona-returning.jpg', name: 'Your logged-in user', who: 'Any test user, inside the tab you are signed into.', catches: 'Buried settings, dashboard dead ends.' },
]

export const reportParts = [
  { img: 'stuck-closeup.png', title: 'Where they got stuck', body: 'Every reported stuck point has a step and the test user’s words. Screenshots and replay appear when capture was available.' },
  { img: 'report.png', title: 'A Launch Ready score', body: 'What a stranger thinks in five seconds, one score from 0 to 100, the fixes to do first and a live badge for your site.' },
  { img: 'seo.png', title: 'SEO and AI search', body: 'Titles, broken links, duplicates and sitemaps across audited pages, plus whether AI crawlers can fetch and understand your content.' },
  { img: 'security.png', title: 'Security hygiene', body: 'Missing headers and plain http on public sites, plus public files and browser-shipped keys on verified domains. Passive checks only.' },
]

export const safety = [
  { icon: LockKeyIcon, title: 'No passwords shared', body: 'Tests run in the tab you are already logged into.' },
  { icon: HandPalmIcon, title: 'Safe mode', body: 'Never clicks delete, cancel or pay. Asks before submitting forms.' },
  { icon: EyeSlashIcon, title: 'Private by default', body: 'Emails, long numbers and typed values are masked in your browser.' },
  { icon: ShieldCheckIcon, title: 'Passive security', body: 'Headers on public pages; file and key checks only on sites you have verified.' },
]

export const plans = [
  { name: 'Free', price: '$0', per: 'forever', cta: 'Scan my site', features: ['Instant Scan, no install', 'SEO, AI search and security report', '3 test runs a month', 'Public pages'] },
  { name: 'Launch Pack', price: '$9', per: 'one time, 30 days', cta: 'Request access', href: '/app/billing', features: ['20 test runs', 'Logged-in pages', '50-page SEO audit', 'Fix prompt for your coding agent', 'Compare with 3 competitors'] },
  { name: 'Pro', price: '$19', per: 'per month, $15 for founding users', cta: 'Request access', href: '/app/billing', highlight: true, features: ['40 test runs a month', 'Everything in Launch Pack', 'Rerun and compare', 'Ignore findings with a reason', '2 sites'] },
  { name: 'Plus', price: '$49', per: 'per month, waitlist', cta: 'Join the waitlist', href: '/app/billing', features: ['150 test runs a month', 'Everything in Pro', '5 sites', 'Weekly watch and deploy alerts', 'MCP server for your coding agent', 'Opens after launch'] },
]

// Absolute (/#...) so they work from docs and legal pages too.
export const navLinks = [
  { label: 'How it works', href: '/#how' },
  { label: 'Report', href: '/#report' },
  { label: 'Pricing', href: '/#pricing' },
  { label: 'FAQ', href: '/#faq' },
  { label: 'Docs', href: '/docs' },
]

export const footer = {
  columns: [
    { title: 'Product', links: [{ label: 'How it works', href: '/#how' }, { label: 'Sample report', href: '/#report' }, { label: 'Pricing', href: '/#pricing' }, { label: 'FAQ', href: '/#faq' }] },
    { title: 'Get started', links: [{ label: 'Scan my site', href: '/#scan' }, { label: 'Documentation', href: '/docs' }, { label: 'Install the extension', href: '/docs#install' }, { label: 'Sign in', href: '/login' }] },
    { title: 'Legal', links: [{ label: 'Privacy', href: '/privacy' }, { label: 'Terms', href: '/terms' }, { label: 'Security', href: '/security' }] },
  ],
}

/** Contact addresses. The domain is a placeholder until it is bought (brand.ts). */
export const contact = {
  hello: 'hello@walkthru.dev',
  privacy: 'privacy@walkthru.dev',
  security: 'security@walkthru.dev',
}

export const faqs = [
  { q: 'What is a test user?', a: 'An AI that acts like a certain kind of visitor, for example a busy shop owner on a phone, and tries to use your site the way that person would. It says what it is thinking, so you see where it gets confused.' },
  { q: 'Can it break my site or delete data?', a: 'Safe mode blocks delete, cancel, payment and send actions and asks you before submitting forms on logged-in pages. For dashboard tests we still recommend a test account.' },
  { q: 'What gets sent to the AI?', a: 'A text outline of the page: buttons, links, headings and errors. Emails, long numbers and typed values are masked in your browser first.' },
  { q: 'Is the security check a penetration test?', a: 'No. It is a hygiene check of headers, https, public files and leaked keys. It never sends attack payloads, and the file and key checks only run on sites you have verified.' },
  { q: 'What is AI search readiness?', a: 'Whether AI search crawlers can fetch and understand your pages. Walkthru measures readiness and gives copy-paste fixes. It never promises citations or rankings.' },
  { q: 'Can it tell me if my site will get customers?', a: 'It shows what stops people: unclear messages, missing trust signals, broken steps. That is an informed review, not a guarantee.' },
]
