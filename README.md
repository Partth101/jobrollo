# LocalApply

**The honest, local-first job-application copilot.** Runs entirely on your own machine
with [Ollama](https://ollama.com) — no API keys, no per-application fees, no data
leaving your laptop. Targets the **ATS boards other bots can't** (Greenhouse, Lever,
Ashby), **never auto-submits**, and **never lies on a form**.

> LocalApply is a *copilot*, not an autopilot. It finds matching roles, drafts tailored
> answers with a local LLM, fills the application, and **stops at the submit button** so
> **you** review and submit. That is a deliberate design choice — see [Why human-gated](#why-human-gated).

---

## Why this exists (and how it's different)

The popular auto-apply bots share three problems:

| Problem with most bots | LocalApply's stance |
| --- | --- |
| **LinkedIn Easy Apply only.** They can't follow a job that redirects to Greenhouse / Lever / Ashby / Workday — which is most of the real market. | **ATS-first.** First-class adapters for Greenhouse, Lever, and Ashby — the boards direct employers actually use. |
| **Fully hands-free auto-submit** → LinkedIn bot-detection trips, accounts get restricted, and low-quality spray applications hurt your reputation. | **Human-gated.** Fills to the final review page and stops. You review and click submit. No bans, no spray. |
| **They fabricate answers** to screening questions to get past required fields. | **Honesty-first.** If it can't answer truthfully from your profile (e.g. sponsorship, non-compete, a skill you don't have), it **flags the field for you** instead of making something up. |
| **Cloud LLM = API keys, cost, and your resume sent to a third party.** | **Local by default.** Ollama runs the model on your hardware. Your resume and answers never leave your machine. |
| **Some solve captchas** (hCaptcha/reCAPTCHA) to defeat anti-bot systems. | **Never.** Captchas and logins are yours to clear. We don't defeat anti-abuse systems. |

If you want a bot that blasts 500 applications overnight, this isn't it (and that bot will
get your LinkedIn banned). LocalApply is for people who want the *grunt work* automated —
finding roles, tailoring answers, filling forms — while keeping a human in the loop and
their accounts safe.

## It's an agent, not a script

Most job bots hardcode one company's form. LocalApply runs an **autonomous agent** that
**perceives** any application form, **decides** the next action with a local LLM, **acts**,
**verifies** the effect, and **self-corrects** — then stops for you. That's why it generalizes
across Greenhouse, Lever, Ashby, and forms it's never seen, instead of breaking on the next
redesign. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

```
perceive (page → normalized fields) → decide (LLM plan + grounding guard)
   → act (typed tools) → verify → … → STOP at submit  → you review + submit
```

## Features

- 🤖 **Autonomous form agent** — a bounded `perceive → decide → act → verify` loop that fills *any* ATS form by reasoning over its structure, not a per-site script.
- 🛡 **Grounding guard** — every value the agent proposes is checked against your real data; anything ungrounded is **flagged for you**, never fabricated. Honesty is enforced in code.
- 🚫 **No submit tool, by construction** — the agent structurally *cannot* submit or solve a captcha. It halts at the review step.
- 🔍 **Discovery** — searches public ATS-board APIs (no scraping) with OR-style titles + location filters, builds a reviewable queue.
- 🧠 **Local & private** — runs on Ollama; your résumé and profile never leave your machine. No API keys, no per-application cost.
- 🗂 **Memory** — remembers your answers within and across runs, so repeated fields are instant and consistent.
- 📊 **Tracker** — logs every application, agent steps, filled fields, and what was flagged.

## Quick start

```bash
# 1. Install Ollama and pull a model
#    https://ollama.com/download
ollama pull llama3.1:8b        # or qwen2.5, mistral, etc.

# 2. Install LocalApply
pip install -e .
playwright install chromium

# 3. Create your profile from the example
cp examples/profile.example.json profile.json
$EDITOR profile.json           # fill in your real details

# 4. Discover roles
localapply discover --keywords "AI Engineer,LLM Engineer,Healthcare AI" --location "United States"

# 5. Review the queue it built, then apply (fills to the submit page and STOPS)
localapply apply --queue queue.json
```

You review each filled application in the browser window and click **Submit** yourself.

## How it works

```
discover ─► queue.json ─► [ you cull the list ] ─► apply (per job):
     the agent loops:  perceive the form ─► decide next action (LLM plan + grounding guard)
                       ─► act (fill / select / click / upload) ─► verify ─► repeat
                       ─► STOP at the submit/review step  ─►  you review + submit
```

Everything the user touches is a **file, not code**: `config.yaml` (search titles as an
OR-list, locations, résumé path via `profile.json`), `profile.json` (personal details),
`answers.json` (canonical screening answers), `companies.txt` (which ATS boards to search).
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the agent design.

## Why human-gated?

Three reasons, in order of importance:

1. **It protects your accounts.** Automated submission at volume trips anti-bot systems (we've watched LinkedIn spawn reCAPTCHA + scraping-detection mid-apply). A restricted account during a job hunt is the worst possible outcome.
2. **It protects your reputation.** Recruiters increasingly filter AI-spray applications. Fifteen tailored, human-reviewed applications beat two hundred generic ones.
3. **It keeps you honest.** A required screening field you can't answer truthfully is a decision only you should make — not a model guessing "Yes."

## Ethics & Terms of Service

LocalApply does **not** scrape behind logins, defeat captchas, or auto-submit. It operates
public ATS application forms the way a fast human would, and always stops for human review.
Read [docs/ETHICS.md](docs/ETHICS.md) before using it. You are responsible for complying
with each site's Terms of Service and for the accuracy of everything you submit.

## Status

v0.1 — the autonomous agent (perception, LLM-planned policy, grounding guard, memory, bounded
self-correcting loop) and public-API discovery work end-to-end; the honesty guard is covered by
tests. Optional per-ATS fast-path adapters ship as reference implementations. Roadmap in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Contributions welcome — especially perception
coverage for new boards (Workday, iCIMS).

## License

MIT — see [LICENSE](LICENSE).
