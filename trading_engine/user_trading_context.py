"""
User Trading Context for Background Trading Bot
사용자별 거래 컨텍스트 및 격리된 거래 환경
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import json
import ccxt

from database import get_db_manager, User, TradingSettings, TradingSession
from .market_monitor import MarketDataMonitor

logger = logging.getLogger(__name__)

class UserTradingContext:
    """사용자별 거래 컨텍스트 클래스"""

    def __init__(self, user: User, trading_settings: TradingSettings,
                 api_credentials: Tuple[str, str], market_monitor: MarketDataMonitor):
        """
        사용자 거래 컨텍스트 초기화

        Args:
            user: 사용자 객체
            trading_settings: 거래 설정
            api_credentials: (API 키, API 시크릿)
            market_monitor: 시장 데이터 모니터
        """
        self.user = user
        self.trading_settings = trading_settings
        self.api_key, self.api_secret = api_credentials
        self.market_monitor = market_monitor
        self.db_manager = get_db_manager()

        # 거래 상태
        self.is_active = False
        self.trading_session: Optional[TradingSession] = None
        self.exchange: Optional[ccxt.Exchange] = None

        # 거래 통계
        self.total_trades = 0
        self.successful_trades = 0
        self.session_profit_loss = 0.0
        self.daily_profit_loss = 0.0
        self.last_signal_time: Optional[datetime] = None

        # 포지션 관리
        self.open_positions: Dict[str, Dict] = {}
        self.position_count = 0

        # 리스크 관리
        self.daily_loss_limit_reached = False
        self.consecutive_losses = 0
        self.last_trade_time: Optional[datetime] = None

        # 거래 설정 파싱
        self._parse_trading_settings()

        logger.info(f"User trading context initialized for {user.username}")

    def _parse_trading_settings(self):
        """거래 설정 파싱"""
        try:
            # 거래 심볼 파싱
            if self.trading_settings.symbols:
                self.symbols = json.loads(self.trading_settings.symbols)
            else:
                self.symbols = ['BTCUSDT', 'ETHUSDT']

            # 전략 설정 파싱
            if self.trading_settings.strategy_config:
                self.strategy_config = json.loads(self.trading_settings.strategy_config)
            else:
                self.strategy_config = {
                    'strategy_type': 'rsi_mean_reversion',
                    'rsi_oversold': 30,
                    'rsi_overbought': 70,
                    'stop_loss_pct': 2.0,
                    'take_profit_pct': 4.0,
                    'min_signal_confidence': 70
                }

        except Exception as e:
            logger.error(f"Error parsing trading settings for user {self.user.id}: {e}")
            # 기본값 설정
            self.symbols = ['BTCUSDT', 'ETHUSDT']
            self.strategy_config = {
                'strategy_type': 'rsi_mean_reversion',
                'rsi_oversold': 30,
                'rsi_overbought': 70,
                'stop_loss_pct': 2.0,
                'take_profit_pct': 4.0,
                'min_signal_confidence': 70
            }

    async def start_trading(self) -> bool:
        """거래 세션 시작"""
        try:
            # 거래소 연결 설정
            self.exchange = ccxt.binance({
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'sandbox': True,  # 테스트넷 모드
                'enableRateLimit': True,
            })

            # 연결 테스트
            balance = self.exchange.fetch_balance()
            logger.info(f"Exchange connected for user {self.user.id}, USDT balance: {balance.get('USDT', {}).get('total', 0)}")

            # 거래 세션 시작
            self.trading_session = self.db_manager.start_trading_session(self.user.id)
            if not self.trading_session:
                logger.error(f"Failed to start trading session for user {self.user.id}")
                return False

            self.is_active = True
            self.session_profit_loss = 0.0
            self.daily_profit_loss = 0.0
            self.daily_loss_limit_reached = False

            logger.info(f"✅ Trading started for user {self.user.id} ({self.user.username})")
            return True

        except Exception as e:
            logger.error(f"Error starting trading for user {self.user.id}: {e}")
            return False

    async def stop_trading(self):
        """거래 세션 중지"""
        try:
            self.is_active = False

            # 모든 오픈 포지션 정리 (실제 구현 시)
            await self._close_all_positions()

            # 거래 세션 종료
            if self.trading_session:
                self.db_manager.end_trading_session(self.user.id, self.trading_session.id)

            logger.info(f"❌ Trading stopped for user {self.user.id} ({self.user.username})")

        except Exception as e:
            logger.error(f"Error stopping trading for user {self.user.id}: {e}")

    async def process_trading_cycle(self):
        """거래 주기 처리"""
        if not self.is_active or not self.exchange:
            return

        try:
            # 리스크 관리 체크
            if not self._check_risk_limits():
                return

            # 각 심볼에 대해 거래 신호 처리
            for symbol in self.symbols:
                await self._process_symbol_trading(symbol)

            # 오픈 포지션 관리
            await self._manage_open_positions()

        except Exception as e:
            logger.error(f"Trading cycle error for user {self.user.id}: {e}")

    async def _process_symbol_trading(self, symbol: str):
        """특정 심볼에 대한 거래 처리"""
        try:
            # 시장 데이터 조회
            market_data = self.market_monitor.get_market_data('binance', symbol.replace('USDT', '/USDT'))
            if not market_data:
                return

            # AI 신호 생성
            signal = self._generate_trading_signal(symbol, market_data)
            if not signal or signal['confidence'] < self.strategy_config['min_signal_confidence']:
                return

            # 신호에 따른 거래 실행
            if signal['action'] == 'BUY' and self.position_count < self.trading_settings.max_positions:
                await self._execute_buy_order(symbol, signal, market_data)
            elif signal['action'] == 'SELL' and symbol in self.open_positions:
                await self._execute_sell_order(symbol, signal, market_data)

            self.last_signal_time = datetime.utcnow()

        except Exception as e:
            logger.error(f"Symbol trading error for {symbol}, user {self.user.id}: {e}")

    def _generate_trading_signal(self, symbol: str, market_data: Dict) -> Optional[Dict]:
        """거래 신호 생성"""
        try:
            indicators = market_data.get('technical_indicators', {})
            price = market_data['price']

            # RSI 기반 평균 회귀 전략
            if self.strategy_config['strategy_type'] == 'rsi_mean_reversion':
                return self._rsi_mean_reversion_signal(symbol, price, indicators)

            return None

        except Exception as e:
            logger.error(f"Signal generation error for {symbol}: {e}")
            return None

    def _rsi_mean_reversion_signal(self, symbol: str, price: float, indicators: Dict) -> Optional[Dict]:
        """RSI 평균 회귀 신호 생성"""
        try:
            rsi = indicators.get('rsi', 50)
            volume_ratio = indicators.get('volume_ratio', 1)
            volatility = indicators.get('volatility', 0)

            # 매수 신호 조건
            if (rsi <= self.strategy_config['rsi_oversold'] and
                volume_ratio > 1.2 and
                volatility < 5.0):  # 변동성이 5% 미만

                confidence = min(100, (50 - rsi) * 2 + volume_ratio * 10)

                return {
                    'action': 'BUY',
                    'symbol': symbol,
                    'price': price,
                    'confidence': int(confidence),
                    'stop_loss': price * (1 - self.strategy_config['stop_loss_pct'] / 100),
                    'take_profit': price * (1 + self.strategy_config['take_profit_pct'] / 100),
                    'reasoning': f'RSI oversold ({rsi:.1f}), volume spike ({volume_ratio:.1f}x)',
                    'indicators': {
                        'rsi': rsi,
                        'volume_ratio': volume_ratio,
                        'volatility': volatility
                    }
                }

            # 매도 신호 조건
            elif (rsi >= self.strategy_config['rsi_overbought'] and
                  volume_ratio > 1.2):

                confidence = min(100, (rsi - 50) * 2 + volume_ratio * 10)

                return {
                    'action': 'SELL',
                    'symbol': symbol,
                    'price': price,
                    'confidence': int(confidence),
                    'reasoning': f'RSI overbought ({rsi:.1f}), volume spike ({volume_ratio:.1f}x)',
                    'indicators': {
                        'rsi': rsi,
                        'volume_ratio': volume_ratio,
                        'volatility': volatility
                    }
                }

            return None

        except Exception as e:
            logger.error(f"RSI signal generation error: {e}")
            return None

    async def _execute_buy_order(self, symbol: str, signal: Dict, market_data: Dict):
        """매수 주문 실행"""
        try:
            # 포지션 크기 계산
            position_size = self._calculate_position_size(signal['price'])
            if position_size <= 0:
                return

            # 주문 실행 (테스트넷이므로 실제로는 시뮬레이션)
            order_result = await self._simulate_buy_order(symbol, signal['price'], position_size)

            if order_result['success']:
                # 포지션 정보 저장
                position = {
                    'symbol': symbol,
                    'side': 'LONG',
                    'entry_price': signal['price'],
                    'quantity': position_size,
                    'stop_loss': signal['stop_loss'],
                    'take_profit': signal['take_profit'],
                    'timestamp': datetime.utcnow(),
                    'signal_confidence': signal['confidence']
                }

                self.open_positions[symbol] = position
                self.position_count += 1

                # 거래 기록 저장
                self.db_manager.record_trade(
                    user_id=self.user.id,
                    session_id=self.trading_session.id,
                    symbol=symbol,
                    side='BUY',
                    amount=position_size,
                    price=signal['price'],
                    signal_confidence=signal['confidence']
                )

                self.total_trades += 1
                logger.info(f"✅ BUY order executed for user {self.user.id}: {symbol} @ {signal['price']:.2f}, size: {position_size:.6f}")

        except Exception as e:
            logger.error(f"Buy order execution error for user {self.user.id}: {e}")

    async def _execute_sell_order(self, symbol: str, signal: Dict, market_data: Dict):
        """매도 주문 실행"""
        try:
            if symbol not in self.open_positions:
                return

            position = self.open_positions[symbol]

            # 주문 실행 (테스트넷이므로 실제로는 시뮬레이션)
            order_result = await self._simulate_sell_order(symbol, signal['price'], position['quantity'])

            if order_result['success']:
                # 손익 계산
                profit_loss = (signal['price'] - position['entry_price']) * position['quantity']
                profit_loss_pct = (profit_loss / (position['entry_price'] * position['quantity'])) * 100

                # 포지션 정리
                del self.open_positions[symbol]
                self.position_count -= 1

                # 거래 기록 저장
                self.db_manager.record_trade(
                    user_id=self.user.id,
                    session_id=self.trading_session.id,
                    symbol=symbol,
                    side='SELL',
                    amount=position['quantity'],
                    price=signal['price'],
                    profit_loss=profit_loss,
                    signal_confidence=signal['confidence']
                )

                # 통계 업데이트
                self.total_trades += 1
                self.session_profit_loss += profit_loss
                self.daily_profit_loss += profit_loss

                if profit_loss > 0:
                    self.successful_trades += 1
                    self.consecutive_losses = 0
                else:
                    self.consecutive_losses += 1

                logger.info(f"✅ SELL order executed for user {self.user.id}: {symbol} @ {signal['price']:.2f}, P&L: {profit_loss:.2f} USDT ({profit_loss_pct:.2f}%)")

        except Exception as e:
            logger.error(f"Sell order execution error for user {self.user.id}: {e}")

    async def _manage_open_positions(self):
        """오픈 포지션 관리 (손절/익절)"""
        try:
            for symbol, position in list(self.open_positions.items()):
                # 현재 가격 조회
                market_data = self.market_monitor.get_market_data('binance', symbol.replace('USDT', '/USDT'))
                if not market_data:
                    continue

                current_price = market_data['price']

                # 손절 조건 체크
                if current_price <= position['stop_loss']:
                    await self._execute_stop_loss(symbol, current_price, position)

                # 익절 조건 체크
                elif current_price >= position['take_profit']:
                    await self._execute_take_profit(symbol, current_price, position)

        except Exception as e:
            logger.error(f"Position management error for user {self.user.id}: {e}")

    async def _execute_stop_loss(self, symbol: str, current_price: float, position: Dict):
        """손절 실행"""
        try:
            # 매도 주문 실행
            order_result = await self._simulate_sell_order(symbol, current_price, position['quantity'])

            if order_result['success']:
                # 손실 계산
                loss = (current_price - position['entry_price']) * position['quantity']

                # 포지션 정리
                del self.open_positions[symbol]
                self.position_count -= 1

                # 거래 기록
                self.db_manager.record_trade(
                    user_id=self.user.id,
                    session_id=self.trading_session.id,
                    symbol=symbol,
                    side='SELL',
                    amount=position['quantity'],
                    price=current_price,
                    profit_loss=loss
                )

                # 통계 업데이트
                self.total_trades += 1
                self.session_profit_loss += loss
                self.daily_profit_loss += loss
                self.consecutive_losses += 1

                logger.info(f"🛑 Stop loss executed for user {self.user.id}: {symbol} @ {current_price:.2f}, Loss: {loss:.2f} USDT")

        except Exception as e:
            logger.error(f"Stop loss execution error: {e}")

    async def _execute_take_profit(self, symbol: str, current_price: float, position: Dict):
        """익절 실행"""
        try:
            # 매도 주문 실행
            order_result = await self._simulate_sell_order(symbol, current_price, position['quantity'])

            if order_result['success']:
                # 수익 계산
                profit = (current_price - position['entry_price']) * position['quantity']

                # 포지션 정리
                del self.open_positions[symbol]
                self.position_count -= 1

                # 거래 기록
                self.db_manager.record_trade(
                    user_id=self.user.id,
                    session_id=self.trading_session.id,
                    symbol=symbol,
                    side='SELL',
                    amount=position['quantity'],
                    price=current_price,
                    profit_loss=profit
                )

                # 통계 업데이트
                self.total_trades += 1
                self.successful_trades += 1
                self.session_profit_loss += profit
                self.daily_profit_loss += profit
                self.consecutive_losses = 0

                logger.info(f"🎯 Take profit executed for user {self.user.id}: {symbol} @ {current_price:.2f}, Profit: {profit:.2f} USDT")

        except Exception as e:
            logger.error(f"Take profit execution error: {e}")

    def _calculate_position_size(self, price: float) -> float:
        """포지션 크기 계산"""
        try:
            # 계좌 잔고 조회 (시뮬레이션)
            account_balance = 10000.0  # 기본 테스트 잔고

            # 리스크 비율에 따른 포지션 크기
            risk_amount = account_balance * (self.trading_settings.risk_percentage / 100)

            # 손절 폭을 고려한 포지션 크기
            stop_loss_pct = self.strategy_config['stop_loss_pct'] / 100
            position_size_usdt = risk_amount / stop_loss_pct

            # 최대 포지션 크기 제한 (계좌의 20%)
            max_position_usdt = account_balance * 0.2
            position_size_usdt = min(position_size_usdt, max_position_usdt)

            # 암호화폐 수량으로 변환
            position_size = position_size_usdt / price

            return position_size

        except Exception as e:
            logger.error(f"Position size calculation error: {e}")
            return 0.0

    async def _simulate_buy_order(self, symbol: str, price: float, quantity: float) -> Dict:
        """매수 주문 시뮬레이션"""
        # 실제 테스트넷 거래소에서는 실제 주문 실행
        # 여기서는 시뮬레이션으로 처리
        return {
            'success': True,
            'order_id': f"buy_{symbol}_{int(datetime.utcnow().timestamp())}",
            'filled_quantity': quantity,
            'filled_price': price
        }

    async def _simulate_sell_order(self, symbol: str, price: float, quantity: float) -> Dict:
        """매도 주문 시뮬레이션"""
        # 실제 테스트넷 거래소에서는 실제 주문 실행
        # 여기서는 시뮬레이션으로 처리
        return {
            'success': True,
            'order_id': f"sell_{symbol}_{int(datetime.utcnow().timestamp())}",
            'filled_quantity': quantity,
            'filled_price': price
        }

    async def _close_all_positions(self):
        """모든 포지션 정리"""
        try:
            for symbol in list(self.open_positions.keys()):
                market_data = self.market_monitor.get_market_data('binance', symbol.replace('USDT', '/USDT'))
                if market_data:
                    current_price = market_data['price']
                    position = self.open_positions[symbol]
                    await self._simulate_sell_order(symbol, current_price, position['quantity'])

            self.open_positions.clear()
            self.position_count = 0

        except Exception as e:
            logger.error(f"Error closing all positions for user {self.user.id}: {e}")

    def _check_risk_limits(self) -> bool:
        """리스크 한도 체크"""
        try:
            # 일일 손실 한도 체크
            daily_loss_limit = 10000.0 * (self.trading_settings.daily_loss_limit / 100)  # 기본 계좌 잔고 기준

            if self.daily_profit_loss <= -daily_loss_limit:
                if not self.daily_loss_limit_reached:
                    self.daily_loss_limit_reached = True
                    logger.warning(f"Daily loss limit reached for user {self.user.id}: {self.daily_profit_loss:.2f}")
                return False

            # 연속 손실 제한
            if self.consecutive_losses >= 5:
                logger.warning(f"Too many consecutive losses for user {self.user.id}: {self.consecutive_losses}")
                return False

            # 최대 포지션 수 체크
            if self.position_count >= self.trading_settings.max_positions:
                return False

            return True

        except Exception as e:
            logger.error(f"Risk limit check error for user {self.user.id}: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """거래 컨텍스트 상태 조회"""
        return {
            'user_id': self.user.id,
            'username': self.user.username,
            'is_active': self.is_active,
            'session_id': self.trading_session.id if self.trading_session else None,
            'total_trades': self.total_trades,
            'successful_trades': self.successful_trades,
            'success_rate': (self.successful_trades / self.total_trades * 100) if self.total_trades > 0 else 0,
            'session_profit_loss': self.session_profit_loss,
            'daily_profit_loss': self.daily_profit_loss,
            'open_positions': len(self.open_positions),
            'consecutive_losses': self.consecutive_losses,
            'daily_loss_limit_reached': self.daily_loss_limit_reached,
            'last_signal_time': self.last_signal_time,
            'symbols': self.symbols,
            'positions': {
                symbol: {
                    'entry_price': pos['entry_price'],
                    'quantity': pos['quantity'],
                    'stop_loss': pos['stop_loss'],
                    'take_profit': pos['take_profit'],
                    'timestamp': pos['timestamp']
                }
                for symbol, pos in self.open_positions.items()
            }
        }