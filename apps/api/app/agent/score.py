"""Launch Ready score: one number from the areas a report actually measured (ARCHITECTURE.md `share-loop`).

Plain code over the stored report, never a model. Ignored findings still count, so the public badge cannot be
gamed by ignoring problems; they only stop repeating in lists.
"""

WEIGHTS = {"ux": 30, "security": 20, "geo": 20, "seo": 15, "speed": 15}
PENALTY = {"high": 25, "medium": 10, "low": 3}
# Journey outcomes that say something about the site. Walkthru's own stops (the owner's Stop, a loop guard,
# a CAPTCHA) and unfinished runs measure nothing, so UX is left out rather than marked down.
JOURNEY = {"done": 100, "safe_stop": 100, "gave_up": 50, "stuck": 50, "budget": 50}


def _penalised(findings: list[dict], kinds: set[str], base: int = 100) -> int:
    return max(0, base - sum(PENALTY.get(f.get("severity"), 0) for f in findings if f.get("kind") in kinds))


def launch_ready(report: dict, status: str) -> dict:
    """{"score": 0-100 or None, "areas": {area: 0-100 or None}}. None means not measured."""
    findings, checks = report.get("findings") or [], report.get("checks") or {}
    done = lambda *names: any(checks.get(n) == "complete" for n in names)
    geo = report.get("geo") or {}
    areas = {
        "ux": _penalised(findings, {"ux"}, JOURNEY[status]) if status in JOURNEY else None,
        "security": _penalised(findings, {"security"}) if done("security") else None,
        "geo": geo.get("score") if done("geo") and geo.get("score") is not None else None,
        "seo": _penalised(findings, {"seo"}) if done("seo") else None,
        "speed": _penalised(findings, {"performance", "accessibility"}) if done("performance", "accessibility") else None,
    }
    measured = {k: v for k, v in areas.items() if v is not None}
    total = sum(WEIGHTS[k] for k in measured)
    return {"score": round(sum(WEIGHTS[k] * v for k, v in measured.items()) / total) if total else None, "areas": areas}


def band(value: int | None) -> str:
    if value is None:
        return "Not measured"
    return "Launch ready" if value >= 85 else "Almost ready" if value >= 60 else "Needs work"


def badge_svg(value: int | None) -> str:
    """A 20px status badge for the owner's footer or README. Hex values mirror DESIGN.md tokens (ink, accent, muted,
    danger) because the SVG renders on other people's sites, outside our CSS. Verdana keeps widths predictable there."""
    label, text = "Walkthru", f"Launch Ready {value}" if value is not None else "Launch Ready ?"
    colour = "#63636b" if value is None else "#4d7274" if value >= 85 else "#63636b" if value >= 60 else "#a33b3b"
    left, right = 10 + round(len(label) * 6.6), 10 + round(len(text) * 6.6)
    width = left + right
    title = f"Walkthru Launch Ready score: {value if value is not None else 'not measured'} of 100. {band(value)}."
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" role="img" aria-label="{title}">'
        f"<title>{title}</title>"
        f'<clipPath id="r"><rect width="{width}" height="20" rx="10"/></clipPath>'
        f'<g clip-path="url(#r)"><rect width="{left}" height="20" fill="#1b1b1f"/><rect x="{left}" width="{right}" height="20" fill="{colour}"/></g>'
        f'<g fill="#f4f4f5" font-family="Verdana,DejaVu Sans,sans-serif" font-size="11" text-anchor="middle">'
        f'<text x="{left / 2}" y="14" textLength="{left - 12}">{label}</text>'
        f'<text x="{left + right / 2}" y="14" textLength="{right - 12}">{text}</text></g></svg>'
    )
