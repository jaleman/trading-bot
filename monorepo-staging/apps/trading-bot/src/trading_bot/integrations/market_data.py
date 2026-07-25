from __future__ import annotations

import os
import random
import time
from datetime import datetime, timedelta

import pandas as pd
import requests

from trading_bot.models import IndicatorSnapshot

DEFAULT_BASE_URL = "https://data.alpaca.markets/v2"

# Two full scan days were lost in April 2026 to `Connection reset by peer`
# reaching Alpaca. A handful of retries with backoff covers that class of
# transient fault without masking a genuine outage.
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BACKOFF_SECONDS = 1.0
MAX_BACKOFF_SECONDS = 8.0

# Rate limiting and gateway errors are worth retrying; other 4xx responses
# (bad symbol, bad credentials) are permanent and retrying only wastes time.
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class MarketDataError(RuntimeError):
    """Raised when market data cannot be fetched or interpreted."""


class AlpacaMarketDataClient:
    """Alpaca market-data adapter for the rebuilt trading bot.

    This is a monorepo-native port of the current `tools/data_tools.py` behavior,
    with clearer boundaries and explicit errors.
    """

    def __init__(
        self,
        api_key: str | None = None,
        secret_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
    ) -> None:
        self.api_key = api_key or os.getenv("ALPACA_API_KEY")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY")
        self.base_url = base_url.rstrip("/")
        self.max_attempts = max(1, max_attempts)
        self.backoff_seconds = max(0.0, backoff_seconds)
        # Populated by get_all_indicators so callers can report partial failures
        # instead of treating a degraded fetch as "no signals today".
        self.last_failed_symbols: list[str] = []
        self.last_failure_reasons: dict[str, str] = {}

    @property
    def headers(self) -> dict[str, str]:
        if not self.api_key or not self.secret_key:
            raise MarketDataError(
                "Missing Alpaca market-data credentials. Set ALPACA_API_KEY and ALPACA_SECRET_KEY."
            )

        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
        }

    def _sleep_before_retry(self, attempt: int) -> None:
        """Exponential backoff with jitter, so retries do not align across symbols."""
        if self.backoff_seconds <= 0:
            return

        delay = min(self.backoff_seconds * (2 ** (attempt - 1)), MAX_BACKOFF_SECONDS)
        time.sleep(delay + random.uniform(0, delay * 0.1))

    def _get_with_retry(self, url: str, params: dict) -> requests.Response:
        """GET with retries for transient transport and gateway failures.

        Credential errors raised by `headers` are not RequestExceptions and so
        propagate immediately rather than burning the retry budget.
        """
        last_error: Exception | None = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
            except requests.exceptions.RequestException as exc:
                last_error = exc
            else:
                if response.status_code not in RETRYABLE_STATUS_CODES:
                    # Permanent 4xx still raises here, which is intended.
                    response.raise_for_status()
                    return response
                last_error = MarketDataError(
                    f"Alpaca returned retryable status {response.status_code}."
                )

            if attempt < self.max_attempts:
                self._sleep_before_retry(attempt)

        raise MarketDataError(
            f"Market data request failed after {self.max_attempts} attempt(s): {last_error}"
        ) from last_error

    def get_bars(
        self,
        symbol: str,
        timeframe: str = "1Day",
        days_back: int = 90,
        limit: int = 1000,
    ) -> pd.DataFrame | None:
        url = f"{self.base_url}/stocks/{symbol}/bars"
        start = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        params = {
            "timeframe": timeframe,
            "start": start,
            "feed": "iex",
            "limit": limit,
        }

        response = self._get_with_retry(url, params)
        data = response.json()
        bars = data.get("bars", [])

        if not bars:
            return None

        frame = pd.DataFrame(bars)
        frame["t"] = pd.to_datetime(frame["t"])
        frame.set_index("t", inplace=True)
        return frame

    def calculate_indicators(self, symbol: str) -> IndicatorSnapshot | None:
        frame = self.get_bars(symbol)

        if frame is None or len(frame) < 50:
            return None

        closes = frame["c"]
        volumes = frame["v"]
        ma_20 = closes.rolling(20).mean().iloc[-1]
        ma_50 = closes.rolling(50).mean().iloc[-1]
        daily_returns = closes.pct_change()

        delta = closes.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = -delta.clip(upper=0).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        recent_return_5d = ((closes.iloc[-1] / closes.iloc[-6]) - 1) * 100 if len(closes) >= 6 else 0.0
        recent_return_20d = ((closes.iloc[-1] / closes.iloc[-21]) - 1) * 100 if len(closes) >= 21 else 0.0
        volatility_20d = daily_returns.tail(20).std() * 100 if len(daily_returns.dropna()) >= 20 else 0.0
        avg_dollar_volume_20d = (closes * volumes).tail(20).mean() if len(frame) >= 20 else 0.0
        current_price = float(closes.iloc[-1])
        distance_to_ma_20_pct = ((current_price - float(ma_20)) / float(ma_20)) * 100 if ma_20 else 0.0
        distance_to_ma_50_pct = ((current_price - float(ma_50)) / float(ma_50)) * 100 if ma_50 else 0.0

        return IndicatorSnapshot(
            symbol=symbol,
            current_price=round(current_price, 2),
            ma_20=round(float(ma_20), 2),
            ma_50=round(float(ma_50), 2),
            rsi=round(float(rsi.iloc[-1]), 2),
            recent_return_5d=round(float(recent_return_5d), 2),
            recent_return_20d=round(float(recent_return_20d), 2),
            volatility_20d=round(float(volatility_20d), 2),
            avg_dollar_volume_20d=round(float(avg_dollar_volume_20d), 2),
            distance_to_ma_20_pct=round(float(distance_to_ma_20_pct), 2),
            distance_to_ma_50_pct=round(float(distance_to_ma_50_pct), 2),
        )

    def get_all_indicators(self, watchlist: list[str]) -> list[IndicatorSnapshot]:
        """Fetch indicators for every symbol, isolating per-symbol failures.

        A single failing symbol previously raised out of this loop and left the
        caller with nothing, which turned one bad request into a skipped
        trading day. Failures are now contained so a partial universe still
        produces a scan; `last_failed_symbols` records what was lost.

        Raises MarketDataError only when nothing at all could be fetched, so a
        total outage is never mistaken for "no signals today".
        """
        # Fail fast on missing credentials rather than once per symbol.
        self.headers

        snapshots: list[IndicatorSnapshot] = []
        failures: dict[str, str] = {}

        for symbol in watchlist:
            try:
                snapshot = self.calculate_indicators(symbol)
            except Exception as exc:
                failures[symbol] = f"{type(exc).__name__}: {exc}"
                continue

            if snapshot:
                snapshots.append(snapshot)

        self.last_failure_reasons = failures
        self.last_failed_symbols = sorted(failures)

        if watchlist and not snapshots and failures:
            raise MarketDataError(
                f"Market data unavailable for all {len(watchlist)} requested symbol(s). "
                f"First error: {next(iter(failures.values()))}"
            )

        return snapshots
