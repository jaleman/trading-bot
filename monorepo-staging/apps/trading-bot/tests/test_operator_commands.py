# pyright: reportMissingImports=false

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_bot.integrations.broker import BrokerError  # noqa: E402
from trading_bot.models import IndicatorSnapshot  # noqa: E402
from trading_bot.models import AccountSnapshot, OrderResult, PositionSnapshot  # noqa: E402
from trading_bot.operator_commands import format_balance, format_holdings, format_latest_summary, format_pending_orders, format_runtime_status, format_stock_info, format_supported_commands  # noqa: E402
from trading_bot.runtime_paths import AppPaths  # noqa: E402


class OperatorCommandsTests(unittest.TestCase):
    def test_format_supported_commands_lists_supported_surface(self) -> None:
        output = format_supported_commands()

        self.assertIn("Supported commands:", output)
        self.assertIn("/bot list - list supported commands", output)
        self.assertIn("/bot holdings - open position breakdown", output)
        self.assertIn("/bot info <TICKER> - market snapshot for one ticker", output)
        self.assertIn("bot list | bot summary | bot pending | bot status | bot balance | bot holdings | bot info <TICKER> | bot sync | bot restart - plain-text fallback inputs", output)
        self.assertIn("/Summary, /Pending, /Status, /Balance, /Holdings, /Info, /Sync, /Restart - compatibility aliases", output)

    def test_format_latest_summary_returns_today_only(self) -> None:
        yesterday = (date.today() - timedelta(days=1)).isoformat() + "T09:35:00"
        with patch("trading_bot.operator_commands.load_latest_summary_payload") as mock_loader:
            mock_loader.return_value = {
                "timestamp": yesterday,
                "summary": {"status": "production-candidate", "order_results": []},
            }

            output = format_latest_summary()

        self.assertEqual(output, "No run summary recorded for today.")

    @patch("trading_bot.operator_commands.AlpacaBrokerClient")
    @patch("trading_bot.operator_commands.load_runtime_env")
    def test_format_pending_orders_reports_open_orders(
        self,
        _mock_load_runtime_env: MagicMock,
        mock_broker_client: MagicMock,
    ) -> None:
        mock_broker = mock_broker_client.return_value
        mock_broker.get_open_orders.return_value = [
            OrderResult(
                id="83d6412c-bb3f-48ed-ab4b-9752f35324ce",
                symbol="BRK.B",
                qty=50.0,
                side="OrderSide.BUY",
                status="OrderStatus.ACCEPTED",
            )
        ]

        output = format_pending_orders(limit=5)

        self.assertEqual(
            output,
            "Pending orders: 1.\n"
            "BRK.B buy qty=50 status=accepted id=83d6412c-bb3f-48ed-ab4b-9752f35324ce",
        )
        mock_broker.get_open_orders.assert_called_once_with(limit=5)

    @patch("trading_bot.operator_commands.AlpacaBrokerClient")
    @patch("trading_bot.operator_commands.load_runtime_env")
    def test_format_pending_orders_reports_none(
        self,
        _mock_load_runtime_env: MagicMock,
        mock_broker_client: MagicMock,
    ) -> None:
        mock_broker_client.return_value.get_open_orders.return_value = []

        output = format_pending_orders()

        self.assertEqual(output, "No pending orders.")

    @patch("trading_bot.operator_commands.AlpacaBrokerClient")
    @patch("trading_bot.operator_commands.load_runtime_env")
    @patch("trading_bot.operator_commands.resolve_paths")
    def test_format_runtime_status_reports_artifacts_and_broker_connectivity(
        self,
        mock_resolve_paths: MagicMock,
        _mock_load_runtime_env: MagicMock,
        mock_broker_client: MagicMock,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime_root = root / "runtime" / "trading-bot"
            logs_dir = runtime_root / "logs"
            database_dir = runtime_root / "database"
            logs_dir.mkdir(parents=True)
            database_dir.mkdir(parents=True)

            trade_log = logs_dir / "trades.log"
            trade_log.write_text("summary available\n", encoding="utf-8")
            trade_log.with_suffix(".jsonl").write_text(
                '{"timestamp":"2026-03-10T09:35:00","summary":{"status":"production-candidate","order_results":[{"id":"1"}]}}\n',
                encoding="utf-8",
            )
            guardrail_state = runtime_root / "guardrail-state.json"
            guardrail_state.write_text(
                '{"current_date":"2026-03-10","claude_calls_today":2,"trades_today":1}',
                encoding="utf-8",
            )

            mock_resolve_paths.return_value = AppPaths(
                app_root=root / "apps" / "trading-bot",
                repo_root=root,
                config_dir=root / "apps" / "trading-bot" / "config",
                runtime_root=runtime_root,
                logs_dir=logs_dir,
                database_dir=database_dir,
                trade_log=trade_log,
                guardrail_state=guardrail_state,
                env_file=root / "apps" / "trading-bot" / ".env",
                strategy_config=root / "apps" / "trading-bot" / "config" / "strategy.local.json",
            )

            mock_broker = mock_broker_client.return_value
            mock_broker.get_account_balance.return_value = AccountSnapshot(
                cash=10000.0,
                portfolio_value=10000.0,
                buying_power=20000.0,
            )

            output = format_runtime_status()

        self.assertIn(
            "Runtime status: latest summary at 2026-03-10T09:35:00; status=production-candidate; paper_orders=1.",
            output,
        )
        self.assertIn("Artifacts: trades.log=yes trades.jsonl=yes guardrail-state=yes.", output)
        self.assertIn("Guardrails: date=2026-03-10 claude_calls_today=2 trades_today=1.", output)
        self.assertIn("Broker: connected.", output)

    @patch("trading_bot.operator_commands.AlpacaBrokerClient")
    @patch("trading_bot.operator_commands.load_runtime_env")
    @patch("trading_bot.operator_commands.resolve_paths")
    def test_format_runtime_status_handles_missing_summary_and_broker_failure(
        self,
        mock_resolve_paths: MagicMock,
        _mock_load_runtime_env: MagicMock,
        mock_broker_client: MagicMock,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime_root = root / "runtime" / "trading-bot"
            logs_dir = runtime_root / "logs"
            database_dir = runtime_root / "database"
            logs_dir.mkdir(parents=True)
            database_dir.mkdir(parents=True)

            mock_resolve_paths.return_value = AppPaths(
                app_root=root / "apps" / "trading-bot",
                repo_root=root,
                config_dir=root / "apps" / "trading-bot" / "config",
                runtime_root=runtime_root,
                logs_dir=logs_dir,
                database_dir=database_dir,
                trade_log=logs_dir / "trades.log",
                guardrail_state=runtime_root / "guardrail-state.json",
                env_file=root / "apps" / "trading-bot" / ".env",
                strategy_config=root / "apps" / "trading-bot" / "config" / "strategy.local.json",
            )
            mock_broker_client.side_effect = BrokerError("Missing Alpaca broker credentials.")

            output = format_runtime_status()

        self.assertIn("Runtime status: no summary log found.", output)
        self.assertIn("Artifacts: trades.log=no trades.jsonl=no guardrail-state=no.", output)
        self.assertIn("Guardrails: unavailable.", output)
        self.assertIn("Broker: unavailable (Missing Alpaca broker credentials.).", output)

    @patch("trading_bot.operator_commands.AlpacaBrokerClient")
    @patch("trading_bot.operator_commands.load_runtime_env")
    def test_format_balance_reports_cash_and_holdings(
        self,
        _mock_load_runtime_env: MagicMock,
        mock_broker_client: MagicMock,
    ) -> None:
        mock_broker = mock_broker_client.return_value
        mock_broker.get_account_balance.return_value = AccountSnapshot(
            cash=10000.0,
            portfolio_value=15500.0,
            buying_power=20000.0,
        )
        mock_broker.get_open_positions.return_value = [
            PositionSnapshot(
                symbol="COST",
                qty=5.0,
                avg_entry_price=1000.0,
                current_price=1100.0,
                unrealized_pl=500.0,
                unrealized_plpc=0.10,
            )
        ]

        output = format_balance()

        self.assertIn(
            "Balance: cash=$10,000.00 holdings=$5,500.00 portfolio=$15,500.00 buying_power=$20,000.00.",
            output,
        )
        self.assertIn("Open positions: 1.", output)

    @patch("trading_bot.operator_commands.AlpacaBrokerClient")
    @patch("trading_bot.operator_commands.load_runtime_env")
    def test_format_holdings_reports_position_breakdown(
        self,
        _mock_load_runtime_env: MagicMock,
        mock_broker_client: MagicMock,
    ) -> None:
        mock_broker = mock_broker_client.return_value
        mock_broker.get_open_positions.return_value = [
            PositionSnapshot(
                symbol="BRK.B",
                qty=50.0,
                avg_entry_price=500.0,
                current_price=505.25,
                unrealized_pl=262.5,
                unrealized_plpc=0.0105,
            ),
            PositionSnapshot(
                symbol="COST",
                qty=24.0,
                avg_entry_price=980.0,
                current_price=981.5,
                unrealized_pl=36.0,
                unrealized_plpc=0.00153,
            ),
        ]

        output = format_holdings()

        self.assertIn("Holdings: 2 open position(s).", output)
        self.assertIn(
            "BRK.B qty=50 market_value=$25,262.50 avg_entry=$500.00 current=$505.25 unrealized_pl=$262.50 unrealized_plpc=1.05%",
            output,
        )
        self.assertIn(
            "COST qty=24 market_value=$23,556.00 avg_entry=$980.00 current=$981.50 unrealized_pl=$36.00 unrealized_plpc=0.15%",
            output,
        )

    @patch("trading_bot.operator_commands.AlpacaBrokerClient")
    @patch("trading_bot.operator_commands.load_runtime_env")
    def test_format_holdings_reports_none(
        self,
        _mock_load_runtime_env: MagicMock,
        mock_broker_client: MagicMock,
    ) -> None:
        mock_broker_client.return_value.get_open_positions.return_value = []

        output = format_holdings()

        self.assertEqual(output, "No open holdings.")

    @patch("trading_bot.operator_commands.AlpacaBrokerClient")
    @patch("trading_bot.operator_commands.AlpacaMarketDataClient")
    @patch("trading_bot.operator_commands.load_runtime_env")
    def test_format_stock_info_reports_indicator_snapshot(
        self,
        _mock_load_runtime_env: MagicMock,
        mock_market_data_client: MagicMock,
        mock_market_data_broker: MagicMock,
    ) -> None:
        mock_market_data_broker.return_value.get_asset_name.return_value = "Apple Inc."
        mock_client = mock_market_data_client.return_value
        mock_client.calculate_indicators.return_value = IndicatorSnapshot(
            symbol="AAPL",
            current_price=215.25,
            ma_20=210.10,
            ma_50=205.55,
            rsi=48.33,
            recent_return_5d=2.50,
            recent_return_20d=5.75,
            volatility_20d=1.80,
            avg_dollar_volume_20d=125000000.0,
            distance_to_ma_20_pct=2.45,
            distance_to_ma_50_pct=4.72,
        )

        output = format_stock_info("aapl")

        self.assertIn("AAPL (Apple Inc.): price=$215.25 rsi=48.33.", output)
        self.assertIn("Trend: ma20=$210.10 ma50=$205.55.", output)
        self.assertIn("Returns: 5d=2.50% 20d=5.75% volatility20d=1.80%.", output)


if __name__ == "__main__":
    unittest.main()