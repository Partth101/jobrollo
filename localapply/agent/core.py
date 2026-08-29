"""The agent loop.

    while not done and steps < budget:
        obs    = perceive(page)          # eyes
        action = policy.decide(obs, ...) # brain  (LLM plan + grounding guard)
        result = execute(action, page)   # hands
        verify = perceive(page)          # did it take? → self-correction / progress

This is the whole point of the project: one loop that fills *any* application form by
reasoning over its structure, instead of a bespoke script per company. Safety is structural —
there is no submit action, and the loop halts the moment the page looks like a submit/review
step.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import re

from .actions import Action, execute
from .memory import Memory
from .perception import Observation, perceive
from .policy import Policy


def _key(label: str) -> str:
    """Stable identity for a field across re-perceptions: its normalized label."""
    return re.sub(r"\s+", " ", (label or "").strip().lower())


@dataclass
class Flag:
    label: str
    reason: str


@dataclass
class AgentResult:
    url: str
    filled: list[str] = field(default_factory=list)
    flagged: list[Flag] = field(default_factory=list)
    resume_attached: bool = False
    steps: int = 0
    stopped_reason: str = ""


class Agent:
    def __init__(self, llm, resume_path: str, step_budget: int = 60):
        self.policy = Policy(llm)
        self.resume_path = resume_path
        self.step_budget = step_budget

    def run(self, page, profile: dict, answers: dict) -> AgentResult:
        mem = Memory(page.url)
        res = AgentResult(url=page.url)
        # Loop-avoidance keys on the field LABEL, not the positional ref: perception
        # reassigns f0..fN every cycle, and choice/select fields don't report a value back,
        # so a ref- or value-based guard would re-act them forever.
        handled: set[str] = set()

        for step in range(self.step_budget):
            res.steps = step + 1
            obs = perceive(page)

            if obs.at_submit_step:
                res.stopped_reason = "reached submit/review step — human gate"
                break

            pending = [f for f in obs.actionable() if _key(f.label) not in handled]
            if not pending:
                res.stopped_reason = "no actionable fields left"
                break

            obs = Observation(url=obs.url, fields=pending, at_submit_step=False)
            action = self.policy.decide(obs, profile, answers, mem)

            if action.tool == "finish":
                res.stopped_reason = "policy finished"
                break

            label = self._label(obs, action.ref)
            self._apply(action, page, obs, res, mem)
            # Always mark handled (even upload/failed actions) so we never loop on one field.
            handled.add(_key(label) or f"__{action.tool}")

        mem.flush()
        return res

    # ---- helpers -------------------------------------------------------------

    def _apply(self, action: Action, page, obs: Observation, res: AgentResult, mem: Memory):
        if action.tool == "flag_for_human":
            label = self._label(obs, action.ref)
            res.flagged.append(Flag(label, action.reason or "left for human"))
            return
        out = execute(action, page, self.resume_path)
        if action.tool == "upload_resume":
            res.resume_attached = out.ok
        elif out.ok:
            res.filled.append(self._label(obs, action.ref) or action.value or action.tool)

    @staticmethod
    def _label(obs: Observation, ref: str | None) -> str:
        f = next((x for x in obs.fields if x.ref == ref), None)
        return f.label if f else ""

    @staticmethod
    def _progressed(page, action: Action) -> bool:
        if action.tool in {"upload_resume", "flag_for_human"}:
            return True
        try:
            loc = page.locator(f"[data-la-ref='{action.ref}']")
            return bool(loc.count() and (loc.input_value() or "").strip())
        except Exception:
            return True
