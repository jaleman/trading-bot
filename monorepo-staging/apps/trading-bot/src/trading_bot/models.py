from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Literal


@dataclass(frozen=True)
class UniverseConfig:
    preset: str | None = None
    symbols: list[str] = field(default_factory=list)
    include_symbols: list[str] = field(default_factory=list)
    exclude_symbols: list[str] = field(default_factory=list)
    shortlist_size: int = 20
    min_price: float | None = None
    min_avg_dollar_volume: float | None = None


@dataclass(frozen=True)
class MovingAverageConfig:
    short: int
    long: int


@dataclass(frozen=True)
class EntryConfig:
    ma_crossover: MovingAverageConfig
    rsi_threshold: float
    min_rsi: float | None = None
    max_volatility_20d: float | None = None
    min_recent_return_5d: float | None = None
    min_recent_return_20d: float | None = None
    min_distance_to_ma_20_pct: float | None = None
    min_distance_to_ma_50_pct: float | None = None


@dataclass(frozen=True)
class ExitConfig:
    profit_target_pct: float
    stop_loss_pct: float


@dataclass(frozen=True)
class RiskConfig:
    max_positions: int
    max_trades_per_day: int
    max_position_size_pct: float
    max_sector_exposure_pct: float | None = None
    allow_pyramiding: bool = False


@dataclass(frozen=True)
class ModelsConfig:
    daily_decision: str
    monitoring: str

    @property
    def claude_review(self) -> str:
        return self.daily_decision

    @property
    def local_analysis(self) -> str:
        return self.monitoring


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
class ModelRoutingConfig:
    local_analysis_enabled: bool = True
    claude_escalation_enabled: bool = True
    max_candidates_for_local_analysis: int = 20
    escalate_when_slots_remaining_lte: int = 1


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
    universe: UniverseConfig | None = None
    risk: RiskConfig | None = None
    model_routing: ModelRoutingConfig = field(default_factory=ModelRoutingConfig)

    def __post_init__(self) -> None:
        if self.universe is None:
            object.__setattr__(
                self,
                "universe",
                UniverseConfig(symbols=list(self.watchlist)),
            )

        if self.risk is None:
            object.__setattr__(
                self,
                "risk",
                RiskConfig(
                    max_positions=self.max_positions,
                    max_trades_per_day=self.max_trades_per_day,
                    max_position_size_pct=self.max_position_size_pct,
                ),
            )


@dataclass(frozen=True)
class IndicatorSnapshot:
    symbol: str
    current_price: float
    ma_20: float
    ma_50: float
    rsi: float
    recent_return_5d: float = 0.0
    recent_return_20d: float = 0.0
    volatility_20d: float = 0.0
    avg_dollar_volume_20d: float = 0.0
    distance_to_ma_20_pct: float = 0.0
    distance_to_ma_50_pct: float = 0.0


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
class StrategyCandidate:
    symbol: str
    action: Literal["buy", "sell", "watch", "hold", "skip"]
    reason: str
    score: float = 0.0


@dataclass(frozen=True)
class StrategyEvaluation:
    classification: ScanResult
    candidates: list[StrategyCandidate] = field(default_factory=list)
    entry_decisions: list["TradeDecision"] = field(default_factory=list)
    exit_decisions: list["TradeDecision"] = field(default_factory=list)


@dataclass(frozen=True)
class LocalAnalysisItem:
    symbol: str
    action: Literal["buy", "sell", "watch", "hold", "skip"]
    summary: str
    confidence: float = 0.0


@dataclass(frozen=True)
class LocalAnalysisResult:
    summary: str
    ranked_candidates: list[LocalAnalysisItem] = field(default_factory=list)
    escalate_to_claude: bool = False
    escalation_reason: str = ""


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
    strategy_evaluation: StrategyEvaluation | None = None
    local_analysis: LocalAnalysisResult | None = None
    triggered: list[str] = field(default_factory=list)
    watching: list[str] = field(default_factory=list)
    decisions: list[TradeDecision] = field(default_factory=list)
    order_results: list[OrderResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
