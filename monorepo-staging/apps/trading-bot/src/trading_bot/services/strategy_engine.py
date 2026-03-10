from __future__ import annotations

from trading_bot.models import (
    IndicatorSnapshot,
    PositionSnapshot,
    ScanResult,
    StrategyCandidate,
    StrategyConfig,
    StrategyEvaluation,
    TradeDecision,
)


def _ma_gap_pct(snapshot: IndicatorSnapshot) -> float:
    if snapshot.ma_50 == 0:
        return 0.0

    return ((snapshot.ma_20 - snapshot.ma_50) / snapshot.ma_50) * 100


def _passes_universe_filters(snapshot: IndicatorSnapshot, strategy: StrategyConfig) -> tuple[bool, str]:
    min_price = strategy.universe.min_price
    min_avg_dollar_volume = strategy.universe.min_avg_dollar_volume

    if min_price is not None and snapshot.current_price < min_price:
        return False, (
            f"Filtered out: current price {snapshot.current_price:.2f} is below the minimum "
            f"price threshold of {min_price:.2f}."
        )

    if min_avg_dollar_volume is not None and snapshot.avg_dollar_volume_20d < min_avg_dollar_volume:
        return False, (
            f"Filtered out: 20-day average dollar volume {snapshot.avg_dollar_volume_20d:.2f} is below "
            f"the minimum threshold of {min_avg_dollar_volume:.2f}."
        )

    return True, ""


def _entry_reason(snapshot: IndicatorSnapshot, strategy: StrategyConfig) -> tuple[bool, str, float]:
    ma_gap_pct = _ma_gap_pct(snapshot)
    min_rsi = strategy.entry.min_rsi
    rsi_threshold = strategy.entry.rsi_threshold
    volatility_cap = strategy.entry.max_volatility_20d
    min_recent_return_5d = strategy.entry.min_recent_return_5d
    min_recent_return_20d = strategy.entry.min_recent_return_20d
    min_distance_to_ma_20_pct = strategy.entry.min_distance_to_ma_20_pct
    min_distance_to_ma_50_pct = strategy.entry.min_distance_to_ma_50_pct

    entry_failures: list[str] = []
    if snapshot.ma_20 <= snapshot.ma_50:
        entry_failures.append(f"MA gap is {ma_gap_pct:.2f}% and must remain positive.")
    if snapshot.rsi > rsi_threshold:
        entry_failures.append(
            f"RSI is {snapshot.rsi:.2f} versus threshold {rsi_threshold:.2f}."
        )
    if min_rsi is not None and snapshot.rsi < min_rsi:
        entry_failures.append(
            f"RSI is {snapshot.rsi:.2f} which is below the minimum required {min_rsi:.2f}."
        )
    if volatility_cap is not None and snapshot.volatility_20d > volatility_cap:
        entry_failures.append(
            f"Volatility {snapshot.volatility_20d:.2f}% exceeds the maximum allowed {volatility_cap:.2f}%."
        )
    if min_recent_return_5d is not None and snapshot.recent_return_5d < min_recent_return_5d:
        entry_failures.append(
            "5-day return is "
            f"{snapshot.recent_return_5d:.2f}% which is below the minimum allowed {min_recent_return_5d:.2f}%."
        )
    if min_recent_return_20d is not None and snapshot.recent_return_20d < min_recent_return_20d:
        entry_failures.append(
            "20-day return is "
            f"{snapshot.recent_return_20d:.2f}% which is below the minimum allowed {min_recent_return_20d:.2f}%."
        )
    if min_distance_to_ma_20_pct is not None and snapshot.distance_to_ma_20_pct < min_distance_to_ma_20_pct:
        entry_failures.append(
            "Price is "
            f"{snapshot.distance_to_ma_20_pct:.2f}% below MA{strategy.entry.ma_crossover.short}, "
            f"beyond the minimum allowed {min_distance_to_ma_20_pct:.2f}%."
        )
    if min_distance_to_ma_50_pct is not None and snapshot.distance_to_ma_50_pct < min_distance_to_ma_50_pct:
        entry_failures.append(
            "Price is "
            f"{snapshot.distance_to_ma_50_pct:.2f}% below MA{strategy.entry.ma_crossover.long}, "
            f"beyond the minimum allowed {min_distance_to_ma_50_pct:.2f}%."
        )

    is_entry = not entry_failures

    score = round(
        max(
            max(ma_gap_pct, 0.0)
            + max(rsi_threshold - snapshot.rsi, 0.0) * 0.35
            + max(snapshot.recent_return_20d, 0.0) * 0.2
            - max(-snapshot.distance_to_ma_20_pct, 0.0) * 0.6
            - max(-snapshot.distance_to_ma_50_pct, 0.0) * 0.8
            - max(-snapshot.recent_return_20d, 0.0) * 0.25,
            0.0,
        ),
        2,
    )

    if is_entry:
        reason = (
            f"Entry signal confirmed: MA{strategy.entry.ma_crossover.short} is above "
            f"MA{strategy.entry.ma_crossover.long} by {ma_gap_pct:.2f}%, RSI is {snapshot.rsi:.2f}, "
            f"5-day return is {snapshot.recent_return_5d:.2f}%, 20-day return is {snapshot.recent_return_20d:.2f}%, "
            f"and price is {snapshot.distance_to_ma_20_pct:.2f}% versus MA{strategy.entry.ma_crossover.short}."
        )
        return True, reason, score

    reason = "Entry not confirmed: " + " ".join(entry_failures)
    return False, reason, score


def _has_hard_entry_failures(snapshot: IndicatorSnapshot, strategy: StrategyConfig) -> bool:
    min_recent_return_5d = strategy.entry.min_recent_return_5d
    min_recent_return_20d = strategy.entry.min_recent_return_20d
    min_distance_to_ma_20_pct = strategy.entry.min_distance_to_ma_20_pct
    min_distance_to_ma_50_pct = strategy.entry.min_distance_to_ma_50_pct

    return (
        (
            min_recent_return_5d is not None
            and snapshot.recent_return_5d < min_recent_return_5d
        )
        or (
            strategy.entry.min_rsi is not None
            and snapshot.rsi < strategy.entry.min_rsi
        )
        or (
            min_recent_return_20d is not None
            and snapshot.recent_return_20d < min_recent_return_20d
        )
        or (
            min_distance_to_ma_20_pct is not None
            and snapshot.distance_to_ma_20_pct < min_distance_to_ma_20_pct
        )
        or (
            min_distance_to_ma_50_pct is not None
            and snapshot.distance_to_ma_50_pct < min_distance_to_ma_50_pct
        )
    )


def _is_watching(snapshot: IndicatorSnapshot, strategy: StrategyConfig) -> bool:
    if _has_hard_entry_failures(snapshot, strategy):
        return False

    rsi_close = snapshot.rsi <= strategy.entry.rsi_threshold + 5
    ma_close = abs(_ma_gap_pct(snapshot)) <= 1.0
    return rsi_close or ma_close


def _exit_reason(position: PositionSnapshot, strategy: StrategyConfig) -> tuple[bool, str, float, str]:
    pnl_pct = position.unrealized_plpc * 100
    profit_target = strategy.exit.profit_target_pct
    stop_loss = strategy.exit.stop_loss_pct

    if pnl_pct >= profit_target:
        reason = (
            f"Exit signal confirmed: unrealized gain is {pnl_pct:.2f}% which meets the "
            f"profit target of {profit_target:.2f}%."
        )
        return True, reason, round(pnl_pct, 2), "sell"

    if pnl_pct <= -stop_loss:
        reason = (
            f"Exit signal confirmed: unrealized drawdown is {pnl_pct:.2f}% which breaches the "
            f"stop loss of -{stop_loss:.2f}%."
        )
        return True, reason, round(abs(pnl_pct), 2), "sell"

    reason = (
        f"Hold position: unrealized P/L is {pnl_pct:.2f}% versus target {profit_target:.2f}% "
        f"and stop -{stop_loss:.2f}%."
    )
    return False, reason, round(pnl_pct, 2), "hold"


def evaluate_strategy(
    strategy: StrategyConfig,
    snapshots: list[IndicatorSnapshot],
    positions: list[PositionSnapshot] | None = None,
) -> StrategyEvaluation:
    positions = positions or []
    positions_by_symbol = {position.symbol: position for position in positions}

    triggered: list[str] = []
    watching: list[str] = []
    inactive: list[str] = []
    candidates: list[StrategyCandidate] = []
    entry_decisions: list[TradeDecision] = []
    exit_decisions: list[TradeDecision] = []

    for snapshot in snapshots:
        passes_universe_filters, filter_reason = _passes_universe_filters(snapshot, strategy)
        if not passes_universe_filters:
            inactive.append(snapshot.symbol)
            candidates.append(
                StrategyCandidate(
                    symbol=snapshot.symbol,
                    action="skip",
                    reason=filter_reason,
                    score=0.0,
                )
            )
            continue

        entry_ok, entry_reason, entry_score = _entry_reason(snapshot, strategy)
        has_position = snapshot.symbol in positions_by_symbol

        if entry_ok:
            triggered.append(snapshot.symbol)
            if has_position and not strategy.risk.allow_pyramiding:
                candidates.append(
                    StrategyCandidate(
                        symbol=snapshot.symbol,
                        action="hold",
                        reason="Entry signal present, but symbol is already held and pyramiding is disabled.",
                        score=entry_score,
                    )
                )
            else:
                candidates.append(
                    StrategyCandidate(
                        symbol=snapshot.symbol,
                        action="buy",
                        reason=entry_reason,
                        score=entry_score,
                    )
                )
                entry_decisions.append(
                    TradeDecision(symbol=snapshot.symbol, action="buy", reason=entry_reason)
                )
        elif _is_watching(snapshot, strategy):
            watching.append(snapshot.symbol)
            candidates.append(
                StrategyCandidate(
                    symbol=snapshot.symbol,
                    action="watch",
                    reason=entry_reason,
                    score=entry_score,
                )
            )
        else:
            inactive.append(snapshot.symbol)
            candidates.append(
                StrategyCandidate(
                    symbol=snapshot.symbol,
                    action="skip",
                    reason=entry_reason,
                    score=entry_score,
                )
            )

    for position in positions:
        exit_ok, exit_reason, exit_score, action = _exit_reason(position, strategy)
        candidates.append(
            StrategyCandidate(
                symbol=position.symbol,
                action=action,
                reason=exit_reason,
                score=exit_score,
            )
        )
        if exit_ok:
            exit_decisions.append(
                TradeDecision(
                    symbol=position.symbol,
                    action="sell",
                    reason=exit_reason,
                    qty=int(position.qty),
                )
            )

    entry_summary = ", ".join(triggered) if triggered else "none"
    exit_summary = ", ".join(item.symbol for item in exit_decisions) if exit_decisions else "none"
    classification = ScanResult(
        triggered=triggered,
        watching=watching,
        inactive=inactive,
        summary=f"Entry candidates: {entry_summary}. Exit candidates: {exit_summary}.",
    )

    return StrategyEvaluation(
        classification=classification,
        candidates=candidates,
        entry_decisions=entry_decisions,
        exit_decisions=exit_decisions,
    )