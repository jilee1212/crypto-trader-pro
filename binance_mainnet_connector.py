#!/usr/bin/env python3
"""
Binance Mainnet Connector - Crypto Trader Pro
실제 거래용 바이낸스 메인넷 API 연결기
보안 강화 및 안전 설정 적용
"""

import os
import time
import logging
import hashlib
import hmac
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlencode

import ccxt
import requests

from api_interface_standard import EnhancedAPIInterface

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BinanceMainnetConnector(EnhancedAPIInterface):
    """바이낸스 메인넷 API 연결기 - 실제 거래용"""

    def __init__(self, api_key: str = None, secret_key: str = None):
        """
        메인넷 커넥터 초기화

        Args:
            api_key: 바이낸스 API 키
            secret_key: 바이낸스 시크릿 키
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = "https://api.binance.com"
        self.exchange = None

        # 극도 보안 설정 (실계좌 안전 최우선)
        self.max_position_size = Decimal('50')    # 최대 포지션 크기 (USDT) - 극소액
        self.max_order_amount = Decimal('5')      # 최대 주문 금액 (USDT) - 극소액
        self.daily_trade_limit = Decimal('20')    # 일일 거래 한도 (USDT) - 극소액
        self.max_consecutive_losses = 3           # 연속 손실 한도
        self.emergency_stop_enabled = True        # 긴급 중단 기능

        # 추가 안전장치
        self.min_balance_required = Decimal('10') # 최소 잔고 요구량
        self.trade_enabled = False                # 거래 기본 비활성화
        self.observation_mode = True              # 관찰 모드 기본 활성화

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 최소 요청 간격 (초)

        if self.api_key and self.secret_key:
            self._init_ccxt_exchange()
            logger.info("BinanceMainnetConnector initialized with API credentials")
        else:
            logger.info("BinanceMainnetConnector initialized without credentials (read-only mode)")

    def _init_ccxt_exchange(self):
        """CCXT 거래소 객체 초기화"""
        try:
            self.exchange = ccxt.binance({
                'apiKey': self.api_key,
                'secret': self.secret_key,
                'sandbox': False,  # 메인넷 사용
                'enableRateLimit': True,
                'rateLimit': 200,  # 보수적인 레이트 제한
                'options': {
                    'defaultType': 'future',  # USDT-M Futures 계좌 사용
                    'adjustForTimeDifference': True
                }
            })
            logger.info("CCXT exchange initialized successfully for MAINNET")
        except Exception as e:
            logger.error(f"Failed to initialize CCXT exchange: {e}")
            self.exchange = None

    def _rate_limit(self):
        """요청 간격 제한"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()

    def _check_trade_limits(self, amount: float, symbol: str = "USDT") -> bool:
        """거래 한도 확인"""
        if amount > float(self.max_order_amount):
            logger.warning(f"Order amount {amount} exceeds max limit {self.max_order_amount}")
            return False
        return True

    def enable_trading(self, user_confirmation: bool = False) -> bool:
        """거래 활성화 (사용자 확인 필요)"""
        if not user_confirmation:
            logger.warning("Trading activation requires explicit user confirmation")
            return False

        self.trade_enabled = True
        logger.info("TRADING ENABLED - Real money will be used!")
        return True

    def disable_trading(self) -> None:
        """거래 비활성화"""
        self.trade_enabled = False
        logger.info("Trading disabled - Safe mode activated")

    def emergency_stop(self) -> None:
        """긴급 중단"""
        self.trade_enabled = False
        self.emergency_stop_enabled = False
        logger.critical("EMERGENCY STOP ACTIVATED - All trading halted!")

    def set_observation_mode(self, enabled: bool) -> None:
        """관찰 모드 설정"""
        self.observation_mode = enabled
        if enabled:
            self.trade_enabled = False
            logger.info("Observation mode enabled - No real trades will be executed")
        else:
            logger.info("Observation mode disabled - Real trading possible (if enabled)")

    def get_safety_status(self) -> Dict[str, Any]:
        """안전 상태 조회"""
        return {
            'trade_enabled': self.trade_enabled,
            'observation_mode': self.observation_mode,
            'emergency_stop_enabled': self.emergency_stop_enabled,
            'max_order_amount': float(self.max_order_amount),
            'daily_trade_limit': float(self.daily_trade_limit),
            'max_position_size': float(self.max_position_size),
            'min_balance_required': float(self.min_balance_required),
            'max_consecutive_losses': self.max_consecutive_losses
        }

    # ===== Public API Methods (인증 불필요) =====

    def is_connected(self) -> bool:
        """연결 상태 확인"""
        try:
            response = requests.get(f"{self.base_url}/api/v3/ping", timeout=5)
            return response.status_code == 200
        except:
            return False

    def get_server_time(self) -> Optional[Dict[str, Any]]:
        """서버 시간 조회"""
        try:
            self._rate_limit()
            response = requests.get(f"{self.base_url}/api/v3/time", timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get server time: {e}")
        return None

    def get_exchange_info(self) -> Optional[Dict[str, Any]]:
        """거래소 정보 조회"""
        try:
            self._rate_limit()
            if self.exchange:
                return self.exchange.load_markets()
            else:
                response = requests.get(f"{self.base_url}/api/v3/exchangeInfo", timeout=10)
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Failed to get exchange info: {e}")
        return None

    def get_current_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """현재 가격 조회"""
        try:
            self._rate_limit()
            if self.exchange:
                ticker = self.exchange.fetch_ticker(symbol)
                return {
                    'symbol': symbol,
                    'price': ticker['last'],
                    'timestamp': ticker['timestamp']
                }
            else:
                # REST API 직접 호출
                binance_symbol = symbol.replace('/', '')
                response = requests.get(
                    f"{self.base_url}/api/v3/ticker/price",
                    params={'symbol': binance_symbol},
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'symbol': symbol,
                        'price': float(data['price']),
                        'timestamp': int(time.time() * 1000)
                    }
        except Exception as e:
            logger.error(f"Failed to get current price for {symbol}: {e}")
        return None

    def get_order_book(self, symbol: str, limit: int = 10) -> Optional[Dict[str, Any]]:
        """오더북 조회"""
        try:
            self._rate_limit()
            if self.exchange:
                orderbook = self.exchange.fetch_order_book(symbol, limit)
                return orderbook
            else:
                binance_symbol = symbol.replace('/', '')
                response = requests.get(
                    f"{self.base_url}/api/v3/depth",
                    params={'symbol': binance_symbol, 'limit': limit},
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'bids': [[float(price), float(qty)] for price, qty in data['bids']],
                        'asks': [[float(price), float(qty)] for price, qty in data['asks']],
                        'timestamp': int(time.time() * 1000)
                    }
        except Exception as e:
            logger.error(f"Failed to get order book for {symbol}: {e}")
        return None

    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> Optional[List[List]]:
        """K-Line 데이터 조회"""
        try:
            self._rate_limit()
            if self.exchange:
                ohlcv = self.exchange.fetch_ohlcv(symbol, interval, limit=limit)
                return ohlcv
            else:
                binance_symbol = symbol.replace('/', '')
                response = requests.get(
                    f"{self.base_url}/api/v3/klines",
                    params={
                        'symbol': binance_symbol,
                        'interval': interval,
                        'limit': limit
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Failed to get klines for {symbol}: {e}")
        return None

    # ===== Private API Methods (인증 필요) =====

    def _get_account_info_internal(self) -> Optional[Dict[str, Any]]:
        """내부 계정 정보 조회 (USDT-M Futures)"""
        if not self.exchange:
            return None

        try:
            self._rate_limit()

            # USDT-M Futures 계좌 정보 조회
            balance = self.exchange.fetch_balance()

            # Futures 계좌의 경우 USDT가 주 자산
            usdt_info = balance.get('USDT', {})
            total_usdt = float(usdt_info.get('total', 0))
            available_usdt = float(usdt_info.get('free', 0))

            # 추가 Futures 계좌 정보
            try:
                # Futures 계좌 상세 정보 조회
                account_info = self.exchange.fapiPrivateGetAccount()

                total_wallet_balance = float(account_info.get('totalWalletBalance', total_usdt))
                available_balance = float(account_info.get('availableBalance', available_usdt))
                unrealized_pnl = float(account_info.get('totalUnrealizedProfit', 0))

                logger.info(f"USDT-M Futures Balance: Total={total_wallet_balance}, Available={available_balance}, PnL={unrealized_pnl}")

            except Exception as e:
                logger.warning(f"Could not get detailed futures info: {e}")
                total_wallet_balance = total_usdt
                available_balance = available_usdt
                unrealized_pnl = 0

            # 메인넷용 안전 확인
            if total_wallet_balance < 10:  # 최소 10 USDT 잔고 확인
                logger.warning(f"Low USDT-M Futures balance detected: {total_wallet_balance}")

            return {
                'canTrade': True,
                'accountType': 'USDT-M Futures',
                'totalWalletBalance': str(total_wallet_balance),
                'availableBalance': str(available_balance),
                'unrealizedProfit': str(unrealized_pnl),
                'balances': [
                    {
                        'asset': asset,
                        'balance': str(info.get('total', 0)),
                        'availableBalance': str(info.get('free', 0)),
                        'unrealizedProfit': str(info.get('unrealizedProfit', 0)) if 'unrealizedProfit' in info else '0'
                    }
                    for asset, info in balance.items()
                    if isinstance(info, dict) and float(info.get('total', 0)) > 0
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get USDT-M Futures account info: {e}")
            return None

    def get_account_info(self, api_key: str = None, api_secret: str = None) -> Optional[Dict[str, Any]]:
        """계정 정보 조회 (메인넷 보안 강화)"""
        if api_key and api_secret:
            # 임시 자격증명으로 테스트
            original_api_key = self.api_key
            original_secret_key = self.secret_key
            self.api_key = api_key
            self.secret_key = api_secret
            self._init_ccxt_exchange()

            try:
                result = self._get_account_info_internal()
                return result
            finally:
                # 원래 자격증명 복원
                self.api_key = original_api_key
                self.secret_key = original_secret_key
                self._init_ccxt_exchange()
        else:
            return self._get_account_info_internal()

    def get_positions(self) -> Optional[List[Dict[str, Any]]]:
        """USDT-M Futures 포지션 조회"""
        if not self.exchange:
            return []

        try:
            self._rate_limit()

            # Futures 포지션 조회
            positions = self.exchange.fetch_positions()

            result = []
            for position in positions:
                if position and float(position.get('contracts', 0)) != 0:
                    result.append({
                        'symbol': position.get('symbol'),
                        'side': position.get('side'),
                        'size': str(position.get('contracts', 0)),
                        'notional': str(position.get('notional', 0)),
                        'unrealizedPnl': str(position.get('unrealizedPnl', 0)),
                        'percentage': str(position.get('percentage', 0)),
                        'entryPrice': str(position.get('entryPrice', 0)),
                        'markPrice': str(position.get('markPrice', 0)),
                        'marginType': position.get('marginType', 'isolated'),
                        'leverage': str(position.get('leverage', 1))
                    })

            logger.info(f"Found {len(result)} active futures positions")
            return result

        except Exception as e:
            logger.error(f"Failed to get USDT-M futures positions: {e}")
            return []

    def get_open_orders(self, symbol: str = None) -> Optional[List[Dict[str, Any]]]:
        """미체결 주문 조회"""
        if not self.exchange:
            return []

        try:
            self._rate_limit()
            if symbol:
                orders = self.exchange.fetch_open_orders(symbol)
            else:
                orders = self.exchange.fetch_open_orders()

            return [
                {
                    'id': order['id'],
                    'symbol': order['symbol'],
                    'side': order['side'],
                    'amount': order['amount'],
                    'price': order['price'],
                    'status': order['status'],
                    'timestamp': order['timestamp']
                }
                for order in orders
            ]
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            return []

    def test_api_credentials(self, api_key: str = None, secret_key: str = None) -> Dict[str, Any]:
        """API 자격증명 테스트 (메인넷용 안전 테스트)"""
        test_api_key = api_key or self.api_key
        test_secret_key = secret_key or self.secret_key

        if not test_api_key or not test_secret_key:
            return {
                'success': False,
                'message': 'API 키와 시크릿 키가 필요합니다',
                'details': {'suggestion': 'API 자격증명을 입력해주세요'}
            }

        try:
            # 임시 exchange 객체로 테스트
            test_exchange = ccxt.binance({
                'apiKey': test_api_key,
                'secret': test_secret_key,
                'sandbox': False,  # 메인넷
                'enableRateLimit': True,
                'timeout': 10000
            })

            # 안전한 계정 정보 조회 테스트
            account = test_exchange.fetch_balance()

            # 메인넷 경고 메시지
            total_usdt = float(account.get('USDT', {}).get('total', 0))

            return {
                'success': True,
                'message': f'메인넷 API 연결 성공! USDT 잔고: {total_usdt:.2f}',
                'data': {
                    'canTrade': True,
                    'network': 'MAINNET',
                    'balance_usdt': total_usdt,
                    'warning': '실제 자금이 사용됩니다. 소액으로 테스트하세요.'
                }
            }

        except ccxt.AuthenticationError:
            return {
                'success': False,
                'message': 'API 키 인증 실패',
                'details': {'suggestion': 'API 키와 시크릿 키를 확인해주세요'}
            }
        except ccxt.PermissionDenied:
            return {
                'success': False,
                'message': 'API 권한 부족',
                'details': {'suggestion': 'API 키에 현물 거래 권한이 필요합니다'}
            }
        except ccxt.NetworkError as e:
            return {
                'success': False,
                'message': '네트워크 연결 오류',
                'details': {'suggestion': '인터넷 연결을 확인해주세요'}
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'알 수 없는 오류: {str(e)}',
                'details': {'suggestion': 'API 설정을 다시 확인해주세요'}
            }

    # ===== Trading Methods (실제 거래 - 보안 강화) =====

    def place_order(self, symbol: str, side: str, amount: float,
                   price: float = None, order_type: str = 'market') -> Optional[Dict[str, Any]]:
        """주문 실행 (극도 보안 제한 적용)"""
        # 1. 기본 안전성 검사
        if not self.exchange:
            logger.error("Exchange not initialized")
            return None

        # 2. 거래 활성화 확인
        if not self.trade_enabled:
            logger.warning("Trading is disabled - Order rejected for safety")
            return {'error': 'Trading disabled', 'safety_check': 'failed'}

        # 3. 관찰 모드 확인
        if self.observation_mode:
            logger.info(f"OBSERVATION MODE: Would place {side} order for {amount} {symbol}")
            return {'simulation': True, 'order_type': order_type, 'side': side, 'amount': amount}

        # 4. 긴급 중단 확인
        if not self.emergency_stop_enabled:
            logger.error("Emergency stop activated - No trading allowed")
            return {'error': 'Emergency stop active', 'safety_check': 'failed'}

        # 5. 거래 한도 확인
        trade_value = amount * (price or 1)
        if not self._check_trade_limits(trade_value):
            logger.error(f"Trade value ${trade_value} exceeds safety limits")
            return {'error': 'Amount exceeds safety limits', 'safety_check': 'failed'}

        # 6. 잔고 확인
        try:
            account_info = self._get_account_info_internal()
            if account_info:
                available_usdt = float(account_info.get('availableBalance', 0))
                if available_usdt < float(self.min_balance_required):
                    logger.error(f"Insufficient balance: ${available_usdt} < ${self.min_balance_required}")
                    return {'error': 'Insufficient balance', 'safety_check': 'failed'}
        except Exception as e:
            logger.error(f"Failed to check balance: {e}")
            return {'error': 'Balance check failed', 'safety_check': 'failed'}

        # 7. 실제 주문 실행 (모든 안전 검사 통과)
        try:
            self._rate_limit()
            logger.warning(f"EXECUTING REAL ORDER: {side} {amount} {symbol} (${trade_value})")

            if order_type == 'market':
                if side == 'buy':
                    order = self.exchange.create_market_buy_order(symbol, amount)
                else:
                    order = self.exchange.create_market_sell_order(symbol, amount)
            else:
                if side == 'buy':
                    order = self.exchange.create_limit_buy_order(symbol, amount, price)
                else:
                    order = self.exchange.create_limit_sell_order(symbol, amount, price)

            logger.info(f"REAL ORDER PLACED: {order['id']}")
            return order

        except Exception as e:
            logger.error(f"Failed to place real order: {e}")
            return {'error': str(e), 'safety_check': 'passed_but_execution_failed'}

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """주문 취소"""
        if not self.exchange:
            return False

        try:
            self._rate_limit()
            result = self.exchange.cancel_order(order_id, symbol)
            logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    def get_order_history(self, symbol: str = None, limit: int = 100) -> Optional[List[Dict[str, Any]]]:
        """주문 내역 조회"""
        if not self.exchange:
            return []

        try:
            self._rate_limit()
            if symbol:
                orders = self.exchange.fetch_orders(symbol, limit=limit)
            else:
                orders = self.exchange.fetch_orders(limit=limit)

            return [
                {
                    'id': order['id'],
                    'symbol': order['symbol'],
                    'side': order['side'],
                    'amount': order['amount'],
                    'price': order['price'],
                    'status': order['status'],
                    'timestamp': order['timestamp']
                }
                for order in orders
            ]
        except Exception as e:
            logger.error(f"Failed to get order history: {e}")
            return []

    # ===== Minimum Order Amount System =====

    def get_min_order_amounts(self) -> Dict[str, float]:
        """거래소 심볼별 최소 주문 금액 조회"""
        try:
            self._rate_limit()

            if not self.exchange:
                # 기본값 반환 (오프라인 시)
                return {
                    'BTC/USDT': 10.0,
                    'ETH/USDT': 10.0,
                    'XRP/USDT': 8.0,
                    'ADA/USDT': 5.0,
                    'DOT/USDT': 5.0,
                    'BNB/USDT': 10.0,
                    'SOL/USDT': 5.0,
                    'MATIC/USDT': 5.0
                }

            # Exchange info에서 최소 주문 금액 조회
            markets = self.exchange.load_markets()
            min_amounts = {}

            # 주요 거래쌍들
            major_symbols = ['BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'ADA/USDT',
                           'DOT/USDT', 'BNB/USDT', 'SOL/USDT', 'MATIC/USDT']

            for symbol in major_symbols:
                if symbol in markets:
                    market = markets[symbol]

                    # CCXT의 limits 정보에서 최소 주문 금액 추출
                    min_cost = market.get('limits', {}).get('cost', {}).get('min')
                    min_amount = market.get('limits', {}).get('amount', {}).get('min')

                    if min_cost:
                        # 최소 비용(USDT 기준)을 직접 사용
                        min_amounts[symbol] = float(min_cost)
                    elif min_amount:
                        # 최소 수량이 있으면 현재 가격으로 계산
                        try:
                            current_price = self.get_current_price(symbol)
                            if current_price:
                                calculated_min = float(min_amount) * current_price['price']
                                min_amounts[symbol] = max(calculated_min, 5.0)  # 최소 5 USDT
                            else:
                                min_amounts[symbol] = 10.0  # 기본값
                        except:
                            min_amounts[symbol] = 10.0
                    else:
                        # 정보가 없으면 기본값 사용
                        min_amounts[symbol] = 10.0
                else:
                    # 마켓 정보가 없으면 기본값
                    min_amounts[symbol] = 10.0

            logger.info(f"Retrieved minimum order amounts: {min_amounts}")
            return min_amounts

        except Exception as e:
            logger.error(f"Failed to get minimum order amounts: {e}")
            # 에러 시 기본값 반환
            return {
                'BTC/USDT': 10.0,
                'ETH/USDT': 10.0,
                'XRP/USDT': 8.0,
                'ADA/USDT': 5.0,
                'DOT/USDT': 5.0,
                'BNB/USDT': 10.0,
                'SOL/USDT': 5.0,
                'MATIC/USDT': 5.0
            }

    def get_symbol_min_amount(self, symbol: str) -> float:
        """특정 심볼의 최소 주문 금액 조회"""
        min_amounts = self.get_min_order_amounts()
        return min_amounts.get(symbol, 10.0)  # 기본값 10 USDT

    def validate_order_amount(self, symbol: str, amount: float) -> Dict[str, Any]:
        """주문 금액 유효성 검사"""
        min_amount = self.get_symbol_min_amount(symbol)

        validation_result = {
            'valid': True,
            'min_amount': min_amount,
            'suggested_amount': None,
            'message': None
        }

        if amount < min_amount:
            validation_result['valid'] = False
            validation_result['suggested_amount'] = min_amount * 1.1  # 10% 여유
            validation_result['message'] = f"{symbol} 최소 주문 금액은 ${min_amount:.1f} USDT입니다"

        return validation_result

    # ===== Additional Required Methods =====

    def get_account_balance(self) -> Optional[Dict[str, Any]]:
        """계정 잔고 조회"""
        account_info = self._get_account_info_internal()
        if account_info:
            return {
                'total_usdt': float(account_info.get('totalWalletBalance', 0)),
                'available_usdt': float(account_info.get('availableBalance', 0)),
                'balances': account_info.get('balances', [])
            }
        return None

    def get_historical_data(self, symbol: str, interval: str, limit: int = 100) -> Optional[List[Dict[str, Any]]]:
        """과거 데이터 조회"""
        klines = self.get_klines(symbol, interval, limit)
        if klines:
            return [
                {
                    'timestamp': kline[0],
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
                }
                for kline in klines
            ]
        return None

    def get_liquidation_price(self, symbol: str) -> Optional[float]:
        """청산 가격 조회 (현물 거래에서는 해당 없음)"""
        return None

    def get_position_info(self, symbol: str = None) -> Optional[Dict[str, Any]]:
        """포지션 정보 조회"""
        positions = self.get_positions()
        if symbol:
            for pos in positions or []:
                if pos.get('symbol') == symbol:
                    return pos
            return None
        else:
            return {'positions': positions or []}

    def test_connection(self) -> bool:
        """연결 테스트"""
        return self.is_connected()

    def set_leverage(self, symbol: str, leverage: int = 1) -> bool:
        """레버리지 설정"""
        if not self.exchange:
            return False

        try:
            self._rate_limit()
            result = self.exchange.set_leverage(leverage, symbol)
            logger.info(f"Leverage set to {leverage}x for {symbol}")
            return True
        except Exception as e:
            logger.error(f"Failed to set leverage for {symbol}: {e}")
            return False

    def set_margin_mode(self, symbol: str, margin_mode: str = 'isolated') -> bool:
        """마진 모드 설정 (isolated/crossed)"""
        if not self.exchange:
            return False

        try:
            self._rate_limit()
            # Binance API에서 marginType 설정
            result = self.exchange.set_margin_mode(margin_mode, symbol)
            logger.info(f"Margin mode set to {margin_mode} for {symbol}")
            return True
        except Exception as e:
            logger.error(f"Failed to set margin mode for {symbol}: {e}")
            return False


# 싱글톤 인스턴스 관리
_mainnet_connector_instance = None

def get_mainnet_connector(api_key: str = None, secret_key: str = None) -> BinanceMainnetConnector:
    """메인넷 커넥터 싱글톤 인스턴스 반환"""
    global _mainnet_connector_instance

    if _mainnet_connector_instance is None or (api_key and secret_key):
        _mainnet_connector_instance = BinanceMainnetConnector(api_key, secret_key)

    return _mainnet_connector_instance