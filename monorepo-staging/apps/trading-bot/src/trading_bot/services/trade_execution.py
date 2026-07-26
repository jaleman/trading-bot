from __future__ import annotations

from trading_bot.models import AccountSnapshot, IndicatorSnapshot, OrderResult, PositionSnapshot, TradeDecision


def calculate_qty(
    account: AccountSnapshot,
    price: float,
    max_position_size_pct: float,
    available_cash: float | None = None,
) -> int:
    """Allocate at most the configured portfolio percentage per position.

    Sizing is based on portfolio value, which is what makes four 25% positions
    equal exactly 100% of equity. When `available_cash` is supplied the
    allocation is additionally capped by it, so a buy can never be funded on
    margin — the strategy is validated unlevered, and a levered return would
    not be the strategy's return.
    """
    if price <= 0 or account.portfolio_value <= 0:
        return 0

    max_allocation = account.portfolio_value * (max_position_size_pct / 100)
    if available_cash is not None:
        max_allocation = min(max_allocation, available_cash)
    if max_allocation <= 0:
        return 0

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

    # Track cash across the loop. Sizing each buy against the same starting
    # snapshot would let two buys in one scan each claim 25% of the portfolio
    # while only one of them is actually affordable, and the shortfall would
    # be silently financed on margin.
    remaining_cash = account.cash

    for decision in decisions:
        if decision.action == "buy":
            price = price_by_symbol.get(decision.symbol)
            if price is None:
                continue

            qty = calculate_qty(account, price, max_position_size_pct, remaining_cash)
            if qty <= 0:
                continue
            results.append(place_order(decision.symbol, qty, "buy"))
            remaining_cash -= qty * price
            continue

        if decision.action == "sell":
            position = positions_by_symbol.get(decision.symbol)
            if position is None:
                continue

            qty = int(decision.qty or position.qty)
            if qty <= 0:
                continue
            results.append(place_order(decision.symbol, qty, "sell"))
            # Proceeds are deliberately NOT credited to remaining_cash. The
            # sale has been submitted, not settled, and spending unsettled
            # proceeds is precisely how an unlevered account drifts into
            # margin. A freed slot is taken on the next scan instead.

    return results
