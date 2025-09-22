"""
📊 Database Models - 데이터베이스 모델 정의

자동매매 시스템의 모든 데이터 모델
- 설정 모델
- 로그 모델
- 신호 모델
- 성과 모델
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Any, Optional

@dataclass
class AutoTradingConfig:
    """자동매매 설정 모델"""
    user_id: int = 1
    is_enabled: bool = False
    trading_mode: str = "CONSERVATIVE"  # CONSERVATIVE, BALANCED, AGGRESSIVE
    max_daily_loss_pct: float = 3.0
    max_positions: int = 5
    trading_interval: int = 300  # seconds
    symbols: List[str] = field(default_factory=lambda: ["BTC/USDT", "ETH/USDT"])
    risk_config: Dict[str, Any] = field(default_factory=dict)
    notification_config: Dict[str, Any] = field(default_factory=dict)
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

@dataclass
class AutoTradingLog:
    """자동매매 로그 모델"""
    user_id: int
    log_level: str  # INFO, WARNING, ERROR, CRITICAL
    component: str  # ENGINE, MONITOR, EXECUTOR, RISK_MANAGER, etc.
    message: str
    data: Optional[Dict[str, Any]] = None
    error_traceback: Optional[str] = None
    id: Optional[int] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class AISignalLog:
    """AI 신호 로그 모델"""
    user_id: int
    symbol: str
    signal_type: str  # BUY, SELL, HOLD
    confidence_score: int  # 0-100
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: Optional[float] = None
    executed: bool = False
    execution_price: Optional[float] = None
    execution_quantity: Optional[float] = None
    pnl: float = 0.0
    signal_data: Optional[Dict[str, Any]] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class PerformanceData:
    """성과 데이터 모델"""
    user_id: int
    date: date
    total_trades: int = 0
    successful_trades: int = 0
    total_pnl: float = 0.0
    daily_pnl: float = 0.0
    total_volume: float = 0.0
    max_drawdown: float = 0.0
    active_positions: int = 0
    system_uptime: int = 0  # seconds
    error_count: int = 0
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if isinstance(self.date, str):
            self.date = datetime.strptime(self.date, '%Y-%m-%d').date()

    @property
    def success_rate(self) -> float:
        """성공률 계산"""
        if self.total_trades == 0:
            return 0.0
        return (self.successful_trades / self.total_trades) * 100

    @property
    def average_profit_per_trade(self) -> float:
        """거래당 평균 수익"""
        if self.total_trades == 0:
            return 0.0
        return self.total_pnl / self.total_trades

@dataclass
class SystemStatus:
    """시스템 상태 모델"""
    component: str
    status: str  # RUNNING, STOPPED, ERROR, STARTING, STOPPING
    last_heartbeat: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: Optional[int] = None

    def __post_init__(self):
        if isinstance(self.last_heartbeat, str):
            self.last_heartbeat = datetime.fromisoformat(self.last_heartbeat)

    @property
    def is_healthy(self) -> bool:
        """상태가 정상인지 확인"""
        return self.status in ["RUNNING", "STARTING"] and \
               (datetime.now() - self.last_heartbeat).total_seconds() < 300  # 5분

@dataclass
class TradingPosition:
    """거래 포지션 모델"""
    user_id: int
    symbol: str
    side: str  # LONG, SHORT
    entry_price: float
    quantity: float
    current_price: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    status: str = "OPEN"  # OPEN, CLOSED, PARTIAL
    signal_id: Optional[int] = None
    order_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: Optional[int] = None
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    def __post_init__(self):
        if self.opened_at is None:
            self.opened_at = datetime.now()

    def update_pnl(self, current_price: float):
        """현재 가격 기준 손익 업데이트"""
        self.current_price = current_price

        if self.side == "LONG":
            self.pnl = (current_price - self.entry_price) * self.quantity
            self.pnl_pct = ((current_price / self.entry_price) - 1) * 100
        else:  # SHORT
            self.pnl = (self.entry_price - current_price) * self.quantity
            self.pnl_pct = ((self.entry_price / current_price) - 1) * 100

    @property
    def is_profitable(self) -> bool:
        """수익 포지션인지 확인"""
        return self.pnl > 0

    @property
    def should_stop_loss(self) -> bool:
        """손절 조건 확인"""
        if not self.stop_loss:
            return False

        if self.side == "LONG":
            return self.current_price <= self.stop_loss
        else:  # SHORT
            return self.current_price >= self.stop_loss

    @property
    def should_take_profit(self) -> bool:
        """익절 조건 확인"""
        if not self.take_profit:
            return False

        if self.side == "LONG":
            return self.current_price >= self.take_profit
        else:  # SHORT
            return self.current_price <= self.take_profit

@dataclass
class RiskMetrics:
    """리스크 지표 모델"""
    user_id: int
    date: date
    daily_var: float = 0.0  # Value at Risk
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    calmar_ratio: float = 0.0
    total_exposure: float = 0.0
    portfolio_beta: float = 0.0
    risk_score: int = 0  # 0-100
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    alerts: List[str] = field(default_factory=list)
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if isinstance(self.date, str):
            self.date = datetime.strptime(self.date, '%Y-%m-%d').date()

    def calculate_risk_score(self) -> int:
        """종합 리스크 점수 계산"""
        score = 0

        # 드로우다운 점수 (낮을수록 좋음)
        if self.max_drawdown > 0.20:  # 20% 이상
            score += 40
        elif self.max_drawdown > 0.10:  # 10% 이상
            score += 25
        elif self.max_drawdown > 0.05:  # 5% 이상
            score += 10

        # 샤프 비율 점수 (높을수록 좋음)
        if self.sharpe_ratio < 0:
            score += 30
        elif self.sharpe_ratio < 0.5:
            score += 20
        elif self.sharpe_ratio < 1.0:
            score += 10

        # 승률 점수
        if self.win_rate < 0.3:
            score += 20
        elif self.win_rate < 0.4:
            score += 10

        # 익절/손절 비율
        if self.profit_factor < 1.0:
            score += 10

        self.risk_score = min(score, 100)

        # 리스크 레벨 설정
        if self.risk_score >= 70:
            self.risk_level = "CRITICAL"
        elif self.risk_score >= 50:
            self.risk_level = "HIGH"
        elif self.risk_score >= 25:
            self.risk_level = "MEDIUM"
        else:
            self.risk_level = "LOW"

        return self.risk_score

@dataclass
class MarketCondition:
    """시장 상황 모델"""
    symbol: str
    timestamp: datetime
    trend: str  # BULLISH, BEARISH, SIDEWAYS
    volatility: float
    volume_change: float
    price_change_24h: float
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    rsi: Optional[float] = None
    macd_signal: Optional[str] = None
    market_sentiment: str = "NEUTRAL"  # BULLISH, BEARISH, NEUTRAL
    fear_greed_index: Optional[int] = None
    correlation_btc: Optional[float] = None
    id: Optional[int] = None

    def __post_init__(self):
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)

    @property
    def is_high_volatility(self) -> bool:
        """높은 변동성 여부"""
        return self.volatility > 0.05  # 5% 이상

    @property
    def trend_strength(self) -> str:
        """트렌드 강도"""
        price_change = abs(self.price_change_24h)
        if price_change > 10:
            return "STRONG"
        elif price_change > 5:
            return "MODERATE"
        else:
            return "WEAK"