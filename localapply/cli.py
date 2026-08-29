"""LocalApply CLI.

    localapply check                      # verify Ollama + config
    localapply discover --keywords ...    # build queue.json from public ATS boards
    localapply apply --queue queue.json   # fill each job, stop at submit (human-gated)
"""
from __future__ import annotations

import json
import os

import typer
from rich.console import Console
from rich.table import Table

from .answers import load_json
from .config import load_config
from .discovery import discover
from .llm import load_llm
from .runner import run

app = typer.Typer(add_completion=False, help="The honest, local-first job-application copilot.")
console = Console()


def _load_companies(path: str) -> list[tuple[str, str]]:
    """companies.txt: one 'ats slug' per line, e.g. 'greenhouse komodohealth'."""
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            ats, slug = line.split()
            out.append((ats, slug))
    return out


@app.command()
def check(config: str = "secret.yaml"):
    """Verify the local LLM is reachable and config loads."""
    cfg = load_config(config)
    llm = load_llm(cfg)
    console.print(f"LLM: [cyan]{llm.provider}[/] · model [cyan]{llm.model}[/] @ {llm.base_url}")
    try:
        out = llm.generate("Reply with the single word: ok", system="You are a health check.")
        console.print(f"[green]LLM reachable.[/] Response: {out[:40]}")
    except Exception as e:
        console.print(f"[red]LLM not reachable:[/] {e}\nIs `ollama serve` running and the model pulled?")


def _resolve_search(cfg: dict, keywords: str | None, location: str | None):
    """Everything is configurable. Precedence: CLI flag > config.search > profile.job_targets."""
    search = cfg.get("search", {})
    titles = keywords or search.get("titles")
    if not titles:  # fall back to the profile's job targets, if present
        jt = cfg.get("profile", {}).get("job_targets", {})
        titles = (jt.get("titles") or []) + (jt.get("keywords") or [])
    locations = location or search.get("locations")
    remote_ok = bool(search.get("remote_ok", True))
    companies = search.get("companies", "companies.txt")
    return titles, locations, remote_ok, companies


@app.command()
def discover_jobs(
    keywords: str = typer.Option(None, "--keywords",
                                 help="Titles as OR-list or 'A OR B'. Omit to use config/profile."),
    location: str = typer.Option(None, "--location", help="OR-list of locations. Omit to use config."),
    companies: str = typer.Option(None, help="File of 'ats slug' lines. Omit to use config."),
    out: str = typer.Option("queue.json", help="Where to write the queue"),
    config: str = "secret.yaml",
):
    """Search public ATS boards for matching roles and write a reviewable queue.

    With no flags at all, this reads titles/locations/companies entirely from your
    secret.yaml (the `search:` section). Flags are optional overrides.
    """
    cfg = load_config(config)
    titles, locations, remote_ok, comp_file = _resolve_search(cfg, keywords, location)
    companies = companies or comp_file
    if not titles:
        console.print("[red]No search titles found. Set search.titles in secret.yaml.")
        raise typer.Exit(1)
    comps = _load_companies(companies)
    jobs = discover(comps, titles, locations=locations, remote_ok=remote_ok,
                    max_per_source=cfg.get("discovery", {}).get("max_per_source", 50))
    json.dump([j.as_dict() for j in jobs], open(out, "w"), indent=2)

    table = Table(title=f"{len(jobs)} matching roles → {out}")
    for c in ("Company", "Title", "ATS", "Location"):
        table.add_column(c)
    for j in jobs:
        table.add_row(j.company, j.title, j.ats, j.location)
    console.print(table)
    console.print("[dim]Review/cull queue.json, then: localapply apply[/]")


# expose as `localapply discover`
app.command(name="discover")(discover_jobs)


@app.command()
def apply(
    queue: str = typer.Option("queue.json", help="Queue file from `discover`"),
    config: str = "secret.yaml",
):
    """Fill each job to the submit page and STOP for your review. Never submits."""
    cfg = load_config(config)
    profile = cfg.get("profile", {})
    answers = cfg.get("answers", {})

    resume = profile.get("resume_path", "")
    if not resume or not os.path.exists(resume):
        console.print(f"[red]Résumé not found at '{resume}'.[/] "
                      "Set profile.resume_path in secret.yaml to your résumé's location on disk.")
        raise typer.Exit(1)

    llm = load_llm(cfg)
    jobs = load_json(queue)
    console.print(
        "[bold]LocalApply is human-gated.[/] It will fill each form and stop at submit.\n"
        "You review and submit every application yourself.\n"
    )
    run(jobs, profile, answers, llm, cfg)


if __name__ == "__main__":
    app()
