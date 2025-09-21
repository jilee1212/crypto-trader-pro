#!/usr/bin/env python3
"""
Real Market Data Module
실시간 시장 데이터 및 현재 가격 조회 모듈
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import ccxt

class RealMarketDataFetcher:
    """실시간 시장 데이터 조회 클래스"""

    def __init__(self):
        self.binance = ccxt.binance()
        self.coingecko_url = "https://api.coingecko.com/api/v3"

    def get_current_price(self, symbol):
        """현재 가격 조회"""
        try:
            # Binance에서 현재 가격 조회
            if symbol.upper() == 'BTC':
                ticker = self.binance.fetch_ticker('BTC/USDT')
            elif symbol.upper() == 'ETH':
                ticker = self.binance.fetch_ticker('ETH/USDT')
            else:
                return None

            return {
                'symbol': symbol.upper(),
                'price': float(ticker['last']),
                'change_24h': float(ticker['percentage']),
                'volume_24h': float(ticker['baseVolume']),
                'high_24h': float(ticker['high']),
                'low_24h': float(ticker['low']),
                'timestamp': datetime.now()
            }
        except Exception as e:
            print(f"Binance 가격 조회 실패: {e}")
            return self._get_coingecko_price(symbol)

    def _get_coingecko_price(self, symbol):
        """CoinGecko에서 가격 조회 (백업)"""
        try:
            coin_id = 'bitcoin' if symbol.upper() == 'BTC' else 'ethereum'
            url = f"{self.coingecko_url}/simple/price"
            params = {
                'ids': coin_id,
                'vs_currencies': 'usd',
                'include_24hr_change': 'true',
                'include_24hr_vol': 'true'
            }

            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            coin_data = data[coin_id]
            return {
                'symbol': symbol.upper(),
                'price': float(coin_data['usd']),
                'change_24h': float(coin_data.get('usd_24h_change', 0)),
                'volume_24h': float(coin_data.get('usd_24h_vol', 0)),
                'high_24h': None,
                'low_24h': None,
                'timestamp': datetime.now()
            }
        except Exception as e:
            print(f"CoinGecko 가격 조회 실패: {e}")
            return None

    def get_real_ohlcv_data(self, symbol, timeframe='1h', limit=100):
        """실시간 OHLCV 데이터 조회"""
        try:
            # Binance에서 OHLCV 데이터 조회
            if symbol.upper() == 'BTC':
                pair = 'BTC/USDT'
            elif symbol.upper() == 'ETH':
                pair = 'ETH/USDT'
            else:
                return None

            ohlcv = self.binance.fetch_ohlcv(pair, timeframe, limit=limit)

            # DataFrame으로 변환
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            return df

        except Exception as e:
            print(f"실시간 OHLCV 데이터 조회 실패: {e}")
            return self._generate_mock_data(symbol, limit)

    def _generate_mock_data(self, symbol, limit):
        """모의 데이터 생성 (백업)"""
        try:
            # 현재 가격 기준으로 모의 데이터 생성
            current_price_data = self.get_current_price(symbol)
            if not current_price_data:
                base_price = 50000 if symbol.upper() == 'BTC' else 3000
            else:
                base_price = current_price_data['price']

            # 시간 생성
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=limit)
            time_range = pd.date_range(start=start_time, end=end_time, periods=limit)

            # 가격 변동 생성
            np.random.seed(int(time.time()) % 1000)
            price_changes = np.random.normal(0, 0.01, limit)  # 1% 변동성
            prices = [base_price]

            for change in price_changes[1:]:
                new_price = prices[-1] * (1 + change)
                prices.append(new_price)

            # OHLCV 데이터 생성
            data = []
            for i, (timestamp, close_price) in enumerate(zip(time_range, prices)):
                open_price = prices[i-1] if i > 0 else close_price
                high_price = close_price * (1 + abs(np.random.normal(0, 0.005)))
                low_price = close_price * (1 - abs(np.random.normal(0, 0.005)))
                volume = np.random.uniform(1000, 10000)

                data.append({
                    'timestamp': timestamp,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': volume
                })

            return pd.DataFrame(data)

        except Exception as e:
            print(f"모의 데이터 생성 실패: {e}")
            return None

    def get_market_summary(self):
        """시장 요약 정보"""
        try:
            # 주요 코인들의 현재 정보
            btc_data = self.get_current_price('BTC')
            eth_data = self.get_current_price('ETH')

            # 시장 공포/탐욕 지수 (간단 버전)
            fear_greed_index = self._calculate_fear_greed_index(btc_data, eth_data)

            return {
                'btc': btc_data,
                'eth': eth_data,
                'fear_greed_index': fear_greed_index,
                'market_trend': self._analyze_market_trend(btc_data, eth_data),
                'last_updated': datetime.now()
            }
        except Exception as e:
            print(f"시장 요약 조회 실패: {e}")
            return None

    def _calculate_fear_greed_index(self, btc_data, eth_data):
        """간단한 공포/탐욕 지수 계산"""
        try:
            if not btc_data or not eth_data:
                return 50

            # 24시간 변화율 기반 계산
            btc_change = btc_data.get('change_24h', 0)
            eth_change = eth_data.get('change_24h', 0)

            avg_change = (btc_change + eth_change) / 2

            # -10% ~ +10% 범위를 0~100으로 매핑
            normalized = ((avg_change + 10) / 20) * 100
            return max(0, min(100, normalized))

        except Exception:
            return 50

    def _analyze_market_trend(self, btc_data, eth_data):
        """시장 트렌드 분석"""
        try:
            if not btc_data or not eth_data:
                return "NEUTRAL"

            btc_change = btc_data.get('change_24h', 0)
            eth_change = eth_data.get('change_24h', 0)

            avg_change = (btc_change + eth_change) / 2

            if avg_change > 3:
                return "STRONG_BULLISH"
            elif avg_change > 1:
                return "BULLISH"
            elif avg_change < -3:
                return "STRONG_BEARISH"
            elif avg_change < -1:
                return "BEARISH"
            else:
                return "NEUTRAL"

        except Exception:
            return "NEUTRAL"

class EnhancedBinanceConnector:
    """향상된 Binance 연결 클래스"""

    def __init__(self, api_key, secret_key, testnet=True):
        self.api_key = api_key
        self.secret_key = secret_key
        self.testnet = testnet

        try:
            self.exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': secret_key,
                'sandbox': testnet,
                'options': {
                    'defaultType': 'future',
                }
            })

            # 실제 잔고 조회 테스트
            self.account_info = self._get_account_info()

        except Exception as e:
            print(f"Binance 연결 실패: {e}")
            self.exchange = None
            self.account_info = None

    def _get_account_info(self):
        """계좌 정보 조회"""
        try:
            balance = self.exchange.fetch_balance()
            return {
                'total_balance': balance.get('USDT', {}).get('total', 0),
                'free_balance': balance.get('USDT', {}).get('free', 0),
                'used_balance': balance.get('USDT', {}).get('used', 0),
                'last_updated': datetime.now()
            }
        except Exception as e:
            print(f"계좌 정보 조회 실패: {e}")
            return None

    def get_real_positions(self):
        """실제 포지션 조회"""
        try:
            if not self.exchange:
                return {'success': False, 'error': 'Exchange 연결되지 않음'}

            positions = self.exchange.fetch_positions()
            active_positions = [pos for pos in positions if float(pos.get('contracts', 0)) != 0]

            total_unrealized = sum(float(pos.get('unrealizedPnl', 0)) for pos in active_positions)

            return {
                'success': True,
                'active_positions': len(active_positions),
                'total_unrealized_pnl': total_unrealized,
                'positions': active_positions,
                'account_info': self.account_info
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def execute_real_order(self, symbol, side, quantity, order_type='MARKET'):
        """실제 주문 실행"""
        try:
            if not self.exchange:
                return {'success': False, 'error': 'Exchange 연결되지 않음'}

            # 주문 실행
            if order_type == 'MARKET':
                order = self.exchange.create_market_order(symbol, side.lower(), quantity)
            else:
                return {'success': False, 'error': '지정가 주문은 추후 구현 예정'}

            return {
                'success': True,
                'order_id': order.get('id'),
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'status': order.get('status'),
                'filled': order.get('filled', 0),
                'remaining': order.get('remaining', 0),
                'order_info': order
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_order_history(self, symbol=None, limit=50):
        """주문 기록 조회"""
        try:
            if not self.exchange:
                return {'success': False, 'error': 'Exchange 연결되지 않음'}

            if symbol:
                orders = self.exchange.fetch_orders(symbol, limit=limit)
            else:
                # 모든 심볼의 주문 기록 (제한적)
                orders = []
                for sym in ['BTC/USDT', 'ETH/USDT']:
                    try:
                        sym_orders = self.exchange.fetch_orders(sym, limit=limit//2)
                        orders.extend(sym_orders)
                    except:
                        continue

            return {
                'success': True,
                'orders': orders,
                'total_orders': len(orders)
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}