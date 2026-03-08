# Trading Bot Config

This directory will hold the future runtime configuration for the rebuilt trading app.

## Rebuild Goal

Move strategy, model selection, limits, and runtime settings into a real configuration system here instead of splitting authority across docs, JSON, and hardcoded Python constants.

## Current Staged Contract

- tracked template: [strategy.example.json](strategy.example.json)
- preferred local rehearsal file: `strategy.local.json`

The staged app now prefers `strategy.local.json` when it exists and falls back to [strategy.example.json](strategy.example.json) otherwise.

Keep `strategy.local.json` safe-mode oriented during rehearsal work and do not commit it.
