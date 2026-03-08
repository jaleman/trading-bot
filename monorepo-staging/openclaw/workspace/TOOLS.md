# TOOLS.md

## Monorepo Trading Platform

This workspace is for the future staged monorepo version of the trading platform.

## Important Status

- The staged monorepo is **not** the live production runtime yet.
- The staged monorepo is **not ready for cutover** yet.
- The current live system still runs from `~/trading-bot`.
- Use the staged monorepo commands only when explicitly working on or validating the rebuild.

## Trading Bot App (Staged)

The staged trading app lives at:

```bash
~/trading-bot/monorepo-staging/apps/trading-bot
```

### Main commands

| What | Command |
|------|---------|
| Print staged operator summary | `~/trading-bot/monorepo-staging/scripts/print_trading_bot_operator_summary.sh` |
| Run supervised staged rehearsal | `~/trading-bot/monorepo-staging/scripts/run_trading_bot_rehearsal.sh` |
| Run staged CLI runtime | `~/trading-bot/monorepo-staging/scripts/run_trading_bot.sh` |
| Run staged tests | `~/trading-bot/monorepo-staging/scripts/run_trading_bot_tests.sh` |
| View staged runtime log | `tail -30 ~/trading-bot/monorepo-staging/runtime/trading-bot/logs/trades.log` |
| View staged guardrail state | `cat ~/trading-bot/monorepo-staging/runtime/trading-bot/guardrail-state.json` |

Wrapper scripts are preferred because they normalize the staged app's `src/` layout and future run conventions.

When an operator-facing summary is needed, prefer the summary wrapper over improvising from raw logs.

## Current Rebuild References

Use these docs before making structural changes:
- `~/trading-bot/docs/rebuild/README.md`
- `~/trading-bot/docs/rebuild/RebuildPlan.md`
- `~/trading-bot/docs/rebuild/Operations.md`
- `~/trading-bot/docs/rebuild/MachineAudit.md`
- `~/trading-bot/docs/rebuild/DriftRegister.md`

## Runtime Boundaries

### OpenClaw owns
- scheduling
- Telegram interaction
- workspace behavior files
- operator-facing summaries

### Staged trading app owns
- config loading
- market-data adapter
- prefilter adapter
- decision adapter
- broker adapter
- runtime logging
- guardrail logic

## Safety Rules

- Do not point production cron at the staged app yet.
- Do not enable staged paper-trade execution without explicit migration approval.
- Treat the staged app as a rebuild/testing target until cutover is formally planned.
- Passing wrapper-script or test validation does not authorize production migration.
