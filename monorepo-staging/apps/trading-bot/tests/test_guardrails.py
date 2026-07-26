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
    OrderResult,
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
    validate_execution_intents,
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

    def test_execution_firewall_blocks_duplicate_executable_symbols(self) -> None:
        strategy = build_strategy()
        decisions = [
            TradeDecision(symbol="JPM", action="buy", reason="first"),
            TradeDecision(symbol="JPM", action="sell", reason="second", qty=1),
        ]

        filtered, status = validate_execution_intents(
            strategy,
            decisions,
            [],
            AccountSnapshot(cash=1000, portfolio_value=1000, buying_power=1000),
        )

        self.assertEqual(len(filtered), 1)
        self.assertFalse(status.allowed)
        self.assertIn("Blocked duplicate executable action for JPM.", status.reasons)

    def test_execution_firewall_blocks_sell_without_position(self) -> None:
        strategy = build_strategy()
        filtered, status = validate_execution_intents(
            strategy,
            [TradeDecision(symbol="JPM", action="sell", reason="exit", qty=1)],
            [],
            AccountSnapshot(cash=1000, portfolio_value=1000, buying_power=1000),
        )

        self.assertEqual(filtered, [])
        self.assertFalse(status.allowed)
        self.assertIn("Blocked sell for JPM because no open position exists.", status.reasons)

    def test_execution_firewall_blocks_buy_when_position_exists_and_pyramiding_disabled(self) -> None:
        strategy = build_strategy()
        filtered, status = validate_execution_intents(
            strategy,
            [TradeDecision(symbol="JPM", action="buy", reason="entry")],
            [PositionSnapshot("JPM", 1, 90, 100, 10, 0.11)],
            AccountSnapshot(cash=1000, portfolio_value=1000, buying_power=1000),
        )

        self.assertEqual(filtered, [])
        self.assertFalse(status.allowed)
        self.assertIn(
            "Blocked buy for JPM because the position already exists and pyramiding is disabled.",
            status.reasons,
        )

    def test_execution_firewall_blocks_sell_when_order_already_working(self) -> None:
        """The stop-loss re-entry case: a working sell still shows its shares in
        the position, so every other check passes and the exit is submitted twice."""
        strategy = build_strategy()
        filtered, status = validate_execution_intents(
            strategy,
            [TradeDecision(symbol="PFE", action="sell", reason="stop loss", qty=914)],
            [PositionSnapshot("PFE", 914, 27.25, 24.54, -2476.94, -0.0995)],
            AccountSnapshot(cash=1000, portfolio_value=1000, buying_power=1000),
            [OrderResult(id="abc", symbol="PFE", qty=914, side="SELL", status="ACCEPTED")],
        )

        self.assertEqual(filtered, [])
        self.assertFalse(status.allowed)
        self.assertIn(
            "Blocked sell for PFE because an order is already working at the broker.",
            status.reasons,
        )
        self.assertEqual(status.details["pending_order_symbols"], ["PFE"])

    def test_execution_firewall_blocks_buy_when_order_already_working(self) -> None:
        strategy = build_strategy()
        filtered, status = validate_execution_intents(
            strategy,
            [TradeDecision(symbol="ABBV", action="buy", reason="entry")],
            [],
            AccountSnapshot(cash=1000, portfolio_value=1000, buying_power=1000),
            [OrderResult(id="abc", symbol="ABBV", qty=10, side="BUY", status="NEW")],
        )

        self.assertEqual(filtered, [])
        self.assertFalse(status.allowed)
        self.assertIn(
            "Blocked buy for ABBV because an order is already working at the broker.",
            status.reasons,
        )

    def test_execution_firewall_only_blocks_symbols_with_working_orders(self) -> None:
        strategy = build_strategy()
        filtered, status = validate_execution_intents(
            strategy,
            [
                TradeDecision(symbol="PFE", action="sell", reason="stop loss", qty=914),
                TradeDecision(symbol="COST", action="sell", reason="stop loss", qty=24),
            ],
            [
                PositionSnapshot("PFE", 914, 27.25, 24.54, -2476.94, -0.0995),
                PositionSnapshot("COST", 24, 1002.81, 935.03, -1626.72, -0.0676),
            ],
            AccountSnapshot(cash=1000, portfolio_value=1000, buying_power=1000),
            [OrderResult(id="abc", symbol="PFE", qty=914, side="SELL", status="ACCEPTED")],
        )

        self.assertEqual([decision.symbol for decision in filtered], ["COST"])
        self.assertFalse(status.allowed)

    def test_execution_firewall_allows_when_no_orders_are_working(self) -> None:
        strategy = build_strategy()
        decision = TradeDecision(symbol="PFE", action="sell", reason="stop loss", qty=914)
        position = PositionSnapshot("PFE", 914, 27.25, 24.54, -2476.94, -0.0995)
        account = AccountSnapshot(cash=1000, portfolio_value=1000, buying_power=1000)

        for label, open_orders in (("empty", []), ("omitted", None)):
            with self.subTest(open_orders=label):
                filtered, status = validate_execution_intents(
                    strategy, [decision], [position], account, open_orders
                )
                self.assertEqual(filtered, [decision])
                self.assertTrue(status.allowed)
                self.assertEqual(status.details["pending_order_symbols"], [])


if __name__ == "__main__":
    unittest.main()
