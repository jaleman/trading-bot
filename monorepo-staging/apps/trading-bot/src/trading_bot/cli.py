"""CLI for the monorepo-managed trading-bot runtime."""

from __future__ import annotations

import argparse
import json

from trading_bot.services.daily_scan import run_daily_scan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Staged trading-bot CLI")
    parser.add_argument(
        "--config",
        dest="strategy_path",
        help="Path to the staged strategy config file.",
    )
    parser.add_argument(
        "--env-file",
        dest="env_file",
        help="Path to the staged env file used for local rehearsal runs.",
    )
    parser.add_argument(
        "--include-market-data",
        action="store_true",
        help="Fetch indicator snapshots during the staged run.",
    )
    parser.add_argument(
        "--include-prefilter",
        action="store_true",
        help="Run the prefilter layer during the staged run.",
    )
    parser.add_argument(
        "--include-decisions",
        action="store_true",
        help="Run the decision-model layer during the staged run.",
    )
    parser.add_argument(
        "--include-broker-context",
        action="store_true",
        help="Fetch broker account and position context during the staged run.",
    )
    parser.add_argument(
        "--execute-paper-trades",
        action="store_true",
        help="Attempt staged paper-trade execution. Guardrails still apply.",
    )
    parser.add_argument(
        "--rehearsal",
        action="store_true",
        help="Enable the staged supervised rehearsal path without forcing paper-trade execution.",
    )
    parser.add_argument(
        "--write-logs",
        dest="write_logs",
        action="store_true",
        help="Force runtime log writes for this invocation.",
    )
    parser.add_argument(
        "--no-write-logs",
        dest="write_logs",
        action="store_false",
        help="Disable runtime log writes for this invocation.",
    )
    parser.set_defaults(write_logs=None)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    include_market_data = args.include_market_data
    include_prefilter = args.include_prefilter
    include_decisions = args.include_decisions
    include_broker_context = args.include_broker_context

    if args.rehearsal:
        include_market_data = True
        include_prefilter = True
        include_decisions = True
        include_broker_context = True

    summary = run_daily_scan(
        strategy_path=args.strategy_path,
        env_file=args.env_file,
        include_market_data=include_market_data,
        include_prefilter=include_prefilter,
        include_decisions=include_decisions,
        include_broker_context=include_broker_context,
        execute_paper_trades=args.execute_paper_trades,
        write_logs=args.write_logs,
    )
    print(json.dumps(summary.to_dict(), indent=2))


if __name__ == "__main__":
    main()
