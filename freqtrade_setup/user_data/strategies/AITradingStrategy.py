# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file

import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional, Dict, Any
import pickle
import os
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter,
                                IStrategy, IntParameter)

# ML Libraries for AI Model
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    import joblib
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

class AITradingStrategy(IStrategy):
    """
    AI-Enhanced Trading Strategy
    Based on CoinGecko ML Components with RandomForest + GradientBoosting

    Features:
    - RandomForest for signal classification (BUY/SELL/HOLD)
    - GradientBoosting for price prediction
    - Dynamic position sizing based on confidence
    - Risk-adjusted signals with ATR
    - Technical indicators fallback
    """

    # Strategy interface version
    INTERFACE_VERSION = 3

    # Optimal timeframe for the strategy
    timeframe = '5m'

    # Can this strategy go short?
    can_short: bool = False

    # ROI table - Conservative approach
    minimal_roi = {
        "60": 0.01,    # 1% after 1 hour
        "30": 0.02,    # 2% after 30 minutes
        "15": 0.03,    # 3% after 15 minutes
        "0": 0.04      # 4% immediate
    }

    # Stoploss
    stoploss = -0.08  # 8% stop loss

    # Trailing stoploss
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

    # Hyperopt parameters for AI model
    ai_confidence_threshold = DecimalParameter(0.5, 0.9, default=0.65, space="buy")
    position_size_multiplier = DecimalParameter(0.5, 2.0, default=1.0, space="buy")
    risk_adjustment_factor = DecimalParameter(0.8, 1.5, default=1.0, space="buy")

    # Technical fallback parameters
    rsi_buy = IntParameter(20, 40, default=30, space="buy")
    rsi_sell = IntParameter(60, 80, default=70, space="sell")

    # Order types
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    # Order time in force
    order_time_in_force = {
        'entry': 'gtc',
        'exit': 'gtc'
    }

    startup_candle_count: int = 100

    def __init__(self, config: dict) -> None:
        super().__init__(config)

        # AI Model components
        self.ml_available = ML_AVAILABLE
        self.is_model_trained = False
        self.model_signal = None
        self.model_price = None
        self.scaler = StandardScaler()
        self.feature_columns = []

        # Model parameters
        self.signal_confidence_threshold = 0.65
        self.min_training_samples = 100
        self.feature_importance = {}

        # Model file paths
        self.models_dir = "user_data/models"
        self.ensure_models_directory()

        # Initialize ML models if available
        if self.ml_available:
            self.initialize_ml_models()

    def ensure_models_directory(self):
        """Ensure models directory exists"""
        os.makedirs(self.models_dir, exist_ok=True)

    def initialize_ml_models(self):
        """Initialize or load pre-trained ML models"""
        try:
            # Try to load existing models
            signal_model_path = os.path.join(self.models_dir, "signal_model.pkl")
            price_model_path = os.path.join(self.models_dir, "price_model.pkl")
            scaler_path = os.path.join(self.models_dir, "scaler.pkl")

            if all(os.path.exists(path) for path in [signal_model_path, price_model_path, scaler_path]):
                self.model_signal = joblib.load(signal_model_path)
                self.model_price = joblib.load(price_model_path)
                self.scaler = joblib.load(scaler_path)
                self.is_model_trained = True
                print("[AI Strategy] Pre-trained models loaded successfully")
            else:
                print("[AI Strategy] No pre-trained models found. Will use technical fallback.")

        except Exception as e:
            print(f"[AI Strategy] Error loading models: {e}")
            self.is_model_trained = False

    def informative_pairs(self):
        """Additional pairs for analysis"""
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate indicators for both AI model and technical analysis
        """

        # Basic OHLCV validation
        if dataframe.empty:
            return dataframe

        # Price-based features
        dataframe['price_change_1'] = dataframe['close'].pct_change(1)
        dataframe['price_change_3'] = dataframe['close'].pct_change(3)
        dataframe['price_change_7'] = dataframe['close'].pct_change(7)

        # Volatility features
        dataframe['volatility_5'] = dataframe['close'].rolling(5).std() / dataframe['close'].rolling(5).mean()
        dataframe['volatility_20'] = dataframe['close'].rolling(20).std() / dataframe['close'].rolling(20).mean()

        # Volume features
        dataframe['volume_change'] = dataframe['volume'].pct_change(1)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume'].rolling(20).mean()

        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['rsi_oversold'] = (dataframe['rsi'] < 30).astype(int)
        dataframe['rsi_overbought'] = (dataframe['rsi'] > 70).astype(int)

        # MACD
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macd_signal'] = macd['macdsignal']
        dataframe['macd_hist'] = macd['macdhist']
        dataframe['macd_crossover'] = (dataframe['macd'] > dataframe['macd_signal']).astype(int)

        # Bollinger Bands
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_lower'] = bollinger['lower']
        dataframe['bb_middle'] = bollinger['mid']
        dataframe['bb_upper'] = bollinger['upper']
        dataframe['bb_position'] = (dataframe['close'] - dataframe['bb_lower']) / (dataframe['bb_upper'] - dataframe['bb_lower'])

        # ATR for risk adjustment
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close']

        # Moving Averages
        dataframe['sma_20'] = ta.SMA(dataframe, timeperiod=20)
        dataframe['sma_50'] = ta.SMA(dataframe, timeperiod=50)
        dataframe['ema_12'] = ta.EMA(dataframe, timeperiod=12)
        dataframe['ema_26'] = ta.EMA(dataframe, timeperiod=26)

        # Trend features
        dataframe['trend_short_long'] = (dataframe['sma_20'] > dataframe['sma_50']).astype(int)

        # AI Model predictions (if available and trained)
        if self.ml_available and self.is_model_trained:
            dataframe = self.add_ai_predictions(dataframe)
        else:
            # Add technical fallback signals
            dataframe = self.add_technical_signals(dataframe)

        return dataframe

    def add_ai_predictions(self, dataframe: DataFrame) -> DataFrame:
        """Add AI model predictions to dataframe"""
        try:
            # Prepare feature columns for prediction
            feature_columns = [
                'price_change_1', 'price_change_3', 'price_change_7',
                'volatility_5', 'volatility_20', 'volume_change', 'volume_ratio',
                'rsi', 'rsi_oversold', 'rsi_overbought',
                'macd', 'macd_signal', 'macd_crossover',
                'bb_position', 'atr_pct', 'trend_short_long'
            ]

            # Check if all required features are available
            available_features = [col for col in feature_columns if col in dataframe.columns]

            if len(available_features) >= 10:  # Minimum features required
                # Prepare features for prediction
                features_df = dataframe[available_features].copy()
                features_df = features_df.fillna(method='ffill').fillna(0)

                # Initialize prediction columns
                dataframe['ai_signal'] = 'HOLD'
                dataframe['ai_confidence'] = 0.5
                dataframe['ai_predicted_return'] = 0.0

                # Make predictions for each row where we have enough history
                for i in range(50, len(dataframe)):  # Need some history for features
                    try:
                        current_features = features_df.iloc[i:i+1]

                        if not current_features.isna().any().any():
                            # Scale features
                            features_scaled = self.scaler.transform(current_features)

                            # Predict signal
                            signal_proba = self.model_signal.predict_proba(features_scaled)[0]
                            signal_classes = self.model_signal.classes_
                            signal_confidence = max(signal_proba)
                            predicted_signal = signal_classes[np.argmax(signal_proba)]

                            # Predict price movement
                            predicted_return = self.model_price.predict(features_scaled)[0]

                            # Apply confidence threshold
                            if signal_confidence < self.signal_confidence_threshold:
                                predicted_signal = 'HOLD'

                            # Update dataframe
                            dataframe.iloc[i, dataframe.columns.get_loc('ai_signal')] = predicted_signal
                            dataframe.iloc[i, dataframe.columns.get_loc('ai_confidence')] = signal_confidence
                            dataframe.iloc[i, dataframe.columns.get_loc('ai_predicted_return')] = predicted_return

                    except Exception as e:
                        # Skip this prediction if there's an error
                        continue

        except Exception as e:
            print(f"[AI Strategy] Error in AI predictions: {e}")
            dataframe = self.add_technical_signals(dataframe)

        return dataframe

    def add_technical_signals(self, dataframe: DataFrame) -> DataFrame:
        """Add technical analysis signals as fallback"""
        # Initialize signal columns
        dataframe['ai_signal'] = 'HOLD'
        dataframe['ai_confidence'] = 0.5
        dataframe['ai_predicted_return'] = 0.0

        # Calculate technical signal score
        for i in range(len(dataframe)):
            signal_score = 0
            total_indicators = 0

            # RSI analysis
            if not pd.isna(dataframe.iloc[i]['rsi']):
                rsi = dataframe.iloc[i]['rsi']
                if rsi < 30:
                    signal_score += 2  # Strong buy
                elif rsi < 50:
                    signal_score += 1  # Mild buy
                elif rsi > 70:
                    signal_score -= 2  # Strong sell
                elif rsi > 50:
                    signal_score -= 1  # Mild sell
                total_indicators += 1

            # MACD analysis
            if not pd.isna(dataframe.iloc[i]['macd_crossover']):
                if dataframe.iloc[i]['macd_crossover'] == 1:
                    signal_score += 1
                else:
                    signal_score -= 1
                total_indicators += 1

            # Bollinger Bands analysis
            if not pd.isna(dataframe.iloc[i]['bb_position']):
                bb_pos = dataframe.iloc[i]['bb_position']
                if bb_pos < 0.2:  # Near lower band
                    signal_score += 1
                elif bb_pos > 0.8:  # Near upper band
                    signal_score -= 1
                total_indicators += 1

            # Determine final signal
            if total_indicators > 0:
                normalized_score = signal_score / total_indicators

                if normalized_score > 0.5:
                    dataframe.iloc[i, dataframe.columns.get_loc('ai_signal')] = 'BUY'
                    confidence = min(0.8, 0.5 + normalized_score)
                elif normalized_score < -0.5:
                    dataframe.iloc[i, dataframe.columns.get_loc('ai_signal')] = 'SELL'
                    confidence = min(0.8, 0.5 + abs(normalized_score))
                else:
                    dataframe.iloc[i, dataframe.columns.get_loc('ai_signal')] = 'HOLD'
                    confidence = 0.5

                dataframe.iloc[i, dataframe.columns.get_loc('ai_confidence')] = confidence

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on AI predictions and technical analysis, populate the entry signal
        """

        # AI-based entry conditions
        ai_buy_condition = (
            (dataframe['ai_signal'] == 'BUY') &
            (dataframe['ai_confidence'] > self.ai_confidence_threshold.value) &
            (dataframe['volume'] > 0)  # Basic volume check
        )

        # Technical confirmation for safety
        technical_confirmation = (
            (dataframe['rsi'] < 70) &  # Not overbought
            (dataframe['bb_position'] < 0.9) &  # Not at upper BB
            (dataframe['volume'] > dataframe['volume'].rolling(10).mean()) &  # Volume above average
            (dataframe['trend_short_long'] == 1)  # Uptrend
        )

        # Combined entry condition
        dataframe.loc[
            ai_buy_condition & technical_confirmation,
            'enter_long'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on AI predictions and technical analysis, populate the exit signal
        """

        # AI-based exit conditions
        ai_sell_condition = (
            (dataframe['ai_signal'] == 'SELL') &
            (dataframe['ai_confidence'] > self.ai_confidence_threshold.value)
        )

        # Technical exit conditions
        technical_exit = (
            (dataframe['rsi'] > 75) |  # Overbought
            (dataframe['bb_position'] > 0.9) |  # At upper BB
            (dataframe['macd'] < dataframe['macd_signal'])  # MACD bearish
        )

        # Risk management exit (rapid price drop)
        risk_exit = (
            (dataframe['price_change_1'] < -0.03) &  # 3% drop in one period
            (dataframe['ai_confidence'] < 0.6)  # Low confidence
        )

        # Combined exit condition
        dataframe.loc[
            ai_sell_condition | technical_exit | risk_exit,
            'exit_long'
        ] = 1

        return dataframe

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                          proposed_stake: float, min_stake: float, max_stake: float,
                          **kwargs) -> float:
        """
        Dynamic position sizing based on AI confidence and risk assessment
        """
        try:
            # Get the latest dataframe
            dataframe = self.dp.get_pair_dataframe(pair, self.timeframe)

            if dataframe.empty:
                return proposed_stake

            latest = dataframe.iloc[-1]

            # Base position size adjustment
            confidence_multiplier = 1.0

            # Adjust based on AI confidence
            if 'ai_confidence' in latest.index and not pd.isna(latest['ai_confidence']):
                ai_confidence = latest['ai_confidence']
                # Higher confidence = larger position (within limits)
                confidence_multiplier = max(0.5, min(1.5, ai_confidence * 1.5))

            # Risk adjustment based on volatility
            risk_multiplier = 1.0
            if 'atr_pct' in latest.index and not pd.isna(latest['atr_pct']):
                atr_pct = latest['atr_pct']
                # Higher volatility = smaller position
                risk_multiplier = max(0.5, min(1.5, 1.0 / (1.0 + atr_pct * 10)))

            # Apply multipliers
            adjusted_stake = proposed_stake * confidence_multiplier * risk_multiplier * self.position_size_multiplier.value

            # Ensure within bounds
            adjusted_stake = max(min_stake, min(adjusted_stake, max_stake))

            return adjusted_stake

        except Exception as e:
            print(f"[AI Strategy] Error in position sizing: {e}")
            return proposed_stake

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float,
                           rate: float, time_in_force: str, current_time: datetime,
                           **kwargs) -> bool:
        """
        Final confirmation before entering a trade
        """
        try:
            # Get latest data
            dataframe = self.dp.get_pair_dataframe(pair, self.timeframe)

            if dataframe.empty:
                return False

            latest = dataframe.iloc[-1]

            # Check AI signal strength
            if 'ai_confidence' in latest.index:
                ai_confidence = latest['ai_confidence']
                if ai_confidence < self.ai_confidence_threshold.value:
                    return False

            # Additional risk checks
            if 'atr_pct' in latest.index:
                atr_pct = latest['atr_pct']
                if atr_pct > 0.05:  # Too volatile (>5% ATR)
                    return False

            # Volume confirmation
            if 'volume_ratio' in latest.index:
                volume_ratio = latest['volume_ratio']
                if volume_ratio < 0.5:  # Too low volume
                    return False

            return True

        except Exception as e:
            print(f"[AI Strategy] Error in trade confirmation: {e}")
            return False

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                       current_rate: float, current_profit: float, **kwargs) -> float:
        """
        Dynamic stoploss based on AI predictions and market conditions
        """
        try:
            # Get latest data
            dataframe = self.dp.get_pair_dataframe(pair, self.timeframe)

            if dataframe.empty:
                return self.stoploss

            latest = dataframe.iloc[-1]

            # Base stoploss
            dynamic_stoploss = self.stoploss

            # Adjust based on AI confidence
            if 'ai_confidence' in latest.index and not pd.isna(latest['ai_confidence']):
                ai_confidence = latest['ai_confidence']
                # Higher confidence = tighter stoploss
                if ai_confidence > 0.8:
                    dynamic_stoploss = max(dynamic_stoploss, -0.06)  # Tighter stoploss
                elif ai_confidence < 0.6:
                    dynamic_stoploss = min(dynamic_stoploss, -0.12)  # Wider stoploss

            # Adjust based on volatility
            if 'atr_pct' in latest.index and not pd.isna(latest['atr_pct']):
                atr_pct = latest['atr_pct']
                # Higher volatility = wider stoploss
                volatility_adjustment = min(0.02, atr_pct * 2)
                dynamic_stoploss -= volatility_adjustment

            return dynamic_stoploss

        except Exception as e:
            print(f"[AI Strategy] Error in dynamic stoploss: {e}")
            return self.stoploss