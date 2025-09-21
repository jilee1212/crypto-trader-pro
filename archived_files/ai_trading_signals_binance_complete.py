#!/usr/bin/env python3
"""
AI Trading Signals - Binance Testnet Integration
Complete CoinGecko + Binance Testnet Trading System

Features:
- CoinGecko market data and analysis
- Binance Testnet live trading
- AI signal generation
- Risk management
- Paper trading simulation
"""

import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import warnings
warnings.filterwarnings('ignore')

# Import all components
try:
    from ai_trading_signals_coingecko import (
        Config, CoinGeckoConnector, EnhancedTechnicalIndicators,
        EnhancedATRCalculator, EnhancedRiskManager
    )
    from coingecko_ml_components import (
        EnhancedMLSignalGenerator, EnhancedPaperTradingSimulator,
        EnhancedDatabaseManager
    )
    from binance_testnet_connector import BinanceTestnetConnector
except ImportError as e:
    st.error(f"Required components not found: {e}")
    st.stop()

# ML and visualization libraries
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError as e:
    st.error(f"Required library missing: {e}")
    st.stop()

# ==========================================
# MAIN DASHBOARD FUNCTIONS
# ==========================================

def main_dashboard():
    """Enhanced main dashboard with Binance Testnet integration"""
    st.set_page_config(
        page_title="Crypto Trader Pro - Binance Edition",
        page_icon="[ROCKET]",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize session state
    init_session_state()

    # Enhanced header
    st.markdown("""
    <div style="background: linear-gradient(90deg, #f0b90b 0%, #1e2329 100%); padding: 1rem; border-radius: 10px; margin-bottom: 2rem;">
        <h1 style="color: white; text-align: center; margin: 0;">
            [ROCKET] Crypto Trader Pro - Binance Edition
        </h1>
        <p style="color: white; text-align: center; margin: 0; opacity: 0.9;">
            CoinGecko Analysis + Binance Testnet Live Trading
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Enhanced sidebar
    create_enhanced_sidebar()

    # Main content tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "[BAR_CHART] Market Analysis",
        "[ROCKET] Live Trading",
        "[MONITOR] Live Trading Monitor",
        "[BRAIN] AI Training",
        "[MONEY] Paper Trading",
        "[CHART] Binance Account",
        "[TOOL] System Status"
    ])

    with tab1:
        create_market_analysis_tab()

    with tab2:
        create_live_trading_tab()

    with tab3:
        create_live_trading_monitor_tab()

    with tab4:
        create_ai_training_tab()

    with tab5:
        create_paper_trading_tab()

    with tab6:
        create_binance_account_tab()

    with tab7:
        create_system_status_tab()

def init_session_state():
    """Initialize session state components"""
    # Initialize auto-refresh settings
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = False

    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()

    if 'cg_connector' not in st.session_state:
        st.session_state.cg_connector = CoinGeckoConnector()

    if 'binance_connector' not in st.session_state:
        st.session_state.binance_connector = BinanceTestnetConnector()

    if 'enhanced_ml_model' not in st.session_state:
        st.session_state.enhanced_ml_model = EnhancedMLSignalGenerator()

    if 'enhanced_paper_trader' not in st.session_state:
        st.session_state.enhanced_paper_trader = EnhancedPaperTradingSimulator(initial_capital=10000)

    if 'enhanced_risk_manager' not in st.session_state:
        st.session_state.enhanced_risk_manager = EnhancedRiskManager(account_balance=10000)

    if 'current_data' not in st.session_state:
        st.session_state.current_data = None

    if 'latest_signal' not in st.session_state:
        st.session_state.latest_signal = None

def create_enhanced_sidebar():
    """Create enhanced sidebar with trading controls"""
    st.sidebar.title("[ROCKET] Trading Controls")
    st.sidebar.markdown("---")

    # Cryptocurrency selection
    st.sidebar.subheader("[TREND_UP] Symbol Selection")
    selected_symbol = st.sidebar.selectbox(
        "Cryptocurrency:",
        options=['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT'],
        key="selected_symbol_binance"
    )

    # Trading mode
    st.sidebar.subheader("[WARNING] Trading Mode")
    trading_mode = st.sidebar.radio(
        "Select Mode:",
        ["Analysis Only", "Paper Trading", "Live Trading (Testnet)"],
        key="trading_mode"
    )

    if trading_mode == "Live Trading (Testnet)":
        st.sidebar.warning("[WARNING] Using Binance Testnet - No real funds at risk")

    # Risk management
    st.sidebar.subheader("[SHIELD] Risk Management")
    risk_per_trade = st.sidebar.slider(
        "Risk per Trade (%)",
        min_value=0.5,
        max_value=5.0,
        value=2.0,
        step=0.1,
        key="risk_per_trade"
    )

    position_size = st.sidebar.slider(
        "Position Size (%)",
        min_value=1.0,
        max_value=10.0,
        value=5.0,
        step=0.5,
        key="position_size"
    )

    # AI settings
    st.sidebar.subheader("[BRAIN] AI Settings")
    confidence_threshold = st.sidebar.slider(
        "Signal Confidence Threshold (%)",
        min_value=50,
        max_value=95,
        value=70,
        step=5,
        key="confidence_threshold"
    )

    auto_trading = st.sidebar.checkbox(
        "Enable Auto Trading",
        value=False,
        key="auto_trading",
        help="Automatically execute trades based on AI signals"
    )

    st.sidebar.markdown("---")

    # Binance connection status
    st.sidebar.subheader("[GLOBE] Binance Status")
    if st.sidebar.button("[SEARCH] Test Binance Connection"):
        test_binance_connection()

    return selected_symbol, trading_mode, risk_per_trade, auto_trading

def test_binance_connection():
    """Test Binance Testnet connection"""
    with st.spinner("Testing Binance connection..."):
        result = st.session_state.binance_connector.test_connection()

        if result.get('success'):
            st.sidebar.success("[OK] Binance Testnet Connected!")
            st.sidebar.write(f"Account Type: {result.get('account_type')}")
            st.sidebar.write(f"Permissions: {', '.join(result.get('permissions', []))}")
        else:
            st.sidebar.error(f"[ERROR] Connection Failed: {result.get('error')}")

def create_market_analysis_tab():
    """Market analysis with CoinGecko data"""
    st.header("[BAR_CHART] Market Analysis")

    selected_symbol = st.session_state.get('selected_symbol_binance', 'BTCUSDT')

    # Convert Binance symbol to CoinGecko ID
    symbol_map = {
        'BTCUSDT': 'bitcoin',
        'ETHUSDT': 'ethereum',
        'BNBUSDT': 'binancecoin',
        'ADAUSDT': 'cardano',
        'SOLUSDT': 'solana'
    }

    coingecko_id = symbol_map.get(selected_symbol, 'bitcoin')

    col1, col2 = st.columns([2, 1])

    with col1:
        if st.button("[REFRESH] Fetch Market Data", type="primary"):
            with st.spinner("Fetching market data..."):
                try:
                    # Get CoinGecko data
                    current_price_data = st.session_state.cg_connector.get_current_price(coingecko_id)
                    df = st.session_state.cg_connector.get_enhanced_market_data(coingecko_id, '1day')

                    if df is not None and not df.empty:
                        # Add technical indicators
                        df_with_indicators = EnhancedTechnicalIndicators.add_all_indicators(
                            df, st.session_state.cg_connector
                        )

                        st.session_state.current_data = df_with_indicators

                        # Display metrics
                        if current_price_data:
                            price = current_price_data['usd']
                            change_24h = current_price_data.get('usd_24h_change', 0)

                            col_a, col_b, col_c, col_d = st.columns(4)

                            with col_a:
                                st.metric(
                                    f"{selected_symbol} Price",
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

                        # Create chart
                        fig = create_enhanced_chart(df_with_indicators, selected_symbol)
                        st.plotly_chart(fig, use_container_width=True)

                        st.success("[OK] Market data loaded successfully!")

                    else:
                        st.error("[ERROR] Failed to fetch market data")

                except Exception as e:
                    st.error(f"Error fetching data: {e}")

    with col2:
        st.subheader("[TARGET] Quick Actions")

        # Binance price check
        if st.button("[SEARCH] Check Binance Price"):
            with st.spinner("Getting Binance price..."):
                price_result = st.session_state.binance_connector.get_current_price(selected_symbol)

                if price_result.get('success'):
                    st.success(f"Binance Price: ${price_result['price']:,.2f}")
                else:
                    st.error(f"Error: {price_result.get('error')}")

        # AI signal generation
        if st.session_state.current_data is not None:
            if st.button("[BRAIN] Generate AI Signal"):
                generate_ai_signal()

def generate_ai_signal():
    """Generate AI trading signal"""
    with st.spinner("Generating AI signal..."):
        try:
            signal_result = st.session_state.enhanced_ml_model.predict_signal(
                st.session_state.current_data
            )

            if signal_result.get('success'):
                st.session_state.latest_signal = signal_result

                signal = signal_result['signal']
                confidence = signal_result['confidence']

                # Display signal
                if signal == 'BUY':
                    st.success(f"[OK] **{signal}** Signal (Confidence: {confidence:.1%})")
                elif signal == 'SELL':
                    st.error(f"[ERROR] **{signal}** Signal (Confidence: {confidence:.1%})")
                else:
                    st.info(f"[INFO] **{signal}** Signal (Confidence: {confidence:.1%})")

                # Show additional details
                with st.expander("Signal Details"):
                    st.write(f"**Risk Level:** {signal_result.get('risk_level', 'N/A')}")
                    st.write(f"**Model Type:** {signal_result.get('model_type', 'N/A')}")
                    if 'predicted_return' in signal_result:
                        st.write(f"**Predicted Return:** {signal_result['predicted_return']:+.2%}")

            else:
                st.error(f"Signal generation failed: {signal_result.get('error')}")

        except Exception as e:
            st.error(f"Signal generation error: {e}")

def create_live_trading_tab():
    """Live trading with Binance Testnet"""
    st.header("[ROCKET] Live Trading")

    selected_symbol = st.session_state.get('selected_symbol_binance', 'BTCUSDT')
    trading_mode = st.session_state.get('trading_mode', 'Analysis Only')

    if trading_mode == "Analysis Only":
        st.info("[INFO] Switch to 'Live Trading (Testnet)' mode in sidebar to enable trading")
        return

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("[MONEY] Manual Trading")

        # Order type selection
        order_type = st.radio("Order Type:", ["Market", "Limit"])

        # Buy section
        st.write("**Buy Order**")
        buy_quantity = st.number_input(
            "Buy Quantity:",
            min_value=0.001,
            value=0.01,
            step=0.001,
            key="buy_quantity"
        )

        if order_type == "Limit":
            buy_price = st.number_input(
                "Buy Price ($):",
                min_value=0.01,
                value=100000.0,
                key="buy_price"
            )

        if st.button("[MONEY] Execute Buy Order", type="primary"):
            execute_buy_order(selected_symbol, order_type, buy_quantity,
                            buy_price if order_type == "Limit" else None)

        st.markdown("---")

        # Sell section
        st.write("**Sell Order**")
        sell_quantity = st.number_input(
            "Sell Quantity:",
            min_value=0.001,
            value=0.01,
            step=0.001,
            key="sell_quantity"
        )

        if order_type == "Limit":
            sell_price = st.number_input(
                "Sell Price ($):",
                min_value=0.01,
                value=100000.0,
                key="sell_price"
            )

        if st.button("💸 Execute Sell Order", type="secondary"):
            execute_sell_order(selected_symbol, order_type, sell_quantity,
                             sell_price if order_type == "Limit" else None)

    with col2:
        st.subheader("[CHART] Account Info")

        if st.button("[REFRESH] Refresh Account"):
            display_account_info()

        st.markdown("---")

        st.subheader("[TARGET] Open Orders")

        if st.button("[SEARCH] Check Open Orders"):
            display_open_orders(selected_symbol)

def execute_buy_order(symbol: str, order_type: str, quantity: float, price: float = None):
    """Execute buy order on Binance Testnet"""
    with st.spinner("Executing buy order..."):
        try:
            if order_type == "Market":
                result = st.session_state.binance_connector.place_market_order(
                    symbol, 'BUY', quantity
                )
            else:  # Limit order
                result = st.session_state.binance_connector.place_limit_order(
                    symbol, 'BUY', quantity, price
                )

            if result.get('success'):
                st.success(f"[OK] Buy order executed! Order ID: {result.get('order_id')}")
                st.write(f"Quantity: {result.get('quantity')} {symbol}")
                if result.get('price'):
                    st.write(f"Price: ${result.get('price'):,.2f}")
                st.write(f"Status: {result.get('status')}")
            else:
                st.error(f"[ERROR] Order failed: {result.get('error')}")

        except Exception as e:
            st.error(f"Order execution error: {e}")

def execute_sell_order(symbol: str, order_type: str, quantity: float, price: float = None):
    """Execute sell order on Binance Testnet"""
    with st.spinner("Executing sell order..."):
        try:
            if order_type == "Market":
                result = st.session_state.binance_connector.place_market_order(
                    symbol, 'SELL', quantity
                )
            else:  # Limit order
                result = st.session_state.binance_connector.place_limit_order(
                    symbol, 'SELL', quantity, price
                )

            if result.get('success'):
                st.success(f"[OK] Sell order executed! Order ID: {result.get('order_id')}")
                st.write(f"Quantity: {result.get('quantity')} {symbol}")
                if result.get('price'):
                    st.write(f"Price: ${result.get('price'):,.2f}")
                st.write(f"Status: {result.get('status')}")
            else:
                st.error(f"[ERROR] Order failed: {result.get('error')}")

        except Exception as e:
            st.error(f"Order execution error: {e}")

def display_account_info():
    """Display Binance account information"""
    with st.spinner("Fetching account info..."):
        account_info = st.session_state.binance_connector.get_account_info()

        if account_info.get('success'):
            st.write(f"**Account Type:** {account_info.get('account_type')}")
            st.write(f"**Can Trade:** {account_info.get('can_trade')}")
            st.write(f"**Permissions:** {', '.join(account_info.get('permissions', []))}")

            # Show balances
            balances = account_info.get('balances', [])
            if balances:
                st.write("**Top Balances:**")
                df_balances = pd.DataFrame(balances[:10])  # Show top 10
                st.dataframe(df_balances)
            else:
                st.info("No balances found")
        else:
            st.error(f"Failed to get account info: {account_info.get('error')}")

def display_open_orders(symbol: str = None):
    """Display open orders"""
    with st.spinner("Fetching open orders..."):
        orders_result = st.session_state.binance_connector.get_open_orders(symbol)

        if orders_result.get('success'):
            orders = orders_result.get('orders', [])
            if orders:
                df_orders = pd.DataFrame(orders)
                st.dataframe(df_orders)

                # Add cancel buttons
                for order in orders:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"Order {order['order_id']}: {order['side']} {order['quantity']} {order['symbol']}")
                    with col2:
                        if st.button(f"Cancel", key=f"cancel_{order['order_id']}"):
                            cancel_order(order['symbol'], order['order_id'])
            else:
                st.info("No open orders")
        else:
            st.error(f"Failed to get orders: {orders_result.get('error')}")

def cancel_order(symbol: str, order_id: int):
    """Cancel an order"""
    with st.spinner("Cancelling order..."):
        result = st.session_state.binance_connector.cancel_order(symbol, order_id)

        if result.get('success'):
            st.success(f"[OK] Order {order_id} cancelled successfully")
            st.rerun()
        else:
            st.error(f"Failed to cancel order: {result.get('error')}")

def create_binance_account_tab():
    """Binance account management tab"""
    st.header("[CHART] Binance Account Management")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("[MONEY] Account Overview")

        if st.button("[REFRESH] Refresh Account Data"):
            account_info = st.session_state.binance_connector.get_account_info()

            if account_info.get('success'):
                st.success("[OK] Account data refreshed")

                # Account details
                st.write(f"**Account Type:** {account_info.get('account_type')}")
                st.write(f"**Trading Enabled:** {account_info.get('can_trade')}")
                st.write(f"**Permissions:** {', '.join(account_info.get('permissions', []))}")

                # Portfolio value calculation
                balances = account_info.get('balances', [])
                total_value = 0

                for balance in balances:
                    if balance['asset'] == 'USDT':
                        total_value += balance['total']

                st.metric("Portfolio Value (USDT)", f"${total_value:,.2f}")

    with col2:
        st.subheader("[BAR_CHART] Top Holdings")

        # Show top balances
        account_info = st.session_state.binance_connector.get_account_info()
        if account_info.get('success'):
            balances = account_info.get('balances', [])
            if balances:
                # Sort by total value
                sorted_balances = sorted(balances, key=lambda x: x['total'], reverse=True)[:10]

                if sorted_balances:
                    df = pd.DataFrame(sorted_balances)
                    fig = px.bar(df, x='asset', y='total', title='Top 10 Holdings')
                    st.plotly_chart(fig, use_container_width=True)

    # Recent orders section
    st.subheader("[TARGET] Order Management")

    col3, col4 = st.columns([1, 1])

    with col3:
        if st.button("[SEARCH] Show All Open Orders"):
            display_open_orders()

    with col4:
        symbol_to_check = st.selectbox(
            "Check orders for symbol:",
            ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
        )
        if st.button(f"[SEARCH] Show {symbol_to_check} Orders"):
            display_open_orders(symbol_to_check)

def create_enhanced_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Create enhanced chart with multiple indicators"""
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
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
            name=f"{symbol} Price"
        ),
        row=1, col=1
    )

    # RSI
    if 'rsi' in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['rsi'], name='RSI', line=dict(color='purple')),
            row=2, col=1
        )
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

    fig.update_layout(
        title=f"Enhanced {symbol} Analysis",
        height=800,
        showlegend=True
    )

    return fig

def create_ai_training_tab():
    """AI training tab"""
    st.header("[BRAIN] Enhanced AI Model Training")
    st.info("Use the same AI training functionality from the CoinGecko system")

def create_paper_trading_tab():
    """Paper trading tab"""
    st.header("[MONEY] Enhanced Paper Trading")
    st.info("Paper trading simulation without real funds")

def create_live_trading_monitor_tab():
    """Live Trading Monitor tab with real-time monitoring and controls"""
    st.header("[MONITOR] Live Trading Monitor")
    st.markdown("Real-time trading monitoring and control center")

    # Initialize trading system if not exists
    if 'live_trading_system' not in st.session_state:
        from ai_live_trading_system import AILiveTradingSystem, TradingMode
        st.session_state.live_trading_system = AILiveTradingSystem(TradingMode.DEMO)

    trading_system = st.session_state.live_trading_system

    # Control Panel
    st.subheader("[CONTROL] Trading Control Panel")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Auto Trading Toggle
        auto_trading = st.toggle("Auto Trading", value=not trading_system.emergency_stop)
        if auto_trading != (not trading_system.emergency_stop):
            if auto_trading:
                trading_system.reset_emergency_stop()
                st.success("[OK] Auto trading enabled")
            else:
                trading_system.emergency_stop_trading()
                st.warning("[STOP] Auto trading disabled")

    with col2:
        # Emergency Stop Button
        if st.button("[EMERGENCY] Emergency Stop", type="secondary"):
            trading_system.emergency_stop_trading()
            st.error("[EMERGENCY] Emergency stop activated!")

    with col3:
        # Trading Mode Selection
        current_mode = "DEMO" if trading_system.mode.value == "demo" else "LIVE"
        new_mode = st.selectbox("Trading Mode", ["DEMO", "LIVE"], index=0 if current_mode == "DEMO" else 1)
        if new_mode != current_mode:
            st.warning(f"[CHANGE] Mode change to {new_mode} requires restart")

    with col4:
        # Risk Level Adjustment
        risk_level = st.slider("Risk Level", 1, 5, 3)
        trading_system.position_size_base = 0.01 * risk_level
        st.info(f"Position Size: {trading_system.position_size_base*100:.1f}%")

    st.divider()

    # Real-time Status Display
    col1, col2 = st.columns([2, 1])

    with col1:
        # Current Positions
        st.subheader("[CHART] Current Positions")

        if trading_system.current_positions:
            # Create positions DataFrame
            positions_data = []
            for symbol, position in trading_system.current_positions.items():
                positions_data.append({
                    'Symbol': position.symbol,
                    'Side': position.side,
                    'Quantity': f"{position.quantity:.8f}",
                    'Entry Price': f"${position.entry_price:,.2f}",
                    'Current Price': f"${position.current_price:,.2f}",
                    'PnL': f"${position.pnl:.2f}",
                    'PnL %': f"{position.pnl_percentage:+.2f}%",
                    'Stop Loss': f"${position.stop_loss:,.2f}",
                    'Take Profit': f"${position.take_profit:,.2f}"
                })

            positions_df = pd.DataFrame(positions_data)
            st.dataframe(positions_df, use_container_width=True)

            # PnL Chart
            fig = go.Figure()
            for symbol, position in trading_system.current_positions.items():
                fig.add_trace(go.Bar(
                    x=[symbol],
                    y=[position.pnl],
                    name=f"{symbol} PnL",
                    marker_color='green' if position.pnl >= 0 else 'red'
                ))

            fig.update_layout(
                title="Position PnL",
                yaxis_title="PnL ($)",
                showlegend=False,
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("[INFO] No active positions")

    with col2:
        # Account Summary
        st.subheader("[MONEY] Account Summary")

        # Get status report
        status = trading_system.get_status_report()

        # Get real-time Binance account info
        binance_connector = st.session_state.binance_connector
        account_info = binance_connector.get_account_info()

        if account_info and account_info.get('success'):
            balances = account_info.get('balances', [])
            usdt_balance = next((b for b in balances if b['asset'] == 'USDT'), None)
            btc_balance = next((b for b in balances if b['asset'] == 'BTC'), None)

            if usdt_balance:
                st.metric("USDT Balance", f"${float(usdt_balance.get('free', 0)):,.2f}")
            if btc_balance:
                st.metric("BTC Balance", f"{float(btc_balance.get('free', 0)):.8f}")

        # Display key metrics
        st.metric("Daily PnL", f"${status.get('daily_stats', {}).get('pnl', 0):.2f}")
        st.metric("Daily Volume", f"${status.get('daily_stats', {}).get('volume', 0):.2f}")
        st.metric("Total Trades", status.get('daily_stats', {}).get('trades', 0))
        st.metric("Consecutive Losses", status.get('daily_stats', {}).get('consecutive_losses', 0))

        # Remaining limits
        remaining_limit = status.get('limits', {}).get('remaining_limit', 100)
        st.metric("Remaining Limit", f"${remaining_limit:.2f}")

        # Progress bar for daily limit
        daily_limit = status.get('limits', {}).get('daily_limit', 100)
        used_percentage = ((daily_limit - remaining_limit) / daily_limit) * 100
        st.progress(used_percentage / 100)
        st.caption(f"{used_percentage:.1f}% of daily limit used")

        # Real-time prices
        st.subheader("[CHART] Live Prices")
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        for symbol in symbols:
            price_info = binance_connector.get_current_price(symbol)
            if price_info and price_info.get('success'):
                price = price_info.get('price', 0)
                st.metric(symbol, f"${price:,.2f}")
            else:
                st.metric(symbol, "N/A")

    st.divider()

    # Trading History and AI Signals
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("[HISTORY] Recent Trading History")

        if trading_system.trading_history:
            # Display last 10 trades
            recent_trades = trading_system.trading_history[-10:]

            history_data = []
            for trade in recent_trades:
                history_data.append({
                    'Time': trade['timestamp'].strftime('%H:%M:%S'),
                    'Symbol': trade['symbol'],
                    'Side': trade['side'],
                    'Quantity': f"{trade['quantity']:.8f}",
                    'Entry': f"${trade['entry_price']:,.2f}",
                    'Exit': f"${trade['exit_price']:,.2f}",
                    'PnL': f"${trade['pnl']:+.2f}",
                    'Reason': trade['reason']
                })

            history_df = pd.DataFrame(history_data)
            st.dataframe(history_df, use_container_width=True)

            # Trading performance chart
            if len(recent_trades) > 1:
                cumulative_pnl = np.cumsum([trade['pnl'] for trade in recent_trades])

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=list(range(len(cumulative_pnl))),
                    y=cumulative_pnl,
                    mode='lines+markers',
                    name='Cumulative PnL',
                    line=dict(color='blue')
                ))

                fig.update_layout(
                    title="Cumulative PnL",
                    xaxis_title="Trade Number",
                    yaxis_title="Cumulative PnL ($)",
                    height=300
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("[INFO] No trading history available")

    with col2:
        st.subheader("[BRAIN] AI Signal Monitoring")

        # Generate current signal
        if st.button("[REFRESH] Get Latest Signal", type="primary"):
            with st.spinner("Generating AI signal..."):
                try:
                    signal = trading_system.generate_trading_signal('BTCUSDT')

                    if signal and hasattr(signal, 'signal'):
                        st.session_state.latest_signal = signal
                        st.success(f"[OK] Signal generated: {signal.signal.value}")
                    else:
                        st.error("[ERROR] Failed to generate valid signal")
                        if 'latest_signal' in st.session_state:
                            del st.session_state.latest_signal
                except Exception as e:
                    st.error(f"[ERROR] Signal generation failed: {str(e)}")
                    if 'latest_signal' in st.session_state:
                        del st.session_state.latest_signal

        # Display latest signal
        if ('latest_signal' in st.session_state and
            st.session_state.latest_signal is not None and
            hasattr(st.session_state.latest_signal, 'signal') and
            st.session_state.latest_signal.signal is not None):

            signal = st.session_state.latest_signal

            # Signal display
            try:
                signal_color = {
                    'BUY': 'green',
                    'SELL': 'red',
                    'HOLD': 'orange'
                }.get(signal.signal.value, 'gray')
            except (AttributeError, TypeError):
                signal_color = 'gray'

            try:
                signal_value = getattr(signal.signal, 'value', 'UNKNOWN')
                signal_symbol = getattr(signal, 'symbol', 'N/A')
                signal_confidence = getattr(signal, 'confidence', 0)
                signal_price = getattr(signal, 'price', 0)
                signal_timestamp = getattr(signal, 'timestamp', datetime.now())

                st.markdown(f"""
                <div style="padding: 1rem; border-radius: 10px; background-color: {signal_color}20; border: 2px solid {signal_color};">
                    <h4 style="color: {signal_color}; margin: 0;">{signal_value} Signal</h4>
                    <p style="margin: 0.5rem 0;">Symbol: {signal_symbol}</p>
                    <p style="margin: 0.5rem 0;">Confidence: {signal_confidence:.2%}</p>
                    <p style="margin: 0.5rem 0;">Price: ${signal_price:,.2f}</p>
                    <p style="margin: 0;">Time: {signal_timestamp.strftime('%H:%M:%S')}</p>
                </div>
                """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"[ERROR] Signal display failed: {str(e)}")
                if 'latest_signal' in st.session_state:
                    del st.session_state.latest_signal

            # Technical indicators
            with st.expander("Technical Indicators"):
                try:
                    indicators = getattr(signal, 'indicators', {})

                    if indicators and 'rsi' in indicators and indicators['rsi']:
                        st.metric("RSI", f"{indicators['rsi'][-1]:.1f}")

                    if indicators and 'macd' in indicators and indicators['macd']:
                        st.metric("MACD", f"{indicators['macd'][-1]:.4f}")

                    # Risk metrics
                    risk_metrics = getattr(signal, 'risk_metrics', {})
                    st.metric("ATR", f"${risk_metrics.get('atr', 0):.2f}")
                    st.metric("Volatility", f"{risk_metrics.get('volatility', 0):.2f}%")
                except Exception as e:
                    st.warning(f"Technical indicators unavailable: {str(e)}")

        else:
            st.info("[INFO] No signal available. Click 'Get Latest Signal' to generate.")

        # Manual trading controls
        st.subheader("[MANUAL] Manual Controls")

        manual_symbol = st.selectbox("Symbol", ["BTCUSDT", "ETHUSDT", "BNBUSDT"])
        manual_side = st.selectbox("Side", ["BUY", "SELL"])
        manual_amount = st.number_input("Amount (USDT)", min_value=10.0, max_value=50.0, value=10.0)

        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"Execute {manual_side} Order", type="secondary"):
                if trading_system.check_trading_limits():
                    st.info(f"[MANUAL] Executing {manual_side} {manual_amount} USDT of {manual_symbol}")
                    # Here you would implement manual order execution
                else:
                    st.error("[LIMIT] Trading limits exceeded")

        with col2:
            if st.button("Clear Signal Data", type="secondary"):
                if 'latest_signal' in st.session_state:
                    del st.session_state.latest_signal
                st.success("[OK] Signal data cleared")

    st.divider()

    # Alert System
    st.subheader("[ALERT] Alert System")

    col1, col2, col3 = st.columns(3)

    with col1:
        # PnL Alerts
        st.write("**PnL Alerts**")
        profit_threshold = st.number_input("Profit Alert ($)", value=50.0)
        loss_threshold = st.number_input("Loss Alert ($)", value=-20.0)

    with col2:
        # Volume Alerts
        st.write("**Volume Alerts**")
        volume_threshold = st.number_input("Volume Alert ($)", value=80.0)

    with col3:
        # System Alerts
        st.write("**System Status**")

        # Check for alerts
        alerts = []

        # Check consecutive losses
        if trading_system.consecutive_losses >= 2:
            alerts.append(f"[WARNING] {trading_system.consecutive_losses} consecutive losses")

        # Check daily volume
        if trading_system.daily_volume > volume_threshold:
            alerts.append(f"[WARNING] Daily volume ${trading_system.daily_volume:.2f} exceeds threshold")

        # Check emergency stop
        if trading_system.emergency_stop:
            alerts.append("[EMERGENCY] Emergency stop is active")

        # Display alerts
        if alerts:
            for alert in alerts:
                st.warning(alert)
        else:
            st.success("[OK] All systems normal")

    # Auto-refresh and Trading Cycle
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("[REFRESH] Run Trading Cycle"):
            with st.spinner("Running trading cycle..."):
                try:
                    trading_system.run_trading_cycle(['BTCUSDT', 'ETHUSDT'])
                    st.success("[OK] Trading cycle completed")
                    st.rerun()
                except Exception as e:
                    st.error(f"[ERROR] Trading cycle failed: {str(e)}")
                    trading_system.emergency_stop_trading()

    with col2:
        auto_refresh_enabled = st.toggle("Auto Refresh (30s)", value=st.session_state.get('auto_refresh', False))
        st.session_state.auto_refresh = auto_refresh_enabled

    with col3:
        if st.button("[UPDATE] Update Positions"):
            with st.spinner("Updating positions..."):
                trading_system.update_positions()
                st.success("[OK] Positions updated")
                st.rerun()

    # Auto-refresh logic
    if auto_refresh_enabled:
        current_time = datetime.now()
        if (current_time - st.session_state.last_refresh).seconds >= 30:
            st.session_state.last_refresh = current_time
            if auto_trading and not trading_system.emergency_stop:
                try:
                    trading_system.update_positions()
                    st.rerun()
                except Exception as e:
                    st.error(f"[ERROR] Auto-refresh failed: {str(e)}")
                    st.session_state.auto_refresh = False

    # Real-time clock
    st.markdown(f"**Last Update:** {datetime.now().strftime('%H:%M:%S')}")

def create_system_status_tab():
    """System status tab"""
    st.header("[TOOL] System Status")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("[GLOBE] CoinGecko API Status")
        cg = st.session_state.cg_connector
        st.metric("Monthly Usage", f"{cg.request_count_month}/10,000")

    with col2:
        st.subheader("[ROCKET] Binance API Status")

        if st.button("[SEARCH] Test Binance Connection"):
            result = st.session_state.binance_connector.test_connection()

            if result.get('success'):
                st.success("[OK] Binance Testnet Connected!")
                st.write(f"Server Time: {result.get('server_time')}")
                st.write(f"Account Type: {result.get('account_type')}")
            else:
                st.error(f"[ERROR] {result.get('error')}")

# ==========================================
# MAIN APPLICATION
# ==========================================

if __name__ == "__main__":
    main_dashboard()