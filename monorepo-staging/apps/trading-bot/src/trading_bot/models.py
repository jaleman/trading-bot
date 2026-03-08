from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Literal


@dataclass(frozen=True)
class MovingAverageConfig:
    short: int
    long: int


@dataclass(frozen=True)
class EntryConfig:
    ma_crossover: MovingAverageConfig
    rsi_threshold: float


@dataclass(frozen=True)
class ExitConfig:
    profit_target_pct: float
    stop_loss_pct: float


@dataclass(frozen=True)
class ModelsConfig:
    daily_decision: str
    monitoring: str


@dataclass(frozen=True)
class CostControlsConfig:
    daily_claude_call_limit: int
    context_reset_after_exchanges: int
    prompt_caching_enabled: bool


@dataclass(frozen=True)
class ExecutionControlsConfig:
    safe_mode: bool
    paper_trade_execution_enabled: bool
    write_logs_by_default: bool


@dataclass(frozen=True)
class PaperToLiveConfig:
    min_return_pct: float
    evaluation_days: int
    max_consecutive_losses: int


@dataclass(frozen=True)
class StrategyConfig:
    watchlist: list[str]
    max_positions: int
    max_trades_per_day: int
    max_position_size_pct: float
    entry: EntryConfig
    exit: ExitConfig
    models: ModelsConfig
    cost_controls: CostControlsConfig
    execution_controls: ExecutionControlsConfig
    paper_to_live: PaperToLiveConfig


@dataclass(frozen=True)
class IndicatorSnapshot:
    symbol: str
    current_price: float
    ma_20: float
    ma_50: float
    rsi: float


@dataclass(frozen=True)
class AccountSnapshot:
    cash: float
    portfolio_value: float
    buying_power: float


@dataclass(frozen=True)
class PositionSnapshot:
    symbol: str
    qty: float
    avg_entry_price: float
    current_price: float
    unrealized_pl: float
    unrealized_plpc: float


@dataclass(frozen=True)
class OrderResult:
    id: str
    symbol: str
    qty: float
    side: str
    status: str


@dataclass(frozen=True)
class TradeHistoryEntry:
    symbol: str
    qty: float
    side: str
    status: str
    filled_avg_price: float


@dataclass(frozen=True)
class GuardrailState:
    current_date: str
    claude_calls_today: int = 0
    trades_today: int = 0


@dataclass(frozen=True)
class GuardrailStatus:
    name: str
    allowed: bool
    reasons: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ScanResult:
    triggered: list[str] = field(default_factory=list)
    watching: list[str] = field(default_factory=list)
    inactive: list[str] = field(default_factory=list)
    summary: str = ""


@dataclass(frozen=True)
class TradeDecision:
    symbol: str
    action: Literal["buy", "sell", "skip"]
    reason: str
    qty: int = 0


@dataclass(frozen=True)
class DailyScanSummary:
    status: str
    strategy_file: str
    runtime_root: str
    notes: list[str] = field(default_factory=list)
    trade_log: str = ""
    guardrail_state: GuardrailState | None = None
    guardrails: list[GuardrailStatus] = field(default_factory=list)
    account: AccountSnapshot | None = None
    positions: list[PositionSnapshot] = field(default_factory=list)
    indicator_snapshots: list[IndicatorSnapshot] = field(default_factory=list)
    prefilter_result: ScanResult | None = None
    triggered: list[str] = field(default_factory=list)
    watching: list[str] = field(default_factory=list)
    decisions: list[TradeDecision] = field(default_factory=list)
    order_results: list[OrderResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
