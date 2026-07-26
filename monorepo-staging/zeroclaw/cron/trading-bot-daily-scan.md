# Daily scan job

Repository-managed definition of the scheduled trading scan. Applied with
`scripts/sync_zeroclaw_config.sh --with-cron`.

## The job

```
zeroclaw cron add '45 9 * * 1-5' \
  '<REPO_ROOT>/monorepo-staging/scripts/run_trading_bot_daily.sh' \
  --agent tradingbot \
  --tz America/Detroit
```

Weekdays at 09:45 America/Detroit, fifteen minutes after the US market opens.

**Moved from 09:35 on 2026-07-26.** Nothing about a daily close-based
strategy needs the earlier slot, and 09:35 put the scan inside the window
where orders from the open may still be filling. The execution firewall now
blocks symbols with working orders, so this is defence in depth rather than
the fix — but it also keeps entries out of the opening auction's spread. The
11:00 watchdog deadline is unaffected.

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

Operator summaries are delivered by the Telegram channel, routed at
`run_trading_bot_telegram_command.sh`. **Configured and verified end-to-end
2026-07-26** — token entered by the operator, `zeroclaw channel list` reports
Telegram available, and a real summary was delivered to the operator's device
in 0.7s with no agent in the path. The scan also writes its record to
`runtime/trading-bot/logs/`, and `/bot` remains available for pull-based
queries.

## Companion job: daily off-machine backup

Decided 2026-07-25. Once daily scans resume, `trades.jsonl` grows every day
but the Google Drive copy only updates when run by hand, so the only
off-machine copy of the 90-day gate evidence silently drifts behind. A second
scheduled job removes that failure mode:

```
zeroclaw cron add '15 10 * * 1-5' \
  '<REPO_ROOT>/monorepo-staging/scripts/run_trading_bot_log_maintenance.sh backup' \
  --agent tradingbot \
  --tz America/Detroit
```

**The destination is not on the command line, deliberately.** It comes from
`TRADING_BOT_BACKUP_DEST` in the app's gitignored `.env`. The Google Drive
path contains a space (`My Drive`) and **ZeroClaw does not tokenise like a
shell** — it split the path into two arguments, and quoting it did not help.
Both forms were tested as one-shot jobs on 2026-07-26 and both failed with
`unrecognized arguments: Drive/trading-bot-backup`, meaning this job would
have errored on every single run. Keeping paths out of scheduled commands
avoids the whole class.

Verified through the scheduler, not just by hand: a copy was deleted from the
Drive folder, a one-shot fired, and the scheduler restored it within ten
seconds.

Runs at 10:15, after the 09:45 scan has completed. This is a local file copy
into a synced folder — Drive handles the upload — so it introduces no new
outbound path. The backup's size guard still refuses to overwrite a larger
backup with a smaller source, so a corrupted local log cannot destroy the
good copy.

`run_trading_bot_log_maintenance.sh` is already in `allowed_commands` in
`config/config.template.toml`, as is `run_trading_bot_watchdog.sh`, so no
risk-profile change is needed to schedule these.

## Companion job: staleness watchdog

The scan reports what happened. Nothing reported what *failed* to happen, and
that is the defect behind the 2026-04-24 to 2026-07-25 silence: a stopped scan
writes no logs, raises no errors and sends no messages, so absence looked
exactly like a quiet market.

```
zeroclaw cron add '0 11 * * 1-5' \
  '<REPO_ROOT>/monorepo-staging/scripts/run_trading_bot_watchdog.sh' \
  --agent tradingbot \
  --tz America/Detroit
```

Runs at 11:00, well after the 09:45 scan. It counts missed *trading weekdays*
rather than elapsed hours -- an earlier version asked "is today a weekday" and
consequently reported a 92-day-old scan as healthy simply because the check
ran on a Saturday, staying silent through precisely the outage it exists to
catch.

Note this shares the ZeroClaw scheduler with the scan, so it cannot report
ZeroClaw itself being down. That gap is covered by the absence of the daily
summary: no message by 09:50 on a weekday is itself the signal.

## Status

**NOT YET ACTIVE — ready to apply.** Everything that gated this is done: the
guardrails drift audit (`docs/SecurityAudit-2026-07-25.md`), the repaired and
tested kill switch, Telegram delivery, and the supervised rehearsal on
2026-07-26.

The dormancy cleanup has **already happened**: that rehearsal sold PFE and
COST on the stop-loss rule. LIN and NEE remain open. So the first scheduled
run is an ordinary trading day, not a cleanup — see the step 5 section in
`todo.md`.

Two defects the rehearsal found, both fixed, both of which would have made
these jobs useless in the same silent way:

- `run_trading_bot_daily.sh` did not pass `--execute-paper-trades`, so the
  scheduled scan would have decided trades and placed none.
- `sync_zeroclaw_config.sh --with-cron` scheduled
  `run_trading_bot_rehearsal.sh` rather than `run_trading_bot_daily.sh` —
  which neither executes nor reports, so applying the job as documented would
  have bypassed the fix above *and* sent no Telegram summary at all.

Apply all three jobs together. `--with-cron` currently adds only the scan;
the backup and watchdog are still added by hand from this file.
