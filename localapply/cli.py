"""LocalApply CLI.

    localapply check                      # verify Ollama + config
    localapply discover --keywords ...    # build queue.json from public ATS boards
    localapply apply --queue queue.json   # fill each job, stop at submit (human-gated)
"""
from __future__ import annotations

import json

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
def check(config: str = "config.yaml"):
    """Verify the local LLM is reachable and config loads."""
    cfg = load_config(config)
    llm = load_llm(cfg)
    console.print(f"LLM: [cyan]{llm.provider}[/] · model [cyan]{llm.model}[/] @ {llm.base_url}")
    try:
        out = llm.generate("Reply with the single word: ok", system="You are a health check.")
        console.print(f"[green]LLM reachable.[/] Response: {out[:40]}")
    except Exception as e:
        console.print(f"[red]LLM not reachable:[/] {e}\nIs `ollama serve` running and the model pulled?")


@app.command()
def discover_jobs(
    keywords: str = typer.Option(..., "--keywords", help="Comma-separated title keywords"),
    companies: str = typer.Option("companies.txt", help="File of 'ats slug' lines"),
    out: str = typer.Option("queue.json", help="Where to write the queue"),
    config: str = "config.yaml",
):
    """Search public ATS boards for matching roles and write a reviewable queue."""
    cfg = load_config(config)
    kw = [k.strip() for k in keywords.split(",") if k.strip()]
    comps = _load_companies(companies)
    jobs = discover(comps, kw, cfg.get("discovery", {}).get("max_per_source", 50))
    json.dump([j.as_dict() for j in jobs], open(out, "w"), indent=2)

    table = Table(title=f"{len(jobs)} matching roles → {out}")
    for c in ("Company", "Title", "ATS", "Location"):
        table.add_column(c)
    for j in jobs:
        table.add_row(j.company, j.title, j.ats, j.location)
    console.print(table)
    console.print("[dim]Review/cull queue.json, then: localapply apply --queue queue.json[/]")


# expose as `localapply discover`
app.command(name="discover")(discover_jobs)


@app.command()
def apply(
    queue: str = typer.Option("queue.json", help="Queue file from `discover`"),
    config: str = "config.yaml",
):
    """Fill each job to the submit page and STOP for your review. Never submits."""
    cfg = load_config(config)
    profile = load_json(cfg.get("profile", "profile.json"))
    answers = load_json(cfg.get("answers", "answers.json"))
    llm = load_llm(cfg)
    jobs = load_json(queue)
    console.print(
        "[bold]LocalApply is human-gated.[/] It will fill each form and stop at submit.\n"
        "You review and submit every application yourself.\n"
    )
    run(jobs, profile, answers, llm, cfg)


if __name__ == "__main__":
    app()
