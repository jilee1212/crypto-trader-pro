#!/usr/bin/env python3
"""
AI Model Training Script for Freqtrade AITradingStrategy
Trains RandomForest + GradientBoosting models based on historical data
"""

import sys
import os
import pandas as pd
import numpy as np
import ccxt
import talib as ta
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ML Libraries
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, mean_squared_error, r2_score
import joblib

class AIModelTrainer:
    """AI Model Trainer for Freqtrade Strategy"""

    def __init__(self, exchange_name='binance', sandbox=True):
        self.exchange = self.setup_exchange(exchange_name, sandbox)
        self.scaler = StandardScaler()
        self.model_signal = None
        self.model_price = None
        self.feature_columns = []

        # Training parameters
        self.lookback_days = 90
        self.prediction_horizon = 5  # 5 periods ahead
        self.min_samples = 200
        self.test_size = 0.2

        # Model save directory
        self.models_dir = "user_data/models"
        os.makedirs(self.models_dir, exist_ok=True)

    def setup_exchange(self, exchange_name, sandbox):
        """Setup exchange connection"""
        try:
            if exchange_name.lower() == 'binance':
                exchange = ccxt.binance({
                    'sandbox': sandbox,
                    'enableRateLimit': True,
                    'options': {'defaultType': 'spot'}
                })
            else:
                raise ValueError(f"Exchange {exchange_name} not supported")

            exchange.load_markets()
            return exchange

        except Exception as e:
            print(f"[ERROR] Failed to setup exchange: {e}")
            return None

    def fetch_historical_data(self, symbol='BTC/USDT', timeframe='5m'):
        """Fetch historical data from exchange"""
        try:
            if not self.exchange:
                raise Exception("Exchange not initialized")

            print(f"[INFO] Fetching historical data for {symbol}...")

            # Calculate how many candles we need
            since = self.exchange.parse8601(
                (datetime.now() - timedelta(days=self.lookback_days)).isoformat()
            )

            # Fetch OHLCV data
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since)

            if not ohlcv:
                raise Exception("No data received from exchange")

            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            print(f"[INFO] Fetched {len(df)} candles from {df.index[0]} to {df.index[-1]}")
            return df

        except Exception as e:
            print(f"[ERROR] Failed to fetch data: {e}")
            return None

    def calculate_technical_indicators(self, df):
        """Calculate technical indicators same as in AITradingStrategy"""
        try:
            print("[INFO] Calculating technical indicators...")

            # Price-based features
            df['price_change_1'] = df['close'].pct_change(1)
            df['price_change_3'] = df['close'].pct_change(3)
            df['price_change_7'] = df['close'].pct_change(7)

            # Volatility features
            df['volatility_5'] = df['close'].rolling(5).std() / df['close'].rolling(5).mean()
            df['volatility_20'] = df['close'].rolling(20).std() / df['close'].rolling(20).mean()

            # Volume features
            df['volume_change'] = df['volume'].pct_change(1)
            df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()

            # RSI
            df['rsi'] = ta.RSI(df['close'].values, timeperiod=14)
            df['rsi_oversold'] = (df['rsi'] < 30).astype(int)
            df['rsi_overbought'] = (df['rsi'] > 70).astype(int)

            # MACD
            macd, macdsignal, macdhist = ta.MACD(df['close'].values)
            df['macd'] = macd
            df['macd_signal'] = macdsignal
            df['macd_hist'] = macdhist
            df['macd_crossover'] = (df['macd'] > df['macd_signal']).astype(int)

            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = ta.BBANDS(df['close'].values, timeperiod=20)
            df['bb_upper'] = bb_upper
            df['bb_middle'] = bb_middle
            df['bb_lower'] = bb_lower
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

            # ATR
            df['atr'] = ta.ATR(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)
            df['atr_pct'] = df['atr'] / df['close']

            # Moving Averages
            df['sma_20'] = ta.SMA(df['close'].values, timeperiod=20)
            df['sma_50'] = ta.SMA(df['close'].values, timeperiod=50)

            # Trend features
            df['trend_short_long'] = (df['sma_20'] > df['sma_50']).astype(int)

            print(f"[INFO] Technical indicators calculated. Shape: {df.shape}")
            return df

        except Exception as e:
            print(f"[ERROR] Failed to calculate indicators: {e}")
            return df

    def create_labels(self, df):
        """Create training labels"""
        try:
            print("[INFO] Creating training labels...")

            # Future returns for price prediction
            df['future_return'] = df['close'].shift(-self.prediction_horizon).pct_change()

            # Signal labels based on future returns
            conditions = [
                df['future_return'] > 0.015,   # BUY: >1.5% return
                df['future_return'] < -0.015   # SELL: <-1.5% return
            ]
            choices = ['BUY', 'SELL']
            df['signal_label'] = np.select(conditions, choices, default='HOLD')

            # Remove rows without future data
            df = df[:-self.prediction_horizon]

            print(f"[INFO] Labels created. Signal distribution:")
            print(df['signal_label'].value_counts())

            return df

        except Exception as e:
            print(f"[ERROR] Failed to create labels: {e}")
            return df

    def prepare_training_data(self, df):
        """Prepare features and labels for training"""
        try:
            print("[INFO] Preparing training data...")

            # Select feature columns
            feature_columns = [
                'price_change_1', 'price_change_3', 'price_change_7',
                'volatility_5', 'volatility_20', 'volume_change', 'volume_ratio',
                'rsi', 'rsi_oversold', 'rsi_overbought',
                'macd', 'macd_signal', 'macd_crossover',
                'bb_position', 'atr_pct', 'trend_short_long'
            ]

            # Filter available columns
            available_features = [col for col in feature_columns if col in df.columns]
            self.feature_columns = available_features

            print(f"[INFO] Using {len(available_features)} features:")
            for feature in available_features:
                print(f"  - {feature}")

            # Prepare features and targets
            X = df[available_features].copy()
            y_signal = df['signal_label'].copy()
            y_price = df['future_return'].copy()

            # Remove rows with NaN values
            valid_mask = ~(X.isna().any(axis=1) | y_signal.isna() | y_price.isna())
            X = X[valid_mask]
            y_signal = y_signal[valid_mask]
            y_price = y_price[valid_mask]

            print(f"[INFO] Training data prepared. Valid samples: {len(X)}")

            if len(X) < self.min_samples:
                raise Exception(f"Insufficient data: {len(X)} < {self.min_samples}")

            return X, y_signal, y_price

        except Exception as e:
            print(f"[ERROR] Failed to prepare training data: {e}")
            return None, None, None

    def train_models(self, X, y_signal, y_price):
        """Train RandomForest and GradientBoosting models"""
        try:
            print("[INFO] Training ML models...")

            # Split data
            X_train, X_test, y_signal_train, y_signal_test, y_price_train, y_price_test = train_test_split(
                X, y_signal, y_price, test_size=self.test_size, random_state=42, stratify=y_signal
            )

            print(f"[INFO] Train samples: {len(X_train)}, Test samples: {len(X_test)}")

            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            # Train signal classification model (RandomForest)
            print("[INFO] Training signal classification model...")
            self.model_signal = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                class_weight='balanced',
                n_jobs=-1
            )

            self.model_signal.fit(X_train_scaled, y_signal_train)

            # Evaluate signal model
            signal_train_score = self.model_signal.score(X_train_scaled, y_signal_train)
            signal_test_score = self.model_signal.score(X_test_scaled, y_signal_test)

            print(f"[INFO] Signal model - Train accuracy: {signal_train_score:.3f}, Test accuracy: {signal_test_score:.3f}")

            # Train price prediction model (GradientBoosting)
            print("[INFO] Training price prediction model...")
            self.model_price = GradientBoostingRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42
            )

            self.model_price.fit(X_train_scaled, y_price_train)

            # Evaluate price model
            price_train_pred = self.model_price.predict(X_train_scaled)
            price_test_pred = self.model_price.predict(X_test_scaled)

            price_train_r2 = r2_score(y_price_train, price_train_pred)
            price_test_r2 = r2_score(y_price_test, price_test_pred)

            print(f"[INFO] Price model - Train R²: {price_train_r2:.3f}, Test R²: {price_test_r2:.3f}")

            # Feature importance
            feature_importance = dict(zip(self.feature_columns, self.model_signal.feature_importances_))
            print("[INFO] Top 10 most important features:")
            for feature, importance in sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {feature}: {importance:.3f}")

            return {
                'signal_train_accuracy': signal_train_score,
                'signal_test_accuracy': signal_test_score,
                'price_train_r2': price_train_r2,
                'price_test_r2': price_test_r2,
                'feature_importance': feature_importance
            }

        except Exception as e:
            print(f"[ERROR] Failed to train models: {e}")
            return None

    def save_models(self):
        """Save trained models to disk"""
        try:
            print("[INFO] Saving models...")

            # Save models
            signal_model_path = os.path.join(self.models_dir, "signal_model.pkl")
            price_model_path = os.path.join(self.models_dir, "price_model.pkl")
            scaler_path = os.path.join(self.models_dir, "scaler.pkl")
            features_path = os.path.join(self.models_dir, "feature_columns.pkl")

            joblib.dump(self.model_signal, signal_model_path)
            joblib.dump(self.model_price, price_model_path)
            joblib.dump(self.scaler, scaler_path)
            joblib.dump(self.feature_columns, features_path)

            # Save training metadata
            metadata = {
                'timestamp': datetime.now().isoformat(),
                'feature_columns': self.feature_columns,
                'prediction_horizon': self.prediction_horizon,
                'lookback_days': self.lookback_days
            }

            metadata_path = os.path.join(self.models_dir, "metadata.json")
            import json
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            print(f"[INFO] Models saved to {self.models_dir}")
            print(f"  - Signal model: {signal_model_path}")
            print(f"  - Price model: {price_model_path}")
            print(f"  - Scaler: {scaler_path}")
            print(f"  - Features: {features_path}")
            print(f"  - Metadata: {metadata_path}")

        except Exception as e:
            print(f"[ERROR] Failed to save models: {e}")

    def train_full_pipeline(self, symbol='BTC/USDT', timeframe='5m'):
        """Execute full training pipeline"""
        print(f"[INFO] Starting AI model training for {symbol} ({timeframe})")
        print("=" * 60)

        # 1. Fetch data
        df = self.fetch_historical_data(symbol, timeframe)
        if df is None:
            return False

        # 2. Calculate indicators
        df = self.calculate_technical_indicators(df)

        # 3. Create labels
        df = self.create_labels(df)

        # 4. Prepare training data
        X, y_signal, y_price = self.prepare_training_data(df)
        if X is None:
            return False

        # 5. Train models
        results = self.train_models(X, y_signal, y_price)
        if results is None:
            return False

        # 6. Save models
        self.save_models()

        print("=" * 60)
        print("[SUCCESS] AI model training completed!")
        print(f"Signal Model Accuracy: {results['signal_test_accuracy']:.3f}")
        print(f"Price Model R²: {results['price_test_r2']:.3f}")
        print("\nModels are ready for use in AITradingStrategy!")

        return True

def main():
    """Main training script"""
    import argparse

    parser = argparse.ArgumentParser(description='Train AI models for Freqtrade')
    parser.add_argument('--symbol', default='BTC/USDT', help='Trading pair to train on')
    parser.add_argument('--timeframe', default='5m', help='Timeframe for training data')
    parser.add_argument('--days', type=int, default=90, help='Days of historical data')
    parser.add_argument('--exchange', default='binance', help='Exchange to use')
    parser.add_argument('--sandbox', action='store_true', default=True, help='Use sandbox/testnet')

    args = parser.parse_args()

    # Initialize trainer
    trainer = AIModelTrainer(exchange_name=args.exchange, sandbox=args.sandbox)
    trainer.lookback_days = args.days

    # Run training
    success = trainer.train_full_pipeline(args.symbol, args.timeframe)

    if success:
        print("\n[INFO] You can now use the AITradingStrategy in Freqtrade!")
        print("Run: freqtrade backtesting --strategy AITradingStrategy")
    else:
        print("\n[ERROR] Training failed. Check the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main()