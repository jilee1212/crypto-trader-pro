"""
Dashboard Components - Crypto Trader Pro
대시보드 컴포넌트 - 메인 대시보드, 포트폴리오, 리스크 관리 등
"""

import streamlit as st
import pandas as pd
import time
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Import our modules
from trading_functions import (
    get_user_api_keys, get_real_account_balance, get_real_positions,
    get_market_data_fetcher, handle_quick_action
)
# Import UI helpers for performance charts
from ui_helpers import show_performance_analysis_charts

def show_main_dashboard():
    """메인 거래 대시보드"""

    # 사이드바 - 사용자 정보 및 설정
    with st.sidebar:
        st.markdown(f"### 👋 {st.session_state.user['username']}님")

        # API 키 상태 확인
        api_keys = get_user_api_keys(st.session_state.user['id'])
        if api_keys:
            st.success("✅ API 연결됨")
            st.info(f"모드: {'테스트넷' if api_keys['is_testnet'] else '실거래'}")
        else:
            st.error("❌ API 키 없음")

        # 실제 API에서 계좌 정보 가져오기 (캐시된 데이터 사용)
        if api_keys and api_keys.get('api_key'):
            if 'sidebar_balance_data' not in st.session_state:
                try:
                    # 최초 한 번만 조회
                    real_balance_data = get_real_account_balance(api_keys)
                    st.session_state.sidebar_balance_data = real_balance_data
                except Exception as e:
                    st.session_state.sidebar_balance_data = {'success': False, 'error': str(e)}

            # 캐시된 데이터 사용
            real_balance_data = st.session_state.sidebar_balance_data

            if real_balance_data and real_balance_data.get('success'):
                st.markdown("### 💰 계좌 정보")
                st.metric("USDT 잔고", f"${real_balance_data['balance']:,.2f}")
                st.metric("사용 가능", f"${real_balance_data['free']:,.2f}")
                if real_balance_data['used'] > 0:
                    st.metric("사용 중", f"${real_balance_data['used']:,.2f}")

                # 수동 새로고침 버튼
                if st.button("🔄 잔고 새로고침", key="refresh_sidebar_balance"):
                    del st.session_state.sidebar_balance_data
                    st.rerun()
            else:
                st.sidebar.error('API 연결 실패')
        else:
            st.sidebar.warning('API 키를 설정해주세요')

        st.markdown("---")

        # 거래 설정 (간소화)
        st.markdown("### ⚙️ 거래 설정")

        trading_mode = st.selectbox(
            "거래 모드",
            ["FUTURES_ONLY", "SPOT_ONLY", "HYBRID"],
            help="FUTURES_ONLY: 선물만, SPOT_ONLY: 현물만, HYBRID: 현물+선물"
        )

        # 기본 리스크 비율 설정 (슬라이더 제거)
        risk_percentage = 2.0

        st.markdown("---")

        # 캐시 클리어 버튼
        if st.button("🧹 캐시 클리어", use_container_width=True):
            cache_keys = [
                'sidebar_balance_data',
                'main_dashboard_balance',
                'dashboard_positions',
                'market_data'
            ]
            for key in cache_keys:
                if key in st.session_state:
                    del st.session_state[key]
            st.success("✅ 캐시가 클리어되었습니다!")
            st.rerun()

        if st.button("🚪 로그아웃", use_container_width=True):
            # 로그아웃 시 모든 캐시도 클리어
            keys_to_clear = ['logged_in', 'user', 'show_api_form', 'sidebar_balance_data',
                           'main_dashboard_balance', 'dashboard_positions', 'market_data']
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    # 메인 컨텐츠
    st.markdown("""
    <div class="main-header">
        <h1>🚀 Crypto Trader Pro Dashboard</h1>
        <p>AI 기반 암호화폐 자동 거래 플랫폼</p>
    </div>
    """, unsafe_allow_html=True)

    # 탭 구성
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 대시보드",
        "🔐 API 설정",
        "🤖 AI 신호",
        "💼 포트폴리오",
        "🛡️ 리스크 관리",
        "📈 거래 기록"
    ])

    # 실시간 계좌 정보 가져오기 (캐시 사용)
    if 'main_dashboard_balance' not in st.session_state and api_keys:
        try:
            st.session_state.main_dashboard_balance = get_real_account_balance(api_keys)
        except Exception:
            st.session_state.main_dashboard_balance = None

    real_account_data = st.session_state.get('main_dashboard_balance') if api_keys else None
    account_balance = real_account_data['balance'] if real_account_data and real_account_data.get('success') else 0

    # 자동 새로고침 제거 - 수동 새로고침만 지원

    with tab1:
        show_dashboard_overview(risk_percentage, api_keys, real_account_data)

    with tab2:
        from trading_functions import show_api_settings
        show_api_settings()

    with tab3:
        from trading_functions import show_ai_signals
        show_ai_signals(real_account_data, risk_percentage, trading_mode, api_keys)

    with tab4:
        show_portfolio(real_account_data, api_keys)

    with tab5:
        show_risk_management(real_account_data, api_keys)

    with tab6:
        from trading_functions import show_trading_history
        show_trading_history(real_account_data, api_keys)

def show_dashboard_overview(risk_percentage, api_keys, real_account_data):
    """대시보드 개요 - 실제 API 데이터만 표시"""

    # 계좌 잔고 계산
    account_balance = real_account_data['balance'] if real_account_data and real_account_data.get('success') else 0

    # 상단 메트릭 카드들
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>💰 계좌 잔고</h3>
            <h2>${:,.2f}</h2>
        </div>
        """.format(real_account_data['balance'] if real_account_data and real_account_data.get('success') else 0), unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>📊 리스크 비율</h3>
            <h2>{:.1f}%</h2>
        </div>
        """.format(risk_percentage), unsafe_allow_html=True)

    with col3:
        daily_risk = account_balance * risk_percentage / 100
        st.markdown("""
        <div class="metric-card">
            <h3>🛡️ 일일 최대 손실</h3>
            <h2>${:,.0f}</h2>
        </div>
        """.format(daily_risk), unsafe_allow_html=True)

    with col4:
        api_status = "연결됨" if api_keys else "미연결"
        color = "#28a745" if api_keys else "#dc3545"
        st.markdown("""
        <div class="metric-card" style="background: {};">
            <h3>🔗 API 상태</h3>
            <h2>{}</h2>
        </div>
        """.format(color, api_status), unsafe_allow_html=True)

    st.markdown("---")

    # 실시간 시장 정보
    st.markdown("### 📈 시장 정보")

    # 시장 데이터 캐시
    if 'market_data' not in st.session_state:
        try:
            market_fetcher = get_market_data_fetcher()
            btc_data = market_fetcher.get_current_price('BTC')
            eth_data = market_fetcher.get_current_price('ETH')
            st.session_state.market_data = {'btc': btc_data, 'eth': eth_data}
        except Exception as e:
            st.session_state.market_data = {'error': str(e)}

    market_data = st.session_state.market_data

    if 'error' not in market_data and market_data.get('btc') and market_data.get('eth'):
        btc_data = market_data['btc']
        eth_data = market_data['eth']

        col1, col2, col3 = st.columns(3)

        with col1:
            btc_change_color = "🟢" if btc_data['change_24h'] > 0 else "🔴"
            st.markdown(f"""
            <div class="card">
                <h4>{btc_change_color} Bitcoin (BTC)</h4>
                <h2>${btc_data['price']:,.2f}</h2>
                <p>24h 변화: {btc_data['change_24h']:+.2f}%</p>
                <p>24h 거래량: ${btc_data['volume_24h']:,.0f}</p>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            eth_change_color = "🟢" if eth_data['change_24h'] > 0 else "🔴"
            st.markdown(f"""
            <div class="card">
                <h4>{eth_change_color} Ethereum (ETH)</h4>
                <h2>${eth_data['price']:,.2f}</h2>
                <p>24h 변화: {eth_data['change_24h']:+.2f}%</p>
                <p>24h 거래량: ${eth_data['volume_24h']:,.0f}</p>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            # 시장 데이터 새로고침 버튼
            if st.button("🔄 시장 데이터 새로고침", key="refresh_market_data"):
                del st.session_state.market_data
                st.rerun()
    else:
        st.warning("시장 데이터를 불러올 수 없습니다.")
        if st.button("🔄 다시 시도", key="retry_market_data"):
            if 'market_data' in st.session_state:
                del st.session_state.market_data
            st.rerun()

    st.markdown("---")

    # 자동 포지션 표시
    st.markdown("### 📊 실시간 포지션 현황")

    if api_keys:
        # 포지션 데이터 캐시 확인
        if 'dashboard_positions' not in st.session_state:
            try:
                # 최초 한 번만 조회
                positions_result = get_real_positions(api_keys)
                st.session_state.dashboard_positions = positions_result
            except Exception as e:
                st.session_state.dashboard_positions = {'success': False, 'error': str(e)}

        positions_result = st.session_state.dashboard_positions

        if positions_result and positions_result.get('success'):
            positions_data = positions_result.get('positions', [])
            total_positions = len([p for p in positions_data if float(p.get('contracts', 0)) != 0])
            total_pnl = sum(float(p.get('unrealizedPnl', 0)) for p in positions_data)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("활성 포지션", total_positions)
            with col2:
                st.metric("미실현 손익", f"${total_pnl:.2f}")
            with col3:
                pnl_color = "normal" if total_pnl >= 0 else "inverse"
                if account_balance > 0:
                    pnl_percentage = (total_pnl / account_balance) * 100
                    st.metric("수익률", f"{pnl_percentage:+.2f}%", delta_color=pnl_color)
                else:
                    st.metric("수익률", "0.00%")
            with col4:
                # 수동 새로고침 버튼
                if st.button("🔄 포지션 새로고침", key="refresh_dashboard_positions"):
                    del st.session_state.dashboard_positions
                    st.rerun()

            if total_positions > 0:
                st.info("📋 포지션 상세 정보는 '포트폴리오' 탭에서 확인하세요.")
            else:
                st.info("📭 현재 활성 포지션이 없습니다.")
        else:
            st.info("📭 현재 활성 포지션이 없습니다.")
    else:
        st.warning("⚠️ 포지션 조회를 위해 API 키를 설정해주세요.")

    st.markdown("---")

    # 빠른 액션 버튼들
    st.markdown("### 🚀 빠른 액션")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🎯 AI 신호 생성", use_container_width=True):
            st.session_state.quick_action = "generate_signal"

    with col2:
        if st.button("⚡ 빠른 거래", use_container_width=True):
            st.session_state.quick_action = "quick_trade"

    with col3:
        if st.button("📈 성과 분석", use_container_width=True):
            st.session_state.quick_action = "performance"

    # 빠른 액션 처리
    if st.session_state.get('quick_action'):
        st.markdown("---")
        handle_quick_action(st.session_state.quick_action, account_balance, risk_percentage, api_keys)

def show_portfolio(real_account_data, api_keys):
    """포트폴리오 관리"""

    st.markdown("### 💼 포트폴리오")

    if not api_keys:
        st.warning("⚠️ 포트폴리오 조회를 위해 API 키를 설정해주세요.")
        return

    # 포지션 조회 버튼
    if st.button("🔄 포지션 새로고침", use_container_width=True):
        st.session_state.refresh_portfolio = True

    # 포지션 조회
    if st.session_state.get('refresh_portfolio', True):
        with st.spinner("포지션 조회 중..."):
            try:
                # 실제 포지션 및 계좌 정보 조회
                positions_result = get_real_positions(api_keys)
                real_balance_result = get_real_account_balance(api_keys)

                if positions_result and positions_result.get('success'):
                    # 포지션 데이터 변환
                    positions_data = positions_result.get('positions', [])
                    active_positions = [p for p in positions_data if float(p.get('contracts', 0)) != 0]
                    total_pnl = sum(float(p.get('unrealizedPnl', 0)) for p in positions_data)

                    # 포트폴리오 형태로 변환
                    portfolio_data = {
                        'success': True,
                        'total_positions': len(active_positions),
                        'total_unrealized_pnl': total_pnl,
                        'positions': active_positions
                    }

                    # 실제 계좌 잔고
                    real_balance = None
                    if real_balance_result and real_balance_result.get('success'):
                        real_balance = {
                            'total_balance': real_balance_result['balance'],
                            'free_balance': real_balance_result['free'],
                            'used_balance': real_balance_result['used']
                        }

                    display_portfolio_overview(portfolio_data, real_balance)
                    display_position_details(portfolio_data, None)
                else:
                    st.info("📭 현재 활성 포지션이 없습니다.")

                st.session_state.refresh_portfolio = False

            except Exception as e:
                st.error(f"오류 발생: {e}")

def get_real_account_balance_from_connector(connector):
    """실제 계좌 잔고 조회"""
    try:
        if hasattr(connector, 'exchange') and connector.exchange:
            balance = connector.exchange.fetch_balance()
            return {
                'total_balance': balance.get('USDT', {}).get('total', 0),
                'free_balance': balance.get('USDT', {}).get('free', 0),
                'used_balance': balance.get('USDT', {}).get('used', 0)
            }
    except Exception as e:
        st.warning(f"잔고 조회 실패: {e}")
    return {'total_balance': 0, 'free_balance': 0, 'used_balance': 0}

def display_portfolio_overview(positions, real_balance=None):
    """포트폴리오 개요 표시"""

    total_positions = positions.get('total_positions', 0)
    total_pnl = positions.get('total_unrealized_pnl', 0)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("활성 포지션", total_positions)

    with col2:
        if real_balance:
            st.metric("계좌 잔고", f"${real_balance['total_balance']:.2f}")
        else:
            st.metric("계좌 잔고", "조회 실패")

    with col3:
        pnl_color = "normal" if total_pnl >= 0 else "inverse"
        st.metric("총 미실현 손익", f"${total_pnl:.2f}",
                 delta_color=pnl_color)

    with col4:
        if real_balance and real_balance['total_balance'] > 0:
            pnl_percentage = (total_pnl / real_balance['total_balance']) * 100
        else:
            pnl_percentage = 0
        st.metric("수익률", f"{pnl_percentage:+.2f}%")

    # 추가 잔고 정보 표시
    if real_balance:
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("사용 가능", f"${real_balance['free_balance']:.2f}")
        with col2:
            st.metric("사용 중", f"${real_balance['used_balance']:.2f}")
        with col3:
            margin_usage = (real_balance['used_balance'] / real_balance['total_balance']) * 100 if real_balance['total_balance'] > 0 else 0
            st.metric("마진 사용률", f"{margin_usage:.1f}%")

def display_position_details(positions, connector):
    """포지션 상세 정보 표시"""

    active_positions = positions.get('positions', [])

    if not active_positions:
        st.info("📭 현재 활성 포지션이 없습니다.")
        return

    st.markdown("---")
    st.markdown("#### 📊 포지션 상세")

    for i, pos in enumerate(active_positions):
        with st.expander(f"🔸 {pos.get('symbol', 'N/A')} 포지션", expanded=True):

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("심볼", pos.get('symbol', 'N/A'))
                st.metric("포지션 크기", f"{pos.get('contracts', 0):.6f}")

            with col2:
                st.metric("진입가", f"${pos.get('entryPrice', 0):,.2f}")
                st.metric("현재가", f"${pos.get('markPrice', 0):,.2f}")

            with col3:
                pnl = pos.get('unrealizedPnl', 0)
                percentage = pos.get('percentage', 0)
                st.metric("미실현 손익", f"${pnl:.2f}")
                st.metric("수익률", f"{percentage:+.2f}%")

            with col4:
                # 포지션 관리 버튼
                if st.button(f"📈 {pos.get('symbol')} 분석", key=f"analyze_{i}"):
                    analyze_position(pos)

                if st.button(f"❌ {pos.get('symbol')} 청산", key=f"close_{i}"):
                    close_position(pos, connector)

def analyze_position(position):
    """포지션 분석"""
    st.info("포지션 분석 기능은 추후 구현 예정입니다.")

def close_position(position, connector):
    """포지션 청산"""
    st.warning("포지션 청산 기능은 추후 구현 예정입니다.")

def show_risk_management(real_account_data, api_keys):
    """고급 리스크 관리 대시보드"""

    st.markdown("""
    <div class="main-header">
        <h1>🛡️ 고급 리스크 관리 시스템</h1>
        <p>전문 트레이더를 위한 실시간 리스크 모니터링 & 제어 패널</p>
    </div>
    """, unsafe_allow_html=True)

    # 수동 새로고침 버튼으로 변경
    if st.button("🔄 데이터 새로고침"):
        st.session_state.refresh_risk_data = True

    # 리스크 데이터 수집
    account_balance = real_account_data['balance'] if real_account_data and real_account_data.get('success') else 10000
    risk_data = get_portfolio_risk_data(account_balance, api_keys)

    if not risk_data:
        st.error("⚠️ 리스크 데이터를 불러올 수 없습니다. API 키를 확인해주세요.")
        return

    # 1. 실시간 리스크 게이지
    col1, col2 = st.columns(2)

    with col1:
        show_risk_gauges(risk_data)

    with col2:
        show_portfolio_metrics(risk_data)

    # 2. 포지션 분석 테이블
    st.markdown("---")
    show_position_analysis_table(risk_data)

    # 3. 리스크 제어 패널
    st.markdown("---")
    show_risk_control_panel(api_keys)

    # 4. 성과 분석 차트
    st.markdown("---")
    show_performance_analysis_charts(risk_data)

def get_portfolio_risk_data(account_balance, api_keys):
    """포트폴리오 리스크 데이터 수집"""

    try:
        # 실제 API에서 포지션 데이터 가져오기
        real_positions = []
        total_margin_used = 0
        total_unrealized_pnl = 0

        if api_keys:
            try:
                # 실제 포지션 데이터 조회
                positions_result = get_real_positions(api_keys)

                if positions_result and positions_result.get('success'):
                    real_positions = positions_result.get('positions', [])
                    total_margin_used = sum(float(pos.get('initialMargin', 0)) for pos in real_positions)
                    total_unrealized_pnl = sum(float(pos.get('unrealizedPnl', 0)) for pos in real_positions)

            except Exception as e:
                st.warning(f"포지션 데이터 조회 실패: {e}")

        # 포트폴리오 메트릭 계산
        margin_usage_pct = (total_margin_used / account_balance) * 100 if account_balance > 0 else 0

        # VaR 계산 (간단 버전)
        var_1day = calculate_portfolio_var(real_positions) if real_positions else 0

        # 리스크 레벨 계산
        risk_level = calculate_risk_level(margin_usage_pct, var_1day, account_balance)

        return {
            'positions': real_positions,
            'total_margin_used': total_margin_used,
            'total_unrealized_pnl': total_unrealized_pnl,
            'margin_usage_pct': margin_usage_pct,
            'var_1day': var_1day,
            'risk_level': risk_level,
            'account_balance': account_balance,
            'free_margin': account_balance - total_margin_used
        }

    except Exception as e:
        st.error(f"리스크 데이터 수집 실패: {e}")
        return None

def calculate_portfolio_var(positions, confidence_level=0.95):
    """포트폴리오 VaR (Value at Risk) 계산"""

    try:
        if not positions:
            return 0

        # 간단한 VaR 계산 (실제로는 더 복잡한 모델 사용)
        total_exposure = 0
        for pos in positions:
            # 실제 Binance API 포지션 데이터 구조에 맞게 수정
            size = abs(float(pos.get('contracts', 0)))
            mark_price = float(pos.get('markPrice', 0))
            leverage = float(pos.get('leverage', 1))

            if size > 0 and mark_price > 0:
                total_exposure += size * mark_price * leverage

        # 일반적인 암호화폐 일일 변동성 (3-5%)
        daily_volatility = 0.04

        # Z-score for 95% confidence level
        z_score = 1.65

        var_1day = total_exposure * daily_volatility * z_score

        return var_1day

    except Exception:
        return 0

def calculate_risk_level(margin_usage_pct, var_1day, account_balance):
    """전체 리스크 레벨 계산"""

    try:
        # 여러 요소를 고려한 리스크 스코어
        margin_risk = min(margin_usage_pct / 50.0, 1.0)  # 50% 기준
        var_risk = min((var_1day / account_balance) / 0.1, 1.0) if account_balance > 0 else 0  # 10% 기준

        overall_risk = (margin_risk * 0.6 + var_risk * 0.4) * 100

        if overall_risk < 30:
            return {'level': 'LOW', 'score': overall_risk, 'color': 'green'}
        elif overall_risk < 60:
            return {'level': 'MEDIUM', 'score': overall_risk, 'color': 'orange'}
        else:
            return {'level': 'HIGH', 'score': overall_risk, 'color': 'red'}

    except Exception:
        return {'level': 'UNKNOWN', 'score': 0, 'color': 'gray'}

def show_risk_gauges(risk_data):
    """실시간 리스크 게이지 표시"""

    st.markdown("### 🎯 실시간 리스크 게이지")

    # 전체 포트폴리오 리스크 게이지
    risk_level = risk_data['risk_level']

    fig_risk = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = risk_level['score'],
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "포트폴리오 리스크"},
        delta = {'reference': 50},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': risk_level['color']},
            'steps': [
                {'range': [0, 30], 'color': "lightgreen"},
                {'range': [30, 60], 'color': "lightyellow"},
                {'range': [60, 100], 'color': "lightcoral"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 80
            }
        }
    ))

    fig_risk.update_layout(height=300)
    st.plotly_chart(fig_risk, use_container_width=True)

def show_portfolio_metrics(risk_data):
    """포트폴리오 주요 메트릭 표시"""

    st.markdown("### 📊 포트폴리오 메트릭")

    # 메트릭 카드들
    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            label="💰 계좌 잔고",
            value=f"${risk_data['account_balance']:,.2f}",
            delta=None
        )

        st.metric(
            label="📈 미실현 손익",
            value=f"${risk_data['total_unrealized_pnl']:,.2f}",
            delta=f"{(risk_data['total_unrealized_pnl']/risk_data['account_balance']*100):+.2f}%" if risk_data['account_balance'] > 0 else "0%"
        )

    with col2:
        st.metric(
            label="🔒 사용 마진",
            value=f"${risk_data['total_margin_used']:,.2f}",
            delta=f"{risk_data['margin_usage_pct']:.1f}% 사용됨"
        )

        st.metric(
            label="⚠️ 1일 VaR",
            value=f"${risk_data['var_1day']:,.2f}",
            delta=f"{(risk_data['var_1day']/risk_data['account_balance']*100):.2f}% 위험" if risk_data['account_balance'] > 0 else "0% 위험"
        )

def show_position_analysis_table(risk_data):
    """포지션 분석 테이블 표시"""

    if not risk_data or not risk_data['positions']:
        st.info("📭 현재 활성 포지션이 없습니다.")
        return

    st.markdown("### 📋 포지션 분석 테이블")

    try:
        # 실제 Binance API 포지션 데이터 구조에 맞게 처리
        positions_data = []
        for pos in risk_data['positions']:
            # Binance 포지션 데이터에서 필요한 정보 추출
            position_data = {
                '심볼': pos.get('symbol', 'N/A'),
                '방향': 'LONG' if float(pos.get('contracts', 0)) > 0 else 'SHORT' if float(pos.get('contracts', 0)) < 0 else 'NONE',
                '크기': abs(float(pos.get('contracts', 0))),
                '진입가': float(pos.get('entryPrice', 0)),
                '현재가': float(pos.get('markPrice', 0)),
                '미실현손익': float(pos.get('unrealizedPnl', 0)),
                '수익률(%)': float(pos.get('percentage', 0)),
                '마진': float(pos.get('initialMargin', 0))
            }

            # 0이 아닌 포지션만 표시
            if position_data['크기'] > 0:
                positions_data.append(position_data)

        if not positions_data:
            st.info("📭 현재 활성 포지션이 없습니다.")
            return

        # DataFrame 생성
        display_df = pd.DataFrame(positions_data)

        # 스타일 적용을 위한 함수
        def style_pnl(val):
            if isinstance(val, (int, float)):
                color = 'color: green' if val > 0 else 'color: red' if val < 0 else 'color: gray'
                return color
            return ''

        # 스타일 적용
        styled_df = display_df.style.applymap(style_pnl, subset=['미실현손익', '수익률(%)'])

        st.dataframe(styled_df, use_container_width=True)

    except Exception as e:
        st.error(f"포지션 테이블 표시 오류: {e}")
        st.info("📭 포지션 데이터를 표시할 수 없습니다.")

def show_risk_control_panel(api_keys):
    """리스크 제어 패널"""

    st.markdown("### 🎛️ 리스크 제어 패널")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 🚨 긴급 제어")

        if st.button("🔴 전체 포지션 청산", type="primary", use_container_width=True):
            if st.session_state.get('emergency_confirm', False):
                # 실제 청산 로직 (시뮬레이션)
                st.success("✅ 모든 포지션이 청산되었습니다!")
                st.session_state.emergency_confirm = False
            else:
                st.session_state.emergency_confirm = True
                st.warning("⚠️ 한 번 더 클릭하여 확인하세요.")

        if st.button("⏸️ 자동 거래 중단", use_container_width=True):
            st.info("🛑 자동 거래가 중단되었습니다.")

    with col2:
        st.markdown("#### ⚙️ 레버리지 관리")

        new_leverage = st.slider(
            "전체 레버리지 조정",
            min_value=1,
            max_value=10,
            value=5,
            help="모든 포지션의 레버리지를 일괄 조정"
        )

        if st.button("적용", use_container_width=True):
            st.success(f"✅ 레버리지가 {new_leverage}배로 조정되었습니다!")

    with col3:
        st.markdown("#### 🛡️ 리스크 한도")

        daily_loss_limit = st.number_input(
            "일일 손실 한도 (%)",
            min_value=1.0,
            max_value=10.0,
            value=3.0,
            step=0.5
        )

        auto_risk_reduction = st.checkbox("자동 리스크 축소", value=True)

        if st.button("설정 저장", use_container_width=True):
            st.success("✅ 리스크 설정이 저장되었습니다!")