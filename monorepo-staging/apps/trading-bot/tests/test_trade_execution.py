# pyright: reportMissingImports=false

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_bot.models import (  # noqa: E402
    AccountSnapshot,
    IndicatorSnapshot,
    OrderResult,
    PositionSnapshot,
    TradeDecision,
)
from trading_bot.services.trade_execution import build_order_results, calculate_qty  # noqa: E402


def account(cash: float, portfolio: float, buying_power: float | None = None) -> AccountSnapshot:
    return AccountSnapshot(
        cash=cash,
        portfolio_value=portfolio,
        buying_power=cash if buying_power is None else buying_power,
    )


def snapshot(symbol: str, price: float) -> IndicatorSnapshot:
    return IndicatorSnapshot(symbol=symbol, current_price=price, ma_20=0, ma_50=0, rsi=50)


def buy(symbol: str) -> TradeDecision:
    return TradeDecision(symbol=symbol, action="buy", reason="test", qty=0)


class CalculateQtyTests(unittest.TestCase):
    def test_sizes_on_portfolio_value_when_cash_is_ample(self) -> None:
        # 25% of a 100k portfolio at $100 == 250 shares.
        qty = calculate_qty(account(cash=100_000, portfolio=100_000), 100.0, 25, 100_000)
        self.assertEqual(qty, 250)

    def test_cash_caps_the_allocation(self) -> None:
        """Portfolio says 250 shares; only $5,000 cash is available."""
        qty = calculate_qty(account(cash=5_000, portfolio=100_000), 100.0, 25, 5_000)
        self.assertEqual(qty, 50)

    def test_no_cash_means_no_shares_rather_than_a_margin_buy(self) -> None:
        self.assertEqual(calculate_qty(account(cash=0, portfolio=100_000), 100.0, 25, 0), 0)

    def test_negative_cash_never_produces_a_position(self) -> None:
        self.assertEqual(calculate_qty(account(cash=-500, portfolio=100_000), 100.0, 25, -500), 0)

    def test_omitting_cash_preserves_portfolio_only_sizing(self) -> None:
        qty = calculate_qty(account(cash=1, portfolio=100_000), 100.0, 25)
        self.assertEqual(qty, 250)


class BuildOrderResultsCashTests(unittest.TestCase):
    def setUp(self) -> None:
        self.placed: list[tuple] = []

    def _place(self, symbol: str, qty: int, side: str) -> OrderResult:
        self.placed.append((symbol, qty, side))
        return OrderResult(id=f"o{len(self.placed)}", symbol=symbol, qty=qty, side=side, status="new")

    def test_second_buy_is_limited_by_cash_left_after_the_first(self) -> None:
        """Regression: both buys previously sized against the same snapshot.

        With $30,000 cash and a $100,000 portfolio, 25% sizing wants $25,000
        each. Sized independently that is $50,000 against $30,000 of cash --
        the shortfall would have been financed on margin.
        """
        results = build_order_results(
            decisions=[buy("AAA"), buy("BBB")],
            snapshots=[snapshot("AAA", 100.0), snapshot("BBB", 100.0)],
            positions=[],
            account=account(cash=30_000, portfolio=100_000),
            max_position_size_pct=25,
            place_order=self._place,
        )

        self.assertEqual(len(results), 2)
        first_cost = self.placed[0][1] * 100.0
        second_cost = self.placed[1][1] * 100.0
        self.assertEqual(first_cost, 25_000.0)
        self.assertEqual(second_cost, 5_000.0, "second buy must use only the remaining cash")
        self.assertLessEqual(first_cost + second_cost, 30_000.0)

    def test_buy_is_skipped_entirely_when_cash_is_exhausted(self) -> None:
        build_order_results(
            decisions=[buy("AAA"), buy("BBB")],
            snapshots=[snapshot("AAA", 100.0), snapshot("BBB", 100.0)],
            positions=[],
            account=account(cash=25_000, portfolio=100_000),
            max_position_size_pct=25,
            place_order=self._place,
        )

        self.assertEqual(len(self.placed), 1, "no order should be placed with zero cash left")
        self.assertEqual(self.placed[0][0], "AAA")

    def test_fully_invested_account_places_no_buys(self) -> None:
        """The live posture: ~$1.8k cash against a ~$97k portfolio."""
        build_order_results(
            decisions=[buy("AAA")],
            snapshots=[snapshot("AAA", 500.0)],
            positions=[],
            account=account(cash=1_848.59, portfolio=97_444.87),
            max_position_size_pct=25,
            place_order=self._place,
        )

        # $1,848 of cash cannot buy a $500 share at 25%-of-portfolio sizing
        # without margin, so at most 3 shares are affordable.
        self.assertTrue(all(qty * 500.0 <= 1_848.59 for _, qty, _ in self.placed))

    def test_sell_proceeds_are_not_spent_in_the_same_scan(self) -> None:
        """Unsettled proceeds must not fund a same-scan buy."""
        sell = TradeDecision(symbol="OLD", action="sell", reason="exit", qty=100)
        build_order_results(
            decisions=[sell, buy("NEW")],
            snapshots=[snapshot("OLD", 100.0), snapshot("NEW", 100.0)],
            positions=[
                PositionSnapshot(
                    symbol="OLD", qty=100, avg_entry_price=100.0,
                    current_price=100.0, unrealized_pl=0.0, unrealized_plpc=0.0,
                )
            ],
            account=account(cash=1_000, portfolio=100_000),
            max_position_size_pct=25,
            place_order=self._place,
        )

        buys = [p for p in self.placed if p[2] == "buy"]
        # Only the original $1,000 is spendable, not the $10,000 just sold.
        self.assertTrue(all(qty * 100.0 <= 1_000 for _, qty, _ in buys))


if __name__ == "__main__":
    unittest.main()
