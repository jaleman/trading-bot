# TOOLS.md

## Monorepo Trading Platform

This workspace drives the active monorepo-managed trading runtime.

## Important Status

- The active managed runtime lives at `~/trading-bot/monorepo-staging`.
- The scheduled OpenClaw job and Telegram workflow now target the monorepo wrapper scripts.
- The current phase is post-cutover paper-trade validation.
- Live-capital trading remains a separate approval gate and is not implied by paper-trade activity.

## Trading Bot App

The trading app lives at:

```bash
~/trading-bot/monorepo-staging/apps/trading-bot
```

### Main commands

| What | Command |
|------|---------|
| Print operator summary | `~/trading-bot/monorepo-staging/scripts/print_trading_bot_operator_summary.sh` |
| Run supervised trading scan | `~/trading-bot/monorepo-staging/scripts/run_trading_bot_rehearsal.sh` |
| Run CLI runtime | `~/trading-bot/monorepo-staging/scripts/run_trading_bot.sh` |
| Run tests | `~/trading-bot/monorepo-staging/scripts/run_trading_bot_tests.sh` |
| View runtime log | `tail -30 ~/trading-bot/monorepo-staging/runtime/trading-bot/logs/trades.log` |
| View guardrail state | `cat ~/trading-bot/monorepo-staging/runtime/trading-bot/guardrail-state.json` |

Wrapper scripts are preferred because they normalize the app's `src/` layout and deployed run conventions.

## Operator Summary Rule

- When an operator asks for the latest summary, run `~/trading-bot/monorepo-staging/scripts/print_trading_bot_operator_summary.sh` every time.
- Reply with the command's stdout only.
- Do not add headings, markdown bullets, explanations, or restated counts before or after the stdout.
- Do not answer latest-summary requests from memory, prior messages, or older run artifacts.
- If the user asks whether submitted buys are pending, accepted, or filled, check broker state before answering.

Example latest-summary reply shape:

Trading scan completed. Executed 2 paper-trade order(s).
Scanned 50 symbol(s). Triggered: BRK.B, COST. Watching: AVGO.
Decisions: 2 buy, 0 sell, 0 skip.
Local analysis: COST presents a clear buy opportunity with a strong setup, while BRK.B also merits consideration. AVGO, though interesting, requires further confirmation and is best watched for now. Top ranked: COST (buy, confidence 0.90).
Guardrails passed. Claude calls today: 0. Trades today: 2.

This example is plain text, not markdown. Preserve line breaks and do not prepend commentary.

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
- delivery of operator summaries

### Trading app owns
- config loading
- market-data adapter
- prefilter adapter
- decision adapter
- broker adapter
- runtime logging
- guardrail logic
- operator summary generation

## Safety Rules

- Keep paper-trade validation distinct from live-capital readiness.
- Do not claim orders were filled when the broker only reports `ACCEPTED`.
- Use runtime artifacts and broker state as the source of truth when operator-facing status is questioned.
