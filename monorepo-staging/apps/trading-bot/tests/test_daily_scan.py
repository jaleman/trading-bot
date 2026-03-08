# pyright: reportMissingImports=false

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_bot.models import (  # noqa: E402
    AccountSnapshot,
    GuardrailState,
    IndicatorSnapshot,
    ScanResult,
    TradeDecision,
)
from trading_bot.runtime_paths import AppPaths  # noqa: E402
from trading_bot.services.daily_scan import run_daily_scan  # noqa: E402


class DailyScanGuardrailTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        app_root = root / "apps" / "trading-bot"
        config_dir = app_root / "config"
        runtime_root = root / "runtime" / "trading-bot"
        logs_dir = runtime_root / "logs"
        database_dir = runtime_root / "database"
        config_dir.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)
        database_dir.mkdir(parents=True, exist_ok=True)

        self.strategy_config = config_dir / "strategy.example.json"
        self.trade_log = logs_dir / "trades.log"
        self.guardrail_state = runtime_root / "guardrail-state.json"
        self.env_file = app_root / ".env"
        self.paths = AppPaths(
            app_root=app_root,
            repo_root=root,
            config_dir=config_dir,
            runtime_root=runtime_root,
            logs_dir=logs_dir,
            database_dir=database_dir,
            trade_log=self.trade_log,
            guardrail_state=self.guardrail_state,
            env_file=self.env_file,
            strategy_config=self.strategy_config,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_strategy(
        self,
        *,
        safe_mode: bool = True,
        paper_enabled: bool = False,
        daily_limit: int = 5,
    ) -> None:
        payload = {
            "watchlist": ["JPM"],
            "max_positions": 4,
            "max_trades_per_day": 2,
            "max_position_size_pct": 25,
            "entry": {"ma_crossover": {"short": 20, "long": 50}, "rsi_threshold": 30},
            "exit": {"profit_target_pct": 10, "stop_loss_pct": 4.5},
            "models": {
                "daily_decision": "claude-sonnet-4-6",
                "monitoring": "qwen2.5:7b",
            },
            "cost_controls": {
                "daily_claude_call_limit": daily_limit,
                "context_reset_after_exchanges": 20,
                "prompt_caching_enabled": True,
            },
            "execution_controls": {
                "safe_mode": safe_mode,
                "paper_trade_execution_enabled": paper_enabled,
                "write_logs_by_default": True,
            },
            "paper_to_live": {
                "min_return_pct": 3.75,
                "evaluation_days": 90,
                "max_consecutive_losses": 2,
            },
        }
        self.strategy_config.write_text(json.dumps(payload, indent=2))

    def write_guardrail_state(self, *, claude_calls_today: int = 0, trades_today: int = 0) -> None:
        state = GuardrailState(
            current_date=date.today().isoformat(),
            claude_calls_today=claude_calls_today,
            trades_today=trades_today,
        )
        self.guardrail_state.write_text(json.dumps({
            "current_date": state.current_date,
            "claude_calls_today": state.claude_calls_today,
            "trades_today": state.trades_today,
        }))

    @patch("trading_bot.services.daily_scan.ensure_runtime_dirs", side_effect=lambda p: p)
    @patch("trading_bot.services.daily_scan.resolve_paths")
    def test_daily_scan_skips_decision_call_when_claude_limit_reached(self, mock_paths: MagicMock, _mock_dirs: MagicMock) -> None:
        self.write_strategy(daily_limit=1)
        self.write_guardrail_state(claude_calls_today=1)
        mock_paths.return_value = self.paths

        fake_market = MagicMock()
        fake_market.get_all_indicators.return_value = [
            IndicatorSnapshot(symbol="JPM", current_price=100, ma_20=101, ma_50=99, rsi=25)
        ]
        fake_prefilter = MagicMock()
        fake_prefilter.classify.return_value = ScanResult(triggered=["JPM"], watching=[], inactive=[], summary="JPM triggered")
        fake_decider = MagicMock()

        with patch("trading_bot.services.daily_scan.AlpacaMarketDataClient", return_value=fake_market), \
             patch("trading_bot.services.daily_scan.OllamaPrefilterClient", return_value=fake_prefilter), \
             patch("trading_bot.services.daily_scan.ClaudeDecisionClient", return_value=fake_decider):
            summary = run_daily_scan(include_prefilter=True, include_decisions=True)

        self.assertEqual(summary.status, "production-candidate-safe-mode")
        self.assertEqual(summary.decisions, [])
        self.assertTrue(any("Claude call guardrail" in note for note in summary.notes))
        fake_decider.decide.assert_not_called()

    @patch("trading_bot.services.daily_scan.ensure_runtime_dirs", side_effect=lambda p: p)
    @patch("trading_bot.services.daily_scan.resolve_paths")
    def test_daily_scan_blocks_paper_trade_execution_in_safe_mode(self, mock_paths: MagicMock, _mock_dirs: MagicMock) -> None:
        self.write_strategy(safe_mode=True, paper_enabled=True)
        self.write_guardrail_state()
        mock_paths.return_value = self.paths

        fake_market = MagicMock()
        fake_market.get_all_indicators.return_value = [
            IndicatorSnapshot(symbol="JPM", current_price=100, ma_20=101, ma_50=99, rsi=25)
        ]
        fake_prefilter = MagicMock()
        fake_prefilter.classify.return_value = ScanResult(triggered=["JPM"], watching=[], inactive=[], summary="JPM triggered")
        fake_decider = MagicMock()
        fake_decider.decide.return_value = [TradeDecision(symbol="JPM", action="buy", reason="ok")]
        fake_broker = MagicMock()
        fake_broker.get_account_balance.return_value = AccountSnapshot(cash=1000, portfolio_value=1000, buying_power=1000)
        fake_broker.get_open_positions.return_value = []

        with patch("trading_bot.services.daily_scan.AlpacaMarketDataClient", return_value=fake_market), \
             patch("trading_bot.services.daily_scan.OllamaPrefilterClient", return_value=fake_prefilter), \
             patch("trading_bot.services.daily_scan.ClaudeDecisionClient", return_value=fake_decider), \
             patch("trading_bot.services.daily_scan.AlpacaBrokerClient", return_value=fake_broker):
            summary = run_daily_scan(
                include_prefilter=True,
                include_decisions=True,
                include_broker_context=True,
                execute_paper_trades=True,
            )

        self.assertEqual(summary.status, "production-candidate-safe-mode")
        self.assertEqual(summary.order_results, [])
        self.assertTrue(any("Execution blocked because safe mode is enabled." in note for note in summary.notes))
        fake_broker.place_paper_trade.assert_not_called()

    @patch("trading_bot.services.daily_scan.ensure_runtime_dirs", side_effect=lambda p: p)
    @patch("trading_bot.services.daily_scan.resolve_paths")
    def test_daily_scan_loads_explicit_env_file_and_reports_strategy_path(self, mock_paths: MagicMock, _mock_dirs: MagicMock) -> None:
        self.write_strategy()
        self.write_guardrail_state()
        self.env_file.write_text("ALPACA_API_KEY=demo-key\n")
        mock_paths.return_value = self.paths

        with patch.dict(os.environ, {}, clear=True):
            summary = run_daily_scan(
                strategy_path=str(self.strategy_config),
                env_file=str(self.env_file),
                write_logs=False,
            )
            loaded_api_key = os.environ.get("ALPACA_API_KEY")

        self.assertEqual(summary.strategy_file, str(self.strategy_config))
        self.assertEqual(summary.status, "production-candidate-safe-mode")
        self.assertEqual(loaded_api_key, "demo-key")
        self.assertTrue(any("Loaded staged env file:" in note for note in summary.notes))


if __name__ == "__main__":
    unittest.main()
