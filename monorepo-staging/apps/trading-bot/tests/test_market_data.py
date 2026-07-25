# pyright: reportMissingImports=false

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_bot.integrations.market_data import (  # noqa: E402
    AlpacaMarketDataClient,
    MarketDataError,
)
from trading_bot.models import IndicatorSnapshot  # noqa: E402


def _client(**kwargs) -> AlpacaMarketDataClient:
    # backoff_seconds=0 keeps retry tests instant.
    kwargs.setdefault("backoff_seconds", 0)
    return AlpacaMarketDataClient(api_key="key", secret_key="secret", **kwargs)


def _response(status_code: int = 200, payload: dict | None = None) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload if payload is not None else {"bars": []}
    return response


def _snapshot(symbol: str) -> IndicatorSnapshot:
    return IndicatorSnapshot(
        symbol=symbol, current_price=100.0, ma_20=98.0, ma_50=95.0, rsi=45.0,
        recent_return_5d=1.0, recent_return_20d=1.0, volatility_20d=2.0,
        avg_dollar_volume_20d=25_000_000.0,
        distance_to_ma_20_pct=1.0, distance_to_ma_50_pct=1.0,
    )


class RetryTests(unittest.TestCase):
    def test_transient_connection_error_is_retried_then_succeeds(self) -> None:
        """The exact April failure: `Connection reset by peer` on first attempt."""
        ok = _response()
        with patch(
            "trading_bot.integrations.market_data.requests.get",
            side_effect=[requests.exceptions.ConnectionError("Connection reset by peer"), ok],
        ) as mock_get:
            result = _client()._get_with_retry("http://example/bars", {})

        self.assertIs(result, ok)
        self.assertEqual(mock_get.call_count, 2)

    def test_retries_are_exhausted_and_raise_market_data_error(self) -> None:
        with patch(
            "trading_bot.integrations.market_data.requests.get",
            side_effect=requests.exceptions.ConnectionError("Connection reset by peer"),
        ) as mock_get:
            with self.assertRaises(MarketDataError) as ctx:
                _client(max_attempts=3)._get_with_retry("http://example/bars", {})

        self.assertEqual(mock_get.call_count, 3)
        self.assertIn("after 3 attempt", str(ctx.exception))

    def test_retryable_status_code_is_retried(self) -> None:
        with patch(
            "trading_bot.integrations.market_data.requests.get",
            side_effect=[_response(status_code=503), _response(status_code=200)],
        ) as mock_get:
            _client()._get_with_retry("http://example/bars", {})

        self.assertEqual(mock_get.call_count, 2)

    def test_permanent_client_error_is_not_retried(self) -> None:
        """A bad symbol must fail fast rather than burn the retry budget."""
        bad = _response(status_code=404)
        bad.raise_for_status.side_effect = requests.exceptions.HTTPError("404")

        with patch("trading_bot.integrations.market_data.requests.get", return_value=bad) as mock_get:
            with self.assertRaises(requests.exceptions.HTTPError):
                _client()._get_with_retry("http://example/bars", {})

        self.assertEqual(mock_get.call_count, 1)

    def test_missing_credentials_do_not_consume_retries(self) -> None:
        client = AlpacaMarketDataClient(api_key=None, secret_key=None, backoff_seconds=0)
        with patch("trading_bot.integrations.market_data.requests.get") as mock_get:
            with self.assertRaises(MarketDataError):
                client._get_with_retry("http://example/bars", {})

        mock_get.assert_not_called()


class PerSymbolIsolationTests(unittest.TestCase):
    def test_one_failing_symbol_does_not_lose_the_whole_scan(self) -> None:
        """Regression: a single bad symbol previously zeroed out the entire day."""
        client = _client()
        with patch.object(
            client, "calculate_indicators",
            side_effect=[_snapshot("AAPL"), MarketDataError("boom"), _snapshot("MSFT")],
        ):
            snapshots = client.get_all_indicators(["AAPL", "BAD", "MSFT"])

        self.assertEqual([s.symbol for s in snapshots], ["AAPL", "MSFT"])
        self.assertEqual(client.last_failed_symbols, ["BAD"])

    def test_total_failure_raises_rather_than_looking_like_no_signals(self) -> None:
        client = _client()
        with patch.object(client, "calculate_indicators", side_effect=MarketDataError("boom")):
            with self.assertRaises(MarketDataError) as ctx:
                client.get_all_indicators(["AAPL", "MSFT"])

        self.assertIn("all 2 requested symbol", str(ctx.exception))

    def test_symbols_without_enough_history_are_not_treated_as_failures(self) -> None:
        """calculate_indicators returns None for thin history; that is not an error."""
        client = _client()
        with patch.object(client, "calculate_indicators", return_value=None):
            snapshots = client.get_all_indicators(["AAPL", "MSFT"])

        self.assertEqual(snapshots, [])
        self.assertEqual(client.last_failed_symbols, [])

    def test_failed_symbols_reset_between_calls(self) -> None:
        client = _client()
        with patch.object(client, "calculate_indicators", side_effect=[_snapshot("A"), MarketDataError("x")]):
            client.get_all_indicators(["A", "B"])
        self.assertEqual(client.last_failed_symbols, ["B"])

        with patch.object(client, "calculate_indicators", return_value=_snapshot("A")):
            client.get_all_indicators(["A"])
        self.assertEqual(client.last_failed_symbols, [])


if __name__ == "__main__":
    unittest.main()
