from __future__ import annotations

import json
import os
from dataclasses import asdict

import anthropic

from trading_bot.models import (
    AccountSnapshot,
    IndicatorSnapshot,
    PositionSnapshot,
    StrategyConfig,
    TradeDecision,
)

SYSTEM_PROMPT = """You are a disciplined swing trading bot managing a paper trading portfolio.

Your strategy rules are strict — never deviate from them:
- Entry: 20-day MA must be above 50-day MA AND RSI must be below 30
- Profit target: 8-12% gain
- Stop loss: 4-5% drawdown
- Maximum 4 open positions at any time

For each triggered stock you receive, respond with a JSON decision:
{
  \"symbol\": \"TICKER\",
  \"action\": \"buy\" or \"skip\",
  \"reason\": \"one sentence explanation\",
  \"qty\": number of shares (if buying)
}

Only recommend buying if ALL entry conditions are met and we have room for another position.
Be conservative. When in doubt, skip.
Return a JSON array of decisions, one per triggered stock."""


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

    def decide(
        self,
        *,
        strategy: StrategyConfig,
        triggered_symbols: list[str],
        summary: str,
        stock_data: list[IndicatorSnapshot],
        account: AccountSnapshot | None = None,
        positions: list[PositionSnapshot] | None = None,
    ) -> list[TradeDecision]:
        if not triggered_symbols:
            return []

        account = account or AccountSnapshot(cash=0.0, portfolio_value=0.0, buying_power=0.0)
        positions = positions or []
        position_count = len(positions)

        strategy_payload = {
            "max_positions": strategy.max_positions,
            "profit_target_pct": strategy.exit.profit_target_pct,
            "stop_loss_pct": strategy.exit.stop_loss_pct,
            "rsi_threshold": strategy.entry.rsi_threshold,
            "ma_short": strategy.entry.ma_crossover.short,
            "ma_long": strategy.entry.ma_crossover.long,
        }

        user_message = f"""
Today's triggered signals: {summary}

Account status:
- Portfolio value: ${account.portfolio_value:,.2f}
- Cash available: ${account.cash:,.2f}
- Open positions: {position_count}/{strategy.max_positions}

Current positions:
{json.dumps([asdict(item) for item in positions], indent=2)}

Triggered stock data:
{json.dumps([asdict(item) for item in stock_data], indent=2)}

Strategy rules:
{json.dumps(strategy_payload, indent=2)}

Please analyze each triggered stock and return your decisions as a JSON array.
"""

        response = self.client.messages.create(
            model=strategy.models.daily_decision,
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
