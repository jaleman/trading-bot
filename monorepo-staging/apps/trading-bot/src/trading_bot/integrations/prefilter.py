from __future__ import annotations

import json
from dataclasses import asdict

import requests

from trading_bot.models import IndicatorSnapshot, ScanResult

DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"

PREFILTER_PROMPT = """You are a trading signal filter for a swing trading bot.

You will receive a JSON snapshot of stocks with the following fields for each:
- symbol
- current_price
- ma_20 (20-day moving average)
- ma_50 (50-day moving average)
- rsi (current RSI value)

Classify each stock into one of three categories:

TRIGGERED: Both conditions are fully met
  - ma_20 is ABOVE ma_50 (confirmed crossover)
  - rsi is BELOW 30 (oversold)

WATCHING: One condition is met or close
  - RSI is between 30-35, OR
  - ma_20 is within 1% of ma_50 but not yet crossed

INACTIVE: Neither condition is met

Return ONLY a JSON object in this exact format, no commentary:

{
  "triggered": ["SYMBOL", ...],
  "watching": ["SYMBOL", ...],
  "inactive": ["SYMBOL", ...],
  "summary": "One sentence max. Only mention triggered stocks."
}

If no stocks are triggered, return empty arrays and summary: "No signals today."
"""


class PrefilterError(RuntimeError):
    """Raised when the local prefilter call fails or returns invalid data."""


class OllamaPrefilterClient:
    """Local Ollama prefilter adapter for the rebuilt trading bot."""

    def __init__(self, model: str, url: str = DEFAULT_OLLAMA_URL) -> None:
        self.model = model
        self.url = url

    def classify(self, snapshots: list[IndicatorSnapshot]) -> ScanResult:
        if not snapshots:
            raise PrefilterError("No indicator snapshots available for prefiltering.")

        payload = json.dumps({"stocks": [asdict(item) for item in snapshots]}, indent=2)
        prompt = f"{PREFILTER_PROMPT}\n\nHere is today's data:\n{payload}"

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
            raise PrefilterError("Ollama prefilter response did not contain a JSON object.")

        try:
            parsed = json.loads(raw[start:end])
        except json.JSONDecodeError as exc:
            raise PrefilterError(f"Failed to decode prefilter response JSON: {exc}") from exc

        return ScanResult(
            triggered=parsed.get("triggered", []),
            watching=parsed.get("watching", []),
            inactive=parsed.get("inactive", []),
            summary=parsed.get("summary", ""),
        )
