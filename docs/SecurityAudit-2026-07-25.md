# Guardrails drift audit — 2026-07-25

First audit of `docs/Security.md` against the implementation since the
2026-03-09 refactor. Security.md was written 2026-03-03 against the *legacy*
single-script bot (`trader_agent.py`, `main.py`), which no longer exists.

**Headline: every trading guardrail it specifies is implemented and enforced.
The drift is in the operational sections, and one item is a safety defect.**

---

## Verified implemented

| Control | Documented | Implementation |
|---|---|---|
| Max simultaneous positions | 4 | `guardrails.evaluate_trade_limits` |
| Max trades per day | 2 | same; counter increments and rolls over daily |
| Max position size | 25% | `trade_execution.calculate_qty` |
| Stop loss | 4–5% | `strategy_engine._exit_reason` (configured 4.5%) |
| Profit target | 8–12% | same (configured 10%) |
| Claude calls per day | 5 | `guardrails.evaluate_claude_call_limit` |
| Ollama gates Claude | required | `model_router.should_escalate_to_claude` returns False when local analysis is unavailable |
| `.env` gitignored | required | confirmed |
| No keys in git history | required | confirmed — a pattern scan returned 3 hits, all HTTP header *names* (`"APCA-API-KEY-ID": self.api_key`), no values |

The daily counter self-heals: `GuardrailStateStore.load()` discards state whose
`current_date` is not today, so the stale `2026-04-08` value on disk cannot
wrongly block or permit anything.

## Controls that exist but are not documented

Drift in the safe direction — the system enforces more than the doc claims:

- `execution_policy` — safe-mode and paper-execution flags gate all execution
- `execution_intent_firewall` — blocks duplicate executable symbols, buys into
  existing positions when pyramiding is disabled, sells with no position, and
  sells exceeding position size
- ZeroClaw risk profile — deny-by-default command allowlist, filesystem roots
  confined to the repo, macOS Seatbelt sandbox, gateway bound to loopback with
  pairing required, secrets encrypted at rest, `zeroclaw estop`

## Defect: the documented kill switch does not work

`Security.md` Test 7 instructs:

```bash
launchctl unload ~/Library/LaunchAgents/ai.openclaw.gateway.plist
```

OpenClaw is not installed. The live service is `com.zeroclaw.daemon`. **Anyone
following the documented emergency procedure would fail to stop the bot** and
would likely believe they had succeeded, since the command exits without error
on a missing plist.

Corrected, and **executed for the first time** — Test 7 had never been run.
Doing so surfaced two further defects that documentation review alone would
not have found:

- `security.estop.enabled` defaults to **false**. `zeroclaw estop` returns
  "Emergency stop is disabled" and halts nothing.
- `security.estop.require_otp_to_resume` defaults to **true**, and resume
  then fails against a disabled OTP config — **engaging the kill switch locks
  you out of releasing it.** The audit hit this live and had to repair a
  stuck estop state.

Both are now set in `zeroclaw/config/config.template.toml`. With them fixed,
the full cycle measured **1s to stop, 6s to restore**, against a documented
60-second criterion. Test 7: **PASS**.

## Documented but not implemented

1. **Paper-to-live gate is only half-computable.** `read_model.gate_metrics()`
   returns return-pct and drawdown but deliberately refuses consecutive losing
   trades, which needs realized round-trip P/L. `services/reconciliation.py`
   now computes it (`max_consecutive_losses`), but nothing automatically
   evaluates both halves against the thresholds and reports pass/fail.
2. **Heartbeat monitoring** ("Heartbeat confirmed monitoring trades.log for
   errors") — does not exist. `zeroclaw doctor` reports scheduler freshness
   but only when asked; nothing pushes an alert. This is the gap that let the
   2026-04-24 stop go unnoticed for three months.
3. **`logs/incidents.log`** — referenced by Incident Response, never created.
4. **Trading boundaries in `SOUL.md`** — the persona files still live in
   `openclaw/workspace/` and have not been deployed to the ZeroClaw agent.
5. **Anthropic monthly spend limit** — external to this repo, unverifiable
   here. Still worth confirming in the console.

## Stale references (OpenClaw-era, now wrong)

- Telegram pairing check reads `~/.openclaw/telegram/paired-users.json`.
  Reality: ZeroClaw stores operator bindings under `[peer_groups.*]` in
  `/opt/homebrew/var/zeroclaw/config.toml`; inspect with `zeroclaw channel list`.
- The credential table lists `~/.openclaw/openclaw.json` and
  `auth-profiles.json`. Reality: Alpaca and Anthropic keys are in
  `apps/trading-bot/.env`; the Telegram token is encrypted (`enc2:` prefix) in
  the ZeroClaw config.
- §1.1/§1.2 attribute enforcement to `trader_agent.py` and `main.py`. Those
  files no longer exist; enforcement is in `services/guardrails.py` and
  `services/trade_execution.py`.
- §1.3 "OpenClaw Containment" is superseded by the ZeroClaw risk profile,
  which enforces its rules mechanically rather than by prompt instruction.

## Divergences worth an explicit decision

1. **`max_trades_per_day` restricts buys only.** Sells are never blocked — a
   sound choice, since exits should always be possible. But sells *do* consume
   the budget (`increment_trades(len(order_results))` counts both sides), so
   two exits can exhaust the day's allowance and block entries. Defensible,
   currently undocumented.
2. **Position sizing uses `portfolio_value`, not buying power.** The paper
   account shows $275k buying power against a $97k portfolio, i.e. margin is
   available. Nothing in the code or the doc prevents a position being opened
   on margin. Harmless on paper; **must be settled before live capital**,
   especially against the documented "$1,000 funded at launch".

## Test status

| Test | Status |
|---|---|
| 1 — daily trade limit | unit coverage in suite (106 tests) |
| 2 — Claude call limit | unit coverage |
| 3 — stop loss execution | unit coverage, plus confirmed against a **real fill**: BRK.B stopped out at −4.89% |
| 4 — unpaired Telegram user | **not performed** (needs a second account) |
| 5 — Ollama pre-filter gate | unit coverage |
| 6 — config modification refusal | **not performed**; largely superseded by the ZeroClaw allowlist, which cannot execute an editor at all |
| 7 — kill switch | **PASS — executed 2026-07-25**, 1s stop / 6s restore |

Test 7 is the one worth highlighting: it had never been run, the documented
procedure was broken, and running it uncovered two further defects that no
amount of reading would have surfaced.
