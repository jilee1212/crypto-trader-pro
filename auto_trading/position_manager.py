"""
📊 PositionManager - 포지션 관리자

자동매매 시스템의 모든 포지션을 추적하고 관리
- 포지션 추적 및 업데이트
- 손익 계산
- 포지션 청산 관리
- 리스크 모니터링
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import threading

from .trade_executor import OrderResult, OrderSide
from .signal_generator import TradingSignal

class PositionStatus(Enum):
    OPEN = "OPEN"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"
    PARTIAL = "PARTIAL"

class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"

@dataclass
class Position:
    id: str
    symbol: str
    side: PositionSide
    entry_price: float
    quantity: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    realized_pnl: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: PositionStatus = PositionStatus.OPEN
    signal_id: Optional[int] = None
    entry_order_id: Optional[str] = None
    stop_order_id: Optional[str] = None
    tp_order_id: Optional[str] = None
    fees_paid: float = 0.0
    opened_at: datetime = field(default_factory=datetime.now)
    closed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update_current_price(self, price: float):
        """현재 가격 업데이트 및 손익 계산"""
        self.current_price = price
        self._calculate_pnl()

    def _calculate_pnl(self):
        """손익 계산"""
        if self.current_price <= 0 or self.entry_price <= 0:
            return

        if self.side == PositionSide.LONG:
            self.unrealized_pnl = (self.current_price - self.entry_price) * self.quantity
            self.unrealized_pnl_pct = ((self.current_price / self.entry_price) - 1) * 100
        else:  # SHORT
            self.unrealized_pnl = (self.entry_price - self.current_price) * self.quantity
            self.unrealized_pnl_pct = ((self.entry_price / self.current_price) - 1) * 100

    @property
    def total_pnl(self) -> float:
        """총 손익 (실현 + 미실현)"""
        return self.realized_pnl + self.unrealized_pnl

    @property
    def is_profitable(self) -> bool:
        """수익 포지션 여부"""
        return self.unrealized_pnl > 0

    @property
    def should_stop_loss(self) -> bool:
        """손절 조건 확인"""
        if not self.stop_loss:
            return False

        if self.side == PositionSide.LONG:
            return self.current_price <= self.stop_loss
        else:  # SHORT
            return self.current_price >= self.stop_loss

    @property
    def should_take_profit(self) -> bool:
        """익절 조건 확인"""
        if not self.take_profit:
            return False

        if self.side == PositionSide.LONG:
            return self.current_price >= self.take_profit
        else:  # SHORT
            return self.current_price <= self.take_profit

    @property
    def holding_duration(self) -> timedelta:
        """보유 기간"""
        end_time = self.closed_at or datetime.now()
        return end_time - self.opened_at

@dataclass
class PortfolioMetrics:
    total_positions: int = 0
    open_positions: int = 0
    total_value: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    winning_positions: int = 0
    losing_positions: int = 0
    win_rate: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    profit_factor: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    total_fees: float = 0.0
    exposure: float = 0.0

class PositionManager:
    """
    📊 포지션 관리자

    기능:
    - 포지션 생성 및 추적
    - 실시간 손익 계산
    - 포지션 청산 관리
    - 포트폴리오 지표 계산
    """

    def __init__(self, config_manager):
        """포지션 관리자 초기화"""
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager

        # 설정 로드
        self.config = config_manager.get_config()
        self.max_positions = self.config.get('engine', {}).get('max_concurrent_positions', 5)

        # 포지션 저장소
        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []

        # 성능 지표
        self.portfolio_metrics = PortfolioMetrics()

        # 스레드 안전성
        self._lock = threading.Lock()

        # 포지션 ID 카운터
        self._position_counter = 0

        self.logger.info("PositionManager 초기화 완료")

    def create_position_from_order(self, signal: TradingSignal,
                                 order_result: OrderResult) -> Optional[Position]:
        """
        주문 결과로부터 포지션 생성

        Args:
            signal: 원본 거래 신호
            order_result: 주문 실행 결과

        Returns:
            Position: 생성된 포지션
        """
        try:
            with self._lock:
                if order_result.filled_amount <= 0:
                    self.logger.warning("체결된 수량이 없어 포지션을 생성할 수 없습니다")
                    return None

                # 포지션 ID 생성
                position_id = self._generate_position_id()

                # 포지션 사이드 결정
                side = PositionSide.LONG if order_result.side == OrderSide.BUY else PositionSide.SHORT

                # 포지션 생성
                position = Position(
                    id=position_id,
                    symbol=order_result.symbol,
                    side=side,
                    entry_price=order_result.average_price,
                    quantity=order_result.filled_amount,
                    current_price=order_result.average_price,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    signal_id=getattr(signal, 'id', None),
                    entry_order_id=order_result.order_id,
                    fees_paid=order_result.fees,
                    metadata={
                        'signal_confidence': signal.confidence,
                        'signal_reasoning': signal.reasoning,
                        'entry_timestamp': order_result.timestamp.isoformat()
                    }
                )

                # 포지션 저장
                self.positions[position_id] = position

                # 포트폴리오 지표 업데이트
                self._update_portfolio_metrics()

                self.logger.info(f"포지션 생성: {position_id} - {position.symbol} {position.side.value}")
                return position

        except Exception as e:
            self.logger.error(f"포지션 생성 실패: {e}")
            return None

    def update_position_prices(self, market_data: List) -> List[Position]:
        """
        시장 데이터로 포지션 가격 업데이트

        Args:
            market_data: 시장 데이터 리스트

        Returns:
            List[Position]: 업데이트된 포지션 리스트
        """
        updated_positions = []

        try:
            # 시장 데이터를 딕셔너리로 변환
            price_data = {data.symbol: data.close for data in market_data}

            with self._lock:
                for position in self.positions.values():
                    if position.symbol in price_data:
                        old_price = position.current_price
                        new_price = price_data[position.symbol]

                        position.update_current_price(new_price)
                        updated_positions.append(position)

                        # 가격 변동 로깅
                        if abs(new_price - old_price) / old_price > 0.01:  # 1% 이상 변동
                            self.logger.debug(
                                f"포지션 가격 업데이트: {position.id} "
                                f"{old_price:.4f} -> {new_price:.4f} "
                                f"({position.unrealized_pnl_pct:.2f}%)"
                            )

                # 포트폴리오 지표 업데이트
                if updated_positions:
                    self._update_portfolio_metrics()

        except Exception as e:
            self.logger.error(f"포지션 가격 업데이트 실패: {e}")

        return updated_positions

    def check_exit_conditions(self) -> List[Position]:
        """
        청산 조건 확인

        Returns:
            List[Position]: 청산이 필요한 포지션 리스트
        """
        positions_to_close = []

        try:
            with self._lock:
                for position in self.positions.values():
                    if position.status != PositionStatus.OPEN:
                        continue

                    should_close = False
                    close_reason = ""

                    # 손절 조건 확인
                    if position.should_stop_loss:
                        should_close = True
                        close_reason = "stop_loss"

                    # 익절 조건 확인
                    elif position.should_take_profit:
                        should_close = True
                        close_reason = "take_profit"

                    # 시간 기반 청산 확인
                    elif self._should_time_based_exit(position):
                        should_close = True
                        close_reason = "time_based"

                    # 리스크 기반 청산 확인
                    elif self._should_risk_based_exit(position):
                        should_close = True
                        close_reason = "risk_management"

                    if should_close:
                        position.metadata['close_reason'] = close_reason
                        positions_to_close.append(position)

        except Exception as e:
            self.logger.error(f"청산 조건 확인 실패: {e}")

        return positions_to_close

    def close_position(self, position_id: str, close_price: float,
                      close_quantity: Optional[float] = None) -> bool:
        """
        포지션 청산

        Args:
            position_id: 포지션 ID
            close_price: 청산 가격
            close_quantity: 청산 수량 (None이면 전량 청산)

        Returns:
            bool: 청산 성공 여부
        """
        try:
            with self._lock:
                if position_id not in self.positions:
                    self.logger.error(f"포지션을 찾을 수 없음: {position_id}")
                    return False

                position = self.positions[position_id]

                if close_quantity is None:
                    close_quantity = position.quantity

                # 부분 청산 처리
                if close_quantity < position.quantity:
                    return self._partial_close_position(position, close_price, close_quantity)

                # 전량 청산
                position.current_price = close_price
                position._calculate_pnl()

                # 실현 손익 계산
                position.realized_pnl = position.unrealized_pnl
                position.status = PositionStatus.CLOSED
                position.closed_at = datetime.now()

                # 포지션을 closed_positions로 이동
                self.closed_positions.append(position)
                del self.positions[position_id]

                # 포트폴리오 지표 업데이트
                self._update_portfolio_metrics()

                close_reason = position.metadata.get('close_reason', 'manual')
                self.logger.info(
                    f"포지션 청산 완료: {position_id} - "
                    f"손익: ${position.realized_pnl:.2f} ({position.unrealized_pnl_pct:.2f}%) "
                    f"사유: {close_reason}"
                )

                return True

        except Exception as e:
            self.logger.error(f"포지션 청산 실패: {e}")
            return False

    def _partial_close_position(self, position: Position, close_price: float,
                              close_quantity: float) -> bool:
        """부분 청산 처리"""
        try:
            # 부분 청산 비율 계산
            close_ratio = close_quantity / position.quantity

            # 부분 실현 손익 계산
            if position.side == PositionSide.LONG:
                partial_pnl = (close_price - position.entry_price) * close_quantity
            else:
                partial_pnl = (position.entry_price - close_price) * close_quantity

            # 포지션 업데이트
            position.quantity -= close_quantity
            position.realized_pnl += partial_pnl
            position.status = PositionStatus.PARTIAL

            # 손절/익절 가격 조정 (필요시)
            if position.stop_loss:
                position.stop_loss = position.stop_loss  # 유지
            if position.take_profit:
                position.take_profit = position.take_profit  # 유지

            self.logger.info(f"부분 청산: {position.id} - {close_quantity}/{position.quantity + close_quantity}")
            return True

        except Exception as e:
            self.logger.error(f"부분 청산 실패: {e}")
            return False

    def liquidate_all_positions(self) -> List[str]:
        """
        모든 포지션 청산

        Returns:
            List[str]: 청산된 포지션 ID 리스트
        """
        liquidated_positions = []

        try:
            with self._lock:
                positions_to_liquidate = list(self.positions.values())

                for position in positions_to_liquidate:
                    # 현재 가격으로 청산
                    if self.close_position(position.id, position.current_price):
                        liquidated_positions.append(position.id)

            self.logger.info(f"{len(liquidated_positions)}개 포지션 긴급 청산 완료")

        except Exception as e:
            self.logger.error(f"전량 청산 실패: {e}")

        return liquidated_positions

    def get_active_positions(self) -> List[Position]:
        """활성 포지션 목록 조회"""
        with self._lock:
            return list(self.positions.values())

    def get_active_count(self) -> int:
        """활성 포지션 수"""
        with self._lock:
            return len(self.positions)

    def get_position_by_symbol(self, symbol: str) -> List[Position]:
        """심볼별 포지션 조회"""
        with self._lock:
            return [pos for pos in self.positions.values() if pos.symbol == symbol]

    def calculate_pnl(self) -> Dict[str, float]:
        """전체 손익 계산"""
        try:
            with self._lock:
                total_unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())
                total_realized = sum(pos.realized_pnl for pos in self.closed_positions)
                today_pnl = self._calculate_today_pnl()

                return {
                    'total_pnl': total_realized + total_unrealized,
                    'realized_pnl': total_realized,
                    'unrealized_pnl': total_unrealized,
                    'today_pnl': today_pnl
                }

        except Exception as e:
            self.logger.error(f"손익 계산 실패: {e}")
            return {'total_pnl': 0, 'realized_pnl': 0, 'unrealized_pnl': 0, 'today_pnl': 0}

    def get_portfolio_metrics(self) -> PortfolioMetrics:
        """포트폴리오 지표 조회"""
        with self._lock:
            return self.portfolio_metrics

    def _update_portfolio_metrics(self):
        """포트폴리오 지표 업데이트"""
        try:
            # 기본 지표
            self.portfolio_metrics.total_positions = len(self.positions) + len(self.closed_positions)
            self.portfolio_metrics.open_positions = len(self.positions)

            # 손익 지표
            self.portfolio_metrics.unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
            self.portfolio_metrics.realized_pnl = sum(pos.realized_pnl for pos in self.closed_positions)
            self.portfolio_metrics.total_pnl = self.portfolio_metrics.realized_pnl + self.portfolio_metrics.unrealized_pnl

            # 포지션 가치
            self.portfolio_metrics.total_value = sum(
                pos.quantity * pos.current_price for pos in self.positions.values()
            )

            # 승률 관련 지표
            winning_trades = [pos for pos in self.closed_positions if pos.realized_pnl > 0]
            losing_trades = [pos for pos in self.closed_positions if pos.realized_pnl < 0]

            self.portfolio_metrics.winning_positions = len(winning_trades)
            self.portfolio_metrics.losing_positions = len(losing_trades)

            if self.closed_positions:
                self.portfolio_metrics.win_rate = len(winning_trades) / len(self.closed_positions) * 100

            if winning_trades:
                self.portfolio_metrics.average_win = sum(pos.realized_pnl for pos in winning_trades) / len(winning_trades)
                self.portfolio_metrics.largest_win = max(pos.realized_pnl for pos in winning_trades)

            if losing_trades:
                self.portfolio_metrics.average_loss = sum(pos.realized_pnl for pos in losing_trades) / len(losing_trades)
                self.portfolio_metrics.largest_loss = min(pos.realized_pnl for pos in losing_trades)

            # 수익/손실 비율
            total_wins = sum(pos.realized_pnl for pos in winning_trades)
            total_losses = abs(sum(pos.realized_pnl for pos in losing_trades))

            if total_losses > 0:
                self.portfolio_metrics.profit_factor = total_wins / total_losses

            # 수수료
            self.portfolio_metrics.total_fees = (
                sum(pos.fees_paid for pos in self.positions.values()) +
                sum(pos.fees_paid for pos in self.closed_positions)
            )

            # 익스포저 (총 포지션 가치)
            self.portfolio_metrics.exposure = self.portfolio_metrics.total_value

        except Exception as e:
            self.logger.error(f"포트폴리오 지표 업데이트 실패: {e}")

    def _calculate_today_pnl(self) -> float:
        """오늘 손익 계산"""
        try:
            today = datetime.now().date()
            today_pnl = 0.0

            # 오늘 청산된 포지션의 실현 손익
            for position in self.closed_positions:
                if position.closed_at and position.closed_at.date() == today:
                    today_pnl += position.realized_pnl

            # 오늘 오픈된 포지션의 미실현 손익
            for position in self.positions.values():
                if position.opened_at.date() == today:
                    today_pnl += position.unrealized_pnl

            return today_pnl

        except Exception:
            return 0.0

    def _should_time_based_exit(self, position: Position) -> bool:
        """시간 기반 청산 조건 확인"""
        try:
            # 설정에서 최대 보유 시간 확인
            max_holding_hours = self.config.get('risk_management', {}).get('max_holding_hours', 24)

            holding_hours = position.holding_duration.total_seconds() / 3600
            return holding_hours >= max_holding_hours

        except Exception:
            return False

    def _should_risk_based_exit(self, position: Position) -> bool:
        """리스크 기반 청산 조건 확인"""
        try:
            # 최대 손실 한도 확인
            max_loss_pct = self.config.get('risk_management', {}).get('max_position_loss_pct', 10.0)

            return position.unrealized_pnl_pct <= -max_loss_pct

        except Exception:
            return False

    def _generate_position_id(self) -> str:
        """포지션 ID 생성"""
        self._position_counter += 1
        timestamp = int(time.time() * 1000)
        return f"pos_{timestamp}_{self._position_counter}"

    def get_position_summary(self) -> Dict[str, Any]:
        """포지션 요약 정보"""
        with self._lock:
            open_positions = list(self.positions.values())

            summary = {
                'total_positions': len(open_positions),
                'symbols': list(set(pos.symbol for pos in open_positions)),
                'total_value': sum(pos.quantity * pos.current_price for pos in open_positions),
                'total_unrealized_pnl': sum(pos.unrealized_pnl for pos in open_positions),
                'profitable_positions': len([pos for pos in open_positions if pos.unrealized_pnl > 0]),
                'losing_positions': len([pos for pos in open_positions if pos.unrealized_pnl < 0]),
                'positions_by_symbol': {}
            }

            # 심볼별 포지션 정보
            for symbol in summary['symbols']:
                symbol_positions = [pos for pos in open_positions if pos.symbol == symbol]
                summary['positions_by_symbol'][symbol] = {
                    'count': len(symbol_positions),
                    'total_quantity': sum(pos.quantity for pos in symbol_positions),
                    'avg_entry_price': sum(pos.entry_price * pos.quantity for pos in symbol_positions) /
                                     sum(pos.quantity for pos in symbol_positions) if symbol_positions else 0,
                    'unrealized_pnl': sum(pos.unrealized_pnl for pos in symbol_positions)
                }

            return summary

    def cleanup(self):
        """리소스 정리"""
        try:
            with self._lock:
                self.positions.clear()
                self.closed_positions.clear()
            self.logger.info("PositionManager 리소스 정리 완료")
        except Exception as e:
            self.logger.error(f"리소스 정리 실패: {e}")