from __future__ import annotations

from trading_bot.config_loader import load_strategy_config
from trading_bot.env_loader import load_runtime_env
from trading_bot.integrations.broker import AlpacaBrokerClient, BrokerError
from trading_bot.integrations.decision_model import ClaudeDecisionClient, DecisionModelError
from trading_bot.integrations.market_data import AlpacaMarketDataClient, MarketDataError
from trading_bot.integrations.prefilter import OllamaPrefilterClient, PrefilterError
from trading_bot.models import DailyScanSummary
from trading_bot.persistence.guardrail_state import GuardrailStateStore
from trading_bot.persistence.trade_log import TradeLogger
from trading_bot.runtime_paths import ensure_runtime_dirs, resolve_paths
from trading_bot.services.decision_context import (
    build_stub_account,
    build_stub_positions,
    filter_triggered_snapshots,
    summarize_decisions,
)
from trading_bot.services.guardrails import (
    evaluate_claude_call_limit,
    evaluate_execution_policy,
    evaluate_position_size,
    evaluate_trade_limits,
)
from trading_bot.services.safety import append_guardrail_note, summarize_guardrails
from trading_bot.services.trade_execution import build_order_results


def determine_runtime_status(
    *,
    safe_mode: bool,
    execute_paper_trades: bool,
    order_results: list,
) -> str:
    if safe_mode:
        return "production-candidate-safe-mode"
    if execute_paper_trades and order_results:
        return "production-candidate-paper-trades-executed"
    if execute_paper_trades:
        return "production-candidate-execution-enabled"
    return "production-candidate"


def run_daily_scan(
    strategy_path: str | None = None,
    env_file: str | None = None,
    include_market_data: bool = False,
    include_prefilter: bool = False,
    include_decisions: bool = False,
    include_broker_context: bool = False,
    execute_paper_trades: bool = False,
    write_logs: bool | None = None,

) -> DailyScanSummary:
    """Production-candidate entrypoint for the staged daily scan flow.

    This function provides the staged monorepo runtime contract for
    configuration loading, runtime path resolution, external integrations,
    and structured return values.
    """

    paths = ensure_runtime_dirs(
        resolve_paths(strategy_path=strategy_path, env_file=env_file)
    )
    loaded_env_file = load_runtime_env(paths.env_file)
    strategy = load_strategy_config(paths.strategy_config)
    logger = TradeLogger(paths.trade_log)
    guardrail_store = GuardrailStateStore(paths.guardrail_state)
    guardrail_state = guardrail_store.load()
    effective_write_logs = (
        strategy.execution_controls.write_logs_by_default
        if write_logs is None
        else write_logs
    )
    notes = [
        "Monorepo trading-bot production-candidate runtime.",
        "Production cutover has not occurred; this runtime remains staged.",
        f"Using strategy config: {paths.strategy_config}",
        f"Configured watchlist size: {len(strategy.watchlist)}",
        f"Configured monitoring model: {strategy.models.monitoring}",
    ]
    if strategy.execution_controls.safe_mode:
        notes.append(
            "Safe mode is enabled in the staged runtime; no trades will execute unless execution policy is explicitly changed."
        )
    else:
        notes.append(
            "Safe mode is disabled in config; execution remains subject to explicit invocation and guardrails."
        )

    if loaded_env_file is not None:
        notes.append(f"Loaded staged env file: {loaded_env_file}")
    else:
        notes.append("No staged env file loaded; relying on existing environment variables.")

    guardrails = []
    account = None
    positions = []
    indicator_snapshots = []
    prefilter_result = None
    decisions = []
    order_results = []

    if include_broker_context or execute_paper_trades:
        try:
            broker = AlpacaBrokerClient()
            account = broker.get_account_balance()
            positions = broker.get_open_positions()
            notes.append(
                f"Fetched broker context with {len(positions)} open positions."
            )
        except BrokerError as exc:
            notes.append(f"Broker context disabled: {exc}")
        except Exception as exc:
            notes.append(f"Broker adapter error: {exc}")
    else:
        notes.append("Broker adapter is implemented but not invoked by default.")

    if include_market_data or include_prefilter:
        try:
            client = AlpacaMarketDataClient()
            indicator_snapshots = client.get_all_indicators(strategy.watchlist)
            notes.append(
                f"Fetched indicator snapshots for {len(indicator_snapshots)} symbols."
            )
        except MarketDataError as exc:
            notes.append(f"Market data disabled: {exc}")
        except Exception as exc:
            notes.append(f"Market data adapter error: {exc}")
    else:
        notes.append("Market data adapter is implemented but not invoked by default.")

    if include_prefilter:
        if indicator_snapshots:
            try:
                prefilter = OllamaPrefilterClient(model=strategy.models.monitoring)
                prefilter_result = prefilter.classify(indicator_snapshots)
                notes.append(
                    f"Prefilter classified {len(prefilter_result.triggered)} triggered and {len(prefilter_result.watching)} watching symbols."
                )
            except PrefilterError as exc:
                notes.append(f"Prefilter disabled: {exc}")
            except Exception as exc:
                notes.append(f"Prefilter adapter error: {exc}")
        else:
            notes.append("Prefilter skipped because no indicator snapshots were available.")
    else:
        notes.append("Prefilter adapter is implemented but not invoked by default.")

    if include_decisions:
        if prefilter_result and prefilter_result.triggered:
            claude_guardrail = evaluate_claude_call_limit(strategy, guardrail_state)
            guardrails.append(claude_guardrail)
            append_guardrail_note(notes, claude_guardrail)

            if not claude_guardrail.allowed:
                notes.append("Decision model call skipped due to Claude call guardrail.")
            else:
                try:
                    decision_client = ClaudeDecisionClient()
                    decisions = decision_client.decide(
                        strategy=strategy,
                        triggered_symbols=prefilter_result.triggered,
                        summary=prefilter_result.summary,
                        stock_data=filter_triggered_snapshots(
                            indicator_snapshots, prefilter_result.triggered
                        ),
                        account=account or build_stub_account(),
                        positions=positions or build_stub_positions(),
                    )
                    guardrail_state = guardrail_store.increment_claude_calls(1)
                    notes.append(summarize_decisions(decisions))
                except DecisionModelError as exc:
                    notes.append(f"Decision model disabled: {exc}")
                except Exception as exc:
                    notes.append(f"Decision-model adapter error: {exc}")
        else:
            notes.append("Decision model skipped because no triggered symbols were available.")
    else:
        notes.append("Decision-model adapter is implemented but not invoked by default.")

    if execute_paper_trades:
        if decisions and account is not None:
            execution_guardrail = evaluate_execution_policy(strategy)
            trade_limit_guardrail, trade_limit_status = None, None
            position_size_guardrail = evaluate_position_size(strategy, account)
            guardrails.append(execution_guardrail)
            guardrails.append(position_size_guardrail)
            append_guardrail_note(notes, execution_guardrail)
            append_guardrail_note(notes, position_size_guardrail)

            filtered_decisions, trade_limit_status = evaluate_trade_limits(
                strategy,
                guardrail_state,
                positions,
                decisions,
            )
            guardrails.append(trade_limit_status)
            append_guardrail_note(notes, trade_limit_status)

            if execution_guardrail.allowed and position_size_guardrail.allowed:
                try:
                    broker = AlpacaBrokerClient()
                    order_results = build_order_results(
                        filtered_decisions,
                        filter_triggered_snapshots(
                            indicator_snapshots,
                            triggered_symbols=[
                                item.symbol for item in filtered_decisions if item.action == "buy"
                            ],
                        ),
                        account,
                        strategy.max_position_size_pct,
                        broker.place_paper_trade,
                    )
                    if order_results:
                        guardrail_state = guardrail_store.increment_trades(len(order_results))
                    notes.append(
                        f"Executed {len(order_results)} paper-trade orders from decision output."
                    )
                except BrokerError as exc:
                    notes.append(f"Paper-trade execution disabled: {exc}")
                except Exception as exc:
                    notes.append(f"Paper-trade execution error: {exc}")
            else:
                notes.append("Paper-trade execution blocked by guardrails.")
        else:
            notes.append("Paper-trade execution skipped because no executable buy decisions were available.")
    else:
        notes.append("Paper-trade execution is implemented but not invoked by default.")

    notes.append(summarize_guardrails(guardrails))
    runtime_status = determine_runtime_status(
        safe_mode=strategy.execution_controls.safe_mode,
        execute_paper_trades=execute_paper_trades,
        order_results=order_results,
    )

    summary = DailyScanSummary(
        status=runtime_status,
        strategy_file=str(paths.strategy_config),
        runtime_root=str(paths.runtime_root),
        trade_log=str(paths.trade_log),
        notes=notes,
        guardrail_state=guardrail_state,
        guardrails=guardrails,
        account=account,
        positions=positions,
        indicator_snapshots=indicator_snapshots,
        prefilter_result=prefilter_result,
        triggered=prefilter_result.triggered if prefilter_result else [],
        watching=prefilter_result.watching if prefilter_result else [],
        decisions=decisions,
        order_results=order_results,
    )

    if effective_write_logs:
        logger.log_message("=== Staged daily scan started ===")
        for note in notes:
            logger.log_message(note)
        logger.log_summary_json(summary)
        logger.log_message("=== Staged daily scan complete ===")

    return summary
