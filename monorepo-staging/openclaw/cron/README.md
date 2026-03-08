# OpenClaw Cron

This folder is reserved for scheduler definitions and notes for the rebuilt platform.

## Current Live Reference

The live daily trading job is currently owned by OpenClaw cron and runs the existing repo directly.

Source reference:
- [../../../docs/rebuild/external-config/cron-jobs.template.json](../../../docs/rebuild/external-config/cron-jobs.template.json)

## Rebuild Goal

Replace direct `~/trading-bot` execution with monorepo-aware job payloads after the new trading app is ready.

## Current Staged Direction

The staged cron flow should prefer:

1. a canonical staged run wrapper
2. a canonical operator-summary wrapper

This reduces OpenClaw-side guesswork and avoids relying on raw log parsing for Telegram summaries.

## Safe Cutover Preparation

Use [../../scripts/prepare_openclaw_cutover_jobs.sh](../../scripts/prepare_openclaw_cutover_jobs.sh) to build a candidate `jobs.json` in the staged runtime area.

That helper reads the live `~/.openclaw/cron/jobs.json`, replaces only the `trading-bot-daily-scan` job definition with the staged template, preserves the live Telegram delivery target when the staged template is redacted, and writes the result to a reviewable candidate file.
