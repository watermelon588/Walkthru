"""Which SEO presentation checks are recommendations and which are advisory, against current primary guidance (R-S17).

Separate from observed site evidence: a finding says what the page does; this says how strongly Google's own docs
support acting on it. Advisory checks are presentation advice, never proven ranking failures. Review the sources
when they change and update `REVIEWED`.
"""

REVIEWED = "2026-10-06"
TITLE_LINKS = "https://developers.google.com/search/docs/appearance/title-link"
SNIPPETS = "https://developers.google.com/search/docs/appearance/snippet"
STARTER_GUIDE = "https://developers.google.com/search/docs/fundamentals/seo-starter-guide"

# rule id -> (status, source, what the source says, in our words)
RULES: dict[str, tuple[str, str, str]] = {
    "seo.missing_page_title": ("recommended", TITLE_LINKS, "Google recommends a unique, descriptive title element for every page."),
    "seo.page_title_is_too_short": ("advisory", TITLE_LINKS, "No minimum length is set; a very short title may describe the page poorly."),
    "seo.page_title_is_too_long": ("advisory", TITLE_LINKS, "No length limit; long title links are truncated to fit the device width."),
    "seo.missing_meta_description": ("advisory", SNIPPETS, "Snippets come mostly from page content; a description is used when it describes the page better."),
    "seo.meta_description_is_too_short": ("advisory", SNIPPETS, "No length limit is set either way; snippets are chosen per query."),
    "seo.meta_description_is_too_long": ("advisory", SNIPPETS, "No length limit; long snippets are truncated to fit the device width."),
    "seo.no_hn_heading": ("advisory", STARTER_GUIDE, "Headings help people and screen readers; Search sets no required heading count."),
    "seo.more_than_one_hn_heading": ("advisory", STARTER_GUIDE, "There is no ideal number of headings, and heading order does not matter for Search."),
}


def note(rule: str | None) -> str | None:
    """One line for prompts and reports: status, review date and the primary source."""
    entry = RULES.get(rule or "")
    if not entry:
        return None
    status, source, says = entry
    return f"Guidance ({status}, reviewed {REVIEWED}): {says} Source: {source}"
