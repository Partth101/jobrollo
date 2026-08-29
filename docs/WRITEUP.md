# Building an honest, local-first job-application copilot

*A technical writeup of LocalApply — why the popular auto-apply bots fail, and the design
choices behind a tool that runs entirely on your machine, targets the boards that matter,
and never lies on a form.*

> This is a draft article intended for publication (personal blog / Dev.to / Medium) as the
> companion writeup to the open-source project. Edit the voice to your own before publishing.

## The problem with "auto-apply"

Job-application automation is a crowded space. The most popular open-source tool has 30,000+
GitHub stars. Yet almost every tool in the category shares the same three flaws:

1. **They only handle LinkedIn Easy Apply.** The moment a posting redirects to an applicant
   tracking system (ATS) — Greenhouse, Lever, Ashby, Workday — most bots can't follow. That
   eliminates the majority of roles at real, direct employers.
2. **They auto-submit at volume.** This trips anti-bot defenses (I watched LinkedIn spawn a
   reCAPTCHA challenge and a scraping-detection endpoint *mid-application*), and it floods
   recruiters with low-quality spray applications that hurt the candidate's reputation.
3. **They fabricate answers.** To get past required screening fields, they let a language
   model guess "Yes" to questions like *"Do you require visa sponsorship?"* or *"Have you
   shipped a production LLM system?"* — answers the candidate then has to defend, or can't.

I wanted the opposite tool: one that automates the *grunt work* (finding roles, tailoring
answers, filling forms) while keeping a human accountable and their accounts safe.

## Four design decisions

### 1. ATS-first, not LinkedIn-first

Instead of fighting LinkedIn's adversarial anti-bot stack, LocalApply targets the ATS boards
direct employers actually use — and which expose **public APIs** for both discovery and
application. Discovery hits documented endpoints like
`boards-api.greenhouse.io/v1/boards/{company}/jobs`, so there's no scraping. Application uses
a per-board **adapter** that understands that board's form.

This also solved a subtler problem: LinkedIn "AI Engineer" Easy-Apply results are dominated
by staffing firms. Querying direct-employer ATS boards biases toward the roles a candidate
actually wants.

### 2. Human-gated by construction

The runner fills every field it can and then **stops at the submit button**. This isn't a
configurable flag — there is no code path that clicks submit. The human reviews the filled
form in a real browser window and submits it themselves.

Three reasons, in priority order: it protects the candidate's accounts from anti-bot bans;
it protects their reputation from spray; and it keeps a human accountable for what gets sent.

### 3. Honesty as a first-class constraint

The LLM runs under a system prompt that forbids invention and requires it to emit a sentinel
token — `ASK_HUMAN` — whenever it cannot answer a question truthfully from the candidate's
profile. Answer resolution is layered: a human-authored answer bank first, then direct
profile facts, then the local model. Any layer can flag a field. The runner then fills
everything else on the page and hands the flagged fields to the human with the reason.

In practice this surfaces exactly the questions that *should* be a human's call: sponsorship
status, non-compete agreements, a specific skill the résumé doesn't clearly support.

### 4. Local by default

The whole pipeline runs on [Ollama](https://ollama.com). The candidate's résumé, answers,
and profile never leave their machine, and there's no per-application API cost. Cloud models
are opt-in via an OpenAI-compatible endpoint, but they're not the default — privacy and cost
are the point.

## Engineering notes: three ATS platforms, three form idioms

Each board renders forms differently, and the adapters encode hard-won specifics:

- **Greenhouse** uses React-select dropdowns — not native `<select>`. You click the control
  to open a listbox, then click the option; setting a value programmatically doesn't register
  with the component's state. EEO and screening questions are all this shape.
- **Lever** hides the résumé file input and can gate the native file chooser behind a cookie
  banner. The adapter dismisses the banner and sets files on the input directly. Lever also
  shows an hCaptcha at submit — which the human-gated design never reaches.
- **Ashby** uses a single `_systemfield_name` field (not split first/last), GUID-keyed custom
  questions, and button-toggle Yes/No controls. Some Ashby forms are embedded cross-origin;
  the automation layer has to see through the iframe to reach them.

The adapter interface (`matches(url)` + `fill(page, profile, answers, llm)`) keeps this
board-specific mess isolated. Adding Workday or iCIMS is one new subclass.

## What I'd tell someone building in this space

Automation is not the hard part; *restraint* is. The valuable, defensible tool isn't the one
that submits the most applications — it's the one that does the tedious 90% correctly, stops
before the irreversible 10%, and never puts words in the candidate's mouth. That constraint
is also what keeps the tool on the right side of platform Terms of Service.

## Try it

LocalApply is open source (MIT). Code, adapters, and setup:
`https://github.com/<your-username>/localapply`.

---

*Author: Parth Ghayal. Contributions — especially new ATS adapters — are welcome.*
