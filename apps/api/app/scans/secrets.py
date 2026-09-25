"""Secrets in public JavaScript, with gitleaks' rule set (MIT; notice in apps/api/THIRD_PARTY.md).

The rules are converted from Go RE2 to Python by scripts/refresh_security_data.py and stored in
app/scans/data/gitleaks.json. The matching follows gitleaks: keywords pre-filter a rule, the secret is the rule's
secret group (or the first non-empty group), a Shannon-entropy floor drops placeholder values, and allowlists drop
known test values. Only verified domains get their bundles fetched (app/scans/security.py).
"""

import hashlib
import json
import math
import os
import re
from collections import Counter
from functools import lru_cache

DATA = os.path.join(os.path.dirname(__file__), "data", "gitleaks.json")
MAX_TEXT = 2_000_000  # the regexes are linear in practice, but a bound keeps one huge bundle from stalling a scan
PER_RULE = 3
# Keys that are public by design in browser code: they cannot be kept secret, so the advice is to restrict them.
PUBLIC_BY_DESIGN = {"gcp-api-key"}
LABELS = {"gcp-api-key": "Google API key", "aws-access-token": "AWS access key", "github-pat": "GitHub token",
          "slack-bot-token": "Slack token", "private-key": "Private key", "openai-api-key": "OpenAI API key",
          "anthropic-api-key": "Anthropic API key", "sendgrid-api-token": "SendGrid API key"}


@lru_cache(maxsize=1)
def _rules() -> tuple[list[dict], list[str], list[re.Pattern]]:
    with open(DATA, encoding="utf-8") as f:
        raw = json.load(f)
    rules = [rule | {"compiled": re.compile(rule["regex"]), "allow": [re.compile(r) for r in rule.get("regexes", [])]} for rule in raw["rules"]]
    return rules, raw.get("stopwords", []), [re.compile(r) for r in raw.get("regexes", [])]


def entropy(value: str) -> float:
    counts = Counter(value)
    return -sum(n / len(value) * math.log2(n / len(value)) for n in counts.values()) if value else 0.0


def _secret(match: re.Match, group: int | None) -> str:
    if group and group <= (match.re.groups or 0):
        return match.group(group) or ""
    return next((g for g in match.groups() if g), match.group(0)) if match.re.groups else match.group(0)


def label(rule_id: str, secret: str) -> str:
    if rule_id == "stripe-access-token":
        return "Stripe live key" if "_live_" in secret else "Stripe test key" if "_test_" in secret else "Stripe key"
    return LABELS.get(rule_id) or rule_id.replace("-", " ").capitalize()


def find(text: str) -> list[tuple[str, str]]:
    """(rule id, secret) pairs, at most PER_RULE per rule."""
    text = text[:MAX_TEXT]
    lowered = text.lower()
    rules, stopwords, global_allow = _rules()
    found: list[tuple[str, str]] = []
    for rule in rules:
        if rule["keywords"] and not any(k in lowered for k in rule["keywords"]):
            continue
        hits, seen = 0, set()
        for match in _matches(rule, text, lowered):
            secret = _secret(match, rule.get("group")).strip()
            if secret in seen:
                continue
            seen.add(secret)
            if not secret or (rule.get("entropy") and entropy(secret) <= rule["entropy"]):
                continue
            low = secret.lower()
            if any(w in low for w in stopwords + [s.lower() for s in rule.get("stopwords", [])]) or any(p.search(secret) for p in rule["allow"] + global_allow):
                continue
            if rule.get("sha256") and hashlib.sha256(secret.encode()).hexdigest() in rule["sha256"]:
                continue
            found.append((rule["id"], secret))
            hits += 1
            if hits >= PER_RULE:
                break
    return found


BEFORE, AFTER = 400, 4000  # a match never starts far before its keyword; a PEM private key runs about 3 kB after it


def _matches(rule: dict, text: str, lowered: str):
    """Run a keyword rule only in windows around its keyword hits (as gitleaks does). Python's backtracking engine is
    slow on the lazy context prefixes these RE2 patterns use; windows keep every scan bounded."""
    if not rule["keywords"]:
        yield from rule["compiled"].finditer(text)
        return
    spans: list[list[int]] = []
    for keyword in rule["keywords"]:
        start = lowered.find(keyword)
        while start != -1:
            spans.append([max(0, start - BEFORE), start + len(keyword) + AFTER])
            start = lowered.find(keyword, start + 1)
    merged: list[list[int]] = []
    for span in sorted(spans):
        if merged and span[0] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], span[1])
        else:
            merged.append(span)
    for start, end in merged:
        yield from rule["compiled"].finditer(text, start, end)


def mask(secret: str) -> str:
    return f"{secret[:4]}… ({len(secret)} characters)"
