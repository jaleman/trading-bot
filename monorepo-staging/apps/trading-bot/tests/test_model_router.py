# pyright: reportMissingImports=false

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_bot.models import (  # noqa: E402
    CostControlsConfig,
    EntryConfig,
    ExecutionControlsConfig,
    ExitConfig,
    LocalAnalysisResult,
    ModelsConfig,
    ModelRoutingConfig,
    MovingAverageConfig,
    PaperToLiveConfig,
    RiskConfig,
    StrategyConfig,
    TradeDecision,
    UniverseConfig,
)
from trading_bot.services.model_router import should_escalate_to_claude  # noqa: E402


def build_strategy(*, claude_enabled: bool = True) -> StrategyConfig:
    return StrategyConfig(
        watchlist=["JPM", "MSFT"],
        max_positions=4,
        max_trades_per_day=2,
        max_position_size_pct=25,
        entry=EntryConfig(
            ma_crossover=MovingAverageConfig(short=20, long=50),
            rsi_threshold=30,
        ),
        exit=ExitConfig(profit_target_pct=10, stop_loss_pct=4.5),
        models=ModelsConfig(daily_decision="claude-sonnet-4-6", monitoring="qwen2.5:7b"),
        cost_controls=CostControlsConfig(
            daily_claude_call_limit=5,
            context_reset_after_exchanges=20,
            prompt_caching_enabled=True,
        ),
        execution_controls=ExecutionControlsConfig(
            safe_mode=True,
            paper_trade_execution_enabled=False,
            write_logs_by_default=True,
        ),
        paper_to_live=PaperToLiveConfig(
            min_return_pct=3.75,
            evaluation_days=90,
            max_consecutive_losses=2,
        ),
        universe=UniverseConfig(symbols=["JPM", "MSFT"]),
        risk=RiskConfig(max_positions=4, max_trades_per_day=2, max_position_size_pct=25),
        model_routing=ModelRoutingConfig(claude_escalation_enabled=claude_enabled),
    )


class ModelRouterTests(unittest.TestCase):
    def test_local_analysis_request_triggers_escalation(self) -> None:
        should_escalate, reason = should_escalate_to_claude(
            build_strategy(),
            LocalAnalysisResult(
                summary="Mixed setup.",
                ranked_candidates=[],
                escalate_to_claude=True,
                escalation_reason="Need portfolio review.",
            ),
            [],
            [TradeDecision(symbol="JPM", action="buy", reason="ok")],
        )

        self.assertTrue(should_escalate)
        self.assertEqual(reason, "Need portfolio review.")

    def test_disabled_claude_escalation_blocks_router(self) -> None:
        should_escalate, reason = should_escalate_to_claude(
            build_strategy(claude_enabled=False),
            LocalAnalysisResult(summary="", ranked_candidates=[], escalate_to_claude=True, escalation_reason="Need review."),
            [],
            [TradeDecision(symbol="JPM", action="buy", reason="ok")],
        )

        self.assertFalse(should_escalate)
        self.assertEqual(reason, "Claude escalation disabled by strategy config.")


if __name__ == "__main__":
    unittest.main()