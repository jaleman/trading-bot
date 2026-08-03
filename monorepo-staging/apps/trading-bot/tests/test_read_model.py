# pyright: reportMissingImports=false

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_bot.persistence.read_model import (  # noqa: E402
    ReadModelError,
    ScanReadModel,
)


def _entry(run_id, timestamp, portfolio_value=100.0, decisions=None,
           indicators=None, notes=None, include_run_id=True):
    payload = {
        "timestamp": timestamp,
        "summary": {
            "status": "ok",
            "account": {"cash": 10.0, "portfolio_value": portfolio_value, "buying_power": 20.0},
            "decisions": decisions or [],
            "positions": [],
            "indicator_snapshots": indicators or [],
            "guardrails": [],
            "triggered": [], "watching": [], "order_results": [],
            "notes": notes or [],
        },
    }
    if include_run_id:
        payload["run_id"] = run_id
    return json.dumps(payload)


class ReadModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.jsonl = self.root / "trades.jsonl"
        self.db = self.root / "db" / "scans.db"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, lines: list[str]) -> None:
        self.jsonl.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_rebuild_populates_runs_and_children(self) -> None:
        self._write([
            _entry("r1", "2026-03-01T09:00:00", decisions=[
                {"symbol": "AAPL", "action": "buy", "qty": 3, "reason": "signal"}
            ], indicators=[{"symbol": "AAPL", "rsi": 28.0, "current_price": 100.0}]),
        ])
        stats = ScanReadModel(self.db).rebuild(self.jsonl)

        self.assertEqual(stats["runs"], 1)
        self.assertEqual(stats["decisions"], 1)
        self.assertEqual(stats["indicators"], 1)
        self.assertEqual(stats["skipped_lines"], 0)

    def test_rebuild_is_idempotent(self) -> None:
        """The database is derived, so replaying must not duplicate rows."""
        self._write([_entry("r1", "2026-03-01T09:00:00"), _entry("r2", "2026-03-02T09:00:00")])
        model = ScanReadModel(self.db)

        first = model.rebuild(self.jsonl)
        second = model.rebuild(self.jsonl)

        self.assertEqual(first, second)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0], 2)

    def test_entries_without_run_id_get_stable_synthetic_ids(self) -> None:
        """April 2026 history predates run-ID stamping."""
        self._write([_entry(None, "2026-03-01T09:00:00", include_run_id=False)])
        model = ScanReadModel(self.db)

        model.rebuild(self.jsonl)
        with sqlite3.connect(self.db) as conn:
            first_id = conn.execute("SELECT run_id FROM runs").fetchone()[0]
        model.rebuild(self.jsonl)
        with sqlite3.connect(self.db) as conn:
            second_id = conn.execute("SELECT run_id FROM runs").fetchone()[0]

        self.assertTrue(first_id.startswith("legacy-"))
        self.assertEqual(first_id, second_id, "synthetic ids must be stable across rebuilds")

    def test_malformed_line_costs_one_run_not_the_history(self) -> None:
        self._write([
            _entry("r1", "2026-03-01T09:00:00"),
            "{ this is not valid json",
            _entry("r2", "2026-03-02T09:00:00"),
        ])
        stats = ScanReadModel(self.db).rebuild(self.jsonl)

        self.assertEqual(stats["runs"], 2)
        self.assertEqual(stats["skipped_lines"], 1)

    def test_missing_source_log_raises(self) -> None:
        with self.assertRaises(ReadModelError):
            ScanReadModel(self.db).rebuild(self.root / "nope.jsonl")

    def test_gate_metrics_computes_return_and_drawdown(self) -> None:
        self._write([
            _entry("r1", "2026-03-01T09:00:00", portfolio_value=100_000.0),
            _entry("r2", "2026-03-02T09:00:00", portfolio_value=110_000.0),
            _entry("r3", "2026-03-03T09:00:00", portfolio_value=104_500.0),
        ])
        model = ScanReadModel(self.db)
        model.rebuild(self.jsonl)
        metrics = model.gate_metrics()

        self.assertEqual(metrics["return_pct"], 4.5)
        self.assertEqual(metrics["peak_value"], 110_000.0)
        self.assertEqual(metrics["max_drawdown_from_peak_pct"], -5.0)

    def test_gate_metrics_scopes_to_clock_start_and_uses_baseline(self) -> None:
        """A clock_start must exclude pre-launch history from the gate window."""
        self._write([
            _entry("dormant", "2026-03-01T09:00:00", portfolio_value=200_000.0),
            _entry("r1", "2026-07-27T09:00:00", portfolio_value=97_444.87),
            _entry("r2", "2026-07-28T09:00:00", portfolio_value=99_161.47),
            _entry("r3", "2026-07-31T09:00:00", portfolio_value=93_316.10),
        ])
        model = ScanReadModel(self.db)
        model.rebuild(self.jsonl)

        metrics = model.gate_metrics(
            clock_start="2026-07-27T00:00:00", baseline_value=97_444.87
        )

        self.assertEqual(metrics["runs"], 3)
        self.assertEqual(metrics["starting_value"], 97_444.87)
        self.assertEqual(metrics["peak_value"], 99_161.47)
        self.assertEqual(
            metrics["return_pct"],
            round((93_316.10 - 97_444.87) / 97_444.87 * 100, 2),
        )

    def test_gate_metrics_does_not_fabricate_consecutive_losses(self) -> None:
        """Realized round-trip P/L belongs to Alpaca, not inferred from scans."""
        self._write([_entry("r1", "2026-03-01T09:00:00")])
        model = ScanReadModel(self.db)
        model.rebuild(self.jsonl)

        self.assertIn("reconciliation", str(model.gate_metrics()["consecutive_losses"]))

    def test_degraded_runs_are_flagged_from_notes(self) -> None:
        self._write([
            _entry("r1", "2026-03-01T09:00:00",
                   notes=["Market data degraded: 3 of 50 symbol(s) failed"]),
            _entry("r2", "2026-03-02T09:00:00", notes=["all good"]),
        ])
        model = ScanReadModel(self.db)
        model.rebuild(self.jsonl)

        self.assertEqual(model.gate_metrics()["degraded_runs"], 1)


if __name__ == "__main__":
    unittest.main()
