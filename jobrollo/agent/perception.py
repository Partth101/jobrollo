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

# Signals that we've landed on a POST-submission confirmation page — the agent must not try
# to "fill" a thank-you page. NOTE: we deliberately do NOT match a "Submit application" button,
# because that button is always present on the fill form; matching it would halt us before we
# ever fill anything. The normal stop condition is simply "no actionable fields left" — the
# human then clicks submit. There is no submit tool, so we can never submit by accident.
SUBMIT_SIGNALS = re.compile(
    r"(thank you for applying|application (was )?submitted|"
    r"application has been (received|submitted)|we('| ha)ve received your application)",
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
    idx = [0]

    def add(handle, kind, label, options=None, value="", required=False):
        ref = f"f{idx[0]}"
        idx[0] += 1
        try:
            handle.evaluate("(el, r) => el.setAttribute('data-la-ref', r)", ref)
        except Exception:
            pass
        label = (label or "").strip()
        if label.lower() in {"search", "search jobs", "keyword"}:
            return
        fields.append(Field(ref=ref, kind=kind, label=label,
                            options=options or [], value=value or "", required=required))

    # 1. Radio + checkbox groups (grouped by `name`). A radio/checkbox's OWN label is the
    #    option ("Yes"/"English"); the real QUESTION lives on the card/fieldset container.
    for typ, group_kind in (("radio", "choice"), ("checkbox", "multiselect")):
        groups: dict[str, list] = {}
        for el in page.query_selector_all(f"input[type={typ}]"):
            try:
                key = el.get_attribute("name") or _own_label(el)
                groups.setdefault(key, []).append(el)
            except Exception:
                continue
        for els in groups.values():
            first = els[0]
            opts = [o for o in (_own_label(e) for e in els) if o]
            question = _clean_label(_container_text(first), opts) or _label_for(first)
            required = any(_required(e) for e in els)
            kind = group_kind if len(els) > 1 else ("choice" if typ == "radio" else "checkbox")
            add(first, kind, question, opts, "", required)

    # 2. Everything else (text, textarea, native + react selects). Skip already-tagged radios.
    for el in page.query_selector_all(
        "input, textarea, select, [role=combobox], [role=radiogroup], [role=group]"
    ):
        try:
            if el.get_attribute("type") in {"radio", "checkbox"}:
                continue
            kind, options, value = _classify(el)
            if kind is None:
                continue
            label = _label_for(el)
            if not label or _noisy(label):
                label = _clean_label(_container_text(el), options) or label
            add(el, kind, label, options, value, _required(el))
        except Exception:
            continue
    return fields


def _noisy(label: str) -> bool:
    """A label is 'noisy' when innerText scooped up the option list (common on native selects)."""
    return len(label) > 80 or "select ..." in label.lower() or "select..." in label.lower()


def _own_label(el) -> str:
    """A radio/checkbox's OWN label — the option text (Yes / English / I consent)."""
    for js in (
        "e => e.labels && e.labels[0] ? e.labels[0].innerText : ''",
        "e => e.getAttribute('aria-label') || ''",
        "e => { const p = e.closest('label'); return p ? p.innerText : ''; }",
        "e => e.value || ''",
    ):
        try:
            t = el.evaluate(js)
            if t and t.strip():
                return re.sub(r"\s+", " ", t).strip()[:60]
        except Exception:
            continue
    return ""


def _container_text(el) -> str:
    """Full text of the field's QUESTION container (question + its options, to be stripped)."""
    js = """e => {
      const c = e.closest('li.application-question, .application-question, fieldset,'
        + '[class*=QuestionEntry], [class*=FieldEntry]');
      return c ? c.innerText : '';
    }"""
    try:
        return re.sub(r"\s+", " ", el.evaluate(js)).strip()
    except Exception:
        return ""


def _clean_label(raw: str, opts: list[str]) -> str:
    """Turn a container's text into just the question by removing option strings + placeholders."""
    if not raw:
        return ""
    for o in sorted(opts, key=len, reverse=True):        # remove longest options first
        raw = raw.replace(o, " ")
    raw = re.sub(r"select\s*\.\.\.", " ", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s+", " ", raw).replace("✱", "").replace("*", "").strip(" -:••")
    return raw


# The résumé upload widget renders as a button group; the real work is done by the file input.
RESUME_WIDGET_OPTS = {"attach", "dropbox", "google drive", "enter manually"}


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
        # A React-select / autocomplete renders as a text input inside a select control.
        # Treat it as a dropdown so the action layer opens it and clicks the option.
        if _is_combo(el):
            return "select", [], ""
        return "text", [], el.input_value() if _has_value(el) else ""
    role = (el.get_attribute("role") or "").lower()
    if role in {"combobox", "radiogroup", "group"}:
        opts = [o.inner_text().strip() for o in el.query_selector_all("[role=option], button, label")]
        opts = [o for o in opts if o]
        # Skip the résumé button-group; the file input handles the actual upload.
        if opts and {o.lower() for o in opts} & RESUME_WIDGET_OPTS:
            return None, None, None
        # A wrapper with no pickable options is not actionable (e.g. a closed react-select
        # container that duplicates the real <input>); skip it to avoid empty-label loops.
        if not opts:
            return None, None, None
        return "choice", opts, ""
    return None, None, None


def _is_combo(el) -> bool:
    try:
        return bool(el.evaluate(
            "e => (e.getAttribute('role')||'')==='combobox' "
            "|| e.getAttribute('aria-autocomplete')!=null "
            "|| !!e.closest('.select__control,[class*=select__control],[class*=Select__control]')"
        ))
    except Exception:
        return False


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
