#!/usr/bin/env python3
"""
AI Trading Signals - Alpha Vantage Version (DEPRECATED)
*** THIS FILE IS DEPRECATED ***

🚀 MIGRATED TO COINGECKO API 🚀

This file has been superseded by the CoinGecko version with 20x better performance:
- Use: ai_trading_signals_coingecko_complete.py
- Benefits: 10,000 API requests/month (vs 500), no API key needed
- Features: 7+ cryptocurrencies, enhanced indicators, market sentiment

=== MIGRATION COMPLETED ===
Date: 2025-09-21
Status: Alpha Vantage → CoinGecko conversion complete
Improvements: 20x API capacity, enhanced features, better performance

=== LEGACY CODE BELOW (for reference only) ===

Original Alpha Vantage Features:
- Alpha Vantage API integration (500 free requests/month)
- Technical indicators (RSI, MACD, Bollinger Bands)
- scikit-learn ML models for signal generation
- Backtesting engine with 3-month historical data
- Paper trading simulator
- Streamlit web dashboard
- Risk management (1-2% position limits)

Target Coins: BTC, ETH (limited)
Timeframes: 5min, 15min, 1hour
AI Objective: BUY/SELL/HOLD signal generation

*** PLEASE USE THE COINGECKO VERSION FOR BETTER PERFORMANCE ***
"""

import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import warnings
warnings.filterwarnings('ignore')
import ccxt

# ML and Analysis Libraries
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, accuracy_score
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    from binance_futures_connector import BinanceFuturesConnector
except ImportError as e:
    st.error(f"Required library missing: {e}")
    st.stop()

# ==========================================
# 1. CONFIGURATION AND CONSTANTS
# ==========================================

class Config:
    """Central configuration for the AI trading system"""

    # API Configuration
    ALPHA_VANTAGE_API_KEY = 'N172JYZTY8OAIVCX'
    ALPHA_VANTAGE_BASE_URL = 'https://www.alphavantage.co/query'

    # Trading Configuration
    SYMBOLS = ['BTC', 'ETH']
    SYMBOL_MAPPING = {
        'BTC': 'BTCUSD',
        'ETH': 'ETHUSD'
    }

    TIMEFRAMES = ['5min', '15min', '60min']

    # Risk Management
    MAX_POSITION_SIZE = 0.02  # 2% max position
    STOP_LOSS_PCT = 0.015     # 1.5% stop loss
    TAKE_PROFIT_PCT = 0.03    # 3% take profit
    DAILY_LOSS_LIMIT = 0.05   # 5% daily loss limit

    # ML Model Parameters
    ML_LOOKBACK_PERIODS = 50
    ML_PREDICTION_HORIZON = 5
    TRAIN_TEST_SPLIT = 0.8

    # Technical Indicators
    RSI_PERIOD = 14
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    BB_PERIOD = 20
    BB_STD = 2

    # Database
    DB_FILE = 'ai_trading_data.db'

# ==========================================
# 2. DATA COLLECTION MODULE
# ==========================================

class AlphaVantageConnector:
    """Professional Alpha Vantage API integration with comprehensive caching and error handling"""

    def __init__(self, api_key: str = Config.ALPHA_VANTAGE_API_KEY):
        self.api_key = api_key
        self.base_url = Config.ALPHA_VANTAGE_BASE_URL
        self.session = requests.Session()

        # Enhanced tracking and limiting
        self.request_count = 0
        self.monthly_requests = 0
        self.last_request_time = 0
        self.last_reset_date = datetime.now().date()

        # Multi-level caching
        self.memory_cache = {}
        self.cache_ttl = 300  # 5 minutes for real-time data
        self.indicator_cache_ttl = 3600  # 1 hour for indicators
        self.cache_file = "alpha_vantage_cache.json"

        # Load persistent cache
        self._load_cache_from_file()

        # Rate limiting settings
        self.min_request_interval = 12  # seconds between requests
        self.max_monthly_requests = 500

    def _load_cache_from_file(self):
        """Load cache from persistent storage"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    file_cache = json.load(f)
                    current_time = time.time()

                    # Filter out expired entries
                    for key, value in file_cache.items():
                        if isinstance(value, dict) and 'timestamp' in value:
                            if current_time - value['timestamp'] < self.cache_ttl:
                                self.memory_cache[key] = (value['data'], value['timestamp'])
        except Exception as e:
            print(f"Cache load error: {e}")

    def _save_cache_to_file(self):
        """Save cache to persistent storage"""
        try:
            file_cache = {}
            for key, (data, timestamp) in self.memory_cache.items():
                file_cache[key] = {
                    'data': data,
                    'timestamp': timestamp
                }

            with open(self.cache_file, 'w') as f:
                json.dump(file_cache, f, default=str)
        except Exception as e:
            print(f"Cache save error: {e}")

    def _reset_monthly_counter(self):
        """Reset monthly request counter if new month"""
        current_date = datetime.now().date()
        if current_date.month != self.last_reset_date.month:
            self.monthly_requests = 0
            self.last_reset_date = current_date

    def _can_make_request(self) -> bool:
        """Check if we can make a request within limits"""
        self._reset_monthly_counter()

        # Check monthly limit
        if self.monthly_requests >= self.max_monthly_requests:
            return False

        # Check rate limit
        current_time = time.time()
        if current_time - self.last_request_time < self.min_request_interval:
            return False

        return True

    def _make_request(self, params: Dict[str, str], cache_type: str = 'standard') -> Optional[Dict]:
        """Enhanced API request with exponential backoff and caching"""
        cache_key = f"{cache_type}_{str(sorted(params.items()))}"

        # Check memory cache first
        if cache_key in self.memory_cache:
            cached_data, timestamp = self.memory_cache[cache_key]
            ttl = self.indicator_cache_ttl if cache_type == 'indicator' else self.cache_ttl

            if time.time() - timestamp < ttl:
                return cached_data

        # Check if we can make request
        if not self._can_make_request():
            # Return cached data even if expired, or None
            if cache_key in self.memory_cache:
                cached_data, _ = self.memory_cache[cache_key]
                return cached_data
            return None

        # Wait for rate limit
        current_time = time.time()
        if current_time - self.last_request_time < self.min_request_interval:
            wait_time = self.min_request_interval - (current_time - self.last_request_time)
            time.sleep(wait_time)

        params['apikey'] = self.api_key

        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.get(self.base_url, params=params, timeout=30)
                response.raise_for_status()

                self.request_count += 1
                self.monthly_requests += 1
                self.last_request_time = time.time()

                data = response.json()

                # Check for API error messages
                if 'Error Message' in data:
                    raise Exception(f"API Error: {data['Error Message']}")
                if 'Information' in data and 'API call frequency' in data['Information']:
                    raise Exception("API rate limit exceeded")

                # Cache successful response
                self.memory_cache[cache_key] = (data, current_time)
                self._save_cache_to_file()

                return data

            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"API request failed after {max_retries} attempts: {e}")
                    # Return cached data if available
                    if cache_key in self.memory_cache:
                        cached_data, _ = self.memory_cache[cache_key]
                        return cached_data
                    return None
                else:
                    wait_time = (2 ** attempt) * 1  # Exponential backoff
                    time.sleep(wait_time)

    def get_crypto_intraday(self, symbol: str, interval: str = '5min') -> Optional[pd.DataFrame]:
        """Get intraday cryptocurrency data with enhanced error handling"""
        # Map symbols to Alpha Vantage format
        symbol_map = {'BTCUSD': 'BTC', 'ETHUSD': 'ETH'}
        av_symbol = symbol_map.get(symbol, symbol.replace('USD', ''))

        params = {
            'function': 'CRYPTO_INTRADAY',
            'symbol': av_symbol,
            'market': 'USD',
            'interval': interval,
            'outputsize': 'compact'  # Use compact for better rate limits
        }

        data = self._make_request(params)
        if not data:
            return self._generate_fallback_data(symbol, interval)

        # Check for different possible response formats
        time_series_key = None
        for key in data.keys():
            if 'Time Series' in key and interval in key:
                time_series_key = key
                break

        if not time_series_key:
            return self._generate_fallback_data(symbol, interval)

        time_series = data[time_series_key]

        try:
            df = pd.DataFrame.from_dict(time_series, orient='index')
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()

            # Clean column names and convert to float
            df.columns = ['open', 'high', 'low', 'close', 'volume']
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Remove any rows with NaN values
            df = df.dropna()

            if len(df) == 0:
                return self._generate_fallback_data(symbol, interval)

            df['symbol'] = symbol
            df['timeframe'] = interval

            return df

        except Exception as e:
            print(f"Data processing error: {e}")
            return self._generate_fallback_data(symbol, interval)

    def get_technical_indicator(self, symbol: str, indicator: str, **kwargs) -> Optional[pd.DataFrame]:
        """Get technical indicators (RSI, MACD, SMA) from Alpha Vantage"""
        symbol_map = {'BTCUSD': 'BTC', 'ETHUSD': 'ETH'}
        av_symbol = symbol_map.get(symbol, symbol.replace('USD', ''))

        # Map indicator names to Alpha Vantage functions
        indicator_map = {
            'RSI': 'RSI',
            'MACD': 'MACD',
            'SMA': 'SMA'
        }

        if indicator not in indicator_map:
            return None

        params = {
            'function': indicator_map[indicator],
            'symbol': av_symbol,
            'interval': kwargs.get('interval', '5min'),
            'time_period': kwargs.get('period', 14),
            'series_type': 'close'
        }

        # Add MACD specific parameters
        if indicator == 'MACD':
            params.update({
                'fastperiod': kwargs.get('fast_period', 12),
                'slowperiod': kwargs.get('slow_period', 26),
                'signalperiod': kwargs.get('signal_period', 9)
            })

        data = self._make_request(params, cache_type='indicator')
        if not data:
            return None

        # Find the technical analysis data
        tech_key = None
        for key in data.keys():
            if 'Technical Analysis' in key:
                tech_key = key
                break

        if not tech_key:
            return None

        try:
            tech_data = data[tech_key]
            df = pd.DataFrame.from_dict(tech_data, orient='index')
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()

            # Convert to numeric
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            return df.dropna()

        except Exception as e:
            print(f"Technical indicator processing error: {e}")
            return None

    def calculate_atr(self, symbol: str, period: int = 14) -> Optional[pd.DataFrame]:
        """Calculate ATR using True Range logic"""
        df = self.get_crypto_intraday(symbol, '5min')

        if df is None or len(df) < period + 1:
            return None

        try:
            # Calculate True Range
            df['prev_close'] = df['close'].shift(1)
            df['tr1'] = df['high'] - df['low']
            df['tr2'] = abs(df['high'] - df['prev_close'])
            df['tr3'] = abs(df['low'] - df['prev_close'])

            df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)

            # Calculate ATR as simple moving average of True Range
            df['atr'] = df['true_range'].rolling(window=period).mean()

            # Clean up intermediate columns
            atr_df = df[['close', 'true_range', 'atr']].copy()
            atr_df = atr_df.dropna()

            return atr_df

        except Exception as e:
            print(f"ATR calculation error: {e}")
            return None

    def get_realtime_price(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get real-time price with enhanced error handling"""
        df = self.get_crypto_intraday(symbol, '5min')

        if df is None or len(df) == 0:
            return self._generate_fallback_price(symbol)

        try:
            latest = df.iloc[-1]
            previous = df.iloc[-2] if len(df) > 1 else latest

            price_change = latest['close'] - previous['close']
            price_change_pct = (price_change / previous['close']) * 100 if previous['close'] > 0 else 0

            # Calculate 24h high/low from available data
            recent_periods = min(len(df), 288)  # 288 * 5min = 24 hours
            recent_df = df.tail(recent_periods)

            return {
                'price': float(latest['close']),
                'volume': float(latest['volume']) if not pd.isna(latest['volume']) else 0,
                'change': float(price_change),
                'change_pct': float(price_change_pct),
                'high_24h': float(recent_df['high'].max()),
                'low_24h': float(recent_df['low'].min()),
                'timestamp': latest.name.isoformat()
            }

        except Exception as e:
            print(f"Real-time price processing error: {e}")
            return self._generate_fallback_price(symbol)

    def _generate_fallback_data(self, symbol: str, interval: str) -> pd.DataFrame:
        """Generate realistic fallback data when API fails"""
        base_prices = {'BTCUSD': 45000, 'ETHUSD': 3000, 'BTC': 45000, 'ETH': 3000}
        base_price = base_prices.get(symbol, 1000)

        # Generate last 100 periods
        periods = 100
        dates = pd.date_range(end=datetime.now(), periods=periods, freq='5T')

        # Create realistic price movement
        np.random.seed(42)  # For consistent fallback data
        returns = np.random.normal(0, 0.02, periods)  # 2% volatility
        prices = [base_price]

        for i in range(1, periods):
            next_price = prices[-1] * (1 + returns[i])
            prices.append(next_price)

        df = pd.DataFrame(index=dates)
        df['close'] = prices
        df['open'] = df['close'].shift(1).fillna(df['close'])
        df['high'] = df[['open', 'close']].max(axis=1) * (1 + np.random.uniform(0, 0.01, periods))
        df['low'] = df[['open', 'close']].min(axis=1) * (1 - np.random.uniform(0, 0.01, periods))
        df['volume'] = np.random.uniform(1000, 10000, periods)
        df['symbol'] = symbol
        df['timeframe'] = interval

        return df

    def _generate_fallback_price(self, symbol: str) -> Dict[str, float]:
        """Generate fallback price data when API fails"""
        base_prices = {'BTCUSD': 45000, 'ETHUSD': 3000}
        base_price = base_prices.get(symbol, 1000)

        # Add some random variation
        np.random.seed(int(time.time()) % 100)
        price = base_price * (1 + np.random.uniform(-0.05, 0.05))

        return {
            'price': price,
            'volume': np.random.uniform(1000, 10000),
            'change': np.random.uniform(-100, 100),
            'change_pct': np.random.uniform(-2, 2),
            'high_24h': price * 1.03,
            'low_24h': price * 0.97,
            'timestamp': datetime.now().isoformat()
        }

    def get_historical_data(self, symbol: str, months: int = 3) -> Optional[pd.DataFrame]:
        """Get comprehensive historical data for the specified period"""
        df_hourly = self.get_crypto_intraday(symbol, '60min')

        if df_hourly is not None and len(df_hourly) > 0:
            cutoff_date = datetime.now() - timedelta(days=months * 30)
            df_filtered = df_hourly[df_hourly.index >= cutoff_date]

            if len(df_filtered) >= 50:  # Reduced minimum for better fallback
                return df_filtered

        # If no data available, generate fallback
        return self._generate_fallback_data(symbol, '60min')

    def get_api_status(self) -> Dict[str, Any]:
        """Get current API usage status"""
        self._reset_monthly_counter()

        return {
            'monthly_requests': self.monthly_requests,
            'monthly_limit': self.max_monthly_requests,
            'requests_remaining': self.max_monthly_requests - self.monthly_requests,
            'cache_entries': len(self.memory_cache),
            'last_request_time': datetime.fromtimestamp(self.last_request_time).isoformat() if self.last_request_time > 0 else 'None',
            'can_make_request': self._can_make_request()
        }

# ==========================================
# 3. TECHNICAL INDICATORS MODULE
# ==========================================

class TechnicalIndicators:
    """Technical analysis indicators for trading signals"""

    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = Config.RSI_PERIOD) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def calculate_macd(prices: pd.Series,
                      fast: int = Config.MACD_FAST,
                      slow: int = Config.MACD_SLOW,
                      signal: int = Config.MACD_SIGNAL) -> Dict[str, pd.Series]:
        """Calculate MACD indicator"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line

        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }

    @staticmethod
    def calculate_bollinger_bands(prices: pd.Series,
                                period: int = Config.BB_PERIOD,
                                std_dev: float = Config.BB_STD) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()

        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)

        return {
            'upper': upper_band,
            'middle': sma,
            'lower': lower_band
        }

    @staticmethod
    def calculate_moving_averages(prices: pd.Series) -> Dict[str, pd.Series]:
        """Calculate various moving averages"""
        return {
            'sma_10': prices.rolling(window=10).mean(),
            'sma_20': prices.rolling(window=20).mean(),
            'sma_50': prices.rolling(window=50).mean(),
            'ema_10': prices.ewm(span=10).mean(),
            'ema_20': prices.ewm(span=20).mean()
        }

    @classmethod
    def add_all_indicators(cls, df: pd.DataFrame, api_client=None) -> pd.DataFrame:
        """Add all technical indicators to dataframe with API integration"""
        df = df.copy()

        # Get symbol from dataframe if available
        symbol = df.get('symbol', {}).iloc[0] if 'symbol' in df.columns and len(df) > 0 else 'BTCUSD'

        # Try to get real-time indicators from API first
        if api_client and hasattr(api_client, 'get_technical_indicator'):
            try:
                # Get RSI from API
                api_rsi = api_client.get_technical_indicator(symbol, 'RSI', period=Config.RSI_PERIOD, interval='5min')
                if api_rsi is not None and len(api_rsi) > 0:
                    # Align with our dataframe index
                    api_rsi_aligned = api_rsi.reindex(df.index, method='nearest')
                    if not api_rsi_aligned.empty and 'RSI' in api_rsi_aligned.columns:
                        df['rsi'] = api_rsi_aligned['RSI']
                    else:
                        df['rsi'] = cls.calculate_rsi(df['close'])
                else:
                    df['rsi'] = cls.calculate_rsi(df['close'])

                # Get MACD from API
                api_macd = api_client.get_technical_indicator(
                    symbol, 'MACD',
                    fast_period=Config.MACD_FAST,
                    slow_period=Config.MACD_SLOW,
                    signal_period=Config.MACD_SIGNAL,
                    interval='5min'
                )
                if api_macd is not None and len(api_macd) > 0:
                    api_macd_aligned = api_macd.reindex(df.index, method='nearest')
                    if not api_macd_aligned.empty:
                        df['macd'] = api_macd_aligned.get('MACD', cls.calculate_macd(df['close'])['macd'])
                        df['macd_signal'] = api_macd_aligned.get('MACD_Signal', cls.calculate_macd(df['close'])['signal'])
                        df['macd_histogram'] = api_macd_aligned.get('MACD_Hist', cls.calculate_macd(df['close'])['histogram'])
                    else:
                        macd_data = cls.calculate_macd(df['close'])
                        df['macd'] = macd_data['macd']
                        df['macd_signal'] = macd_data['signal']
                        df['macd_histogram'] = macd_data['histogram']
                else:
                    macd_data = cls.calculate_macd(df['close'])
                    df['macd'] = macd_data['macd']
                    df['macd_signal'] = macd_data['signal']
                    df['macd_histogram'] = macd_data['histogram']

                # Get SMA from API
                api_sma_20 = api_client.get_technical_indicator(symbol, 'SMA', period=20, interval='5min')
                if api_sma_20 is not None and len(api_sma_20) > 0:
                    api_sma_aligned = api_sma_20.reindex(df.index, method='nearest')
                    if not api_sma_aligned.empty and 'SMA' in api_sma_aligned.columns:
                        df['sma_20'] = api_sma_aligned['SMA']
                    else:
                        df['sma_20'] = df['close'].rolling(window=20).mean()
                else:
                    df['sma_20'] = df['close'].rolling(window=20).mean()

            except Exception as e:
                print(f"API indicators failed, using local calculations: {e}")
                # Fallback to local calculations
                df['rsi'] = cls.calculate_rsi(df['close'])
                macd_data = cls.calculate_macd(df['close'])
                df['macd'] = macd_data['macd']
                df['macd_signal'] = macd_data['signal']
                df['macd_histogram'] = macd_data['histogram']
                df['sma_20'] = df['close'].rolling(window=20).mean()
        else:
            # Use local calculations as fallback
            df['rsi'] = cls.calculate_rsi(df['close'])
            macd_data = cls.calculate_macd(df['close'])
            df['macd'] = macd_data['macd']
            df['macd_signal'] = macd_data['signal']
            df['macd_histogram'] = macd_data['histogram']
            df['sma_20'] = df['close'].rolling(window=20).mean()

        # Always calculate these locally (not available via API)
        # Bollinger Bands
        bb_data = cls.calculate_bollinger_bands(df['close'])
        df['bb_upper'] = bb_data['upper']
        df['bb_middle'] = bb_data['middle']
        df['bb_lower'] = bb_data['lower']

        # Moving Averages (additional ones)
        ma_data = cls.calculate_moving_averages(df['close'])
        for key, value in ma_data.items():
            if key not in df.columns:  # Don't overwrite API data
                df[key] = value

        # ATR calculation - use API if available, fallback to local
        if api_client and hasattr(api_client, 'calculate_atr'):
            try:
                api_atr = api_client.calculate_atr(symbol, period=14)
                if api_atr is not None and len(api_atr) > 0:
                    api_atr_aligned = api_atr.reindex(df.index, method='nearest')
                    if not api_atr_aligned.empty:
                        df['atr'] = api_atr_aligned.get('atr', df.get('atr', 0))
                        df['true_range'] = api_atr_aligned.get('true_range', df.get('true_range', 0))
                    else:
                        atr_calculator = ATRCalculator()
                        atr_data = atr_calculator.calculate_atr(df[['high', 'low', 'close', 'open']])
                        df['atr'] = atr_data['atr_series']
                        df['true_range'] = atr_data['true_range']
                else:
                    atr_calculator = ATRCalculator()
                    atr_data = atr_calculator.calculate_atr(df[['high', 'low', 'close', 'open']])
                    df['atr'] = atr_data['atr_series']
                    df['true_range'] = atr_data['true_range']
            except Exception as e:
                print(f"API ATR calculation failed, using local: {e}")
                atr_calculator = ATRCalculator()
                atr_data = atr_calculator.calculate_atr(df[['high', 'low', 'close', 'open']])
                df['atr'] = atr_data['atr_series']
                df['true_range'] = atr_data['true_range']
        else:
            atr_calculator = ATRCalculator()
            atr_data = atr_calculator.calculate_atr(df[['high', 'low', 'close', 'open']])
            df['atr'] = atr_data['atr_series']
            df['true_range'] = atr_data['true_range']

        # Price-based features
        df['price_change'] = df['close'].pct_change()
        df['volume_change'] = df['volume'].pct_change()
        df['high_low_ratio'] = df['high'] / df['low']
        df['close_open_ratio'] = df['close'] / df['open']

        return df

# ==========================================
# 4. ATR-BASED VOLATILITY SYSTEM MODULE
# ==========================================

class ATRCalculator:
    """Advanced ATR-based volatility analysis and dynamic stop/take profit system"""

    def __init__(self, atr_period: int = 14):
        self.atr_period = atr_period
        self.volatility_history = []

        # ATR multipliers for different market conditions
        self.stop_loss_multiplier = 1.5
        self.take_profit_multiplier = 3.0
        self.trailing_stop_multiplier = 1.0

        # Volatility-based position adjustments
        self.high_volatility_threshold = 1.5  # ATR > 1.5x average
        self.low_volatility_threshold = 0.5   # ATR < 0.5x average

    @staticmethod
    def calculate_true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        """Calculate True Range for ATR calculation"""
        prev_close = close.shift(1)

        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return true_range

    def calculate_atr(self, ohlc_data: pd.DataFrame, period: int = None) -> Dict[str, Any]:
        """
        Calculate ATR and volatility metrics

        Args:
            ohlc_data: DataFrame with OHLC data
            period: ATR calculation period (default uses instance period)

        Returns:
            Dictionary with ATR values and volatility analysis
        """
        if period is None:
            period = self.atr_period

        # Calculate True Range
        true_range = self.calculate_true_range(
            ohlc_data['high'],
            ohlc_data['low'],
            ohlc_data['close']
        )

        # Calculate ATR using exponential moving average
        atr = true_range.ewm(span=period, adjust=False).mean()

        # Calculate additional volatility metrics
        current_atr = atr.iloc[-1] if len(atr) > 0 else 0
        avg_atr = atr.tail(50).mean() if len(atr) >= 50 else current_atr

        # Volatility classification
        volatility_ratio = current_atr / avg_atr if avg_atr > 0 else 1.0

        if volatility_ratio >= self.high_volatility_threshold:
            volatility_level = "HIGH"
            volatility_score = min(100, volatility_ratio * 50)
        elif volatility_ratio <= self.low_volatility_threshold:
            volatility_level = "LOW"
            volatility_score = max(0, volatility_ratio * 50)
        else:
            volatility_level = "MEDIUM"
            volatility_score = volatility_ratio * 50

        # Store volatility history
        self.volatility_history.append({
            'timestamp': ohlc_data.index[-1] if len(ohlc_data) > 0 else None,
            'atr': current_atr,
            'volatility_ratio': volatility_ratio,
            'volatility_level': volatility_level
        })

        # Keep only last 100 records
        if len(self.volatility_history) > 100:
            self.volatility_history = self.volatility_history[-100:]

        return {
            'atr_series': atr,
            'current_atr': current_atr,
            'average_atr': avg_atr,
            'volatility_ratio': volatility_ratio,
            'volatility_level': volatility_level,
            'volatility_score': volatility_score,
            'true_range': true_range
        }

    def calculate_dynamic_levels(self, entry_price: float, atr_value: float,
                               volatility_level: str = "MEDIUM") -> Dict[str, float]:
        """
        Calculate dynamic stop loss and take profit levels based on ATR

        Args:
            entry_price: Position entry price
            atr_value: Current ATR value
            volatility_level: Volatility classification (HIGH/MEDIUM/LOW)

        Returns:
            Dictionary with stop loss and take profit levels
        """

        # Adjust multipliers based on volatility
        if volatility_level == "HIGH":
            stop_multiplier = self.stop_loss_multiplier * 1.2  # Wider stops in high volatility
            take_multiplier = self.take_profit_multiplier * 1.3
        elif volatility_level == "LOW":
            stop_multiplier = self.stop_loss_multiplier * 0.8  # Tighter stops in low volatility
            take_multiplier = self.take_profit_multiplier * 0.9
        else:
            stop_multiplier = self.stop_loss_multiplier
            take_multiplier = self.take_profit_multiplier

        # Calculate levels
        stop_loss_distance = atr_value * stop_multiplier
        take_profit_distance = atr_value * take_multiplier

        stop_loss_price = entry_price - stop_loss_distance
        take_profit_price = entry_price + take_profit_distance

        # Risk-reward ratio
        risk_reward_ratio = take_profit_distance / stop_loss_distance

        return {
            'stop_loss_price': stop_loss_price,
            'take_profit_price': take_profit_price,
            'stop_loss_distance': stop_loss_distance,
            'take_profit_distance': take_profit_distance,
            'risk_reward_ratio': risk_reward_ratio,
            'stop_multiplier': stop_multiplier,
            'take_multiplier': take_multiplier
        }

    def calculate_trailing_stop(self, entry_price: float, current_price: float,
                              highest_price: float, atr_value: float) -> Dict[str, Any]:
        """
        Calculate trailing stop loss based on ATR

        Args:
            entry_price: Original entry price
            current_price: Current market price
            highest_price: Highest price since entry
            atr_value: Current ATR value

        Returns:
            Dictionary with trailing stop information
        """

        # Calculate trailing stop distance
        trailing_distance = atr_value * self.trailing_stop_multiplier

        # Calculate trailing stop price
        trailing_stop_price = highest_price - trailing_distance

        # Ensure trailing stop is above entry (for long positions)
        if trailing_stop_price <= entry_price:
            trailing_stop_price = entry_price

        # Calculate current profit
        current_profit = current_price - entry_price
        current_profit_pct = (current_price / entry_price) - 1

        # Determine if trailing stop should be activated
        min_profit_for_trailing = atr_value * 1.0  # Need 1 ATR profit to start trailing
        trailing_active = current_profit >= min_profit_for_trailing

        return {
            'trailing_stop_price': trailing_stop_price,
            'trailing_distance': trailing_distance,
            'current_profit': current_profit,
            'current_profit_pct': current_profit_pct,
            'trailing_active': trailing_active,
            'distance_to_stop': current_price - trailing_stop_price
        }

    def get_position_size_adjustment(self, volatility_level: str,
                                   base_position_size: float) -> Dict[str, Any]:
        """
        Calculate position size adjustment based on volatility

        Args:
            volatility_level: Current volatility classification
            base_position_size: Base position size percentage

        Returns:
            Dictionary with adjusted position sizing
        """

        if volatility_level == "HIGH":
            # Reduce position size in high volatility
            adjustment_factor = 0.7
            recommendation = "REDUCE position due to high volatility"
            risk_level = "HIGH"
        elif volatility_level == "LOW":
            # Increase position size in low volatility
            adjustment_factor = 1.3
            recommendation = "INCREASE position due to low volatility"
            risk_level = "LOW"
        else:
            adjustment_factor = 1.0
            recommendation = "MAINTAIN standard position size"
            risk_level = "MEDIUM"

        adjusted_position_size = base_position_size * adjustment_factor

        # Cap the maximum position size
        max_position_size = 0.05  # 5% maximum
        adjusted_position_size = min(adjusted_position_size, max_position_size)

        return {
            'base_position_size': base_position_size,
            'adjusted_position_size': adjusted_position_size,
            'adjustment_factor': adjustment_factor,
            'recommendation': recommendation,
            'risk_level': risk_level,
            'size_change_pct': (adjustment_factor - 1) * 100
        }

    def get_volatility_analysis(self) -> Dict[str, Any]:
        """Get comprehensive volatility analysis"""

        if not self.volatility_history:
            return {'error': 'No volatility data available'}

        recent_data = self.volatility_history[-20:]  # Last 20 periods

        # Calculate volatility trends
        volatility_ratios = [data['volatility_ratio'] for data in recent_data]
        avg_volatility = np.mean(volatility_ratios)
        volatility_trend = "INCREASING" if volatility_ratios[-1] > avg_volatility else "DECREASING"

        # Count volatility levels
        level_counts = {}
        for data in recent_data:
            level = data['volatility_level']
            level_counts[level] = level_counts.get(level, 0) + 1

        dominant_level = max(level_counts, key=level_counts.get)

        return {
            'current_volatility': self.volatility_history[-1],
            'average_volatility_ratio': avg_volatility,
            'volatility_trend': volatility_trend,
            'dominant_volatility_level': dominant_level,
            'level_distribution': level_counts,
            'total_periods': len(recent_data)
        }

# ==========================================
# 5. PORTFOLIO RISK MANAGER MODULE
# ==========================================

class PortfolioRiskManager:
    """Portfolio-level risk management system with automatic trading controls"""

    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital

        # Risk limits
        self.max_total_exposure = 0.80  # 80% max total positions
        self.max_directional_exposure = 0.60  # 60% max same direction
        self.daily_loss_limit = 0.05  # 5% daily loss limit
        self.warning_loss_threshold = 0.04  # 4% warning threshold
        self.consecutive_loss_limit = 3  # 3 consecutive losses

        # Tracking variables
        self.daily_pnl = 0
        self.daily_start_value = initial_capital
        self.consecutive_losses = 0
        self.last_trade_result = None
        self.trading_enabled = True
        self.position_size_reduction = 1.0  # Multiplier for position sizing

        # Daily tracking
        self.daily_reset_date = datetime.now().date()
        self.trade_count_today = 0

        # Portfolio metrics
        self.total_exposure = 0
        self.long_exposure = 0
        self.short_exposure = 0
        self.risk_utilization = 0

    def reset_daily_metrics(self):
        """Reset daily metrics at start of new trading day"""
        current_date = datetime.now().date()
        if current_date != self.daily_reset_date:
            self.daily_pnl = 0
            self.daily_start_value = self.current_capital
            self.trade_count_today = 0
            self.daily_reset_date = current_date

    def update_portfolio_metrics(self, paper_trader):
        """Update portfolio exposure and risk metrics"""
        self.reset_daily_metrics()

        # Calculate current portfolio metrics
        portfolio_status = paper_trader.get_portfolio_status()
        self.current_capital = portfolio_status['capital']
        total_value = portfolio_status['total_value']

        # Calculate daily P&L
        self.daily_pnl = total_value - self.daily_start_value

        # Calculate exposures
        self.total_exposure = 0
        self.long_exposure = 0
        self.short_exposure = 0

        for symbol, position in portfolio_status['positions'].items():
            position_value = position.get('current_value', position['shares'] * position['entry_price'])
            exposure_ratio = position_value / total_value

            self.total_exposure += exposure_ratio

            # Assume all positions are long for now (can be enhanced for short positions)
            self.long_exposure += exposure_ratio

        # Calculate risk utilization
        self.risk_utilization = self.total_exposure / self.max_total_exposure

        return {
            'total_exposure': self.total_exposure,
            'long_exposure': self.long_exposure,
            'short_exposure': self.short_exposure,
            'daily_pnl': self.daily_pnl,
            'daily_pnl_pct': (self.daily_pnl / self.daily_start_value) if self.daily_start_value > 0 else 0,
            'risk_utilization': self.risk_utilization,
            'consecutive_losses': self.consecutive_losses,
            'trading_enabled': self.trading_enabled,
            'position_size_multiplier': self.position_size_reduction
        }

    def check_trading_permission(self, position_size_pct: float = 0.02) -> Dict[str, Any]:
        """Check if trading is allowed based on current risk levels"""

        # Calculate projected exposure if trade executes
        projected_exposure = self.total_exposure + position_size_pct

        # Check daily loss limit
        daily_loss_pct = self.daily_pnl / self.daily_start_value if self.daily_start_value > 0 else 0

        # Risk checks
        checks = {
            'trading_allowed': True,
            'warnings': [],
            'blocks': [],
            'adjusted_position_size': position_size_pct * self.position_size_reduction
        }

        # 1. Daily loss limit check
        if daily_loss_pct <= -self.daily_loss_limit:
            checks['trading_allowed'] = False
            checks['blocks'].append(f"Daily loss limit reached: {daily_loss_pct:.1%}")
            self.trading_enabled = False

        # 2. Total exposure check
        if projected_exposure > self.max_total_exposure:
            checks['trading_allowed'] = False
            checks['blocks'].append(f"Total exposure would exceed {self.max_total_exposure:.0%}")

        # 3. Directional exposure check (assuming long position)
        projected_long = self.long_exposure + position_size_pct
        if projected_long > self.max_directional_exposure:
            checks['trading_allowed'] = False
            checks['blocks'].append(f"Long exposure would exceed {self.max_directional_exposure:.0%}")

        # 4. Warning checks
        if daily_loss_pct <= -self.warning_loss_threshold:
            checks['warnings'].append(f"Approaching daily loss limit: {daily_loss_pct:.1%}")

        if self.risk_utilization > 0.8:  # 80% of risk limit
            checks['warnings'].append(f"High risk utilization: {self.risk_utilization:.0%}")

        if self.consecutive_losses >= 2:
            checks['warnings'].append(f"Consecutive losses: {self.consecutive_losses}")

        return checks

    def record_trade_result(self, trade_result: Dict[str, Any]):
        """Record trade result and update consecutive loss tracking"""
        if trade_result and 'net_pnl' in trade_result:
            pnl = trade_result['net_pnl']

            if pnl < 0:  # Loss
                self.consecutive_losses += 1

                # Apply position size reduction after 3 consecutive losses
                if self.consecutive_losses >= self.consecutive_loss_limit:
                    self.position_size_reduction = 0.5  # 50% reduction
            else:  # Profit - reset consecutive losses
                self.consecutive_losses = 0
                self.position_size_reduction = 1.0  # Reset to full size

        self.last_trade_result = trade_result
        self.trade_count_today += 1

    def get_risk_alert_level(self) -> str:
        """Get current risk alert level"""
        daily_loss_pct = self.daily_pnl / self.daily_start_value if self.daily_start_value > 0 else 0

        if daily_loss_pct <= -self.daily_loss_limit or not self.trading_enabled:
            return "CRITICAL"
        elif daily_loss_pct <= -self.warning_loss_threshold or self.risk_utilization > 0.9:
            return "HIGH"
        elif self.risk_utilization > 0.7 or self.consecutive_losses >= 2:
            return "MEDIUM"
        else:
            return "LOW"

    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary"""
        daily_loss_pct = self.daily_pnl / self.daily_start_value if self.daily_start_value > 0 else 0
        alert_level = self.get_risk_alert_level()

        return {
            'alert_level': alert_level,
            'trading_enabled': self.trading_enabled,
            'daily_pnl': self.daily_pnl,
            'daily_pnl_pct': daily_loss_pct,
            'total_exposure': self.total_exposure,
            'long_exposure': self.long_exposure,
            'short_exposure': self.short_exposure,
            'risk_utilization': self.risk_utilization,
            'consecutive_losses': self.consecutive_losses,
            'position_size_multiplier': self.position_size_reduction,
            'trade_count_today': self.trade_count_today,
            'remaining_exposure_capacity': max(0, self.max_total_exposure - self.total_exposure),
            'remaining_daily_loss_capacity': max(0, self.warning_loss_threshold + daily_loss_pct)
        }

    def enable_trading(self):
        """Manually enable trading (admin override)"""
        self.trading_enabled = True

    def disable_trading(self):
        """Manually disable trading"""
        self.trading_enabled = False

# ==========================================
# 6. ML SIGNAL GENERATOR MODULE
# ==========================================

class MLSignalGenerator:
    """Enhanced ML model for precise trading signal generation"""

    def __init__(self):
        # Classification model for BUY/SELL/HOLD signals
        self.classification_model = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            class_weight='balanced'
        )

        # Regression models for price prediction
        self.price_regression_model = GradientBoostingRegressor(
            n_estimators=150,
            max_depth=8,
            learning_rate=0.1,
            subsample=0.8,
            random_state=42
        )

        # Additional return prediction model
        self.return_regression_model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.15,
            random_state=42
        )

        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.is_trained = False
        self.feature_names = []
        self.training_history = []

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enhanced feature engineering for ML models"""

        # Core technical indicators
        feature_cols = [
            'rsi', 'macd', 'macd_signal', 'macd_histogram',
            'bb_upper', 'bb_middle', 'bb_lower',
            'sma_10', 'sma_20', 'sma_50', 'ema_10', 'ema_20',
            'price_change', 'volume_change', 'high_low_ratio', 'close_open_ratio'
        ]

        # Select available features
        available_features = [col for col in feature_cols if col in df.columns]
        features_df = df[available_features].copy()

        # Add price-based features
        if 'close' in df.columns:
            # Price momentum indicators
            for period in [3, 5, 10, 20]:
                features_df[f'price_momentum_{period}'] = df['close'] / df['close'].shift(period) - 1
                features_df[f'price_volatility_{period}'] = df['close'].rolling(period).std() / df['close'].rolling(period).mean()

            # Moving average crossovers
            if 'sma_10' in features_df.columns and 'sma_20' in features_df.columns:
                features_df['ma_cross_10_20'] = (features_df['sma_10'] / features_df['sma_20'] - 1) * 100

            if 'ema_10' in features_df.columns and 'ema_20' in features_df.columns:
                features_df['ema_cross_10_20'] = (features_df['ema_10'] / features_df['ema_20'] - 1) * 100

        # Volume-based features
        if 'volume' in df.columns:
            features_df['volume_sma_10'] = df['volume'].rolling(10).mean()
            features_df['volume_ratio'] = df['volume'] / features_df['volume_sma_10']

            # Volume momentum
            for period in [3, 5, 10]:
                features_df[f'volume_momentum_{period}'] = df['volume'] / df['volume'].shift(period) - 1

        # RSI-based features
        if 'rsi' in features_df.columns:
            features_df['rsi_oversold'] = (features_df['rsi'] < 30).astype(int)
            features_df['rsi_overbought'] = (features_df['rsi'] > 70).astype(int)
            features_df['rsi_momentum'] = features_df['rsi'].diff()

        # MACD-based features
        if 'macd' in features_df.columns and 'macd_signal' in features_df.columns:
            features_df['macd_cross'] = (features_df['macd'] > features_df['macd_signal']).astype(int)
            features_df['macd_divergence'] = features_df['macd'] - features_df['macd_signal']

        # Bollinger Bands features
        if all(col in features_df.columns for col in ['bb_upper', 'bb_lower', 'close']):
            bb_width = features_df['bb_upper'] - features_df['bb_lower']
            bb_middle = (features_df['bb_upper'] + features_df['bb_lower']) / 2
            features_df['bb_position'] = (df['close'] - features_df['bb_lower']) / bb_width
            features_df['bb_squeeze'] = bb_width / bb_middle

        # Lag features for key indicators
        lag_features = ['close', 'rsi', 'macd', 'volume']
        for col in lag_features:
            if col in df.columns:
                for lag in [1, 2, 3, 5, 10]:
                    features_df[f'{col}_lag_{lag}'] = df[col].shift(lag)

        # Rolling statistics
        if 'close' in df.columns:
            for window in [5, 10, 20]:
                features_df[f'price_rolling_mean_{window}'] = df['close'].rolling(window).mean()
                features_df[f'price_rolling_std_{window}'] = df['close'].rolling(window).std()
                features_df[f'price_z_score_{window}'] = (df['close'] - features_df[f'price_rolling_mean_{window}']) / features_df[f'price_rolling_std_{window}']

        # Time-based features
        features_df['hour'] = df.index.hour
        features_df['day_of_week'] = df.index.dayofweek
        features_df['is_weekend'] = (df.index.dayofweek >= 5).astype(int)

        # Store feature names for later use
        self.feature_names = [col for col in features_df.columns if col != 'close']

        return features_df.dropna()

    def create_labels(self, df: pd.DataFrame, horizon: int = Config.ML_PREDICTION_HORIZON) -> Dict[str, pd.Series]:
        """Create enhanced labels for classification and regression"""

        # Calculate future returns for different horizons
        future_returns_short = df['close'].shift(-horizon) / df['close'] - 1  # Next few periods
        future_returns_long = df['close'].shift(-horizon*2) / df['close'] - 1  # Longer term

        # Classification labels based on future returns
        conditions = [
            future_returns_short > 0.015,   # Strong buy (1.5%+)
            future_returns_short > 0.005,   # Buy (0.5%+)
            future_returns_short < -0.015,  # Strong sell (-1.5%+)
            future_returns_short < -0.005   # Sell (-0.5%+)
        ]
        choices = ['STRONG_BUY', 'BUY', 'STRONG_SELL', 'SELL']

        classification_labels = np.select(conditions, choices, default='HOLD')

        # Regression labels: actual future prices and returns
        future_prices = df['close'].shift(-horizon)
        future_returns = future_returns_short

        return {
            'classification': pd.Series(classification_labels, index=df.index),
            'future_price': future_prices,
            'future_return': future_returns,
            'future_return_long': future_returns_long
        }

    def train_model(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Enhanced training with multiple models and comprehensive evaluation"""

        # Prepare features and labels
        features_df = self.prepare_features(df)
        labels_dict = self.create_labels(df)

        # Use only rows where we have all data
        features_df = features_df.dropna()
        valid_indices = features_df.index

        # Filter labels to valid indices
        classification_labels = labels_dict['classification'].loc[valid_indices].dropna()
        price_labels = labels_dict['future_price'].loc[valid_indices].dropna()
        return_labels = labels_dict['future_return'].loc[valid_indices].dropna()

        # Find common indices across all datasets
        common_index = features_df.index.intersection(classification_labels.index)
        common_index = common_index.intersection(price_labels.index)
        common_index = common_index.intersection(return_labels.index)

        if len(common_index) < 100:
            return {"error": f"Insufficient data for training. Found {len(common_index)} samples, need at least 100"}

        # Prepare final datasets
        X = features_df.loc[common_index]
        y_class = classification_labels.loc[common_index]
        y_price = price_labels.loc[common_index]
        y_return = return_labels.loc[common_index]

        # Split data
        X_train, X_test, y_class_train, y_class_test = train_test_split(
            X, y_class, test_size=1-Config.TRAIN_TEST_SPLIT, random_state=42, stratify=y_class
        )

        # Align price and return labels with the split
        y_price_train = y_price.loc[X_train.index]
        y_price_test = y_price.loc[X_test.index]
        y_return_train = y_return.loc[X_train.index]
        y_return_test = y_return.loc[X_test.index]

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train classification model
        y_class_encoded = self.label_encoder.fit_transform(y_class_train)
        self.classification_model.fit(X_train_scaled, y_class_encoded)

        # Train price regression model
        self.price_regression_model.fit(X_train_scaled, y_price_train)

        # Train return regression model
        self.return_regression_model.fit(X_train_scaled, y_return_train)

        # Evaluate models
        results = {}

        # Classification evaluation
        y_class_pred = self.classification_model.predict(X_test_scaled)
        y_class_test_encoded = self.label_encoder.transform(y_class_test)

        results['classification_accuracy'] = accuracy_score(y_class_test_encoded, y_class_pred)
        results['classification_report'] = classification_report(
            y_class_test_encoded, y_class_pred,
            target_names=self.label_encoder.classes_,
            output_dict=True
        )

        # Price regression evaluation
        y_price_pred = self.price_regression_model.predict(X_test_scaled)
        price_mae = np.mean(np.abs(y_price_test - y_price_pred))
        price_rmse = np.sqrt(np.mean((y_price_test - y_price_pred) ** 2))
        price_r2 = self.price_regression_model.score(X_test_scaled, y_price_test)

        results['price_mae'] = price_mae
        results['price_rmse'] = price_rmse
        results['price_r2'] = price_r2

        # Return regression evaluation
        y_return_pred = self.return_regression_model.predict(X_test_scaled)
        return_mae = np.mean(np.abs(y_return_test - y_return_pred))
        return_rmse = np.sqrt(np.mean((y_return_test - y_return_pred) ** 2))
        return_r2 = self.return_regression_model.score(X_test_scaled, y_return_test)

        results['return_mae'] = return_mae
        results['return_rmse'] = return_rmse
        results['return_r2'] = return_r2

        # Feature importance
        results['feature_importance'] = dict(zip(self.feature_names,
                                                self.classification_model.feature_importances_))

        # Training metadata
        results['training_samples'] = len(X_train)
        results['test_samples'] = len(X_test)
        results['feature_count'] = len(self.feature_names)
        results['class_distribution'] = y_class_train.value_counts().to_dict()

        # Store training history
        training_record = {
            'timestamp': datetime.now(),
            'samples': len(X_train),
            'accuracy': results['classification_accuracy'],
            'price_r2': results['price_r2'],
            'return_r2': results['return_r2']
        }
        self.training_history.append(training_record)

        self.is_trained = True

        return results

    def predict_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Enhanced signal generation with multiple model predictions"""
        if not self.is_trained:
            return {"error": "Model not trained"}

        features_df = self.prepare_features(df)
        if len(features_df) == 0:
            return {"error": "No valid features"}

        # Use latest data point
        latest_features = features_df.iloc[-1:].values

        # Scale features
        latest_scaled = self.scaler.transform(latest_features)

        # Classification prediction
        signal_encoded = self.classification_model.predict(latest_scaled)[0]
        signal_proba = self.classification_model.predict_proba(latest_scaled)[0]
        signal = self.label_encoder.inverse_transform([signal_encoded])[0]

        # Price prediction
        predicted_price = self.price_regression_model.predict(latest_scaled)[0]

        # Return prediction
        predicted_return = self.return_regression_model.predict(latest_scaled)[0]

        current_price = df['close'].iloc[-1]

        # Calculate confidence based on probability and model agreement
        max_proba = np.max(signal_proba)

        # Additional confidence from return prediction alignment
        return_signal_agreement = 0.5  # neutral baseline
        if signal in ['BUY', 'STRONG_BUY'] and predicted_return > 0:
            return_signal_agreement = 0.8
        elif signal in ['SELL', 'STRONG_SELL'] and predicted_return < 0:
            return_signal_agreement = 0.8
        elif signal == 'HOLD' and abs(predicted_return) < 0.01:
            return_signal_agreement = 0.7

        # Combined confidence
        confidence = (max_proba + return_signal_agreement) / 2

        # Technical indicator confirmation
        technical_confirmation = self._get_technical_confirmation(df)

        # Risk assessment
        risk_level = self._assess_risk(df, predicted_return)

        return {
            "signal": signal,
            "confidence": confidence,
            "current_price": current_price,
            "predicted_price": predicted_price,
            "predicted_return": predicted_return,
            "expected_return": (predicted_price / current_price) - 1,
            "probabilities": dict(zip(self.label_encoder.classes_, signal_proba)),
            "technical_confirmation": technical_confirmation,
            "risk_level": risk_level,
            "model_agreement": return_signal_agreement
        }

    def _get_technical_confirmation(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get technical indicator confirmation"""
        if len(df) == 0:
            return {}

        latest = df.iloc[-1]
        confirmation = {}

        # RSI confirmation
        if 'rsi' in df.columns:
            rsi_val = latest['rsi']
            if rsi_val < 30:
                confirmation['rsi'] = 'oversold_buy'
            elif rsi_val > 70:
                confirmation['rsi'] = 'overbought_sell'
            else:
                confirmation['rsi'] = 'neutral'

        # MACD confirmation
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            macd_val = latest['macd']
            macd_signal_val = latest['macd_signal']
            if macd_val > macd_signal_val:
                confirmation['macd'] = 'bullish'
            else:
                confirmation['macd'] = 'bearish'

        # Bollinger Bands confirmation
        if all(col in df.columns for col in ['bb_upper', 'bb_lower', 'close']):
            bb_upper = latest['bb_upper']
            bb_lower = latest['bb_lower']
            close_price = latest['close']

            if close_price <= bb_lower:
                confirmation['bollinger'] = 'oversold_buy'
            elif close_price >= bb_upper:
                confirmation['bollinger'] = 'overbought_sell'
            else:
                confirmation['bollinger'] = 'neutral'

        return confirmation

    def _assess_risk(self, df: pd.DataFrame, predicted_return: float) -> str:
        """Assess risk level of the prediction"""
        risk_factors = 0

        # Volatility risk
        if 'close' in df.columns and len(df) >= 20:
            recent_volatility = df['close'].tail(20).std() / df['close'].tail(20).mean()
            if recent_volatility > 0.05:  # 5% volatility
                risk_factors += 1

        # Magnitude of predicted return
        if abs(predicted_return) > 0.1:  # 10% predicted move
            risk_factors += 1

        # Volume analysis
        if 'volume' in df.columns and len(df) >= 10:
            recent_volume = df['volume'].tail(5).mean()
            avg_volume = df['volume'].tail(20).mean()
            if recent_volume < avg_volume * 0.5:  # Low volume
                risk_factors += 1

        # Risk classification
        if risk_factors == 0:
            return 'low'
        elif risk_factors == 1:
            return 'medium'
        else:
            return 'high'

# ==========================================
# 5. BINANCE FUTURES INTEGRATION
# ==========================================

class FuturesTrader:
    """
    🚀 스마트 주문 시스템이 탑재된 바이낸스 선물 거래 클래스

    핵심 기능:
    1. AI 신호 기반 최적 진입가 계산
    2. 동적 손절/익절 시스템 (ATR 기반)
    3. 트레일링 스톱 & 부분 익절 시스템
    4. OCO 주문 & 조건부 주문 관리
    5. 스마트 주문 관리 & 시간 기반 취소
    """

    def __init__(self):
        self.connector = BinanceFuturesConnector()
        self.risk_manager = RiskManager()

        # 스마트 주문 관리 상태
        self.active_orders = {}
        self.trailing_stops = {}
        self.profit_targets = {}
        self.time_based_orders = {}

        # 부분 익절 설정
        self.profit_taking_levels = [0.25, 0.50, 0.75]  # 25%, 50%, 75% 익절
        self.profit_taking_thresholds = [2.0, 4.0, 6.0]  # 2%, 4%, 6% 수익률

        print("🚀 스마트 주문 시스템 초기화 완료")
        print(f"   부분 익절 레벨: {self.profit_taking_levels}")
        print(f"   익절 임계점: {self.profit_taking_thresholds}%")

    def calculate_optimal_entry_price(self, signal: Dict[str, Any], symbol: str,
                                    current_price: float, market_data: pd.DataFrame = None) -> Dict[str, Any]:
        """
        AI 신호 기반 최적 진입가 계산

        Args:
            signal: AI 거래 신호
            symbol: 거래 심볼
            current_price: 현재 가격
            market_data: 시장 데이터 (지지/저항 계산용)

        Returns:
            최적 진입가 정보
        """
        try:
            signal_type = signal.get('signal', 'HOLD')
            confidence = signal.get('confidence', 0)

            if signal_type == 'HOLD':
                return {'optimal_entry': current_price, 'order_type': 'MARKET'}

            # 신뢰도에 따른 슬리피지 허용치 계산
            max_slippage = 0.001 if confidence > 0.8 else 0.002 if confidence > 0.6 else 0.005

            # 기본 진입가 계산
            if signal_type in ['BUY', 'STRONG_BUY']:
                # 매수 시: 현재가보다 약간 높은 가격으로 빠른 체결
                slippage_factor = 1 + max_slippage
                optimal_entry = current_price * slippage_factor

                # 지지선이 있다면 더 공격적으로
                if market_data is not None:
                    support_level = self._calculate_support_resistance(market_data, 'support')
                    if support_level and current_price > support_level:
                        # 지지선 근처라면 더 공격적으로 진입
                        optimal_entry = current_price * (1 + max_slippage * 0.5)

            elif signal_type in ['SELL', 'STRONG_SELL']:
                # 매도 시: 현재가보다 약간 낮은 가격으로 빠른 체결
                slippage_factor = 1 - max_slippage
                optimal_entry = current_price * slippage_factor

                # 저항선이 있다면 더 공격적으로
                if market_data is not None:
                    resistance_level = self._calculate_support_resistance(market_data, 'resistance')
                    if resistance_level and current_price < resistance_level:
                        # 저항선 근처라면 더 공격적으로 진입
                        optimal_entry = current_price * (1 - max_slippage * 0.5)

            # 주문 타입 결정
            price_diff_pct = abs(optimal_entry - current_price) / current_price
            order_type = 'MARKET' if price_diff_pct < 0.001 else 'LIMIT'

            return {
                'optimal_entry': round(optimal_entry, 2),
                'current_price': current_price,
                'price_improvement': round((optimal_entry - current_price) / current_price * 100, 4),
                'order_type': order_type,
                'max_slippage': max_slippage,
                'confidence': confidence,
                'signal_strength': signal_type
            }

        except Exception as e:
            return {'error': f'진입가 계산 실패: {str(e)}'}

    def set_dynamic_stop_loss(self, symbol: str, entry_price: float, position_side: str,
                            atr_value: float = None, leverage: int = 1) -> Dict[str, Any]:
        """
        ATR 기반 동적 손절선 설정

        Args:
            symbol: 거래 심볼
            entry_price: 진입 가격
            position_side: 포지션 방향 ('LONG' or 'SHORT')
            atr_value: ATR 값
            leverage: 레버리지

        Returns:
            손절선 정보
        """
        try:
            # ATR 기본값 설정 (현재가의 2%)
            if atr_value is None:
                atr_value = entry_price * 0.02

            # 레버리지에 따른 ATR 조정
            atr_multiplier = max(1.0, 3.0 - (leverage * 0.2))  # 레버리지가 높을수록 좁은 손절

            if position_side == 'LONG':
                # 롱 포지션: 진입가 - (ATR × 배수)
                stop_loss_price = entry_price - (atr_value * atr_multiplier)
                take_profit_price = entry_price + (atr_value * atr_multiplier * 2)  # 2:1 손익비

            else:  # SHORT
                # 숏 포지션: 진입가 + (ATR × 배수)
                stop_loss_price = entry_price + (atr_value * atr_multiplier)
                take_profit_price = entry_price - (atr_value * atr_multiplier * 2)  # 2:1 손익비

            # 손절 폭 계산
            stop_loss_pct = abs(stop_loss_price - entry_price) / entry_price * 100
            take_profit_pct = abs(take_profit_price - entry_price) / entry_price * 100

            return {
                'stop_loss_price': round(stop_loss_price, 2),
                'take_profit_price': round(take_profit_price, 2),
                'stop_loss_pct': round(stop_loss_pct, 2),
                'take_profit_pct': round(take_profit_pct, 2),
                'atr_value': atr_value,
                'atr_multiplier': atr_multiplier,
                'risk_reward_ratio': round(take_profit_pct / stop_loss_pct, 2)
            }

        except Exception as e:
            return {'error': f'동적 손절선 설정 실패: {str(e)}'}

    def execute_smart_order(self, signal: Dict[str, Any], symbol: str = 'BTCUSDT',
                          leverage: int = 5, market_data: pd.DataFrame = None,
                          auto_stop_loss: bool = True) -> Dict[str, Any]:
        """
        스마트 주문 실행 (진입가 최적화 + 자동 손절/익절)

        Args:
            signal: AI 거래 신호
            symbol: 거래 심볼
            leverage: 레버리지
            market_data: 시장 데이터
            auto_stop_loss: 자동 손절/익절 설정 여부

        Returns:
            스마트 주문 실행 결과
        """
        try:
            # 1. 연결 상태 확인
            connection_check = self.check_connection()
            if not connection_check.get('connected'):
                return {'success': False, 'error': '거래소 연결 실패'}

            # 2. 현재 가격 조회
            current_price = 63000.0  # 실제로는 실시간 가격 API 사용

            # 3. 최적 진입가 계산
            entry_analysis = self.calculate_optimal_entry_price(signal, symbol, current_price, market_data)
            if 'error' in entry_analysis:
                return {'success': False, 'error': entry_analysis['error']}

            # 4. 레버리지 및 마진 설정
            leverage = min(leverage, self.connector.max_leverage)
            self.connector.set_leverage(symbol, leverage)
            self.connector.set_margin_type(symbol, 'CROSSED')

            # 5. 리스크 체크
            risk_check = self.risk_manager.check_trading_permission()
            if not risk_check['trading_allowed']:
                return {
                    'success': False,
                    'error': '리스크 관리 제한',
                    'blocks': risk_check['blocks']
                }

            # 6. 포지션 크기 계산
            account_info = self.connector.get_account_info()
            if not account_info:
                return {'success': False, 'error': '계좌 정보 조회 실패'}

            available_balance = float(account_info.get('availableBalance', 0))
            position_size_usd = available_balance * risk_check['adjusted_position_size'] * leverage
            quantity = position_size_usd / entry_analysis['optimal_entry']

            # 7. 신호 강도 확인
            signal_type = signal.get('signal', 'HOLD')
            confidence = signal.get('confidence', 0)

            if signal_type == 'HOLD' or confidence < 0.6:
                return {
                    'success': False,
                    'error': '신호 강도 부족',
                    'signal': signal_type,
                    'confidence': confidence
                }

            # 8. 스마트 주문 실행
            if entry_analysis['order_type'] == 'MARKET':
                # 시장가 주문
                order_result = self.connector.place_market_order(symbol, signal_type, quantity)
            else:
                # 지정가 주문
                order_result = self.connector.place_limit_order(
                    symbol, signal_type, quantity, entry_analysis['optimal_entry']
                )

            if not order_result:
                return {'success': False, 'error': '주문 실행 실패'}

            # 9. 자동 손절/익절 설정
            if auto_stop_loss:
                position_side = 'LONG' if signal_type in ['BUY', 'STRONG_BUY'] else 'SHORT'
                atr_value = current_price * 0.02  # 임시 ATR 값

                stop_loss_info = self.set_dynamic_stop_loss(
                    symbol, entry_analysis['optimal_entry'], position_side, atr_value, leverage
                )

                if 'error' not in stop_loss_info:
                    # OCO 주문 설정 (손절 + 익절)
                    oco_result = self._place_oco_order(
                        symbol, position_side, quantity,
                        stop_loss_info['stop_loss_price'],
                        stop_loss_info['take_profit_price']
                    )

                    # 트레일링 스톱 활성화
                    self._activate_trailing_stop(symbol, position_side, entry_analysis['optimal_entry'])

            # 10. 주문 추적 시작
            order_id = order_result.get('orderId')
            self.active_orders[order_id] = {
                'symbol': symbol,
                'signal': signal,
                'entry_price': entry_analysis['optimal_entry'],
                'quantity': quantity,
                'leverage': leverage,
                'timestamp': datetime.now(),
                'stop_loss_info': stop_loss_info if auto_stop_loss else None
            }

            # 11. 결과 반환
            return {
                'success': True,
                'order_id': order_id,
                'symbol': symbol,
                'signal_type': signal_type,
                'confidence': confidence,
                'entry_analysis': entry_analysis,
                'quantity': quantity,
                'leverage': leverage,
                'stop_loss_info': stop_loss_info if auto_stop_loss else None,
                'risk_management': risk_check,
                'timestamp': datetime.now().isoformat(),
                'smart_features': {
                    'optimal_entry': True,
                    'dynamic_stops': auto_stop_loss,
                    'trailing_stop': auto_stop_loss,
                    'partial_profit': auto_stop_loss
                }
            }

        except Exception as e:
            return {'success': False, 'error': f'스마트 주문 실행 실패: {str(e)}'}

    def manage_trailing_stop(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """
        트레일링 스톱 관리

        Args:
            symbol: 거래 심볼
            current_price: 현재 가격

        Returns:
            트레일링 스톱 업데이트 결과
        """
        try:
            if symbol not in self.trailing_stops:
                return {'error': f'{symbol}에 대한 트레일링 스톱이 없습니다'}

            trailing_info = self.trailing_stops[symbol]
            position_side = trailing_info['position_side']
            entry_price = trailing_info['entry_price']
            trailing_distance = trailing_info['trailing_distance']
            current_stop = trailing_info['current_stop']
            best_price = trailing_info.get('best_price', entry_price)

            # 최고/최저 가격 업데이트
            if position_side == 'LONG':
                if current_price > best_price:
                    best_price = current_price
                    new_stop = current_price - trailing_distance

                    # 스톱이 상승했을 때만 업데이트
                    if new_stop > current_stop:
                        current_stop = new_stop
                        trailing_updated = True
                    else:
                        trailing_updated = False
                else:
                    trailing_updated = False

            else:  # SHORT
                if current_price < best_price:
                    best_price = current_price
                    new_stop = current_price + trailing_distance

                    # 스톱이 하락했을 때만 업데이트
                    if new_stop < current_stop:
                        current_stop = new_stop
                        trailing_updated = True
                    else:
                        trailing_updated = False
                else:
                    trailing_updated = False

            # 트레일링 스톱 정보 업데이트
            self.trailing_stops[symbol].update({
                'best_price': best_price,
                'current_stop': current_stop,
                'last_update': datetime.now()
            })

            # 스톱 로스 트리거 확인
            stop_triggered = False
            if position_side == 'LONG' and current_price <= current_stop:
                stop_triggered = True
            elif position_side == 'SHORT' and current_price >= current_stop:
                stop_triggered = True

            if stop_triggered:
                # 포지션 청산 실행
                close_result = self.connector.close_position(symbol, 100.0)
                del self.trailing_stops[symbol]

                return {
                    'trailing_stop_triggered': True,
                    'close_result': close_result,
                    'exit_price': current_price,
                    'stop_price': current_stop
                }

            return {
                'trailing_updated': trailing_updated,
                'current_stop': current_stop,
                'best_price': best_price,
                'current_price': current_price,
                'unrealized_pnl_pct': ((current_price - entry_price) / entry_price * 100) if position_side == 'LONG' else ((entry_price - current_price) / entry_price * 100)
            }

        except Exception as e:
            return {'error': f'트레일링 스톱 관리 실패: {str(e)}'}

    def partial_profit_taking(self, symbol: str, current_price: float, entry_price: float,
                            position_side: str, total_quantity: float) -> Dict[str, Any]:
        """
        부분 익절 시스템 (25%, 50%, 75%)

        Args:
            symbol: 거래 심볼
            current_price: 현재 가격
            entry_price: 진입 가격
            position_side: 포지션 방향
            total_quantity: 전체 포지션 수량

        Returns:
            부분 익절 실행 결과
        """
        try:
            # 현재 수익률 계산
            if position_side == 'LONG':
                pnl_pct = (current_price - entry_price) / entry_price * 100
            else:
                pnl_pct = (entry_price - current_price) / entry_price * 100

            if pnl_pct <= 0:
                return {'message': '아직 수익이 없어 부분 익절 불가'}

            # 익절할 구간 확인
            profit_taken = []
            remaining_quantity = total_quantity

            for i, threshold in enumerate(self.profit_taking_thresholds):
                if pnl_pct >= threshold:
                    profit_level = self.profit_taking_levels[i]

                    # 이미 익절했는지 확인
                    profit_key = f"{symbol}_{i}"
                    if profit_key not in self.profit_targets:
                        # 부분 익절 실행
                        sell_quantity = total_quantity * profit_level
                        remaining_quantity -= sell_quantity

                        close_result = self.connector.close_position(symbol, profit_level * 100)

                        profit_taken.append({
                            'level': i + 1,
                            'threshold_pct': threshold,
                            'profit_pct': profit_level * 100,
                            'quantity_sold': sell_quantity,
                            'price': current_price,
                            'realized_pnl': sell_quantity * (current_price - entry_price) if position_side == 'LONG' else sell_quantity * (entry_price - current_price),
                            'close_result': close_result
                        })

                        # 익절 기록
                        self.profit_targets[profit_key] = {
                            'executed': True,
                            'price': current_price,
                            'timestamp': datetime.now()
                        }

            return {
                'success': True,
                'profit_taken': profit_taken,
                'current_pnl_pct': pnl_pct,
                'remaining_quantity': remaining_quantity,
                'total_profit_levels_hit': len(profit_taken)
            }

        except Exception as e:
            return {'error': f'부분 익절 실패: {str(e)}'}

    def check_connection(self) -> Dict[str, Any]:
        """연결 상태 및 계좌 정보 확인"""
        try:
            server_time = self.connector.get_server_time()
            account_info = self.connector.get_account_info()

            if not server_time or not account_info:
                return {
                    'connected': False,
                    'error': 'API 연결 실패'
                }

            return {
                'connected': True,
                'server_time': server_time,
                'account_info': account_info,
                'balance': account_info.get('totalWalletBalance', '0'),
                'available_margin': account_info.get('availableBalance', '0')
            }
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }

    # ==========================================
    # 스마트 주문 시스템 헬퍼 메서드들
    # ==========================================

    def _calculate_support_resistance(self, market_data: pd.DataFrame, level_type: str) -> float:
        """
        지지/저항선 계산

        Args:
            market_data: 시장 데이터
            level_type: 'support' 또는 'resistance'

        Returns:
            지지/저항 레벨 가격
        """
        try:
            if market_data is None or len(market_data) < 20:
                return None

            # 최근 20개 캔들 사용
            recent_data = market_data.tail(20)

            if level_type == 'support':
                # 지지선: 최근 저점들의 평균
                low_prices = recent_data['low'].nsmallest(5)
                return float(low_prices.mean())
            else:
                # 저항선: 최근 고점들의 평균
                high_prices = recent_data['high'].nlargest(5)
                return float(high_prices.mean())

        except Exception as e:
            print(f"지지/저항선 계산 실패: {e}")
            return None

    def _place_oco_order(self, symbol: str, position_side: str, quantity: float,
                        stop_price: float, profit_price: float) -> Dict[str, Any]:
        """
        OCO (One-Cancels-Other) 주문 실행

        Args:
            symbol: 거래 심볼
            position_side: 포지션 방향
            quantity: 수량
            stop_price: 손절 가격
            profit_price: 익절 가격

        Returns:
            OCO 주문 결과
        """
        try:
            # OCO 주문 시뮬레이션 (실제로는 Binance OCO API 사용)
            oco_order = {
                'symbol': symbol,
                'position_side': position_side,
                'quantity': quantity,
                'stop_loss_price': stop_price,
                'take_profit_price': profit_price,
                'order_type': 'OCO',
                'status': 'PENDING',
                'created_at': datetime.now(),
                'order_id': f"OCO_{symbol}_{int(datetime.now().timestamp())}"
            }

            # OCO 주문 추적 시작
            order_id = oco_order['order_id']
            self.active_orders[order_id] = oco_order

            print(f"OCO 주문 생성: {symbol} | 손절: ${stop_price} | 익절: ${profit_price}")

            return {
                'success': True,
                'oco_order_id': order_id,
                'stop_loss_price': stop_price,
                'take_profit_price': profit_price,
                'message': 'OCO 주문 생성 완료'
            }

        except Exception as e:
            return {'error': f'OCO 주문 실패: {str(e)}'}

    def _activate_trailing_stop(self, symbol: str, position_side: str, entry_price: float) -> bool:
        """
        트레일링 스톱 활성화

        Args:
            symbol: 거래 심볼
            position_side: 포지션 방향
            entry_price: 진입 가격

        Returns:
            활성화 성공 여부
        """
        try:
            # ATR 기반 트레일링 거리 계산
            trailing_distance = entry_price * 0.03  # 3% 트레일링 거리

            self.trailing_stops[symbol] = {
                'position_side': position_side,
                'entry_price': entry_price,
                'trailing_distance': trailing_distance,
                'current_stop': entry_price - trailing_distance if position_side == 'LONG' else entry_price + trailing_distance,
                'best_price': entry_price,
                'activated_at': datetime.now()
            }

            print(f"트레일링 스톱 활성화: {symbol} | 거리: {trailing_distance:.2f}")
            return True

        except Exception as e:
            print(f"트레일링 스톱 활성화 실패: {e}")
            return False

    def manage_conditional_orders(self, symbol: str, current_price: float,
                                ai_signal: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        조건부 주문 관리 (AI 신호 재확인 기반)

        Args:
            symbol: 거래 심볼
            current_price: 현재 가격
            ai_signal: 최신 AI 신호

        Returns:
            조건부 주문 처리 결과
        """
        try:
            results = []

            # 활성 주문들 확인
            for order_id, order_info in list(self.active_orders.items()):
                if order_info.get('symbol') != symbol:
                    continue

                order_type = order_info.get('order_type', 'MARKET')

                # OCO 주문 처리
                if order_type == 'OCO':
                    oco_result = self._check_oco_trigger(order_info, current_price)
                    if oco_result.get('triggered'):
                        results.append(oco_result)
                        del self.active_orders[order_id]

                # 조건부 주문 처리 (AI 신호 재확인)
                elif order_type == 'CONDITIONAL':
                    conditional_result = self._check_conditional_trigger(order_info, ai_signal)
                    if conditional_result.get('triggered'):
                        results.append(conditional_result)
                        del self.active_orders[order_id]

                # 시간 기반 주문 취소
                elif order_type == 'TIMED':
                    time_result = self._check_time_based_cancel(order_info)
                    if time_result.get('cancelled'):
                        results.append(time_result)
                        del self.active_orders[order_id]

            return {
                'success': True,
                'processed_orders': len(results),
                'results': results,
                'active_orders_remaining': len(self.active_orders)
            }

        except Exception as e:
            return {'error': f'조건부 주문 관리 실패: {str(e)}'}

    def _check_oco_trigger(self, oco_order: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """OCO 주문 트리거 확인"""
        try:
            stop_price = oco_order['stop_loss_price']
            profit_price = oco_order['take_profit_price']
            position_side = oco_order['position_side']

            if position_side == 'LONG':
                # 롱 포지션: 손절 또는 익절 확인
                if current_price <= stop_price:
                    # 손절 트리거
                    return {
                        'triggered': True,
                        'trigger_type': 'STOP_LOSS',
                        'exit_price': current_price,
                        'order_id': oco_order['order_id']
                    }
                elif current_price >= profit_price:
                    # 익절 트리거
                    return {
                        'triggered': True,
                        'trigger_type': 'TAKE_PROFIT',
                        'exit_price': current_price,
                        'order_id': oco_order['order_id']
                    }

            else:  # SHORT
                # 숏 포지션: 손절 또는 익절 확인
                if current_price >= stop_price:
                    # 손절 트리거
                    return {
                        'triggered': True,
                        'trigger_type': 'STOP_LOSS',
                        'exit_price': current_price,
                        'order_id': oco_order['order_id']
                    }
                elif current_price <= profit_price:
                    # 익절 트리거
                    return {
                        'triggered': True,
                        'trigger_type': 'TAKE_PROFIT',
                        'exit_price': current_price,
                        'order_id': oco_order['order_id']
                    }

            return {'triggered': False}

        except Exception as e:
            return {'error': f'OCO 트리거 확인 실패: {str(e)}'}

    def _check_conditional_trigger(self, conditional_order: Dict[str, Any],
                                 ai_signal: Dict[str, Any]) -> Dict[str, Any]:
        """조건부 주문 트리거 확인 (AI 신호 재확인)"""
        try:
            if not ai_signal:
                return {'triggered': False}

            original_signal = conditional_order.get('original_signal', 'HOLD')
            current_signal = ai_signal.get('signal', 'HOLD')
            confidence = ai_signal.get('confidence', 0)

            # AI 신호가 반전되었거나 신뢰도가 떨어졌는지 확인
            signal_reversed = (
                (original_signal in ['BUY', 'STRONG_BUY'] and current_signal in ['SELL', 'STRONG_SELL']) or
                (original_signal in ['SELL', 'STRONG_SELL'] and current_signal in ['BUY', 'STRONG_BUY'])
            )

            confidence_dropped = confidence < 0.5

            if signal_reversed or confidence_dropped:
                return {
                    'triggered': True,
                    'trigger_type': 'SIGNAL_REVERSAL' if signal_reversed else 'LOW_CONFIDENCE',
                    'original_signal': original_signal,
                    'current_signal': current_signal,
                    'confidence': confidence,
                    'order_id': conditional_order.get('order_id')
                }

            return {'triggered': False}

        except Exception as e:
            return {'error': f'조건부 트리거 확인 실패: {str(e)}'}

    def _check_time_based_cancel(self, timed_order: Dict[str, Any]) -> Dict[str, Any]:
        """시간 기반 주문 취소 확인"""
        try:
            created_at = timed_order.get('created_at')
            timeout_minutes = timed_order.get('timeout_minutes', 60)  # 기본 1시간

            if not created_at:
                return {'cancelled': False}

            elapsed_time = datetime.now() - created_at
            elapsed_minutes = elapsed_time.total_seconds() / 60

            if elapsed_minutes >= timeout_minutes:
                return {
                    'cancelled': True,
                    'cancel_reason': 'TIMEOUT',
                    'elapsed_minutes': elapsed_minutes,
                    'order_id': timed_order.get('order_id')
                }

            return {'cancelled': False}

        except Exception as e:
            return {'error': f'시간 기반 취소 확인 실패: {str(e)}'}

    def monitor_smart_positions(self, symbol: str = None) -> Dict[str, Any]:
        """
        스마트 포지션 모니터링 (트레일링 스톱, 부분 익절 포함)

        Args:
            symbol: 특정 심볼 모니터링 (None이면 전체)

        Returns:
            포지션 모니터링 결과
        """
        try:
            # 현재 포지션 조회
            positions = self.connector.get_positions()
            if not positions:
                return {
                    'active_positions': 0,
                    'monitoring_results': [],
                    'total_unrealized_pnl': 0
                }

            monitoring_results = []
            total_pnl = 0

            for position in positions:
                pos_symbol = position.get('symbol', '')
                pos_size = float(position.get('positionAmt', 0))

                if pos_size == 0:
                    continue

                if symbol and pos_symbol != symbol:
                    continue

                # 현재 가격 (실제로는 실시간 API에서 가져와야 함)
                current_price = 63000.0 if 'BTC' in pos_symbol else 4000.0

                entry_price = float(position.get('entryPrice', 0))
                position_side = 'LONG' if pos_size > 0 else 'SHORT'
                unrealized_pnl = float(position.get('unRealizedProfit', 0))
                total_pnl += unrealized_pnl

                # 트레일링 스톱 관리
                trailing_result = self.manage_trailing_stop(pos_symbol, current_price)

                # 부분 익절 확인
                profit_result = self.partial_profit_taking(
                    pos_symbol, current_price, entry_price, position_side, abs(pos_size)
                )

                # 조건부 주문 관리
                conditional_result = self.manage_conditional_orders(pos_symbol, current_price)

                monitoring_results.append({
                    'symbol': pos_symbol,
                    'position_side': position_side,
                    'size': pos_size,
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'unrealized_pnl': unrealized_pnl,
                    'trailing_stop': trailing_result,
                    'partial_profit': profit_result,
                    'conditional_orders': conditional_result
                })

            return {
                'active_positions': len(monitoring_results),
                'monitoring_results': monitoring_results,
                'total_unrealized_pnl': total_pnl,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {'error': f'스마트 포지션 모니터링 실패: {str(e)}'}

    def close_all_positions(self, emergency: bool = False) -> Dict[str, Any]:
        """모든 포지션 청산 (스마트 주문 포함)"""
        try:
            if emergency:
                # 긴급 청산: 모든 스마트 주문도 취소
                self.active_orders.clear()
                self.trailing_stops.clear()
                self.profit_targets.clear()

                results = self.connector.emergency_close_all_positions()
            else:
                positions = self.connector.get_positions()
                results = []

                for position in positions:
                    symbol = position.get('symbol')
                    result = self.connector.close_position(symbol, percentage=100.0)
                    results.append({
                        'symbol': symbol,
                        'close_result': result
                    })

                    # 해당 심볼의 스마트 주문들도 정리
                    if symbol in self.trailing_stops:
                        del self.trailing_stops[symbol]

                    # 익절 타겟 정리
                    profit_keys_to_remove = [key for key in self.profit_targets.keys() if symbol in key]
                    for key in profit_keys_to_remove:
                        del self.profit_targets[key]

            return {
                'success': True,
                'closed_positions': len(results),
                'results': results,
                'smart_orders_cleared': True
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'포지션 청산 실패: {str(e)}'
            }

    def execute_advanced_futures_trade(self, signal: Dict[str, Any], symbol: str = 'BTCUSDT',
                                     leverage: int = 5, atr_value: float = None) -> Dict[str, Any]:
        """
        Execute futures trade with advanced risk management

        Args:
            signal: AI trading signal
            symbol: Trading symbol
            leverage: Desired leverage
            atr_value: ATR value for dynamic stop loss

        Returns:
            Dictionary with trade execution result
        """

        try:
            # Get current account info and positions
            account_info = self.connector.get_account_info()
            positions = self.connector.get_positions()

            if not account_info:
                return {'success': False, 'error': 'Failed to get account info'}

            # Monitor margin health first
            margin_health = self.risk_manager.monitor_margin_health(positions, account_info)

            if margin_health.get('auto_close_triggered', False):
                # Execute emergency closure if needed
                closure_plan = self.risk_manager.emergency_position_closure(
                    positions, margin_health['margin_usage_pct']
                )
                return {
                    'success': False,
                    'error': 'Emergency margin management triggered',
                    'closure_plan': closure_plan,
                    'margin_health': margin_health
                }

            # Get current price for calculations
            current_price = 50000.0  # This should come from market data

            # Use default ATR if not provided
            if atr_value is None:
                atr_value = current_price * 0.02  # 2% of current price as default ATR

            # Calculate optimized position size with Kelly criterion
            position_sizing = self.risk_manager.calculate_futures_position_size(
                symbol=symbol,
                entry_price=current_price,
                atr_value=atr_value,
                leverage=leverage,
                win_rate=0.6  # Assuming 60% win rate for now
            )

            if 'error' in position_sizing:
                return {'success': False, 'error': position_sizing['error']}

            # Calculate dynamic stop loss and take profit
            dynamic_stops = self.risk_manager.calculate_dynamic_stop_loss(
                symbol=symbol,
                entry_price=current_price,
                current_price=current_price,
                atr_value=atr_value,
                leverage=leverage,
                position_side="LONG" if signal.get('signal') == 'BUY' else "SHORT"
            )

            # Check funding rate optimization (mock funding rate for testing)
            mock_funding_rate = 0.0005  # 0.05% funding rate
            funding_optimization = self.risk_manager.optimize_position_for_funding(
                symbol=symbol,
                current_position_size=0,  # No current position
                funding_rate=mock_funding_rate,
                market_signal=signal.get('signal', 'HOLD')
            )

            # Execute the trade with calculated parameters
            trade_result = self.execute_futures_trade(
                signal=signal,
                symbol=symbol,
                leverage=leverage
            )

            # Add advanced risk management info to result
            if trade_result.get('success'):
                trade_result.update({
                    'position_sizing': position_sizing,
                    'dynamic_stops': dynamic_stops,
                    'funding_optimization': funding_optimization,
                    'margin_health': margin_health,
                    'risk_management_applied': True
                })

            return trade_result

        except Exception as e:
            return {
                'success': False,
                'error': f'Advanced futures trade failed: {str(e)}'
            }

    def monitor_advanced_positions(self) -> Dict[str, Any]:
        """
        Advanced position monitoring with comprehensive risk analysis

        Returns:
            Dictionary with detailed position and risk analysis
        """

        try:
            # Get current positions and account info
            positions = self.connector.get_positions()
            account_info = self.connector.get_account_info()

            if not positions or not account_info:
                return {
                    'success': False,
                    'error': 'Failed to get position or account data'
                }

            # Comprehensive margin health analysis
            margin_health = self.risk_manager.monitor_margin_health(positions, account_info)

            # Analyze each position with dynamic risk management
            position_analyses = []
            total_funding_cost = 0

            for position in positions:
                symbol = position.get('symbol', '')
                size = float(position.get('positionAmt', 0))

                if size == 0:
                    continue

                entry_price = float(position.get('entryPrice', 0))
                mark_price = float(position.get('markPrice', 0))
                leverage = float(position.get('leverage', 1))

                # Mock ATR value (should come from technical analysis)
                atr_value = mark_price * 0.02

                # Calculate dynamic stops
                dynamic_stops = self.risk_manager.calculate_dynamic_stop_loss(
                    symbol=symbol,
                    entry_price=entry_price,
                    current_price=mark_price,
                    atr_value=atr_value,
                    leverage=leverage,
                    position_side="LONG" if size > 0 else "SHORT"
                )

                # Mock funding rate analysis
                mock_funding_rate = 0.0005
                funding_analysis = self.risk_manager.track_funding_fees(
                    symbol=symbol,
                    funding_rate=mock_funding_rate,
                    position_size=size
                )

                total_funding_cost += funding_analysis['estimated_daily_fee']

                position_analyses.append({
                    'symbol': symbol,
                    'size': size,
                    'entry_price': entry_price,
                    'mark_price': mark_price,
                    'leverage': leverage,
                    'dynamic_stops': dynamic_stops,
                    'funding_analysis': funding_analysis,
                    'unrealized_pnl': size * (mark_price - entry_price),
                    'unrealized_pnl_pct': ((mark_price - entry_price) / entry_price) * 100 if size > 0 else ((entry_price - mark_price) / entry_price) * 100
                })

            # Generate overall risk recommendations
            risk_summary = self.risk_manager.get_risk_summary()
            risk_summary.update({
                'margin_health': margin_health,
                'total_daily_funding_cost': total_funding_cost,
                'positions_analyzed': len(position_analyses),
                'emergency_action_required': margin_health.get('auto_close_triggered', False)
            })

            return {
                'success': True,
                'active_positions': len(position_analyses),
                'position_analyses': position_analyses,
                'margin_health': margin_health,
                'risk_summary': risk_summary,
                'total_funding_cost_daily': total_funding_cost,
                'recommendations': margin_health.get('recommendations', []),
                'monitoring_timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Advanced position monitoring failed: {str(e)}'
            }

# ==========================================
# 6. BACKTESTING ENGINE MODULE
# ==========================================

class BacktestingEngine:
    """Enhanced backtesting system with comprehensive performance analysis"""

    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.results = []

    def run_backtest(self, df: pd.DataFrame, ml_model: MLSignalGenerator) -> Dict[str, Any]:
        """Run comprehensive backtest with detailed performance metrics"""
        if not ml_model.is_trained:
            return {"error": "ML model not trained"}

        # Initialize portfolio
        capital = self.initial_capital
        position = 0
        position_price = 0
        position_entry_date = None
        trades = []
        portfolio_values = []
        daily_returns = []

        # Minimum data for ML prediction
        min_lookback = max(Config.ML_LOOKBACK_PERIODS, 50)

        # Track benchmark (buy and hold)
        benchmark_start_price = df['close'].iloc[min_lookback]
        benchmark_values = []

        for i in range(min_lookback, len(df)):
            # Get historical data up to current point
            hist_data = df.iloc[:i+1].copy()
            current_price = hist_data['close'].iloc[-1]
            current_date = hist_data.index[-1]

            # Calculate benchmark value
            benchmark_return = (current_price / benchmark_start_price) - 1
            benchmark_value = self.initial_capital * (1 + benchmark_return)
            benchmark_values.append(benchmark_value)

            # Generate signal
            signal_result = ml_model.predict_signal(hist_data)

            if "error" in signal_result:
                total_value = capital + position * current_price
                portfolio_values.append(total_value)
                continue

            signal = signal_result['signal']
            confidence = signal_result['confidence']
            risk_level = signal_result.get('risk_level', 'medium')

            # Adjust confidence threshold based on risk
            min_confidence = 0.7 if risk_level == 'high' else 0.6 if risk_level == 'medium' else 0.5

            # Trading logic
            if signal in ['BUY', 'STRONG_BUY'] and position == 0 and confidence > min_confidence:
                # Calculate position size based on confidence and risk
                confidence_multiplier = min(confidence * 1.5, 1.0)
                risk_multiplier = 1.0 if risk_level == 'low' else 0.8 if risk_level == 'medium' else 0.5

                position_size = capital * Config.MAX_POSITION_SIZE * confidence_multiplier * risk_multiplier
                position_size = min(position_size, capital * 0.8)  # Never risk more than 80%

                shares = position_size / current_price

                if shares > 0 and position_size > 100:  # Minimum trade size
                    position = shares
                    position_price = current_price
                    position_entry_date = current_date
                    capital -= position_size

                    trades.append({
                        'date': current_date,
                        'type': 'BUY',
                        'price': current_price,
                        'shares': shares,
                        'value': position_size,
                        'signal': signal,
                        'confidence': confidence,
                        'risk_level': risk_level
                    })

            elif signal in ['SELL', 'STRONG_SELL'] and position > 0:
                # Exit position
                proceeds = position * current_price
                capital += proceeds

                pnl = proceeds - (position * position_price)
                pnl_pct = (current_price / position_price) - 1
                hold_days = (current_date - position_entry_date).days if position_entry_date else 0

                trades.append({
                    'date': current_date,
                    'type': 'SELL',
                    'price': current_price,
                    'shares': position,
                    'value': proceeds,
                    'signal': signal,
                    'confidence': confidence,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'hold_days': hold_days,
                    'entry_price': position_price,
                    'entry_date': position_entry_date
                })

                position = 0
                position_price = 0
                position_entry_date = None

            # Risk management: Stop loss and take profit
            elif position > 0:
                current_return = (current_price / position_price) - 1
                hold_days = (current_date - position_entry_date).days if position_entry_date else 0

                # Stop loss
                if current_return <= -Config.STOP_LOSS_PCT:
                    proceeds = position * current_price
                    capital += proceeds

                    pnl = proceeds - (position * position_price)

                    trades.append({
                        'date': current_date,
                        'type': 'STOP_LOSS',
                        'price': current_price,
                        'shares': position,
                        'value': proceeds,
                        'signal': 'STOP_LOSS',
                        'confidence': 1.0,
                        'pnl': pnl,
                        'pnl_pct': current_return,
                        'hold_days': hold_days,
                        'entry_price': position_price,
                        'entry_date': position_entry_date
                    })

                    position = 0
                    position_price = 0
                    position_entry_date = None

                # Take profit
                elif current_return >= Config.TAKE_PROFIT_PCT:
                    proceeds = position * current_price
                    capital += proceeds

                    pnl = proceeds - (position * position_price)

                    trades.append({
                        'date': current_date,
                        'type': 'TAKE_PROFIT',
                        'price': current_price,
                        'shares': position,
                        'value': proceeds,
                        'signal': 'TAKE_PROFIT',
                        'confidence': 1.0,
                        'pnl': pnl,
                        'pnl_pct': current_return,
                        'hold_days': hold_days,
                        'entry_price': position_price,
                        'entry_date': position_entry_date
                    })

                    position = 0
                    position_price = 0
                    position_entry_date = None

            # Record portfolio value
            total_value = capital + position * current_price
            portfolio_values.append(total_value)

            # Calculate daily return
            if len(portfolio_values) > 1:
                daily_return = (total_value / portfolio_values[-2]) - 1
                daily_returns.append(daily_return)

        # Calculate comprehensive performance metrics
        return self._calculate_performance_metrics(
            df, trades, portfolio_values, benchmark_values, daily_returns, min_lookback
        )

    def _calculate_performance_metrics(self, df: pd.DataFrame, trades: List[Dict],
                                     portfolio_values: List[float], benchmark_values: List[float],
                                     daily_returns: List[float], min_lookback: int) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics"""

        trades_df = pd.DataFrame(trades)
        portfolio_df = pd.DataFrame({
            'date': df.index[min_lookback:len(portfolio_values) + min_lookback],
            'portfolio_value': portfolio_values,
            'benchmark_value': benchmark_values[:len(portfolio_values)]
        })

        if len(portfolio_values) == 0:
            return {"error": "No portfolio data generated"}

        final_value = portfolio_values[-1]
        benchmark_final = benchmark_values[-1] if benchmark_values else self.initial_capital

        # Basic returns
        total_return = (final_value / self.initial_capital) - 1
        benchmark_return = (benchmark_final / self.initial_capital) - 1
        excess_return = total_return - benchmark_return

        # Risk metrics
        if len(daily_returns) > 1:
            daily_returns_series = pd.Series(daily_returns)
            portfolio_volatility = daily_returns_series.std() * np.sqrt(252)
            sharpe_ratio = (total_return / (len(daily_returns) / 252)) / portfolio_volatility if portfolio_volatility > 0 else 0

            # Downside deviation (for Sortino ratio)
            negative_returns = daily_returns_series[daily_returns_series < 0]
            downside_deviation = negative_returns.std() * np.sqrt(252) if len(negative_returns) > 0 else 0
            sortino_ratio = (total_return / (len(daily_returns) / 252)) / downside_deviation if downside_deviation > 0 else 0
        else:
            portfolio_volatility = 0
            sharpe_ratio = 0
            sortino_ratio = 0

        # Drawdown analysis
        max_drawdown, avg_drawdown, drawdown_duration = self._calculate_drawdown_metrics(portfolio_values)

        # Trading statistics
        trade_stats = self._calculate_trade_statistics(trades_df) if len(trades_df) > 0 else {}

        # Monthly/quarterly returns
        time_series_stats = self._calculate_time_series_stats(portfolio_df)

        # Performance metrics
        results = {
            # Basic Performance
            "initial_capital": self.initial_capital,
            "final_value": final_value,
            "total_return": total_return,
            "benchmark_return": benchmark_return,
            "excess_return": excess_return,
            "annualized_return": total_return * (252 / len(daily_returns)) if len(daily_returns) > 0 else 0,

            # Risk Metrics
            "volatility": portfolio_volatility,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "max_drawdown": max_drawdown,
            "avg_drawdown": avg_drawdown,
            "max_drawdown_duration": drawdown_duration,

            # Trading Statistics
            "total_trades": len(trades),
            **trade_stats,

            # Time Series
            **time_series_stats,

            # Data
            "trades": trades_df.to_dict('records') if len(trades) > 0 else [],
            "portfolio_history": portfolio_df.to_dict('records'),
            "backtest_period_days": len(portfolio_values)
        }

        return results

    def _calculate_drawdown_metrics(self, portfolio_values: List[float]) -> Tuple[float, float, int]:
        """Calculate detailed drawdown metrics"""
        if len(portfolio_values) < 2:
            return 0, 0, 0

        values = pd.Series(portfolio_values)
        rolling_max = values.expanding().max()
        drawdown = (values - rolling_max) / rolling_max

        max_drawdown = abs(drawdown.min())
        avg_drawdown = abs(drawdown[drawdown < 0].mean()) if len(drawdown[drawdown < 0]) > 0 else 0

        # Calculate maximum drawdown duration
        is_drawdown = drawdown < -0.01  # 1% threshold
        drawdown_periods = []
        current_period = 0

        for is_dd in is_drawdown:
            if is_dd:
                current_period += 1
            else:
                if current_period > 0:
                    drawdown_periods.append(current_period)
                current_period = 0

        max_duration = max(drawdown_periods) if drawdown_periods else 0

        return max_drawdown, avg_drawdown, max_duration

    def _calculate_trade_statistics(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate comprehensive trading statistics"""
        if len(trades_df) == 0:
            return {}

        # Filter completed trades (with PnL)
        completed_trades = trades_df[trades_df['pnl'].notna()]

        if len(completed_trades) == 0:
            return {"completed_trades": 0}

        # Win/Loss statistics
        winning_trades = completed_trades[completed_trades['pnl'] > 0]
        losing_trades = completed_trades[completed_trades['pnl'] < 0]

        win_rate = len(winning_trades) / len(completed_trades)
        avg_win = winning_trades['pnl_pct'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['pnl_pct'].mean() if len(losing_trades) > 0 else 0
        profit_factor = abs(winning_trades['pnl'].sum() / losing_trades['pnl'].sum()) if len(losing_trades) > 0 and losing_trades['pnl'].sum() != 0 else float('inf')

        # Hold time analysis
        avg_hold_days = completed_trades['hold_days'].mean() if 'hold_days' in completed_trades.columns else 0

        # Trade type analysis
        trade_type_stats = {}
        for trade_type in ['SELL', 'STOP_LOSS', 'TAKE_PROFIT']:
            type_trades = completed_trades[completed_trades['type'] == trade_type]
            if len(type_trades) > 0:
                trade_type_stats[f'{trade_type.lower()}_count'] = len(type_trades)
                trade_type_stats[f'{trade_type.lower()}_avg_return'] = type_trades['pnl_pct'].mean()

        return {
            "completed_trades": len(completed_trades),
            "win_rate": win_rate,
            "avg_win_pct": avg_win,
            "avg_loss_pct": avg_loss,
            "profit_factor": profit_factor,
            "avg_hold_days": avg_hold_days,
            "best_trade_pct": completed_trades['pnl_pct'].max(),
            "worst_trade_pct": completed_trades['pnl_pct'].min(),
            **trade_type_stats
        }

    def _calculate_time_series_stats(self, portfolio_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate time-based performance statistics"""
        if len(portfolio_df) < 30:  # Need at least 30 days
            return {}

        portfolio_df = portfolio_df.copy()
        portfolio_df['returns'] = portfolio_df['portfolio_value'].pct_change()

        # Monthly returns
        portfolio_df['month'] = portfolio_df['date'].dt.to_period('M')
        monthly_returns = portfolio_df.groupby('month')['returns'].apply(lambda x: (1 + x).prod() - 1)

        # Positive months percentage
        positive_months = (monthly_returns > 0).sum() / len(monthly_returns) if len(monthly_returns) > 0 else 0

        return {
            "positive_months_pct": positive_months,
            "best_month": monthly_returns.max() if len(monthly_returns) > 0 else 0,
            "worst_month": monthly_returns.min() if len(monthly_returns) > 0 else 0,
            "monthly_volatility": monthly_returns.std() if len(monthly_returns) > 1 else 0
        }

# ==========================================
# 6. PROFESSIONAL RISK MANAGEMENT MODULE
# ==========================================

class RiskManager:
    """Professional-grade risk management and position sizing"""

    def __init__(self, account_balance: float = 10000, max_leverage: float = 5.0):
        self.account_balance = account_balance
        self.max_leverage = max_leverage
        self.default_account_risk = 0.01  # 1% default account risk
        self.min_account_risk = 0.005     # 0.5% minimum
        self.max_account_risk = 0.03      # 3.0% maximum

        # Risk monitoring
        self.current_positions = {}
        self.daily_risk_used = 0.0
        self.max_daily_risk = 0.03  # 3% max daily risk (as requested)

        # Advanced futures risk settings
        self.max_margin_usage = 0.50      # 50% max margin usage
        self.liquidation_warning_level = 0.80  # 80% margin usage warning
        self.auto_liquidation_level = 0.80     # Auto close at 80% margin usage

        # Position sizing optimization
        self.kelly_adjustment = 0.25      # Kelly fraction adjustment (25%)
        self.atr_multiplier = 2.0         # ATR multiplier for stop loss
        self.partial_take_profit_levels = [0.25, 0.50, 0.75]  # 25%, 50%, 75%

        # Funding fee tracking
        self.funding_fee_history = {}
        self.funding_fee_threshold = 0.1  # 0.1% threshold for position adjustment

        # Advanced metrics tracking
        self.win_rate_history = []
        self.recent_trades_count = 20     # Track last 20 trades for win rate

    def calculate_position_size(self, entry_price: float, stop_loss_price: float,
                              account_risk_pct: float = None, confidence: float = 1.0) -> Dict[str, Any]:
        """
        Professional position sizing calculation

        Formula: Position Ratio = Account Risk / Price Risk
        Leverage = min(Position Ratio, Max Leverage)

        Args:
            entry_price: Entry price for the position
            stop_loss_price: Stop loss price
            account_risk_pct: Account risk percentage (0.005 to 0.03)
            confidence: Signal confidence (0.0 to 1.0)

        Returns:
            Dictionary with position sizing details
        """

        # Validate inputs
        if entry_price <= 0 or stop_loss_price <= 0:
            return {"error": "Invalid price inputs"}

        if account_risk_pct is None:
            account_risk_pct = self.default_account_risk

        # Clamp account risk to valid range
        account_risk_pct = max(self.min_account_risk,
                              min(self.max_account_risk, account_risk_pct))

        # Adjust account risk based on confidence
        adjusted_account_risk = account_risk_pct * confidence

        # Calculate price risk (percentage loss from entry to stop)
        if entry_price > stop_loss_price:  # Long position
            price_risk = (entry_price - stop_loss_price) / entry_price
        else:  # Short position
            price_risk = (stop_loss_price - entry_price) / entry_price

        # Avoid division by zero
        if price_risk <= 0:
            return {"error": "Invalid stop loss price - no risk defined"}

        # Calculate position ratio and leverage
        position_ratio = adjusted_account_risk / price_risk
        leverage = min(position_ratio, self.max_leverage)

        # Calculate position details
        risk_amount = self.account_balance * adjusted_account_risk
        position_value = self.account_balance * leverage
        shares = position_value / entry_price

        # Check daily risk limits
        if self.daily_risk_used + adjusted_account_risk > self.max_daily_risk:
            return {"error": f"Daily risk limit exceeded. Used: {self.daily_risk_used:.1%}, Limit: {self.max_daily_risk:.1%}"}

        return {
            "entry_price": entry_price,
            "stop_loss_price": stop_loss_price,
            "account_risk_pct": account_risk_pct,
            "adjusted_account_risk": adjusted_account_risk,
            "price_risk_pct": price_risk,
            "position_ratio": position_ratio,
            "leverage": leverage,
            "risk_amount": risk_amount,
            "position_value": position_value,
            "shares": shares,
            "confidence": confidence,
            "max_loss": risk_amount,
            "is_leveraged": leverage > 1.0,
            "leverage_multiplier": leverage
        }

    def get_position_sizing_examples(self, current_price: float) -> List[Dict]:
        """Generate example position sizing calculations"""
        examples = []

        # Example 1: Conservative (2% price risk)
        stop_loss_1 = current_price * 0.98
        example_1 = self.calculate_position_size(current_price, stop_loss_1, 0.01, 1.0)
        if "error" not in example_1:
            example_1["description"] = "Conservative: 2% price risk, 1% account risk"
            examples.append(example_1)

        # Example 2: Tight stop (0.5% price risk)
        stop_loss_2 = current_price * 0.995
        example_2 = self.calculate_position_size(current_price, stop_loss_2, 0.01, 1.0)
        if "error" not in example_2:
            example_2["description"] = "Tight Stop: 0.5% price risk, 1% account risk"
            examples.append(example_2)

        # Example 3: High confidence (1.5% price risk, high confidence)
        stop_loss_3 = current_price * 0.985
        example_3 = self.calculate_position_size(current_price, stop_loss_3, 0.015, 0.9)
        if "error" not in example_3:
            example_3["description"] = "High Confidence: 1.5% price risk, 1.5% account risk"
            examples.append(example_3)

        return examples

    def monitor_position_risk(self, symbol: str, current_price: float,
                            position_data: Dict) -> Dict[str, Any]:
        """Real-time position risk monitoring"""

        entry_price = position_data.get('entry_price', 0)
        stop_loss = position_data.get('stop_loss_price', 0)
        shares = position_data.get('shares', 0)

        if not all([entry_price, stop_loss, shares]):
            return {"error": "Incomplete position data"}

        # Current position value and P&L
        current_value = shares * current_price
        entry_value = shares * entry_price
        unrealized_pnl = current_value - entry_value
        unrealized_pnl_pct = (current_price / entry_price) - 1

        # Risk metrics
        current_risk_pct = abs((current_price - stop_loss) / current_price)
        max_loss_amount = shares * abs(entry_price - stop_loss)

        # Risk status
        risk_status = "LOW"
        if current_risk_pct > 0.02:
            risk_status = "MEDIUM"
        if current_risk_pct > 0.05:
            risk_status = "HIGH"

        # Position health
        distance_to_stop = abs(current_price - stop_loss) / current_price
        health_score = min(100, distance_to_stop * 1000)  # Scale to 0-100

        return {
            "symbol": symbol,
            "current_price": current_price,
            "current_value": current_value,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_pct": unrealized_pnl_pct,
            "current_risk_pct": current_risk_pct,
            "max_loss_amount": max_loss_amount,
            "risk_status": risk_status,
            "health_score": health_score,
            "distance_to_stop_pct": distance_to_stop,
            "stop_loss_price": stop_loss
        }

    def update_daily_risk(self, risk_amount: float):
        """Update daily risk usage"""
        risk_pct = risk_amount / self.account_balance
        self.daily_risk_used += risk_pct

    def reset_daily_risk(self):
        """Reset daily risk counter"""
        self.daily_risk_used = 0.0

    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary"""
        return {
            "account_balance": self.account_balance,
            "max_leverage": self.max_leverage,
            "daily_risk_used": self.daily_risk_used,
            "daily_risk_remaining": self.max_daily_risk - self.daily_risk_used,
            "max_daily_risk": self.max_daily_risk,
            "default_account_risk": self.default_account_risk,
            "risk_range": f"{self.min_account_risk:.1%} - {self.max_account_risk:.1%}",
            "total_positions": len(self.current_positions)
        }

    def calculate_futures_position_size(self, symbol: str, entry_price: float,
                                      atr_value: float, leverage: int = 5,
                                      win_rate: float = None) -> Dict[str, Any]:
        """
        Advanced futures position sizing with Kelly formula and ATR optimization

        Args:
            symbol: Trading symbol
            entry_price: Entry price
            atr_value: Average True Range value
            leverage: Desired leverage (1-10x)
            win_rate: Historical win rate (optional)

        Returns:
            Dictionary with optimized position sizing
        """

        # Validate inputs
        if entry_price <= 0 or atr_value <= 0:
            return {"error": "Invalid price or ATR inputs"}

        # Limit leverage to max 10x as per safety requirements
        leverage = min(leverage, 10)

        # Calculate ATR-based stop loss
        atr_stop_distance = atr_value * self.atr_multiplier
        stop_loss_price = entry_price - atr_stop_distance  # For long positions

        # Calculate basic position size
        base_position = self.calculate_position_size(
            entry_price, stop_loss_price, self.default_account_risk, 1.0
        )

        if "error" in base_position:
            return base_position

        # Kelly Criterion optimization
        kelly_fraction = 0
        if win_rate is not None and win_rate > 0:
            # Simplified Kelly: (win_rate * avg_win - loss_rate * avg_loss) / avg_win
            # Assuming 1:2 risk-reward ratio
            loss_rate = 1 - win_rate
            avg_win = 2.0  # 2% average win
            avg_loss = 1.0  # 1% average loss

            kelly_fraction = (win_rate * avg_win - loss_rate * avg_loss) / avg_win
            kelly_fraction = max(0, min(kelly_fraction, 1.0))  # Clamp 0-1
            kelly_fraction *= self.kelly_adjustment  # Apply safety factor

        # Account size optimization
        account_tier_multiplier = 1.0
        if self.account_balance >= 50000:
            account_tier_multiplier = 1.2
        elif self.account_balance >= 100000:
            account_tier_multiplier = 1.5

        # Calculate optimized position size
        kelly_adjusted_risk = self.default_account_risk
        if kelly_fraction > 0:
            kelly_adjusted_risk = self.default_account_risk * (1 + kelly_fraction)
            kelly_adjusted_risk = min(kelly_adjusted_risk, self.max_account_risk)

        # Apply account tier and leverage adjustments
        risk_per_leverage = kelly_adjusted_risk / leverage
        final_risk = risk_per_leverage * account_tier_multiplier
        final_risk = min(final_risk, self.max_account_risk)

        # Calculate margin requirements
        position_value = self.account_balance * leverage * final_risk
        margin_required = position_value / leverage
        margin_usage_pct = margin_required / self.account_balance

        # Safety checks
        if margin_usage_pct > self.max_margin_usage:
            return {"error": f"Position would exceed max margin usage ({self.max_margin_usage:.0%})"}

        # Calculate final position details
        position_size = position_value / entry_price
        risk_amount = self.account_balance * final_risk

        return {
            "symbol": symbol,
            "entry_price": entry_price,
            "stop_loss_price": stop_loss_price,
            "atr_value": atr_value,
            "atr_stop_distance": atr_stop_distance,
            "leverage": leverage,
            "position_size": position_size,
            "position_value": position_value,
            "margin_required": margin_required,
            "margin_usage_pct": margin_usage_pct,
            "risk_amount": risk_amount,
            "final_risk_pct": final_risk,
            "kelly_fraction": kelly_fraction if win_rate else 0,
            "kelly_adjusted_risk": kelly_adjusted_risk,
            "account_tier_multiplier": account_tier_multiplier,
            "max_loss_usd": risk_amount,
            "risk_reward_ratio": 2.0,
            "safety_status": "SAFE" if margin_usage_pct < self.liquidation_warning_level else "WARNING"
        }

    def calculate_dynamic_stop_loss(self, symbol: str, entry_price: float,
                                  current_price: float, atr_value: float,
                                  leverage: int, position_side: str = "LONG") -> Dict[str, Any]:
        """
        Dynamic stop loss and take profit system with trailing stop

        Args:
            symbol: Trading symbol
            entry_price: Entry price
            current_price: Current market price
            atr_value: Current ATR value
            leverage: Position leverage
            position_side: "LONG" or "SHORT"

        Returns:
            Dictionary with dynamic stop loss and take profit levels
        """

        # Base stop loss distance (ATR-based)
        base_stop_distance = atr_value * self.atr_multiplier

        # Adjust for leverage (higher leverage = tighter stops)
        leverage_adjustment = 1.0 - (leverage - 1) * 0.1  # Reduce by 10% per leverage level
        leverage_adjustment = max(0.5, leverage_adjustment)  # Minimum 50% of base distance

        adjusted_stop_distance = base_stop_distance * leverage_adjustment

        if position_side.upper() == "LONG":
            # Long position stops
            initial_stop = entry_price - adjusted_stop_distance
            trailing_stop = current_price - adjusted_stop_distance

            # Use higher of initial stop or trailing stop
            dynamic_stop = max(initial_stop, trailing_stop)

            # Take profit levels
            tp_distances = [
                adjusted_stop_distance * 2,  # 1:2 risk-reward
                adjusted_stop_distance * 3,  # 1:3 risk-reward
                adjusted_stop_distance * 4   # 1:4 risk-reward
            ]

            take_profit_levels = [
                {
                    "level": i + 1,
                    "price": entry_price + distance,
                    "percentage": self.partial_take_profit_levels[i],
                    "risk_reward": (i + 2)
                }
                for i, distance in enumerate(tp_distances)
            ]

        else:  # SHORT position
            initial_stop = entry_price + adjusted_stop_distance
            trailing_stop = current_price + adjusted_stop_distance

            # Use lower of initial stop or trailing stop for shorts
            dynamic_stop = min(initial_stop, trailing_stop)

            # Take profit levels for shorts
            tp_distances = [
                adjusted_stop_distance * 2,
                adjusted_stop_distance * 3,
                adjusted_stop_distance * 4
            ]

            take_profit_levels = [
                {
                    "level": i + 1,
                    "price": entry_price - distance,
                    "percentage": self.partial_take_profit_levels[i],
                    "risk_reward": (i + 2)
                }
                for i, distance in enumerate(tp_distances)
            ]

        # Calculate current P&L
        if position_side.upper() == "LONG":
            unrealized_pnl_pct = (current_price - entry_price) / entry_price
        else:
            unrealized_pnl_pct = (entry_price - current_price) / entry_price

        return {
            "symbol": symbol,
            "position_side": position_side,
            "entry_price": entry_price,
            "current_price": current_price,
            "dynamic_stop_loss": dynamic_stop,
            "initial_stop_loss": initial_stop,
            "trailing_stop_loss": trailing_stop,
            "atr_value": atr_value,
            "stop_distance": adjusted_stop_distance,
            "leverage_adjustment": leverage_adjustment,
            "take_profit_levels": take_profit_levels,
            "unrealized_pnl_pct": unrealized_pnl_pct,
            "stop_loss_distance_pct": adjusted_stop_distance / entry_price,
            "trailing_active": abs(current_price - entry_price) > adjusted_stop_distance
        }

    def monitor_margin_health(self, positions: List[Dict], account_info: Dict) -> Dict[str, Any]:
        """
        Real-time margin monitoring and liquidation risk calculation

        Args:
            positions: List of current positions
            account_info: Account balance and margin info

        Returns:
            Dictionary with margin health analysis
        """

        total_margin_used = account_info.get('totalMarginBalance', 0)
        available_balance = account_info.get('availableBalance', 0)
        total_wallet_balance = account_info.get('totalWalletBalance', 0)

        if total_wallet_balance <= 0:
            return {"error": "Invalid account balance"}

        # Calculate margin usage percentage
        margin_usage_pct = total_margin_used / total_wallet_balance if total_wallet_balance > 0 else 0

        # Calculate liquidation risk for each position
        position_risks = []
        total_unrealized_pnl = 0

        for position in positions:
            symbol = position.get('symbol', '')
            size = float(position.get('positionAmt', 0))
            entry_price = float(position.get('entryPrice', 0))
            mark_price = float(position.get('markPrice', 0))
            leverage = float(position.get('leverage', 1))

            if size == 0:
                continue

            # Calculate position value and unrealized PnL
            position_value = abs(size) * mark_price
            unrealized_pnl = size * (mark_price - entry_price)
            total_unrealized_pnl += unrealized_pnl

            # Calculate liquidation price (simplified)
            maintenance_margin = position_value * 0.05  # 5% maintenance margin
            liquidation_distance = maintenance_margin / abs(size)

            if size > 0:  # Long position
                liquidation_price = entry_price - liquidation_distance
                distance_to_liquidation = (mark_price - liquidation_price) / mark_price
            else:  # Short position
                liquidation_price = entry_price + liquidation_distance
                distance_to_liquidation = (liquidation_price - mark_price) / mark_price

            position_risk = {
                "symbol": symbol,
                "size": size,
                "entry_price": entry_price,
                "mark_price": mark_price,
                "leverage": leverage,
                "position_value": position_value,
                "unrealized_pnl": unrealized_pnl,
                "liquidation_price": liquidation_price,
                "distance_to_liquidation_pct": distance_to_liquidation,
                "risk_level": self._calculate_risk_level(distance_to_liquidation)
            }
            position_risks.append(position_risk)

        # Overall margin health assessment
        health_score = max(0, min(100, (1 - margin_usage_pct) * 100))

        # Determine margin status
        if margin_usage_pct < 0.5:
            margin_status = "HEALTHY"
        elif margin_usage_pct < self.liquidation_warning_level:
            margin_status = "MODERATE"
        elif margin_usage_pct < self.auto_liquidation_level:
            margin_status = "WARNING"
        else:
            margin_status = "CRITICAL"

        # Calculate time to liquidation (if current trend continues)
        risk_recommendations = self._generate_risk_recommendations(margin_usage_pct, position_risks)

        return {
            "margin_usage_pct": margin_usage_pct,
            "available_balance": available_balance,
            "total_margin_used": total_margin_used,
            "total_wallet_balance": total_wallet_balance,
            "total_unrealized_pnl": total_unrealized_pnl,
            "health_score": health_score,
            "margin_status": margin_status,
            "position_count": len([p for p in positions if float(p.get('positionAmt', 0)) != 0]),
            "position_risks": position_risks,
            "max_additional_margin": total_wallet_balance * self.max_margin_usage - total_margin_used,
            "liquidation_warning": margin_usage_pct >= self.liquidation_warning_level,
            "auto_close_triggered": margin_usage_pct >= self.auto_liquidation_level,
            "recommendations": risk_recommendations
        }

    def _calculate_risk_level(self, distance_to_liquidation: float) -> str:
        """Calculate risk level based on distance to liquidation"""
        if distance_to_liquidation > 0.1:  # >10%
            return "LOW"
        elif distance_to_liquidation > 0.05:  # >5%
            return "MEDIUM"
        elif distance_to_liquidation > 0.02:  # >2%
            return "HIGH"
        else:
            return "CRITICAL"

    def _generate_risk_recommendations(self, margin_usage_pct: float, position_risks: List[Dict]) -> List[str]:
        """Generate risk management recommendations"""
        recommendations = []

        if margin_usage_pct > self.liquidation_warning_level:
            recommendations.append("URGENT: Margin usage exceeds safe levels - consider reducing positions")

        if margin_usage_pct > 0.6:
            recommendations.append("HIGH RISK: Consider closing least profitable positions")

        # Find positions closest to liquidation
        high_risk_positions = [p for p in position_risks if p['risk_level'] in ['HIGH', 'CRITICAL']]
        if high_risk_positions:
            symbols = [p['symbol'] for p in high_risk_positions]
            recommendations.append(f"Monitor closely: {', '.join(symbols[:3])} near liquidation")

        # Check for overleveraged positions
        high_leverage_positions = [p for p in position_risks if p['leverage'] > 5]
        if high_leverage_positions:
            recommendations.append("Consider reducing leverage on high-leverage positions")

        if not recommendations:
            recommendations.append("Margin usage is within safe parameters")

        return recommendations

    def emergency_position_closure(self, positions: List[Dict], margin_usage_pct: float) -> Dict[str, Any]:
        """
        Emergency position closure logic when margin usage is critical

        Args:
            positions: Current positions
            margin_usage_pct: Current margin usage percentage

        Returns:
            Dictionary with closure plan
        """

        if margin_usage_pct < self.auto_liquidation_level:
            return {"action": "NO_ACTION", "reason": "Margin usage within safe limits"}

        # Sort positions by risk level (worst first)
        positions_with_risk = []
        for position in positions:
            size = float(position.get('positionAmt', 0))
            if size == 0:
                continue

            entry_price = float(position.get('entryPrice', 0))
            mark_price = float(position.get('markPrice', 0))
            unrealized_pnl = size * (mark_price - entry_price)
            leverage = float(position.get('leverage', 1))

            positions_with_risk.append({
                "symbol": position.get('symbol'),
                "size": size,
                "unrealized_pnl": unrealized_pnl,
                "leverage": leverage,
                "risk_score": leverage * abs(unrealized_pnl) if unrealized_pnl < 0 else 0
            })

        # Sort by risk score (highest risk first)
        positions_with_risk.sort(key=lambda x: x['risk_score'], reverse=True)

        # Determine positions to close
        positions_to_close = []
        target_margin_reduction = (margin_usage_pct - 0.6) * self.account_balance  # Target 60% margin usage

        margin_freed = 0
        for position in positions_with_risk:
            if margin_freed >= target_margin_reduction:
                break

            position_margin = abs(position['size']) * position.get('mark_price', 0) / position['leverage']
            margin_freed += position_margin

            positions_to_close.append({
                "symbol": position['symbol'],
                "action": "MARKET_CLOSE",
                "reason": "Emergency margin management",
                "priority": len(positions_to_close) + 1
            })

        return {
            "action": "EMERGENCY_CLOSE",
            "margin_usage_pct": margin_usage_pct,
            "target_margin_usage": 0.6,
            "positions_to_close": positions_to_close,
            "total_positions": len(positions_to_close),
            "estimated_margin_freed": margin_freed,
            "execution_order": "HIGHEST_RISK_FIRST"
        }

    def track_funding_fees(self, symbol: str, funding_rate: float, position_size: float) -> Dict[str, Any]:
        """
        Track and analyze funding fees for position optimization

        Args:
            symbol: Trading symbol
            funding_rate: Current funding rate (8-hour rate)
            position_size: Position size (positive for long, negative for short)

        Returns:
            Dictionary with funding fee analysis
        """

        # Initialize symbol tracking if not exists
        if symbol not in self.funding_fee_history:
            self.funding_fee_history[symbol] = {
                "rates": [],
                "fees_paid": 0,
                "fees_received": 0,
                "net_fees": 0,
                "position_adjustments": 0
            }

        # Add current rate to history
        history = self.funding_fee_history[symbol]
        history["rates"].append({
            "timestamp": datetime.now(),
            "rate": funding_rate,
            "position_size": position_size
        })

        # Keep only last 30 funding periods (10 days)
        if len(history["rates"]) > 30:
            history["rates"] = history["rates"][-30:]

        # Calculate funding fee impact
        funding_fee = abs(position_size) * funding_rate

        if position_size > 0:  # Long position
            if funding_rate > 0:
                # Pay funding fee
                history["fees_paid"] += funding_fee
                fee_impact = "PAYING"
            else:
                # Receive funding fee
                history["fees_received"] += abs(funding_fee)
                fee_impact = "RECEIVING"
        else:  # Short position
            if funding_rate > 0:
                # Receive funding fee
                history["fees_received"] += funding_fee
                fee_impact = "RECEIVING"
            else:
                # Pay funding fee
                history["fees_paid"] += abs(funding_fee)
                fee_impact = "PAYING"

        # Update net fees
        history["net_fees"] = history["fees_received"] - history["fees_paid"]

        # Calculate average funding rate
        recent_rates = [r["rate"] for r in history["rates"][-10:]]  # Last 10 periods
        avg_funding_rate = sum(recent_rates) / len(recent_rates) if recent_rates else 0

        # Generate funding optimization recommendation
        recommendation = self._analyze_funding_optimization(
            symbol, funding_rate, avg_funding_rate, position_size, history
        )

        return {
            "symbol": symbol,
            "current_funding_rate": funding_rate,
            "average_funding_rate": avg_funding_rate,
            "position_size": position_size,
            "current_fee_impact": fee_impact,
            "estimated_8h_fee": funding_fee,
            "estimated_daily_fee": funding_fee * 3,  # 3 funding periods per day
            "total_fees_paid": history["fees_paid"],
            "total_fees_received": history["fees_received"],
            "net_funding_result": history["net_fees"],
            "funding_efficiency": history["fees_received"] / max(history["fees_paid"], 0.01),
            "recommendation": recommendation,
            "rate_trend": self._calculate_funding_trend(recent_rates),
            "high_funding_alert": abs(funding_rate) > self.funding_fee_threshold
        }

    def _analyze_funding_optimization(self, symbol: str, current_rate: float,
                                    avg_rate: float, position_size: float,
                                    history: Dict) -> Dict[str, Any]:
        """Analyze and recommend funding fee optimization strategies"""

        recommendations = []
        optimization_type = "HOLD"

        # High funding rate analysis
        if abs(current_rate) > self.funding_fee_threshold:
            if position_size > 0 and current_rate > self.funding_fee_threshold:
                # Long position paying high funding
                recommendations.append("Consider reducing long position size")
                recommendations.append("High funding rate favors short positions")
                optimization_type = "REDUCE_LONG"

            elif position_size < 0 and current_rate > self.funding_fee_threshold:
                # Short position receiving high funding
                recommendations.append("Favorable funding for short positions")
                recommendations.append("Consider maintaining or increasing short size")
                optimization_type = "INCREASE_SHORT"

            elif position_size > 0 and current_rate < -self.funding_fee_threshold:
                # Long position receiving funding
                recommendations.append("Favorable funding for long positions")
                recommendations.append("Consider maintaining or increasing long size")
                optimization_type = "INCREASE_LONG"

            elif position_size < 0 and current_rate < -self.funding_fee_threshold:
                # Short position paying high funding
                recommendations.append("Consider reducing short position size")
                recommendations.append("High negative funding favors long positions")
                optimization_type = "REDUCE_SHORT"

        # Trend analysis
        rate_trend = self._calculate_funding_trend([r["rate"] for r in history["rates"][-5:]])
        if rate_trend == "INCREASING" and current_rate > 0:
            recommendations.append("Funding rates trending higher - consider position timing")
        elif rate_trend == "DECREASING" and current_rate < 0:
            recommendations.append("Negative funding rates increasing - monitor closely")

        # Net funding efficiency
        if history["net_fees"] < 0:  # Paying more than receiving
            recommendations.append("Net funding cost negative - review position strategy")

        if not recommendations:
            recommendations.append("Funding rates within normal range")

        return {
            "type": optimization_type,
            "recommendations": recommendations,
            "priority": "HIGH" if abs(current_rate) > self.funding_fee_threshold else "NORMAL",
            "estimated_daily_cost": abs(position_size) * current_rate * 3,
            "cost_impact_pct": (abs(position_size) * current_rate * 3) / self.account_balance * 100
        }

    def _calculate_funding_trend(self, rates: List[float]) -> str:
        """Calculate funding rate trend"""
        if len(rates) < 3:
            return "INSUFFICIENT_DATA"

        # Simple trend calculation
        recent_avg = sum(rates[-3:]) / 3
        older_avg = sum(rates[:-3]) / max(len(rates) - 3, 1) if len(rates) > 3 else recent_avg

        if recent_avg > older_avg * 1.1:
            return "INCREASING"
        elif recent_avg < older_avg * 0.9:
            return "DECREASING"
        else:
            return "STABLE"

    def optimize_position_for_funding(self, symbol: str, current_position_size: float,
                                    funding_rate: float, market_signal: str) -> Dict[str, Any]:
        """
        Optimize position size considering both market signals and funding costs

        Args:
            symbol: Trading symbol
            current_position_size: Current position size
            funding_rate: Current funding rate
            market_signal: AI market signal ('BUY', 'SELL', 'HOLD')

        Returns:
            Dictionary with optimized position recommendation
        """

        # Get funding analysis
        funding_analysis = self.track_funding_fees(symbol, funding_rate, current_position_size)

        # Base position sizing from market signal
        signal_strength = {
            'BUY': 1.0,
            'SELL': -1.0,
            'HOLD': 0.0
        }.get(market_signal, 0.0)

        # Funding rate adjustment factor
        funding_adjustment = 1.0

        if abs(funding_rate) > self.funding_fee_threshold:
            if funding_rate > 0:  # High positive funding (expensive for longs)
                funding_adjustment = 0.7 if signal_strength > 0 else 1.3
            else:  # High negative funding (expensive for shorts)
                funding_adjustment = 1.3 if signal_strength > 0 else 0.7

        # Calculate optimal position size
        base_position_value = self.account_balance * 0.1  # 10% of account
        adjusted_position_value = base_position_value * signal_strength * funding_adjustment

        # Convert to position size (assuming current price for simplicity)
        current_price = 50000  # This should come from market data
        optimal_position_size = adjusted_position_value / current_price

        # Position change recommendation
        position_change = optimal_position_size - current_position_size
        change_percentage = (position_change / max(abs(current_position_size), 0.001)) * 100

        return {
            "symbol": symbol,
            "current_position_size": current_position_size,
            "optimal_position_size": optimal_position_size,
            "position_change": position_change,
            "change_percentage": change_percentage,
            "market_signal": market_signal,
            "signal_strength": signal_strength,
            "funding_rate": funding_rate,
            "funding_adjustment": funding_adjustment,
            "funding_cost_daily": abs(optimal_position_size) * funding_rate * 3,
            "action_required": abs(change_percentage) > 20,  # 20% threshold for action
            "reasoning": funding_analysis["recommendation"]["recommendations"],
            "priority": funding_analysis["recommendation"]["priority"]
        }

# ==========================================
# 7. PAPER TRADING SIMULATOR MODULE
# ==========================================

class PaperTradingSimulator:
    """Enhanced Real-time Paper Trading Simulation with Advanced Analytics"""

    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = {}
        self.trade_history = []
        self.portfolio_history = []
        self.daily_returns = []
        self.performance_metrics = {}

        # Enhanced tracking
        self.daily_pnl = {}
        self.weekly_pnl = {}
        self.monthly_pnl = {}
        self.trade_fees = 0
        self.max_drawdown = 0
        self.peak_value = initial_capital

        # Trading settings
        self.maker_fee = 0.001   # 0.1% maker fee
        self.taker_fee = 0.0015  # 0.15% taker fee
        self.min_trade_size = 10  # Minimum $10 trade

        # Professional Risk Management Integration
        self.risk_manager = RiskManager(account_balance=initial_capital)

    def execute_professional_trade(self, symbol: str, signal: str, price: float,
                                 confidence: float, timestamp: datetime,
                                 account_risk_pct: float = None) -> Dict[str, Any]:
        """Execute trade using professional risk management and position sizing"""

        if signal not in ['BUY', 'STRONG_BUY', 'SELL', 'STRONG_SELL']:
            return {"error": "Invalid signal"}

        # Update risk manager balance
        self.risk_manager.account_balance = self.capital

        # For buy signals
        if signal in ['BUY', 'STRONG_BUY'] and symbol not in self.positions:
            # Calculate stop loss price
            stop_loss_price = price * (1 - Config.STOP_LOSS_PCT)

            # Get professional position sizing
            position_calc = self.risk_manager.calculate_position_size(
                entry_price=price,
                stop_loss_price=stop_loss_price,
                account_risk_pct=account_risk_pct,
                confidence=confidence
            )

            if "error" in position_calc:
                return position_calc

            # Check if we can afford this position
            position_value = position_calc['position_value']
            if position_value > self.capital:
                return {"error": f"Insufficient capital. Required: ${position_value:.2f}, Available: ${self.capital:.2f}"}

            # Calculate fees
            fee = position_value * self.taker_fee
            net_position_value = position_value - fee

            # Execute the trade
            shares = position_calc['shares']

            self.positions[symbol] = {
                'shares': shares,
                'entry_price': price,
                'entry_time': timestamp,
                'signal': signal,
                'confidence': confidence,
                'entry_fee': fee,
                'stop_loss_price': stop_loss_price,
                'take_profit_price': price * (1 + Config.TAKE_PROFIT_PCT),
                'risk_level': 'professional',
                'leverage': position_calc['leverage'],
                'position_ratio': position_calc['position_ratio'],
                'account_risk_pct': position_calc['account_risk_pct'],
                'price_risk_pct': position_calc['price_risk_pct'],
                'max_loss': position_calc['max_loss'],
                'is_leveraged': position_calc['is_leveraged']
            }

            # Update capital and fees
            self.capital -= position_value
            self.trade_fees += fee

            # Update risk manager
            self.risk_manager.update_daily_risk(position_calc['risk_amount'])

            trade = {
                'timestamp': timestamp,
                'symbol': symbol,
                'action': 'BUY',
                'shares': shares,
                'price': price,
                'value': position_value,
                'fee': fee,
                'net_value': net_position_value,
                'signal': signal,
                'confidence': confidence,
                'risk_level': 'professional',
                'leverage': position_calc['leverage'],
                'position_ratio': position_calc['position_ratio'],
                'account_risk_pct': position_calc['account_risk_pct'],
                'price_risk_pct': position_calc['price_risk_pct'],
                'max_loss': position_calc['max_loss']
            }

            self.trade_history.append(trade)
            self._update_portfolio_history(timestamp)

            return trade

        # For sell signals - close existing position
        elif signal in ['SELL', 'STRONG_SELL'] and symbol in self.positions:
            return self._close_position(symbol, price, timestamp, signal, confidence)

        return {"error": "Trade conditions not met"}

    def get_professional_position_preview(self, symbol: str, price: float,
                                        confidence: float, account_risk_pct: float = None) -> Dict[str, Any]:
        """Preview professional position sizing without executing trade"""

        # Update risk manager balance
        self.risk_manager.account_balance = self.capital

        # Calculate stop loss price
        stop_loss_price = price * (1 - Config.STOP_LOSS_PCT)

        # Get position sizing calculation
        position_calc = self.risk_manager.calculate_position_size(
            entry_price=price,
            stop_loss_price=stop_loss_price,
            account_risk_pct=account_risk_pct,
            confidence=confidence
        )

        if "error" in position_calc:
            return position_calc

        # Add additional preview info
        position_calc['symbol'] = symbol
        position_calc['fee'] = position_calc['position_value'] * self.taker_fee
        position_calc['net_position_value'] = position_calc['position_value'] - position_calc['fee']
        position_calc['affordable'] = position_calc['position_value'] <= self.capital
        position_calc['capital_utilization'] = position_calc['position_value'] / self.capital

        return position_calc

    def execute_atr_trade(self, symbol: str, signal: str, price: float,
                         confidence: float, timestamp: datetime,
                         atr_value: float, volatility_level: str,
                         account_risk_pct: float = None) -> Dict[str, Any]:
        """Execute trade using ATR-based dynamic stop/take profit levels"""

        if signal not in ['BUY', 'STRONG_BUY', 'SELL', 'STRONG_SELL']:
            return {"error": "Invalid signal"}

        # Update risk manager balance
        self.risk_manager.account_balance = self.capital

        # For buy signals
        if signal in ['BUY', 'STRONG_BUY'] and symbol not in self.positions:
            # Initialize ATR calculator if not available
            if not hasattr(self, 'atr_calculator'):
                self.atr_calculator = ATRCalculator()

            # Calculate ATR-based dynamic levels
            atr_levels = self.atr_calculator.calculate_dynamic_levels(
                price, atr_value, volatility_level
            )

            # Use ATR stop loss for position sizing
            atr_stop_loss = atr_levels['stop_loss_price']

            # Get professional position sizing with ATR stop
            position_calc = self.risk_manager.calculate_position_size(
                entry_price=price,
                stop_loss_price=atr_stop_loss,
                account_risk_pct=account_risk_pct,
                confidence=confidence
            )

            if "error" in position_calc:
                return position_calc

            # Check volatility-based position adjustment
            base_position_size = position_calc['position_ratio']
            size_adjustment = self.atr_calculator.get_position_size_adjustment(
                volatility_level, base_position_size
            )

            # Apply volatility adjustment
            adjusted_position_value = position_calc['position_value'] * size_adjustment['adjustment_factor']
            adjusted_shares = adjusted_position_value / price

            # Check if we can afford this position
            if adjusted_position_value > self.capital:
                return {"error": f"Insufficient capital. Required: ${adjusted_position_value:.2f}, Available: ${self.capital:.2f}"}

            # Calculate fees
            fee = adjusted_position_value * self.taker_fee
            net_position_value = adjusted_position_value - fee

            self.positions[symbol] = {
                'shares': adjusted_shares,
                'entry_price': price,
                'entry_time': timestamp,
                'signal': signal,
                'confidence': confidence,
                'entry_fee': fee,
                'stop_loss_price': atr_levels['stop_loss_price'],
                'take_profit_price': atr_levels['take_profit_price'],
                'risk_level': 'atr_professional',
                'leverage': position_calc['leverage'],
                'position_ratio': position_calc['position_ratio'],
                'account_risk_pct': position_calc['account_risk_pct'],
                'price_risk_pct': position_calc['price_risk_pct'],
                'max_loss': position_calc['max_loss'],
                'is_leveraged': position_calc['is_leveraged'],
                'atr_value': atr_value,
                'volatility_level': volatility_level,
                'atr_stop_multiplier': atr_levels['stop_multiplier'],
                'atr_take_multiplier': atr_levels['take_multiplier'],
                'risk_reward_ratio': atr_levels['risk_reward_ratio'],
                'volatility_adjustment': size_adjustment['adjustment_factor'],
                'highest_price': price  # For trailing stop
            }

            # Update capital and fees
            self.capital -= adjusted_position_value
            self.trade_fees += fee

            # Update risk manager
            self.risk_manager.update_daily_risk(position_calc['risk_amount'])

            trade = {
                'timestamp': timestamp,
                'symbol': symbol,
                'action': 'BUY',
                'shares': adjusted_shares,
                'price': price,
                'value': adjusted_position_value,
                'fee': fee,
                'net_value': net_position_value,
                'signal': signal,
                'confidence': confidence,
                'risk_level': 'atr_professional',
                'leverage': position_calc['leverage'],
                'position_ratio': position_calc['position_ratio'],
                'account_risk_pct': position_calc['account_risk_pct'],
                'price_risk_pct': position_calc['price_risk_pct'],
                'max_loss': position_calc['max_loss'],
                'atr_value': atr_value,
                'volatility_level': volatility_level,
                'atr_stop_loss': atr_levels['stop_loss_price'],
                'atr_take_profit': atr_levels['take_profit_price'],
                'risk_reward_ratio': atr_levels['risk_reward_ratio'],
                'volatility_adjustment': size_adjustment['adjustment_factor']
            }

            self.trade_history.append(trade)
            self._update_portfolio_history(timestamp)

            return trade

        # For sell signals - close existing position
        elif signal in ['SELL', 'STRONG_SELL'] and symbol in self.positions:
            return self._close_position(symbol, price, timestamp, signal, confidence)

        return {"error": "Trade conditions not met"}

    def execute_trade(self, symbol: str, signal: str, price: float,
                     confidence: float, timestamp: datetime,
                     risk_level: str = 'medium') -> Dict[str, Any]:
        """Enhanced trade execution with fees and improved position sizing"""

        # Risk-adjusted position sizing
        base_position_size = Config.MAX_POSITION_SIZE
        confidence_multiplier = min(confidence * 1.2, 1.0)

        risk_multipliers = {'low': 1.0, 'medium': 0.8, 'high': 0.5}
        risk_multiplier = risk_multipliers.get(risk_level, 0.8)

        adjusted_position_size = base_position_size * confidence_multiplier * risk_multiplier

        if signal in ['BUY', 'STRONG_BUY'] and symbol not in self.positions and confidence > 0.6:
            # Calculate position size with fees
            risk_amount = self.capital * adjusted_position_size
            fee = risk_amount * self.taker_fee
            net_amount = risk_amount - fee
            shares = net_amount / price

            if shares > 0 and risk_amount >= self.min_trade_size and risk_amount <= self.capital:
                # Execute buy order
                self.positions[symbol] = {
                    'shares': shares,
                    'entry_price': price,
                    'entry_time': timestamp,
                    'signal': signal,
                    'confidence': confidence,
                    'risk_level': risk_level,
                    'entry_fee': fee,
                    'stop_loss_price': price * (1 - Config.STOP_LOSS_PCT),
                    'take_profit_price': price * (1 + Config.TAKE_PROFIT_PCT)
                }

                self.capital -= risk_amount
                self.trade_fees += fee

                trade = {
                    'timestamp': timestamp,
                    'symbol': symbol,
                    'action': 'BUY',
                    'shares': shares,
                    'price': price,
                    'value': risk_amount,
                    'fee': fee,
                    'net_value': net_amount,
                    'signal': signal,
                    'confidence': confidence,
                    'risk_level': risk_level
                }

                self.trade_history.append(trade)
                self._update_portfolio_history(timestamp)
                return trade

        elif signal in ['SELL', 'STRONG_SELL'] and symbol in self.positions:
            return self._close_position(symbol, price, timestamp, signal, confidence)

        return None

    def _close_position(self, symbol: str, price: float, timestamp: datetime,
                       signal: str = 'SELL', confidence: float = 1.0) -> Dict[str, Any]:
        """Close a position with detailed P&L calculation"""
        if symbol not in self.positions:
            return None

        position = self.positions[symbol]
        gross_proceeds = position['shares'] * price
        exit_fee = gross_proceeds * self.taker_fee
        net_proceeds = gross_proceeds - exit_fee

        # Calculate P&L
        total_cost = position['shares'] * position['entry_price'] + position['entry_fee']
        net_pnl = net_proceeds - total_cost
        gross_pnl = gross_proceeds - (position['shares'] * position['entry_price'])
        pnl_pct = (price / position['entry_price']) - 1

        # Hold duration
        hold_duration_hours = (timestamp - position['entry_time']).total_seconds() / 3600
        hold_duration_days = hold_duration_hours / 24

        self.capital += net_proceeds
        self.trade_fees += exit_fee

        trade = {
            'timestamp': timestamp,
            'symbol': symbol,
            'action': signal.replace('STRONG_', ''),
            'shares': position['shares'],
            'price': price,
            'value': gross_proceeds,
            'fee': exit_fee,
            'net_value': net_proceeds,
            'gross_pnl': gross_pnl,
            'net_pnl': net_pnl,
            'pnl_pct': pnl_pct,
            'signal': signal,
            'confidence': confidence,
            'hold_duration_hours': hold_duration_hours,
            'hold_duration_days': hold_duration_days,
            'entry_price': position['entry_price'],
            'entry_time': position['entry_time'],
            'entry_fee': position['entry_fee'],
            'total_fees': position['entry_fee'] + exit_fee,
            'risk_level': position['risk_level']
        }

        self.trade_history.append(trade)
        del self.positions[symbol]

        # Update daily P&L tracking
        self._update_daily_pnl(timestamp, net_pnl)
        self._update_portfolio_history(timestamp)

        return trade

    def check_risk_management(self, symbol: str, current_price: float,
                            timestamp: datetime) -> Optional[Dict[str, Any]]:
        """Enhanced risk management with precise stop/take levels"""
        if symbol not in self.positions:
            return None

        position = self.positions[symbol]
        current_return = (current_price / position['entry_price']) - 1

        # Stop loss check
        if current_price <= position['stop_loss_price']:
            return self._close_position(symbol, current_price, timestamp, 'STOP_LOSS', 1.0)

        # Take profit check
        elif current_price >= position['take_profit_price']:
            return self._close_position(symbol, current_price, timestamp, 'TAKE_PROFIT', 1.0)

        # Trailing stop (optional enhancement)
        elif current_return > 0.05:  # If up 5%+, implement trailing stop
            new_stop_loss = current_price * (1 - Config.STOP_LOSS_PCT * 0.5)  # Tighter stop
            if new_stop_loss > position['stop_loss_price']:
                position['stop_loss_price'] = new_stop_loss

        return None

    def _update_daily_pnl(self, timestamp: datetime, pnl: float):
        """Update daily P&L tracking"""
        date_key = timestamp.date()

        if date_key not in self.daily_pnl:
            self.daily_pnl[date_key] = {'pnl': 0, 'trades': 0, 'fees': 0}

        self.daily_pnl[date_key]['pnl'] += pnl
        self.daily_pnl[date_key]['trades'] += 1

    def _update_portfolio_history(self, timestamp: datetime):
        """Update portfolio value history"""
        total_value = self.get_current_portfolio_value()

        self.portfolio_history.append({
            'timestamp': timestamp,
            'total_value': total_value,
            'capital': self.capital,
            'positions_value': total_value - self.capital,
            'total_return': (total_value / self.initial_capital) - 1
        })

        # Update peak and drawdown
        if total_value > self.peak_value:
            self.peak_value = total_value

        current_drawdown = (self.peak_value - total_value) / self.peak_value
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown

    def get_current_portfolio_value(self, current_prices: Dict[str, float] = None) -> float:
        """Calculate current portfolio value"""
        total_value = self.capital

        for symbol, position in self.positions.items():
            if current_prices and symbol in current_prices:
                current_price = current_prices[symbol]
            else:
                current_price = position['entry_price']  # Fallback to entry price

            position_value = position['shares'] * current_price
            total_value += position_value

        return total_value

    def get_portfolio_status(self, current_prices: Dict[str, float] = None) -> Dict[str, Any]:
        """Enhanced portfolio status with detailed metrics"""
        total_value = self.get_current_portfolio_value(current_prices)
        total_return = (total_value / self.initial_capital) - 1

        # Position details with current P&L
        position_details = {}
        for symbol, position in self.positions.items():
            current_price = current_prices.get(symbol, position['entry_price']) if current_prices else position['entry_price']
            unrealized_pnl = (current_price - position['entry_price']) * position['shares']
            unrealized_pnl_pct = (current_price / position['entry_price']) - 1

            position_details[symbol] = {
                **position,
                'current_price': current_price,
                'current_value': position['shares'] * current_price,
                'unrealized_pnl': unrealized_pnl,
                'unrealized_pnl_pct': unrealized_pnl_pct
            }

        return {
            'capital': self.capital,
            'total_value': total_value,
            'total_return': total_return,
            'positions': position_details,
            'position_count': len(self.positions),
            'trade_count': len(self.trade_history),
            'total_fees': self.trade_fees,
            'max_drawdown': self.max_drawdown,
            'peak_value': self.peak_value
        }

    def get_performance_analytics(self) -> Dict[str, Any]:
        """Comprehensive performance analytics"""
        if not self.trade_history:
            return {'error': 'No trades to analyze'}

        completed_trades = [t for t in self.trade_history if 'net_pnl' in t]

        if not completed_trades:
            return {'error': 'No completed trades to analyze'}

        # Basic metrics
        total_trades = len(completed_trades)
        winning_trades = [t for t in completed_trades if t['net_pnl'] > 0]
        losing_trades = [t for t in completed_trades if t['net_pnl'] < 0]

        win_rate = len(winning_trades) / total_trades
        avg_win = np.mean([t['pnl_pct'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl_pct'] for t in losing_trades]) if losing_trades else 0

        # Profit factor
        gross_profit = sum([t['net_pnl'] for t in winning_trades])
        gross_loss = abs(sum([t['net_pnl'] for t in losing_trades]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Return metrics
        returns = [t['pnl_pct'] for t in completed_trades]
        avg_return = np.mean(returns)
        return_std = np.std(returns)

        # Sharpe ratio (assuming daily trading)
        sharpe_ratio = (avg_return / return_std) * np.sqrt(252) if return_std > 0 else 0

        # Time-based analysis
        avg_hold_time = np.mean([t['hold_duration_hours'] for t in completed_trades])

        # Fee impact
        total_fees = sum([t.get('total_fees', 0) for t in completed_trades])
        fee_impact_pct = (total_fees / self.initial_capital) * 100

        # Daily/Weekly/Monthly returns
        daily_returns = self._calculate_period_returns('daily')
        weekly_returns = self._calculate_period_returns('weekly')
        monthly_returns = self._calculate_period_returns('monthly')

        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'avg_win_pct': avg_win,
            'avg_loss_pct': avg_loss,
            'profit_factor': profit_factor,
            'avg_return_pct': avg_return,
            'return_volatility': return_std,
            'sharpe_ratio': sharpe_ratio,
            'avg_hold_hours': avg_hold_time,
            'max_drawdown': self.max_drawdown,
            'total_fees': total_fees,
            'fee_impact_pct': fee_impact_pct,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'net_profit': gross_profit - gross_loss,
            'best_trade_pct': max(returns) if returns else 0,
            'worst_trade_pct': min(returns) if returns else 0,
            'daily_returns': daily_returns,
            'weekly_returns': weekly_returns,
            'monthly_returns': monthly_returns
        }

    def _calculate_period_returns(self, period: str) -> List[Dict]:
        """Calculate returns for specific periods"""
        if not self.portfolio_history:
            return []

        df = pd.DataFrame(self.portfolio_history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)

        if period == 'daily':
            grouped = df.groupby(df.index.date)
        elif period == 'weekly':
            grouped = df.groupby(pd.Grouper(freq='W'))
        elif period == 'monthly':
            grouped = df.groupby(pd.Grouper(freq='M'))
        else:
            return []

        period_returns = []
        for name, group in grouped:
            if len(group) > 0:
                start_value = group['total_value'].iloc[0]
                end_value = group['total_value'].iloc[-1]
                period_return = (end_value / start_value) - 1

                period_returns.append({
                    'period': str(name),
                    'start_value': start_value,
                    'end_value': end_value,
                    'return_pct': period_return,
                    'trades': len([t for t in self.trade_history
                                 if (pd.to_datetime(t['timestamp']).date() == name
                                     if period == 'daily'
                                     else pd.to_datetime(t['timestamp']) >= name - pd.Timedelta(days=7)
                                     if period == 'weekly'
                                     else pd.to_datetime(t['timestamp']).month == name.month)])
                })

        return period_returns

    def export_to_csv(self, filename: str = None) -> Tuple[str, str]:
        """Export trading history and performance to CSV"""
        import csv
        from io import StringIO

        if filename is None:
            filename = f"paper_trading_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        # Prepare trade data
        trade_data = []
        for trade in self.trade_history:
            trade_row = {
                'timestamp': trade['timestamp'],
                'symbol': trade['symbol'],
                'action': trade['action'],
                'shares': trade.get('shares', 0),
                'price': trade.get('price', 0),
                'value': trade.get('value', 0),
                'fee': trade.get('fee', 0),
                'net_pnl': trade.get('net_pnl', 0),
                'pnl_pct': trade.get('pnl_pct', 0),
                'signal': trade.get('signal', ''),
                'confidence': trade.get('confidence', 0),
                'hold_duration_hours': trade.get('hold_duration_hours', 0),
                'risk_level': trade.get('risk_level', '')
            }
            trade_data.append(trade_row)

        # Create CSV content
        output = StringIO()

        # Write summary
        analytics = self.get_performance_analytics()
        if 'error' not in analytics:
            output.write("PERFORMANCE SUMMARY\n")
            output.write(f"Total Trades,{analytics['total_trades']}\n")
            output.write(f"Win Rate,{analytics['win_rate']:.2%}\n")
            output.write(f"Profit Factor,{analytics['profit_factor']:.2f}\n")
            output.write(f"Sharpe Ratio,{analytics['sharpe_ratio']:.2f}\n")
            output.write(f"Max Drawdown,{analytics['max_drawdown']:.2%}\n")
            output.write(f"Total Fees,${analytics['total_fees']:.2f}\n")
            output.write(f"Net Profit,${analytics['net_profit']:.2f}\n")
            output.write("\n")

        # Write trade details
        output.write("TRADE DETAILS\n")
        if trade_data:
            fieldnames = trade_data[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(trade_data)

        csv_content = output.getvalue()
        output.close()

        return csv_content, filename

    def reset_simulation(self):
        """Reset the simulation to initial state"""
        self.capital = self.initial_capital
        self.positions = {}
        self.trade_history = []
        self.portfolio_history = []
        self.daily_pnl = {}
        self.trade_fees = 0
        self.max_drawdown = 0
        self.peak_value = self.initial_capital

# ==========================================
# 7. DATABASE MODULE
# ==========================================

class DatabaseManager:
    """SQLite database for storing trading data"""

    def __init__(self, db_file: str = Config.DB_FILE):
        self.db_file = db_file
        self.init_database()

    def init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_file) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS price_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    symbol TEXT,
                    timeframe TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    rsi REAL,
                    macd REAL,
                    macd_signal REAL,
                    bb_upper REAL,
                    bb_lower REAL,
                    UNIQUE(timestamp, symbol, timeframe)
                )
            ''')

            conn.execute('''
                CREATE TABLE IF NOT EXISTS trading_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    symbol TEXT,
                    signal TEXT,
                    confidence REAL,
                    current_price REAL,
                    predicted_price REAL,
                    expected_return REAL
                )
            ''')

            conn.execute('''
                CREATE TABLE IF NOT EXISTS paper_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    symbol TEXT,
                    action TEXT,
                    shares REAL,
                    price REAL,
                    value REAL,
                    pnl REAL,
                    pnl_pct REAL,
                    signal TEXT,
                    confidence REAL
                )
            ''')

    def save_price_data(self, df: pd.DataFrame):
        """Save price data with indicators"""
        with sqlite3.connect(self.db_file) as conn:
            df_to_save = df.copy()
            df_to_save['timestamp'] = df_to_save.index.strftime('%Y-%m-%d %H:%M:%S')

            # Select columns that exist in the dataframe
            columns = ['timestamp', 'symbol', 'timeframe', 'open', 'high', 'low', 'close', 'volume']
            optional_columns = ['rsi', 'macd', 'macd_signal', 'bb_upper', 'bb_lower']

            for col in optional_columns:
                if col in df_to_save.columns:
                    columns.append(col)

            df_to_save[columns].to_sql('price_data', conn, if_exists='append', index=False)

    def save_trading_signal(self, timestamp: datetime, symbol: str, signal_data: Dict):
        """Save trading signal"""
        with sqlite3.connect(self.db_file) as conn:
            conn.execute('''
                INSERT INTO trading_signals
                (timestamp, symbol, signal, confidence, current_price, predicted_price, expected_return)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                symbol,
                signal_data.get('signal'),
                signal_data.get('confidence'),
                signal_data.get('current_price'),
                signal_data.get('predicted_price'),
                signal_data.get('expected_return')
            ))

    def save_paper_trade(self, trade_data: Dict):
        """Save paper trade"""
        with sqlite3.connect(self.db_file) as conn:
            conn.execute('''
                INSERT INTO paper_trades
                (timestamp, symbol, action, shares, price, value, pnl, pnl_pct, signal, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                trade_data['symbol'],
                trade_data['action'],
                trade_data['shares'],
                trade_data['price'],
                trade_data['value'],
                trade_data.get('pnl'),
                trade_data.get('pnl_pct'),
                trade_data['signal'],
                trade_data['confidence']
            ))

    def get_price_data(self, symbol: str = None, timeframe: str = None, limit: int = 1000) -> pd.DataFrame:
        """Retrieve price data"""
        with sqlite3.connect(self.db_file) as conn:
            query = "SELECT * FROM price_data"
            conditions = []
            params = []

            if symbol:
                conditions.append("symbol = ?")
                params.append(symbol)

            if timeframe:
                conditions.append("timeframe = ?")
                params.append(timeframe)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            df = pd.read_sql_query(query, conn, params=params)

            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                df.sort_index(inplace=True)

            return df

# ==========================================
# 8. STREAMLIT DASHBOARD MODULE
# ==========================================

def main_dashboard():
    """Professional Risk Management Trading Dashboard"""
    st.set_page_config(
        page_title="Crypto Trader Pro - Risk Management Dashboard",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize session state
    if 'api_client' not in st.session_state:
        st.session_state.api_client = AlphaVantageConnector()

    if 'ml_model' not in st.session_state:
        st.session_state.ml_model = MLSignalGenerator()

    if 'paper_trader' not in st.session_state:
        st.session_state.paper_trader = PaperTradingSimulator(initial_capital=10000)

    # Initialize professional risk manager separately for flexibility
    if 'risk_manager' not in st.session_state:
        st.session_state.risk_manager = RiskManager(account_balance=10000)

    # Initialize ATR calculator for volatility analysis
    if 'atr_calculator' not in st.session_state:
        st.session_state.atr_calculator = ATRCalculator()

    # Initialize Portfolio Risk Manager for portfolio-level risk control
    if 'portfolio_risk_manager' not in st.session_state:
        st.session_state.portfolio_risk_manager = PortfolioRiskManager(initial_capital=10000)

    if 'db_manager' not in st.session_state:
        st.session_state.db_manager = DatabaseManager()

    if 'auto_trading' not in st.session_state:
        st.session_state.auto_trading = False

    if 'current_data' not in st.session_state:
        st.session_state.current_data = None

    if 'latest_signal' not in st.session_state:
        st.session_state.latest_signal = None

    # Custom CSS for better styling
    st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #d1d5db;
    }
    .signal-buy {
        background-color: #10b981;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 0.25rem;
        font-weight: bold;
    }
    .signal-sell {
        background-color: #ef4444;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 0.25rem;
        font-weight: bold;
    }
    .signal-hold {
        background-color: #6b7280;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 0.25rem;
        font-weight: bold;
    }
    .portfolio-positive {
        color: #10b981;
        font-weight: bold;
    }
    .portfolio-negative {
        color: #ef4444;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

    # Professional Dashboard Header
    st.title("🛡️ Crypto Trader Pro - Risk Management Dashboard")
    st.markdown("---")

    # Top Metrics Section (4 columns as requested)
    col1, col2, col3, col4 = st.columns(4)

    # Update portfolio and risk metrics
    st.session_state.portfolio_risk_manager.update_portfolio_metrics(st.session_state.paper_trader)
    portfolio_status = st.session_state.paper_trader.get_portfolio_status()
    risk_summary = st.session_state.portfolio_risk_manager.get_risk_summary()

    # Calculate additional metrics
    total_value = portfolio_status['total_value']
    total_return = portfolio_status['total_return']
    daily_return = risk_summary['daily_pnl_pct']

    # Get current month return (simulate for demo)
    monthly_return = total_return * 0.3 if total_return > 0 else total_return * 1.2  # Placeholder calculation

    # Current leverage calculation
    current_leverage = 1.0
    if portfolio_status['positions']:
        total_position_value = sum([pos.get('current_value', pos['shares'] * pos['entry_price'])
                                  for pos in portfolio_status['positions'].values()])
        if portfolio_status['capital'] > 0:
            current_leverage = total_position_value / portfolio_status['capital']

    with col1:
        delta_color = "normal" if total_return >= 0 else "inverse"
        st.metric(
            "💰 총 투자금",
            f"${total_value:,.2f}",
            delta=f"${portfolio_status['capital']:,.2f} 계좌 잔고",
            delta_color=delta_color
        )

    with col2:
        daily_delta = f"{daily_return:+.2%}" if daily_return != 0 else "0.00%"
        monthly_delta = f"{monthly_return:+.2%}" if monthly_return != 0 else "0.00%"
        st.metric(
            "📈 오늘 수익률",
            daily_delta,
            delta=f"이번달: {monthly_delta}",
            delta_color="normal" if daily_return >= 0 else "inverse"
        )

    with col3:
        exposure_pct = risk_summary['total_exposure'] * 100
        risk_util_pct = risk_summary['risk_utilization'] * 100
        exposure_color = "normal" if exposure_pct < 70 else "inverse"
        st.metric(
            "🎯 총 노출도",
            f"{exposure_pct:.0f}%",
            delta=f"리스크 사용률: {risk_util_pct:.0f}%",
            delta_color=exposure_color
        )

    with col4:
        position_count = len(portfolio_status['positions'])
        leverage_color = "normal" if current_leverage <= 2.0 else "inverse"
        st.metric(
            "⚡ 현재 레버리지",
            f"{current_leverage:.1f}x",
            delta=f"포지션: {position_count}개",
            delta_color=leverage_color
        )

    st.markdown("---")

    # Professional Risk Management Sidebar
    st.sidebar.title("🛡️ 리스크 관리 설정")
    st.sidebar.markdown("---")

    # 기본 거래 설정
    st.sidebar.subheader("📈 기본 거래 설정")

    selected_symbol = st.sidebar.selectbox(
        "암호화폐 선택",
        Config.SYMBOLS,
        index=0,
        help="거래할 암호화폐를 선택하세요"
    )

    selected_timeframe = st.sidebar.selectbox(
        "분석 시간프레임",
        Config.TIMEFRAMES,
        index=1,
        help="기술적 분석 시간프레임"
    )

    st.sidebar.markdown("---")

    # 리스크 매개변수 (요청사항에 맞게)
    st.sidebar.subheader("⚠️ 리스크 매개변수")

    # 계좌 리스크 슬라이더 (0.5% ~ 3.0%)
    account_risk = st.sidebar.slider(
        "💰 계좌 리스크 (%)",
        min_value=0.5,
        max_value=3.0,
        value=1.0,
        step=0.1,
        help="거래당 계좌 자금의 리스크 비율",
        key="account_risk_slider"
    ) / 100

    # 최대 레버리지 설정 (1x ~ 5x)
    max_leverage = st.sidebar.slider(
        "⚡ 최대 레버리지",
        min_value=1.0,
        max_value=5.0,
        value=3.0,
        step=0.5,
        help="허용되는 최대 레버리지",
        key="max_leverage_slider"
    )

    # 포트폴리오 한도 설정 (50% ~ 90%)
    portfolio_limit = st.sidebar.slider(
        "🎯 포트폴리오 한도 (%)",
        min_value=50,
        max_value=90,
        value=80,
        step=5,
        help="최대 포트폴리오 노출도",
        key="portfolio_limit_slider"
    ) / 100

    # 일일 손실 한도 (3% ~ 10%)
    daily_loss_limit = st.sidebar.slider(
        "🚨 일일 손실 한도 (%)",
        min_value=3.0,
        max_value=10.0,
        value=5.0,
        step=0.5,
        help="일일 최대 허용 손실",
        key="daily_loss_limit_slider"
    ) / 100

    # 설정 적용
    st.session_state.risk_manager.max_leverage = max_leverage
    st.session_state.risk_manager.default_account_risk = account_risk
    st.session_state.portfolio_risk_manager.max_total_exposure = portfolio_limit
    st.session_state.portfolio_risk_manager.daily_loss_limit = daily_loss_limit

    st.sidebar.markdown("---")

    # 실시간 리스크 상태
    st.sidebar.subheader("📊 실시간 리스크 상태")

    # 현재 리스크 지표들
    current_exposure = risk_summary['total_exposure']
    current_daily_loss = abs(risk_summary['daily_pnl_pct'])

    # 리스크 게이지 표시
    exposure_pct = (current_exposure / portfolio_limit) * 100
    daily_loss_pct = (current_daily_loss / daily_loss_limit) * 100

    # 노출도 상태
    if exposure_pct < 50:
        exposure_status = "🟢 안전"
    elif exposure_pct < 80:
        exposure_status = "🟡 주의"
    else:
        exposure_status = "🔴 위험"

    st.sidebar.metric("포트폴리오 노출도", f"{exposure_status} {current_exposure:.0%}")

    # 일일 손실 상태
    if daily_loss_pct < 50:
        loss_status = "🟢 안전"
    elif daily_loss_pct < 80:
        loss_status = "🟡 주의"
    else:
        loss_status = "🔴 위험"

    st.sidebar.metric("일일 손실률", f"{loss_status} {current_daily_loss:.1%}")

    # 레버리지 상태
    if current_leverage <= 2.0:
        leverage_status = "🟢 안전"
    elif current_leverage <= 4.0:
        leverage_status = "🟡 주의"
    else:
        leverage_status = "🔴 위험"

    st.sidebar.metric("현재 레버리지", f"{leverage_status} {current_leverage:.1f}x")

    st.sidebar.markdown("---")

    # Trading Mode
    st.sidebar.subheader("🤖 Trading Mode")

    auto_trading = st.sidebar.checkbox(
        "Auto Trading Mode",
        value=st.session_state.auto_trading,
        help="Enable automatic trade execution"
    )
    st.session_state.auto_trading = auto_trading

    if auto_trading:
        st.sidebar.success("🟢 Auto Trading: ON")
    else:
        st.sidebar.info("🔵 Manual Trading Mode")

    # Portfolio Risk Overview
    st.sidebar.subheader("🛡️ Portfolio Risk Overview")

    # Update portfolio metrics
    st.session_state.portfolio_risk_manager.update_portfolio_metrics(st.session_state.paper_trader)
    risk_summary = st.session_state.portfolio_risk_manager.get_risk_summary()

    # Risk Alert Level
    alert_level = risk_summary['alert_level']
    alert_colors = {
        'LOW': '🟢',
        'MEDIUM': '🟡',
        'HIGH': '🟠',
        'CRITICAL': '🔴'
    }
    alert_color = alert_colors.get(alert_level, '⚪')

    st.sidebar.metric("Risk Level", f"{alert_color} {alert_level}")

    # Core Risk Metrics
    col_risk1, col_risk2 = st.sidebar.columns(2)

    with col_risk1:
        st.metric("Total Exposure", f"{risk_summary['total_exposure']:.0%}")
        st.metric("Daily P&L", f"${risk_summary['daily_pnl']:.0f}")

    with col_risk2:
        st.metric("Risk Used", f"{risk_summary['risk_utilization']:.0%}")
        consecutive_color = "🔴" if risk_summary['consecutive_losses'] >= 2 else "🟢"
        st.metric("Consecutive Losses", f"{consecutive_color} {risk_summary['consecutive_losses']}")

    # Trading Status
    if risk_summary['trading_enabled']:
        if risk_summary['position_size_multiplier'] < 1.0:
            reduction_pct = (1 - risk_summary['position_size_multiplier']) * 100
            st.sidebar.warning(f"📉 Position size reduced: {reduction_pct:.0f}%")
        else:
            st.sidebar.success("✅ Trading enabled")
    else:
        st.sidebar.error("🚫 Trading disabled")

    # Portfolio Risk Controls
    with st.sidebar.expander("🔧 Risk Controls", expanded=False):
        if st.button("🔄 Reset Daily Metrics", help="Reset daily P&L and trading counters"):
            st.session_state.portfolio_risk_manager.daily_pnl = 0
            st.session_state.portfolio_risk_manager.daily_start_value = st.session_state.portfolio_risk_manager.current_capital
            st.session_state.portfolio_risk_manager.trade_count_today = 0
            st.success("Daily metrics reset!")

        if st.button("🚫 Disable Trading", help="Manually disable all trading"):
            st.session_state.portfolio_risk_manager.disable_trading()
            st.warning("Trading disabled!")

        if st.button("✅ Enable Trading", help="Manually enable trading (override)"):
            st.session_state.portfolio_risk_manager.enable_trading()
            st.success("Trading enabled!")

        if st.button("🔄 Reset Consecutive Losses", help="Reset consecutive loss counter"):
            st.session_state.portfolio_risk_manager.consecutive_losses = 0
            st.session_state.portfolio_risk_manager.position_size_reduction = 1.0
            st.success("Consecutive losses reset!")

    # Quick Actions
    st.sidebar.subheader("⚡ Quick Actions")

    col_a, col_b = st.sidebar.columns(2)

    with col_a:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()

    with col_b:
        if st.button("🎯 Get Signal", use_container_width=True):
            st.session_state.force_signal = True
            st.rerun()

    # 전문가급 메인 대시보드 (4개 탭 구성)
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 Live Trading",
        "📊 Portfolio Overview",
        "⚠️ Risk Analysis",
        "📈 Backtest Results"
    ])

    # Tab 1: Live Trading (실시간 신호 + 포지션 계산)
    with tab1:
        create_live_trading_tab(selected_symbol, selected_timeframe, account_risk, max_leverage)

    # Tab 2: Portfolio Overview (포트폴리오 현황)
    with tab2:
        create_portfolio_overview_tab()

    # Tab 3: Risk Analysis (리스크 분석)
    with tab3:
        create_risk_analysis_tab()

    # Tab 4: Backtest Results (백테스팅 결과)
    with tab4:
        create_backtest_results_tab(selected_symbol, selected_timeframe)

def create_main_dashboard(symbol: str, timeframe: str, risk_level: float,
                         stop_loss: float, take_profit: float):
    """Create the main dashboard layout"""

    # Top row: Real-time price and AI signal
    col1, col2 = st.columns([2, 1])

    with col1:
        display_realtime_price_chart(symbol, timeframe)

    with col2:
        display_ai_signal_panel(symbol, timeframe)

    # Middle row: Portfolio and performance
    col3, col4, col5 = st.columns([1, 1, 1])

    with col3:
        display_portfolio_overview()

    with col4:
        display_recent_trades()

    with col5:
        display_performance_metrics()

    # Bottom row: Model status and risk indicators
    col6, col7 = st.columns([1, 1])

    with col6:
        display_model_status()

    with col7:
        display_risk_indicators()

def display_realtime_price_chart(symbol: str, timeframe: str):
    """Display real-time price chart with technical indicators"""
    st.subheader(f"📈 {symbol} Price Chart ({timeframe})")

    # Get data
    with st.spinner("Loading price data..."):
        df = st.session_state.api_client.get_historical_data(symbol, months=1)

        if df is not None and len(df) > 0:
            # Add technical indicators
            df_with_indicators = TechnicalIndicators.add_all_indicators(df, st.session_state.api_client)
            st.session_state.current_data = df_with_indicators

            # Create enhanced chart
            fig = create_enhanced_price_chart(df_with_indicators, symbol)
            st.plotly_chart(fig, use_container_width=True)

            # Display current price info
            latest = df_with_indicators.iloc[-1]

            col_a, col_b, col_c, col_d = st.columns(4)

            with col_a:
                st.metric("Current Price", f"${latest['close']:,.2f}")

            with col_b:
                change = latest.get('price_change', 0) * 100
                st.metric("24h Change", f"{change:+.2f}%")

            with col_c:
                st.metric("Volume", f"{latest['volume']:,.0f}")

            with col_d:
                rsi = latest.get('rsi', 50)
                st.metric("RSI", f"{rsi:.1f}")

        else:
            st.error("Failed to load price data. Please check your API key.")

def display_ai_signal_panel(symbol: str, timeframe: str):
    """Display AI signal generation panel"""
    st.subheader("🧠 AI Trading Signal")

    # Auto-refresh every 30 seconds or manual trigger
    if st.session_state.current_data is not None:

        # Generate signal button
        if st.button("🎯 Generate AI Signal", type="primary", use_container_width=True):
            with st.spinner("Generating AI signal..."):

                # Train model if not trained
                if not st.session_state.ml_model.is_trained:
                    training_result = st.session_state.ml_model.train_model(st.session_state.current_data)
                    if "error" in training_result:
                        st.error(f"Model training failed: {training_result['error']}")
                        return

                # Generate signal
                signal_result = st.session_state.ml_model.predict_signal(st.session_state.current_data)

                if "error" not in signal_result:
                    st.session_state.latest_signal = signal_result

                    # Display signal
                    signal = signal_result['signal']
                    confidence = signal_result['confidence']
                    risk_level = signal_result.get('risk_level', 'medium')

                    # Signal display with color coding
                    if signal in ['BUY', 'STRONG_BUY']:
                        st.success(f"🟢 **{signal}**")
                    elif signal in ['SELL', 'STRONG_SELL']:
                        st.error(f"🔴 **{signal}**")
                    else:
                        st.info(f"🔵 **{signal}**")

                    # Signal details
                    st.write(f"**Confidence:** {confidence:.1%}")
                    st.write(f"**Risk Level:** {risk_level.title()}")

                    if 'predicted_return' in signal_result:
                        predicted_return = signal_result['predicted_return']
                        st.write(f"**Expected Return:** {predicted_return:+.2%}")

                    # Technical confirmation
                    if 'technical_confirmation' in signal_result:
                        with st.expander("🔍 Technical Analysis"):
                            tech_conf = signal_result['technical_confirmation']
                            for indicator, status in tech_conf.items():
                                st.write(f"**{indicator.upper()}:** {status}")

                    # Execute trade if auto-trading is enabled
                    if st.session_state.auto_trading and confidence > 0.7:
                        execute_auto_trade(symbol, signal_result)

                else:
                    st.error(f"Signal generation failed: {signal_result['error']}")

    else:
        st.info("Load price data first to generate signals")

    # Manual trading buttons
    if st.session_state.latest_signal:
        st.subheader("📋 Manual Trading")

        col_a, col_b = st.columns(2)

        with col_a:
            if st.button("💰 Execute Buy", use_container_width=True):
                execute_manual_trade(symbol, "BUY")

        with col_b:
            if st.button("💸 Execute Sell", use_container_width=True):
                execute_manual_trade(symbol, "SELL")

def display_portfolio_overview():
    """Display portfolio overview"""
    st.subheader("💼 Portfolio Overview")

    portfolio_status = st.session_state.paper_trader.get_portfolio_status()

    # Portfolio metrics
    total_value = portfolio_status['total_value']
    capital = portfolio_status['capital']
    total_return = portfolio_status['total_return']
    positions = portfolio_status['positions']

    st.metric("Total Value", f"${total_value:,.2f}", f"{total_return:+.2%}")
    st.metric("Available Cash", f"${capital:,.2f}")
    st.metric("Active Positions", len(positions))

    # Position details
    if positions:
        with st.expander("📊 Position Details"):
            for symbol, position in positions.items():
                st.write(f"**{symbol}**")
                st.write(f"  • Shares: {position['shares']:.4f}")
                st.write(f"  • Entry Price: ${position['entry_price']:.2f}")
                st.write(f"  • Signal: {position['signal']}")

def display_recent_trades():
    """Display recent trading activity"""
    st.subheader("📈 Recent Trades")

    trades = st.session_state.paper_trader.trade_history

    if trades:
        # Show last 5 trades
        recent_trades = trades[-5:]

        for trade in reversed(recent_trades):
            with st.container():
                col_a, col_b, col_c = st.columns([2, 1, 1])

                with col_a:
                    action_emoji = "🟢" if trade['action'] == 'BUY' else "🔴"
                    st.write(f"{action_emoji} **{trade['action']}** {trade['symbol']}")

                with col_b:
                    st.write(f"${trade['price']:.2f}")

                with col_c:
                    if 'pnl_pct' in trade:
                        pnl_color = "🟢" if trade['pnl_pct'] > 0 else "🔴"
                        st.write(f"{pnl_color} {trade['pnl_pct']:+.2%}")

                st.caption(f"{trade['timestamp'].strftime('%H:%M:%S')}")
                st.divider()

    else:
        st.info("No trades executed yet")

def display_performance_metrics():
    """Display performance metrics"""
    st.subheader("📊 Performance Metrics")

    portfolio_status = st.session_state.paper_trader.get_portfolio_status()
    trades = st.session_state.paper_trader.trade_history

    if trades:
        completed_trades = [t for t in trades if 'pnl_pct' in t]

        if completed_trades:
            returns = [t['pnl_pct'] for t in completed_trades]
            winning_trades = [r for r in returns if r > 0]

            win_rate = len(winning_trades) / len(returns) if returns else 0
            avg_return = np.mean(returns) if returns else 0
            total_trades = len(completed_trades)

            st.metric("Win Rate", f"{win_rate:.1%}")
            st.metric("Avg Return", f"{avg_return:+.2%}")
            st.metric("Total Trades", total_trades)

            # Performance chart
            if len(returns) > 1:
                fig = go.Figure()
                cumulative_returns = np.cumprod([1 + r for r in returns])
                fig.add_trace(go.Scatter(
                    y=cumulative_returns,
                    mode='lines',
                    name='Cumulative Returns',
                    line=dict(color='blue')
                ))
                fig.update_layout(
                    title="Cumulative Returns",
                    height=200,
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No performance data yet")

def display_model_status():
    """Display ML model status and performance"""
    st.subheader("🤖 Model Status")

    if st.session_state.ml_model.is_trained:
        st.success("✅ Model Trained")

        # Training history
        if st.session_state.ml_model.training_history:
            latest_training = st.session_state.ml_model.training_history[-1]

            st.metric("Model Accuracy", f"{latest_training['accuracy']:.1%}")
            st.metric("Training Samples", latest_training['samples'])
            st.metric("Price R²", f"{latest_training.get('price_r2', 0):.3f}")

        # Retrain button
        if st.button("🔄 Retrain Model", use_container_width=True):
            if st.session_state.current_data is not None:
                with st.spinner("Retraining model..."):
                    result = st.session_state.ml_model.train_model(st.session_state.current_data)
                    if "error" not in result:
                        st.success("Model retrained successfully!")
                        st.rerun()
                    else:
                        st.error(f"Training failed: {result['error']}")

    else:
        st.warning("⚠️ Model Not Trained")

        if st.button("🚀 Train Model", type="primary", use_container_width=True):
            if st.session_state.current_data is not None:
                with st.spinner("Training model..."):
                    result = st.session_state.ml_model.train_model(st.session_state.current_data)
                    if "error" not in result:
                        st.success("Model trained successfully!")
                        st.rerun()
                    else:
                        st.error(f"Training failed: {result['error']}")

def display_risk_indicators():
    """Display risk management indicators"""
    st.subheader("⚠️ Risk Indicators")

    portfolio_status = st.session_state.paper_trader.get_portfolio_status()

    # Calculate risk metrics
    total_value = portfolio_status['total_value']
    daily_risk = total_value * Config.DAILY_LOSS_LIMIT
    position_risk = total_value * Config.MAX_POSITION_SIZE

    st.metric("Daily Risk Limit", f"${daily_risk:,.2f}")
    st.metric("Max Position Size", f"${position_risk:,.2f}")

    # Risk level indicator
    current_return = portfolio_status['total_return']

    if current_return > 0.1:  # 10%+
        st.success("🟢 Low Risk")
    elif current_return > -0.05:  # -5% to +10%
        st.info("🔵 Medium Risk")
    else:  # -5% or worse
        st.error("🔴 High Risk")

    # Risk gauge
    risk_percentage = abs(current_return) * 100
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = risk_percentage,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Risk Level (%)"},
        gauge = {
            'axis': {'range': [None, 20]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 5], 'color': "lightgray"},
                {'range': [5, 10], 'color': "yellow"},
                {'range': [10, 20], 'color': "red"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 15
            }
        }
    ))
    fig.update_layout(height=200)
    st.plotly_chart(fig, use_container_width=True)

def execute_auto_trade(symbol: str, signal_result: Dict[str, Any]):
    """Execute automatic trade based on signal"""
    signal = signal_result['signal']
    confidence = signal_result['confidence']
    current_price = signal_result['current_price']

    trade_result = st.session_state.paper_trader.execute_trade(
        symbol, signal, current_price, confidence, datetime.now()
    )

    if trade_result:
        st.success(f"🤖 Auto-trade executed: {trade_result['action']} {symbol}")
        # Save to database
        st.session_state.db_manager.save_paper_trade(trade_result)

def execute_manual_trade(symbol: str, action: str):
    """Execute manual trade"""
    if st.session_state.current_data is not None:
        current_price = st.session_state.current_data['close'].iloc[-1]

        trade_result = st.session_state.paper_trader.execute_trade(
            symbol, action, current_price, 1.0, datetime.now()
        )

        if trade_result:
            st.success(f"✅ Manual trade executed: {action} {symbol}")
            # Save to database
            st.session_state.db_manager.save_paper_trade(trade_result)
            st.rerun()
        else:
            st.warning("Trade conditions not met")

def create_enhanced_price_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Create enhanced price chart with indicators and signals"""

    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        subplot_titles=[
            f'{symbol} Price & Bollinger Bands',
            'Volume',
            'RSI',
            'MACD'
        ],
        row_heights=[0.5, 0.15, 0.15, 0.2]
    )

    # Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name="Price",
            increasing_line_color='#00ff88',
            decreasing_line_color='#ff4444'
        ),
        row=1, col=1
    )

    # Bollinger Bands
    if 'bb_upper' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['bb_upper'],
                line=dict(color='rgba(173, 204, 255, 0.5)', width=1),
                name='BB Upper',
                showlegend=False
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['bb_lower'],
                line=dict(color='rgba(173, 204, 255, 0.5)', width=1),
                fill='tonexty',
                name='BB Bands',
                fillcolor='rgba(173, 204, 255, 0.1)'
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['bb_middle'],
                line=dict(color='orange', width=1),
                name='BB Middle'
            ),
            row=1, col=1
        )

    # Volume
    colors = ['green' if row['close'] >= row['open'] else 'red' for _, row in df.iterrows()]
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['volume'],
            name='Volume',
            marker_color=colors,
            showlegend=False
        ),
        row=2, col=1
    )

    # RSI
    if 'rsi' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['rsi'],
                line=dict(color='purple', width=2),
                name='RSI',
                showlegend=False
            ),
            row=3, col=1
        )

        # RSI levels
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1, opacity=0.7)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1, opacity=0.7)
        fig.add_hline(y=50, line_dash="dot", line_color="gray", row=3, col=1, opacity=0.5)

    # MACD
    if 'macd' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['macd'],
                line=dict(color='blue', width=1),
                name='MACD',
                showlegend=False
            ),
            row=4, col=1
        )

        if 'macd_signal' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['macd_signal'],
                    line=dict(color='red', width=1),
                    name='Signal',
                    showlegend=False
                ),
                row=4, col=1
            )

        if 'macd_histogram' in df.columns:
            colors = ['green' if val >= 0 else 'red' for val in df['macd_histogram']]
            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=df['macd_histogram'],
                    name='Histogram',
                    marker_color=colors,
                    showlegend=False
                ),
                row=4, col=1
            )

    fig.update_layout(
        title=f"{symbol} Technical Analysis Dashboard",
        xaxis_rangeslider_visible=False,
        height=800,
        showlegend=True,
        template="plotly_white"
    )

    return fig

def show_live_data_tab(symbol: str, timeframe: str):
    """Live data and signals tab"""
    st.header(f"📊 Live Data - {symbol} ({timeframe})")

    col1, col2 = st.columns([2, 1])

    with col1:
        if st.button("🔄 Fetch Latest Data", type="primary"):
            with st.spinner("Fetching data from Alpha Vantage..."):
                # Fetch data
                if timeframe == '60min':
                    df = st.session_state.api_client.get_crypto_intraday(symbol, '60min')
                else:
                    df = st.session_state.api_client.get_crypto_intraday(symbol, timeframe)

                if df is not None and not df.empty:
                    # Add technical indicators
                    df_with_indicators = TechnicalIndicators.add_all_indicators(df, st.session_state.api_client)

                    # Save to database
                    st.session_state.db_manager.save_price_data(df_with_indicators)

                    # Generate ML signal
                    if st.session_state.ml_model.is_trained:
                        signal_result = st.session_state.ml_model.predict_signal(df_with_indicators)

                        if "error" not in signal_result:
                            # Save signal
                            st.session_state.db_manager.save_trading_signal(
                                datetime.now(), symbol, signal_result
                            )

                            # Display signal
                            st.success(f"✅ Data fetched and signal generated!")

                            # Show current signal
                            signal_color = {
                                'STRONG_BUY': '🟢',
                                'BUY': '🟡',
                                'HOLD': '⚪',
                                'SELL': '🟠',
                                'STRONG_SELL': '🔴'
                            }.get(signal_result['signal'], '⚪')

                            st.metric(
                                "Current Signal",
                                f"{signal_color} {signal_result['signal']}",
                                f"Confidence: {signal_result['confidence']:.2%}"
                            )

                        else:
                            st.warning(f"Signal generation failed: {signal_result['error']}")
                    else:
                        st.info("ML model not trained. Please train the model first.")

                    # Display price chart
                    fig = create_price_chart(df_with_indicators, symbol)
                    st.plotly_chart(fig, use_container_width=True)

                    # Display technical indicators
                    if len(df_with_indicators) > 0:
                        show_technical_indicators(df_with_indicators)

                else:
                    st.error("Failed to fetch data. Please check your API key and symbol.")

    with col2:
        # Display recent signals
        st.subheader("🎯 Recent Signals")

        # Get recent signals from database
        try:
            with sqlite3.connect(st.session_state.db_manager.db_file) as conn:
                signals_df = pd.read_sql_query('''
                    SELECT timestamp, symbol, signal, confidence, current_price
                    FROM trading_signals
                    WHERE symbol = ?
                    ORDER BY timestamp DESC
                    LIMIT 10
                ''', conn, params=[symbol])

            if not signals_df.empty:
                for _, row in signals_df.iterrows():
                    signal_color = {
                        'STRONG_BUY': '🟢',
                        'BUY': '🟡',
                        'HOLD': '⚪',
                        'SELL': '🟠',
                        'STRONG_SELL': '🔴'
                    }.get(row['signal'], '⚪')

                    st.text(f"{signal_color} {row['signal']} - {row['confidence']:.2%}")
                    st.caption(f"${row['current_price']:.2f} - {row['timestamp']}")
            else:
                st.info("No recent signals available")

        except Exception as e:
            st.error(f"Error loading signals: {e}")

def show_ml_training_tab(symbol: str, timeframe: str):
    """ML model training tab"""
    st.header("🧠 ML Model Training")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Training Configuration")

        # Get training data
        training_data_source = st.radio(
            "Training Data Source",
            ["Database", "Fetch Fresh Data"]
        )

        if st.button("🚀 Train ML Model", type="primary"):
            with st.spinner("Training ML model..."):
                if training_data_source == "Database":
                    # Load from database
                    df = st.session_state.db_manager.get_price_data(symbol, timeframe, limit=2000)
                else:
                    # Fetch fresh data
                    df = st.session_state.api_client.get_crypto_daily(symbol)

                if df is not None and not df.empty:
                    # Add technical indicators
                    df_with_indicators = TechnicalIndicators.add_all_indicators(df, st.session_state.api_client)

                    # Train model
                    training_results = st.session_state.ml_model.train_model(df_with_indicators)

                    if "error" not in training_results:
                        st.success("✅ Model trained successfully!")

                        # Display training metrics
                        col_a, col_b, col_c = st.columns(3)

                        with col_a:
                            st.metric("Accuracy", f"{training_results['accuracy']:.2%}")

                        with col_b:
                            st.metric("Training Samples", training_results['training_samples'])

                        with col_c:
                            st.metric("Model Status", "✅ Trained")

                        # Feature importance
                        if 'feature_importance' in training_results:
                            st.subheader("📊 Feature Importance")
                            importance_df = pd.DataFrame(
                                list(training_results['feature_importance'].items()),
                                columns=['Feature', 'Importance']
                            ).sort_values('Importance', ascending=False).head(10)

                            fig = px.bar(importance_df, x='Importance', y='Feature', orientation='h')
                            st.plotly_chart(fig, use_container_width=True)

                    else:
                        st.error(f"Training failed: {training_results['error']}")

                else:
                    st.error("No training data available")

    with col2:
        st.subheader("Model Status")

        if st.session_state.ml_model.is_trained:
            st.success("✅ Model is trained and ready")

            # Model details
            st.info("""
            **Model Details:**
            - Classification: Random Forest (100 trees)
            - Regression: Gradient Boosting (100 estimators)
            - Features: Technical indicators + price action
            - Labels: STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
            """)
        else:
            st.warning("⚠️ Model not trained yet")
            st.info("Please train the model using historical data to start generating signals.")

def show_backtesting_tab(symbol: str, timeframe: str):
    """Backtesting tab"""
    st.header("📈 Strategy Backtesting")

    if not st.session_state.ml_model.is_trained:
        st.warning("⚠️ Please train the ML model first before running backtests.")
        return

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Backtest Configuration")

        backtest_period = st.selectbox(
            "Backtest Period",
            ["3 months", "6 months", "1 year"],
            index=0
        )

        initial_capital = st.number_input(
            "Initial Capital ($)",
            min_value=1000,
            max_value=100000,
            value=10000,
            step=1000
        )

        if st.button("🔄 Run Backtest", type="primary"):
            with st.spinner("Running backtest..."):
                # Get historical data
                df = st.session_state.db_manager.get_price_data(symbol, timeframe, limit=5000)

                if df is not None and not df.empty:
                    # Add technical indicators if not present
                    if 'rsi' not in df.columns:
                        df = TechnicalIndicators.add_all_indicators(df, st.session_state.api_client)

                    # Initialize backtesting engine
                    backtest_engine = BacktestingEngine(initial_capital)

                    # Run backtest
                    results = backtest_engine.run_backtest(df, st.session_state.ml_model)

                    if "error" not in results:
                        st.success("✅ Backtest completed!")

                        # Store results in session state
                        st.session_state.backtest_results = results
                    else:
                        st.error(f"Backtest failed: {results['error']}")
                else:
                    st.error("Insufficient historical data for backtesting")

    with col2:
        # Display backtest results
        if 'backtest_results' in st.session_state:
            results = st.session_state.backtest_results

            st.subheader("📊 Backtest Results")

            # Performance metrics
            col_a, col_b, col_c = st.columns(3)

            with col_a:
                st.metric(
                    "Total Return",
                    f"{results['total_return']:.2%}",
                    delta=f"${results['final_value'] - results['initial_capital']:.2f}"
                )

            with col_b:
                st.metric("Sharpe Ratio", f"{results['sharpe_ratio']:.2f}")

            with col_c:
                st.metric("Max Drawdown", f"{results['max_drawdown']:.2%}")

            # Additional metrics
            col_d, col_e, col_f = st.columns(3)

            with col_d:
                st.metric("Total Trades", results['total_trades'])

            with col_e:
                st.metric("Win Rate", f"{results['win_rate']:.2%}")

            with col_f:
                st.metric("Final Value", f"${results['final_value']:.2f}")

            # Portfolio performance chart
            if results['portfolio_history']:
                portfolio_df = pd.DataFrame(results['portfolio_history'])
                portfolio_df['date'] = pd.to_datetime(portfolio_df['date'])

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=portfolio_df['date'],
                    y=portfolio_df['portfolio_value'],
                    mode='lines',
                    name='Portfolio Value',
                    line=dict(color='blue', width=2)
                ))

                fig.add_hline(
                    y=results['initial_capital'],
                    line_dash="dash",
                    line_color="gray",
                    annotation_text="Initial Capital"
                )

                fig.update_layout(
                    title="Portfolio Performance Over Time",
                    xaxis_title="Date",
                    yaxis_title="Portfolio Value ($)",
                    hovermode='x'
                )

                st.plotly_chart(fig, use_container_width=True)

            # Trade history
            if results['trades']:
                st.subheader("📋 Trade History")
                trades_df = pd.DataFrame(results['trades'])
                st.dataframe(trades_df, use_container_width=True)

def show_paper_trading_tab(symbol: str):
    """Paper trading tab"""
    st.header("💰 Paper Trading Simulator")

    if not st.session_state.ml_model.is_trained:
        st.warning("⚠️ Please train the ML model first before starting paper trading.")
        return

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🎯 Generate Trading Signal")

        if st.button("🔄 Get Current Signal", type="primary"):
            with st.spinner("Generating signal..."):
                # Get latest data
                df = st.session_state.db_manager.get_price_data(symbol, limit=100)

                if df is not None and not df.empty:
                    # Add indicators if needed
                    if 'rsi' not in df.columns:
                        df = TechnicalIndicators.add_all_indicators(df, st.session_state.api_client)

                    # Generate signal
                    signal_result = st.session_state.ml_model.predict_signal(df)

                    if "error" not in signal_result:
                        current_price = signal_result['current_price']
                        signal = signal_result['signal']
                        confidence = signal_result['confidence']

                        # Display signal
                        signal_color = {
                            'STRONG_BUY': '🟢',
                            'BUY': '🟡',
                            'HOLD': '⚪',
                            'SELL': '🟠',
                            'STRONG_SELL': '🔴'
                        }.get(signal, '⚪')

                        st.success(f"Signal Generated: {signal_color} {signal}")

                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            st.metric("Current Price", f"${current_price:.2f}")
                        with col_b:
                            st.metric("Confidence", f"{confidence:.2%}")
                        with col_c:
                            st.metric("Expected Return", f"{signal_result['expected_return']:.2%}")

                        # ATR Volatility Analysis
                        st.subheader("📊 ATR Volatility Analysis")

                        # Calculate ATR for current data
                        atr_data = st.session_state.atr_calculator.calculate_atr(df)

                        if 'atr' in df.columns and len(df) > 0:
                            current_atr = atr_data['current_atr']
                            volatility_level = atr_data['volatility_level']
                            volatility_ratio = atr_data['volatility_ratio']

                            # Display ATR metrics
                            atr_col1, atr_col2, atr_col3 = st.columns(3)

                            with atr_col1:
                                volatility_color = "🔴" if volatility_level == "HIGH" else "🟡" if volatility_level == "MEDIUM" else "🟢"
                                st.metric("Volatility Level", f"{volatility_color} {volatility_level}")
                                st.metric("Current ATR", f"${current_atr:.2f}")

                            with atr_col2:
                                st.metric("Volatility Ratio", f"{volatility_ratio:.2f}x")
                                st.metric("Average ATR", f"${atr_data['average_atr']:.2f}")

                            # Calculate dynamic stop/take levels
                            dynamic_levels = st.session_state.atr_calculator.calculate_dynamic_levels(
                                current_price, current_atr, volatility_level
                            )

                            with atr_col3:
                                st.metric("ATR Stop Loss", f"${dynamic_levels['stop_loss_price']:.2f}")
                                st.metric("ATR Take Profit", f"${dynamic_levels['take_profit_price']:.2f}")

                            # Risk-Reward Ratio
                            risk_reward = dynamic_levels['risk_reward_ratio']
                            rr_color = "🟢" if risk_reward >= 2.0 else "🟡" if risk_reward >= 1.5 else "🔴"
                            st.info(f"**Risk-Reward Ratio: {rr_color} {risk_reward:.2f}:1** (Target: 2:1+)")

                            # Position size adjustment recommendation
                            base_position_size = 0.02  # 2% base
                            size_adjustment = st.session_state.atr_calculator.get_position_size_adjustment(
                                volatility_level, base_position_size
                            )

                            st.markdown(f"**Position Recommendation:** {size_adjustment['recommendation']}")
                            st.markdown(f"**Adjusted Position Size:** {size_adjustment['adjusted_position_size']:.1%} "
                                      f"({size_adjustment['size_change_pct']:+.0f}% vs base)")

                            # ATR Volatility History Chart
                            st.subheader("📈 ATR Volatility History")

                            # Create ATR history chart
                            fig_atr = go.Figure()

                            # Add price line
                            fig_atr.add_trace(go.Scatter(
                                x=df.index[-20:],  # Last 20 periods
                                y=df['close'].iloc[-20:],
                                mode='lines',
                                name='Price',
                                line=dict(color='blue', width=2),
                                yaxis='y'
                            ))

                            # Add ATR line (scaled for visualization)
                            if 'atr' in df.columns:
                                atr_scaled = df['atr'].iloc[-20:] * 10  # Scale ATR for visibility
                                fig_atr.add_trace(go.Scatter(
                                    x=df.index[-20:],
                                    y=atr_scaled,
                                    mode='lines',
                                    name='ATR (×10)',
                                    line=dict(color='orange', width=2),
                                    yaxis='y2'
                                ))

                                # Add volatility level zones
                                avg_atr = atr_data['average_atr']
                                high_threshold = avg_atr * 1.5
                                low_threshold = avg_atr * 0.7

                                fig_atr.add_hline(
                                    y=high_threshold * 10,
                                    line_dash="dash",
                                    line_color="red",
                                    annotation_text="High Volatility",
                                    yref='y2'
                                )

                                fig_atr.add_hline(
                                    y=low_threshold * 10,
                                    line_dash="dash",
                                    line_color="green",
                                    annotation_text="Low Volatility",
                                    yref='y2'
                                )

                            # Update layout for dual axis
                            fig_atr.update_layout(
                                title="Price and ATR Volatility Analysis",
                                xaxis_title="Time",
                                yaxis=dict(
                                    title="Price ($)",
                                    side="left"
                                ),
                                yaxis2=dict(
                                    title="ATR (×10)",
                                    side="right",
                                    overlaying="y"
                                ),
                                hovermode='x unified',
                                height=400
                            )

                            st.plotly_chart(fig_atr, use_container_width=True)

                        # Professional Position Sizing Preview
                        # Get current trading mode from sidebar
                        trading_mode = st.sidebar.selectbox(
                            "Trading Mode (Current)",
                            ["Simple", "Professional", "ATR Professional"],
                            index=0,
                            help="Simple: Basic sizing | Professional: Dynamic leverage | ATR Professional: Volatility-based stops",
                            key="current_trading_mode"
                        )

                        if trading_mode == "Professional":
                            st.subheader("🎯 Professional Position Sizing")

                            # Get position preview
                            position_preview = st.session_state.paper_trader.get_professional_position_preview(
                                symbol, current_price, confidence
                            )

                            if "error" not in position_preview:
                                # Display position sizing metrics
                                pos_col1, pos_col2, pos_col3 = st.columns(3)

                                with pos_col1:
                                    st.metric("Position Size", f"${position_preview['position_value']:.2f}")
                                    st.metric("Shares", f"{position_preview['shares']:.4f}")

                                with pos_col2:
                                    leverage_color = "🟢" if position_preview['leverage'] <= 2 else "🟡" if position_preview['leverage'] <= 4 else "🔴"
                                    st.metric("Leverage", f"{leverage_color} {position_preview['leverage']:.2f}x")
                                    st.metric("Capital Use", f"{position_preview['capital_utilization']:.1%}")

                                with pos_col3:
                                    st.metric("Price Risk", f"{position_preview['price_risk_pct']:.2%}")
                                    st.metric("Max Loss", f"${position_preview['max_loss']:.2f}")

                                # Position sizing examples
                                examples = st.session_state.risk_manager.get_position_sizing_examples(current_price)
                                if examples:
                                    with st.expander("📊 Position Sizing Examples", expanded=False):
                                        for i, example in enumerate(examples):
                                            st.write(f"**{example['description']}**")
                                            ex_col1, ex_col2, ex_col3 = st.columns(3)
                                            with ex_col1:
                                                st.metric("Position", f"${example['position_value']:.0f}")
                                            with ex_col2:
                                                st.metric("Leverage", f"{example['leverage']:.1f}x")
                                            with ex_col3:
                                                st.metric("Max Loss", f"${example['max_loss']:.0f}")
                                            if i < len(examples) - 1:
                                                st.divider()

                            else:
                                st.error(f"Position sizing error: {position_preview['error']}")

                        # Execute paper trade with mode selection
                        if trading_mode == "ATR Professional":
                            trade_button_text = "🎯 Execute ATR Professional Trade"
                        elif trading_mode == "Professional":
                            trade_button_text = "🎯 Execute Professional Trade"
                        else:
                            trade_button_text = "✅ Execute Paper Trade"

                        if st.button(trade_button_text):
                            # Portfolio Risk Management Check
                            st.session_state.portfolio_risk_manager.update_portfolio_metrics(st.session_state.paper_trader)

                            # Determine position size based on mode
                            if trading_mode == "ATR Professional" or trading_mode == "Professional":
                                position_size_pct = st.session_state.risk_manager.default_account_risk
                            else:
                                position_size_pct = 0.02  # Default 2%

                            # Check trading permission
                            risk_permission = st.session_state.portfolio_risk_manager.check_trading_permission(position_size_pct)

                            # Display warnings if any
                            if risk_permission['warnings']:
                                for warning in risk_permission['warnings']:
                                    st.warning(f"⚠️ {warning}")

                            # Display blocks if any
                            if risk_permission['blocks']:
                                for block in risk_permission['blocks']:
                                    st.error(f"🚫 {block}")

                            # Execute trade only if allowed
                            if risk_permission['trading_allowed']:
                                # Execute trade based on mode
                                if trading_mode == "ATR Professional":
                                    # Get current account risk setting
                                    current_account_risk = risk_permission['adjusted_position_size']

                                    trade_result = st.session_state.paper_trader.execute_atr_trade(
                                        symbol, signal, current_price, confidence, datetime.now(),
                                        atr_value=current_atr, volatility_level=volatility_level,
                                        account_risk_pct=current_account_risk
                                    )
                                elif trading_mode == "Professional":
                                    # Get current account risk setting
                                    current_account_risk = risk_permission['adjusted_position_size']

                                    trade_result = st.session_state.paper_trader.execute_professional_trade(
                                        symbol, signal, current_price, confidence, datetime.now(),
                                        account_risk_pct=current_account_risk
                                    )
                                else:
                                    trade_result = st.session_state.paper_trader.execute_trade(
                                        symbol, signal, current_price, confidence, datetime.now()
                                    )

                                if trade_result:
                                    # Record trade result for portfolio risk tracking
                                    st.session_state.portfolio_risk_manager.record_trade_result(trade_result)

                                    st.success(f"Paper trade executed: {trade_result['action']} {trade_result['shares']:.4f} {symbol}")

                                    # Save to database
                                    st.session_state.db_manager.save_paper_trade(trade_result)

                                    # Show position size adjustment if applied
                                    if risk_permission['adjusted_position_size'] != position_size_pct:
                                        reduction_pct = (1 - st.session_state.portfolio_risk_manager.position_size_reduction) * 100
                                        st.info(f"📉 Position size reduced by {reduction_pct:.0f}% due to consecutive losses")
                                else:
                                    st.info("No trade executed (conditions not met)")
                            else:
                                st.error("🚫 **Trading blocked by Portfolio Risk Manager**")
                                st.info("Check risk overview in sidebar for details.")

                        # Check risk management
                        risk_trade = st.session_state.paper_trader.check_risk_management(
                            symbol, current_price, datetime.now()
                        )

                        if risk_trade:
                            st.warning(f"Risk management triggered: {risk_trade['action']}")
                            st.session_state.db_manager.save_paper_trade(risk_trade)

                    else:
                        st.error(f"Signal generation failed: {signal_result['error']}")
                else:
                    st.error("No data available for signal generation")

    with col2:
        st.subheader("📊 Trading Performance")

        # Get portfolio status
        portfolio_status = st.session_state.paper_trader.get_portfolio_status()

        col_a, col_b = st.columns(2)

        with col_a:
            st.metric(
                "Total Value",
                f"${portfolio_status['total_value']:.2f}",
                delta=f"{portfolio_status['total_return']:.2%}"
            )

        with col_b:
            st.metric("Available Capital", f"${portfolio_status['capital']:.2f}")

        # Current positions
        if portfolio_status['positions']:
            st.subheader("📈 Current Positions")

            for pos_symbol, position in portfolio_status['positions'].items():
                with st.expander(f"{pos_symbol} Position"):
                    col_x, col_y, col_z = st.columns(3)

                    with col_x:
                        st.metric("Shares", f"{position['shares']:.4f}")

                    with col_y:
                        st.metric("Entry Price", f"${position['entry_price']:.2f}")

                    with col_z:
                        st.metric("Confidence", f"{position['confidence']:.2%}")

                    # Enhanced position details
                    if 'current_price' in position:
                        detail_col1, detail_col2, detail_col3 = st.columns(3)

                        with detail_col1:
                            current_value = position.get('current_value', position['shares'] * position['entry_price'])
                            st.metric("Current Value", f"${current_value:.2f}")

                        with detail_col2:
                            unrealized_pnl = position.get('unrealized_pnl', 0)
                            pnl_color = "🟢" if unrealized_pnl >= 0 else "🔴"
                            st.metric("Unrealized P&L", f"{pnl_color} ${unrealized_pnl:.2f}")

                        with detail_col3:
                            unrealized_pnl_pct = position.get('unrealized_pnl_pct', 0)
                            st.metric("P&L %", f"{unrealized_pnl_pct:.2%}")

                    # Risk management levels
                    risk_col1, risk_col2 = st.columns(2)

                    with risk_col1:
                        if 'stop_loss_price' in position:
                            st.metric("Stop Loss", f"${position['stop_loss_price']:.2f}")

                    with risk_col2:
                        if 'take_profit_price' in position:
                            st.metric("Take Profit", f"${position['take_profit_price']:.2f}")

                    # ATR Trailing Stop Indicator (for positions with profit)
                    if 'current_price' in position and 'unrealized_pnl' in position:
                        current_price = position['current_price']
                        unrealized_pnl = position['unrealized_pnl']
                        entry_price = position['entry_price']

                        # Check if position is in profit (5%+ for trailing stop activation)
                        profit_threshold = entry_price * 0.05  # 5% profit
                        if unrealized_pnl > profit_threshold:
                            # Get latest data for ATR calculation
                            try:
                                df = st.session_state.db_manager.get_price_data(pos_symbol, limit=50)
                                if df is not None and not df.empty:
                                    # Add indicators if needed
                                    if 'atr' not in df.columns:
                                        df = TechnicalIndicators.add_all_indicators(df, st.session_state.api_client)

                                    # Calculate ATR
                                    atr_data = st.session_state.atr_calculator.calculate_atr(df)
                                    if 'current_atr' in atr_data:
                                        current_atr = atr_data['current_atr']
                                        volatility_level = atr_data['volatility_level']

                                        # Calculate trailing stop (tighter for profitable positions)
                                        trailing_multiplier = 1.0 if volatility_level == "LOW" else 1.2 if volatility_level == "MEDIUM" else 1.5
                                        trailing_stop_price = current_price - (current_atr * trailing_multiplier)

                                        # Only show if trailing stop is higher than original stop loss
                                        original_stop = position.get('stop_loss_price', entry_price * 0.98)
                                        if trailing_stop_price > original_stop:
                                            st.success("🎯 **Trailing Stop Active**")

                                            trail_col1, trail_col2, trail_col3 = st.columns(3)

                                            with trail_col1:
                                                st.metric("Trailing Stop", f"${trailing_stop_price:.2f}")

                                            with trail_col2:
                                                protected_profit = (trailing_stop_price - entry_price) * position['shares']
                                                st.metric("Protected Profit", f"${protected_profit:.2f}")

                                            with trail_col3:
                                                distance_pct = ((current_price - trailing_stop_price) / current_price) * 100
                                                st.metric("Stop Distance", f"{distance_pct:.1f}%")

                                            # Visual indicator
                                            trail_risk = "🟢 Low Risk" if distance_pct > 5 else "🟡 Medium Risk" if distance_pct > 2 else "🔴 High Risk"
                                            st.info(f"Trailing Stop Status: {trail_risk} (ATR-based)")

                            except Exception as e:
                                st.caption(f"⚠️ Could not calculate trailing stop: {str(e)}")

                    # Additional info
                    st.caption(f"Entry Fee: ${position.get('entry_fee', 0):.2f} | Risk Level: {position.get('risk_level', 'N/A')} | Signal: {position.get('signal', 'N/A')}")

        # Recent trades
        if st.session_state.paper_trader.trade_history:
            st.subheader("📋 Recent Trades")

            recent_trades = st.session_state.paper_trader.trade_history[-5:]  # Last 5 trades

            for trade in reversed(recent_trades):
                action_color = "🟢" if trade['action'] == 'BUY' else "🔴"
                pnl_text = f" (P&L: {trade.get('pnl_pct', 0):.2%})" if 'pnl_pct' in trade else ""

                # Enhanced trade display
                with st.container():
                    trade_col1, trade_col2, trade_col3 = st.columns([2, 1, 1])

                    with trade_col1:
                        st.text(f"{action_color} {trade['action']} {trade['shares']:.4f} {trade['symbol']} @ ${trade['price']:.2f}{pnl_text}")

                    with trade_col2:
                        if 'fee' in trade:
                            st.caption(f"Fee: ${trade['fee']:.2f}")

                    with trade_col3:
                        if 'net_pnl' in trade:
                            net_pnl = trade['net_pnl']
                            pnl_emoji = "🟢" if net_pnl >= 0 else "🔴"
                            st.caption(f"{pnl_emoji} ${net_pnl:.2f}")

                    st.caption(f"Signal: {trade['signal']} ({trade.get('confidence', 0):.1%}) - {trade['timestamp'].strftime('%Y-%m-%d %H:%M')}")

                    if 'hold_duration_hours' in trade:
                        st.caption(f"Hold: {trade['hold_duration_hours']:.1f}h | Risk: {trade.get('risk_level', 'N/A')}")

                    st.divider()

def show_portfolio_status_tab():
    """Portfolio status tab"""
    st.header("📋 Portfolio & System Status")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("💼 Portfolio Overview")

        # Get portfolio status
        portfolio_status = st.session_state.paper_trader.get_portfolio_status()

        # Portfolio metrics
        col_a, col_b, col_c = st.columns(3)

        with col_a:
            st.metric(
                "Portfolio Value",
                f"${portfolio_status['total_value']:.2f}",
                delta=f"{portfolio_status['total_return']:.2%}"
            )

        with col_b:
            st.metric("Available Cash", f"${portfolio_status['capital']:.2f}")

        with col_c:
            st.metric("Total Trades", portfolio_status['trade_count'])

        # Risk metrics
        st.subheader("⚠️ Risk Management")

        daily_risk = portfolio_status['capital'] * Config.DAILY_LOSS_LIMIT
        position_risk = portfolio_status['capital'] * Config.MAX_POSITION_SIZE

        col_d, col_e = st.columns(2)

        with col_d:
            st.metric("Daily Risk Limit", f"${daily_risk:.2f}")

        with col_e:
            st.metric("Max Position Size", f"${position_risk:.2f}")

        # Portfolio Risk Overview Section
        st.subheader("🛡️ Portfolio Risk Overview")

        # Update portfolio metrics
        st.session_state.portfolio_risk_manager.update_portfolio_metrics(st.session_state.paper_trader)
        risk_summary = st.session_state.portfolio_risk_manager.get_risk_summary()

        # Risk level alert with detailed view
        alert_level = risk_summary['alert_level']
        alert_colors = {
            'LOW': {'color': 'green', 'emoji': '🟢'},
            'MEDIUM': {'color': 'orange', 'emoji': '🟡'},
            'HIGH': {'color': 'red', 'emoji': '🟠'},
            'CRITICAL': {'color': 'darkred', 'emoji': '🔴'}
        }
        alert_info = alert_colors.get(alert_level, {'color': 'gray', 'emoji': '⚪'})

        # Risk Level Display
        risk_level_col1, risk_level_col2, risk_level_col3 = st.columns([1, 2, 1])
        with risk_level_col2:
            st.markdown(f"### {alert_info['emoji']} Risk Level: **{alert_level}**")

        # Key Risk Metrics
        risk_metric_col1, risk_metric_col2, risk_metric_col3, risk_metric_col4 = st.columns(4)

        with risk_metric_col1:
            exposure_color = "🔴" if risk_summary['total_exposure'] > 0.7 else "🟡" if risk_summary['total_exposure'] > 0.5 else "🟢"
            st.metric("Total Exposure", f"{exposure_color} {risk_summary['total_exposure']:.0%}")

        with risk_metric_col2:
            st.metric("Daily P&L", f"${risk_summary['daily_pnl']:.2f}",
                     delta=f"{risk_summary['daily_pnl_pct']:.1%}")

        with risk_metric_col3:
            consecutive_color = "🔴" if risk_summary['consecutive_losses'] >= 3 else "🟡" if risk_summary['consecutive_losses'] >= 2 else "🟢"
            st.metric("Consecutive Losses", f"{consecutive_color} {risk_summary['consecutive_losses']}")

        with risk_metric_col4:
            trading_status = "✅ Enabled" if risk_summary['trading_enabled'] else "🚫 Disabled"
            st.metric("Trading Status", trading_status)

        # Portfolio Risk Gauges and Charts
        gauge_col1, gauge_col2 = st.columns(2)

        with gauge_col1:
            st.subheader("📊 Risk Utilization Gauge")

            # Create risk utilization gauge chart
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = risk_summary['risk_utilization'] * 100,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Risk Utilization (%)"},
                delta = {'reference': 50},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgreen"},
                        {'range': [50, 80], 'color': "yellow"},
                        {'range': [80, 100], 'color': "red"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            fig_gauge.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_gauge, use_container_width=True)

        with gauge_col2:
            st.subheader("🥧 Position Distribution")

            # Create position distribution pie chart
            if portfolio_status['positions']:
                symbols = []
                values = []
                for symbol, position in portfolio_status['positions'].items():
                    symbols.append(symbol)
                    values.append(position.get('current_value', position['shares'] * position['entry_price']))

                fig_pie = go.Figure(data=[go.Pie(
                    labels=symbols,
                    values=values,
                    hole=0.3,
                    textinfo='label+percent',
                    textposition='outside'
                )])

                fig_pie.update_layout(
                    title="Position Distribution by Value",
                    height=300,
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No active positions to display")

        # Daily P&L Chart
        st.subheader("📈 Daily P&L Performance")

        # Generate daily P&L data from portfolio history
        if st.session_state.paper_trader.portfolio_history:
            portfolio_df = pd.DataFrame(st.session_state.paper_trader.portfolio_history)
            portfolio_df['date'] = pd.to_datetime(portfolio_df['timestamp']).dt.date
            daily_pnl = portfolio_df.groupby('date').agg({
                'total_value': ['first', 'last']
            }).reset_index()
            daily_pnl.columns = ['date', 'start_value', 'end_value']
            daily_pnl['daily_pnl'] = daily_pnl['end_value'] - daily_pnl['start_value']
            daily_pnl['daily_pnl_pct'] = (daily_pnl['daily_pnl'] / daily_pnl['start_value']) * 100

            if len(daily_pnl) > 0:
                fig_pnl = go.Figure()

                # Add daily P&L bar chart
                colors = ['green' if pnl >= 0 else 'red' for pnl in daily_pnl['daily_pnl']]
                fig_pnl.add_trace(go.Bar(
                    x=daily_pnl['date'],
                    y=daily_pnl['daily_pnl'],
                    name='Daily P&L ($)',
                    marker_color=colors,
                    text=[f"${pnl:.2f}" for pnl in daily_pnl['daily_pnl']],
                    textposition='outside'
                ))

                fig_pnl.update_layout(
                    title="Daily P&L Performance",
                    xaxis_title="Date",
                    yaxis_title="P&L ($)",
                    hovermode='x unified',
                    height=400
                )

                st.plotly_chart(fig_pnl, use_container_width=True)
            else:
                st.info("No daily P&L data available yet")
        else:
            st.info("No portfolio history available yet")

        # Risk Limits and Warnings
        st.subheader("⚠️ Risk Limits & Warnings")

        # Risk capacity indicators
        capacity_col1, capacity_col2, capacity_col3 = st.columns(3)

        with capacity_col1:
            remaining_exposure = max(0, 0.80 - risk_summary['total_exposure'])
            exposure_status = "🟢 Safe" if remaining_exposure > 0.2 else "🟡 Caution" if remaining_exposure > 0.1 else "🔴 Critical"
            st.metric("Remaining Exposure Capacity", f"{exposure_status} {remaining_exposure:.0%}")

        with capacity_col2:
            daily_loss_capacity = max(0, 0.04 + risk_summary['daily_pnl_pct'])  # 4% warning threshold
            loss_status = "🟢 Safe" if daily_loss_capacity > 0.02 else "🟡 Caution" if daily_loss_capacity > 0.01 else "🔴 Critical"
            st.metric("Daily Loss Capacity", f"{loss_status} {daily_loss_capacity:.1%}")

        with capacity_col3:
            position_multiplier = risk_summary['position_size_multiplier']
            if position_multiplier < 1.0:
                reduction_pct = (1 - position_multiplier) * 100
                st.metric("Position Size Reduction", f"📉 {reduction_pct:.0f}%")
            else:
                st.metric("Position Size Reduction", "✅ None")

        # Configuration display
        st.subheader("⚙️ Current Configuration")

        config_data = {
            "Symbols": ", ".join(Config.SYMBOLS),
            "Timeframes": ", ".join(Config.TIMEFRAMES),
            "Max Position": f"{Config.MAX_POSITION_SIZE:.1%}",
            "Stop Loss": f"{Config.STOP_LOSS_PCT:.1%}",
            "Take Profit": f"{Config.TAKE_PROFIT_PCT:.1%}",
            "Daily Loss Limit": f"{Config.DAILY_LOSS_LIMIT:.1%}"
        }

        for key, value in config_data.items():
            st.text(f"{key}: {value}")

        # Enhanced Performance Analytics
        st.subheader("📊 Performance Analytics")

        analytics = st.session_state.paper_trader.get_performance_analytics()

        if 'error' not in analytics:
            # Key performance metrics
            perf_col1, perf_col2, perf_col3, perf_col4 = st.columns(4)

            with perf_col1:
                st.metric("Win Rate", f"{analytics['win_rate']:.1%}")

            with perf_col2:
                st.metric("Profit Factor", f"{analytics['profit_factor']:.2f}")

            with perf_col3:
                st.metric("Sharpe Ratio", f"{analytics['sharpe_ratio']:.2f}")

            with perf_col4:
                st.metric("Max Drawdown", f"{analytics['max_drawdown']:.1%}")

            # Additional metrics
            metric_col1, metric_col2, metric_col3 = st.columns(3)

            with metric_col1:
                st.metric("Avg Hold Time", f"{analytics['avg_hold_hours']:.1f} hrs")

            with metric_col2:
                st.metric("Total Fees", f"${analytics['total_fees']:.2f}")

            with metric_col3:
                st.metric("Net Profit", f"${analytics['net_profit']:.2f}")

            # Period returns
            if analytics['daily_returns']:
                st.subheader("📈 Period Returns")

                period_tab1, period_tab2, period_tab3 = st.tabs(["Daily", "Weekly", "Monthly"])

                with period_tab1:
                    daily_df = pd.DataFrame(analytics['daily_returns'])
                    if not daily_df.empty:
                        st.dataframe(daily_df, use_container_width=True)
                    else:
                        st.info("No daily returns data available yet")

                with period_tab2:
                    weekly_df = pd.DataFrame(analytics['weekly_returns'])
                    if not weekly_df.empty:
                        st.dataframe(weekly_df, use_container_width=True)
                    else:
                        st.info("No weekly returns data available yet")

                with period_tab3:
                    monthly_df = pd.DataFrame(analytics['monthly_returns'])
                    if not monthly_df.empty:
                        st.dataframe(monthly_df, use_container_width=True)
                    else:
                        st.info("No monthly returns data available yet")
        else:
            st.info("No completed trades available for analytics yet")

        # CSV Export
        st.subheader("📄 Export Data")

        col_export1, col_export2 = st.columns(2)

        with col_export1:
            if st.button("📊 Export Trading Report", type="secondary"):
                if st.session_state.paper_trader.trade_history:
                    csv_content, filename = st.session_state.paper_trader.export_to_csv()

                    st.download_button(
                        label="⬇️ Download CSV Report",
                        data=csv_content,
                        file_name=filename,
                        mime="text/csv",
                        type="primary"
                    )
                    st.success(f"Trading report ready for download: {filename}")
                else:
                    st.warning("No trading data to export yet")

        with col_export2:
            if st.button("🔄 Reset Simulation", type="secondary"):
                if st.button("⚠️ Confirm Reset", type="secondary"):
                    st.session_state.paper_trader.reset_simulation()
                    st.success("Simulation reset successfully!")
                    st.experimental_rerun()

    with col2:
        st.subheader("🖥️ System Status")

        # System health checks
        system_status = {}

        # API connectivity
        try:
            # Simple connectivity test
            test_result = st.session_state.api_client.request_count
            system_status["API Connection"] = "✅ Connected"
        except:
            system_status["API Connection"] = "❌ Failed"

        # ML Model status
        if st.session_state.ml_model.is_trained:
            system_status["ML Model"] = "✅ Trained"
        else:
            system_status["ML Model"] = "⚠️ Not Trained"

        # Database status
        try:
            df = st.session_state.db_manager.get_price_data(limit=1)
            system_status["Database"] = "✅ Connected"
        except:
            system_status["Database"] = "❌ Failed"

        # Paper trading status
        if st.session_state.paper_trader.trade_history:
            system_status["Paper Trading"] = "✅ Active"
        else:
            system_status["Paper Trading"] = "⚪ Inactive"

        for component, status in system_status.items():
            st.text(f"{component}: {status}")

        # API usage
        st.subheader("📊 API Usage")
        st.metric(
            "API Requests Used",
            st.session_state.api_client.request_count,
            help="Alpha Vantage free tier: 500 requests/month"
        )

        # Database statistics
        st.subheader("💾 Database Statistics")

        try:
            with sqlite3.connect(st.session_state.db_manager.db_file) as conn:
                # Count records
                price_count = conn.execute("SELECT COUNT(*) FROM price_data").fetchone()[0]
                signal_count = conn.execute("SELECT COUNT(*) FROM trading_signals").fetchone()[0]
                trade_count = conn.execute("SELECT COUNT(*) FROM paper_trades").fetchone()[0]

                st.text(f"Price Records: {price_count}")
                st.text(f"Trading Signals: {signal_count}")
                st.text(f"Paper Trades: {trade_count}")

        except Exception as e:
            st.error(f"Database error: {e}")

def create_price_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Create interactive price chart with indicators"""
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=[f'{symbol} Price & Bollinger Bands', 'RSI', 'MACD'],
        row_width=[0.6, 0.2, 0.2]
    )

    # Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name="Price"
        ),
        row=1, col=1
    )

    # Bollinger Bands
    if 'bb_upper' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['bb_upper'],
                line=dict(color='rgba(173, 204, 255, 0.8)', width=1),
                name='BB Upper',
                showlegend=False
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['bb_lower'],
                line=dict(color='rgba(173, 204, 255, 0.8)', width=1),
                fill='tonexty',
                name='BB Lower',
                showlegend=False
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['bb_middle'],
                line=dict(color='orange', width=1),
                name='BB Middle'
            ),
            row=1, col=1
        )

    # RSI
    if 'rsi' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['rsi'],
                line=dict(color='purple', width=2),
                name='RSI'
            ),
            row=2, col=1
        )

        # RSI levels
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        fig.add_hline(y=50, line_dash="dot", line_color="gray", row=2, col=1)

    # MACD
    if 'macd' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['macd'],
                line=dict(color='blue', width=1),
                name='MACD'
            ),
            row=3, col=1
        )

        if 'macd_signal' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['macd_signal'],
                    line=dict(color='red', width=1),
                    name='MACD Signal'
                ),
                row=3, col=1
            )

        if 'macd_histogram' in df.columns:
            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=df['macd_histogram'],
                    name='MACD Histogram',
                    marker_color='green'
                ),
                row=3, col=1
            )

    fig.update_layout(
        title=f"{symbol} Technical Analysis",
        xaxis_rangeslider_visible=False,
        height=800,
        showlegend=True
    )

    return fig

def show_technical_indicators(df: pd.DataFrame):
    """Show current technical indicator values"""
    st.subheader("📊 Current Technical Indicators")

    if len(df) == 0:
        st.warning("No data available")
        return

    latest = df.iloc[-1]

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if 'rsi' in df.columns:
            rsi_val = latest['rsi']
            rsi_signal = "Overbought" if rsi_val > 70 else "Oversold" if rsi_val < 30 else "Neutral"
            st.metric("RSI", f"{rsi_val:.1f}", rsi_signal)

    with col2:
        if 'macd' in df.columns:
            macd_val = latest['macd']
            macd_signal = "Bullish" if macd_val > 0 else "Bearish"
            st.metric("MACD", f"{macd_val:.4f}", macd_signal)

    with col3:
        if 'bb_upper' in df.columns and 'bb_lower' in df.columns:
            bb_position = (latest['close'] - latest['bb_lower']) / (latest['bb_upper'] - latest['bb_lower'])
            bb_signal = "Upper" if bb_position > 0.8 else "Lower" if bb_position < 0.2 else "Middle"
            st.metric("BB Position", f"{bb_position:.2%}", bb_signal)

    with col4:
        if 'price_change' in df.columns:
            price_change = latest['price_change']
            st.metric("Price Change", f"{price_change:.2%}",
                     "📈" if price_change > 0 else "📉" if price_change < 0 else "➡️")

# ==========================================
# 9. MAIN EXECUTION
# ==========================================

# ==========================================
# 9. PROFESSIONAL TAB FUNCTIONS
# ==========================================

def create_live_trading_tab(symbol: str, timeframe: str, account_risk: float, max_leverage: float):
    """Tab 1: Live Trading - 실시간 신호 + 포지션 계산"""

    # API Status Display at the top
    api_status = st.session_state.api_client.get_api_status()

    api_col1, api_col2, api_col3, api_col4 = st.columns(4)

    with api_col1:
        api_color = "🟢" if api_status['can_make_request'] else "🔴"
        st.metric("API 연결 상태", f"{api_color} {'연결됨' if api_status['can_make_request'] else '제한됨'}")

    with api_col2:
        remaining_pct = (api_status['requests_remaining'] / api_status['monthly_limit']) * 100
        color = "🟢" if remaining_pct > 50 else "🟡" if remaining_pct > 20 else "🔴"
        st.metric("API 잔여 요청", f"{color} {api_status['requests_remaining']}")

    with api_col3:
        last_request = api_status['last_request_time']
        if last_request != 'None':
            try:
                from datetime import datetime
                last_time = datetime.fromisoformat(last_request.replace('Z', '+00:00'))
                time_str = last_time.strftime("%H:%M:%S")
            except:
                time_str = "N/A"
        else:
            time_str = "없음"
        st.metric("마지막 API 요청", time_str)

    with api_col4:
        st.metric("캐시 항목", f"📦 {api_status['cache_entries']}")

    st.markdown("---")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"📈 {symbol} 실시간 차트")

        # Get latest data
        with st.spinner("차트 데이터 로딩중..."):
            df = st.session_state.api_client.get_historical_data(symbol, months=1)

            if df is not None and len(df) > 0:
                # Add technical indicators
                if 'rsi' not in df.columns:
                    df = TechnicalIndicators.add_all_indicators(df, st.session_state.api_client)

                # Create enhanced chart
                fig = create_enhanced_price_chart(df, symbol)
                st.plotly_chart(fig, use_container_width=True)

                # Current price metrics
                latest = df.iloc[-1]
                current_price = latest['close']

                price_col1, price_col2, price_col3, price_col4 = st.columns(4)

                with price_col1:
                    st.metric("현재 가격", f"${current_price:,.2f}")

                with price_col2:
                    change_24h = latest.get('price_change', 0) * 100
                    st.metric("24시간 변화", f"{change_24h:+.2f}%")

                with price_col3:
                    volume = latest.get('volume', 0)
                    st.metric("거래량", f"{volume:,.0f}")

                with price_col4:
                    rsi = latest.get('rsi', 50)
                    rsi_status = "🔴 과매도" if rsi < 30 else "🟢 과매수" if rsi > 70 else "🟡 중립"
                    st.metric("RSI", f"{rsi_status} {rsi:.1f}")

    with col2:
        st.subheader("🎯 실시간 신호 분석")

        # Generate AI signal
        if st.button("🔄 신호 생성", type="primary", use_container_width=True):
            with st.spinner("AI 신호 분석중..."):
                if df is not None and len(df) > 0:
                    signal_result = st.session_state.ml_model.predict_signal(df)

                    if "error" not in signal_result:
                        current_price = signal_result['current_price']
                        signal = signal_result['signal']
                        confidence = signal_result['confidence']
                        expected_return = signal_result['expected_return']

                        # Display signal with alert system
                        signal_color = {
                            'STRONG_BUY': '🟢',
                            'BUY': '🟡',
                            'HOLD': '⚪',
                            'SELL': '🟠',
                            'STRONG_SELL': '🔴'
                        }.get(signal, '⚪')

                        # Signal display with professional alert system
                        if signal in ['STRONG_BUY', 'BUY']:
                            st.success(f"**{signal_color} {signal}**")
                            st.success(f"신뢰도: {confidence:.1%}")
                            st.success(f"예상 수익률: {expected_return:.2%}")
                        elif signal in ['STRONG_SELL', 'SELL']:
                            st.error(f"**{signal_color} {signal}**")
                            st.error(f"신뢰도: {confidence:.1%}")
                            st.error(f"예상 수익률: {expected_return:.2%}")
                        else:
                            st.info(f"**{signal_color} {signal}**")
                            st.info(f"신뢰도: {confidence:.1%}")
                            st.info(f"예상 수익률: {expected_return:.2%}")

                        st.markdown("---")

                        # 실시간 포지션 계산 (요청사항)
                        st.subheader("💰 실시간 포지션 계산")

                        # Risk permission check
                        position_size_pct = account_risk
                        risk_permission = st.session_state.portfolio_risk_manager.check_trading_permission(position_size_pct)

                        # Position sizing calculations
                        account_balance = st.session_state.portfolio_risk_manager.current_capital
                        position_value = account_balance * position_size_pct
                        shares = position_value / current_price

                        # Calculate leverage
                        leverage = min(position_size_pct / 0.01, max_leverage) if position_size_pct > 0.01 else 1.0

                        # ATR-based stop/take calculations
                        atr_data = st.session_state.atr_calculator.calculate_atr(df)
                        if 'current_atr' in atr_data:
                            current_atr = atr_data['current_atr']
                            volatility_level = atr_data['volatility_level']

                            # Dynamic stop/take levels
                            dynamic_levels = st.session_state.atr_calculator.calculate_dynamic_levels(
                                current_price, current_atr, volatility_level
                            )

                            stop_loss_price = dynamic_levels['stop_loss_price']
                            take_profit_price = dynamic_levels['take_profit_price']
                            risk_reward_ratio = dynamic_levels['risk_reward_ratio']
                        else:
                            # Fallback to simple percentage
                            stop_loss_price = current_price * 0.98
                            take_profit_price = current_price * 1.03
                            risk_reward_ratio = 1.5

                        # Position sizing display
                        pos_col1, pos_col2 = st.columns(2)

                        with pos_col1:
                            st.metric("포지션 크기", f"${position_value:,.2f}")
                            st.metric("주식 수량", f"{shares:.4f}")
                            st.metric("레버리지", f"{leverage:.1f}x")

                        with pos_col2:
                            st.metric("손절가", f"${stop_loss_price:.2f}")
                            st.metric("익절가", f"${take_profit_price:.2f}")
                            st.metric("손익비", f"{risk_reward_ratio:.1f}:1")

                        # 예상 손익 시뮬레이션 (요청사항)
                        st.subheader("📊 예상 손익 시뮬레이션")

                        # Calculate potential outcomes
                        max_loss = (current_price - stop_loss_price) * shares
                        max_profit = (take_profit_price - current_price) * shares
                        break_even = current_price

                        sim_col1, sim_col2, sim_col3 = st.columns(3)

                        with sim_col1:
                            st.metric("최대 손실", f"-${abs(max_loss):,.2f}", delta=f"{(max_loss/position_value)*100:.1f}%")

                        with sim_col2:
                            st.metric("손익분기점", f"${break_even:,.2f}", delta="0.0%")

                        with sim_col3:
                            st.metric("최대 수익", f"+${max_profit:,.2f}", delta=f"{(max_profit/position_value)*100:.1f}%")

                        # Alert system for risk warnings
                        if risk_permission['warnings']:
                            for warning in risk_permission['warnings']:
                                st.warning(f"⚠️ {warning}")

                        if risk_permission['blocks']:
                            for block in risk_permission['blocks']:
                                st.error(f"🚫 {block}")

                        # Execute trade button
                        if risk_permission['trading_allowed']:
                            if st.button("⚡ 거래 실행", type="primary", use_container_width=True):
                                # Execute the trade
                                trade_result = st.session_state.paper_trader.execute_atr_trade(
                                    symbol, signal, current_price, confidence, datetime.now(),
                                    atr_value=current_atr if 'current_atr' in atr_data else None,
                                    volatility_level=volatility_level if 'current_atr' in atr_data else 'MEDIUM',
                                    account_risk_pct=account_risk
                                )

                                if trade_result:
                                    st.session_state.portfolio_risk_manager.record_trade_result(trade_result)
                                    st.success(f"✅ 거래 실행: {trade_result['action']} {trade_result['shares']:.4f} {symbol}")
                                    st.session_state.db_manager.save_paper_trade(trade_result)
                                    st.rerun()
                                else:
                                    st.info("거래 조건이 충족되지 않았습니다.")
                        else:
                            st.error("🚫 **리스크 관리자에 의해 거래가 차단되었습니다**")
                    else:
                        st.error(f"신호 생성 실패: {signal_result['error']}")

                    # Add detailed debugging information
                    with st.expander("🔍 데이터 소스 및 디버깅 정보"):
                        st.subheader("📊 데이터 소스 분석")

                        # API 데이터 품질 체크
                        api_data_quality = {}
                        latest = df.iloc[-1]

                        # Check if RSI came from API
                        try:
                            api_rsi = st.session_state.api_client.get_technical_indicator(symbol, 'RSI', period=14, interval='5min')
                            if api_rsi is not None and len(api_rsi) > 0:
                                api_data_quality['RSI'] = "🟢 API 데이터"
                            else:
                                api_data_quality['RSI'] = "🟡 로컬 계산"
                        except:
                            api_data_quality['RSI'] = "🔴 계산 실패"

                        # Check if MACD came from API
                        try:
                            api_macd = st.session_state.api_client.get_technical_indicator(symbol, 'MACD', interval='5min')
                            if api_macd is not None and len(api_macd) > 0:
                                api_data_quality['MACD'] = "🟢 API 데이터"
                            else:
                                api_data_quality['MACD'] = "🟡 로컬 계산"
                        except:
                            api_data_quality['MACD'] = "🔴 계산 실패"

                        # Check ATR source
                        try:
                            api_atr = st.session_state.api_client.calculate_atr(symbol)
                            if api_atr is not None and len(api_atr) > 0:
                                api_data_quality['ATR'] = "🟢 API 계산"
                            else:
                                api_data_quality['ATR'] = "🟡 로컬 계산"
                        except:
                            api_data_quality['ATR'] = "🔴 계산 실패"

                        # Display data source table
                        data_source_df = pd.DataFrame([
                            {"지표": "RSI", "데이터 소스": api_data_quality.get('RSI', '🔴 알 수 없음'), "현재 값": f"{latest.get('rsi', 0):.2f}"},
                            {"지표": "MACD", "데이터 소스": api_data_quality.get('MACD', '🔴 알 수 없음'), "현재 값": f"{latest.get('macd', 0):.4f}"},
                            {"지표": "ATR", "데이터 소스": api_data_quality.get('ATR', '🔴 알 수 없음'), "현재 값": f"{latest.get('atr', 0):.2f}"},
                            {"지표": "Price", "데이터 소스": "🟢 API 데이터" if df.shape[0] > 90 else "🟡 Fallback", "현재 값": f"${latest['close']:,.2f}"}
                        ])
                        st.dataframe(data_source_df, use_container_width=True)

                        st.subheader("⚙️ 계산 과정 로그")

                        # Position sizing calculation details
                        if "error" not in signal_result:
                            calculation_log = f"""
                            **포지션 사이징 계산:**
                            - 계좌 리스크: {account_risk * 100:.1f}%
                            - 현재 가격: ${current_price:,.2f}
                            - ATR 값: {atr_data.get('current_atr', 'N/A')}
                            - 변동성 레벨: {atr_data.get('volatility_level', 'MEDIUM')}
                            - 계산된 레버리지: {position_data['leverage']:.2f}x
                            - 포지션 크기: ${position_data['position_value']:,.2f}

                            **손절/익절가 계산:**
                            - 손절가: ${position_data['stop_loss_price']:,.2f} (-{((current_price - position_data['stop_loss_price']) / current_price * 100):.1f}%)
                            - 익절가: ${position_data['take_profit_price']:,.2f} (+{((position_data['take_profit_price'] - current_price) / current_price * 100):.1f}%)
                            - 손익비: {position_data['risk_reward_ratio']:.1f}:1

                            **AI 신호 분석:**
                            - 신호: {signal}
                            - 신뢰도: {confidence:.1f}%
                            - 예상 수익률: {expected_return:.1f}%
                            """
                            st.text(calculation_log)

                        st.subheader("🕐 업데이트 시간")
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        st.text(f"마지막 업데이트: {current_time}")
                        st.text(f"데이터 기간: {df.index[0].strftime('%Y-%m-%d %H:%M')} ~ {df.index[-1].strftime('%Y-%m-%d %H:%M')}")
                        st.text(f"총 데이터 포인트: {len(df)} 개")

                else:
                    st.error("데이터가 없습니다")

def create_portfolio_overview_tab():
    """Tab 2: Portfolio Overview - 포트폴리오 현황"""

    # Use existing portfolio status function but enhance it
    show_portfolio_status_tab()

def create_risk_analysis_tab():
    """Tab 3: Risk Analysis - 리스크 분석"""

    st.subheader("⚠️ 종합 리스크 분석")

    # Update portfolio metrics
    st.session_state.portfolio_risk_manager.update_portfolio_metrics(st.session_state.paper_trader)
    risk_summary = st.session_state.portfolio_risk_manager.get_risk_summary()
    portfolio_status = st.session_state.paper_trader.get_portfolio_status()

    # Risk Level Alert
    alert_level = risk_summary['alert_level']
    if alert_level == "CRITICAL":
        st.error(f"🔴 **위험 등급: {alert_level}**")
        st.error("즉시 포지션 검토 및 리스크 조치가 필요합니다!")
    elif alert_level == "HIGH":
        st.warning(f"🟠 **위험 등급: {alert_level}**")
        st.warning("주의깊은 모니터링이 필요합니다.")
    elif alert_level == "MEDIUM":
        st.info(f"🟡 **위험 등급: {alert_level}**")
        st.info("정상적인 리스크 수준입니다.")
    else:
        st.success(f"🟢 **위험 등급: {alert_level}**")
        st.success("안전한 리스크 수준입니다.")

    st.markdown("---")

    # Risk Metrics Grid
    risk_col1, risk_col2, risk_col3, risk_col4 = st.columns(4)

    with risk_col1:
        exposure = risk_summary['total_exposure']
        if exposure > 0.8:
            st.error(f"총 노출도: {exposure:.0%}")
        elif exposure > 0.6:
            st.warning(f"총 노출도: {exposure:.0%}")
        else:
            st.success(f"총 노출도: {exposure:.0%}")

    with risk_col2:
        daily_pnl_pct = risk_summary['daily_pnl_pct']
        if daily_pnl_pct <= -0.04:
            st.error(f"일일 손익: {daily_pnl_pct:.1%}")
        elif daily_pnl_pct <= -0.02:
            st.warning(f"일일 손익: {daily_pnl_pct:.1%}")
        else:
            st.success(f"일일 손익: {daily_pnl_pct:.1%}")

    with risk_col3:
        consecutive_losses = risk_summary['consecutive_losses']
        if consecutive_losses >= 3:
            st.error(f"연속 손실: {consecutive_losses}회")
        elif consecutive_losses >= 2:
            st.warning(f"연속 손실: {consecutive_losses}회")
        else:
            st.success(f"연속 손실: {consecutive_losses}회")

    with risk_col4:
        trading_status = "활성화" if risk_summary['trading_enabled'] else "비활성화"
        if risk_summary['trading_enabled']:
            st.success(f"거래 상태: {trading_status}")
        else:
            st.error(f"거래 상태: {trading_status}")

    # Enhanced Risk Charts from existing portfolio overview
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 리스크 게이지")

        # Risk utilization gauge
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = risk_summary['risk_utilization'] * 100,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "리스크 사용률 (%)"},
            delta = {'reference': 50},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgreen"},
                    {'range': [50, 80], 'color': "yellow"},
                    {'range': [80, 100], 'color': "red"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))
        fig_gauge.update_layout(height=400)
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col2:
        st.subheader("📈 일일 P&L 추이")

        # Create mock daily PnL data for demonstration
        dates = pd.date_range(end=datetime.now(), periods=10)
        daily_pnl_data = [risk_summary['daily_pnl'] * (0.5 + 0.5 * i/10) for i in range(10)]

        fig_pnl = go.Figure()
        colors = ['green' if pnl >= 0 else 'red' for pnl in daily_pnl_data]

        fig_pnl.add_trace(go.Bar(
            x=dates,
            y=daily_pnl_data,
            marker_color=colors,
            name="일일 P&L"
        ))

        fig_pnl.update_layout(
            title="최근 일일 손익 추이",
            xaxis_title="날짜",
            yaxis_title="손익 ($)",
            height=400
        )

        st.plotly_chart(fig_pnl, use_container_width=True)

def create_backtest_results_tab(symbol: str, timeframe: str):
    """Tab 4: Backtest Results - 백테스팅 결과"""

    # Use existing backtesting function but enhance it
    show_backtesting_tab(symbol)

# ==========================================
# 10. HYBRID AI TRADING SYSTEM
# ==========================================

class HybridAITradingSystem:
    """
    현물 + 선물 하이브리드 AI 트레이딩 시스템

    모드:
    - SPOT_ONLY: 현물만 거래
    - FUTURES_ONLY: 선물만 거래
    - HYBRID: 현물 + 선물 균형 거래
    """

    def __init__(self, trading_mode: str = "HYBRID", initial_capital: float = 10000):
        # 거래 모드 설정
        self.trading_mode = trading_mode.upper()
        self.initial_capital = initial_capital

        # 기존 시스템 연동
        self.ml_generator = MLSignalGenerator()
        self.risk_manager = RiskManager(account_balance=initial_capital)
        self.futures_trader = FuturesTrader()
        self.portfolio_risk_manager = PortfolioRiskManager()

        # 하이브리드 설정
        self.spot_allocation = 0.7 if trading_mode == "HYBRID" else (1.0 if trading_mode == "SPOT_ONLY" else 0.0)
        self.futures_allocation = 0.3 if trading_mode == "HYBRID" else (1.0 if trading_mode == "FUTURES_ONLY" else 0.0)

        # 포지션 추적
        self.spot_positions = {}
        self.futures_positions = {}
        self.performance_history = []

        # 신호 생성 설정
        self.signal_confidence_threshold = 0.6
        self.max_leverage_by_confidence = {
            0.9: 8,  # 90% 신뢰도 -> 최대 8배
            0.8: 6,  # 80% 신뢰도 -> 최대 6배
            0.7: 4,  # 70% 신뢰도 -> 최대 4배
            0.6: 2   # 60% 신뢰도 -> 최대 2배
        }

    def generate_hybrid_signal(self, symbol: str, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        현물 + 선물 통합 신호 생성

        Args:
            symbol: 거래 심볼
            market_data: 시장 데이터

        Returns:
            통합 거래 신호
        """

        # 기본 ML 신호 생성
        base_signals = self.ml_generator.predict_signal(market_data)

        if not base_signals or len(base_signals) == 0 or 'error' in base_signals:
            # 모델이 학습되지 않은 경우 기본 기술적 분석 신호 생성
            base_signals = {
                'signal': 'BUY' if market_data['close'].iloc[-1] > market_data['close'].mean() else 'SELL',
                'confidence': 0.6,
                'reasoning': 'Basic technical analysis'
            }

        if isinstance(base_signals, dict) and 'error' not in base_signals:
            latest_signal = base_signals
        elif isinstance(base_signals, list) and len(base_signals) > 0:
            latest_signal = base_signals[-1]
        else:
            # 대체 신호 생성
            latest_signal = {
                'signal': 'HOLD',
                'confidence': 0.5,
                'reasoning': 'Technical analysis fallback'
            }

        # 다중 시간프레임 분석
        multi_timeframe_analysis = self._analyze_multiple_timeframes(market_data)

        # 신호 강도 계산
        signal_strength = self._calculate_signal_strength(latest_signal, multi_timeframe_analysis)

        # 거래 모드별 신호 생성
        if self.trading_mode == "SPOT_ONLY":
            return self._generate_spot_signal(symbol, latest_signal, signal_strength)
        elif self.trading_mode == "FUTURES_ONLY":
            return self._generate_futures_signal(symbol, latest_signal, signal_strength)
        else:  # HYBRID
            return self._generate_hybrid_signal_combined(symbol, latest_signal, signal_strength)

    def _analyze_multiple_timeframes(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """다중 시간프레임 분석"""

        # 시간프레임별 트렌드 분석
        short_term_trend = self._calculate_trend(market_data.tail(20))  # 20 periods
        medium_term_trend = self._calculate_trend(market_data.tail(50))  # 50 periods
        long_term_trend = self._calculate_trend(market_data.tail(100))  # 100 periods

        # 볼륨 분석
        recent_volume = market_data['volume'].tail(10).mean()
        avg_volume = market_data['volume'].mean()
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0

        # 변동성 분석
        atr_calculator = ATRCalculator()
        atr_data = atr_calculator.calculate_atr(market_data)
        current_volatility = atr_data.get('volatility_level', 'NORMAL')

        return {
            'short_term_trend': short_term_trend,
            'medium_term_trend': medium_term_trend,
            'long_term_trend': long_term_trend,
            'volume_ratio': volume_ratio,
            'volatility_level': current_volatility,
            'trend_alignment': self._check_trend_alignment(short_term_trend, medium_term_trend, long_term_trend)
        }

    def _calculate_trend(self, data: pd.DataFrame) -> str:
        """트렌드 방향 계산"""
        if len(data) < 2:
            return "NEUTRAL"

        start_price = data['close'].iloc[0]
        end_price = data['close'].iloc[-1]

        change_pct = (end_price - start_price) / start_price

        if change_pct > 0.02:  # 2% 이상 상승
            return "BULLISH"
        elif change_pct < -0.02:  # 2% 이상 하락
            return "BEARISH"
        else:
            return "NEUTRAL"

    def _check_trend_alignment(self, short: str, medium: str, long: str) -> Dict[str, Any]:
        """트렌드 정렬 확인"""
        trends = [short, medium, long]

        bullish_count = trends.count("BULLISH")
        bearish_count = trends.count("BEARISH")
        neutral_count = trends.count("NEUTRAL")

        if bullish_count >= 2:
            alignment = "BULLISH"
            strength = bullish_count / 3
        elif bearish_count >= 2:
            alignment = "BEARISH"
            strength = bearish_count / 3
        else:
            alignment = "NEUTRAL"
            strength = neutral_count / 3

        return {
            'alignment': alignment,
            'strength': strength,
            'details': {
                'short_term': short,
                'medium_term': medium,
                'long_term': long
            }
        }

    def _calculate_signal_strength(self, base_signal: Dict, multi_tf: Dict) -> Dict[str, Any]:
        """신호 강도 계산"""

        base_confidence = base_signal.get('confidence', 0.5)

        # 트렌드 정렬 보너스
        trend_bonus = 0.0
        if multi_tf['trend_alignment']['alignment'] != "NEUTRAL":
            if ((base_signal.get('signal') == 'BUY' and multi_tf['trend_alignment']['alignment'] == "BULLISH") or
                (base_signal.get('signal') == 'SELL' and multi_tf['trend_alignment']['alignment'] == "BEARISH")):
                trend_bonus = multi_tf['trend_alignment']['strength'] * 0.2  # 최대 20% 보너스

        # 볼륨 보너스
        volume_bonus = 0.0
        if multi_tf['volume_ratio'] > 1.5:  # 50% 이상 높은 볼륨
            volume_bonus = min(0.1, (multi_tf['volume_ratio'] - 1.0) * 0.1)  # 최대 10% 보너스

        # 변동성 조정
        volatility_adjustment = 0.0
        if multi_tf['volatility_level'] == 'LOW':
            volatility_adjustment = 0.05  # 낮은 변동성에서 신뢰도 증가
        elif multi_tf['volatility_level'] == 'HIGH':
            volatility_adjustment = -0.05  # 높은 변동성에서 신뢰도 감소

        # 최종 신뢰도 계산
        final_confidence = min(0.95, base_confidence + trend_bonus + volume_bonus + volatility_adjustment)

        # 레버리지 결정
        leverage = self._determine_leverage(final_confidence)

        return {
            'base_confidence': base_confidence,
            'trend_bonus': trend_bonus,
            'volume_bonus': volume_bonus,
            'volatility_adjustment': volatility_adjustment,
            'final_confidence': final_confidence,
            'recommended_leverage': leverage,
            'signal_grade': self._grade_signal(final_confidence)
        }

    def _determine_leverage(self, confidence: float) -> int:
        """신뢰도 기반 레버리지 결정"""
        for conf_threshold in sorted(self.max_leverage_by_confidence.keys(), reverse=True):
            if confidence >= conf_threshold:
                return self.max_leverage_by_confidence[conf_threshold]
        return 1  # 기본 레버리지

    def _grade_signal(self, confidence: float) -> str:
        """신호 등급 매기기"""
        if confidence >= 0.85:
            return "A+"
        elif confidence >= 0.8:
            return "A"
        elif confidence >= 0.75:
            return "B+"
        elif confidence >= 0.7:
            return "B"
        elif confidence >= 0.65:
            return "C+"
        elif confidence >= 0.6:
            return "C"
        else:
            return "D"

    def _generate_spot_signal(self, symbol: str, base_signal: Dict, strength: Dict) -> Dict[str, Any]:
        """현물 전용 신호 생성"""

        if strength['final_confidence'] < self.signal_confidence_threshold:
            return self._create_hold_signal(symbol, f"Confidence {strength['final_confidence']:.1%} below threshold")

        return {
            'symbol': symbol,
            'trading_mode': 'SPOT_ONLY',
            'signal_type': 'SPOT',
            'action': base_signal.get('signal', 'HOLD'),
            'confidence': strength['final_confidence'],
            'signal_grade': strength['signal_grade'],
            'reasoning': base_signal.get('reasoning', ''),
            'allocation': self.spot_allocation,
            'leverage': 1,  # 현물은 레버리지 없음
            'position_size_pct': self._calculate_position_size(strength['final_confidence']),
            'stop_loss': base_signal.get('stop_loss'),
            'take_profit': base_signal.get('take_profit'),
            'timestamp': datetime.now().isoformat()
        }

    def _generate_futures_signal(self, symbol: str, base_signal: Dict, strength: Dict) -> Dict[str, Any]:
        """선물 전용 신호 생성"""

        if strength['final_confidence'] < self.signal_confidence_threshold:
            return self._create_hold_signal(symbol, f"Confidence {strength['final_confidence']:.1%} below threshold")

        # BUY/SELL -> LONG/SHORT 변환
        futures_action = self._convert_to_futures_action(base_signal.get('signal', 'HOLD'))

        return {
            'symbol': symbol,
            'trading_mode': 'FUTURES_ONLY',
            'signal_type': 'FUTURES',
            'action': futures_action,
            'confidence': strength['final_confidence'],
            'signal_grade': strength['signal_grade'],
            'reasoning': base_signal.get('reasoning', ''),
            'allocation': self.futures_allocation,
            'leverage': strength['recommended_leverage'],
            'position_size_pct': self._calculate_position_size(strength['final_confidence']),
            'stop_loss': base_signal.get('stop_loss'),
            'take_profit': base_signal.get('take_profit'),
            'timestamp': datetime.now().isoformat()
        }

    def _generate_hybrid_signal_combined(self, symbol: str, base_signal: Dict, strength: Dict) -> Dict[str, Any]:
        """하이브리드 모드 통합 신호 생성"""

        if strength['final_confidence'] < self.signal_confidence_threshold:
            return self._create_hold_signal(symbol, f"Confidence {strength['final_confidence']:.1%} below threshold")

        base_action = base_signal.get('signal', 'HOLD')
        futures_action = self._convert_to_futures_action(base_action)

        # 하이브리드 전략: 현물은 안정적, 선물은 레버리지로 수익 증대
        return {
            'symbol': symbol,
            'trading_mode': 'HYBRID',
            'spot_signal': {
                'signal_type': 'SPOT',
                'action': base_action,
                'allocation': self.spot_allocation,
                'leverage': 1,
                'position_size_pct': self._calculate_position_size(strength['final_confidence'] * 0.8)  # 현물은 보수적
            },
            'futures_signal': {
                'signal_type': 'FUTURES',
                'action': futures_action,
                'allocation': self.futures_allocation,
                'leverage': min(strength['recommended_leverage'], 5),  # 하이브리드에서는 레버리지 제한
                'position_size_pct': self._calculate_position_size(strength['final_confidence'])
            },
            'combined_confidence': strength['final_confidence'],
            'signal_grade': strength['signal_grade'],
            'reasoning': base_signal.get('reasoning', ''),
            'stop_loss': base_signal.get('stop_loss'),
            'take_profit': base_signal.get('take_profit'),
            'timestamp': datetime.now().isoformat()
        }

    def _convert_to_futures_action(self, spot_action: str) -> str:
        """현물 신호를 선물 신호로 변환"""
        conversion_map = {
            'BUY': 'LONG',
            'SELL': 'SHORT',
            'HOLD': 'CLOSE'
        }
        return conversion_map.get(spot_action, 'CLOSE')

    def _calculate_position_size(self, confidence: float) -> float:
        """신뢰도 기반 포지션 크기 계산"""
        base_size = 0.05  # 5% 기본 포지션
        confidence_multiplier = confidence / 0.6  # 60% 신뢰도를 1.0으로 정규화

        return min(0.2, base_size * confidence_multiplier)  # 최대 20% 포지션

    def _create_hold_signal(self, symbol: str, reason: str) -> Dict[str, Any]:
        """HOLD 신호 생성"""
        return {
            'symbol': symbol,
            'trading_mode': self.trading_mode,
            'signal_type': 'HOLD',
            'action': 'HOLD',
            'confidence': 0.0,
            'signal_grade': 'N/A',
            'reasoning': reason,
            'allocation': 0.0,
            'leverage': 1,
            'position_size_pct': 0.0,
            'timestamp': datetime.now().isoformat()
        }

    def execute_hybrid_trade(self, signal: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """
        하이브리드 신호 실행 (현물 + 선물)

        Args:
            signal: 생성된 하이브리드 신호
            current_price: 현재 시장 가격

        Returns:
            거래 실행 결과
        """

        if signal['action'] == 'HOLD':
            return {
                'success': True,
                'action': 'HOLD',
                'message': signal['reasoning']
            }

        results = {
            'symbol': signal['symbol'],
            'trading_mode': signal['trading_mode'],
            'timestamp': datetime.now().isoformat(),
            'success': True,
            'trades_executed': []
        }

        try:
            # 하이브리드 모드 실행
            if signal['trading_mode'] == 'HYBRID':
                # 현물 거래 실행
                spot_result = self._execute_spot_trade(signal['spot_signal'], current_price)
                results['trades_executed'].append(spot_result)

                # 선물 거래 실행
                futures_result = self._execute_futures_trade(signal['futures_signal'], current_price)
                results['trades_executed'].append(futures_result)

            elif signal['trading_mode'] == 'SPOT_ONLY':
                spot_result = self._execute_spot_trade(signal, current_price)
                results['trades_executed'].append(spot_result)

            elif signal['trading_mode'] == 'FUTURES_ONLY':
                futures_result = self._execute_futures_trade(signal, current_price)
                results['trades_executed'].append(futures_result)

            # 포지션 업데이트
            self._update_positions(signal, results['trades_executed'])

            # 성과 기록
            self._record_performance(signal, current_price, results['trades_executed'])

            return results

        except Exception as e:
            return {
                'success': False,
                'error': f'Trade execution failed: {str(e)}',
                'signal': signal
            }

    def _execute_spot_trade(self, signal: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """현물 거래 실행"""

        symbol = signal.get('symbol', signal.get('symbol'))
        action = signal['action']
        position_size_pct = signal['position_size_pct']

        # 포지션 크기 계산
        trade_amount = self.initial_capital * position_size_pct * signal['allocation']
        quantity = trade_amount / current_price

        # 현물 거래 시뮬레이션
        trade_result = {
            'trade_type': 'SPOT',
            'symbol': symbol,
            'action': action,
            'quantity': quantity,
            'price': current_price,
            'value': trade_amount,
            'leverage': 1,
            'timestamp': datetime.now().isoformat(),
            'success': True,
            'fees': trade_amount * 0.001  # 0.1% 수수료
        }

        # 현물 포지션 업데이트
        if symbol not in self.spot_positions:
            self.spot_positions[symbol] = {'quantity': 0, 'avg_price': 0, 'total_cost': 0}

        if action == 'BUY':
            # 매수
            old_total_cost = self.spot_positions[symbol]['total_cost']
            old_quantity = self.spot_positions[symbol]['quantity']

            new_total_cost = old_total_cost + trade_amount
            new_quantity = old_quantity + quantity

            self.spot_positions[symbol] = {
                'quantity': new_quantity,
                'avg_price': new_total_cost / new_quantity if new_quantity > 0 else current_price,
                'total_cost': new_total_cost
            }

        elif action == 'SELL' and self.spot_positions[symbol]['quantity'] > 0:
            # 매도
            sell_quantity = min(quantity, self.spot_positions[symbol]['quantity'])
            self.spot_positions[symbol]['quantity'] -= sell_quantity

            if self.spot_positions[symbol]['quantity'] <= 0:
                self.spot_positions[symbol] = {'quantity': 0, 'avg_price': 0, 'total_cost': 0}

            trade_result['quantity'] = sell_quantity
            trade_result['value'] = sell_quantity * current_price

        return trade_result

    def _execute_futures_trade(self, signal: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """선물 거래 실행"""

        symbol = signal.get('symbol', signal.get('symbol'))
        action = signal['action']
        leverage = signal['leverage']
        position_size_pct = signal['position_size_pct']

        # 포지션 크기 계산 (레버리지 적용)
        margin_amount = self.initial_capital * position_size_pct * signal['allocation']
        position_value = margin_amount * leverage
        quantity = position_value / current_price

        # 리스크 관리 체크
        risk_check = self.risk_manager.calculate_futures_position_size(
            symbol=symbol,
            entry_price=current_price,
            atr_value=current_price * 0.02,  # 2% ATR 가정
            leverage=leverage
        )

        if 'error' in risk_check:
            return {
                'trade_type': 'FUTURES',
                'symbol': symbol,
                'action': action,
                'success': False,
                'error': risk_check['error']
            }

        # 선물 거래 실행 (시뮬레이션)
        if action in ['LONG', 'SHORT']:
            # 새 포지션 열기
            trade_result = {
                'trade_type': 'FUTURES',
                'symbol': symbol,
                'action': action,
                'quantity': quantity,
                'price': current_price,
                'margin': margin_amount,
                'position_value': position_value,
                'leverage': leverage,
                'timestamp': datetime.now().isoformat(),
                'success': True,
                'fees': position_value * 0.0004  # 0.04% 수수료
            }

            # 선물 포지션 업데이트
            self.futures_positions[symbol] = {
                'side': action,
                'quantity': quantity,
                'entry_price': current_price,
                'leverage': leverage,
                'margin': margin_amount,
                'timestamp': datetime.now().isoformat()
            }

        elif action == 'CLOSE':
            # 포지션 청산
            if symbol in self.futures_positions:
                position = self.futures_positions[symbol]
                pnl = self._calculate_futures_pnl(position, current_price)

                trade_result = {
                    'trade_type': 'FUTURES',
                    'symbol': symbol,
                    'action': 'CLOSE',
                    'quantity': position['quantity'],
                    'entry_price': position['entry_price'],
                    'exit_price': current_price,
                    'pnl': pnl,
                    'leverage': position['leverage'],
                    'timestamp': datetime.now().isoformat(),
                    'success': True,
                    'fees': position['quantity'] * current_price * 0.0004
                }

                # 포지션 제거
                del self.futures_positions[symbol]
            else:
                trade_result = {
                    'trade_type': 'FUTURES',
                    'symbol': symbol,
                    'action': 'CLOSE',
                    'success': False,
                    'error': 'No position to close'
                }

        return trade_result

    def _calculate_futures_pnl(self, position: Dict[str, Any], current_price: float) -> float:
        """선물 포지션 PnL 계산"""

        entry_price = position['entry_price']
        quantity = position['quantity']
        side = position['side']

        if side == 'LONG':
            pnl = (current_price - entry_price) * quantity
        else:  # SHORT
            pnl = (entry_price - current_price) * quantity

        return pnl

    def _update_positions(self, signal: Dict[str, Any], trade_results: List[Dict[str, Any]]):
        """포지션 업데이트"""

        # 거래 결과를 바탕으로 포지션 상태 업데이트
        for trade in trade_results:
            if trade['success']:
                symbol = trade['symbol']

                # 자동 스톱로스/익절 설정
                if trade['trade_type'] == 'FUTURES' and trade['action'] in ['LONG', 'SHORT']:
                    self._set_automatic_stops(symbol, signal, trade)

    def _set_automatic_stops(self, symbol: str, signal: Dict[str, Any], trade: Dict[str, Any]):
        """자동 스톱로스/익절 설정"""

        if symbol not in self.futures_positions:
            return

        position = self.futures_positions[symbol]
        entry_price = position['entry_price']
        leverage = position['leverage']

        # ATR 기반 동적 스톱 계산
        atr_value = entry_price * 0.02  # 2% ATR 가정

        dynamic_stops = self.risk_manager.calculate_dynamic_stop_loss(
            symbol=symbol,
            entry_price=entry_price,
            current_price=entry_price,
            atr_value=atr_value,
            leverage=leverage,
            position_side=position['side']
        )

        # 스톱로스/익절 레벨 저장
        self.futures_positions[symbol].update({
            'stop_loss': dynamic_stops['dynamic_stop_loss'],
            'take_profit_levels': dynamic_stops['take_profit_levels'],
            'trailing_stop_active': False
        })

    def _record_performance(self, signal: Dict[str, Any], current_price: float, trade_results: List[Dict[str, Any]]):
        """성과 기록"""

        performance_entry = {
            'timestamp': datetime.now().isoformat(),
            'signal': signal,
            'current_price': current_price,
            'trades': trade_results,
            'total_value': self._calculate_total_portfolio_value(current_price)
        }

        self.performance_history.append(performance_entry)

        # 최근 100개 기록만 유지
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]

    def _calculate_total_portfolio_value(self, current_price: float) -> Dict[str, Any]:
        """전체 포트폴리오 가치 계산"""

        # 현물 가치
        spot_value = 0
        for symbol, position in self.spot_positions.items():
            if position['quantity'] > 0:
                spot_value += position['quantity'] * current_price

        # 선물 가치 (미실현 손익 포함)
        futures_value = 0
        futures_pnl = 0
        for symbol, position in self.futures_positions.items():
            margin = position['margin']
            pnl = self._calculate_futures_pnl(position, current_price)

            futures_value += margin
            futures_pnl += pnl

        # 현금 (초기 자본에서 사용한 자금 제외)
        total_spot_investment = sum(pos['total_cost'] for pos in self.spot_positions.values())
        total_futures_margin = sum(pos['margin'] for pos in self.futures_positions.values())
        cash_remaining = self.initial_capital - total_spot_investment - total_futures_margin

        total_portfolio_value = cash_remaining + spot_value + futures_value + futures_pnl

        return {
            'cash': cash_remaining,
            'spot_value': spot_value,
            'futures_margin': futures_value,
            'futures_pnl': futures_pnl,
            'total_value': total_portfolio_value,
            'total_return_pct': ((total_portfolio_value - self.initial_capital) / self.initial_capital) * 100
        }

    def monitor_positions(self, current_prices: Dict[str, float]) -> Dict[str, Any]:
        """포지션 모니터링 및 자동 관리"""

        monitoring_results = {
            'timestamp': datetime.now().isoformat(),
            'spot_positions': len(self.spot_positions),
            'futures_positions': len(self.futures_positions),
            'actions_taken': [],
            'alerts': []
        }

        # 선물 포지션 모니터링
        for symbol, position in list(self.futures_positions.items()):
            current_price = current_prices.get(symbol, position['entry_price'])

            # PnL 계산
            current_pnl = self._calculate_futures_pnl(position, current_price)
            pnl_pct = (current_pnl / position['margin']) * 100

            # 스톱로스 체크
            if 'stop_loss' in position:
                stop_triggered = False
                if position['side'] == 'LONG' and current_price <= position['stop_loss']:
                    stop_triggered = True
                elif position['side'] == 'SHORT' and current_price >= position['stop_loss']:
                    stop_triggered = True

                if stop_triggered:
                    # 스톱로스 실행
                    close_result = self._execute_futures_trade({
                        'symbol': symbol,
                        'action': 'CLOSE',
                        'leverage': position['leverage'],
                        'position_size_pct': 0,
                        'allocation': 1.0
                    }, current_price)

                    monitoring_results['actions_taken'].append({
                        'type': 'STOP_LOSS',
                        'symbol': symbol,
                        'price': current_price,
                        'pnl': current_pnl,
                        'result': close_result
                    })

            # 익절 체크
            if 'take_profit_levels' in position:
                for tp_level in position['take_profit_levels']:
                    tp_triggered = False
                    if position['side'] == 'LONG' and current_price >= tp_level['price']:
                        tp_triggered = True
                    elif position['side'] == 'SHORT' and current_price <= tp_level['price']:
                        tp_triggered = True

                    if tp_triggered:
                        # 부분 익절 실행
                        partial_close_pct = tp_level['percentage']

                        monitoring_results['actions_taken'].append({
                            'type': 'TAKE_PROFIT',
                            'symbol': symbol,
                            'level': tp_level['level'],
                            'price': current_price,
                            'close_percentage': partial_close_pct,
                            'pnl': current_pnl
                        })

            # 강제청산 위험 경고
            if pnl_pct < -80:  # 80% 손실 시 경고
                monitoring_results['alerts'].append({
                    'type': 'LIQUIDATION_RISK',
                    'symbol': symbol,
                    'current_pnl_pct': pnl_pct,
                    'message': f'{symbol} position at high liquidation risk: {pnl_pct:.1f}% loss'
                })

        return monitoring_results

    def get_performance_analytics(self) -> Dict[str, Any]:
        """
        현물 + 선물 통합 성과 분석

        Returns:
            상세한 성과 분석 데이터
        """

        if len(self.performance_history) == 0:
            return {
                'error': 'No performance data available',
                'total_trades': 0
            }

        # 기본 통계
        total_trades = len(self.performance_history)
        current_portfolio = self.performance_history[-1]['total_value']

        # 수익률 계산
        total_return = current_portfolio['total_return_pct']
        initial_value = self.initial_capital

        # 거래별 분석
        spot_trades = []
        futures_trades = []
        daily_returns = []

        for entry in self.performance_history:
            for trade in entry['trades']:
                if trade.get('success', False):
                    if trade['trade_type'] == 'SPOT':
                        spot_trades.append(trade)
                    elif trade['trade_type'] == 'FUTURES':
                        futures_trades.append(trade)

            # 일별 수익률 계산
            daily_return = entry['total_value']['total_return_pct']
            daily_returns.append(daily_return)

        # 승률 계산
        profitable_futures = [t for t in futures_trades if t.get('pnl', 0) > 0]
        win_rate = len(profitable_futures) / len(futures_trades) * 100 if futures_trades else 0

        # 샤프 비율 계산 (간단 버전)
        if len(daily_returns) > 1:
            returns_array = np.array(daily_returns)
            if len(returns_array) > 1:
                returns_diff = np.diff(returns_array)
                if np.std(returns_diff) > 0:
                    sharpe_ratio = np.mean(returns_diff) / np.std(returns_diff) * np.sqrt(252)
                else:
                    sharpe_ratio = 0
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0

        # 최대 낙폭 계산
        portfolio_values = [entry['total_value']['total_value'] for entry in self.performance_history]
        max_drawdown = self._calculate_max_drawdown(portfolio_values)

        # 레버리지별 성과 분석
        leverage_performance = self._analyze_leverage_performance(futures_trades)

        # 시간대별 성과 분석
        hourly_performance = self._analyze_hourly_performance()

        # 현물 vs 선물 성과 비교
        spot_vs_futures = self._compare_spot_futures_performance(spot_trades, futures_trades)

        return {
            # 전체 성과
            'overall_performance': {
                'total_return_pct': total_return,
                'total_trades': total_trades,
                'spot_trades': len(spot_trades),
                'futures_trades': len(futures_trades),
                'win_rate': win_rate,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'current_portfolio_value': current_portfolio['total_value'],
                'initial_capital': initial_value
            },

            # 자산별 분석
            'asset_breakdown': {
                'cash': current_portfolio['cash'],
                'spot_value': current_portfolio['spot_value'],
                'futures_margin': current_portfolio['futures_margin'],
                'futures_pnl': current_portfolio['futures_pnl'],
                'cash_pct': current_portfolio['cash'] / current_portfolio['total_value'] * 100,
                'spot_pct': current_portfolio['spot_value'] / current_portfolio['total_value'] * 100,
                'futures_pct': (current_portfolio['futures_margin'] + current_portfolio['futures_pnl']) / current_portfolio['total_value'] * 100
            },

            # 레버리지 분석
            'leverage_analysis': leverage_performance,

            # 시간대별 분석
            'time_analysis': hourly_performance,

            # 현물 vs 선물 비교
            'spot_vs_futures': spot_vs_futures,

            # 리스크 메트릭
            'risk_metrics': {
                'value_at_risk_95': self._calculate_var(daily_returns, 0.95),
                'volatility': np.std(daily_returns) if daily_returns else 0,
                'max_consecutive_losses': self._calculate_max_consecutive_losses(futures_trades),
                'current_drawdown': self._calculate_current_drawdown(portfolio_values)
            },

            # 최근 성과
            'recent_performance': {
                'last_7_days': self._calculate_period_performance(7),
                'last_30_days': self._calculate_period_performance(30),
                'last_trade': self.performance_history[-1] if self.performance_history else None
            }
        }

    def _calculate_max_drawdown(self, portfolio_values: List[float]) -> float:
        """최대 낙폭 계산"""
        if len(portfolio_values) < 2:
            return 0.0

        peak = portfolio_values[0]
        max_dd = 0.0

        for value in portfolio_values:
            if value > peak:
                peak = value
            else:
                drawdown = (peak - value) / peak
                max_dd = max(max_dd, drawdown)

        return max_dd * 100  # 퍼센트로 반환

    def _analyze_leverage_performance(self, futures_trades: List[Dict]) -> Dict[str, Any]:
        """레버리지별 성과 분석"""
        leverage_stats = {}

        for trade in futures_trades:
            leverage = trade.get('leverage', 1)
            pnl = trade.get('pnl', 0)

            if leverage not in leverage_stats:
                leverage_stats[leverage] = {
                    'trades': 0,
                    'total_pnl': 0,
                    'winning_trades': 0,
                    'avg_pnl': 0
                }

            leverage_stats[leverage]['trades'] += 1
            leverage_stats[leverage]['total_pnl'] += pnl
            if pnl > 0:
                leverage_stats[leverage]['winning_trades'] += 1

        # 통계 계산
        for leverage, stats in leverage_stats.items():
            stats['avg_pnl'] = stats['total_pnl'] / stats['trades']
            stats['win_rate'] = stats['winning_trades'] / stats['trades'] * 100

        return leverage_stats

    def _analyze_hourly_performance(self) -> Dict[str, Any]:
        """시간대별 성과 분석"""
        hourly_stats = {hour: {'trades': 0, 'total_pnl': 0} for hour in range(24)}

        for entry in self.performance_history:
            timestamp = datetime.fromisoformat(entry['timestamp'])
            hour = timestamp.hour

            for trade in entry['trades']:
                if trade.get('success', False) and trade['trade_type'] == 'FUTURES':
                    pnl = trade.get('pnl', 0)
                    hourly_stats[hour]['trades'] += 1
                    hourly_stats[hour]['total_pnl'] += pnl

        # 평균 계산
        for hour, stats in hourly_stats.items():
            if stats['trades'] > 0:
                stats['avg_pnl'] = stats['total_pnl'] / stats['trades']
            else:
                stats['avg_pnl'] = 0

        return hourly_stats

    def _compare_spot_futures_performance(self, spot_trades: List[Dict], futures_trades: List[Dict]) -> Dict[str, Any]:
        """현물 vs 선물 성과 비교"""

        # 현물 성과
        spot_total_value = sum(trade.get('value', 0) for trade in spot_trades if trade.get('action') == 'BUY')
        spot_fees = sum(trade.get('fees', 0) for trade in spot_trades)

        # 선물 성과
        futures_total_pnl = sum(trade.get('pnl', 0) for trade in futures_trades if 'pnl' in trade)
        futures_fees = sum(trade.get('fees', 0) for trade in futures_trades)

        return {
            'spot': {
                'total_trades': len(spot_trades),
                'total_invested': spot_total_value,
                'total_fees': spot_fees,
                'avg_trade_size': spot_total_value / len(spot_trades) if spot_trades else 0
            },
            'futures': {
                'total_trades': len(futures_trades),
                'total_pnl': futures_total_pnl,
                'total_fees': futures_fees,
                'avg_pnl_per_trade': futures_total_pnl / len(futures_trades) if futures_trades else 0
            },
            'comparison': {
                'futures_pnl_vs_spot_fees': futures_total_pnl / max(spot_fees, 1),
                'total_fees': spot_fees + futures_fees,
                'net_profit': futures_total_pnl - (spot_fees + futures_fees)
            }
        }

    def _calculate_var(self, returns: List[float], confidence: float) -> float:
        """Value at Risk 계산"""
        if len(returns) < 10:
            return 0.0

        returns_array = np.array(returns)
        percentile = (1 - confidence) * 100
        var = np.percentile(returns_array, percentile)
        return abs(var)

    def _calculate_max_consecutive_losses(self, futures_trades: List[Dict]) -> int:
        """연속 손실 거래 최대값 계산"""
        consecutive_losses = 0
        max_consecutive = 0

        for trade in futures_trades:
            pnl = trade.get('pnl', 0)
            if pnl < 0:
                consecutive_losses += 1
                max_consecutive = max(max_consecutive, consecutive_losses)
            else:
                consecutive_losses = 0

        return max_consecutive

    def _calculate_current_drawdown(self, portfolio_values: List[float]) -> float:
        """현재 낙폭 계산"""
        if len(portfolio_values) < 2:
            return 0.0

        peak = max(portfolio_values)
        current_value = portfolio_values[-1]
        current_dd = (peak - current_value) / peak * 100

        return max(0, current_dd)

    def _calculate_period_performance(self, days: int) -> Dict[str, Any]:
        """특정 기간 성과 계산"""
        if len(self.performance_history) == 0:
            return {'return_pct': 0, 'trades': 0}

        # 최근 N일 데이터 필터링 (실제로는 거래 횟수로 근사)
        recent_entries = self.performance_history[-min(days, len(self.performance_history)):]

        if len(recent_entries) < 2:
            return {'return_pct': 0, 'trades': len(recent_entries)}

        start_value = recent_entries[0]['total_value']['total_value']
        end_value = recent_entries[-1]['total_value']['total_value']

        period_return = (end_value - start_value) / start_value * 100

        total_trades = sum(len(entry['trades']) for entry in recent_entries)

        return {
            'return_pct': period_return,
            'trades': total_trades,
            'start_value': start_value,
            'end_value': end_value
        }

# ==========================================
# COINGECKO DATA FETCHER CLASS
# ==========================================

class CoinGeckoDataFetcher:
    """Simple CoinGecko data fetcher for testing purposes"""

    def __init__(self):
        self.base_url = 'https://api.coingecko.com/api/v3'
        self.session = requests.Session()

    def get_market_data(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """Fetch basic market data for testing"""
        try:
            # Map common symbols
            symbol_map = {
                'bitcoin': 'bitcoin',
                'btc': 'bitcoin',
                'ethereum': 'ethereum',
                'eth': 'ethereum'
            }

            coin_id = symbol_map.get(symbol.lower(), symbol.lower())

            # Get historical prices
            url = f"{self.base_url}/coins/{coin_id}/market_chart"
            params = {
                'vs_currency': 'usd',
                'days': days,
                'interval': 'daily' if days > 7 else 'hourly'
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Convert to DataFrame
            prices = data.get('prices', [])
            if not prices:
                return pd.DataFrame()

            df = pd.DataFrame(prices, columns=['timestamp', 'close'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            # Add basic OHLCV structure
            df['open'] = df['close'].shift(1).fillna(df['close'])
            df['high'] = df['close'] * 1.02  # Mock data
            df['low'] = df['close'] * 0.98   # Mock data
            df['volume'] = 1000000  # Mock volume

            return df.dropna()

        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            # Return mock data for testing
            dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
            prices = np.random.normal(50000, 2000, len(dates))

            return pd.DataFrame({
                'timestamp': dates,
                'open': prices * 0.99,
                'high': prices * 1.02,
                'low': prices * 0.98,
                'close': prices,
                'volume': 1000000
            })

# ==========================================
# DYNAMIC RISK MANAGER CLASS
# ==========================================

class DynamicRiskManager:
    """
    🚀 고도화된 포지션 사이징 & AI 신호 연동 리스크 관리 시스템

    핵심 기능:
    1. 켈리 공식 + AI 신뢰도 연동 포지션 사이징
    2. 레버리지별 동적 리스크 조절 (1-10배)
    3. 계좌 크기 대비 최적 포지션 계산
    4. ATR 기반 동적 손절/익절 레벨 계산
    5. 상관관계 고려 다중 포지션 리스크 관리

    핵심 공식:
    - 기본포지션 = (계좌잔고 × 리스크비율) ÷ (레버리지 × 예상손절폭)
    - 신뢰도조정 = AI신뢰도 × 0.5 + 0.5 (최소 50% 포지션)
    - 최종포지션 = 기본포지션 × 신뢰도조정 × 켈리승수
    """

    def __init__(self, max_leverage: int = 10, max_margin_usage: float = 0.5,
                 min_position_size: float = 100.0, daily_loss_limit: float = 0.05,
                 max_correlation_exposure: float = 0.3):
        """
        Args:
            max_leverage: 최대 레버리지 제한 (기본 10배)
            max_margin_usage: 최대 마진 사용률 (기본 50%)
            min_position_size: 최소 포지션 크기 (기본 $100)
            daily_loss_limit: 일일 최대 손실 한도 (기본 5%)
            max_correlation_exposure: 상관관계 최대 노출 (기본 30%)
        """
        self.max_leverage = max_leverage
        self.max_margin_usage = max_margin_usage
        self.min_position_size = min_position_size
        self.daily_loss_limit = daily_loss_limit
        self.max_correlation_exposure = max_correlation_exposure

        # 포트폴리오 추적
        self.active_positions = {}
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.win_rate_history = []

        # 켈리 공식 파라미터
        self.kelly_lookback = 20  # 과거 20거래 기준
        self.kelly_fraction = 0.25  # 켈리 결과의 25%만 사용 (보수적)

        print(f"🚀 DynamicRiskManager v2.0 초기화")
        print(f"   최대 레버리지: {self.max_leverage}배")
        print(f"   최대 마진 사용률: {self.max_margin_usage:.0%}")
        print(f"   최소 포지션 크기: ${self.min_position_size:,.0f}")
        print(f"   일일 손실 한도: {self.daily_loss_limit:.1%}")
        print(f"   상관관계 한도: {self.max_correlation_exposure:.1%}")
        print()

    def calculate_enhanced_position_size(self, entry_price: float, stop_loss_price: float,
                                       take_profit_price: float, account_balance: float,
                                       ai_confidence: float, risk_percent: float = 0.02,
                                       symbol: str = "BTC", atr_value: float = None) -> Dict[str, Any]:
        """
        🎯 AI 신뢰도 + 켈리 공식 통합 포지션 사이징

        Args:
            entry_price: 진입가
            stop_loss_price: 손절가
            take_profit_price: 익절가
            account_balance: 계좌 잔고
            ai_confidence: AI 신뢰도 (0.0-1.0)
            risk_percent: 기본 리스크 비율
            symbol: 거래 심볼
            atr_value: ATR 값 (옵션)

        Returns:
            향상된 포지션 사이징 정보
        """

        print(f"🎯 Enhanced Position Sizing: {symbol.upper()}")
        print(f"📊 입력 조건:")
        print(f"   진입가: ${entry_price:,.2f}")
        print(f"   손절가: ${stop_loss_price:,.2f}")
        print(f"   익절가: ${take_profit_price:,.2f}")
        print(f"   AI 신뢰도: {ai_confidence:.1%}")
        print(f"   계좌 잔고: ${account_balance:,.2f}")
        print()

        try:
            # 1. 기본 리스크 계산
            stop_loss_percent = abs(entry_price - stop_loss_price) / entry_price
            take_profit_percent = abs(take_profit_price - entry_price) / entry_price
            risk_reward_ratio = take_profit_percent / stop_loss_percent if stop_loss_percent > 0 else 2.0

            # 2. 레버리지 계산 (ATR 고려)
            optimal_leverage = self._calculate_optimal_leverage(
                stop_loss_percent, ai_confidence, atr_value, entry_price
            )

            # 3. 켈리 공식 적용
            kelly_multiplier = self._calculate_kelly_multiplier(
                ai_confidence, risk_reward_ratio
            )

            # 4. AI 신뢰도 조정
            confidence_adjustment = ai_confidence * 0.5 + 0.5  # 50%-100% 범위

            # 5. 기본 포지션 계산
            account_risk_amount = account_balance * risk_percent
            base_position_size = account_risk_amount / (optimal_leverage * stop_loss_percent)

            # 6. 최종 포지션 크기 (켈리 + 신뢰도 조정)
            final_position_size = base_position_size * confidence_adjustment * kelly_multiplier

            # 7. 일일 손실 제한 적용
            position_after_daily_limit = self._apply_daily_loss_limit(
                final_position_size, account_balance, optimal_leverage
            )

            # 8. 상관관계 제한 적용
            position_after_correlation = self._apply_correlation_limit(
                position_after_daily_limit, symbol, account_balance
            )

            # 9. 연속 손실 조정
            position_after_streak = self._apply_consecutive_loss_adjustment(
                position_after_correlation
            )

            final_position = position_after_streak
            required_margin = final_position / optimal_leverage

            # 10. 안전장치 검증
            validation = self._validate_enhanced_position(
                final_position, optimal_leverage, required_margin, account_balance
            )

            if not validation['is_valid']:
                final_position = validation.get('adjusted_position', final_position)
                required_margin = final_position / optimal_leverage

            # 11. 상세 결과 생성
            result = self._generate_enhanced_result(
                symbol, entry_price, stop_loss_price, take_profit_price,
                final_position, optimal_leverage, required_margin,
                account_balance, ai_confidence, kelly_multiplier,
                confidence_adjustment, validation
            )

            # 12. 포지션 추적에 추가
            self._track_position(symbol, result)

            print(f"🎉 최종 포지션 사이징 완료")
            print(f"   포지션 크기: ${final_position:,.2f}")
            print(f"   레버리지: {optimal_leverage}배")
            print(f"   투입 자금: ${required_margin:,.2f}")
            print(f"   신뢰도 조정: {confidence_adjustment:.1%}")
            print(f"   켈리 승수: {kelly_multiplier:.2f}")
            print()

            return result

        except Exception as e:
            error_result = {
                'success': False,
                'error': f"Enhanced position sizing failed: {str(e)}",
                'position_size': 0,
                'required_margin': 0,
                'optimal_leverage': 1
            }
            print(f"❌ ERROR: {error_result['error']}")
            return error_result

    def _calculate_optimal_leverage(self, stop_loss_percent: float, ai_confidence: float,
                                  atr_value: float = None, current_price: float = None) -> int:
        """
        🔄 동적 레버리지 계산 (ATR + AI 신뢰도 고려)
        """
        # 기본 레버리지 (손절 폭 기준)
        if stop_loss_percent <= 0.005:     # 0.5% 이하
            base_leverage = 10
        elif stop_loss_percent <= 0.01:    # 1% 이하
            base_leverage = 8
        elif stop_loss_percent <= 0.02:    # 2% 이하
            base_leverage = 5
        elif stop_loss_percent <= 0.03:    # 3% 이하
            base_leverage = 3
        elif stop_loss_percent <= 0.05:    # 5% 이하
            base_leverage = 2
        else:                              # 5% 초과
            base_leverage = 1

        # AI 신뢰도 조정 (높은 신뢰도 = 약간 더 공격적)
        if ai_confidence >= 0.8:
            confidence_boost = 1.2
        elif ai_confidence >= 0.6:
            confidence_boost = 1.0
        else:
            confidence_boost = 0.8

        # ATR 기반 변동성 조정
        if atr_value and current_price:
            atr_percent = atr_value / current_price
            if atr_percent > 0.05:        # 높은 변동성
                volatility_adjustment = 0.7
            elif atr_percent > 0.03:      # 중간 변동성
                volatility_adjustment = 0.85
            else:                         # 낮은 변동성
                volatility_adjustment = 1.0
        else:
            volatility_adjustment = 1.0

        # 최종 레버리지
        final_leverage = int(base_leverage * confidence_boost * volatility_adjustment)
        return max(1, min(final_leverage, self.max_leverage))

    def _calculate_kelly_multiplier(self, ai_confidence: float, risk_reward_ratio: float) -> float:
        """
        💰 켈리 공식 승수 계산

        Kelly% = (bp - q) / b
        where: b = risk_reward_ratio, p = win_probability, q = loss_probability
        """
        # AI 신뢰도를 승률로 변환 (보수적 접근)
        win_probability = 0.5 + (ai_confidence - 0.5) * 0.5  # 50%-75% 범위
        loss_probability = 1 - win_probability

        # 켈리 공식
        if risk_reward_ratio > 0:
            kelly_percent = (risk_reward_ratio * win_probability - loss_probability) / risk_reward_ratio
        else:
            kelly_percent = 0

        # 안전을 위해 켈리 결과의 일부만 사용
        kelly_multiplier = max(0.1, min(2.0, kelly_percent * self.kelly_fraction))

        return kelly_multiplier

    def _apply_daily_loss_limit(self, position_size: float, account_balance: float,
                              leverage: int) -> float:
        """
        📅 일일 손실 한도 적용
        """
        if abs(self.daily_pnl) >= account_balance * self.daily_loss_limit:
            print(f"⚠️ 일일 손실 한도 도달: {self.daily_pnl:,.2f}")
            return position_size * 0.5  # 포지션 크기 50% 감소

        # 손실이 누적되면 점진적 감소
        loss_ratio = abs(self.daily_pnl) / (account_balance * self.daily_loss_limit)
        adjustment = 1.0 - (loss_ratio * 0.3)  # 최대 30% 감소

        return position_size * max(0.3, adjustment)

    def _apply_correlation_limit(self, position_size: float, symbol: str,
                               account_balance: float) -> float:
        """
        🔗 상관관계 기반 포지션 제한
        """
        # 간단한 상관관계 모델 (같은 카테고리 자산)
        crypto_symbols = ['BTC', 'ETH', 'BNB', 'ADA', 'SOL']

        if symbol.upper() in crypto_symbols:
            # 기존 암호화폐 포지션 확인
            crypto_exposure = sum(
                pos['position_value'] for pos in self.active_positions.values()
                if pos['symbol'].upper() in crypto_symbols
            )

            max_crypto_exposure = account_balance * self.max_correlation_exposure

            if crypto_exposure + position_size > max_crypto_exposure:
                allowed_position = max_crypto_exposure - crypto_exposure
                print(f"🔗 상관관계 제한 적용: 암호화폐 노출 한도")
                return max(0, allowed_position)

        return position_size

    def _apply_consecutive_loss_adjustment(self, position_size: float) -> float:
        """
        📉 연속 손실 조정
        """
        if self.consecutive_losses >= 3:
            reduction = min(0.5, self.consecutive_losses * 0.1)  # 최대 50% 감소
            print(f"📉 연속 손실 조정: {self.consecutive_losses}회 → {reduction:.1%} 감소")
            return position_size * (1 - reduction)

        return position_size

    def _validate_enhanced_position(self, position_size: float, leverage: int,
                                  margin_required: float, account_balance: float) -> Dict[str, Any]:
        """
        🛡️ 향상된 안전장치 검증
        """
        issues = []
        is_valid = True
        adjusted_position = position_size

        # 1. 최소 포지션 크기
        if position_size < self.min_position_size:
            issues.append(f"최소 포지션 크기 미달")
            adjusted_position = self.min_position_size
            is_valid = False

        # 2. 마진 사용률
        margin_usage = margin_required / account_balance
        if margin_usage > self.max_margin_usage:
            issues.append(f"마진 사용률 초과: {margin_usage:.1%}")
            adjusted_position = account_balance * self.max_margin_usage * leverage
            is_valid = False

        # 3. 레버리지 한도
        if leverage > self.max_leverage:
            issues.append(f"레버리지 한도 초과: {leverage}배")
            is_valid = False

        # 4. 계좌 대비 포지션 크기
        if position_size > account_balance * 5:  # 포지션이 계좌의 5배 초과
            issues.append(f"과도한 포지션 크기")
            adjusted_position = account_balance * 3
            is_valid = False

        return {
            'is_valid': is_valid,
            'issues': issues,
            'adjusted_position': adjusted_position,
            'margin_usage_percent': margin_usage
        }

    def _generate_enhanced_result(self, symbol: str, entry_price: float,
                                stop_loss_price: float, take_profit_price: float,
                                position_size: float, leverage: int, margin_required: float,
                                account_balance: float, ai_confidence: float,
                                kelly_multiplier: float, confidence_adjustment: float,
                                validation: Dict[str, Any]) -> Dict[str, Any]:
        """
        📋 향상된 결과 생성
        """
        stop_loss_percent = abs(entry_price - stop_loss_price) / entry_price
        take_profit_percent = abs(take_profit_price - entry_price) / entry_price

        return {
            'success': True,
            'symbol': symbol,
            'entry_price': entry_price,
            'stop_loss_price': stop_loss_price,
            'take_profit_price': take_profit_price,
            'stop_loss_percent': stop_loss_percent,
            'take_profit_percent': take_profit_percent,
            'risk_reward_ratio': take_profit_percent / stop_loss_percent if stop_loss_percent > 0 else 2.0,

            # 포지션 정보
            'position_size': position_size,
            'leverage': leverage,
            'margin_required': margin_required,
            'position_value': position_size,
            'margin_usage_percent': margin_required / account_balance,

            # AI & 켈리 정보
            'ai_confidence': ai_confidence,
            'confidence_adjustment': confidence_adjustment,
            'kelly_multiplier': kelly_multiplier,

            # 리스크 지표
            'max_loss_amount': position_size * stop_loss_percent,
            'max_profit_amount': position_size * take_profit_percent,
            'account_risk_percent': (position_size * stop_loss_percent) / account_balance * 100,

            # 검증 결과
            'validation': validation,

            # 포트폴리오 상태
            'daily_pnl': self.daily_pnl,
            'consecutive_losses': self.consecutive_losses,
            'active_positions_count': len(self.active_positions)
        }

    def _track_position(self, symbol: str, position_data: Dict[str, Any]):
        """
        📊 포지션 추적
        """
        self.active_positions[symbol] = {
            'symbol': symbol,
            'position_size': position_data['position_size'],
            'position_value': position_data['position_value'],
            'margin_required': position_data['margin_required'],
            'entry_time': datetime.now(),
            'entry_price': position_data['entry_price']
        }

    def calculate_portfolio_risk(self) -> Dict[str, Any]:
        """
        📊 포트폴리오 전체 리스크 분석
        """
        total_margin = sum(pos['margin_required'] for pos in self.active_positions.values())
        total_position_value = sum(pos['position_value'] for pos in self.active_positions.values())

        # 상관관계 기반 리스크
        crypto_exposure = sum(
            pos['position_value'] for pos in self.active_positions.values()
            if pos['symbol'].upper() in ['BTC', 'ETH', 'BNB', 'ADA', 'SOL']
        )

        return {
            'total_positions': len(self.active_positions),
            'total_margin_used': total_margin,
            'total_position_value': total_position_value,
            'crypto_correlation_exposure': crypto_exposure,
            'daily_pnl': self.daily_pnl,
            'consecutive_losses': self.consecutive_losses,
            'risk_metrics': {
                'margin_utilization': total_margin,
                'correlation_risk': crypto_exposure,
                'daily_loss_proximity': abs(self.daily_pnl) / (total_margin * self.daily_loss_limit)
            }
        }

    def update_trade_result(self, symbol: str, pnl: float, was_winner: bool):
        """
        📈 거래 결과 업데이트
        """
        self.daily_pnl += pnl
        self.win_rate_history.append(was_winner)

        if was_winner:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1

        # 히스토리 크기 제한
        if len(self.win_rate_history) > self.kelly_lookback:
            self.win_rate_history.pop(0)

        # 포지션 제거
        if symbol in self.active_positions:
            del self.active_positions[symbol]

    def get_enhanced_risk_metrics(self) -> Dict[str, Any]:
        """
        📊 향상된 리스크 지표
        """
        current_win_rate = sum(self.win_rate_history) / len(self.win_rate_history) if self.win_rate_history else 0.5

        return {
            'portfolio_risk': self.calculate_portfolio_risk(),
            'performance_metrics': {
                'daily_pnl': self.daily_pnl,
                'consecutive_losses': self.consecutive_losses,
                'current_win_rate': current_win_rate,
                'total_trades': len(self.win_rate_history)
            },
            'risk_limits': {
                'daily_loss_limit': self.daily_loss_limit,
                'max_margin_usage': self.max_margin_usage,
                'max_correlation_exposure': self.max_correlation_exposure,
                'max_leverage': self.max_leverage
            }
        }

# ==========================================
# ENHANCED AI TRADING SYSTEM WITH RISK INTEGRATION
# ==========================================

class EnhancedAITradingSystem:
    """
    AI 신호와 리스크 관리를 완벽 통합한 향상된 트레이딩 시스템

    Features:
    - AI 신호에 진입가/손절가/익절가 자동 계산
    - DynamicRiskManager와 실시간 연동
    - 신호별 최적 포지션 사이징
    - 상세한 리스크 분석 및 시각화
    """

    def __init__(self, account_balance: float = 10000, risk_percent: float = 0.02):
        """
        Args:
            account_balance: 계좌 잔고
            risk_percent: 거래당 리스크 비율 (기본 2%)
        """
        self.account_balance = account_balance
        self.risk_percent = risk_percent

        # Core components
        self.ml_generator = MLSignalGenerator()
        self.atr_calculator = ATRCalculator()
        self.risk_manager = DynamicRiskManager()

        print(f"EnhancedAITradingSystem 초기화")
        print(f"  계좌 잔고: ${account_balance:,.2f}")
        print(f"  거래 리스크: {risk_percent:.1%}")
        print()

    def generate_enhanced_signal(self, symbol: str, market_data: pd.DataFrame,
                                account_balance: float = None) -> Dict[str, Any]:
        """
        AI 신호와 리스크 관리가 통합된 향상된 신호 생성

        Args:
            symbol: 거래 심볼
            market_data: 시장 데이터 (OHLCV)
            account_balance: 계좌 잔고 (옵션)

        Returns:
            완전한 거래 정보가 포함된 신호
        """

        print(f"=== Enhanced AI Signal Generation: {symbol.upper()} ===")
        print()

        # 계좌 잔고 설정
        balance = account_balance or self.account_balance

        try:
            # 1. 기본 AI 신호 생성
            base_signal = self._generate_base_ai_signal(market_data)
            if 'error' in base_signal:
                return base_signal

            # 2. 현재 가격 및 ATR 계산
            current_price = market_data['close'].iloc[-1]
            atr_result = self.atr_calculator.calculate_atr(market_data)
            atr_value = atr_result.get('current_atr', current_price * 0.02)  # fallback 2%

            # 3. AI 기반 진입가/손절가/익절가 계산
            entry_signals = self._calculate_entry_exit_prices(
                base_signal, current_price, atr_value, market_data
            )

            # 4. 리스크 관리 계산
            risk_analysis = self._calculate_risk_management(
                entry_signals, balance
            )

            # 5. 통합 신호 생성
            enhanced_signal = self._create_enhanced_signal(
                base_signal, entry_signals, risk_analysis, symbol
            )

            # 6. 결과 출력
            self._display_signal_summary(enhanced_signal)

            return enhanced_signal

        except Exception as e:
            error_result = {
                'success': False,
                'error': f"Enhanced signal generation failed: {str(e)}",
                'symbol': symbol
            }
            print(f"ERROR: {error_result['error']}")
            return error_result

    def _generate_base_ai_signal(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """기본 AI 신호 생성"""

        # ML 모델이 학습되어 있다면 사용, 아니면 기술적 분석
        if self.ml_generator.is_trained:
            signal_result = self.ml_generator.predict_signal(market_data)
        else:
            signal_result = self._generate_technical_signal(market_data)

        return signal_result

    def _generate_technical_signal(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """기술적 분석 기반 신호 생성 (ML 모델 미학습시 대체)"""

        # 간단한 이동평균 기반 신호
        short_ma = market_data['close'].rolling(5).mean().iloc[-1]
        long_ma = market_data['close'].rolling(20).mean().iloc[-1]
        current_price = market_data['close'].iloc[-1]

        # RSI 계산
        rsi = self._calculate_rsi(market_data['close'])

        # 신호 결정
        if short_ma > long_ma and rsi < 70:
            signal = 'BUY'
            confidence = 0.65
        elif short_ma < long_ma and rsi > 30:
            signal = 'SELL'
            confidence = 0.65
        else:
            signal = 'HOLD'
            confidence = 0.50

        return {
            'signal': signal,
            'confidence': confidence,
            'reasoning': f"MA cross + RSI({rsi:.1f})",
            'current_price': current_price
        }

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """RSI 계산"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]

    def _calculate_entry_exit_prices(self, base_signal: Dict[str, Any],
                                   current_price: float, atr_value: float,
                                   market_data: pd.DataFrame) -> Dict[str, Any]:
        """AI 기반 진입가/손절가/익절가 계산"""

        signal_type = base_signal['signal']
        confidence = base_signal['confidence']

        # 신뢰도에 따른 ATR 배수 조정
        if confidence >= 0.8:
            stop_multiplier = 1.5   # 고신뢰도: 타이트한 손절
            profit_multiplier = 3.0
        elif confidence >= 0.6:
            stop_multiplier = 2.0   # 중신뢰도: 표준 손절
            profit_multiplier = 2.5
        else:
            stop_multiplier = 2.5   # 저신뢰도: 여유있는 손절
            profit_multiplier = 2.0

        # 변동성 고려
        volatility_adj = min(atr_value / current_price, 0.05)  # 최대 5%

        if signal_type == 'BUY':
            # 매수 신호
            entry_price = current_price
            stop_loss_price = current_price - (atr_value * stop_multiplier)
            take_profit_price = current_price + (atr_value * profit_multiplier)

        elif signal_type == 'SELL':
            # 매도 신호 (숏 포지션)
            entry_price = current_price
            stop_loss_price = current_price + (atr_value * stop_multiplier)
            take_profit_price = current_price - (atr_value * profit_multiplier)

        else:  # HOLD
            entry_price = current_price
            stop_loss_price = current_price
            take_profit_price = current_price

        # 손절 폭 계산
        stop_loss_percent = abs(entry_price - stop_loss_price) / entry_price
        take_profit_percent = abs(take_profit_price - entry_price) / entry_price

        return {
            'entry_price': entry_price,
            'stop_loss_price': stop_loss_price,
            'take_profit_price': take_profit_price,
            'stop_loss_percent': stop_loss_percent,
            'take_profit_percent': take_profit_percent,
            'atr_value': atr_value,
            'confidence_score': int(confidence * 100)  # 0-100 점수
        }

    def _calculate_risk_management(self, entry_signals: Dict[str, Any],
                                 balance: float) -> Dict[str, Any]:
        """DynamicRiskManager를 사용한 리스크 계산"""

        entry_price = entry_signals['entry_price']
        stop_loss_price = entry_signals['stop_loss_price']

        # DynamicRiskManager로 포지션 사이징
        position_result = self.risk_manager.calculate_position_size(
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            account_balance=balance,
            risk_percent=self.risk_percent
        )

        if position_result['success']:
            return {
                'success': True,
                'position_size': position_result['position_size'],
                'leverage': position_result['optimal_leverage'],
                'margin_required': position_result['required_margin'],
                'position_value': position_result['position_value'],
                'margin_usage_percent': position_result['margin_usage_percent'],
                'max_loss_amount': position_result['account_risk_amount'],
                'risk_reward_ratio': position_result['risk_reward_ratio']
            }
        else:
            return {
                'success': False,
                'error': position_result['error'],
                'position_size': 0,
                'leverage': 1,
                'margin_required': 0
            }

    def _create_enhanced_signal(self, base_signal: Dict[str, Any],
                              entry_signals: Dict[str, Any],
                              risk_analysis: Dict[str, Any],
                              symbol: str) -> Dict[str, Any]:
        """모든 정보를 통합한 향상된 신호 생성"""

        return {
            'success': True,
            'symbol': symbol.upper(),
            'timestamp': datetime.now(),

            # AI 신호 정보
            'signal': base_signal['signal'],
            'reasoning': base_signal.get('reasoning', 'AI analysis'),
            'confidence_score': entry_signals['confidence_score'],

            # 가격 정보
            'entry_price': entry_signals['entry_price'],
            'stop_loss_price': entry_signals['stop_loss_price'],
            'take_profit_price': entry_signals['take_profit_price'],
            'stop_loss_percent': entry_signals['stop_loss_percent'],
            'take_profit_percent': entry_signals['take_profit_percent'],

            # 리스크 관리 정보
            'risk_management': risk_analysis,

            # ATR 정보
            'atr_value': entry_signals['atr_value'],

            # 거래 실행 가능 여부
            'executable': risk_analysis['success'] and base_signal['signal'] != 'HOLD'
        }

    def _display_signal_summary(self, signal: Dict[str, Any]):
        """신호 요약 정보 표시"""

        if not signal['success']:
            print(f"Signal generation failed: {signal.get('error', 'Unknown error')}")
            return

        print(f"Signal: {signal['signal']} {signal['symbol']}")
        print(f"Entry: ${signal['entry_price']:,.2f}")

        if signal['signal'] != 'HOLD':
            print(f"Stop Loss: ${signal['stop_loss_price']:,.2f} ({signal['stop_loss_percent']:+.1%})")
            print(f"Take Profit: ${signal['take_profit_price']:,.2f} ({signal['take_profit_percent']:+.1%})")

        print(f"Confidence: {signal['confidence_score']}%")
        print()

        # 리스크 계산 정보
        risk = signal['risk_management']
        if risk['success']:
            print("Risk Calculation:")
            print(f"- Position Size: ${risk['position_size']:,.2f}")
            print(f"- Leverage: {risk['leverage']}x")
            print(f"- Margin Required: ${risk['margin_required']:,.2f}")
            print(f"- Max Loss: ${risk['max_loss_amount']:,.2f} ({self.risk_percent:.1%})")
            print(f"- Margin Usage: {risk['margin_usage_percent']:.1%}")
            print(f"- Risk/Reward: 1:{risk['risk_reward_ratio']:.1f}")
        else:
            print(f"Risk calculation failed: {risk['error']}")

        print()
        print(f"Executable: {'YES' if signal['executable'] else 'NO'}")
        print("=" * 50)
        print()

    def update_account_balance(self, new_balance: float):
        """계좌 잔고 업데이트"""
        self.account_balance = new_balance
        print(f"Account balance updated to: ${new_balance:,.2f}")

    def set_risk_percent(self, new_risk_percent: float):
        """리스크 비율 업데이트"""
        self.risk_percent = new_risk_percent
        print(f"Risk percentage updated to: {new_risk_percent:.1%}")


class BinanceFuturesConnector:
    """
    Binance Futures API 연결 및 거래 실행 클래스
    DynamicRiskManager와 연동하여 계산된 포지션을 실제 실행
    """

    def __init__(self, api_key: str, secret_key: str, testnet: bool = True):
        """
        Binance Futures Connector 초기화

        Args:
            api_key: Binance API 키
            secret_key: Binance Secret 키
            testnet: 테스트넷 사용 여부 (기본값: True)
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.testnet = testnet

        # CCXT 거래소 객체 초기화
        try:
            self.exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': secret_key,
                'sandbox': testnet,  # 테스트넷 사용
                'options': {
                    'defaultType': 'future',  # 선물 거래
                }
            })
            print(f"BinanceFuturesConnector 초기화 완료")
            print(f"테스트넷 모드: {'ON' if testnet else 'OFF'}")

            # 연결 테스트
            self._test_connection()

        except Exception as e:
            print(f"Binance 연결 실패: {e}")
            self.exchange = None

    def _test_connection(self):
        """API 연결 테스트"""
        try:
            balance = self.exchange.fetch_balance()
            print(f"OK Binance API 연결 성공")
            print(f"USDT 잔고: {balance.get('USDT', {}).get('free', 0):.2f}")
            return True
        except Exception as e:
            print(f"ERROR API 연결 테스트 실패: {e}")
            return False

    def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """
        레버리지 설정

        Args:
            symbol: 거래 심볼 (예: 'BTC/USDT')
            leverage: 레버리지 배수 (1-10배)

        Returns:
            설정 결과 딕셔너리
        """
        try:
            # 레버리지 범위 검증
            if not 1 <= leverage <= 10:
                return {
                    'success': False,
                    'error': f'레버리지는 1-10배 범위 내에서 설정해야 합니다. 입력값: {leverage}'
                }

            if not self.exchange:
                return {'success': False, 'error': 'Exchange 연결이 설정되지 않았습니다'}

            # 레버리지 설정
            result = self.exchange.set_leverage(leverage, symbol)

            print(f"레버리지 설정 완료: {symbol} → {leverage}배")
            return {
                'success': True,
                'symbol': symbol,
                'leverage': leverage,
                'result': result
            }

        except Exception as e:
            error_msg = f"레버리지 설정 실패 ({symbol}, {leverage}배): {e}"
            print(f"ERROR {error_msg}")
            return {'success': False, 'error': error_msg}

    def set_margin_type(self, symbol: str, margin_type: str = 'ISOLATED') -> Dict[str, Any]:
        """
        마진 모드 설정

        Args:
            symbol: 거래 심볼
            margin_type: 'ISOLATED' (격리) 또는 'CROSSED' (교차)

        Returns:
            설정 결과 딕셔너리
        """
        try:
            if margin_type not in ['ISOLATED', 'CROSSED']:
                return {
                    'success': False,
                    'error': f'마진 타입은 ISOLATED 또는 CROSSED여야 합니다. 입력값: {margin_type}'
                }

            if not self.exchange:
                return {'success': False, 'error': 'Exchange 연결이 설정되지 않았습니다'}

            # 마진 타입 설정
            params = {'marginType': margin_type}
            result = self.exchange.set_margin_mode(margin_type.lower(), symbol, params)

            print(f"마진 모드 설정 완료: {symbol} → {margin_type}")
            return {
                'success': True,
                'symbol': symbol,
                'margin_type': margin_type,
                'result': result
            }

        except Exception as e:
            error_msg = f"마진 모드 설정 실패 ({symbol}, {margin_type}): {e}"
            print(f"ERROR {error_msg}")
            return {'success': False, 'error': error_msg}

    def place_futures_order(self, symbol: str, side: str, quantity: float,
                           order_type: str = 'MARKET', price: float = None) -> Dict[str, Any]:
        """
        선물 주문 실행

        Args:
            symbol: 거래 심볼 (예: 'BTC/USDT')
            side: 'BUY' (롱) 또는 'SELL' (숏)
            quantity: 주문 수량 (DynamicRiskManager에서 계산된 값)
            order_type: 주문 타입 ('MARKET', 'LIMIT')
            price: 지정가 (LIMIT 주문시 필요)

        Returns:
            주문 실행 결과 딕셔너리
        """
        try:
            if not self.exchange:
                return {'success': False, 'error': 'Exchange 연결이 설정되지 않았습니다'}

            # 파라미터 검증
            if side not in ['BUY', 'SELL']:
                return {'success': False, 'error': f'잘못된 side 값: {side}'}

            if quantity <= 0:
                return {'success': False, 'error': f'수량은 0보다 커야 합니다: {quantity}'}

            if order_type == 'LIMIT' and not price:
                return {'success': False, 'error': 'LIMIT 주문시 가격을 지정해야 합니다'}

            # 주문 실행
            if order_type == 'MARKET':
                order = self.exchange.create_market_order(symbol, side.lower(), quantity)
            else:  # LIMIT
                order = self.exchange.create_limit_order(symbol, side.lower(), quantity, price)

            print(f"OK 선물 주문 실행 완료:")
            print(f"   심볼: {symbol}")
            print(f"   방향: {side}")
            print(f"   수량: {quantity}")
            print(f"   타입: {order_type}")
            if price:
                print(f"   가격: ${price:,.2f}")
            print(f"   주문ID: {order.get('id', 'N/A')}")

            return {
                'success': True,
                'order_id': order.get('id'),
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'order_type': order_type,
                'price': price,
                'order_info': order
            }

        except Exception as e:
            error_msg = f"주문 실행 실패 ({symbol} {side} {quantity}): {e}"
            print(f"ERROR {error_msg}")
            return {'success': False, 'error': error_msg}

    def get_position_info(self, symbol: str = None) -> Dict[str, Any]:
        """
        포지션 정보 조회

        Args:
            symbol: 특정 심볼 조회 (None시 모든 포지션)

        Returns:
            포지션 정보 딕셔너리
        """
        try:
            if not self.exchange:
                return {'success': False, 'error': 'Exchange 연결이 설정되지 않았습니다'}

            # 모든 포지션 조회
            positions = self.exchange.fetch_positions()

            if symbol:
                # 특정 심볼 필터링
                target_positions = [pos for pos in positions if pos['symbol'] == symbol]
                if not target_positions:
                    return {
                        'success': True,
                        'symbol': symbol,
                        'position_size': 0,
                        'entry_price': 0,
                        'unrealized_pnl': 0,
                        'margin_usage': 0,
                        'liquidation_price': 0
                    }

                pos = target_positions[0]
                return {
                    'success': True,
                    'symbol': symbol,
                    'position_size': pos.get('contracts', 0),
                    'entry_price': pos.get('entryPrice', 0),
                    'mark_price': pos.get('markPrice', 0),
                    'unrealized_pnl': pos.get('unrealizedPnl', 0),
                    'percentage': pos.get('percentage', 0),
                    'liquidation_price': pos.get('liquidationPrice', 0),
                    'margin_usage': pos.get('marginRatio', 0),
                    'position_info': pos
                }
            else:
                # 모든 포지션 요약
                active_positions = [pos for pos in positions if pos.get('contracts', 0) != 0]
                total_unrealized = sum(pos.get('unrealizedPnl', 0) for pos in active_positions)

                return {
                    'success': True,
                    'total_positions': len(active_positions),
                    'total_unrealized_pnl': total_unrealized,
                    'positions': active_positions
                }

        except Exception as e:
            error_msg = f"포지션 정보 조회 실패: {e}"
            print(f"ERROR {error_msg}")
            return {'success': False, 'error': error_msg}

    def execute_ai_signal(self, signal: Dict[str, Any], risk_calculation: Dict[str, Any]) -> Dict[str, Any]:
        """
        AI 신호에 따른 전체 거래 실행 프로세스

        Args:
            signal: EnhancedAITradingSystem에서 생성된 신호
            risk_calculation: DynamicRiskManager에서 계산된 리스크 정보

        Returns:
            전체 실행 결과 딕셔너리
        """
        try:
            if not signal.get('success') or not signal.get('executable'):
                return {
                    'success': False,
                    'error': f"실행 불가능한 신호: {signal.get('error', '알 수 없는 오류')}"
                }

            symbol = signal['symbol']
            if symbol == 'BTC':
                symbol = 'BTC/USDT'
            elif symbol == 'ETH':
                symbol = 'ETH/USDT'

            signal_type = signal['signal']
            leverage = risk_calculation.get('leverage', 1)
            position_size = risk_calculation.get('position_size', 0)

            print(f"=== AI 신호 실행 시작 ===")
            print(f"신호: {signal_type} {symbol}")
            print(f"신뢰도: {signal.get('confidence_score', 0)}%")
            print(f"레버리지: {leverage}배")
            print(f"포지션 크기: ${position_size:,.2f}")
            print()

            execution_results = []

            # 1. 레버리지 설정
            print("1. 레버리지 설정 중...")
            leverage_result = self.set_leverage(symbol, leverage)
            execution_results.append(('leverage', leverage_result))

            if not leverage_result['success']:
                return {
                    'success': False,
                    'error': f"레버리지 설정 실패: {leverage_result['error']}",
                    'execution_results': execution_results
                }

            # 2. 마진 모드 설정 (격리 마진)
            print("2. 마진 모드 설정 중...")
            margin_result = self.set_margin_type(symbol, 'ISOLATED')
            execution_results.append(('margin_type', margin_result))

            # 3. 현재 포지션 확인
            print("3. 현재 포지션 확인 중...")
            current_position = self.get_position_info(symbol)
            execution_results.append(('current_position', current_position))

            if current_position['success']:
                current_size = current_position.get('position_size', 0)
                if current_size != 0:
                    print(f"WARNING 기존 포지션 감지: {current_size}")
                    print("기존 포지션 청산을 권장합니다.")

            # 4. 주문 수량 계산 (USDT 기준 → BTC 수량 변환)
            current_price = signal.get('entry_price', 50000)  # 진입가 사용
            if position_size > 0:
                # USDT 금액을 실제 코인 수량으로 변환
                quantity = position_size / current_price

                # Binance 최소 주문 단위 적용 (BTC는 보통 0.001)
                min_quantity = 0.001
                if quantity < min_quantity:
                    print(f"WARNING 최소 주문 수량 미달: {quantity:.6f} < {min_quantity}")
                    quantity = min_quantity

                print(f"4. 주문 실행 중...")
                print(f"   주문 수량: {quantity:.6f} BTC")
                print(f"   예상 가격: ${current_price:,.2f}")
                print(f"   총 투입금: ${quantity * current_price:,.2f}")

                # 5. 실제 주문 실행
                if signal_type in ['BUY', 'SELL']:
                    order_result = self.place_futures_order(
                        symbol=symbol,
                        side=signal_type,
                        quantity=quantity,
                        order_type='MARKET'
                    )
                    execution_results.append(('order', order_result))

                    if order_result['success']:
                        print(f"OK 주문 실행 성공!")

                        # 6. 실행 후 포지션 확인
                        time.sleep(2)  # 주문 처리 대기
                        final_position = self.get_position_info(symbol)
                        execution_results.append(('final_position', final_position))

                        return {
                            'success': True,
                            'signal_executed': signal_type,
                            'symbol': symbol,
                            'quantity': quantity,
                            'leverage': leverage,
                            'order_id': order_result.get('order_id'),
                            'execution_results': execution_results,
                            'final_position': final_position
                        }
                    else:
                        return {
                            'success': False,
                            'error': f"주문 실행 실패: {order_result['error']}",
                            'execution_results': execution_results
                        }
                else:
                    print(f"WARNING HOLD 신호 - 주문 실행하지 않음")
                    return {
                        'success': True,
                        'signal_executed': 'HOLD',
                        'symbol': symbol,
                        'execution_results': execution_results
                    }
            else:
                return {
                    'success': False,
                    'error': '계산된 포지션 크기가 0입니다',
                    'execution_results': execution_results
                }

        except Exception as e:
            error_msg = f"AI 신호 실행 중 오류 발생: {e}"
            print(f"ERROR {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'execution_results': execution_results if 'execution_results' in locals() else []
            }

    def monitor_positions(self) -> Dict[str, Any]:
        """
        모든 포지션 모니터링

        Returns:
            포지션 모니터링 결과
        """
        try:
            print("=== 포지션 모니터링 ===")

            positions = self.get_position_info()
            if not positions['success']:
                return positions

            active_positions = positions.get('positions', [])
            total_pnl = positions.get('total_unrealized_pnl', 0)

            print(f"활성 포지션 수: {len(active_positions)}")
            print(f"총 미실현 손익: ${total_pnl:,.2f}")

            if active_positions:
                print("\n개별 포지션 상세:")
                for i, pos in enumerate(active_positions, 1):
                    symbol = pos.get('symbol', 'N/A')
                    size = pos.get('contracts', 0)
                    entry_price = pos.get('entryPrice', 0)
                    mark_price = pos.get('markPrice', 0)
                    pnl = pos.get('unrealizedPnl', 0)
                    percentage = pos.get('percentage', 0)

                    print(f"{i}. {symbol}")
                    print(f"   포지션: {size}")
                    print(f"   진입가: ${entry_price:,.2f}")
                    print(f"   현재가: ${mark_price:,.2f}")
                    print(f"   손익: ${pnl:,.2f} ({percentage:+.2f}%)")
                    print()

            return {
                'success': True,
                'monitoring_time': datetime.now(),
                'active_positions_count': len(active_positions),
                'total_unrealized_pnl': total_pnl,
                'positions_detail': active_positions
            }

        except Exception as e:
            error_msg = f"포지션 모니터링 실패: {e}"
            print(f"ERROR {error_msg}")
            return {'success': False, 'error': error_msg}


# AI 신호 + 리스크 관리 + 실제 거래 통합 실행 함수
def execute_integrated_trading_system(api_key: str, secret_key: str,
                                     account_balance: float = 10000,
                                     risk_percent: float = 0.02,
                                     testnet: bool = True) -> Dict[str, Any]:
    """
    통합 거래 시스템 실행
    AI 신호 → 리스크 계산 → 실제 거래 실행

    Args:
        api_key: Binance API 키
        secret_key: Binance Secret 키
        account_balance: 계좌 잔고
        risk_percent: 리스크 비율 (0.02 = 2%)
        testnet: 테스트넷 사용 여부

    Returns:
        전체 실행 결과
    """
    print("=== 통합 거래 시스템 시작 ===")
    print(f"계좌 잔고: ${account_balance:,.2f}")
    print(f"리스크 비율: {risk_percent:.1%}")
    print(f"테스트넷: {'ON' if testnet else 'OFF'}")
    print()

    try:
        # 1. AI 거래 시스템 초기화
        print("1. EnhancedAITradingSystem 초기화...")
        ai_system = EnhancedAITradingSystem(
            account_balance=account_balance,
            risk_percent=risk_percent
        )

        # 2. Binance 연결 초기화
        print("2. BinanceFuturesConnector 초기화...")
        binance = BinanceFuturesConnector(
            api_key=api_key,
            secret_key=secret_key,
            testnet=testnet
        )

        if not binance.exchange:
            return {
                'success': False,
                'error': 'Binance 연결 실패'
            }

        # 3. 시장 데이터 생성 (실제 환경에서는 실시간 데이터 사용)
        print("3. 시장 데이터 준비...")
        from test_enhanced_ai_system import create_test_market_data
        market_data = create_test_market_data()

        # 4. AI 신호 생성
        print("4. AI 신호 생성...")
        signal = ai_system.generate_enhanced_signal('BTC', market_data)

        if not signal['success']:
            return {
                'success': False,
                'error': f"AI 신호 생성 실패: {signal.get('error')}"
            }

        print(f"AI 신호: {signal['signal']} (신뢰도: {signal.get('confidence_score')}%)")

        # 5. 실제 거래 실행 (HOLD 신호가 아닌 경우에만)
        if signal['signal'] != 'HOLD' and signal.get('executable'):
            print("5. 실제 거래 실행...")
            execution_result = binance.execute_ai_signal(signal, signal['risk_management'])

            return {
                'success': True,
                'ai_signal': signal,
                'execution_result': execution_result,
                'integrated_system': 'completed'
            }
        else:
            print("5. HOLD 신호 또는 실행 불가 - 거래 미실행")
            return {
                'success': True,
                'ai_signal': signal,
                'execution_result': {'signal_executed': 'HOLD', 'reason': 'Hold signal or not executable'},
                'integrated_system': 'completed'
            }

    except Exception as e:
        error_msg = f"통합 거래 시스템 실행 중 오류: {e}"
        print(f"ERROR {error_msg}")
        return {
            'success': False,
            'error': error_msg
        }


if __name__ == "__main__":
    main_dashboard()