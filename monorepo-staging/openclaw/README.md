# OpenClaw Runtime Assets

This folder holds the monorepo-managed version of the OpenClaw-facing runtime artifacts.

## Current Contents

- `workspace/AGENTS.md` — workspace/session operating rules
- `workspace/BOOTSTRAP.md` — startup guidance
- `workspace/SOUL.md` — runtime tone, boundaries, and behavior rules
- `workspace/IDENTITY.md` — trading-bot identity
- `workspace/TOOLS.md` — monorepo commands and boundaries
- `workspace/HEARTBEAT.md` — rebuild heartbeat checks
- `workspace/USER.md` — operator context
- `workspace/MIGRATION.md` — live-vs-managed runtime guidance
- `CUTOVER_CHECKLIST.md` — deployment and rollback checklist
- `CUTOVER_RUNBOOK.md` — executed cutover procedure record
- `DEPLOYMENT_MAP.md` — file-by-file mapping from repo assets to live `~/.openclaw/` destinations
- `FINAL_REVIEW.md` — review, cutover, and go-live record
- `APPROVAL_PASS.md` — operator sign-off packet for wording and runtime-position decisions
- `cron/trading-bot-daily-scan.template.json` — monorepo-managed cron template source
- `config/README.md` — sanitized config reference area

## Current Status

- controlled cutover completed on March 8, 2026
- approved workspace files from this folder were deployed into `~/.openclaw/workspace/`
- the live trading job now points at the wrapper-script flow under `~/trading-bot/monorepo-staging/`
- the live trading job was enabled after verification and pre-enable backup
- the live OpenClaw default operator-chat model was switched to `ollama/qwen2.5:7b`

## Important Rule

The files in this folder are the repository-managed source of truth for the deployed OpenClaw trading-bot contract, but the live runtime still executes the copied versions under `~/.openclaw/`.

Operational edits should be made here first and then deployed deliberately rather than patched directly in `~/.openclaw/` without record.

## Purpose

This directory defines the OpenClaw side of the trading-bot runtime contract:

- workspace behavior
- operator identity and boundaries
- cron payload shape
- deployment and rollback procedure
- review and go-live history

## Key Reference Docs

- [FINAL_REVIEW.md](FINAL_REVIEW.md)
- [CUTOVER_CHECKLIST.md](CUTOVER_CHECKLIST.md)
- [CUTOVER_RUNBOOK.md](CUTOVER_RUNBOOK.md)
- [DEPLOYMENT_MAP.md](DEPLOYMENT_MAP.md)

## Live Boundary

OpenClaw owns:

- schedule and session orchestration
- Telegram delivery
- workspace instructions and operator-facing behavior
- default operator-chat model routing

The trading-bot app under `apps/trading-bot/` owns:

- scan execution
- guardrails
- broker and model integrations
- runtime summaries and logs

## Model Boundary

- default OpenClaw operator chat: `ollama/qwen2.5:7b`
- explicit trading decision path inside the Python runtime: Anthropic/Claude
- local prefilter and monitoring path: Ollama/qwen
