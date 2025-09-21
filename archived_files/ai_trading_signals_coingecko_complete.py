#!/usr/bin/env python3
"""
AI Trading Signals - Complete CoinGecko Integration
Enhanced cryptocurrency trading system with CoinGecko API

Key Improvements over Alpha Vantage:
- 20x more API requests (10,000/month vs 500)
- No API key required
- More cryptocurrencies supported
- Better technical indicators with pandas_ta
- Real-time market sentiment integration
- Enhanced ML models with confidence scoring
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

# Import all components from our modular files
try:
    from ai_trading_signals_coingecko import (
        Config, CoinGeckoConnector, EnhancedTechnicalIndicators,
        EnhancedATRCalculator, EnhancedRiskManager
    )
    from coingecko_ml_components import (
        EnhancedMLSignalGenerator, EnhancedPaperTradingSimulator,
        EnhancedDatabaseManager
    )
except ImportError:
    st.error("CoinGecko components not found. Please ensure all files are in the same directory.")
    st.stop()

# ML and visualization libraries
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots

    # Check for pandas_ta
    try:
        import pandas_ta as ta
        PANDAS_TA_AVAILABLE = True
        st.success("[ROCKET] Enhanced technical analysis available with pandas_ta")
    except ImportError:
        PANDAS_TA_AVAILABLE = False
        st.warning("[WARNING] pandas_ta not available. Install with: pip install pandas_ta")

except ImportError as e:
    st.error(f"Required library missing: {e}")
    st.stop()

# ==========================================
# MAIN DASHBOARD FUNCTIONS
# ==========================================

def main_dashboard():
    """Enhanced main dashboard with CoinGecko integration"""
    st.set_page_config(
        page_title="Crypto Trader Pro - CoinGecko Edition",
        page_icon="[ROCKET]",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize session state with enhanced components
    if 'cg_connector' not in st.session_state:
        st.session_state.cg_connector = CoinGeckoConnector()

    if 'enhanced_ml_model' not in st.session_state:
        st.session_state.enhanced_ml_model = EnhancedMLSignalGenerator()

    if 'enhanced_paper_trader' not in st.session_state:
        st.session_state.enhanced_paper_trader = EnhancedPaperTradingSimulator(initial_capital=10000)

    if 'enhanced_risk_manager' not in st.session_state:
        st.session_state.enhanced_risk_manager = EnhancedRiskManager(account_balance=10000)

    if 'enhanced_atr_calculator' not in st.session_state:
        st.session_state.enhanced_atr_calculator = EnhancedATRCalculator()

    if 'enhanced_db_manager' not in st.session_state:
        st.session_state.enhanced_db_manager = EnhancedDatabaseManager()

    if 'current_data' not in st.session_state:
        st.session_state.current_data = None

    if 'latest_signal' not in st.session_state:
        st.session_state.latest_signal = None

    # Enhanced header with CoinGecko branding
    st.markdown("""
    <div style="background: linear-gradient(90deg, #1f77b4 0%, #ff7f0e 100%); padding: 1rem; border-radius: 10px; margin-bottom: 2rem;">
        <h1 style="color: white; text-align: center; margin: 0;">
            [ROCKET] Crypto Trader Pro - CoinGecko Edition
        </h1>
        <p style="color: white; text-align: center; margin: 0; opacity: 0.9;">
            Advanced AI Trading with 10,000+ API calls/month | Real-time market sentiment
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Enhanced sidebar with more options (called once to avoid duplicate keys)
    create_enhanced_sidebar()

    # Main content tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "[BAR_CHART] Live Trading",
        "[BRAIN] AI Training",
        "[TREND_UP] Backtesting",
        "[MONEY] Paper Trading",
        "🌍 Market Overview",
        "⚙️ System Status"
    ])

    with tab1:
        create_live_trading_tab()

    with tab2:
        create_ai_training_tab()

    with tab3:
        create_backtesting_tab()

    with tab4:
        create_paper_trading_tab()

    with tab5:
        create_market_overview_tab()

    with tab6:
        create_system_status_tab()

def create_enhanced_sidebar():
    """Create enhanced sidebar with CoinGecko options"""
    st.sidebar.title("[ROCKET] CoinGecko Trading Settings")
    st.sidebar.markdown("---")

    # Cryptocurrency selection (expanded list)
    st.sidebar.subheader("[TREND_UP] Cryptocurrency Selection")
    selected_symbol = st.sidebar.selectbox(
        "Choose Cryptocurrency:",
        options=list(Config.SYMBOLS),
        format_func=lambda x: f"{Config.SYMBOL_DISPLAY_NAMES[x]} ({x})",
        key="selected_symbol_cg"
    )

    # Timeframe selection (expanded options)
    selected_timeframe = st.sidebar.selectbox(
        "Timeframe:",
        options=Config.TIMEFRAMES,
        index=5,  # Default to 1day (free tier compatible)
        key="selected_timeframe_cg",
        help="Note: 1min, 5min, 15min, 1hour, 4hour require CoinGecko Enterprise plan. 1day works with free tier."
    )

    # Values automatically stored in session state via widget keys

    st.sidebar.markdown("---")

    # Enhanced risk parameters
    st.sidebar.subheader("[WARNING] Risk Management")

    account_risk = st.sidebar.slider(
        "Account Risk per Trade (%)",
        min_value=0.5,
        max_value=5.0,
        value=2.0,
        step=0.1,
        help="Percentage of account to risk per trade"
    )

    max_leverage = st.sidebar.slider(
        "Maximum Leverage",
        min_value=1.0,
        max_value=5.0,
        value=2.0,
        step=0.5,
        help="Maximum leverage allowed"
    )

    portfolio_limit = st.sidebar.slider(
        "Portfolio Exposure Limit (%)",
        min_value=10,
        max_value=100,
        value=50,
        step=5,
        help="Maximum percentage of portfolio in active positions"
    )

    # Values automatically stored in session state via widget keys

    # Update risk manager settings
    st.session_state.enhanced_risk_manager.max_leverage = max_leverage
    st.session_state.enhanced_risk_manager.max_risk_per_trade = account_risk / 100

    st.sidebar.markdown("---")

    # Trading mode
    st.sidebar.subheader("🤖 Trading Mode")
    auto_trading = st.sidebar.checkbox(
        "Enable Auto Trading",
        value=False,
        help="Automatically execute trades based on AI signals"
    )

    confidence_threshold = st.sidebar.slider(
        "Minimum Signal Confidence (%)",
        min_value=50,
        max_value=95,
        value=70,
        step=5,
        help="Minimum confidence required for auto trading"
    )

    # Values automatically stored in session state via widget keys

    st.sidebar.markdown("---")

    # Market sentiment display
    st.sidebar.subheader("🌡️ Market Sentiment")

    try:
        fear_greed = st.session_state.cg_connector.get_fear_greed_index()
        if fear_greed:
            fg_value = fear_greed['value']
            fg_class = fear_greed['classification']

            # Color based on sentiment
            if fg_value < 25:
                color = "🔴"
            elif fg_value < 50:
                color = "🟡"
            else:
                color = "🟢"

            st.sidebar.metric(
                "Fear & Greed Index",
                f"{fg_value}/100",
                f"{color} {fg_class}"
            )
        else:
            st.sidebar.info("Fear & Greed data unavailable")
    except Exception:
        st.sidebar.info("Loading market sentiment...")

    # API status
    st.sidebar.markdown("---")
    st.sidebar.subheader("📡 CoinGecko API Status")

    # Show request counts
    cg = st.session_state.cg_connector
    st.sidebar.metric("Requests This Minute", f"{cg.request_count_minute}/50")
    st.sidebar.metric("Monthly Usage", f"{cg.request_count_month}/10,000")

    # Connection status
    if hasattr(cg, 'last_request_time') and time.time() - cg.last_request_time < 300:
        st.sidebar.success("🟢 API Connected")
    else:
        st.sidebar.warning("🟡 Testing connection...")

    return selected_symbol, selected_timeframe, account_risk, auto_trading, confidence_threshold

def create_live_trading_tab():
    """Enhanced live trading tab with CoinGecko data"""
    st.header("[BAR_CHART] Live Trading - Enhanced with CoinGecko")

    # Get sidebar values from session state
    selected_symbol = st.session_state.get('selected_symbol_cg', 'bitcoin')
    selected_timeframe = st.session_state.get('selected_timeframe_cg', '1day')  # Changed to 1day (free tier compatible)
    account_risk = st.session_state.get('account_risk_cg', 2.0)
    auto_trading = st.session_state.get('auto_trading_cg', False)
    confidence_threshold = st.session_state.get('confidence_threshold_cg', 70)

    col1, col2 = st.columns([2, 1])

    with col1:
        if st.button("[REFRESH] Fetch Live Data from CoinGecko", type="primary"):
            with st.spinner("Fetching data from CoinGecko API..."):
                try:
                    # Get current price
                    current_price_data = st.session_state.cg_connector.get_current_price(selected_symbol)

                    # Get historical OHLCV data
                    df = st.session_state.cg_connector.get_enhanced_market_data(
                        selected_symbol, selected_timeframe
                    )

                    if df is not None and not df.empty:
                        # Add enhanced technical indicators
                        df_with_indicators = EnhancedTechnicalIndicators.add_all_indicators(
                            df, st.session_state.cg_connector
                        )

                        st.session_state.current_data = df_with_indicators

                        # Display current price info
                        if current_price_data:
                            price = current_price_data['usd']
                            change_24h = current_price_data.get('usd_24h_change', 0)

                            col_a, col_b, col_c, col_d = st.columns(4)

                            with col_a:
                                st.metric(
                                    f"{Config.SYMBOL_DISPLAY_NAMES[selected_symbol]} Price",
                                    f"${price:,.2f}",
                                    f"{change_24h:+.2f}%"
                                )

                            with col_b:
                                volume_24h = current_price_data.get('usd_24h_vol', 0)
                                st.metric("24h Volume", f"${volume_24h:,.0f}")

                            with col_c:
                                market_cap = current_price_data.get('usd_market_cap', 0)
                                st.metric("Market Cap", f"${market_cap:,.0f}")

                            with col_d:
                                if 'rsi' in df_with_indicators.columns:
                                    rsi = df_with_indicators['rsi'].iloc[-1]
                                    st.metric("RSI", f"{rsi:.1f}")

                        # Create enhanced chart
                        fig = create_enhanced_chart(df_with_indicators, selected_symbol)
                        st.plotly_chart(fig, use_container_width=True)

                        st.success("[OK] CoinGecko data loaded successfully!")

                    else:
                        st.error("[ERROR] Failed to fetch data from CoinGecko")
                        if selected_timeframe in ['1min', '5min', '15min', '1hour', '4hour']:
                            st.warning(f"[WARNING] The timeframe '{selected_timeframe}' requires CoinGecko Enterprise plan. Please select '1day' for free tier access.")

                except Exception as e:
                    st.error(f"Error fetching CoinGecko data: {e}")
                    if "401" in str(e) or "Enterprise" in str(e):
                        st.warning(f"[WARNING] API access denied. The timeframe '{selected_timeframe}' requires CoinGecko Enterprise plan. Please select '1day' for free tier access.")

    with col2:
        st.subheader("[TARGET] AI Signal Generation")

        if st.session_state.current_data is not None:
            if st.button("[BRAIN] Generate Enhanced AI Signal", type="primary"):
                with st.spinner("Generating AI signal..."):
                    try:
                        # Generate signal using enhanced ML model
                        signal_result = st.session_state.enhanced_ml_model.predict_signal(
                            st.session_state.current_data
                        )

                        if signal_result.get('success'):
                            st.session_state.latest_signal = signal_result

                            signal = signal_result['signal']
                            confidence = signal_result['confidence']
                            risk_level = signal_result['risk_level']
                            model_type = signal_result.get('model_type', 'Enhanced ML')

                            # Display signal with enhanced formatting
                            if signal == 'BUY':
                                st.success(f"🟢 **{signal}** Signal")
                            elif signal == 'SELL':
                                st.error(f"🔴 **{signal}** Signal")
                            else:
                                st.info(f"🔵 **{signal}** Signal")

                            st.write(f"**Confidence:** {confidence:.1%}")
                            st.write(f"**Risk Level:** {risk_level.title()}")
                            st.write(f"**Model:** {model_type}")

                            # Show predicted return if available
                            if 'predicted_return' in signal_result:
                                pred_return = signal_result['predicted_return']
                                st.write(f"**Predicted Return:** {pred_return:+.2%}")

                            # Show technical analysis
                            if 'technical_analysis' in signal_result:
                                with st.expander("[SEARCH] Technical Analysis Details"):
                                    tech_analysis = signal_result['technical_analysis']
                                    for indicator, status in tech_analysis.items():
                                        st.write(f"**{indicator}:** {status}")

                            # Auto-execute if enabled and confidence is high
                            if (auto_trading and confidence >= confidence_threshold/100
                                and signal in ['BUY', 'SELL']):
                                st.info("🤖 Auto-trading conditions met!")
                                # Execute trade logic here

                        else:
                            st.error(f"Signal generation failed: {signal_result.get('error')}")

                    except Exception as e:
                        st.error(f"Signal generation error: {e}")

        else:
            st.info("Load market data first to generate signals")

        # Manual trading controls
        if st.session_state.latest_signal:
            st.subheader("[MONEY] Manual Trading")

            col_a, col_b = st.columns(2)

            with col_a:
                if st.button("[MONEY] Execute Buy", use_container_width=True):
                    execute_manual_trade(selected_symbol, 'BUY')

            with col_b:
                if st.button("💸 Execute Sell", use_container_width=True):
                    execute_manual_trade(selected_symbol, 'SELL')

def create_enhanced_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Create enhanced chart with multiple indicators"""
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,  # Fixed parameter name
        vertical_spacing=0.05,
        subplot_titles=('Price & Volume', 'RSI', 'MACD', 'ATR'),
        row_heights=[0.5, 0.2, 0.2, 0.1]
    )

    # Price candlesticks
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name=f"{Config.SYMBOL_DISPLAY_NAMES.get(symbol, symbol)} Price"
        ),
        row=1, col=1
    )

    # Bollinger Bands
    if 'bb_upper' in df.columns and 'bb_lower' in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['bb_upper'], name='BB Upper', line=dict(color='gray', dash='dash')),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df.index, y=df['bb_lower'], name='BB Lower', line=dict(color='gray', dash='dash')),
            row=1, col=1
        )

    # Moving averages
    if 'sma_20' in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['sma_20'], name='SMA 20', line=dict(color='orange')),
            row=1, col=1
        )

    # Volume
    if 'volume' in df.columns:
        fig.add_trace(
            go.Bar(x=df.index, y=df['volume'], name='Volume', opacity=0.3),
            row=1, col=1
        )

    # RSI
    if 'rsi' in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['rsi'], name='RSI', line=dict(color='purple')),
            row=2, col=1
        )
        # RSI levels
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    # MACD
    if 'macd' in df.columns and 'macd_signal' in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['macd'], name='MACD', line=dict(color='blue')),
            row=3, col=1
        )
        fig.add_trace(
            go.Scatter(x=df.index, y=df['macd_signal'], name='Signal', line=dict(color='red')),
            row=3, col=1
        )
        if 'macd_histogram' in df.columns:
            fig.add_trace(
                go.Bar(x=df.index, y=df['macd_histogram'], name='Histogram'),
                row=3, col=1
            )

    # ATR
    if 'atr' in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['atr'], name='ATR', line=dict(color='green')),
            row=4, col=1
        )

    fig.update_layout(
        title=f"Enhanced {Config.SYMBOL_DISPLAY_NAMES.get(symbol, symbol)} Analysis",
        height=800,
        showlegend=True
    )

    return fig

def create_market_overview_tab():
    """Create market overview tab with global data"""
    st.header("🌍 Global Market Overview")

    try:
        # Get global market data
        global_data = st.session_state.cg_connector.get_global_market_data()

        if global_data:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                total_market_cap = global_data.get('total_market_cap', {}).get('usd', 0)
                st.metric(
                    "Total Market Cap",
                    f"${total_market_cap/1e12:.2f}T",
                    f"{global_data.get('market_cap_change_percentage_24h_usd', 0):+.2f}%"
                )

            with col2:
                total_volume = global_data.get('total_volume', {}).get('usd', 0)
                st.metric("24h Volume", f"${total_volume/1e9:.1f}B")

            with col3:
                btc_dominance = global_data.get('market_cap_percentage', {}).get('btc', 0)
                st.metric("BTC Dominance", f"{btc_dominance:.1f}%")

            with col4:
                active_cryptocurrencies = global_data.get('active_cryptocurrencies', 0)
                st.metric("Active Cryptocurrencies", f"{active_cryptocurrencies:,}")

        # Get trending coins
        st.subheader("[FIRE] Trending Cryptocurrencies")
        trending = st.session_state.cg_connector.get_trending_coins()

        if trending:
            for i, coin in enumerate(trending[:5]):
                coin_data = coin['item']
                col1, col2, col3 = st.columns([2, 1, 1])

                with col1:
                    st.write(f"**{coin_data['name']} ({coin_data['symbol']})**")

                with col2:
                    st.write(f"Rank: #{coin_data['market_cap_rank'] or 'N/A'}")

                with col3:
                    if st.button(f"Analyze {coin_data['symbol']}", key=f"analyze_{i}"):
                        st.info(f"Analysis for {coin_data['name']} would be shown here")

    except Exception as e:
        st.error(f"Error loading market overview: {e}")

def create_system_status_tab():
    """Create system status tab"""
    st.header("⚙️ System Status & Performance")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📡 CoinGecko API Status")

        cg = st.session_state.cg_connector

        # API usage metrics
        st.metric("Requests This Minute", f"{cg.request_count_minute}/50")
        st.metric("Monthly Usage", f"{cg.request_count_month}/10,000")

        usage_percentage = (cg.request_count_month / 10000) * 100
        st.progress(usage_percentage / 100)
        st.write(f"Monthly usage: {usage_percentage:.1f}%")

        # Connection test
        if st.button("[SEARCH] Test API Connection"):
            with st.spinner("Testing connection..."):
                try:
                    test_data = cg.get_current_price('bitcoin')
                    if test_data:
                        st.success("[OK] CoinGecko API connection successful!")
                        st.write(f"BTC Price: ${test_data['usd']:,.2f}")
                    else:
                        st.error("[ERROR] API connection failed")
                except Exception as e:
                    st.error(f"Connection test failed: {e}")

    with col2:
        st.subheader("[BRAIN] ML Model Status")

        ml_model = st.session_state.enhanced_ml_model

        if ml_model.is_trained:
            st.success("[OK] Enhanced ML Model Trained")

            if ml_model.training_history:
                latest_training = ml_model.training_history[-1]
                st.metric("Model Accuracy", f"{latest_training['accuracy']:.1%}")
                st.metric("Training Samples", latest_training['samples'])

                if 'price_r2' in latest_training:
                    st.metric("Price Prediction R²", f"{latest_training['price_r2']:.3f}")
        else:
            st.warning("[WARNING] ML Model Not Trained")
            st.info("Train the model in the AI Training tab")

    # Performance metrics
    st.subheader("[BAR_CHART] System Performance")

    # Cache performance
    cache_size = len(cg.memory_cache)
    st.metric("Cache Entries", cache_size)

    # Show recent activity
    if hasattr(cg, 'last_request_time'):
        last_request = datetime.fromtimestamp(cg.last_request_time)
        time_since = datetime.now() - last_request
        st.write(f"Last API request: {time_since.seconds} seconds ago")

def create_ai_training_tab():
    """Create AI training tab"""
    st.header("[BRAIN] Enhanced AI Model Training")

    selected_symbol = st.session_state.get('selected_symbol_cg', 'bitcoin')

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Training Configuration")

        training_period = st.selectbox(
            "Training Period",
            ["30 days", "90 days", "180 days", "365 days"],
            index=1
        )

        period_map = {"30 days": 30, "90 days": 90, "180 days": 180, "365 days": 365}
        days = period_map[training_period]

        if st.button("[ROCKET] Train Enhanced ML Model", type="primary"):
            with st.spinner("Training enhanced ML model..."):
                try:
                    # Get training data
                    df = st.session_state.cg_connector.get_enhanced_market_data(
                        selected_symbol, '1day'
                    )

                    if df is not None and len(df) > 100:
                        # Add enhanced indicators
                        df_with_indicators = EnhancedTechnicalIndicators.add_all_indicators(
                            df, st.session_state.cg_connector
                        )

                        # Train the model
                        training_results = st.session_state.enhanced_ml_model.train_model(df_with_indicators)

                        if training_results.get('success'):
                            st.success("[OK] Enhanced model trained successfully!")

                            col_a, col_b, col_c = st.columns(3)

                            with col_a:
                                st.metric("Accuracy", f"{training_results['accuracy']:.2%}")

                            with col_b:
                                st.metric("Training Samples", training_results['training_samples'])

                            with col_c:
                                st.metric("Features Used", training_results['features_used'])

                            # Show feature importance
                            if 'feature_importance' in training_results:
                                st.subheader("[BAR_CHART] Feature Importance")
                                importance_df = pd.DataFrame([
                                    {'Feature': k, 'Importance': v}
                                    for k, v in training_results['feature_importance'].items()
                                ]).sort_values('Importance', ascending=False).head(10)

                                fig = px.bar(importance_df, x='Importance', y='Feature', orientation='h')
                                st.plotly_chart(fig, use_container_width=True)

                        else:
                            st.error(f"Training failed: {training_results.get('error')}")

                    else:
                        st.error("Insufficient data for training")

                except Exception as e:
                    st.error(f"Training error: {e}")

    with col2:
        st.subheader("Model Performance")

        ml_model = st.session_state.enhanced_ml_model

        if ml_model.is_trained:
            st.success("[OK] Model is trained and ready")

            if ml_model.training_history:
                history_df = pd.DataFrame(ml_model.training_history)

                fig = px.line(history_df, x='timestamp', y='accuracy', title='Training Accuracy Over Time')
                st.plotly_chart(fig, use_container_width=True)

        else:
            st.warning("[WARNING] Model not trained yet")
            st.info("Train the model using the controls on the left")

def create_backtesting_tab():
    """Create backtesting tab"""
    st.header("[TREND_UP] Enhanced Backtesting")
    st.info("Backtesting with CoinGecko historical data")

    selected_symbol = st.session_state.get('selected_symbol_cg', 'bitcoin')

    # Backtesting would be implemented here with enhanced features
    st.write("Enhanced backtesting features coming soon!")

def create_paper_trading_tab():
    """Create paper trading tab"""
    st.header("[MONEY] Enhanced Paper Trading")

    selected_symbol = st.session_state.get('selected_symbol_cg', 'bitcoin')

    # Get portfolio status
    portfolio_status = st.session_state.enhanced_paper_trader.get_portfolio_status()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Value", f"${portfolio_status['total_value']:,.2f}")

    with col2:
        st.metric("Available Cash", f"${portfolio_status['available_cash']:,.2f}")

    with col3:
        st.metric("Total Return", f"{portfolio_status['total_return']:+.2f}%")

    # Show positions
    if portfolio_status['positions']:
        st.subheader("[BAR_CHART] Current Positions")

        for symbol, position in portfolio_status['positions'].items():
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.write(f"**{Config.SYMBOL_DISPLAY_NAMES.get(symbol, symbol)}**")

            with col2:
                st.write(f"Shares: {position['shares']:.6f}")

            with col3:
                st.write(f"Entry: ${position['entry_price']:,.2f}")

            with col4:
                st.write(f"Value: ${position['current_value']:,.2f}")

def execute_manual_trade(symbol: str, action: str):
    """Execute manual trade"""
    try:
        if st.session_state.current_data is not None:
            current_price = st.session_state.current_data['close'].iloc[-1]

            # Calculate position size based on risk management
            if action == 'BUY':
                stop_loss = current_price * 0.98  # 2% stop loss
            else:
                stop_loss = current_price * 1.02  # 2% stop loss for short

            position_calc = st.session_state.enhanced_risk_manager.calculate_position_size(
                entry_price=current_price,
                stop_loss_price=stop_loss,
                account_risk_pct=0.02,
                confidence=st.session_state.latest_signal.get('confidence', 1.0)
            )

            if position_calc.get('success'):
                quantity = position_calc['position_size']

                trade_result = st.session_state.enhanced_paper_trader.execute_trade(
                    symbol=symbol,
                    action=action,
                    price=current_price,
                    quantity=quantity,
                    signal=st.session_state.latest_signal.get('signal', action),
                    confidence=st.session_state.latest_signal.get('confidence', 1.0)
                )

                if trade_result.get('success'):
                    st.success(f"[OK] {action} order executed: {quantity:.6f} {Config.SYMBOL_DISPLAY_NAMES.get(symbol, symbol)}")

                    # Save to database
                    st.session_state.enhanced_db_manager.save_trading_signal({
                        'symbol': symbol,
                        'timeframe': 'manual',
                        'signal': action,
                        'confidence': st.session_state.latest_signal.get('confidence', 1.0),
                        'current_price': current_price
                    })

                    st.rerun()
                else:
                    st.error(f"Trade failed: {trade_result.get('error')}")
            else:
                st.error(f"Position calculation failed: {position_calc.get('error')}")

    except Exception as e:
        st.error(f"Manual trade error: {e}")

# ==========================================
# MAIN APPLICATION
# ==========================================

if __name__ == "__main__":
    main_dashboard()