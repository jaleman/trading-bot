# pyright: reportMissingImports=false

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_bot.integrations.local_analysis import OllamaLocalAnalysisClient  # noqa: E402
from trading_bot.models import RiskConfig, StrategyCandidate, StrategyConfig, UniverseConfig  # noqa: E402
from trading_bot.models import CostControlsConfig, EntryConfig, ExecutionControlsConfig, ExitConfig, ModelsConfig, ModelRoutingConfig, MovingAverageConfig, PaperToLiveConfig  # noqa: E402


class LocalAnalysisTests(unittest.TestCase):
    def test_fallback_ranked_candidates_prioritizes_buys_then_score(self) -> None:
        ranked = OllamaLocalAnalysisClient._fallback_ranked_candidates(
            [
                StrategyCandidate(symbol="MSFT", action="watch", reason="watch", score=9.0),
                StrategyCandidate(symbol="JPM", action="buy", reason="buy", score=5.0),
                StrategyCandidate(symbol="UPS", action="buy", reason="stronger buy", score=8.0),
            ]
        )

        self.assertEqual([item.symbol for item in ranked[:3]], ["UPS", "JPM", "MSFT"])
        self.assertEqual(ranked[0].action, "buy")
        self.assertGreater(ranked[0].confidence, ranked[1].confidence)

    @patch("trading_bot.integrations.local_analysis.requests.post")
    def test_analyze_tolerates_ranked_candidates_missing_summary(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": json.dumps(
                {
                    "summary": "UPS is strongest.",
                    "ranked_candidates": [
                        {"symbol": "UPS", "action": "buy", "confidence": 0.82}
                    ],
                    "escalate_to_claude": False,
                    "escalation_reason": "",
                }
            )
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        client = OllamaLocalAnalysisClient(model="qwen2.5:7b")
        result = client.analyze(
            strategy=StrategyConfig(
                watchlist=["UPS"],
                max_positions=4,
                max_trades_per_day=2,
                max_position_size_pct=25,
                entry=EntryConfig(MovingAverageConfig(20, 50), 30, 4.5),
                exit=ExitConfig(10, 4.5),
                models=ModelsConfig("claude-sonnet-4-6", "qwen2.5:7b"),
                cost_controls=CostControlsConfig(5, 20, True),
                execution_controls=ExecutionControlsConfig(True, False, True),
                paper_to_live=PaperToLiveConfig(3.75, 90, 2),
                universe=UniverseConfig(symbols=["UPS"]),
                risk=RiskConfig(4, 2, 25),
                model_routing=ModelRoutingConfig(),
            ),
            candidates=[StrategyCandidate(symbol="UPS", action="buy", reason="Strong setup", score=8.0)],
        )

        self.assertEqual(result.summary, "UPS is strongest.")
        self.assertEqual(result.ranked_candidates[0].symbol, "UPS")
        self.assertEqual(result.ranked_candidates[0].summary, "No local-analysis summary provided.")

    @patch("trading_bot.integrations.local_analysis.requests.post")
    def test_analyze_preserves_deterministic_candidate_action(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": json.dumps(
                {
                    "summary": "BRK.B and COST look strongest.",
                    "ranked_candidates": [
                        {"symbol": "BRK.B", "action": "watch", "summary": "Needs more confirmation.", "confidence": 0.8},
                        {"symbol": "COST", "action": "buy", "summary": "Confirmed setup.", "confidence": 0.95},
                    ],
                    "escalate_to_claude": False,
                    "escalation_reason": "",
                }
            )
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        client = OllamaLocalAnalysisClient(model="qwen2.5:7b")
        result = client.analyze(
            strategy=StrategyConfig(
                watchlist=["BRK.B", "COST"],
                max_positions=4,
                max_trades_per_day=2,
                max_position_size_pct=25,
                entry=EntryConfig(MovingAverageConfig(20, 50), 30, 40, 4.5),
                exit=ExitConfig(10, 4.5),
                models=ModelsConfig("claude-sonnet-4-6", "qwen2.5:7b"),
                cost_controls=CostControlsConfig(5, 20, True),
                execution_controls=ExecutionControlsConfig(True, False, True),
                paper_to_live=PaperToLiveConfig(3.75, 90, 2),
                universe=UniverseConfig(symbols=["BRK.B", "COST"]),
                risk=RiskConfig(4, 2, 25),
                model_routing=ModelRoutingConfig(),
            ),
            candidates=[
                StrategyCandidate(symbol="BRK.B", action="buy", reason="Confirmed setup", score=5.0),
                StrategyCandidate(symbol="COST", action="buy", reason="Confirmed setup", score=8.0),
            ],
        )

        self.assertEqual(result.ranked_candidates[0].symbol, "BRK.B")
        self.assertEqual(result.ranked_candidates[0].action, "buy")
        self.assertEqual(result.ranked_candidates[1].action, "buy")


if __name__ == "__main__":
    unittest.main()