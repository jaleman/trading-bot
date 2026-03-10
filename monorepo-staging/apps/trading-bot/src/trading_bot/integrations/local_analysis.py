from __future__ import annotations

import json
from dataclasses import asdict

import requests

from trading_bot.models import (
    AccountSnapshot,
    IndicatorSnapshot,
    LocalAnalysisItem,
    LocalAnalysisResult,
    PositionSnapshot,
    StrategyCandidate,
    StrategyConfig,
)

DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"

LOCAL_ANALYSIS_PROMPT = """You are a local market-analysis assistant for a swing trading bot.

You will receive a shortlist of deterministic trading candidates that has already been filtered by code.
Do not re-check the threshold math. Instead:

- rank the candidates by setup quality and actionability
- preserve each candidate's provided action label; you may rank candidates differently, but you must not change buy/sell/watch/hold/skip classifications
- give a concise explanation for each ranked candidate
- use the richer market snapshot fields such as returns, volatility, liquidity, and distance from moving averages
- decide whether the situation is routine enough for local handling or should be escalated to Claude

Return ONLY a JSON object in this exact format:

{
  "summary": "One or two sentences summarizing the best opportunities and risks.",
  "ranked_candidates": [
    {
      "symbol": "TICKER",
      "action": "buy" or "sell" or "watch" or "hold" or "skip",
      "summary": "Short rationale",
      "confidence": 0.0
    }
  ],
  "escalate_to_claude": true,
  "escalation_reason": "Short reason"
}

Use confidence values between 0.0 and 1.0.
Escalate only for ambiguous, high-impact, or portfolio-conflicted situations.
"""


class LocalAnalysisError(RuntimeError):
    """Raised when the local analysis call fails or returns invalid data."""


class OllamaLocalAnalysisClient:
    """Local Ollama analysis adapter for ranked deterministic candidates."""

    def __init__(self, model: str, url: str = DEFAULT_OLLAMA_URL) -> None:
        self.model = model
        self.url = url

    def analyze(
        self,
        *,
        strategy: StrategyConfig,
        candidates: list[StrategyCandidate],
        snapshots: list[IndicatorSnapshot] | None = None,
        account: AccountSnapshot | None = None,
        positions: list[PositionSnapshot] | None = None,
    ) -> LocalAnalysisResult:
        if not candidates:
            raise LocalAnalysisError("No deterministic candidates available for local analysis.")

        snapshots_by_symbol = {
            item.symbol: asdict(item)
            for item in (snapshots or [])
        }
        candidates_by_symbol = {item.symbol: item for item in candidates}
        candidate_payload = [
            {
                "candidate": asdict(item),
                "market_snapshot": snapshots_by_symbol.get(item.symbol),
            }
            for item in candidates
        ]

        payload = {
            "strategy": {
                "max_positions": strategy.risk.max_positions,
                "max_trades_per_day": strategy.risk.max_trades_per_day,
                "max_position_size_pct": strategy.risk.max_position_size_pct,
                "allow_pyramiding": strategy.risk.allow_pyramiding,
            },
            "account": asdict(account) if account is not None else None,
            "positions": [asdict(item) for item in (positions or [])],
            "candidates": candidate_payload,
        }
        prompt = f"{LOCAL_ANALYSIS_PROMPT}\n\nHere is today's shortlist:\n{json.dumps(payload, indent=2)}"

        response = requests.post(
            self.url,
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=60,
        )
        response.raise_for_status()

        raw = response.json().get("response", "")
        start = raw.find("{")
        end = raw.rfind("}") + 1

        if start == -1 or end <= 0:
            raise LocalAnalysisError("Local analysis response did not contain a JSON object.")

        try:
            parsed = json.loads(raw[start:end])
        except json.JSONDecodeError as exc:
            raise LocalAnalysisError(f"Failed to decode local analysis response JSON: {exc}") from exc

        ranked_candidates: list[LocalAnalysisItem] = []
        for item in parsed.get("ranked_candidates", []):
            symbol = item.get("symbol")
            if not symbol:
                continue

            candidate = candidates_by_symbol.get(symbol)
            if candidate is None:
                continue

            ranked_candidates.append(
                LocalAnalysisItem(
                    symbol=symbol,
                    action=candidate.action,
                    summary=item.get("summary") or item.get("reason") or "No local-analysis summary provided.",
                    confidence=float(item.get("confidence", 0.0)),
                )
            )

        if not ranked_candidates:
            ranked_candidates = self._fallback_ranked_candidates(candidates)

        return LocalAnalysisResult(
            summary=parsed.get("summary", ""),
            ranked_candidates=ranked_candidates,
            escalate_to_claude=bool(parsed.get("escalate_to_claude", False)),
            escalation_reason=parsed.get("escalation_reason", ""),
        )

    @staticmethod
    def _fallback_ranked_candidates(
        candidates: list[StrategyCandidate],
    ) -> list[LocalAnalysisItem]:
        ranked: list[LocalAnalysisItem] = []
        priority = {"buy": 0, "sell": 1, "watch": 2, "hold": 3, "skip": 4}

        sorted_candidates = sorted(
            candidates,
            key=lambda item: (priority.get(item.action, 99), -item.score, item.symbol),
        )

        for item in sorted_candidates[:5]:
            confidence = max(0.1, min(0.95, round(item.score / 20, 2)))
            ranked.append(
                LocalAnalysisItem(
                    symbol=item.symbol,
                    action=item.action,
                    summary=item.reason,
                    confidence=confidence,
                )
            )

        return ranked