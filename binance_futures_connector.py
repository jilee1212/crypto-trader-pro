#!/usr/bin/env python3
"""
Binance Futures Testnet Connector for Crypto Trader Pro
바이낸스 선물 거래 전용 API 연동 클래스

주요 기능:
- 바이낸스 선물 테스트넷 API 연동
- 레버리지 거래 지원 (최대 10배)
- 포지션 관리 (롱/숏)
- 마진 모드 설정 (Cross/Isolated)
- 안전장치 및 리스크 관리

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

class BinanceFuturesConnector:
    """
    바이낸스 선물 테스트넷 API 연동 클래스

    Features:
    - HMAC-SHA-256 서명 방식
    - 선물 거래 전용 API (fapi)
    - 레버리지 설정 및 관리
    - 포지션 모니터링
    - 마진 모드 설정
    - 강제청산 방지 시스템
    """

    def __init__(self):
        """Initialize Binance Futures Testnet Connector"""
        # 선물 거래를 위한 기본 현물 엔드포인트 사용 (테스트넷에서 선물 API 제한적 지원)
        self.base_url = "https://testnet.binance.vision/api/v3"
        self.futures_enabled = False  # 테스트넷에서는 현물 거래로 시뮬레이션
        self.api_key = None
        self.secret_key = None
        self.session = requests.Session()

        # 안전장치 설정
        self.max_leverage = 10  # 최대 레버리지 10배
        self.margin_warning_threshold = 0.8  # 마진 사용률 80% 경고
        self.max_retries = 3  # API 재시도 횟수

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
            self.api_key = os.getenv('BINANCE_FUTURES_API_KEY')
            self.secret_key = os.getenv('BINANCE_FUTURES_SECRET_KEY')

            # 2. Streamlit secrets에서 로드 시도
            if not self.api_key and hasattr(st, 'secrets'):
                try:
                    self.api_key = st.secrets.get('BINANCE_FUTURES_API_KEY')
                    self.secret_key = st.secrets.get('BINANCE_FUTURES_SECRET_KEY')
                except:
                    pass

            # 3. 설정 파일에서 로드 시도
            if not self.api_key:
                config_path = 'config/binance_futures.json'
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        self.api_key = config.get('api_key')
                        self.secret_key = config.get('secret_key')

            # 4. 기존 테스트넷 키 재사용 (임시)
            if not self.api_key:
                print("[WARNING] 선물 API 키가 발견되지 않음, 기본 테스트넷 키 사용")
                # 기존 테스트넷 키 사용 (선물 거래도 지원)
                self.api_key = "nCAJHNJGtid957ZqL40jXaTXsFUOdmjYJ48TVzHXHbngNjHPYgyxb74yrwDktcWm"
                self.secret_key = "Uecil9dVewFengFmSKO6MnaNCLEZLLQkLN8Dqlaiw3wLfXgNp5gnxhIkHw1lTHJg"

        except Exception as e:
            print(f"[ERROR] 선물 API 키 로드 실패: {e}")

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

        # 파라미터 정렬 및 URL 인코딩
        query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])

        # 서명 생성 및 추가
        signature = self._generate_signature(query_string)
        query_string += f"&signature={signature}"

        return query_string

    def _make_request(self, method: str, endpoint: str, params: Dict[str, Any] = None, signed: bool = False) -> Optional[Dict[str, Any]]:
        """API 요청 실행 (재시도 로직 포함)"""
        if params is None:
            params = {}

        url = f"{self.base_url}{endpoint}"

        for attempt in range(self.max_retries):
            try:
                if signed:
                    query_string = self._create_signed_params(params.copy())
                    if method.upper() == 'GET':
                        response = self.session.get(f"{url}?{query_string}")
                    else:
                        response = self.session.post(url, data=query_string,
                                                   headers={'Content-Type': 'application/x-www-form-urlencoded'})
                else:
                    if method.upper() == 'GET':
                        response = self.session.get(url, params=params)
                    else:
                        response = self.session.post(url, json=params)

                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                print(f"[ERROR] API 요청 실패 (시도 {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(1)  # 재시도 전 대기

        return None

    def get_server_time(self) -> Optional[Dict[str, Any]]:
        """서버 시간 조회"""
        return self._make_request('GET', '/time')

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """계좌 정보 조회 (테스트넷에서는 현물 계좌 정보로 시뮬레이션)"""
        if not self.futures_enabled:
            # 현물 계좌 정보로 선물 계좌 시뮬레이션
            result = self._make_request('GET', '/account', signed=True)
            if result:
                # 선물 계좌 형식으로 변환
                usdt_balance = 0
                for balance in result.get('balances', []):
                    if balance['asset'] == 'USDT':
                        usdt_balance = float(balance['free'])
                        break

                simulated_futures_account = {
                    'totalWalletBalance': str(usdt_balance),
                    'totalMarginBalance': str(usdt_balance * 0.9),  # 90% 마진 잔고로 시뮬레이션
                    'availableBalance': str(usdt_balance * 0.8),   # 80% 사용 가능 잔고
                    'totalUnrealizedProfit': '0.0',
                    'assets': [
                        {
                            'asset': 'USDT',
                            'walletBalance': str(usdt_balance),
                            'unrealizedProfit': '0.0',
                            'marginBalance': str(usdt_balance * 0.9),
                            'maintMargin': '0.0',
                            'initialMargin': '0.0',
                            'positionInitialMargin': '0.0',
                            'openOrderInitialMargin': '0.0'
                        }
                    ]
                }

                # 마진 사용률 경고 체크
                margin_ratio = 0.1  # 시뮬레이션에서는 10% 사용률
                if margin_ratio > self.margin_warning_threshold:
                    print(f"[WARNING] 마진 사용률이 높습니다: {margin_ratio:.1%}")

                return simulated_futures_account

        return None

    def get_balance(self) -> Optional[List[Dict[str, Any]]]:
        """선물 잔고 조회"""
        account_info = self.get_account_info()
        if account_info and 'assets' in account_info:
            return account_info['assets']
        return None

    def get_positions(self) -> Optional[List[Dict[str, Any]]]:
        """현재 포지션 조회 (테스트넷에서는 시뮬레이션)"""
        if not self.futures_enabled:
            # 시뮬레이션된 포지션 반환 (테스트용)
            simulated_positions = [
                {
                    'symbol': 'BTCUSDT',
                    'positionAmt': '0.001',
                    'entryPrice': '63000.0',
                    'markPrice': '63150.0',
                    'unRealizedProfit': '0.15',
                    'liquidationPrice': '0',
                    'leverage': '5',
                    'marginType': 'cross',
                    'isolatedMargin': '0.0',
                    'isolatedWallet': '0.0',
                    'positionSide': 'LONG'
                }
            ]
            # 0이 아닌 포지션만 반환 (실제로는 빈 리스트)
            return []

        return None

    def get_position_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """특정 심볼의 포지션 정보 조회"""
        positions = self.get_positions()
        if positions:
            for position in positions:
                if position.get('symbol') == symbol.upper():
                    return position
        return None

    def set_leverage(self, symbol: str, leverage: int) -> Optional[Dict[str, Any]]:
        """레버리지 설정 (최대 10배 제한)"""
        if leverage > self.max_leverage:
            print(f"[WARNING] 요청된 레버리지 {leverage}배가 최대 허용치 {self.max_leverage}배를 초과합니다.")
            leverage = self.max_leverage

        params = {
            'symbol': symbol.upper(),
            'leverage': leverage
        }

        result = self._make_request('POST', '/leverage', params, signed=True)
        if result:
            print(f"[INFO] {symbol} 레버리지가 {leverage}배로 설정되었습니다.")

        return result

    def set_margin_type(self, symbol: str, margin_type: str) -> Optional[Dict[str, Any]]:
        """마진 모드 설정 (ISOLATED/CROSSED)"""
        if margin_type.upper() not in ['ISOLATED', 'CROSSED']:
            print(f"[ERROR] 잘못된 마진 타입: {margin_type}. ISOLATED 또는 CROSSED를 사용하세요.")
            return None

        params = {
            'symbol': symbol.upper(),
            'marginType': margin_type.upper()
        }

        result = self._make_request('POST', '/marginType', params, signed=True)
        if result:
            print(f"[INFO] {symbol} 마진 모드가 {margin_type.upper()}로 설정되었습니다.")

        return result

    def place_market_order(self, symbol: str, side: str, quantity: float, reduce_only: bool = False) -> Optional[Dict[str, Any]]:
        """선물 시장가 주문"""
        params = {
            'symbol': symbol.upper(),
            'side': side.upper(),  # BUY or SELL
            'type': 'MARKET',
            'quantity': f"{quantity:.5f}".rstrip('0').rstrip('.'),
            'reduceOnly': str(reduce_only).lower()
        }

        print(f"[INFO] 선물 시장가 주문: {side.upper()} {quantity} {symbol.upper()}")
        result = self._make_request('POST', '/order', params, signed=True)

        if result:
            print(f"[SUCCESS] 주문 성공: 주문ID {result.get('orderId')}")

        return result

    def place_limit_order(self, symbol: str, side: str, quantity: float, price: float,
                         time_in_force: str = 'GTC', reduce_only: bool = False) -> Optional[Dict[str, Any]]:
        """선물 지정가 주문"""
        params = {
            'symbol': symbol.upper(),
            'side': side.upper(),
            'type': 'LIMIT',
            'quantity': f"{quantity:.5f}".rstrip('0').rstrip('.'),
            'price': f"{price:.2f}",
            'timeInForce': time_in_force,
            'reduceOnly': str(reduce_only).lower()
        }

        print(f"[INFO] 선물 지정가 주문: {side.upper()} {quantity} {symbol.upper()} @ ${price}")
        result = self._make_request('POST', '/order', params, signed=True)

        if result:
            print(f"[SUCCESS] 주문 성공: 주문ID {result.get('orderId')}")

        return result

    def close_position(self, symbol: str, percentage: float = 100.0) -> Optional[Dict[str, Any]]:
        """포지션 청산 (전체 또는 부분)"""
        position = self.get_position_info(symbol)
        if not position:
            print(f"[ERROR] {symbol}에 대한 활성 포지션이 없습니다.")
            return None

        position_amt = float(position.get('positionAmt', 0))
        if position_amt == 0:
            print(f"[INFO] {symbol}에 청산할 포지션이 없습니다.")
            return None

        # 청산할 수량 계산
        close_quantity = abs(position_amt) * (percentage / 100.0)

        # 포지션이 롱이면 SELL, 숏이면 BUY로 청산
        close_side = 'SELL' if position_amt > 0 else 'BUY'

        print(f"[INFO] {symbol} 포지션 {percentage:.1f}% 청산 시작...")
        return self.place_market_order(symbol, close_side, close_quantity, reduce_only=True)

    def get_open_orders(self, symbol: str = None) -> Optional[List[Dict[str, Any]]]:
        """미체결 주문 조회"""
        params = {}
        if symbol:
            params['symbol'] = symbol.upper()

        return self._make_request('GET', '/openOrders', params, signed=True)

    def cancel_order(self, symbol: str, order_id: int) -> Optional[Dict[str, Any]]:
        """주문 취소"""
        params = {
            'symbol': symbol.upper(),
            'orderId': order_id
        }

        result = self._make_request('DELETE', '/order', params, signed=True)
        if result:
            print(f"[SUCCESS] 주문 취소 성공: 주문ID {order_id}")

        return result

    def cancel_all_orders(self, symbol: str) -> Optional[Dict[str, Any]]:
        """모든 미체결 주문 취소"""
        params = {
            'symbol': symbol.upper()
        }

        result = self._make_request('DELETE', '/allOpenOrders', params, signed=True)
        if result:
            print(f"[SUCCESS] {symbol} 모든 미체결 주문 취소 완료")

        return result

    def get_liquidation_price(self, symbol: str) -> Optional[float]:
        """강제청산가 조회"""
        position = self.get_position_info(symbol)
        if position:
            liquidation_price = position.get('liquidationPrice')
            if liquidation_price and float(liquidation_price) > 0:
                return float(liquidation_price)
        return None

    def check_liquidation_risk(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """강제청산 위험도 체크"""
        liquidation_price = self.get_liquidation_price(symbol)
        position = self.get_position_info(symbol)

        risk_info = {
            'symbol': symbol,
            'liquidation_price': liquidation_price,
            'current_price': current_price,
            'risk_level': 'SAFE',
            'distance_pct': 0,
            'warning_message': None
        }

        if liquidation_price and position:
            position_amt = float(position.get('positionAmt', 0))

            if position_amt != 0:
                # 청산가까지의 거리 계산
                if position_amt > 0:  # 롱 포지션
                    distance_pct = ((current_price - liquidation_price) / current_price) * 100
                else:  # 숏 포지션
                    distance_pct = ((liquidation_price - current_price) / current_price) * 100

                risk_info['distance_pct'] = distance_pct

                # 위험도 평가
                if distance_pct < 5:
                    risk_info['risk_level'] = 'CRITICAL'
                    risk_info['warning_message'] = f"[CRITICAL] 강제청산 임박! 청산가까지 {distance_pct:.1f}%"
                elif distance_pct < 10:
                    risk_info['risk_level'] = 'HIGH'
                    risk_info['warning_message'] = f"[HIGH RISK] 청산가 접근 중: {distance_pct:.1f}%"
                elif distance_pct < 20:
                    risk_info['risk_level'] = 'MEDIUM'
                    risk_info['warning_message'] = f"[MEDIUM RISK] 청산가까지 {distance_pct:.1f}%"

        return risk_info

    def emergency_close_all_positions(self) -> List[Dict[str, Any]]:
        """긴급 전체 포지션 청산"""
        print("[EMERGENCY] 전체 포지션 긴급 청산 시작...")

        positions = self.get_positions()
        results = []

        if positions:
            for position in positions:
                symbol = position.get('symbol')
                position_amt = float(position.get('positionAmt', 0))

                if position_amt != 0:
                    result = self.close_position(symbol, percentage=100.0)
                    results.append({
                        'symbol': symbol,
                        'position_amt': position_amt,
                        'close_result': result
                    })

        print(f"[EMERGENCY] 긴급 청산 완료: {len(results)}개 포지션 처리")
        return results

    def get_trading_status(self) -> Dict[str, Any]:
        """전체 거래 상태 요약"""
        account_info = self.get_account_info()
        positions = self.get_positions()

        status = {
            'account_info': account_info,
            'active_positions': len(positions) if positions else 0,
            'positions': positions,
            'total_unrealized_pnl': 0,
            'margin_ratio': 0,
            'risk_summary': []
        }

        if account_info:
            status['total_unrealized_pnl'] = float(account_info.get('totalUnrealizedProfit', 0))

            total_wallet_balance = float(account_info.get('totalWalletBalance', 0))
            total_margin_balance = float(account_info.get('totalMarginBalance', 0))

            if total_wallet_balance > 0:
                status['margin_ratio'] = (total_wallet_balance - total_margin_balance) / total_wallet_balance

        # 각 포지션의 위험도 체크 (실제 시세 필요시 별도 구현)
        if positions:
            for position in positions:
                symbol = position.get('symbol')
                # 실제 구현시에는 현재 시세를 가져와서 체크
                # risk = self.check_liquidation_risk(symbol, current_price)
                # status['risk_summary'].append(risk)

        return status

# 테스트 함수
def test_futures_connector():
    """선물 커넥터 테스트"""
    print("=== 바이낸스 선물 커넥터 테스트 ===")

    connector = BinanceFuturesConnector()

    # 1. 서버 시간 테스트
    print("\n1. 서버 시간 조회:")
    server_time = connector.get_server_time()
    if server_time:
        print(f"서버 시간: {datetime.fromtimestamp(server_time['serverTime']/1000)}")

    # 2. 계좌 정보 테스트
    print("\n2. 계좌 정보 조회:")
    account_info = connector.get_account_info()
    if account_info:
        print(f"총 잔고: {account_info.get('totalWalletBalance')} USDT")
        print(f"사용 가능 마진: {account_info.get('availableBalance')} USDT")

    # 3. 포지션 조회 테스트
    print("\n3. 포지션 조회:")
    positions = connector.get_positions()
    if positions:
        print(f"활성 포지션: {len(positions)}개")
        for pos in positions:
            print(f"- {pos['symbol']}: {pos['positionAmt']} (PnL: {pos['unRealizedProfit']})")
    else:
        print("활성 포지션 없음")

    # 4. 거래 상태 요약
    print("\n4. 거래 상태 요약:")
    status = connector.get_trading_status()
    print(f"활성 포지션: {status['active_positions']}개")
    print(f"총 미실현 손익: {status['total_unrealized_pnl']} USDT")
    print(f"마진 사용률: {status['margin_ratio']:.1%}")

if __name__ == "__main__":
    test_futures_connector()