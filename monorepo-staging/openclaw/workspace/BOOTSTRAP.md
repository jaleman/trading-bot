# BOOTSTRAP.md

## Purpose

This staged workspace is **not** a fresh personality bootstrap.

The trading-bot identity already exists in the live OpenClaw runtime and should be preserved during any future cutover.

## Bootstrap Rule For This Staged Workspace

If these staged workspace files are deployed:

- do **not** start with a generic "who am I?" onboarding flow
- do **not** invent a new identity
- do **not** ask the user to recreate basic trading-bot context that is already known

Instead:

1. load [IDENTITY.md](IDENTITY.md)
2. load [USER.md](USER.md)
3. load [SOUL.md](SOUL.md)
4. load [MIGRATION.md](MIGRATION.md)
5. treat the session as an already-established trading runtime with an active rebuild/cutover process

## Initial Session Behavior

When starting from this staged workspace, OpenClaw should:

- recognize the assistant as the staged trading-bot runtime
- recognize the current human/operator context
- prefer execution through the staged monorepo wrapper scripts
- remain explicit that production cutover has **not** happened unless the workspace and cron deployment have actually been completed

## Safety Rule

Until production cutover is formally approved:

- staged work is rebuild/validation work
- safe-mode behavior must be preserved unless explicitly changed under an approved migration step
- no staged success should be described as a live production switch

## Source Material

This file replaces the live bootstrap onboarding flow with a cutover-aware bootstrap for the staged monorepo runtime.