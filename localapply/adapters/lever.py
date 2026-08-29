"""Lever adapter.

Lever forms use predictable input names (name, email, phone, org, urls[...]) plus custom
cards and a native-<select> EEO block. Two gotchas encoded here: a cookie banner can eat the
file chooser, and the resume file input is visually hidden — so we dismiss the banner and set
files on the input directly. Lever shows an hCaptcha at submit; we never reach it (human-gated).
"""
from __future__ import annotations

import re

from playwright.sync_api import Page

from ..answers import resolve_answer
from ..llm import ASK_HUMAN
from .base import ATSAdapter, FieldFlag, FillResult

FIELD_MAP = {
    'input[name=name]': ("identity", "preferred_name_full"),
    'input[name=email]': ("identity", "email"),
    'input[name=phone]': ("identity", "phone"),
    'input[name=org]': ("_", "current_company"),
    'input[name="urls[LinkedIn]"]': ("links", "linkedin"),
    'input[name="urls[GitHub]"]': ("links", "github"),
}


class LeverAdapter(ATSAdapter):
    name = "lever"

    @staticmethod
    def matches(url: str) -> bool:
        return "jobs.lever.co" in url

    def fill(self, page: Page, profile: dict, answers: dict, llm) -> FillResult:
        res = FillResult(
            company=_slug(page.url), role=page.title().split(" - ")[-1],
            ats=self.name, url=page.url,
        )
        _dismiss_cookie_banner(page)

        full_name = f"{profile['identity']['legal_first_name']} {profile['identity']['legal_last_name']}"
        self._safe_fill(page, 'input[name=name]', full_name) and res.filled.append("name")
        self._safe_fill(page, 'input[name=email]', profile["identity"]["email"]) and res.filled.append("email")
        self._safe_fill(page, 'input[name=phone]', profile["identity"]["phone"]) and res.filled.append("phone")
        self._safe_fill(page, 'input[name=org]', profile.get("_current_company", "")) and res.filled.append("company")
        self._safe_fill(page, 'input[name="urls[LinkedIn]"]', profile["links"].get("linkedin", ""))
        self._safe_fill(page, 'input[name="urls[GitHub]"]', profile["links"].get("github", ""))

        res.resume_attached = self._upload_resume(page, profile["resume_path"])

        # Native-select EEO block.
        _set_native_select(page, 'select[name="eeo[gender]"]', profile["eeo"]["gender"])
        _set_native_select(page, 'select[name="eeo[race]"]', profile["eeo"]["race_ethnicity"])
        _set_native_select(page, 'select[name="eeo[veteran]"]', profile["eeo"]["veteran_status"])

        # Custom cards (work auth, sponsorship, free-text) — honest resolution.
        for card in page.query_selector_all(".application-question, li.application-question"):
            label_el = card.query_selector(".application-label, label")
            if not label_el:
                continue
            label = re.sub(r"\s+", " ", label_el.inner_text()).replace("✱", "").strip()
            value = resolve_answer(label, profile, answers, llm)
            if value == ASK_HUMAN:
                res.flagged.append(FieldFlag(label, "Could not answer truthfully from profile"))
                continue
            _answer_lever_card(card, value, res)

        return res


def _answer_lever_card(card, value, res):
    ta = card.query_selector("textarea")
    if ta:
        ta.fill(value)
        res.filled.append(value[:30])
        return
    # radio/button choice
    for el in card.query_selector_all("input[type=radio], button, label"):
        try:
            if value.lower() in el.inner_text().strip().lower():
                el.click()
                res.filled.append(value[:30])
                return
        except Exception:
            continue


def _dismiss_cookie_banner(page: Page):
    for text in ("Deny", "Decline", "Reject", "Accept"):
        try:
            btn = page.get_by_role("button", name=re.compile(text, re.I))
            if btn.count():
                btn.first.click(timeout=1500)
                return
        except Exception:
            continue


def _set_native_select(page: Page, selector: str, want: str):
    try:
        el = page.query_selector(selector)
        if not el:
            return
        for opt in el.query_selector_all("option"):
            if want.split()[0].lower() in opt.inner_text().lower():
                page.select_option(selector, label=opt.inner_text())
                return
    except Exception:
        pass


def _slug(url: str) -> str:
    m = re.search(r"lever\.co/([^/]+)", url)
    return (m.group(1) if m else "unknown").replace("-", " ").title()
