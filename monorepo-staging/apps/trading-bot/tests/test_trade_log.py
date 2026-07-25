# pyright: reportMissingImports=false

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_bot.persistence.trade_log import TradeLogger, new_run_id  # noqa: E402


class TradeLoggerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.log_path = Path(self._tmp.name) / "logs" / "trades.log"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_appends_rather_than_rewriting_history(self) -> None:
        """Regression: the old implementation rewrote the whole file per line."""
        TradeLogger(self.log_path, run_id="run-a").log_message("first")
        TradeLogger(self.log_path, run_id="run-b").log_message("second")

        lines = self.log_path.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("first", lines[0])
        self.assertIn("second", lines[1])

    def test_preexisting_history_is_never_truncated(self) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.write_text("PRIOR HISTORY\n", encoding="utf-8")

        TradeLogger(self.log_path, run_id="run-a").log_message("new entry")

        content = self.log_path.read_text(encoding="utf-8")
        self.assertIn("PRIOR HISTORY", content)
        self.assertIn("new entry", content)

    def test_run_id_is_stamped_on_every_line(self) -> None:
        logger = TradeLogger(self.log_path, run_id="run-xyz")
        logger.log_messages(["alpha", "beta"])

        for line in self.log_path.read_text(encoding="utf-8").strip().splitlines():
            self.assertIn("[run-xyz]", line)

    def test_run_ids_are_unique(self) -> None:
        self.assertNotEqual(new_run_id(), new_run_id())

    def test_log_exception_records_type_message_and_traceback(self) -> None:
        logger = TradeLogger(self.log_path, run_id="run-a")
        try:
            raise ValueError("connection reset")
        except ValueError as exc:
            logger.log_exception(exc, context="Daily scan aborted")

        content = self.log_path.read_text(encoding="utf-8")
        self.assertIn("Daily scan aborted", content)
        self.assertIn("UNHANDLED ValueError: connection reset", content)
        self.assertIn("Traceback", content)
        self.assertIn("raise ValueError", content)

    def test_summary_json_carries_matching_run_id(self) -> None:
        class FakeSummary:
            __dataclass_fields__: dict = {}

        logger = TradeLogger(self.log_path, run_id="run-corr")
        # asdict() requires a real dataclass; use the real path via a stub.
        from dataclasses import dataclass

        @dataclass
        class Summary:
            status: str = "ok"

        logger.log_summary_json(Summary())

        payload = json.loads(
            self.log_path.with_suffix(".jsonl").read_text(encoding="utf-8").strip()
        )
        self.assertEqual(payload["run_id"], "run-corr")
        self.assertEqual(payload["summary"]["status"], "ok")

    def test_log_survives_process_being_killed_mid_run(self) -> None:
        """A hard kill must leave the lines written so far on disk.

        This is the failure the previous design could not survive: everything
        was buffered and written only after a successful completion.
        """
        script = textwrap.dedent(f"""
            import sys, os, signal
            sys.path.insert(0, {str(Path(__file__).resolve().parents[1] / "src")!r})
            from trading_bot.persistence.trade_log import TradeLogger
            logger = TradeLogger({str(self.log_path)!r}, run_id="run-killed")
            logger.log_message("=== Staged daily scan started ===")
            logger.log_message("work in progress")
            os.kill(os.getpid(), signal.SIGKILL)
        """)
        result = subprocess.run([sys.executable, "-c", script], capture_output=True)

        self.assertNotEqual(result.returncode, 0, "process should have been killed")
        content = self.log_path.read_text(encoding="utf-8")
        self.assertIn("=== Staged daily scan started ===", content)
        self.assertIn("work in progress", content)
        self.assertIn("[run-killed]", content)


if __name__ == "__main__":
    unittest.main()
