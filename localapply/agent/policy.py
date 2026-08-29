"""The decision policy — the agent's "brain."

Given an Observation of the current form, the policy decides the next Action. It is a hybrid:

  1. An LLM *planner* reasons over the whole form and proposes the next action as JSON.
  2. A deterministic *grounding guard* verifies any value against the candidate's real data
     (answer bank + profile). If a value isn't grounded — a fact the profile doesn't support —
     the guard overrides the action to `flag_for_human`. Honesty is enforced in code, not hope.
  3. If the local model returns malformed JSON, we fall back to a deterministic field-by-field
     policy so the agent never stalls.

This is what makes it an agent rather than a script: it plans over an unseen form, its actions
are checked and can be overridden, and it self-corrects across steps (see core.py).
"""
from __future__ import annotations

import json
import re

from ..answers import resolve_answer
from ..llm import ASK_HUMAN
from .actions import Action
from .perception import Field, Observation

PLANNER_SYSTEM = """You are the decision policy of a job-application agent. You see a list of
unfilled form fields and the candidate's profile. Choose the SINGLE next action.

Respond with ONE JSON object only, no prose:
  {"tool": "...", "ref": "...", "value": "...", "reason": "..."}

Tools:
  fill_text      - type text (ref = a text/textarea field)
  select_option  - choose a dropdown option (value = option text)
  click_choice   - pick a radio/button/listbox option (value = option text)
  upload_resume  - attach the résumé (no ref/value)
  flag_for_human - leave a field for the human (reason required)
  finish         - nothing left to do

Rules:
  - Prefer required, unfilled fields first.
  - NEVER invent facts. If a field needs information the profile does not support, use
    flag_for_human. There is no submit tool.
  - value must be grounded in the profile."""


def _json_extract(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


class Policy:
    def __init__(self, llm):
        self.llm = llm

    # ---- main entrypoint -----------------------------------------------------

    def decide(self, obs: Observation, profile: dict, answers: dict, memory) -> Action:
        if obs.at_submit_step or not obs.actionable():
            return Action(tool="finish", reason="form complete or at submit step")

        action = self._plan(obs, profile) or self._fallback(obs)
        return self._ground_and_guard(action, obs, profile, answers, memory)

    # ---- 1. LLM planner ------------------------------------------------------

    def _plan(self, obs: Observation, profile: dict) -> Action | None:
        prompt = (
            f"CANDIDATE PROFILE:\n{json.dumps(profile)}\n\n"
            f"UNFILLED FIELDS:\n{obs.render()}\n\n"
            "Return the JSON action for the next field."
        )
        raw = self.llm.generate(prompt, system=PLANNER_SYSTEM)
        data = _json_extract(raw)
        if not data:
            return None
        try:
            return Action(**{k: data.get(k) for k in ("tool", "ref", "value", "reason")})
        except Exception:
            return None

    # ---- 2. deterministic fallback ------------------------------------------

    def _fallback(self, obs: Observation) -> Action:
        f = obs.actionable()[0]
        tool = {
            "text": "fill_text", "textarea": "fill_text",
            "select": "select_option", "choice": "click_choice",
            "radio": "click_choice", "checkbox": "click_choice", "file": "upload_resume",
        }.get(f.kind, "flag_for_human")
        return Action(tool=tool, ref=f.ref, reason="deterministic fallback")

    # ---- 3. grounding guard (honesty enforced in code) -----------------------

    def _ground_and_guard(self, action: Action, obs: Observation,
                          profile: dict, answers: dict, memory) -> Action:
        if action.tool in {"finish", "upload_resume", "flag_for_human"}:
            return action

        fld = self._field(obs, action.ref)
        if fld is None:
            return Action(tool="finish", reason="target field not found")

        # Reuse a remembered decision for identical labels (consistency + speed).
        remembered = memory.recall(fld.label)
        grounded = remembered if remembered is not None else resolve_answer(
            fld.label, profile, answers, self.llm
        )

        if grounded == ASK_HUMAN:
            return Action(tool="flag_for_human", ref=fld.ref,
                          reason="Not answerable truthfully from profile")

        # For choice/select we trust the grounded value over whatever the planner guessed,
        # so the agent can't drift into a fabricated option.
        memory.remember(fld.label, grounded)
        return Action(tool=action.tool, ref=fld.ref, value=grounded, reason=action.reason)

    @staticmethod
    def _field(obs: Observation, ref: str | None) -> Field | None:
        if ref is None:
            return None
        return next((f for f in obs.fields if f.ref == ref), None)
