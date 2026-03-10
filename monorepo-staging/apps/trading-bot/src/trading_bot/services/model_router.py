from __future__ import annotations

from trading_bot.models import LocalAnalysisResult, PositionSnapshot, StrategyConfig, TradeDecision


def should_escalate_to_claude(
    strategy: StrategyConfig,
    local_analysis: LocalAnalysisResult | None,
    positions: list[PositionSnapshot],
    decisions: list[TradeDecision],
) -> tuple[bool, str]:
    if not strategy.model_routing.claude_escalation_enabled:
        return False, "Claude escalation disabled by strategy config."

    if local_analysis is None:
        return False, "Claude escalation skipped because local analysis was not available."

    buy_count = sum(1 for item in decisions if item.action == "buy")
    sell_count = sum(1 for item in decisions if item.action == "sell")
    remaining_slots = max(strategy.risk.max_positions - len(positions), 0)

    if local_analysis.escalate_to_claude:
        return True, local_analysis.escalation_reason or "Local analysis requested escalation."

    if buy_count > remaining_slots and buy_count > 0:
        return True, "Eligible buy candidates exceed remaining portfolio slots."

    if buy_count > 0 and sell_count > 0:
        return True, "Concurrent entry and exit actions warrant portfolio-level review."

    if remaining_slots <= strategy.model_routing.escalate_when_slots_remaining_lte and buy_count > 1:
        return True, "Few remaining slots with multiple buy candidates."

    return False, "Routine local-analysis outcome; no Claude escalation required."