# Trading Bot Tests

This directory is reserved for tests for the rebuilt trading app.

## Initial priorities

- config loading
- signal gating behavior
- broker wrapper contracts
- logging and persistence behavior
- guardrail enforcement

## Current Test Coverage

- guardrail evaluation rules
- Claude daily call limit blocking
- trade-limit blocking
- max-position blocking
- safe-mode execution blocking in the staged daily scan flow

## Current Runner

```bash
cd ~/trading-bot/monorepo-staging
./scripts/run_trading_bot_tests.sh
```
