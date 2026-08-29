"""Ashby adapter.

Ashby forms use a single ``_systemfield_name`` field (not split first/last), a
``_systemfield_email``, ``_systemfield_resume`` file input, and custom questions keyed by
GUID. Yes/No questions render as button toggles; single-selects as listboxes; multi-selects
as checkboxes. This adapter maps the common shapes and defers everything else to honest
resolution.
"""
from __future__ import annotations

import re

from playwright.sync_api import Page

from ..answers import resolve_answer
from ..llm import ASK_HUMAN
from .base import ATSAdapter, FieldFlag, FillResult


class AshbyAdapter(ATSAdapter):
    name = "ashby"

    @staticmethod
    def matches(url: str) -> bool:
        return "jobs.ashbyhq.com" in url

    def fill(self, page: Page, profile: dict, answers: dict, llm) -> FillResult:
        res = FillResult(
            company=_slug(page.url), role=page.title().split("@")[0].strip() or page.title(),
            ats=self.name, url=page.url,
        )
        if "Job not found" in page.content():
            res.ok = False
            res.error = "Ashby job not found (closed)."
            return res

        ident = profile["identity"]
        full = f"{ident['legal_first_name']} {ident['legal_last_name']}"
        self._safe_fill(page, 'input[name=_systemfield_name]', full) and res.filled.append("name")
        self._safe_fill(page, 'input[name=_systemfield_email]', ident["email"]) and res.filled.append("email")
        # phone: first tel input
        tel = page.query_selector('input[type=tel]')
        if tel:
            tel.fill(ident["phone"])
            res.filled.append("phone")

        res.resume_attached = self._upload_resume(page, profile["resume_path"])

        for q in _collect_ashby_questions(page):
            self._answer(page, q, profile, answers, llm, res)
        return res

    def _answer(self, page, q, profile, answers, llm, res):
        label, node = q["label"], q["node"]
        value = resolve_answer(label, profile, answers, llm)
        if value == ASK_HUMAN:
            res.flagged.append(FieldFlag(label, "Could not answer truthfully from profile"))
            return
        # Yes/No button toggle
        for b in node.query_selector_all("button"):
            if b.inner_text().strip().lower() == value.strip().lower():
                b.click()
                res.filled.append(label[:40])
                return
        # text
        ta = node.query_selector("textarea, input[type=text]")
        if ta:
            ta.fill(value)
            res.filled.append(label[:40])
            return
        # listbox option
        for opt in node.query_selector_all("[role=option], li"):
            if value.lower() in opt.inner_text().strip().lower():
                opt.click()
                res.filled.append(label[:40])
                return
        res.flagged.append(FieldFlag(label, f"No matching control for '{value}'"))


def _collect_ashby_questions(page: Page) -> list[dict]:
    out = []
    for fld in page.query_selector_all("[class*=_fieldEntry], fieldset, [class*=FieldEntry]"):
        title = fld.query_selector("[class*=QuestionTitle], label, legend")
        if not title:
            continue
        label = re.sub(r"\s+", " ", title.inner_text()).replace("*", "").strip()
        if not label or label.lower() in {"name", "email", "phone", "resume"}:
            continue
        out.append({"label": label, "node": fld})
    return out


def _slug(url: str) -> str:
    m = re.search(r"ashbyhq\.com/([^/]+)", url)
    return (m.group(1) if m else "unknown").replace("-", " ").title()
