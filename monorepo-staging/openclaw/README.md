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
- `workspace/.openclaw/extensions/bot-command/` — native `/bot` workspace command that dispatches repo-managed operator wrappers
- `CUTOVER_CHECKLIST.md` — deployment and rollback checklist
- `CUTOVER_RUNBOOK.md` — executed cutover procedure record
- `DEPLOYMENT_MAP.md` — file-by-file mapping from repo assets to live `~/.openclaw/` destinations
- `FINAL_REVIEW.md` — review, cutover, and go-live record
- `APPROVAL_PASS.md` — operator sign-off packet for wording and runtime-position decisions
- `cron/trading-bot-daily-scan.template.json` — monorepo-managed cron template source
- `config/README.md` — sanitized config reference area

## Current Status

> **Deprecated (2026-07-25) — this section describes March 2026, not today.**
> Every "live" claim below is stale: OpenClaw is not installed on the current
> host (no `~/.openclaw/`, no scheduled job, nothing deployed), the daily scan
> has not run since 2026-04-24, and `qwen2.5:7b` is no longer installed in
> Ollama. Treat the list as a record of the March cutover. Whether OpenClaw is
> redeployed at all is an open question — see Phase 3 in `todo.md`.

- controlled cutover completed on March 8, 2026
- approved workspace files from this folder were deployed into `~/.openclaw/workspace/`
- the live trading job now points at the wrapper-script flow under `~/trading-bot/monorepo-staging/`
- the live trading job was enabled after verification and pre-enable backup
- the live OpenClaw default operator-chat model was switched to `ollama/qwen2.5:7b`
- Telegram `/bot` requests now bypass the ambiguous skill path and route through the native workspace command plugin

## Important Rule

The files in this folder are the repository-managed source of truth for the deployed OpenClaw trading-bot contract, but the live runtime still executes the copied versions under `~/.openclaw/`.

Operational edits should be made here first and then deployed deliberately rather than patched directly in `~/.openclaw/` without record.

When workspace behavior changes include native commands, sync both the tracked workspace markdown files and the tracked `.openclaw/extensions/` tree into the deployed runtime.

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
- native `/bot` command registration and repo-to-runtime workspace extension deployment
- default operator-chat model routing

The trading-bot app under `apps/trading-bot/` owns:

- scan execution
- guardrails
- broker and model integrations
- runtime summaries and logs

## Model Boundary

> **Deprecated (2026-07-25).** Two of the three lines below are stale.
> `qwen2.5:7b` is no longer installed in Ollama, and OpenClaw itself is not
> installed on the current host. The local analysis path now runs
> `gemma4:e4b-mlx` (see `apps/trading-bot/config/strategy.local.json`). The
> operator-chat line is left unchanged rather than repointed, because the
> agent-harness decision is still open — see Phase 3 in `todo.md`. Only the
> Claude decision-path boundary below is still accurate.

- default OpenClaw operator chat: `ollama/qwen2.5:7b`
- explicit trading decision path inside the Python runtime: Anthropic/Claude
- local prefilter and monitoring path: Ollama/qwen
