# ZeroClaw runtime contract

Repository-managed source of truth for the agent runtime that schedules the
trading scan and serves the operator interface. Replaces `../openclaw/` as of
2026-07-25.

## The rule

**Edit here. Deploy with the sync script. Never hand-edit the live config.**

| | |
|---|---|
| Source of truth | `zeroclaw/config/config.template.toml` (this tree) |
| Runtime state | `/opt/homebrew/var/zeroclaw/config.toml` |
| Sync direction | repo → runtime, one-way |
| Backups | `runtime/zeroclaw-backups/` (gitignored) |

Sync is deliberately one-way. This settles the question left open in
`todo.md` since 2026-03-10 about whether deployed changes should flow back
into the repo: they should not. Runtime is disposable; the repo is the
contract. If something needs to change, change it here and redeploy.

## Layout

- `config/config.template.toml` — the full config, with the repo root as a
  substituted placeholder
- `cron/trading-bot-daily-scan.md` — the daily scan job definition and why it
  is a bare command rather than an agent prompt

## Commands

```bash
../scripts/sync_zeroclaw_config.sh --check       # diff repo against runtime
../scripts/sync_zeroclaw_config.sh               # deploy config
../scripts/sync_zeroclaw_config.sh --with-cron   # deploy, then add the daily scan
zeroclaw service restart                         # apply config to the daemon
zeroclaw doctor                                  # scheduler + heartbeat freshness
zeroclaw status                                  # provider, agents, cost, service
```

## Secrets

The config in this repo contains **no credentials**, and must not. The local
model provider needs no API key, which is part of why it was chosen.

Channel tokens (Telegram) are set directly against the live config with
`zeroclaw config set <path>`, which takes masked input and stores them only
in the runtime file. The sync script backs up the live config before every
write and warns when it is about to overwrite credential-looking values, so a
sync cannot silently destroy a token — but it will need re-applying after.

## Why ZeroClaw

The previous OpenClaw job carried a natural-language instruction as its
scheduled payload with best-effort delivery, so both execution and reporting
depended on a model reading prose correctly each day, and a silent stop was
invisible. Between 2026-04-24 and 2026-07-25 exactly that happened.

ZeroClaw was adopted after a trial that verified three things: deterministic
cron execution with no model in the path, a launchd service that recovers
from `kill -9` with the schedule intact, and `zeroclaw doctor` reporting
scheduler and heartbeat freshness so staleness is observable. It also keeps
the local-model cost posture and enforces a deny-by-default command
allowlist. Trial notes are in `todo.md`.

## Migrating from OpenClaw

Agent identity uses `format = "openclaw"`, and the runtime looks for the same
`SOUL.md` / `AGENTS.md` filenames already present in `../openclaw/workspace/`.
Those files port across, but review them first — some contain instructions
that were already wrong under OpenClaw, such as `HEARTBEAT.md` telling the
agent to inspect `crontab -l` when the runtime owned scheduling itself.
