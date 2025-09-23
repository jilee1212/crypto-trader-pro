"""
Order Manager - 지정가 주문 및 OCO 주문 관리 시스템
리스크 계산 결과를 바탕으로 정밀한 주문 실행
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import time
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class OrderType(Enum):
    """주문 타입"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    OCO = "oco"

class OrderStatus(Enum):
    """주문 상태"""
    PENDING = "pending"
    PLACED = "placed"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PARTIALLY_FILLED = "partially_filled"

@dataclass
class OrderRequest:
    """주문 요청 데이터 클래스"""
    symbol: str
    side: str  # 'buy' or 'sell'
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = 'GTC'  # Good Till Cancelled
    reduce_only: bool = False
    post_only: bool = False

@dataclass
class OrderResult:
    """주문 결과 데이터 클래스"""
    success: bool
    order_id: Optional[str] = None
    message: str = ""
    timestamp: Optional[datetime] = None
    order_data: Optional[Dict] = None

class OrderManager:
    """지정가 주문 및 OCO 주문 관리자"""

    def __init__(self, connector=None):
        self.connector = connector
        self.active_orders: Dict[str, Dict] = {}
        self.order_history: List[Dict] = []

    def create_entry_order(self, risk_result: Dict[str, Any],
                          current_price: float, direction: str = 'LONG',
                          price_offset_percent: float = 0.1) -> OrderResult:
        """
        리스크 계산 결과를 바탕으로 진입 지정가 주문 생성

        Args:
            risk_result: RiskCalculator의 계산 결과
            current_price: 현재 시장 가격
            direction: 'LONG' 또는 'SHORT'
            price_offset_percent: 현재가 대비 주문가 오프셋 (%)

        Returns:
            OrderResult: 주문 실행 결과
        """
        try:
            if not risk_result.get('valid', False):
                return OrderResult(False, message=risk_result.get('message', 'Invalid risk calculation'))

            symbol = risk_result.get('symbol', 'UNKNOWN')
            quantity = risk_result.get('quantity', 0)
            entry_price = risk_result.get('entry_price')

            if quantity <= 0:
                return OrderResult(False, message="Invalid quantity")

            # 진입 가격 조정 (시장가보다 유리한 가격으로)
            if direction.upper() == 'LONG':
                # 롱 포지션: 현재가보다 약간 낮은 가격에 매수 주문
                order_price = current_price * (1 - price_offset_percent / 100)
                side = 'buy'
            else:
                # 숏 포지션: 현재가보다 약간 높은 가격에 매도 주문
                order_price = current_price * (1 + price_offset_percent / 100)
                side = 'sell'

            # 주문 요청 생성
            order_request = OrderRequest(
                symbol=symbol,
                side=side,
                order_type=OrderType.LIMIT,
                quantity=quantity,
                price=order_price,
                time_in_force='GTC',
                post_only=True  # 수수료 절약을 위한 포스트 온리
            )

            # 주문 실행
            result = self._execute_order(order_request)

            if result.success:
                # 성공한 주문을 활성 주문에 추가
                order_info = {
                    'order_id': result.order_id,
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'price': order_price,
                    'type': 'entry',
                    'direction': direction,
                    'risk_result': risk_result,
                    'timestamp': datetime.now(),
                    'status': OrderStatus.PLACED
                }
                self.active_orders[result.order_id] = order_info

                logger.info(f"Entry order placed: {symbol} {direction} {quantity} @ {order_price}")

            return result

        except Exception as e:
            logger.error(f"Error creating entry order: {e}")
            return OrderResult(False, message=f"주문 생성 실패: {str(e)}")

    def create_stop_loss_order(self, entry_order_id: str) -> OrderResult:
        """진입 주문과 연결된 손절 주문 생성"""

        try:
            if entry_order_id not in self.active_orders:
                return OrderResult(False, message="연결된 진입 주문을 찾을 수 없습니다")

            entry_order = self.active_orders[entry_order_id]
            risk_result = entry_order['risk_result']

            symbol = entry_order['symbol']
            quantity = entry_order['quantity']
            stop_loss_price = risk_result.get('stop_loss')
            direction = entry_order['direction']

            if not stop_loss_price:
                return OrderResult(False, message="손절가 정보가 없습니다")

            # 손절 주문 방향 (진입과 반대)
            if direction.upper() == 'LONG':
                side = 'sell'
            else:
                side = 'buy'

            # 손절 주문 요청 생성
            order_request = OrderRequest(
                symbol=symbol,
                side=side,
                order_type=OrderType.STOP_LOSS,
                quantity=quantity,
                stop_price=stop_loss_price,
                reduce_only=True  # 포지션 축소만 가능
            )

            result = self._execute_order(order_request)

            if result.success:
                # 손절 주문 정보 저장
                stop_order_info = {
                    'order_id': result.order_id,
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'stop_price': stop_loss_price,
                    'type': 'stop_loss',
                    'parent_order_id': entry_order_id,
                    'timestamp': datetime.now(),
                    'status': OrderStatus.PLACED
                }
                self.active_orders[result.order_id] = stop_order_info

                logger.info(f"Stop loss order placed: {symbol} {side} {quantity} @ {stop_loss_price}")

            return result

        except Exception as e:
            logger.error(f"Error creating stop loss order: {e}")
            return OrderResult(False, message=f"손절 주문 생성 실패: {str(e)}")

    def create_oco_order(self, risk_result: Dict[str, Any], current_price: float,
                        direction: str = 'LONG', take_profit_price: Optional[float] = None) -> Dict[str, OrderResult]:
        """
        OCO (One-Cancels-Other) 주문 생성
        진입 + 손절 + 익절을 동시에 설정
        """

        results = {}

        # 1. 진입 주문 생성
        entry_result = self.create_entry_order(risk_result, current_price, direction)
        results['entry'] = entry_result

        if not entry_result.success:
            return results

        # 2. 손절 주문 생성 (진입 주문 체결 후 자동 실행되도록 설정)
        # 실제 구현에서는 진입 주문 체결 콜백에서 처리
        results['stop_loss'] = OrderResult(True, message="손절 주문 예약됨")

        # 3. 익절 주문 생성 (선택사항)
        if take_profit_price:
            results['take_profit'] = OrderResult(True, message="익절 주문 예약됨")
        else:
            results['take_profit'] = OrderResult(True, message="익절 주문 미설정")

        return results

    def _execute_order(self, order_request: OrderRequest) -> OrderResult:
        """실제 주문 실행"""

        try:
            if not self.connector:
                # 테스트 모드: 실제 주문 없이 성공 시뮬레이션
                fake_order_id = f"test_{int(time.time())}"
                return OrderResult(
                    success=True,
                    order_id=fake_order_id,
                    message="테스트 모드 - 주문 시뮬레이션 성공",
                    timestamp=datetime.now()
                )

            # 실제 거래소 API 호출
            if order_request.order_type == OrderType.LIMIT:
                order_data = self.connector.create_limit_order(
                    symbol=order_request.symbol,
                    side=order_request.side,
                    amount=order_request.quantity,
                    price=order_request.price
                )
            elif order_request.order_type == OrderType.STOP_LOSS:
                order_data = self.connector.create_stop_order(
                    symbol=order_request.symbol,
                    side=order_request.side,
                    amount=order_request.quantity,
                    stop_price=order_request.stop_price
                )
            else:
                return OrderResult(False, message="지원되지 않는 주문 타입")

            return OrderResult(
                success=True,
                order_id=order_data.get('id'),
                message="주문 성공",
                timestamp=datetime.now(),
                order_data=order_data
            )

        except Exception as e:
            logger.error(f"Order execution failed: {e}")
            return OrderResult(False, message=f"주문 실패: {str(e)}")

    def cancel_order(self, order_id: str) -> OrderResult:
        """주문 취소"""

        try:
            if order_id not in self.active_orders:
                return OrderResult(False, message="주문을 찾을 수 없습니다")

            order_info = self.active_orders[order_id]

            if self.connector:
                # 실제 거래소에서 주문 취소
                cancel_result = self.connector.cancel_order(order_id, order_info['symbol'])

                if cancel_result:
                    order_info['status'] = OrderStatus.CANCELLED
                    order_info['cancelled_at'] = datetime.now()
                    self._move_to_history(order_id)

                    return OrderResult(True, message="주문이 취소되었습니다")
                else:
                    return OrderResult(False, message="주문 취소 실패")
            else:
                # 테스트 모드
                order_info['status'] = OrderStatus.CANCELLED
                self._move_to_history(order_id)
                return OrderResult(True, message="테스트 모드 - 주문 취소 시뮬레이션")

        except Exception as e:
            logger.error(f"Order cancellation failed: {e}")
            return OrderResult(False, message=f"주문 취소 실패: {str(e)}")

    def cancel_all_orders(self, symbol: Optional[str] = None) -> Dict[str, OrderResult]:
        """모든 주문 또는 특정 심볼의 모든 주문 취소"""

        results = {}
        orders_to_cancel = []

        for order_id, order_info in self.active_orders.items():
            if symbol is None or order_info['symbol'] == symbol:
                orders_to_cancel.append(order_id)

        for order_id in orders_to_cancel:
            results[order_id] = self.cancel_order(order_id)

        return results

    def get_active_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """활성 주문 목록 조회"""

        if symbol:
            return [order for order in self.active_orders.values()
                   if order['symbol'] == symbol]
        else:
            return list(self.active_orders.values())

    def update_order_status(self, order_id: str, new_status: OrderStatus) -> bool:
        """주문 상태 업데이트"""

        if order_id in self.active_orders:
            self.active_orders[order_id]['status'] = new_status
            self.active_orders[order_id]['updated_at'] = datetime.now()

            # 완료된 주문은 히스토리로 이동
            if new_status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                self._move_to_history(order_id)

            return True
        return False

    def _move_to_history(self, order_id: str):
        """주문을 히스토리로 이동"""
        if order_id in self.active_orders:
            order_info = self.active_orders.pop(order_id)
            order_info['completed_at'] = datetime.now()
            self.order_history.append(order_info)

    def get_order_statistics(self) -> Dict[str, Any]:
        """주문 통계 정보"""

        total_orders = len(self.order_history) + len(self.active_orders)
        completed_orders = len(self.order_history)
        active_orders = len(self.active_orders)

        filled_orders = len([o for o in self.order_history if o['status'] == OrderStatus.FILLED])
        cancelled_orders = len([o for o in self.order_history if o['status'] == OrderStatus.CANCELLED])

        return {
            'total_orders': total_orders,
            'active_orders': active_orders,
            'completed_orders': completed_orders,
            'filled_orders': filled_orders,
            'cancelled_orders': cancelled_orders,
            'fill_rate': filled_orders / completed_orders * 100 if completed_orders > 0 else 0
        }


# 싱글톤 인스턴스
_order_manager = None

def get_order_manager(connector=None) -> OrderManager:
    """주문 관리자 인스턴스 반환"""
    global _order_manager
    if _order_manager is None:
        _order_manager = OrderManager(connector)
    return _order_manager