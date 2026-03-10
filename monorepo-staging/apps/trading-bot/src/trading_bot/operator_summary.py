from __future__ import annotations

import argparse
import json
from pathlib import Path

from trading_bot.runtime_paths import resolve_paths


def _top_blocked_candidates(summary: dict) -> list[dict]:
	strategy_evaluation = summary.get("strategy_evaluation") or {}
	candidates = strategy_evaluation.get("candidates") or []
	watch_candidates = [item for item in candidates if item.get("action") == "watch"]
	watch_candidates.sort(key=lambda item: (-float(item.get("score", 0.0)), item.get("symbol", "")))
	return watch_candidates[:3]


def _compact_reason(reason: str) -> str:
	prefix = "Entry not confirmed: "
	if reason.startswith(prefix):
		reason = reason[len(prefix):]
	return reason.strip()


def load_latest_summary_payload(jsonl_path: str | Path | None = None) -> dict:
	path = Path(jsonl_path).expanduser().resolve() if jsonl_path else resolve_paths().trade_log.with_suffix(".jsonl")
	if not path.is_file():
		raise FileNotFoundError(f"No summary log found at {path}")

	last_line = ""
	with path.open("r", encoding="utf-8") as handle:
		for line in handle:
			if line.strip():
				last_line = line

	if not last_line:
		raise ValueError(f"Summary log is empty at {path}")

	return json.loads(last_line)


def format_operator_summary(payload: dict) -> str:
	summary = payload.get("summary", payload)
	notes = summary.get("notes", [])
	triggered = summary.get("triggered", [])
	watching = summary.get("watching", [])
	decisions = summary.get("decisions", [])
	local_analysis = summary.get("local_analysis") or {}
	orders = summary.get("order_results", [])
	guardrails = summary.get("guardrails", [])
	guardrail_state = summary.get("guardrail_state") or {}
	indicator_snapshots = summary.get("indicator_snapshots", [])
	blocked_candidates = _top_blocked_candidates(summary)

	buys = sum(1 for item in decisions if item.get("action") == "buy")
	sells = sum(1 for item in decisions if item.get("action") == "sell")
	skips = sum(1 for item in decisions if item.get("action") == "skip")
	blocked_guardrails = [item.get("name", "unknown") for item in guardrails if not item.get("allowed", False)]
	status = summary.get("status", "")
	normalized_notes = [note.lower() for note in notes]
	safe_mode_active = "safe-mode" in status or any(
		"safe mode is enabled" in note or "live actions remain disabled" in note
		for note in normalized_notes
	)
	claude_reviewed = any("claude escalation reviewed candidates" in note for note in normalized_notes)

	triggered_text = ", ".join(triggered) if triggered else "none"
	watching_text = ", ".join(watching) if watching else "none"
	trade_count = len(orders)
	scanned_count = len(indicator_snapshots)
	local_summary = local_analysis.get("summary", "")
	ranked_candidates = local_analysis.get("ranked_candidates", [])
	top_candidate = ranked_candidates[0] if ranked_candidates else None

	line_1 = "Trading scan completed."
	if safe_mode_active and trade_count == 0:
		line_1 = "Trading scan completed. Safe mode remained active; no trades executed."
	elif trade_count > 0:
		line_1 = f"Trading scan completed. Executed {trade_count} paper-trade order(s)."

	line_2 = f"Scanned {scanned_count} symbol(s). Triggered: {triggered_text}. Watching: {watching_text}."
	line_3 = f"Decisions: {buys} buy, {sells} sell, {skips} skip."
	analysis_parts = []
	if local_summary:
		analysis_parts.append(f"Local analysis: {local_summary}")
	if top_candidate:
		symbol = top_candidate.get("symbol", "unknown")
		action = top_candidate.get("action", "unknown")
		confidence = float(top_candidate.get("confidence", 0.0))
		analysis_parts.append(f"Top ranked: {symbol} ({action}, confidence {confidence:.2f}).")
	if claude_reviewed:
		analysis_parts.append("Claude escalation reviewed the shortlist.")
	if not decisions and blocked_candidates:
		blocked_parts = []
		for item in blocked_candidates:
			blocked_parts.append(
				f"{item.get('symbol', 'unknown')}: {_compact_reason(item.get('reason', 'No reason provided.'))}"
			)
		analysis_parts.append("Blocked setups: " + " | ".join(blocked_parts))

	line_4 = " ".join(analysis_parts) if analysis_parts else ""
	if blocked_guardrails:
		line_5 = f"Guardrails blocked: {', '.join(blocked_guardrails)}."
	else:
		line_5 = (
			"Guardrails passed. "
			f"Claude calls today: {guardrail_state.get('claude_calls_today', 0)}. "
			f"Trades today: {guardrail_state.get('trades_today', 0)}."
		)

	lines = [line_1, line_2, line_3]
	if line_4:
		lines.append(line_4)
	lines.append(line_5)
	return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="Print the latest staged trading-bot operator summary")
	parser.add_argument(
		"--jsonl",
		dest="jsonl_path",
		help="Optional path to the staged JSONL summary log.",
	)
	return parser


def main(argv: list[str] | None = None) -> None:
	parser = build_parser()
	args = parser.parse_args(argv)
	payload = load_latest_summary_payload(args.jsonl_path)
	print(format_operator_summary(payload))


if __name__ == "__main__":
	main()