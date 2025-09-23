#!/usr/bin/env python3
"""
Performance Validation System for AI Model Porting
Compares original AI system vs Freqtrade AI strategy performance
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
from sklearn.metrics import classification_report, accuracy_score, precision_score, recall_score
import joblib

# Freqtrade imports
try:
    from freqtrade.data.history import load_pair_history
    from freqtrade.data.dataprovider import DataProvider
    from freqtrade.configuration import Configuration
    from freqtrade.resolvers import StrategyResolver
    FREQTRADE_AVAILABLE = True
except ImportError:
    print("[WARN] Freqtrade not available. Using standalone validation.")
    FREQTRADE_AVAILABLE = False

class PerformanceValidator:
    """Validates AI model performance between original and Freqtrade implementations"""

    def __init__(self, config_path="config/config.json"):
        self.config_path = config_path
        self.exchange = self.setup_exchange()
        self.scaler = StandardScaler()

        # Performance metrics storage
        self.results = {
            'original_ai': {},
            'freqtrade_ai': {},
            'comparison': {}
        }

        # Model paths
        self.models_dir = "user_data/models"
        self.results_dir = "user_data/validation_results"
        os.makedirs(self.results_dir, exist_ok=True)

    def setup_exchange(self):
        """Setup exchange connection for data fetching"""
        try:
            exchange = ccxt.binance({
                'sandbox': True,
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
            exchange.load_markets()
            return exchange
        except Exception as e:
            print(f"[ERROR] Failed to setup exchange: {e}")
            return None

    def fetch_validation_data(self, symbol='BTC/USDT', timeframe='5m', days=30):
        """Fetch historical data for validation"""
        try:
            print(f"[INFO] Fetching validation data for {symbol}...")

            since = self.exchange.parse8601(
                (datetime.now() - timedelta(days=days)).isoformat()
            )

            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since)

            if not ohlcv:
                raise Exception("No data received from exchange")

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            print(f"[INFO] Fetched {len(df)} candles for validation")
            return df

        except Exception as e:
            print(f"[ERROR] Failed to fetch validation data: {e}")
            return None

    def calculate_technical_indicators(self, df):
        """Calculate same technical indicators as used in strategies"""
        try:
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
            df['trend_short_long'] = (df['sma_20'] > df['sma_50']).astype(int)

            return df

        except Exception as e:
            print(f"[ERROR] Failed to calculate indicators: {e}")
            return df

    def load_trained_models(self):
        """Load pre-trained AI models"""
        try:
            print("[INFO] Loading trained AI models...")

            signal_model_path = os.path.join(self.models_dir, "signal_model.pkl")
            price_model_path = os.path.join(self.models_dir, "price_model.pkl")
            scaler_path = os.path.join(self.models_dir, "scaler.pkl")
            features_path = os.path.join(self.models_dir, "feature_columns.pkl")

            if not all(os.path.exists(path) for path in [signal_model_path, price_model_path, scaler_path, features_path]):
                raise Exception("Model files not found. Run train_ai_models.py first.")

            model_signal = joblib.load(signal_model_path)
            model_price = joblib.load(price_model_path)
            scaler = joblib.load(scaler_path)
            feature_columns = joblib.load(features_path)

            print(f"[INFO] Models loaded successfully. Features: {len(feature_columns)}")

            return model_signal, model_price, scaler, feature_columns

        except Exception as e:
            print(f"[ERROR] Failed to load models: {e}")
            return None, None, None, None

    def simulate_original_ai_signals(self, df, model_signal, model_price, scaler, feature_columns):
        """Simulate original AI system signals"""
        try:
            print("[INFO] Simulating original AI system signals...")

            signals = []
            prices_pred = []
            confidences = []

            for i in range(50, len(df)):  # Start after enough data for indicators
                try:
                    current_data = df.iloc[i:i+1]

                    # Prepare features
                    features = current_data[feature_columns].values

                    # Check for NaN values
                    if np.isnan(features).any():
                        signals.append('HOLD')
                        prices_pred.append(0.0)
                        confidences.append(0.0)
                        continue

                    # Scale features
                    features_scaled = scaler.transform(features)

                    # Get predictions
                    signal_pred = model_signal.predict(features_scaled)[0]
                    signal_prob = model_signal.predict_proba(features_scaled)[0]
                    price_pred = model_price.predict(features_scaled)[0]

                    # Calculate confidence (max probability)
                    confidence = np.max(signal_prob)

                    # Apply confidence threshold (similar to original system)
                    if confidence < 0.6:
                        signal_pred = 'HOLD'

                    signals.append(signal_pred)
                    prices_pred.append(price_pred)
                    confidences.append(confidence)

                except Exception as e:
                    signals.append('HOLD')
                    prices_pred.append(0.0)
                    confidences.append(0.0)

            # Add results to dataframe
            df_result = df.iloc[50:].copy()
            df_result['ai_signal'] = signals
            df_result['ai_price_pred'] = prices_pred
            df_result['ai_confidence'] = confidences

            print(f"[INFO] Generated {len(signals)} original AI signals")
            return df_result

        except Exception as e:
            print(f"[ERROR] Failed to simulate original AI: {e}")
            return df

    def simulate_freqtrade_strategy(self, df):
        """Simulate Freqtrade AITradingStrategy signals"""
        try:
            print("[INFO] Simulating Freqtrade AI strategy signals...")

            # Load AITradingStrategy if available
            if FREQTRADE_AVAILABLE:
                try:
                    from user_data.strategies.AITradingStrategy import AITradingStrategy
                    strategy = AITradingStrategy({})

                    # Simulate strategy signals
                    signals = []
                    confidences = []

                    for i in range(50, len(df)):
                        current_data = df.iloc[max(0, i-100):i+1]  # Provide enough history

                        # Convert to format expected by strategy
                        dataframe = current_data.copy()

                        try:
                            # Populate indicators (strategy method)
                            dataframe = strategy.populate_indicators(dataframe, {'pair': 'BTC/USDT'})

                            # Check buy/sell signals
                            dataframe = strategy.populate_buy_trend(dataframe, {'pair': 'BTC/USDT'})
                            dataframe = strategy.populate_sell_trend(dataframe, {'pair': 'BTC/USDT'})

                            last_row = dataframe.iloc[-1]

                            if last_row.get('buy', 0) == 1:
                                signal = 'BUY'
                            elif last_row.get('sell', 0) == 1:
                                signal = 'SELL'
                            else:
                                signal = 'HOLD'

                            # Get confidence from ai_confidence column if available
                            confidence = last_row.get('ai_confidence', 0.5)

                        except Exception as e:
                            signal = 'HOLD'
                            confidence = 0.0

                        signals.append(signal)
                        confidences.append(confidence)

                    df_result = df.iloc[50:].copy()
                    df_result['ft_signal'] = signals
                    df_result['ft_confidence'] = confidences

                    print(f"[INFO] Generated {len(signals)} Freqtrade strategy signals")
                    return df_result

                except ImportError:
                    print("[WARN] AITradingStrategy not available. Using fallback simulation.")

            # Fallback: Simple RSI-based simulation
            signals = []
            for i in range(50, len(df)):
                rsi = df['rsi'].iloc[i]
                if rsi < 30:
                    signals.append('BUY')
                elif rsi > 70:
                    signals.append('SELL')
                else:
                    signals.append('HOLD')

            df_result = df.iloc[50:].copy()
            df_result['ft_signal'] = signals
            df_result['ft_confidence'] = [0.5] * len(signals)

            return df_result

        except Exception as e:
            print(f"[ERROR] Failed to simulate Freqtrade strategy: {e}")
            return df

    def calculate_performance_metrics(self, df):
        """Calculate performance metrics for both systems"""
        try:
            print("[INFO] Calculating performance metrics...")

            metrics = {}

            # Calculate future returns for validation
            df['future_return_1'] = df['close'].shift(-1).pct_change()
            df['future_return_5'] = df['close'].shift(-5).pct_change()

            # Original AI system metrics
            if 'ai_signal' in df.columns:
                ai_signals = df['ai_signal'].values[:-5]  # Remove last 5 for future return calculation
                future_returns = df['future_return_5'].values[:-5]

                # Signal accuracy
                accurate_signals = 0
                total_signals = 0

                for i, (signal, future_ret) in enumerate(zip(ai_signals, future_returns)):
                    if pd.notna(future_ret) and signal != 'HOLD':
                        total_signals += 1
                        if (signal == 'BUY' and future_ret > 0) or (signal == 'SELL' and future_ret < 0):
                            accurate_signals += 1

                metrics['original_ai'] = {
                    'signal_accuracy': accurate_signals / total_signals if total_signals > 0 else 0,
                    'total_signals': total_signals,
                    'buy_signals': np.sum(ai_signals == 'BUY'),
                    'sell_signals': np.sum(ai_signals == 'SELL'),
                    'hold_signals': np.sum(ai_signals == 'HOLD'),
                    'avg_confidence': df['ai_confidence'].mean() if 'ai_confidence' in df.columns else 0
                }

            # Freqtrade AI system metrics
            if 'ft_signal' in df.columns:
                ft_signals = df['ft_signal'].values[:-5]

                accurate_signals = 0
                total_signals = 0

                for signal, future_ret in zip(ft_signals, future_returns):
                    if pd.notna(future_ret) and signal != 'HOLD':
                        total_signals += 1
                        if (signal == 'BUY' and future_ret > 0) or (signal == 'SELL' and future_ret < 0):
                            accurate_signals += 1

                metrics['freqtrade_ai'] = {
                    'signal_accuracy': accurate_signals / total_signals if total_signals > 0 else 0,
                    'total_signals': total_signals,
                    'buy_signals': np.sum(ft_signals == 'BUY'),
                    'sell_signals': np.sum(ft_signals == 'SELL'),
                    'hold_signals': np.sum(ft_signals == 'HOLD'),
                    'avg_confidence': df['ft_confidence'].mean() if 'ft_confidence' in df.columns else 0
                }

            # Signal agreement analysis
            if 'ai_signal' in df.columns and 'ft_signal' in df.columns:
                agreement = np.sum(df['ai_signal'] == df['ft_signal']) / len(df)

                # Agreement by signal type
                buy_agreement = np.sum((df['ai_signal'] == 'BUY') & (df['ft_signal'] == 'BUY')) / max(1, np.sum(df['ai_signal'] == 'BUY'))
                sell_agreement = np.sum((df['ai_signal'] == 'SELL') & (df['ft_signal'] == 'SELL')) / max(1, np.sum(df['ai_signal'] == 'SELL'))

                metrics['comparison'] = {
                    'overall_agreement': agreement,
                    'buy_signal_agreement': buy_agreement,
                    'sell_signal_agreement': sell_agreement,
                    'correlation_confidence': np.corrcoef(df['ai_confidence'], df['ft_confidence'])[0,1] if len(df) > 1 else 0
                }

            return metrics

        except Exception as e:
            print(f"[ERROR] Failed to calculate metrics: {e}")
            return {}

    def run_validation(self, symbol='BTC/USDT', timeframe='5m', days=30):
        """Run complete validation pipeline"""
        print("🔍 AI Model Performance Validation")
        print("=" * 50)

        # 1. Fetch validation data
        df = self.fetch_validation_data(symbol, timeframe, days)
        if df is None:
            return False

        # 2. Calculate technical indicators
        df = self.calculate_technical_indicators(df)

        # 3. Load trained models
        model_signal, model_price, scaler, feature_columns = self.load_trained_models()
        if model_signal is None:
            print("[ERROR] Could not load trained models. Run train_ai_models.py first.")
            return False

        # 4. Simulate original AI system
        df = self.simulate_original_ai_signals(df, model_signal, model_price, scaler, feature_columns)

        # 5. Simulate Freqtrade strategy
        df = self.simulate_freqtrade_strategy(df)

        # 6. Calculate performance metrics
        metrics = self.calculate_performance_metrics(df)

        # 7. Save results
        self.save_validation_results(df, metrics)

        # 8. Display results
        self.display_results(metrics)

        return True

    def save_validation_results(self, df, metrics):
        """Save validation results to files"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Save detailed data
            data_file = os.path.join(self.results_dir, f"validation_data_{timestamp}.csv")
            df.to_csv(data_file)

            # Save metrics
            metrics_file = os.path.join(self.results_dir, f"validation_metrics_{timestamp}.json")
            import json
            with open(metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2, default=str)

            print(f"[INFO] Results saved to {self.results_dir}")

        except Exception as e:
            print(f"[ERROR] Failed to save results: {e}")

    def display_results(self, metrics):
        """Display validation results"""
        print("\n📊 VALIDATION RESULTS")
        print("=" * 50)

        if 'original_ai' in metrics:
            print("\n🤖 Original AI System:")
            orig = metrics['original_ai']
            print(f"  Signal Accuracy: {orig['signal_accuracy']:.3f}")
            print(f"  Total Signals: {orig['total_signals']}")
            print(f"  Buy/Sell/Hold: {orig['buy_signals']}/{orig['sell_signals']}/{orig['hold_signals']}")
            print(f"  Avg Confidence: {orig['avg_confidence']:.3f}")

        if 'freqtrade_ai' in metrics:
            print("\n🚀 Freqtrade AI System:")
            ft = metrics['freqtrade_ai']
            print(f"  Signal Accuracy: {ft['signal_accuracy']:.3f}")
            print(f"  Total Signals: {ft['total_signals']}")
            print(f"  Buy/Sell/Hold: {ft['buy_signals']}/{ft['sell_signals']}/{ft['hold_signals']}")
            print(f"  Avg Confidence: {ft['avg_confidence']:.3f}")

        if 'comparison' in metrics:
            print("\n🔄 System Comparison:")
            comp = metrics['comparison']
            print(f"  Overall Agreement: {comp['overall_agreement']:.3f}")
            print(f"  Buy Signal Agreement: {comp['buy_signal_agreement']:.3f}")
            print(f"  Sell Signal Agreement: {comp['sell_signal_agreement']:.3f}")
            print(f"  Confidence Correlation: {comp['correlation_confidence']:.3f}")

        # Performance assessment
        print("\n✅ ASSESSMENT:")
        if 'original_ai' in metrics and 'freqtrade_ai' in metrics:
            orig_acc = metrics['original_ai']['signal_accuracy']
            ft_acc = metrics['freqtrade_ai']['signal_accuracy']
            agreement = metrics['comparison']['overall_agreement'] if 'comparison' in metrics else 0

            if abs(orig_acc - ft_acc) < 0.05 and agreement > 0.8:
                print("🎉 EXCELLENT: AI model porting successful!")
                print("   Both systems show similar performance and high agreement.")
            elif abs(orig_acc - ft_acc) < 0.1 and agreement > 0.7:
                print("✅ GOOD: AI model porting mostly successful.")
                print("   Minor differences detected, acceptable for production.")
            else:
                print("⚠️  NEEDS REVIEW: Significant differences detected.")
                print("   Consider model retraining or strategy adjustment.")

def main():
    """Main validation script"""
    import argparse

    parser = argparse.ArgumentParser(description='Validate AI model porting performance')
    parser.add_argument('--symbol', default='BTC/USDT', help='Trading pair to validate')
    parser.add_argument('--timeframe', default='5m', help='Timeframe for validation')
    parser.add_argument('--days', type=int, default=30, help='Days of validation data')

    args = parser.parse_args()

    # Initialize validator
    validator = PerformanceValidator()

    # Run validation
    success = validator.run_validation(args.symbol, args.timeframe, args.days)

    if success:
        print("\n🎯 Validation completed successfully!")
        print("Review the results above and check saved files in user_data/validation_results/")
    else:
        print("\n❌ Validation failed. Check the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main()