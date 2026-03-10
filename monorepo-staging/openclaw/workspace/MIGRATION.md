# MIGRATION.md

## Purpose

This file explains how OpenClaw should think about the completed transition into the monorepo-native trading platform and the remaining approval gates.

## Current State

### Active runtime path
- `~/trading-bot/monorepo-staging`

### Legacy root path
- `~/trading-bot`

## Rule

Do not confuse the active monorepo runtime with legacy root materials.

### Active system
The current OpenClaw cron and Telegram-facing workflow target the monorepo wrapper scripts.

### Current phase
Cutover completed on March 8, 2026. Paper-trade execution was exercised on March 9, 2026. Live-capital trading remains a separate gate.

## Cutover Principle

OpenClaw should treat cutover as complete, but should still keep the remaining gate explicit:
- paper-trade results are monitored through runtime artifacts and broker state
- operator summaries come from the monorepo summary wrapper
- live-capital authorization requires a separate explicit approval
