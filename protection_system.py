"""
Protection System - 자동 보호 메커니즘
일일 손실 추적, 연속 손실 추적, 자동 거래 중단 시스템
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, date, time
from dataclasses import dataclass
from enum import Enum
from database.database_manager import get_db_manager
from database.models import TradeHistory, TradingSession, TradingSettings

logger = logging.getLogger(__name__)

class ProtectionStatus(Enum):
    """보호 상태"""
    ACTIVE = "active"          # 정상 거래 가능
    DAILY_LIMIT = "daily_limit"  # 일일 손실 한도 도달
    CONSECUTIVE_LOSS = "consecutive_loss"  # 연속 손실 한도 도달
    MANUAL_STOP = "manual_stop"  # 수동 중단
    EMERGENCY_STOP = "emergency_stop"  # 긴급 중단

@dataclass
class DailyStats:
    """일일 거래 통계"""
    date: date
    total_trades: int
    successful_trades: int
    failed_trades: int
    total_pnl: float
    total_loss: float
    total_profit: float
    max_drawdown: float
    current_loss_streak: int

@dataclass
class ProtectionState:
    """보호 시스템 상태"""
    status: ProtectionStatus
    daily_loss: float
    daily_loss_percent: float
    consecutive_losses: int
    last_trade_time: Optional[datetime]
    protection_triggered_at: Optional[datetime]
    can_trade: bool
    message: str

class ProtectionSystem:
    """자동 보호 시스템"""

    def __init__(self):
        self.db_manager = get_db_manager()
        self._protection_states: Dict[int, ProtectionState] = {}

    def check_protection_status(self, user_id: int, account_balance: float) -> ProtectionState:
        """
        사용자의 현재 보호 상태 확인

        Args:
            user_id: 사용자 ID
            account_balance: 현재 계좌 잔고

        Returns:
            ProtectionState: 현재 보호 상태
        """
        try:
            # 사용자 설정 로드
            settings = self._get_user_settings(user_id)
            if not settings:
                return self._create_error_state("사용자 설정을 찾을 수 없습니다")

            # 캐시된 상태 확인
            if user_id in self._protection_states:
                cached_state = self._protection_states[user_id]
                if cached_state.status in [ProtectionStatus.MANUAL_STOP, ProtectionStatus.EMERGENCY_STOP]:
                    return cached_state

            # 일일 통계 계산
            daily_stats = self._get_daily_stats(user_id)

            # 연속 손실 계산
            consecutive_losses = self._get_consecutive_losses(user_id)

            # 보호 상태 판정
            protection_state = self._evaluate_protection_status(
                settings, daily_stats, consecutive_losses, account_balance
            )

            # 상태 캐시
            self._protection_states[user_id] = protection_state

            return protection_state

        except Exception as e:
            logger.error(f"Error checking protection status for user {user_id}: {e}")
            return self._create_error_state(f"보호 상태 확인 중 오류: {str(e)}")

    def _get_daily_stats(self, user_id: int) -> DailyStats:
        """오늘의 거래 통계 계산"""
        try:
            with self.db_manager.get_session() as session:
                today = date.today()

                # 오늘의 거래 내역 조회
                trades = session.query(TradeHistory).filter(
                    TradeHistory.user_id == user_id,
                    TradeHistory.timestamp >= datetime.combine(today, time.min),
                    TradeHistory.timestamp <= datetime.combine(today, time.max)
                ).all()

                total_trades = len(trades)
                total_pnl = sum(trade.profit_loss or 0 for trade in trades)

                successful_trades = len([t for t in trades if (t.profit_loss or 0) > 0])
                failed_trades = len([t for t in trades if (t.profit_loss or 0) < 0])

                total_profit = sum(trade.profit_loss for trade in trades if (trade.profit_loss or 0) > 0)
                total_loss = abs(sum(trade.profit_loss for trade in trades if (trade.profit_loss or 0) < 0))

                # 연속 손실 계산
                consecutive_losses = 0
                for trade in reversed(trades):  # 최근 거래부터
                    if (trade.profit_loss or 0) < 0:
                        consecutive_losses += 1
                    else:
                        break

                return DailyStats(
                    date=today,
                    total_trades=total_trades,
                    successful_trades=successful_trades,
                    failed_trades=failed_trades,
                    total_pnl=total_pnl,
                    total_loss=total_loss,
                    total_profit=total_profit,
                    max_drawdown=total_loss,  # 간단한 드로우다운 계산
                    current_loss_streak=consecutive_losses
                )

        except Exception as e:
            logger.error(f"Error calculating daily stats: {e}")
            return DailyStats(
                date=date.today(), total_trades=0, successful_trades=0,
                failed_trades=0, total_pnl=0.0, total_loss=0.0, total_profit=0.0,
                max_drawdown=0.0, current_loss_streak=0
            )

    def _get_consecutive_losses(self, user_id: int) -> int:
        """마지막 성공 거래 이후 연속 손실 횟수 계산"""
        try:
            with self.db_manager.get_session() as session:
                # 최근 거래부터 조회
                recent_trades = session.query(TradeHistory).filter(
                    TradeHistory.user_id == user_id
                ).order_by(TradeHistory.timestamp.desc()).limit(20).all()

                consecutive_losses = 0
                for trade in recent_trades:
                    if (trade.profit_loss or 0) < 0:
                        consecutive_losses += 1
                    else:
                        break  # 수익 거래를 만나면 중단

                return consecutive_losses

        except Exception as e:
            logger.error(f"Error calculating consecutive losses: {e}")
            return 0

    def _evaluate_protection_status(self, settings: Dict, daily_stats: DailyStats,
                                  consecutive_losses: int, account_balance: float) -> ProtectionState:
        """보호 상태 평가"""

        daily_loss_limit = settings['daily_loss_limit']
        consecutive_loss_limit = settings['consecutive_loss_limit']
        auto_protection_enabled = settings['auto_protection_enabled']

        # 일일 손실 비율 계산
        daily_loss_percent = (daily_stats.total_loss / account_balance) * 100 if account_balance > 0 else 0

        # 보호 상태 판정
        if auto_protection_enabled:
            # 일일 손실 한도 확인
            if daily_loss_percent >= daily_loss_limit:
                return ProtectionState(
                    status=ProtectionStatus.DAILY_LIMIT,
                    daily_loss=daily_stats.total_loss,
                    daily_loss_percent=daily_loss_percent,
                    consecutive_losses=consecutive_losses,
                    last_trade_time=None,
                    protection_triggered_at=datetime.now(),
                    can_trade=False,
                    message=f"일일 손실 한도 {daily_loss_limit}%에 도달했습니다. 내일 00:00에 자동 재개됩니다."
                )

            # 연속 손실 한도 확인
            if consecutive_losses >= consecutive_loss_limit:
                return ProtectionState(
                    status=ProtectionStatus.CONSECUTIVE_LOSS,
                    daily_loss=daily_stats.total_loss,
                    daily_loss_percent=daily_loss_percent,
                    consecutive_losses=consecutive_losses,
                    last_trade_time=None,
                    protection_triggered_at=datetime.now(),
                    can_trade=False,
                    message=f"연속 손실 {consecutive_loss_limit}회에 도달했습니다. 수동으로 재개하거나 내일 00:00에 자동 재개됩니다."
                )

        # 정상 상태
        return ProtectionState(
            status=ProtectionStatus.ACTIVE,
            daily_loss=daily_stats.total_loss,
            daily_loss_percent=daily_loss_percent,
            consecutive_losses=consecutive_losses,
            last_trade_time=None,
            protection_triggered_at=None,
            can_trade=True,
            message="정상 거래 가능"
        )

    def manually_reset_protection(self, user_id: int) -> bool:
        """보호 상태 수동 재설정"""
        try:
            if user_id in self._protection_states:
                current_state = self._protection_states[user_id]

                # 긴급 중단은 수동으로 재설정 불가
                if current_state.status == ProtectionStatus.EMERGENCY_STOP:
                    logger.warning(f"Emergency stop cannot be manually reset for user {user_id}")
                    return False

                # 보호 상태 초기화
                del self._protection_states[user_id]
                logger.info(f"Protection manually reset for user {user_id}")
                return True

            return True  # 보호 상태가 없으면 이미 재설정된 것으로 간주

        except Exception as e:
            logger.error(f"Error resetting protection for user {user_id}: {e}")
            return False

    def emergency_stop_all_trading(self, user_id: int, reason: str = "Emergency stop") -> bool:
        """긴급 전체 거래 중단"""
        try:
            # 보호 상태를 긴급 중단으로 설정
            emergency_state = ProtectionState(
                status=ProtectionStatus.EMERGENCY_STOP,
                daily_loss=0.0,
                daily_loss_percent=0.0,
                consecutive_losses=0,
                last_trade_time=datetime.now(),
                protection_triggered_at=datetime.now(),
                can_trade=False,
                message=f"긴급 중단: {reason}"
            )

            self._protection_states[user_id] = emergency_state

            # 실제 구현에서는 여기서 모든 미체결 주문 취소 등의 작업 수행
            logger.critical(f"Emergency stop activated for user {user_id}: {reason}")
            return True

        except Exception as e:
            logger.error(f"Error during emergency stop for user {user_id}: {e}")
            return False

    def get_protection_summary(self, user_id: int, account_balance: float) -> Dict[str, Any]:
        """보호 시스템 요약 정보"""
        try:
            state = self.check_protection_status(user_id, account_balance)
            settings = self._get_user_settings(user_id)
            daily_stats = self._get_daily_stats(user_id)

            return {
                'protection_status': state.status.value,
                'can_trade': state.can_trade,
                'message': state.message,
                'daily_stats': {
                    'total_trades': daily_stats.total_trades,
                    'successful_trades': daily_stats.successful_trades,
                    'failed_trades': daily_stats.failed_trades,
                    'total_pnl': daily_stats.total_pnl,
                    'total_loss': daily_stats.total_loss,
                    'daily_loss_percent': state.daily_loss_percent,
                    'daily_limit_percent': settings['daily_loss_limit'],
                    'remaining_loss_allowance': settings['daily_loss_limit'] - state.daily_loss_percent
                },
                'consecutive_stats': {
                    'current_losses': state.consecutive_losses,
                    'limit': settings['consecutive_loss_limit'],
                    'remaining_allowance': max(0, settings['consecutive_loss_limit'] - state.consecutive_losses)
                },
                'settings': {
                    'auto_protection_enabled': settings['auto_protection_enabled'],
                    'daily_loss_limit': settings['daily_loss_limit'],
                    'consecutive_loss_limit': settings['consecutive_loss_limit']
                }
            }

        except Exception as e:
            logger.error(f"Error getting protection summary: {e}")
            return {
                'protection_status': 'error',
                'can_trade': False,
                'message': f'보호 시스템 오류: {str(e)}',
                'daily_stats': {},
                'consecutive_stats': {},
                'settings': {}
            }

    def _get_user_settings(self, user_id: int) -> Optional[Dict[str, Any]]:
        """사용자 거래 설정 조회"""
        try:
            with self.db_manager.get_session() as session:
                settings = session.query(TradingSettings).filter_by(user_id=user_id).first()

                if settings:
                    return {
                        'daily_loss_limit': settings.daily_loss_limit,
                        'consecutive_loss_limit': settings.consecutive_loss_limit,
                        'auto_protection_enabled': settings.auto_protection_enabled
                    }
                else:
                    # 기본 설정
                    return {
                        'daily_loss_limit': 5.0,
                        'consecutive_loss_limit': 3,
                        'auto_protection_enabled': True
                    }

        except Exception as e:
            logger.error(f"Error getting user settings: {e}")
            return None

    def _create_error_state(self, message: str) -> ProtectionState:
        """오류 상태 생성"""
        return ProtectionState(
            status=ProtectionStatus.EMERGENCY_STOP,
            daily_loss=0.0,
            daily_loss_percent=0.0,
            consecutive_losses=0,
            last_trade_time=None,
            protection_triggered_at=datetime.now(),
            can_trade=False,
            message=message
        )

    def should_execute_trade(self, user_id: int, account_balance: float,
                           risk_amount: float) -> Dict[str, Any]:
        """거래 실행 전 보호 시스템 확인"""
        state = self.check_protection_status(user_id, account_balance)

        result = {
            'allowed': state.can_trade,
            'protection_status': state.status.value,
            'message': state.message,
            'warnings': []
        }

        if state.can_trade:
            # 추가 경고 확인
            settings = self._get_user_settings(user_id)
            if settings:
                # 리스크가 일일 한도에 근접하는지 확인
                potential_loss_percent = ((state.daily_loss + risk_amount) / account_balance) * 100
                if potential_loss_percent > settings['daily_loss_limit'] * 0.8:  # 80% 도달
                    result['warnings'].append(f"이 거래 후 일일 손실이 한도의 80%에 근접합니다")

                # 연속 손실 경고
                if state.consecutive_losses >= settings['consecutive_loss_limit'] - 1:
                    result['warnings'].append(f"연속 손실 한도에 근접했습니다 ({state.consecutive_losses + 1}/{settings['consecutive_loss_limit']})")

        return result


# 싱글톤 인스턴스
_protection_system = None

def get_protection_system() -> ProtectionSystem:
    """보호 시스템 인스턴스 반환"""
    global _protection_system
    if _protection_system is None:
        _protection_system = ProtectionSystem()
    return _protection_system