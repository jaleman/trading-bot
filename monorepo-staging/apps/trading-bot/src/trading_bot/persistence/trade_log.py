from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import json

from trading_bot.models import DailyScanSummary
from trading_bot.runtime_paths import ensure_runtime_dirs, resolve_paths


class TradeLogger:
    """Simple runtime logger for the staged trading-bot app."""

    def __init__(self, log_path: Path | None = None) -> None:
        if log_path is None:
            paths = resolve_paths()
            ensure_runtime_dirs(paths)
            log_path = paths.trade_log
        self.log_path = log_path

    def log_message(self, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {message}\n"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.write_text(
            self.log_path.read_text() + entry if self.log_path.exists() else entry
        )

    def log_summary_json(self, summary: DailyScanSummary) -> None:
        jsonl_path = self.log_path.with_suffix(".jsonl")
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "timestamp": datetime.now().isoformat(),
            "summary": asdict(summary),
        }
        with jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
