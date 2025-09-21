"""
Trading Functions - Crypto Trader Pro
거래 관련 함수들 - AI 신호, API 설정, 거래 기록, 계좌 정보 등
"""

import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import time

# Import trading modules
try:
    from ai_trading_signals import (
        EnhancedAITradingSystem,
        BinanceFuturesConnector,
        execute_integrated_trading_system
    )
    from real_market_data import RealMarketDataFetcher, EnhancedBinanceConnector
except ImportError as e:
    st.error(f"모듈 import 실패: {e}")

# 전역 데이터 페처 초기화
@st.cache_resource
def get_market_data_fetcher():
    return RealMarketDataFetcher()

def get_user_api_keys(user_id):
    """사용자 API 키 조회"""
    try:
        conn = sqlite3.connect('crypto_trader_users.db')
        cursor = conn.cursor()

        cursor.execute('''
            SELECT api_key_encrypted, secret_key_encrypted, is_testnet
            FROM users WHERE id = ?
        ''', (user_id,))

        result = cursor.fetchone()
        conn.close()

        if result and result[0] and result[1]:
            return {
                'api_key': result[0],
                'secret_key': result[1],
                'is_testnet': bool(result[2])
            }
        return None

    except Exception as e:
        st.error(f"API 키 조회 중 오류: {e}")
        return None

def save_api_keys(user_id, api_key, secret_key, is_testnet):
    """API 키 저장 (실제 환경에서는 암호화 필요)"""
    try:
        conn = sqlite3.connect('crypto_trader_users.db')
        cursor = conn.cursor()

        # 간단한 인코딩 (실제로는 강력한 암호화 사용 권장)
        api_key_encoded = api_key
        secret_key_encoded = secret_key

        cursor.execute('''
            UPDATE users SET
            api_key_encrypted = ?,
            secret_key_encrypted = ?,
            is_testnet = ?
            WHERE id = ?
        ''', (api_key_encoded, secret_key_encoded, is_testnet, user_id))

        conn.commit()
        conn.close()
        return True, "API 키가 저장되었습니다."

    except Exception as e:
        return False, f"API 키 저장 중 오류: {e}"

def get_real_account_balance(api_keys):
    """실제 Binance 계좌 잔고 조회"""
    if not api_keys:
        return {'success': False, 'error': 'API 키가 없습니다'}

    try:
        # EnhancedBinanceConnector를 사용하여 실제 계좌 정보 조회
        connector = EnhancedBinanceConnector(
            api_keys['api_key'],
            api_keys['secret_key'],
            api_keys['is_testnet']
        )

        if connector.account_info:
            balance = connector.account_info.get('total_balance', 0)
            free_balance = connector.account_info.get('free_balance', 0)
            used_balance = connector.account_info.get('used_balance', 0)

            return {
                'success': True,
                'balance': float(balance),
                'free': float(free_balance),
                'used': float(used_balance),
                'last_updated': connector.account_info.get('last_updated')
            }
        else:
            return {'success': False, 'error': 'API 연결 실패'}

    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_real_positions(api_keys):
    """실제 Binance 포지션 조회"""
    if not api_keys:
        return {'success': False, 'error': 'API 키가 없습니다'}

    try:
        connector = EnhancedBinanceConnector(
            api_keys['api_key'],
            api_keys['secret_key'],
            api_keys['is_testnet']
        )

        positions_result = connector.get_real_positions()
        return positions_result

    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_real_trading_history(api_keys, limit=50):
    """실제 Binance 거래 기록 조회"""
    if not api_keys:
        return {'success': False, 'error': 'API 키가 없습니다'}

    try:
        connector = EnhancedBinanceConnector(
            api_keys['api_key'],
            api_keys['secret_key'],
            api_keys['is_testnet']
        )

        history_result = connector.get_order_history(limit=limit)
        return history_result

    except Exception as e:
        return {'success': False, 'error': str(e)}

# API 키 설정 페이지
def show_api_settings():
    """API 키 설정 페이지"""
    st.markdown("### 🔐 API 키 설정")

    # 현재 저장된 API 키 확인
    current_keys = get_user_api_keys(st.session_state.user['id'])

    if current_keys:
        st.success("✅ API 키가 설정되어 있습니다.")

        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**현재 모드**: {'테스트넷' if current_keys['is_testnet'] else '실거래'}")
        with col2:
            if st.button("🔄 API 키 재설정"):
                st.session_state.show_api_form = True
                st.rerun()
    else:
        st.warning("⚠️ API 키가 설정되지 않았습니다. 거래를 위해 API 키를 설정해주세요.")
        st.session_state.show_api_form = True

    # API 키 입력 폼
    if st.session_state.get('show_api_form', False) or not current_keys:
        st.markdown("---")

        with st.form("api_keys_form"):
            st.markdown("#### Binance API 키 설정")

            # 모드 선택
            is_testnet = st.checkbox(
                "테스트넷 사용 (권장)",
                value=True,
                help="실제 자금 없이 거래 테스트가 가능합니다."
            )

            if is_testnet:
                st.info("🧪 **테스트넷 모드**: 실제 자금 없이 안전하게 테스트할 수 있습니다.")
            else:
                st.warning("⚠️ **실거래 모드**: 실제 자금이 사용됩니다. 신중히 설정하세요.")

            api_key = st.text_input(
                "API Key",
                type="password",
                placeholder="Binance API Key를 입력하세요",
                help="Binance에서 발급받은 API Key를 입력하세요."
            )

            secret_key = st.text_input(
                "Secret Key",
                type="password",
                placeholder="Binance Secret Key를 입력하세요",
                help="Binance에서 발급받은 Secret Key를 입력하세요."
            )

            submitted = st.form_submit_button("💾 API 키 저장", use_container_width=True)

            if submitted:
                if api_key and secret_key:
                    # API 키 유효성 간단 테스트
                    try:
                        # BinanceFuturesConnector로 연결 테스트
                        test_connector = BinanceFuturesConnector(api_key, secret_key, is_testnet)
                        if test_connector.exchange:
                            success, message = save_api_keys(
                                st.session_state.user['id'],
                                api_key,
                                secret_key,
                                is_testnet
                            )
                            if success:
                                st.success(message)
                                st.session_state.show_api_form = False
                                st.rerun()
                            else:
                                st.error(message)
                        else:
                            st.error("API 키 연결 테스트에 실패했습니다. 키를 확인해주세요.")
                    except Exception as e:
                        st.error(f"API 키 테스트 중 오류: {e}")
                else:
                    st.error("API Key와 Secret Key를 모두 입력해주세요.")

    # API 키 안내
    if st.expander("📋 Binance API 키 발급 방법"):
        st.markdown("""
        **테스트넷 API 키 발급:**
        1. [Binance Testnet](https://testnet.binance.vision/) 접속
        2. GitHub 계정으로 로그인
        3. "Generate HMAC_SHA256 Key" 클릭
        4. API Key와 Secret Key 복사

        **실거래 API 키 발급:**
        1. [Binance](https://www.binance.com/) 로그인
        2. 계정 → API 관리
        3. API 키 생성
        4. **선물 거래 권한** 활성화
        5. IP 제한 설정 권장

        ⚠️ **보안 주의사항:**
        - Secret Key는 절대 타인과 공유하지 마세요
        - 출금 권한은 비활성화하세요
        - IP 제한을 설정하세요
        """)

def show_ai_signals(real_account_data, risk_percentage, trading_mode, api_keys):
    """AI 신호 생성 및 실행"""

    st.markdown("### 🤖 AI 거래 신호")

    col1, col2 = st.columns([2, 1])

    with col1:
        # 신호 생성 설정
        symbol = st.selectbox("거래 코인", ["BTC", "ETH"], help="거래할 암호화폐 선택")

        account_balance = real_account_data['balance'] if real_account_data and real_account_data.get('success') else 10000

        custom_balance = st.number_input(
            "사용할 잔고 ($)",
            min_value=100.0,
            max_value=account_balance,
            value=min(5000.0, account_balance),
            help="이번 거래에 사용할 자금 (실제 잔고: ${:,.2f})".format(account_balance)
        )

        custom_risk = st.slider(
            "이번 거래 리스크 (%)",
            min_value=0.5,
            max_value=5.0,
            value=risk_percentage,
            step=0.1
        )

    with col2:
        st.markdown("#### 📋 신호 설정")
        auto_execute = st.checkbox("자동 실행", help="신호 생성 시 자동으로 거래 실행")
        show_analysis = st.checkbox("상세 분석", value=True, help="신호 생성 과정 표시")

    st.markdown("---")

    # 신호 생성 버튼
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if st.button("🎯 AI 신호 생성", use_container_width=True, type="primary"):
            generate_and_display_signal(
                symbol, custom_balance, custom_risk, trading_mode,
                api_keys, auto_execute, show_analysis
            )

def generate_and_display_signal(symbol, balance, risk_pct, trading_mode, api_keys, auto_execute, show_analysis):
    """AI 신호 생성 및 표시"""

    with st.spinner("🤖 AI 신호 분석 중..."):
        try:
            # AI 시스템 초기화
            ai_system = EnhancedAITradingSystem(
                account_balance=balance,
                risk_percent=risk_pct/100
            )

            # 실시간 시장 데이터 조회
            market_fetcher = get_market_data_fetcher()
            market_data = market_fetcher.get_real_ohlcv_data(symbol)

            if show_analysis:
                with st.expander("📊 시장 데이터 분석", expanded=True):
                    current_price = market_data['close'].iloc[-1]
                    price_change = ((current_price - market_data['close'].iloc[-2]) / market_data['close'].iloc[-2]) * 100

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("현재 가격", f"${current_price:,.2f}", f"{price_change:+.2f}%")
                    with col2:
                        st.metric("24h 최고", f"${market_data['high'].iloc[-1]:,.2f}")
                    with col3:
                        st.metric("24h 최저", f"${market_data['low'].iloc[-1]:,.2f}")

            # 신호 생성
            signal = ai_system.generate_enhanced_signal(symbol, market_data)

            if signal['success']:
                # 신호 결과 표시
                display_signal_result(signal, symbol, auto_execute, api_keys)

                # 자동 실행
                if auto_execute and api_keys and signal.get('executable'):
                    execute_signal_automatically(signal, api_keys)

            else:
                st.error(f"❌ 신호 생성 실패: {signal.get('error')}")

        except Exception as e:
            st.error(f"❌ 오류 발생: {e}")

def display_signal_result(signal, symbol, auto_execute, api_keys):
    """신호 결과 표시"""

    # 신호 헤더
    signal_type = signal['signal']
    confidence = signal['confidence_score']

    if signal_type == "BUY":
        signal_color = "#28a745"
        signal_icon = "📈"
    elif signal_type == "SELL":
        signal_color = "#dc3545"
        signal_icon = "📉"
    else:
        signal_color = "#6c757d"
        signal_icon = "⏸️"

    st.markdown(f"""
    <div style="background: {signal_color}; color: white; padding: 1rem; border-radius: 10px; text-align: center; margin: 1rem 0;">
        <h2>{signal_icon} {signal_type} {symbol}</h2>
        <p>신뢰도: {confidence}%</p>
    </div>
    """, unsafe_allow_html=True)

    # 신호 상세 정보
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 💰 가격 정보")
        st.metric("진입가", f"${signal['entry_price']:,.2f}")
        if signal_type != "HOLD":
            st.metric("손절가", f"${signal['stop_loss_price']:,.2f}",
                     f"{signal['stop_loss_percent']:+.1%}")
            st.metric("익절가", f"${signal['take_profit_price']:,.2f}",
                     f"{signal['take_profit_percent']:+.1%}")

    with col2:
        st.markdown("#### 📊 리스크 관리")
        risk = signal['risk_management']
        if risk['success']:
            st.metric("포지션 크기", f"${risk['position_size']:,.2f}")
            st.metric("레버리지", f"{risk['leverage']}x")
            st.metric("마진 사용률", f"{risk['margin_usage_percent']:.1%}")
            st.metric("최대 손실", f"${risk['max_loss_amount']:,.2f}")

    with col3:
        st.markdown("#### ⚙️ 실행 설정")
        executable = signal.get('executable', False)

        if executable:
            st.success("✅ 실행 가능")

            if not auto_execute and api_keys:
                if st.button(f"🚀 {signal_type} 거래 실행", use_container_width=True):
                    execute_signal_manually(signal, api_keys)
            elif not api_keys:
                st.warning("API 키 설정 필요")
        else:
            st.warning("⚠️ 실행 불가")
            st.caption("HOLD 신호 또는 조건 미충족")

def execute_signal_manually(signal, api_keys):
    """수동 신호 실행"""
    with st.spinner("거래 실행 중..."):
        execute_signal_automatically(signal, api_keys)

def execute_signal_automatically(signal, api_keys):
    """자동 신호 실행"""
    try:
        # Binance 연결
        connector = BinanceFuturesConnector(
            api_keys['api_key'],
            api_keys['secret_key'],
            api_keys['is_testnet']
        )

        # 신호 실행
        result = connector.execute_ai_signal(signal, signal['risk_management'])

        if result['success']:
            st.success("✅ 거래가 성공적으로 실행되었습니다!")

            # 실행 결과 표시
            with st.expander("📋 실행 결과 상세", expanded=True):
                st.json(result)

        else:
            st.error(f"❌ 거래 실행 실패: {result.get('error')}")

            # 실패 원인 분석
            if "Margin is insufficient" in str(result.get('error', '')):
                st.info("💡 팁: 테스트넷 계좌에 충분한 잔고가 없을 수 있습니다.")

    except Exception as e:
        st.error(f"❌ 거래 실행 중 오류: {e}")

def handle_quick_action(action, account_balance, risk_percentage, api_keys):
    """빠른 액션 처리"""

    if action == "generate_signal":
        st.markdown("### 🎯 AI 신호 생성")

        if api_keys:
            symbol = st.selectbox("코인 선택", ["BTC", "ETH"], key="quick_symbol")

            if st.button("신호 생성", key="quick_generate"):
                with st.spinner("AI 신호 생성 중..."):
                    try:
                        # AI 시스템 초기화
                        ai_system = EnhancedAITradingSystem(
                            account_balance=account_balance,
                            risk_percent=risk_percentage/100
                        )

                        # 실시간 시장 데이터 조회
                        market_fetcher = get_market_data_fetcher()
                        market_data = market_fetcher.get_real_ohlcv_data(symbol)

                        # 신호 생성
                        signal = ai_system.generate_enhanced_signal(symbol, market_data)

                        if signal['success']:
                            st.success(f"✅ {signal['signal']} 신호 생성!")

                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("신호", signal['signal'])
                                st.metric("신뢰도", f"{signal['confidence_score']}%")
                                st.metric("진입가", f"${signal['entry_price']:,.2f}")

                            with col2:
                                st.metric("손절가", f"${signal['stop_loss_price']:,.2f}")
                                st.metric("익절가", f"${signal['take_profit_price']:,.2f}")
                                st.metric("포지션 크기", f"${signal['risk_management']['position_size']:,.2f}")
                        else:
                            st.error(f"신호 생성 실패: {signal.get('error')}")

                    except Exception as e:
                        st.error(f"오류 발생: {e}")
        else:
            st.warning("API 키를 먼저 설정해주세요.")

def show_trading_history(real_account_data, api_keys):
    """거래 기록"""

    st.markdown("### 📈 거래 기록")

    # 실제 거래 기록 조회
    if api_keys and st.button("🔄 거래 기록 새로고침"):
        st.session_state.refresh_trading_history = True

    # 거래 기록 조회
    trades = get_user_trades(st.session_state.user['id'])

    if trades:
        display_trading_statistics(trades)
        display_trades_table(trades)
        display_performance_chart(trades)
    else:
        st.info("📭 거래 기록이 없습니다.")

def get_user_trades(user_id):
    """사용자 거래 기록 조회"""
    try:
        conn = sqlite3.connect('crypto_trader_users.db')
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM trades WHERE user_id = ? ORDER BY timestamp DESC
        ''', (user_id,))

        trades = cursor.fetchall()
        conn.close()

        if trades:
            columns = ['id', 'user_id', 'symbol', 'signal', 'entry_price', 'exit_price',
                      'quantity', 'leverage', 'profit_loss', 'confidence_score', 'timestamp']
            return [dict(zip(columns, trade)) for trade in trades]

        return []

    except Exception as e:
        st.error(f"거래 기록 조회 중 오류: {e}")
        return []

def display_trading_statistics(trades):
    """거래 통계 표시"""

    if not trades:
        return

    # 통계 계산
    total_trades = len(trades)
    profitable_trades = len([t for t in trades if t['profit_loss'] > 0])
    win_rate = (profitable_trades / total_trades) * 100 if total_trades > 0 else 0
    total_pnl = sum(t['profit_loss'] for t in trades)
    avg_profit = total_pnl / total_trades if total_trades > 0 else 0

    # 통계 표시
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("총 거래 수", total_trades)

    with col2:
        st.metric("승률", f"{win_rate:.1f}%")

    with col3:
        st.metric("총 손익", f"${total_pnl:.2f}")

    with col4:
        st.metric("평균 손익", f"${avg_profit:.2f}")

def display_trades_table(trades):
    """거래 테이블 표시"""

    st.markdown("#### 📋 거래 내역")

    # 데이터프레임 생성
    df = pd.DataFrame(trades)

    # 표시할 컬럼 선택
    display_df = df[['timestamp', 'symbol', 'signal', 'entry_price', 'exit_price',
                    'quantity', 'profit_loss', 'confidence_score']].copy()

    # 컬럼명 한글화
    display_df.columns = ['시간', '심볼', '신호', '진입가', '청산가', '수량', '손익', '신뢰도']

    # 데이터 포맷팅
    display_df['진입가'] = display_df['진입가'].apply(lambda x: f"${x:,.2f}")
    display_df['청산가'] = display_df['청산가'].apply(lambda x: f"${x:,.2f}")
    display_df['수량'] = display_df['수량'].apply(lambda x: f"{x:.6f}")
    display_df['손익'] = display_df['손익'].apply(lambda x: f"${x:,.2f}")
    display_df['신뢰도'] = display_df['신뢰도'].apply(lambda x: f"{x}%")

    st.dataframe(display_df, use_container_width=True)

def display_performance_chart(trades):
    """성과 차트 표시"""

    st.markdown("#### 📊 성과 차트")

    if len(trades) < 2:
        st.info("차트 표시를 위해 더 많은 거래 데이터가 필요합니다.")
        return

    # 누적 손익 계산
    df = pd.DataFrame(trades)
    df['cumulative_pnl'] = df['profit_loss'].cumsum()
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # 차트 생성
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['cumulative_pnl'],
        mode='lines+markers',
        name='누적 손익',
        line=dict(color='#667eea', width=3),
        marker=dict(size=6)
    ))

    fig.update_layout(
        title="📈 누적 손익 추이",
        xaxis_title="시간",
        yaxis_title="누적 손익 ($)",
        hovermode='x unified',
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

def show_daily_pnl_chart():
    """일별 손익 곡선"""

    # 실제 거래 기록에서 일별 손익 데이터 가져오기
    try:
        trades = get_user_trades(st.session_state.user['id'])

        if not trades or len(trades) < 2:
            st.info("📊 일별 손익 차트를 표시하기 위해 더 많은 거래 데이터가 필요합니다.")
            return

        # 거래 데이터를 날짜별로 그룹화
        df = pd.DataFrame(trades)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date

        # 일별 손익 계산
        daily_pnl = df.groupby('date')['profit_loss'].sum().reset_index()
        daily_pnl['cumulative_pnl'] = daily_pnl['profit_loss'].cumsum()

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=daily_pnl['date'],
            y=daily_pnl['cumulative_pnl'],
            mode='lines+markers',
            name='누적 손익',
            line=dict(color='#1f77b4', width=2),
            marker=dict(size=6)
        ))

        fig.update_layout(
            title="📊 일별 누적 손익 추이",
            xaxis_title="날짜",
            yaxis_title="누적 손익 ($)",
            hovermode='x unified',
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"일별 손익 차트 생성 오류: {e}")
        st.info("📊 거래 데이터를 확인해주세요.")

def show_drawdown_chart():
    """드로우다운 차트"""

    try:
        # 실제 거래 기록에서 드로우다운 계산
        trades = get_user_trades(st.session_state.user['id'])

        if not trades or len(trades) < 5:
            st.info("📉 드로우다운 차트를 표시하기 위해 더 많은 거래 데이터가 필요합니다.")
            return

        # 거래 데이터를 시간순으로 정렬
        df = pd.DataFrame(trades)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        # 누적 손익 계산
        df['cumulative_pnl'] = df['profit_loss'].cumsum()
        df['portfolio_value'] = 10000 + df['cumulative_pnl']  # 초기 자본 10000 가정

        # 드로우다운 계산
        running_max = df['portfolio_value'].expanding().max()
        drawdown = (df['portfolio_value'] - running_max) / running_max * 100

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=drawdown,
            mode='lines',
            name='드로우다운',
            line=dict(color='red', width=2),
            fill='tozeroy',
            fillcolor='rgba(255, 0, 0, 0.1)'
        ))

        fig.update_layout(
            title="📉 포트폴리오 드로우다운",
            xaxis_title="날짜",
            yaxis_title="드로우다운 (%)",
            hovermode='x unified',
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"드로우다운 차트 생성 오류: {e}")
        st.info("📉 거래 데이터를 확인해주세요.")

def show_win_rate_stats():
    """승률 및 손익비 통계"""

    try:
        # 실제 거래 기록에서 승률 및 손익비 계산
        trades = get_user_trades(st.session_state.user['id'])

        if not trades or len(trades) < 5:
            st.info("🎯 승률 통계를 표시하기 위해 더 많은 거래 데이터가 필요합니다.")
            return

        col1, col2 = st.columns(2)

        with col1:
            # 실제 승률 계산
            winning_trades = [t for t in trades if t['profit_loss'] > 0]
            win_rate = (len(winning_trades) / len(trades)) * 100
            lose_rate = 100 - win_rate

            fig_donut = go.Figure(data=[go.Pie(
                labels=['승리', '패배'],
                values=[win_rate, lose_rate],
                hole=0.6,
                marker_colors=['#00cc96', '#ff6b6b']
            )])

            fig_donut.update_layout(
                title="🎯 승률 분석",
                annotations=[dict(text=f'{win_rate:.1f}%', x=0.5, y=0.5, font_size=20, showarrow=False)],
                height=400
            )

            st.plotly_chart(fig_donut, use_container_width=True)

        with col2:
            # 실제 손익 분포
            recent_trades = trades[:10]  # 최근 10개 거래
            profit_loss_values = [t['profit_loss'] for t in recent_trades]

            fig_bar = go.Figure(data=[go.Bar(
                x=[f'Trade {i+1}' for i in range(len(profit_loss_values))],
                y=profit_loss_values,
                marker_color=['green' if pnl > 0 else 'red' for pnl in profit_loss_values]
            )])

            fig_bar.update_layout(
                title="💰 최근 거래 손익 분포",
                xaxis_title="거래",
                yaxis_title="손익 ($)",
                height=400
            )

            st.plotly_chart(fig_bar, use_container_width=True)

    except Exception as e:
        st.error(f"승률 통계 생성 오류: {e}")
        st.info("🎯 거래 데이터를 확인해주세요.")

def show_monthly_returns_heatmap():
    """월별 수익률 히트맵"""

    try:
        # 실제 거래 기록에서 월별 수익률 계산
        trades = get_user_trades(st.session_state.user['id'])

        if not trades or len(trades) < 10:
            st.info("🗓️ 월별 수익률 히트맵을 표시하기 위해 더 많은 거래 데이터가 필요합니다.")
            return

        # 거래 데이터를 월별로 그룹화
        df = pd.DataFrame(trades)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['year'] = df['timestamp'].dt.year
        df['month'] = df['timestamp'].dt.month

        # 월별 수익률 계산
        monthly_returns = df.groupby(['year', 'month'])['profit_loss'].sum().reset_index()

        # 히트맵 데이터 준비
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        years = sorted(monthly_returns['year'].unique())

        returns_data = []
        for year in years:
            year_returns = []
            for month_num in range(1, 13):
                monthly_data = monthly_returns[
                    (monthly_returns['year'] == year) &
                    (monthly_returns['month'] == month_num)
                ]
                if not monthly_data.empty:
                    # 수익률을 퍼센트로 변환 (초기 자본 10000 가정)
                    monthly_return = (monthly_data['profit_loss'].iloc[0] / 10000) * 100
                    year_returns.append(monthly_return)
                else:
                    year_returns.append(None)
            returns_data.append(year_returns)

        fig_heatmap = go.Figure(data=go.Heatmap(
            z=returns_data,
            x=months,
            y=years,
            colorscale='RdYlGn',
            zmid=0,
            text=[[f'{val:.1f}%' if val is not None else '' for val in row] for row in returns_data],
            texttemplate='%{text}',
            textfont={"size": 10},
            hoverongaps=False
        ))

        fig_heatmap.update_layout(
            title="🗓️ 월별 수익률 히트맵",
            xaxis_title="월",
            yaxis_title="년도",
            height=300
        )

        st.plotly_chart(fig_heatmap, use_container_width=True)

    except Exception as e:
        st.error(f"월별 수익률 히트맵 생성 오류: {e}")
        st.info("🗓️ 거래 데이터를 확인해주세요.")