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

	def test_format_operator_summary_reports_local_analysis_and_claude_review(self) -> None:
		payload = {
			"timestamp": "2026-03-09T09:35:00",
			"summary": {
				"status": "production-candidate",
				"notes": [
					"Local analysis summary: JPM is the cleanest setup.",
					"Claude escalation reviewed candidates: one remaining slot.",
				],
				"indicator_snapshots": [{"symbol": "JPM"}, {"symbol": "MSFT"}],
				"triggered": ["JPM"],
				"watching": ["MSFT"],
				"decisions": [{"symbol": "JPM", "action": "buy"}],
				"local_analysis": {
					"summary": "JPM is the cleanest setup.",
					"ranked_candidates": [
						{"symbol": "JPM", "action": "buy", "summary": "Strong trend.", "confidence": 0.83}
					]
				},
				"order_results": [],
				"guardrails": [{"name": "execution_policy", "allowed": True}],
				"guardrail_state": {"claude_calls_today": 1, "trades_today": 0},
			},
		}

		summary_text = format_operator_summary(payload)

		self.assertIn("Local analysis: JPM is the cleanest setup.", summary_text)
		self.assertIn("Top ranked: JPM (buy, confidence 0.83).", summary_text)
		self.assertIn("Claude escalation reviewed the shortlist.", summary_text)

	def test_format_operator_summary_reports_blocked_watch_reasons_when_no_decisions(self) -> None:
		payload = {
			"timestamp": "2026-03-09T19:58:21",
			"summary": {
				"status": "production-candidate",
				"notes": [],
				"indicator_snapshots": [{"symbol": "AAPL"}, {"symbol": "CAT"}, {"symbol": "SPY"}],
				"triggered": [],
				"watching": ["CAT", "AAPL", "SPY"],
				"decisions": [],
				"strategy_evaluation": {
					"candidates": [
						{
							"symbol": "CAT",
							"action": "watch",
							"reason": "Entry not confirmed: RSI is 33.96 versus threshold 30.00.",
							"score": 5.76,
						},
						{
							"symbol": "AAPL",
							"action": "watch",
							"reason": "Entry not confirmed: RSI is 44.70 versus threshold 30.00.",
							"score": 0.5,
						},
						{
							"symbol": "SPY",
							"action": "watch",
							"reason": "Entry not confirmed: MA gap is -0.37% and must remain positive.",
							"score": 0.2,
						},
					],
				},
				"order_results": [],
				"guardrails": [{"name": "execution_policy", "allowed": True}],
				"guardrail_state": {"claude_calls_today": 0, "trades_today": 0},
			},
		}

		summary_text = format_operator_summary(payload)

		self.assertIn("Blocked setups: CAT: RSI is 33.96 versus threshold 30.00.", summary_text)
		self.assertIn("AAPL: RSI is 44.70 versus threshold 30.00.", summary_text)


if __name__ == "__main__":
	unittest.main()