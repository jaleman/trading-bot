from __future__ import annotations

import json
from pathlib import Path

from trading_bot.models import (
    CostControlsConfig,
    EntryConfig,
    ExecutionControlsConfig,
    ExitConfig,
    ModelsConfig,
    MovingAverageConfig,
    PaperToLiveConfig,
    StrategyConfig,
)
from trading_bot.runtime_paths import resolve_paths


def load_strategy_config(path: str | Path | None = None) -> StrategyConfig:
    config_path = Path(path) if path else resolve_paths().strategy_config
    raw = json.loads(config_path.read_text())

    return StrategyConfig(
        watchlist=raw["watchlist"],
        max_positions=raw["max_positions"],
        max_trades_per_day=raw.get("max_trades_per_day", 2),
        max_position_size_pct=raw.get("max_position_size_pct", 25),
        entry=EntryConfig(
            ma_crossover=MovingAverageConfig(
                short=raw["entry"]["ma_crossover"]["short"],
                long=raw["entry"]["ma_crossover"]["long"],
            ),
            rsi_threshold=raw["entry"]["rsi_threshold"],
        ),
        exit=ExitConfig(
            profit_target_pct=raw["exit"]["profit_target_pct"],
            stop_loss_pct=raw["exit"]["stop_loss_pct"],
        ),
        models=ModelsConfig(
            daily_decision=raw["models"]["daily_decision"],
            monitoring=raw["models"]["monitoring"],
        ),
        cost_controls=CostControlsConfig(
            daily_claude_call_limit=raw["cost_controls"]["daily_claude_call_limit"],
            context_reset_after_exchanges=raw["cost_controls"]["context_reset_after_exchanges"],
            prompt_caching_enabled=raw["cost_controls"]["prompt_caching_enabled"],
        ),
        execution_controls=ExecutionControlsConfig(
            safe_mode=raw.get("execution_controls", {}).get("safe_mode", True),
            paper_trade_execution_enabled=raw.get("execution_controls", {}).get(
                "paper_trade_execution_enabled", False
            ),
            write_logs_by_default=raw.get("execution_controls", {}).get(
                "write_logs_by_default", True
            ),
        ),
        paper_to_live=PaperToLiveConfig(
            min_return_pct=raw["paper_to_live"]["min_return_pct"],
            evaluation_days=raw["paper_to_live"]["evaluation_days"],
            max_consecutive_losses=raw["paper_to_live"]["max_consecutive_losses"],
        ),
    )
