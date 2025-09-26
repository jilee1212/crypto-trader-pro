"""
Automated Trading Engine with AI Signal Integration
AI 신호 기반 자동 거래 실행 엔진
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json

from .ai_signal_generator import AISignal, SignalType, SignalValidator
from .ai_risk_manager import AIRiskManager
from ..services.binance_futures_client import BinanceFuturesClient

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class TradeStatus(Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


@dataclass
class AutoTradeConfig:
    """자동 거래 설정"""
    enabled: bool = False
    max_concurrent_trades: int = 3
    max_daily_trades: int = 10
    default_risk_percentage: float = 2.0
    max_leverage: int = 10
    min_signal_confidence: float = 75.0
    enable_stop_loss: bool = True
    enable_take_profit: bool = True
    emergency_stop_loss_percent: float = 10.0
    max_daily_loss_percent: float = 5.0


@dataclass
class TradeOrder:
    """거래 주문 정보"""
    order_id: Optional[str]
    order_type: str  # "MARKET", "LIMIT", "STOP_MARKET"
    side: str  # "BUY", "SELL"
    symbol: str
    quantity: float
    price: Optional[float]
    status: OrderStatus
    filled_qty: float = 0.0
    avg_price: float = 0.0
    created_time: datetime = None
    filled_time: Optional[datetime] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.created_time is None:
            self.created_time = datetime.now()


@dataclass
class ActiveTrade:
    """활성 거래 정보"""
    trade_id: str
    symbol: str
    signal: AISignal
    position_size: float
    leverage: int
    entry_order: TradeOrder
    stop_loss_order: Optional[TradeOrder] = None
    take_profit_order: Optional[TradeOrder] = None
    status: TradeStatus = TradeStatus.ACTIVE
    created_time: datetime = None
    closed_time: Optional[datetime] = None
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    max_profit: float = 0.0
    max_drawdown: float = 0.0

    def __post_init__(self):
        if self.created_time is None:
            self.created_time = datetime.now()
        if not self.trade_id:
            self.trade_id = f"{self.symbol}_{int(self.created_time.timestamp())}"


@dataclass
class TradingStats:
    """거래 통계"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_profit: float = 0.0
    total_loss: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    daily_pnl: float = 0.0
    daily_trades: int = 0
    last_reset_date: datetime = None

    def __post_init__(self):
        if self.last_reset_date is None:
            self.last_reset_date = datetime.now().date()


class AutoTradingEngine:
    """자동 거래 엔진"""

    def __init__(self, binance_client: BinanceFuturesClient):
        self.binance_client = binance_client
        self.config = AutoTradeConfig()
        self.signal_validator = SignalValidator()
        self.risk_manager = None  # Will be initialized with account balance

        # 거래 상태 관리
        self.active_trades: Dict[str, ActiveTrade] = {}
        self.trade_history: List[ActiveTrade] = []
        self.stats = TradingStats()

        # 안전 장치
        self.emergency_stop = False
        self.last_error_time = None
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5

        # 비동기 작업 관리
        self.monitoring_task = None
        self.is_running = False

    async def initialize(self):
        """엔진 초기화"""
        try:
            # 계좌 정보 조회
            account_info = await self.binance_client.get_account_info()
            total_balance = float(account_info.get('totalWalletBalance', 1000))

            # 리스크 관리자 초기화
            self.risk_manager = AIRiskManager(
                account_balance=total_balance,
                risk_percentage=self.config.default_risk_percentage
            )

            logger.info(f"Auto trading engine initialized with balance: {total_balance} USDT")
            return True

        except Exception as e:
            logger.error(f"Engine initialization failed: {e}")
            return False

    def update_config(self, new_config: Dict):
        """설정 업데이트"""
        for key, value in new_config.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        logger.info("Auto trading config updated")

    def enable_trading(self):
        """자동 거래 활성화"""
        self.config.enabled = True
        self.emergency_stop = False
        logger.info("Auto trading enabled")

    def disable_trading(self):
        """자동 거래 비활성화"""
        self.config.enabled = False
        logger.info("Auto trading disabled")

    def emergency_stop_all(self):
        """긴급 정지"""
        self.emergency_stop = True
        self.config.enabled = False
        logger.critical("Emergency stop activated!")

    async def process_signal(self, signal: AISignal) -> Dict:
        """AI 신호 처리"""
        try:
            # 기본 검증
            if not self._can_process_signal(signal):
                return {"success": False, "reason": "Signal validation failed"}

            # 신호 검증
            is_valid, warnings = self.signal_validator.validate_signal(signal)
            if not is_valid:
                return {"success": False, "reason": f"Signal invalid: {warnings}"}

            # 포지션 크기 계산
            position_calculation = self.risk_manager.calculate_position_size(
                entry_price=signal.entry_price,
                stop_loss_price=signal.stop_loss
            )

            # 거래 실행
            result = await self._execute_trade(signal, position_calculation)

            return result

        except Exception as e:
            logger.error(f"Signal processing error: {e}")
            return {"success": False, "reason": str(e)}

    def _can_process_signal(self, signal: AISignal) -> bool:
        """신호 처리 가능 여부 확인"""
        # 자동 거래 비활성화
        if not self.config.enabled or self.emergency_stop:
            return False

        # 신뢰도 확인
        if signal.confidence < self.config.min_signal_confidence:
            return False

        # 동시 거래 수 제한
        if len(self.active_trades) >= self.config.max_concurrent_trades:
            return False

        # 일일 거래 수 제한
        if self._get_daily_trade_count() >= self.config.max_daily_trades:
            return False

        # 일일 손실 제한
        if abs(self.stats.daily_pnl) >= (self.risk_manager.account_balance *
                                       self.config.max_daily_loss_percent / 100):
            return False

        # 동일 심볼 중복 거래 확인
        for trade in self.active_trades.values():
            if trade.symbol == signal.symbol:
                return False

        # 신호 유효성 확인
        if signal.valid_until < datetime.now():
            return False

        return True

    async def _execute_trade(self, signal: AISignal, position_calc: Dict) -> Dict:
        """거래 실행"""
        try:
            symbol = signal.symbol
            side = "BUY" if signal.signal_type == SignalType.LONG else "SELL"
            quantity = position_calc["position_quantity"]
            leverage = position_calc["leverage"]

            # 레버리지 설정
            await self.binance_client.set_leverage(symbol, leverage)

            # 마켓 주문 실행
            entry_order_result = await self.binance_client.place_order(
                symbol=symbol,
                side=side,
                order_type="MARKET",
                quantity=quantity
            )

            if entry_order_result.get("status") != "FILLED":
                return {"success": False, "reason": "Entry order failed"}

            # 주문 정보 생성
            entry_order = TradeOrder(
                order_id=entry_order_result.get("orderId"),
                order_type="MARKET",
                side=side,
                symbol=symbol,
                quantity=quantity,
                price=None,
                status=OrderStatus.FILLED,
                filled_qty=float(entry_order_result.get("executedQty", 0)),
                avg_price=float(entry_order_result.get("avgPrice", 0))
            )

            # 활성 거래 생성
            trade = ActiveTrade(
                trade_id="",  # Will be auto-generated
                symbol=symbol,
                signal=signal,
                position_size=quantity,
                leverage=leverage,
                entry_order=entry_order
            )

            # 손절/익절 주문 설정
            if self.config.enable_stop_loss:
                await self._set_stop_loss_order(trade)

            if self.config.enable_take_profit and signal.take_profit:
                await self._set_take_profit_order(trade)

            # 활성 거래에 추가
            self.active_trades[trade.trade_id] = trade

            # 통계 업데이트
            self._update_trading_stats(trade, "opened")

            logger.info(f"Trade executed: {trade.trade_id} - {signal.signal_type.value} {symbol}")

            return {
                "success": True,
                "trade_id": trade.trade_id,
                "entry_order": asdict(entry_order),
                "position_calculation": position_calc
            }

        except Exception as e:
            logger.error(f"Trade execution error: {e}")
            return {"success": False, "reason": str(e)}

    async def _set_stop_loss_order(self, trade: ActiveTrade):
        """손절 주문 설정"""
        try:
            symbol = trade.symbol
            signal = trade.signal
            opposite_side = "SELL" if trade.entry_order.side == "BUY" else "BUY"

            stop_order_result = await self.binance_client.place_order(
                symbol=symbol,
                side=opposite_side,
                order_type="STOP_MARKET",
                quantity=trade.position_size,
                stop_price=signal.stop_loss
            )

            trade.stop_loss_order = TradeOrder(
                order_id=stop_order_result.get("orderId"),
                order_type="STOP_MARKET",
                side=opposite_side,
                symbol=symbol,
                quantity=trade.position_size,
                price=signal.stop_loss,
                status=OrderStatus.PENDING
            )

            logger.info(f"Stop loss order set for {trade.trade_id}")

        except Exception as e:
            logger.error(f"Stop loss order error for {trade.trade_id}: {e}")

    async def _set_take_profit_order(self, trade: ActiveTrade):
        """익절 주문 설정"""
        try:
            symbol = trade.symbol
            signal = trade.signal
            opposite_side = "SELL" if trade.entry_order.side == "BUY" else "BUY"

            if not signal.take_profit:
                return

            tp_order_result = await self.binance_client.place_order(
                symbol=symbol,
                side=opposite_side,
                order_type="LIMIT",
                quantity=trade.position_size,
                price=signal.take_profit,
                time_in_force="GTC"
            )

            trade.take_profit_order = TradeOrder(
                order_id=tp_order_result.get("orderId"),
                order_type="LIMIT",
                side=opposite_side,
                symbol=symbol,
                quantity=trade.position_size,
                price=signal.take_profit,
                status=OrderStatus.PENDING
            )

            logger.info(f"Take profit order set for {trade.trade_id}")

        except Exception as e:
            logger.error(f"Take profit order error for {trade.trade_id}: {e}")

    async def monitor_trades(self):
        """거래 모니터링"""
        while self.is_running:
            try:
                await self._check_active_trades()
                await self._update_unrealized_pnl()
                await asyncio.sleep(10)  # 10초마다 확인

            except Exception as e:
                logger.error(f"Trade monitoring error: {e}")
                await asyncio.sleep(30)

    async def _check_active_trades(self):
        """활성 거래 상태 확인"""
        for trade_id, trade in list(self.active_trades.items()):
            try:
                # 주문 상태 확인
                if trade.stop_loss_order and trade.stop_loss_order.status == OrderStatus.PENDING:
                    await self._check_order_status(trade, trade.stop_loss_order)

                if trade.take_profit_order and trade.take_profit_order.status == OrderStatus.PENDING:
                    await self._check_order_status(trade, trade.take_profit_order)

                # 거래 종료 확인
                if self._is_trade_closed(trade):
                    await self._close_trade(trade)

            except Exception as e:
                logger.error(f"Trade check error for {trade_id}: {e}")

    async def _check_order_status(self, trade: ActiveTrade, order: TradeOrder):
        """주문 상태 확인"""
        try:
            order_info = await self.binance_client.get_order_status(
                trade.symbol, order.order_id
            )

            if order_info.get("status") == "FILLED":
                order.status = OrderStatus.FILLED
                order.filled_qty = float(order_info.get("executedQty", 0))
                order.avg_price = float(order_info.get("avgPrice", 0))
                order.filled_time = datetime.now()

                logger.info(f"Order filled: {order.order_id} for trade {trade.trade_id}")

        except Exception as e:
            logger.error(f"Order status check error: {e}")

    def _is_trade_closed(self, trade: ActiveTrade) -> bool:
        """거래 종료 여부 확인"""
        # 손절 또는 익절 주문이 체결된 경우
        if (trade.stop_loss_order and trade.stop_loss_order.status == OrderStatus.FILLED or
            trade.take_profit_order and trade.take_profit_order.status == OrderStatus.FILLED):
            return True

        # 신호 유효 시간 만료
        if trade.signal.valid_until < datetime.now():
            return True

        return False

    async def _close_trade(self, trade: ActiveTrade):
        """거래 종료"""
        try:
            # 미체결 주문 취소
            if trade.stop_loss_order and trade.stop_loss_order.status == OrderStatus.PENDING:
                await self.binance_client.cancel_order(trade.symbol, trade.stop_loss_order.order_id)

            if trade.take_profit_order and trade.take_profit_order.status == OrderStatus.PENDING:
                await self.binance_client.cancel_order(trade.symbol, trade.take_profit_order.order_id)

            # 현재 포지션 확인 및 청산
            position_info = await self.binance_client.get_position_info(trade.symbol)
            if position_info and float(position_info.get("positionAmt", 0)) != 0:
                await self._close_position(trade)

            # 거래 종료 처리
            trade.status = TradeStatus.CLOSED
            trade.closed_time = datetime.now()

            # 실현 손익 계산
            await self._calculate_realized_pnl(trade)

            # 활성 거래에서 제거
            if trade.trade_id in self.active_trades:
                del self.active_trades[trade.trade_id]

            # 거래 히스토리에 추가
            self.trade_history.append(trade)

            # 통계 업데이트
            self._update_trading_stats(trade, "closed")

            logger.info(f"Trade closed: {trade.trade_id} with PnL: {trade.realized_pnl:.2f} USDT")

        except Exception as e:
            logger.error(f"Trade close error for {trade.trade_id}: {e}")

    async def _close_position(self, trade: ActiveTrade):
        """포지션 강제 청산"""
        try:
            opposite_side = "SELL" if trade.entry_order.side == "BUY" else "BUY"

            close_order_result = await self.binance_client.place_order(
                symbol=trade.symbol,
                side=opposite_side,
                order_type="MARKET",
                quantity=trade.position_size,
                reduce_only=True
            )

            logger.info(f"Position closed for trade {trade.trade_id}")

        except Exception as e:
            logger.error(f"Position close error for {trade.trade_id}: {e}")

    async def _calculate_realized_pnl(self, trade: ActiveTrade):
        """실현 손익 계산"""
        try:
            # 거래 내역에서 PnL 계산
            account_info = await self.binance_client.get_account_info()
            # 실제 구현에서는 거래 내역에서 정확한 PnL을 계산해야 함
            # 여기서는 간단한 추정치 사용
            if trade.signal.signal_type == SignalType.LONG:
                if trade.take_profit_order and trade.take_profit_order.status == OrderStatus.FILLED:
                    trade.realized_pnl = (trade.take_profit_order.avg_price - trade.entry_order.avg_price) * trade.position_size
                elif trade.stop_loss_order and trade.stop_loss_order.status == OrderStatus.FILLED:
                    trade.realized_pnl = (trade.stop_loss_order.avg_price - trade.entry_order.avg_price) * trade.position_size
            else:  # SHORT
                if trade.take_profit_order and trade.take_profit_order.status == OrderStatus.FILLED:
                    trade.realized_pnl = (trade.entry_order.avg_price - trade.take_profit_order.avg_price) * trade.position_size
                elif trade.stop_loss_order and trade.stop_loss_order.status == OrderStatus.FILLED:
                    trade.realized_pnl = (trade.entry_order.avg_price - trade.stop_loss_order.avg_price) * trade.position_size

        except Exception as e:
            logger.error(f"PnL calculation error for {trade.trade_id}: {e}")

    async def _update_unrealized_pnl(self):
        """미실현 손익 업데이트"""
        try:
            for trade in self.active_trades.values():
                # 현재 가격 조회
                ticker = await self.binance_client.get_ticker_price(trade.symbol)
                current_price = float(ticker.get("price", 0))

                if current_price > 0:
                    if trade.signal.signal_type == SignalType.LONG:
                        trade.unrealized_pnl = (current_price - trade.entry_order.avg_price) * trade.position_size
                    else:  # SHORT
                        trade.unrealized_pnl = (trade.entry_order.avg_price - current_price) * trade.position_size

                    # 최대 수익/손실 추적
                    if trade.unrealized_pnl > trade.max_profit:
                        trade.max_profit = trade.unrealized_pnl
                    if trade.unrealized_pnl < trade.max_drawdown:
                        trade.max_drawdown = trade.unrealized_pnl

        except Exception as e:
            logger.error(f"Unrealized PnL update error: {e}")

    def _update_trading_stats(self, trade: ActiveTrade, action: str):
        """거래 통계 업데이트"""
        try:
            current_date = datetime.now().date()

            # 일일 초기화
            if self.stats.last_reset_date != current_date:
                self.stats.daily_pnl = 0.0
                self.stats.daily_trades = 0
                self.stats.last_reset_date = current_date

            if action == "opened":
                self.stats.total_trades += 1
                self.stats.daily_trades += 1

            elif action == "closed":
                pnl = trade.realized_pnl
                self.stats.daily_pnl += pnl

                if pnl > 0:
                    self.stats.winning_trades += 1
                    self.stats.total_profit += pnl
                else:
                    self.stats.losing_trades += 1
                    self.stats.total_loss += abs(pnl)

                # 승률 계산
                if self.stats.total_trades > 0:
                    self.stats.win_rate = (self.stats.winning_trades / self.stats.total_trades) * 100

                # 프로핏 팩터 계산
                if self.stats.total_loss > 0:
                    self.stats.profit_factor = self.stats.total_profit / self.stats.total_loss

        except Exception as e:
            logger.error(f"Stats update error: {e}")

    def _get_daily_trade_count(self) -> int:
        """일일 거래 수 조회"""
        current_date = datetime.now().date()
        if self.stats.last_reset_date != current_date:
            return 0
        return self.stats.daily_trades

    async def start_monitoring(self):
        """모니터링 시작"""
        if not self.is_running:
            self.is_running = True
            self.monitoring_task = asyncio.create_task(self.monitor_trades())
            logger.info("Trade monitoring started")

    async def stop_monitoring(self):
        """모니터링 중지"""
        if self.is_running:
            self.is_running = False
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            logger.info("Trade monitoring stopped")

    def get_active_trades(self) -> List[Dict]:
        """활성 거래 목록 조회"""
        return [asdict(trade) for trade in self.active_trades.values()]

    def get_trading_stats(self) -> Dict:
        """거래 통계 조회"""
        return asdict(self.stats)

    def get_config(self) -> Dict:
        """설정 조회"""
        return asdict(self.config)