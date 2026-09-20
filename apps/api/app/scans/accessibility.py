"""Fast, deterministic accessibility checks over server-fetched HTML.

These checks are evidence, not a WCAG certification. Browser-level audits remain a later layer.
"""

from itertools import pairwise

from selectolax.parser import HTMLParser, Node

from app.agent.schema import Finding


def _f(severity: str, title: str, detail: str, fix: str, evidence: str | None = None) -> Finding:
    return Finding(kind="accessibility", severity=severity, title=title, detail=detail, fix=fix, evidence=evidence[:300] if evidence else None)


def _has_name(node: Node, tree: HTMLParser) -> bool:
    attrs = node.attributes
    if (attrs.get("aria-label") or attrs.get("aria-labelledby") or attrs.get("title") or "").strip():
        return True
    if node.tag == "button" and node.text(strip=True):
        return True
    if node.tag == "input" and node.attributes.get("type", "").lower() in {"submit", "button", "reset"} and (attrs.get("value") or "").strip():
        return True
    node_id = attrs.get("id")
    if node_id and any(label.attributes.get("for") == node_id for label in tree.css("label[for]")):
        return True
    parent = node.parent
    return bool(parent is not None and parent.tag == "label" and parent.text(strip=True))


def scan(html: str, url: str) -> list[Finding]:
    tree = HTMLParser(html)
    out: list[Finding] = []

    root = tree.css_first("html")
    if root is None or not (root.attributes.get("lang") or "").strip():
        out.append(_f("medium", "Page language is not declared", "Assistive technology must guess how to pronounce this page.", 'Set the page language on the html element, for example lang="en".', url))

    headings = tree.css("h1, h2, h3, h4, h5, h6")
    levels = [int(node.tag[1]) for node in headings]
    skipped = next(((before, after) for before, after in pairwise(levels) if after > before + 1), None)
    if skipped:
        out.append(_f("medium", "Heading levels are skipped", f"The heading order jumps from h{skipped[0]} to h{skipped[1]}.", "Use headings in a logical outline without skipping levels.", f"h{skipped[0]} to h{skipped[1]} at {url}"))

    images = [node for node in tree.css("img") if node.attributes.get("alt") is None]
    if images:
        count = len(images)
        title = "Image is missing text alternative" if count == 1 else f"{count} images are missing text alternatives"
        sources = ", ".join((node.attributes.get("src") or "unknown image")[:60] for node in images[:3])
        out.append(_f("medium", title, "Meaningful images without alt text are not announced to screen-reader users.", 'Add descriptive alt text, or alt="" when an image is decorative.', sources))

    controls = [node for node in tree.css("input, select, textarea, button") if node.attributes.get("type", "").lower() != "hidden"]
    unnamed = [node for node in controls if not _has_name(node, tree)]
    if unnamed:
        count = len(unnamed)
        title = "Form control has no accessible name" if count == 1 else f"{count} form controls have no accessible name"
        evidence = ", ".join(f"<{node.tag}>" for node in unnamed[:4])
        out.append(_f("high", title, "A screen reader cannot tell users what this control does.", "Add a visible label or an accurate aria-label to every control.", evidence))

    return out
