#!/usr/bin/env python3
"""
Hybrid AI Trading Dashboard
현물 + 선물 하이브리드 트레이딩 시스템 대시보드
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np
import time

# Add current directory to Python path
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_trading_signals import HybridAITradingSystem, CoinGeckoDataFetcher

# Configure Streamlit page
st.set_page_config(
    page_title="🚀 Hybrid AI Trading System",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5em;
        font-weight: bold;
        color: #2E86AB;
        text-align: center;
        margin-bottom: 30px;
    }

    .mode-selector {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin-bottom: 20px;
    }

    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 10px 0;
    }

    .signal-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }

    .spot-signal {
        background: linear-gradient(135deg, #56ab2f 0%, #a8e6cf 100%);
    }

    .futures-signal {
        background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
    }

    .hybrid-signal {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """세션 상태 초기화"""
    if 'trading_system' not in st.session_state:
        st.session_state.trading_system = None

    if 'current_mode' not in st.session_state:
        st.session_state.current_mode = "HYBRID"

    if 'data_fetcher' not in st.session_state:
        st.session_state.data_fetcher = CoinGeckoDataFetcher()

    if 'last_signal' not in st.session_state:
        st.session_state.last_signal = None

    if 'performance_data' not in st.session_state:
        st.session_state.performance_data = []

def create_mode_selector():
    """거래 모드 선택 인터페이스"""
    st.markdown('<div class="mode-selector">', unsafe_allow_html=True)
    st.markdown("### 🎯 거래 모드 선택")

    col1, col2, col3 = st.columns(3)

    with col1:
        spot_selected = st.button(
            "🏦 현물 전용\n안정적 장기투자",
            key="spot_mode",
            help="현물만 거래하여 안정적인 수익 추구"
        )

    with col2:
        futures_selected = st.button(
            "⚡ 선물 전용\n레버리지 거래",
            key="futures_mode",
            help="선물 레버리지로 높은 수익 추구"
        )

    with col3:
        hybrid_selected = st.button(
            "🚀 하이브리드\n균형잡힌 포트폴리오",
            key="hybrid_mode",
            help="현물 70% + 선물 30% 균형 전략"
        )

    st.markdown('</div>', unsafe_allow_html=True)

    # 모드 변경 처리
    if spot_selected:
        st.session_state.current_mode = "SPOT_ONLY"
        st.session_state.trading_system = None  # 시스템 재초기화
        st.rerun()
    elif futures_selected:
        st.session_state.current_mode = "FUTURES_ONLY"
        st.session_state.trading_system = None
        st.rerun()
    elif hybrid_selected:
        st.session_state.current_mode = "HYBRID"
        st.session_state.trading_system = None
        st.rerun()

    return st.session_state.current_mode

def initialize_trading_system(mode: str, capital: float):
    """트레이딩 시스템 초기화"""
    if st.session_state.trading_system is None:
        st.session_state.trading_system = HybridAITradingSystem(
            trading_mode=mode,
            initial_capital=capital
        )
    return st.session_state.trading_system

def show_mode_info(mode: str):
    """선택된 모드 정보 표시"""
    mode_info = {
        "SPOT_ONLY": {
            "title": "🏦 현물 전용 모드",
            "description": "안정적인 현물 거래로 장기적 수익 추구",
            "allocation": "현물 100%",
            "risk_level": "낮음",
            "expected_return": "월 2-5%"
        },
        "FUTURES_ONLY": {
            "title": "⚡ 선물 전용 모드",
            "description": "레버리지를 활용한 고수익 선물 거래",
            "allocation": "선물 100%",
            "risk_level": "높음",
            "expected_return": "월 10-20%"
        },
        "HYBRID": {
            "title": "🚀 하이브리드 모드",
            "description": "현물의 안정성과 선물의 수익성을 결합",
            "allocation": "현물 70% + 선물 30%",
            "risk_level": "중간",
            "expected_return": "월 5-15%"
        }
    }

    info = mode_info[mode]

    st.markdown(f"""
    <div class="metric-card">
        <h3>{info['title']}</h3>
        <p><strong>전략:</strong> {info['description']}</p>
        <p><strong>자산 배분:</strong> {info['allocation']}</p>
        <p><strong>위험도:</strong> {info['risk_level']}</p>
        <p><strong>예상 수익:</strong> {info['expected_return']}</p>
    </div>
    """, unsafe_allow_html=True)

def generate_and_display_signal(trading_system, symbol: str, market_data: pd.DataFrame):
    """신호 생성 및 표시"""
    try:
        signal = trading_system.generate_hybrid_signal(symbol, market_data)
        st.session_state.last_signal = signal

        if signal['action'] == 'HOLD':
            st.markdown(f"""
            <div class="signal-card">
                <h4>📊 현재 신호: HOLD</h4>
                <p><strong>사유:</strong> {signal['reasoning']}</p>
                <p><strong>신뢰도:</strong> {signal['confidence']:.1%}</p>
            </div>
            """, unsafe_allow_html=True)
            return signal

        # 모드별 신호 표시
        if signal['trading_mode'] == 'HYBRID':
            display_hybrid_signal(signal)
        elif signal['trading_mode'] == 'SPOT_ONLY':
            display_spot_signal(signal)
        elif signal['trading_mode'] == 'FUTURES_ONLY':
            display_futures_signal(signal)

        return signal

    except Exception as e:
        st.error(f"신호 생성 중 오류 발생: {str(e)}")
        return None

def display_hybrid_signal(signal):
    """하이브리드 신호 표시"""
    col1, col2 = st.columns(2)

    with col1:
        spot_signal = signal['spot_signal']
        st.markdown(f"""
        <div class="signal-card spot-signal">
            <h4>🏦 현물 신호</h4>
            <p><strong>액션:</strong> {spot_signal['action']}</p>
            <p><strong>비중:</strong> {spot_signal['allocation']:.0%}</p>
            <p><strong>포지션 크기:</strong> {spot_signal['position_size_pct']:.1%}</p>
            <p><strong>레버리지:</strong> {spot_signal['leverage']}x</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        futures_signal = signal['futures_signal']
        st.markdown(f"""
        <div class="signal-card futures-signal">
            <h4>⚡ 선물 신호</h4>
            <p><strong>액션:</strong> {futures_signal['action']}</p>
            <p><strong>비중:</strong> {futures_signal['allocation']:.0%}</p>
            <p><strong>포지션 크기:</strong> {futures_signal['position_size_pct']:.1%}</p>
            <p><strong>레버리지:</strong> {futures_signal['leverage']}x</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="signal-card hybrid-signal">
        <h4>🚀 통합 신호 정보</h4>
        <p><strong>신뢰도:</strong> {signal['combined_confidence']:.1%}</p>
        <p><strong>신호 등급:</strong> {signal['signal_grade']}</p>
        <p><strong>분석 근거:</strong> {signal['reasoning']}</p>
    </div>
    """, unsafe_allow_html=True)

def display_spot_signal(signal):
    """현물 신호 표시"""
    st.markdown(f"""
    <div class="signal-card spot-signal">
        <h4>🏦 현물 거래 신호</h4>
        <p><strong>액션:</strong> {signal['action']}</p>
        <p><strong>신뢰도:</strong> {signal['confidence']:.1%}</p>
        <p><strong>신호 등급:</strong> {signal['signal_grade']}</p>
        <p><strong>포지션 크기:</strong> {signal['position_size_pct']:.1%}</p>
        <p><strong>분석 근거:</strong> {signal['reasoning']}</p>
    </div>
    """, unsafe_allow_html=True)

def display_futures_signal(signal):
    """선물 신호 표시"""
    st.markdown(f"""
    <div class="signal-card futures-signal">
        <h4>⚡ 선물 거래 신호</h4>
        <p><strong>액션:</strong> {signal['action']}</p>
        <p><strong>신뢰도:</strong> {signal['confidence']:.1%}</p>
        <p><strong>신호 등급:</strong> {signal['signal_grade']}</p>
        <p><strong>레버리지:</strong> {signal['leverage']}x</p>
        <p><strong>포지션 크기:</strong> {signal['position_size_pct']:.1%}</p>
        <p><strong>분석 근거:</strong> {signal['reasoning']}</p>
    </div>
    """, unsafe_allow_html=True)

def show_portfolio_status(trading_system):
    """포트폴리오 상태 표시"""
    if len(trading_system.performance_history) == 0:
        st.info("아직 거래 기록이 없습니다. 신호를 생성하고 거래를 실행해보세요.")
        return

    # 최신 포트폴리오 정보
    latest_portfolio = trading_system.performance_history[-1]['total_value']

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "총 포트폴리오 가치",
            f"${latest_portfolio['total_value']:,.0f}",
            f"{latest_portfolio['total_return_pct']:+.2f}%"
        )

    with col2:
        st.metric(
            "현금",
            f"${latest_portfolio['cash']:,.0f}",
            f"{latest_portfolio['cash'] / latest_portfolio['total_value'] * 100:.1f}%"
        )

    with col3:
        st.metric(
            "현물 포지션",
            f"${latest_portfolio['spot_value']:,.0f}",
            f"{latest_portfolio['spot_value'] / latest_portfolio['total_value'] * 100:.1f}%"
        )

    with col4:
        st.metric(
            "선물 P&L",
            f"${latest_portfolio['futures_pnl']:,.0f}",
            "미실현 손익"
        )

def show_performance_analytics(trading_system):
    """성과 분석 표시"""
    if len(trading_system.performance_history) == 0:
        st.info("성과 분석을 위한 데이터가 충분하지 않습니다.")
        return

    analytics = trading_system.get_performance_analytics()

    if 'error' in analytics:
        st.warning(analytics['error'])
        return

    # 전체 성과 요약
    overall = analytics['overall_performance']

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("총 수익률", f"{overall['total_return_pct']:.2f}%")
        st.metric("샤프 비율", f"{overall['sharpe_ratio']:.2f}")

    with col2:
        st.metric("승률", f"{overall['win_rate']:.1f}%")
        st.metric("최대 낙폭", f"{overall['max_drawdown']:.2f}%")

    with col3:
        st.metric("총 거래 수", f"{overall['total_trades']}")
        st.metric("현재 포트폴리오", f"${overall['current_portfolio_value']:,.0f}")

    # 자산 배분 차트
    asset_breakdown = analytics['asset_breakdown']

    fig_pie = go.Figure(data=[go.Pie(
        labels=['현금', '현물', '선물'],
        values=[asset_breakdown['cash_pct'], asset_breakdown['spot_pct'], asset_breakdown['futures_pct']],
        hole=0.4
    )])

    fig_pie.update_layout(title="포트폴리오 자산 배분")
    st.plotly_chart(fig_pie, use_container_width=True)

def execute_trade_interface(trading_system, signal, current_price):
    """거래 실행 인터페이스"""
    if signal is None or signal['action'] == 'HOLD':
        st.info("현재 실행할 신호가 없습니다.")
        return

    st.markdown("### 🎯 거래 실행")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.write(f"**신호:** {signal['action']}")
        st.write(f"**신뢰도:** {signal.get('confidence', signal.get('combined_confidence', 0)):.1%}")
        st.write(f"**현재 가격:** ${current_price:,.2f}")

    with col2:
        if st.button("🚀 거래 실행", type="primary"):
            with st.spinner("거래 실행 중..."):
                result = trading_system.execute_hybrid_trade(signal, current_price)

                if result['success']:
                    st.success("✅ 거래가 성공적으로 실행되었습니다!")

                    # 실행 결과 표시
                    for trade in result['trades_executed']:
                        if trade['success']:
                            st.write(f"✅ {trade['trade_type']} {trade['action']}: ${trade.get('value', trade.get('position_value', 0)):,.2f}")
                        else:
                            st.write(f"❌ {trade['trade_type']} 실행 실패: {trade.get('error', 'Unknown error')}")
                else:
                    st.error(f"❌ 거래 실행 실패: {result.get('error', 'Unknown error')}")

def main():
    """메인 대시보드"""
    initialize_session_state()

    # 헤더
    st.markdown('<h1 class="main-header">🚀 Hybrid AI Trading System</h1>', unsafe_allow_html=True)

    # 사이드바 설정
    with st.sidebar:
        st.header("⚙️ 시스템 설정")

        # 초기 자본 설정
        initial_capital = st.number_input(
            "초기 자본 ($)",
            min_value=1000,
            max_value=1000000,
            value=10000,
            step=1000
        )

        # 거래 심볼 선택
        symbol = st.selectbox(
            "거래 심볼",
            ["bitcoin", "ethereum", "binancecoin", "cardano", "solana"],
            format_func=lambda x: f"{x.upper()} ({x})"
        )

        # 자동 새로고침 설정
        auto_refresh = st.checkbox("자동 새로고침 (30초)", value=True)

        if auto_refresh:
            time.sleep(0.1)  # 작은 지연
            st.rerun()

    # 메인 컨텐츠
    # 1. 모드 선택
    current_mode = create_mode_selector()

    # 2. 선택된 모드 정보
    show_mode_info(current_mode)

    # 3. 트레이딩 시스템 초기화
    trading_system = initialize_trading_system(current_mode, initial_capital)

    # 4. 시장 데이터 가져오기
    try:
        with st.spinner("시장 데이터 로딩 중..."):
            market_data = st.session_state.data_fetcher.get_historical_data(symbol, days=100)
            current_price = market_data['close'].iloc[-1]

        # 5. 탭으로 구성된 메인 인터페이스
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 신호 분석",
            "💼 포트폴리오",
            "📈 성과 분석",
            "🎯 거래 실행"
        ])

        with tab1:
            st.header("📊 AI 신호 분석")

            # 현재 가격 정보
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("현재 가격", f"${current_price:,.2f}")
            with col2:
                price_change = market_data['close'].iloc[-1] - market_data['close'].iloc[-2]
                st.metric("24시간 변동", f"${price_change:,.2f}", f"{price_change/market_data['close'].iloc[-2]*100:+.2f}%")
            with col3:
                st.metric("거래량", f"{market_data['volume'].iloc[-1]:,.0f}")

            # 신호 생성 및 표시
            signal = generate_and_display_signal(trading_system, symbol, market_data)

        with tab2:
            st.header("💼 포트폴리오 현황")
            show_portfolio_status(trading_system)

            # 포지션 상세 정보
            if trading_system.spot_positions or trading_system.futures_positions:
                st.subheader("📋 현재 포지션")

                if trading_system.spot_positions:
                    st.write("**현물 포지션:**")
                    for symbol_pos, position in trading_system.spot_positions.items():
                        if position['quantity'] > 0:
                            st.write(f"- {symbol_pos}: {position['quantity']:.6f} @ ${position['avg_price']:.2f}")

                if trading_system.futures_positions:
                    st.write("**선물 포지션:**")
                    for symbol_pos, position in trading_system.futures_positions.items():
                        pnl = trading_system._calculate_futures_pnl(position, current_price)
                        st.write(f"- {symbol_pos}: {position['side']} {position['quantity']:.6f} @ ${position['entry_price']:.2f} (P&L: ${pnl:.2f})")

        with tab3:
            st.header("📈 성과 분석")
            show_performance_analytics(trading_system)

        with tab4:
            st.header("🎯 거래 실행")
            signal = st.session_state.last_signal
            execute_trade_interface(trading_system, signal, current_price)

    except Exception as e:
        st.error(f"데이터 로딩 중 오류 발생: {str(e)}")
        st.info("네트워크 연결을 확인하고 페이지를 새로고침해주세요.")

if __name__ == "__main__":
    main()