"""Extract plain text from a résumé file so the LLM can ground open-ended answers in it.

Supports PDF (via ``pypdf``), DOCX (via ``python-docx``), and plain ``.txt`` / ``.md``.
Best-effort by design: if the file is missing or can't be parsed, it returns an empty
string and the agent falls back to the profile ``background`` — it never crashes a run.

Privacy note: with the default local (Ollama) model, this text is sent only to the model
running on your machine. If you opt into a cloud model, your résumé text goes to that
provider like any other prompt.
"""
from __future__ import annotations

import os


def extract_resume_text(path: str, max_chars: int = 6000) -> str:
    """Return the résumé's text (whitespace-normalized, truncated), or "" on any failure."""
    if not path or not os.path.exists(path):
        return ""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in {".txt", ".md"}:
            with open(path, encoding="utf-8", errors="ignore") as f:
                text = f.read()
        elif ext == ".pdf":
            text = _pdf_text(path)
        elif ext == ".docx":
            text = _docx_text(path)
        else:
            return ""
    except Exception:
        return ""
    text = " ".join(text.split())          # collapse whitespace/newlines
    return text[:max_chars]


def _pdf_text(path: str) -> str:
    from pypdf import PdfReader

    reader = PdfReader(path)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _docx_text(path: str) -> str:
    from docx import Document

    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)
