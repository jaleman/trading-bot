from __future__ import annotations

from trading_bot.models import AccountSnapshot, IndicatorSnapshot, OrderResult, PositionSnapshot, TradeDecision


def calculate_qty(account: AccountSnapshot, price: float, max_position_size_pct: float) -> int:
    """Allocate at most the configured portfolio percentage per position."""
    if price <= 0 or account.portfolio_value <= 0:
        return 0

    max_allocation = account.portfolio_value * (max_position_size_pct / 100)
    qty = int(max_allocation / price)
    return max(qty, 0)


def build_order_results(
    decisions: list[TradeDecision],
    snapshots: list[IndicatorSnapshot],
    positions: list[PositionSnapshot],
    account: AccountSnapshot,
    max_position_size_pct: float,
    place_order: callable,
) -> list[OrderResult]:
    results: list[OrderResult] = []
    price_by_symbol = {snapshot.symbol: snapshot.current_price for snapshot in snapshots}
    positions_by_symbol = {position.symbol: position for position in positions}

    for decision in decisions:
        if decision.action == "buy":
            price = price_by_symbol.get(decision.symbol)
            if price is None:
                continue

            qty = calculate_qty(account, price, max_position_size_pct)
            if qty <= 0:
                continue
            results.append(place_order(decision.symbol, qty, "buy"))
            continue

        if decision.action == "sell":
            position = positions_by_symbol.get(decision.symbol)
            if position is None:
                continue

            qty = int(decision.qty or position.qty)
            if qty <= 0:
                continue
            results.append(place_order(decision.symbol, qty, "sell"))

    return results
