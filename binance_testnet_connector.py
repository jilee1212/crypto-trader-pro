#!/usr/bin/env python3
"""
Binance Testnet Connector for Crypto Trader Pro
안전한 API 키 관리와 HMAC-SHA-256 서명 방식 구현

보안 주의사항:
- 실제 거래에서는 절대 API 키를 하드코딩하지 마세요
- 환경변수 또는 st.secrets 사용 권장
- 테스트넷 환경에서만 사용하세요
"""

import os
import time
import hmac
import hashlib
import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import streamlit as st

class BinanceTestnetConnector:
    """
    바이낸스 테스트넷 API 연동 클래스

    Features:
    - HMAC-SHA-256 서명 방식
    - 안전한 API 키 관리
    - 계좌 정보 조회
    - 기본 주문 기능
    - 에러 핸들링 및 재시도 로직
    """

    def __init__(self):
        """Initialize Binance Testnet Connector"""
        self.base_url = "https://testnet.binance.vision/api/v3"
        self.api_key = None
        self.secret_key = None
        self.session = requests.Session()

        # Load API credentials
        self._load_credentials()

        # Request headers
        if self.api_key:
            self.session.headers.update({
                'X-MBX-APIKEY': self.api_key,
                'Content-Type': 'application/json'
            })

    def _load_credentials(self):
        """안전한 API 키 로드 (환경변수 > st.secrets > 설정)"""
        try:
            # 1. 환경변수에서 로드 시도
            self.api_key = os.getenv('BINANCE_TESTNET_API_KEY')
            self.secret_key = os.getenv('BINANCE_TESTNET_SECRET_KEY')

            # 2. Streamlit secrets에서 로드 시도
            if not self.api_key and hasattr(st, 'secrets'):
                try:
                    self.api_key = st.secrets.get('BINANCE_TESTNET_API_KEY')
                    self.secret_key = st.secrets.get('BINANCE_TESTNET_SECRET_KEY')
                except:
                    pass

            # 3. 설정 파일에서 로드 시도 (개발 환경용)
            if not self.api_key:
                config_path = 'config/binance_testnet.json'
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        self.api_key = config.get('api_key')
                        self.secret_key = config.get('secret_key')

            # 4. 임시 개발용 (주의: 실제 환경에서는 사용 금지)
            if not self.api_key:
                print("[WARNING] API 키가 환경변수나 secrets에서 발견되지 않음")
                print("[INFO] 개발 환경용 임시 키 사용 (테스트넷만)")
                # 제공된 테스트넷 키 (공개된 상태이므로 테스트넷에서만 사용)
                self.api_key = "nCAJHNJGtid957ZqL40jXaTXsFUOdmjYJ48TVzHXHbngNjHPYgyxb74yrwDktcWm"
                self.secret_key = "Uecil9dVewFengFmSKO6MnaNCLEZLLQkLN8Dqlaiw3wLfXgNp5gnxhIkHw1lTHJg"

        except Exception as e:
            print(f"[ERROR] API 키 로드 실패: {e}")

    def _generate_signature(self, query_string: str) -> str:
        """HMAC-SHA-256 서명 생성"""
        if not self.secret_key:
            raise ValueError("Secret key not available")

        return hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _create_signed_params(self, params: Dict[str, Any]) -> str:
        """서명된 파라미터 문자열 생성"""
        # 타임스탬프 추가
        params['timestamp'] = int(time.time() * 1000)

        # 쿼리 스트링 생성
        query_string = '&'.join([f"{key}={value}" for key, value in params.items()])

        # 서명 생성 및 추가
        signature = self._generate_signature(query_string)

        return f"{query_string}&signature={signature}"

    def _make_request(self, endpoint: str, method: str = 'GET', params: Dict = None, signed: bool = False, retries: int = 3) -> Optional[Dict]:
        """API 요청 수행 (재시도 로직 포함)"""
        if params is None:
            params = {}

        url = f"{self.base_url}/{endpoint}"

        for attempt in range(retries):
            try:
                if signed:
                    # 서명된 요청
                    query_string = self._create_signed_params(params)

                    if method == 'GET':
                        response = self.session.get(f"{url}?{query_string}")
                    elif method == 'POST':
                        response = self.session.post(f"{url}?{query_string}")
                    else:
                        raise ValueError(f"Unsupported method: {method}")
                else:
                    # 공개 요청
                    if method == 'GET':
                        response = self.session.get(url, params=params)
                    elif method == 'POST':
                        response = self.session.post(url, json=params)
                    else:
                        raise ValueError(f"Unsupported method: {method}")

                # 응답 처리
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    # Rate limit - 잠시 대기 후 재시도
                    print(f"[WARNING] Rate limit hit, waiting before retry {attempt + 1}/{retries}")
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    print(f"[ERROR] API request failed: {response.status_code} - {response.text}")
                    return None

            except Exception as e:
                print(f"[ERROR] Request attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(1)
                    continue
                else:
                    return None

        return None

    def test_connection(self) -> Dict[str, Any]:
        """API 연결 테스트"""
        try:
            # 1. 서버 시간 확인 (공개 API)
            server_time = self._make_request('time')
            if not server_time:
                return {
                    'success': False,
                    'error': 'Failed to connect to Binance Testnet',
                    'details': 'Server time request failed'
                }

            # 2. Exchange 정보 확인 (공개 API)
            exchange_info = self._make_request('exchangeInfo')
            if not exchange_info:
                return {
                    'success': False,
                    'error': 'Failed to get exchange info',
                    'details': 'Exchange info request failed'
                }

            # 3. 계좌 정보 확인 (인증 필요)
            account_info = self.get_account_info()
            if not account_info.get('success', False):
                return {
                    'success': False,
                    'error': 'Failed to authenticate',
                    'details': 'Account info request failed - check API keys'
                }

            return {
                'success': True,
                'server_time': datetime.fromtimestamp(server_time['serverTime'] / 1000),
                'exchange': exchange_info['exchangeFilters'][:3],  # Show first 3 filters
                'account_type': account_info.get('account_type', 'Unknown'),
                'permissions': account_info.get('permissions', []),
                'message': 'Binance Testnet connection successful!'
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Connection test failed: {str(e)}',
                'details': 'Unexpected error during connection test'
            }

    def get_account_info(self) -> Dict[str, Any]:
        """계좌 정보 조회"""
        try:
            if not self.api_key or not self.secret_key:
                return {
                    'success': False,
                    'error': 'API credentials not available'
                }

            result = self._make_request('account', signed=True)

            if result:
                # 잔고 정보 처리
                balances = []
                for balance in result.get('balances', []):
                    free = float(balance['free'])
                    locked = float(balance['locked'])
                    total = free + locked

                    if total > 0:  # 잔고가 있는 자산만 표시
                        balances.append({
                            'asset': balance['asset'],
                            'free': free,
                            'locked': locked,
                            'total': total
                        })

                return {
                    'success': True,
                    'account_type': result.get('accountType', 'Unknown'),
                    'permissions': result.get('permissions', []),
                    'can_trade': result.get('canTrade', False),
                    'can_withdraw': result.get('canWithdraw', False),
                    'can_deposit': result.get('canDeposit', False),
                    'balances': balances,
                    'total_assets': len(balances)
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to fetch account information'
                }

        except Exception as e:
            return {
                'success': False,
                'error': f'Account info error: {str(e)}'
            }

    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """심볼 정보 조회"""
        try:
            exchange_info = self._make_request('exchangeInfo')
            if not exchange_info:
                return {'success': False, 'error': 'Failed to get exchange info'}

            # 특정 심볼 찾기
            for symbol_info in exchange_info.get('symbols', []):
                if symbol_info['symbol'] == symbol.upper():
                    return {
                        'success': True,
                        'symbol': symbol_info['symbol'],
                        'status': symbol_info['status'],
                        'base_asset': symbol_info['baseAsset'],
                        'quote_asset': symbol_info['quoteAsset'],
                        'is_spot_trading_allowed': symbol_info.get('isSpotTradingAllowed', False),
                        'permissions': symbol_info.get('permissions', []),
                        'filters': symbol_info.get('filters', [])
                    }

            return {
                'success': False,
                'error': f'Symbol {symbol} not found'
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Symbol info error: {str(e)}'
            }

    def get_current_price(self, symbol: str) -> Dict[str, Any]:
        """현재 가격 조회"""
        try:
            result = self._make_request('ticker/price', params={'symbol': symbol.upper()})

            if result:
                return {
                    'success': True,
                    'symbol': result['symbol'],
                    'price': float(result['price']),
                    'timestamp': datetime.now()
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to get price for {symbol}'
                }

        except Exception as e:
            return {
                'success': False,
                'error': f'Price fetch error: {str(e)}'
            }

    def place_market_order(self, symbol: str, side: str, quantity: float) -> Dict[str, Any]:
        """시장가 주문 실행"""
        try:
            if not self.api_key or not self.secret_key:
                return {
                    'success': False,
                    'error': 'API credentials not available'
                }

            # 주문 파라미터 준비
            params = {
                'symbol': symbol.upper(),
                'side': side.upper(),  # BUY 또는 SELL
                'type': 'MARKET',
                'quantity': f"{quantity:.5f}".rstrip('0').rstrip('.')
            }

            result = self._make_request('order', method='POST', params=params, signed=True)

            if result:
                return {
                    'success': True,
                    'order_id': result.get('orderId'),
                    'symbol': result.get('symbol'),
                    'side': result.get('side'),
                    'type': result.get('type'),
                    'quantity': float(result.get('executedQty', 0)),
                    'price': float(result.get('price', 0)),
                    'status': result.get('status'),
                    'transaction_time': datetime.fromtimestamp(result.get('transactTime', 0) / 1000),
                    'fills': result.get('fills', [])
                }
            else:
                return {
                    'success': False,
                    'error': 'Order placement failed'
                }

        except Exception as e:
            return {
                'success': False,
                'error': f'Order error: {str(e)}'
            }

    def place_limit_order(self, symbol: str, side: str, quantity: float, price: float) -> Dict[str, Any]:
        """지정가 주문 실행"""
        try:
            if not self.api_key or not self.secret_key:
                return {
                    'success': False,
                    'error': 'API credentials not available'
                }

            # 주문 파라미터 준비
            params = {
                'symbol': symbol.upper(),
                'side': side.upper(),  # BUY 또는 SELL
                'type': 'LIMIT',
                'timeInForce': 'GTC',  # Good Till Cancelled
                'quantity': f"{quantity:.5f}".rstrip('0').rstrip('.'),
                'price': f"{price:.2f}".rstrip('0').rstrip('.')
            }

            result = self._make_request('order', method='POST', params=params, signed=True)

            if result:
                return {
                    'success': True,
                    'order_id': result.get('orderId'),
                    'symbol': result.get('symbol'),
                    'side': result.get('side'),
                    'type': result.get('type'),
                    'quantity': float(result.get('origQty', 0)),
                    'price': float(result.get('price', 0)),
                    'status': result.get('status'),
                    'transaction_time': datetime.fromtimestamp(result.get('transactTime', 0) / 1000)
                }
            else:
                return {
                    'success': False,
                    'error': 'Limit order placement failed'
                }

        except Exception as e:
            return {
                'success': False,
                'error': f'Limit order error: {str(e)}'
            }

    def get_order_status(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """주문 상태 조회"""
        try:
            params = {
                'symbol': symbol.upper(),
                'orderId': order_id
            }

            result = self._make_request('order', params=params, signed=True)

            if result:
                return {
                    'success': True,
                    'order_id': result.get('orderId'),
                    'symbol': result.get('symbol'),
                    'status': result.get('status'),
                    'type': result.get('type'),
                    'side': result.get('side'),
                    'quantity': float(result.get('origQty', 0)),
                    'executed_quantity': float(result.get('executedQty', 0)),
                    'price': float(result.get('price', 0)),
                    'time': datetime.fromtimestamp(result.get('time', 0) / 1000)
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to get order status'
                }

        except Exception as e:
            return {
                'success': False,
                'error': f'Order status error: {str(e)}'
            }

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """주문 취소"""
        try:
            params = {
                'symbol': symbol.upper(),
                'orderId': order_id
            }

            result = self._make_request('order', method='DELETE', params=params, signed=True)

            if result:
                return {
                    'success': True,
                    'order_id': result.get('orderId'),
                    'symbol': result.get('symbol'),
                    'status': result.get('status'),
                    'message': 'Order cancelled successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to cancel order'
                }

        except Exception as e:
            return {
                'success': False,
                'error': f'Cancel order error: {str(e)}'
            }

    def get_open_orders(self, symbol: str = None) -> Dict[str, Any]:
        """미체결 주문 조회"""
        try:
            params = {}
            if symbol:
                params['symbol'] = symbol.upper()

            result = self._make_request('openOrders', params=params, signed=True)

            if isinstance(result, list):
                orders = []
                for order in result:
                    orders.append({
                        'order_id': order.get('orderId'),
                        'symbol': order.get('symbol'),
                        'side': order.get('side'),
                        'type': order.get('type'),
                        'quantity': float(order.get('origQty', 0)),
                        'price': float(order.get('price', 0)),
                        'status': order.get('status'),
                        'time': datetime.fromtimestamp(order.get('time', 0) / 1000)
                    })

                return {
                    'success': True,
                    'orders': orders,
                    'total_orders': len(orders)
                }
            else:
                return {
                    'success': False,
                    'error': 'Invalid response format'
                }

        except Exception as e:
            return {
                'success': False,
                'error': f'Open orders error: {str(e)}'
            }

    def get_exchange_info(self) -> List[str]:
        """거래 가능한 심볼 목록 조회"""
        try:
            result = self._make_request('exchangeInfo')
            if result and 'symbols' in result:
                symbols = [symbol['symbol'] for symbol in result['symbols']
                          if symbol['status'] == 'TRADING']
                return symbols
            return []
        except Exception as e:
            print(f"[ERROR] Exchange info error: {str(e)}")
            return []

    def get_server_time(self) -> Optional[int]:
        """서버 시간 조회"""
        try:
            result = self._make_request('time')
            if result and 'serverTime' in result:
                return result['serverTime']
            return None
        except Exception as e:
            print(f"[ERROR] Server time error: {str(e)}")
            return None

    def get_order_book(self, symbol: str, limit: int = 100) -> Optional[Dict[str, Any]]:
        """호가창 조회"""
        try:
            params = {
                'symbol': symbol.upper(),
                'limit': limit
            }
            result = self._make_request('depth', params=params)
            if result:
                return {
                    'bids': result.get('bids', []),
                    'asks': result.get('asks', []),
                    'last_update_id': result.get('lastUpdateId')
                }
            return None
        except Exception as e:
            print(f"[ERROR] Order book error: {str(e)}")
            return None

# 안전한 설정 파일 생성 헬퍼 함수
def create_safe_config_template():
    """안전한 설정 파일 템플릿 생성"""
    config_dir = 'config'
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    template = {
        "api_key": "YOUR_BINANCE_TESTNET_API_KEY_HERE",
        "secret_key": "YOUR_BINANCE_TESTNET_SECRET_KEY_HERE",
        "note": "테스트넷 전용 - 실제 자금과 연결되지 않음"
    }

    template_path = os.path.join(config_dir, 'binance_testnet_template.json')
    with open(template_path, 'w') as f:
        json.dump(template, f, indent=2)

    # .gitignore에 실제 설정 파일 추가
    gitignore_path = '.gitignore'
    gitignore_entry = 'config/binance_testnet.json\n'

    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            content = f.read()
        if gitignore_entry.strip() not in content:
            with open(gitignore_path, 'a') as f:
                f.write('\n' + gitignore_entry)
    else:
        with open(gitignore_path, 'w') as f:
            f.write(gitignore_entry)

    print(f"[INFO] Configuration template created: {template_path}")
    print(f"[INFO] Add your API keys to config/binance_testnet.json")
    print(f"[INFO] File added to .gitignore for security")

if __name__ == "__main__":
    # 테스트 실행
    print("=== Binance Testnet Connector Test ===")

    connector = BinanceTestnetConnector()

    # 연결 테스트
    test_result = connector.test_connection()
    print("Connection Test:", test_result)

    if test_result.get('success'):
        # 계좌 정보 테스트
        account_info = connector.get_account_info()
        print("Account Info:", account_info)

        # 가격 조회 테스트
        price_info = connector.get_current_price('BTCUSDT')
        print("BTC Price:", price_info)

    # 안전한 설정 파일 템플릿 생성
    create_safe_config_template()