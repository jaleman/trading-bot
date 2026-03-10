from __future__ import annotations

import json
import os
from dataclasses import asdict

import anthropic

from trading_bot.models import (
    AccountSnapshot,
        LocalAnalysisResult,
    PositionSnapshot,
        StrategyCandidate,
    StrategyConfig,
    TradeDecision,
)

SYSTEM_PROMPT = """You are a portfolio review layer for a disciplined swing trading bot.

The deterministic trading engine has already applied the core strategy rules.
Your job is not to re-check simple threshold math. Your job is to review the shortlisted candidates and make a final portfolio-aware recommendation.

You must:
- consider current positions and portfolio capacity
- respect the provided strategy and risk settings
- avoid inventing symbols or actions not present in the candidate set
- be conservative when evidence is mixed

Return ONLY a JSON array of decisions using this format:

[
    {
        \"symbol\": \"TICKER\",
        \"action\": \"buy\" or \"sell\" or \"skip\",
        \"reason\": \"one sentence explanation\",
        \"qty\": number
    }
]

Rules for qty:
- For buy decisions, qty should usually be 0 because code performs final sizing.
- For sell decisions, qty may be 0 to indicate full-position exit.
- For skip decisions, qty must be 0.

Return at most one decision per candidate symbol."""


class DecisionModelError(RuntimeError):
    """Raised when the decision model call fails or returns invalid data."""


class ClaudeDecisionClient:
    """Anthropic decision-model adapter for the rebuilt trading bot."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise DecisionModelError(
                "Missing ANTHROPIC_API_KEY for decision-model adapter."
            )
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def review(
        self,
        *,
        strategy: StrategyConfig,
        candidates: list[StrategyCandidate],
        local_analysis: LocalAnalysisResult,
        account: AccountSnapshot | None = None,
        positions: list[PositionSnapshot] | None = None,
    ) -> list[TradeDecision]:
        if not candidates:
            return []

        account = account or AccountSnapshot(cash=0.0, portfolio_value=0.0, buying_power=0.0)
        positions = positions or []
        position_count = len(positions)

        strategy_payload = {
            "max_positions": strategy.risk.max_positions,
            "max_trades_per_day": strategy.risk.max_trades_per_day,
            "max_position_size_pct": strategy.risk.max_position_size_pct,
            "allow_pyramiding": strategy.risk.allow_pyramiding,
            "profit_target_pct": strategy.exit.profit_target_pct,
            "min_rsi": strategy.entry.min_rsi,
            "stop_loss_pct": strategy.exit.stop_loss_pct,
            "rsi_threshold": strategy.entry.rsi_threshold,
            "ma_short": strategy.entry.ma_crossover.short,
            "ma_long": strategy.entry.ma_crossover.long,
            "max_volatility_20d": strategy.entry.max_volatility_20d,
            "min_recent_return_5d": strategy.entry.min_recent_return_5d,
            "min_recent_return_20d": strategy.entry.min_recent_return_20d,
            "min_distance_to_ma_20_pct": strategy.entry.min_distance_to_ma_20_pct,
            "min_distance_to_ma_50_pct": strategy.entry.min_distance_to_ma_50_pct,
        }

        user_message = f"""
Review reason: {local_analysis.escalation_reason or 'Portfolio review requested.'}

Local analysis summary: {local_analysis.summary}

Account status:
- Portfolio value: ${account.portfolio_value:,.2f}
- Cash available: ${account.cash:,.2f}
- Open positions: {position_count}/{strategy.risk.max_positions}

Current positions:
{json.dumps([asdict(item) for item in positions], indent=2)}

Local analysis ranking:
{json.dumps([asdict(item) for item in local_analysis.ranked_candidates], indent=2)}

Deterministic candidate set:
{json.dumps([asdict(item) for item in candidates], indent=2)}

Strategy rules:
{json.dumps(strategy_payload, indent=2)}

Please review the candidate set and return your final portfolio-aware decisions as a JSON array.
"""

        response = self.client.messages.create(
            model=strategy.models.claude_review,
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text
        start = raw.find("[")
        end = raw.rfind("]") + 1

        if start == -1 or end <= 0:
            raise DecisionModelError("Decision model response did not contain a JSON array.")

        try:
            parsed = json.loads(raw[start:end])
        except json.JSONDecodeError as exc:
            raise DecisionModelError(f"Failed to decode decision JSON: {exc}") from exc

        decisions: list[TradeDecision] = []
        for item in parsed:
            decisions.append(
                TradeDecision(
                    symbol=item["symbol"],
                    action=item["action"],
                    reason=item["reason"],
                    qty=int(item.get("qty", 0) or 0),
                )
            )

        return decisions
