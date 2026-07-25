# pyright: reportMissingImports=false

from __future__ import annotations

import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_bot.persistence.log_maintenance import (  # noqa: E402
    BackupError,
    backup_runtime_logs,
    rotate_log,
    rotate_runtime_logs,
)


@dataclass
class FakePaths:
    logs_dir: Path
    trade_log: Path
    operator_log: Path


class RotationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.logs = Path(self._tmp.name) / "logs"
        self.logs.mkdir(parents=True)
        self.paths = FakePaths(
            logs_dir=self.logs,
            trade_log=self.logs / "trades.log",
            operator_log=self.logs / "operator.log",
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_small_log_is_left_alone(self) -> None:
        self.paths.trade_log.write_text("small", encoding="utf-8")
        self.assertIsNone(rotate_log(self.paths.trade_log, max_bytes=1000))
        self.assertTrue(self.paths.trade_log.exists())

    def test_oversized_log_is_archived_not_deleted(self) -> None:
        self.paths.trade_log.write_text("x" * 500, encoding="utf-8")
        archive = rotate_log(self.paths.trade_log, max_bytes=100)

        self.assertIsNotNone(archive)
        self.assertTrue(archive.exists())
        self.assertEqual(archive.read_text(encoding="utf-8"), "x" * 500)
        self.assertFalse(self.paths.trade_log.exists())

    def test_rotation_never_overwrites_an_existing_archive(self) -> None:
        first = None
        for _ in range(2):
            self.paths.trade_log.write_text("y" * 500, encoding="utf-8")
            archive = rotate_log(self.paths.trade_log, max_bytes=100)
            first = first or archive
        archives = list(self.logs.glob("trades-*.log"))
        self.assertGreaterEqual(len(archives), 1)
        self.assertTrue(all(a.exists() for a in archives))

    def test_jsonl_source_of_truth_is_never_rotated(self) -> None:
        """Splitting the JSONL would orphan history from the read model."""
        jsonl = self.logs / "trades.jsonl"
        jsonl.write_text("z" * 10_000, encoding="utf-8")
        self.paths.trade_log.write_text("x" * 10_000, encoding="utf-8")

        rotate_runtime_logs(paths=self.paths, max_bytes=100)

        self.assertTrue(jsonl.exists())
        self.assertEqual(len(jsonl.read_text(encoding="utf-8")), 10_000)
        self.assertEqual(len(list(self.logs.glob("trades-*.jsonl"))), 0)


class BackupTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.logs = root / "logs"
        self.logs.mkdir(parents=True)
        self.dest = root / "backup"
        self.paths = FakePaths(
            logs_dir=self.logs,
            trade_log=self.logs / "trades.log",
            operator_log=self.logs / "operator.log",
        )
        (self.logs / "trades.jsonl").write_text('{"a": 1}\n', encoding="utf-8")
        self.paths.trade_log.write_text("log line\n", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_copies_logs_to_destination(self) -> None:
        results = backup_runtime_logs(self.dest, paths=self.paths)

        self.assertTrue((self.dest / "trades.jsonl").exists())
        self.assertTrue((self.dest / "trades.log").exists())
        self.assertIn("copied", results["trades.jsonl"])
        self.assertIn("not present", results["operator.log"])

    def test_refuses_to_overwrite_larger_backup_with_smaller_source(self) -> None:
        """A locally truncated log must not destroy a good backup."""
        backup_runtime_logs(self.dest, paths=self.paths)
        (self.dest / "trades.jsonl").write_text('{"a": 1}\n{"b": 2}\n{"c": 3}\n', encoding="utf-8")
        good_size = (self.dest / "trades.jsonl").stat().st_size

        results = backup_runtime_logs(self.dest, paths=self.paths)

        self.assertIn("REFUSED", results["trades.jsonl"])
        self.assertEqual((self.dest / "trades.jsonl").stat().st_size, good_size)

    def test_force_overrides_the_size_guard(self) -> None:
        backup_runtime_logs(self.dest, paths=self.paths)
        (self.dest / "trades.jsonl").write_text("x" * 999, encoding="utf-8")

        results = backup_runtime_logs(self.dest, paths=self.paths, force=True)

        self.assertIn("copied", results["trades.jsonl"])

    def test_growing_source_is_backed_up_normally(self) -> None:
        backup_runtime_logs(self.dest, paths=self.paths)
        (self.logs / "trades.jsonl").write_text('{"a":1}\n{"b":2}\n', encoding="utf-8")

        results = backup_runtime_logs(self.dest, paths=self.paths)

        self.assertIn("copied", results["trades.jsonl"])

    def test_rotated_archives_are_backed_up_too(self) -> None:
        (self.logs / "trades-20260301-120000.log").write_text("old\n", encoding="utf-8")
        results = backup_runtime_logs(self.dest, paths=self.paths)

        self.assertTrue((self.dest / "trades-20260301-120000.log").exists())
        self.assertIn("archived", results["trades-20260301-120000.log"])

    def test_unwritable_destination_raises(self) -> None:
        with self.assertRaises(BackupError):
            backup_runtime_logs("/proc/nonexistent/backup", paths=self.paths)


if __name__ == "__main__":
    unittest.main()
