"""Report when the daily scan did *not* run.

Every other safeguard in this system reports what happened. Nothing reported
what failed to happen, and that is the actual defect behind the 2026-04-24 to
2026-07-25 silence: the scan simply stopped, and because a stopped scan writes
no logs, raises no errors and sends no messages, absence looked identical to a
quiet market.

A watchdog cannot live inside the thing it watches. This runs as its own
scheduled job so that a failure of the scan -- or of whatever schedules it --
still leaves something able to speak up.

Deliberately dependency-light: it reads the scan log and shells out to send a
message. It does not import the scan, the broker, or any model.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# Weekday scans only; a quiet Saturday is not a fault.
TRADING_WEEKDAYS = {0, 1, 2, 3, 4}

# The scan runs at 09:35. Today only counts as missed once this hour passes,
# which absorbs a late start without crying wolf.
DEFAULT_SCAN_DEADLINE_HOUR = 11.0

# One missed weekday is worth knowing about. Waiting longer to "avoid noise"
# is how three months went by.
DEFAULT_MISSED_WEEKDAYS_ALLOWED = 0


def last_scan_time(jsonl_path: Path) -> datetime | None:
    """Timestamp of the most recent completed scan, or None if never."""
    if not jsonl_path.exists():
        return None

    latest: datetime | None = None
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            stamp = json.loads(line).get("timestamp")
            parsed = datetime.fromisoformat(stamp) if stamp else None
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
        if parsed and (latest is None or parsed > latest):
            latest = parsed
    return latest


def missed_weekdays(
    last: datetime,
    now: datetime,
    scan_deadline_hour: float = DEFAULT_SCAN_DEADLINE_HOUR,
) -> int:
    """Count weekdays since `last` on which a scan should have run but didn't.

    Counting missed *weekdays* rather than asking "is today a weekday" matters.
    An earlier version did the latter and reported a 92-day-old scan as healthy
    purely because the check happened on a Saturday — it would have stayed
    silent through the entire outage it exists to catch.
    """
    missed = 0
    day = last.date() + timedelta(days=1)
    while day <= now.date():
        if day.weekday() in TRADING_WEEKDAYS:
            if day < now.date():
                missed += 1
            elif now.hour + now.minute / 60 >= scan_deadline_hour:
                # Today counts only once the scan window has clearly passed.
                missed += 1
        day += timedelta(days=1)
    return missed


def evaluate(
    jsonl_path: Path,
    now: datetime | None = None,
    missed_weekdays_allowed: int = DEFAULT_MISSED_WEEKDAYS_ALLOWED,
    scan_deadline_hour: float = DEFAULT_SCAN_DEADLINE_HOUR,
) -> tuple[bool, str]:
    """Return (is_stale, human-readable explanation)."""
    now = now or datetime.now()
    latest = last_scan_time(jsonl_path)

    if latest is None:
        return True, "No scan has ever been recorded."

    stamp = latest.strftime("%Y-%m-%d %H:%M")
    age_days = (now - latest).days
    missed = missed_weekdays(latest, now, scan_deadline_hour)

    if missed <= missed_weekdays_allowed:
        return False, (
            f"Last scan {stamp} ({age_days}d ago), {missed} weekday(s) missed — healthy."
        )

    return True, (
        f"No scan since {stamp} — {missed} trading weekday(s) missed "
        f"({age_days} calendar days). The scheduler, the Mac, or the scan "
        f"itself has stopped."
    )


def send_alert(message: str, recipient: str) -> bool:
    """Deliver via ZeroClaw's agent-free send path. Best-effort."""
    try:
        result = subprocess.run(
            ["zeroclaw", "channel", "send", message,
             "--channel-id", "telegram", "--recipient", recipient],
            capture_output=True, text=True, timeout=60,
        )
        return result.returncode == 0
    except Exception:
        return False


def main(argv: list[str] | None = None) -> int:
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Alert when the daily scan has not run.")
    parser.add_argument("--missed-weekdays-allowed", type=int,
                        default=DEFAULT_MISSED_WEEKDAYS_ALLOWED)
    parser.add_argument("--scan-deadline-hour", type=float,
                        default=DEFAULT_SCAN_DEADLINE_HOUR)
    parser.add_argument("--check-only", action="store_true", help="Report without sending.")
    args = parser.parse_args(argv)

    from trading_bot.env_loader import load_runtime_env
    from trading_bot.runtime_paths import ensure_runtime_dirs, resolve_paths

    paths = ensure_runtime_dirs(resolve_paths())
    load_runtime_env(paths.env_file)

    jsonl = paths.trade_log.with_suffix(".jsonl")
    is_stale, message = evaluate(
        jsonl,
        missed_weekdays_allowed=args.missed_weekdays_allowed,
        scan_deadline_hour=args.scan_deadline_hour,
    )
    print(message)

    if not is_stale:
        return 0
    if args.check_only:
        # Non-zero even when only reporting, so the exit status is usable in
        # a shell check without parsing the message.
        return 1

    recipient = os.getenv("TRADING_BOT_TELEGRAM_RECIPIENT", "").strip()
    if not recipient:
        print("No TRADING_BOT_TELEGRAM_RECIPIENT configured; alert not sent.")
        return 1

    if send_alert(f"trading-bot: SCAN MISSING\n\n{message}", recipient):
        print("Alert sent.")
    else:
        print("Alert delivery FAILED.")
    # Non-zero so the scheduler also records the fault.
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
