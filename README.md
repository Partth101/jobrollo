<div align="center">

# 🦉 JobRollo

### The agentic, local-first job-application agent

**Finds matching roles, fills the application on any ATS, and stops at the submit button so you review and send it.**
Runs entirely on your machine with [Ollama](https://ollama.com) — no API keys, no per-application fees, no data leaving your laptop. It **never auto-submits**, **never fabricates an answer**, and **never solves a captcha**.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Runs on Ollama](https://img.shields.io/badge/LLM-local%20via%20Ollama-000000.svg)](https://ollama.com)
[![Playwright](https://img.shields.io/badge/browser-Playwright-2EAD33.svg)](https://playwright.dev)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#contributing)

**Supported application platforms**

[![Greenhouse](https://img.shields.io/badge/Greenhouse-supported-24A47C.svg)](#supported-ats-platforms)
[![Lever](https://img.shields.io/badge/Lever-supported-5555FF.svg)](#supported-ats-platforms)
[![Ashby](https://img.shields.io/badge/Ashby-partial-8A63D2.svg)](#supported-ats-platforms)
[![Workday](https://img.shields.io/badge/Workday-roadmap-lightgrey.svg)](#supported-ats-platforms)
[![iCIMS](https://img.shields.io/badge/iCIMS-roadmap-lightgrey.svg)](#supported-ats-platforms)

*JobRollo works the **ATS boards** where applications actually live — **Greenhouse, Lever, Ashby** today,
with **Workday & iCIMS** on the roadmap. It deliberately does **not** automate **LinkedIn, Indeed, or
Glassdoor**: those sites ban automated accounts, so JobRollo instead applies through the ATS the posting
redirects to — keeping your accounts safe.*

</div>

---

## Table of contents

- [What is JobRollo?](#what-is-jobrollo)
- [Why it's different](#why-its-different)
- [How it works](#how-it-works)
- [Requirements](#requirements)
- [Installation](#installation)
  - [1. Install Ollama](#1-install-ollama)
  - [2. Pull a model](#2-pull-a-model)
  - [3. Install JobRollo](#3-install-jobrollo)
  - [4. Verify the install](#4-verify-the-install)
- [Choosing a model](#choosing-a-model)
- [Configuration (`secret.yaml`)](#configuration-secretyaml)
  - [`companies.txt`](#companiestxt)
- [Usage](#usage)
  - [Step 1 — Discover roles](#step-1--discover-roles)
  - [Step 2 — Review the queue](#step-2--review-the-queue)
  - [Step 3 — Apply (human-gated)](#step-3--apply-human-gated)
- [CLI reference](#cli-reference)
- [Supported ATS platforms](#supported-ats-platforms)
- [Architecture](#architecture)
- [Safety & ethics](#safety--ethics)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## What is JobRollo?

JobRollo automates the **grunt work** of job hunting — finding relevant openings, tailoring answers, and filling out application forms — while keeping **you** in control of every submission.

It is a genuine **autonomous agent**, not a hardcoded script. For each application it runs a
`perceive → decide → act → verify` loop: it reads the form's structure, decides what to enter
using a local LLM (grounded strictly in *your* data), acts, checks its work, and self-corrects —
then **stops at the review step** for you to submit.

```
  discover  ──►  queue.json  ──►  [ you cull ]  ──►  apply  ──►  [ you review + submit ]
   (public ATS APIs)                                 (fills every field, stops at submit)
```

## Why it's different

Most auto-apply bots share three problems. JobRollo is built to be the opposite:

| Most job bots | JobRollo |
| --- | --- |
| **LinkedIn Easy Apply only** — can't follow a job that redirects to Greenhouse / Lever / Ashby / Workday, which is most of the real market. | **ATS-first.** First-class support for the boards direct employers actually use. |
| **Fully hands-free auto-submit** → trips anti-bot detection, gets accounts restricted, floods recruiters with spray. | **Human-gated by construction.** No code path clicks submit. You review and send every application. |
| **Fabricate answers** to get past required screening fields. | **Honesty enforced in code.** If it can't answer truthfully from your profile, it **flags the field for you** instead of inventing an answer. |
| **Cloud LLM** → API keys, cost, and your résumé sent to a third party. | **Local by default.** Ollama runs the model on your hardware. Your résumé and answers never leave your machine. |
| **Some solve captchas** to defeat anti-abuse systems. | **Never.** Captchas and logins are yours to clear. |

> **JobRollo is not a mass-apply cannon.** If you want to blast 500 applications overnight, this
> is the wrong tool (and that approach gets your accounts banned). JobRollo is for people who want
> the tedious 90% automated while a human stays accountable for what actually gets submitted.

## How it works

```
                     ┌──────────────────────── Agent.run(page) ───────────────────────┐
                     │                                                                 │
 secret.yaml  ──┐    │   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌────────────┐   │
  (profile,     ├───►│   │ perceive │──►│  decide  │──►│  execute │──►│  verify /  │   │
   answers,     │    │   │ (eyes)   │   │ (brain)  │   │ (hands)  │   │self-correct│   │
   background)  │    │   └──────────┘   └────┬─────┘   └──────────┘   └─────┬──────┘   │
 Ollama (LLM) ──┘    │        ▲              │                              │          │
                     │        └──────────── memory ◄─────────────────────────┘         │
                     │   halts on: submit/review step · nothing left · stall · budget  │
                     └─────────────────────────────────────────────────────────────────┘
                                                 │
                                     [ STOP → you review + submit ]
```

- **Perceive** — normalizes any application page into a flat list of fields (`label, kind, options, required`).
- **Decide** — resolves each field's value from your answer bank → profile facts → the local LLM, under a **grounding guard** that flags anything it can't answer truthfully.
- **Act** — a typed action space of six tools. **There is no `submit` tool** — the agent structurally cannot submit.
- **Verify + remember** — re-reads the form, avoids re-acting a field, and remembers answers within and across runs.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design.

---

## Requirements

| | Minimum | Recommended |
| --- | --- | --- |
| **OS** | macOS, Linux, or Windows (WSL2 recommended on Windows) | macOS / Linux |
| **Python** | 3.10+ | 3.11+ |
| **RAM** | 8 GB (for a 7B model) | 16 GB+ |
| **Disk** | ~6 GB (model + browser) | — |
| **Tools** | [Ollama](https://ollama.com), Git | — |

## Installation

### 1. Install Ollama

Ollama runs the language model locally. Install it for your OS:

**macOS**
```bash
brew install ollama          # or download the app from https://ollama.com/download
```

**Linux**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows** — download the installer from [ollama.com/download](https://ollama.com/download) (WSL2 also works).

Then start the Ollama server (it runs in the background and serves on `http://localhost:11434`):
```bash
ollama serve
```
> On macOS/Windows the desktop app starts the server automatically. On Linux with systemd it runs as a service; otherwise run `ollama serve` in a terminal.

### 2. Pull a model

Pull one model to start. `qwen2.5:7b` is a great default — fast, and strong at following instructions and producing JSON:

```bash
ollama pull qwen2.5:7b
```

See [Choosing a model](#choosing-a-model) for alternatives and hardware guidance.

### 3. Install JobRollo

```bash
git clone https://github.com/Partth101/jobrollo.git
cd jobrollo

# (recommended) create a virtual environment
python3 -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate

# install JobRollo and the browser it drives
pip install -e .
playwright install chromium
```

### 4. Verify the install

```bash
# copy the config template and the example company list
cp secret.example.yaml secret.yaml
cp examples/companies.example.txt companies.txt

# check the local model is reachable
jobrollo check
```

Expected output:
```
LLM: ollama · model qwen2.5:7b @ http://localhost:11434
LLM reachable. Response: ok
```

If you see an error, jump to [Troubleshooting](#troubleshooting).

---

## Choosing a model

JobRollo resolves most fields **deterministically** (from your answer bank and profile facts), so
the LLM is mainly used for open-ended questions ("Tell us about a project…"). This means even a
small 7B model works well. Pick based on your hardware:

| Model | Download | Min RAM | Speed | Quality | Notes |
| --- | --- | --- | --- | --- | --- |
| **`qwen2.5:7b`** ⭐ | ~4.7 GB | 8 GB | Fast | Good | **Recommended default.** Excellent at instructions + JSON. |
| `llama3.1:8b` | ~4.9 GB | 8 GB | Fast | Good | Solid all-rounder. |
| `mistral:7b` | ~4.1 GB | 8 GB | Fastest | OK | Lightest option. |
| `qwen2.5:14b` | ~9 GB | 16 GB | Medium | Better | Nicer free-text answers. |
| `qwen2.5:32b` / `llama3.1:70b` | 20 GB+ | 32–48 GB+ | Slow | Best | Only if you have the hardware. |

Set your choice in `secret.yaml` under `llm.model`. To try another model, just `ollama pull <model>`
and update that one line.

**Prefer a cloud model?** (opt-in, not the default — your data leaves your machine):
```yaml
llm:
  provider: openai_compatible
  base_url: https://api.openai.com/v1
  model: gpt-4o-mini
  api_key_env: OPENAI_API_KEY   # JobRollo reads the key from this env var
```

---

## Configuration (`secret.yaml`)

Everything you configure lives in **one private, git-ignored file**: `secret.yaml`. Copy it from
`secret.example.yaml` and fill it in. It has five sections:

```yaml
# 1) MODEL — which brain runs the agent
llm:
  provider: ollama
  base_url: http://localhost:11434
  model: qwen2.5:7b
  temperature: 0.1

# 2) YOU — details used to fill forms
profile:
  identity: { legal_first_name: "Jane", legal_last_name: "Doe", email: "jane@example.com", phone: "5551234567" }
  location: { city: "New York", state: "NY", country: "United States", zip: "10001", willing_to_relocate: true }
  work_authorization: { authorized_us_any_employer: true, visa_status: "F-1 OPT", require_sponsorship_future: true }
  links: { linkedin: "https://linkedin.com/in/janedoe", github: "https://github.com/janedoe" }
  resume_path: "/absolute/path/to/resume.pdf"
  background: |
    Free-text the AI may draw on for open-ended questions. Write it truthfully and
    specifically — the model is told to ground every answer ONLY in this text and to
    FLAG (never invent) anything it doesn't support.

# 3) ANSWERS — canonical responses to recurring questions.
#    Set any value to ASK_HUMAN to force the agent to leave it for you.
answers:
  authorized_to_work_us: "Yes"
  require_sponsorship_now_or_future: "Yes"
  salary_expectation: "135000-160000"
  veteran_status: "I am not a protected veteran"
  # ...

# 4) SEARCH — what to look for. Titles use OR semantics (match ANY).
search:
  titles: "AI Engineer OR LLM Engineer OR Machine Learning Engineer"
  locations: ["United States", "Remote"]   # empty = anywhere
  remote_ok: true
  companies: companies.txt

# 5) BEHAVIOR
browser: { headless: false, slow_mo_ms: 200, throttle_between_jobs_s: 30 }
runner:  { step_budget: 60 }
```

> ⚠️ **Quote your Yes/No values.** In YAML, an unquoted `Yes`/`No`/`on`/`off` is parsed as a boolean.
> Always write `"Yes"` / `"No"` (with quotes) in the `answers` section.

`secret.yaml`, `companies.txt`, `queue.json`, `tracker.json`, and your résumé are all **git-ignored** —
they never get committed.

### `companies.txt`

Discovery searches the **public job-board API** of each company you list. Format is one
`<ats> <slug>` per line — find the slug in a company's careers URL:

```txt
# careers URL                          → line   (slugs below are placeholders)
# job-boards.greenhouse.io/acme-corp   → greenhouse acme-corp
# jobs.lever.co/globex                 → lever globex
# jobs.ashbyhq.com/initech             → ashby initech

greenhouse acme-corp
lever globex
ashby initech
```

---

## Usage

The workflow is three steps: **discover → review → apply**.

### Step 1 — Discover roles

```bash
jobrollo discover
```

Reads your `search.titles` / `locations` / `companies` from `secret.yaml`, queries each company's
public ATS API, filters by your titles (OR semantics) and location, and writes a reviewable
`queue.json`. Example output:

```
        7 matching roles → queue.json
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Company    ┃ Title                   ┃ ATS        ┃ Location       ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ Acme Corp  │ Senior AI Engineer      │ greenhouse │ United States  │
│ Globex     │ Staff AI Engineer       │ ashby      │ Remote - US    │
│ Initech    │ LLM Engineer            │ lever      │ Remote         │
└────────────┴─────────────────────────┴────────────┴────────────────┘
```

Override any setting with flags:
```bash
jobrollo discover --keywords "LLM Engineer OR Forward Deployed Engineer" --location "Remote"
```

### Step 2 — Review the queue

Open `queue.json` and **delete anything you don't want to apply to**. This is your first gate.

### Step 3 — Apply (human-gated)

```bash
jobrollo apply --queue queue.json
```

For each job, a browser opens; the agent fills the form to the submit page, prints exactly what it
filled and what it flagged, then **waits for you**:

```
──────────────── 1/7  Acme Corp — Senior AI Engineer ────────────────
╭──────────────────────────── agent result ────────────────────────────╮
│ Résumé attached: True                                                 │
│ Filled (17): First Name, Last Name, Email, Phone, LinkedIn, Are you   │
│   legally authorized to work…, Do you require sponsorship…, Gender,    │
│   Veteran Status, Disability Status, …                                 │
│ Left for you (couldn't answer honestly):                              │
│   • Why do you want to work here? — open-ended, your voice            │
│ Stopped: no actionable fields left                                    │
╰───────────────────────────────────────────────────────────────────────╯

Review the form in the browser, then submit it yourself.
Press Enter when done (or 's' to skip)…
```

You review the filled form in the browser, handle any flagged fields, click **Submit** yourself,
then press Enter to move to the next role. Every application is logged to `tracker.json`.

---

## CLI reference

| Command | Description |
| --- | --- |
| `jobrollo check` | Verify the local model is reachable and config loads. |
| `jobrollo discover` | Search public ATS boards → write `queue.json`. |
| `jobrollo apply` | Fill each job to the submit page and stop for review. |

**Common flags**

```
jobrollo discover [--keywords "A OR B"] [--location "X, Y"] [--companies companies.txt]
                  [--out queue.json] [--config secret.yaml]

jobrollo apply    [--queue queue.json] [--config secret.yaml]
```

All settings default to your `secret.yaml`; flags are optional overrides.

---

## Supported ATS platforms

| ATS | Discovery (public API) | Auto-fill | Notes |
| --- | :---: | :---: | --- |
| **Greenhouse** | ✅ | ✅ Solid | React-select dropdowns, EEO, custom questions. |
| **Lever** | ✅ | ✅ Solid | Radio-card questions, native-select EEO, cookie-banner handling; hCaptcha at submit is yours to solve. |
| **Ashby** | ✅ | 🟡 Partial | Contact + résumé + basic questions; button-toggles/checkboxes are being hardened. |
| **Workday / iCIMS** | — | 🗺️ Roadmap | Multi-page + account creation; will be human-finished. |

The agent generalizes by reasoning over form *structure*, so it often makes progress on boards not
listed here — and anything it can't fill confidently is flagged for you rather than guessed.

## Architecture

A quick tour (full detail in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)):

| Module | Responsibility |
| --- | --- |
| `jobrollo/agent/perception.py` | Page → normalized `Observation` (the agent's eyes). |
| `jobrollo/agent/policy.py` | Resolve each field's value + grounding guard (the brain). |
| `jobrollo/agent/actions.py` | Six typed tools; **no submit tool** (the hands). |
| `jobrollo/agent/core.py` | The bounded, self-correcting `perceive→decide→act→verify` loop. |
| `jobrollo/agent/memory.py` | Per-run + persisted answer memory. |
| `jobrollo/answers.py` | Grounded answer resolution (bank → profile → LLM → `ASK_HUMAN`). |
| `jobrollo/discovery/ats_search.py` | Public ATS-board API search. |
| `jobrollo/runner.py` | Drives the agent per job; the human gate. |

## Safety & ethics

JobRollo is built on one principle: **automate the grunt work, keep a human accountable.**

- **No auto-submit** — there is no code path that clicks submit. It's absent by construction.
- **No fabrication** — the grounding guard overrides any ungrounded value to *flag for human*.
- **No captcha solving, no login scraping** — not in the action space.
- **Local & private** — Ollama by default; your résumé and answers stay on your machine.

You are responsible for the accuracy of everything you submit and for complying with each site's
Terms of Service. Read [`docs/ETHICS.md`](docs/ETHICS.md) before using it.

---

## Troubleshooting

<details>
<summary><b>`jobrollo check` says the LLM is not reachable</b></summary>

- Make sure the Ollama server is running: `ollama serve` (or open the desktop app).
- Confirm the model is pulled: `ollama list` — if missing, `ollama pull qwen2.5:7b`.
- Confirm the URL/model in `secret.yaml` matches (`base_url: http://localhost:11434`, `model: qwen2.5:7b`).
- Test Ollama directly: `curl http://localhost:11434/api/tags` should return JSON.
</details>

<details>
<summary><b>It's very slow (many seconds per field)</b></summary>

- Use a smaller/faster model (`qwen2.5:7b`, `llama3.1:8b`, or `mistral:7b`).
- First run of a model is slower (it loads into RAM/VRAM); later runs are faster.
- Close other memory-heavy apps; a 7B model needs ~5–6 GB free.
- Most fields are resolved without the LLM — the slow part is open-ended questions, which are usually few.
</details>

<details>
<summary><b>`playwright` / browser errors, or no window opens</b></summary>

- Install the browser once: `playwright install chromium`.
- On Linux you may need system libs: `playwright install-deps` (or `sudo apt-get install` the listed packages).
- To watch it work, keep `browser.headless: false` in `secret.yaml`.
</details>

<details>
<summary><b>The agent filled 0 fields / stopped immediately</b></summary>

- Some ATS forms render client-side; JobRollo waits for the form, but very slow pages may need more time — re-run, or open the URL manually to confirm the form loads.
- Confirm the job URL points to the **application** page (Ashby/Lever apply URLs end in `/application` or `/apply`).
- The posting may be **closed** (returns "not found") — refresh your queue with `jobrollo discover`.
</details>

<details>
<summary><b>A field I expected filled was flagged "couldn't answer honestly"</b></summary>

This is intentional — the agent won't guess. Fix it by giving it the answer:
- Add the fact to your `answers:` section in `secret.yaml`, **or**
- Add detail to `profile.background` so the model can ground an answer, **or**
- Just fill that one field yourself during review (that's what flagging is for).
</details>

<details>
<summary><b>The résumé didn't attach</b></summary>

- Check `profile.resume_path` is an **absolute path** to an existing PDF/DOC/DOCX.
- **macOS:** if your résumé lives in `~/Desktop` or `~/Documents`, macOS privacy (TCC) may block Python from reading it. Move the résumé to the project folder, or grant your terminal **Full Disk Access** in System Settings → Privacy & Security.
</details>

<details>
<summary><b>My "Yes/No" answers behave oddly</b></summary>

YAML parses unquoted `Yes`/`No` as booleans. **Quote them:** `authorized_to_work_us: "Yes"`.
</details>

<details>
<summary><b>Lever shows an hCaptcha; the agent stopped</b></summary>

That's by design — the captcha only appears at **submit**, which the agent never reaches. Solve it
yourself when you submit.
</details>

<details>
<summary><b>Is my LinkedIn/account at risk?</b></summary>

JobRollo doesn't touch LinkedIn or any logged-in site — discovery uses public board APIs, and it
never auto-submits or solves captchas. Keep `throttle_between_jobs_s` at a sane value (default 30s)
to stay a good citizen.
</details>

## FAQ

**Does it submit applications for me?** No. It fills to the submit page and stops. You review and submit.

**Does my data leave my machine?** No, when using the default Ollama backend. Cloud models are opt-in.

**Will it lie to get past a required field?** No. It flags anything it can't answer truthfully from your data.

**Do I need a GPU?** No. A 7B model runs on CPU; a GPU just makes it faster.

**Which boards work best?** Greenhouse and Lever are solid today; Ashby is partial; more are on the roadmap.

## Roadmap

- [ ] Harden Ashby to Greenhouse/Lever quality
- [ ] Workday / iCIMS support (multi-page, human-finished)
- [ ] Résumé tailoring + grounded cover-letter generation (local)
- [ ] Local web UI to review the queue, the agent's plan, and flagged fields
- [ ] Eval harness: saved form snapshots to measure fill-accuracy + honesty regressions

## Contributing

Contributions are very welcome — especially **perception coverage for new ATS boards**.

```bash
git clone https://github.com/Partth101/jobrollo.git && cd jobrollo
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q            # run the tests (the honesty guard is covered here)
```

To add a board, extend the perception/policy layers so its fields are recognized, and add a test.
Please keep the core guarantees intact: **never submit, never fabricate.**

## License

[MIT](LICENSE) © Parth Ghayal
