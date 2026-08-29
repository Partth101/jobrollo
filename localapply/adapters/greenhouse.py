"""Greenhouse adapter — the reference implementation.

Greenhouse forms use standard inputs for name/email/phone, a file input for the resume, and
custom React-select dropdowns for screening + EEO questions. React-select is not a native
<select>; you click the control to open a listbox, then click the option. This adapter
encodes that dance, plus the honesty flow for free-text and dropdown questions.
"""
from __future__ import annotations

import re

from playwright.sync_api import Page

from ..llm import ASK_HUMAN
from .base import ATSAdapter, FieldFlag, FillResult
from ..answers import resolve_answer

# Map common Greenhouse field ids to profile paths.
BASIC_FIELDS = {
    "#first_name": ("identity", "legal_first_name"),
    "#last_name": ("identity", "legal_last_name"),
    "#email": ("identity", "email"),
    "#phone": ("identity", "phone"),
}


class GreenhouseAdapter(ATSAdapter):
    name = "greenhouse"

    @staticmethod
    def matches(url: str) -> bool:
        return "greenhouse.io" in url

    def fill(self, page: Page, profile: dict, answers: dict, llm) -> FillResult:
        res = FillResult(
            company=_company_from_url(page.url),
            role=_role_from_title(page.title()),
            ats=self.name,
            url=page.url,
        )
        try:
            page.wait_for_selector("#first_name, input[name=first_name]", timeout=15000)
        except Exception:
            res.ok = False
            res.error = "No Greenhouse application form found (job may be closed)."
            return res

        for selector, (a, b) in BASIC_FIELDS.items():
            if self._safe_fill(page, selector, str(profile.get(a, {}).get(b, ""))):
                res.filled.append(selector.lstrip("#"))

        res.resume_attached = self._upload_resume(page, profile["resume_path"])

        # Every labeled question that isn't a basic field: answer it honestly.
        for q in _collect_questions(page):
            self._answer_question(page, q, profile, answers, llm, res)

        return res

    # ---- question handling ---------------------------------------------------

    def _answer_question(self, page, q, profile, answers, llm, res):
        label, kind, handle = q["label"], q["kind"], q["handle"]
        value = resolve_answer(label, profile, answers, llm)

        if value == ASK_HUMAN:
            res.flagged.append(FieldFlag(label, "Could not answer truthfully from profile"))
            return

        if kind == "text":
            handle.fill(value)
            res.filled.append(label[:40])
        elif kind == "select":
            if self._pick_react_select(page, handle, value):
                res.filled.append(label[:40])
            else:
                res.flagged.append(FieldFlag(label, f"No option matched '{value}'"))

    def _pick_react_select(self, page: Page, control, want: str) -> bool:
        """Open a Greenhouse React-select control and click the best-matching option."""
        try:
            control.click()
            page.wait_for_timeout(400)
            options = page.query_selector_all('[role=option], .select__option')
            want_l = want.lower()
            # exact-ish first, then substring
            for opt in options:
                if opt.inner_text().strip().lower() == want_l:
                    opt.click()
                    return True
            for opt in options:
                if want_l in opt.inner_text().strip().lower():
                    opt.click()
                    return True
        except Exception:
            pass
        return False


# ---- page scraping helpers ---------------------------------------------------

def _collect_questions(page: Page) -> list[dict]:
    """Return [{label, kind, handle}] for each answerable question on the form."""
    out: list[dict] = []
    for group in page.query_selector_all("div.field, div[class*=field]"):
        label_el = group.query_selector("label")
        if not label_el:
            continue
        label = re.sub(r"\s+", " ", label_el.inner_text()).replace("*", "").strip()
        if not label or label.lower() in {"first name", "last name", "email", "phone"}:
            continue
        textarea = group.query_selector("textarea")
        if textarea:
            out.append({"label": label, "kind": "text", "handle": textarea})
            continue
        select = group.query_selector(".select__control, [class*=select__control]")
        if select:
            out.append({"label": label, "kind": "select", "handle": select})
    return out


def _company_from_url(url: str) -> str:
    m = re.search(r"greenhouse\.io/(?:embed/)?([^/]+)", url)
    return (m.group(1) if m else "unknown").replace("-", " ").title()


def _role_from_title(title: str) -> str:
    return re.sub(r"^(Job Application for|Application for)\s*", "", title).split(" at ")[0].strip()
