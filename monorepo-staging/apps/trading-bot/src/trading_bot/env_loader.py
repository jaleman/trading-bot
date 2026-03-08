from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from trading_bot.runtime_paths import resolve_paths


def load_runtime_env(path: str | Path | None = None) -> Path | None:
    resolved = Path(path).expanduser().resolve() if path else resolve_paths().env_file
    if resolved is None or not resolved.is_file():
        return None

    load_dotenv(resolved, override=False)
    return resolved