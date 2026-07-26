"""Executive summary PDF for the trading-bot paper-trading system.

Generates a shareable, high-level summary for a non-operator audience. First
produced 2026-07-26 for an external review.

    python3 -m venv /tmp/pdfenv && /tmp/pdfenv/bin/pip install reportlab
    /tmp/pdfenv/bin/python monorepo-staging/scripts/build_executive_summary.py

reportlab is deliberately NOT added to the app's virtualenv -- the trading
runtime has no business carrying a PDF library. Use a throwaway environment.

-----------------------------------------------------------------------------
BEFORE REGENERATING: refresh the LIVE block below.
-----------------------------------------------------------------------------
Everything in LIVE goes stale. Everything in HISTORICAL is a permanent record
of what happened in a closed window and must NOT be updated -- the April
return and the dormancy figures stay true no matter what the account does
next.

A document that renders cleanly with stale numbers is exactly the failure this
project keeps finding in itself: something that looks fine while being wrong.
Run these first and reconcile every LIVE value:

    ./monorepo-staging/scripts/print_trading_bot_balance.sh       # portfolio value
    ./monorepo-staging/scripts/print_trading_bot_holdings.sh      # open positions
    ./monorepo-staging/scripts/run_trading_bot_reconciliation.sh  # realised P/L,
                                                                 # round trips,
                                                                 # consecutive losses

Also re-read section 6: the round-trip table lists completed trades
individually and grows as more close. And section 7 restates the return
against the gate -- update it once the 90-day window actually produces one.
"""

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# --------------------------------------------------------------------------
# LIVE — refresh every regeneration. See the module docstring for the commands.
# --------------------------------------------------------------------------
AS_AT_ISO = "2026-07-26"   # filename; sorts chronologically
AS_AT = "26 July 2026"     # prose
AS_AT_SHORT = "26 Jul 2026"  # table cells

LIVE = {
    # print_trading_bot_balance.sh
    "portfolio_value": "$97,444.87",
    # print_trading_bot_holdings.sh
    "open_positions": "4",
    "open_positions_note": "2 exiting on the stop-loss rule",
    # run_trading_bot_reconciliation.sh
    "realised_pl": "+$1,373.54",
    "round_trips_note": "2 completed round trips",
    "max_consecutive_losses": "1",
}

# --------------------------------------------------------------------------
# HISTORICAL — closed-window record. Do NOT update these on a refresh.
# The 8 Mar - 24 Apr 2026 window is over; its numbers do not change, and the
# dormancy figures stay true regardless of what the account does afterwards.
# --------------------------------------------------------------------------
HIST = {
    "active_return": "+2.24%",
    "peak_value": "$102,932.51",
    "peak_date": "10 Apr 2026",
    "active_window": "8 Mar &ndash; 24 Apr 2026",
    "max_drawdown": "&minus;2.93%",
    "dormancy_cost": "$2,555",
}

OUT = f"TradingBot-ExecutiveSummary-{AS_AT_ISO}.pdf"

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


BODY = style("body", fontName="Helvetica", fontSize=9.5, leading=14,
             textColor=INK, alignment=TA_JUSTIFY, spaceAfter=7)
H1 = style("h1", fontName="Helvetica-Bold", fontSize=13, leading=16,
           textColor=ACCENT, spaceBefore=14, spaceAfter=7)
H2 = style("h2", fontName="Helvetica-Bold", fontSize=10, leading=13,
           textColor=INK, spaceBefore=9, spaceAfter=4)
SMALL = style("small", fontName="Helvetica", fontSize=8.2, leading=11.5,
              textColor=MUTED, spaceAfter=5)
CELL = style("cell", fontName="Helvetica", fontSize=8.6, leading=11.5,
             textColor=INK)
CELLB = style("cellb", fontName="Helvetica-Bold", fontSize=8.6, leading=11.5,
              textColor=INK)
BULLET = style("bullet", parent=BODY, leftIndent=13, bulletIndent=3,
               spaceAfter=4, alignment=0)


def header_footer(canvas, doc):
    canvas.saveState()
    w, h = LETTER
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(0.9 * inch, h - 0.62 * inch,
                      "TRADING-BOT  ·  EXECUTIVE SUMMARY")
    canvas.drawRightString(w - 0.9 * inch, h - 0.62 * inch,
                           "Paper trading · not live capital")
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.6)
    canvas.line(0.9 * inch, h - 0.72 * inch, w - 0.9 * inch, h - 0.72 * inch)
    canvas.line(0.9 * inch, 0.72 * inch, w - 0.9 * inch, 0.72 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(0.9 * inch, 0.56 * inch, f"Prepared {AS_AT}")
    canvas.drawRightString(w - 0.9 * inch, 0.56 * inch, "Page %d" % doc.page)
    canvas.restoreState()


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


def p(text, s=BODY):
    return Paragraph(text, s)


def bullets(items):
    return [Paragraph(f"&bull;&nbsp;&nbsp;{i}", BULLET) for i in items]


story = []

# ---------------------------------------------------------------- title
story.append(Spacer(1, 6))
story.append(Paragraph(
    "Automated Equity Trading System", ParagraphStyle(
        "t", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=19,
        leading=23, textColor=ACCENT, spaceAfter=2)))
story.append(Paragraph(
    "Executive Summary &mdash; Paper-Trading Validation Phase",
    ParagraphStyle("st", parent=styles["Normal"], fontName="Helvetica",
                   fontSize=11, leading=14, textColor=MUTED, spaceAfter=10)))

story.append(table([
    [p("<b>Status</b>", CELLB), p("Paper trading only. No live capital deployed at any point.", CELL)],
    [p("<b>Broker</b>", CELLB), p("Alpaca paper account, funded at $100,000 notional", CELL)],
    [p("<b>Strategy</b>", CELLB), p("Long-only mean reversion on oversold large-cap equities, evaluated once daily", CELL)],
    [p("<b>Objective</b>", CELLB), p("Complete a 90-day validated track record against a pre-defined "
                                     "approval gate before any real capital is considered", CELL)],
], [1.05 * inch, 5.55 * inch], header=False))

story.append(Spacer(1, 4))
story.append(p(
    "This document summarises a personal research project. It is not an investment product, "
    "not a solicitation, and not investment advice. All results below are from simulated "
    "execution against live market data.", SMALL))

# ---------------------------------------------------------------- 1
story.append(p("1.  Position at a Glance", H1))

story.append(table([
    [p("<b>Metric</b>", CELLB), p("<b>Value</b>", CELLB), p("<b>Note</b>", CELLB)],
    [p("Portfolio value", CELL), p(LIVE["portfolio_value"], CELL),
     p(f"as at {AS_AT_SHORT}", CELL)],
    [p("Peak portfolio value", CELL), p(HIST["peak_value"], CELL),
     p(HIST["peak_date"], CELL)],
    [p("Return while system was running", CELL),
     p(f'<font color="#1a6b3c"><b>{HIST["active_return"]}</b></font>', CELL),
     p(HIST["active_window"], CELL)],
    [p("Maximum drawdown from peak", CELL), p(HIST["max_drawdown"], CELL),
     p("within the active window", CELL)],
    [p("Realised profit and loss", CELL),
     p(f'<font color="#1a6b3c"><b>{LIVE["realised_pl"]}</b></font>', CELL),
     p(LIVE["round_trips_note"], CELL)],
    [p("Maximum consecutive losing trades", CELL),
     p(LIVE["max_consecutive_losses"], CELL), p("approval gate allows 2", CELL)],
    [p("Open positions", CELL), p(LIVE["open_positions"], CELL),
     p(LIVE["open_positions_note"], CELL)],
], [2.5 * inch, 1.6 * inch, 2.5 * inch]))

story.append(Spacer(1, 6))
story.append(p(
    "The headline figure requires an important caveat, addressed in section 5: the system was "
    "<b>dormant from 24 April to 25 July 2026</b>. The " + HIST["active_return"] + " was earned "
    "while it was running; the decline from that level to today's " + LIVE["portfolio_value"] +
    " accrued while it was not, with no exit rules being enforced on open positions. That "
    "distinction is the single most instructive result the project has produced so far.", BODY))

# ---------------------------------------------------------------- 2
story.append(p("2.  What the System Does", H1))
story.append(p(
    "The system scans a fixed universe of roughly 50 large-capitalisation US equities once per "
    "trading day, shortly after the open. It looks for names that have sold off sharply against "
    "their own recent trend &mdash; low relative strength, negative short-horizon return, price "
    "extended below its moving averages &mdash; on the thesis that high-quality large caps tend "
    "to revert after short-term dislocation.", BODY))
story.append(p(
    "Entries and exits are governed by fixed, published rules rather than discretion. Every "
    "position carries a hard stop and a profit target from the moment it is opened, and both are "
    "evaluated on every subsequent daily scan. The system is long-only and does not use margin, "
    "leverage, options, or short selling.", BODY))

story.append(p("Illustrative entries from the recorded history", H2))
story.append(p(
    "UPS was flagged at a 14-day relative strength index of 19.0 following a &minus;12.66% "
    "five-day return; 3M at an RSI of 21.4. These are genuinely deep oversold readings rather "
    "than marginal signals, which is the intended behaviour of the entry filter.", BODY))

# ---------------------------------------------------------------- 3
story.append(p("3.  Architecture", H1))
story.append(p(
    "The design separates <b>deterministic rules</b> from <b>judgement</b>, and deliberately "
    "keeps the rules in charge. Language models are used only where ranking genuinely helps, "
    "never to decide whether a trade is permissible.", BODY))

story.append(table([
    [p("<b>Layer</b>", CELLB), p("<b>Role</b>", CELLB), p("<b>Runs</b>", CELLB)],
    [p("Market data and indicators", CELL),
     p("Fetches daily bars for the universe and computes the indicator set. Isolated per symbol, "
       "so a single bad symbol cannot blank the whole scan.", CELL), p("Every scan", CELL)],
    [p("Deterministic strategy engine", CELL),
     p("Applies the entry and exit rules and scores every candidate. This layer alone can produce "
       "a complete, valid trading decision.", CELL), p("Every scan", CELL)],
    [p("Local language model", CELL),
     p("An 8-billion-parameter model running on local hardware produces a ranked shortlist and "
       "commentary. No data leaves the machine; no per-call cost.", CELL), p("Every scan", CELL)],
    [p("Cloud model escalation", CELL),
     p("A frontier model is consulted <i>only</i> when candidate selection is genuinely contested "
       "&mdash; more qualifying candidates than free portfolio slots. Hard-capped at 5 calls per day.", CELL),
     p("Contested days only", CELL)],
    [p("Guardrail layer", CELL),
     p("Independently re-checks every proposed order against position limits, size limits, the "
       "daily trade budget, and an execution firewall. Nothing reaches the broker without passing.", CELL),
     p("Before every order", CELL)],
    [p("Broker adapter", CELL),
     p("Submits orders to the Alpaca paper endpoint and reconciles them against the broker's own "
       "record of fills.", CELL), p("On execution", CELL)],
    [p("Audit log", CELL),
     p("Append-only record of market state, reasoning and outcome for every scan, with a derived "
       "queryable database rebuilt from it.", CELL), p("Every scan", CELL)],
], [1.35 * inch, 3.85 * inch, 1.4 * inch]))

story.append(Spacer(1, 6))
story.append(p(
    "The escalation design is the commercially interesting part. Routine days are handled entirely "
    "by local computation at zero marginal cost; paid inference is spent only on the decisions "
    "where it can change the outcome. In the recorded history, only 10 of 45 scans had two or more "
    "competing candidates, and only one had more candidates than free slots.", BODY))
story.append(p(
    "That single contested day is the best available evidence that the routing works. On 30 March "
    "the system held three positions with one slot free and two qualifying candidates. The escalated "
    "model selected NextEra Energy over Cisco, reasoning that no capacity remained after filling the "
    "slot with the higher-conviction trade. The independent deterministic score agreed &mdash; 3.60 "
    "against 1.12 &mdash; and the trade filled at $92.62.", BODY))

# ---------------------------------------------------------------- 4
story.append(p("4.  Risk Controls", H1))
story.append(p(
    "Every control below is enforced in code and verified by an automated test suite. They were "
    "independently audited against their written specification on 25 July 2026; all trading "
    "guardrails were confirmed implemented and enforced.", BODY))

story.append(KeepTogether([table([
    [p("<b>Control</b>", CELLB), p("<b>Setting</b>", CELLB), p("<b>Rationale</b>", CELLB)],
    [p("Maximum simultaneous positions", CELL), p("4", CELL),
     p("With the size cap, the book is fully invested at 4 positions", CELL)],
    [p("Maximum position size", CELL), p("25% of portfolio", CELL),
     p("Concentrated by design; bounded by the stop", CELL)],
    [p("Stop loss", CELL), p('<font color="#a32020"><b>&minus;4.5%</b></font>', CELL),
     p("Caps single-name damage at roughly 1.1% of portfolio", CELL)],
    [p("Profit target", CELL), p('<font color="#1a6b3c"><b>+10%</b></font>', CELL),
     p("Fixed exit; no discretionary letting-run", CELL)],
    [p("Maximum new trades per day", CELL), p("2", CELL),
     p("Limits the damage a single bad session can do", CELL)],
    [p("Exits exempt from the daily cap", CELL), p("Yes", CELL),
     p("Risk reduction must always be possible", CELL)],
    [p("Leverage / margin / shorting", CELL), p("None", CELL),
     p("Long-only, cash basis, enforced in code and at the broker", CELL)],
    [p("Paid inference calls per day", CELL), p("5", CELL),
     p("Bounds operating cost independently of market conditions", CELL)],
    [p("Emergency stop", CELL), p("1 second", CELL),
     p("Halts all activity; measured, not estimated", CELL)],
], [1.85 * inch, 1.35 * inch, 3.4 * inch])]))

story.append(Spacer(1, 6))
story.append(p(
    "The concentration setting deserves explicit mention because it is a deliberate choice rather "
    "than an inherited default. Four positions at 25% is materially more concentrated than a "
    "typical diversified book. The justification is that the stop, not the position size, bounds "
    "the loss: a stop that fires at &minus;4.5% on a 25% position costs about 1.12% of the "
    "portfolio. This was verified against a real fill &mdash; Berkshire Hathaway B stopped out at "
    "&minus;4.89%, costing 1.21%.", BODY))
story.append(p(
    "That reasoning holds <b>only while the exit machinery actually runs</b>. Pfizer, left "
    "unmanaged through the dormancy, reached &minus;9.95% &mdash; costing 2.49%, or roughly double. "
    "The gap between those two figures is not a concentration problem. It is an operational one.", BODY))

# ---------------------------------------------------------------- 5
story.append(p("5.  The Dormancy Incident", H1))
story.append(p(
    "On 24 April 2026 the scheduled daily scan stopped running. It was not noticed until 25 July "
    "&mdash; three months later. During that period four positions remained open with no exit rule "
    "being applied to them.", BODY))
story.append(p("Cause", H2))
story.append(p(
    "The scheduled job carried a natural-language instruction as its payload &mdash; effectively "
    "<i>&ldquo;run the scan, then send the summary&rdquo;</i> &mdash; which depended on a language "
    "model interpreting prose correctly every single day, with delivery marked best-effort. When it "
    "stopped, nothing reported the failure. A silent job is indistinguishable from a quiet market.", BODY))
story.append(p("Cost", H2))
story.append(p(
    "The " + HIST["active_return"] + " earned during the active window round-tripped into a net loss. Two positions drifted "
    "well past their stop thresholds &mdash; Pfizer to &minus;9.95%, Costco to &minus;6.76% &mdash; "
    "losses the stop rule would have bounded at &minus;4.5% had anything been running to enforce it. "
    "In paper terms the cost was approximately " + HIST["dormancy_cost"] + " of portfolio value.", BODY))
story.append(p("Response", H2))
story.append(p(
    "The remediation was structural rather than procedural, on the view that &ldquo;check it more "
    "often&rdquo; is not a control:", BODY))
for b in bullets([
    "Scheduling is now deterministic &mdash; a fixed command with no language model anywhere in "
    "the execution path.",
    "The scheduler runs as a supervised system service that restarts automatically after a crash, "
    "verified by killing the process and confirming the schedule survived.",
    "A daily summary is delivered on every run, and a failing run reports its own failure and "
    "exits non-zero. <b>Silence is never treated as success.</b>",
    "A separate watchdog counts missed trading weekdays independently of the scan itself.",
    "Every notification attempt is now written to a durable log, after a delivery path was found "
    "that could fail while reporting success.",
    "The emergency stop was tested for the first time, found non-functional, repaired, and "
    "re-tested: one second to halt, six to restore.",
]):
    story.append(b)

story.append(Spacer(1, 3))
story.append(p(
    "Six defects of this class were found and fixed in the course of preparing for restart. All "
    "shared one shape: a component that reported success while doing nothing. That pattern &mdash; "
    "not strategy selection &mdash; has been the dominant risk in this project.", BODY))

# ---------------------------------------------------------------- 6
story.append(p("6.  Track Record", H1))
story.append(p(
    "Two positions have completed a full round trip. Both exited on rule, not discretion, and both "
    "are confirmed against the broker's own record of fills rather than the system's internal log.", BODY))

story.append(table([
    [p("<b>Symbol</b>", CELLB), p("<b>Entry</b>", CELLB), p("<b>Exit</b>", CELLB),
     p("<b>Result</b>", CELLB), p("<b>Exit trigger</b>", CELLB)],
    [p("CVX", CELL), p("$187.81", CELL), p("$207.40", CELL),
     p('<font color="#1a6b3c"><b>+$2,585.54 (+10.43%)</b></font>', CELL), p("Profit target", CELL)],
    [p("BRK.B", CELL), p("$495.50", CELL), p("$471.26", CELL),
     p('<font color="#a32020"><b>&minus;$1,212.00 (&minus;4.89%)</b></font>', CELL), p("Stop loss", CELL)],
], [0.75 * inch, 0.85 * inch, 0.85 * inch, 2.15 * inch, 2.0 * inch]))

story.append(Spacer(1, 6))
story.append(p(
    "Both confirm the exit logic fires as configured. The stop executed at &minus;4.89% against a "
    "&minus;4.5% threshold, the difference being ordinary slippage on a market order.", BODY))
story.append(p(
    "The sample is deliberately not oversold here: <b>two completed round trips is not a track "
    "record.</b> Across 45 scans the system generated 51 decisions but only 8 orders, because the "
    "four-position limit was binding almost continuously &mdash; the portfolio was fully invested "
    "with under 2% cash through most of the window. The constraint on activity was capital "
    "allocation, not signal generation.", BODY))

# ---------------------------------------------------------------- 7
story.append(p("7.  Path to Live Capital", H1))
story.append(p(
    "A pre-defined gate must be cleared before any real money is considered. It was set in advance "
    "and has not been adjusted to fit results.", BODY))

story.append(KeepTogether([table([
    [p("<b>Criterion</b>", CELLB), p("<b>Threshold</b>", CELLB), p("<b>Current</b>", CELLB)],
    [p("Validated track record", CELL), p("90 consecutive days", CELL),
     p("Clock restarting; prior window invalidated by the outage", CELL)],
    [p("Return over the window", CELL), p("&ge; 3.75%", CELL),
     p(HIST["active_return"] + " achieved over the shorter active window", CELL)],
    [p("Maximum consecutive losing trades", CELL), p("&le; 2", CELL),
     p("1", CELL)],
    [p("Unattended operation", CELL), p("No unreported failures", CELL),
     p("Newly instrumented; unproven over a full window", CELL)],
], [2.1 * inch, 1.5 * inch, 3.0 * inch])]))

story.append(Spacer(1, 6))
story.append(p(
    "The 90-day clock is being restarted from zero rather than credited with the earlier window. "
    "The earlier data was gathered under a system that could stop without telling anyone, and "
    "before the audit logging needed to evaluate the gate properly existed. Carrying it forward "
    "would mean grading the experiment on evidence known to be incomplete.", BODY))

# ---------------------------------------------------------------- 8
story.append(p("8.  Known Limitations and Open Questions", H1))
story.append(p("Stated plainly, as these are the points most worth a second opinion:", BODY))
for b in bullets([
    "<b>Sample size.</b> Two completed round trips and 45 scans. Nothing here is statistically "
    "meaningful yet, and the 90-day window will likely produce only tens of trades.",
    "<b>No backtest.</b> The strategy has never been run against historical data with forward "
    "prices. All evidence is forward-looking paper trading. A parameter sweep has been deliberately "
    "deferred rather than run without a proper backtester.",
    "<b>Position sizing uses portfolio value, not buying power.</b> The paper account shows "
    "substantially more buying power than portfolio value, and nothing currently prevents a "
    "position being opened on margin. Harmless in simulation; must be settled before live capital.",
    "<b>Concentration is unvalidated.</b> Four positions at 25% was chosen deliberately and locked "
    "before the measurement window, but whether it is the right posture &mdash; against, say, eight "
    "at 12.5% &mdash; has not been tested.",
    "<b>Single-venue, single-strategy.</b> One broker, one strategy, one asset class, one machine. "
    "There is no redundancy in any of those dimensions.",
    "<b>The operator is the single point of failure.</b> The system now reports its own health, "
    "but someone still has to read those reports.",
]):
    story.append(b)

story.append(Spacer(1, 10))
story.append(p(
    "<b>Summary.</b> The engineering is in materially better condition than the strategy evidence. "
    "Risk controls are implemented, independently audited and demonstrated against real fills; the "
    "operational failure mode that caused the outage has been addressed structurally. What does not "
    "yet exist is a statistically meaningful track record &mdash; which is precisely what the next "
    "90 days are intended to produce.", BODY))

story.append(Spacer(1, 8))
story.append(p(
    "Figures are as at " + AS_AT + " and reflect simulated execution against live market data on an "
    "Alpaca paper account. Two positions were exiting on the stop-loss rule at the time of writing, "
    "so portfolio composition will differ once those settle.", SMALL))


doc = BaseDocTemplate(OUT, pagesize=LETTER,
                      leftMargin=0.9 * inch, rightMargin=0.9 * inch,
                      topMargin=0.95 * inch, bottomMargin=0.9 * inch,
                      title="Trading Bot - Executive Summary",
                      author="", subject="Paper-trading validation summary")
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
doc.addPageTemplates([PageTemplate(id="main", frames=[frame],
                                   onPage=header_footer)])
doc.build(story)
print("wrote", OUT)
