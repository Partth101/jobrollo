"""The ATS adapter interface.

Every supported board (Greenhouse, Lever, Ashby, ...) implements this. The runner is
board-agnostic: it detects the ATS from the URL, hands the page to the right adapter, and
the adapter does the board-specific field mapping. Adding a new board = one new subclass.

The contract every adapter must honor:
  * fill() maps profile + answers onto the form and UPLOADS the resume.
  * fill() must NEVER click a submit/finish button. Human-gated is enforced here, not by policy.
  * When a required field can't be answered truthfully, append a FieldFlag instead of guessing.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from playwright.sync_api import Page


@dataclass
class FieldFlag:
    """A field the runner deliberately left for the human, with the reason."""
    label: str
    reason: str


@dataclass
class FillResult:
    company: str
    role: str
    ats: str
    url: str
    filled: list[str] = field(default_factory=list)
    flagged: list[FieldFlag] = field(default_factory=list)
    resume_attached: bool = False
    ok: bool = True
    error: str | None = None


class ATSAdapter:
    name: str = "base"

    @staticmethod
    def matches(url: str) -> bool:
        """Return True if this adapter handles the given application URL."""
        raise NotImplementedError

    def fill(self, page: Page, profile: dict, answers: dict, llm) -> FillResult:
        """Fill the application to the final review step. MUST NOT submit."""
        raise NotImplementedError

    # ---- shared helpers usable by all adapters -------------------------------

    @staticmethod
    def _safe_fill(page: Page, selector: str, value: str) -> bool:
        try:
            el = page.query_selector(selector)
            if el and value:
                el.fill(value)
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def _upload_resume(page: Page, resume_path: str) -> bool:
        """Attach the resume via the first file input, made visible if needed.

        Learned the hard way: some boards (Lever) hide the file input and gate the
        native chooser behind a cookie banner, so we set the input files directly.
        """
        try:
            file_input = page.query_selector('input[type=file]')
            if not file_input:
                return False
            file_input.set_input_files(resume_path)
            return True
        except Exception:
            return False
