"""Rotation and off-machine backup for runtime logs.

Two deliberate asymmetries:

*   `trades.jsonl` is **never rotated**. It is the source of truth the read
    model replays, and splitting it across archives would silently orphan
    history from any rebuild. At roughly 23 KB per run it grows about 5.6 MB
    a year, so retention is not a real problem worth that risk.
*   The human-readable logs *are* rotated, but archives are **never deleted**
    by default. `trades.log` holds the crash tracebacks, which the JSONL does
    not — the JSONL is only written on a successful scan — so those archives
    are the only record of failures.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

# Human-readable logs only; the JSONL source of truth is exempt.
DEFAULT_MAX_BYTES = 5 * 1024 * 1024

BACKUP_FILENAMES = ("trades.jsonl", "trades.log", "operator.log")


class BackupError(RuntimeError):
    """Raised when logs cannot be backed up safely."""


def rotate_log(path: str | Path, max_bytes: int = DEFAULT_MAX_BYTES) -> Path | None:
    """Rename an oversized log aside. Returns the archive path, or None.

    Archives are timestamped rather than numbered, so rotation never
    overwrites an older archive.
    """
    path = Path(path)
    if not path.exists() or path.stat().st_size < max_bytes:
        return None

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive = path.with_name(f"{path.stem}-{stamp}{path.suffix}")
    path.rename(archive)
    return archive


def rotate_runtime_logs(paths=None, max_bytes: int = DEFAULT_MAX_BYTES) -> dict:
    from trading_bot.runtime_paths import resolve_paths

    paths = paths or resolve_paths()
    rotated = {}
    for target in (paths.trade_log, paths.operator_log):
        archive = rotate_log(target, max_bytes=max_bytes)
        if archive is not None:
            rotated[target.name] = str(archive)
    return rotated


def backup_runtime_logs(destination: str | Path, paths=None, force: bool = False) -> dict:
    """Copy runtime logs to an off-machine destination.

    The gate evidence otherwise lives on exactly one Mac. `destination` is
    intentionally caller-supplied: point it at iCloud Drive, an external
    volume, or a mounted share.

    Refuses to overwrite a larger backup with a smaller source unless forced,
    so a locally truncated log cannot destroy a good copy — precisely the
    failure this backup exists to survive.
    """
    from trading_bot.runtime_paths import resolve_paths

    paths = paths or resolve_paths()
    destination = Path(destination).expanduser()

    try:
        destination.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise BackupError(f"Cannot create backup destination {destination}: {exc}") from exc

    results: dict[str, str] = {}
    for name in BACKUP_FILENAMES:
        source = paths.logs_dir / name
        if not source.exists():
            results[name] = "skipped: not present"
            continue

        target = destination / name
        if target.exists() and not force:
            if source.stat().st_size < target.stat().st_size:
                results[name] = (
                    f"REFUSED: source ({source.stat().st_size} B) is smaller than "
                    f"existing backup ({target.stat().st_size} B); use force to override"
                )
                continue

        shutil.copy2(source, target)
        results[name] = f"copied {source.stat().st_size} B"

    # Archived rotations travel with the live logs.
    for archive in sorted(paths.logs_dir.glob("*-20*.log")):
        target = destination / archive.name
        if not target.exists():
            shutil.copy2(archive, target)
            results[archive.name] = f"archived {archive.stat().st_size} B"

    return results


def main(argv: list[str] | None = None) -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Runtime log rotation and backup.")
    parser.add_argument("command", choices=["rotate", "backup"])
    parser.add_argument("destination", nargs="?", help="Backup destination directory.")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--force", action="store_true",
                        help="Allow overwriting a larger backup with a smaller source.")
    args = parser.parse_args(argv)

    if args.command == "rotate":
        result = rotate_runtime_logs(max_bytes=args.max_bytes)
        print(json.dumps(result or {"rotated": "nothing exceeded the threshold"}, indent=2))
    else:
        if not args.destination:
            parser.error("backup requires a destination directory")
        print(json.dumps(backup_runtime_logs(args.destination, force=args.force), indent=2))


if __name__ == "__main__":
    main()
