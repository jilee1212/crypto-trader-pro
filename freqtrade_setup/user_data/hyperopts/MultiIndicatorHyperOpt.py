#!/usr/bin/env python3
"""
HyperOpt Configuration for MultiIndicatorStrategy
Optimizes parameters for RSI, MACD, Bollinger Bands, and signal weights
"""

from functools import reduce
from typing import Dict, Any, Callable, List

from freqtrade.optimize.hyperopt_interface import IHyperOpt
from freqtrade.optimize.space import Categorical, Dimension, Integer, SKDecimal


class MultiIndicatorHyperOpt(IHyperOpt):
    """
    HyperOpt class for MultiIndicatorStrategy

    Optimizes:
    - Individual indicator parameters (RSI, MACD, BB)
    - Signal weights and thresholds
    - Risk management parameters
    - Time and volatility filters
    """

    @staticmethod
    def buy_strategy_generator(params: Dict[str, Any]) -> Callable:
        """
        Define the buy strategy space for optimization
        """
        def populate_buy_trend(dataframe, metadata):
            """Optimized buy strategy logic"""

            conditions = []

            # ==================== RSI CONDITIONS ====================
            if 'rsi-enabled' in params and params['rsi-enabled']:
                rsi_period = params.get('rsi-period', 14)
                rsi_oversold = params.get('rsi-oversold', 30)

                # Calculate RSI if not exists
                if f'rsi_{rsi_period}' not in dataframe.columns:
                    dataframe[f'rsi_{rsi_period}'] = ta.RSI(dataframe, timeperiod=rsi_period)

                conditions.append(dataframe[f'rsi_{rsi_period}'] < rsi_oversold)

            # ==================== MACD CONDITIONS ====================
            if 'macd-enabled' in params and params['macd-enabled']:
                macd_fast = params.get('macd-fast', 12)
                macd_slow = params.get('macd-slow', 26)
                macd_signal = params.get('macd-signal', 9)

                # Calculate MACD if not exists
                macd_key = f'macd_{macd_fast}_{macd_slow}_{macd_signal}'
                if f'{macd_key}_macd' not in dataframe.columns:
                    macd = ta.MACD(dataframe,
                                  fastperiod=macd_fast,
                                  slowperiod=macd_slow,
                                  signalperiod=macd_signal)
                    dataframe[f'{macd_key}_macd'] = macd['macd']
                    dataframe[f'{macd_key}_signal'] = macd['macdsignal']
                    dataframe[f'{macd_key}_hist'] = macd['macdhist']

                # MACD bullish crossover
                macd_condition = (
                    (dataframe[f'{macd_key}_macd'] > dataframe[f'{macd_key}_signal']) &
                    (dataframe[f'{macd_key}_hist'] > dataframe[f'{macd_key}_hist'].shift(1))
                )
                conditions.append(macd_condition)

            # ==================== BOLLINGER BANDS CONDITIONS ====================
            if 'bb-enabled' in params and params['bb-enabled']:
                bb_period = params.get('bb-period', 20)
                bb_std = params.get('bb-std', 2.0)

                # Calculate BB if not exists
                bb_key = f'bb_{bb_period}_{bb_std:.1f}'
                if f'{bb_key}_lower' not in dataframe.columns:
                    bollinger = qtpylib.bollinger_bands(
                        dataframe['close'],
                        window=bb_period,
                        stds=bb_std
                    )
                    dataframe[f'{bb_key}_lower'] = bollinger['lower']
                    dataframe[f'{bb_key}_upper'] = bollinger['upper']
                    dataframe[f'{bb_key}_percent'] = (
                        (dataframe['close'] - bollinger['lower']) /
                        (bollinger['upper'] - bollinger['lower'])
                    )

                # Near lower Bollinger Band
                bb_oversold_threshold = params.get('bb-oversold-threshold', 0.1)
                bb_condition = dataframe[f'{bb_key}_percent'] <= bb_oversold_threshold
                conditions.append(bb_condition)

            # ==================== VOLUME CONDITIONS ====================
            if 'volume-enabled' in params and params['volume-enabled']:
                volume_period = params.get('volume-period', 20)
                volume_threshold = params.get('volume-threshold', 1.5)

                # Calculate volume indicators if not exists
                if f'volume_sma_{volume_period}' not in dataframe.columns:
                    dataframe[f'volume_sma_{volume_period}'] = ta.SMA(dataframe['volume'], timeperiod=volume_period)
                    dataframe[f'volume_ratio_{volume_period}'] = (
                        dataframe['volume'] / dataframe[f'volume_sma_{volume_period}']
                    )

                volume_condition = dataframe[f'volume_ratio_{volume_period}'] >= volume_threshold
                conditions.append(volume_condition)

            # ==================== TREND CONDITIONS ====================
            if 'trend-enabled' in params and params['trend-enabled']:
                trend_short = params.get('trend-short-period', 20)
                trend_long = params.get('trend-long-period', 50)

                # Calculate trend indicators if not exists
                if f'sma_{trend_short}' not in dataframe.columns:
                    dataframe[f'sma_{trend_short}'] = ta.SMA(dataframe, timeperiod=trend_short)
                    dataframe[f'sma_{trend_long}'] = ta.SMA(dataframe, timeperiod=trend_long)

                trend_condition = (
                    (dataframe['close'] > dataframe[f'sma_{trend_short}']) &
                    (dataframe[f'sma_{trend_short}'] > dataframe[f'sma_{trend_long}'])
                )
                conditions.append(trend_condition)

            # ==================== VOLATILITY FILTER ====================
            if 'volatility-enabled' in params and params['volatility-enabled']:
                atr_period = params.get('atr-period', 14)
                volatility_threshold = params.get('volatility-threshold', 0.02)

                # Calculate ATR if not exists
                if f'atr_{atr_period}' not in dataframe.columns:
                    dataframe[f'atr_{atr_period}'] = ta.ATR(dataframe, timeperiod=atr_period)
                    dataframe[f'atr_percent_{atr_period}'] = (
                        dataframe[f'atr_{atr_period}'] / dataframe['close'] * 100
                    )

                volatility_condition = dataframe[f'atr_percent_{atr_period}'] <= volatility_threshold * 100
                conditions.append(volatility_condition)

            # ==================== SIGNAL AGGREGATION ====================
            min_conditions = params.get('min-conditions', 3)

            if len(conditions) >= min_conditions:
                # Convert conditions to numeric and sum
                condition_sum = sum([cond.astype(int) for cond in conditions])
                final_condition = condition_sum >= min_conditions

                dataframe.loc[final_condition, 'buy'] = 1

            return dataframe

        return populate_buy_trend

    @staticmethod
    def sell_strategy_generator(params: Dict[str, Any]) -> Callable:
        """
        Define the sell strategy space for optimization
        """
        def populate_sell_trend(dataframe, metadata):
            """Optimized sell strategy logic"""

            conditions = []

            # ==================== RSI SELL CONDITIONS ====================
            if 'rsi-enabled' in params and params['rsi-enabled']:
                rsi_period = params.get('rsi-period', 14)
                rsi_overbought = params.get('rsi-overbought', 70)

                if f'rsi_{rsi_period}' not in dataframe.columns:
                    dataframe[f'rsi_{rsi_period}'] = ta.RSI(dataframe, timeperiod=rsi_period)

                conditions.append(dataframe[f'rsi_{rsi_period}'] > rsi_overbought)

            # ==================== MACD SELL CONDITIONS ====================
            if 'macd-enabled' in params and params['macd-enabled']:
                macd_fast = params.get('macd-fast', 12)
                macd_slow = params.get('macd-slow', 26)
                macd_signal = params.get('macd-signal', 9)

                macd_key = f'macd_{macd_fast}_{macd_slow}_{macd_signal}'
                if f'{macd_key}_macd' not in dataframe.columns:
                    macd = ta.MACD(dataframe,
                                  fastperiod=macd_fast,
                                  slowperiod=macd_slow,
                                  signalperiod=macd_signal)
                    dataframe[f'{macd_key}_macd'] = macd['macd']
                    dataframe[f'{macd_key}_signal'] = macd['macdsignal']
                    dataframe[f'{macd_key}_hist'] = macd['macdhist']

                # MACD bearish crossover
                macd_condition = (
                    (dataframe[f'{macd_key}_macd'] < dataframe[f'{macd_key}_signal']) &
                    (dataframe[f'{macd_key}_hist'] < dataframe[f'{macd_key}_hist'].shift(1))
                )
                conditions.append(macd_condition)

            # ==================== BOLLINGER BANDS SELL CONDITIONS ====================
            if 'bb-enabled' in params and params['bb-enabled']:
                bb_period = params.get('bb-period', 20)
                bb_std = params.get('bb-std', 2.0)

                bb_key = f'bb_{bb_period}_{bb_std:.1f}'
                if f'{bb_key}_percent' not in dataframe.columns:
                    bollinger = qtpylib.bollinger_bands(
                        dataframe['close'],
                        window=bb_period,
                        stds=bb_std
                    )
                    dataframe[f'{bb_key}_lower'] = bollinger['lower']
                    dataframe[f'{bb_key}_upper'] = bollinger['upper']
                    dataframe[f'{bb_key}_percent'] = (
                        (dataframe['close'] - bollinger['lower']) /
                        (bollinger['upper'] - bollinger['lower'])
                    )

                # Near upper Bollinger Band
                bb_overbought_threshold = params.get('bb-overbought-threshold', 0.9)
                bb_condition = dataframe[f'{bb_key}_percent'] >= bb_overbought_threshold
                conditions.append(bb_condition)

            # ==================== PROFIT TAKING ====================
            if 'profit-enabled' in params and params['profit-enabled']:
                profit_threshold = params.get('profit-threshold', 0.02)
                # This would need trade information - simplified for hyperopt
                conditions.append(dataframe['close'] > dataframe['close'].shift(5) * (1 + profit_threshold))

            # ==================== SIGNAL AGGREGATION ====================
            min_sell_conditions = params.get('min-sell-conditions', 2)

            if len(conditions) >= min_sell_conditions:
                condition_sum = sum([cond.astype(int) for cond in conditions])
                final_condition = condition_sum >= min_sell_conditions

                dataframe.loc[final_condition, 'sell'] = 1

            return dataframe

        return populate_sell_trend

    @staticmethod
    def buy_params_space() -> List[Dimension]:
        """
        Define parameter space for buy strategy optimization
        """
        return [
            # ==================== INDICATOR ENABLERS ====================
            Categorical([True, False], name='rsi-enabled'),
            Categorical([True, False], name='macd-enabled'),
            Categorical([True, False], name='bb-enabled'),
            Categorical([True, False], name='volume-enabled'),
            Categorical([True, False], name='trend-enabled'),
            Categorical([True, False], name='volatility-enabled'),

            # ==================== RSI PARAMETERS ====================
            Integer(10, 21, name='rsi-period'),
            Integer(25, 35, name='rsi-oversold'),

            # ==================== MACD PARAMETERS ====================
            Integer(8, 16, name='macd-fast'),
            Integer(20, 30, name='macd-slow'),
            Integer(6, 12, name='macd-signal'),

            # ==================== BOLLINGER BANDS PARAMETERS ====================
            Integer(15, 25, name='bb-period'),
            SKDecimal(1.5, 2.5, decimals=1, name='bb-std'),
            SKDecimal(0.05, 0.15, decimals=2, name='bb-oversold-threshold'),

            # ==================== VOLUME PARAMETERS ====================
            Integer(10, 30, name='volume-period'),
            SKDecimal(1.2, 2.0, decimals=1, name='volume-threshold'),

            # ==================== TREND PARAMETERS ====================
            Integer(15, 25, name='trend-short-period'),
            Integer(40, 60, name='trend-long-period'),

            # ==================== VOLATILITY PARAMETERS ====================
            Integer(10, 20, name='atr-period'),
            SKDecimal(0.015, 0.035, decimals=3, name='volatility-threshold'),

            # ==================== SIGNAL AGGREGATION ====================
            Integer(2, 5, name='min-conditions'),
        ]

    @staticmethod
    def sell_params_space() -> List[Dimension]:
        """
        Define parameter space for sell strategy optimization
        """
        return [
            # ==================== RSI SELL PARAMETERS ====================
            Integer(65, 80, name='rsi-overbought'),

            # ==================== BOLLINGER BANDS SELL PARAMETERS ====================
            SKDecimal(0.85, 0.95, decimals=2, name='bb-overbought-threshold'),

            # ==================== PROFIT TAKING ====================
            Categorical([True, False], name='profit-enabled'),
            SKDecimal(0.015, 0.04, decimals=3, name='profit-threshold'),

            # ==================== SIGNAL AGGREGATION ====================
            Integer(1, 4, name='min-sell-conditions'),
        ]

    @staticmethod
    def stoploss_space() -> List[Dimension]:
        """
        Define parameter space for stoploss optimization
        """
        return [
            SKDecimal(-0.15, -0.05, decimals=2, name='stoploss'),
        ]

    @staticmethod
    def trailing_space() -> List[Dimension]:
        """
        Define parameter space for trailing stop optimization
        """
        return [
            # Trailing stop
            Categorical([True, False], name='trailing_stop'),
            SKDecimal(0.01, 0.05, decimals=3, name='trailing_stop_positive'),
            SKDecimal(0.005, 0.02, decimals=3, name='trailing_stop_positive_offset'),
            Categorical([True, False], name='trailing_only_offset_is_reached'),
        ]

    @staticmethod
    def roi_space() -> List[Dimension]:
        """
        Define parameter space for ROI table optimization
        """
        return [
            Integer(10, 120, name='roi_t1'),
            Integer(10, 60, name='roi_t2'),
            Integer(10, 40, name='roi_t3'),
            SKDecimal(0.01, 0.04, decimals=3, name='roi_p1'),
            SKDecimal(0.01, 0.07, decimals=3, name='roi_p2'),
            SKDecimal(0.01, 0.20, decimals=3, name='roi_p3'),
        ]

    def populate_buy_trend(self, dataframe, metadata):
        """
        Based on TA indicators, populates the buy signal for the given dataframe
        This method is called during hyperopt optimization
        """
        params = self.buy_params if hasattr(self, 'buy_params') else {}

        buy_strategy = self.buy_strategy_generator(params)
        return buy_strategy(dataframe, metadata)

    def populate_sell_trend(self, dataframe, metadata):
        """
        Based on TA indicators, populates the sell signal for the given dataframe
        This method is called during hyperopt optimization
        """
        params = self.sell_params if hasattr(self, 'sell_params') else {}

        sell_strategy = self.sell_strategy_generator(params)
        return sell_strategy(dataframe, metadata)

    @staticmethod
    def generate_roi_table(params: Dict) -> Dict[int, float]:
        """
        Generate optimal ROI table from hyperopt parameters
        """
        roi_t1 = params.get('roi_t1', 60)
        roi_t2 = params.get('roi_t2', 30)
        roi_t3 = params.get('roi_t3', 20)
        roi_p1 = params.get('roi_p1', 0.01)
        roi_p2 = params.get('roi_p2', 0.02)
        roi_p3 = params.get('roi_p3', 0.03)

        # Ensure time values are ordered correctly
        times = sorted([roi_t1, roi_t2, roi_t3], reverse=True)

        return {
            "0": roi_p1 + roi_p2 + roi_p3,
            str(times[2]): roi_p2 + roi_p3,
            str(times[1]): roi_p3,
            str(times[0]): 0
        }


# Import required libraries (for strategy methods)
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib