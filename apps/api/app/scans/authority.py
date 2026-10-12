"""Authority and backlinks, prelaunch advisory mode (R-S17a): twelve link tactics, each marked advisory, missing a
prerequisite, not applicable or not recommended for this site.

Built only from the R-S17 page map (the audited pages' own copy). No link index, mention search, publisher list or
outreach. An advisory brief names the page it builds on and what it needs before anyone acts on it; a tactic that
needs outside evidence (a link export, a dated mention, a real list or request) says exactly which, and nothing is
filled in. Stored as `report.authority`; never findings or score. Contract: docs/authority-plan.md.
"""

from urllib.parse import urlsplit

MODE = "prelaunch_advisory"
LINK_SPAM = "https://developers.google.com/search/docs/essentials/spam-policies#link-spam"
BASIS = ("Built from the audited public pages' own copy. No backlink index, mention search, publisher list or "
         "outreach was used, and none is invented.")
RULES = (
    "Nothing here sends email, posts, registers profiles or places links. Every step is yours to take, or to scope separately.",
    "Drafts and media briefs need a factual and rights review before use. Building a tool or producing a video is separate work.",
    "Backlinks, GEO readiness and AI citations are different things. Links do not guarantee an AI citation or a higher rank.",
)
SEPARATE = {
    "geo_readiness": "GEO readiness (its own chapter) checks whether AI crawlers can read and understand your pages.",
    "ai_citations": ("AI citations are sampled separately with engine, prompt, date, sources and sample size. A brand mention "
                     "or an answer from memory is not a citation, and a failed or missing sample is not zero visibility."),
    "backlinks": "No link data was read for this report, so nothing here measures links you have or lost.",
}
MEASURE_LINKS = "Count new referring pages to the target page 90 days after it ships, from your own analytics or a link export. No rank change is promised."


def _sections(page: dict) -> list[str]:
    return [h["text"] for h in page.get("supporting") or []]


def _missing(tactic: str, title: str, needs: list[str], benefit: str, effort: str, measurement: str = MEASURE_LINKS) -> dict:
    return {"id": tactic, "title": title, "state": "prerequisite_missing", "target": None, "source": None, "brief": None,
            "reader_benefit": benefit, "prerequisites": needs, "missing": needs, "effort": effort, "measurement": measurement, "policy": None}


def build(advice: dict | None) -> dict | None:
    """The plan for one report, from its R-S17 page map. Legacy reports without a map get none."""
    pages = (advice or {}).get("pages") or []
    if not pages:
        return None
    stated = [p for p in pages if p.get("primary_intent")]
    home = min(stated, key=lambda p: len(urlsplit(p["url"]).path)) if stated else None  # the shallowest page states the main job
    explainer = next((p for p in pages if len(_sections(p)) >= 3), None)

    def advisory(tactic, title, page, brief, benefit, needs, missing, effort, measurement=MEASURE_LINKS):
        return {"id": tactic, "title": title, "state": "advisory", "target": page["url"],
                "source": {"kind": "audited_page", "url": page["url"], "observed": "audited in this report"},
                "brief": brief, "reader_benefit": benefit, "prerequisites": needs, "missing": missing, "effort": effort,
                "measurement": measurement, "policy": None}

    def not_applicable(tactic, title, why):
        return {"id": tactic, "title": title, "state": "not_applicable", "target": None, "source": None, "brief": None,
                "reader_benefit": why, "prerequisites": [], "missing": [], "effort": None, "measurement": None, "policy": None}

    topic = home["primary_intent"]["text"] if home else None
    outline = _sections(explainer) if explainer else []
    tactics = [
        _missing("lost_links", "Recover lost links", ["A backlink history export with source URL, target URL and the date each link was last seen."],
                 "Readers who follow an old link reach a working page instead of an error.", "low"),
        _missing("unlinked_mentions", "Unlinked mentions", ["A dated page on another site that names your product without linking to it."],
                 "Readers of that page can reach the thing it already mentions. An AI answer that mentions you is not such a page.", "low"),
        advisory("free_tool", "Free tools", home,
                 f'A small free tool that does one step of "{topic}" in the browser, on its own page linked from {home["url"]}.',
                 "Readers can try the job before signing up, and other sites gain a useful resource to point to.",
                 ["A job your audience repeats that a small checker, generator or converter can do.", "A scope you can build and maintain.",
                  "Examples of pages where it would help readers."],
                 ["Which job to build for, and whether you can maintain it."], "high",
                 "Tool uses and referring pages to the tool page 90 days after launch. No rank change is promised.")
        if home else not_applicable("free_tool", "Free tools", "No audited page states a topic to build a tool around."),
        _missing("listicle_outreach", "Listicle outreach", ["A real, current list of tools in your category, with its selection criteria.", "True product facts that meet those criteria."],
                 "Readers comparing options see an accurate entry for your product.", "medium"),
        _missing("competitor_links", "Competitor links", ["Authorized link data for named competitors: a licensed provider or your own export.", "Editorial reasons those sources would also value your product."],
                 "Readers of those editorial sources find another relevant option. Links are never transferred or guaranteed.", "medium"),
        _missing("broken_link_building", "Broken link building", ["A verified dead link on a relevant page.", "A working page of yours that replaces what it pointed to."],
                 "Readers who hit the dead link get a working, relevant page.", "medium"),
        _missing("outdated_guides", "Fix outdated guides", ["A dated guide with a passage that is now wrong.", "Primary evidence for the correction."],
                 "Readers of the guide get correct, current information.", "medium"),
        _missing("statistics_page", "Statistics page", ["Original data you own and may publish, with its method, sample size and collection dates."],
                 "Writers and readers get numbers they can check and cite. Walkthru never supplies or estimates the statistics.", "high",
                 "Referring pages citing the statistics page 90 days after it ships. No rank change is promised."),
        _missing("reporter_outreach", "Reporter outreach", ["A genuine open request from a writer, with its deadline.", "Your consent and a factual, attributable quote."],
                 "The writer's readers get an expert, attributable answer.", "medium"),
        advisory("infographics", "Infographics", explainer,
                 f"A visual summary of {explainer['url']}, one panel per section: " + "; ".join(f'"{s}"' for s in outline[:6]) + ".",
                 "Readers grasp the page's sections at a glance; other writers can reuse it with credit.",
                 ["Rights to every figure, logo and screenshot used.", "A source for every number shown.", "A text alternative that says the same thing."],
                 ["A rights and accuracy review of the page's content."], "medium")
        if explainer else not_applicable("infographics", "Infographics", "No audited page has three or more sections to summarize visually."),
        advisory("article_to_video", "Article to video", explainer,
                 f"A short explainer video from {explainer['url']}, one scene per section: " + "; ".join(f'"{s}"' for s in outline[:6]) + ".",
                 "Readers who prefer watching get the same explanation, with a link back to the page.",
                 ["Permission for anything shown or said.", "An accuracy review of the script against the page.", "Evidence your audience watches video."],
                 ["Whether your audience watches video, and a production budget."], "high",
                 "Views, and visits from the video to the page, 90 days after publishing. No rank change is promised.")
        if explainer else not_applicable("article_to_video", "Article to video", "No audited page has three or more sections to turn into scenes."),
        {"id": "link_exchanges", "title": "Link exchanges", "state": "not_recommended", "target": None, "source": None, "brief": None,
         "reader_benefit": "Link only where a page genuinely helps the reader, for its own editorial reason.",
         "prerequisites": [], "missing": [], "effort": None, "measurement": None,
         "policy": ("Excessive or reciprocal and three-way exchanges, automated link creation and links bought to rank are link spam "
                    "under Google's policy. Paid placements must be marked rel=\"sponsored\".")},
    ]
    return {"mode": MODE, "link_data": "none", "basis": BASIS, "rules": list(RULES), "separate": SEPARATE, "policy_source": LINK_SPAM,
            "tactics": tactics}


STATE_WORD = {"advisory": "Advisory brief", "prerequisite_missing": "Needs input", "not_applicable": "Not applicable", "not_recommended": "Not recommended"}


def counts(plan: dict) -> dict[str, int]:
    out = dict.fromkeys(STATE_WORD, 0)
    for t in plan["tactics"]:
        out[t["state"]] += 1
    return out


def lines(plan: dict) -> list[str]:
    """The plan as text, shared by the Authority chapter prompt and MCP get_report(section="authority")."""
    out = [f"Mode: {plan['mode']} (no link data). {plan['basis']}", *[f"Rule: {r}" for r in plan["rules"]],
           *[f"Kept separate: {v}" for v in plan["separate"].values()], ""]
    for n, t in enumerate(plan["tactics"], start=1):
        out.append(f"### {n}. {t['title']}: {STATE_WORD[t['state']]}")
        if t["brief"]:
            out.append(f"Brief (from {t['source']['url']}, {t['source']['observed']}): {t['brief']}")
        out.append(f"Reader benefit: {t['reader_benefit']}")
        out += [f"Needs: {m}" for m in t["missing"]]
        if t["effort"]:
            out.append(f"Effort: {t['effort']}. Measure: {t['measurement']}")
        if t["policy"]:
            out.append(f"Policy: {t['policy']} Source: {plan['policy_source']}")
        out.append("")
    return out
