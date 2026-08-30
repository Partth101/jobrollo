# Contributing to JobRollo

Thanks for your interest! JobRollo uses the standard **fork → branch → pull request** model.
Nobody pushes directly to `main` — all changes land through a reviewed PR that passes CI.

## Workflow

1. **Fork** the repository to your own account.
2. **Clone** your fork and create a branch:
   ```bash
   git clone https://github.com/<you>/jobrollo.git
   cd jobrollo
   git checkout -b my-change
   ```
3. **Set up the dev environment and run the tests:**
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -e ".[dev]"
   pytest -q
   ```
4. **Make your change**, add tests, and keep the core guarantees intact:
   - **Never submit.** Do not add a submit/finish action.
   - **Never fabricate.** Unanswerable fields must be flagged, not guessed.
5. **Open a pull request** against `main`. CI must pass and a maintainer must approve before merge.

## Good first contributions

- **Perception coverage for a new ATS board** (e.g. Workday, iCIMS).
- Bug fixes with a regression test.
- Documentation improvements.

## Ground rules

- Keep PRs focused and small where possible.
- Do not commit personal data (`secret.yaml`, résumés, `queue.json`) — they are git-ignored.
- By contributing, you agree your contributions are licensed under the repository's LICENSE.
