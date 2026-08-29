"""Perception: turn a live web page into a compact, model-readable Observation.

This is the agent's "eyes." Instead of hardcoding one company's form, we normalize *any*
application form into a flat list of interactive `Field`s (label, kind, options, value,
required, and a stable locator). The policy reasons over this structure, so the same agent
handles Greenhouse, Lever, Ashby, Workday, or a form it has never seen.

Kept deliberately dependency-light at import time: Playwright is only touched inside
`perceive()`, so the schema is importable (and testable) without a browser.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field

# Signals that we've reached a terminal review/submit step. The agent STOPS here — it never
# submits. Detection is intentionally generous: a false "stop" is safe; a false "continue"
# risks clicking submit, which must never happen.
SUBMIT_SIGNALS = re.compile(
    r"\b(submit application|submit your application|review your application|"
    r"thank you for applying|application submitted)\b",
    re.IGNORECASE,
)


@dataclass
class Field:
    ref: str                      # stable locator the actions layer can act on
    kind: str                     # text | textarea | select | radio | checkbox | file | choice
    label: str
    options: list[str] = dc_field(default_factory=list)
    value: str = ""
    required: bool = False

    @property
    def filled(self) -> bool:
        return bool(self.value.strip())

    def render(self) -> str:
        req = "*" if self.required else ""
        opts = f" options={self.options}" if self.options else ""
        val = f" value={self.value!r}" if self.value else ""
        return f"[{self.ref}] ({self.kind}{req}) {self.label!r}{opts}{val}"


@dataclass
class Observation:
    url: str
    fields: list[Field]
    at_submit_step: bool = False

    def unfilled_required(self) -> list[Field]:
        return [f for f in self.fields if f.required and not f.filled]

    def actionable(self) -> list[Field]:
        """Required-unfilled first, then optional-unfilled — what still needs a decision."""
        req = [f for f in self.fields if f.required and not f.filled]
        opt = [f for f in self.fields if not f.required and not f.filled]
        return req + opt

    def render(self, limit: int = 40) -> str:
        return "\n".join(f.render() for f in self.actionable()[:limit])


def perceive(page) -> Observation:
    """Serialize the current page into an Observation. `page` is a Playwright Page."""
    at_submit = bool(SUBMIT_SIGNALS.search(page.title() + " " + _visible_text(page)))
    return Observation(url=page.url, fields=_extract_fields(page), at_submit_step=at_submit)


# --------------------------------------------------------------------------- helpers

def _visible_text(page) -> str:
    try:
        return page.inner_text("body")[:4000]
    except Exception:
        return ""


def _extract_fields(page) -> list[Field]:
    fields: list[Field] = []
    idx = 0

    def add(handle, kind, label, options=None, value="", required=False):
        nonlocal idx
        ref = f"f{idx}"
        try:
            handle.evaluate("(el, r) => el.setAttribute('data-la-ref', r)", ref)
        except Exception:
            pass
        fields.append(Field(ref=ref, kind=kind, label=label or "",
                            options=options or [], value=value or "", required=required))
        idx += 1

    for el in page.query_selector_all(
        "input, textarea, select, [role=combobox], [role=radiogroup], [role=group]"
    ):
        try:
            kind, options, value = _classify(el)
            if kind is None:
                continue
            add(el, kind, _label_for(el), options, value, _required(el))
        except Exception:
            continue
    return fields


def _classify(el):
    tag = (el.evaluate("e => e.tagName") or "").lower()
    typ = (el.get_attribute("type") or "").lower()
    if tag == "input" and typ in {"hidden", "submit", "button"}:
        return None, None, None
    if tag == "input" and typ == "file":
        return "file", [], ""
    if tag == "input" and typ in {"radio", "checkbox"}:
        return typ, [], el.get_attribute("value") or ""
    if tag == "textarea":
        return "textarea", [], el.input_value() if _has_value(el) else ""
    if tag == "select":
        opts = [o.inner_text().strip() for o in el.query_selector_all("option")]
        return "select", opts, ""
    if tag == "input":
        return "text", [], el.input_value() if _has_value(el) else ""
    role = (el.get_attribute("role") or "").lower()
    if role in {"combobox", "radiogroup", "group"}:
        opts = [o.inner_text().strip() for o in el.query_selector_all("[role=option], button, label")]
        return "choice", [o for o in opts if o], ""
    return None, None, None


def _has_value(el) -> bool:
    try:
        return bool(el.input_value())
    except Exception:
        return False


def _label_for(el) -> str:
    for js in (
        "e => e.labels && e.labels[0] ? e.labels[0].innerText : ''",
        "e => e.getAttribute('aria-label') || ''",
        "e => e.getAttribute('placeholder') || ''",
        "e => { const g = e.closest('[class*=field],fieldset,[class*=FieldEntry]');"
        "return g ? (g.querySelector('label,legend,[class*=QuestionTitle]')||{}).innerText||'' : ''; }",
    ):
        try:
            txt = el.evaluate(js)
            if txt and txt.strip():
                return re.sub(r"\s+", " ", txt).replace("*", "").strip()
        except Exception:
            continue
    return ""


def _required(el) -> bool:
    try:
        if el.get_attribute("required") is not None or el.get_attribute("aria-required") == "true":
            return True
        lab = _label_for(el)
        return "*" in (el.evaluate("e => (e.closest('[class*=field],fieldset)||{}).innerText || ''") or "")
    except Exception:
        return False
