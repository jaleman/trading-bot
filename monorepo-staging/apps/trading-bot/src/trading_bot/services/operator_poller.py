"""Deterministic Telegram poller for operator commands.

`/bot balance` is a fixed command with a fixed handler: run a wrapper script,
return its stdout. There is nothing to reason about, so no model is involved.

This exists because routing operator commands through an agent was tried and
was worse in every dimension -- roughly eleven seconds of model latency plus a
manual approval tap for a command that takes one second, and the model could
decide not to run the tool at all (it did, answering "I couldn't produce a
visible reply" while executing nothing). The previous OpenClaw setup got this
right with a native command plugin; this is that idea rebuilt in a form the
project owns.

Division of responsibility with ZeroClaw:

*   ZeroClaw schedules the daily scan and delivers its summary outbound via
    `channel send`, which works even when its Telegram channel is disabled.
*   This poller owns *inbound* messages. Two processes cannot poll one bot
    token -- Telegram hands each update to whoever asks first -- so ZeroClaw's
    Telegram channel must be disabled for this to work reliably.

Security posture: deny-by-default. Messages from any sender other than the
configured operator are ignored, not answered.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import requests

TELEGRAM_API = "https://api.telegram.org"

# Telegram rejects messages above 4096 characters.
MAX_REPLY_CHARS = 3900
LONG_POLL_TIMEOUT_SECONDS = 30
COMMAND_TIMEOUT_SECONDS = 120

# Anything the repo-managed router understands. The router itself does the
# real parsing, including aliases; this only decides what to forward.
COMMAND_PREFIXES = ("/bot", "bot ")
ALIAS_COMMANDS = (
    "/summary", "/pending", "/status", "/balance",
    "/holdings", "/info", "/list", "/sync", "/restart",
)


@dataclass(frozen=True)
class PollerConfig:
    bot_token: str
    operator_id: str
    router_script: Path
    state_file: Path


class PollerConfigError(RuntimeError):
    """Raised when the poller cannot start with the given configuration."""


def looks_like_command(text: str) -> bool:
    """True when the message should be forwarded to the router."""
    stripped = (text or "").strip()
    if not stripped:
        return False
    lowered = stripped.lower()
    if lowered.startswith(COMMAND_PREFIXES):
        return True
    return any(
        lowered == alias or lowered.startswith(alias + " ")
        for alias in ALIAS_COMMANDS
    )


def is_authorized(sender_id, operator_id: str) -> bool:
    """Deny-by-default: only the configured operator is answered."""
    return str(sender_id) == str(operator_id)


def run_router(config: PollerConfig, text: str) -> str:
    """Hand the raw message to the repo-managed router, verbatim."""
    try:
        completed = subprocess.run(
            [str(config.router_script), text.strip()],
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return f"Command timed out after {COMMAND_TIMEOUT_SECONDS}s."
    except Exception as exc:  # noqa: BLE001 - report rather than crash the loop
        return f"Command failed to run: {type(exc).__name__}: {exc}"

    output = (completed.stdout or "").strip() or (completed.stderr or "").strip()
    if not output:
        output = f"No output (exit code {completed.returncode})."
    if len(output) > MAX_REPLY_CHARS:
        output = output[:MAX_REPLY_CHARS] + "\n… truncated."
    return output


def handle_update(config: PollerConfig, update: dict) -> tuple[str | None, str | None]:
    """Map one Telegram update to (chat_id, reply). Both None means ignore."""
    message = update.get("message") or update.get("edited_message") or {}
    text = message.get("text") or ""
    chat_id = (message.get("chat") or {}).get("id")
    sender_id = (message.get("from") or {}).get("id")

    if chat_id is None or not text:
        return None, None
    if not is_authorized(sender_id, config.operator_id):
        # Silence rather than "unauthorized", which would confirm the bot is live.
        return None, None
    if not looks_like_command(text):
        return None, None

    return str(chat_id), run_router(config, text)


def send_message(config: PollerConfig, chat_id: str, text: str) -> bool:
    try:
        response = requests.post(
            f"{TELEGRAM_API}/bot{config.bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=30,
        )
        response.raise_for_status()
        return True
    except Exception:
        return False


def load_offset(state_file: Path) -> int:
    """Resume after the last handled update so a restart does not replay."""
    try:
        return int(json.loads(state_file.read_text(encoding="utf-8"))["offset"])
    except Exception:
        return 0


def save_offset(state_file: Path, offset: int) -> None:
    try:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps({"offset": offset}), encoding="utf-8")
    except Exception:
        pass


def poll_once(config: PollerConfig, offset: int) -> int:
    """One long-poll cycle. Returns the next offset."""
    response = requests.get(
        f"{TELEGRAM_API}/bot{config.bot_token}/getUpdates",
        params={"offset": offset, "timeout": LONG_POLL_TIMEOUT_SECONDS},
        timeout=LONG_POLL_TIMEOUT_SECONDS + 15,
    )
    response.raise_for_status()

    for update in response.json().get("result", []):
        offset = int(update["update_id"]) + 1
        chat_id, reply = handle_update(config, update)
        if chat_id and reply:
            send_message(config, chat_id, reply)
        save_offset(config.state_file, offset)

    return offset


def build_config(env_file: Path | None = None) -> PollerConfig:
    from trading_bot.env_loader import load_runtime_env
    from trading_bot.runtime_paths import ensure_runtime_dirs, resolve_paths

    paths = ensure_runtime_dirs(resolve_paths(env_file=env_file))
    load_runtime_env(paths.env_file)

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    operator = os.getenv("TRADING_BOT_TELEGRAM_RECIPIENT", "").strip()
    if not token:
        raise PollerConfigError(
            "TELEGRAM_BOT_TOKEN is not set. The poller needs its own copy: "
            "ZeroClaw stores the token encrypted and will not reveal it."
        )
    if not operator:
        raise PollerConfigError("TRADING_BOT_TELEGRAM_RECIPIENT is not set.")

    router = paths.repo_root / "monorepo-staging" / "scripts" / "run_trading_bot_telegram_command.sh"
    if not router.exists():
        raise PollerConfigError(f"Router script not found: {router}")

    return PollerConfig(
        bot_token=token,
        operator_id=operator,
        router_script=router,
        state_file=paths.runtime_root / "telegram-poller-state.json",
    )


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Deterministic /bot Telegram poller.")
    parser.add_argument("--env-file", dest="env_file")
    parser.add_argument("--once", action="store_true", help="Single cycle, for testing.")
    args = parser.parse_args(argv)

    config = build_config(Path(args.env_file) if args.env_file else None)
    offset = load_offset(config.state_file)
    print(f"Polling as operator {config.operator_id}; router {config.router_script.name}")

    if args.once:
        poll_once(config, offset)
        return

    while True:
        try:
            offset = poll_once(config, offset)
        except KeyboardInterrupt:
            raise
        except Exception as exc:  # noqa: BLE001 - a transient API error must not end the service
            print(f"poll error: {type(exc).__name__}: {exc}", flush=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
