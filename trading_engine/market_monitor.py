"""
Market Data Monitor for Background Trading Bot
실시간 시장 데이터 모니터링 및 관리
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import ccxt
import pandas as pd
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class MarketDataMonitor:
    """시장 데이터 모니터링 클래스"""

    def __init__(self):
        """마켓 데이터 모니터 초기화"""
        self.exchanges = {
            'binance': ccxt.binance({
                'enableRateLimit': True,
                'sandbox': True,  # 테스트넷 모드
            })
        }

        # 시장 데이터 저장
        self.market_data: Dict[str, Dict] = {}
        self.price_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.last_update_time = datetime.utcnow()
        self.update_interval = 10  # 10초마다 업데이트

        # 모니터링할 심볼 목록
        self.symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT']

        logger.info("Market Data Monitor initialized")

    async def update_market_data(self):
        """시장 데이터 업데이트"""
        try:
            current_time = datetime.utcnow()

            # 업데이트 간격 체크
            if current_time - self.last_update_time < timedelta(seconds=self.update_interval):
                return

            # 각 거래소별 데이터 업데이트
            for exchange_name, exchange in self.exchanges.items():
                await self._update_exchange_data(exchange_name, exchange)

            self.last_update_time = current_time

        except Exception as e:
            logger.error(f"Market data update error: {e}")

    async def _update_exchange_data(self, exchange_name: str, exchange):
        """특정 거래소 데이터 업데이트"""
        try:
            for symbol in self.symbols:
                try:
                    # 현재 가격 및 티커 데이터
                    ticker = exchange.fetch_ticker(symbol)

                    # OHLCV 데이터 (최근 100개)
                    ohlcv = exchange.fetch_ohlcv(symbol, '1m', limit=100)

                    # 시장 데이터 구성
                    market_data = {
                        'symbol': symbol,
                        'exchange': exchange_name,
                        'timestamp': datetime.utcnow(),
                        'price': ticker['last'],
                        'bid': ticker['bid'],
                        'ask': ticker['ask'],
                        'volume': ticker['quoteVolume'],
                        'change_24h': ticker['percentage'],
                        'high_24h': ticker['high'],
                        'low_24h': ticker['low'],
                        'ticker': ticker,
                        'ohlcv': ohlcv
                    }

                    # 기술적 분석 지표 계산
                    technical_data = self._calculate_technical_indicators(symbol, ohlcv)
                    market_data.update(technical_data)

                    # 데이터 저장
                    self.market_data[f"{exchange_name}:{symbol}"] = market_data

                    # 가격 히스토리 저장
                    self.price_history[f"{exchange_name}:{symbol}"].append({
                        'timestamp': datetime.utcnow(),
                        'price': ticker['last'],
                        'volume': ticker['quoteVolume']
                    })

                except Exception as e:
                    logger.error(f"Error updating {symbol} on {exchange_name}: {e}")

        except Exception as e:
            logger.error(f"Error updating exchange {exchange_name}: {e}")

    def _calculate_technical_indicators(self, symbol: str, ohlcv: List) -> Dict[str, Any]:
        """기술적 분석 지표 계산"""
        try:
            if not ohlcv or len(ohlcv) < 20:
                return {'technical_indicators': {}}

            # OHLCV 데이터를 DataFrame으로 변환
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            indicators = {}

            # RSI 계산
            indicators['rsi'] = self._calculate_rsi(df['close'])

            # 이동평균 계산
            indicators['sma_20'] = df['close'].rolling(window=20).mean().iloc[-1]
            indicators['ema_20'] = df['close'].ewm(span=20).mean().iloc[-1]

            # MACD 계산
            macd_data = self._calculate_macd(df['close'])
            indicators.update(macd_data)

            # 볼린저 밴드
            bb_data = self._calculate_bollinger_bands(df['close'])
            indicators.update(bb_data)

            # 거래량 분석
            indicators['volume_sma_20'] = df['volume'].rolling(window=20).mean().iloc[-1]
            indicators['volume_ratio'] = df['volume'].iloc[-1] / indicators['volume_sma_20'] if indicators['volume_sma_20'] > 0 else 1

            # 변동성 계산
            indicators['volatility'] = df['close'].pct_change().rolling(window=20).std().iloc[-1] * 100

            # 가격 변화율
            indicators['price_change_1h'] = ((df['close'].iloc[-1] - df['close'].iloc[-60]) / df['close'].iloc[-60] * 100) if len(df) >= 60 else 0
            indicators['price_change_4h'] = ((df['close'].iloc[-1] - df['close'].iloc[-240]) / df['close'].iloc[-240] * 100) if len(df) >= 240 else 0

            return {'technical_indicators': indicators}

        except Exception as e:
            logger.error(f"Technical indicators calculation error for {symbol}: {e}")
            return {'technical_indicators': {}}

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """RSI 계산"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50

        except Exception:
            return 50

    def _calculate_macd(self, prices: pd.Series) -> Dict[str, float]:
        """MACD 계산"""
        try:
            ema_12 = prices.ewm(span=12).mean()
            ema_26 = prices.ewm(span=26).mean()
            macd_line = ema_12 - ema_26
            signal_line = macd_line.ewm(span=9).mean()
            histogram = macd_line - signal_line

            return {
                'macd_line': macd_line.iloc[-1],
                'macd_signal': signal_line.iloc[-1],
                'macd_histogram': histogram.iloc[-1]
            }

        except Exception:
            return {
                'macd_line': 0,
                'macd_signal': 0,
                'macd_histogram': 0
            }

    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2) -> Dict[str, float]:
        """볼린저 밴드 계산"""
        try:
            sma = prices.rolling(window=period).mean()
            std = prices.rolling(window=period).std()

            upper_band = sma + (std * std_dev)
            lower_band = sma - (std * std_dev)

            return {
                'bb_upper': upper_band.iloc[-1],
                'bb_middle': sma.iloc[-1],
                'bb_lower': lower_band.iloc[-1],
                'bb_width': ((upper_band.iloc[-1] - lower_band.iloc[-1]) / sma.iloc[-1]) * 100
            }

        except Exception:
            return {
                'bb_upper': 0,
                'bb_middle': 0,
                'bb_lower': 0,
                'bb_width': 0
            }

    def get_market_data(self, exchange: str, symbol: str) -> Optional[Dict]:
        """특정 심볼의 시장 데이터 조회"""
        key = f"{exchange}:{symbol}"
        return self.market_data.get(key)

    def get_all_market_data(self) -> Dict[str, Dict]:
        """모든 시장 데이터 조회"""
        return self.market_data.copy()

    def get_price_history(self, exchange: str, symbol: str, limit: int = 100) -> List[Dict]:
        """가격 히스토리 조회"""
        key = f"{exchange}:{symbol}"
        history = list(self.price_history[key])
        return history[-limit:] if history else []

    def is_market_open(self, exchange: str = 'binance') -> bool:
        """시장 개장 여부 확인 (암호화폐는 24시간이므로 항상 True)"""
        return True

    def get_market_summary(self) -> Dict[str, Any]:
        """시장 요약 정보"""
        try:
            summary = {
                'total_symbols': len(self.market_data),
                'last_update': self.last_update_time,
                'symbols': {}
            }

            for key, data in self.market_data.items():
                exchange, symbol = key.split(':')
                summary['symbols'][symbol] = {
                    'exchange': exchange,
                    'price': data['price'],
                    'change_24h': data['change_24h'],
                    'volume': data['volume'],
                    'rsi': data.get('technical_indicators', {}).get('rsi', 0),
                    'last_update': data['timestamp']
                }

            return summary

        except Exception as e:
            logger.error(f"Market summary error: {e}")
            return {}

    def detect_anomalies(self) -> List[Dict]:
        """시장 이상 징후 감지"""
        anomalies = []

        try:
            for key, data in self.market_data.items():
                exchange, symbol = key.split(':')

                # 급격한 가격 변동 감지
                if abs(data.get('change_24h', 0)) > 10:  # 10% 이상 변동
                    anomalies.append({
                        'type': 'high_volatility',
                        'symbol': symbol,
                        'exchange': exchange,
                        'change_24h': data['change_24h'],
                        'timestamp': data['timestamp']
                    })

                # 비정상적 거래량 감지
                indicators = data.get('technical_indicators', {})
                volume_ratio = indicators.get('volume_ratio', 1)

                if volume_ratio > 3:  # 평균 거래량의 3배 이상
                    anomalies.append({
                        'type': 'high_volume',
                        'symbol': symbol,
                        'exchange': exchange,
                        'volume_ratio': volume_ratio,
                        'timestamp': data['timestamp']
                    })

                # RSI 극값 감지
                rsi = indicators.get('rsi', 50)
                if rsi > 80 or rsi < 20:
                    anomalies.append({
                        'type': 'rsi_extreme',
                        'symbol': symbol,
                        'exchange': exchange,
                        'rsi': rsi,
                        'condition': 'overbought' if rsi > 80 else 'oversold',
                        'timestamp': data['timestamp']
                    })

        except Exception as e:
            logger.error(f"Anomaly detection error: {e}")

        return anomalies

    def get_status(self) -> Dict[str, Any]:
        """모니터링 상태 조회"""
        return {
            'is_running': True,
            'last_update_time': self.last_update_time,
            'update_interval': self.update_interval,
            'monitored_symbols': len(self.symbols),
            'data_points': len(self.market_data),
            'exchanges': list(self.exchanges.keys()),
            'symbols': self.symbols
        }