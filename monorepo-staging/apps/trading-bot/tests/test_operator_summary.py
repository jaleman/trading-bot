# pyright: reportMissingImports=false

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_bot.operator_summary import (  # noqa: E402
	format_operator_summary,
	load_latest_summary_payload,
)


class OperatorSummaryTests(unittest.TestCase):
	def test_load_latest_summary_payload_uses_last_nonempty_line(self) -> None:
		with tempfile.TemporaryDirectory() as tmp:
			jsonl_path = Path(tmp) / "trades.jsonl"
			jsonl_path.write_text(
				json.dumps({"summary": {"status": "first"}}) + "\n\n" + json.dumps({"summary": {"status": "last"}}) + "\n"
			)

			payload = load_latest_summary_payload(jsonl_path)

		self.assertEqual(payload["summary"]["status"], "last")

	def test_format_operator_summary_safe_mode_output(self) -> None:
		payload = {
			"timestamp": "2026-03-08T16:12:11",
			"summary": {
				"status": "production-candidate-safe-mode",
				"notes": [
					"Safe mode is enabled in the staged runtime; no trades will execute unless execution policy is explicitly changed.",
				],
				"indicator_snapshots": [{"symbol": "CAT"}, {"symbol": "MSFT"}],
				"triggered": ["CAT"],
				"watching": [],
				"decisions": [{"symbol": "CAT", "action": "buy"}],
				"order_results": [],
				"guardrails": [{"name": "daily_claude_call_limit", "allowed": True}],
				"guardrail_state": {"claude_calls_today": 1, "trades_today": 0},
			},
		}

		summary_text = format_operator_summary(payload)

		self.assertIn("Safe mode remained active; no trades executed.", summary_text)
		self.assertIn("Scanned 2 symbol(s). Triggered: CAT.", summary_text)
		self.assertIn("Decisions: 1 buy, 0 sell, 0 skip.", summary_text)
		self.assertIn("Guardrails passed. Claude calls today: 1. Trades today: 0.", summary_text)
		self.assertTrue(summary_text.startswith("Trading scan completed."))

	def test_format_operator_summary_does_not_report_safe_mode_when_disabled(self) -> None:
		payload = {
			"timestamp": "2026-03-08T19:42:28",
			"summary": {
				"status": "production-candidate",
				"notes": [
					"Safe mode is disabled in config; paper-trade execution remains subject to explicit invocation and guardrails.",
				],
				"indicator_snapshots": [{"symbol": "CAT"}],
				"triggered": ["CAT"],
				"watching": [],
				"decisions": [{"symbol": "CAT", "action": "buy"}],
				"order_results": [],
				"guardrails": [{"name": "daily_claude_call_limit", "allowed": True}],
				"guardrail_state": {"claude_calls_today": 4, "trades_today": 0},
			},
		}

		summary_text = format_operator_summary(payload)

		self.assertTrue(summary_text.startswith("Trading scan completed."))
		self.assertNotIn("Safe mode remained active", summary_text)
		self.assertIn("Decisions: 1 buy, 0 sell, 0 skip.", summary_text)


if __name__ == "__main__":
	unittest.main()