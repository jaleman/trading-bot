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

# A realistic scan payload (15 candidates plus open positions and full snapshot
# fields) measures close to 4,000 prompt tokens, which overflows Ollama's 4,096
# default. Ollama truncates from the front of the prompt, silently discarding
# the instructions below, so the window is set explicitly.
DEFAULT_NUM_CTX = 8192

# Holds the model resident long enough for the scan's broker and market-data
# fetches to complete between the warm call and the analysis call.
DEFAULT_KEEP_ALIVE = "10m"

# Constrains decoding so the response is always a valid instance of this shape,
# rather than prose or fenced markdown that has to be scraped for braces.
LOCAL_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "ranked_candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "action": {
                        "type": "string",
                        "enum": ["buy", "sell", "watch", "hold", "skip"],
                    },
                    "summary": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["symbol", "action", "summary", "confidence"],
            },
        },
        "escalate_to_claude": {"type": "boolean"},
        "escalation_reason": {"type": "string"},
    },
    "required": [
        "summary",
        "ranked_candidates",
        "escalate_to_claude",
        "escalation_reason",
    ],
}

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

    def __init__(
        self,
        model: str,
        url: str = DEFAULT_OLLAMA_URL,
        num_ctx: int = DEFAULT_NUM_CTX,
        keep_alive: str = DEFAULT_KEEP_ALIVE,
    ) -> None:
        self.model = model
        self.url = url
        self.num_ctx = num_ctx
        self.keep_alive = keep_alive

    def warm(self, timeout: int = 180) -> bool:
        """Preload the model so its load time is not charged to the analysis call.

        A cold Ollama load of a multi-gigabyte model can take longer than the
        analysis request timeout on its own, which is a real risk for a
        once-daily scan that always starts cold. Best-effort: failures here are
        not fatal, the analysis call simply pays the load cost as before.
        """
        try:
            response = requests.post(
                self.url,
                json={
                    "model": self.model,
                    "keep_alive": self.keep_alive,
                    "options": {"num_ctx": self.num_ctx},
                },
                timeout=timeout,
            )
            response.raise_for_status()
        except Exception:
            return False

        return True

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
                # Gemma-class models spend hidden reasoning tokens before
                # emitting any output, which dominated the response time and
                # can consume an entire num_predict budget before the first
                # brace is written.
                "think": False,
                "format": LOCAL_ANALYSIS_SCHEMA,
                "keep_alive": self.keep_alive,
                "options": {"num_ctx": self.num_ctx},
            },
            timeout=90,
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