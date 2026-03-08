# External Config Templates
*Last updated: March 8, 2026*

## Purpose

This folder is reserved for **sanitized** templates and notes for configuration or runtime artifacts that live **outside** this repository.

Do **not** store secrets here.

## Expected Future Contents

Examples of files or templates that may belong here later:
- redacted OpenClaw main config structure
- redacted auth profile structure
- redacted `SOUL.md` template
- redacted `TOOLS.md` template
- redacted `HEARTBEAT.md` template
- launchd or scheduler template notes
- Telegram pairing/state notes without private identifiers

## Current Contents

- [openclaw.template.json](openclaw.template.json) — sanitized structure from the live `~/.openclaw/openclaw.json`
- [auth-profiles.template.json](auth-profiles.template.json) — sanitized structure from the live auth profiles file
- [cron-jobs.template.json](cron-jobs.template.json) — sanitized structure from the live OpenClaw cron job definition
- [TOOLS.template.md](TOOLS.template.md) — sanitized summary of live trading-bot workspace instructions
- [HEARTBEAT.template.md](HEARTBEAT.template.md) — sanitized summary of live heartbeat checks for the trading bot
- [SOUL.notes.md](SOUL.notes.md) — verified notes about the live `SOUL.md` role in the runtime

## Rules

- Never commit API keys, tokens, chat IDs, or credentials
- Document file paths, field meanings, and ownership instead of secret values
- Link each template back to the live file location in [../Operations.md](../Operations.md)
- Prefer placeholders like `YOUR_TOKEN_HERE` or `[REDACTED]`

## Status

Initial sanitized templates have been created from the March 8, 2026 live audit.
The next step is to add any additional safe templates needed after reviewing the remaining unknowns around Telegram policy, gateway settings, and restart behavior.
