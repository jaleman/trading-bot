from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from trading_bot.models import GuardrailState
from trading_bot.runtime_paths import ensure_runtime_dirs, resolve_paths


class GuardrailStateStore:
    """Persists daily guardrail counters for the staged trading app."""

    def __init__(self, state_path: Path | None = None) -> None:
        if state_path is None:
            paths = ensure_runtime_dirs(resolve_paths())
            state_path = paths.guardrail_state
        self.state_path = state_path

    def load(self) -> GuardrailState:
        today = date.today().isoformat()
        if not self.state_path.exists():
            return GuardrailState(current_date=today)

        data = json.loads(self.state_path.read_text())
        state = GuardrailState(
            current_date=data.get("current_date", today),
            claude_calls_today=int(data.get("claude_calls_today", 0)),
            trades_today=int(data.get("trades_today", 0)),
        )

        if state.current_date != today:
            return GuardrailState(current_date=today)

        return state

    def save(self, state: GuardrailState) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(asdict(state), indent=2))

    def increment_claude_calls(self, count: int = 1) -> GuardrailState:
        state = self.load()
        updated = GuardrailState(
            current_date=state.current_date,
            claude_calls_today=state.claude_calls_today + count,
            trades_today=state.trades_today,
        )
        self.save(updated)
        return updated

    def increment_trades(self, count: int) -> GuardrailState:
        state = self.load()
        updated = GuardrailState(
            current_date=state.current_date,
            claude_calls_today=state.claude_calls_today,
            trades_today=state.trades_today + count,
        )
        self.save(updated)
        return updated
