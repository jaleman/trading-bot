from __future__ import annotations

from dataclasses import replace

from trading_bot.models import DailyScanSummary, GuardrailStatus


def append_guardrail_note(notes: list[str], status: GuardrailStatus) -> None:
    if status.allowed:
        notes.append(f"Guardrail passed: {status.name}")
        return

    reason_text = "; ".join(status.reasons) if status.reasons else "blocked"
    notes.append(f"Guardrail blocked: {status.name} — {reason_text}")


def summarize_guardrails(statuses: list[GuardrailStatus]) -> str:
    blocked = [item.name for item in statuses if not item.allowed]
    if not blocked:
        return "All evaluated guardrails passed."
    return f"Blocked by guardrails: {', '.join(blocked)}"


def set_status(summary: DailyScanSummary, status: str) -> DailyScanSummary:
    return replace(summary, status=status)
