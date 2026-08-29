"""Tests for the agent's decision policy — especially the grounding guard.

The guarantee under test: the agent uses grounded answers where they exist, and *cannot*
fill a field it can't answer truthfully — it must flag it. Honesty is enforced by code.
"""
import json
import tempfile

from localapply.agent.memory import Memory
from localapply.agent.perception import Field, Observation
from localapply.agent.policy import PLANNER_SYSTEM, Policy
from localapply.llm import ASK_HUMAN


class FakeLLM:
    """Planner returns a (deliberately wrong) value; honesty calls return ASK_HUMAN."""
    def generate(self, prompt, system=None):
        if system == PLANNER_SYSTEM:
            return json.dumps({"tool": "click_choice", "ref": "f0",
                               "value": "FABRICATED", "reason": "planner guess"})
        return ASK_HUMAN


def _mem():
    return Memory("https://boards.greenhouse.io/acme/jobs/1",
                  store_path=tempfile.mktemp(suffix=".json"))


PROFILE = {"identity": {"email": "j@x.com"}, "location": {}, "links": {}}


def test_guard_overrides_planner_with_grounded_value():
    """Planner says 'FABRICATED'; guard must replace it with the grounded bank answer."""
    obs = Observation("u", [Field("f0", "choice", "Do you require visa sponsorship?",
                                  ["Yes", "No"], required=True)])
    answers = {"require_sponsorship_now_or_future": "Yes"}
    action = Policy(FakeLLM()).decide(obs, PROFILE, answers, _mem())
    assert action.tool == "click_choice"
    assert action.value == "Yes"          # grounded, NOT the planner's fabrication


def test_unanswerable_field_is_flagged_not_fabricated():
    obs = Observation("u", [Field("f0", "text", "Describe your active security clearance.",
                                  required=True)])
    action = Policy(FakeLLM()).decide(obs, PROFILE, {}, _mem())
    assert action.tool == "flag_for_human"


def test_submit_step_finishes_without_acting():
    obs = Observation("u", [Field("f0", "text", "First name", required=True)], at_submit_step=True)
    assert Policy(FakeLLM()).decide(obs, PROFILE, {}, _mem()).tool == "finish"


def test_memory_makes_repeat_fields_consistent():
    mem = _mem()
    answers = {"require_sponsorship_now_or_future": "Yes"}
    obs = Observation("u", [Field("f0", "choice", "Require visa sponsorship?", required=True)])
    a1 = Policy(FakeLLM()).decide(obs, PROFILE, answers, mem)
    assert mem.recall("Require visa sponsorship?") == "Yes"
    assert a1.value == "Yes"
