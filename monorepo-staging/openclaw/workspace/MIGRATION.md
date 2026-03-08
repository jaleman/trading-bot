# MIGRATION.md

## Purpose

This file explains how OpenClaw should think about the transition from the current live trading bot to the future monorepo-native trading platform.

## Current State

### Live production path
- `~/trading-bot`

### Staged rebuild path
- `~/trading-bot/monorepo-staging`

## Rule

Do not confuse the two.

### Live system
The current OpenClaw cron and Telegram-facing workflow still target the live repo.

### Staged system
The staged monorepo exists for rebuild work, validation, and future cutover preparation.

## Cutover Principle

OpenClaw should only be switched to the staged/monorepo-native commands after:
- rebuild docs are complete
- staged app behavior is validated
- safety controls are validated
- migration commands and rollback steps are documented
