# Personal Workflow: Goals, Looping, Prototyping

How I use Claude Code to work on this project. Read this at the start of a
work cycle, alongside `todo.md` and (if present) `startHere.md`.

**Status note, 2026-07-26.** The dormancy this file was written against
(2026-03-10 → 2026-07-25) is over, and **Phase 0 below is complete** — its
findings are the dated sections in `todo.md`. The reverse-sync question it
names is settled (one-way, repo → runtime), and OpenClaw has been replaced
by ZeroClaw. Read Phase 0 as a record of how the restart was done, not as a
task. Everything from "Goals" onward is still current practice.

## The three pieces

- **Goals** — a small, explicit stack (north star → current milestone → next
  action) that survives context resets, so every session starts from the
  same frame instead of re-deriving intent from old todos.
- **Looping** — two different tools for two different situations: `/loop`
  for active, self-paced work while I'm at the keyboard; scheduled tasks for
  passive, unattended checks.
- **Prototyping** — a tight, safe iteration loop that never touches the live
  scheduled path or the deployed OpenClaw workspace until a change has been
  proven in isolation.

---

## Phase 0 — Reassess before resuming anything (do this first, once)

Four+ months is long enough that "current reality" in `todo.md` may no
longer be true. Don't resume the reverse-sync decision blind. Run one
session whose only job is to re-establish ground truth:

1. `git status` / `git log` in both the root repo and `monorepo-staging/`.
2. Confirm whether the OpenClaw cron job `trading-bot-daily-scan` is still
   running, and what `print_trading_bot_operator_summary.sh` reports now.
3. Diff the deployed `~/.openclaw/workspace/` against the repo-managed
   source, since drift between the two is the exact open question in
   `todo.md`.
4. Re-read `docs/TradingBotPlan.md` and `monorepo-staging/docs/Architecture.md`
   and note anything that no longer matches what's deployed.
5. Write the findings back into `todo.md` (replace the stale "Decision From
   Tonight" section with a dated reality check) rather than trusting memory
   of March.

This is a single interactive session, not a loop — the point is judgment
about what changed, not iteration.

## Goals — keep a visible stack

Add a `## Goals` section to `todo.md` (or split into `GOALS.md` if it grows)
with three tiers, reviewed and updated at the start of every session:

- **North star** (quarter-scale, rarely changes) — e.g. "reach the
  live-capital approval gate with a clean audit trail," or whatever Phase 0
  reassessment concludes is actually still the target.
- **Current milestone** (2–4 weeks) — e.g. "resolve the reverse-sync policy
  and close the drift gap between deployed and repo-managed OpenClaw state."
- **Next action** (this session) — one concrete, falsifiable task.

Every session, interactive or looped, should start by reading this stack
plus `startHere.md`'s "First Reads" list — that's what keeps a fresh context
window from re-litigating settled decisions or drifting off the milestone.

## Looping — two modes, different jobs

**Interactive (`/loop`)** — for real implementation work while I'm present.
Use it to self-pace through a single milestone-sized task: e.g. "implement
the reverse-sync allowlist and review path," or "clear the drift found in
Phase 0." Good fit whenever the task has a clear stopping condition (tests
pass, drift resolved, feature works) but unknown iteration count.

**Scheduled (background)** — for passive monitoring between sessions, not
for touching code unattended. Given the safety rules in `startHere.md`
(paper-trade only, no live-capital action without an explicit gate), the
scheduled task should be read-only: check that the daily cron job actually
ran, pull the latest operator summary, flag drift or failures, and notify —
never modify the runtime or push a sync on its own. This is the "mix of
both" cadence: unattended eyes on the bot, attended hands on any change.

A reasonable starting cadence: one interactive `/loop` session per week for
real progress on the current milestone, plus a scheduled status check
2–3x/week (or daily, matching the trading cron) that reports summary +
drift and does nothing else. I'll ask before setting the scheduled task up —
this document is the plan, not the setup.

## Prototyping — safe iteration loop

The live path is real (paper-trade, but live-scheduled), so prototyping
must not touch it directly:

1. Do exploratory/risky changes in a git worktree, not on `main` directly.
2. Iterate with the app-layer scripts only:
   `bootstrap_trading_bot.sh` → `run_trading_bot_tests.sh` →
   `run_trading_bot_rehearsal.sh` → `print_trading_bot_operator_summary.sh`.
3. Only after that loop is green does a change get promoted via
   `sync_zeroclaw_config.sh` — which is the one script that actually touches
   the deployed runtime, and should always be a deliberate, reviewed step,
   never something a loop or scheduled task does on its own. Verify with
   `sync_zeroclaw_config.sh --check`.
4. `zeroclaw service restart` only when a reload is actually needed, per
   `startHere.md`. (Updated 2026-07-26: this step named
   `sync_openclaw_workspace.sh` and `restart_openclaw_gateway.sh`, both
   removed in commit 514073f.)

## A typical cycle, once Phase 0 is done

1. Start of session: read goal stack + `startHere.md` first-reads + latest
   scheduled-check report.
2. Confirm or update "next action" against what the scheduled checks have
   surfaced since last time.
3. Prototype the change in a worktree; run the test/rehearsal loop.
4. If it's a multi-step implementation, drive it with `/loop` rather than
   manually re-prompting each step.
5. Promote via the sync script only when green, as a deliberate step.
6. Update `todo.md`'s goal stack before ending the session — next session
   starts from here, not from memory.

## Immediate next actions

1. Run the Phase 0 reassessment session.
2. Based on what it finds, rewrite `todo.md`'s goal stack (north
   star / milestone / next action) instead of the current freeform notes.
3. Decide, with actual current drift data in hand, whether to resume the
   reverse-sync decision as originally scoped or reprioritize.
