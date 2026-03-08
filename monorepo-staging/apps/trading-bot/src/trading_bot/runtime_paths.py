from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    app_root: Path
    repo_root: Path
    config_dir: Path
    runtime_root: Path
    logs_dir: Path
    database_dir: Path
    trade_log: Path
    guardrail_state: Path
    env_file: Path | None
    strategy_config: Path


def _resolve_input_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def resolve_paths(
    *,
    strategy_path: str | Path | None = None,
    env_file: str | Path | None = None,
) -> AppPaths:
    app_root = Path(__file__).resolve().parents[2]
    repo_root = app_root.parents[1]
    config_dir = app_root / "config"
    runtime_root = repo_root / "runtime" / "trading-bot"
    logs_dir = runtime_root / "logs"
    database_dir = runtime_root / "database"
    trade_log = logs_dir / "trades.log"
    guardrail_state = runtime_root / "guardrail-state.json"
    default_strategy_config = config_dir / "strategy.local.json"
    if not default_strategy_config.exists():
        default_strategy_config = config_dir / "strategy.example.json"

    strategy_config = (
        _resolve_input_path(strategy_path)
        if strategy_path is not None
        else default_strategy_config
    )

    default_env_file = app_root / ".env"
    resolved_env_file = (
        _resolve_input_path(env_file)
        if env_file is not None
        else default_env_file if default_env_file.exists() else None
    )

    return AppPaths(
        app_root=app_root,
        repo_root=repo_root,
        config_dir=config_dir,
        runtime_root=runtime_root,
        logs_dir=logs_dir,
        database_dir=database_dir,
        trade_log=trade_log,
        guardrail_state=guardrail_state,
        env_file=resolved_env_file,
        strategy_config=strategy_config,
    )


def ensure_runtime_dirs(paths: AppPaths | None = None) -> AppPaths:
    resolved = paths or resolve_paths()
    resolved.runtime_root.mkdir(parents=True, exist_ok=True)
    resolved.logs_dir.mkdir(parents=True, exist_ok=True)
    resolved.database_dir.mkdir(parents=True, exist_ok=True)
    return resolved
