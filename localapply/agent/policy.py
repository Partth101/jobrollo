"""The decision policy — the agent's "brain."

Design note (learned from running it against real forms): small local models are unreliable
at *picking which field* to act on by opaque ref — one hallucinated ref shouldn't abort a
whole application. So responsibility is split for robustness:

  * The agent LOOP chooses the next field deterministically (first unfilled/pending).
  * The POLICY decides how to handle THAT field: pick the tool from its type, and resolve a
    *grounded* value (answer bank → profile facts → honesty-constrained local LLM). If the value
    can't be grounded, it emits `flag_for_human`. Honesty is enforced in code, not by prompt.

This keeps the interesting, model-driven part (generating and honesty-checking free-text
answers) where the model is strong, and the brittle part (DOM targeting) deterministic.
"""
from __future__ import annotations

import re

from ..answers import resolve_answer
from ..llm import ASK_HUMAN
from .actions import Action
from .perception import Field, Observation

# Match only actual résumé-upload fields, not any question that mentions "resume"
# (e.g. "may we share your resume with partners?" is a consent, not an upload).
RESUME_HINT = re.compile(r"^(resume/?cv|attach resume|upload resume|resume\s*$)", re.IGNORECASE)

# Field kind → tool.
TOOL_FOR_KIND = {
    "text": "fill_text",
    "textarea": "fill_text",
    "select": "select_option",
    "choice": "click_choice",
    "radio": "click_choice",
    "checkbox": "click_choice",
    "file": "upload_resume",
}


class Policy:
    def __init__(self, llm):
        self.llm = llm

    def decide(self, obs: Observation, profile: dict, answers: dict, memory) -> Action:
        pending = obs.actionable()
        if obs.at_submit_step or not pending:
            return Action(tool="finish", reason="form complete or at submit step")

        fld = pending[0]

        # Résumé upload: detected by a file input or a résumé/attach label.
        if fld.kind == "file" or RESUME_HINT.search(fld.label):
            return Action(tool="upload_resume", ref=fld.ref, reason="attach résumé")

        # Multi-selects (e.g. "languages, check all that apply") and lone consent checkboxes
        # are judgment calls we won't make for the candidate.
        if fld.kind == "multiselect":
            return Action(tool="flag_for_human", ref=fld.ref,
                          reason="Multi-select — please choose the applicable options")
        if fld.kind == "checkbox":
            return Action(tool="flag_for_human", ref=fld.ref,
                          reason="Checkbox/consent — your decision")

        # A grounded value — remembered, else resolved (bank → profile → honest LLM).
        value = memory.recall(fld.label)
        if value is None:
            value = resolve_answer(fld.label, profile, answers, self.llm)

        if value == ASK_HUMAN or value == "":
            return Action(tool="flag_for_human", ref=fld.ref,
                          reason="Not answerable truthfully from profile")

        memory.remember(fld.label, value)
        tool = TOOL_FOR_KIND.get(fld.kind, "flag_for_human")
        if tool == "flag_for_human":
            return Action(tool="flag_for_human", ref=fld.ref,
                          reason=f"Unsupported field kind: {fld.kind}")
        return Action(tool=tool, ref=fld.ref, value=value, reason="grounded answer")

    @staticmethod
    def _field(obs: Observation, ref: str | None) -> Field | None:
        return next((f for f in obs.fields if f.ref == ref), None) if ref else None
