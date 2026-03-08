# OpenClaw Cutover Checklist

## Purpose

This checklist defines the concrete file-level steps for switching OpenClaw from the current live repo to the staged monorepo-managed assets.

Use [DEPLOYMENT_MAP.md](DEPLOYMENT_MAP.md) for the exact staged-to-live file mapping.
Use [CUTOVER_RUNBOOK.md](CUTOVER_RUNBOOK.md) for the exact planned execution order.

## Pre-cutover checks

- confirm staged tests pass
- confirm the latest supervised rehearsal succeeded
- confirm staged operator summary output is acceptable
- confirm staged cron payload text is finalized
- confirm staged workspace files are finalized
- confirm rollback files and destinations are identified

## Files to back up before any cutover

- `~/.openclaw/cron/jobs.json`
- `~/.openclaw/workspace/AGENTS.md`
- `~/.openclaw/workspace/TOOLS.md`
- `~/.openclaw/workspace/HEARTBEAT.md`
- `~/.openclaw/workspace/SOUL.md`
- `~/.openclaw/workspace/IDENTITY.md`
- `~/.openclaw/workspace/BOOTSTRAP.md`
- `~/.openclaw/workspace/USER.md`

## Staged assets intended for deployment

- `monorepo-staging/openclaw/workspace/AGENTS.md`
- `monorepo-staging/openclaw/workspace/BOOTSTRAP.md`
- `monorepo-staging/openclaw/workspace/IDENTITY.md`
- `monorepo-staging/openclaw/workspace/TOOLS.md`
- `monorepo-staging/openclaw/workspace/HEARTBEAT.md`
- `monorepo-staging/openclaw/workspace/MIGRATION.md`
- `monorepo-staging/openclaw/workspace/USER.md`
- `monorepo-staging/openclaw/cron/trading-bot-daily-scan.template.json`

## Deployment sequence

1. back up live OpenClaw cron and workspace files
2. build and review a candidate `jobs.json` using `scripts/prepare_openclaw_cutover_jobs.sh`
3. disable the live `trading-bot-daily-scan` job
4. deploy the staged workspace files selected for cutover
5. update only the `trading-bot-daily-scan` job definition inside `~/.openclaw/cron/jobs.json`
6. run one supervised post-deploy scan
7. review the operator summary output and runtime artifacts
8. only then re-enable the schedule

## Rollback sequence

1. disable the staged cron job or restore the previous job definition
2. restore the backed-up workspace files
3. restore the previous `jobs.json`
4. manually confirm the live repo path still runs correctly
5. document the rollback reason and observed failure mode

## Current status

- checklist drafted
- rollback rehearsal completed as a non-destructive dry run on March 8, 2026
- backup snapshot created under `monorepo-staging/runtime/rollback-rehearsal/20260308-161833`
- restore manifest recorded in `RESTORE_MANIFEST.md`
- staged workspace file coverage now matches the live workspace file types
- staged asset wording approved in the operator approval pass
- cron-cutover helper validated with candidate output under `monorepo-staging/runtime/cutover-rehearsal/20260308-chron-merge/jobs.candidate.json`
- final review recorded in `openclaw/FINAL_REVIEW.md`
- exact live cutover runbook drafted in `openclaw/CUTOVER_RUNBOOK.md`
- controlled live cutover executed on March 8, 2026 using snapshot `monorepo-staging/runtime/cutover-execution/20260308-165207`
- live OpenClaw workspace files now match the approved staged sources
- live `trading-bot-daily-scan` job now contains the staged rehearsal payload with preserved Telegram delivery target
- supervised post-deploy validation passed and produced an acceptable operator summary
- pre-enable safety snapshot created at `monorepo-staging/runtime/go-live-execution/20260308-165905/backup/jobs.json`
- live `trading-bot-daily-scan` job is now enabled