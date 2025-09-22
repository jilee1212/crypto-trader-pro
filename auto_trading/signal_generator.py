"""
🧠 AISignalGenerator - AI 기반 신호 생성기

기존 AI 시스템과 통합하여 자동매매 신호를 생성
- 다중 지표 분석
- 신뢰도 기반 신호 필터링
- 시장 상황 고려
- 신호 품질 검증
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass
from enum import Enum

# 기존 AI 시스템 import
try:
    from ai_trading_signals import EnhancedAITradingSystem
except ImportError:
    EnhancedAITradingSystem = None

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class SignalStrength(Enum):
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    VERY_STRONG = "VERY_STRONG"

@dataclass
class TradingSignal:
    symbol: str
    signal_type: SignalType
    confidence: int  # 0-100
    strength: SignalStrength
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: Optional[float] = None
    reasoning: str = ""
    technical_data: Dict[str, Any] = None
    market_conditions: Dict[str, Any] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.technical_data is None:
            self.technical_data = {}
        if self.market_conditions is None:
            self.market_conditions = {}

class AISignalGenerator:
    """
    🧠 AI 기반 신호 생성기

    기능:
    - 기존 AI 시스템과 통합
    - 다중 지표 분석
    - 신호 품질 검증
    - 리스크 조정된 신호 생성
    """

    def __init__(self, config_manager):
        """신호 생성기 초기화"""
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager

        # 설정 로드
        self.config = config_manager.get_config()
        self.ai_settings = self.config.get('ai_settings', {})
        self.symbols = config_manager.get_trading_symbols()

        # AI 시스템 초기화
        self.ai_system = None
        self._initialize_ai_system()

        # 신호 캐시
        self.signal_cache = {}
        self.signal_history = []
        self.last_signal_time = {}

        # 성능 지표
        self.generated_signals = 0
        self.successful_predictions = 0

        # 필터링 설정
        self.confidence_threshold = self.ai_settings.get('confidence_threshold', 70)
        self.min_signal_interval = 300  # 5분

        self.logger.info("AISignalGenerator 초기화 완료")

    def _initialize_ai_system(self):
        """AI 시스템 초기화"""
        try:
            if EnhancedAITradingSystem:
                self.ai_system = EnhancedAITradingSystem()
                self.logger.info("기존 AI 시스템 연동 성공")
            else:
                self.logger.warning("AI 시스템을 찾을 수 없음 - 기본 분석기 사용")
                self._use_fallback_analyzer()

        except Exception as e:
            self.logger.error(f"AI 시스템 초기화 실패: {e}")
            self._use_fallback_analyzer()

    def _use_fallback_analyzer(self):
        """기본 분석기 사용"""
        self.ai_system = None
        self.logger.info("기본 기술적 분석기로 대체")

    async def generate_signals(self, market_data: List) -> List[TradingSignal]:
        """
        시장 데이터를 기반으로 거래 신호 생성

        Args:
            market_data: 시장 데이터 리스트

        Returns:
            List[TradingSignal]: 생성된 신호 리스트
        """
        signals = []

        try:
            for data in market_data:
                symbol = data.symbol

                # 신호 간격 체크
                if not self._should_generate_signal(symbol):
                    continue

                # AI 시스템 사용 여부에 따라 분기
                if self.ai_system:
                    signal = await self._generate_ai_signal(data)
                else:
                    signal = await self._generate_technical_signal(data)

                if signal and self._validate_signal(signal):
                    signals.append(signal)
                    self.generated_signals += 1
                    self.last_signal_time[symbol] = datetime.now()

            # 신호 후처리
            signals = self._post_process_signals(signals)

            self.logger.info(f"{len(signals)}개 신호 생성됨")
            return signals

        except Exception as e:
            self.logger.error(f"신호 생성 실패: {e}")
            return []

    async def _generate_ai_signal(self, market_data) -> Optional[TradingSignal]:
        """AI 시스템을 사용한 신호 생성"""
        try:
            symbol = market_data.symbol

            # AI 시스템에서 분석 요청
            analysis = await self._get_ai_analysis(symbol, market_data)

            if not analysis:
                return None

            # 신호 변환
            signal_type = self._convert_ai_signal(analysis.get('recommendation', 'HOLD'))
            confidence = analysis.get('confidence', 0)

            if confidence < self.confidence_threshold:
                return None

            # 신호 강도 계산
            strength = self._calculate_signal_strength(confidence, analysis)

            # 가격 목표 계산
            entry_price = market_data.close
            stop_loss = self._calculate_stop_loss(analysis, entry_price, signal_type)
            take_profit = self._calculate_take_profit(analysis, entry_price, signal_type)

            return TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                strength=strength,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reasoning=analysis.get('reasoning', ''),
                technical_data=analysis.get('technical_analysis', {}),
                market_conditions=analysis.get('market_conditions', {})
            )

        except Exception as e:
            self.logger.error(f"AI 신호 생성 실패: {e}")
            return None

    async def _get_ai_analysis(self, symbol: str, market_data) -> Optional[Dict]:
        """AI 시스템에서 분석 결과 가져오기"""
        try:
            # 실제 AI 시스템 호출 (시뮬레이션)
            # 실제 구현에서는 기존 AI 시스템의 메서드 호출

            # 기본 기술적 지표 계산
            rsi = self._calculate_rsi(market_data)
            macd = self._calculate_macd(market_data)
            bollinger = self._calculate_bollinger_bands(market_data)

            # 간단한 신호 로직
            signals = []
            confidences = []

            # RSI 기반 신호
            if rsi < 30:
                signals.append('BUY')
                confidences.append(80)
            elif rsi > 70:
                signals.append('SELL')
                confidences.append(75)

            # MACD 기반 신호
            if macd['signal'] == 'BUY':
                signals.append('BUY')
                confidences.append(70)
            elif macd['signal'] == 'SELL':
                signals.append('SELL')
                confidences.append(70)

            # 볼린저 밴드 기반 신호
            if bollinger['signal'] == 'BUY':
                signals.append('BUY')
                confidences.append(65)
            elif bollinger['signal'] == 'SELL':
                signals.append('SELL')
                confidences.append(65)

            if not signals:
                return {
                    'recommendation': 'HOLD',
                    'confidence': 50,
                    'reasoning': '명확한 신호 없음'
                }

            # 다수결 신호
            buy_count = signals.count('BUY')
            sell_count = signals.count('SELL')

            if buy_count > sell_count:
                recommendation = 'BUY'
                confidence = int(np.mean([c for i, c in enumerate(confidences) if signals[i] == 'BUY']))
            elif sell_count > buy_count:
                recommendation = 'SELL'
                confidence = int(np.mean([c for i, c in enumerate(confidences) if signals[i] == 'SELL']))
            else:
                recommendation = 'HOLD'
                confidence = 50

            return {
                'recommendation': recommendation,
                'confidence': confidence,
                'reasoning': f'RSI: {rsi:.1f}, MACD: {macd["signal"]}, BB: {bollinger["signal"]}',
                'technical_analysis': {
                    'rsi': rsi,
                    'macd': macd,
                    'bollinger_bands': bollinger
                },
                'market_conditions': {
                    'volatility': market_data.volatility,
                    'volume_change': getattr(market_data, 'volume_change', 0),
                    'trend': self._determine_trend(market_data)
                }
            }

        except Exception as e:
            self.logger.error(f"AI 분석 실패: {e}")
            return None

    async def _generate_technical_signal(self, market_data) -> Optional[TradingSignal]:
        """기본 기술적 분석 신호 생성"""
        try:
            symbol = market_data.symbol

            # 기본 지표들 계산
            rsi = self._calculate_rsi(market_data)
            macd = self._calculate_macd(market_data)

            # 간단한 신호 로직
            signal_type = SignalType.HOLD
            confidence = 50
            reasoning = "기본 기술적 분석"

            # RSI 기반 신호
            if rsi < 30:
                signal_type = SignalType.BUY
                confidence = 75
                reasoning = f"RSI 과매도 ({rsi:.1f})"
            elif rsi > 70:
                signal_type = SignalType.SELL
                confidence = 75
                reasoning = f"RSI 과매수 ({rsi:.1f})"

            if confidence < self.confidence_threshold:
                return None

            entry_price = market_data.close
            strength = self._calculate_signal_strength(confidence, {'rsi': rsi})

            return TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                strength=strength,
                entry_price=entry_price,
                reasoning=reasoning,
                technical_data={'rsi': rsi, 'macd': macd}
            )

        except Exception as e:
            self.logger.error(f"기술적 신호 생성 실패: {e}")
            return None

    def _calculate_rsi(self, market_data, period: int = 14) -> float:
        """RSI 계산 (시뮬레이션)"""
        # 실제 구현에서는 historical data 필요
        # 현재는 random 값으로 시뮬레이션
        import random
        return random.uniform(20, 80)

    def _calculate_macd(self, market_data) -> Dict[str, Any]:
        """MACD 계산 (시뮬레이션)"""
        import random
        macd_value = random.uniform(-1, 1)
        signal_line = random.uniform(-1, 1)

        return {
            'macd': macd_value,
            'signal_line': signal_line,
            'histogram': macd_value - signal_line,
            'signal': 'BUY' if macd_value > signal_line else 'SELL'
        }

    def _calculate_bollinger_bands(self, market_data) -> Dict[str, Any]:
        """볼린저 밴드 계산 (시뮬레이션)"""
        price = market_data.close
        # 시뮬레이션된 밴드
        middle = price
        upper = price * 1.02
        lower = price * 0.98

        signal = 'HOLD'
        if price <= lower:
            signal = 'BUY'
        elif price >= upper:
            signal = 'SELL'

        return {
            'upper': upper,
            'middle': middle,
            'lower': lower,
            'signal': signal,
            'position': (price - lower) / (upper - lower)
        }

    def _determine_trend(self, market_data) -> str:
        """트렌드 판단"""
        change_24h = getattr(market_data, 'change_24h', 0)

        if change_24h > 2:
            return 'BULLISH'
        elif change_24h < -2:
            return 'BEARISH'
        else:
            return 'SIDEWAYS'

    def _convert_ai_signal(self, ai_recommendation: str) -> SignalType:
        """AI 추천을 신호로 변환"""
        if ai_recommendation.upper() == 'BUY':
            return SignalType.BUY
        elif ai_recommendation.upper() == 'SELL':
            return SignalType.SELL
        else:
            return SignalType.HOLD

    def _calculate_signal_strength(self, confidence: int, analysis: Dict) -> SignalStrength:
        """신호 강도 계산"""
        if confidence >= 90:
            return SignalStrength.VERY_STRONG
        elif confidence >= 80:
            return SignalStrength.STRONG
        elif confidence >= 70:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK

    def _calculate_stop_loss(self, analysis: Dict, entry_price: float,
                           signal_type: SignalType) -> Optional[float]:
        """손절가 계산"""
        try:
            risk_config = self.config_manager.get_risk_limits()
            stop_loss_pct = risk_config.get('stop_loss', 1.5) / 100

            if signal_type == SignalType.BUY:
                return entry_price * (1 - stop_loss_pct)
            elif signal_type == SignalType.SELL:
                return entry_price * (1 + stop_loss_pct)

            return None

        except Exception:
            return None

    def _calculate_take_profit(self, analysis: Dict, entry_price: float,
                             signal_type: SignalType) -> Optional[float]:
        """목표가 계산"""
        try:
            risk_config = self.config_manager.get_risk_limits()
            take_profit_pct = risk_config.get('take_profit', 3.0) / 100

            if signal_type == SignalType.BUY:
                return entry_price * (1 + take_profit_pct)
            elif signal_type == SignalType.SELL:
                return entry_price * (1 - take_profit_pct)

            return None

        except Exception:
            return None

    def _should_generate_signal(self, symbol: str) -> bool:
        """신호 생성 허용 여부 확인"""
        if symbol not in self.last_signal_time:
            return True

        time_since_last = datetime.now() - self.last_signal_time[symbol]
        return time_since_last.total_seconds() >= self.min_signal_interval

    def _validate_signal(self, signal: TradingSignal) -> bool:
        """신호 유효성 검증"""
        try:
            # 기본 검증
            if signal.confidence < self.confidence_threshold:
                return False

            if signal.signal_type == SignalType.HOLD:
                return False

            # 가격 검증
            if signal.entry_price <= 0:
                return False

            # 손절/익절 가격 검증
            if signal.stop_loss and signal.stop_loss <= 0:
                return False

            if signal.take_profit and signal.take_profit <= 0:
                return False

            # 시장 상황 필터링
            if self.ai_settings.get('market_condition_filter', True):
                if not self._check_market_conditions(signal):
                    return False

            return True

        except Exception as e:
            self.logger.error(f"신호 검증 실패: {e}")
            return False

    def _check_market_conditions(self, signal: TradingSignal) -> bool:
        """시장 상황 확인"""
        try:
            market_conditions = signal.market_conditions

            # 높은 변동성 시 신호 강도 요구사항 증가
            volatility = market_conditions.get('volatility', 0)
            if volatility > 0.1 and signal.strength == SignalStrength.WEAK:
                return False

            return True

        except Exception:
            return True

    def _post_process_signals(self, signals: List[TradingSignal]) -> List[TradingSignal]:
        """신호 후처리"""
        try:
            # 중복 신호 제거
            unique_signals = {}
            for signal in signals:
                if signal.symbol not in unique_signals:
                    unique_signals[signal.symbol] = signal
                else:
                    # 더 높은 신뢰도 신호 선택
                    if signal.confidence > unique_signals[signal.symbol].confidence:
                        unique_signals[signal.symbol] = signal

            # 신호 우선순위 정렬
            sorted_signals = sorted(
                unique_signals.values(),
                key=lambda x: (x.confidence, x.strength.value),
                reverse=True
            )

            return sorted_signals

        except Exception as e:
            self.logger.error(f"신호 후처리 실패: {e}")
            return signals

    def get_signal_statistics(self) -> Dict[str, Any]:
        """신호 생성 통계"""
        success_rate = 0
        if self.generated_signals > 0:
            success_rate = (self.successful_predictions / self.generated_signals) * 100

        return {
            'total_signals': self.generated_signals,
            'successful_predictions': self.successful_predictions,
            'success_rate': success_rate,
            'avg_confidence': self._calculate_avg_confidence(),
            'signal_distribution': self._get_signal_distribution()
        }

    def _calculate_avg_confidence(self) -> float:
        """평균 신뢰도 계산"""
        if not self.signal_history:
            return 0.0

        confidences = [s.confidence for s in self.signal_history[-100:]]  # 최근 100개
        return sum(confidences) / len(confidences)

    def _get_signal_distribution(self) -> Dict[str, int]:
        """신호 분포 통계"""
        distribution = {'BUY': 0, 'SELL': 0, 'HOLD': 0}

        for signal in self.signal_history[-100:]:  # 최근 100개
            distribution[signal.signal_type.value] += 1

        return distribution

    def update_signal_outcome(self, signal_id: int, successful: bool):
        """신호 결과 업데이트"""
        if successful:
            self.successful_predictions += 1

        # 실제 구현에서는 데이터베이스에 기록
        self.logger.info(f"신호 결과 업데이트: {'성공' if successful else '실패'}")

    def cleanup(self):
        """리소스 정리"""
        try:
            if self.ai_system and hasattr(self.ai_system, 'cleanup'):
                self.ai_system.cleanup()
            self.logger.info("AISignalGenerator 리소스 정리 완료")
        except Exception as e:
            self.logger.error(f"리소스 정리 실패: {e}")