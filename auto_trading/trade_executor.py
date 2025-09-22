"""
⚡ TradeExecutor - 거래 실행기

자동매매 신호를 실제 거래로 실행하는 컴포넌트
- 거래소 API 연동
- 주문 실행 및 관리
- 포지션 추적
- 실행 결과 검증
"""

import time
import ccxt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
from dataclasses import dataclass
from enum import Enum
import asyncio

from .signal_generator import TradingSignal, SignalType

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class OrderStatus(Enum):
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELED = "canceled"
    FAILED = "failed"

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

@dataclass
class OrderRequest:
    symbol: str
    side: OrderSide
    order_type: OrderType
    amount: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    signal_id: Optional[int] = None
    metadata: Dict[str, Any] = None

@dataclass
class OrderResult:
    order_id: str
    symbol: str
    side: OrderSide
    amount: float
    filled_amount: float
    price: float
    average_price: float
    status: OrderStatus
    fees: float
    timestamp: datetime
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class ExecutionReport:
    signal_id: Optional[int]
    order_results: List[OrderResult]
    total_executed: float
    average_price: float
    total_fees: float
    execution_time: float
    success: bool
    error_message: Optional[str] = None

class TradeExecutor:
    """
    ⚡ 거래 실행기

    기능:
    - 신호를 실제 주문으로 변환
    - 거래소 API 연동
    - 주문 상태 추적
    - 실행 결과 검증
    """

    def __init__(self, config_manager):
        """거래 실행기 초기화"""
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager

        # 설정 로드
        self.config = config_manager.get_config()
        self.exchange_config = self.config.get('exchange', {})
        self.is_paper_trading = config_manager.is_paper_trading()

        # 거래소 연결
        self.exchange = None
        self._initialize_exchange()

        # 주문 추적
        self.active_orders = {}
        self.execution_history = []

        # 성능 지표
        self.total_executed_orders = 0
        self.successful_executions = 0
        self.total_fees_paid = 0

        # 실행 제한
        self.max_retries = 3
        self.retry_delay = 1  # seconds

        self.logger.info(f"TradeExecutor 초기화 완료 (페이퍼 트레이딩: {self.is_paper_trading})")

    def _initialize_exchange(self):
        """거래소 API 초기화"""
        try:
            exchange_name = self.exchange_config.get('name', 'binance')
            testnet = self.exchange_config.get('testnet', True)

            if exchange_name.lower() == 'binance':
                if self.is_paper_trading:
                    # 페이퍼 트레이딩용 설정
                    self.exchange = ccxt.binance({
                        'apiKey': '',
                        'secret': '',
                        'sandbox': True,
                        'rateLimit': self.exchange_config.get('rate_limit', 1200),
                        'timeout': self.exchange_config.get('timeout', 30000),
                        'enableRateLimit': True,
                    })
                else:
                    # 실제 거래용 설정 (API 키 필요)
                    self.exchange = ccxt.binance({
                        'apiKey': '',  # 실제 구현 시 환경변수에서 로드
                        'secret': '',  # 실제 구현 시 환경변수에서 로드
                        'sandbox': testnet,
                        'rateLimit': self.exchange_config.get('rate_limit', 1200),
                        'timeout': self.exchange_config.get('timeout', 30000),
                        'enableRateLimit': True,
                    })

            # 마켓 로드
            if not self.is_paper_trading:
                self.exchange.load_markets()

            self.logger.info(f"거래소 연결 성공: {exchange_name}")

        except Exception as e:
            self.logger.error(f"거래소 초기화 실패: {e}")
            self.exchange = None

    def test_connection(self) -> bool:
        """거래소 연결 테스트"""
        try:
            if self.is_paper_trading:
                # 페이퍼 트레이딩에서는 항상 성공
                return True

            if not self.exchange:
                return False

            # 계좌 정보 조회로 연결 테스트
            balance = self.exchange.fetch_balance()
            return balance is not None

        except Exception as e:
            self.logger.error(f"거래소 연결 테스트 실패: {e}")
            return False

    async def execute_signal(self, signal: TradingSignal) -> ExecutionReport:
        """
        거래 신호 실행

        Args:
            signal: 실행할 거래 신호

        Returns:
            ExecutionReport: 실행 결과
        """
        start_time = time.time()

        try:
            self.logger.info(f"신호 실행 시작: {signal.symbol} {signal.signal_type.value}")

            # 신호 유효성 재검증
            if not self._validate_signal_for_execution(signal):
                return ExecutionReport(
                    signal_id=getattr(signal, 'id', None),
                    order_results=[],
                    total_executed=0,
                    average_price=0,
                    total_fees=0,
                    execution_time=time.time() - start_time,
                    success=False,
                    error_message="신호 유효성 검증 실패"
                )

            # 포지션 크기 계산
            position_size = await self._calculate_position_size(signal)
            if position_size <= 0:
                return ExecutionReport(
                    signal_id=getattr(signal, 'id', None),
                    order_results=[],
                    total_executed=0,
                    average_price=0,
                    total_fees=0,
                    execution_time=time.time() - start_time,
                    success=False,
                    error_message="포지션 크기 계산 실패"
                )

            # 주문 요청 생성
            order_request = self._create_order_request(signal, position_size)

            # 주문 실행
            order_result = await self._execute_order(order_request)

            # 스탑로스/테이크프로핏 주문 생성
            stop_orders = []
            if order_result.success and signal.stop_loss:
                stop_order = await self._place_stop_loss_order(signal, order_result)
                if stop_order:
                    stop_orders.append(stop_order)

            if order_result.success and signal.take_profit:
                tp_order = await self._place_take_profit_order(signal, order_result)
                if tp_order:
                    stop_orders.append(tp_order)

            # 실행 보고서 생성
            all_orders = [order_result] + stop_orders
            execution_report = ExecutionReport(
                signal_id=getattr(signal, 'id', None),
                order_results=all_orders,
                total_executed=order_result.filled_amount,
                average_price=order_result.average_price,
                total_fees=sum(order.fees for order in all_orders),
                execution_time=time.time() - start_time,
                success=order_result.status == OrderStatus.CLOSED,
                error_message=order_result.error_message
            )

            # 통계 업데이트
            self.total_executed_orders += 1
            if execution_report.success:
                self.successful_executions += 1
                self.total_fees_paid += execution_report.total_fees

            # 실행 기록 저장
            self.execution_history.append(execution_report)

            self.logger.info(f"신호 실행 완료: {'성공' if execution_report.success else '실패'}")
            return execution_report

        except Exception as e:
            self.logger.error(f"신호 실행 중 오류: {e}")
            return ExecutionReport(
                signal_id=getattr(signal, 'id', None),
                order_results=[],
                total_executed=0,
                average_price=0,
                total_fees=0,
                execution_time=time.time() - start_time,
                success=False,
                error_message=str(e)
            )

    def _validate_signal_for_execution(self, signal: TradingSignal) -> bool:
        """실행을 위한 신호 유효성 검증"""
        try:
            # 기본 검증
            if signal.signal_type == SignalType.HOLD:
                return False

            if signal.entry_price <= 0:
                return False

            # 심볼 검증
            if not self._is_symbol_supported(signal.symbol):
                self.logger.error(f"지원하지 않는 심볼: {signal.symbol}")
                return False

            # 최소 주문 금액 확인
            min_amount = self._get_min_order_amount(signal.symbol)
            if signal.position_size and signal.position_size < min_amount:
                self.logger.error(f"최소 주문 금액 미달: {signal.position_size} < {min_amount}")
                return False

            return True

        except Exception as e:
            self.logger.error(f"신호 검증 실패: {e}")
            return False

    async def _calculate_position_size(self, signal: TradingSignal) -> float:
        """포지션 크기 계산"""
        try:
            # 신호에 이미 포지션 크기가 있으면 사용
            if signal.position_size and signal.position_size > 0:
                return signal.position_size

            # 계좌 잔고 기반 계산
            if self.is_paper_trading:
                # 페이퍼 트레이딩용 시뮬레이션
                account_balance = 10000  # $10,000 시뮬레이션 잔고
            else:
                account_balance = await self._get_account_balance()

            if account_balance <= 0:
                return 0

            # 리스크 관리 설정에 따른 포지션 크기
            risk_config = self.config_manager.get_risk_limits()
            position_size_pct = risk_config.get('position_size', 2.0) / 100

            # 최대 포지션 크기 계산
            max_position_value = account_balance * position_size_pct

            # 주문 수량 계산 (가격 기준)
            position_size = max_position_value / signal.entry_price

            # 최소/최대 제한 적용
            min_size = self._get_min_order_amount(signal.symbol)
            max_size = self._get_max_order_amount(signal.symbol)

            position_size = max(min_size, min(position_size, max_size))

            self.logger.debug(f"포지션 크기 계산: {position_size} {signal.symbol}")
            return position_size

        except Exception as e:
            self.logger.error(f"포지션 크기 계산 실패: {e}")
            return 0

    def _create_order_request(self, signal: TradingSignal, position_size: float) -> OrderRequest:
        """주문 요청 생성"""
        side = OrderSide.BUY if signal.signal_type == SignalType.BUY else OrderSide.SELL

        return OrderRequest(
            symbol=signal.symbol,
            side=side,
            order_type=OrderType.MARKET,  # 기본적으로 시장가 주문
            amount=position_size,
            price=signal.entry_price,
            signal_id=getattr(signal, 'id', None),
            metadata={
                'confidence': signal.confidence,
                'reasoning': signal.reasoning,
                'timestamp': signal.timestamp.isoformat()
            }
        )

    async def _execute_order(self, order_request: OrderRequest) -> OrderResult:
        """주문 실행"""
        for attempt in range(self.max_retries):
            try:
                if self.is_paper_trading:
                    return await self._execute_paper_order(order_request)
                else:
                    return await self._execute_real_order(order_request)

            except Exception as e:
                self.logger.warning(f"주문 실행 시도 {attempt + 1} 실패: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    return OrderResult(
                        order_id="",
                        symbol=order_request.symbol,
                        side=order_request.side,
                        amount=order_request.amount,
                        filled_amount=0,
                        price=order_request.price or 0,
                        average_price=0,
                        status=OrderStatus.FAILED,
                        fees=0,
                        timestamp=datetime.now(),
                        error_message=str(e)
                    )

    async def _execute_paper_order(self, order_request: OrderRequest) -> OrderResult:
        """페이퍼 트레이딩 주문 실행"""
        try:
            # 시뮬레이션된 주문 실행
            order_id = f"paper_{int(time.time() * 1000)}"

            # 시뮬레이션된 실행 가격 (약간의 슬리피지 적용)
            slippage = 0.001  # 0.1%
            if order_request.side == OrderSide.BUY:
                execution_price = order_request.price * (1 + slippage)
            else:
                execution_price = order_request.price * (1 - slippage)

            # 시뮬레이션된 수수료
            fee_rate = 0.001  # 0.1%
            fees = order_request.amount * execution_price * fee_rate

            # 약간의 지연 시뮬레이션
            await asyncio.sleep(0.1)

            return OrderResult(
                order_id=order_id,
                symbol=order_request.symbol,
                side=order_request.side,
                amount=order_request.amount,
                filled_amount=order_request.amount,  # 완전 체결
                price=execution_price,
                average_price=execution_price,
                status=OrderStatus.CLOSED,
                fees=fees,
                timestamp=datetime.now(),
                metadata=order_request.metadata
            )

        except Exception as e:
            self.logger.error(f"페이퍼 주문 실행 실패: {e}")
            raise

    async def _execute_real_order(self, order_request: OrderRequest) -> OrderResult:
        """실제 주문 실행"""
        try:
            if not self.exchange:
                raise Exception("거래소 연결이 없습니다")

            # 실제 주문 실행
            order = self.exchange.create_order(
                symbol=order_request.symbol,
                type=order_request.order_type.value,
                side=order_request.side.value,
                amount=order_request.amount,
                price=order_request.price
            )

            # 주문 상태 확인
            filled_order = self.exchange.fetch_order(order['id'], order_request.symbol)

            return OrderResult(
                order_id=order['id'],
                symbol=order_request.symbol,
                side=order_request.side,
                amount=order_request.amount,
                filled_amount=filled_order.get('filled', 0),
                price=order_request.price or 0,
                average_price=filled_order.get('average', 0),
                status=self._convert_order_status(filled_order.get('status')),
                fees=filled_order.get('fee', {}).get('cost', 0),
                timestamp=datetime.now(),
                metadata=order_request.metadata
            )

        except Exception as e:
            self.logger.error(f"실제 주문 실행 실패: {e}")
            raise

    async def _place_stop_loss_order(self, signal: TradingSignal,
                                   main_order: OrderResult) -> Optional[OrderResult]:
        """손절 주문 배치"""
        try:
            if not signal.stop_loss or main_order.filled_amount <= 0:
                return None

            # 손절 주문 생성
            stop_side = OrderSide.SELL if signal.signal_type == SignalType.BUY else OrderSide.BUY

            if self.is_paper_trading:
                # 페이퍼 트레이딩에서는 주문 생성만 기록
                return OrderResult(
                    order_id=f"stop_{int(time.time() * 1000)}",
                    symbol=signal.symbol,
                    side=stop_side,
                    amount=main_order.filled_amount,
                    filled_amount=0,
                    price=signal.stop_loss,
                    average_price=0,
                    status=OrderStatus.OPEN,
                    fees=0,
                    timestamp=datetime.now(),
                    metadata={'order_type': 'stop_loss'}
                )

            # 실제 손절 주문 (구현 필요)
            # stop_order = self.exchange.create_stop_order(...)

            return None

        except Exception as e:
            self.logger.error(f"손절 주문 배치 실패: {e}")
            return None

    async def _place_take_profit_order(self, signal: TradingSignal,
                                     main_order: OrderResult) -> Optional[OrderResult]:
        """익절 주문 배치"""
        try:
            if not signal.take_profit or main_order.filled_amount <= 0:
                return None

            # 익절 주문 생성
            tp_side = OrderSide.SELL if signal.signal_type == SignalType.BUY else OrderSide.BUY

            if self.is_paper_trading:
                # 페이퍼 트레이딩에서는 주문 생성만 기록
                return OrderResult(
                    order_id=f"tp_{int(time.time() * 1000)}",
                    symbol=signal.symbol,
                    side=tp_side,
                    amount=main_order.filled_amount,
                    filled_amount=0,
                    price=signal.take_profit,
                    average_price=0,
                    status=OrderStatus.OPEN,
                    fees=0,
                    timestamp=datetime.now(),
                    metadata={'order_type': 'take_profit'}
                )

            # 실제 익절 주문 (구현 필요)
            # tp_order = self.exchange.create_limit_order(...)

            return None

        except Exception as e:
            self.logger.error(f"익절 주문 배치 실패: {e}")
            return None

    def _convert_order_status(self, exchange_status: str) -> OrderStatus:
        """거래소 주문 상태를 내부 상태로 변환"""
        status_map = {
            'open': OrderStatus.OPEN,
            'closed': OrderStatus.CLOSED,
            'canceled': OrderStatus.CANCELED,
            'pending': OrderStatus.PENDING
        }
        return status_map.get(exchange_status, OrderStatus.FAILED)

    async def _get_account_balance(self) -> float:
        """계좌 잔고 조회"""
        try:
            if self.is_paper_trading:
                return 10000  # 시뮬레이션 잔고

            if not self.exchange:
                return 0

            balance = self.exchange.fetch_balance()
            return balance.get('USDT', {}).get('free', 0)

        except Exception as e:
            self.logger.error(f"잔고 조회 실패: {e}")
            return 0

    def _is_symbol_supported(self, symbol: str) -> bool:
        """심볼 지원 여부 확인"""
        try:
            if self.is_paper_trading:
                # 페이퍼 트레이딩에서는 모든 심볼 지원
                return True

            if not self.exchange or not hasattr(self.exchange, 'markets'):
                return False

            return symbol in self.exchange.markets

        except Exception:
            return False

    def _get_min_order_amount(self, symbol: str) -> float:
        """최소 주문 수량 조회"""
        try:
            if self.is_paper_trading:
                return 0.001  # 시뮬레이션 최소값

            if not self.exchange or not hasattr(self.exchange, 'markets'):
                return 0.001

            market = self.exchange.markets.get(symbol, {})
            return market.get('limits', {}).get('amount', {}).get('min', 0.001)

        except Exception:
            return 0.001

    def _get_max_order_amount(self, symbol: str) -> float:
        """최대 주문 수량 조회"""
        try:
            if self.is_paper_trading:
                return 1000000  # 시뮬레이션 최대값

            if not self.exchange or not hasattr(self.exchange, 'markets'):
                return 1000000

            market = self.exchange.markets.get(symbol, {})
            return market.get('limits', {}).get('amount', {}).get('max', 1000000)

        except Exception:
            return 1000000

    def get_execution_statistics(self) -> Dict[str, Any]:
        """실행 통계 조회"""
        success_rate = 0
        if self.total_executed_orders > 0:
            success_rate = (self.successful_executions / self.total_executed_orders) * 100

        return {
            'total_orders': self.total_executed_orders,
            'successful_executions': self.successful_executions,
            'success_rate': success_rate,
            'total_fees_paid': self.total_fees_paid,
            'average_execution_time': self._calculate_avg_execution_time(),
            'paper_trading': self.is_paper_trading
        }

    def _calculate_avg_execution_time(self) -> float:
        """평균 실행 시간 계산"""
        if not self.execution_history:
            return 0.0

        execution_times = [report.execution_time for report in self.execution_history[-100:]]
        return sum(execution_times) / len(execution_times)

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """주문 취소"""
        try:
            if self.is_paper_trading:
                # 페이퍼 트레이딩에서는 시뮬레이션
                if order_id in self.active_orders:
                    del self.active_orders[order_id]
                return True

            if not self.exchange:
                return False

            self.exchange.cancel_order(order_id, symbol)
            return True

        except Exception as e:
            self.logger.error(f"주문 취소 실패: {e}")
            return False

    def get_order_status(self, order_id: str, symbol: str) -> Optional[OrderResult]:
        """주문 상태 조회"""
        try:
            if self.is_paper_trading:
                # 페이퍼 트레이딩에서는 캐시된 정보 반환
                return self.active_orders.get(order_id)

            if not self.exchange:
                return None

            order = self.exchange.fetch_order(order_id, symbol)
            # OrderResult로 변환하여 반환
            # (구현 필요)

            return None

        except Exception as e:
            self.logger.error(f"주문 상태 조회 실패: {e}")
            return None

    def cleanup(self):
        """리소스 정리"""
        try:
            if self.exchange and hasattr(self.exchange, 'close'):
                self.exchange.close()
            self.logger.info("TradeExecutor 리소스 정리 완료")
        except Exception as e:
            self.logger.error(f"리소스 정리 실패: {e}")