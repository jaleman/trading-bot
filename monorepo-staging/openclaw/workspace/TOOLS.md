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
| Print account balance | `~/trading-bot/monorepo-staging/scripts/print_trading_bot_balance.sh` |
| Print supported commands | `~/trading-bot/monorepo-staging/scripts/print_trading_bot_supported_commands.sh` |
| Print holdings breakdown | `~/trading-bot/monorepo-staging/scripts/print_trading_bot_holdings.sh` |
| Print operator summary | `~/trading-bot/monorepo-staging/scripts/print_trading_bot_operator_summary.sh` |
| Print pending orders | `~/trading-bot/monorepo-staging/scripts/print_trading_bot_pending_orders.sh` |
| Print runtime status | `~/trading-bot/monorepo-staging/scripts/print_trading_bot_runtime_status.sh` |
| Print stock info | `~/trading-bot/monorepo-staging/scripts/print_trading_bot_stock_info.sh <TICKER>` |
| Route a Telegram operator command | `~/trading-bot/monorepo-staging/scripts/run_trading_bot_telegram_command.sh '<COMMAND LINE>'` |
| Run supervised trading scan | `~/trading-bot/monorepo-staging/scripts/run_trading_bot_rehearsal.sh` |
| Run CLI runtime | `~/trading-bot/monorepo-staging/scripts/run_trading_bot.sh` |
| Run tests | `~/trading-bot/monorepo-staging/scripts/run_trading_bot_tests.sh` |
| Sync deployed OpenClaw workspace | `~/trading-bot/monorepo-staging/scripts/sync_openclaw_workspace.sh` |
| Restart OpenClaw gateway | `~/trading-bot/monorepo-staging/scripts/restart_openclaw_gateway.sh` |
| View runtime log | `tail -30 ~/trading-bot/monorepo-staging/runtime/trading-bot/logs/trades.log` |
| View guardrail state | `cat ~/trading-bot/monorepo-staging/runtime/trading-bot/guardrail-state.json` |

Wrapper scripts are preferred because they normalize the app's `src/` layout and deployed run conventions.

## Operator Summary Rule

- `/Summary` means today's run summary only.
- When an operator asks for the latest summary or sends `/Summary`, run `~/trading-bot/monorepo-staging/scripts/print_trading_bot_operator_summary.sh` every time.
- Reply with the command's stdout only.
- Do not add headings, markdown bullets, explanations, or restated counts before or after the stdout.
- Do not answer latest-summary requests from memory, prior messages, or older run artifacts.
- If the user asks whether submitted buys are pending, accepted, or filled, run `~/trading-bot/monorepo-staging/scripts/print_trading_bot_pending_orders.sh` before answering.
- If the user asks for runtime health or current state, run `~/trading-bot/monorepo-staging/scripts/print_trading_bot_runtime_status.sh`.
- If the user asks for the supported command list or sends `/bot list` or `bot list`, run `~/trading-bot/monorepo-staging/scripts/print_trading_bot_supported_commands.sh`.
- If the user asks for account balances or sends `bot balance`, run `~/trading-bot/monorepo-staging/scripts/print_trading_bot_balance.sh`.
- If the user asks for per-position holdings or sends `bot holdings`, run `~/trading-bot/monorepo-staging/scripts/print_trading_bot_holdings.sh`.
- If the user asks for current stock info or sends `bot info <TICKER>`, run `~/trading-bot/monorepo-staging/scripts/print_trading_bot_stock_info.sh <TICKER>`.
- If OpenClaw workspace files are updated in-repo, use `~/trading-bot/monorepo-staging/scripts/sync_openclaw_workspace.sh` instead of ad hoc copy commands.
- If OpenClaw config changes require a gateway reload, use `~/trading-bot/monorepo-staging/scripts/restart_openclaw_gateway.sh`.

## Telegram Command Routing

Treat these Telegram operator commands as exact actions. Route them through the single repo-managed Telegram command router and reply with stdout only.

| Telegram command | Required action |
|---|---|
| `/bot list` | Run `~/trading-bot/monorepo-staging/scripts/run_trading_bot_telegram_command.sh 'bot list'` |
| `/bot summary` | Run `~/trading-bot/monorepo-staging/scripts/run_trading_bot_telegram_command.sh 'bot summary'` |
| `/bot pending` | Run `~/trading-bot/monorepo-staging/scripts/run_trading_bot_telegram_command.sh 'bot pending'` |
| `/bot status` | Run `~/trading-bot/monorepo-staging/scripts/run_trading_bot_telegram_command.sh 'bot status'` |
| `/bot balance` | Run `~/trading-bot/monorepo-staging/scripts/run_trading_bot_telegram_command.sh 'bot balance'` |
| `/bot holdings` | Run `~/trading-bot/monorepo-staging/scripts/run_trading_bot_telegram_command.sh 'bot holdings'` |
| `/bot info <TICKER>` | Run `~/trading-bot/monorepo-staging/scripts/run_trading_bot_telegram_command.sh 'bot info <TICKER>'` |
| `/bot sync` | Run `~/trading-bot/monorepo-staging/scripts/run_trading_bot_telegram_command.sh 'bot sync'` |
| `/bot restart` | Run `~/trading-bot/monorepo-staging/scripts/run_trading_bot_telegram_command.sh 'bot restart'` |
| `bot list` | Run `~/trading-bot/monorepo-staging/scripts/run_trading_bot_telegram_command.sh 'bot list'` |
| `bot summary` | Run `~/trading-bot/monorepo-staging/scripts/run_trading_bot_telegram_command.sh 'bot summary'` |
| `bot pending` | Run `~/trading-bot/monorepo-staging/scripts/run_trading_bot_telegram_command.sh 'bot pending'` |
| `bot status` | Run `~/trading-bot/monorepo-staging/scripts/run_trading_bot_telegram_command.sh 'bot status'` |
| `bot balance` | Run `~/trading-bot/monorepo-staging/scripts/run_trading_bot_telegram_command.sh 'bot balance'` |
| `bot holdings` | Run `~/trading-bot/monorepo-staging/scripts/run_trading_bot_telegram_command.sh 'bot holdings'` |
| `bot info <TICKER>` | Run `~/trading-bot/monorepo-staging/scripts/run_trading_bot_telegram_command.sh 'bot info <TICKER>'` |
| `bot sync` | Run `~/trading-bot/monorepo-staging/scripts/run_trading_bot_telegram_command.sh 'bot sync'` |
| `bot restart` | Run `~/trading-bot/monorepo-staging/scripts/run_trading_bot_telegram_command.sh 'bot restart'` |

Routing rules:

- Telegram may prepend a `Conversation info (untrusted metadata)` block before the operator text. Ignore that block when routing commands.
- The native `/bot` workspace command is the preferred Telegram operator entrypoint because it bypasses the ambiguous plain-chat path.
- Determine command intent from the final non-empty line of the user message after any untrusted metadata block.
- If the final non-empty line starts with `/bot `, route it exactly as the same `bot ...` subcommand without conversational interpretation.
- If that final non-empty line exactly matches `bot <subcommand ...>` for a supported subcommand, execute `~/trading-bot/monorepo-staging/scripts/run_trading_bot_telegram_command.sh '<final non-empty line>'` immediately.
- Command routing takes priority over greetings, summaries, recaps, or follow-up questions.
- Match the subcommand token case-insensitively, but preserve ticker arguments after `bot info`.
- Never execute `bot`, `/bot`, `/Summary`, `/Pending`, `/Status`, `/Balance`, `/Holdings`, `/Info`, `/Sync`, or `/Restart` directly as shell commands. They are router inputs, not executables.
- `/bot list` is the canonical help surface.
- `bot summary` returns today's run summary only; if no summary exists for today, reply with that exact wrapper output.
- `bot status` reports runtime health only and should not include balance or holdings detail.
- `bot balance` reports aggregate cash, holdings value, portfolio value, and buying power.
- `bot holdings` reports the detailed open-position breakdown.
- `bot sync` and `bot restart` are operator-triggered backend actions; report success or failure plainly from wrapper stdout/stderr.
- `/Summary`, `/Pending`, `/Status`, `/Balance`, `/Holdings`, `/Info`, `/Sync`, and `/Restart` remain compatibility aliases, but `/bot ...` is preferred.
- For unknown commands, reply with `Unsupported command. Available commands: /bot list | /bot summary | /bot pending | /bot status | /bot balance | /bot holdings | /bot info <TICKER> | /bot sync | /bot restart`.

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
