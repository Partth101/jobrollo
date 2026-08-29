"""The agent's action space.

A small, typed set of tools. The policy emits one `Action`; the executor performs it against
the page and returns an `ActionResult`. Two invariants are enforced *here*, in code, not by
convention:

  * There is NO submit tool. The agent cannot submit an application.
  * `flag_for_human` is a first-class action — the honest way to "handle" a field the agent
    must not answer itself.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ToolName = Literal[
    "fill_text",       # type text into an input/textarea
    "select_option",   # choose an option in a native <select> or react-select
    "click_choice",    # pick a radio / button-toggle / listbox option by visible text
    "upload_resume",   # attach the résumé to the file input
    "flag_for_human",  # leave this field for the human, with a reason (honesty)
    "finish",          # nothing left to do on this page
]


class Action(BaseModel):
    tool: ToolName
    ref: Optional[str] = Field(None, description="Target field ref from the observation")
    value: Optional[str] = Field(None, description="Text to type, option to pick, etc.")
    reason: str = Field("", description="Why — especially required for flag_for_human")


class ActionResult(BaseModel):
    ok: bool
    detail: str = ""


def execute(action: Action, page, resume_path: str) -> ActionResult:
    fn = _DISPATCH.get(action.tool)
    if not fn:
        return ActionResult(ok=False, detail=f"unknown tool {action.tool}")
    try:
        return fn(action, page, resume_path)
    except Exception as e:  # noqa: BLE001 - agent must survive a bad action and self-correct
        return ActionResult(ok=False, detail=f"{type(e).__name__}: {e}")


def _loc(page, ref: str):
    return page.locator(f"[data-la-ref='{ref}']")


def _fill_text(a: Action, page, _r) -> ActionResult:
    _loc(page, a.ref).fill(a.value or "")
    return ActionResult(ok=True, detail=f"typed into {a.ref}")


import re

# Phrases that all mean "decline / no answer", so EEO options match across sites.
_DECLINE = ("decline", "do not want", "don't want", "dont want", "prefer not",
            "don't wish", "dont wish", "do not wish", "not to answer", "wish not")


def _best_match(want: str, texts: list[str]) -> int | None:
    """Index of the option that best matches `want`, or None. Robust to EEO phrasing."""
    w = (want or "").strip().lower()
    if not w:
        return None
    norm = [t.strip().lower() for t in texts]
    for i, t in enumerate(norm):                       # exact
        if t == w:
            return i
    for i, t in enumerate(norm):                       # substring either direction
        if t and (w in t or t in w):
            return i
    if any(d in w for d in _DECLINE):                  # decline synonyms
        for i, t in enumerate(norm):
            if any(d in t for d in _DECLINE):
                return i
    wt = set(re.findall(r"[a-z]+", w))                 # token overlap
    best, score = None, 0
    for i, t in enumerate(norm):
        s = len(wt & set(re.findall(r"[a-z]+", t)))
        if s > score:
            best, score = i, s
    return best if score >= 2 else None


def _select_option(a: Action, page, _r) -> ActionResult:
    loc = _loc(page, a.ref)
    try:                                               # native <select>
        opts = [o.inner_text() for o in loc.locator("option").all()]
        idx = _best_match(a.value, opts)
        if idx is not None:
            loc.select_option(label=opts[idx].strip())
            return ActionResult(ok=True, detail=f"selected {opts[idx].strip()}")
    except Exception:
        pass
    loc.click()                                        # react-select: open, then click option
    page.wait_for_timeout(350)
    els = page.query_selector_all("[role=option], .select__option, li[role=option]")
    idx = _best_match(a.value, [e.inner_text() for e in els])
    if idx is not None:
        els[idx].click()
        return ActionResult(ok=True, detail=f"picked {els[idx].inner_text().strip()}")
    return ActionResult(ok=False, detail=f"no option matched {a.value!r}")


def _click_choice(a: Action, page, _r) -> ActionResult:
    scope = _loc(page, a.ref)
    pool = []
    for sel in ("button", "input[type=radio]", "label", "[role=option]"):
        pool += (scope.locator(sel).all() if scope.count() else page.locator(sel).all())
    texts = []
    for el in pool:
        try:
            texts.append(el.inner_text())
        except Exception:
            texts.append("")
    idx = _best_match(a.value, texts)
    if idx is not None:
        pool[idx].click()
        return ActionResult(ok=True, detail=f"clicked {texts[idx].strip()}")
    return ActionResult(ok=False, detail=f"no choice matched {a.value!r}")


def _upload_resume(_a: Action, page, resume_path: str) -> ActionResult:
    fi = page.query_selector("input[type=file]")
    if not fi:
        return ActionResult(ok=False, detail="no file input")
    fi.set_input_files(resume_path)
    return ActionResult(ok=True, detail="résumé attached")


def _flag(a: Action, _page, _r) -> ActionResult:
    return ActionResult(ok=True, detail=f"flagged: {a.reason}")


def _finish(_a: Action, _page, _r) -> ActionResult:
    return ActionResult(ok=True, detail="finished")


_DISPATCH = {
    "fill_text": _fill_text,
    "select_option": _select_option,
    "click_choice": _click_choice,
    "upload_resume": _upload_resume,
    "flag_for_human": _flag,
    "finish": _finish,
}
