"""
Trading Page for Crypto Trader Pro
거래 모니터링 및 제어 페이지
"""

import streamlit as st
import sys
import os
import time
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import json

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from auth import get_auth_manager, SessionManager
from database import get_db_manager

def main():
    """거래 페이지 메인 함수"""
    st.set_page_config(
        page_title="거래 - Crypto Trader Pro",
        page_icon="📈",
        layout="wide"
    )

    # 세션 상태 초기화
    SessionManager.init_session_state()

    # 인증 확인
    auth_manager = get_auth_manager()
    if not auth_manager.is_authenticated():
        st.error("로그인이 필요합니다.")
        st.switch_page("pages/login.py")
        return

    # 현재 사용자 정보
    current_user = auth_manager.get_current_user()
    if not current_user:
        st.error("사용자 정보를 가져올 수 없습니다.")
        st.switch_page("pages/login.py")
        return

    # 거래 페이지 렌더링
    render_trading_page(current_user)

def render_trading_page(user_info: dict):
    """거래 페이지 렌더링"""
    # 헤더
    render_header()

    # 뒤로가기 및 새로고침 버튼
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("← 대시보드로 돌아가기"):
            st.switch_page("pages/dashboard.py")

    with col2:
        if st.button("🔄 새로고침"):
            st.rerun()

    with col3:
        # 자동 새로고침 토글
        auto_refresh = st.toggle("자동 새로고침 (30초)", value=False)
        if auto_refresh:
            time.sleep(30)
            st.rerun()

    # 거래 데이터 로드
    trading_data = load_trading_data(user_info['user_id'])

    # 실시간 상태 표시
    render_real_time_status(trading_data)

    # 메인 컨텐츠
    col1, col2 = st.columns([2, 1])

    with col1:
        render_trading_charts(trading_data)
        render_trade_history(trading_data)

    with col2:
        render_trading_controls(user_info['user_id'])
        render_current_positions(trading_data)

def render_header():
    """헤더 렌더링"""
    st.markdown("""
    <div style='background: linear-gradient(90deg, #0f7b0f 0%, #2d5aa0 100%);
                padding: 1rem; border-radius: 10px; margin-bottom: 2rem;'>
        <h1 style='color: white; margin: 0;'>📈 거래 모니터링</h1>
        <p style='color: #e0e0e0; margin: 0;'>실시간 거래 상태 및 제어</p>
    </div>
    """, unsafe_allow_html=True)

def render_real_time_status(trading_data: dict):
    """실시간 상태 표시"""
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        status_color = "🟢" if trading_data['bot_status']['is_running'] else "🔴"
        st.metric(
            "거래 봇 상태",
            f"{status_color} {'실행 중' if trading_data['bot_status']['is_running'] else '중지됨'}"
        )

    with col2:
        st.metric(
            "활성 포지션",
            f"{trading_data['active_positions']}개",
            delta=f"{trading_data['position_change']:+d}"
        )

    with col3:
        st.metric(
            "오늘 손익",
            f"${trading_data['today_pnl']:,.2f}",
            delta=f"{trading_data['today_pnl_pct']:+.2f}%"
        )

    with col4:
        st.metric(
            "총 거래",
            f"{trading_data['total_trades']}회",
            delta=f"성공률 {trading_data['success_rate']:.1f}%"
        )

    with col5:
        last_update = trading_data.get('last_update', datetime.utcnow())
        seconds_ago = (datetime.utcnow() - last_update).total_seconds()
        st.metric(
            "마지막 업데이트",
            f"{int(seconds_ago)}초 전",
            delta="실시간" if seconds_ago < 30 else "지연됨"
        )

def render_trading_charts(trading_data: dict):
    """거래 차트 렌더링"""
    st.markdown("### 📊 거래 성과 분석")

    # 탭으로 차트 구분
    chart_tabs = st.tabs(["💰 손익 추이", "📈 거래량", "🎯 성공률", "📊 포지션 분포"])

    with chart_tabs[0]:
        render_pnl_chart(trading_data)

    with chart_tabs[1]:
        render_volume_chart(trading_data)

    with chart_tabs[2]:
        render_success_rate_chart(trading_data)

    with chart_tabs[3]:
        render_position_distribution(trading_data)

def render_pnl_chart(trading_data: dict):
    """손익 차트 렌더링"""
    pnl_data = trading_data.get('pnl_history', [])

    if pnl_data:
        df = pd.DataFrame(pnl_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        fig = go.Figure()

        # 누적 손익 라인
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['cumulative_pnl'],
            mode='lines',
            name='누적 손익',
            line=dict(color='#2E86AB', width=2),
            hovertemplate='시간: %{x}<br>누적 손익: $%{y:.2f}<extra></extra>'
        ))

        # 일일 손익 바
        fig.add_trace(go.Bar(
            x=df['timestamp'],
            y=df['daily_pnl'],
            name='일일 손익',
            opacity=0.7,
            marker_color=['green' if x >= 0 else 'red' for x in df['daily_pnl']],
            hovertemplate='날짜: %{x}<br>일일 손익: $%{y:.2f}<extra></extra>'
        ))

        fig.update_layout(
            title="손익 추이",
            xaxis_title="시간",
            yaxis_title="손익 (USDT)",
            height=400,
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("손익 데이터가 없습니다. 거래가 시작되면 차트가 표시됩니다.")

def render_volume_chart(trading_data: dict):
    """거래량 차트 렌더링"""
    volume_data = trading_data.get('volume_history', [])

    if volume_data:
        df = pd.DataFrame(volume_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        fig = px.bar(
            df, x='timestamp', y='volume',
            title='일별 거래량',
            labels={'volume': '거래량 (USDT)', 'timestamp': '날짜'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("거래량 데이터가 없습니다.")

def render_success_rate_chart(trading_data: dict):
    """성공률 차트 렌더링"""
    success_data = trading_data.get('success_history', [])

    if success_data:
        df = pd.DataFrame(success_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['success_rate'],
            mode='lines+markers',
            name='성공률',
            line=dict(color='#A23B72', width=2),
            hovertemplate='날짜: %{x}<br>성공률: %{y:.1f}%<extra></extra>'
        ))

        fig.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="기준선 (50%)")

        fig.update_layout(
            title="거래 성공률 추이",
            xaxis_title="시간",
            yaxis_title="성공률 (%)",
            height=400,
            yaxis=dict(range=[0, 100])
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("성공률 데이터가 없습니다.")

def render_position_distribution(trading_data: dict):
    """포지션 분포 차트 렌더링"""
    positions = trading_data.get('current_positions', [])

    if positions:
        df = pd.DataFrame(positions)

        # 심볼별 포지션 크기
        fig = px.pie(
            df, values='size_usdt', names='symbol',
            title='심볼별 포지션 분포'
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("현재 열린 포지션이 없습니다.")

def render_trading_controls(user_id: int):
    """거래 제어 패널 렌더링"""
    st.markdown("### 🎮 거래 제어")

    # 자동매매 제어
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 거래 시작", use_container_width=True, type="primary"):
            start_auto_trading(user_id)

    with col2:
        if st.button("🛑 거래 중지", use_container_width=True):
            stop_auto_trading(user_id)

    st.divider()

    # 수동 제어
    st.markdown("#### 수동 제어")

    if st.button("⏸️ 일시 정지", use_container_width=True):
        pause_trading(user_id)

    if st.button("🔄 재시작", use_container_width=True):
        restart_trading(user_id)

    if st.button("🚨 긴급 정지", use_container_width=True):
        emergency_stop(user_id)

    st.divider()

    # 빠른 설정
    st.markdown("#### 빠른 설정")

    risk_level = st.selectbox(
        "리스크 레벨",
        ["보수적 (1%)", "균형 (2%)", "공격적 (3%)"],
        index=1
    )

    if st.button("⚡ 설정 적용", use_container_width=True):
        apply_quick_settings(user_id, risk_level)

def render_current_positions(trading_data: dict):
    """현재 포지션 표시"""
    st.markdown("### 💼 현재 포지션")

    positions = trading_data.get('current_positions', [])

    if positions:
        for position in positions:
            with st.container():
                col1, col2 = st.columns([2, 1])

                with col1:
                    # 포지션 정보
                    profit_color = "green" if position['pnl'] >= 0 else "red"
                    st.markdown(f"""
                    **{position['symbol']}** ({position['side']})
                    - 진입가: ${position['entry_price']:,.2f}
                    - 현재가: ${position['current_price']:,.2f}
                    - 수량: {position['quantity']:.6f}
                    - <span style='color: {profit_color}'>손익: ${position['pnl']:,.2f} ({position['pnl_pct']:+.2f}%)</span>
                    """, unsafe_allow_html=True)

                with col2:
                    if st.button(f"❌ 청산", key=f"close_{position['symbol']}"):
                        close_position(position['symbol'])

                st.divider()
    else:
        st.info("현재 열린 포지션이 없습니다.")

def render_trade_history(trading_data: dict):
    """거래 내역 표시"""
    st.markdown("### 📋 최근 거래 내역")

    trades = trading_data.get('recent_trades', [])

    if trades:
        # 거래 내역 필터
        col1, col2, col3 = st.columns(3)

        with col1:
            symbol_filter = st.selectbox(
                "심볼 필터",
                ["전체"] + list(set([trade['symbol'] for trade in trades]))
            )

        with col2:
            side_filter = st.selectbox(
                "거래 유형",
                ["전체", "BUY", "SELL"]
            )

        with col3:
            date_filter = st.date_input(
                "날짜 필터",
                value=datetime.now().date()
            )

        # 필터 적용
        filtered_trades = filter_trades(trades, symbol_filter, side_filter, date_filter)

        # 거래 내역 테이블
        if filtered_trades:
            df = pd.DataFrame(filtered_trades)
            st.dataframe(
                df[['timestamp', 'symbol', 'side', 'amount', 'price', 'profit_loss', 'signal_confidence']],
                use_container_width=True,
                column_config={
                    "timestamp": st.column_config.DatetimeColumn(
                        "시간",
                        format="MM/DD HH:mm:ss"
                    ),
                    "symbol": "심볼",
                    "side": "유형",
                    "amount": st.column_config.NumberColumn(
                        "수량",
                        format="%.6f"
                    ),
                    "price": st.column_config.NumberColumn(
                        "가격 (USDT)",
                        format="$%.2f"
                    ),
                    "profit_loss": st.column_config.NumberColumn(
                        "손익 (USDT)",
                        format="%.2f"
                    ),
                    "signal_confidence": st.column_config.ProgressColumn(
                        "신뢰도",
                        min_value=0,
                        max_value=100
                    )
                }
            )
        else:
            st.info("필터 조건에 맞는 거래가 없습니다.")
    else:
        st.info("거래 내역이 없습니다.")

def load_trading_data(user_id: int) -> dict:
    """거래 데이터 로드"""
    try:
        from database.database_manager import get_db_manager
        from database.api_manager import get_api_manager
        from binance_testnet_connector import BinanceTestnetConnector

        db_manager = get_db_manager()
        api_manager = get_api_manager()

        # 기본 데이터
        recent_trades = db_manager.get_user_trades(user_id, limit=50)
        active_session = db_manager.get_active_trading_session(user_id)

        # 실제 API 데이터 가져오기
        credentials = api_manager.get_api_credentials(user_id, "binance", is_testnet=True)

        if credentials:
            api_key, api_secret = credentials
            connector = BinanceTestnetConnector()

            try:
                # 실제 계좌 정보 조회
                account_info = connector.get_account_info(api_key, api_secret)
                open_orders = connector.get_open_orders(api_key, api_secret)

                # 오늘 거래 기록에서 손익 계산
                today = datetime.now().date()
                today_trades = [t for t in recent_trades if t.timestamp.date() == today]
                today_pnl = sum(t.profit_loss or 0.0 for t in today_trades)

                # USDT 잔고 조회
                usdt_balance = 0.0
                if account_info.get('success'):
                    balances = account_info.get('data', {}).get('balances', [])
                    for balance in balances:
                        if balance['asset'] == 'USDT':
                            usdt_balance = float(balance['free']) + float(balance['locked'])
                            break

                # 현재 포지션 정보 (미체결 주문에서 추정)
                current_positions = []
                active_positions_count = 0

                if open_orders.get('success'):
                    orders = open_orders.get('data', [])
                    # USDT 페어 주문만 필터링
                    usdt_orders = [order for order in orders if order['symbol'].endswith('USDT')]
                    active_positions_count = len(usdt_orders)

                    for order in usdt_orders[:5]:  # 최대 5개만 표시
                        try:
                            symbol = order['symbol']
                            side = order['side']
                            price = float(order['price'])
                            quantity = float(order['origQty'])

                            # 현재 시장 가격 조회 시도
                            current_price = price  # 기본값
                            try:
                                ticker = connector.get_ticker_price(symbol)
                                if ticker.get('success'):
                                    current_price = float(ticker['data']['price'])
                            except:
                                pass

                            # PnL 계산 (간단한 추정)
                            if side == 'BUY':
                                pnl = (current_price - price) * quantity
                                pnl_pct = ((current_price / price) - 1) * 100
                            else:
                                pnl = (price - current_price) * quantity
                                pnl_pct = ((price / current_price) - 1) * 100

                            current_positions.append({
                                'symbol': symbol,
                                'side': 'LONG' if side == 'BUY' else 'SHORT',
                                'entry_price': price,
                                'current_price': current_price,
                                'quantity': quantity,
                                'pnl': pnl,
                                'pnl_pct': pnl_pct,
                                'size_usdt': quantity * current_price
                            })
                        except Exception as e:
                            print(f"포지션 계산 오류: {e}")
                            continue

                # 성공률 계산
                success_rate = 0.0
                if recent_trades:
                    profitable_trades = [t for t in recent_trades if (t.profit_loss or 0.0) > 0]
                    success_rate = (len(profitable_trades) / len(recent_trades)) * 100

                # 실제 데이터로 반환
                return {
                    'bot_status': {
                        'is_running': active_session is not None,
                        'last_heartbeat': datetime.utcnow()
                    },
                    'active_positions': active_positions_count,
                    'position_change': 0,  # 이전 데이터와 비교 필요
                    'today_pnl': today_pnl,
                    'today_pnl_pct': (today_pnl / usdt_balance * 100) if usdt_balance > 0 else 0.0,
                    'total_trades': len(recent_trades),
                    'success_rate': success_rate,
                    'last_update': datetime.utcnow(),
                    'pnl_history': [
                        {
                            'timestamp': datetime.utcnow() - timedelta(days=i),
                            'daily_pnl': sum(t.profit_loss or 0.0 for t in recent_trades
                                           if t.timestamp.date() == (datetime.now() - timedelta(days=i)).date()),
                            'cumulative_pnl': sum(t.profit_loss or 0.0 for t in recent_trades
                                                if t.timestamp.date() <= (datetime.now() - timedelta(days=i)).date())
                        }
                        for i in range(7, 0, -1)
                    ],
                    'volume_history': [
                        {
                            'timestamp': datetime.utcnow() - timedelta(days=i),
                            'volume': sum(t.amount * t.price for t in recent_trades
                                        if t.timestamp.date() == (datetime.now() - timedelta(days=i)).date())
                        }
                        for i in range(7, 0, -1)
                    ],
                    'success_history': [
                        {
                            'timestamp': datetime.utcnow() - timedelta(days=i),
                            'success_rate': success_rate  # 일별 성공률은 추후 구현
                        }
                        for i in range(7, 0, -1)
                    ],
                    'current_positions': current_positions,
                    'recent_trades': [
                        {
                            'timestamp': trade.timestamp,
                            'symbol': trade.symbol,
                            'side': trade.side,
                            'amount': trade.amount,
                            'price': trade.price,
                            'profit_loss': trade.profit_loss or 0.0,
                            'signal_confidence': trade.signal_confidence or 75
                        }
                        for trade in recent_trades
                    ]
                }

            except Exception as e:
                print(f"API 연동 오류: {e}")
                # API 오류 시 데이터베이스 데이터만 사용
                pass

        # API 키가 없거나 API 오류 시 기본 데이터
        success_rate = 0.0
        today_pnl = 0.0
        if recent_trades:
            profitable_trades = [t for t in recent_trades if (t.profit_loss or 0.0) > 0]
            success_rate = (len(profitable_trades) / len(recent_trades)) * 100
            today = datetime.now().date()
            today_trades = [t for t in recent_trades if t.timestamp.date() == today]
            today_pnl = sum(t.profit_loss or 0.0 for t in today_trades)

        return {
            'bot_status': {
                'is_running': active_session is not None,
                'last_heartbeat': datetime.utcnow()
            },
            'active_positions': 0,
            'position_change': 0,
            'today_pnl': today_pnl,
            'today_pnl_pct': 0.0,
            'total_trades': len(recent_trades),
            'success_rate': success_rate,
            'last_update': datetime.utcnow(),
            'pnl_history': [],
            'volume_history': [],
            'success_history': [],
            'current_positions': [],
            'recent_trades': [
                {
                    'timestamp': trade.timestamp,
                    'symbol': trade.symbol,
                    'side': trade.side,
                    'amount': trade.amount,
                    'price': trade.price,
                    'profit_loss': trade.profit_loss or 0.0,
                    'signal_confidence': trade.signal_confidence or 75
                }
                for trade in recent_trades
            ]
        }

    except Exception as e:
        st.error(f"거래 데이터 로드 오류: {e}")
        return {
            'bot_status': {'is_running': False, 'last_heartbeat': datetime.utcnow()},
            'active_positions': 0,
            'position_change': 0,
            'today_pnl': 0.0,
            'today_pnl_pct': 0.0,
            'total_trades': 0,
            'success_rate': 0.0,
            'last_update': datetime.utcnow(),
            'pnl_history': [],
            'volume_history': [],
            'success_history': [],
            'current_positions': [],
            'recent_trades': []
        }

def start_auto_trading(user_id: int):
    """자동매매 시작"""
    try:
        from auth import get_user_manager
        user_manager = get_user_manager()
        result = user_manager.enable_trading(user_id, True)

        if result['success']:
            st.success("🚀 자동매매가 시작되었습니다!")
            st.info("백그라운드 거래 봇이 활성화되는데 최대 5분 정도 소요될 수 있습니다.")
            st.rerun()
        else:
            st.error(result['message'])

    except Exception as e:
        st.error(f"자동매매 시작 오류: {e}")

def stop_auto_trading(user_id: int):
    """자동매매 중지"""
    try:
        from auth import get_user_manager
        user_manager = get_user_manager()
        result = user_manager.enable_trading(user_id, False)

        if result['success']:
            st.warning("🛑 자동매매가 중지되었습니다!")
            st.rerun()
        else:
            st.error(result['message'])

    except Exception as e:
        st.error(f"자동매매 중지 오류: {e}")

def pause_trading(user_id: int):
    """거래 일시 정지"""
    st.info("⏸️ 거래가 일시 정지되었습니다.")
    # TODO: 백그라운드 봇과 통신 구현

def restart_trading(user_id: int):
    """거래 재시작"""
    st.success("🔄 거래가 재시작되었습니다.")
    # TODO: 백그라운드 봇과 통신 구현

def emergency_stop(user_id: int):
    """긴급 정지"""
    st.error("🚨 긴급 정지가 실행되었습니다!")
    st.warning("모든 거래가 즉시 중단되고 포지션이 정리됩니다.")
    # TODO: 백그라운드 봇과 통신 구현

def apply_quick_settings(user_id: int, risk_level: str):
    """빠른 설정 적용"""
    risk_map = {
        "보수적 (1%)": 1.0,
        "균형 (2%)": 2.0,
        "공격적 (3%)": 3.0
    }

    risk_percentage = risk_map.get(risk_level, 2.0)

    try:
        db_manager = get_db_manager()
        result = db_manager.update_trading_settings(
            user_id=user_id,
            risk_percentage=risk_percentage
        )

        if result:
            st.success(f"⚡ 리스크 레벨이 {risk_level}로 설정되었습니다!")
        else:
            st.error("설정 적용에 실패했습니다.")

    except Exception as e:
        st.error(f"설정 적용 오류: {e}")

def close_position(symbol: str):
    """포지션 청산"""
    st.warning(f"❌ {symbol} 포지션 청산이 요청되었습니다.")
    # TODO: 백그라운드 봇과 통신 구현

def filter_trades(trades: list, symbol_filter: str, side_filter: str, date_filter) -> list:
    """거래 내역 필터링"""
    filtered = trades

    if symbol_filter != "전체":
        filtered = [t for t in filtered if t['symbol'] == symbol_filter]

    if side_filter != "전체":
        filtered = [t for t in filtered if t['side'] == side_filter]

    if date_filter:
        filtered = [t for t in filtered if t['timestamp'].date() == date_filter]

    return filtered

if __name__ == "__main__":
    main()