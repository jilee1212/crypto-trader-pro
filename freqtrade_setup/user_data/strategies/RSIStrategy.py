# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
# --- Do not remove these libs ---
import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame  # noqa
from datetime import datetime
from typing import Optional

from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter,
                                IStrategy, IntParameter)

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


class RSIStrategy(IStrategy):
    """
    Conservative RSI-based strategy for crypto trading
    Based on RSI overbought/oversold levels with additional confirmations
    """

    # Strategy interface version - allow new iterations of the strategy interface.
    # Check the documentation or the Sample strategy to get the latest version.
    INTERFACE_VERSION = 3

    # Optimal timeframe for the strategy.
    timeframe = '5m'

    # Can this strategy go short?
    can_short: bool = False

    # Minimal ROI designed for the strategy.
    minimal_roi = {
        "60": 0.01,
        "30": 0.02,
        "0": 0.04
    }

    # Optimal stoploss designed for the strategy.
    stoploss = -0.10

    # Trailing stoploss
    trailing_stop = False

    # Hyperopt parameters
    buy_rsi_value = IntParameter(20, 40, default=30, space="buy")
    sell_rsi_value = IntParameter(60, 80, default=70, space="sell")

    # Optional order type mapping.
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    # Optional order time in force.
    order_time_in_force = {
        'entry': 'gtc',
        'exit': 'gtc'
    }

    startup_candle_count: int = 30

    def informative_pairs(self):
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds several different TA indicators to the given DataFrame
        """

        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        # Bollinger Bands
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_upperband'] = bollinger['upper']
        dataframe["bb_percent"] = (
            (dataframe["close"] - dataframe["bb_lowerband"]) /
            (dataframe["bb_upperband"] - dataframe["bb_lowerband"])
        )
        dataframe["bb_width"] = (
            (dataframe["bb_upperband"] - dataframe["bb_lowerband"]) / dataframe["bb_middleband"]
        )

        # MACD
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']

        # SMA - Simple Moving Average
        dataframe['sma_fast'] = ta.SMA(dataframe, timeperiod=10)
        dataframe['sma_slow'] = ta.SMA(dataframe, timeperiod=25)

        # EMA - Exponential Moving Average
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=12)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=26)

        # Volume indicators
        dataframe['ad'] = ta.AD(dataframe)
        dataframe['obv'] = ta.OBV(dataframe)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the entry signal for the given dataframe
        :param dataframe: DataFrame
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with entry columns populated
        """
        dataframe.loc[
            (
                # RSI is oversold
                (dataframe['rsi'] < self.buy_rsi_value.value) &

                # Volume is above average
                (dataframe['volume'] > dataframe['volume'].rolling(20).mean()) &

                # Price is near lower Bollinger Band
                (dataframe['bb_percent'] < 0.2) &

                # MACD is showing potential reversal
                (dataframe['macd'] > dataframe['macdsignal']) &

                # Price is above EMA fast (trend confirmation)
                (dataframe['close'] > dataframe['ema_fast']) &

                # Additional safety: not in strong downtrend
                (dataframe['ema_fast'] > dataframe['ema_slow'])
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the exit signal for the given dataframe
        :param dataframe: DataFrame
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with exit columns populated
        """
        dataframe.loc[
            (
                # RSI is overbought
                (dataframe['rsi'] > self.sell_rsi_value.value) &

                # Price is near upper Bollinger Band
                (dataframe['bb_percent'] > 0.8) &

                # MACD is showing potential reversal
                (dataframe['macd'] < dataframe['macdsignal']) &

                # Volume confirmation
                (dataframe['volume'] > dataframe['volume'].rolling(10).mean())
            ),
            'exit_long'] = 1

        return dataframe