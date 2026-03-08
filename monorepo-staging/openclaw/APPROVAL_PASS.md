# OpenClaw Approval Pass
*Created March 8, 2026*

## Purpose

This document captures the operator approval targets for the staged OpenClaw cutover package.

Approval here is about **wording and operational intent**, not actual deployment.

## Approval Targets

### 1. Workspace operating rules
Files under review:
- `openclaw/workspace/AGENTS.md`
- `openclaw/workspace/SOUL.md`
- `openclaw/workspace/BOOTSTRAP.md`
- `openclaw/workspace/IDENTITY.md`
- `openclaw/workspace/USER.md`
- `openclaw/workspace/TOOLS.md`
- `openclaw/workspace/HEARTBEAT.md`
- `openclaw/workspace/MIGRATION.md`

Current review position:
- staged/live boundary is explicit
- safe mode is explicit
- runtime identity is preserved
- cutover is not falsely implied

### 2. Cron payload wording
File under review:
- `runtime/cutover-rehearsal/20260308-chron-merge/jobs.candidate.json`

Current review position:
- uses staged rehearsal wrapper
- uses staged operator-summary wrapper
- preserves Telegram destination
- remains disabled by default for safe review

### 3. Promoted runtime wording
Files under review:
- `apps/trading-bot/src/trading_bot/services/daily_scan.py`
- `apps/trading-bot/src/trading_bot/operator_summary.py`
- `docs/Migration.md`
- `openclaw/FINAL_REVIEW.md`

Current review position:
- runtime now reports `production-candidate-safe-mode`
- summary still explicitly says cutover has not occurred
- safe mode remains the dominant protection signal

## Current Recommendation

Recommended approval outcome:
- workspace wording: approve unless tone changes are desired
- cron payload wording: approve unless message phrasing should be more/less strict
- promoted runtime wording: approve unless `production-candidate` should be renamed

## Approval Result

**Approved on March 8, 2026.**

- workspace wording: approved
- cron payload wording: approved
- promoted runtime wording: approved

No approval blockers remain in this packet.

## Not Included In This Approval

This approval pass does **not**:
- perform cutover
- modify `~/.openclaw/`
- enable the cron job
- authorize live trading

## Next Step After Approval

If the operator approves these wording targets, the next step is to prepare a controlled cutover window and execute the staged deployment checklist.
