# Monorepo Docs Hub

This directory holds longer-form documentation for the active monorepo-managed trading-bot runtime.

## Start Here

- [../README.md](../README.md) — current repo status, phase, canonical commands, and doc map
- [Architecture.md](Architecture.md) — current system layers and live execution model
- [Migration.md](Migration.md) — migration history, cutover outcome, and current phase
- [../openclaw/README.md](../openclaw/README.md) — deployed OpenClaw-facing contract and ownership boundary
- [../apps/trading-bot/APP_CONTRACT.md](../apps/trading-bot/APP_CONTRACT.md) — trading app ownership and runtime contract
- [../apps/trading-bot/ENV_CONTRACT.md](../apps/trading-bot/ENV_CONTRACT.md) — env/config contract for the live wrapper flow

## Scope

Use this docs folder for repository-level narrative documents such as:

- architecture overviews
- migration and cutover history
- operations guidance when it becomes stable enough to deserve a long-lived doc
- security or ownership model documents if they are promoted into the monorepo docs set

## Documentation Rule

Keep current status and phase tracking in [../README.md](../README.md) or the most local contract document.
Avoid repeating live-status summaries across multiple docs unless the status is essential to that document's purpose.

## Historical Material

The rebuild reasoning and historical planning material still live under [../../docs/rebuild/](../../docs/rebuild/).
Treat those files as background and audit history rather than the day-to-day entry point for the live monorepo runtime.
