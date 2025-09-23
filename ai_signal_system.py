"""
AI Signal System - AI 신호 생성 및 자동 주문 실행 시스템
신뢰도 기반 자동 실행 및 주문 상태 모니터링
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import random
import json
import time

logger = logging.getLogger(__name__)

class SignalAction(Enum):
    """신호 액션"""
    LONG = "LONG"
    SHORT = "SHORT"
    CLOSE_LONG = "CLOSE_LONG"
    CLOSE_SHORT = "CLOSE_SHORT"

class SignalConfidence(Enum):
    """신호 신뢰도 레벨"""
    LOW = "low"           # < 0.6 - 알림만, 수동 실행
    MEDIUM = "medium"     # 0.6-0.8 - 사용자 확인 후 실행
    HIGH = "high"         # > 0.8 - 즉시 자동 실행

class SignalStatus(Enum):
    """신호 상태"""
    PENDING = "pending"        # 대기 중
    APPROVED = "approved"      # 승인됨 (자동 또는 수동)
    EXECUTED = "executed"      # 실행됨
    CANCELLED = "cancelled"    # 취소됨
    EXPIRED = "expired"        # 만료됨
    FAILED = "failed"          # 실행 실패

@dataclass
class AISignal:
    """AI 신호 데이터 클래스"""
    timestamp: datetime
    symbol: str
    action: SignalAction
    confidence: float  # 0-1 범위
    entry_price: float
    stop_loss: float
    take_profit: Optional[float] = None
    strategy: str = "UNKNOWN"
    market_condition: str = "UNKNOWN"
    volatility: float = 0.0

    # 메타데이터
    signal_id: str = field(default_factory=lambda: f"signal_{int(time.time())}")
    status: SignalStatus = SignalStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    # 실행 정보
    executed_at: Optional[datetime] = None
    execution_price: Optional[float] = None
    order_ids: List[str] = field(default_factory=list)

    # 성과 정보
    final_pnl: Optional[float] = None
    final_pnl_percent: Optional[float] = None

    def __post_init__(self):
        """초기화 후 처리"""
        if self.expires_at is None:
            # 기본 만료 시간: 30분
            self.expires_at = self.created_at + timedelta(minutes=30)

    @property
    def confidence_level(self) -> SignalConfidence:
        """신뢰도 레벨 반환"""
        if self.confidence < 0.6:
            return SignalConfidence.LOW
        elif self.confidence < 0.8:
            return SignalConfidence.MEDIUM
        else:
            return SignalConfidence.HIGH

    @property
    def is_expired(self) -> bool:
        """만료 여부 확인"""
        return datetime.now() > self.expires_at

    @property
    def risk_reward_ratio(self) -> Optional[float]:
        """리스크 리워드 비율 계산"""
        if self.take_profit is None:
            return None

        if self.action in [SignalAction.LONG]:
            risk = abs(self.entry_price - self.stop_loss)
            reward = abs(self.take_profit - self.entry_price)
        else:  # SHORT
            risk = abs(self.stop_loss - self.entry_price)
            reward = abs(self.entry_price - self.take_profit)

        return reward / risk if risk > 0 else None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'signal_id': self.signal_id,
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'action': self.action.value,
            'confidence': self.confidence,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'strategy': self.strategy,
            'market_condition': self.market_condition,
            'volatility': self.volatility,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'execution_price': self.execution_price,
            'order_ids': self.order_ids,
            'final_pnl': self.final_pnl,
            'final_pnl_percent': self.final_pnl_percent,
            'confidence_level': self.confidence_level.value,
            'risk_reward_ratio': self.risk_reward_ratio
        }

class AISignalGenerator:
    """AI 신호 생성기 (시뮬레이션)"""

    def __init__(self):
        self.strategies = [
            "RSI_MACD_CONFLUENCE",
            "BOLLINGER_BREAKOUT",
            "EMA_CROSSOVER",
            "VOLUME_BREAKOUT",
            "SUPPORT_RESISTANCE"
        ]

        self.market_conditions = [
            "TRENDING_UP",
            "TRENDING_DOWN",
            "SIDEWAYS",
            "HIGH_VOLATILITY",
            "LOW_VOLATILITY"
        ]

    def generate_signal(self, symbol: str = "BTC/USDT", current_price: float = 26500.0) -> AISignal:
        """모의 AI 신호 생성"""

        # 랜덤 신호 생성 (실제로는 AI 모델에서 생성)
        action = random.choice(list(SignalAction))
        confidence = random.uniform(0.4, 0.95)
        strategy = random.choice(self.strategies)
        market_condition = random.choice(self.market_conditions)
        volatility = random.uniform(0.01, 0.05)  # 1-5% 변동성

        # 가격 계산
        if action == SignalAction.LONG:
            entry_price = current_price * random.uniform(0.998, 1.002)  # 현재가 ±0.2%
            stop_loss = entry_price * random.uniform(0.97, 0.99)        # 1-3% 손절
            take_profit = entry_price * random.uniform(1.02, 1.05)      # 2-5% 익절
        else:  # SHORT
            entry_price = current_price * random.uniform(0.998, 1.002)
            stop_loss = entry_price * random.uniform(1.01, 1.03)
            take_profit = entry_price * random.uniform(0.95, 0.98)

        return AISignal(
            timestamp=datetime.now(),
            symbol=symbol,
            action=action,
            confidence=confidence,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy=strategy,
            market_condition=market_condition,
            volatility=volatility
        )

class AISignalManager:
    """AI 신호 관리 및 자동 실행 시스템"""

    def __init__(self, risk_calculator=None, order_manager=None, protection_system=None):
        self.risk_calculator = risk_calculator
        self.order_manager = order_manager
        # self.protection_system = protection_system  # 보호시스템 비활성화

        self.active_signals: Dict[str, AISignal] = {}
        self.signal_history: List[AISignal] = []
        self.signal_generator = AISignalGenerator()

        # 설정
        self.auto_execute_high_confidence = True
        self.require_confirmation_medium = True
        self.notify_only_low = True

    def process_new_signal(self, signal: AISignal, user_id: int,
                          account_balance: float) -> Dict[str, Any]:
        """
        새로운 AI 신호 처리

        Args:
            signal: AI 신호
            user_id: 사용자 ID
            account_balance: 계좌 잔고

        Returns:
            처리 결과
        """
        try:
            # 신호 만료 확인
            if signal.is_expired:
                signal.status = SignalStatus.EXPIRED
                return {
                    'success': False,
                    'action': 'expired',
                    'message': '신호가 만료되었습니다',
                    'signal': signal.to_dict()
                }

            # 보호 시스템 확인 (일시적으로 비활성화)
            # if self.protection_system:
            #     protection_check = self.protection_system.should_execute_trade(
            #         user_id, account_balance, 0  # 임시 리스크 금액
            #     )

            #     if not protection_check['allowed']:
            #         signal.status = SignalStatus.CANCELLED
            #         return {
            #             'success': False,
            #             'action': 'blocked',
            #             'message': f"보호 시스템에 의해 차단됨: {protection_check['message']}",
            #             'signal': signal.to_dict()
            #         }

            # 신뢰도 기반 처리
            if signal.confidence_level == SignalConfidence.HIGH and self.auto_execute_high_confidence:
                return self._auto_execute_signal(signal, user_id, account_balance)

            elif signal.confidence_level == SignalConfidence.MEDIUM and self.require_confirmation_medium:
                return self._request_confirmation(signal, user_id, account_balance)

            else:  # LOW confidence
                return self._notify_only(signal)

        except Exception as e:
            logger.error(f"Error processing signal {signal.signal_id}: {e}")
            signal.status = SignalStatus.FAILED
            return {
                'success': False,
                'action': 'error',
                'message': f'신호 처리 중 오류: {str(e)}',
                'signal': signal.to_dict()
            }

    def _auto_execute_signal(self, signal: AISignal, user_id: int,
                           account_balance: float) -> Dict[str, Any]:
        """고신뢰도 신호 자동 실행"""
        try:
            # 리스크 계산
            if self.risk_calculator:
                from database.trading_settings_manager import get_trading_settings_manager
                settings_manager = get_trading_settings_manager()
                risk_settings = settings_manager.get_risk_settings(user_id)

                risk_result = self.risk_calculator.calculate_position(
                    user_capital=account_balance,
                    risk_percent=risk_settings['position_risk_percent'],
                    entry_price=signal.entry_price,
                    stop_loss=signal.stop_loss,
                    symbol=signal.symbol
                )

                if not risk_result.get('valid', False):
                    signal.status = SignalStatus.FAILED
                    return {
                        'success': False,
                        'action': 'risk_calculation_failed',
                        'message': f"리스크 계산 실패: {risk_result.get('message', '알 수 없는 오류')}",
                        'signal': signal.to_dict()
                    }

                # 주문 실행
                if self.order_manager:
                    direction = 'LONG' if signal.action == SignalAction.LONG else 'SHORT'

                    # OCO 주문 생성 (진입 + 손절 + 익절)
                    order_results = self.order_manager.create_oco_order(
                        risk_result, signal.entry_price, direction, signal.take_profit
                    )

                    if order_results['entry'].success:
                        signal.status = SignalStatus.EXECUTED
                        signal.executed_at = datetime.now()
                        signal.execution_price = signal.entry_price
                        signal.order_ids = [order_results['entry'].order_id]

                        self.active_signals[signal.signal_id] = signal

                        return {
                            'success': True,
                            'action': 'auto_executed',
                            'message': f'고신뢰도 신호 자동 실행됨 (신뢰도: {signal.confidence:.1%})',
                            'signal': signal.to_dict(),
                            'risk_result': risk_result,
                            'order_results': order_results
                        }

            # 테스트 모드 (실제 주문 없이)
            signal.status = SignalStatus.EXECUTED
            signal.executed_at = datetime.now()
            signal.execution_price = signal.entry_price
            self.active_signals[signal.signal_id] = signal

            return {
                'success': True,
                'action': 'auto_executed_test',
                'message': f'고신뢰도 신호 자동 실행됨 (테스트 모드, 신뢰도: {signal.confidence:.1%})',
                'signal': signal.to_dict()
            }

        except Exception as e:
            logger.error(f"Error auto-executing signal: {e}")
            signal.status = SignalStatus.FAILED
            return {
                'success': False,
                'action': 'execution_error',
                'message': f'자동 실행 중 오류: {str(e)}',
                'signal': signal.to_dict()
            }

    def _request_confirmation(self, signal: AISignal, user_id: int,
                            account_balance: float) -> Dict[str, Any]:
        """중신뢰도 신호 - 사용자 확인 요청"""
        signal.status = SignalStatus.PENDING
        self.active_signals[signal.signal_id] = signal

        return {
            'success': True,
            'action': 'confirmation_required',
            'message': f'중신뢰도 신호 - 사용자 확인 필요 (신뢰도: {signal.confidence:.1%})',
            'signal': signal.to_dict(),
            'requires_confirmation': True
        }

    def _notify_only(self, signal: AISignal) -> Dict[str, Any]:
        """저신뢰도 신호 - 알림만"""
        signal.status = SignalStatus.PENDING
        self.active_signals[signal.signal_id] = signal

        return {
            'success': True,
            'action': 'notification_only',
            'message': f'저신뢰도 신호 - 알림만 (신뢰도: {signal.confidence:.1%})',
            'signal': signal.to_dict(),
            'manual_execution_available': True
        }

    def manually_execute_signal(self, signal_id: str, user_id: int,
                               account_balance: float) -> Dict[str, Any]:
        """신호 수동 실행"""
        if signal_id not in self.active_signals:
            return {
                'success': False,
                'message': '신호를 찾을 수 없습니다'
            }

        signal = self.active_signals[signal_id]

        if signal.is_expired:
            signal.status = SignalStatus.EXPIRED
            return {
                'success': False,
                'message': '신호가 만료되었습니다'
            }

        # 자동 실행과 동일한 로직으로 수동 실행
        result = self._auto_execute_signal(signal, user_id, account_balance)
        result['action'] = 'manually_executed'
        result['message'] = result['message'].replace('자동', '수동')

        return result

    def cancel_signal(self, signal_id: str) -> Dict[str, Any]:
        """신호 취소"""
        if signal_id not in self.active_signals:
            return {
                'success': False,
                'message': '신호를 찾을 수 없습니다'
            }

        signal = self.active_signals[signal_id]
        signal.status = SignalStatus.CANCELLED

        # 히스토리로 이동
        self.signal_history.append(signal)
        del self.active_signals[signal_id]

        return {
            'success': True,
            'message': f'신호 {signal_id}가 취소되었습니다',
            'signal': signal.to_dict()
        }

    def get_active_signals(self) -> List[Dict[str, Any]]:
        """활성 신호 목록"""
        return [signal.to_dict() for signal in self.active_signals.values()]

    def get_signal_statistics(self) -> Dict[str, Any]:
        """신호 통계"""
        all_signals = list(self.active_signals.values()) + self.signal_history

        if not all_signals:
            return {
                'total_signals': 0,
                'executed_signals': 0,
                'success_rate': 0,
                'avg_confidence': 0,
                'avg_pnl': 0
            }

        executed_signals = [s for s in all_signals if s.status == SignalStatus.EXECUTED]
        successful_signals = [s for s in executed_signals if s.final_pnl and s.final_pnl > 0]

        return {
            'total_signals': len(all_signals),
            'active_signals': len(self.active_signals),
            'executed_signals': len(executed_signals),
            'successful_signals': len(successful_signals),
            'success_rate': len(successful_signals) / len(executed_signals) * 100 if executed_signals else 0,
            'avg_confidence': sum(s.confidence for s in all_signals) / len(all_signals),
            'avg_pnl': sum(s.final_pnl for s in executed_signals if s.final_pnl) / len(executed_signals) if executed_signals else 0,
            'confidence_distribution': {
                'high': len([s for s in all_signals if s.confidence_level == SignalConfidence.HIGH]),
                'medium': len([s for s in all_signals if s.confidence_level == SignalConfidence.MEDIUM]),
                'low': len([s for s in all_signals if s.confidence_level == SignalConfidence.LOW])
            }
        }

    def simulate_signal_generation(self, symbol: str = "BTC/USDT",
                                  current_price: float = 26500.0) -> AISignal:
        """신호 생성 시뮬레이션"""
        return self.signal_generator.generate_signal(symbol, current_price)


# 싱글톤 인스턴스
_ai_signal_manager = None

def get_ai_signal_manager(risk_calculator=None, order_manager=None, protection_system=None) -> AISignalManager:
    """AI 신호 관리자 인스턴스 반환"""
    global _ai_signal_manager
    if _ai_signal_manager is None:
        _ai_signal_manager = AISignalManager(risk_calculator, order_manager, None)  # 보호시스템 비활성화
    return _ai_signal_manager