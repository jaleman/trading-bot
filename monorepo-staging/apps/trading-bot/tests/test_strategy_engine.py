# pyright: reportMissingImports=false

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_bot.models import (  # noqa: E402
    CostControlsConfig,
    EntryConfig,
    ExecutionControlsConfig,
    ExitConfig,
    IndicatorSnapshot,
    ModelsConfig,
    ModelRoutingConfig,
    MovingAverageConfig,
    PaperToLiveConfig,
    PositionSnapshot,
    RiskConfig,
    StrategyConfig,
    UniverseConfig,
)
from trading_bot.services.strategy_engine import evaluate_strategy  # noqa: E402
from trading_bot.services.universe import resolve_scan_universe  # noqa: E402


def build_strategy() -> StrategyConfig:
    return StrategyConfig(
        watchlist=["JPM", "MSFT"],
        max_positions=4,
        max_trades_per_day=2,
        max_position_size_pct=25,
        entry=EntryConfig(
            ma_crossover=MovingAverageConfig(short=20, long=50),
            min_rsi=None,
            rsi_threshold=30,
            max_volatility_20d=4.5,
        ),
        exit=ExitConfig(profit_target_pct=10, stop_loss_pct=4.5),
        models=ModelsConfig(
            daily_decision="claude-sonnet-4-6",
            monitoring="qwen2.5:7b",
        ),
        cost_controls=CostControlsConfig(
            daily_claude_call_limit=5,
            context_reset_after_exchanges=20,
            prompt_caching_enabled=True,
        ),
        execution_controls=ExecutionControlsConfig(
            safe_mode=True,
            paper_trade_execution_enabled=False,
            write_logs_by_default=True,
        ),
        paper_to_live=PaperToLiveConfig(
            min_return_pct=3.75,
            evaluation_days=90,
            max_consecutive_losses=2,
        ),
        universe=UniverseConfig(symbols=["JPM", "MSFT"], shortlist_size=10),
        risk=RiskConfig(
            max_positions=4,
            max_trades_per_day=2,
            max_position_size_pct=25,
            max_sector_exposure_pct=None,
            allow_pyramiding=False,
        ),
        model_routing=ModelRoutingConfig(),
    )


class StrategyEngineTests(unittest.TestCase):
    def test_entry_signal_generates_buy_decision(self) -> None:
        strategy = build_strategy()
        evaluation = evaluate_strategy(
            strategy,
            [IndicatorSnapshot(symbol="JPM", current_price=100, ma_20=101, ma_50=99, rsi=25)],
            [],
        )

        self.assertEqual(evaluation.classification.triggered, ["JPM"])
        self.assertEqual([item.action for item in evaluation.entry_decisions], ["buy"])

    def test_existing_position_blocks_duplicate_buy_when_pyramiding_disabled(self) -> None:
        strategy = build_strategy()
        evaluation = evaluate_strategy(
            strategy,
            [IndicatorSnapshot(symbol="JPM", current_price=100, ma_20=101, ma_50=99, rsi=25)],
            [PositionSnapshot("JPM", 1, 90, 100, 10, 0.11)],
        )

        self.assertEqual(evaluation.classification.triggered, ["JPM"])
        self.assertEqual(evaluation.entry_decisions, [])
        self.assertTrue(any(item.action == "hold" for item in evaluation.candidates))

    def test_profit_target_generates_sell_decision(self) -> None:
        strategy = build_strategy()
        evaluation = evaluate_strategy(
            strategy,
            [IndicatorSnapshot(symbol="JPM", current_price=100, ma_20=98, ma_50=101, rsi=45)],
            [PositionSnapshot("JPM", 3, 90, 100, 30, 0.12)],
        )

        self.assertEqual([item.action for item in evaluation.exit_decisions], ["sell"])
        self.assertEqual(evaluation.exit_decisions[0].qty, 3)

    def test_universe_builder_resolves_preset_with_include_and_exclude(self) -> None:
        strategy = build_strategy()
        strategy = StrategyConfig(
            **{
                **strategy.__dict__,
                "universe": UniverseConfig(
                    preset="mega-cap-tech",
                    symbols=[],
                    include_symbols=["JPM"],
                    exclude_symbols=["TSLA"],
                    shortlist_size=10,
                ),
            }
        )

        symbols = resolve_scan_universe(strategy)

        self.assertIn("MSFT", symbols)
        self.assertIn("JPM", symbols)
        self.assertNotIn("TSLA", symbols)

    def test_low_dollar_volume_blocks_entry_candidate(self) -> None:
        strategy = build_strategy()
        strategy = StrategyConfig(
            **{
                **strategy.__dict__,
                "universe": UniverseConfig(
                    preset="manual",
                    symbols=["JPM"],
                    min_price=20,
                    min_avg_dollar_volume=15000000,
                    shortlist_size=10,
                ),
            }
        )

        evaluation = evaluate_strategy(
            strategy,
            [
                IndicatorSnapshot(
                    symbol="JPM",
                    current_price=100,
                    ma_20=101,
                    ma_50=99,
                    rsi=25,
                    avg_dollar_volume_20d=5000000,
                )
            ],
            [],
        )

        self.assertEqual(evaluation.entry_decisions, [])
        self.assertIn("JPM", evaluation.classification.inactive)
        self.assertTrue(any("minimum threshold" in item.reason for item in evaluation.candidates))

    def test_excess_volatility_blocks_entry_candidate(self) -> None:
        strategy = build_strategy()
        evaluation = evaluate_strategy(
            strategy,
            [
                IndicatorSnapshot(
                    symbol="JPM",
                    current_price=100,
                    ma_20=101,
                    ma_50=99,
                    rsi=25,
                    volatility_20d=6.0,
                    avg_dollar_volume_20d=20000000,
                )
            ],
            [],
        )

        self.assertEqual(evaluation.entry_decisions, [])
        self.assertTrue(any("Volatility 6.00% exceeds" in item.reason for item in evaluation.candidates))

    def test_deep_pullback_below_moving_averages_blocks_entry_candidate(self) -> None:
        strategy = build_strategy()
        strategy = StrategyConfig(
            **{
                **strategy.__dict__,
                "entry": EntryConfig(
                    ma_crossover=MovingAverageConfig(short=20, long=50),
                    rsi_threshold=30,
                    max_volatility_20d=4.5,
                    min_distance_to_ma_20_pct=-5.0,
                    min_distance_to_ma_50_pct=-3.0,
                ),
            }
        )

        evaluation = evaluate_strategy(
            strategy,
            [
                IndicatorSnapshot(
                    symbol="JPM",
                    current_price=100,
                    ma_20=101,
                    ma_50=99,
                    rsi=25,
                    distance_to_ma_20_pct=-6.0,
                    distance_to_ma_50_pct=-4.0,
                    avg_dollar_volume_20d=20000000,
                )
            ],
            [],
        )

        self.assertEqual(evaluation.entry_decisions, [])
        self.assertIn("JPM", evaluation.classification.inactive)
        self.assertNotIn("JPM", evaluation.classification.watching)
        self.assertTrue(any("below MA20" in item.reason for item in evaluation.candidates))
        self.assertTrue(any("below MA50" in item.reason for item in evaluation.candidates))

    def test_negative_20_day_return_floor_blocks_entry_candidate(self) -> None:
        strategy = build_strategy()
        strategy = StrategyConfig(
            **{
                **strategy.__dict__,
                "entry": EntryConfig(
                    ma_crossover=MovingAverageConfig(short=20, long=50),
                    rsi_threshold=30,
                    max_volatility_20d=4.5,
                    min_recent_return_20d=-8.0,
                ),
            }
        )

        evaluation = evaluate_strategy(
            strategy,
            [
                IndicatorSnapshot(
                    symbol="JPM",
                    current_price=100,
                    ma_20=101,
                    ma_50=99,
                    rsi=25,
                    recent_return_20d=-12.0,
                    avg_dollar_volume_20d=20000000,
                )
            ],
            [],
        )

        self.assertEqual(evaluation.entry_decisions, [])
        self.assertIn("JPM", evaluation.classification.inactive)
        self.assertNotIn("JPM", evaluation.classification.watching)
        self.assertTrue(any("20-day return is -12.00%" in item.reason for item in evaluation.candidates))

    def test_close_setup_without_hard_failures_remains_watch_candidate(self) -> None:
        strategy = build_strategy()

        evaluation = evaluate_strategy(
            strategy,
            [
                IndicatorSnapshot(
                    symbol="JPM",
                    current_price=100,
                    ma_20=100.5,
                    ma_50=100,
                    rsi=34,
                    recent_return_20d=-4.0,
                    distance_to_ma_20_pct=-1.0,
                    distance_to_ma_50_pct=0.0,
                    avg_dollar_volume_20d=20000000,
                )
            ],
            [],
        )

        self.assertIn("JPM", evaluation.classification.watching)
        self.assertNotIn("JPM", evaluation.classification.inactive)

    def test_rebound_confirmation_profile_generates_buy_decision(self) -> None:
        strategy = build_strategy()
        strategy = StrategyConfig(
            **{
                **strategy.__dict__,
                "entry": EntryConfig(
                    ma_crossover=MovingAverageConfig(short=20, long=50),
                    min_rsi=40,
                    rsi_threshold=60,
                    max_volatility_20d=4.5,
                    min_recent_return_5d=0.0,
                    min_recent_return_20d=-3.0,
                    min_distance_to_ma_20_pct=0.0,
                    min_distance_to_ma_50_pct=0.0,
                ),
            }
        )

        evaluation = evaluate_strategy(
            strategy,
            [
                IndicatorSnapshot(
                    symbol="JPM",
                    current_price=100,
                    ma_20=99,
                    ma_50=98,
                    rsi=52,
                    recent_return_5d=1.2,
                    recent_return_20d=2.5,
                    distance_to_ma_20_pct=1.0,
                    distance_to_ma_50_pct=2.0,
                    avg_dollar_volume_20d=20000000,
                )
            ],
            [],
        )

        self.assertEqual(evaluation.classification.triggered, ["JPM"])
        self.assertEqual([item.action for item in evaluation.entry_decisions], ["buy"])

    def test_rebound_confirmation_blocks_oversold_name_below_rsi_floor(self) -> None:
        strategy = build_strategy()
        strategy = StrategyConfig(
            **{
                **strategy.__dict__,
                "entry": EntryConfig(
                    ma_crossover=MovingAverageConfig(short=20, long=50),
                    min_rsi=40,
                    rsi_threshold=60,
                    max_volatility_20d=4.5,
                    min_recent_return_5d=0.0,
                    min_recent_return_20d=-3.0,
                    min_distance_to_ma_20_pct=0.0,
                    min_distance_to_ma_50_pct=0.0,
                ),
            }
        )

        evaluation = evaluate_strategy(
            strategy,
            [
                IndicatorSnapshot(
                    symbol="JPM",
                    current_price=100,
                    ma_20=99,
                    ma_50=98,
                    rsi=28,
                    recent_return_5d=1.2,
                    recent_return_20d=2.5,
                    distance_to_ma_20_pct=1.0,
                    distance_to_ma_50_pct=2.0,
                    avg_dollar_volume_20d=20000000,
                )
            ],
            [],
        )

        self.assertEqual(evaluation.entry_decisions, [])
        self.assertIn("JPM", evaluation.classification.inactive)
        self.assertTrue(any("below the minimum required 40.00" in item.reason for item in evaluation.candidates))


if __name__ == "__main__":
    unittest.main()