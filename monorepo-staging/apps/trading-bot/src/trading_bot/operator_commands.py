from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

from trading_bot.env_loader import load_runtime_env
from trading_bot.integrations.broker import AlpacaBrokerClient, BrokerError
from trading_bot.integrations.market_data import AlpacaMarketDataClient, MarketDataError
from trading_bot.operator_summary import format_operator_summary, load_latest_summary_payload
from trading_bot.runtime_paths import resolve_paths


def _normalize_enum_value(value: str) -> str:
    token = value.split(".")[-1]
    return token.replace("_", "-").lower()


def _format_qty(qty: float) -> str:
    if qty.is_integer():
        return str(int(qty))

    return f"{qty:.4f}".rstrip("0").rstrip(".")


def _format_currency(value: float) -> str:
    return f"${value:,.2f}"


def _format_stock_label(symbol: str, asset_name: str | None) -> str:
    if not asset_name:
        return symbol

    return f"{symbol} ({asset_name})"


def _load_guardrail_state(path: Path) -> dict | None:
    if not path.is_file():
        return None

    return json.loads(path.read_text(encoding="utf-8"))


def _extract_payload_date(payload: dict) -> date | None:
    summary = payload.get("summary", payload)
    raw_timestamp = payload.get("timestamp") or summary.get("timestamp")
    if not raw_timestamp:
        return None

    try:
        normalized = str(raw_timestamp).replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).date()
    except ValueError:
        return None


def format_latest_summary(jsonl_path: str | Path | None = None) -> str:
    payload = load_latest_summary_payload(jsonl_path)
    payload_date = _extract_payload_date(payload)
    if payload_date is not None and payload_date != date.today():
        return "No run summary recorded for today."

    return format_operator_summary(payload)


def format_pending_orders(*, env_file: str | Path | None = None, limit: int = 10) -> str:
    load_runtime_env(env_file)
    broker = AlpacaBrokerClient()
    orders = broker.get_open_orders(limit=limit)

    if not orders:
        return "No pending orders."

    lines = [f"Pending orders: {len(orders)}."]
    for order in orders:
        lines.append(
            f"{order.symbol} {_normalize_enum_value(order.side)} qty={_format_qty(order.qty)} "
            f"status={_normalize_enum_value(order.status)} id={order.id}"
        )

    return "\n".join(lines)


def format_runtime_status(
    *,
    env_file: str | Path | None = None,
) -> str:
    paths = resolve_paths(env_file=env_file)
    summary_path = paths.trade_log.with_suffix(".jsonl")
    lines: list[str] = []

    try:
        payload = load_latest_summary_payload(summary_path)
    except (FileNotFoundError, ValueError):
        lines.append("Runtime status: no summary log found.")
    else:
        summary = payload.get("summary", payload)
        timestamp = payload.get("timestamp") or summary.get("timestamp") or "unknown"
        status = summary.get("status", "unknown")
        paper_orders = len(summary.get("order_results", []))
        lines.append(
            f"Runtime status: latest summary at {timestamp}; status={status}; paper_orders={paper_orders}."
        )

    lines.append(
        "Artifacts: "
        f"trades.log={'yes' if paths.trade_log.is_file() else 'no'} "
        f"trades.jsonl={'yes' if summary_path.is_file() else 'no'} "
        f"guardrail-state={'yes' if paths.guardrail_state.is_file() else 'no'}."
    )

    guardrail_state = _load_guardrail_state(paths.guardrail_state)
    if guardrail_state is None:
        lines.append("Guardrails: unavailable.")
    else:
        lines.append(
            "Guardrails: "
            f"date={guardrail_state.get('current_date', 'unknown')} "
            f"claude_calls_today={int(guardrail_state.get('claude_calls_today', 0))} "
            f"trades_today={int(guardrail_state.get('trades_today', 0))}."
        )

    try:
        load_runtime_env(paths.env_file)
        broker = AlpacaBrokerClient()
        broker.get_account_balance()
    except Exception as exc:  # pragma: no cover - external broker failure paths vary.
        lines.append(f"Broker: unavailable ({str(exc).strip()}).")
    else:
        lines.append("Broker: connected.")

    return "\n".join(lines)


def format_balance(*, env_file: str | Path | None = None) -> str:
    load_runtime_env(env_file)
    broker = AlpacaBrokerClient()
    account = broker.get_account_balance()
    positions = broker.get_open_positions()
    holdings_value = sum(position.qty * position.current_price for position in positions)

    lines = [
        "Balance: "
        f"cash={_format_currency(account.cash)} "
        f"holdings={_format_currency(holdings_value)} "
        f"portfolio={_format_currency(account.portfolio_value)} "
        f"buying_power={_format_currency(account.buying_power)}."
    ]
    lines.append(f"Open positions: {len(positions)}.")

    return "\n".join(lines)


def format_holdings(*, env_file: str | Path | None = None) -> str:
    load_runtime_env(env_file)
    broker = AlpacaBrokerClient()
    positions = broker.get_open_positions()

    if not positions:
        return "No open holdings."

    ordered_positions = sorted(positions, key=lambda position: position.symbol)
    lines = [f"Holdings: {len(ordered_positions)} open position(s)."]
    for position in ordered_positions:
        market_value = position.qty * position.current_price
        lines.append(
            f"{position.symbol} qty={_format_qty(position.qty)} "
            f"market_value={_format_currency(market_value)} "
            f"avg_entry={_format_currency(position.avg_entry_price)} "
            f"current={_format_currency(position.current_price)} "
            f"unrealized_pl={_format_currency(position.unrealized_pl)} "
            f"unrealized_plpc={position.unrealized_plpc * 100:.2f}%"
        )

    return "\n".join(lines)


def format_stock_info(symbol: str, *, env_file: str | Path | None = None) -> str:
    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol:
        raise ValueError("Missing ticker symbol. Use /Info <TICKER>.")

    load_runtime_env(env_file)
    asset_name: str | None = None
    try:
        broker = AlpacaBrokerClient()
        asset_name = broker.get_asset_name(normalized_symbol)
    except Exception:
        asset_name = None

    client = AlpacaMarketDataClient()
    snapshot = client.calculate_indicators(normalized_symbol)
    if snapshot is None:
        raise ValueError(f"No market data snapshot available for {normalized_symbol}.")

    lines = [
        f"{_format_stock_label(normalized_symbol, asset_name)}: price={_format_currency(snapshot.current_price)} rsi={snapshot.rsi:.2f}.",
        f"Trend: ma20={_format_currency(snapshot.ma_20)} ma50={_format_currency(snapshot.ma_50)}.",
        f"Returns: 5d={snapshot.recent_return_5d:.2f}% 20d={snapshot.recent_return_20d:.2f}% volatility20d={snapshot.volatility_20d:.2f}%.",
        f"Distance: ma20={snapshot.distance_to_ma_20_pct:.2f}% ma50={snapshot.distance_to_ma_50_pct:.2f}% avg_dollar_volume20d={_format_currency(snapshot.avg_dollar_volume_20d)}.",
    ]

    return "\n".join(lines)


def format_supported_commands() -> str:
    return "\n".join(
        [
            "Supported commands:",
            "/bot list - list supported commands",
            "/bot summary - today's run summary",
            "/bot pending - open orders",
            "/bot status - runtime health",
            "/bot balance - aggregate account values",
            "/bot holdings - open position breakdown",
            "/bot info <TICKER> - market snapshot for one ticker",
            "bot list | bot summary | bot pending | bot status | bot balance | bot holdings | bot info <TICKER> - plain-text fallback inputs",
            "/Summary, /Pending, /Status, /Balance, /Holdings, /Info - compatibility aliases",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Print staged OpenClaw operator command output")
    subparsers = parser.add_subparsers(dest="command", required=True)

    summary_parser = subparsers.add_parser("summary", help="Print the latest operator summary")
    summary_parser.add_argument(
        "--jsonl",
        dest="jsonl_path",
        help="Optional path to the staged JSONL summary log.",
    )

    pending_orders_parser = subparsers.add_parser(
        "pending-orders",
        help="Print broker-backed pending orders.",
    )
    pending_orders_parser.add_argument(
        "--env-file",
        dest="env_file",
        help="Optional path to the staged env file used for broker credentials.",
    )
    pending_orders_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of open orders to print.",
    )

    runtime_status_parser = subparsers.add_parser(
        "runtime-status",
        help="Print the current staged runtime status.",
    )
    runtime_status_parser.add_argument(
        "--env-file",
        dest="env_file",
        help="Optional path to the staged env file used for broker credentials.",
    )

    balance_parser = subparsers.add_parser(
        "balance",
        help="Print the current account balance summary.",
    )
    balance_parser.add_argument(
        "--env-file",
        dest="env_file",
        help="Optional path to the staged env file used for broker credentials.",
    )

    holdings_parser = subparsers.add_parser(
        "holdings",
        help="Print the current open holdings breakdown.",
    )
    holdings_parser.add_argument(
        "--env-file",
        dest="env_file",
        help="Optional path to the staged env file used for broker credentials.",
    )

    info_parser = subparsers.add_parser(
        "info",
        help="Print current market snapshot information for a ticker.",
    )
    info_parser.add_argument(
        "symbol",
        help="Ticker symbol to inspect.",
    )
    info_parser.add_argument(
        "--env-file",
        dest="env_file",
        help="Optional path to the staged env file used for broker credentials.",
    )

    subparsers.add_parser(
        "list-commands",
        help="Print the supported operator commands.",
    )

    return parser


def _operator_logger():
    """Logger for operator activity, or None if the runtime is unavailable.

    Built once per invocation so the whole command shares a single run ID and
    its start/outcome lines can be correlated.
    """
    try:
        from trading_bot.persistence.trade_log import TradeLogger
        from trading_bot.runtime_paths import ensure_runtime_dirs, resolve_paths

        paths = ensure_runtime_dirs(resolve_paths())
        return TradeLogger(paths.operator_log)
    except Exception:
        return None


def log_operator_activity(logger, command: str, status: str, detail: str = "") -> None:
    """Record one operator command event.

    Best-effort by design: a logging failure must never break the operator
    command the user is actually running. Only the command name and outcome
    are recorded -- never env file contents or credentials.
    """
    if logger is None:
        return
    try:
        suffix = f" — {detail}" if detail else ""
        logger.log_message(f"operator command '{command}' {status}{suffix}")
    except Exception:
        return


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = getattr(args, "command", "unknown")

    logger = _operator_logger()
    log_operator_activity(logger, command, "invoked")

    try:
        _dispatch(args)
    except SystemExit as exc:
        log_operator_activity(logger, command, "failed", str(exc))
        raise
    except BaseException as exc:
        log_operator_activity(logger, command, "failed", f"{type(exc).__name__}: {exc}")
        raise
    else:
        log_operator_activity(logger, command, "completed")


def _dispatch(args) -> None:
    try:
        if args.command == "summary":
            print(format_latest_summary(args.jsonl_path))
            return

        if args.command == "pending-orders":
            print(format_pending_orders(env_file=args.env_file, limit=args.limit))
            return

        if args.command == "runtime-status":
            print(format_runtime_status(env_file=args.env_file))
            return

        if args.command == "balance":
            print(format_balance(env_file=args.env_file))
            return

        if args.command == "holdings":
            print(format_holdings(env_file=args.env_file))
            return

        if args.command == "info":
            print(format_stock_info(args.symbol, env_file=args.env_file))
            return

        if args.command == "list-commands":
            print(format_supported_commands())
            return
    except (BrokerError, FileNotFoundError, ValueError, MarketDataError) as exc:
        raise SystemExit(str(exc)) from exc

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()