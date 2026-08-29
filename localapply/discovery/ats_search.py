"""Discovery via the ATS boards' own PUBLIC APIs — no scraping, no login, no third party.

Greenhouse, Lever, and Ashby each publish a job board API per company:
  * Greenhouse: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true
  * Lever:      https://api.lever.co/v0/postings/{slug}?mode=json
  * Ashby:      https://api.ashbyhq.com/posting-api/job-board/{slug}

You give LocalApply a list of company slugs (companies.txt) and your keywords; it queries
each company's public board and returns roles whose title matches. This is deliberate: it
keeps discovery on documented public APIs instead of scraping aggregators, and it biases
toward *direct employers* rather than staffing-firm reposts.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict

import httpx


@dataclass
class Job:
    company: str
    title: str
    location: str
    ats: str
    url: str

    def as_dict(self) -> dict:
        return asdict(self)


def parse_terms(raw) -> list[str]:
    """Accept a list, or an OR-statement string like 'AI OR LLM OR Healthcare'.

    Both of these mean the same thing (match ANY term):
        ["AI Engineer", "LLM Engineer", "Healthcare AI"]
        "AI Engineer OR LLM Engineer OR Healthcare AI"
        "AI Engineer, LLM Engineer, Healthcare AI"
    """
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(t).strip() for t in raw if str(t).strip()]
    parts = re.split(r"\s+OR\s+|,", str(raw), flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]


def _match(title: str, keywords: list[str]) -> bool:
    """OR semantics: a title matches if it contains ANY of the terms."""
    t = title.lower()
    return any(re.search(re.escape(k.lower()), t) for k in keywords)


def _location_ok(location: str, wanted: list[str], remote_ok: bool) -> bool:
    """Empty `wanted` = accept anywhere. 'remote' in the posting always passes if remote_ok."""
    loc = (location or "").lower()
    if remote_ok and "remote" in loc:
        return True
    if not wanted:
        return True
    return any(w.lower() in loc for w in wanted)


def _greenhouse(slug: str, keywords: list[str]) -> list[Job]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    try:
        data = httpx.get(url, timeout=20).json()
    except Exception:
        return []
    jobs = []
    for j in data.get("jobs", []):
        if _match(j.get("title", ""), keywords):
            jobs.append(Job(slug.title(), j["title"], j.get("location", {}).get("name", ""),
                            "greenhouse", j["absolute_url"]))
    return jobs


def _lever(slug: str, keywords: list[str]) -> list[Job]:
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        data = httpx.get(url, timeout=20).json()
    except Exception:
        return []
    jobs = []
    for j in data:
        if _match(j.get("text", ""), keywords):
            jobs.append(Job(slug.title(), j["text"],
                            j.get("categories", {}).get("location", ""),
                            "lever", j["hostedUrl"]))
    return jobs


def _ashby(slug: str, keywords: list[str]) -> list[Job]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    try:
        data = httpx.get(url, timeout=20).json()
    except Exception:
        return []
    jobs = []
    for j in data.get("jobs", []):
        if _match(j.get("title", ""), keywords):
            jobs.append(Job(slug.title(), j["title"], j.get("location", ""),
                            "ashby", j.get("jobUrl") or j.get("applyUrl", "")))
    return jobs


FETCHERS = {"greenhouse": _greenhouse, "lever": _lever, "ashby": _ashby}


def discover(companies: list[tuple[str, str]], keywords, *,
             locations=None, remote_ok: bool = True, max_per_source: int = 50) -> list[Job]:
    """companies: list of (ats, slug). Returns matching Jobs, deduped by url.

    `keywords` and `locations` may be lists or OR-statement strings — both are parsed with
    OR semantics (match ANY). Empty locations = anywhere.
    """
    terms = parse_terms(keywords)
    wanted_locs = parse_terms(locations)
    seen: set[str] = set()
    out: list[Job] = []
    for ats, slug in companies:
        fetch = FETCHERS.get(ats)
        if not fetch:
            continue
        for job in fetch(slug, terms)[:max_per_source]:
            if job.url and job.url not in seen and _location_ok(job.location, wanted_locs, remote_ok):
                seen.add(job.url)
                out.append(job)
    return out
