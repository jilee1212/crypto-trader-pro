"""
📊 MarketMonitor - 실시간 시장 모니터링

시장 데이터 수집 및 모니터링을 담당하는 컴포넌트
- 실시간 가격 데이터 수집
- 시장 이상 감지
- 데이터 검증 및 정제
- 시장 상태 분석
"""

import time
import ccxt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
import asyncio
from dataclasses import dataclass
import pandas as pd
import numpy as np

@dataclass
class MarketData:
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    change_24h: float = 0.0
    volatility: float = 0.0

@dataclass
class MarketAnomalyAlert:
    type: str
    symbol: str
    message: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    timestamp: datetime
    data: Dict[str, Any]

class MarketMonitor:
    """
    📊 실시간 시장 모니터링

    기능:
    - 실시간 시장 데이터 수집
    - 시장 이상 감지
    - 데이터 품질 검증
    - 볼라틸리티 분석
    """

    def __init__(self, config_manager):
        """마켓 모니터 초기화"""
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager

        # 설정 로드
        self.symbols = config_manager.get_trading_symbols()
        self.config = config_manager.get_config()

        # 거래소 API 초기화
        self.exchange = None
        self._initialize_exchange()

        # 데이터 캐시
        self.price_cache = {}
        self.historical_data = {}
        self.last_update = {}

        # 이상 감지 설정
        self.anomaly_thresholds = {
            'price_spike': 0.05,  # 5% 급등/급락
            'volume_spike': 3.0,  # 평균 대비 3배 거래량
            'bid_ask_spread': 0.01,  # 1% 스프레드
            'connection_timeout': 30  # 30초
        }

        self.logger.info("MarketMonitor 초기화 완료")

    def _initialize_exchange(self):
        """거래소 API 초기화"""
        try:
            # 기본적으로 Binance 사용 (무료 API)
            self.exchange = ccxt.binance({
                'apiKey': '',  # 읽기 전용이므로 API 키 불필요
                'secret': '',
                'sandbox': False,
                'rateLimit': 1200,
                'timeout': 30000,
                'enableRateLimit': True,
            })

            # 연결 테스트
            self.exchange.load_markets()
            self.logger.info("거래소 API 연결 성공")

        except Exception as e:
            self.logger.error(f"거래소 API 초기화 실패: {e}")
            self.exchange = None

    def test_data_feed(self) -> bool:
        """
        데이터 피드 연결 테스트

        Returns:
            bool: 연결 상태
        """
        try:
            if not self.exchange:
                return False

            # 테스트 데이터 요청
            ticker = self.exchange.fetch_ticker('BTC/USDT')
            if ticker and 'last' in ticker:
                self.logger.info("데이터 피드 연결 정상")
                return True

            return False

        except Exception as e:
            self.logger.error(f"데이터 피드 테스트 실패: {e}")
            return False

    def collect_data(self) -> List[MarketData]:
        """
        시장 데이터 수집

        Returns:
            List[MarketData]: 수집된 시장 데이터
        """
        market_data = []

        try:
            for symbol in self.symbols:
                data = self._fetch_symbol_data(symbol)
                if data:
                    market_data.append(data)

            self.logger.debug(f"{len(market_data)}개 심볼 데이터 수집 완료")
            return market_data

        except Exception as e:
            self.logger.error(f"시장 데이터 수집 실패: {e}")
            return []

    def _fetch_symbol_data(self, symbol: str) -> Optional[MarketData]:
        """개별 심볼 데이터 수집"""
        try:
            # 현재 가격 정보
            ticker = self.exchange.fetch_ticker(symbol)

            # OHLCV 데이터 (5분봉)
            ohlcv = self.exchange.fetch_ohlcv(symbol, '5m', limit=20)

            if not ticker or not ohlcv:
                return None

            # 최신 캔들 데이터
            latest_candle = ohlcv[-1]

            # 24시간 변화율 계산
            change_24h = ticker.get('percentage', 0.0) or 0.0

            # 볼라틸리티 계산 (최근 20개 캔들 기준)
            volatility = self._calculate_volatility(ohlcv)

            # MarketData 객체 생성
            market_data = MarketData(
                symbol=symbol,
                timestamp=datetime.fromtimestamp(latest_candle[0] / 1000),
                open=latest_candle[1],
                high=latest_candle[2],
                low=latest_candle[3],
                close=latest_candle[4],
                volume=latest_candle[5],
                change_24h=change_24h,
                volatility=volatility
            )

            # 캐시 업데이트
            self.price_cache[symbol] = market_data
            self.last_update[symbol] = datetime.now()

            # 이상 감지
            anomalies = self._detect_anomalies(market_data)
            if anomalies:
                self._handle_anomalies(anomalies)

            return market_data

        except Exception as e:
            self.logger.error(f"{symbol} 데이터 수집 실패: {e}")
            return None

    def _calculate_volatility(self, ohlcv_data: List) -> float:
        """볼라틸리티 계산 (표준편차 기반)"""
        try:
            if len(ohlcv_data) < 2:
                return 0.0

            closes = [candle[4] for candle in ohlcv_data]
            returns = []

            for i in range(1, len(closes)):
                return_rate = (closes[i] - closes[i-1]) / closes[i-1]
                returns.append(return_rate)

            if returns:
                volatility = np.std(returns) * np.sqrt(288)  # 5분봉 -> 일간 변환
                return float(volatility)

            return 0.0

        except Exception:
            return 0.0

    def _detect_anomalies(self, data: MarketData) -> List[MarketAnomalyAlert]:
        """시장 이상 감지"""
        anomalies = []

        try:
            # 1. 급격한 가격 변동 감지
            if abs(data.change_24h) > self.anomaly_thresholds['price_spike'] * 100:
                severity = "HIGH" if abs(data.change_24h) > 10 else "MEDIUM"
                anomalies.append(MarketAnomalyAlert(
                    type="PRICE_SPIKE",
                    symbol=data.symbol,
                    message=f"급격한 가격 변동: {data.change_24h:.2f}%",
                    severity=severity,
                    timestamp=datetime.now(),
                    data={"change_24h": data.change_24h}
                ))

            # 2. 높은 볼라틸리티 감지
            if data.volatility > 0.5:  # 50% 이상 일간 변동성
                anomalies.append(MarketAnomalyAlert(
                    type="HIGH_VOLATILITY",
                    symbol=data.symbol,
                    message=f"높은 변동성 감지: {data.volatility:.2f}",
                    severity="MEDIUM",
                    timestamp=datetime.now(),
                    data={"volatility": data.volatility}
                ))

            # 3. 거래량 급증 감지
            avg_volume = self._get_average_volume(data.symbol)
            if avg_volume and data.volume > avg_volume * self.anomaly_thresholds['volume_spike']:
                anomalies.append(MarketAnomalyAlert(
                    type="VOLUME_SPIKE",
                    symbol=data.symbol,
                    message=f"거래량 급증: {data.volume / avg_volume:.1f}배",
                    severity="MEDIUM",
                    timestamp=datetime.now(),
                    data={"volume_ratio": data.volume / avg_volume}
                ))

        except Exception as e:
            self.logger.error(f"이상 감지 오류: {e}")

        return anomalies

    def _get_average_volume(self, symbol: str) -> Optional[float]:
        """평균 거래량 계산"""
        try:
            # 최근 24시간 평균 거래량 (실제 구현에서는 DB에서 조회)
            if symbol in self.historical_data:
                volumes = self.historical_data[symbol]
                return sum(volumes) / len(volumes) if volumes else None
            return None

        except Exception:
            return None

    def _handle_anomalies(self, anomalies: List[MarketAnomalyAlert]):
        """이상 상황 처리"""
        for anomaly in anomalies:
            # 로그 기록
            if anomaly.severity in ["HIGH", "CRITICAL"]:
                self.logger.warning(f"시장 이상 감지: {anomaly.message}")
            else:
                self.logger.info(f"시장 이상 감지: {anomaly.message}")

            # TODO: 알림 시스템 연동
            # self.notification_manager.send_alert(anomaly)

    def get_current_prices(self) -> Dict[str, float]:
        """
        현재 가격 조회

        Returns:
            Dict: 심볼별 현재 가격
        """
        prices = {}
        for symbol, data in self.price_cache.items():
            if data:
                prices[symbol] = data.close
        return prices

    def get_market_status(self) -> Dict[str, Any]:
        """
        시장 상태 조회

        Returns:
            Dict: 시장 상태 정보
        """
        return {
            'symbols_monitored': len(self.symbols),
            'data_freshness': self._check_data_freshness(),
            'api_status': 'CONNECTED' if self.exchange else 'DISCONNECTED',
            'last_update': max(self.last_update.values()) if self.last_update else None,
            'average_volatility': self._calculate_average_volatility()
        }

    def _check_data_freshness(self) -> Dict[str, str]:
        """데이터 신선도 확인"""
        freshness = {}
        now = datetime.now()

        for symbol, last_time in self.last_update.items():
            age = (now - last_time).total_seconds()
            if age < 60:
                freshness[symbol] = "FRESH"
            elif age < 300:
                freshness[symbol] = "STALE"
            else:
                freshness[symbol] = "OLD"

        return freshness

    def _calculate_average_volatility(self) -> float:
        """평균 변동성 계산"""
        try:
            volatilities = [data.volatility for data in self.price_cache.values() if data]
            return sum(volatilities) / len(volatilities) if volatilities else 0.0
        except Exception:
            return 0.0

    def cleanup(self):
        """리소스 정리"""
        try:
            if self.exchange:
                self.exchange.close()
            self.logger.info("MarketMonitor 리소스 정리 완료")
        except Exception as e:
            self.logger.error(f"리소스 정리 실패: {e}")