"""Derived SQLite read model over the append-only scan log.

`trades.jsonl` is the source of truth. This database is a *projection* of it:
disposable, rebuildable, and free to change schema, because it can always be
replayed from the log. Nothing writes here except a rebuild.

The point is queryability. A single JSONL entry is ~31 KB, dominated by the
indicator snapshots, so answering "which entry conditions preceded losing
trades" means parsing every blob. In SQL it is a join.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE runs (
    run_id           TEXT PRIMARY KEY,
    timestamp        TEXT NOT NULL,
    status           TEXT,
    cash             REAL,
    portfolio_value  REAL,
    buying_power     REAL,
    triggered_count  INTEGER,
    watching_count   INTEGER,
    decision_count   INTEGER,
    position_count   INTEGER,
    order_count      INTEGER,
    degraded         INTEGER NOT NULL DEFAULT 0,
    strategy_file    TEXT,
    source_line      INTEGER NOT NULL
);

CREATE TABLE decisions (
    run_id     TEXT NOT NULL,
    timestamp  TEXT NOT NULL,
    symbol     TEXT NOT NULL,
    action     TEXT NOT NULL,
    qty        REAL,
    reason     TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE positions (
    run_id           TEXT NOT NULL,
    timestamp        TEXT NOT NULL,
    symbol           TEXT NOT NULL,
    qty              REAL,
    avg_entry_price  REAL,
    current_price    REAL,
    unrealized_pl    REAL,
    unrealized_plpc  REAL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE indicators (
    run_id                 TEXT NOT NULL,
    timestamp              TEXT NOT NULL,
    symbol                 TEXT NOT NULL,
    current_price          REAL,
    ma_20                  REAL,
    ma_50                  REAL,
    rsi                    REAL,
    recent_return_5d       REAL,
    recent_return_20d      REAL,
    volatility_20d         REAL,
    avg_dollar_volume_20d  REAL,
    distance_to_ma_20_pct  REAL,
    distance_to_ma_50_pct  REAL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE guardrails (
    run_id   TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    name     TEXT NOT NULL,
    allowed  INTEGER NOT NULL,
    reasons  TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE INDEX idx_decisions_symbol ON decisions(symbol);
CREATE INDEX idx_decisions_action ON decisions(action);
CREATE INDEX idx_indicators_symbol ON indicators(symbol);
CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_runs_timestamp ON runs(timestamp);
"""


class ReadModelError(RuntimeError):
    """Raised when the read model cannot be built from the source log."""


def _synthetic_run_id(timestamp: str, line_number: int) -> str:
    """Run ID for entries written before run IDs existed.

    The April 2026 history predates run-ID stamping, so those rows get a
    deterministic identifier derived from their timestamp and position, which
    keeps rebuilds idempotent.
    """
    try:
        stamp = datetime.fromisoformat(timestamp).strftime("%Y%m%d-%H%M%S")
    except (TypeError, ValueError):
        stamp = "unknown"
    return f"legacy-{stamp}-{line_number:05d}"


class ScanReadModel:
    """Queryable projection of trades.jsonl."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)

    def rebuild(self, jsonl_path: str | Path) -> dict:
        """Drop and repopulate the database from the log.

        Rebuilding is always safe: the database holds no original data.
        """
        jsonl_path = Path(jsonl_path)
        if not jsonl_path.exists():
            raise ReadModelError(f"Source log not found: {jsonl_path}")

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if self.db_path.exists():
            self.db_path.unlink()

        stats = {"runs": 0, "decisions": 0, "positions": 0,
                 "indicators": 0, "guardrails": 0, "skipped_lines": 0}

        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(SCHEMA)
            seen: set[str] = set()

            for line_number, raw in enumerate(
                jsonl_path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    entry = json.loads(raw)
                except json.JSONDecodeError:
                    # One malformed line costs one run, not the history --
                    # the reason the JSONL stays the source of truth.
                    stats["skipped_lines"] += 1
                    continue

                summary = entry.get("summary") or {}
                timestamp = entry.get("timestamp", "")
                run_id = entry.get("run_id") or _synthetic_run_id(timestamp, line_number)
                if run_id in seen:
                    stats["skipped_lines"] += 1
                    continue
                seen.add(run_id)

                self._insert_run(conn, run_id, timestamp, summary, line_number)
                stats["runs"] += 1
                stats["decisions"] += self._insert_decisions(conn, run_id, timestamp, summary)
                stats["positions"] += self._insert_positions(conn, run_id, timestamp, summary)
                stats["indicators"] += self._insert_indicators(conn, run_id, timestamp, summary)
                stats["guardrails"] += self._insert_guardrails(conn, run_id, timestamp, summary)

        return stats

    @staticmethod
    def _insert_run(conn, run_id, timestamp, summary, line_number) -> None:
        account = summary.get("account") or {}
        notes = summary.get("notes") or []
        conn.execute(
            "INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                run_id, timestamp, summary.get("status"),
                account.get("cash"), account.get("portfolio_value"),
                account.get("buying_power"),
                len(summary.get("triggered") or []),
                len(summary.get("watching") or []),
                len(summary.get("decisions") or []),
                len(summary.get("positions") or []),
                len(summary.get("order_results") or []),
                int(any("degraded" in str(n).lower() for n in notes)),
                summary.get("strategy_file"),
                line_number,
            ),
        )

    @staticmethod
    def _insert_decisions(conn, run_id, timestamp, summary) -> int:
        rows = [
            (run_id, timestamp, d.get("symbol"), d.get("action"), d.get("qty"), d.get("reason"))
            for d in (summary.get("decisions") or [])
        ]
        conn.executemany("INSERT INTO decisions VALUES (?,?,?,?,?,?)", rows)
        return len(rows)

    @staticmethod
    def _insert_positions(conn, run_id, timestamp, summary) -> int:
        rows = [
            (run_id, timestamp, p.get("symbol"), p.get("qty"), p.get("avg_entry_price"),
             p.get("current_price"), p.get("unrealized_pl"), p.get("unrealized_plpc"))
            for p in (summary.get("positions") or [])
        ]
        conn.executemany("INSERT INTO positions VALUES (?,?,?,?,?,?,?,?)", rows)
        return len(rows)

    @staticmethod
    def _insert_indicators(conn, run_id, timestamp, summary) -> int:
        rows = [
            (run_id, timestamp, s.get("symbol"), s.get("current_price"), s.get("ma_20"),
             s.get("ma_50"), s.get("rsi"), s.get("recent_return_5d"),
             s.get("recent_return_20d"), s.get("volatility_20d"),
             s.get("avg_dollar_volume_20d"), s.get("distance_to_ma_20_pct"),
             s.get("distance_to_ma_50_pct"))
            for s in (summary.get("indicator_snapshots") or [])
        ]
        conn.executemany("INSERT INTO indicators VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        return len(rows)

    @staticmethod
    def _insert_guardrails(conn, run_id, timestamp, summary) -> int:
        rows = [
            (run_id, timestamp, g.get("name"), int(bool(g.get("allowed"))),
             json.dumps(g.get("reasons") or []))
            for g in (summary.get("guardrails") or [])
        ]
        conn.executemany("INSERT INTO guardrails VALUES (?,?,?,?,?)", rows)
        return len(rows)

    def gate_metrics(
        self, clock_start: str | None = None, baseline_value: float | None = None
    ) -> dict:
        """Portfolio-level metrics for the paper-to-live gate.

        `clock_start` scopes the window to runs at or after that timestamp.
        Without it, every run ever logged counts — including the dormant
        March-April history and the 2026-07-26 rehearsal cleanup — which
        would badly distort the 90-day evaluation. `baseline_value` anchors
        the return/drawdown calculation to the portfolio value recorded at
        clock_start, rather than whatever the first in-window run happened
        to report.

        Deliberately does NOT report consecutive losing *trades*. That needs
        realized round-trip P/L, and Alpaca -- not this log -- is the system of
        record for fills. Deriving it here would be inference presented as fact;
        it belongs in the Alpaca reconciliation step instead.
        """
        window_clause = " AND timestamp >= ?" if clock_start else ""
        window_params = (clock_start,) if clock_start else ()

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT timestamp, portfolio_value FROM runs "
                "WHERE portfolio_value IS NOT NULL" + window_clause +
                " ORDER BY timestamp",
                window_params,
            ).fetchall()
            degraded = conn.execute(
                "SELECT COUNT(*) FROM runs WHERE degraded = 1" + window_clause,
                window_params,
            ).fetchone()[0]
            total_runs = conn.execute(
                "SELECT COUNT(*) FROM runs"
                + (" WHERE timestamp >= ?" if clock_start else ""),
                window_params,
            ).fetchone()[0]

        if not rows:
            return {"runs": total_runs, "valued_runs": 0,
                    "note": "No portfolio values recorded."}

        first = baseline_value if baseline_value is not None else rows[0]["portfolio_value"]
        last = rows[-1]["portfolio_value"]
        peak = max([first, *(r["portfolio_value"] for r in rows)])
        peak_timestamp = (
            clock_start if peak == first and baseline_value is not None
            else next(x["timestamp"] for x in rows if x["portfolio_value"] == peak)
        )
        trough_after_peak = min(
            (r["portfolio_value"] for r in rows if r["timestamp"] >= peak_timestamp),
            default=peak,
        )

        return {
            "runs": total_runs,
            "valued_runs": len(rows),
            "degraded_runs": degraded,
            "clock_start": clock_start,
            "first_timestamp": rows[0]["timestamp"],
            "last_timestamp": rows[-1]["timestamp"],
            "starting_value": first,
            "ending_value": last,
            "peak_value": peak,
            "return_pct": round((last - first) / first * 100, 2) if first else None,
            "max_drawdown_from_peak_pct": (
                round((trough_after_peak - peak) / peak * 100, 2) if peak else None
            ),
            "consecutive_losses": (
                "see scripts/run_trading_bot_reconciliation.sh — realized "
                "round-trip P/L comes from Alpaca fills, not the scan log"
            ),
        }


def _default_paths() -> tuple[Path, Path, Path]:
    from trading_bot.runtime_paths import resolve_paths

    paths = resolve_paths()
    return (
        paths.database_dir / "scans.db",
        paths.trade_log.with_suffix(".jsonl"),
        paths.strategy_config,
    )


def _load_gate_window(strategy_config: Path) -> tuple[str | None, float | None]:
    """Read the paper-to-live clock-start and baseline from the strategy config."""
    if not strategy_config.exists():
        return None, None
    config = json.loads(strategy_config.read_text(encoding="utf-8"))
    window = config.get("paper_to_live") or {}
    return window.get("clock_start"), window.get("baseline_portfolio_value")


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Derived read model over the append-only scan log."
    )
    parser.add_argument("command", choices=["rebuild", "metrics", "query"])
    parser.add_argument("sql", nargs="?", help="SQL for the query command.")
    parser.add_argument("--db", dest="db_path")
    parser.add_argument("--jsonl", dest="jsonl_path")
    args = parser.parse_args(argv)

    default_db, default_jsonl, default_strategy = _default_paths()
    model = ScanReadModel(args.db_path or default_db)

    if args.command == "rebuild":
        stats = model.rebuild(args.jsonl_path or default_jsonl)
        print(json.dumps({"database": str(model.db_path), **stats}, indent=2))
    elif args.command == "metrics":
        clock_start, baseline_value = _load_gate_window(default_strategy)
        print(json.dumps(
            model.gate_metrics(clock_start=clock_start, baseline_value=baseline_value),
            indent=2,
        ))
    else:
        if not args.sql:
            parser.error("query requires a SQL statement")
        with sqlite3.connect(model.db_path) as conn:
            conn.row_factory = sqlite3.Row
            for row in conn.execute(args.sql).fetchall():
                print(json.dumps(dict(row)))


if __name__ == "__main__":
    main()
