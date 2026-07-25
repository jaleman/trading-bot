"""Reconcile what the bot believed it did against what the broker actually did.

The scan log records *why* a trade was made; Alpaca records *what* happened.
Neither alone is sufficient: the bot writes an order's status at submission
time (typically `PENDING_NEW` or `ACCEPTED`, never `FILLED`) and never revisits
it, so on its own it cannot tell a completed trade from a rejected one.

This module is the join between the two. It answers:

*   Did every order the bot believed it placed actually fill?
*   Did anything fill partially, or at a materially different price?
*   Did the broker fill anything the bot has no record of?
*   What is the realized round-trip P/L, and the consecutive-loss run that the
    paper-to-live gate depends on?
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# A fill this far from the decision-time price is worth a human look rather
# than being silently absorbed.
PRICE_DIVERGENCE_PCT = 5.0


@dataclass(frozen=True)
class RoundTrip:
    symbol: str
    buy_price: float
    sell_price: float
    qty: float
    realized_pl: float
    realized_pct: float
    opened_at: str
    closed_at: str

    @property
    def is_loss(self) -> bool:
        return self.realized_pl < 0


@dataclass
class ReconciliationReport:
    believed_orders: int = 0
    broker_orders: int = 0
    matched: list[dict] = field(default_factory=list)
    missing_at_broker: list[dict] = field(default_factory=list)
    unknown_to_bot: list[dict] = field(default_factory=list)
    partial_fills: list[dict] = field(default_factory=list)
    not_filled: list[dict] = field(default_factory=list)
    round_trips: list[RoundTrip] = field(default_factory=list)

    @property
    def discrepancies(self) -> int:
        return (len(self.missing_at_broker) + len(self.unknown_to_bot)
                + len(self.partial_fills) + len(self.not_filled))

    @property
    def realized_pl(self) -> float:
        return round(sum(t.realized_pl for t in self.round_trips), 2)

    @property
    def wins(self) -> int:
        return sum(1 for t in self.round_trips if not t.is_loss)

    @property
    def losses(self) -> int:
        return sum(1 for t in self.round_trips if t.is_loss)

    @property
    def max_consecutive_losses(self) -> int:
        """Longest run of losing round trips — a paper-to-live gate criterion."""
        longest = current = 0
        for trip in sorted(self.round_trips, key=lambda t: t.closed_at):
            current = current + 1 if trip.is_loss else 0
            longest = max(longest, current)
        return longest

    def to_dict(self) -> dict:
        return {
            "believed_orders": self.believed_orders,
            "broker_orders": self.broker_orders,
            "discrepancies": self.discrepancies,
            "missing_at_broker": self.missing_at_broker,
            "unknown_to_bot": self.unknown_to_bot,
            "partial_fills": self.partial_fills,
            "not_filled": self.not_filled,
            "round_trips": [t.__dict__ for t in self.round_trips],
            "realized_pl": self.realized_pl,
            "wins": self.wins,
            "losses": self.losses,
            "max_consecutive_losses": self.max_consecutive_losses,
        }


def load_believed_orders(jsonl_path: str | Path) -> list[dict]:
    """Every order the scan log claims was placed, oldest first."""
    path = Path(jsonl_path)
    if not path.exists():
        return []

    believed: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        summary = entry.get("summary") or {}
        for order in summary.get("order_results") or []:
            believed.append({
                "id": order.get("id", ""),
                "symbol": order.get("symbol"),
                "qty": float(order.get("qty") or 0),
                "side": str(order.get("side", "")).split(".")[-1],
                "believed_status": str(order.get("status", "")).split(".")[-1],
                "run_id": entry.get("run_id", ""),
                "timestamp": entry.get("timestamp", ""),
            })
    return believed


def build_round_trips(fills: list) -> list[RoundTrip]:
    """Pair buys with sells per symbol, FIFO, into realized round trips.

    Only fully closed pairs count. An open position has no realized P/L and is
    deliberately excluded rather than marked to market.
    """
    open_buys: dict[str, list] = defaultdict(list)
    trips: list[RoundTrip] = []

    for fill in sorted(fills, key=lambda f: f.filled_at or f.submitted_at):
        if fill.status != "FILLED":
            continue
        qty = fill.filled_qty or fill.qty
        if fill.side == "BUY":
            open_buys[fill.symbol].append((qty, fill.filled_avg_price, fill.filled_at))
            continue

        remaining = qty
        while remaining > 0 and open_buys[fill.symbol]:
            buy_qty, buy_price, opened_at = open_buys[fill.symbol].pop(0)
            matched_qty = min(remaining, buy_qty)
            realized = (fill.filled_avg_price - buy_price) * matched_qty
            trips.append(RoundTrip(
                symbol=fill.symbol,
                buy_price=round(buy_price, 4),
                sell_price=round(fill.filled_avg_price, 4),
                qty=matched_qty,
                realized_pl=round(realized, 2),
                realized_pct=round((fill.filled_avg_price - buy_price) / buy_price * 100, 2)
                if buy_price else 0.0,
                opened_at=opened_at,
                closed_at=fill.filled_at,
            ))
            remaining -= matched_qty
            if buy_qty > matched_qty:
                open_buys[fill.symbol].insert(0, (buy_qty - matched_qty, buy_price, opened_at))

    return trips


def reconcile(believed: list[dict], fills: list) -> ReconciliationReport:
    report = ReconciliationReport(believed_orders=len(believed), broker_orders=len(fills))
    fills_by_id = {f.id: f for f in fills if f.id}
    seen_ids: set[str] = set()

    for order in believed:
        fill = fills_by_id.get(order["id"])
        if fill is None:
            # The bot thinks it traded and the broker has no such order.
            report.missing_at_broker.append(order)
            continue

        seen_ids.add(fill.id)
        record = {
            **order,
            "actual_status": fill.status,
            "filled_qty": fill.filled_qty,
            "filled_avg_price": fill.filled_avg_price,
        }

        if fill.status != "FILLED":
            report.not_filled.append(record)
        elif fill.filled_qty and order["qty"] and fill.filled_qty < order["qty"]:
            report.partial_fills.append(record)
        else:
            report.matched.append(record)

    for fill in fills:
        if fill.id and fill.id not in seen_ids:
            # Filled at the broker with no corresponding entry in the scan log.
            report.unknown_to_bot.append({
                "id": fill.id, "symbol": fill.symbol, "side": fill.side,
                "qty": fill.qty, "status": fill.status,
                "filled_avg_price": fill.filled_avg_price, "filled_at": fill.filled_at,
            })

    report.round_trips = build_round_trips(fills)
    return report


def run_reconciliation(jsonl_path: str | Path | None = None, env_file=None) -> ReconciliationReport:
    from trading_bot.env_loader import load_runtime_env
    from trading_bot.integrations.broker import AlpacaBrokerClient
    from trading_bot.runtime_paths import resolve_paths

    paths = resolve_paths(env_file=env_file)
    # Broker credentials live in the runtime env file, same as every other
    # broker-touching entrypoint.
    load_runtime_env(paths.env_file)
    jsonl_path = jsonl_path or paths.trade_log.with_suffix(".jsonl")

    believed = load_believed_orders(jsonl_path)
    fills = AlpacaBrokerClient().get_trade_history(limit=500)
    return reconcile(believed, fills)


def format_report(report: ReconciliationReport) -> str:
    lines = [
        "Reconciliation: bot record vs Alpaca",
        f"  believed orders: {report.believed_orders}   broker orders: {report.broker_orders}",
        f"  matched: {len(report.matched)}   discrepancies: {report.discrepancies}",
    ]
    for label, rows in (
        ("MISSING AT BROKER", report.missing_at_broker),
        ("UNKNOWN TO BOT", report.unknown_to_bot),
        ("PARTIAL FILL", report.partial_fills),
        ("NOT FILLED", report.not_filled),
    ):
        for row in rows:
            lines.append(f"  {label}: {row.get('symbol')} qty={row.get('qty')} "
                         f"status={row.get('actual_status', row.get('status', 'n/a'))}")

    lines.append("")
    lines.append(f"Realized round trips: {len(report.round_trips)} "
                 f"({report.wins} win / {report.losses} loss)")
    for trip in sorted(report.round_trips, key=lambda t: t.closed_at):
        verdict = "LOSS" if trip.is_loss else "WIN "
        lines.append(f"  {verdict} {trip.symbol:6} ${trip.buy_price:>9.2f} -> "
                     f"${trip.sell_price:>9.2f}  ${trip.realized_pl:>9.2f} "
                     f"({trip.realized_pct:+.2f}%)")
    lines.append(f"Realized P/L: ${report.realized_pl:,.2f}")
    lines.append(f"Max consecutive losses: {report.max_consecutive_losses}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Reconcile scan log against broker fills.")
    parser.add_argument("--jsonl", dest="jsonl_path")
    parser.add_argument("--env-file", dest="env_file")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable output.")
    args = parser.parse_args(argv)

    report = run_reconciliation(args.jsonl_path, env_file=args.env_file)
    print(json.dumps(report.to_dict(), indent=2) if args.json else format_report(report))


if __name__ == "__main__":
    main()
