"""The human-gated apply loop.

For each job: open it, detect the ATS, let the adapter fill everything it honestly can,
then STOP. The runner prints exactly what was filled and what was left for the human (and
why), and waits for you to review + submit in the browser before moving on. It never clicks
a submit button — that capability simply does not exist in this codebase.
"""
from __future__ import annotations

import time

from playwright.sync_api import sync_playwright
from rich.console import Console
from rich.panel import Panel

from .adapters import get_adapter
from .tracker import Tracker

console = Console()


def run(jobs: list[dict], profile: dict, answers: dict, llm, cfg: dict) -> None:
    b = cfg.get("browser", {})
    tracker = Tracker(cfg.get("tracker_path", "tracker.json"))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=b.get("headless", False),
                                    slow_mo=b.get("slow_mo_ms", 250))
        context = browser.new_context(accept_downloads=True)

        for i, job in enumerate(jobs, 1):
            url = job["url"]
            adapter = get_adapter(url)
            console.rule(f"[bold]{i}/{len(jobs)}  {job.get('company','')} — {job.get('title','')}")
            if not adapter:
                console.print(f"[yellow]No adapter for {url} — skipping (add one!).")
                tracker.record(job, status="skipped_no_adapter")
                continue

            page = context.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                result = adapter.fill(page, profile, answers, llm)
            except Exception as e:
                console.print(f"[red]Error filling: {e}")
                tracker.record(job, status="error", note=str(e))
                page.close()
                continue

            _report(result)
            tracker.record(job, status="filled_parked",
                           filled=result.filled,
                           flagged=[f.label for f in result.flagged],
                           resume=result.resume_attached)

            # HUMAN GATE. We do not submit. You do.
            console.print(
                "\n[bold cyan]Review the form in the browser, then submit it yourself.[/]\n"
                "Press [bold]Enter[/] here when you're done (or type 's' to skip)…"
            )
            choice = input("> ").strip().lower()
            if choice == "s":
                tracker.record(job, status="skipped_by_user")
            page.close()

            if i < len(jobs):
                time.sleep(b.get("throttle_between_jobs_s", 30))

        browser.close()
    console.print(f"\n[green]Done. Tracker written to {tracker.path}.")


def _report(result) -> None:
    body = []
    if result.error:
        console.print(f"[red]{result.error}")
        return
    body.append(f"[green]Resume attached:[/] {result.resume_attached}")
    body.append(f"[green]Filled ({len(result.filled)}):[/] " + ", ".join(result.filled[:20]))
    if result.flagged:
        body.append("\n[bold yellow]Left for you (could not answer honestly):[/]")
        for f in result.flagged:
            body.append(f"  • {f.label} — {f.reason}")
    else:
        body.append("[dim]Nothing flagged — but still review before submitting.[/]")
    console.print(Panel("\n".join(body), title=f"{result.company} · {result.ats}", expand=False))
