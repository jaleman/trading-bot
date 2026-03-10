from __future__ import annotations

from trading_bot.models import StrategyConfig

CORE_LIQUID_SYMBOLS = [
    "AAPL", "ABBV", "ABT", "ADBE", "AMD", "AMGN", "AMZN", "AVGO", "AXP", "BA",
    "BAC", "BRK.B", "CAT", "COST", "CRM", "CSCO", "CVX", "DIS", "GOOGL", "GS",
    "HD", "HON", "INTC", "JNJ", "JPM", "KO", "LIN", "LLY", "MA", "MCD",
    "META", "MMM", "MRK", "MSFT", "NEE", "NFLX", "NKE", "NVDA", "ORCL", "PEP",
    "PFE", "PG", "QCOM", "SPY", "TMO", "TSLA", "UNH", "UPS", "V", "WMT",
]

MEGA_CAP_TECH_SYMBOLS = [
    "AAPL", "ADBE", "AMD", "AMZN", "AVGO", "CRM", "GOOGL", "META", "MSFT", "NFLX",
    "NVDA", "ORCL", "QCOM", "TSLA",
]

UNIVERSE_PRESETS = {
    "manual": [],
    "core-liquid": CORE_LIQUID_SYMBOLS,
    "mega-cap-tech": MEGA_CAP_TECH_SYMBOLS,
}


class UniverseError(RuntimeError):
    """Raised when a configured scan universe cannot be resolved."""


def _dedupe(symbols: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    for symbol in symbols:
        if symbol in seen:
            continue
        seen.add(symbol)
        ordered.append(symbol)

    return ordered


def resolve_scan_universe(strategy: StrategyConfig) -> list[str]:
    universe = strategy.universe
    preset_name = universe.preset or "manual"

    if preset_name not in UNIVERSE_PRESETS:
        raise UniverseError(f"Unsupported universe preset: {preset_name}")

    if preset_name == "manual":
        base_symbols = list(universe.symbols or strategy.watchlist)
    else:
        base_symbols = list(UNIVERSE_PRESETS[preset_name])

    combined = [
        *base_symbols,
        *universe.symbols,
        *universe.include_symbols,
    ]
    filtered = [symbol for symbol in _dedupe(combined) if symbol not in set(universe.exclude_symbols)]

    if not filtered:
        raise UniverseError("Configured scan universe resolved to zero symbols.")

    return filtered