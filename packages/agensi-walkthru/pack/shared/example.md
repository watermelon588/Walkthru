# Example report review

Illustrative example using fictional report data.

**Request**

> Review this Walkthru findings export for my product. What should I fix before launch?

**Supplied findings**

| Chapter | Page | Evidence |
| --- | --- | --- |
| Accessibility | `/signup` | The email input has no accessible name. |
| SEO | `/pricing` | The page title is identical to the homepage title. |
| Journey | `/signup` | This export contains technical findings only. |

**Example response**

1. **Label the email field on `/signup`.** The export reports that the field has no accessible name. Associate a visible “Email address” label with the input. Verify that the browser accessibility tree exposes that name and that activating the label focuses the input.
2. **Give `/pricing` a distinct title.** Its reported title matches the homepage. Set a pricing-specific page title. Recheck both URLs and confirm that their rendered titles differ and describe each page.

The supplied export does not establish whether a visitor can finish signup. Run that journey in Walkthru to collect task evidence.
