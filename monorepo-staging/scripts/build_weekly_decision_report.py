"""Weekly decision-rationale report for the trading-bot paper-trading system.

Reads trades.jsonl for a date range and renders one section per trading day
explaining what was scanned, what was bought/sold/held and why, what a
guardrail blocked (if anything), and what actually executed. Written for a
non-technical reader -- e.g. handing to a financial advisor for review.

`trades.jsonl` already carries this detail on every run (decision reasons,
local-model commentary, guardrail outcomes); this script only formats it.
Nothing here is inferred or summarised by a language model -- every sentence
in the output is copied from a field the scan itself wrote.

reportlab is deliberately NOT in the app's virtualenv, same reasoning as
build_executive_summary.py: the trading runtime has no business carrying a
PDF library. Use a throwaway environment:

    python3 -m venv /tmp/pdfenv && /tmp/pdfenv/bin/pip install reportlab
    /tmp/pdfenv/bin/python monorepo-staging/scripts/build_weekly_decision_report.py

Options:
    --days N            Trailing N calendar days ending today (default 7).
    --start YYYY-MM-DD   Explicit start date (overrides --days).
    --end YYYY-MM-DD     Explicit end date (default: today).
    --out PATH           Output PDF path (default: TradingBot-WeeklyDecisions-<end>.pdf).
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
TRADES_JSONL = REPO_ROOT / "runtime" / "trading-bot" / "logs" / "trades.jsonl"

INK = colors.HexColor("#1a1a1a")
MUTED = colors.HexColor("#5f6b7a")
RULE = colors.HexColor("#d5dbe2")
ACCENT = colors.HexColor("#1f4e79")
BAND = colors.HexColor("#f2f5f8")
POS = colors.HexColor("#1a6b3c")
NEG = colors.HexColor("#a32020")

styles = getSampleStyleSheet()


def style(name, **kw):
    kw.setdefault("parent", styles["Normal"])
    return ParagraphStyle(name, **kw)


BODY = style("body", fontName="Helvetica", fontSize=9.5, leading=13.5,
             textColor=INK, alignment=TA_JUSTIFY, spaceAfter=6)
H1 = style("h1", fontName="Helvetica-Bold", fontSize=13, leading=16,
           textColor=ACCENT, spaceBefore=14, spaceAfter=6)
H2 = style("h2", fontName="Helvetica-Bold", fontSize=10, leading=13,
           textColor=INK, spaceBefore=8, spaceAfter=3)
SMALL = style("small", fontName="Helvetica", fontSize=8.2, leading=11.5,
              textColor=MUTED, spaceAfter=5)
CELL = style("cell", fontName="Helvetica", fontSize=8.6, leading=12,
             textColor=INK)
CELLB = style("cellb", fontName="Helvetica-Bold", fontSize=8.6, leading=12,
              textColor=INK)
BULLET = style("bullet", parent=BODY, leftIndent=13, bulletIndent=3,
               spaceAfter=4, alignment=0)


def p(text, s=BODY):
    return Paragraph(text, s)


def bullets(items, s=BULLET):
    return [Paragraph(f"&bull;&nbsp;&nbsp;{i}", s) for i in items]


def table(rows, widths, align_right=(), header=True):
    t = Table(rows, colWidths=widths, hAlign="LEFT", repeatRows=1 if header else 0)
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, RULE if not header else ACCENT),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BAND]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 1), (-1, -2), 0.3, RULE),
    ]
    for c in align_right:
        cmds.append(("ALIGN", (c, 0), (c, -1), "RIGHT"))
    t.setStyle(TableStyle(cmds))
    return t


def header_footer(canvas, doc):
    canvas.saveState()
    w, h = LETTER
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(0.9 * inch, h - 0.62 * inch,
                       "TRADING-BOT  ·  WEEKLY DECISION REPORT")
    canvas.drawRightString(w - 0.9 * inch, h - 0.62 * inch,
                           "Paper trading · not live capital")
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.6)
    canvas.line(0.9 * inch, h - 0.72 * inch, w - 0.9 * inch, h - 0.72 * inch)
    canvas.line(0.9 * inch, 0.72 * inch, w - 0.9 * inch, 0.72 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawRightString(w - 0.9 * inch, 0.56 * inch, "Page %d" % doc.page)
    canvas.restoreState()


def load_runs(jsonl_path: Path, start: date, end: date) -> list[dict]:
    if not jsonl_path.exists():
        raise SystemExit(f"Trade log not found: {jsonl_path}")

    runs = []
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        try:
            run_date = datetime.fromisoformat(entry.get("timestamp", "")).date()
        except ValueError:
            continue
        if start <= run_date <= end:
            runs.append(entry)

    runs.sort(key=lambda e: e["timestamp"])
    return runs


def fmt_money(value) -> str:
    if value is None:
        return "n/a"
    return f"${value:,.2f}"


def fmt_pct(value) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.2f}%"


def action_color(action: str) -> colors.Color:
    return {"buy": POS, "sell": NEG}.get(action, INK)


def hexcolor(c: colors.Color) -> str:
    return "#" + c.hexval()[2:]


def build_day_story(entry: dict) -> list:
    ts = entry.get("timestamp", "")
    run_date = datetime.fromisoformat(ts).date()
    summary = entry.get("summary", {})

    story: list = []
    story.append(p(run_date.strftime("%A, %-d %B %Y"), H1))

    account = summary.get("account") or {}
    positions = summary.get("positions") or []
    story.append(p(
        f"Portfolio value {fmt_money(account.get('portfolio_value'))} &middot; "
        f"cash {fmt_money(account.get('cash'))} &middot; "
        f"{len(positions)} open position(s)",
        SMALL,
    ))

    classification = (summary.get("strategy_evaluation") or {}).get("classification") or {}
    triggered = classification.get("triggered") or []
    watching = classification.get("watching") or []
    inactive = classification.get("inactive") or []

    story.append(p("Market scan", H2))
    class_summary = classification.get("summary")
    if class_summary:
        story.append(p(class_summary, BODY))
    story.append(p(
        f"{len(triggered)} triggered, {len(watching)} on watch, "
        f"{len(inactive)} screened with no qualifying signal.",
        SMALL,
    ))

    local_analysis = summary.get("local_analysis") or {}
    la_summary = local_analysis.get("summary")
    if la_summary:
        story.append(p("Analyst commentary", H2))
        story.append(p(la_summary, BODY))
        if local_analysis.get("escalate_to_claude"):
            reason = local_analysis.get("escalation_reason") or "Ambiguous candidate set."
            story.append(p(f"<i>Escalated for a second opinion: {reason}</i>", SMALL))
            escalation_note = next(
                (n for n in (summary.get("notes") or [])
                 if n.startswith("Claude escalation reviewed candidates")),
                None,
            )
            if escalation_note:
                story.append(p(f"<i>{escalation_note}</i>", SMALL))

    decisions = summary.get("decisions") or []
    story.append(p("Decisions and rationale", H2))
    if decisions:
        rows = [[p("<b>Symbol</b>", CELLB), p("<b>Decision</b>", CELLB), p("<b>Why</b>", CELLB)]]
        for d in decisions:
            action = (d.get("action") or "").upper()
            rows.append([
                p(d.get("symbol", ""), CELL),
                p(f'<font color="{hexcolor(action_color(d.get("action", "")))}">'
                  f'<b>{action}</b></font>', CELL),
                p(d.get("reason") or "", CELL),
            ])
        story.append(table(rows, [0.7 * inch, 0.7 * inch, 4.9 * inch]))
    else:
        story.append(p("No entry, exit, or hold decisions were generated today.", BODY))

    guardrails = summary.get("guardrails") or []
    blocked = [g for g in guardrails if not g.get("allowed")]
    story.append(p("Guardrail checks", H2))
    if blocked:
        for g in blocked:
            reasons = "; ".join(g.get("reasons") or []) or "no reason recorded"
            story.append(p(f"<b>{g.get('name')}</b> blocked an action: {reasons}", BODY))
    elif guardrails:
        story.append(p("All guardrails passed; nothing was blocked today.", SMALL))
    else:
        story.append(p("No guardrail evaluation ran today (no executable decisions).", SMALL))

    order_results = summary.get("order_results") or []
    story.append(p("Orders executed", H2))
    if order_results:
        rows = [[p("<b>Symbol</b>", CELLB), p("<b>Side</b>", CELLB),
                 p("<b>Qty</b>", CELLB), p("<b>Status</b>", CELLB)]]
        for o in order_results:
            side = o.get("side", "").split(".")[-1]
            rows.append([
                p(o.get("symbol", ""), CELL),
                p(f'<font color="{hexcolor(action_color(side.lower()))}">'
                  f'<b>{side}</b></font>', CELL),
                p(str(o.get("qty", "")), CELL),
                p(o.get("status", "").split(".")[-1], CELL),
            ])
        story.append(table(rows, [1.0 * inch, 1.0 * inch, 1.0 * inch, 3.3 * inch]))
    else:
        story.append(p("No orders were submitted today.", SMALL))

    if positions:
        story.append(p("Positions held at scan time", H2))
        rows = [[p("<b>Symbol</b>", CELLB), p("<b>Qty</b>", CELLB), p("<b>Entry</b>", CELLB),
                 p("<b>Current</b>", CELLB), p("<b>Unrealised P/L</b>", CELLB)]]
        for pos in positions:
            plpc = pos.get("unrealized_plpc")
            plpc_color = POS if (plpc or 0) >= 0 else NEG
            rows.append([
                p(pos.get("symbol", ""), CELL),
                p(str(pos.get("qty", "")), CELL),
                p(fmt_money(pos.get("avg_entry_price")), CELL),
                p(fmt_money(pos.get("current_price")), CELL),
                p(f'<font color="{hexcolor(plpc_color)}">'
                  f'{fmt_pct((plpc or 0) * 100)}</font>', CELL),
            ])
        story.append(table(rows, [0.9 * inch, 0.7 * inch, 1.1 * inch, 1.1 * inch, 1.5 * inch]))

    story.append(Spacer(1, 10))
    return story


def build_week_summary(runs: list[dict], start: date, end: date) -> list:
    story = []
    story.append(Spacer(1, 6))
    story.append(p("Automated Equity Trading System", ParagraphStyle(
        "t", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=19,
        leading=23, textColor=ACCENT, spaceAfter=2)))
    story.append(p(
        f"Weekly Decision Report &mdash; {start.strftime('%-d %b %Y')} to {end.strftime('%-d %b %Y')}",
        ParagraphStyle("st", parent=styles["Normal"], fontName="Helvetica",
                       fontSize=11, leading=14, textColor=MUTED, spaceAfter=10)))
    story.append(p(
        "This document summarises a personal research project. It is not an investment "
        "product, not a solicitation, and not investment advice. Every statement below is "
        "copied directly from the system's own daily audit log &mdash; nothing is inferred "
        "or added after the fact.", SMALL))

    if not runs:
        story.append(p(
            "No scans were recorded in this date range. Either the market was closed for "
            "the entire window or the scheduled job did not run &mdash; check the watchdog "
            "before trusting an empty week.", BODY))
        return story

    first_acc = (runs[0].get("summary") or {}).get("account") or {}
    last_acc = (runs[-1].get("summary") or {}).get("account") or {}
    start_val = first_acc.get("portfolio_value")
    end_val = last_acc.get("portfolio_value")
    return_pct = ((end_val - start_val) / start_val * 100) if start_val else None

    buys = sells = 0
    blocked_days = 0
    for entry in runs:
        s = entry.get("summary") or {}
        for o in (s.get("order_results") or []):
            side = o.get("side", "").upper()
            if side.endswith("BUY"):
                buys += 1
            elif side.endswith("SELL"):
                sells += 1
        if any(not g.get("allowed") for g in (s.get("guardrails") or [])):
            blocked_days += 1

    story.append(table([
        [p("<b>Metric</b>", CELLB), p("<b>Value</b>", CELLB)],
        [p("Trading days covered", CELL), p(str(len(runs)), CELL)],
        [p("Portfolio value, start of window", CELL), p(fmt_money(start_val), CELL)],
        [p("Portfolio value, end of window", CELL), p(fmt_money(end_val), CELL)],
        [p("Return over the window", CELL),
         p(f'<font color="{hexcolor(POS if (return_pct or 0) >= 0 else NEG)}">'
           f'<b>{fmt_pct(return_pct)}</b></font>', CELL)],
        [p("Buy orders executed", CELL), p(str(buys), CELL)],
        [p("Sell orders executed", CELL), p(str(sells), CELL)],
        [p("Days with a guardrail block", CELL), p(str(blocked_days), CELL)],
    ], [3.0 * inch, 3.3 * inch]))
    story.append(Spacer(1, 8))
    story.append(p(
        "The day-by-day sections below give the full rationale for every decision: what "
        "the deterministic strategy engine and, where consulted, the language-model layer, "
        "concluded, and what the independent guardrail layer allowed or blocked before "
        "anything reached the broker.", BODY))
    return story


def last_full_week(today: date) -> tuple[date, date]:
    """The most recently completed Monday-Friday week, as of `today`.

    Works regardless of which day it's called on: on a Saturday the answer is
    the week that just ended; called mid-week, it's the prior week, not the
    partial one in progress -- there's no such thing as a "full week" that
    includes today.
    """
    days_since_friday = (today.weekday() - 4) % 7
    if days_since_friday == 0:
        days_since_friday = 7
    last_friday = today - timedelta(days=days_since_friday)
    return last_friday - timedelta(days=4), last_friday


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--start", type=str, default=None)
    parser.add_argument("--end", type=str, default=None)
    parser.add_argument("--last-full-week", action="store_true",
                         help="Most recent complete Monday-Friday week, overriding --days/--start/--end.")
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()

    if args.last_full_week:
        start, end = last_full_week(date.today())
    else:
        end = date.fromisoformat(args.end) if args.end else date.today()
        start = date.fromisoformat(args.start) if args.start else end - timedelta(days=args.days - 1)

    runs = load_runs(TRADES_JSONL, start, end)
    out_path = Path(args.out) if args.out else Path(
        f"TradingBot-WeeklyDecisions-{start.isoformat()}-to-{end.isoformat()}.pdf"
    )

    story = build_week_summary(runs, start, end)
    for entry in runs:
        story.extend(build_day_story(entry))

    doc = BaseDocTemplate(str(out_path), pagesize=LETTER,
                           leftMargin=0.9 * inch, rightMargin=0.9 * inch,
                           topMargin=0.95 * inch, bottomMargin=0.9 * inch,
                           title="Trading Bot - Weekly Decision Report",
                           author="", subject="Weekly buy/sell/hold rationale")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=header_footer)])
    doc.build(story)
    print("wrote", out_path)


if __name__ == "__main__":
    main()
