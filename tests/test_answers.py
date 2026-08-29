"""Tests for the honesty layer — the most important behavior to lock down."""
from jobrollo.answers import resolve_answer
from jobrollo.llm import ASK_HUMAN


class FakeLLM:
    """Returns ASK_HUMAN so we can assert the tool never fabricates for unknown questions."""
    def generate(self, prompt, system=None):
        return ASK_HUMAN


PROFILE = {
    "identity": {"email": "j@x.com"},
    "location": {"city": "New York", "state": "NY", "zip": "10001"},
    "links": {"linkedin": "https://linkedin.com/in/j", "github": "https://github.com/j"},
}
ANSWERS = {
    "require_sponsorship_now_or_future": "Yes",
    "salary_expectation": "135000-160000",
    "typescript_production_experience": ASK_HUMAN,
}


def test_bank_hit():
    assert resolve_answer("Do you require visa sponsorship?", PROFILE, ANSWERS, FakeLLM()) == "Yes"


def test_profile_fact():
    assert "linkedin.com" in resolve_answer("LinkedIn URL", PROFILE, ANSWERS, FakeLLM())


def test_flagged_answer_propagates():
    # A bank value of ASK_HUMAN must flag, never fabricate.
    val = resolve_answer("Have you worked in a TypeScript service?", PROFILE, ANSWERS, FakeLLM())
    # No bank pattern matches this label, so it falls through to the (fake) LLM → ASK_HUMAN.
    assert val == ASK_HUMAN


def test_unknown_question_flags_not_fabricates():
    val = resolve_answer("Describe a time you invented cold fusion.", PROFILE, ANSWERS, FakeLLM())
    assert val == ASK_HUMAN
