# OpenClaw Cutover Runbook
*Created March 8, 2026*

## Purpose

This runbook defines the exact live cutover procedure for switching the trading-bot OpenClaw runtime from the current live repo to the approved staged monorepo assets.

This document is for execution planning.
It does **not** mean cutover has been performed.

## Authoritative Inputs

Use these files together:
- [CUTOVER_CHECKLIST.md](CUTOVER_CHECKLIST.md)
- [DEPLOYMENT_MAP.md](DEPLOYMENT_MAP.md)
- [FINAL_REVIEW.md](FINAL_REVIEW.md)
- [APPROVAL_PASS.md](APPROVAL_PASS.md)
- [../apps/trading-bot/ENV_CONTRACT.md](../apps/trading-bot/ENV_CONTRACT.md)

## Approved Staged Sources

### Workspace files
- `monorepo-staging/openclaw/workspace/AGENTS.md`
- `monorepo-staging/openclaw/workspace/BOOTSTRAP.md`
- `monorepo-staging/openclaw/workspace/HEARTBEAT.md`
- `monorepo-staging/openclaw/workspace/IDENTITY.md`
- `monorepo-staging/openclaw/workspace/MIGRATION.md`
- `monorepo-staging/openclaw/workspace/SOUL.md`
- `monorepo-staging/openclaw/workspace/TOOLS.md`
- `monorepo-staging/openclaw/workspace/USER.md`

### Cron source
- `monorepo-staging/runtime/cutover-rehearsal/20260308-chron-merge/jobs.candidate.json`

## Pre-Execution Requirements

Before running this cutover:
- staged tests must pass
- the latest staged rehearsal must be acceptable
- operator summary wording must be accepted
- the staged `.env` and `strategy.local.json` contract must remain valid
- a fresh day-of backup snapshot must be taken from `~/.openclaw/`
- operator must explicitly approve the cutover window

## Day-Of Backup Procedure

Create a fresh timestamped backup directory under:
- `monorepo-staging/runtime/cutover-execution/<timestamp>/backup`

Back up these live files before changing anything:
- `~/.openclaw/cron/jobs.json`
- `~/.openclaw/workspace/AGENTS.md`
- `~/.openclaw/workspace/BOOTSTRAP.md`
- `~/.openclaw/workspace/HEARTBEAT.md`
- `~/.openclaw/workspace/IDENTITY.md`
- `~/.openclaw/workspace/SOUL.md`
- `~/.openclaw/workspace/TOOLS.md`
- `~/.openclaw/workspace/USER.md`

Also record:
- backup timestamp
- operator name
- reason for change window

## Exact Cutover Sequence

1. Confirm the fresh backup exists and is readable.
2. Confirm the approved candidate cron file exists and still matches the intended staged payload.
3. Disable the live `trading-bot-daily-scan` job.
4. Copy the approved staged workspace files into `~/.openclaw/workspace/` using the mappings in [DEPLOYMENT_MAP.md](DEPLOYMENT_MAP.md).
5. Replace only the `trading-bot-daily-scan` job definition inside `~/.openclaw/cron/jobs.json` using the approved candidate file.
6. Keep the cutover cron job disabled initially after writing the file.
7. Run one supervised post-deploy invocation through the staged runtime path.
8. Review the staged operator summary and runtime artifacts.
9. If the supervised post-deploy run is acceptable, re-enable the `trading-bot-daily-scan` job.
10. Record the cutover result in the rebuild notes.

## Post-Deploy Verification

Confirm all of the following:
- OpenClaw workspace files under `~/.openclaw/workspace/` match the approved staged versions
- `~/.openclaw/cron/jobs.json` contains the staged trading-bot payload and preserved Telegram target
- the staged runtime produces an operator summary without implying live trades when safe mode is active
- the staged runtime log and JSONL artifacts are updated under `monorepo-staging/runtime/trading-bot/`
- guardrail state is sensible after the supervised run

## Abort Conditions

Abort the cutover if any of the following occur before re-enabling schedule:
- backup is missing or unreadable
- workspace copy set is incomplete
- candidate cron job does not match the approved payload
- supervised post-deploy run fails
- operator summary wording is misleading
- runtime artifacts do not update as expected

## Rollback Entry Point

If cutover fails:
- use the fresh day-of backup first
- if needed, use the previously rehearsed restore mappings in `runtime/rollback-rehearsal/20260308-161833/RESTORE_MANIFEST.md`
- restore the original workspace files and original `jobs.json`
- confirm the live repo path still runs correctly
- record the failure before retrying

## Current Status

- runbook drafted
- executed in controlled form on March 8, 2026
- execution snapshot recorded at `monorepo-staging/runtime/cutover-execution/20260308-165207`
- live workspace deployment verified after execution
- supervised post-deploy rehearsal passed
- pre-enable backup recorded at `monorepo-staging/runtime/go-live-execution/20260308-165905/backup/jobs.json`
- live `trading-bot-daily-scan` job enabled after verification
