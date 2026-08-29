"""The human-gated apply loop.

Drives the autonomous Agent over each job: open the page, let the agent perceive/decide/act
until the form is complete or a submit step appears, then STOP. The runner prints what the
agent filled and what it left for you (and why), and waits for you to review + submit. No code
path here or in the agent clicks submit.
"""
from __future__ import annotations

import time

from playwright.sync_api import sync_playwright
from rich.console import Console
from rich.panel import Panel

from .agent import Agent
from .tracker import Tracker

console = Console()


def run(jobs: list[dict], profile: dict, answers: dict, llm, cfg: dict) -> None:
    b = cfg.get("browser", {})
    tracker = Tracker(cfg.get("tracker_path", "tracker.json"))
    agent = Agent(llm, resume_path=profile["resume_path"],
                  step_budget=cfg.get("runner", {}).get("step_budget", 60))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=b.get("headless", False),
                                    slow_mo=b.get("slow_mo_ms", 250))
        context = browser.new_context(accept_downloads=True)

        for i, job in enumerate(jobs, 1):
            console.rule(f"[bold]{i}/{len(jobs)}  {job.get('company','')} — {job.get('title','')}")
            page = context.new_page()
            try:
                page.goto(job["url"], wait_until="domcontentloaded", timeout=45000)
                _dismiss_cookies(page)
                result = agent.run(page, profile, answers)
            except Exception as e:  # noqa: BLE001
                console.print(f"[red]Error: {e}")
                tracker.record(job, status="error", note=str(e))
                page.close()
                continue

            _report(result)
            tracker.record(job, status="filled_parked", steps=result.steps,
                           filled=result.filled,
                           flagged=[f.label for f in result.flagged],
                           resume=result.resume_attached,
                           stopped=result.stopped_reason)

            console.print(
                "\n[bold cyan]Review the form in the browser, then submit it yourself.[/]\n"
                "Press [bold]Enter[/] when done (or 's' to skip)…"
            )
            if input("> ").strip().lower() == "s":
                tracker.record(job, status="skipped_by_user")
            page.close()

            if i < len(jobs):
                time.sleep(b.get("throttle_between_jobs_s", 30))

        browser.close()
    console.print(f"\n[green]Done. Tracker: {tracker.path}[/]")


def _dismiss_cookies(page):
    import re
    for name in ("Deny", "Decline", "Reject", "Accept all", "Accept"):
        try:
            btn = page.get_by_role("button", name=re.compile(name, re.I))
            if btn.count():
                btn.first.click(timeout=1200)
                return
        except Exception:
            continue


def _report(result) -> None:
    body = [
        f"[green]Résumé attached:[/] {result.resume_attached}",
        f"[green]Filled ({len(result.filled)}) in {result.steps} agent steps:[/] "
        + ", ".join(result.filled[:20]),
    ]
    if result.flagged:
        body.append("\n[bold yellow]Left for you (couldn't answer honestly):[/]")
        body += [f"  • {f.label} — {f.reason}" for f in result.flagged]
    else:
        body.append("[dim]Nothing flagged — still review before submitting.[/]")
    body.append(f"[dim]Stopped: {result.stopped_reason}[/]")
    console.print(Panel("\n".join(body), title="agent result", expand=False))
