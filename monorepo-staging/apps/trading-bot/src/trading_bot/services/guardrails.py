from __future__ import annotations

from trading_bot.models import (
    AccountSnapshot,
    GuardrailState,
    GuardrailStatus,
    PositionSnapshot,
    StrategyConfig,
    TradeDecision,
)


def evaluate_claude_call_limit(
    strategy: StrategyConfig,
    state: GuardrailState,
) -> GuardrailStatus:
    limit = strategy.cost_controls.daily_claude_call_limit
    allowed = state.claude_calls_today < limit
    reasons = [] if allowed else ["Daily Claude call limit reached."]
    return GuardrailStatus(
        name="daily_claude_call_limit",
        allowed=allowed,
        reasons=reasons,
        details={
            "used": state.claude_calls_today,
            "limit": limit,
            "remaining": max(limit - state.claude_calls_today, 0),
        },
    )


def evaluate_trade_limits(
    strategy: StrategyConfig,
    state: GuardrailState,
    positions: list[PositionSnapshot],
    decisions: list[TradeDecision],
) -> tuple[list[TradeDecision], GuardrailStatus]:
    buy_decisions = [item for item in decisions if item.action == "buy"]
    other_decisions = [item for item in decisions if item.action != "buy"]

    remaining_trade_budget = max(strategy.max_trades_per_day - state.trades_today, 0)
    remaining_position_slots = max(strategy.max_positions - len(positions), 0)
    buy_allowance = min(remaining_trade_budget, remaining_position_slots)

    allowed_buys = buy_decisions[:buy_allowance]
    blocked_buys = buy_decisions[buy_allowance:]

    reasons: list[str] = []
    if remaining_trade_budget == 0 and buy_decisions:
        reasons.append("Daily trade limit reached.")
    if remaining_position_slots == 0 and buy_decisions:
        reasons.append("Maximum simultaneous positions reached.")
    if blocked_buys:
        reasons.append(f"Blocked {len(blocked_buys)} buy decision(s) due to guardrails.")

    status = GuardrailStatus(
        name="trade_execution_limits",
        allowed=not blocked_buys,
        reasons=reasons,
        details={
            "open_positions": len(positions),
            "max_positions": strategy.max_positions,
            "trades_today": state.trades_today,
            "max_trades_per_day": strategy.max_trades_per_day,
            "requested_buys": len(buy_decisions),
            "allowed_buys": len(allowed_buys),
        },
    )

    return [*other_decisions, *allowed_buys], status


def evaluate_execution_policy(strategy: StrategyConfig) -> GuardrailStatus:
    safe_mode = strategy.execution_controls.safe_mode
    paper_enabled = strategy.execution_controls.paper_trade_execution_enabled
    allowed = paper_enabled and not safe_mode
    reasons = []
    if safe_mode:
        reasons.append("Execution blocked because safe mode is enabled.")
    if not paper_enabled:
        reasons.append("Execution blocked because paper-trade execution is disabled in config.")

    return GuardrailStatus(
        name="execution_policy",
        allowed=allowed,
        reasons=reasons,
        details={
            "safe_mode": safe_mode,
            "paper_trade_execution_enabled": paper_enabled,
        },
    )


def evaluate_position_size(
    strategy: StrategyConfig,
    account: AccountSnapshot | None,
) -> GuardrailStatus:
    return GuardrailStatus(
        name="position_size_limit",
        allowed=account is not None and account.portfolio_value > 0,
        reasons=(
            []
            if account is not None and account.portfolio_value > 0
            else ["Position sizing unavailable because account context is missing or empty."]
        ),
        details={
            "max_position_size_pct": strategy.max_position_size_pct,
            "portfolio_value": account.portfolio_value if account is not None else 0,
        },
    )


def validate_execution_intents(
    strategy: StrategyConfig,
    decisions: list[TradeDecision],
    positions: list[PositionSnapshot],
    account: AccountSnapshot | None,
) -> tuple[list[TradeDecision], GuardrailStatus]:
    positions_by_symbol = {position.symbol: position for position in positions}
    seen_executable_symbols: set[str] = set()
    allowed: list[TradeDecision] = []
    blocked_reasons: list[str] = []

    for decision in decisions:
        if decision.action not in {"buy", "sell"}:
            allowed.append(decision)
            continue

        if decision.symbol in seen_executable_symbols:
            blocked_reasons.append(
                f"Blocked duplicate executable action for {decision.symbol}."
            )
            continue

        if decision.action == "buy":
            if decision.symbol in positions_by_symbol and not strategy.risk.allow_pyramiding:
                blocked_reasons.append(
                    f"Blocked buy for {decision.symbol} because the position already exists and pyramiding is disabled."
                )
                continue
            if account is None or account.buying_power <= 0:
                blocked_reasons.append(
                    f"Blocked buy for {decision.symbol} because buying power is unavailable or zero."
                )
                continue

        if decision.action == "sell":
            position = positions_by_symbol.get(decision.symbol)
            if position is None:
                blocked_reasons.append(
                    f"Blocked sell for {decision.symbol} because no open position exists."
                )
                continue

            requested_qty = int(decision.qty or position.qty)
            if requested_qty <= 0:
                blocked_reasons.append(
                    f"Blocked sell for {decision.symbol} because the requested quantity is invalid."
                )
                continue
            if requested_qty > int(position.qty):
                blocked_reasons.append(
                    f"Blocked sell for {decision.symbol} because the requested quantity exceeds the open position size."
                )
                continue

        seen_executable_symbols.add(decision.symbol)
        allowed.append(decision)

    status = GuardrailStatus(
        name="execution_intent_firewall",
        allowed=not blocked_reasons,
        reasons=blocked_reasons,
        details={
            "input_decisions": len(decisions),
            "allowed_decisions": len(allowed),
            "blocked_decisions": len(blocked_reasons),
        },
    )

    return allowed, status
