"""Honesty-first answer resolution.

Given a form question label, produce an answer by trying, in order:
  1. The canonical answer bank (answers.json) — fast, deterministic, human-authored.
  2. Direct profile facts (work auth, salary, EEO, location, links).
  3. The local LLM, grounded strictly in the profile via the honesty system prompt.

Any step may return the ``ASK_HUMAN`` sentinel, which propagates up and causes the runner
to leave the field for the human. A fabricated answer is never acceptable — the whole point
of LocalApply is that a required field you can't answer truthfully is *your* decision.
"""
from __future__ import annotations

import json
import re

from .llm import ASK_HUMAN

# Question-label patterns → answer-bank keys. Extend freely; order matters (first match wins).
BANK_PATTERNS: list[tuple[str, str]] = [
    (r"authorized to work|legally authorized|eligible to work", "authorized_to_work_us"),
    (r"require .*sponsorship|need .*sponsorship|visa sponsorship", "require_sponsorship_now_or_future"),
    (r"\bopt\b|h4 visa|h-4 visa", "currently_on_opt_or_h4"),
    (r"salary|compensation expectation|desired pay", "salary_expectation"),
    (r"how did you (hear|find)", "how_did_you_hear"),
    (r"relocat", "willing_to_relocate"),
    (r"non-?compete|non-?solicit|restrictive covenant", "non_compete"),
    (r"previously (work|employ)|worked (here|at)|been (an )?employee", "previously_worked_here"),
    (r"referr?ed (you|by)|employee refer", "referred_by_employee"),
    (r"years.*experience", "years_experience"),
    (r"gender", "gender"),
    (r"hispanic|latino", "hispanic_latino"),   # a Yes/No question, distinct from race
    (r"race|ethnicity", "race_ethnicity"),
    (r"veteran", "veteran_status"),
    (r"disability", "disability_status"),
    (r"comfortable.*remote|open to remote", "comfortable_remote"),
    (r"comfortable.*hybrid|open to hybrid", "comfortable_hybrid"),
    (r"comfortable.*onsite|on-?site|commut", "comfortable_onsite"),
    (r"currently reside|do you reside|reside in the (us|united states)", "currently_reside_us"),
    (r"start date|when can you start|available to start|earliest", "earliest_start"),
    (r"notice period", "notice_period"),
]


def load_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def resolve_answer(label: str, profile: dict, answers: dict, llm) -> str:
    """Return an answer string, or the ASK_HUMAN sentinel."""
    ll = label.lower()

    # 1. Answer bank by pattern.
    for pattern, key in BANK_PATTERNS:
        if re.search(pattern, ll):
            val = answers.get(key)
            if val == ASK_HUMAN:
                return ASK_HUMAN
            if val is not None:
                return str(val)

    # 2. Direct profile facts for a few obvious ones.
    if "linkedin" in ll:
        return profile.get("links", {}).get("linkedin", "") or ASK_HUMAN
    if "github" in ll:
        return profile.get("links", {}).get("github", "") or ASK_HUMAN
    loc = profile.get("location", {})
    if ll.strip() in {"state", "state/province", "state / province", "province"}:
        return loc.get("state", "") or ASK_HUMAN
    if ll.strip() in {"city", "town"} or re.search(r"\bcity\b", ll):
        return loc.get("city", "") or ASK_HUMAN
    if re.search(r"location|current location|where are you", ll):
        return f"{loc.get('city','')}, {loc.get('state','')}".strip(", ") or ASK_HUMAN
    if re.search(r"\bcountry\b", ll):
        return loc.get("country", "") or ASK_HUMAN
    if "zip" in ll or "postal" in ll:
        return loc.get("zip", "") or ASK_HUMAN

    # 3. Free-text → local LLM, grounded in the profile (may itself return ASK_HUMAN).
    prompt = (
        f"Candidate profile (JSON):\n{json.dumps(profile)}\n\n"
        f"Form question:\n{label}\n\n"
        "Write a truthful answer grounded only in the profile, or ASK_HUMAN if you cannot."
    )
    out = llm.generate(prompt).strip()
    # Guard: if the model wandered off, treat suspiciously-empty answers as a flag.
    if not out or out.upper() == ASK_HUMAN:
        return ASK_HUMAN
    return out
