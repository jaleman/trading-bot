from __future__ import annotations

import json
from pathlib import Path

from trading_bot.models import (
    CostControlsConfig,
    EntryConfig,
    ExecutionControlsConfig,
    ExitConfig,
    ModelRoutingConfig,
    ModelsConfig,
    MovingAverageConfig,
    PaperToLiveConfig,
    RiskConfig,
    StrategyConfig,
    UniverseConfig,
)
from trading_bot.runtime_paths import resolve_paths


def _first_present(raw: dict, *keys: str, default=None):
    for key in keys:
        if key in raw:
            return raw[key]

    return default


def _load_universe_config(raw: dict) -> UniverseConfig:
    universe_raw = raw.get("universe", {})
    symbols = list(universe_raw.get("symbols") or raw.get("watchlist", []))

    return UniverseConfig(
        preset=universe_raw.get("preset"),
        symbols=symbols,
        include_symbols=list(universe_raw.get("include_symbols", [])),
        exclude_symbols=list(universe_raw.get("exclude_symbols", [])),
        shortlist_size=universe_raw.get("shortlist_size", 20),
        min_price=universe_raw.get("min_price"),
        min_avg_dollar_volume=universe_raw.get("min_avg_dollar_volume"),
    )


def _load_risk_config(raw: dict) -> RiskConfig:
    risk_raw = raw.get("risk", {})
    max_positions = risk_raw["max_positions"] if "max_positions" in risk_raw else raw["max_positions"]

    return RiskConfig(
        max_positions=max_positions,
        max_trades_per_day=risk_raw.get("max_trades_per_day", raw.get("max_trades_per_day", 2)),
        max_position_size_pct=risk_raw.get("max_position_size_pct", raw.get("max_position_size_pct", 25)),
        max_sector_exposure_pct=risk_raw.get("max_sector_exposure_pct"),
        allow_pyramiding=risk_raw.get("allow_pyramiding", False),
    )


def _load_models_config(raw: dict) -> ModelsConfig:
    models_raw = raw["models"]

    return ModelsConfig(
        daily_decision=_first_present(
            models_raw,
            "claude_review",
            "daily_decision",
        ),
        monitoring=_first_present(
            models_raw,
            "local_analysis",
            "monitoring",
        ),
    )


def _load_model_routing_config(raw: dict) -> ModelRoutingConfig:
    routing_raw = raw.get("model_routing", {})

    return ModelRoutingConfig(
        local_analysis_enabled=routing_raw.get("local_analysis_enabled", True),
        claude_escalation_enabled=routing_raw.get("claude_escalation_enabled", True),
        max_candidates_for_local_analysis=routing_raw.get(
            "max_candidates_for_local_analysis", 20
        ),
        escalate_when_slots_remaining_lte=routing_raw.get(
            "escalate_when_slots_remaining_lte", 1
        ),
    )


def load_strategy_config(path: str | Path | None = None) -> StrategyConfig:
    config_path = Path(path) if path else resolve_paths().strategy_config
    raw = json.loads(config_path.read_text())
    universe = _load_universe_config(raw)
    risk = _load_risk_config(raw)

    return StrategyConfig(
        watchlist=universe.symbols,
        max_positions=risk.max_positions,
        max_trades_per_day=risk.max_trades_per_day,
        max_position_size_pct=risk.max_position_size_pct,
        entry=EntryConfig(
            ma_crossover=MovingAverageConfig(
                short=raw["entry"]["ma_crossover"]["short"],
                long=raw["entry"]["ma_crossover"]["long"],
            ),
            min_rsi=raw["entry"].get("min_rsi"),
            rsi_threshold=raw["entry"]["rsi_threshold"],
            max_volatility_20d=raw["entry"].get("max_volatility_20d"),
            min_recent_return_5d=raw["entry"].get("min_recent_return_5d"),
            min_recent_return_20d=raw["entry"].get("min_recent_return_20d"),
            min_distance_to_ma_20_pct=raw["entry"].get("min_distance_to_ma_20_pct"),
            min_distance_to_ma_50_pct=raw["entry"].get("min_distance_to_ma_50_pct"),
        ),
        exit=ExitConfig(
            profit_target_pct=raw["exit"]["profit_target_pct"],
            stop_loss_pct=raw["exit"]["stop_loss_pct"],
        ),
        models=_load_models_config(raw),
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
        universe=universe,
        risk=risk,
        model_routing=_load_model_routing_config(raw),
    )
