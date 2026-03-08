from __future__ import annotations

from trading_bot.models import AccountSnapshot, IndicatorSnapshot, PositionSnapshot, TradeDecision


def build_stub_account() -> AccountSnapshot:
    """Temporary account stub until broker adapter is ported."""
    return AccountSnapshot(cash=0.0, portfolio_value=0.0, buying_power=0.0)


def build_stub_positions() -> list[PositionSnapshot]:
    """Temporary positions stub until broker adapter is ported."""
    return []


def filter_triggered_snapshots(
    snapshots: list[IndicatorSnapshot],
    triggered_symbols: list[str],
) -> list[IndicatorSnapshot]:
    return [snapshot for snapshot in snapshots if snapshot.symbol in triggered_symbols]


def summarize_decisions(decisions: list[TradeDecision]) -> str:
    if not decisions:
        return "No decision-model output."

    buys = sum(1 for item in decisions if item.action == "buy")
    skips = sum(1 for item in decisions if item.action == "skip")
    sells = sum(1 for item in decisions if item.action == "sell")
    return f"Decision model returned {buys} buy, {sells} sell, and {skips} skip decisions."
