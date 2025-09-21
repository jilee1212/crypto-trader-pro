#!/usr/bin/env python3
"""
AI 신호 기반 실시간 거래 시스템
CoinGecko 분석 + Binance 실제 거래 연동

기능:
1. AI 신호 생성 (BUY/SELL/HOLD)
2. 신호 신뢰도에 따른 주문 크기 결정
3. 리스크 관리 적용 (ATR 기반 손절/익절)
4. 자동 주문 실행 및 포지션 관리
5. 실시간 손익 추적

안전 기능:
- 연속 손실 시 자동 중단 (3회 연속 손실)
- 일일 거래 한도 (100 USDT)
- 긴급 정지 버튼 기능
"""

import sys
import time
import json
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ai_trading_signals_coingecko import CoinGeckoConnector, EnhancedTechnicalIndicators, EnhancedATRCalculator, EnhancedRiskManager
from binance_testnet_connector import BinanceTestnetConnector

class TradingMode(Enum):
    DEMO = "demo"
    LIVE = "live"

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

@dataclass
class TradingSignal:
    symbol: str
    signal: SignalType
    confidence: float  # 0.0 ~ 1.0
    price: float
    timestamp: datetime
    indicators: Dict
    risk_metrics: Dict

@dataclass
class Position:
    symbol: str
    side: str  # 'LONG' or 'SHORT'
    quantity: float
    entry_price: float
    current_price: float
    stop_loss: float
    take_profit: float
    pnl: float
    pnl_percentage: float
    timestamp: datetime

class AILiveTradingSystem:
    """AI 신호 기반 실시간 거래 시스템"""

    def __init__(self, mode: TradingMode = TradingMode.DEMO):
        self.mode = mode
        self.coingecko = CoinGeckoConnector()
        self.binance = BinanceTestnetConnector() if mode == TradingMode.LIVE else None
        self.indicators = EnhancedTechnicalIndicators()
        self.atr_calculator = EnhancedATRCalculator()
        self.risk_manager = EnhancedRiskManager()

        # 거래 설정
        self.daily_limit = 100.0  # USDT
        self.max_consecutive_losses = 3
        self.min_confidence = 0.6
        self.position_size_base = 0.02  # 포트폴리오의 2%

        # 상태 추적
        self.current_positions = {}
        self.trading_history = []
        self.consecutive_losses = 0
        self.daily_pnl = 0.0
        self.daily_volume = 0.0
        self.emergency_stop = False

        # 로깅
        self.trading_log = []

        self.log_trade("INIT", f"AI 거래 시스템 초기화 완료 - 모드: {mode.value}")

    def log_trade(self, action: str, message: str):
        """거래 로그 기록"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'message': message
        }
        self.trading_log.append(log_entry)
        print(f"[{action}] {message}")

    def emergency_stop_trading(self):
        """긴급 정지"""
        self.emergency_stop = True
        self.log_trade("EMERGENCY", "거래 시스템 긴급 정지 활성화")

    def reset_emergency_stop(self):
        """긴급 정지 해제"""
        self.emergency_stop = False
        self.log_trade("RESET", "거래 시스템 긴급 정지 해제")

    def check_trading_limits(self) -> bool:
        """거래 한도 확인"""
        if self.emergency_stop:
            return False

        if self.consecutive_losses >= self.max_consecutive_losses:
            self.log_trade("LIMIT", f"연속 손실 한도 초과: {self.consecutive_losses}회")
            return False

        if self.daily_volume >= self.daily_limit:
            self.log_trade("LIMIT", f"일일 거래 한도 초과: ${self.daily_volume:.2f}")
            return False

        return True

    def generate_trading_signal(self, symbol: str, timeframe: str = '1day') -> Optional[TradingSignal]:
        """AI 거래 신호 생성"""
        try:
            self.log_trade("SIGNAL", f"{symbol} 신호 생성 시작")

            # 1. 시장 데이터 조회
            coingecko_symbol = symbol.lower().replace('usdt', '')
            if coingecko_symbol == 'btc':
                coingecko_symbol = 'bitcoin'
            elif coingecko_symbol == 'eth':
                coingecko_symbol = 'ethereum'
            elif coingecko_symbol == 'bnb':
                coingecko_symbol = 'binancecoin'

            data = self.coingecko.get_ohlc_data(coingecko_symbol, 100)
            if data is None or len(data) < 50:
                self.log_trade("ERROR", f"{symbol} 데이터 부족")
                return None

            # 2. 기술적 지표 계산
            data_with_indicators = self.indicators.add_all_indicators(data)
            if data_with_indicators is None or data_with_indicators.empty:
                self.log_trade("ERROR", f"{symbol} 지표 계산 실패")
                return None

            # 지표를 딕셔너리로 변환
            indicators = {}
            if 'rsi' in data_with_indicators.columns:
                indicators['rsi'] = data_with_indicators['rsi'].tolist()
            if 'macd' in data_with_indicators.columns:
                indicators['macd'] = data_with_indicators['macd'].tolist()
            if 'macd_signal' in data_with_indicators.columns:
                indicators['macd_signal'] = data_with_indicators['macd_signal'].tolist()
            if 'bb_lower' in data_with_indicators.columns:
                indicators['bb_lower'] = data_with_indicators['bb_lower'].tolist()
            if 'bb_upper' in data_with_indicators.columns:
                indicators['bb_upper'] = data_with_indicators['bb_upper'].tolist()
            if 'volume_change' in data_with_indicators.columns:
                indicators['volume_change'] = data_with_indicators['volume_change'].iloc[-1] if len(data_with_indicators) > 0 else 0

            # 3. ATR 및 리스크 메트릭 계산
            atr_result = self.atr_calculator.calculate_atr(data)
            atr_value = atr_result.get('atr', 0.02 * float(data['close'].iloc[-1]))

            risk_metrics = {
                'atr': atr_value,
                'atr_percentage': atr_value / float(data['close'].iloc[-1]) * 100,
                'volatility': float(data['close'].pct_change().std() * 100)
            }

            # 4. AI 신호 생성 로직
            signal, confidence = self._analyze_signals(data, indicators, risk_metrics)

            # 5. 현재 가격 조회
            current_price = None
            if self.mode == TradingMode.LIVE and self.binance:
                price_info = self.binance.get_current_price(symbol)
                if price_info and price_info.get('success'):
                    current_price = price_info.get('price')

            if current_price is None:
                current_price = float(data['close'].iloc[-1])

            trading_signal = TradingSignal(
                symbol=symbol,
                signal=signal,
                confidence=confidence,
                price=current_price,
                timestamp=datetime.now(),
                indicators=indicators,
                risk_metrics=risk_metrics
            )

            self.log_trade("SIGNAL", f"{symbol} 신호: {signal.value} (신뢰도: {confidence:.2f})")
            return trading_signal

        except Exception as e:
            self.log_trade("ERROR", f"신호 생성 중 오류: {str(e)}")
            return None

    def _analyze_signals(self, data: pd.DataFrame, indicators: Dict, risk_metrics: Dict) -> Tuple[SignalType, float]:
        """신호 분석 로직"""
        try:
            signals = []
            weights = []

            # RSI 신호
            rsi = indicators.get('rsi', [])
            if len(rsi) > 0:
                current_rsi = rsi[-1]
                if current_rsi < 30:
                    signals.append(1)  # 매수 신호
                    weights.append(0.3)
                elif current_rsi > 70:
                    signals.append(-1)  # 매도 신호
                    weights.append(0.3)
                else:
                    signals.append(0)  # 중립
                    weights.append(0.1)

            # MACD 신호
            macd = indicators.get('macd', [])
            macd_signal = indicators.get('macd_signal', [])
            if len(macd) > 1 and len(macd_signal) > 1:
                if macd[-1] > macd_signal[-1] and macd[-2] <= macd_signal[-2]:
                    signals.append(1)  # 골든 크로스
                    weights.append(0.25)
                elif macd[-1] < macd_signal[-1] and macd[-2] >= macd_signal[-2]:
                    signals.append(-1)  # 데드 크로스
                    weights.append(0.25)
                else:
                    signals.append(0)
                    weights.append(0.1)

            # 볼린저 밴드 신호
            bb_lower = indicators.get('bb_lower', [])
            bb_upper = indicators.get('bb_upper', [])
            current_price = float(data['close'].iloc[-1])

            if len(bb_lower) > 0 and len(bb_upper) > 0:
                if current_price <= bb_lower[-1]:
                    signals.append(1)  # 하단 밴드 터치
                    weights.append(0.2)
                elif current_price >= bb_upper[-1]:
                    signals.append(-1)  # 상단 밴드 터치
                    weights.append(0.2)
                else:
                    signals.append(0)
                    weights.append(0.1)

            # 거래량 확인
            volume_change = indicators.get('volume_change', 0)
            if volume_change > 0.2:  # 20% 이상 거래량 증가
                if len(signals) > 0 and signals[-1] != 0:
                    weights[-1] *= 1.2  # 거래량 증가 시 신호 강화

            # 종합 신호 계산
            if len(signals) == 0:
                return SignalType.HOLD, 0.0

            weighted_signal = np.average(signals, weights=weights)
            confidence = min(abs(weighted_signal), 1.0)

            if weighted_signal > 0.3:
                return SignalType.BUY, confidence
            elif weighted_signal < -0.3:
                return SignalType.SELL, confidence
            else:
                return SignalType.HOLD, confidence

        except Exception as e:
            self.log_trade("ERROR", f"신호 분석 중 오류: {str(e)}")
            return SignalType.HOLD, 0.0

    def calculate_position_size(self, signal: TradingSignal, portfolio_value: float) -> float:
        """포지션 크기 계산"""
        try:
            # 기본 포지션 크기 (포트폴리오의 2%)
            base_size = portfolio_value * self.position_size_base

            # 신뢰도에 따른 조정
            confidence_multiplier = signal.confidence
            adjusted_size = base_size * confidence_multiplier

            # ATR 기반 리스크 조정
            atr_risk = signal.risk_metrics.get('atr_percentage', 0.02)
            if atr_risk > 0.05:  # 5% 이상 변동성
                adjusted_size *= 0.5  # 포지션 크기 절반으로 감소

            # 연속 손실 시 포지션 크기 감소
            if self.consecutive_losses > 0:
                loss_penalty = 0.8 ** self.consecutive_losses
                adjusted_size *= loss_penalty

            # 최소/최대 포지션 크기 제한
            min_size = 10.0  # 최소 $10
            max_size = min(50.0, self.daily_limit - self.daily_volume)  # 최대 $50 또는 남은 한도

            final_size = max(min_size, min(adjusted_size, max_size))

            self.log_trade("POSITION", f"포지션 크기: ${final_size:.2f} (신뢰도: {signal.confidence:.2f})")
            return final_size

        except Exception as e:
            self.log_trade("ERROR", f"포지션 크기 계산 중 오류: {str(e)}")
            return 10.0  # 기본값

    def calculate_stop_loss_take_profit(self, signal: TradingSignal, entry_price: float) -> Tuple[float, float]:
        """손절/익절 가격 계산"""
        try:
            atr = signal.risk_metrics.get('atr', 0.02 * entry_price)

            if signal.signal == SignalType.BUY:
                stop_loss = entry_price - (2 * atr)  # 2 ATR 아래
                take_profit = entry_price + (3 * atr)  # 3 ATR 위 (1:1.5 비율)
            else:  # SELL
                stop_loss = entry_price + (2 * atr)  # 2 ATR 위
                take_profit = entry_price - (3 * atr)  # 3 ATR 아래

            return stop_loss, take_profit

        except Exception as e:
            self.log_trade("ERROR", f"손절/익절 계산 중 오류: {str(e)}")
            # 기본값 (2% 손절, 3% 익절)
            if signal.signal == SignalType.BUY:
                return entry_price * 0.98, entry_price * 1.03
            else:
                return entry_price * 1.02, entry_price * 0.97

    def execute_trade(self, signal: TradingSignal) -> bool:
        """거래 실행"""
        try:
            if not self.check_trading_limits():
                self.log_trade("ABORT", "거래 한도 초과로 거래 취소")
                return False

            if signal.confidence < self.min_confidence:
                self.log_trade("SKIP", f"신뢰도 부족으로 거래 건너뛰기: {signal.confidence:.2f}")
                return False

            # 포트폴리오 가치 조회
            portfolio_value = 1000.0  # 기본값
            if self.mode == TradingMode.LIVE and self.binance:
                account = self.binance.get_account_info()
                if account and account.get('success'):
                    usdt_balance = next((b for b in account.get('balances', [])
                                       if b['asset'] == 'USDT'), None)
                    if usdt_balance:
                        portfolio_value = float(usdt_balance.get('free', 1000))

            # 포지션 크기 계산
            position_size_usdt = self.calculate_position_size(signal, portfolio_value)

            if self.mode == TradingMode.DEMO:
                # 데모 모드: 시뮬레이션만
                self._execute_demo_trade(signal, position_size_usdt)
                return True
            else:
                # 라이브 모드: 실제 거래
                return self._execute_live_trade(signal, position_size_usdt)

        except Exception as e:
            self.log_trade("ERROR", f"거래 실행 중 오류: {str(e)}")
            return False

    def _execute_demo_trade(self, signal: TradingSignal, position_size_usdt: float):
        """데모 거래 실행"""
        try:
            # 수량 계산
            quantity = position_size_usdt / signal.price

            # 손절/익절 계산
            stop_loss, take_profit = self.calculate_stop_loss_take_profit(signal, signal.price)

            # 시뮬레이션 주문
            order_result = {
                'success': True,
                'order_id': f"DEMO_{int(time.time())}",
                'symbol': signal.symbol,
                'side': signal.signal.value,
                'quantity': quantity,
                'price': signal.price,
                'status': 'FILLED'
            }

            # 포지션 기록
            position = Position(
                symbol=signal.symbol,
                side='LONG' if signal.signal == SignalType.BUY else 'SHORT',
                quantity=quantity,
                entry_price=signal.price,
                current_price=signal.price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                pnl=0.0,
                pnl_percentage=0.0,
                timestamp=datetime.now()
            )

            self.current_positions[signal.symbol] = position
            self.daily_volume += position_size_usdt

            self.log_trade("DEMO_TRADE",
                          f"{signal.signal.value} {quantity:.5f} {signal.symbol} @ ${signal.price:.2f}")
            self.log_trade("DEMO_TRADE",
                          f"손절: ${stop_loss:.2f}, 익절: ${take_profit:.2f}")

        except Exception as e:
            self.log_trade("ERROR", f"데모 거래 실행 중 오류: {str(e)}")

    def _execute_live_trade(self, signal: TradingSignal, position_size_usdt: float) -> bool:
        """실제 거래 실행"""
        try:
            if not self.binance:
                self.log_trade("ERROR", "Binance 커넥터가 초기화되지 않음")
                return False

            # 수량 계산
            quantity_info = self._calculate_live_quantity(signal.symbol, position_size_usdt, signal.price)
            if not quantity_info:
                return False

            quantity = quantity_info['quantity']

            # 실제 주문 실행
            side = 'BUY' if signal.signal == SignalType.BUY else 'SELL'
            order_result = self.binance.place_market_order(signal.symbol, side, quantity)

            if not order_result.get('success'):
                self.log_trade("ERROR", f"주문 실패: {order_result.get('error')}")
                return False

            # 주문 체결 확인
            order_id = order_result.get('order_id')
            self.log_trade("LIVE_TRADE", f"주문 실행 완료 - ID: {order_id}")

            # 포지션 기록
            stop_loss, take_profit = self.calculate_stop_loss_take_profit(signal, signal.price)

            position = Position(
                symbol=signal.symbol,
                side='LONG' if signal.signal == SignalType.BUY else 'SHORT',
                quantity=quantity,
                entry_price=signal.price,
                current_price=signal.price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                pnl=0.0,
                pnl_percentage=0.0,
                timestamp=datetime.now()
            )

            self.current_positions[signal.symbol] = position
            self.daily_volume += position_size_usdt

            self.log_trade("LIVE_TRADE",
                          f"{side} {quantity:.5f} {signal.symbol} @ ${signal.price:.2f}")

            return True

        except Exception as e:
            self.log_trade("ERROR", f"실제 거래 실행 중 오류: {str(e)}")
            return False

    def _calculate_live_quantity(self, symbol: str, usdt_amount: float, price: float) -> Optional[Dict]:
        """실제 거래용 수량 계산"""
        try:
            # 심볼 정보 조회
            symbol_info = self.binance.get_symbol_info(symbol)
            if not symbol_info.get('success'):
                self.log_trade("ERROR", f"심볼 정보 조회 실패: {symbol}")
                return None

            # LOT_SIZE 필터 찾기
            step_size = '0.00001'
            min_qty = 0.00001

            for filter_info in symbol_info.get('filters', []):
                if filter_info.get('filterType') == 'LOT_SIZE':
                    step_size = filter_info.get('stepSize', '0.00001')
                    min_qty = float(filter_info.get('minQty', 0.00001))
                    break

            # 수량 계산
            quantity = Decimal(str(usdt_amount)) / Decimal(str(price))
            step_decimal = Decimal(step_size)
            quantity = (quantity / step_decimal).quantize(Decimal('1'), rounding='ROUND_DOWN') * step_decimal
            final_quantity = float(quantity)

            if final_quantity < min_qty:
                self.log_trade("ERROR", f"계산된 수량이 최소 수량보다 작음: {final_quantity} < {min_qty}")
                return None

            return {
                'quantity': final_quantity,
                'step_size': step_size,
                'min_qty': min_qty
            }

        except Exception as e:
            self.log_trade("ERROR", f"수량 계산 중 오류: {str(e)}")
            return None

    def update_positions(self):
        """포지션 업데이트"""
        try:
            for symbol, position in list(self.current_positions.items()):
                # 현재 가격 조회
                current_price = None
                if self.mode == TradingMode.LIVE and self.binance:
                    price_info = self.binance.get_current_price(symbol)
                    if price_info and price_info.get('success'):
                        current_price = price_info.get('price')

                if current_price is None:
                    # 데모 모드 또는 가격 조회 실패 시 CoinGecko에서 조회
                    coingecko_symbol = symbol.lower().replace('usdt', '')
                    if coingecko_symbol == 'btc':
                        coingecko_symbol = 'bitcoin'
                    elif coingecko_symbol == 'eth':
                        coingecko_symbol = 'ethereum'
                    elif coingecko_symbol == 'bnb':
                        coingecko_symbol = 'binancecoin'

                    data = self.coingecko.get_ohlc_data(coingecko_symbol, 1)
                    if data is not None and len(data) > 0:
                        current_price = float(data['close'].iloc[-1])

                if current_price:
                    # PnL 계산
                    if position.side == 'LONG':
                        pnl = (current_price - position.entry_price) * position.quantity
                    else:
                        pnl = (position.entry_price - current_price) * position.quantity

                    pnl_percentage = (pnl / (position.entry_price * position.quantity)) * 100

                    # 포지션 업데이트
                    position.current_price = current_price
                    position.pnl = pnl
                    position.pnl_percentage = pnl_percentage

                    # 손절/익절 확인
                    self._check_stop_loss_take_profit(symbol, position)

        except Exception as e:
            self.log_trade("ERROR", f"포지션 업데이트 중 오류: {str(e)}")

    def _check_stop_loss_take_profit(self, symbol: str, position: Position):
        """손절/익절 확인"""
        try:
            if position.side == 'LONG':
                if position.current_price <= position.stop_loss:
                    self.log_trade("STOP_LOSS", f"{symbol} 손절 실행: ${position.current_price:.2f}")
                    self._close_position(symbol, "STOP_LOSS")
                elif position.current_price >= position.take_profit:
                    self.log_trade("TAKE_PROFIT", f"{symbol} 익절 실행: ${position.current_price:.2f}")
                    self._close_position(symbol, "TAKE_PROFIT")
            else:  # SHORT
                if position.current_price >= position.stop_loss:
                    self.log_trade("STOP_LOSS", f"{symbol} 손절 실행: ${position.current_price:.2f}")
                    self._close_position(symbol, "STOP_LOSS")
                elif position.current_price <= position.take_profit:
                    self.log_trade("TAKE_PROFIT", f"{symbol} 익절 실행: ${position.current_price:.2f}")
                    self._close_position(symbol, "TAKE_PROFIT")

        except Exception as e:
            self.log_trade("ERROR", f"손절/익절 확인 중 오류: {str(e)}")

    def _close_position(self, symbol: str, reason: str):
        """포지션 종료"""
        try:
            if symbol not in self.current_positions:
                return

            position = self.current_positions[symbol]

            if self.mode == TradingMode.LIVE and self.binance:
                # 실제 매도 주문
                side = 'SELL' if position.side == 'LONG' else 'BUY'
                order_result = self.binance.place_market_order(symbol, side, position.quantity)

                if not order_result.get('success'):
                    self.log_trade("ERROR", f"포지션 종료 실패: {order_result.get('error')}")
                    return

            # 거래 기록
            trade_record = {
                'symbol': symbol,
                'side': position.side,
                'quantity': position.quantity,
                'entry_price': position.entry_price,
                'exit_price': position.current_price,
                'pnl': position.pnl,
                'pnl_percentage': position.pnl_percentage,
                'reason': reason,
                'timestamp': datetime.now()
            }

            self.trading_history.append(trade_record)
            self.daily_pnl += position.pnl

            # 연속 손실 카운터 업데이트
            if position.pnl < 0:
                self.consecutive_losses += 1
            else:
                self.consecutive_losses = 0

            self.log_trade("CLOSE", f"{symbol} 포지션 종료 - PnL: ${position.pnl:.2f} ({position.pnl_percentage:+.2f}%)")

            # 포지션 제거
            del self.current_positions[symbol]

        except Exception as e:
            self.log_trade("ERROR", f"포지션 종료 중 오류: {str(e)}")

    def run_trading_cycle(self, symbols: List[str] = ['BTCUSDT']):
        """거래 사이클 실행"""
        try:
            self.log_trade("CYCLE", f"거래 사이클 시작 - 심볼: {symbols}")

            # 포지션 업데이트
            self.update_positions()

            # 각 심볼에 대해 신호 생성 및 거래 실행
            for symbol in symbols:
                if not self.check_trading_limits():
                    break

                # 이미 포지션이 있는 경우 건너뛰기
                if symbol in self.current_positions:
                    continue

                # 신호 생성
                signal = self.generate_trading_signal(symbol)
                if signal and signal.signal != SignalType.HOLD:
                    # 거래 실행
                    self.execute_trade(signal)

            self.log_trade("CYCLE", "거래 사이클 완료")

        except Exception as e:
            self.log_trade("ERROR", f"거래 사이클 중 오류: {str(e)}")

    def get_status_report(self) -> Dict:
        """상태 보고서 생성"""
        try:
            total_positions = len(self.current_positions)
            total_pnl = sum(pos.pnl for pos in self.current_positions.values()) + self.daily_pnl

            return {
                'mode': self.mode.value,
                'current_time': datetime.now().isoformat(),
                'positions': {
                    'total': total_positions,
                    'symbols': list(self.current_positions.keys())
                },
                'daily_stats': {
                    'pnl': round(total_pnl, 2),
                    'volume': round(self.daily_volume, 2),
                    'trades': len(self.trading_history),
                    'consecutive_losses': self.consecutive_losses
                },
                'limits': {
                    'daily_limit': self.daily_limit,
                    'remaining_limit': round(self.daily_limit - self.daily_volume, 2),
                    'emergency_stop': self.emergency_stop
                },
                'positions_detail': [
                    {
                        'symbol': pos.symbol,
                        'side': pos.side,
                        'quantity': pos.quantity,
                        'entry_price': pos.entry_price,
                        'current_price': pos.current_price,
                        'pnl': round(pos.pnl, 2),
                        'pnl_percentage': round(pos.pnl_percentage, 2)
                    }
                    for pos in self.current_positions.values()
                ]
            }

        except Exception as e:
            self.log_trade("ERROR", f"상태 보고서 생성 중 오류: {str(e)}")
            return {}

if __name__ == "__main__":
    # AI 실시간 거래 시스템 테스트
    print("=== AI 실시간 거래 시스템 테스트 ===")

    # 데모 모드로 시작
    trading_system = AILiveTradingSystem(TradingMode.DEMO)

    # 단일 사이클 실행
    trading_system.run_trading_cycle(['BTCUSDT'])

    # 상태 보고서 출력
    status = trading_system.get_status_report()
    print("\n=== 상태 보고서 ===")
    print(json.dumps(status, indent=2))