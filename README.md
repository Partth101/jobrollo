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

## Features

- 🔍 **Discovery** — searches public ATS boards for roles matching your keywords, dedupes, and builds a reviewable queue.
- 🧠 **Local answer generation** — tailors resume bullets, cover letters, and screening answers with an Ollama model, grounded strictly in your `profile.json` (no invented experience).
- 🧩 **ATS adapters** — Greenhouse, Lever, Ashby (incl. iframe-embedded forms). A clean `ATSAdapter` interface makes new boards easy to add.
- ✋ **Human-gated submit** — fills every field it can, stops at the review page, and prints exactly what it left for you (and why).
- 🗂 **Answer bank** — reuses your canonical answers (work auth, salary, EEO, common screening Qs) across applications so each one gets faster.
- 📊 **Tracker** — logs every application, its status, and per-field notes.

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
discover ──► queue.json ──► [ you cull the list ] ──► apply (per job):
                                                        1. open in browser
                                                        2. detect ATS (Greenhouse/Lever/Ashby)
                                                        3. fill contact + upload resume
                                                        4. generate honest answers via Ollama
                                                        5. flag anything it can't answer truthfully
                                                        6. STOP at submit  ──► you review + submit
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design and how to add an ATS adapter.

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

v0.1 — Greenhouse adapter is the reference implementation; Lever and Ashby adapters are
functional; discovery and the human-gated runner work end-to-end. Roadmap in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Contributions welcome — especially new ATS
adapters.

## License

MIT — see [LICENSE](LICENSE).
