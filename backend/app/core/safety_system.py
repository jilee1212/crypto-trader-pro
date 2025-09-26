"""
Advanced Safety and Emergency Stop System
고급 안전 장치 및 긴급 정지 시스템
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import json
import hashlib

from ..services.binance_futures_client import BinanceFuturesClient

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"


class SafetyTrigger(Enum):
    DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"
    POSITION_LOSS_LIMIT = "POSITION_LOSS_LIMIT"
    MARGIN_RATIO_HIGH = "MARGIN_RATIO_HIGH"
    CONSECUTIVE_LOSSES = "CONSECUTIVE_LOSSES"
    API_ERROR_RATE = "API_ERROR_RATE"
    MANUAL_TRIGGER = "MANUAL_TRIGGER"
    LIQUIDATION_RISK = "LIQUIDATION_RISK"


@dataclass
class SafetyConfig:
    """안전 시스템 설정"""
    # 손실 제한
    max_daily_loss_percent: float = 5.0
    max_position_loss_percent: float = 10.0
    max_portfolio_loss_percent: float = 15.0

    # 마진 제한
    warning_margin_ratio: float = 70.0
    critical_margin_ratio: float = 80.0
    emergency_margin_ratio: float = 85.0

    # 거래 제한
    max_consecutive_losses: int = 5
    max_daily_trades: int = 20
    cooling_off_period_hours: int = 4

    # API 오류 제한
    max_api_errors_per_hour: int = 10
    api_error_cooldown_minutes: int = 15

    # 청산 위험
    liquidation_warning_distance: float = 20.0  # %
    liquidation_emergency_distance: float = 10.0  # %

    # 긴급 정지 설정
    enable_emergency_stop: bool = True
    emergency_confirmation_required: bool = True
    emergency_stop_timeout_minutes: int = 60


@dataclass
class SafetyAlert:
    """안전 경고"""
    alert_id: str
    level: AlertLevel
    trigger: SafetyTrigger
    message: str
    timestamp: datetime
    acknowledged: bool = False
    resolved: bool = False
    metadata: Dict = None

    def __post_init__(self):
        if not self.alert_id:
            self.alert_id = hashlib.md5(
                f"{self.trigger.value}_{self.timestamp}_{self.message}".encode()
            ).hexdigest()[:12]


@dataclass
class EmergencyStop:
    """긴급 정지 상태"""
    is_active: bool = False
    trigger: Optional[SafetyTrigger] = None
    activated_time: Optional[datetime] = None
    confirmation_code: Optional[str] = None
    auto_resolve_time: Optional[datetime] = None
    manual_override: bool = False
    stopped_positions: List[str] = None
    cancelled_orders: List[str] = None

    def __post_init__(self):
        if self.stopped_positions is None:
            self.stopped_positions = []
        if self.cancelled_orders is None:
            self.cancelled_orders = []


class SafetySystem:
    """종합 안전 관리 시스템"""

    def __init__(self, binance_client: BinanceFuturesClient):
        self.binance_client = binance_client
        self.config = SafetyConfig()

        # 상태 관리
        self.emergency_stop = EmergencyStop()
        self.active_alerts: Dict[str, SafetyAlert] = {}
        self.alert_history: List[SafetyAlert] = []

        # 통계 추적
        self.daily_stats = {
            'trades': 0,
            'losses': 0,
            'consecutive_losses': 0,
            'api_errors': 0,
            'last_reset_date': datetime.now().date()
        }

        # 모니터링 상태
        self.is_monitoring = False
        self.monitoring_task = None
        self.alert_callbacks: List[Callable] = []

        # API 오류 추적
        self.api_error_timestamps: List[datetime] = []
        self.last_error_time = None

    async def initialize(self):
        """안전 시스템 초기화"""
        try:
            # 현재 포트폴리오 상태 확인
            await self._check_initial_state()
            logger.info("Safety system initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Safety system initialization failed: {e}")
            return False

    async def _check_initial_state(self):
        """초기 상태 확인"""
        try:
            # 계좌 정보 확인
            account_info = await self.binance_client.get_account_info()

            # 활성 포지션 확인
            positions = await self.binance_client.get_positions()

            # 미결 주문 확인
            open_orders = await self.binance_client.get_open_orders()

            logger.info(f"Initial check: {len(positions)} positions, {len(open_orders)} open orders")

        except Exception as e:
            logger.error(f"Initial state check error: {e}")

    def update_config(self, new_config: Dict):
        """설정 업데이트"""
        for key, value in new_config.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        logger.info("Safety system config updated")

    def add_alert_callback(self, callback: Callable):
        """경고 콜백 추가"""
        self.alert_callbacks.append(callback)

    async def start_monitoring(self):
        """안전 모니터링 시작"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Safety monitoring started")

    async def stop_monitoring(self):
        """안전 모니터링 중지"""
        if self.is_monitoring:
            self.is_monitoring = False
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            logger.info("Safety monitoring stopped")

    async def _monitoring_loop(self):
        """모니터링 루프"""
        while self.is_monitoring:
            try:
                await self._check_all_safety_conditions()
                await asyncio.sleep(30)  # 30초마다 확인
            except Exception as e:
                logger.error(f"Safety monitoring error: {e}")
                await asyncio.sleep(60)

    async def _check_all_safety_conditions(self):
        """모든 안전 조건 확인"""
        try:
            # 일일 통계 초기화
            self._reset_daily_stats_if_needed()

            # 계좌 정보 조회
            account_info = await self.binance_client.get_account_info()
            positions = await self.binance_client.get_positions()

            # 각종 안전 조건 확인
            await self._check_loss_limits(account_info, positions)
            await self._check_margin_ratios(account_info, positions)
            await self._check_liquidation_risks(positions)
            await self._check_api_error_rate()
            await self._check_consecutive_losses()

        except Exception as e:
            logger.error(f"Safety condition check error: {e}")
            await self._handle_api_error()

    async def _check_loss_limits(self, account_info: Dict, positions: List[Dict]):
        """손실 제한 확인"""
        try:
            total_balance = float(account_info.get('totalWalletBalance', 0))
            total_unrealized_pnl = float(account_info.get('totalUnrealizedProfit', 0))

            # 일일 손실 확인 (간단한 추정)
            daily_loss_percent = abs(total_unrealized_pnl) / total_balance * 100

            if daily_loss_percent >= self.config.max_daily_loss_percent:
                await self._create_alert(
                    AlertLevel.CRITICAL,
                    SafetyTrigger.DAILY_LOSS_LIMIT,
                    f"일일 손실 한도 초과: {daily_loss_percent:.2f}%",
                    {"loss_percent": daily_loss_percent, "limit": self.config.max_daily_loss_percent}
                )

                if daily_loss_percent >= self.config.max_portfolio_loss_percent:
                    await self._trigger_emergency_stop(
                        SafetyTrigger.DAILY_LOSS_LIMIT,
                        f"포트폴리오 손실 한도 초과: {daily_loss_percent:.2f}%"
                    )

        except Exception as e:
            logger.error(f"Loss limit check error: {e}")

    async def _check_margin_ratios(self, account_info: Dict, positions: List[Dict]):
        """마진 비율 확인"""
        try:
            total_margin_balance = float(account_info.get('totalMarginBalance', 0))
            total_maintenance_margin = float(account_info.get('totalMaintMargin', 0))

            if total_margin_balance > 0:
                margin_ratio = (total_maintenance_margin / total_margin_balance) * 100

                if margin_ratio >= self.config.emergency_margin_ratio:
                    await self._trigger_emergency_stop(
                        SafetyTrigger.MARGIN_RATIO_HIGH,
                        f"긴급: 마진 비율 {margin_ratio:.1f}%"
                    )
                elif margin_ratio >= self.config.critical_margin_ratio:
                    await self._create_alert(
                        AlertLevel.CRITICAL,
                        SafetyTrigger.MARGIN_RATIO_HIGH,
                        f"위험: 마진 비율 {margin_ratio:.1f}%",
                        {"margin_ratio": margin_ratio}
                    )
                elif margin_ratio >= self.config.warning_margin_ratio:
                    await self._create_alert(
                        AlertLevel.WARNING,
                        SafetyTrigger.MARGIN_RATIO_HIGH,
                        f"주의: 마진 비율 {margin_ratio:.1f}%",
                        {"margin_ratio": margin_ratio}
                    )

        except Exception as e:
            logger.error(f"Margin ratio check error: {e}")

    async def _check_liquidation_risks(self, positions: List[Dict]):
        """청산 위험 확인"""
        try:
            for position in positions:
                position_amt = float(position.get('positionAmt', 0))
                if position_amt == 0:
                    continue

                mark_price = float(position.get('markPrice', 0))
                liquidation_price = float(position.get('liquidationPrice', 0))
                symbol = position.get('symbol')

                if liquidation_price > 0 and mark_price > 0:
                    if position_amt > 0:  # LONG
                        distance_percent = ((mark_price - liquidation_price) / mark_price) * 100
                    else:  # SHORT
                        distance_percent = ((liquidation_price - mark_price) / mark_price) * 100

                    if distance_percent <= self.config.liquidation_emergency_distance:
                        await self._trigger_emergency_stop(
                            SafetyTrigger.LIQUIDATION_RISK,
                            f"{symbol} 청산 위험: {distance_percent:.1f}% 거리"
                        )
                    elif distance_percent <= self.config.liquidation_warning_distance:
                        await self._create_alert(
                            AlertLevel.CRITICAL,
                            SafetyTrigger.LIQUIDATION_RISK,
                            f"{symbol} 청산 주의: {distance_percent:.1f}% 거리",
                            {"symbol": symbol, "distance_percent": distance_percent}
                        )

        except Exception as e:
            logger.error(f"Liquidation risk check error: {e}")

    async def _check_api_error_rate(self):
        """API 오류율 확인"""
        try:
            now = datetime.now()
            hour_ago = now - timedelta(hours=1)

            # 지난 1시간 내 오류 수 확인
            recent_errors = [
                ts for ts in self.api_error_timestamps
                if ts > hour_ago
            ]

            if len(recent_errors) >= self.config.max_api_errors_per_hour:
                await self._create_alert(
                    AlertLevel.CRITICAL,
                    SafetyTrigger.API_ERROR_RATE,
                    f"API 오류율 높음: {len(recent_errors)}회/시간",
                    {"error_count": len(recent_errors), "timeframe": "1hour"}
                )

        except Exception as e:
            logger.error(f"API error rate check error: {e}")

    async def _check_consecutive_losses(self):
        """연속 손실 확인"""
        try:
            if self.daily_stats['consecutive_losses'] >= self.config.max_consecutive_losses:
                await self._create_alert(
                    AlertLevel.WARNING,
                    SafetyTrigger.CONSECUTIVE_LOSSES,
                    f"연속 손실: {self.daily_stats['consecutive_losses']}회",
                    {"consecutive_losses": self.daily_stats['consecutive_losses']}
                )

        except Exception as e:
            logger.error(f"Consecutive losses check error: {e}")

    async def _create_alert(self, level: AlertLevel, trigger: SafetyTrigger,
                          message: str, metadata: Dict = None):
        """안전 경고 생성"""
        try:
            alert = SafetyAlert(
                alert_id="",  # Will be auto-generated
                level=level,
                trigger=trigger,
                message=message,
                timestamp=datetime.now(),
                metadata=metadata or {}
            )

            # 중복 경고 확인
            existing_alert = None
            for existing in self.active_alerts.values():
                if (existing.trigger == trigger and
                    not existing.resolved and
                    existing.timestamp > datetime.now() - timedelta(minutes=5)):
                    existing_alert = existing
                    break

            if not existing_alert:
                self.active_alerts[alert.alert_id] = alert
                self.alert_history.append(alert)

                logger.warning(f"Safety alert created: {level.value} - {message}")

                # 콜백 실행
                for callback in self.alert_callbacks:
                    try:
                        await callback(alert)
                    except Exception as e:
                        logger.error(f"Alert callback error: {e}")

        except Exception as e:
            logger.error(f"Alert creation error: {e}")

    async def _trigger_emergency_stop(self, trigger: SafetyTrigger, message: str):
        """긴급 정지 실행"""
        try:
            if self.emergency_stop.is_active:
                logger.warning("Emergency stop already active")
                return

            logger.critical(f"EMERGENCY STOP TRIGGERED: {message}")

            # 긴급 정지 상태 설정
            self.emergency_stop.is_active = True
            self.emergency_stop.trigger = trigger
            self.emergency_stop.activated_time = datetime.now()

            if self.config.emergency_stop_timeout_minutes > 0:
                self.emergency_stop.auto_resolve_time = (
                    datetime.now() + timedelta(minutes=self.config.emergency_stop_timeout_minutes)
                )

            # 확인 코드 생성
            if self.config.emergency_confirmation_required:
                self.emergency_stop.confirmation_code = self._generate_confirmation_code()

            # 긴급 경고 생성
            await self._create_alert(
                AlertLevel.EMERGENCY,
                trigger,
                f"긴급 정지 활성화: {message}",
                {"confirmation_code": self.emergency_stop.confirmation_code}
            )

            # 모든 포지션 및 주문 정리
            await self._emergency_close_all()

        except Exception as e:
            logger.error(f"Emergency stop trigger error: {e}")

    async def _emergency_close_all(self):
        """긴급 상황시 모든 포지션/주문 정리"""
        try:
            # 모든 미결 주문 취소
            open_orders = await self.binance_client.get_open_orders()
            for order in open_orders:
                try:
                    await self.binance_client.cancel_order(
                        order['symbol'], order['orderId']
                    )
                    self.emergency_stop.cancelled_orders.append(order['orderId'])
                    logger.info(f"Cancelled order: {order['orderId']}")
                except Exception as e:
                    logger.error(f"Failed to cancel order {order['orderId']}: {e}")

            # 모든 포지션 청산
            positions = await self.binance_client.get_positions()
            for position in positions:
                position_amt = float(position.get('positionAmt', 0))
                if position_amt == 0:
                    continue

                try:
                    symbol = position['symbol']
                    side = "SELL" if position_amt > 0 else "BUY"
                    quantity = abs(position_amt)

                    close_result = await self.binance_client.place_order(
                        symbol=symbol,
                        side=side,
                        order_type="MARKET",
                        quantity=quantity,
                        reduce_only=True
                    )

                    self.emergency_stop.stopped_positions.append(symbol)
                    logger.info(f"Emergency closed position: {symbol}")

                except Exception as e:
                    logger.error(f"Failed to close position {symbol}: {e}")

        except Exception as e:
            logger.error(f"Emergency close all error: {e}")

    def _generate_confirmation_code(self) -> str:
        """확인 코드 생성"""
        timestamp = int(datetime.now().timestamp())
        return f"STOP{timestamp % 10000:04d}"

    async def resolve_emergency_stop(self, confirmation_code: str = None,
                                   manual_override: bool = False) -> bool:
        """긴급 정지 해제"""
        try:
            if not self.emergency_stop.is_active:
                logger.warning("No active emergency stop to resolve")
                return False

            # 확인 코드 검증
            if (self.config.emergency_confirmation_required and
                not manual_override and
                confirmation_code != self.emergency_stop.confirmation_code):
                logger.error("Invalid confirmation code for emergency stop resolution")
                return False

            # 긴급 정지 해제
            self.emergency_stop.is_active = False
            self.emergency_stop.manual_override = manual_override

            logger.info("Emergency stop resolved")

            # 해제 알림
            await self._create_alert(
                AlertLevel.INFO,
                SafetyTrigger.MANUAL_TRIGGER,
                "긴급 정지 해제됨",
                {"resolved_by": "manual" if manual_override else "confirmation"}
            )

            return True

        except Exception as e:
            logger.error(f"Emergency stop resolution error: {e}")
            return False

    async def _handle_api_error(self):
        """API 오류 처리"""
        now = datetime.now()
        self.api_error_timestamps.append(now)
        self.last_error_time = now

        # 오래된 오류 기록 정리
        hour_ago = now - timedelta(hours=1)
        self.api_error_timestamps = [
            ts for ts in self.api_error_timestamps
            if ts > hour_ago
        ]

    def _reset_daily_stats_if_needed(self):
        """일일 통계 초기화"""
        current_date = datetime.now().date()
        if self.daily_stats['last_reset_date'] != current_date:
            self.daily_stats.update({
                'trades': 0,
                'losses': 0,
                'consecutive_losses': 0,
                'api_errors': 0,
                'last_reset_date': current_date
            })

    def acknowledge_alert(self, alert_id: str) -> bool:
        """경고 확인"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            return True
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        """경고 해결"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].resolved = True
            return True
        return False

    def get_active_alerts(self) -> List[Dict]:
        """활성 경고 목록"""
        return [asdict(alert) for alert in self.active_alerts.values() if not alert.resolved]

    def get_emergency_status(self) -> Dict:
        """긴급 정지 상태"""
        return asdict(self.emergency_stop)

    def get_safety_status(self) -> Dict:
        """전체 안전 상태"""
        return {
            "monitoring_active": self.is_monitoring,
            "emergency_stop": self.get_emergency_status(),
            "active_alerts_count": len([a for a in self.active_alerts.values() if not a.resolved]),
            "daily_stats": self.daily_stats.copy(),
            "config": asdict(self.config)
        }