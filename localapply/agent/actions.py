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


def _select_option(a: Action, page, _r) -> ActionResult:
    loc = _loc(page, a.ref)
    # native <select> first
    try:
        loc.select_option(label=a.value)
        return ActionResult(ok=True, detail=f"selected {a.value}")
    except Exception:
        pass
    # react-select / custom: open then click the matching option
    loc.click()
    page.wait_for_timeout(300)
    want = (a.value or "").strip().lower()
    for opt in page.query_selector_all("[role=option], .select__option, li[role=option]"):
        if want and want in opt.inner_text().strip().lower():
            opt.click()
            return ActionResult(ok=True, detail=f"picked {a.value}")
    return ActionResult(ok=False, detail=f"no option matched {a.value!r}")


def _click_choice(a: Action, page, _r) -> ActionResult:
    want = (a.value or "").strip().lower()
    scope = _loc(page, a.ref)
    for sel in ("button", "input[type=radio]", "label", "[role=option]"):
        for el in scope.locator(sel).all() if scope.count() else page.locator(sel).all():
            try:
                if want and want == el.inner_text().strip().lower():
                    el.click()
                    return ActionResult(ok=True, detail=f"clicked {a.value}")
            except Exception:
                continue
    # fall back to substring match
    for el in page.locator("button, [role=option], label").all():
        try:
            if want and want in el.inner_text().strip().lower():
                el.click()
                return ActionResult(ok=True, detail=f"clicked ~{a.value}")
        except Exception:
            continue
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
