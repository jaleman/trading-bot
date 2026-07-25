# pyright: reportMissingImports=false

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_bot.models import TradeHistoryEntry  # noqa: E402
from trading_bot.services.reconciliation import (  # noqa: E402
    build_round_trips,
    load_believed_orders,
    reconcile,
)


def fill(symbol, side, qty, price, when, *, order_id=None, status="FILLED", filled_qty=None):
    return TradeHistoryEntry(
        symbol=symbol, qty=qty, side=side, status=status,
        filled_avg_price=price, id=order_id or f"{symbol}-{side}-{when}",
        filled_qty=qty if filled_qty is None else filled_qty,
        submitted_at=when, filled_at=when,
    )


def believed(symbol, side, qty, order_id, status="ACCEPTED"):
    return {"id": order_id, "symbol": symbol, "qty": qty, "side": side,
            "believed_status": status, "run_id": "r1", "timestamp": "2026-03-01T09:00:00"}


class DiscrepancyDetectionTests(unittest.TestCase):
    def test_clean_match_reports_no_discrepancies(self) -> None:
        report = reconcile(
            [believed("AAPL", "BUY", 10, "o1")],
            [fill("AAPL", "BUY", 10, 100.0, "2026-03-01T09:00:00", order_id="o1")],
        )
        self.assertEqual(report.discrepancies, 0)
        self.assertEqual(len(report.matched), 1)

    def test_order_the_bot_believes_in_but_broker_never_saw(self) -> None:
        """The bot thinks it traded; the broker has no such order."""
        report = reconcile([believed("AAPL", "BUY", 10, "ghost")], [])

        self.assertEqual(len(report.missing_at_broker), 1)
        self.assertEqual(report.discrepancies, 1)

    def test_broker_fill_the_bot_has_no_record_of(self) -> None:
        report = reconcile(
            [], [fill("TSLA", "BUY", 5, 200.0, "2026-03-01T09:00:00", order_id="x1")]
        )
        self.assertEqual(len(report.unknown_to_bot), 1)
        self.assertEqual(report.unknown_to_bot[0]["symbol"], "TSLA")

    def test_partial_fill_is_flagged(self) -> None:
        """Bot believes 914 shares; only 600 actually filled."""
        report = reconcile(
            [believed("PFE", "BUY", 914, "o2")],
            [fill("PFE", "BUY", 914, 27.25, "2026-03-01T09:00:00",
                  order_id="o2", filled_qty=600)],
        )
        self.assertEqual(len(report.partial_fills), 1)
        self.assertEqual(report.partial_fills[0]["filled_qty"], 600)

    def test_rejected_order_is_flagged_as_not_filled(self) -> None:
        report = reconcile(
            [believed("AAPL", "BUY", 10, "o3")],
            [fill("AAPL", "BUY", 10, 0.0, "2026-03-01T09:00:00",
                  order_id="o3", status="REJECTED", filled_qty=0)],
        )
        self.assertEqual(len(report.not_filled), 1)
        self.assertEqual(report.not_filled[0]["actual_status"], "REJECTED")


class RoundTripTests(unittest.TestCase):
    def test_buy_then_sell_produces_realized_pl(self) -> None:
        trips = build_round_trips([
            fill("CVX", "BUY", 132, 187.81, "2026-03-11T13:36:58"),
            fill("CVX", "SELL", 132, 207.40, "2026-03-24T13:37:28"),
        ])
        self.assertEqual(len(trips), 1)
        self.assertAlmostEqual(trips[0].realized_pl, 2585.88, places=1)
        self.assertFalse(trips[0].is_loss)

    def test_open_position_yields_no_round_trip(self) -> None:
        """An unsold buy has no realized P/L and must not be marked to market."""
        trips = build_round_trips([fill("LIN", "BUY", 51, 493.59, "2026-03-26T13:36:51")])
        self.assertEqual(trips, [])

    def test_unfilled_orders_are_excluded(self) -> None:
        trips = build_round_trips([
            fill("AAPL", "BUY", 10, 0.0, "2026-03-01T09:00:00", status="CANCELED", filled_qty=0),
            fill("AAPL", "SELL", 10, 0.0, "2026-03-02T09:00:00", status="CANCELED", filled_qty=0),
        ])
        self.assertEqual(trips, [])

    def test_buys_are_paired_fifo(self) -> None:
        trips = build_round_trips([
            fill("X", "BUY", 10, 100.0, "2026-03-01T09:00:00"),
            fill("X", "BUY", 10, 200.0, "2026-03-02T09:00:00"),
            fill("X", "SELL", 10, 150.0, "2026-03-03T09:00:00"),
        ])
        self.assertEqual(len(trips), 1)
        # FIFO: the $100 lot closes first, so this is a win, not a loss.
        self.assertEqual(trips[0].buy_price, 100.0)
        self.assertFalse(trips[0].is_loss)

    def test_partial_sell_leaves_remainder_open(self) -> None:
        trips = build_round_trips([
            fill("X", "BUY", 10, 100.0, "2026-03-01T09:00:00"),
            fill("X", "SELL", 4, 120.0, "2026-03-02T09:00:00"),
        ])
        self.assertEqual(len(trips), 1)
        self.assertEqual(trips[0].qty, 4)
        self.assertAlmostEqual(trips[0].realized_pl, 80.0, places=2)


class GateMetricTests(unittest.TestCase):
    def _report(self, results):
        fills = []
        for i, (symbol, buy, sell) in enumerate(results):
            fills.append(fill(symbol, "BUY", 1, buy, f"2026-03-{i*2+1:02d}T09:00:00"))
            fills.append(fill(symbol, "SELL", 1, sell, f"2026-03-{i*2+2:02d}T09:00:00"))
        return reconcile([], fills)

    def test_counts_wins_and_losses(self) -> None:
        report = self._report([("A", 100, 110), ("B", 100, 90), ("C", 100, 120)])
        self.assertEqual(report.wins, 2)
        self.assertEqual(report.losses, 1)

    def test_max_consecutive_losses_is_the_longest_run(self) -> None:
        # loss, loss, win, loss  -> longest run is 2
        report = self._report([("A", 100, 90), ("B", 100, 80), ("C", 100, 130), ("D", 100, 95)])
        self.assertEqual(report.max_consecutive_losses, 2)

    def test_no_round_trips_means_zero_consecutive_losses(self) -> None:
        self.assertEqual(reconcile([], []).max_consecutive_losses, 0)


class LoadBelievedOrdersTests(unittest.TestCase):
    def test_reads_orders_across_runs_and_tolerates_bad_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trades.jsonl"
            path.write_text("\n".join([
                json.dumps({"run_id": "r1", "timestamp": "t1", "summary": {"order_results": [
                    {"id": "o1", "symbol": "AAPL", "qty": 1, "side": "OrderSide.BUY",
                     "status": "OrderStatus.ACCEPTED"}]}}),
                "not json at all",
                json.dumps({"run_id": "r2", "timestamp": "t2", "summary": {"order_results": []}}),
            ]) + "\n", encoding="utf-8")

            orders = load_believed_orders(path)

        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]["side"], "BUY")
        self.assertEqual(orders[0]["believed_status"], "ACCEPTED")

    def test_missing_file_is_not_an_error(self) -> None:
        self.assertEqual(load_believed_orders("/nonexistent/trades.jsonl"), [])


if __name__ == "__main__":
    unittest.main()
