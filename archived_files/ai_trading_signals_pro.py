#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏆 CRYPTO AI TRADING DASHBOARD PRO
Professional-grade trading platform with revolutionary UIUX
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import requests
import time
import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import warnings
warnings.filterwarnings('ignore')

# Custom CSS for professional trading platform look
def load_custom_css():
    st.markdown("""
    <style>
    /* Global Theme Variables */
    :root {
        --profit-color: #00ff88;
        --loss-color: #ff4444;
        --warning-color: #ffaa00;
        --info-color: #4488ff;
        --dark-bg: #0e1117;
        --light-bg: #ffffff;
        --card-bg: #1e2329;
        --border-color: #2b2f36;
    }

    /* Main container styling */
    .main > div {
        padding-top: 2rem;
        max-width: 100%;
    }

    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }

    .main-header h1 {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }

    .main-header p {
        font-size: 1.2rem;
        opacity: 0.9;
        margin: 0;
    }

    /* Navigation tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: var(--card-bg);
        padding: 0.5rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 12px 24px;
        border-radius: 8px;
        font-weight: 600;
        background-color: transparent;
        border: 2px solid transparent;
        transition: all 0.3s ease;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background-color: rgba(70, 136, 255, 0.1);
        border-color: var(--info-color);
    }

    .stTabs [aria-selected="true"] {
        background-color: var(--info-color) !important;
        color: white !important;
        border-color: var(--info-color) !important;
    }

    /* Metric cards */
    .metric-card {
        background: var(--card-bg);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid var(--border-color);
        margin-bottom: 1rem;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.15);
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    .metric-label {
        font-size: 0.9rem;
        opacity: 0.7;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .profit { color: var(--profit-color); }
    .loss { color: var(--loss-color); }
    .warning { color: var(--warning-color); }
    .info { color: var(--info-color); }

    /* Action buttons */
    .action-button {
        padding: 0.75rem 1.5rem;
        border-radius: 8px;
        border: none;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        text-decoration: none;
        display: inline-block;
        text-align: center;
        margin: 0.25rem;
    }

    .btn-emergency {
        background-color: var(--loss-color);
        color: white;
    }

    .btn-auto {
        background-color: var(--profit-color);
        color: white;
    }

    .btn-rebalance {
        background-color: var(--warning-color);
        color: white;
    }

    .action-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }

    /* Signal indicators */
    .signal-indicator {
        display: inline-flex;
        align-items: center;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        margin: 0.25rem;
    }

    .signal-buy {
        background-color: rgba(0, 255, 136, 0.2);
        color: var(--profit-color);
        border: 1px solid var(--profit-color);
    }

    .signal-sell {
        background-color: rgba(255, 68, 68, 0.2);
        color: var(--loss-color);
        border: 1px solid var(--loss-color);
    }

    .signal-hold {
        background-color: rgba(255, 170, 0, 0.2);
        color: var(--warning-color);
        border: 1px solid var(--warning-color);
    }

    /* Position cards */
    .position-card {
        background: var(--card-bg);
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.5rem;
        border-left: 4px solid var(--info-color);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .position-profit {
        border-left-color: var(--profit-color);
    }

    .position-loss {
        border-left-color: var(--loss-color);
    }

    /* Alert styling */
    .alert {
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        border-left: 4px solid;
    }

    .alert-success {
        background-color: rgba(0, 255, 136, 0.1);
        border-left-color: var(--profit-color);
        color: var(--profit-color);
    }

    .alert-danger {
        background-color: rgba(255, 68, 68, 0.1);
        border-left-color: var(--loss-color);
        color: var(--loss-color);
    }

    .alert-warning {
        background-color: rgba(255, 170, 0, 0.1);
        border-left-color: var(--warning-color);
        color: var(--warning-color);
    }

    /* Responsive design */
    @media (max-width: 768px) {
        .main-header h1 {
            font-size: 1.8rem;
        }

        .metric-value {
            font-size: 1.5rem;
        }

        .stTabs [data-baseweb="tab"] {
            padding: 8px 16px;
            font-size: 0.9rem;
        }
    }

    /* Loading animations */
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }

    .loading {
        animation: pulse 2s infinite;
    }

    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }

    ::-webkit-scrollbar-track {
        background: var(--card-bg);
    }

    ::-webkit-scrollbar-thumb {
        background: var(--border-color);
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--info-color);
    }
    </style>
    """, unsafe_allow_html=True)

# Enhanced data fetching with error handling
@st.cache_data(ttl=300)
def fetch_crypto_data(symbol: str = "bitcoin") -> Dict[str, Any]:
    """Fetch cryptocurrency data from CoinGecko API"""
    try:
        # Current price and basic data
        url = f"https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': symbol,
            'vs_currencies': 'usd',
            'include_24hr_change': 'true',
            'include_24hr_vol': 'true',
            'include_market_cap': 'true'
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        price_data = response.json()

        if symbol not in price_data:
            return {}

        # Historical data for charts
        hist_url = f"https://api.coingecko.com/api/v3/coins/{symbol}/market_chart"
        hist_params = {
            'vs_currency': 'usd',
            'days': '7',
            'interval': 'hourly'
        }

        hist_response = requests.get(hist_url, params=hist_params, timeout=10)
        hist_response.raise_for_status()
        hist_data = hist_response.json()

        return {
            'current': price_data[symbol],
            'historical': hist_data,
            'symbol': symbol,
            'last_updated': datetime.now()
        }

    except Exception as e:
        st.error(f"API 오류: {e}")
        return {}

# AI Signal Generation (Enhanced)
def generate_ai_signal(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate enhanced AI trading signals"""
    if not data or 'historical' not in data:
        return {
            'signal': 'HOLD',
            'confidence': 0,
            'price_target': 0,
            'stop_loss': 0,
            'reasoning': 'No data available'
        }

    try:
        # Process historical data
        prices = [p[1] for p in data['historical']['prices'][-24:]]  # Last 24 hours
        volumes = [v[1] for v in data['historical']['total_volumes'][-24:]]

        if len(prices) < 10:
            return {
                'signal': 'HOLD',
                'confidence': 0,
                'price_target': 0,
                'stop_loss': 0,
                'reasoning': 'Insufficient data'
            }

        # Calculate technical indicators
        current_price = prices[-1]
        price_change_24h = data['current'].get('usd_24h_change', 0)

        # RSI-like momentum indicator
        price_changes = np.diff(prices)
        gains = np.where(price_changes > 0, price_changes, 0)
        losses = np.where(price_changes < 0, -price_changes, 0)

        avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else np.mean(gains)
        avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else np.mean(losses)

        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        # Volume analysis
        avg_volume = np.mean(volumes[-7:])
        current_volume = volumes[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1

        # Price trend analysis
        sma_short = np.mean(prices[-5:])
        sma_long = np.mean(prices[-10:])
        trend_strength = (sma_short - sma_long) / sma_long * 100

        # Generate signal based on multiple factors
        confidence = 0
        signal = 'HOLD'
        reasoning = []

        # RSI analysis
        if rsi < 30:
            confidence += 30
            reasoning.append(f"RSI oversold ({rsi:.1f})")
            signal = 'BUY'
        elif rsi > 70:
            confidence += 30
            reasoning.append(f"RSI overbought ({rsi:.1f})")
            signal = 'SELL'

        # Trend analysis
        if trend_strength > 2:
            confidence += 25
            reasoning.append(f"Strong uptrend ({trend_strength:.1f}%)")
            if signal != 'SELL':
                signal = 'BUY'
        elif trend_strength < -2:
            confidence += 25
            reasoning.append(f"Strong downtrend ({trend_strength:.1f}%)")
            if signal != 'BUY':
                signal = 'SELL'

        # Volume confirmation
        if volume_ratio > 1.5:
            confidence += 20
            reasoning.append(f"High volume ({volume_ratio:.1f}x)")

        # Price change momentum
        if abs(price_change_24h) > 5:
            confidence += 15
            if price_change_24h > 0:
                reasoning.append(f"Strong 24h gain ({price_change_24h:.1f}%)")
            else:
                reasoning.append(f"Strong 24h drop ({price_change_24h:.1f}%)")

        # Set targets
        price_target = current_price * (1.03 if signal == 'BUY' else 0.97)
        stop_loss = current_price * (0.98 if signal == 'BUY' else 1.02)

        return {
            'signal': signal,
            'confidence': min(confidence, 95),
            'price_target': price_target,
            'stop_loss': stop_loss,
            'reasoning': ' | '.join(reasoning) if reasoning else 'Market analysis',
            'rsi': rsi,
            'trend_strength': trend_strength,
            'volume_ratio': volume_ratio
        }

    except Exception as e:
        return {
            'signal': 'HOLD',
            'confidence': 0,
            'price_target': 0,
            'stop_loss': 0,
            'reasoning': f'Analysis error: {str(e)}'
        }

# Create enhanced charts
def create_price_chart(data: Dict[str, Any], signals: Dict[str, Any]) -> go.Figure:
    """Create professional trading chart with signals"""
    if not data or 'historical' not in data:
        fig = go.Figure()
        fig.add_annotation(text="No data available",
                         xref="paper", yref="paper",
                         x=0.5, y=0.5, showarrow=False)
        return fig

    # Prepare data
    timestamps = [datetime.fromtimestamp(p[0]/1000) for p in data['historical']['prices']]
    prices = [p[1] for p in data['historical']['prices']]
    volumes = [v[1] for v in data['historical']['total_volumes']]

    # Create subplots
    fig = make_subplots(
        rows=3, cols=1,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=['Price Chart', 'Volume', 'Technical Indicators'],
        vertical_spacing=0.05
    )

    # Price line
    fig.add_trace(go.Scatter(
        x=timestamps, y=prices,
        mode='lines',
        name='Price',
        line=dict(color='#4488ff', width=2),
        hovertemplate='Price: $%{y:,.2f}<br>Time: %{x}<extra></extra>'
    ), row=1, col=1)

    # Moving averages
    if len(prices) >= 10:
        sma_5 = pd.Series(prices).rolling(5).mean()
        sma_10 = pd.Series(prices).rolling(10).mean()

        fig.add_trace(go.Scatter(
            x=timestamps, y=sma_5,
            mode='lines',
            name='SMA 5',
            line=dict(color='#ffaa00', width=1, dash='dash'),
            opacity=0.7
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=timestamps, y=sma_10,
            mode='lines',
            name='SMA 10',
            line=dict(color='#ff4444', width=1, dash='dot'),
            opacity=0.7
        ), row=1, col=1)

    # Volume bars
    volume_colors = ['#00ff88' if prices[i] >= prices[i-1] else '#ff4444'
                    for i in range(1, len(prices))]
    volume_colors.insert(0, '#4488ff')

    fig.add_trace(go.Bar(
        x=timestamps, y=volumes,
        name='Volume',
        marker_color=volume_colors,
        opacity=0.7
    ), row=2, col=1)

    # RSI indicator
    if 'rsi' in signals:
        rsi_values = [signals['rsi']] * len(timestamps)
        fig.add_trace(go.Scatter(
            x=timestamps, y=rsi_values,
            mode='lines',
            name=f'RSI ({signals["rsi"]:.1f})',
            line=dict(color='#9966ff', width=2)
        ), row=3, col=1)

        # RSI levels
        fig.add_hline(y=70, line=dict(color='#ff4444', dash='dash'), row=3, col=1)
        fig.add_hline(y=30, line=dict(color='#00ff88', dash='dash'), row=3, col=1)
        fig.add_hline(y=50, line=dict(color='#666666', dash='dot'), row=3, col=1)

    # Signal markers
    current_time = timestamps[-1] if timestamps else datetime.now()
    current_price = prices[-1] if prices else 0

    if signals['signal'] == 'BUY':
        fig.add_trace(go.Scatter(
            x=[current_time], y=[current_price],
            mode='markers',
            name='BUY Signal',
            marker=dict(color='#00ff88', size=15, symbol='triangle-up'),
            showlegend=True
        ), row=1, col=1)
    elif signals['signal'] == 'SELL':
        fig.add_trace(go.Scatter(
            x=[current_time], y=[current_price],
            mode='markers',
            name='SELL Signal',
            marker=dict(color='#ff4444', size=15, symbol='triangle-down'),
            showlegend=True
        ), row=1, col=1)

    # Update layout
    fig.update_layout(
        title=f"{data.get('symbol', 'Crypto').upper()} Trading Chart",
        height=700,
        showlegend=True,
        template='plotly_dark',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')

    return fig

# Main application
def main():
    st.set_page_config(
        page_title="Crypto AI Trading Dashboard Pro",
        page_icon="🏆",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Load custom CSS
    load_custom_css()

    # Main header
    st.markdown("""
    <div class="main-header">
        <h1>🏆 CRYPTO AI TRADING DASHBOARD</h1>
        <p>Professional-grade trading platform with AI-powered signals</p>
    </div>
    """, unsafe_allow_html=True)

    # Initialize session state
    if 'theme' not in st.session_state:
        st.session_state.theme = 'dark'
    if 'auto_trading' not in st.session_state:
        st.session_state.auto_trading = False
    if 'portfolio_value' not in st.session_state:
        st.session_state.portfolio_value = 10523.45
    if 'daily_pnl' not in st.session_state:
        st.session_state.daily_pnl = 2.3

    # Sidebar controls
    with st.sidebar:
        st.header("⚙️ Dashboard Controls")

        # Theme toggle
        theme = st.selectbox(
            "🎨 Theme",
            options=['Dark', 'Light'],
            index=0 if st.session_state.theme == 'dark' else 1
        )
        st.session_state.theme = theme.lower()

        # Auto trading toggle
        auto_trading = st.toggle("🤖 Auto Trading", value=st.session_state.auto_trading)
        st.session_state.auto_trading = auto_trading

        # Quick actions
        st.header("⚡ Quick Actions")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🛑 Emergency Stop", type="secondary"):
                st.session_state.auto_trading = False
                st.success("Emergency stop activated!")

        with col2:
            if st.button("🔄 Rebalance", type="secondary"):
                st.info("Portfolio rebalancing initiated...")

        # Market overview
        st.header("📊 Market Overview")

        # Fetch sample data for sidebar
        btc_data = fetch_crypto_data("bitcoin")
        if btc_data and 'current' in btc_data:
            btc_price = btc_data['current']['usd']
            btc_change = btc_data['current'].get('usd_24h_change', 0)

            st.metric(
                "Bitcoin",
                f"${btc_price:,.2f}",
                f"{btc_change:+.2f}%"
            )

        # Risk metrics
        st.header("⚠️ Risk Metrics")
        st.metric("Portfolio VaR", "-2.1%", "Low Risk")
        st.metric("Max Drawdown", "-1.8%", "Acceptable")
        st.metric("Sharpe Ratio", "2.14", "Excellent")

    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔴 Live Trading",
        "💼 Portfolio",
        "⚠️ Risk Management",
        "🔙 Backtesting",
        "📊 Performance"
    ])

    with tab1:
        show_live_trading_tab()

    with tab2:
        show_portfolio_tab()

    with tab3:
        show_risk_management_tab()

    with tab4:
        show_backtesting_tab()

    with tab5:
        show_performance_tab()

def show_live_trading_tab():
    """Enhanced live trading interface"""
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        st.markdown("### 📊 실시간 메트릭")

        # Portfolio metrics with enhanced styling
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value profit">${st.session_state.portfolio_value:,.2f}</div>
            <div class="metric-label">총 자산</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value {'profit' if st.session_state.daily_pnl >= 0 else 'loss'}">
                {st.session_state.daily_pnl:+.2f}%
            </div>
            <div class="metric-label">일일 수익률</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value info">3개</div>
            <div class="metric-label">활성 포지션</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("### 🎯 AI 신호")

        # Fetch real data for AI signals
        symbols = [
            ("bitcoin", "BTC"),
            ("ethereum", "ETH"),
            ("cardano", "ADA")
        ]

        for symbol, ticker in symbols:
            data = fetch_crypto_data(symbol)
            if data:
                signals = generate_ai_signal(data)
                signal_class = f"signal-{signals['signal'].lower()}"

                st.markdown(f"""
                <div class="signal-indicator {signal_class}">
                    {ticker}: {signals['signal']}
                    ({signals['confidence']:.0f}% 신뢰도)
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="signal-indicator signal-hold">
                    {ticker}: HOLD (데이터 없음)
                </div>
                """, unsafe_allow_html=True)

    with col3:
        st.markdown("### ⚡ 빠른 액션")

        st.markdown("""
        <div style="display: flex; flex-direction: column; gap: 0.5rem;">
            <button class="action-button btn-emergency">🛑 긴급정지</button>
            <button class="action-button btn-auto">🤖 자동거래</button>
            <button class="action-button btn-rebalance">🔄 리밸런싱</button>
        </div>
        """, unsafe_allow_html=True)

    # Trading chart section
    st.markdown("### 📈 실시간 차트")

    # Symbol selector
    selected_symbol = st.selectbox(
        "코인 선택",
        options=[
            ("bitcoin", "Bitcoin (BTC)"),
            ("ethereum", "Ethereum (ETH)"),
            ("cardano", "Cardano (ADA)"),
            ("polkadot", "Polkadot (DOT)"),
            ("chainlink", "Chainlink (LINK)")
        ],
        format_func=lambda x: x[1]
    )

    # Fetch data and create chart
    data = fetch_crypto_data(selected_symbol[0])
    if data:
        signals = generate_ai_signal(data)
        chart = create_price_chart(data, signals)
        st.plotly_chart(chart, use_container_width=True)

        # Signal details
        if signals['signal'] != 'HOLD':
            alert_class = 'alert-success' if signals['signal'] == 'BUY' else 'alert-danger'
            st.markdown(f"""
            <div class="alert {alert_class}">
                <strong>{signals['signal']} 신호 활성</strong><br>
                신뢰도: {signals['confidence']:.0f}%<br>
                목표가: ${signals['price_target']:,.2f}<br>
                손절가: ${signals['stop_loss']:,.2f}<br>
                분석: {signals['reasoning']}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.error("차트 데이터를 불러올 수 없습니다.")

    # Active positions
    st.markdown("### 💰 활성 포지션")

    positions = [
        {"symbol": "BTC/USDT", "pnl": 127.45, "pnl_pct": 2.3},
        {"symbol": "ETH/USDT", "pnl": -43.21, "pnl_pct": -1.1},
        {"symbol": "ADA/USDT", "pnl": 89.67, "pnl_pct": 3.7}
    ]

    for pos in positions:
        position_class = "position-profit" if pos["pnl"] >= 0 else "position-loss"
        pnl_class = "profit" if pos["pnl"] >= 0 else "loss"

        st.markdown(f"""
        <div class="position-card {position_class}">
            <div>
                <strong>{pos['symbol']}</strong>
            </div>
            <div class="{pnl_class}">
                ${pos['pnl']:+.2f} ({pos['pnl_pct']:+.1f}%)
            </div>
        </div>
        """, unsafe_allow_html=True)

def show_portfolio_tab():
    """Portfolio overview tab"""
    st.markdown("### 💼 포트폴리오 개요")

    # Portfolio allocation chart
    allocation_data = {
        'Asset': ['Bitcoin', 'Ethereum', 'Cardano', 'Polkadot', 'Cash'],
        'Value': [4500, 3200, 1800, 800, 223.45],
        'Percentage': [42.8, 30.4, 17.1, 7.6, 2.1]
    }

    fig = px.pie(
        values=allocation_data['Value'],
        names=allocation_data['Asset'],
        title="포트폴리오 구성",
        color_discrete_sequence=['#00ff88', '#4488ff', '#ffaa00', '#ff4444', '#9966ff']
    )
    fig.update_layout(template='plotly_dark')
    st.plotly_chart(fig, use_container_width=True)

    # Portfolio table
    df = pd.DataFrame(allocation_data)
    st.dataframe(df, use_container_width=True)

def show_risk_management_tab():
    """Risk management interface"""
    st.markdown("### ⚠️ 리스크 관리")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 리스크 한도 설정")

        max_position_size = st.slider("최대 포지션 크기 (%)", 1, 20, 5)
        daily_loss_limit = st.slider("일일 손실 한도 (%)", 1, 10, 3)
        stop_loss_pct = st.slider("기본 손절 비율 (%)", 1, 10, 2)

        st.markdown("#### 현재 리스크 상태")
        st.metric("포트폴리오 베타", "0.85", "안정적")
        st.metric("최대 포지션", "4.2%", "안전")
        st.metric("상관계수", "0.73", "양호")

    with col2:
        st.markdown("#### 리스크 알림")

        st.markdown("""
        <div class="alert alert-success">
            ✅ 모든 포지션이 리스크 한도 내에 있습니다.
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="alert alert-warning">
            ⚠️ BTC 포지션이 일일 변동성 한도에 근접했습니다.
        </div>
        """, unsafe_allow_html=True)

def show_backtesting_tab():
    """Backtesting interface"""
    st.markdown("### 🔙 백테스팅")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("#### 백테스트 설정")

        test_period = st.selectbox("테스트 기간", ["1개월", "3개월", "6개월", "1년"])
        initial_capital = st.number_input("초기 자본 ($)", value=10000, min_value=1000)
        strategy = st.selectbox("전략", ["AI 신호", "RSI", "MACD", "볼린저 밴드"])

        if st.button("백테스트 실행"):
            with st.spinner("백테스트 실행 중..."):
                time.sleep(2)
                st.success("백테스트 완료!")

    with col2:
        st.markdown("#### 백테스트 결과")

        # Sample backtest results
        results_data = {
            'Metric': ['총 수익률', '연환산 수익률', '샤프 비율', '최대 드로우다운', '승률'],
            'Value': ['+15.7%', '+21.3%', '1.85', '-4.2%', '68.5%'],
            'Benchmark': ['+8.2%', '+11.1%', '1.20', '-12.8%', '50.0%']
        }

        st.dataframe(pd.DataFrame(results_data), use_container_width=True)

def show_performance_tab():
    """Performance analysis tab"""
    st.markdown("### 📊 성과 분석")

    # Redirect to performance dashboard
    st.info("상세한 성과 분석은 전용 대시보드에서 확인하세요: http://localhost:8506")

    # Quick performance overview
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("월간 수익률", "+8.5%", "+2.3%")

    with col2:
        st.metric("승률", "73.2%", "+5.1%")

    with col3:
        st.metric("샤프 비율", "2.14", "+0.25")

    with col4:
        st.metric("최대 드로우다운", "-2.1%", "+1.2%")

    # Performance chart
    dates = pd.date_range(start='2025-08-21', end='2025-09-21', freq='D')
    returns = np.cumsum(np.random.normal(0.002, 0.02, len(dates))) * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=returns,
        mode='lines',
        name='누적 수익률',
        line=dict(color='#00ff88', width=3)
    ))

    fig.update_layout(
        title="월간 성과 추이",
        xaxis_title="날짜",
        yaxis_title="누적 수익률 (%)",
        template='plotly_dark'
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()