# Daily scan job

Repository-managed definition of the scheduled trading scan. Applied with
`scripts/sync_zeroclaw_config.sh --with-cron`.

## The job

```
zeroclaw cron add '35 9 * * 1-5' \
  '<REPO_ROOT>/monorepo-staging/scripts/run_trading_bot_rehearsal.sh' \
  --agent tradingbot \
  --tz America/Detroit
```

Weekdays at 09:35 America/Detroit, five minutes after the US market opens.

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

## Status

**NOT YET ACTIVE.** Deliberately not scheduled until the guardrails drift
audit (`docs/Security.md` vs `services/guardrails.py`) has been completed —
that audit has not been re-run since the 2026-03-09 refactor, and it is the
last unverified safety claim before paper trading resumes.

The first active run will close PFE and COST on the stop-loss rule; LIN and
NEE remain open. See the position decision in `todo.md`.
