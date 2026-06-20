"""État partagé pour le suivi temps réel d'une recherche (thread + UI Streamlit)."""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass, field

from services.search_runner import SearchSession, build_initial_steps


@dataclass
class LiveSearchProgress:
    steps: list[dict] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    elapsed_ms: int = 0
    running: bool = False
    done: bool = False
    error: str | None = None
    result: dict | None = None
    start_time: float = field(default_factory=time.time)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def sync_from_session(self, session: SearchSession) -> None:
        with self.lock:
            self.steps = [dict(step) for step in session.steps]
            self.sources = list(session.sources)
            self.elapsed_ms = session.elapsed_ms()

    def snapshot(self) -> dict:
        with self.lock:
            elapsed = int((time.time() - self.start_time) * 1000) if self.running else self.elapsed_ms
            return {
                "steps": [dict(step) for step in self.steps],
                "sources": list(self.sources),
                "elapsed_ms": elapsed,
                "running": self.running,
                "done": self.done,
                "error": self.error,
                "result": dict(self.result) if self.result else None,
            }


def _run_search_thread(
    progress: LiveSearchProgress,
    *,
    app,
    query: str,
    criteria: str,
    playwright_available: bool,
) -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    progress.running = True
    progress.done = False
    progress.error = None
    progress.result = None

    try:
        if app.sidekick is not None and app.sidekick.graph is None:
            app.sidekick = None

        async def _run() -> dict:
            session = SearchSession(playwright_available=playwright_available)
            progress.sync_from_session(session)

            def on_update(s: SearchSession) -> None:
                progress.sync_from_session(s)

            return await session.run(app, query, criteria, on_update=on_update)

        result = loop.run_until_complete(_run())
        with progress.lock:
            progress.result = result
            progress.steps = [dict(step) for step in (result.get("steps") or progress.steps)]
            progress.sources = list(result.get("sources") or progress.sources)
            progress.elapsed_ms = max(progress.elapsed_ms, int(result.get("duration_s", 0) * 1000))
    except Exception as exc:
        progress.error = str(exc)
        with progress.lock:
            for step in progress.steps:
                if step.get("status") in {"active", "pending"}:
                    step["status"] = "done"
            progress.elapsed_ms = int((time.time() - progress.start_time) * 1000)
    finally:
        progress.running = False
        progress.done = True
        with progress.lock:
            if progress.elapsed_ms <= 0:
                progress.elapsed_ms = int((time.time() - progress.start_time) * 1000)
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass
        loop.close()


def start_search_thread(
    *,
    app,
    query: str,
    criteria: str,
    playwright_available: bool,
) -> LiveSearchProgress:
    progress = LiveSearchProgress(steps=build_initial_steps(playwright_available))
    thread = threading.Thread(
        target=_run_search_thread,
        args=(progress,),
        kwargs={
            "app": app,
            "query": query,
            "criteria": criteria,
            "playwright_available": playwright_available,
        },
        daemon=True,
    )
    thread.start()
    progress.thread = thread  # type: ignore[attr-defined]
    return progress
