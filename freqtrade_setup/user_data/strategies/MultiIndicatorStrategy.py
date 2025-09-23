#!/usr/bin/env python3
"""
Multi-Indicator Strategy for Freqtrade
Combines RSI, MACD, and Bollinger Bands with weighted signal aggregation
"""

import talib.abstract as ta
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter, CategoricalParameter
import freqtrade.vendor.qtpylib.indicators as qtpylib


class MultiIndicatorStrategy(IStrategy):
    """
    Multi-Indicator Strategy combining RSI, MACD, and Bollinger Bands

    Features:
    - N of M signal logic (e.g., 3 out of 5 signals required)
    - Weighted signal aggregation with confidence scoring
    - Advanced filtering: time, volatility, trend
    - Dynamic position sizing based on signal strength
    """

    # Strategy interface version
    INTERFACE_VERSION = 3

    # Strategy metadata
    can_short = False
    stoploss = -0.08  # 8% stoploss
    startup_candle_count: int = 50

    # Timeframes
    timeframe = '5m'
    informative_timeframe = '1h'

    # ==================== HYPEROPT PARAMETERS ====================

    # RSI Parameters
    rsi_period = IntParameter(10, 21, default=14, space='buy', optimize=True)
    rsi_oversold = IntParameter(25, 35, default=30, space='buy', optimize=True)
    rsi_overbought = IntParameter(65, 75, default=70, space='sell', optimize=True)

    # MACD Parameters
    macd_fast = IntParameter(8, 16, default=12, space='buy', optimize=True)
    macd_slow = IntParameter(20, 30, default=26, space='buy', optimize=True)
    macd_signal = IntParameter(6, 12, default=9, space='buy', optimize=True)

    # Bollinger Bands Parameters
    bb_period = IntParameter(15, 25, default=20, space='buy', optimize=True)
    bb_std = DecimalParameter(1.8, 2.5, default=2.0, space='buy', optimize=True)

    # Signal Weights (relative importance)
    weight_rsi = DecimalParameter(0.5, 2.0, default=1.0, space='buy', optimize=True)
    weight_macd = DecimalParameter(0.8, 2.2, default=1.5, space='buy', optimize=True)
    weight_bb = DecimalParameter(0.6, 1.8, default=1.2, space='buy', optimize=True)
    weight_volume = DecimalParameter(0.3, 1.5, default=0.8, space='buy', optimize=True)
    weight_trend = DecimalParameter(0.5, 1.8, default=1.0, space='buy', optimize=True)

    # Signal Thresholds
    confidence_threshold_buy = DecimalParameter(60, 85, default=70, space='buy', optimize=True)
    confidence_threshold_sell = DecimalParameter(55, 80, default=65, space='sell', optimize=True)
    required_signals_buy = IntParameter(2, 4, default=3, space='buy', optimize=True)
    required_signals_sell = IntParameter(2, 4, default=3, space='sell', optimize=True)

    # Risk Management
    max_position_size = DecimalParameter(0.3, 1.0, default=0.5, space='buy', optimize=True)
    volatility_threshold = DecimalParameter(0.01, 0.05, default=0.02, space='buy', optimize=True)

    # Time Filters
    trade_start_hour = IntParameter(0, 23, default=9, space='buy', optimize=False)
    trade_end_hour = IntParameter(0, 23, default=18, space='buy', optimize=False)

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """Calculate all technical indicators"""

        # =========================== RSI ===========================
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.rsi_period.value)
        dataframe['rsi_oversold'] = dataframe['rsi'] <= self.rsi_oversold.value
        dataframe['rsi_overbought'] = dataframe['rsi'] >= self.rsi_overbought.value

        # =========================== MACD ===========================
        macd = ta.MACD(
            dataframe,
            fastperiod=self.macd_fast.value,
            slowperiod=self.macd_slow.value,
            signalperiod=self.macd_signal.value
        )
        dataframe['macd'] = macd['macd']
        dataframe['macd_signal'] = macd['macdsignal']
        dataframe['macd_hist'] = macd['macdhist']

        # MACD signals
        dataframe['macd_bullish'] = (
            (dataframe['macd'] > dataframe['macd_signal']) &
            (dataframe['macd_hist'] > dataframe['macd_hist'].shift(1))
        )
        dataframe['macd_bearish'] = (
            (dataframe['macd'] < dataframe['macd_signal']) &
            (dataframe['macd_hist'] < dataframe['macd_hist'].shift(1))
        )

        # =========================== BOLLINGER BANDS ===========================
        bollinger = qtpylib.bollinger_bands(
            dataframe['close'],
            window=self.bb_period.value,
            stds=self.bb_std.value
        )
        dataframe['bb_lower'] = bollinger['lower']
        dataframe['bb_middle'] = bollinger['mid']
        dataframe['bb_upper'] = bollinger['upper']
        dataframe['bb_percent'] = (dataframe['close'] - dataframe['bb_lower']) / (dataframe['bb_upper'] - dataframe['bb_lower'])
        dataframe['bb_width'] = (dataframe['bb_upper'] - dataframe['bb_lower']) / dataframe['bb_middle']

        # BB signals
        dataframe['bb_oversold'] = dataframe['bb_percent'] <= 0.1  # Near lower band
        dataframe['bb_overbought'] = dataframe['bb_percent'] >= 0.9  # Near upper band

        # =========================== VOLUME INDICATORS ===========================
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']
        dataframe['volume_spike'] = dataframe['volume_ratio'] >= 1.5

        # On Balance Volume
        dataframe['obv'] = ta.OBV(dataframe['close'], dataframe['volume'])
        dataframe['obv_sma'] = ta.SMA(dataframe['obv'], timeperiod=10)
        dataframe['obv_rising'] = dataframe['obv'] > dataframe['obv_sma']

        # =========================== TREND INDICATORS ===========================
        dataframe['sma_20'] = ta.SMA(dataframe, timeperiod=20)
        dataframe['sma_50'] = ta.SMA(dataframe, timeperiod=50)
        dataframe['ema_12'] = ta.EMA(dataframe, timeperiod=12)

        # Trend signals
        dataframe['trend_bullish'] = (
            (dataframe['close'] > dataframe['sma_20']) &
            (dataframe['sma_20'] > dataframe['sma_50']) &
            (dataframe['close'] > dataframe['ema_12'])
        )
        dataframe['trend_bearish'] = (
            (dataframe['close'] < dataframe['sma_20']) &
            (dataframe['sma_20'] < dataframe['sma_50']) &
            (dataframe['close'] < dataframe['ema_12'])
        )

        # =========================== ATR & VOLATILITY ===========================
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_percent'] = dataframe['atr'] / dataframe['close'] * 100
        dataframe['volatility_normal'] = dataframe['atr_percent'] <= self.volatility_threshold.value * 100

        # =========================== PRICE ACTION ===========================
        dataframe['price_change_1'] = dataframe['close'].pct_change(1)
        dataframe['price_change_3'] = dataframe['close'].pct_change(3)

        # Support/Resistance levels
        dataframe['recent_high'] = dataframe['high'].rolling(20).max()
        dataframe['recent_low'] = dataframe['low'].rolling(20).min()
        dataframe['near_support'] = dataframe['close'] <= dataframe['recent_low'] * 1.02
        dataframe['near_resistance'] = dataframe['close'] >= dataframe['recent_high'] * 0.98

        # =========================== TIME FILTERS ===========================
        dataframe['hour'] = pd.to_datetime(dataframe.index).hour
        dataframe['trading_hours'] = (
            (dataframe['hour'] >= self.trade_start_hour.value) &
            (dataframe['hour'] <= self.trade_end_hour.value)
        )

        # =========================== SIGNAL AGGREGATION ===========================
        dataframe = self.calculate_signal_scores(dataframe)

        return dataframe

    def calculate_signal_scores(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Calculate weighted signal scores and confidence levels"""

        # Initialize signal arrays
        buy_signals = []
        sell_signals = []
        buy_weights = []
        sell_weights = []

        # =============== BUY SIGNALS ===============

        # 1. RSI Oversold
        buy_signals.append(dataframe['rsi_oversold'])
        buy_weights.append(self.weight_rsi.value)

        # 2. MACD Bullish
        buy_signals.append(dataframe['macd_bullish'])
        buy_weights.append(self.weight_macd.value)

        # 3. Bollinger Bands Oversold
        buy_signals.append(dataframe['bb_oversold'])
        buy_weights.append(self.weight_bb.value)

        # 4. Volume Spike + OBV Rising
        volume_signal = dataframe['volume_spike'] & dataframe['obv_rising']
        buy_signals.append(volume_signal)
        buy_weights.append(self.weight_volume.value)

        # 5. Trend Alignment or Near Support
        trend_support_signal = dataframe['trend_bullish'] | dataframe['near_support']
        buy_signals.append(trend_support_signal)
        buy_weights.append(self.weight_trend.value)

        # =============== SELL SIGNALS ===============

        # 1. RSI Overbought
        sell_signals.append(dataframe['rsi_overbought'])
        sell_weights.append(self.weight_rsi.value)

        # 2. MACD Bearish
        sell_signals.append(dataframe['macd_bearish'])
        sell_weights.append(self.weight_macd.value)

        # 3. Bollinger Bands Overbought
        sell_signals.append(dataframe['bb_overbought'])
        sell_weights.append(self.weight_bb.value)

        # 4. Volume Declining
        volume_decline_signal = ~dataframe['obv_rising'] & (dataframe['volume_ratio'] < 0.8)
        sell_signals.append(volume_decline_signal)
        sell_weights.append(self.weight_volume.value)

        # 5. Trend Bearish or Near Resistance
        trend_resistance_signal = dataframe['trend_bearish'] | dataframe['near_resistance']
        sell_signals.append(trend_resistance_signal)
        sell_weights.append(self.weight_trend.value)

        # =============== CALCULATE CONFIDENCE SCORES ===============

        # Buy confidence score (0-100)
        buy_score = np.zeros(len(dataframe))
        total_buy_weight = sum(buy_weights)

        for signal, weight in zip(buy_signals, buy_weights):
            buy_score += signal.astype(int) * weight

        dataframe['buy_confidence'] = (buy_score / total_buy_weight) * 100

        # Sell confidence score (0-100)
        sell_score = np.zeros(len(dataframe))
        total_sell_weight = sum(sell_weights)

        for signal, weight in zip(sell_signals, sell_weights):
            sell_score += signal.astype(int) * weight

        dataframe['sell_confidence'] = (sell_score / total_sell_weight) * 100

        # =============== COUNT ACTIVE SIGNALS ===============

        # Count how many buy signals are active
        buy_signal_count = np.zeros(len(dataframe))
        for signal in buy_signals:
            buy_signal_count += signal.astype(int)
        dataframe['buy_signal_count'] = buy_signal_count

        # Count how many sell signals are active
        sell_signal_count = np.zeros(len(dataframe))
        for signal in sell_signals:
            sell_signal_count += signal.astype(int)
        dataframe['sell_signal_count'] = sell_signal_count

        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """Define buy entry conditions"""

        conditions = [
            # Core signal requirements
            (dataframe['buy_confidence'] >= self.confidence_threshold_buy.value),
            (dataframe['buy_signal_count'] >= self.required_signals_buy.value),

            # Risk filters
            (dataframe['volatility_normal']),  # Normal volatility
            (dataframe['trading_hours']),      # Trading hours filter

            # Additional safety checks
            (dataframe['volume'] > 0),         # Volume exists
            (dataframe['close'] > 0),          # Valid price

            # Trend filter (optional - can be optimized)
            (
                dataframe['trend_bullish'] |   # Either in bullish trend
                dataframe['near_support']      # Or near support level
            )
        ]

        dataframe.loc[
            reduce(lambda x, y: x & y, conditions),
            'enter_long'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """Define sell exit conditions"""

        conditions = [
            # Core signal requirements
            (dataframe['sell_confidence'] >= self.confidence_threshold_sell.value),
            (dataframe['sell_signal_count'] >= self.required_signals_sell.value),

            # Additional exit conditions
            (
                dataframe['rsi_overbought'] |         # RSI overbought
                dataframe['bb_overbought'] |          # BB overbought
                dataframe['near_resistance']          # Near resistance
            )
        ]

        dataframe.loc[
            reduce(lambda x, y: x & y, conditions),
            'exit_long'
        ] = 1

        return dataframe

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                           proposed_stake: float, min_stake: Optional[float], max_stake: Optional[float],
                           leverage: float, entry_tag: Optional[str], side: str, **kwargs) -> float:
        """Dynamic position sizing based on signal confidence"""

        try:
            # Get the latest dataframe for this pair
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)

            if dataframe.empty:
                return proposed_stake * 0.5  # Conservative fallback

            # Get latest signal data
            latest = dataframe.iloc[-1]

            # Base confidence (buy_confidence from 0-100)
            confidence = latest.get('buy_confidence', 50) / 100.0  # Convert to 0-1

            # Volatility adjustment
            atr_pct = latest.get('atr_percent', 2.0)
            volatility_multiplier = max(0.5, min(1.5, 1.0 / (1.0 + atr_pct * 0.1)))

            # Signal strength adjustment
            signal_count = latest.get('buy_signal_count', 0)
            signal_multiplier = min(1.2, 0.8 + (signal_count * 0.1))

            # Calculate final position size
            confidence_multiplier = max(0.3, min(1.5, confidence * 1.5))
            total_multiplier = confidence_multiplier * volatility_multiplier * signal_multiplier

            # Apply maximum position size limit
            final_stake = proposed_stake * total_multiplier * self.max_position_size.value

            # Ensure within bounds
            if min_stake and final_stake < min_stake:
                final_stake = min_stake
            if max_stake and final_stake > max_stake:
                final_stake = max_stake

            return final_stake

        except Exception:
            # Fallback to conservative sizing
            return proposed_stake * 0.5

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                       current_rate: float, current_profit: float, **kwargs) -> float:
        """Dynamic stoploss based on volatility"""

        try:
            # Get the latest dataframe for this pair
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)

            if dataframe.empty:
                return self.stoploss  # Default stoploss

            # Get latest volatility data
            latest = dataframe.iloc[-1]
            atr_pct = latest.get('atr_percent', 2.0)

            # Adjust stoploss based on volatility
            # Higher volatility = wider stoploss
            volatility_adjustment = max(1.0, min(2.0, atr_pct / 2.0))
            dynamic_stoploss = self.stoploss * volatility_adjustment

            # Ensure stoploss doesn't exceed -15%
            return max(-0.15, dynamic_stoploss)

        except Exception:
            return self.stoploss

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float,
                           rate: float, time_in_force: str, current_time: datetime,
                           entry_tag: Optional[str], side: str, **kwargs) -> bool:
        """Final trade confirmation with additional safety checks"""

        try:
            # Get the latest dataframe
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)

            if dataframe.empty:
                return False

            latest = dataframe.iloc[-1]

            # Safety checks
            checks = [
                # Minimum confidence level
                latest.get('buy_confidence', 0) >= self.confidence_threshold_buy.value,

                # Minimum signal count
                latest.get('buy_signal_count', 0) >= self.required_signals_buy.value,

                # Normal volatility
                latest.get('volatility_normal', False),

                # Trading hours
                latest.get('trading_hours', False),

                # Volume check
                latest.get('volume_ratio', 0) >= 0.5,
            ]

            return all(checks)

        except Exception:
            return False

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                side: str, **kwargs) -> float:
        """Dynamic leverage based on signal confidence"""

        try:
            # Get signal confidence
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)

            if dataframe.empty:
                return 1.0  # No leverage for safety

            latest = dataframe.iloc[-1]
            confidence = latest.get('buy_confidence', 50) / 100.0
            volatility = latest.get('atr_percent', 2.0)

            # Lower leverage for high volatility
            volatility_factor = max(0.5, 1.0 - (volatility * 0.05))

            # Higher leverage for high confidence
            confidence_factor = 0.5 + (confidence * 0.5)

            # Calculate dynamic leverage
            dynamic_leverage = min(max_leverage, 5.0 * confidence_factor * volatility_factor)

            return max(1.0, dynamic_leverage)

        except Exception:
            return 1.0


# Helper function for condition reduction
def reduce(function, iterable, initializer=None):
    """Reduce function for combining conditions"""
    it = iter(iterable)
    if initializer is None:
        value = next(it)
    else:
        value = initializer
    for element in it:
        value = function(value, element)
    return value