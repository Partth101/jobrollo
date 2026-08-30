"""Tests for résumé text extraction (best-effort, never crashes)."""
import os
import tempfile

from jobrollo.resume import extract_resume_text


def test_missing_file_returns_empty():
    assert extract_resume_text("/no/such/file.pdf") == ""
    assert extract_resume_text("") == ""


def test_txt_extraction_and_whitespace_normalized():
    p = tempfile.mktemp(suffix=".txt")
    with open(p, "w") as f:
        f.write("Senior AI Engineer\n\n  Built   LLM   systems.\n")
    try:
        text = extract_resume_text(p)
        assert "Senior AI Engineer" in text
        assert "Built LLM systems." in text        # collapsed whitespace
    finally:
        os.remove(p)


def test_truncation_respects_max_chars():
    p = tempfile.mktemp(suffix=".md")
    with open(p, "w") as f:
        f.write("x " * 5000)
    try:
        assert len(extract_resume_text(p, max_chars=100)) == 100
    finally:
        os.remove(p)


def test_unknown_extension_returns_empty():
    p = tempfile.mktemp(suffix=".xyz")
    with open(p, "w") as f:
        f.write("data")
    try:
        assert extract_resume_text(p) == ""
    finally:
        os.remove(p)
