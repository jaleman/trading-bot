# pyright: reportMissingImports=false

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_bot.services.watchdog import (  # noqa: E402
    evaluate,
    last_scan_time,
    missed_weekdays,
)

# A Wednesday, for weekday-sensitive assertions.
WEDNESDAY = datetime(2026, 7, 22, 11, 0)
SATURDAY = datetime(2026, 7, 25, 11, 0)


def write_log(path: Path, timestamps: list[datetime]) -> None:
    path.write_text(
        "\n".join(json.dumps({"timestamp": t.isoformat(), "summary": {}}) for t in timestamps) + "\n",
        encoding="utf-8",
    )


class LastScanTimeTests(unittest.TestCase):
    def test_returns_the_most_recent_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "trades.jsonl"
            write_log(p, [WEDNESDAY - timedelta(days=3), WEDNESDAY - timedelta(days=1)])
            self.assertEqual(last_scan_time(p), WEDNESDAY - timedelta(days=1))

    def test_missing_file_is_none_not_an_error(self) -> None:
        self.assertIsNone(last_scan_time(Path("/nonexistent/trades.jsonl")))

    def test_malformed_lines_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "trades.jsonl"
            p.write_text(
                "not json\n" + json.dumps({"timestamp": WEDNESDAY.isoformat()}) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(last_scan_time(p), WEDNESDAY)


class EvaluateTests(unittest.TestCase):
    def _log(self, tmp: str, when: datetime) -> Path:
        p = Path(tmp) / "trades.jsonl"
        write_log(p, [when])
        return p

    def test_recent_scan_is_healthy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = self._log(tmp, WEDNESDAY - timedelta(hours=2))
            stale, msg = evaluate(p, now=WEDNESDAY)
        self.assertFalse(stale)
        self.assertIn("healthy", msg)

    def test_missed_weekday_scan_is_stale(self) -> None:
        """The failure this exists for: scan stopped, nothing said so."""
        with tempfile.TemporaryDirectory() as tmp:
            p = self._log(tmp, WEDNESDAY - timedelta(days=4))
            stale, msg = evaluate(p, now=WEDNESDAY)
        self.assertTrue(stale)
        self.assertIn("No scan since", msg)

    def test_three_month_gap_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = self._log(tmp, WEDNESDAY - timedelta(days=92))
            stale, _ = evaluate(p, now=WEDNESDAY)
        self.assertTrue(stale)

    def test_friday_scan_checked_on_saturday_does_not_alarm(self) -> None:
        """A quiet Saturday after a good Friday run is not a fault."""
        with tempfile.TemporaryDirectory() as tmp:
            p = self._log(tmp, SATURDAY - timedelta(days=1))  # Friday
            stale, msg = evaluate(p, now=SATURDAY)
        self.assertFalse(stale)
        self.assertIn("healthy", msg)

    def test_long_outage_alarms_even_when_checked_on_a_weekend(self) -> None:
        """Regression: the original logic reported a 92-day gap as healthy
        purely because the check ran on a Saturday."""
        with tempfile.TemporaryDirectory() as tmp:
            p = self._log(tmp, SATURDAY - timedelta(days=92))
            stale, msg = evaluate(p, now=SATURDAY)
        self.assertTrue(stale, "a three-month gap must alarm on any day")
        self.assertIn("weekday(s) missed", msg)

    def test_never_scanned_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "trades.jsonl"
            stale, msg = evaluate(p, now=WEDNESDAY)
        self.assertTrue(stale)
        self.assertIn("ever been recorded", msg.lower())

    def test_yesterday_scan_is_healthy_before_todays_deadline(self) -> None:
        """At 08:00 today's 09:35 scan is not yet late."""
        with tempfile.TemporaryDirectory() as tmp:
            p = self._log(tmp, WEDNESDAY - timedelta(days=1))
            stale, _ = evaluate(p, now=WEDNESDAY.replace(hour=8))
        self.assertFalse(stale)

    def test_yesterday_scan_is_stale_after_todays_deadline(self) -> None:
        """By midday, a scan due at 09:35 that never ran is a fault."""
        with tempfile.TemporaryDirectory() as tmp:
            p = self._log(tmp, WEDNESDAY - timedelta(days=1))
            stale, _ = evaluate(p, now=WEDNESDAY.replace(hour=12))
        self.assertTrue(stale)


class MissedWeekdayCountingTests(unittest.TestCase):
    def test_same_day_scan_counts_nothing(self) -> None:
        self.assertEqual(missed_weekdays(WEDNESDAY, WEDNESDAY.replace(hour=15)), 0)

    def test_today_not_counted_before_the_deadline(self) -> None:
        """A scan due at 09:35 is not 'missed' when checked at 08:00."""
        yesterday = WEDNESDAY - timedelta(days=1)
        self.assertEqual(missed_weekdays(yesterday, WEDNESDAY.replace(hour=8)), 0)

    def test_today_counted_after_the_deadline(self) -> None:
        yesterday = WEDNESDAY - timedelta(days=1)
        self.assertEqual(missed_weekdays(yesterday, WEDNESDAY.replace(hour=12)), 1)

    def test_weekend_days_are_not_counted(self) -> None:
        friday = datetime(2026, 7, 24, 9, 40)
        monday = datetime(2026, 7, 27, 12, 0)
        # Sat and Sun skipped; only Monday counts.
        self.assertEqual(missed_weekdays(friday, monday), 1)

if __name__ == "__main__":
    unittest.main()
