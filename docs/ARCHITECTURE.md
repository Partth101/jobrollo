# Architecture

LocalApply is an **autonomous agent**, not a per-site script. One loop fills *any* application
form by perceiving its structure, reasoning about it with a local LLM, acting, and verifying —
then stopping for a human. The hard, brittle part of the domain (every ATS renders forms
differently) is handled by *generalization*, not by hardcoding one company at a time.

## The agent loop

```
                       ┌──────────────────────── Agent.run(page) ───────────────────────┐
                       │                                                                 │
  profile.json ──┐     │   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌────────────┐   │
  answers.json ──┼────►│   │ perceive │──►│  decide  │──►│  execute │──►│  verify /  │   │
  Ollama (LLM) ──┘     │   │ (eyes)   │   │ (brain)  │   │ (hands)  │   │ self-correct│  │
                       │   └──────────┘   └────┬─────┘   └──────────┘   └─────┬──────┘   │
                       │        ▲              │                              │          │
                       │        └──────────────┴──────── memory ◄────────────┘          │
                       │                                                                 │
                       │   halts on: submit/review step (human gate) · nothing left ·    │
                       │             no-progress stall · step budget                     │
                       └─────────────────────────────────────────────────────────────────┘
                                                   │
                                        [ STOP → human reviews + submits ]
```

### 1. Perception (`agent/perception.py`)
Serializes the live page into an `Observation`: a flat list of `Field`s
(`ref, kind, label, options, value, required`) derived from the DOM + accessibility tree, plus
a `at_submit_step` flag. This normalization is why one agent handles Greenhouse, Lever, Ashby,
Workday, or a form it has never seen — the policy reasons over *structure*, not brand.

### 2. Decision policy (`agent/policy.py`)
A **hybrid** decision core:
- an **LLM planner** proposes the next action as JSON over the whole observation;
- a **grounding guard** (deterministic) checks any proposed value against the candidate's real
  data (answer bank → profile → honesty-constrained LLM). If a value isn't grounded, the guard
  **overrides the action to `flag_for_human`.** Honesty is enforced in code, not by prompt alone;
- a **deterministic fallback** runs if the local model emits malformed JSON, so the agent never
  stalls.

### 3. Action space (`agent/actions.py`)
Six typed tools: `fill_text`, `select_option`, `click_choice`, `upload_resume`,
`flag_for_human`, `finish`. **There is no `submit` tool** — the agent structurally cannot
submit. `flag_for_human` is a first-class action: the honest way to "handle" a field.

### 4. Memory (`agent/memory.py`)
Working memory keeps per-run label→answer decisions (consistency + progress across
re-observation); site memory persists non-sensitive question→answer mappings per domain, so the
agent gets faster and steadier the more you use it on a given ATS.

### 5. The loop (`agent/core.py`)
Bounded `perceive → decide → execute → verify` with loop-avoidance (don't re-act a field),
a no-progress stall detector (self-correction), and hard halts on the submit/review step.

## Safety, by construction

| Guarantee | How it's enforced |
| --- | --- |
| Never submits | No submit action exists; loop halts at the submit/review step. |
| Never fabricates | Grounding guard overrides any ungrounded value to `flag_for_human`. |
| Never solves captchas / logs in | Not in the action space; perception treats them as human steps. |
| Local & private | Ollama by default; résumé/profile never leave the machine. |

## Module map

| Module | Responsibility |
| --- | --- |
| `agent/perception.py` | Page → `Observation` (normalized fields). |
| `agent/policy.py` | LLM planner + grounding guard + fallback → next `Action`. |
| `agent/actions.py` | Typed tools + executor. No submit tool. |
| `agent/memory.py` | Working + persisted site memory. |
| `agent/core.py` | The bounded, self-correcting agent loop. |
| `answers.py` | Grounded answer resolution (bank → profile → LLM → `ASK_HUMAN`). |
| `llm/ollama_client.py` | Local-first LLM + honesty system prompt. |
| `discovery/ats_search.py` | Public ATS-board APIs → candidate queue (OR titles, location filter). |
| `runner.py` | Drives the agent per job; reports; human gate. |
| `adapters/` | Optional deterministic fast-paths / reference implementations per ATS. |

## Adapters vs. the agent

The agent generalizes to any form and is the default engine. The `adapters/` (Greenhouse,
Lever, Ashby) remain as optional **fast-path recognizers** and as executable documentation of
each board's quirks. Roadmap: let the agent consult a matching adapter as a hint before falling
back to full LLM planning (fewer tokens on known boards, generality everywhere else).

## Roadmap

- [ ] Wire adapters as optional fast-path hints into the policy.
- [ ] Résumé tailoring + cover-letter generation (grounded, local).
- [ ] Workday / iCIMS perception coverage (multi-page, account-creation aware — human-finished).
- [ ] Local web UI to review the queue, the agent's plan, and flagged fields.
- [ ] Eval harness: a corpus of saved form snapshots to measure fill-accuracy + honesty regressions.
