# OpenClaw Deployment Map

## Purpose

This document maps staged monorepo OpenClaw assets to their intended live destinations under `~/.openclaw/`.

It is for cutover planning only.
It does **not** authorize deployment by itself.

Use [CUTOVER_RUNBOOK.md](CUTOVER_RUNBOOK.md) for the planned execution sequence.

## Workspace file mapping

| Staged source | Intended live destination |
|---|---|
| `monorepo-staging/openclaw/workspace/AGENTS.md` | `~/.openclaw/workspace/AGENTS.md` |
| `monorepo-staging/openclaw/workspace/BOOTSTRAP.md` | `~/.openclaw/workspace/BOOTSTRAP.md` |
| `monorepo-staging/openclaw/workspace/HEARTBEAT.md` | `~/.openclaw/workspace/HEARTBEAT.md` |
| `monorepo-staging/openclaw/workspace/IDENTITY.md` | `~/.openclaw/workspace/IDENTITY.md` |
| `monorepo-staging/openclaw/workspace/MIGRATION.md` | `~/.openclaw/workspace/MIGRATION.md` |
| `monorepo-staging/openclaw/workspace/SOUL.md` | `~/.openclaw/workspace/SOUL.md` |
| `monorepo-staging/openclaw/workspace/TOOLS.md` | `~/.openclaw/workspace/TOOLS.md` |
| `monorepo-staging/openclaw/workspace/USER.md` | `~/.openclaw/workspace/USER.md` |

## Cron mapping

| Staged source | Intended live destination |
|---|---|
| `monorepo-staging/openclaw/cron/trading-bot-daily-scan.template.json` | selected job entry inside `~/.openclaw/cron/jobs.json` |

## Recommended preparation command

- build candidate merged cron file: `~/trading-bot/monorepo-staging/scripts/prepare_openclaw_cutover_jobs.sh`
- validated candidate example: `monorepo-staging/runtime/cutover-rehearsal/20260308-chron-merge/jobs.candidate.json`

## Notes

- `jobs.json` is a shared container file, so cutover should replace only the `trading-bot-daily-scan` job definition, not blindly overwrite unrelated jobs.
- `MIGRATION.md` does not currently exist in the live workspace inventory captured during the audit. If deployed, it should be treated as an additive workspace file rather than a replacement.
- `openclaw/CUTOVER_CHECKLIST.md`, `openclaw/DEPLOYMENT_MAP.md`, and `openclaw/README.md` are planning artifacts kept in-repo and are not intended to be copied into `~/.openclaw/`.

## Pre-deploy checks

Before any real deployment:
- confirm each staged file is final
- confirm backups exist for every replaced live file
- confirm the cron payload text matches the latest wrapper-script contract
- confirm rollback sources are still present and readable

## Current status

- workspace file coverage is now mapped
- cron mapping is defined
- candidate merged cron file has been generated successfully for review
- deployment remains blocked pending final cutover approval
