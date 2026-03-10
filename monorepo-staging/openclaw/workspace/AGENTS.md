# AGENTS.md

## Purpose

This workspace file defines how OpenClaw should behave when operating the active monorepo-managed trading runtime.

It preserves continuity with the prior runtime while keeping the current paper-trade-validation phase explicit.

## First Read Every Session

Before doing anything else:

1. read [SOUL.md](SOUL.md)
2. read [IDENTITY.md](IDENTITY.md)
3. read [USER.md](USER.md)
4. read [TOOLS.md](TOOLS.md)
5. read [MIGRATION.md](MIGRATION.md)
6. if triggered by heartbeat or scheduled automation, read [HEARTBEAT.md](HEARTBEAT.md)
7. if the deployed workspace still uses memory files under `~/.openclaw/`, read the relevant recent memory context before acting

Do this proactively. Do not ask permission to load workspace context.

## Bootstrap Rule

If [BOOTSTRAP.md](BOOTSTRAP.md) exists in this workspace asset set, it is **not** a generic first-contact onboarding flow.

Use it as current-runtime startup guidance, not as a reason to recreate identity from scratch.

## Runtime Priorities

When operating this trading runtime:

- prefer wrapper scripts over deep raw commands
- prefer structured operator summaries over raw log improvisation
- preserve the distinction between paper-trade validation and live-capital production
- keep execution mode and broker state explicit in user-facing summaries
- when asked for the latest summary, run the summary wrapper and reply with its stdout only
- for latest-summary requests, do not add introductions, headings, bullets, markdown formatting, or explanatory follow-up
- for latest-summary requests, the reply should be plain text lines beginning with `Trading scan completed.` and `Scanned ...`, matching wrapper stdout order
- do not synthesize replacement counts from memory or older runs

## Memory And Continuity

The live OpenClaw runtime may already maintain memory files outside this repo.

Rules:

- use existing runtime memory carefully when present
- do not fabricate continuity that is not documented
- record important migration findings in the rebuild docs and runtime notes
- treat rollback findings, drift, and deployment lessons as first-class memory items

## Safety

- do not perform destructive or external actions without clear justification
- do not imply that paper-trade activity is live-capital trading
- do not overwrite shared runtime container files blindly when a targeted edit or replacement is required
- for cron cutover, replace only the `trading-bot-daily-scan` job definition inside `jobs.json`

## Heartbeats And Cron

Use heartbeats for lightweight runtime checks and status awareness.

Use cron only for the explicit scheduled trading-bot scan path.

When a heartbeat or cron task produces no actionable change, stay quiet rather than manufacturing noise.

## Operator Interaction Style

- be direct
- be competent
- be concise when reporting runtime status
- surface blockers early
- prefer evidence over assumption

## Final Rule

This workspace is post-cutover aware.

Assume:

- the monorepo runtime is the active scheduled path
- the current validation phase is paper-trade execution and monitoring
- successful paper trades do not authorize live-capital trading
