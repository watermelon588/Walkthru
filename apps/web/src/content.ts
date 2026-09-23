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
  title: 'See where strangers get stuck on your site.',
  sub: 'AI test users try your signup, dashboard and checkout in your browser, then tell you what to fix first.',
  primary: 'Scan my site',
  secondary: 'See a sample report',
}

export const steps = [
  { icon: PlusIcon, title: 'Add your site', body: 'Paste the address and confirm it is yours with one meta tag.' },
  { icon: UserPlusIcon, title: 'Pick who tests it', body: 'A busy shop owner, a careful buyer, someone on a phone. Give them a goal.' },
  { icon: CursorClickIcon, title: 'Watch it try', body: 'Our extension drives your real tab. Our server decides every click and notes what confused it.' },
  { icon: ListNumbersIcon, title: 'Fix what matters', body: 'One report with stuck points, SEO gaps, security warnings and the five fixes worth doing first.' },
]

// Sample run for a made-up app, quickinvoice.app
export const run = [
  { action: 'Opened quickinvoice.app', thought: 'The headline says "Streamline fiscal workflows". Not sure this is for me.' },
  { action: 'Clicked "Get started"', thought: 'The "Get started" and "Book a demo" buttons look the same. I will try the first one.' },
  { action: 'Typed email and business name', thought: 'It wants a tax ID before I have seen anything. I do not have that handy.' },
  { action: 'Clicked "Create account"', thought: 'Nothing happened. No error message. I would leave now.' },
]

export const personas = [
  { icon: StorefrontIcon, img: 'persona-owner.jpg', name: 'The busy owner', who: 'Not technical. About 30 seconds of patience.', catches: 'Unclear headlines, jargon, too many steps.' },
  { icon: DeviceMobileIcon, img: 'persona-phone.jpg', name: 'The phone user', who: 'Small screen, one thumb, bad signal.', catches: 'Broken menus, tiny buttons, slow pages.' },
  { icon: ReceiptIcon, img: 'persona-buyer.jpg', name: 'The careful buyer', who: 'Wants price and proof before signing up.', catches: 'Hidden pricing, missing trust signals.' },
  { icon: UserPlusIcon, img: 'persona-signup.jpg', name: 'The first signup', who: 'Has never seen your product before.', catches: 'Confusing forms, silent errors, dead ends.' },
  { icon: SquaresFourIcon, img: 'persona-returning.jpg', name: 'The returning user', who: 'Logged in and trying to get work done.', catches: 'Buried settings, dashboard dead ends.' },
]

export const reportParts = [
  { img: 'stuck-closeup.png', title: 'Where they got stuck', body: 'Every stuck point with the screenshot and the exact words the test user said.' },
  { img: 'report.png', title: 'First impression in five seconds', body: 'What a stranger thinks your site does, who it is for, and what they would click first.' },
  { img: 'seo.png', title: 'SEO check', body: 'Titles, descriptions, alt text, sitemap and load speed on every page the test users visited.' },
  { img: 'security.png', title: 'Security hygiene', body: 'Missing headers, insecure cookies, public files and keys leaked into JavaScript. Passive checks only.' },
]

export const safety = [
  { icon: LockKeyIcon, title: 'No passwords shared', body: 'Tests run in the tab you are already logged into.' },
  { icon: HandPalmIcon, title: 'Safe mode', body: 'Never clicks delete, cancel or pay. Asks before submitting forms.' },
  { icon: EyeSlashIcon, title: 'Private by default', body: 'Emails, numbers and typed values are masked in your browser.' },
  { icon: ShieldCheckIcon, title: 'Passive security', body: 'Headers and public files only, on sites you have verified.' },
]

export const plans = [
  { name: 'Free', price: '$0', per: 'forever', cta: 'Scan my site', features: ['Instant Scan, no install', '3 test runs a month', 'Public pages only'] },
  { name: 'Launch Pack', price: '$9', per: 'one time', cta: 'Buy the pack', features: ['20 runs within 30 days', 'Everything in Pro'] },
  { name: 'Pro', price: '$15', per: 'per month', cta: 'Start Pro', highlight: true, features: ['60 runs a month', 'Logged-in pages', 'Full-site SEO', 'Full security check', 'Compare runs'] },
  { name: 'Team', price: '$39', per: 'per month', cta: 'Start Team', features: ['250 runs a month', '5 sites', 'Custom test users', 'Weekly scans'] },
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
  { q: 'Is the security check a penetration test?', a: 'No. It is a hygiene check of headers, cookies, public files and leaked keys. It never sends attack payloads and only runs on sites you have verified.' },
  { q: 'Can it tell me if my site will get customers?', a: 'It shows what stops people: unclear messages, missing trust signals, broken steps. That is an informed review, not a guarantee.' },
]
