#!/usr/bin/env python3
"""
Binance Standard Connector for Crypto Trader Pro
python-binance 라이브러리의 표준 패턴을 사용한 안정적인 API 연동

Features:
- python-binance 라이브러리 기반
- 표준 에러 핸들링
- 테스트넷 지원
- 계좌 정보 조회
- 주문 관리
- 실시간 가격 데이터
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from decimal import Decimal

from binance.client import Client
from binance.enums import *
from binance.exceptions import BinanceAPIException, BinanceOrderException, BinanceRequestException

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BinanceStandardConnector:
    """
    python-binance 라이브러리를 사용한 표준 바이낸스 연동 클래스

    Best Practices:
    - 공식 라이브러리 사용으로 안정성 확보
    - 표준 예외 처리
    - 테스트넷 지원
    - 타입 힌팅 및 문서화
    """

    def __init__(self, api_key: str = None, api_secret: str = None, testnet: bool = True):
        """
        바이낸스 클라이언트 초기화

        Args:
            api_key: 바이낸스 API 키
            api_secret: 바이낸스 API 시크릿
            testnet: 테스트넷 사용 여부 (기본값: True)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.client = None

        if api_key and api_secret:
            self._initialize_client()

    def _initialize_client(self) -> None:
        """바이낸스 클라이언트 초기화"""
        try:
            self.client = Client(
                api_key=self.api_key,
                api_secret=self.api_secret,
                testnet=self.testnet
            )
            logger.info(f"바이낸스 클라이언트 초기화 완료 (테스트넷: {self.testnet})")
        except Exception as e:
            logger.error(f"바이낸스 클라이언트 초기화 실패: {e}")
            raise

    def set_credentials(self, api_key: str, api_secret: str) -> bool:
        """API 자격 증명 설정"""
        try:
            self.api_key = api_key
            self.api_secret = api_secret
            self._initialize_client()
            return True
        except Exception as e:
            logger.error(f"API 자격 증명 설정 실패: {e}")
            return False

    def test_connectivity(self) -> Dict[str, Any]:
        """연결 테스트 및 서버 시간 확인"""
        try:
            if not self.client:
                return {
                    'success': False,
                    'error': 'API 클라이언트가 초기화되지 않았습니다.'
                }

            # 서버 시간 확인
            server_time = self.client.get_server_time()

            # 계좌 정보 확인 (인증 테스트)
            account = self.client.get_account()

            return {
                'success': True,
                'server_time': server_time,
                'account_type': account.get('accountType', 'Unknown'),
                'can_trade': account.get('canTrade', False),
                'permissions': account.get('permissions', [])
            }

        except BinanceAPIException as e:
            return {
                'success': False,
                'error': f'Binance API 오류: {e.message}',
                'code': e.code,
                'status_code': e.status_code
            }
        except BinanceRequestException as e:
            return {
                'success': False,
                'error': f'네트워크 오류: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'연결 테스트 오류: {str(e)}'
            }

    def get_account_info(self, api_key: str = None, api_secret: str = None) -> Dict[str, Any]:
        """
        계좌 정보 조회 (표준 패턴)

        Args:
            api_key: API 키 (선택사항, 없으면 기본 키 사용)
            api_secret: API 시크릿 (선택사항, 없으면 기본 키 사용)

        Returns:
            계좌 정보 딕셔너리
        """
        try:
            # 임시 클라이언트 사용 (매개변수로 키가 제공된 경우)
            client = self.client
            if api_key and api_secret:
                client = Client(api_key=api_key, api_secret=api_secret, testnet=self.testnet)

            if not client:
                return {
                    'success': False,
                    'error': 'API 클라이언트가 초기화되지 않았습니다.'
                }

            # 계좌 정보 조회
            account = client.get_account()

            # USDT 중심으로 잔고 정보 정리
            balances = []
            total_btc_value = Decimal('0')

            for balance in account['balances']:
                free = Decimal(balance['free'])
                locked = Decimal(balance['locked'])
                total = free + locked

                if total > 0:  # 잔고가 있는 자산만 포함
                    balance_info = {
                        'asset': balance['asset'],
                        'free': float(free),
                        'locked': float(locked),
                        'total': float(total)
                    }

                    # USDT 가치 계산 (간단한 버전)
                    if balance['asset'] == 'USDT':
                        balance_info['usdt_value'] = float(total)
                    else:
                        # 다른 코인의 USDT 가치는 현재 가격으로 계산
                        try:
                            symbol = f"{balance['asset']}USDT"
                            ticker = client.get_symbol_ticker(symbol=symbol)
                            price = Decimal(ticker['price'])
                            balance_info['usdt_value'] = float(total * price)
                        except:
                            balance_info['usdt_value'] = 0.0

                    balances.append(balance_info)

            return {
                'success': True,
                'data': {
                    'account_type': account.get('accountType', 'SPOT'),
                    'can_trade': account.get('canTrade', False),
                    'can_withdraw': account.get('canWithdraw', False),
                    'can_deposit': account.get('canDeposit', False),
                    'permissions': account.get('permissions', []),
                    'balances': balances,
                    'total_assets': len(balances),
                    'update_time': account.get('updateTime', int(time.time() * 1000))
                }
            }

        except BinanceAPIException as e:
            logger.error(f"Binance API 오류: {e.message}")
            return {
                'success': False,
                'error': f'API 오류: {e.message}',
                'code': e.code
            }
        except BinanceRequestException as e:
            logger.error(f"네트워크 오류: {str(e)}")
            return {
                'success': False,
                'error': f'네트워크 오류: {str(e)}'
            }
        except Exception as e:
            logger.error(f"계좌 정보 조회 오류: {str(e)}")
            return {
                'success': False,
                'error': f'계좌 정보 조회 오류: {str(e)}'
            }

    def get_open_orders(self, api_key: str = None, api_secret: str = None, symbol: str = None) -> Dict[str, Any]:
        """
        미체결 주문 조회 (표준 패턴)

        Args:
            api_key: API 키 (선택사항)
            api_secret: API 시크릿 (선택사항)
            symbol: 심볼 (선택사항, 없으면 모든 심볼)

        Returns:
            미체결 주문 목록
        """
        try:
            # 임시 클라이언트 사용 (매개변수로 키가 제공된 경우)
            client = self.client
            if api_key and api_secret:
                client = Client(api_key=api_key, api_secret=api_secret, testnet=self.testnet)

            if not client:
                return {
                    'success': False,
                    'error': 'API 클라이언트가 초기화되지 않았습니다.'
                }

            # 미체결 주문 조회
            orders = client.get_open_orders(symbol=symbol)

            # USDT 페어만 필터링
            usdt_orders = []
            for order in orders:
                if order['symbol'].endswith('USDT'):
                    order_info = {
                        'order_id': order['orderId'],
                        'symbol': order['symbol'],
                        'side': order['side'],
                        'type': order['type'],
                        'quantity': float(order['origQty']),
                        'price': float(order['price']) if order['price'] != '0.00000000' else 0.0,
                        'executed_qty': float(order['executedQty']),
                        'status': order['status'],
                        'time': datetime.fromtimestamp(order['time'] / 1000),
                        'update_time': datetime.fromtimestamp(order['updateTime'] / 1000)
                    }
                    usdt_orders.append(order_info)

            return {
                'success': True,
                'data': usdt_orders,
                'total_orders': len(usdt_orders)
            }

        except BinanceAPIException as e:
            logger.error(f"Binance API 오류: {e.message}")
            return {
                'success': False,
                'error': f'API 오류: {e.message}',
                'code': e.code
            }
        except Exception as e:
            logger.error(f"미체결 주문 조회 오류: {str(e)}")
            return {
                'success': False,
                'error': f'미체결 주문 조회 오류: {str(e)}'
            }

    def get_symbol_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        심볼 가격 정보 조회

        Args:
            symbol: 심볼 (예: BTCUSDT)

        Returns:
            가격 정보
        """
        try:
            if not self.client:
                # 가격 정보는 인증 없이도 조회 가능
                client = Client(testnet=self.testnet)
            else:
                client = self.client

            ticker = client.get_symbol_ticker(symbol=symbol)

            return {
                'success': True,
                'data': {
                    'symbol': ticker['symbol'],
                    'price': float(ticker['price'])
                }
            }

        except BinanceAPIException as e:
            return {
                'success': False,
                'error': f'API 오류: {e.message}',
                'code': e.code
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'가격 조회 오류: {str(e)}'
            }

    def get_24hr_ticker(self, symbol: str = None) -> Dict[str, Any]:
        """
        24시간 가격 변동 정보 조회

        Args:
            symbol: 심볼 (선택사항, 없으면 모든 심볼)

        Returns:
            24시간 가격 변동 정보
        """
        try:
            if not self.client:
                client = Client(testnet=self.testnet)
            else:
                client = self.client

            if symbol:
                ticker = client.get_ticker(symbol=symbol)
                tickers = [ticker]
            else:
                tickers = client.get_ticker()

            # USDT 페어만 필터링
            usdt_tickers = []
            for ticker in tickers:
                if ticker['symbol'].endswith('USDT'):
                    ticker_info = {
                        'symbol': ticker['symbol'],
                        'price_change': float(ticker['priceChange']),
                        'price_change_percent': float(ticker['priceChangePercent']),
                        'last_price': float(ticker['lastPrice']),
                        'high_price': float(ticker['highPrice']),
                        'low_price': float(ticker['lowPrice']),
                        'volume': float(ticker['volume']),
                        'quote_volume': float(ticker['quoteVolume'])
                    }
                    usdt_tickers.append(ticker_info)

            return {
                'success': True,
                'data': usdt_tickers if not symbol else usdt_tickers[0] if usdt_tickers else None
            }

        except BinanceAPIException as e:
            return {
                'success': False,
                'error': f'API 오류: {e.message}',
                'code': e.code
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'가격 정보 조회 오류: {str(e)}'
            }

    def get_exchange_info(self) -> Dict[str, Any]:
        """거래소 정보 조회"""
        try:
            if not self.client:
                client = Client(testnet=self.testnet)
            else:
                client = self.client

            info = client.get_exchange_info()

            # USDT 페어만 필터링
            usdt_symbols = []
            for symbol_info in info['symbols']:
                if (symbol_info['symbol'].endswith('USDT') and
                    symbol_info['status'] == 'TRADING'):
                    usdt_symbols.append({
                        'symbol': symbol_info['symbol'],
                        'base_asset': symbol_info['baseAsset'],
                        'quote_asset': symbol_info['quoteAsset'],
                        'status': symbol_info['status']
                    })

            return {
                'success': True,
                'data': {
                    'timezone': info['timezone'],
                    'server_time': info['serverTime'],
                    'symbols': usdt_symbols,
                    'total_symbols': len(usdt_symbols)
                }
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'거래소 정보 조회 오류: {str(e)}'
            }


# 편의를 위한 함수들
def create_testnet_client(api_key: str, api_secret: str) -> BinanceStandardConnector:
    """테스트넷 클라이언트 생성"""
    return BinanceStandardConnector(api_key=api_key, api_secret=api_secret, testnet=True)

def create_mainnet_client(api_key: str, api_secret: str) -> BinanceStandardConnector:
    """메인넷 클라이언트 생성"""
    return BinanceStandardConnector(api_key=api_key, api_secret=api_secret, testnet=False)

def test_api_connection(api_key: str, api_secret: str, testnet: bool = True) -> Dict[str, Any]:
    """API 연결 테스트"""
    try:
        connector = BinanceStandardConnector(api_key=api_key, api_secret=api_secret, testnet=testnet)
        return connector.test_connectivity()
    except Exception as e:
        return {
            'success': False,
            'error': f'연결 테스트 오류: {str(e)}'
        }


if __name__ == "__main__":
    # 간단한 테스트
    print("=== Binance Standard Connector 테스트 ===")

    # 인증 없이 가능한 테스트
    connector = BinanceStandardConnector(testnet=True)

    # 거래소 정보 조회
    exchange_info = connector.get_exchange_info()
    if exchange_info['success']:
        print(f"USDT 페어 수: {exchange_info['data']['total_symbols']}")

    # BTC 가격 조회
    btc_price = connector.get_symbol_ticker('BTCUSDT')
    if btc_price['success']:
        print(f"BTC 가격: ${btc_price['data']['price']:,.2f}")

    print("테스트 완료!")