# Next Steps

Updated: 2026-07-25 (Phase 0/1 reassessment session — see WORKFLOW.md)

## Goals

- **North star**: reach the live-capital approval gate with a clean audit
  trail (≥3.75% return over 90 days, ≤2 consecutive losing trades) —
  confirmed as still the target in the 2026-07-25 reassessment session.
- **Current milestone**: harden reliability (Ollama timeout margin, market
  data adapter retries) and decide the OpenClaw-vs-lighter-harness question
  before redeploying and restarting the 90-day clock.
- **Next action (2026-07-26): step 5 done — apply the cron jobs.**
  Steps 1–5 of the agreed plan are complete. What remains:

  1. ~~Supervised end-to-end rehearsal + Telegram delivery.~~ **DONE
     2026-07-26** — see "Step 5 supervised rehearsal" below. It found and
     fixed a defect that would have made the scheduled job never trade.
  2. Apply the three cron jobs together — scan **09:45**, Drive backup 10:15,
     watchdog 11:00 — via `sync_zeroclaw_config.sh --with-cron` plus the two
     companion jobs in `zeroclaw/cron/trading-bot-daily-scan.md`. Safe to run
     unattended: see "Unattended-safe activation" below.
  3. Record the clock-start date and baseline portfolio value so
     `gate_metrics` measures the right window. **The dormancy cleanup already
     happened** — PFE and COST were sold during the 2026-07-26 rehearsal, so
     those two realised losses land on 07-26 and are *not* strategy results.
     Start the measurement window after them.
  4. Then steps 6–7: the strategy plug-in interface, and the shadow advisor
     — design note for step 7 is below ("Step 7 design note — shadow advisor
     decision capture"), and it is deliberately sequenced *after* activation.

### Harness hardening complete (2026-07-25/26)
- Scheduling, crash recovery, staleness reporting: ZeroClaw, all verified
- Daily summary out: agent-free `channel send`, ~1s, zero trace events
- Failure alerting: scan failures send the traceback and exit non-zero
- `/bot` commands in: dedicated poller, sub-second, deny-by-default
- Kill switch: repaired and tested, 1s stop / 6s restore
- No-margin, long-only: enforced at the broker *and* in code
- Staleness watchdog: counts missed trading weekdays
- **Mac sleep was set to 1 minute**, held awake only by a "display is on"
  assertion — turning the monitor off would have stopped the scan. Now
  `pmset sleep 0`.

## Phase 1.5 — Audit-grade logging (added 2026-07-25)

Added ahead of Phase 2/3 because the 90-day validation clock is about to
restart: instrument the experiment before running it. Scans that run before
this lands produce evidence that cannot be trusted or queried. Alerting is
also downstream — a failure path that writes nothing cannot be alerted on.

**What is authoritative where** (this drives the whole design):
- **Alpaca is the system of record for *what* happened** — orders, fills,
  tax documents. Do not rebuild durable trade storage; it already exists.
- **This app is the only record of *why*.** 88% of each log entry is
  `strategy_evaluation` (13.8 KB) + `indicator_snapshots` (13.5 KB, 50
  symbols) — market state at decision time, which no historical API can
  reconstruct accurately afterward. That is the irreplaceable asset.

**Storage model:** `trades.jsonl` stays the append-only source of truth (a
corrupt line costs one run; a database fails as a unit). SQLite will be a
*derived, rebuildable* read model for queries and gate metrics — never
authoritative, so its schema can change freely.

**Not in scope:** WORM, hash chains, tamper-evidence, OpenTelemetry. This is
a personal single-user paper-trading bot, not a broker-dealer or registered
adviser, so SEC 17a-4 / FINRA books-and-records do not apply. Revisit only
if meaningful real capital is ever deployed.

### Done (2026-07-25)
- **Append-only writes.** `TradeLogger.log_message` previously did
  `write_text(read_text() + entry)` for *every line* — quadratic, and a
  failure mid-write truncated the entire history. Now opens in append mode
  with `flush()` + `os.fsync()`, so a kill or power loss keeps what was
  written. Verified against the real 811-line April log: all prior lines
  byte-identical after an append.
- **Crash evidence.** All logging previously ran *after* a successful scan,
  so a crash produced zero record — not even that the scan started. The
  start marker is now written before any work, and the scan body is wrapped
  so a failure logs partial progress, the exception, a full traceback, and a
  `FAILED` marker before re-raising.
- **Run IDs.** Every log line and JSONL entry carries a sortable run ID
  (`20260725-133759-6be2`) so one run correlates across both files.
- **Bug found by the new tests:** `TradeLogger` did not coerce `log_path` to
  `Path`, so a string path crashed on `.parent`. Now coerced.
- 66 tests pass (8 new), including a subprocess test that SIGKILLs a run
  mid-write and asserts the lines already written survive.

- **SQLite read model** (`persistence/read_model.py`, run via
  `scripts/run_trading_bot_read_model.sh {rebuild|metrics|query}`). Derived
  and disposable — `rebuild` drops and replays from `trades.jsonl`, so the
  schema can change freely. Tables: runs, decisions, positions, indicators,
  guardrails. Rebuilt cleanly from the real 45-run April history with zero
  skipped lines (372 KB db vs 1.0 MB source log). Entries predating run IDs
  get stable synthetic `legacy-*` ids so rebuilds stay idempotent.
  `gate_metrics` deliberately refuses to report consecutive losing *trades*:
  that needs realized round-trip P/L and Alpaca is the system of record for
  fills, so inferring it here would be presenting inference as fact.

### What the April history actually shows (now queryable)

Rebuilding surfaced things that were impractical to see before:

- **Return +2.24%** over 2026-03-08 → 04-24, peak $102,932.51, max drawdown
  from peak −2.93%.
- **51 decisions produced only 8 orders.** `trade_execution_limits` blocked
  7 of 15 evaluations — every other guardrail blocked nothing. So the
  binding constraint on the strategy was `max_positions: 4`, not signal
  generation. The same buy candidates (UPS, MMM, CAT) recur across
  consecutive days because the decision regenerated daily while the position
  cap kept rejecting it.
- Entry signals fired at genuinely deep oversold levels — UPS at RSI 19.0
  with a −12.66% 5-day return, MMM at RSI 21.4.
- Two runs carry no portfolio value; both are 2026-03-08 `scaffold-only`
  runs from before broker context was wired in, not failures.
- Older entries have null `volatility_20d` / `recent_return_5d` (fields
  added in the March 9 refactor), so the schema tolerates nulls.

## Step 5 supervised rehearsal — 2026-07-26

Run supervised, on a Sunday, market closed. **Two runs**: a dry run, then an
executing one after fixing what the dry run exposed.

### The defect: the scheduled job would never have traded

`run_trading_bot_daily.sh` invoked `run_trading_bot_rehearsal.sh` with no
arguments. `--rehearsal` sets the four `include_*` flags but deliberately
**not** `execute_paper_trades` (`cli.py:82`, help text: "without forcing
paper-trade execution"), and the whole execution branch —
`build_order_results` → `broker.place_paper_trade`, plus
`evaluate_execution_policy`, `evaluate_position_size`,
`evaluate_trade_limits` and `validate_execution_intents` — sits behind
`if execute_paper_trades:` at `daily_scan.py:349`.

So the 09:35 cron would have scanned, decided *sell PFE, sell COST*, placed
nothing, and reported `Trading scan completed. Guardrails passed.` every
morning. **The signature failure of this project, with a green light on it** —
and harder to catch than the April silence, because absence of a message is
noticeable and a daily healthy message is not.

Only `daily_claude_call_limit` appeared in the guardrail record. The other
four never evaluated, so they would have produced no evidence across the
90-day window despite being correctly implemented.

`--dry-run` was *not* what suppressed execution: it only gated `notify()`.

### Fixed

`run_trading_bot_daily.sh` now passes `--execute-paper-trades` on the real
path, and `--dry-run` suppresses execution as well as delivery — a flag by
that name that still placed orders is a trap. Header comment records why.

### Verified

| | dry run `20260726-001739-da0f` | executing `20260726-002430-aa41` |
|---|---|---|
| status | `production-candidate` | `production-candidate-paper-trades-executed` |
| guardrails evaluated | 1 | **5**, all passed |
| orders | `[]` | PFE 914 sell, COST 24 sell — both `accepted` |

Confirmed at the broker: `print_trading_bot_pending_orders.sh` went from "No
pending orders" to both sells queued. Market closed, so they fill at Monday's
open — **fill prices will differ from the Friday closes the decision was made
against.**

Telegram delivery confirmed received on device, `channel send` in 0.7s, no
agent in the path. The operator summary correctly leads with "Executed 2
paper-trade order(s)"; when nothing executes it omits that clause.

### Notes for the next run

- `trades_today: 2` — the day's budget is **exhausted by two sells**. This is
  the documented divergence (`max_trades_per_day` restricts buys, but sells
  consume the allowance) now demonstrated live: Claude skipped ABBV, JNJ and
  LLY explicitly citing the exhausted limit. Monday's scan starts fresh.
- Claude calls: 2 of 5 used on 07-26.
- Telegram is **wired** — `channel list` shows it green and both env vars are
  set. Adoption checklist item 4 and "no channels configured" in the Phase 3
  section are stale; Telegram needs no further work.

## Unattended-safe activation — 2026-07-26

The operator may not be at the keyboard for the first scheduled run. Rather
than schedule around that, the two things that made supervision necessary
were fixed. **Supervision is now optional.**

### 1. The firewall could not see working orders

`validate_execution_intents` checked positions only, and `PositionSnapshot`
carries `qty` with no `qty_available`. A working sell still shows its shares
in the position, so every check passed for a symbol already being sold: the
scan would re-decide the exit and submit it twice. Nothing in this process
prevented that — rejection depended on the broker noticing the shares were
held, which is luck, not a control.

Fixed: `broker.get_open_orders()` (which already existed, used by `/bot
pending`) is now fetched with positions and passed to the firewall, which
blocks any buy or sell whose symbol has a working order. The guardrail record
carries `pending_order_symbols`.

Positions and orders are committed together deliberately — the firewall fails
open without the orders, so a partial fetch yielding positions but no orders
would silently restore the bug.

**Verified against live broker state** while PFE and COST had working sells,
read-only, nothing submitted:

```
working orders  : COST SELL ACCEPTED, PFE SELL ACCEPTED
with the fix    : blocked PFE, blocked COST, allowed ABBV (no working order)
without the fix : would have submitted PFE, COST and ABBV
```

4 new tests; 149 pass.

### 2. `--with-cron` scheduled the wrong script

`sync_zeroclaw_config.sh` set `SCAN` to `run_trading_bot_rehearsal.sh`, not
`run_trading_bot_daily.sh`. The rehearsal script neither executes nor reports,
so applying the cron *as documented* would have bypassed the
`--execute-paper-trades` fix **and** delivered no Telegram summary — the
identical silent-failure shape, one layer down. Same root cause as the step 5
defect: `rehearsal` and `daily` are easy to confuse and only one of them
trades.

### 3. Scan moved 09:35 → 09:45

Defence in depth, not the fix. Nothing about a daily close-based strategy
needs the earlier slot, and 09:35 sat inside the window where orders from the
open may still be filling. Also keeps entries out of the opening auction's
spread. The 11:00 watchdog deadline is unaffected; its comments and test
docstrings were resynced.

### Also corrected

The cron doc claimed `run_trading_bot_log_maintenance.sh` had to be added to
`allowed_commands` before the backup job could be scheduled. It and
`run_trading_bot_watchdog.sh` are **already allowlisted** in
`config.template.toml`; no risk-profile change is needed.

### Remaining rough edge

`--with-cron` applies only the scan. The backup (10:15) and watchdog (11:00)
jobs still have to be added by hand from
`zeroclaw/cron/trading-bot-daily-scan.md`. Worth folding into the script so
"apply the three together" is one command that cannot half-succeed.

## Step 7 design note — shadow advisor decision capture (2026-07-26)

Question raised: should the daily scan capture decision, strategy, the order
sent to Alpaca, results and summary into a log that the shadow advisor can
analyse? **Yes — but the logging is ~85% built already, and treating this as
a new logging project would rebuild what Phase 1.5 landed.** The actual work
is one narrow gap.

### What each scan already writes

`DailyScanSummary` (`models.py:250`) is serialised whole into `trades.jsonl`
every run and projected into the read model. It already carries
`strategy_file` and `strategy_evaluation`, `decisions`, `order_results`,
`notes`/`triggered`/`watching`, `indicator_snapshots` for all 50 symbols,
`account`, `positions`, `guardrail_state` and `guardrails` — correlated by
run ID across `trades.log` and `trades.jsonl`.

### The useful accident: three opinions per run, already separated

The fields do not overwrite each other, so each run records what every
opinion source wanted, independently:

| source | field |
|---|---|
| deterministic `entry_score` ordering | `strategy_evaluation.entry_decisions` |
| Ollama ranking, with confidence | `local_analysis.ranked_candidates` |
| Claude's reviewed list (escalation only) | `decisions` |

Claude replaces `decisions` wholesale at `daily_scan.py:334`, but the
deterministic and local rankings survive alongside it. Combined with
`indicator_snapshots` covering the whole universe daily — which accumulates
a forward price series for symbols that were *not* bought — the disagreement
between sources and the counterfactual outcome of the road not taken are
both already recoverable. **This is the main reason not to redesign the
logging: the shadow-advisor dataset is largely emergent from what Phase 1.5
already captures.**

### The one real gap: no outcome to score against

`OrderResult` (`models.py:163`) is `id, symbol, qty, side, status` — no fill
price, no fill timestamp — and status is recorded at submission, which is why
6 of 8 historical orders read `PENDING_NEW`. `services/reconciliation.py`
computes fills and FIFO round-trip P/L correctly, but it is an on-demand
script whose output is written nowhere.

So the log holds three opinions per day and **no scoring key**. Everything
else in the original question is already captured; this is not.

Two narrow additions close it:

1. Carry fill price, filled qty and fill timestamp on `OrderResult`.
2. Persist reconciliation's per-run realized P/L back into the JSONL, or as a
   read-model table, so decisions join to outcomes without an ad-hoc query.

### Framing: disagreement log first, scoreboard much later

The April window produced **8 orders across 45 runs**. Ninety days at
`max_trades_per_day: 2` against a 4-slot cap plausibly yields round trips in
the low tens. That supports forensics — *why was this trade taken, and did
the sources disagree* — and does **not** support ranking advisors against
each other with statistical confidence. Decide this now rather than
discovering it in October. Same instinct as `gate_metrics` refusing to
compute consecutive losses: do not present inference as fact.

Also price in that a shadow advisor running daily makes a Claude call on days
escalation would not have fired, against the 5/day limit and the monthly cap
that is still unverified in the console (open item from the drift audit).

### Sequencing

**Not before activation.** Closing the outcome loop modifies `OrderResult`,
which is on the live execution path; step 5 should not carry an unrelated
change to it. Do this after the cron jobs are applied and the clock has
started — the additions are additive to the schema, and the read model is
rebuildable, so nothing is lost by capturing outcomes from day N rather than
day 1.

## OPEN DECISION: position cap, concentration, and selection order

Flagged 2026-07-25 as important, deliberately **not** acted on yet. This
bears directly on whether the 90-day gate will mean anything.

### The obvious reading is wrong

"The cap cost us 43 trades" is not what happened. The portfolio was **fully
deployed** — 1.8% cash, 4 of 4 slots filled, every day through the back half
of the window. `max_positions: 4` × `max_position_size_pct: 25` = exactly
100%. There was no idle capital to take those trades with.

So the cap did not limit *participation*. It set **concentration**.

### The real policy question

Is 4 × 25% the right risk posture, versus something like 8 × 12.5%?

Concrete stakes: a −10% move on a 25% position costs 2.5% of the portfolio.
PFE's −9.95% cost roughly that. At 8 × 12.5% the same move costs 1.24%. But
more diversification also dilutes winners, so this is a genuine tradeoff and
not an obvious improvement in either direction. It should be decided
deliberately, not inherited.

### CORRECTED 2026-07-25 — the earlier "alphabet decides" claim was wrong

An earlier version of this section asserted that the alphabet decides which
positions are held. **That was substantially wrong**, and checking the actual
run data disproved it. Recording the correction rather than quietly editing.

What is genuinely true:

- `guardrails.py:45` does take `buy_decisions[:buy_allowance]` — the first N
  in list order, not the best N.
- `strategy_engine` emits `entry_decisions` in **alphabetical** universe order,
  and the deterministic `entry_score` is never used to sort them.
- The *local* model's `ranked_candidates` really is used only for log notes
  (`daily_scan.py:280-287`) and never reorders anything.

**But Claude escalation reorders the decision list before guardrails see it.**
`daily_scan.py:334` replaces `decisions` wholesale with Claude's reviewed
output, and `should_escalate_to_claude` (`model_router.py:25-32`) fires
precisely when selection matters — when buy candidates exceed remaining
slots, or when few slots remain with multiple candidates.

Confirmed in the real 2026-03-30 run: 3 positions held, 1 slot free, CSCO and
NEE both eligible. Claude chose NEE — *"best candidate for the single
remaining portfolio slot"* — and skipped CSCO as *"no portfolio capacity
remains after filling the open slot with the higher-conviction NEE trade."*
Alpaca confirms NEE filled at $92.62 that day. Alphabetical order would have
taken CSCO. Claude's pick also matched the deterministic score (NEE 3.60 vs
CSCO 1.12), which is a good independent signal that the routing works.

### The real, narrower gap

Selection is quality-driven **only when Claude escalation fires**. It falls
back to alphabetical whenever escalation does not, and there are four such
paths:

1. the daily Claude call limit (5/day) is exhausted
2. the Claude API errors or is unreachable
3. `claude_escalation_enabled` is false
4. local analysis is unavailable — which is what `should_escalate_to_claude`
   returns `False` for at `model_router.py:15-16`

Path 4 is the concerning one: **the Ollama timeouts seen throughout April
disabled local analysis, which in turn suppressed Claude escalation**, which
would have silently dropped selection back to alphabetical on exactly those
days. The fix landed 2026-07-25 makes this far less likely, but the fallback
remains unprincipled.

### Measured impact on the April window

Across 45 runs, only **10** had 2+ competing buy candidates, and of those only
**one** (2026-03-30) had more candidates than slots *and* actually executed —
and Claude handled it correctly. So the alphabetical fallback appears to have
cost nothing measurable in the recorded history. The concern is forward-looking
robustness, not a realised loss.

### Why this still matters for the gate

The +2.24% result measures "entry rules + 4×25% concentration + a selection
path that is quality-driven when Claude runs and alphabetical when it does
not." The concentration question stands on its own regardless. The selection
fallback matters less than first thought, but it is still an unprincipled
path that activates exactly when other things are already going wrong.

### DONE 2026-07-25 — entries are now ranked by score

`evaluate_strategy` sorts `entry_decisions` by the candidate's `entry_score`
descending before returning (`strategy_engine.py`, just before the
`StrategyEvaluation` return). Guardrails' `buy_decisions[:allowance]` now
takes the strongest candidates instead of the alphabetically-first ones.

Not literally one line: `TradeDecision` carries no score, so the sort joins
back to `candidates` by symbol. The sort is **stable**, so equal scores keep
alphabetical order and runs stay deterministic.

This is a *fallback-quality* fix, not a redesign — Claude escalation still
reorders on contested slots when it runs, and that path was already working.
What changes is the path taken when escalation does not fire.

Verified by replaying the real 2026-03-30 scan through the fixed code:

```
entry_decisions order : ['NEE', 'CSCO']     (was ['CSCO', 'NEE'])
scores                : {'NEE': 3.6, 'CSCO': 1.12}
guardrail would take  : ['NEE']  with 1 slot free
```

which now matches, without any model call, what Claude chose that day and
what Alpaca confirms actually filled ($92.62). The deterministic fallback and
the escalated path agree.

### DECIDED 2026-07-25 — concentration stays as-is, revisit later

`max_positions: 4` and `max_position_size_pct: 25` are **unchanged**. Locked
before the 90-day clock starts, deliberately: changing concentration
mid-window would confound the measurement the same way the logging gaps
would have.

**A correction that informed this.** An earlier note in this file said a −10%
single-name move costs 2.5% of the portfolio. That was misleading, because it
ignored the stop-loss:

| | outcome | portfolio impact |
|---|---|---|
| theoretical, stop fires | 4.5% × 25% | **−1.12%** |
| BRK.B — stop actually fired | −4.89% | **−1.21%** |
| PFE — stop never fired (bot dormant) | −9.95% | **−2.49%** |

The gap between −1.21% and −2.49% is **dormancy, not concentration**. With
daily scans running, the stop bounds per-name damage to roughly 1.1% of the
portfolio, and BRK.B shows that working on real fills. 4 × 25% with a 4.5%
stop is internally consistent *provided the exit machinery actually runs* —
which is what the Phase 1.5 and 2 reliability work buys.

When revisiting, note two system-level couplings: widening to 8 positions
collides with `max_trades_per_day: 2` (filling 8 slots takes 4+ days), and
raises Claude escalation frequency, since escalation fires when candidates
exceed free slots — which has cost implications against the 5-calls/day
budget. A parameter sweep was offered and deferred; it would need a real
backtester with forward prices and is path-dependent, so results would be
indicative rather than authoritative.

Also deferred: feeding the local model's `ranked_candidates` into ordering.
Not recommended — it would put an LLM in the selection path for routine runs,
which the current design deliberately avoids, and the deterministic score
already agrees with Claude's judgment in the one case we can check.

- **Operator activity logging.** `operator_commands.main()` now records every
  `/bot` invocation to a separate `logs/operator.log` — kept apart from
  `trades.log` so frequent commands do not drown the daily trading
  narrative. Logs invoked/completed/failed with the failure reason, sharing
  one run ID per command. Best-effort throughout: a logging failure (or an
  unavailable runtime) never breaks the command the operator is running,
  which is covered by tests. Only command names and outcomes are recorded —
  never env contents or credentials.
- **Rotation and backup** (`persistence/log_maintenance.py`, via
  `scripts/run_trading_bot_log_maintenance.sh {rotate|backup <dest>}`).
  Two deliberate asymmetries:
  - `trades.jsonl` is **never rotated**. Splitting the source of truth would
    silently orphan history from a read-model rebuild, and at ~5.6 MB/year
    retention is not a problem worth that risk.
  - Rotated archives are **never deleted**. `trades.log` holds crash
    tracebacks that the JSONL does not — the JSONL is only written on a
    successful scan — so archives are the only record of failures.
  Backup refuses to overwrite a larger backup with a smaller source unless
  forced, so a locally truncated log cannot destroy a good copy — precisely
  the failure the backup exists to survive.

**89 tests pass** (23 added across Phase 1.5).

- **Backup destination chosen and live: Google Drive.** Runtime logs back up
  to `My Drive/trading-bot-backup` via:

  ```
  ./monorepo-staging/scripts/run_trading_bot_log_maintenance.sh backup \
    ~/Library/CloudStorage/GoogleDrive-whatiskali@gmail.com/My\ Drive/trading-bot-backup
  ```

  Verified 2026-07-25: all three logs copied byte-for-byte identical, no
  credentials present in any backed-up file, and the truncation guard was
  exercised against the live Drive folder — a deliberately truncated local
  log was **REFUSED** rather than overwriting the 1 MB good copy.

  Drive was chosen over a git repo specifically because it needs **no
  scheduled job**. This project's defining failure was an unattended
  automated task stopping silently for three months; adding another cron job
  that can fail the same way works against the actual risk. Drive syncs
  continuously with nothing to schedule.

  Known limitation: Drive keeps version history for non-Google files for
  roughly 30 days, which is **shorter than the 90-day gate window**. So Drive
  protects against machine loss, not against slow-burn corruption noticed
  late. The truncation guard and append-only+fsync writes cover the likely
  corruption paths; **Time Machine is still the missing piece** for deep
  version history.

### DECIDED 2026-07-25 — ZeroClaw is the go-forward harness

Adopting ZeroClaw, replacing OpenClaw. Rationale, in short: it fixes the
three things that actually caused the three-month silence — deterministic
cron instead of a natural-language payload, a launchd service that
auto-restarts after a hard kill, and built-in scheduler/heartbeat freshness
checks — while preserving the Ollama-first cost model and costing far less
migration than expected, since the persona files use the same format and
filenames. Trial evidence below.

### Adoption checklist
1. ~~**Repo-manage the config.**~~ **DONE 2026-07-25.**
   `monorepo-staging/zeroclaw/` now holds `config/config.template.toml`
   (repo-root substituted at sync time), `cron/trading-bot-daily-scan.md`,
   and a `README.md` stating the contract. Deployed via
   `scripts/sync_zeroclaw_config.sh` — one-way repo → runtime, backing up the
   live config to gitignored `runtime/zeroclaw-backups/` before each write and
   warning before it would overwrite credential-looking values.

   Verified: deploy → `zeroclaw service restart` → `doctor` reports 24 ok, 0
   errors, and `--check` confirms live config matches the repo exactly.

   **This closes the question open since 2026-03-10** about whether deployed
   changes should flow back into the repo. They should not. Runtime is
   disposable; the repo is the contract. Sync is one-way, by design.
2. **Port the persona files** from `openclaw/workspace/` into the agent
   workspace. Same format, same filenames; review content for OpenClaw-
   specific instructions (e.g. `HEARTBEAT.md` telling the agent to check
   `crontab -l`, which was already wrong) before reuse.
3. ~~**Define the daily scan.**~~ **DEFINED, DELIBERATELY NOT ACTIVE.**
   `zeroclaw/cron/trading-bot-daily-scan.md` records the job:
   `35 9 * * 1-5` `America/Detroit` → `run_trading_bot_daily.sh`, a bare
   command with no model in the execution path. Apply with
   `sync_zeroclaw_config.sh --with-cron`, together with the backup (10:15)
   and watchdog (11:00) companion jobs defined in the same file.

   **Not scheduled yet, on purpose:** the drift audit that previously gated
   this is complete (`docs/SecurityAudit-2026-07-25.md`) and the kill switch
   it found broken is repaired and tested. What remains is the supervised
   rehearsal — the first active run closes PFE and COST on the stop rule, so
   enabling it is a real trading action, not just a config change.
4. ~~**Wire Telegram**~~ **DONE.** Token entered by the operator;
   `zeroclaw channel list` reports Telegram available, and delivery to the
   operator recipient was confirmed end-to-end on 2026-07-26 (0.7s, no agent
   in the path). `/bot` routes at `run_trading_bot_telegram_command.sh`,
   replacing the 56-line TypeScript shim with configuration.
5. **Resolve the deprecated docs.** The 2026-07-25 deprecation markers in
   `Architecture.md`, `openclaw/README.md`, and `TradingBotPlan.md` can now
   be rewritten against ZeroClaw rather than left as tombstones. Decide
   whether `monorepo-staging/openclaw/` is kept as history or removed.
6. ~~**Guardrails drift audit**~~ **DONE 2026-07-25 —
   `docs/SecurityAudit-2026-07-25.md`.** Every trading guardrail in
   `docs/Security.md` is implemented and enforced; the drift is operational.
   It found the documented kill switch was broken (it named an OpenClaw plist
   that does not exist, and failed silently), repaired it, and ran Test 7 for
   the first time: 1s stop, 6s restore against a 60s criterion. Doing so
   surfaced two further defects — `estop.enabled` defaulted false, and
   `require_otp_to_resume` defaulted true against a disabled OTP config, so
   engaging the kill switch locked you out of releasing it. Both fixed in
   `config.template.toml`.

   Still open from the audit, none blocking activation: no automated
   pass/fail evaluation of both halves of the paper-to-live gate;
   `logs/incidents.log` is referenced but never created; the persona files
   (checklist item 2) are still unported; the Anthropic monthly spend limit
   is unverified in the console; and `Security.md`'s OpenClaw-era sections
   (§1.1–1.3, the credential table, Telegram pairing paths) are still to be
   rewritten as part of checklist item 5.
7. **Restart the 90-day clock clean** once the above is green.

## Phase 3 — ZeroClaw trial (2026-07-25)

Installed `zeroclaw` 0.8.3 from **homebrew-core** (not a third-party tap;
Apache-2.0/MIT). All three trial criteria **passed**.

### 1. Ollama routing — PASS
`zeroclaw doctor` confirms `ollama.default: model: gemma4:e4b-mlx`. The cost
model survives: no Anthropic dependency required for the runtime itself.

### 2. Deterministic cron — PASS, and this is the key fix
Scheduled `print_trading_bot_runtime_status.sh` on `*/2 * * * *` with
`--tz America/Detroit`. It fired at :36, :38, :40 and executed the shell
script **directly — no LLM in the path**. Verified independently: the app's
own `operator.log` recorded each `runtime-status` invocation at those exact
timestamps.

This is the direct remedy for the original failure. The old OpenClaw job
carried a *natural-language instruction* ("run the scan, then send that
summary to Telegram") with `bestEffort: true` delivery, so execution and
delivery both depended on an LLM interpreting prose correctly every day.
ZeroClaw separates the two: a bare command runs deterministically, and
`--agent` is opt-in when you actually want reasoning.

### 3. Crash recovery — PASS
Installed as a launchd user service, then `kill -9` on the daemon. It came
back automatically (pid 76798 → 77152) **and the schedule kept firing across
the restart**. This is the exact failure mode that went unnoticed for three
months.

### Bonus findings
- **`zeroclaw doctor` already does staleness detection** — "heartbeat fresh
  (3s ago)", "scheduler healthy (last ok 13s ago)". The alerting/staleness
  work drafted earlier in Phase 2 is largely unnecessary; it exists here.
- **Persona files port as-is.** Agent identity `format = "openclaw"`, and
  doctor looks for `SOUL.md` / `AGENTS.md` — the exact filenames already in
  `monorepo-staging/openclaw/workspace/`. Migration cost is far lower than
  the earlier 120-line estimate.
- **Security model is deny-by-default.** Scheduling was *blocked* until the
  repo's wrapper scripts were explicitly allowlisted via
  `risk_profiles.tradingbot.allowed_commands`, with `allowed_roots` scoping
  filesystem access to the trading-bot tree. Stronger than what
  `docs/Security.md` describes today.
- Built-in cost tracking with daily/monthly caps, and an `estop` command that
  maps onto the kill switch in `docs/Security.md`.

### Rough edges (real, but minor)
- `zeroclaw config init` with no arguments wrote a config whose `gateway`,
  `transcription`, and `tunnel` sections its **own parser rejects**. Had to
  reset to `schema_version = 3` and build up by hand.
- `zeroclaw agents create` produces an agent with no resolvable
  `risk_profile`, which then fails validation at cron-add time.
- `config init <section>` reported "All sections already configured" while
  adding nothing; the provider block had to be written directly.
- Help text shows `cron add '*/5 * * * *' 'echo ok'` without `--agent`, but
  0.8.3 **requires** `--agent`. Docs lag the binary.

None are blocking — all were worked around in a single session — but expect
to hand-write `config.toml` rather than trust the wizards.

### Current state left on the machine
- launchd service `com.zeroclaw.daemon` **installed and running**
- config at `/opt/homebrew/var/zeroclaw/config.toml`: agent `tradingbot`,
  provider `ollama.default` → `gemma4:e4b-mlx`, risk profile scoped to the
  repo with five wrapper scripts allowlisted
- test cron job removed; **no scheduled jobs remain**
- ~~no channels configured~~ — Telegram wired and delivery verified
  2026-07-26 (see the step 5 rehearsal section)

## Decided 2026-07-25
- **Time Machine: not being set up at this time.** Accepted consequences:
  the `.env` holding Alpaca and Anthropic API keys, `strategy.local.json`,
  and the venv remain unbacked, and Drive's ~30-day version history stays
  shorter than the 90-day gate window. Revisit if an external drive appears.
- **Backup stays manual, not scheduled.** Run the command after meaningful
  runs. This means the Drive copy is only as fresh as the last manual run —
  worth doing at the end of any session that produced new scans.
- **Alpaca reconciliation** (`services/reconciliation.py`, via
  `scripts/run_trading_bot_reconciliation.sh [--json]`). Read-only; places no
  orders.

  **Bug it exposed first:** `broker.get_trade_history()` called
  `client.get_orders()` with no filter, and Alpaca defaults that to *open*
  orders only. Since every order that ever mattered had filled and closed, it
  returned **zero, always** — silently useless since it was written. Fixed
  with `status=ALL`, and the model now carries fill price, filled qty, and
  timestamps.

  **Why reconciliation is needed at all:** the bot writes an order's status at
  submission — 6 of the 8 historical orders are recorded as `PENDING_NEW`,
  which is the status milliseconds after submit — and never looks again. No
  fill price is recorded anywhere. On its own the bot cannot distinguish a
  completed trade from a rejected one.

  Detects: orders the bot believes in that the broker never saw, broker fills
  the bot has no record of, partial fills, and orders that never filled.
  Computes FIFO round-trip realized P/L and the consecutive-loss run.

  **First run against real data (2026-07-25):** 8 believed / 8 broker orders,
  **0 discrepancies**, and it surfaced two completed round trips that were
  invisible in the bot's own logs:

  | | symbol | bought | sold | realized |
  |---|---|---|---|---|
  | WIN | CVX | $187.81 | $207.40 | +$2,585.54 (+10.43%) |
  | LOSS | BRK.B | $495.50 | $471.26 | −$1,212.00 (−4.89%) |

  Realized P/L **+$1,373.54**, max consecutive losses **1** (gate allows ≤2).
  Both exits confirm the rules fired as configured — CVX hit the +10% profit
  target, BRK.B tripped the −4.5% stop at −4.89% with slippage. This is the
  first evidence the exit logic works against live fills.

  `read_model.gate_metrics()` still refuses to compute consecutive losses
  itself and now points at this command instead.

## 2026-07-25 — Market data resilience (Phase 2, done)

Fixed the April failure mode where `Connection reset by peer` cost two full
scan days. Two separate defects, the second worse than the first:

1. **No retry.** `get_bars()` made a single request with no retry. Now goes
   through `_get_with_retry()`: 3 attempts, exponential backoff with jitter
   (1s/2s, capped at 8s). Retries transport errors and 429/500/502/503/504;
   deliberately does **not** retry other 4xx (bad symbol, bad credentials),
   and credential errors bypass the retry budget entirely.
2. **No per-symbol isolation — the real bug.** `get_all_indicators()` looped
   without a try/except, so one bad symbol out of 50 raised, `daily_scan`
   caught it into an empty list, and the whole day silently did nothing.
   Failures are now contained per symbol; a partial universe still scans.

Crucially, `get_all_indicators()` raises only when **nothing** could be
fetched, so a total outage is never mistaken for "no signals today" — the
distinction that made the April failures invisible. Partial failures surface
in the scan notes as `Market data degraded: N of M symbol(s) failed`, so a
degraded run cannot pass as a quiet market.

Verified: 58 tests pass (11 new). Live check against Alpaca confirmed normal
fetches still work and a simulated total outage raises correctly. Note an
invalid symbol returns HTTP 200 with empty bars rather than an error, so it
is skipped as "no data" rather than counted as a failure — correct, but it
means the live run did not exercise the isolation path; unit tests and the
outage simulation cover that.

## DEFERRED: same-scan capital recycling (2026-07-25)

`build_order_results` does not credit sell proceeds to a buy in the same
scan, on the grounds that a submitted sale is not a settled one. Accepted as
the conservative default; **revisit once there is data.**

The cost, if any, is a freed slot sitting idle for one scan after an exit.
That is now measurable — once daily scans resume, the read model can answer
it directly:

```sql
-- scans that sold, and whether the freed slot was used the next day
SELECT r.timestamp, r.position_count, r.decision_count, r.order_count
FROM runs r ORDER BY r.timestamp;
```

If exits are rare, this costs essentially nothing and should stay as is. If
the strategy churns and slots idle regularly, the fix is to credit proceeds
once Alpaca reports the sale settled rather than at submission — not to
spend unsettled cash.

## Decision: open positions (2026-07-25)

**Let the bot's own exit logic close the stale positions on first resumed
run** rather than closing them manually.

Verified against the live broker and the real `_exit_reason()` rules
(+10% profit target / −4.5% stop loss) — note this closes **two of the
four**, not all of them:

| position | unrealized | first run |
|---|---|---|
| PFE | −9.95% | **SELL** (breaches stop) |
| COST | −6.76% | **SELL** (breaches stop) |
| NEE | −3.07% | HOLD — inside the stop |
| LIN | +3.79% | HOLD — short of the +10% target |

So LIN and NEE stay open and carry into the resumed run. Both sells will
execute: `max_trades_per_day: 2` constrains **buys only** — sells bypass the
daily budget and position-slot checks (`guardrails.py:38-70`) and are gated
only by the execution firewall (position exists, quantity valid), which they
pass. Worth re-checking prices at the time of the actual run, since these
thresholds are evaluated against live P/L, not today's snapshot.

## 2026-07-25 Reality Check (Phase 0/1)

Ground truth as of this session, replacing the stale March notes below:

- **Dormancy confirmed**: last commit 2026-03-10, last automated scan
  2026-04-24. ~3 months of no automated activity.
- **This machine has no OpenClaw install** (`~/.openclaw/` absent, no
  crontab entry) even though it's intended as the long-term host — it
  needs to be (re)installed, or replaced with a lighter alternative (see
  Architecture Decisions below), before scheduled runs can resume.
- **Environment rebuilt and verified working**: `.venv` recreated via
  `bootstrap_trading_bot.sh`; full test suite (47 tests) passes clean on
  current dependency versions (Python 3.14, pandas 3.0.5, alpaca-py
  0.43.5, anthropic 0.120.0).
- **Local model mismatch found and fixed**: `strategy.local.json` /
  `strategy.example.json` referenced `qwen2.5:7b`, but only `gemma4:latest`
  (8B, pulled 2026-04-25 — one day after the bot stopped, never wired in)
  is actually installed via Ollama. Config now points at `gemma4:latest`.
- **Ollama timeout root-caused and fixed**: the ~52s latency (60s timeout)
  wasn't model size or GPU/CPU fallback (confirmed 100% GPU, ~27 tok/s,
  normal for an 8B Q4 model on the M4) — it was Gemma 4's hidden
  chain-of-thought. With the default request, `eval_count` was 978 tokens
  for a ~200-token visible response; capping `num_predict` produced an
  *empty* response because the model spent the whole budget "thinking"
  before ever emitting JSON. Fix: added `"think": false` to the Ollama
  request in `local_analysis.py`. Result at the real 15-candidate scale:
  978→155 tokens on the 1-candidate case, and a full 15-candidate shortlist
  now completes in **~38s** (was 68s+ and climbing at just 10 candidates).
  Also bumped the request timeout 60s→90s as a safety buffer. Verified:
  output is still valid, correctly-shaped JSON; all 47 tests still pass.
- **Found, not touched**: `integrations/prefilter.py`
  (`OllamaPrefilterClient`) is dead code — not referenced anywhere in
  `src/` or `tests/`, left over from the pre-refactor model-first design.
  Candidate cleanup, not urgent.

## 2026-07-25 (later) — Ollama tuning, measured

Ollama client and server are both on 0.32.3 now (an earlier client/server
version mismatch has been resolved). Three fixes landed, all verified:

1. **Context window was overflowing (real bug).** The actual scan payload —
   15 candidates + 4 open positions + full snapshot fields — measures
   **4,346 prompt tokens**, against Ollama's 4,096 default. Ollama truncates
   from the *front*, which is where `LOCAL_ANALYSIS_PROMPT`'s instructions
   live, so on a high-signal day the model would silently lose its own rules
   while still answering. `num_ctx` is now set explicitly to 8,192
   (`DEFAULT_NUM_CTX` in `local_analysis.py`); real payloads land at ~64% of
   the window. Typical April days only produced ~3 candidates, so this
   rarely fired then — but it triggers exactly on the busiest days.
2. **Structured output.** The Ollama request now passes a JSON schema
   (`LOCAL_ANALYSIS_SCHEMA`) via `format`, so malformed output is impossible
   by construction rather than handled after the fact. The old
   brace-scraping parse is kept as a defensive fallback.
3. **Model pre-warm.** `OllamaLocalAnalysisClient.warm()` preloads the model
   at scan start, before the broker and market-data fetches, so cold-load
   time is not charged against the analysis call's timeout. Best-effort —
   failure just means the analysis call absorbs load time as before.

### Model benchmark (real payload, clean unload between runs)

| model | size | cold | load | prompt eval | gen | warm |
|---|---|---|---|---|---|---|
| `gemma4:latest` (E4B GGUF) | 9.6 GB | 62.5s | 15.3s | 13.6s | 33.5s | 30.5s |
| `gemma4:12b-mlx` | 7.7 GB | 83.2s | 3.6s | 37.4s | 42.2s | 42.5s |
| `gemma4:e4b-it-qat` | 6.1 GB | 54.0s | 6.0s | 12.3s | 35.7s | 27.4s |
| **`gemma4:e4b-mlx`** | **8.8 GB** | **32.4s** | **3.9s** | **10.5s** | **17.9s** | **18.9s** |

**Now configured: `gemma4:e4b-mlx`.** Fastest on every axis. Generation is
the decisive gap — ~46 tok/s vs ~26 tok/s for the GGUF builds of the *same*
model, i.e. MLX is ~1.7x faster on Apple Silicon, which is exactly what MLX
claims. End-to-end on a realistic uncached payload: **3.5s pre-warm + 26.7s
analysis = 30.2s, 34% of the 90s timeout** (vs 48.1s / 53% for the QAT
GGUF build).

**Correction to an earlier conclusion in this file.** An initial round
rejected MLX after `gemma4:12b-mlx` benchmarked badly, concluding "MLX
prompt processing is slow." That comparison was confounded — it changed
*two* variables at once (MLX format **and** a 12B model instead of E4B).
Testing `gemma4:e4b-mlx` isolates the format, and MLX prompt eval is
actually the **fastest** of the four (10.5s vs 12.3–13.6s for GGUF). The
12B's poor showing was model size, not MLX. The right takeaway is: **prefer
MLX builds on this hardware, but keep the model at E4B size.**

At 8.8GB `e4b-mlx` is still smaller than the 9.6GB originally configured,
and memory is not a real constraint here: the model is resident only during
the scan plus its `keep_alive` window (~10 min/day) and uses nothing the
rest of the day. Neither latency nor memory is close to binding — 30s
against a 90s timeout, 8.8GB of 16GB for ten minutes. If that ever changes,
`gemma4:e4b-it-qat` (6.1GB, ~1.6x slower) is a one-minute `ollama pull`
away; it is deliberately not kept on disk, because pre-staging for an
unlikely and trivially reversible scenario is not worth carrying.

### Two measurement traps worth remembering

- **Never leave two models resident on this 16GB box.** An early benchmark
  showed 12b-mlx taking *180 seconds* to emit 2 tokens; the cause was
  `gemma4:latest` still loaded alongside it (7.5GB + 3.2GB) and contending
  for unified memory. Alone, the same call took 5.8s. Any benchmarking must
  unload everything first, and `keep_alive` should not be raised carelessly.
- **Benchmark "warm" numbers flatter reality.** Re-sending an identical
  prompt hits Ollama's prompt cache (prompt_eval drops to ~0.06s). Real
  trading days send a different payload every time, so prompt eval (~12s) is
  paid daily. Realistic end-to-end, measured with a perturbed payload:
  **~1.9s pre-warm + ~41s analysis = 46% of the 90s timeout budget.**

- **Don't change two variables at once.** The 12b-mlx result nearly produced
  a wrong standing conclusion about MLX. Isolate format from model size.

### Cross-project model reference sweep (2026-07-25)

Reviewed `~/Projects/` and `~/trading-bot/` for references to local models.
**All three project-iq variants were broken, not merely stale** — their live
`.env` files pointed at `gemma4:latest`, which is no longer installed. Their
own `ProjectIQ_Rebalance_Theory_Validation.md` had already flagged this class
of bug (F9/R4: a model-ID mismatch fails *silently*). Repointed 21 references
across `project-iq`, `project-iq-refactor`, `project-iq-staging` and this
repo to `gemma4:e4b-mlx`: live `.env`/`.env.dev`, the `.env*.example`
templates, the `ollama_model` defaults in `backend/config.py`, and
`docs/SYSTEM_DESIGN.md` (including a bare `ollama pull gemma4`, which
resolves to `:latest` and would have reinstalled the wrong GGUF build).

Worth knowing: project-iq's `SYSTEM_DESIGN.md` sets
`OLLAMA_MAX_LOADED_MODELS=1` and `OLLAMA_KEEP_ALIVE=24h`. Now that project-iq
and the trading bot share one model, they share one resident copy. Had they
been left on different models, that config would make them evict each other
on every switch — reproducing the memory-contention stall that turned a
6-second call into 180 seconds during benchmarking.

**OpenClaw `qwen2.5:7b` references marked deprecated, not repointed.** These
describe OpenClaw's *operator-chat* model, a different role from the trading
app's local analysis, for a runtime that is not installed here — and the
harness decision is still open (Phase 3). Repointing them would assert a
choice that has not been made. Dated deprecation notes added to
`monorepo-staging/docs/Architecture.md`,
`monorepo-staging/openclaw/README.md` (where the whole "Current Status"
section describes a deployment that no longer exists), and
`docs/TradingBotPlan.md`.

Deliberately left untouched as point-in-time records: `openclaw/FINAL_REVIEW.md`
(a go-live review), `docs/rebuild/{MachineAudit,Operations,README}.md` (host
audits), the project-iq validation findings, `.claude/worktrees/` copies, and
test fixtures using `"qwen2.5:7b"` as arbitrary mock data.

### Ollama state after this session
- `gemma4:e4b-mlx` (8.8GB) is the only model installed, matching
  `strategy.local.json`. The benchmark candidates (`gemma4:latest`,
  `gemma4:12b-mlx`, `gemma4:e4b-it-qat`) were all removed.
- **Alpaca paper account still reachable**, keys still valid. But:
  **the 4 positions left open since 2026-04-24 have been sitting
  unmanaged for 3 months with no exit-rule enforcement.** Current state:
  - COST: -6.76% unrealized (past the 4.5% stop-loss threshold)
  - PFE: -9.95% unrealized (well past the 4.5% stop-loss threshold)
  - NEE: -3.07% unrealized
  - LIN: +3.79% unrealized
  - Portfolio value: **$97,444.87**, down from $100,000 start and down
    from the $102,932.51 peak recorded on 2026-04-10 — the +2.2% gain
    seen while the bot was actively running has since round-tripped into
    a net loss, entirely because nothing was enforcing exits during the
    dormancy. Paper money, no real harm — but it's a concrete demonstration
    of why unattended monitoring (WORKFLOW.md's proposed scheduled check)
    matters, and something to decide on explicitly (manually close/reset
    these positions vs. let the bot's exit logic handle them on first
    resumed run) before restarting the clock.

## Architecture decisions raised this session (not yet resolved)

- **Language**: recommendation is to stay in Python for now — this is a
  once-daily batch job, not latency-sensitive, and Python's ecosystem
  (`pandas`, `alpaca-py`, `anthropic`) still wins for iterating on an
  unproven strategy (only 45 trades so far). Revisit only after the
  strategy is validated.
- **Agent harness**: OpenClaw is dominant but heavy (434k+ LOC) for what
  this project needs (one cron scan + Telegram routing). Worth evaluating
  **NanoClaw** (~3,900 LOC, same core capabilities) or **ZeroClaw** (Rust,
  small/fast) before reinstalling OpenClaw specifically — this machine
  having no OpenClaw install at all is the cheapest point to make that
  switch.
- **Local model**: superseded later the same day — see the benchmark below.
  Settled on `gemma4:e4b-mlx`, not `gemma4:latest`.

## Candidate future phases (not committed)

- ~~**Phase 2 — Reliability hardening**~~ — **COMPLETE.** All four items
  landed 2026-07-25: Ollama timeout margin, market-data retry/backoff and
  per-symbol isolation, Telegram failure alerting (plus the staleness
  watchdog), and the guardrails drift audit. See the dated sections above.
- **Phase 3 — Harness decision + redeploy** — decision made (ZeroClaw,
  installed and running as `com.zeroclaw.daemon`); redeploy is what the
  "Next action" at the top of this file is executing. Restarting the 90-day
  clock clean is the last step, given the reliability gaps and the
  unmanaged-position drawdown in the original window.

---

## Superseded (from 2026-03-10 — kept for history, no longer active)

<details>
<summary>Original reverse-sync decision notes</summary>

- Do not set up OpenClaw command behavior as a chat-defined persistent session.
- Keep command logic in the repo and let OpenClaw call repo-managed wrappers.
- Treat the deployed OpenClaw environment as runtime state, not as the source of truth.
- Open question: whether environment-originated OpenClaw changes should
  ever flow back into the repo, or whether repo-to-runtime sync should
  stay strictly one-way (with an allowlist + review path if reverse sync
  is ever allowed).
- This whole question is now moot until the Phase 3 harness decision is
  made — if OpenClaw is replaced, the reverse-sync design may not even
  apply to whatever replaces it.

</details>
