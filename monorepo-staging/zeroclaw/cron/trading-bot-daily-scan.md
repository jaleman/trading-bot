# Daily scan job

Repository-managed definition of the scheduled trading scan. Applied with
`scripts/sync_zeroclaw_config.sh --with-cron`.

## The job

```
zeroclaw cron add '35 9 * * 1-5' \
  '<REPO_ROOT>/monorepo-staging/scripts/run_trading_bot_daily.sh' \
  --agent tradingbot \
  --tz America/Detroit
```

Weekdays at 09:35 America/Detroit, five minutes after the US market opens.

`run_trading_bot_daily.sh` is the complete flow: run the scan, then report
the outcome to Telegram via `zeroclaw channel send`. On failure it sends the
error and exits non-zero, so the scheduler records a failure too. **Silence is
never the success signal** — a scan that dies says so.

Verified 2026-07-25: `channel send` delivers in ~1s adding zero runtime-trace
events and no model calls, so reporting has no agent in the path. Both the
success and failure paths were exercised with `--dry-run`.

## Why the command is bare

The command is a plain script path with **no `--agent` reasoning step in the
execution path**. ZeroClaw runs it directly.

This is deliberate, and it is the correction for the failure that made this
project dormant from 2026-04-24 to 2026-07-25. The previous OpenClaw job
carried a natural-language instruction as its payload:

> "Run the staged monorepo trading bot scan with ...run_trading_bot_rehearsal.sh
> After it completes, run ...print_trading_bot_operator_summary.sh and send
> that summary to Telegram."

combined with `"bestEffort": true` on delivery. Both execution and reporting
therefore depended on a model interpreting prose correctly every single day,
and a delivery failure was tolerated silently. Nothing ever reported that the
job had stopped.

Here the schedule is deterministic, the daemon is a launchd service that
restarts after a crash, and `zeroclaw doctor` reports scheduler and heartbeat
freshness so staleness is observable rather than invisible.

## Reporting

Operator summaries are delivered by the Telegram channel once it is
configured (`zeroclaw channel`), routed at
`run_trading_bot_telegram_command.sh`. Until then the scan writes its record
to `runtime/trading-bot/logs/` as usual and reporting is pull-based via
`/bot` equivalents run locally.

## Companion job: daily off-machine backup

Decided 2026-07-25. Once daily scans resume, `trades.jsonl` grows every day
but the Google Drive copy only updates when run by hand, so the only
off-machine copy of the 90-day gate evidence silently drifts behind. A second
scheduled job removes that failure mode:

```
zeroclaw cron add '15 10 * * 1-5' \
  '<REPO_ROOT>/monorepo-staging/scripts/run_trading_bot_log_maintenance.sh backup /Users/labanlaro/Library/CloudStorage/GoogleDrive-whatiskali@gmail.com/My Drive/trading-bot-backup' \
  --agent tradingbot \
  --tz America/Detroit
```

Runs at 10:15, after the 09:35 scan has completed. This is a local file copy
into a synced folder — Drive handles the upload — so it introduces no new
outbound path. The backup's size guard still refuses to overwrite a larger
backup with a smaller source, so a corrupted local log cannot destroy the
good copy.

The script must be added to `allowed_commands` in the risk profile before
this job can be scheduled.

## Status

**NOT YET ACTIVE.** Deliberately not scheduled until the guardrails drift
audit (`docs/Security.md` vs `services/guardrails.py`) has been completed —
that audit has not been re-run since the 2026-03-09 refactor, and it is the
last unverified safety claim before paper trading resumes.

The first active run will close PFE and COST on the stop-loss rule; LIN and
NEE remain open. See the position decision in `todo.md`.
