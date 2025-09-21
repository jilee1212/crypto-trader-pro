#!/usr/bin/env python3
"""
CoinGecko ML Components - Extended ML Signal Generator and Dashboard Components
This file contains the remaining components for the CoinGecko conversion
"""

import streamlit as st
import pandas as pd
import numpy as np
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any

# Import the base components
from ai_trading_signals_coingecko import (
    Config, CoinGeckoConnector, EnhancedTechnicalIndicators,
    EnhancedATRCalculator, EnhancedRiskManager
)

from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

# ==========================================
# 6. ENHANCED ML SIGNAL GENERATOR
# ==========================================

class EnhancedMLSignalGenerator:
    """Enhanced ML Signal Generator optimized for CoinGecko data"""

    def __init__(self):
        self.is_trained = False
        self.model_signal = None
        self.model_price = None
        self.scaler = StandardScaler()
        self.feature_columns = []
        self.training_history = []
        self.feature_importance = {}

        # Enhanced model parameters
        self.signal_confidence_threshold = 0.6
        self.min_training_samples = 100

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare enhanced features for ML model"""
        if df is None or df.empty:
            return df

        features_df = df.copy()

        try:
            # Price-based features
            features_df['price_change_1'] = features_df['close'].pct_change(1)
            features_df['price_change_3'] = features_df['close'].pct_change(3)
            features_df['price_change_7'] = features_df['close'].pct_change(7)

            # Volatility features
            features_df['volatility_5'] = features_df['close'].rolling(5).std() / features_df['close'].rolling(5).mean()
            features_df['volatility_20'] = features_df['close'].rolling(20).std() / features_df['close'].rolling(20).mean()

            # Volume features (if available)
            if 'volume' in features_df.columns:
                features_df['volume_change'] = features_df['volume'].pct_change(1)
                features_df['volume_ratio'] = features_df['volume'] / features_df['volume'].rolling(20).mean()

            # Technical indicator ratios and differences
            if 'rsi' in features_df.columns:
                features_df['rsi_oversold'] = (features_df['rsi'] < 30).astype(int)
                features_df['rsi_overbought'] = (features_df['rsi'] > 70).astype(int)

            if 'macd' in features_df.columns and 'macd_signal' in features_df.columns:
                features_df['macd_crossover'] = (features_df['macd'] > features_df['macd_signal']).astype(int)

            if 'bb_upper' in features_df.columns and 'bb_lower' in features_df.columns:
                features_df['bb_position'] = (features_df['close'] - features_df['bb_lower']) / (features_df['bb_upper'] - features_df['bb_lower'])

            # Market sentiment features
            if 'fear_greed_index' in features_df.columns:
                features_df['fear_greed_normalized'] = features_df['fear_greed_index'] / 100

            # Trend features
            if 'sma_20' in features_df.columns and 'sma_50' in features_df.columns:
                features_df['trend_short_long'] = (features_df['sma_20'] > features_df['sma_50']).astype(int)

        except Exception as e:
            print(f"Feature preparation error: {e}")

        return features_df

    def create_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create enhanced labels for signal prediction"""
        df_copy = df.copy()

        try:
            # Price direction labels (for signal classification)
            future_return = df_copy['close'].shift(-Config.ML_PREDICTION_HORIZON).pct_change()
            df_copy['future_return'] = future_return

            # Create signal labels based on future returns and volatility
            conditions = [
                future_return > 0.02,   # Strong Buy: >2% return
                future_return > 0.005,  # Buy: >0.5% return
                future_return < -0.02,  # Strong Sell: <-2% return
                future_return < -0.005  # Sell: <-0.5% return
            ]

            choices = ['STRONG_BUY', 'BUY', 'STRONG_SELL', 'SELL']
            df_copy['signal_label'] = np.select(conditions, choices, default='HOLD')

            # Simplified 3-class labels
            df_copy['simple_signal'] = np.where(
                future_return > 0.01, 'BUY',
                np.where(future_return < -0.01, 'SELL', 'HOLD')
            )

            # Risk-adjusted labels considering volatility
            if 'atr' in df_copy.columns:
                atr_pct = df_copy['atr'] / df_copy['close']
                risk_adjusted_threshold = atr_pct * 0.5  # Half of ATR as threshold

                df_copy['risk_adjusted_signal'] = np.where(
                    future_return > risk_adjusted_threshold, 'BUY',
                    np.where(future_return < -risk_adjusted_threshold, 'SELL', 'HOLD')
                )

        except Exception as e:
            print(f"Label creation error: {e}")

        return df_copy

    def train_model(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Train enhanced ML models"""
        try:
            if df is None or len(df) < self.min_training_samples:
                return {
                    'success': False,
                    'error': f'Insufficient data. Need at least {self.min_training_samples} samples'
                }

            # Prepare features and labels
            enhanced_df = self.prepare_features(df)
            labeled_df = self.create_labels(enhanced_df)

            # Select feature columns (excluding target variables and non-numeric)
            exclude_columns = ['signal_label', 'simple_signal', 'risk_adjusted_signal', 'future_return']
            feature_columns = [col for col in labeled_df.columns
                             if col not in exclude_columns
                             and labeled_df[col].dtype in ['float64', 'int64', 'float32', 'int32']]

            self.feature_columns = feature_columns

            # Prepare training data
            X = labeled_df[feature_columns].copy()
            y_signal = labeled_df['simple_signal'].copy()
            y_price = labeled_df['future_return'].copy()

            # Remove rows with NaN values
            valid_mask = ~(X.isna().any(axis=1) | y_signal.isna() | y_price.isna())
            X = X[valid_mask]
            y_signal = y_signal[valid_mask]
            y_price = y_price[valid_mask]

            if len(X) < self.min_training_samples:
                return {
                    'success': False,
                    'error': f'Insufficient valid data after cleaning: {len(X)} samples'
                }

            # Split data
            X_train, X_test, y_signal_train, y_signal_test, y_price_train, y_price_test = train_test_split(
                X, y_signal, y_price, test_size=1-Config.TRAIN_TEST_SPLIT, random_state=42
            )

            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            # Train signal classification model
            self.model_signal = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                class_weight='balanced'
            )

            self.model_signal.fit(X_train_scaled, y_signal_train)

            # Train price prediction model
            self.model_price = GradientBoostingRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42
            )

            self.model_price.fit(X_train_scaled, y_price_train)

            # Evaluate models
            signal_accuracy = self.model_signal.score(X_test_scaled, y_signal_test)
            price_r2 = self.model_price.score(X_test_scaled, y_price_test)

            # Feature importance
            self.feature_importance = dict(zip(
                feature_columns,
                self.model_signal.feature_importances_
            ))

            # Update training history
            training_result = {
                'timestamp': datetime.now().isoformat(),
                'samples': len(X),
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'accuracy': signal_accuracy,
                'price_r2': price_r2,
                'features': len(feature_columns)
            }

            self.training_history.append(training_result)
            self.is_trained = True

            return {
                'success': True,
                'accuracy': signal_accuracy,
                'price_r2': price_r2,
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'features_used': len(feature_columns),
                'feature_importance': self.feature_importance
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Training failed: {str(e)}'
            }

    def predict_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate enhanced trading signals"""
        try:
            if not self.is_trained:
                return self._generate_technical_signal(df)

            # Prepare features
            enhanced_df = self.prepare_features(df)

            if enhanced_df is None or enhanced_df.empty:
                return {'success': False, 'error': 'No data for prediction'}

            # Get latest features
            latest_features = enhanced_df[self.feature_columns].iloc[-1:].copy()

            # Check for missing values
            if latest_features.isna().any().any():
                return self._generate_technical_signal(df)

            # Scale features
            features_scaled = self.scaler.transform(latest_features)

            # Predict signal
            signal_proba = self.model_signal.predict_proba(features_scaled)[0]
            signal_classes = self.model_signal.classes_
            signal_confidence = max(signal_proba)
            predicted_signal = signal_classes[np.argmax(signal_proba)]

            # Predict price movement
            predicted_return = self.model_price.predict(features_scaled)[0]

            # Assess risk level
            risk_level = self._assess_signal_risk(enhanced_df, signal_confidence, predicted_return)

            # Adjust signal based on confidence threshold
            if signal_confidence < self.signal_confidence_threshold:
                predicted_signal = 'HOLD'

            # Get technical analysis confirmation
            technical_analysis = self._get_technical_analysis(enhanced_df)

            return {
                'success': True,
                'signal': predicted_signal,
                'confidence': signal_confidence,
                'predicted_return': predicted_return,
                'risk_level': risk_level,
                'technical_analysis': technical_analysis,
                'timestamp': datetime.now().isoformat(),
                'model_type': 'ML_ENHANCED'
            }

        except Exception as e:
            return self._generate_technical_signal(df)

    def _generate_technical_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Fallback technical analysis signal generation"""
        try:
            if df is None or df.empty:
                return {'success': False, 'error': 'No data available'}

            latest = df.iloc[-1]
            signal_score = 0
            total_indicators = 0

            # RSI analysis
            if 'rsi' in latest.index and not pd.isna(latest['rsi']):
                if latest['rsi'] < 30:
                    signal_score += 2  # Strong buy
                elif latest['rsi'] < 50:
                    signal_score += 1  # Mild buy
                elif latest['rsi'] > 70:
                    signal_score -= 2  # Strong sell
                elif latest['rsi'] > 50:
                    signal_score -= 1  # Mild sell
                total_indicators += 1

            # MACD analysis
            if 'macd' in latest.index and 'macd_signal' in latest.index:
                if not pd.isna(latest['macd']) and not pd.isna(latest['macd_signal']):
                    if latest['macd'] > latest['macd_signal']:
                        signal_score += 1
                    else:
                        signal_score -= 1
                    total_indicators += 1

            # Bollinger Bands analysis
            if all(col in latest.index for col in ['bb_upper', 'bb_lower']):
                if not pd.isna(latest['bb_upper']) and not pd.isna(latest['bb_lower']):
                    if latest['close'] < latest['bb_lower']:
                        signal_score += 1  # Oversold
                    elif latest['close'] > latest['bb_upper']:
                        signal_score -= 1  # Overbought
                    total_indicators += 1

            # Determine signal
            if total_indicators == 0:
                signal = 'HOLD'
                confidence = 0.5
            else:
                normalized_score = signal_score / total_indicators
                if normalized_score > 0.5:
                    signal = 'BUY'
                    confidence = min(0.8, 0.5 + normalized_score)
                elif normalized_score < -0.5:
                    signal = 'SELL'
                    confidence = min(0.8, 0.5 + abs(normalized_score))
                else:
                    signal = 'HOLD'
                    confidence = 0.6

            return {
                'success': True,
                'signal': signal,
                'confidence': confidence,
                'predicted_return': 0.0,
                'risk_level': 'medium',
                'technical_analysis': {'score': signal_score, 'indicators': total_indicators},
                'timestamp': datetime.now().isoformat(),
                'model_type': 'TECHNICAL_FALLBACK'
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Technical signal generation failed: {str(e)}'
            }

    def _assess_signal_risk(self, df: pd.DataFrame, confidence: float, predicted_return: float) -> str:
        """Assess risk level of the trading signal"""
        try:
            risk_factors = 0

            # Low confidence increases risk
            if confidence < 0.7:
                risk_factors += 1

            # High volatility increases risk
            if 'volatility_20' in df.columns:
                latest_vol = df['volatility_20'].iloc[-1]
                if not pd.isna(latest_vol) and latest_vol > 0.05:  # 5% volatility
                    risk_factors += 1

            # Extreme predicted returns increase risk
            if abs(predicted_return) > 0.1:  # 10% predicted return
                risk_factors += 1

            # Market sentiment risk
            if 'fear_greed_index' in df.columns:
                fear_greed = df['fear_greed_index'].iloc[-1]
                if not pd.isna(fear_greed) and (fear_greed < 25 or fear_greed > 75):
                    risk_factors += 1

            # Determine risk level
            if risk_factors >= 3:
                return 'high'
            elif risk_factors >= 1:
                return 'medium'
            else:
                return 'low'

        except Exception:
            return 'medium'

    def _get_technical_analysis(self, df: pd.DataFrame) -> Dict[str, str]:
        """Get detailed technical analysis"""
        analysis = {}

        try:
            latest = df.iloc[-1]

            # RSI analysis
            if 'rsi' in latest.index and not pd.isna(latest['rsi']):
                rsi = latest['rsi']
                if rsi < 30:
                    analysis['RSI'] = f'Oversold ({rsi:.1f})'
                elif rsi > 70:
                    analysis['RSI'] = f'Overbought ({rsi:.1f})'
                else:
                    analysis['RSI'] = f'Neutral ({rsi:.1f})'

            # MACD analysis
            if 'macd' in latest.index and 'macd_signal' in latest.index:
                if not pd.isna(latest['macd']) and not pd.isna(latest['macd_signal']):
                    if latest['macd'] > latest['macd_signal']:
                        analysis['MACD'] = 'Bullish'
                    else:
                        analysis['MACD'] = 'Bearish'

            # Trend analysis
            if 'sma_20' in latest.index and 'sma_50' in latest.index:
                if not pd.isna(latest['sma_20']) and not pd.isna(latest['sma_50']):
                    if latest['sma_20'] > latest['sma_50']:
                        analysis['Trend'] = 'Uptrend'
                    else:
                        analysis['Trend'] = 'Downtrend'

        except Exception as e:
            analysis['Error'] = str(e)

        return analysis

# ==========================================
# 7. ENHANCED PAPER TRADING SIMULATOR
# ==========================================

class EnhancedPaperTradingSimulator:
    """Enhanced paper trading with multiple cryptocurrencies"""

    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = {}  # {symbol: {shares, entry_price, entry_time, signal}}
        self.trade_history = []
        self.daily_pnl_history = []

        # Enhanced tracking
        self.total_fees_paid = 0
        self.win_rate = 0
        self.max_drawdown = 0
        self.sharpe_ratio = 0

    def execute_trade(self, symbol: str, action: str, price: float, quantity: float,
                     signal: str = None, confidence: float = 1.0) -> Dict[str, Any]:
        """Execute enhanced trade with multiple validation checks"""
        try:
            # Validate inputs
            if price <= 0 or quantity <= 0:
                return {'success': False, 'error': 'Invalid price or quantity'}

            trade_value = quantity * price
            fee_rate = 0.001  # 0.1% trading fee
            fee = trade_value * fee_rate

            if action.upper() == 'BUY':
                # Check if we have enough capital
                total_cost = trade_value + fee
                if total_cost > self.current_capital:
                    return {'success': False, 'error': 'Insufficient capital'}

                # Execute buy order
                if symbol in self.positions:
                    # Add to existing position (average down/up)
                    existing = self.positions[symbol]
                    total_shares = existing['shares'] + quantity
                    total_value = (existing['shares'] * existing['entry_price']) + trade_value
                    new_avg_price = total_value / total_shares

                    self.positions[symbol].update({
                        'shares': total_shares,
                        'entry_price': new_avg_price,
                        'entry_time': datetime.now(),
                        'signal': signal or 'BUY'
                    })
                else:
                    # New position
                    self.positions[symbol] = {
                        'shares': quantity,
                        'entry_price': price,
                        'entry_time': datetime.now(),
                        'signal': signal or 'BUY'
                    }

                self.current_capital -= total_cost
                self.total_fees_paid += fee

                trade_record = {
                    'timestamp': datetime.now(),
                    'symbol': symbol,
                    'action': 'BUY',
                    'quantity': quantity,
                    'price': price,
                    'value': trade_value,
                    'fee': fee,
                    'signal': signal,
                    'confidence': confidence,
                    'capital_after': self.current_capital
                }

            elif action.upper() == 'SELL':
                # Check if we have the position
                if symbol not in self.positions:
                    return {'success': False, 'error': 'No position to sell'}

                position = self.positions[symbol]
                if quantity > position['shares']:
                    return {'success': False, 'error': 'Insufficient shares'}

                # Calculate P&L
                entry_price = position['entry_price']
                pnl = (price - entry_price) * quantity
                pnl_pct = ((price - entry_price) / entry_price) * 100

                # Execute sell order
                self.current_capital += trade_value - fee
                self.total_fees_paid += fee

                # Update position
                remaining_shares = position['shares'] - quantity
                if remaining_shares > 0:
                    self.positions[symbol]['shares'] = remaining_shares
                else:
                    del self.positions[symbol]

                trade_record = {
                    'timestamp': datetime.now(),
                    'symbol': symbol,
                    'action': 'SELL',
                    'quantity': quantity,
                    'price': price,
                    'value': trade_value,
                    'fee': fee,
                    'signal': signal,
                    'confidence': confidence,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'entry_price': entry_price,
                    'capital_after': self.current_capital
                }

            else:
                return {'success': False, 'error': 'Invalid action'}

            # Add to trade history
            self.trade_history.append(trade_record)

            # Generate unique trade ID
            trade_id = f"{symbol}_{int(time.time())}"

            return {
                'success': True,
                'trade_id': trade_id,
                'action': action.upper(),
                'symbol': symbol,
                'quantity': quantity,
                'price': price,
                'fee': fee,
                'capital_remaining': self.current_capital
            }

        except Exception as e:
            return {'success': False, 'error': f'Trade execution failed: {str(e)}'}

    def get_portfolio_status(self) -> Dict[str, Any]:
        """Get comprehensive portfolio status"""
        try:
            total_position_value = 0
            positions_detail = {}

            # Calculate position values (using last known prices)
            for symbol, position in self.positions.items():
                # For demo, assume current price = entry price (in real scenario, fetch current price)
                current_value = position['shares'] * position['entry_price']
                total_position_value += current_value

                positions_detail[symbol] = {
                    'shares': position['shares'],
                    'entry_price': position['entry_price'],
                    'current_value': current_value,
                    'entry_time': position['entry_time'],
                    'signal': position['signal']
                }

            total_value = self.current_capital + total_position_value
            total_return = ((total_value - self.initial_capital) / self.initial_capital) * 100

            # Calculate performance metrics
            win_trades = [t for t in self.trade_history if t.get('pnl', 0) > 0]
            total_trades = len([t for t in self.trade_history if 'pnl' in t])
            win_rate = (len(win_trades) / total_trades * 100) if total_trades > 0 else 0

            return {
                'total_value': total_value,
                'available_cash': self.current_capital,
                'position_value': total_position_value,
                'total_return': total_return,
                'total_return_abs': total_value - self.initial_capital,
                'positions': positions_detail,
                'total_trades': total_trades,
                'win_rate': win_rate,
                'total_fees': self.total_fees_paid
            }

        except Exception as e:
            return {
                'total_value': self.initial_capital,
                'available_cash': self.current_capital,
                'position_value': 0,
                'total_return': 0,
                'positions': {},
                'error': str(e)
            }

# ==========================================
# 8. DATABASE MANAGER (Enhanced)
# ==========================================

class EnhancedDatabaseManager:
    """Enhanced database manager for CoinGecko data"""

    def __init__(self, db_file: str = Config.DB_FILE):
        self.db_file = db_file
        self.init_database()

    def init_database(self):
        """Initialize enhanced database schema"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()

                # Enhanced price data table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS price_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        open REAL,
                        high REAL,
                        low REAL,
                        close REAL NOT NULL,
                        volume REAL,
                        market_cap REAL,
                        fear_greed_index INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(symbol, timestamp)
                    )
                ''')

                # Enhanced trading signals table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trading_signals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        timeframe TEXT NOT NULL,
                        signal TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        predicted_return REAL,
                        risk_level TEXT,
                        model_type TEXT,
                        current_price REAL,
                        technical_analysis TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Paper trades table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS paper_trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        action TEXT NOT NULL,
                        quantity REAL NOT NULL,
                        price REAL NOT NULL,
                        value REAL NOT NULL,
                        fee REAL NOT NULL,
                        signal TEXT,
                        confidence REAL,
                        pnl REAL,
                        pnl_pct REAL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Market data cache table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS market_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        cache_key TEXT UNIQUE NOT NULL,
                        data TEXT NOT NULL,
                        expires_at DATETIME NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                conn.commit()

        except Exception as e:
            print(f"Database initialization error: {e}")

    def save_price_data(self, symbol: str, df: pd.DataFrame) -> bool:
        """Save enhanced price data"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                # Prepare data for insertion
                df_copy = df.copy()
                df_copy['symbol'] = symbol
                df_copy.reset_index(inplace=True)

                # Insert data
                df_copy.to_sql('price_data', conn, if_exists='append', index=False,
                             method='ignore')  # Ignore duplicates

                return True

        except Exception as e:
            print(f"Error saving price data: {e}")
            return False

    def save_trading_signal(self, signal_data: Dict) -> bool:
        """Save enhanced trading signal"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO trading_signals
                    (symbol, timeframe, signal, confidence, predicted_return, risk_level,
                     model_type, current_price, technical_analysis)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    signal_data.get('symbol', ''),
                    signal_data.get('timeframe', ''),
                    signal_data.get('signal', ''),
                    signal_data.get('confidence', 0),
                    signal_data.get('predicted_return', 0),
                    signal_data.get('risk_level', 'medium'),
                    signal_data.get('model_type', 'unknown'),
                    signal_data.get('current_price', 0),
                    json.dumps(signal_data.get('technical_analysis', {}))
                ))

                conn.commit()
                return True

        except Exception as e:
            print(f"Error saving trading signal: {e}")
            return False

if __name__ == "__main__":
    print("CoinGecko ML Components loaded successfully!")
    print("Enhanced features:")
    print("- ML Signal Generator with improved confidence scoring")
    print("- Multi-cryptocurrency paper trading")
    print("- Enhanced database with market sentiment")
    print("- Advanced technical analysis integration")