"""
Risk Management Pydantic schemas
AI 기반 리스크 관리 스키마 정의
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from decimal import Decimal


class RiskCalculationRequest(BaseModel):
    """포지션 사이징 계산 요청"""
    entry_price: float = Field(..., gt=0, description="진입 예상 가격")
    stop_loss_price: float = Field(..., gt=0, description="손절 가격")
    risk_percentage: float = Field(default=3.0, ge=0.1, le=10.0, description="리스크 비율 (%)")
    account_balance: Optional[float] = Field(None, gt=0, description="계좌 잔고 (없으면 자동 조회)")


class RiskCalculationResponse(BaseModel):
    """포지션 사이징 계산 응답"""
    # 기본 정보
    position_value: float = Field(..., description="포지션 총 가치 (USDT)")
    position_quantity: float = Field(..., description="포지션 수량")
    leverage: int = Field(..., description="최적 레버리지")
    seed_usage_percent: float = Field(..., description="시드 사용률 (%)")
    margin_used: float = Field(..., description="사용 마진 (USDT)")

    # 배율 정보
    actual_multiplier: float = Field(..., description="실제 달성 배율")
    target_multiplier: float = Field(..., description="목표 배율")

    # 리스크 정보
    target_risk_amount: float = Field(..., description="목표 리스크 금액 (USDT)")
    actual_risk_amount: float = Field(..., description="실제 리스크 금액 (USDT)")
    risk_accuracy: float = Field(..., description="리스크 정확도 (%)")
    risk_percentage: float = Field(..., description="리스크 비율 (%)")

    # 가격 정보
    entry_price: float = Field(..., description="진입가")
    stop_loss_price: float = Field(..., description="손절가")
    price_diff_percent: float = Field(..., description="가격 차이 (%)")

    # 계좌 정보
    account_balance: float = Field(..., description="계좌 잔고")
    remaining_balance: float = Field(..., description="남은 잔고")

    # 최적화 정보
    optimization_notes: str = Field(..., description="최적화 설명")
    is_optimal: bool = Field(..., description="최적 조합 여부")

    # 경고 및 상태
    warnings: List[str] = Field(default=[], description="경고 메시지")
    risk_level: Literal["VERY_LOW", "LOW", "MEDIUM", "HIGH"] = Field(..., description="리스크 레벨")


class MultiScenarioRequest(BaseModel):
    """다중 시나리오 계산 요청"""
    entry_price: float = Field(..., gt=0, description="진입가")
    stop_loss_prices: List[float] = Field(..., min_items=1, max_items=10, description="손절가 목록")
    risk_percentage: float = Field(default=3.0, ge=0.1, le=10.0, description="리스크 비율")
    account_balance: float = Field(default=1000.0, gt=0, description="계좌 잔고")


class MultiScenarioResponse(BaseModel):
    """다중 시나리오 계산 응답"""
    entry_price: float
    scenarios: Dict[str, Any]
    account_balance: float
    risk_percentage: float


class OptimalStopLossRequest(BaseModel):
    """최적 손절가 범위 요청"""
    entry_price: float = Field(..., gt=0, description="진입가")
    risk_percentage: float = Field(default=3.0, ge=0.1, le=10.0, description="리스크 비율")
    account_balance: float = Field(default=1000.0, gt=0, description="계좌 잔고")
    min_leverage: int = Field(default=1, ge=1, le=20, description="최소 레버리지")
    max_leverage: int = Field(default=10, ge=1, le=20, description="최대 레버리지")


class OptimalStopData(BaseModel):
    """최적 손절 데이터"""
    leverage: int
    stop_loss_price: float
    price_diff_percent: float


class OptimalStopLossResponse(BaseModel):
    """최적 손절가 범위 응답"""
    entry_price: float
    optimal_stops: List[OptimalStopData]
    risk_amount: float
    risk_percentage: float


class PositionRiskAssessment(BaseModel):
    """개별 포지션 리스크 평가"""
    symbol: str
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    margin_ratio: float = Field(..., description="마진 비율 (%)")
    liquidation_distance: float = Field(..., description="청산가까지 거리 (%)")
    pnl_percent: float = Field(..., description="미실현 손익 비율 (%)")
    alerts: List[str] = Field(default=[], description="경고 메시지")
    requires_action: bool = Field(..., description="조치 필요 여부")


class PortfolioRiskAssessment(BaseModel):
    """포트폴리오 리스크 평가"""
    portfolio_risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    total_balance: float
    total_unrealized_pnl: float
    portfolio_pnl_percent: float
    overall_margin_ratio: float
    position_count: int
    critical_positions: int
    high_risk_positions: int
    position_risks: List[PositionRiskAssessment]
    requires_immediate_action: bool
    recommendation: str


# AI 신호 관련 스키마
class FuturesAISignal(BaseModel):
    """선물 거래 AI 신호"""
    symbol: str = Field(..., description="거래 심볼")
    action: Literal["LONG", "SHORT", "CLOSE"] = Field(..., description="거래 방향")
    entry_price: float = Field(..., gt=0, description="진입가")
    stop_loss_price: float = Field(..., gt=0, description="손절가")
    take_profit_price: Optional[float] = Field(None, gt=0, description="익절가")
    confidence: float = Field(..., ge=0, le=100, description="신뢰도 (0-100)")
    reasoning: str = Field(..., description="신호 근거")
    risk_reward_ratio: Optional[float] = Field(None, description="위험 대비 수익 비율")

    def calculate_risk_reward_ratio(self) -> float:
        """위험 대비 수익 비율 계산"""
        if not self.take_profit_price:
            return 0.0

        risk = abs(self.entry_price - self.stop_loss_price)
        reward = abs(self.take_profit_price - self.entry_price)

        return reward / risk if risk > 0 else 0.0


class AutoTradingRequest(BaseModel):
    """자동 거래 실행 요청"""
    signal: FuturesAISignal
    risk_percentage: float = Field(default=3.0, ge=0.1, le=10.0)
    max_leverage: int = Field(default=10, ge=1, le=20)
    enable_stop_loss: bool = Field(default=True, description="자동 손절 활성화")
    enable_take_profit: bool = Field(default=True, description="자동 익절 활성화")


class AutoTradingResponse(BaseModel):
    """자동 거래 실행 응답"""
    success: bool
    main_order: Optional[Dict[str, Any]] = None
    stop_order: Optional[Dict[str, Any]] = None
    take_profit_order: Optional[Dict[str, Any]] = None
    position_calculation: Optional[RiskCalculationResponse] = None
    error_message: Optional[str] = None


# 긴급 정지 관련 스키마
class EmergencyStopRequest(BaseModel):
    """긴급 정지 요청"""
    stop_type: Literal["CLOSE_ALL", "CLOSE_SYMBOL", "CANCEL_ORDERS"] = Field(..., description="정지 타입")
    symbol: Optional[str] = Field(None, description="특정 심볼 (CLOSE_SYMBOL인 경우 필수)")
    confirm_code: str = Field(..., description="확인 코드")


class EmergencyStopResponse(BaseModel):
    """긴급 정지 응답"""
    success: bool
    stopped_positions: List[str] = Field(default=[], description="정지된 포지션")
    cancelled_orders: List[str] = Field(default=[], description="취소된 주문")
    total_pnl: float = Field(default=0.0, description="총 실현 손익")
    message: str
    timestamp: str


# 리스크 설정 프리셋
class RiskPreset(BaseModel):
    """리스크 설정 프리셋"""
    name: str
    risk_percentage: float
    max_leverage: int
    description: str


class RiskSettings(BaseModel):
    """사용자 리스크 설정"""
    default_risk_percentage: float = Field(default=3.0, ge=0.1, le=10.0)
    max_leverage: int = Field(default=10, ge=1, le=20)
    emergency_stop_loss_percent: float = Field(default=10.0, ge=1.0, le=50.0)
    max_daily_loss_percent: float = Field(default=15.0, ge=1.0, le=50.0)
    auto_stop_loss_enabled: bool = Field(default=True)
    auto_take_profit_enabled: bool = Field(default=True)
    notifications_enabled: bool = Field(default=True)


# 실시간 모니터링 응답
class RiskMonitoringStatus(BaseModel):
    """실시간 리스크 모니터링 상태"""
    timestamp: str
    portfolio_risk: PortfolioRiskAssessment
    active_alerts: List[str]
    system_status: Literal["NORMAL", "WARNING", "CRITICAL"]
    last_update: str


class LeverageRecommendation(BaseModel):
    """레버리지 추천"""
    symbol: str
    current_price: float
    recommended_leverage: int
    max_safe_leverage: int
    reasoning: str
    risk_factors: List[str]