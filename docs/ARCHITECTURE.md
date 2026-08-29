# Architecture

LocalApply is a small pipeline with a clean seam at the ATS adapter, so the hard part
(board-specific form quirks) is isolated and extensible.

```
                 ┌─────────────┐
 keywords  ─────►│  discovery  │  public ATS APIs (Greenhouse/Lever/Ashby)
 companies ─────►│ ats_search  │───► queue.json  ──►  [ human culls the list ]
                 └─────────────┘
                                                          │
                                                          ▼
 profile.json ─┐                                   ┌────────────┐
 answers.json ─┼──────────────────────────────────►│   runner   │  (human-gated loop)
 Ollama (LLM) ─┘                                    └─────┬──────┘
                                                          │ per job
                                          ┌───────────────┼────────────────┐
                                          ▼               ▼                ▼
                                    get_adapter(url)  adapter.fill()   [ STOP → you submit ]
                                          │
                        ┌─────────────────┼──────────────────┐
                        ▼                 ▼                  ▼
                  GreenhouseAdapter   LeverAdapter      AshbyAdapter
                        └──────── ATSAdapter interface ────────┘
                                          │
                                   answers.resolve_answer()
                                   (bank → profile → local LLM → ASK_HUMAN)
```

## Components

| Module | Responsibility |
| --- | --- |
| `discovery/ats_search.py` | Query public ATS board APIs per company, filter by keywords, dedupe. |
| `answers.py` | Map a question label → truthful answer via bank, profile, then local LLM. Emits `ASK_HUMAN`. |
| `llm/ollama_client.py` | Local-first LLM with the honesty system prompt. Ollama default; cloud opt-in. |
| `adapters/base.py` | `ATSAdapter` interface + shared helpers (`_safe_fill`, `_upload_resume`). |
| `adapters/greenhouse.py` | Reference adapter. React-select handling, custom questions, EEO. |
| `adapters/lever.py` | Lever inputs, native-select EEO, cookie-banner + hidden-file-input handling. |
| `adapters/ashby.py` | Single name field, GUID questions, button-toggle Yes/No, listbox selects. |
| `runner.py` | Opens each job, calls the adapter, reports filled/flagged, waits for human. Never submits. |
| `tracker.py` | Appends one row per application to `tracker.json`. |

## The adapter contract

```python
class ATSAdapter:
    name: str
    @staticmethod
    def matches(url: str) -> bool: ...
    def fill(self, page, profile, answers, llm) -> FillResult: ...   # MUST NOT submit
```

`FillResult` carries `filled`, `flagged` (`FieldFlag(label, reason)`), and `resume_attached`.
The human-gate lives in the runner, and no adapter is allowed to click submit.

## Adding a new ATS (e.g. Workday, iCIMS)

1. Create `adapters/workday.py` with a `WorkdayAdapter(ATSAdapter)`.
2. Implement `matches()` (URL host) and `fill()` (map fields, upload resume, resolve answers).
3. Register it in `adapters/__init__.py`.
4. Never add a submit click. Flag anything you can't answer honestly.

Workday-class boards (account creation, multi-page, captchas) are the frontier — they're the
reason human-gating matters most. Contributions welcome.

## Roadmap

- [ ] Resume tailoring per role (bullet re-ranking) from the local model.
- [ ] Cover-letter generation grounded in the posting + profile.
- [ ] Workday / iCIMS adapters (partial, human-finished).
- [ ] A tiny local web UI for reviewing the queue and flags.
- [ ] Company-slug discovery helpers (seed lists by industry).
