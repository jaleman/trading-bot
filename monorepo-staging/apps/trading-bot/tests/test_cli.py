# pyright: reportMissingImports=false

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_bot.cli import main  # noqa: E402


class CliTests(unittest.TestCase):
    @patch("builtins.print")
    @patch("trading_bot.cli.run_daily_scan")
    def test_rehearsal_mode_enables_supervised_runtime_layers(
        self,
        mock_run_daily_scan: MagicMock,
        _mock_print: MagicMock,
    ) -> None:
        fake_summary = MagicMock()
        fake_summary.to_dict.return_value = {"status": "production-candidate-safe-mode"}
        mock_run_daily_scan.return_value = fake_summary

        main(
            [
                "--config",
                "/tmp/strategy.local.json",
                "--env-file",
                "/tmp/.env",
                "--rehearsal",
                "--no-write-logs",
            ]
        )

        mock_run_daily_scan.assert_called_once_with(
            strategy_path="/tmp/strategy.local.json",
            env_file="/tmp/.env",
            include_market_data=True,
            include_prefilter=True,
            include_decisions=True,
            include_broker_context=True,
            execute_paper_trades=False,
            write_logs=False,
        )


if __name__ == "__main__":
    unittest.main()