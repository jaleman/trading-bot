# Migration & Cutover Plan
*Created March 8, 2026*

## Readiness Status

**Not ready for cutover.**

The staged monorepo has passed staged runtime validation, including:
- wrapper scripts run successfully
- staged tests pass
- staged CLI returns a structured production-candidate summary

That is **not** the same as production readiness.

Production cutover remains blocked until the staged app, staged OpenClaw assets, secrets handling, supervised runbook, and rollback procedure are all fully validated.

## Purpose

This document defines how the current live trading bot at `~/trading-bot` will eventually be replaced by the staged monorepo implementation at `~/trading-bot/monorepo-staging`.

## Current Reality

### Live runtime
- OpenClaw production workspace: `~/.openclaw/`
- Live trading bot repo: `~/trading-bot`
- Live scheduled job: `trading-bot-daily-scan`
- Live cron payload currently runs `python main.py` in the repo root

### Staged rebuild runtime
- Staged monorepo root: `~/trading-bot/monorepo-staging`
- Staged trading app: `~/trading-bot/monorepo-staging/apps/trading-bot`
- Staged OpenClaw assets: `~/trading-bot/monorepo-staging/openclaw`
- Staged runtime state: `~/trading-bot/monorepo-staging/runtime/trading-bot`

## Canonical Staged Commands

These are the canonical commands for the staged monorepo.

### Run staged trading bot
```bash
~/trading-bot/monorepo-staging/scripts/run_trading_bot.sh
```

### Bootstrap staged trading bot environment
```bash
~/trading-bot/monorepo-staging/scripts/bootstrap_trading_bot.sh
```

### Run staged tests
```bash
~/trading-bot/monorepo-staging/scripts/run_trading_bot_tests.sh
```

These wrapper scripts are preferred over raw `python -m ...` commands because they normalize the `src/` layout and future runtime assumptions.

They also prefer an app-local virtualenv at `apps/trading-bot/.venv`, which is the intended steady-state environment for the staged app.

## Cutover Preconditions

Do not cut over OpenClaw production to the monorepo until all of the following are true:

- staged trading app behavior is validated
- staged guardrails are validated
- staged OpenClaw workspace files are finalized
- staged cron payload is finalized
- migration rollback steps are documented
- runtime paths and secret expectations are documented
- operator confirms cutover window

## Current Blocking Items

The following items are still open and prevent cutover:

- no production-equivalent supervised end-to-end run has been approved
- no final cutover checklist has been executed against the live host
- no live restore execution has been rehearsed after a deployed staged cutover

## Current Next Step

The staged runtime promotion work is complete.
The staged operator approval pass is complete.
The exact live cutover runbook is now drafted.

The next step is to decide whether to open a controlled cutover window and, if approved, execute the staged deployment checklist against the live host.

### Phase 1 cutover gate

Complete these items first:

1. add staged CLI support for selecting a real strategy config file
2. add staged CLI or bootstrap support for a monorepo-native env file / secret-loading path
3. create a non-committed staged config file that mirrors live settings while keeping safe mode enabled
4. run one supervised manual staged scan on the Mac Mini using real secrets, real config, and safe-mode execution
5. verify the staged summary, runtime log, and guardrail state match expectations

### Phase 1 implementation status

- staged CLI config override: implemented via `--config`
- staged CLI env-file override: implemented via `--env-file`
- staged rehearsal shortcut: implemented via `--rehearsal`
- preferred local config path: `apps/trading-bot/config/strategy.local.json`
- preferred local env path: `apps/trading-bot/.env`
- canonical rehearsal wrapper: `scripts/run_trading_bot_rehearsal.sh`

Phase 1 runtime-contract work is complete.

### Canonical supervised rehearsal command

```bash
~/trading-bot/monorepo-staging/scripts/run_trading_bot_rehearsal.sh
```

This command intentionally fails fast if the local-only staged `.env` file or `strategy.local.json` file has not been created yet.

### Phase 1 rehearsal result

**Completed on March 8, 2026.**

Observed outcome from the supervised staged rehearsal:

- staged local env file loaded successfully
- staged local strategy file loaded successfully
- broker context loaded successfully
- market-data snapshots loaded for the configured watchlist
- prefilter produced 1 triggered symbol
- decision-model call completed successfully
- guardrails remained in a passing state
- no trades were executed
- daily guardrail state updated to reflect 1 Claude call and 0 trades

This confirms that the staged monorepo can perform a supervised safe-mode rehearsal with real credentials and real external dependencies.

It does **not** authorize production cutover.

### Next cutover gate after rehearsal

The next gate is to compare the staged rehearsal behavior against the live hybrid runtime and close any remaining deployment gaps:

1. verify the staged operator-facing summary shape is acceptable for OpenClaw
2. finalize staged OpenClaw workspace assets for deployment
3. finalize the staged cron payload and rollback checklist
4. decide whether one more supervised rehearsal is needed before any cron change
5. only then plan a controlled cutover window

### Post-rehearsal implementation status

- canonical operator-summary formatter: implemented
- summary wrapper script: `scripts/print_trading_bot_operator_summary.sh`
- staged cron template updated to prefer the summary wrapper over raw log parsing
- staged OpenClaw cutover checklist drafted at `openclaw/CUTOVER_CHECKLIST.md`
- non-destructive rollback rehearsal completed and backup snapshot recorded under `runtime/rollback-rehearsal/20260308-161833`
- staged OpenClaw deployment map drafted at `openclaw/DEPLOYMENT_MAP.md`
- safe cron-merge helper added: `scripts/prepare_openclaw_cutover_jobs.sh`
- candidate merged cron file generated successfully under `runtime/cutover-rehearsal/20260308-chron-merge/jobs.candidate.json`
- staged OpenClaw final review recorded at `openclaw/FINAL_REVIEW.md`
- staged app promoted from `scaffold-only` to a production-candidate runtime status
- staged operator approval packet prepared at `openclaw/APPROVAL_PASS.md`
- staged operator approval pass completed on March 8, 2026
- staged env/config contract documented at `apps/trading-bot/ENV_CONTRACT.md`
- exact live cutover runbook drafted at `openclaw/CUTOVER_RUNBOOK.md`

### Cron-cutover rehearsal result

Observed outcome from the staged cron-cutover rehearsal:

- only the `trading-bot-daily-scan` job was replaced in the candidate file
- the live Telegram delivery target was preserved
- the staged payload text was applied
- the resulting candidate job remained disabled by default for safe review

This confirms that the staged cutover process can prepare a reviewable `jobs.json` candidate without overwriting the live OpenClaw cron file.

### Current staged operator-summary shape

The current validated summary output is:

```text
Staged trading scan completed. Safe mode remained active; no trades executed.
Scanned 12 symbol(s). Triggered: none. Watching: CAT.
Decisions: 0 buy, 0 sell, 0 skip.
Guardrails passed. Claude calls today: 1. Trades today: 0.
```

This is the current target shape for staged OpenClaw delivery until a better operator-facing format is chosen.

### Rollback rehearsal result

**Completed on March 8, 2026 as a non-destructive dry run.**

Observed outcome:

- live OpenClaw cron and workspace files were verified
- a timestamped backup snapshot was created in the staged runtime area
- a restore manifest was recorded for the backed-up files
- no files were restored to `~/.openclaw/`

New finding from the rehearsal:

- the staged OpenClaw workspace set was incomplete relative to the live workspace
- explicit staged replacements were then added for `BOOTSTRAP.md`, `IDENTITY.md`, and `USER.md`
- the remaining issue is final deployment readiness, not missing file coverage

### Explicit non-goals for this phase

Do **not** do these yet:

- do not repoint OpenClaw cron
- do not replace live workspace files
- do not enable staged paper-trade execution by default
- do not treat a successful rehearsal as final cutover approval

## Cutover Sequence

1. Freeze live changes to the current repo
2. Confirm staged tests pass
3. Confirm staged runtime commands behave as expected
4. Prepare final OpenClaw workspace files for deployment
5. Prepare final OpenClaw cron job payload for deployment
6. Back up live OpenClaw config and workspace files
7. Disable live cron job temporarily
8. Point OpenClaw runtime assets to the monorepo-native equivalents
9. Run one supervised staged scan
10. Verify logs, summaries, and guardrail state
11. Re-enable schedule under the new command path only after supervised validation

## Rollback Plan

If cutover fails:

1. restore the previous OpenClaw workspace files
2. restore the previous cron payload
3. point execution back to `~/trading-bot/main.py`
4. verify the next manual live run behaves as expected
5. document the failed cutover in rebuild notes before retrying

## Success Criteria

A successful cutover means:
- OpenClaw uses monorepo-native runtime assets
- scheduled scans run via wrapper scripts, not ad hoc deep commands
- staged app logs and guardrails behave predictably
- operator-facing summaries remain correct
- rollback remains documented and practical

## Current Status

- Controlled cutover completed on March 8, 2026
- Production OpenClaw now targets the monorepo wrapper flow rather than the legacy root repo
- The live scheduled job is enabled and running through the monorepo-managed OpenClaw assets
- Paper-trade execution was exercised successfully on March 9, 2026 under guardrail enforcement
- This document is now partly historical: the migration plan succeeded, but live-capital trading remains a separate post-cutover gate

## Current Phase

The active phase is now:

1. post-cutover validation
2. paper-trade monitoring
3. deciding the explicit gate for any future live-capital promotion

The next meaningful process decision is no longer whether to cut over OpenClaw.
The next decision is whether the paper-trading results, guardrail behavior, and operator workflow are strong enough to justify defining a live-capital approval gate.
