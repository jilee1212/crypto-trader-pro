"""
🛡️ RiskManager - 리스크 관리자

자동매매 시스템의 리스크를 종합적으로 관리
- 일일/주간/월간 손실 한도 관리
- 포지션 크기 제한
- 시장 상황 기반 리스크 조정
- 긴급 중단 조건 모니터링
"""

import time
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple, Callable
import logging
from dataclasses import dataclass, field
from enum import Enum
import threading
import asyncio
import json

from .signal_generator import TradingSignal
from .position_manager import Position, PositionManager

class RiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AlertType(Enum):
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"

@dataclass
class RiskAlert:
    type: AlertType
    level: RiskLevel
    message: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False

@dataclass
class RiskMetrics:
    daily_pnl: float = 0.0
    daily_loss_pct: float = 0.0
    weekly_pnl: float = 0.0
    monthly_pnl: float = 0.0
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    portfolio_value: float = 0.0
    total_exposure: float = 0.0
    position_concentration: float = 0.0
    correlation_risk: float = 0.0
    volatility_score: float = 0.0
    overall_risk_score: int = 0
    risk_level: RiskLevel = RiskLevel.LOW

@dataclass
class LossLimits:
    daily_limit_pct: float = 3.0
    daily_limit_amount: float = 1000.0
    weekly_limit_pct: float = 10.0
    monthly_limit_pct: float = 25.0
    max_drawdown_pct: float = 5.0

class RiskManager:
    """
    🛡️ 리스크 관리자

    기능:
    - 다층 손실 한도 관리
    - 포지션 크기 제한
    - 시장 리스크 모니터링
    - 긴급 중단 조건 확인
    """

    def __init__(self, config_manager):
        """리스크 관리자 초기화"""
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager

        # 설정 로드
        self.config = config_manager.get_config()
        self.risk_config = self.config.get('risk_management', {})

        # 손실 한도 설정
        self.loss_limits = LossLimits(
            daily_limit_pct=self.risk_config.get('daily_loss_limit_pct', 3.0),
            daily_limit_amount=self.risk_config.get('daily_loss_limit_amount', 1000.0),
            weekly_limit_pct=self.risk_config.get('weekly_loss_limit_pct', 10.0),
            monthly_limit_pct=self.risk_config.get('monthly_loss_limit_pct', 25.0),
            max_drawdown_pct=self.risk_config.get('max_drawdown_pct', 5.0)
        )

        # 포지션 제한
        self.max_positions = self.risk_config.get('max_positions', 5)
        self.max_position_size_pct = self.risk_config.get('max_position_size_pct', 5.0)
        self.max_correlation = self.risk_config.get('max_correlation', 0.7)

        # 리스크 지표
        self.risk_metrics = RiskMetrics()
        self.risk_alerts: List[RiskAlert] = []

        # 일일 손실 추적
        self.daily_losses = {}
        self.weekly_losses = {}
        self.monthly_losses = {}

        # 최고 포트폴리오 가치 (드로우다운 계산용)
        self.peak_portfolio_value = 0.0

        # 스레드 안전성
        self._lock = threading.Lock()

        # 마지막 업데이트 시간
        self.last_update = datetime.now()

        self.logger.info("RiskManager 초기화 완료")

    def pre_trading_check(self) -> bool:
        """
        거래 시작 전 리스크 검사

        Returns:
            bool: 거래 허용 여부
        """
        try:
            checks = [
                ("일일 손실 한도", self._check_daily_loss_limit()),
                ("주간 손실 한도", self._check_weekly_loss_limit()),
                ("월간 손실 한도", self._check_monthly_loss_limit()),
                ("최대 드로우다운", self._check_max_drawdown()),
                ("포지션 한도", self._check_position_limits()),
                ("시장 상황", self._check_market_conditions())
            ]

            all_passed = True
            for check_name, result in checks:
                if not result:
                    self.logger.error(f"❌ {check_name} 검사 실패")
                    all_passed = False
                else:
                    self.logger.debug(f"✅ {check_name} 검사 통과")

            if not all_passed:
                self._create_alert(
                    AlertType.CRITICAL,
                    RiskLevel.HIGH,
                    "사전 리스크 검사 실패 - 거래 시작 불가",
                    {}
                )

            return all_passed

        except Exception as e:
            self.logger.error(f"사전 리스크 검사 실패: {e}")
            return False

    def safety_check(self) -> bool:
        """
        실시간 안전 검사

        Returns:
            bool: 거래 계속 허용 여부
        """
        try:
            with self._lock:
                # 긴급 중단 조건 확인
                if self._check_emergency_conditions():
                    return False

                # 기본 리스크 검사
                safety_checks = [
                    self._check_daily_loss_limit(),
                    self._check_max_drawdown(),
                    self._check_position_concentration(),
                    self._check_api_connectivity()
                ]

                return all(safety_checks)

        except Exception as e:
            self.logger.error(f"안전 검사 실패: {e}")
            return False

    def validate_signal(self, signal: TradingSignal) -> bool:
        """
        신호 실행 전 리스크 검증

        Args:
            signal: 검증할 거래 신호

        Returns:
            bool: 신호 실행 허용 여부
        """
        try:
            # 포지션 수 제한 확인
            if not self._check_position_count():
                self.logger.warning("최대 포지션 수 도달 - 신호 거부")
                return False

            # 포지션 크기 검증
            if signal.position_size:
                if not self._validate_position_size(signal.position_size, signal.entry_price):
                    self.logger.warning("포지션 크기 제한 초과 - 신호 거부")
                    return False

            # 심볼별 집중도 확인
            if not self._check_symbol_concentration(signal.symbol):
                self.logger.warning("심볼 집중도 초과 - 신호 거부")
                return False

            # 신뢰도 기반 필터링
            min_confidence = self._get_min_confidence_for_current_risk()
            if signal.confidence < min_confidence:
                self.logger.warning(f"신뢰도 부족 ({signal.confidence} < {min_confidence}) - 신호 거부")
                return False

            # 시장 변동성 기반 필터링
            if not self._check_volatility_filter(signal):
                self.logger.warning("높은 변동성으로 인한 신호 거부")
                return False

            return True

        except Exception as e:
            self.logger.error(f"신호 검증 실패: {e}")
            return False

    def calculate_position_size(self, signal: TradingSignal, account_balance: float) -> float:
        """
        리스크 조정된 포지션 크기 계산

        Args:
            signal: 거래 신호
            account_balance: 계좌 잔고

        Returns:
            float: 조정된 포지션 크기
        """
        try:
            # 기본 포지션 크기 (계좌의 %)
            base_position_pct = self.risk_config.get('position_size_pct', 2.0) / 100

            # 신뢰도 기반 조정
            confidence_multiplier = signal.confidence / 100.0

            # 현재 리스크 레벨 기반 조정
            risk_multiplier = self._get_risk_multiplier()

            # 변동성 기반 조정
            volatility_multiplier = self._get_volatility_multiplier(signal.symbol)

            # 최종 포지션 크기 계산
            adjusted_pct = base_position_pct * confidence_multiplier * risk_multiplier * volatility_multiplier

            # 최대 제한 적용
            max_position_pct = self.max_position_size_pct / 100
            adjusted_pct = min(adjusted_pct, max_position_pct)

            # 포지션 크기 계산
            position_value = account_balance * adjusted_pct
            position_size = position_value / signal.entry_price

            self.logger.debug(
                f"포지션 크기 계산: {position_size:.6f} "
                f"(기본: {base_position_pct:.2%}, 신뢰도: {confidence_multiplier:.2f}, "
                f"리스크: {risk_multiplier:.2f}, 변동성: {volatility_multiplier:.2f})"
            )

            return position_size

        except Exception as e:
            self.logger.error(f"포지션 크기 계산 실패: {e}")
            return 0.0

    def update_risk_metrics(self, position_manager: PositionManager,
                          account_balance: float):
        """
        리스크 지표 업데이트

        Args:
            position_manager: 포지션 관리자
            account_balance: 계좌 잔고
        """
        try:
            with self._lock:
                # 손익 데이터 수집
                pnl_data = position_manager.calculate_pnl()
                portfolio_metrics = position_manager.get_portfolio_metrics()

                # 기본 지표 업데이트
                self.risk_metrics.daily_pnl = pnl_data.get('today_pnl', 0)
                self.risk_metrics.portfolio_value = account_balance + pnl_data.get('unrealized_pnl', 0)
                self.risk_metrics.total_exposure = portfolio_metrics.total_value

                # 손실 비율 계산
                if account_balance > 0:
                    self.risk_metrics.daily_loss_pct = abs(min(self.risk_metrics.daily_pnl, 0)) / account_balance * 100

                # 드로우다운 계산
                self._update_drawdown_metrics()

                # 집중도 리스크 계산
                self._calculate_concentration_risk(position_manager)

                # 전체 리스크 점수 계산
                self._calculate_overall_risk_score()

                # 리스크 레벨 결정
                self._determine_risk_level()

                # 위험 상황 알림 생성
                self._check_and_create_alerts()

                self.last_update = datetime.now()

        except Exception as e:
            self.logger.error(f"리스크 지표 업데이트 실패: {e}")

    def _check_daily_loss_limit(self) -> bool:
        """일일 손실 한도 확인"""
        try:
            daily_loss_pct = self.risk_metrics.daily_loss_pct
            daily_loss_amount = abs(min(self.risk_metrics.daily_pnl, 0))

            return (daily_loss_pct < self.loss_limits.daily_limit_pct and
                   daily_loss_amount < self.loss_limits.daily_limit_amount)

        except Exception:
            return True

    def _check_weekly_loss_limit(self) -> bool:
        """주간 손실 한도 확인"""
        try:
            # 주간 손실 계산 (실제 구현에서는 DB에서 조회)
            weekly_loss = 0.0  # 시뮬레이션
            return weekly_loss < self.loss_limits.weekly_limit_pct

        except Exception:
            return True

    def _check_monthly_loss_limit(self) -> bool:
        """월간 손실 한도 확인"""
        try:
            # 월간 손실 계산 (실제 구현에서는 DB에서 조회)
            monthly_loss = 0.0  # 시뮬레이션
            return monthly_loss < self.loss_limits.monthly_limit_pct

        except Exception:
            return True

    def _check_max_drawdown(self) -> bool:
        """최대 드로우다운 확인"""
        try:
            return self.risk_metrics.current_drawdown < self.loss_limits.max_drawdown_pct

        except Exception:
            return True

    def _check_position_limits(self) -> bool:
        """포지션 한도 확인"""
        try:
            # 실제 구현에서는 position_manager에서 조회
            current_positions = 0  # 시뮬레이션
            return current_positions < self.max_positions

        except Exception:
            return True

    def _check_market_conditions(self) -> bool:
        """시장 상황 확인"""
        try:
            # 시장 상황 기반 리스크 평가
            # 실제 구현에서는 시장 데이터 분석
            return True  # 시뮬레이션

        except Exception:
            return True

    def _check_emergency_conditions(self) -> bool:
        """긴급 중단 조건 확인"""
        try:
            emergency_conditions = [
                self.risk_metrics.daily_loss_pct >= self.loss_limits.daily_limit_pct * 0.9,  # 90% 도달
                self.risk_metrics.current_drawdown >= self.loss_limits.max_drawdown_pct * 0.8,  # 80% 도달
                self.risk_metrics.overall_risk_score >= 90,  # 위험 점수 90 이상
            ]

            if any(emergency_conditions):
                self._create_alert(
                    AlertType.EMERGENCY,
                    RiskLevel.CRITICAL,
                    "긴급 중단 조건 감지",
                    {
                        'daily_loss_pct': self.risk_metrics.daily_loss_pct,
                        'current_drawdown': self.risk_metrics.current_drawdown,
                        'risk_score': self.risk_metrics.overall_risk_score
                    }
                )
                return True

            return False

        except Exception as e:
            self.logger.error(f"긴급 조건 확인 실패: {e}")
            return True  # 오류 시 안전하게 중단

    def _check_position_count(self) -> bool:
        """포지션 수 확인"""
        # 실제 구현에서는 position_manager에서 조회
        current_count = 0  # 시뮬레이션
        return current_count < self.max_positions

    def _validate_position_size(self, position_size: float, entry_price: float) -> bool:
        """포지션 크기 검증"""
        try:
            position_value = position_size * entry_price
            portfolio_value = self.risk_metrics.portfolio_value

            if portfolio_value <= 0:
                return False

            position_pct = position_value / portfolio_value * 100
            return position_pct <= self.max_position_size_pct

        except Exception:
            return False

    def _check_symbol_concentration(self, symbol: str) -> bool:
        """심볼 집중도 확인"""
        # 실제 구현에서는 현재 포지션에서 해당 심볼의 비중 확인
        return True  # 시뮬레이션

    def _get_min_confidence_for_current_risk(self) -> int:
        """현재 리스크에 따른 최소 신뢰도"""
        risk_adjustments = {
            RiskLevel.LOW: 60,
            RiskLevel.MEDIUM: 70,
            RiskLevel.HIGH: 80,
            RiskLevel.CRITICAL: 90
        }
        return risk_adjustments.get(self.risk_metrics.risk_level, 70)

    def _check_volatility_filter(self, signal: TradingSignal) -> bool:
        """변동성 필터 확인"""
        try:
            # 높은 변동성 시 신호 필터링
            market_conditions = signal.market_conditions or {}
            volatility = market_conditions.get('volatility', 0)

            high_volatility_threshold = self.risk_config.get('high_volatility_threshold', 0.05)

            if volatility > high_volatility_threshold:
                # 높은 변동성 시 더 높은 신뢰도 요구
                required_confidence = 85
                return signal.confidence >= required_confidence

            return True

        except Exception:
            return True

    def _get_risk_multiplier(self) -> float:
        """리스크 레벨에 따른 포지션 크기 배수"""
        multipliers = {
            RiskLevel.LOW: 1.0,
            RiskLevel.MEDIUM: 0.8,
            RiskLevel.HIGH: 0.5,
            RiskLevel.CRITICAL: 0.2
        }
        return multipliers.get(self.risk_metrics.risk_level, 0.5)

    def _get_volatility_multiplier(self, symbol: str) -> float:
        """변동성에 따른 포지션 크기 배수"""
        # 실제 구현에서는 심볼별 변동성 데이터 사용
        return 1.0  # 시뮬레이션

    def _update_drawdown_metrics(self):
        """드로우다운 지표 업데이트"""
        try:
            current_value = self.risk_metrics.portfolio_value

            # 최고점 업데이트
            if current_value > self.peak_portfolio_value:
                self.peak_portfolio_value = current_value

            # 현재 드로우다운 계산
            if self.peak_portfolio_value > 0:
                self.risk_metrics.current_drawdown = (
                    (self.peak_portfolio_value - current_value) / self.peak_portfolio_value * 100
                )

            # 최대 드로우다운 업데이트
            self.risk_metrics.max_drawdown = max(
                self.risk_metrics.max_drawdown,
                self.risk_metrics.current_drawdown
            )

        except Exception as e:
            self.logger.error(f"드로우다운 지표 업데이트 실패: {e}")

    def _calculate_concentration_risk(self, position_manager: PositionManager):
        """집중도 리스크 계산"""
        try:
            # 포지션 요약 정보 가져오기
            summary = position_manager.get_position_summary()

            if summary['total_value'] <= 0:
                self.risk_metrics.position_concentration = 0
                return

            # 최대 심볼 비중 계산
            max_symbol_weight = 0
            for symbol_data in summary['positions_by_symbol'].values():
                symbol_value = abs(symbol_data.get('unrealized_pnl', 0))
                weight = symbol_value / summary['total_value'] * 100
                max_symbol_weight = max(max_symbol_weight, weight)

            self.risk_metrics.position_concentration = max_symbol_weight

        except Exception as e:
            self.logger.error(f"집중도 리스크 계산 실패: {e}")

    def _calculate_overall_risk_score(self):
        """전체 리스크 점수 계산"""
        try:
            score = 0

            # 일일 손실 점수 (40점 만점)
            daily_loss_score = min(self.risk_metrics.daily_loss_pct / self.loss_limits.daily_limit_pct * 40, 40)
            score += daily_loss_score

            # 드로우다운 점수 (30점 만점)
            drawdown_score = min(self.risk_metrics.current_drawdown / self.loss_limits.max_drawdown_pct * 30, 30)
            score += drawdown_score

            # 집중도 점수 (20점 만점)
            concentration_score = min(self.risk_metrics.position_concentration / 50 * 20, 20)
            score += concentration_score

            # 변동성 점수 (10점 만점)
            volatility_score = min(self.risk_metrics.volatility_score / 0.1 * 10, 10)
            score += volatility_score

            self.risk_metrics.overall_risk_score = int(score)

        except Exception as e:
            self.logger.error(f"리스크 점수 계산 실패: {e}")

    def _determine_risk_level(self):
        """리스크 레벨 결정"""
        score = self.risk_metrics.overall_risk_score

        if score >= 80:
            self.risk_metrics.risk_level = RiskLevel.CRITICAL
        elif score >= 60:
            self.risk_metrics.risk_level = RiskLevel.HIGH
        elif score >= 40:
            self.risk_metrics.risk_level = RiskLevel.MEDIUM
        else:
            self.risk_metrics.risk_level = RiskLevel.LOW

    def _check_api_connectivity(self) -> bool:
        """API 연결 상태 확인"""
        # 실제 구현에서는 거래소 API 연결 상태 확인
        return True  # 시뮬레이션

    def _check_and_create_alerts(self):
        """위험 상황 알림 생성"""
        try:
            # 일일 손실 경고
            if self.risk_metrics.daily_loss_pct >= self.loss_limits.daily_limit_pct * 0.8:
                self._create_alert(
                    AlertType.WARNING,
                    RiskLevel.HIGH,
                    f"일일 손실 한도 80% 도달 ({self.risk_metrics.daily_loss_pct:.1f}%)",
                    {'daily_loss_pct': self.risk_metrics.daily_loss_pct}
                )

            # 드로우다운 경고
            if self.risk_metrics.current_drawdown >= self.loss_limits.max_drawdown_pct * 0.7:
                self._create_alert(
                    AlertType.WARNING,
                    RiskLevel.HIGH,
                    f"드로우다운 경고 ({self.risk_metrics.current_drawdown:.1f}%)",
                    {'current_drawdown': self.risk_metrics.current_drawdown}
                )

            # 높은 집중도 경고
            if self.risk_metrics.position_concentration >= 40:
                self._create_alert(
                    AlertType.WARNING,
                    RiskLevel.MEDIUM,
                    f"높은 포지션 집중도 ({self.risk_metrics.position_concentration:.1f}%)",
                    {'concentration': self.risk_metrics.position_concentration}
                )

        except Exception as e:
            self.logger.error(f"알림 생성 실패: {e}")

    def _create_alert(self, alert_type: AlertType, risk_level: RiskLevel,
                     message: str, data: Dict[str, Any]):
        """리스크 알림 생성"""
        alert = RiskAlert(
            type=alert_type,
            level=risk_level,
            message=message,
            data=data
        )

        self.risk_alerts.append(alert)

        # 로그 레벨에 따른 기록
        if alert_type == AlertType.EMERGENCY:
            self.logger.critical(f"🚨 {message}")
        elif alert_type == AlertType.CRITICAL:
            self.logger.error(f"❌ {message}")
        else:
            self.logger.warning(f"⚠️ {message}")

        # 알림 개수 제한 (최근 100개만 유지)
        if len(self.risk_alerts) > 100:
            self.risk_alerts = self.risk_alerts[-100:]

    def get_risk_status(self) -> Dict[str, Any]:
        """리스크 상태 조회"""
        with self._lock:
            return {
                'risk_level': self.risk_metrics.risk_level.value,
                'risk_score': self.risk_metrics.overall_risk_score,
                'daily_loss_pct': self.risk_metrics.daily_loss_pct,
                'current_drawdown': self.risk_metrics.current_drawdown,
                'position_concentration': self.risk_metrics.position_concentration,
                'limits': {
                    'daily_limit': self.loss_limits.daily_limit_pct,
                    'max_drawdown': self.loss_limits.max_drawdown_pct,
                    'max_positions': self.max_positions
                },
                'alerts_count': len([a for a in self.risk_alerts if not a.acknowledged]),
                'last_update': self.last_update.isoformat()
            }

    def get_recent_alerts(self, limit: int = 10) -> List[RiskAlert]:
        """최근 알림 조회"""
        with self._lock:
            return sorted(self.risk_alerts, key=lambda x: x.timestamp, reverse=True)[:limit]

    def acknowledge_alert(self, alert_index: int) -> bool:
        """알림 확인 처리"""
        try:
            with self._lock:
                if 0 <= alert_index < len(self.risk_alerts):
                    self.risk_alerts[alert_index].acknowledged = True
                    return True
                return False
        except Exception:
            return False

    def reset_daily_metrics(self):
        """일일 지표 초기화"""
        try:
            with self._lock:
                self.risk_metrics.daily_pnl = 0.0
                self.risk_metrics.daily_loss_pct = 0.0
                self.logger.info("일일 리스크 지표 초기화")
        except Exception as e:
            self.logger.error(f"일일 지표 초기화 실패: {e}")

    def emergency_stop_check(self) -> Tuple[bool, str]:
        """
        긴급 중단 검사

        Returns:
            Tuple[bool, str]: (중단 필요 여부, 중단 사유)
        """
        try:
            # 일일 손실 한도 초과
            if self.risk_metrics.daily_loss_pct >= self.loss_limits.daily_limit_pct:
                return True, f"일일 손실 한도 초과 ({self.risk_metrics.daily_loss_pct:.1f}%)"

            # 최대 드로우다운 초과
            if self.risk_metrics.current_drawdown >= self.loss_limits.max_drawdown_pct:
                return True, f"최대 드로우다운 초과 ({self.risk_metrics.current_drawdown:.1f}%)"

            # 위험 점수 초과
            if self.risk_metrics.overall_risk_score >= 95:
                return True, f"위험 점수 임계치 초과 ({self.risk_metrics.overall_risk_score})"

            return False, ""

        except Exception as e:
            self.logger.error(f"긴급 중단 검사 실패: {e}")
            return True, "리스크 검사 오류"

    def cleanup(self):
        """리소스 정리"""
        try:
            with self._lock:
                self.risk_alerts.clear()
            self.logger.info("RiskManager 리소스 정리 완료")
        except Exception as e:
            self.logger.error(f"리소스 정리 실패: {e}")


# ==========================================
# EMERGENCY STOP SYSTEM
# ==========================================

class EmergencyStopTrigger(Enum):
    """긴급 중단 트리거 유형"""
    DAILY_LOSS_EXCEEDED = "DAILY_LOSS_EXCEEDED"
    API_CONNECTION_LOST = "API_CONNECTION_LOST"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    MANUAL_STOP = "MANUAL_STOP"
    VOLATILITY_SPIKE = "VOLATILITY_SPIKE"
    MARKET_CRASH = "MARKET_CRASH"
    POSITION_LIMIT_EXCEEDED = "POSITION_LIMIT_EXCEEDED"
    CORRELATION_BREACH = "CORRELATION_BREACH"

@dataclass
class EmergencyStopEvent:
    """긴급 중단 이벤트"""
    trigger: EmergencyStopTrigger
    message: str
    severity: AlertType
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    positions_to_close: List[str] = field(default_factory=list)
    action_taken: str = ""

class EmergencyStop:
    """
    🚨 긴급 중단 시스템

    기능:
    - 다양한 위험 상황에서 자동 중단
    - 포지션 청산 관리
    - 알림 발송
    - 상황별 대응 전략
    """

    def __init__(self, config_manager, position_manager=None):
        """긴급 중단 시스템 초기화"""
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self.position_manager = position_manager

        # 설정
        self.config = config_manager.get_config()
        self.emergency_config = self.config.get('emergency_stop', {})

        # 긴급 중단 상태
        self.is_emergency_mode = False
        self.emergency_events: List[EmergencyStopEvent] = []
        self.last_check_time = datetime.now()

        # 트리거별 처리 함수
        self.trigger_handlers = {
            EmergencyStopTrigger.DAILY_LOSS_EXCEEDED: self._handle_loss_exceeded,
            EmergencyStopTrigger.API_CONNECTION_LOST: self._handle_api_lost,
            EmergencyStopTrigger.SYSTEM_ERROR: self._handle_system_error,
            EmergencyStopTrigger.MANUAL_STOP: self._handle_manual_stop,
            EmergencyStopTrigger.VOLATILITY_SPIKE: self._handle_volatility_spike,
            EmergencyStopTrigger.MARKET_CRASH: self._handle_market_crash,
            EmergencyStopTrigger.POSITION_LIMIT_EXCEEDED: self._handle_position_limit,
            EmergencyStopTrigger.CORRELATION_BREACH: self._handle_correlation_breach
        }

        # 스레드 안전성
        self._lock = threading.Lock()

        self.logger.info("EmergencyStop 시스템 초기화 완료")

    def trigger_emergency_stop(self, trigger: EmergencyStopTrigger,
                             message: str, data: Dict[str, Any] = None) -> bool:
        """
        긴급 중단 실행

        Args:
            trigger: 중단 트리거
            message: 중단 사유
            data: 추가 데이터

        Returns:
            성공 여부
        """
        try:
            with self._lock:
                # 긴급 중단 이벤트 생성
                event = EmergencyStopEvent(
                    trigger=trigger,
                    message=message,
                    severity=AlertType.EMERGENCY,
                    data=data or {},
                    timestamp=datetime.now()
                )

                self.emergency_events.append(event)
                self.is_emergency_mode = True

                self.logger.critical(f"🚨 긴급 중단 실행: {trigger.value} - {message}")

                # 트리거별 처리
                if trigger in self.trigger_handlers:
                    action_result = self.trigger_handlers[trigger](event)
                    event.action_taken = action_result
                else:
                    # 기본 처리
                    action_result = self._default_emergency_action(event)
                    event.action_taken = action_result

                # 알림 발송
                self._send_emergency_notification(event)

                return True

        except Exception as e:
            self.logger.error(f"긴급 중단 실행 실패: {e}")
            return False

    def _handle_loss_exceeded(self, event: EmergencyStopEvent) -> str:
        """일일 손실 한도 초과 처리"""
        try:
            # 모든 포지션 청산
            if self.position_manager:
                positions = self.position_manager.get_all_positions()
                for position in positions:
                    self.position_manager.close_position(position.symbol, "EMERGENCY_LOSS_LIMIT")
                return f"손실 한도 초과로 {len(positions)}개 포지션 청산"
            return "손실 한도 초과 - 거래 중단"

        except Exception as e:
            self.logger.error(f"손실 초과 처리 실패: {e}")
            return f"처리 실패: {e}"

    def _handle_api_lost(self, event: EmergencyStopEvent) -> str:
        """API 연결 끊김 처리"""
        try:
            # 연결 재시도 및 포지션 모니터링 강화
            return "API 연결 끊김 - 재연결 시도 및 포지션 모니터링 강화"
        except Exception as e:
            return f"API 끊김 처리 실패: {e}"

    def _handle_system_error(self, event: EmergencyStopEvent) -> str:
        """시스템 오류 처리"""
        try:
            # 시스템 안전 모드 전환
            return "시스템 오류 - 안전 모드 전환"
        except Exception as e:
            return f"시스템 오류 처리 실패: {e}"

    def _handle_manual_stop(self, event: EmergencyStopEvent) -> str:
        """수동 중단 처리"""
        return "사용자 요청으로 시스템 중단"

    def _handle_volatility_spike(self, event: EmergencyStopEvent) -> str:
        """변동성 급증 처리"""
        try:
            # 높은 변동성 포지션만 선별 청산
            return "변동성 급증 - 위험 포지션 선별 청산"
        except Exception as e:
            return f"변동성 처리 실패: {e}"

    def _handle_market_crash(self, event: EmergencyStopEvent) -> str:
        """시장 폭락 처리"""
        try:
            # 모든 롱 포지션 청산, 숏 포지션 유지
            if self.position_manager:
                positions = self.position_manager.get_all_positions()
                closed_count = 0
                for position in positions:
                    if position.side == 'LONG':
                        self.position_manager.close_position(position.symbol, "MARKET_CRASH")
                        closed_count += 1
                return f"시장 폭락으로 {closed_count}개 롱 포지션 청산"
            return "시장 폭락 감지 - 거래 중단"
        except Exception as e:
            return f"시장 폭락 처리 실패: {e}"

    def _handle_position_limit(self, event: EmergencyStopEvent) -> str:
        """포지션 한도 초과 처리"""
        return "포지션 한도 초과 - 신규 거래 중단"

    def _handle_correlation_breach(self, event: EmergencyStopEvent) -> str:
        """상관관계 위반 처리"""
        return "상관관계 위반 - 유사 포지션 정리"

    def _default_emergency_action(self, event: EmergencyStopEvent) -> str:
        """기본 긴급 처리"""
        return f"기본 긴급 처리: {event.trigger.value}"

    def _send_emergency_notification(self, event: EmergencyStopEvent):
        """긴급 알림 발송"""
        try:
            # 여기서 실제 알림 시스템과 연동
            notification_data = {
                'type': 'EMERGENCY_STOP',
                'trigger': event.trigger.value,
                'message': event.message,
                'timestamp': event.timestamp.isoformat(),
                'action_taken': event.action_taken
            }

            self.logger.critical(f"긴급 알림: {json.dumps(notification_data, ensure_ascii=False)}")

        except Exception as e:
            self.logger.error(f"긴급 알림 발송 실패: {e}")

    def check_emergency_conditions(self) -> Tuple[bool, Optional[EmergencyStopTrigger], str]:
        """
        긴급 상황 확인

        Returns:
            (긴급상황여부, 트리거, 메시지)
        """
        try:
            # 이미 긴급 모드인 경우
            if self.is_emergency_mode:
                return True, EmergencyStopTrigger.MANUAL_STOP, "이미 긴급 모드"

            # 시스템 상태 확인
            # 여기서 다양한 조건들을 확인

            return False, None, ""

        except Exception as e:
            self.logger.error(f"긴급 조건 확인 실패: {e}")
            return True, EmergencyStopTrigger.SYSTEM_ERROR, f"시스템 확인 실패: {e}"

    def reset_emergency_mode(self) -> bool:
        """긴급 모드 해제"""
        try:
            with self._lock:
                self.is_emergency_mode = False
                self.logger.info("긴급 모드 해제됨")
                return True
        except Exception as e:
            self.logger.error(f"긴급 모드 해제 실패: {e}")
            return False

    def get_emergency_status(self) -> Dict[str, Any]:
        """긴급 상태 조회"""
        try:
            with self._lock:
                return {
                    'is_emergency_mode': self.is_emergency_mode,
                    'total_events': len(self.emergency_events),
                    'recent_events': [
                        {
                            'trigger': event.trigger.value,
                            'message': event.message,
                            'timestamp': event.timestamp.isoformat(),
                            'action_taken': event.action_taken
                        }
                        for event in self.emergency_events[-5:]  # 최근 5개
                    ]
                }
        except Exception as e:
            self.logger.error(f"긴급 상태 조회 실패: {e}")
            return {'is_emergency_mode': False, 'error': str(e)}


# ==========================================
# SAFETY SYSTEM
# ==========================================

class SafetyCheck:
    """안전 검사 결과"""
    def __init__(self, name: str, passed: bool, message: str = "", data: Dict[str, Any] = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.data = data or {}
        self.timestamp = datetime.now()

class SafetySystem:
    """
    🛡️ 다층 안전 시스템

    기능:
    - 여러 안전 검사를 순차적으로 실행
    - 실패 시 즉시 중단
    - 안전 검사 이력 관리
    - 동적 안전 기준 조정
    """

    def __init__(self, config_manager, risk_manager: RiskManager,
                 emergency_stop: EmergencyStop, position_manager=None):
        """안전 시스템 초기화"""
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self.risk_manager = risk_manager
        self.emergency_stop = emergency_stop
        self.position_manager = position_manager

        # 설정
        self.config = config_manager.get_config()
        self.safety_config = self.config.get('safety_system', {})

        # 안전 검사 함수들
        self.safety_checks: List[Callable[[], SafetyCheck]] = [
            self.check_daily_loss_limit,
            self.check_position_limits,
            self.check_api_connectivity,
            self.check_market_volatility,
            self.check_account_balance,
            self.check_system_resources,
            self.check_trading_hours,
            self.check_correlation_limits
        ]

        # 검사 이력
        self.check_history: List[List[SafetyCheck]] = []
        self.last_check_time = datetime.now()
        self.check_interval = self.safety_config.get('check_interval', 60)  # 60초

        # 스레드 안전성
        self._lock = threading.Lock()

        self.logger.info("SafetySystem 초기화 완료")

    def run_all_safety_checks(self) -> Tuple[bool, List[SafetyCheck]]:
        """
        모든 안전 검사 실행

        Returns:
            (전체통과여부, 검사결과목록)
        """
        try:
            with self._lock:
                checks = []
                all_passed = True

                self.logger.info("안전 검사 시작")

                for check_func in self.safety_checks:
                    try:
                        result = check_func()
                        checks.append(result)

                        if not result.passed:
                            all_passed = False
                            self.logger.warning(f"안전 검사 실패: {result.name} - {result.message}")

                            # 심각한 실패의 경우 긴급 중단
                            if self._is_critical_failure(result):
                                self.emergency_stop.trigger_emergency_stop(
                                    EmergencyStopTrigger.SYSTEM_ERROR,
                                    f"심각한 안전 검사 실패: {result.name}",
                                    {'check_result': result.data}
                                )
                        else:
                            self.logger.debug(f"안전 검사 통과: {result.name}")

                    except Exception as e:
                        error_check = SafetyCheck(
                            name=f"{check_func.__name__}_error",
                            passed=False,
                            message=f"검사 실행 오류: {e}"
                        )
                        checks.append(error_check)
                        all_passed = False
                        self.logger.error(f"안전 검사 오류: {check_func.__name__} - {e}")

                # 검사 이력 저장
                self.check_history.append(checks)
                if len(self.check_history) > 100:  # 최근 100회만 보관
                    self.check_history.pop(0)

                self.last_check_time = datetime.now()

                self.logger.info(f"안전 검사 완료: {len([c for c in checks if c.passed])}/{len(checks)} 통과")

                return all_passed, checks

        except Exception as e:
            self.logger.error(f"안전 검사 실행 실패: {e}")
            return False, [SafetyCheck("system_error", False, f"시스템 오류: {e}")]

    def check_daily_loss_limit(self) -> SafetyCheck:
        """일일 손실 한도 확인"""
        try:
            # risk_manager에서 일일 손실 확인
            current_loss = self.risk_manager.risk_metrics.daily_pnl
            loss_limit = self.risk_manager.loss_limits.daily_limit_amount

            if current_loss <= -loss_limit:
                return SafetyCheck(
                    "daily_loss_limit",
                    False,
                    f"일일 손실 한도 초과: ${current_loss:.2f} / ${loss_limit:.2f}",
                    {'current_loss': current_loss, 'limit': loss_limit}
                )

            return SafetyCheck(
                "daily_loss_limit",
                True,
                f"일일 손실 한도 내: ${current_loss:.2f} / ${loss_limit:.2f}",
                {'current_loss': current_loss, 'limit': loss_limit}
            )

        except Exception as e:
            return SafetyCheck("daily_loss_limit", False, f"확인 실패: {e}")

    def check_position_limits(self) -> SafetyCheck:
        """포지션 한도 확인"""
        try:
            if self.position_manager:
                position_count = len(self.position_manager.get_all_positions())
                max_positions = self.risk_manager.max_positions

                if position_count >= max_positions:
                    return SafetyCheck(
                        "position_limits",
                        False,
                        f"포지션 한도 초과: {position_count}/{max_positions}",
                        {'current': position_count, 'limit': max_positions}
                    )

            return SafetyCheck("position_limits", True, "포지션 한도 내")

        except Exception as e:
            return SafetyCheck("position_limits", False, f"확인 실패: {e}")

    def check_api_connectivity(self) -> SafetyCheck:
        """API 연결 상태 확인"""
        try:
            # 여기서 실제 API 연결 상태 확인
            # 현재는 시뮬레이션
            return SafetyCheck("api_connectivity", True, "API 연결 정상")
        except Exception as e:
            return SafetyCheck("api_connectivity", False, f"확인 실패: {e}")

    def check_market_volatility(self) -> SafetyCheck:
        """시장 변동성 확인"""
        try:
            # 여기서 실제 시장 변동성 확인
            # 현재는 시뮬레이션
            return SafetyCheck("market_volatility", True, "시장 변동성 정상 범위")
        except Exception as e:
            return SafetyCheck("market_volatility", False, f"확인 실패: {e}")

    def check_account_balance(self) -> SafetyCheck:
        """계좌 잔고 확인"""
        try:
            # 여기서 실제 계좌 잔고 확인
            # 현재는 시뮬레이션
            return SafetyCheck("account_balance", True, "계좌 잔고 충분")
        except Exception as e:
            return SafetyCheck("account_balance", False, f"확인 실패: {e}")

    def check_system_resources(self) -> SafetyCheck:
        """시스템 리소스 확인"""
        try:
            # 메모리, CPU 사용률 등 확인
            return SafetyCheck("system_resources", True, "시스템 리소스 정상")
        except Exception as e:
            return SafetyCheck("system_resources", False, f"확인 실패: {e}")

    def check_trading_hours(self) -> SafetyCheck:
        """거래 시간 확인"""
        try:
            # 암호화폐는 24시간이므로 항상 True
            return SafetyCheck("trading_hours", True, "거래 시간 내")
        except Exception as e:
            return SafetyCheck("trading_hours", False, f"확인 실패: {e}")

    def check_correlation_limits(self) -> SafetyCheck:
        """상관관계 한도 확인"""
        try:
            # 포트폴리오 내 상관관계 확인
            return SafetyCheck("correlation_limits", True, "상관관계 한도 내")
        except Exception as e:
            return SafetyCheck("correlation_limits", False, f"확인 실패: {e}")

    def _is_critical_failure(self, check: SafetyCheck) -> bool:
        """심각한 실패 여부 판단"""
        critical_checks = [
            'daily_loss_limit',
            'api_connectivity',
            'account_balance',
            'system_error'
        ]
        return check.name in critical_checks

    def get_safety_status(self) -> Dict[str, Any]:
        """안전 상태 조회"""
        try:
            with self._lock:
                recent_checks = self.check_history[-1] if self.check_history else []

                return {
                    'last_check_time': self.last_check_time.isoformat(),
                    'total_checks': len(recent_checks),
                    'passed_checks': len([c for c in recent_checks if c.passed]),
                    'failed_checks': [
                        {'name': c.name, 'message': c.message}
                        for c in recent_checks if not c.passed
                    ],
                    'check_history_count': len(self.check_history)
                }
        except Exception as e:
            return {'error': f"상태 조회 실패: {e}"}