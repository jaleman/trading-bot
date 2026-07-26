from __future__ import annotations

from trading_bot.config_loader import load_strategy_config
from trading_bot.env_loader import load_runtime_env
from trading_bot.integrations.broker import AlpacaBrokerClient, BrokerError
from trading_bot.integrations.decision_model import ClaudeDecisionClient, DecisionModelError
from trading_bot.integrations.local_analysis import (
    LocalAnalysisError,
    OllamaLocalAnalysisClient,
)
from trading_bot.integrations.market_data import AlpacaMarketDataClient, MarketDataError
from trading_bot.models import DailyScanSummary
from trading_bot.persistence.guardrail_state import GuardrailStateStore
from trading_bot.persistence.trade_log import TradeLogger
from trading_bot.runtime_paths import ensure_runtime_dirs, resolve_paths
from trading_bot.services.decision_context import summarize_decisions
from trading_bot.services.guardrails import (
    evaluate_claude_call_limit,
    evaluate_execution_policy,
    evaluate_position_size,
    evaluate_trade_limits,
    validate_execution_intents,
)
from trading_bot.services.model_router import should_escalate_to_claude
from trading_bot.services.safety import append_guardrail_note, summarize_guardrails
from trading_bot.services.strategy_engine import evaluate_strategy
from trading_bot.services.trade_execution import build_order_results
from trading_bot.services.universe import UniverseError, resolve_scan_universe


def _build_local_analysis_candidates(strategy, strategy_evaluation):
    candidates = [
        item
        for item in strategy_evaluation.candidates
        if item.action in {"buy", "sell", "watch", "hold"}
    ]
    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates[: strategy.model_routing.max_candidates_for_local_analysis]


def _filter_candidate_snapshots(indicator_snapshots, candidates):
    candidate_symbols = {item.symbol for item in candidates}
    return [item for item in indicator_snapshots if item.symbol in candidate_symbols]


def _has_actionable_candidates(strategy_evaluation) -> bool:
    return bool(
        strategy_evaluation.entry_decisions
        or strategy_evaluation.exit_decisions
    )


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
    scan_symbols = []
    effective_write_logs = (
        strategy.execution_controls.write_logs_by_default
        if write_logs is None
        else write_logs
    )

    # Written before any work happens, so an interrupted scan still leaves
    # evidence that it started and when. Previously every line — including the
    # start marker — was written only after a successful completion, so a crash
    # produced no record at all.
    notes: list[str] = []
    if effective_write_logs:
        logger.log_message("=== Staged daily scan started ===")

    try:
        return _run_daily_scan_body(
            logger=logger,
            notes=notes,
            paths=paths,
            strategy=strategy,
            guardrail_store=guardrail_store,
            guardrail_state=guardrail_state,
            loaded_env_file=loaded_env_file,
            effective_write_logs=effective_write_logs,
            include_broker_context=include_broker_context,
            include_market_data=include_market_data,
            include_prefilter=include_prefilter,
            include_decisions=include_decisions,
            execute_paper_trades=execute_paper_trades,
        )
    except BaseException as exc:
        if effective_write_logs:
            # Flush whatever progress was made before the failure, then the
            # traceback, so the log explains how far the scan got and why it died.
            logger.log_messages(notes)
            logger.log_exception(exc, context="Daily scan aborted")
            logger.log_message("=== Staged daily scan FAILED ===")
        raise


def _run_daily_scan_body(
    *,
    logger,
    notes: list[str],
    paths,
    strategy,
    guardrail_store,
    guardrail_state,
    loaded_env_file,
    effective_write_logs: bool,
    include_broker_context: bool,
    include_market_data: bool,
    include_prefilter: bool,
    include_decisions: bool,
    execute_paper_trades: bool,
) -> DailyScanSummary:
    """Body of the daily scan, separated so failures can be logged around it."""
    scan_symbols = []

    try:
        scan_symbols = resolve_scan_universe(strategy)
    except UniverseError as exc:
        scan_symbols = list(strategy.watchlist)
        notes[:] = [
            "Monorepo trading-bot runtime.",
            f"Using strategy config: {paths.strategy_config}",
            f"Universe resolution failed: {exc}",
            f"Falling back to compatibility watchlist size: {len(scan_symbols)}",
            f"Configured local analysis model: {strategy.models.monitoring}",
        ]
    else:
        notes[:] = [
            "Monorepo trading-bot runtime.",
            f"Using strategy config: {paths.strategy_config}",
            f"Configured universe size: {len(scan_symbols)}",
            f"Configured local analysis model: {strategy.models.monitoring}",
        ]
    if strategy.execution_controls.safe_mode:
        notes.append(
            "Safe mode is enabled; no trades will execute unless execution policy is explicitly changed."
        )
    else:
        notes.append(
            "Safe mode is disabled in config; paper-trade execution remains subject to explicit invocation and guardrails."
        )

    if loaded_env_file is not None:
        notes.append(f"Loaded runtime env file: {loaded_env_file}")
    else:
        notes.append("No runtime env file loaded; relying on existing environment variables.")

    guardrails = []
    account = None
    positions = []
    indicator_snapshots = []
    prefilter_result = None
    strategy_evaluation = None
    local_analysis = None
    decisions = []
    order_results = []
    open_orders = []

    # Preload the local model before the network fetches below. A daily scan
    # always starts with the model cold, and its load time would otherwise be
    # charged against the analysis request's own timeout.
    if include_prefilter and strategy.model_routing.local_analysis_enabled:
        warm_client = OllamaLocalAnalysisClient(model=strategy.models.local_analysis)
        if warm_client.warm():
            notes.append(f"Preloaded local analysis model: {strategy.models.local_analysis}")
        else:
            notes.append(
                "Local analysis model preload failed; the analysis call will absorb model load time."
            )

    if include_broker_context or execute_paper_trades:
        try:
            broker = AlpacaBrokerClient()
            account = broker.get_account_balance()
            fetched_positions = broker.get_open_positions()
            # Committed together, deliberately. The execution firewall fails
            # open without the working orders, so a partial fetch that yielded
            # positions but no orders would silently re-enable the duplicate
            # submissions this exists to prevent.
            fetched_open_orders = broker.get_open_orders()
            positions = fetched_positions
            open_orders = fetched_open_orders
            notes.append(
                f"Fetched broker context with {len(positions)} open positions "
                f"and {len(open_orders)} working order(s)."
            )
        except BrokerError as exc:
            notes.append(f"Broker context disabled: {exc}")
        except Exception as exc:
            notes.append(f"Broker adapter error: {exc}")
    else:
        notes.append("Broker adapter is implemented but not invoked by default.")

    if include_market_data or include_prefilter or include_decisions or execute_paper_trades:
        try:
            client = AlpacaMarketDataClient()
            indicator_snapshots = client.get_all_indicators(scan_symbols)
            notes.append(
                f"Fetched indicator snapshots for {len(indicator_snapshots)} symbols."
            )
            # A partial fetch still scans, but must not look like a quiet market.
            failed_symbols = getattr(client, "last_failed_symbols", None)
            if isinstance(failed_symbols, list) and failed_symbols:
                notes.append(
                    f"Market data degraded: {len(failed_symbols)} of {len(scan_symbols)} "
                    f"symbol(s) failed and were excluded from this scan "
                    f"({', '.join(failed_symbols[:10])}"
                    f"{', ...' if len(failed_symbols) > 10 else ''})."
                )
        except MarketDataError as exc:
            notes.append(f"Market data disabled: {exc}")
        except Exception as exc:
            notes.append(f"Market data adapter error: {exc}")
    else:
        notes.append("Market data adapter is implemented but not invoked by default.")

    if indicator_snapshots:
        strategy_evaluation = evaluate_strategy(strategy, indicator_snapshots, positions)
        prefilter_result = strategy_evaluation.classification
        notes.append(
            "Deterministic strategy engine evaluated "
            f"{len(strategy_evaluation.classification.triggered)} entry and "
            f"{len(strategy_evaluation.exit_decisions)} exit candidates."
        )
    else:
        notes.append("Deterministic strategy engine skipped because no indicator snapshots were available.")

    if include_prefilter:
        if strategy_evaluation is not None:
            notes.append(
                f"Deterministic classification returned {len(prefilter_result.triggered)} triggered and {len(prefilter_result.watching)} watching symbols."
            )
            if strategy.model_routing.local_analysis_enabled:
                if not _has_actionable_candidates(strategy_evaluation):
                    notes.append(
                        "Local analysis skipped because there were no actionable deterministic candidates."
                    )
                else:
                    shortlist = _build_local_analysis_candidates(strategy, strategy_evaluation)
                    if shortlist:
                        try:
                            analysis_client = OllamaLocalAnalysisClient(model=strategy.models.local_analysis)
                            local_analysis = analysis_client.analyze(
                                strategy=strategy,
                                candidates=shortlist,
                                snapshots=_filter_candidate_snapshots(indicator_snapshots, shortlist),
                                account=account,
                                positions=positions,
                            )
                            notes.append(
                                f"Local analysis ranked {len(local_analysis.ranked_candidates)} candidate(s)."
                            )
                            if local_analysis.summary:
                                notes.append(f"Local analysis summary: {local_analysis.summary}")
                            if local_analysis.escalate_to_claude:
                                notes.append(
                                    "Local analysis recommends Claude escalation"
                                    f": {local_analysis.escalation_reason or 'no reason provided.'}"
                                )
                        except LocalAnalysisError as exc:
                            notes.append(f"Local analysis disabled: {exc}")
                        except Exception as exc:
                            notes.append(f"Local analysis adapter error: {exc}")
                    else:
                        notes.append("Local analysis skipped because no shortlist candidates were available.")
            else:
                notes.append("Local analysis is disabled by strategy config.")
        else:
            notes.append("Signal classification skipped because no deterministic evaluation was available.")
    else:
        notes.append("Local analysis is available but not requested for this run.")

    if include_decisions:
        if strategy_evaluation is not None:
            decisions = [
                *strategy_evaluation.entry_decisions,
                *strategy_evaluation.exit_decisions,
            ]
            notes.append(summarize_decisions(decisions))
            should_escalate, escalation_reason = should_escalate_to_claude(
                strategy,
                local_analysis,
                positions,
                decisions,
            )
            if should_escalate:
                claude_guardrail = evaluate_claude_call_limit(strategy, guardrail_state)
                guardrails.append(claude_guardrail)
                append_guardrail_note(notes, claude_guardrail)

                if not claude_guardrail.allowed:
                    notes.append("Claude escalation skipped due to Claude call guardrail.")
                else:
                    shortlist = _build_local_analysis_candidates(strategy, strategy_evaluation)
                    try:
                        decision_client = ClaudeDecisionClient()
                        reviewed_decisions = decision_client.review(
                            strategy=strategy,
                            candidates=shortlist,
                            local_analysis=local_analysis,
                            account=account,
                            positions=positions,
                        )
                        if reviewed_decisions:
                            decisions = reviewed_decisions
                            notes.append(f"Claude escalation reviewed candidates: {escalation_reason}")
                            notes.append(summarize_decisions(decisions))
                        guardrail_state = guardrail_store.increment_claude_calls(1)
                    except DecisionModelError as exc:
                        notes.append(f"Claude escalation disabled: {exc}")
                    except Exception as exc:
                        notes.append(f"Claude escalation adapter error: {exc}")
            else:
                notes.append(f"Claude escalation skipped: {escalation_reason}")
        else:
            notes.append("Decision generation skipped because no deterministic evaluation was available.")
    else:
        notes.append("Deterministic decision generation is available but not requested for this run.")

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

            filtered_decisions, execution_intent_status = validate_execution_intents(
                strategy,
                filtered_decisions,
                positions,
                account,
                open_orders,
            )
            guardrails.append(execution_intent_status)
            append_guardrail_note(notes, execution_intent_status)

            if execution_guardrail.allowed and position_size_guardrail.allowed:
                try:
                    broker = AlpacaBrokerClient()
                    order_results = build_order_results(
                        filtered_decisions,
                        indicator_snapshots,
                        positions,
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
        strategy_evaluation=strategy_evaluation,
        local_analysis=local_analysis,
        triggered=prefilter_result.triggered if prefilter_result else [],
        watching=prefilter_result.watching if prefilter_result else [],
        decisions=decisions,
        order_results=order_results,
    )

    if effective_write_logs:
        # The start marker was already written before any work began.
        logger.log_messages(notes)
        logger.log_summary_json(summary)
        logger.log_message("=== Staged daily scan complete ===")

    return summary
