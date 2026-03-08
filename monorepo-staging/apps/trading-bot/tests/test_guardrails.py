# pyright: reportMissingImports=false

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_bot.models import (  # noqa: E402
    AccountSnapshot,
    CostControlsConfig,
    EntryConfig,
    ExecutionControlsConfig,
    ExitConfig,
    GuardrailState,
    ModelsConfig,
    MovingAverageConfig,
    PaperToLiveConfig,
    PositionSnapshot,
    StrategyConfig,
    TradeDecision,
)
from trading_bot.services.guardrails import (  # noqa: E402
    evaluate_claude_call_limit,
    evaluate_execution_policy,
    evaluate_position_size,
    evaluate_trade_limits,
)


def build_strategy(*, safe_mode: bool = True, paper_enabled: bool = False) -> StrategyConfig:
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
        models=ModelsConfig(
            daily_decision="claude-sonnet-4-6",
            monitoring="qwen2.5:7b",
        ),
        cost_controls=CostControlsConfig(
            daily_claude_call_limit=5,
            context_reset_after_exchanges=20,
            prompt_caching_enabled=True,
        ),
        execution_controls=ExecutionControlsConfig(
            safe_mode=safe_mode,
            paper_trade_execution_enabled=paper_enabled,
            write_logs_by_default=True,
        ),
        paper_to_live=PaperToLiveConfig(
            min_return_pct=3.75,
            evaluation_days=90,
            max_consecutive_losses=2,
        ),
    )


class GuardrailTests(unittest.TestCase):
    def test_claude_call_limit_blocks_at_limit(self) -> None:
        strategy = build_strategy()
        state = GuardrailState(current_date="2026-03-08", claude_calls_today=5, trades_today=0)

        status = evaluate_claude_call_limit(strategy, state)

        self.assertFalse(status.allowed)
        self.assertIn("Daily Claude call limit reached.", status.reasons)
        self.assertEqual(status.details["remaining"], 0)

    def test_trade_limits_block_buys_when_daily_limit_hit(self) -> None:
        strategy = build_strategy()
        state = GuardrailState(current_date="2026-03-08", claude_calls_today=0, trades_today=2)
        decisions = [
            TradeDecision(symbol="JPM", action="buy", reason="ok"),
            TradeDecision(symbol="MSFT", action="skip", reason="skip"),
        ]

        filtered, status = evaluate_trade_limits(strategy, state, [], decisions)

        self.assertEqual([item.action for item in filtered], ["skip"])
        self.assertFalse(status.allowed)
        self.assertIn("Daily trade limit reached.", status.reasons)

    def test_trade_limits_block_buys_when_position_limit_hit(self) -> None:
        strategy = build_strategy()
        state = GuardrailState(current_date="2026-03-08", claude_calls_today=0, trades_today=0)
        positions = [
            PositionSnapshot("A", 1, 1, 1, 0, 0),
            PositionSnapshot("B", 1, 1, 1, 0, 0),
            PositionSnapshot("C", 1, 1, 1, 0, 0),
            PositionSnapshot("D", 1, 1, 1, 0, 0),
        ]
        decisions = [TradeDecision(symbol="JPM", action="buy", reason="ok")]

        filtered, status = evaluate_trade_limits(strategy, state, positions, decisions)

        self.assertEqual(filtered, [])
        self.assertFalse(status.allowed)
        self.assertIn("Maximum simultaneous positions reached.", status.reasons)

    def test_execution_policy_blocks_when_safe_mode_enabled(self) -> None:
        strategy = build_strategy(safe_mode=True, paper_enabled=True)

        status = evaluate_execution_policy(strategy)

        self.assertFalse(status.allowed)
        self.assertIn("Execution blocked because safe mode is enabled.", status.reasons)

    def test_position_size_requires_nonzero_account_context(self) -> None:
        strategy = build_strategy()
        status = evaluate_position_size(
            strategy,
            AccountSnapshot(cash=0.0, portfolio_value=0.0, buying_power=0.0),
        )

        self.assertFalse(status.allowed)
        self.assertIn("Position sizing unavailable", status.reasons[0])


if __name__ == "__main__":
    unittest.main()
