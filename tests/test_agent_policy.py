"""Tests for the agent's decision policy — especially the grounding guard.

The guarantee under test: the policy fills a field only with a value grounded in the
candidate's real data; anything it can't ground truthfully becomes `flag_for_human`.
The loop picks the field; the policy decides how to handle it. Honesty is enforced in code.
"""
import tempfile

from jobrollo.agent.memory import Memory
from jobrollo.agent.perception import Field, Observation
from jobrollo.agent.policy import Policy
from jobrollo.llm import ASK_HUMAN


class FakeLLM:
    """Honesty/free-text calls return ASK_HUMAN, so any un-grounded field must be flagged."""
    def generate(self, prompt, system=None):
        return ASK_HUMAN


def _mem():
    return Memory("https://boards.greenhouse.io/acme/jobs/1",
                  store_path=tempfile.mktemp(suffix=".json"))


PROFILE = {"identity": {"email": "j@x.com"}, "location": {}, "links": {}}


def test_grounded_value_from_bank_is_used():
    obs = Observation("u", [Field("f0", "choice", "Do you require visa sponsorship?",
                                  ["Yes", "No"], required=True)])
    answers = {"require_sponsorship_now_or_future": "Yes"}
    action = Policy(FakeLLM()).decide(obs, PROFILE, answers, _mem())
    assert action.tool == "click_choice"
    assert action.value == "Yes"


def test_unanswerable_field_is_flagged_not_fabricated():
    obs = Observation("u", [Field("f0", "text", "Describe your active security clearance.",
                                  required=True)])
    action = Policy(FakeLLM()).decide(obs, PROFILE, {}, _mem())
    assert action.tool == "flag_for_human"


def test_resume_field_triggers_upload():
    obs = Observation("u", [Field("f0", "file", "Resume/CV", required=True)])
    assert Policy(FakeLLM()).decide(obs, PROFILE, {}, _mem()).tool == "upload_resume"


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
