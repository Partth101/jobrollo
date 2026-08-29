"""Local-first LLM client.

Default backend is Ollama (http://localhost:11434). Anything OpenAI-compatible works too,
but the whole point of JobRollo is that your resume never has to leave your machine — so
Ollama is the default and cloud is opt-in.

The system prompt here is the honesty guardrail: the model is told, in no uncertain terms,
to ground every answer in the candidate's profile and to emit the sentinel ``ASK_HUMAN``
whenever it cannot answer truthfully. The runner treats that sentinel as a hard stop.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

ASK_HUMAN = "ASK_HUMAN"

HONESTY_SYSTEM_PROMPT = f"""You help a job seeker fill out application forms. You are given
their verified profile and a form question. Rules you must never break:

1. Ground every answer ONLY in the provided profile. Never invent experience, skills,
   employers, dates, numbers, or credentials the profile does not support.
2. If the question asks about something the profile does not clearly support — a skill they
   may not have, a legal/eligibility fact, a personal preference, anything requiring their
   judgment — respond with exactly this token and nothing else: {ASK_HUMAN}
3. Prefer concise, specific, professional answers. Match the requested length.
4. Never exaggerate. A modest true answer beats an impressive false one.
Return only the answer text (or {ASK_HUMAN}). No preamble, no quotes."""


@dataclass
class LLMClient:
    base_url: str
    model: str
    provider: str = "ollama"
    temperature: float = 0.2
    api_key_env: str | None = None
    timeout: float = 120.0

    def generate(self, prompt: str, system: str = HONESTY_SYSTEM_PROMPT) -> str:
        if self.provider == "ollama":
            return self._ollama(prompt, system)
        return self._openai_compatible(prompt, system)

    def _ollama(self, prompt: str, system: str) -> str:
        r = httpx.post(
            f"{self.base_url.rstrip('/')}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "options": {"temperature": self.temperature},
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()["message"]["content"].strip()

    def _openai_compatible(self, prompt: str, system: str) -> str:
        headers = {}
        if self.api_key_env:
            key = os.environ.get(self.api_key_env)
            if not key:
                raise RuntimeError(f"Env var {self.api_key_env} is not set")
            headers["Authorization"] = f"Bearer {key}"
        r = httpx.post(
            f"{self.base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": self.temperature,
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


def load_llm(cfg: dict) -> LLMClient:
    llm = cfg.get("llm", {})
    return LLMClient(
        base_url=llm.get("base_url", "http://localhost:11434"),
        model=llm.get("model", "llama3.1:8b"),
        provider=llm.get("provider", "ollama"),
        temperature=float(llm.get("temperature", 0.2)),
        api_key_env=llm.get("api_key_env"),
    )
