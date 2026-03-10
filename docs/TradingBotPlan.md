# Trading Bot Implementation Plan
*Updated March 9, 2026 — Reflects the live monorepo runtime, post-cutover status, and current paper-trading phase*

---

## Hardware & Deployment

The bot runs on a dedicated **Mac Mini M4 (16GB RAM)** as an always-on local machine. There is no VPS phase — the Mac Mini replaces that need entirely, running 24/7 at no additional infrastructure cost.

**OpenClaw** is the agent platform, running natively on the Mac Mini. It handles agent orchestration, Telegram integration, and Claude API connectivity out of the box, eliminating the need to build custom agent infrastructure from scratch.

## Current Repository Reality

The repository has moved beyond the original single-root implementation plan.

- the active scheduled runtime now lives under `monorepo-staging/`
- OpenClaw is the outer runtime and Telegram/operator interface
- the Python trading engine now runs through wrapper scripts rather than direct `main.py` execution
- the legacy root-level implementation remains available as historical reference and fallback context, but it is no longer the intended scheduled path

The current managed live path is:

1. OpenClaw cron job `trading-bot-daily-scan`
2. wrapper execution via `monorepo-staging/scripts/run_trading_bot_rehearsal.sh`
3. operator summary delivery via `monorepo-staging/scripts/print_trading_bot_operator_summary.sh`

---

## Phase 1: Foundation Setup

### 1.1 Platform & Environment

- Install **OpenClaw** on Mac Mini M4
- Install **Ollama** for local model inference (continuous monitoring layer)
- Install Python 3.10+ with a virtual environment
- Key libraries:
  - `alpaca-trade-api` — stock trading
  - `pandas` and `numpy` — data analysis
  - `python-dotenv` — secure credential management

### 1.2 API & Credentials

- **Anthropic API key** — for Claude (daily trading decisions only)
- **Alpaca API key + secret** — stored in `.env`, never committed to git
- Credentials managed via **Bitwarden**; Gmail aliases used per service for organization

> **Cost tip from video:** Consider routing Claude through **Open Router** with a weekly credit cap (e.g. $10/week) instead of directly through the Anthropic API. This gives you model flexibility and a built-in spending guardrail in one place.

---

## Phase 2: Broker Setup

### Alpaca (Stocks Only — Crypto Excluded)

1. Account created at [alpaca.markets](https://alpaca.markets)
2. Paper trading enabled — $100,000 simulated balance
3. API key and secret stored in `.env`
4. No crypto exchange needed — stock trading only

---

## Phase 3: Dual-Model Agent Architecture

This is the core architectural decision. Two models handle different layers of the bot, splitting tasks by cost and complexity.

### 3.1 Ollama (Local — Free)
Handles **continuous event monitoring** between market hours and during the trading day. Runs entirely on the Mac Mini with no API calls, no cost.

Responsibilities:
- Watch for price alerts and threshold triggers on watchlist stocks
- Monitor Alpaca account for unexpected activity
- Pre-filter market data before passing to Claude
- Queue up signals for Claude's daily review

### 3.2 Claude API via OpenClaw (Daily — Paid)
Handles **trading decisions** that require high-quality reasoning. Called once per day (or on a confirmed signal), not continuously.

Responsibilities:
- Analyze pre-filtered signals from Ollama
- Apply strategy rules and make buy/sell decisions
- Log reasoning behind each trade
- Send Telegram notifications via OpenClaw

### 3.3 Model Tiering Within Claude Calls (Video Optimization)

Not every Claude call needs the same model. Map task complexity to cost:

| Task | Recommended Model | Reason |
|------|-------------------|--------|
| Daily market scan + decision | Claude Sonnet | High reasoning, moderate cost |
| Complex or high-conviction trade analysis | Claude Opus | Max quality, use sparingly |
| Routine summaries / portfolio check | Claude Haiku or Deepseek V3 | Cheap, sufficient for summaries |

Configure this in `strategy.json` so models can be swapped without touching code.

### 3.4 Agent Tools

| Tool | Description |
|------|-------------|
| `fetch_market_data(symbol, timeframe)` | Gets current price and technical indicators |
| `place_paper_trade(symbol, quantity, side, price)` | Executes the trade via Alpaca |
| `get_account_balance()` | Checks current portfolio value |
| `get_trade_history()` | Retrieves past trades for analysis |

---

## Phase 4: Trading Strategy

### Asset Universe — 12-Stock Watchlist

Diversified across five sectors, maximum **4 active positions** at any time:

| Sector | Stocks |
|--------|--------|
| Tech / AI | NVDA, MSFT |
| Healthcare | UNH, JNJ |
| Consumer Staples | KO, COST |
| Financials | JPM, V |
| Industrials | CAT, HON |
| Broad Market | BRK.B, SPY |

### Strategy: Swing Trading

**Target:** 15% annual return  
**Starting capital (live):** $1,000

**Entry Conditions (both required):**
- 20-day MA crosses above 50-day MA (confirmed crossover)
- RSI signal confirms (RSI < 30 oversold on entry)

**Exit Rules:**
- Profit target: **8–12%** gain
- Stop loss: **4–5%** drawdown
- Max 4 positions open simultaneously

### Paper-to-Live Thresholds (both must be met):
- Minimum **3.75% return** over 90 days of paper trading
- No more than **2 consecutive losing trades**

---

## Phase 5: Cost Optimization (Video Strategy Applied)

The original plan estimated $10–$50/month in Claude API costs. With the dual-model architecture and the following optimizations, the realistic target is **under $5/month**.

### 5.1 Context Window Resets
Add a session management rule to Claude's system prompt in OpenClaw: reset the session after 15–20 exchanges or 30 minutes of conversation. Since Claude is called daily rather than continuously, this mainly applies to longer analytical sessions. This alone can cut context overhead by ~50%.

### 5.2 Prompt Caching
The strategy rules, watchlist, and tool definitions are repeated in every Claude call. Prompt caching gives up to a **90% discount on repeated content**. Configure this in the Anthropic SDK or enable it via Open Router automatically.

### 5.3 Hard Daily API Guardrails
Add a `daily_api_call_limit` field to `strategy.json`. The bot should never exceed this regardless of signal volume. Suggested starting limit: **5 Claude calls per day** during paper trading.

### 5.4 Tool Output Efficiency
Instruct Claude in its system prompt to summarize large JSON responses from Alpaca (account data, trade history) rather than processing them in full. This keeps tokens lean when tools return verbose payloads.

### 5.5 Ollama as the Cost Shield
The most impactful optimization is already baked into the architecture — Ollama absorbs all continuous monitoring at zero API cost, meaning Claude is only called when there's actually something worth deciding. This is better than any caching or tiering trick.

---

## Phase 6: Project Structure

```
trading-bot/
├── docs/
│   └── TradingBotPlan.md
├── config/
│   └── strategy.json                  # legacy root config reference
├── logs/                              # legacy root logs
├── database/                          # legacy root database area
└── monorepo-staging/
  ├── README.md                      # active managed runtime overview
  ├── apps/
  │   └── trading-bot/
  │       ├── pyproject.toml
  │       ├── .env.example
  │       ├── config/
  │       │   ├── strategy.example.json
  │       │   └── strategy.local.json    # local-only runtime config
  │       ├── src/trading_bot/
  │       └── tests/
  ├── openclaw/                     # deployed OpenClaw-facing assets and cutover docs
  ├── runtime/                      # runtime state, deployment snapshots, logs, guardrails
  └── scripts/                      # canonical wrapper, summary, bootstrap, and test scripts
```

### Runtime Config Structure (Current Direction)

The live managed runtime now prefers the monorepo app-local config path:

- `monorepo-staging/apps/trading-bot/config/strategy.local.json` for local runtime config
- `monorepo-staging/apps/trading-bot/.env` for local secrets

The tracked example config remains the template for local operator files.

```json
{
  "watchlist": ["NVDA", "MSFT", "UNH", "JNJ", "KO", "COST", "JPM", "V", "CAT", "HON", "BRK.B", "SPY"],
  "max_positions": 4,
  "entry": {
    "ma_crossover": { "short": 20, "long": 50 },
    "rsi_threshold": 30
  },
  "exit": {
    "profit_target_pct": 10,
    "stop_loss_pct": 4.5
  },
  "models": {
    "daily_decision": "claude-sonnet-4-6",
    "complex_analysis": "claude-opus-4-6",
    "routine_summary": "claude-haiku-4-5",
    "monitoring": "ollama/llama3"
  },
  "cost_controls": {
    "daily_claude_call_limit": 5,
    "context_reset_after_exchanges": 20,
    "prompt_caching_enabled": true
  },
  "paper_to_live": {
    "min_return_pct": 3.75,
    "evaluation_days": 90,
    "max_consecutive_losses": 2
  }
}
```

---

## Cost Breakdown (Revised)

| Item | Cost | Notes |
|------|------|-------|
| Alpaca paper trading | Free | $100k simulated balance |
| Mac Mini M4 | $0/month | Already purchased, always-on |
| Ollama (local monitoring) | $0 | Runs locally, no API cost |
| Claude API (daily decisions) | ~$2–$5/month | With tiering, caching, and call limits |
| Open Router (optional) | $0 | Free routing layer, pay per use |
| **Total to start** | **~$2–$5/month** | |

---

## Current Status & Next Steps

*Last updated: March 9, 2026 — Monorepo cutover complete, paper-trade validation active*

**Completed:**
- Mac Mini M4 purchased and designated as trading machine
- macOS, Python 3.14, Node 22, VS Code, Git installed
- Alpaca account created with paper trading active ($100,000 balance)
- Anthropic API key acquired
- Bitwarden + Gmail alias credential system in place
- Strategy, watchlist, and paper-to-live thresholds defined
- OpenClaw 2026.3.1 installed, configured with Anthropic API key, running as background service (launchd, PID persistent across reboots)
- Ollama installed, `qwen2.5:7b` model running as background service
- Telegram bot (`@labanlarotrading_bot`) connected and responsive
- monorepo trading app created under `monorepo-staging/apps/trading-bot/`
- wrapper-script based runtime contract established under `monorepo-staging/scripts/`
- OpenClaw runtime assets, cutover checklist, runbook, and final review recorded under `monorepo-staging/openclaw/`
- controlled cutover to the monorepo runtime completed on March 8, 2026
- live OpenClaw trading job enabled on March 8, 2026 after verification and backup
- live OpenClaw default operator-chat model switched to `ollama/qwen2.5:7b`
- deterministic strategy engine, local analysis, optional Claude escalation, broker adapter, runtime logging, and guardrails are all ported into the monorepo app
- paper-trade execution was exercised successfully on March 9, 2026 with guardrails passing
- latest managed-runtime paper trades executed for `BRK.B` and `COST` with accepted paper orders

**Current Phase: Post-Cutover Validation And Paper Trading**

The repo is no longer in pre-cutover staging.
It is now in the managed-runtime validation phase:

| Area | Current State |
|------|---------------|
| OpenClaw runtime | live and cut over to monorepo assets |
| Scheduled job | enabled and wrapper-based |
| Operator summaries | generated from structured runtime artifacts |
| Guardrails | enforced for execution policy, sizing, trade counts, and final intent validation |
| Paper trading | active under the monorepo runtime |
| Live-capital trading | not approved |

**Still To Do:**
1. Monitor paper-trade performance and operator workflow under the live monorepo path
2. Decide the explicit approval gate for any live-capital promotion
3. Improve persistence and reporting beyond the current runtime logs and daily guardrail counters
4. Deploy live capital only after a separate go/no-go decision beyond paper-trade success

---

*The migration goal is complete. The current gate is no longer cutover readiness; it is whether guarded paper-trading results justify a future live-capital approval.*
