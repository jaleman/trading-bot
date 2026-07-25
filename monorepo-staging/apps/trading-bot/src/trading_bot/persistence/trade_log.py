from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import json
import os
import traceback
import uuid

from trading_bot.models import DailyScanSummary
from trading_bot.runtime_paths import ensure_runtime_dirs, resolve_paths


def new_run_id() -> str:
    """Short, sortable identifier correlating one scan across log files."""
    return f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:4]}"


class TradeLogger:
    """Append-only runtime logger for the staged trading-bot app.

    Writes are append-and-sync so that a crash, kill, or power loss leaves the
    record written so far intact. An earlier implementation read the whole log
    and rewrote it for every line, which was quadratic and — worse — could
    truncate the entire history if it failed mid-write.
    """

    def __init__(self, log_path: str | Path | None = None, run_id: str | None = None) -> None:
        if log_path is None:
            paths = resolve_paths()
            ensure_runtime_dirs(paths)
            log_path = paths.trade_log
        # Coerce so a str path does not fail later on .parent / .with_suffix.
        self.log_path = Path(log_path)
        self.run_id = run_id or new_run_id()

    def _append(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(text)
            # Durability matters more than throughput here: this is roughly
            # twenty lines a day, and the whole point is surviving a crash.
            handle.flush()
            os.fsync(handle.fileno())

    def log_message(self, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._append(self.log_path, f"[{timestamp}] [{self.run_id}] {message}\n")

    def log_messages(self, messages: list[str]) -> None:
        for message in messages:
            self.log_message(message)

    def log_exception(self, exc: BaseException, context: str = "") -> None:
        """Record an unhandled failure, including traceback, before re-raising.

        Without this a crashed scan left no trace at all, because logging only
        ran after a successful scan completed.
        """
        label = f"{context}: " if context else ""
        self.log_message(f"{label}UNHANDLED {type(exc).__name__}: {exc}")
        formatted = "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        ).rstrip()
        for line in formatted.splitlines():
            self.log_message(f"    {line}")

    def log_summary_json(self, summary: DailyScanSummary) -> None:
        jsonl_path = self.log_path.with_suffix(".jsonl")
        payload = {
            "timestamp": datetime.now().isoformat(),
            "run_id": self.run_id,
            "summary": asdict(summary),
        }
        self._append(jsonl_path, json.dumps(payload) + "\n")
