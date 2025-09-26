"""
AI-based Trading Signal Generator for Futures Trading
기술적 분석과 머신러닝을 결합한 지능형 거래 신호 생성 시스템
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SignalType(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    CLOSE = "CLOSE"
    HOLD = "HOLD"


class ConfidenceLevel(Enum):
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


@dataclass
class TechnicalIndicators:
    """기술적 지표 데이터"""
    rsi: float
    macd: float
    macd_signal: float
    macd_histogram: float
    bb_upper: float
    bb_middle: float
    bb_lower: float
    ema_9: float
    ema_21: float
    ema_50: float
    volume_sma: float
    atr: float


@dataclass
class MarketCondition:
    """시장 상황 분석"""
    trend_direction: str  # "BULLISH", "BEARISH", "SIDEWAYS"
    volatility_level: str  # "LOW", "MEDIUM", "HIGH"
    momentum_strength: float  # 0-100
    support_level: float
    resistance_level: float


@dataclass
class AISignal:
    """AI 생성 거래 신호"""
    symbol: str
    signal_type: SignalType
    confidence: float  # 0-100
    confidence_level: ConfidenceLevel
    entry_price: float
    stop_loss: float
    take_profit: Optional[float]
    risk_reward_ratio: float
    reasoning: str
    technical_score: float
    market_condition_score: float
    timestamp: datetime
    valid_until: datetime


class AISignalGenerator:
    """AI 기반 거래 신호 생성기"""

    def __init__(self):
        self.min_confidence_threshold = 65.0
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.volatility_lookback = 14

    def calculate_technical_indicators(self, df: pd.DataFrame) -> TechnicalIndicators:
        """기술적 지표 계산"""
        try:
            # RSI 계산
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]

            # MACD 계산
            ema_12 = df['close'].ewm(span=12).mean()
            ema_26 = df['close'].ewm(span=26).mean()
            macd = (ema_12 - ema_26).iloc[-1]
            macd_signal = (ema_12 - ema_26).ewm(span=9).mean().iloc[-1]
            macd_histogram = macd - macd_signal

            # Bollinger Bands
            bb_middle = df['close'].rolling(window=20).mean().iloc[-1]
            bb_std = df['close'].rolling(window=20).std().iloc[-1]
            bb_upper = bb_middle + (bb_std * 2)
            bb_lower = bb_middle - (bb_std * 2)

            # EMA
            ema_9 = df['close'].ewm(span=9).mean().iloc[-1]
            ema_21 = df['close'].ewm(span=21).mean().iloc[-1]
            ema_50 = df['close'].ewm(span=50).mean().iloc[-1]

            # Volume SMA
            volume_sma = df['volume'].rolling(window=20).mean().iloc[-1]

            # ATR (Average True Range)
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            tr = np.maximum(high_low, np.maximum(high_close, low_close))
            atr = tr.rolling(window=14).mean().iloc[-1]

            return TechnicalIndicators(
                rsi=rsi,
                macd=macd,
                macd_signal=macd_signal,
                macd_histogram=macd_histogram,
                bb_upper=bb_upper,
                bb_middle=bb_middle,
                bb_lower=bb_lower,
                ema_9=ema_9,
                ema_21=ema_21,
                ema_50=ema_50,
                volume_sma=volume_sma,
                atr=atr
            )

        except Exception as e:
            logger.error(f"Technical indicators calculation error: {e}")
            raise

    def analyze_market_condition(self, df: pd.DataFrame, indicators: TechnicalIndicators) -> MarketCondition:
        """시장 상황 분석"""
        try:
            current_price = df['close'].iloc[-1]

            # 트렌드 방향 결정
            if indicators.ema_9 > indicators.ema_21 > indicators.ema_50:
                trend_direction = "BULLISH"
            elif indicators.ema_9 < indicators.ema_21 < indicators.ema_50:
                trend_direction = "BEARISH"
            else:
                trend_direction = "SIDEWAYS"

            # 변동성 레벨
            price_changes = df['close'].pct_change().abs().rolling(window=20).mean().iloc[-1]
            if price_changes < 0.02:
                volatility_level = "LOW"
            elif price_changes < 0.05:
                volatility_level = "MEDIUM"
            else:
                volatility_level = "HIGH"

            # 모멘텀 강도
            momentum_strength = min(100, max(0, (indicators.rsi +
                                                (50 + (indicators.macd_histogram * 10))) / 2))

            # 지지/저항 레벨 (간단 버전)
            recent_highs = df['high'].rolling(window=10).max().iloc[-1]
            recent_lows = df['low'].rolling(window=10).min().iloc[-1]

            return MarketCondition(
                trend_direction=trend_direction,
                volatility_level=volatility_level,
                momentum_strength=momentum_strength,
                support_level=recent_lows,
                resistance_level=recent_highs
            )

        except Exception as e:
            logger.error(f"Market condition analysis error: {e}")
            raise

    def calculate_signal_confidence(self, indicators: TechnicalIndicators,
                                  market_condition: MarketCondition,
                                  signal_type: SignalType) -> Tuple[float, float, float]:
        """신호 신뢰도 계산"""
        technical_score = 0.0
        market_score = 0.0

        # 기술적 분석 점수
        if signal_type == SignalType.LONG:
            # RSI 조건
            if indicators.rsi < 40:
                technical_score += 20
            elif indicators.rsi < 50:
                technical_score += 10

            # MACD 조건
            if indicators.macd > indicators.macd_signal:
                technical_score += 25
            if indicators.macd_histogram > 0:
                technical_score += 15

            # EMA 조건
            if indicators.ema_9 > indicators.ema_21:
                technical_score += 20
            if indicators.ema_21 > indicators.ema_50:
                technical_score += 20

        elif signal_type == SignalType.SHORT:
            # RSI 조건
            if indicators.rsi > 60:
                technical_score += 20
            elif indicators.rsi > 50:
                technical_score += 10

            # MACD 조건
            if indicators.macd < indicators.macd_signal:
                technical_score += 25
            if indicators.macd_histogram < 0:
                technical_score += 15

            # EMA 조건
            if indicators.ema_9 < indicators.ema_21:
                technical_score += 20
            if indicators.ema_21 < indicators.ema_50:
                technical_score += 20

        # 시장 조건 점수
        if signal_type == SignalType.LONG:
            if market_condition.trend_direction == "BULLISH":
                market_score += 40
            elif market_condition.trend_direction == "SIDEWAYS":
                market_score += 20

            if market_condition.momentum_strength > 60:
                market_score += 30
            elif market_condition.momentum_strength > 40:
                market_score += 15

            if market_condition.volatility_level == "MEDIUM":
                market_score += 30
            elif market_condition.volatility_level == "HIGH":
                market_score += 15

        elif signal_type == SignalType.SHORT:
            if market_condition.trend_direction == "BEARISH":
                market_score += 40
            elif market_condition.trend_direction == "SIDEWAYS":
                market_score += 20

            if market_condition.momentum_strength < 40:
                market_score += 30
            elif market_condition.momentum_strength < 60:
                market_score += 15

            if market_condition.volatility_level == "MEDIUM":
                market_score += 30
            elif market_condition.volatility_level == "HIGH":
                market_score += 15

        # 전체 신뢰도 계산 (기술적 60%, 시장조건 40%)
        overall_confidence = (technical_score * 0.6) + (market_score * 0.4)

        return overall_confidence, technical_score, market_score

    def calculate_price_targets(self, current_price: float, signal_type: SignalType,
                              indicators: TechnicalIndicators,
                              market_condition: MarketCondition) -> Tuple[float, float]:
        """손절가와 목표가 계산"""
        atr_multiplier = 2.0

        if signal_type == SignalType.LONG:
            # 롱 포지션
            stop_loss = current_price - (indicators.atr * atr_multiplier)
            take_profit = current_price + (indicators.atr * 3.0)

            # 지지/저항 레벨 고려
            if market_condition.support_level > 0:
                stop_loss = max(stop_loss, market_condition.support_level * 0.98)

        else:  # SHORT
            # 숏 포지션
            stop_loss = current_price + (indicators.atr * atr_multiplier)
            take_profit = current_price - (indicators.atr * 3.0)

            # 지지/저항 레벨 고려
            if market_condition.resistance_level > 0:
                stop_loss = min(stop_loss, market_condition.resistance_level * 1.02)

        return stop_loss, take_profit

    def get_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """신뢰도 레벨 분류"""
        if confidence >= 85:
            return ConfidenceLevel.VERY_HIGH
        elif confidence >= 75:
            return ConfidenceLevel.HIGH
        elif confidence >= 65:
            return ConfidenceLevel.MEDIUM
        elif confidence >= 50:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    def generate_reasoning(self, signal_type: SignalType, indicators: TechnicalIndicators,
                          market_condition: MarketCondition, confidence: float) -> str:
        """신호 근거 생성"""
        reasoning_parts = []

        if signal_type == SignalType.LONG:
            reasoning_parts.append("🔵 LONG 신호 분석:")

            if indicators.rsi < 50:
                reasoning_parts.append(f"• RSI({indicators.rsi:.1f}) 과매도 구간")
            if indicators.macd > indicators.macd_signal:
                reasoning_parts.append("• MACD 골든크로스 확인")
            if indicators.ema_9 > indicators.ema_21:
                reasoning_parts.append("• 단기 상승 추세 확인")
            if market_condition.trend_direction == "BULLISH":
                reasoning_parts.append("• 전체 트렌드 강세")

        else:  # SHORT
            reasoning_parts.append("🔴 SHORT 신호 분석:")

            if indicators.rsi > 50:
                reasoning_parts.append(f"• RSI({indicators.rsi:.1f}) 과매수 구간")
            if indicators.macd < indicators.macd_signal:
                reasoning_parts.append("• MACD 데드크로스 확인")
            if indicators.ema_9 < indicators.ema_21:
                reasoning_parts.append("• 단기 하락 추세 확인")
            if market_condition.trend_direction == "BEARISH":
                reasoning_parts.append("• 전체 트렌드 약세")

        reasoning_parts.append(f"• 신뢰도: {confidence:.1f}% ({market_condition.volatility_level} 변동성)")

        return " ".join(reasoning_parts)

    def generate_signal(self, symbol: str, df: pd.DataFrame) -> Optional[AISignal]:
        """AI 거래 신호 생성"""
        try:
            if len(df) < 50:
                logger.warning(f"Insufficient data for {symbol}")
                return None

            # 기술적 지표 계산
            indicators = self.calculate_technical_indicators(df)

            # 시장 상황 분석
            market_condition = self.analyze_market_condition(df, indicators)

            current_price = df['close'].iloc[-1]

            # 신호 결정 로직
            signal_type = None

            # LONG 신호 조건
            if (indicators.rsi < 40 and
                indicators.macd > indicators.macd_signal and
                indicators.ema_9 > indicators.ema_21 and
                current_price < indicators.bb_upper):
                signal_type = SignalType.LONG

            # SHORT 신호 조건
            elif (indicators.rsi > 60 and
                  indicators.macd < indicators.macd_signal and
                  indicators.ema_9 < indicators.ema_21 and
                  current_price > indicators.bb_lower):
                signal_type = SignalType.SHORT

            if not signal_type:
                return None  # 신호 없음

            # 신뢰도 계산
            confidence, technical_score, market_score = self.calculate_signal_confidence(
                indicators, market_condition, signal_type
            )

            # 최소 신뢰도 미달시 신호 생성하지 않음
            if confidence < self.min_confidence_threshold:
                logger.info(f"Signal confidence too low for {symbol}: {confidence:.1f}%")
                return None

            # 가격 목표 계산
            stop_loss, take_profit = self.calculate_price_targets(
                current_price, signal_type, indicators, market_condition
            )

            # 위험 대비 수익 비율 계산
            if signal_type == SignalType.LONG:
                risk = current_price - stop_loss
                reward = take_profit - current_price
            else:
                risk = stop_loss - current_price
                reward = current_price - take_profit

            risk_reward_ratio = reward / risk if risk > 0 else 0

            # 신호 생성
            signal = AISignal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                confidence_level=self.get_confidence_level(confidence),
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=risk_reward_ratio,
                reasoning=self.generate_reasoning(signal_type, indicators, market_condition, confidence),
                technical_score=technical_score,
                market_condition_score=market_score,
                timestamp=datetime.now(),
                valid_until=datetime.now() + timedelta(hours=4)  # 4시간 유효
            )

            logger.info(f"Generated {signal_type.value} signal for {symbol} with {confidence:.1f}% confidence")
            return signal

        except Exception as e:
            logger.error(f"Signal generation error for {symbol}: {e}")
            return None

    def generate_multiple_signals(self, market_data: Dict[str, pd.DataFrame]) -> List[AISignal]:
        """여러 심볼에 대한 신호 생성"""
        signals = []

        for symbol, df in market_data.items():
            signal = self.generate_signal(symbol, df)
            if signal:
                signals.append(signal)

        # 신뢰도 순으로 정렬
        signals.sort(key=lambda s: s.confidence, reverse=True)

        return signals


class SignalValidator:
    """신호 검증 시스템"""

    def __init__(self):
        self.min_risk_reward_ratio = 1.5
        self.max_risk_per_trade = 5.0  # %

    def validate_signal(self, signal: AISignal) -> Tuple[bool, List[str]]:
        """신호 검증"""
        is_valid = True
        warnings = []

        # 신뢰도 검증
        if signal.confidence < 65:
            warnings.append(f"신뢰도가 낮습니다 ({signal.confidence:.1f}%)")

        # 위험 대비 수익 비율 검증
        if signal.risk_reward_ratio < self.min_risk_reward_ratio:
            warnings.append(f"위험 대비 수익 비율이 낮습니다 ({signal.risk_reward_ratio:.2f})")

        # 가격 범위 검증
        if signal.signal_type == SignalType.LONG:
            risk_percent = (signal.entry_price - signal.stop_loss) / signal.entry_price * 100
        else:
            risk_percent = (signal.stop_loss - signal.entry_price) / signal.entry_price * 100

        if risk_percent > self.max_risk_per_trade:
            warnings.append(f"거래당 리스크가 높습니다 ({risk_percent:.1f}%)")

        # 신호 유효성 검증
        if signal.timestamp < datetime.now() - timedelta(minutes=15):
            warnings.append("신호가 너무 오래되었습니다")
            is_valid = False

        return is_valid, warnings