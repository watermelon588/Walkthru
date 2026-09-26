# Chrome Web Store listing: answers to paste

Written 2026-09-26 for docs/agent-safety-plan.md item 7. Every answer must match the Privacy page (`/privacy`, section "What the Chrome extension reads"). If one changes, change both. Publish as **Unlisted** for the beta (item 8), then Public at launch.

## Single purpose

> Walkthru runs an AI test user through a website you are testing, in the tab you choose, and reports where a visitor would get stuck.

## Permission justifications

| Permission | Justification to paste |
|---|---|
| `sidePanel` | Shows the test controls and each step of the test user beside the page being tested. |
| `activeTab` | Reads the address of the tab the user starts a test in, only after they press Start. |
| `tabs` | Follows the tested tab as the test user navigates, and stops the test if it leaves the site. |
| `scripting` | Adds the page reader to the tested tab when a test starts. Nothing runs on other tabs. |
| `storage` | Keeps the user's Walkthru sign-in so they do not sign in every time they open the side panel. |
| Optional host access (`<all_urls>`) | Requested only when a test starts, because Chrome allows tab screenshots only with site access. Used only for the tab under test, to capture up to eight screenshots with form fields hidden. |
| Remote code | No. All code ships in the package. |

## Data usage (privacy practices form)

Collected, for the single purpose only:
- **Website content:** a masked outline of the tested page (buttons, links, headings, visible errors, control labels) and up to eight screenshots of that tab, with emails, long numbers and typed values masked before they leave the browser.
- **Authentication information:** the user's own Walkthru session token, kept in extension storage to call the Walkthru API. Not the tested site's credentials.
- **Web history:** no. Only the address of the tab under test, while the test runs.

Not collected: personally identifiable information from the tested site, health, financial, location, personal communications, user activity outside the tested tab, cookies, local or session storage, passwords.

Certify:
- Data is not sold to third parties.
- Data is not used or transferred for purposes unrelated to the single purpose.
- Data is not used or transferred to determine creditworthiness or for lending.

Privacy policy URL: `https://<domain>/privacy`

## Proof we keep true

- `apps/extension/tests/privacy.test.ts` fails the build if the extension's code touches cookies, page storage, history or network requests, or if the manifest gains broad permissions.
- Blocked categories, visitor mode and the per-step gate are enforced by the API (docs/agent-safety-plan.md), so a modified copy of the extension cannot act beyond them.
