"""
Main Dashboard for Crypto Trader Pro
사용자별 메인 대시보드
"""

import streamlit as st
import sys
import os
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import time

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from auth import get_auth_manager, SessionManager
from database import get_db_manager
from database.api_manager import get_api_manager as get_api_key_manager
import logging

# 로그 설정
logger = logging.getLogger(__name__)

def main():
    """대시보드 메인 함수"""
    st.set_page_config(
        page_title="대시보드 - Crypto Trader Pro",
        page_icon="📊",
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

    # 대시보드 렌더링
    render_dashboard(current_user)

def render_dashboard(user_info: dict):
    """대시보드 렌더링"""
    # 헤더
    render_header(user_info)

    # 메인 컨텐츠
    render_main_content(user_info)

def render_header(user_info: dict):
    """헤더 렌더링"""
    st.markdown("""
    <div style='background: linear-gradient(90deg, #1f4e79 0%, #2d5aa0 100%);
                padding: 1rem; border-radius: 10px; margin-bottom: 2rem;'>
        <h1 style='color: white; margin: 0;'>📊 Crypto Trader Pro Dashboard</h1>
        <p style='color: #e0e0e0; margin: 0;'>24시간 무인 자동매매 시스템</p>
    </div>
    """, unsafe_allow_html=True)

    # 상단 네비게이션
    col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])

    with col1:
        st.markdown(f"**환영합니다, {user_info['username']}님! 👋**")

    with col2:
        if st.button("⚙️ 설정"):
            st.switch_page("pages/settings.py")

    with col3:
        if st.button("📈 거래"):
            st.switch_page("pages/trading.py")

    with col4:
        if st.button("📊 분석"):
            # 향후 분석 페이지로 이동
            st.info("분석 페이지는 곧 추가됩니다!")

    with col5:
        if st.button("🚪 로그아웃"):
            handle_logout()

def render_main_content(user_info: dict):
    """메인 컨텐츠 렌더링 - 캐싱 적용"""
    # 캐싱을 위한 세션 상태 키
    cache_key = f"dashboard_user_data_{user_info['user_id']}"

    # 캐시된 데이터가 없거나 수동 새로고침 요청이 있으면 데이터 로드
    if cache_key not in st.session_state or st.session_state.get('force_refresh', False):
        with st.spinner("계좌 정보를 조회하는 중..."):
            user_data = load_user_data(user_info['user_id'])
            st.session_state[cache_key] = user_data
            # 새로고침 플래그 제거
            if 'force_refresh' in st.session_state:
                del st.session_state['force_refresh']
    else:
        user_data = st.session_state[cache_key]

    # 주요 지표 카드
    render_metrics_cards(user_data)

    # 메인 컨텐츠 영역
    col1, col2 = st.columns([2, 1])

    with col1:
        render_trading_overview(user_data)
        render_recent_trades(user_data)

    with col2:
        render_account_status(user_data)
        render_quick_actions(user_info['user_id'])

def render_metrics_cards(user_data: dict):
    """주요 지표 카드 렌더링 - 실제 API 데이터"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # 실제 USDT 잔고 표시
        total_balance = user_data['total_balance']
        free_balance = user_data.get('free_balance', 0.0)

        st.metric(
            label="💰 총 자산 (USDT)",
            value=f"${total_balance:,.2f}",
            delta=f"사용가능: ${free_balance:,.2f}"
        )

    with col2:
        # API 연결 상태와 활성 포지션
        api_connected = user_data['api_status']['connected']
        st.metric(
            label="🔗 API 상태",
            value="🟢 연결됨" if api_connected else "🔴 연결안됨",
            delta="테스트넷" if user_data['api_status']['testnet'] else "실거래"
        )

    with col3:
        st.metric(
            label="🎯 오늘 거래",
            value=f"{user_data['today_trades']}회",
            delta=f"성공률 {user_data['success_rate']:.1f}%"
        )

    with col4:
        st.metric(
            label="💡 자동매매",
            value="🟢 활성" if user_data['auto_trading_enabled'] else "🔴 비활성",
            delta="실행 중" if user_data['auto_trading_enabled'] else "중지됨"
        )

    # 실시간 새로고침 버튼 추가 및 자동 새로고침 옵션
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        auto_refresh = st.checkbox("🔄 자동 새로고침 (5분)", key="auto_refresh")
        if auto_refresh:
            # 5분마다 자동 새로고침
            time_now = int(time.time())
            if time_now % 300 < 10:  # 5분마다 10초 윈도우
                st.session_state['force_refresh'] = True
                st.rerun()

    with col2:
        if st.button("🔄 수동 새로고침", use_container_width=True):
            # 강제 새로고침 플래그 설정
            st.session_state['force_refresh'] = True
            st.rerun()

    with col3:
        # API 연결 상태 표시
        if user_data.get('api_status', {}).get('connected'):
            st.success("🟢 API 연결됨")
        else:
            st.error("🔴 API 연결안됨")

def render_trading_overview(user_data: dict):
    """거래 개요 렌더링"""
    st.markdown("### 📊 거래 성과 개요")

    # 수익률 차트
    if user_data['profit_history']:
        df = pd.DataFrame(user_data['profit_history'])
        df['date'] = pd.to_datetime(df['date'])

        fig = px.line(
            df, x='date', y='cumulative_pnl',
            title='누적 손익 추이',
            labels={'cumulative_pnl': '누적 손익 (USDT)', 'date': '날짜'}
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("거래 데이터가 없습니다. 자동매매를 시작하여 성과를 확인하세요!")

def render_recent_trades(user_data: dict):
    """최근 거래 내역 렌더링"""
    st.markdown("### 📋 최근 거래 내역")

    if user_data['recent_trades']:
        trades_df = pd.DataFrame(user_data['recent_trades'])

        # 거래 내역 테이블
        st.dataframe(
            trades_df[['timestamp', 'symbol', 'side', 'amount', 'price', 'profit_loss']],
            use_container_width=True,
            column_config={
                "timestamp": st.column_config.DatetimeColumn(
                    "시간",
                    format="MM/DD HH:mm"
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
                )
            }
        )
    else:
        st.info("아직 거래 내역이 없습니다.")

def render_account_status(user_data: dict):
    """계정 상태 렌더링 - 실제 API 데이터"""
    st.markdown("### 🔍 계정 상태")

    # API 연결 상태 및 실제 잔고 정보
    api_status = user_data['api_status']
    real_balance_data = user_data.get('real_balance_data')

    if api_status['connected']:
        st.success("✅ API 연결 정상")
        st.info(f"거래소: {api_status['exchange'].upper()}")
        st.info(f"모드: {'테스트넷' if api_status['testnet'] else '실거래'}")

        # 실제 잔고 상세 정보 (USDT 기준)
        if real_balance_data:
            st.markdown("**💰 계좌 잔고 상세 (USDT 환산):**")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("총 자산", f"{real_balance_data['total']:,.2f} USDT")
            with col2:
                st.metric("사용 가능", f"{real_balance_data['free']:,.2f} USDT")
            with col3:
                st.metric("거래 중", f"{real_balance_data['locked']:,.2f} USDT")

            # 사용률 계산
            if real_balance_data['total'] > 0:
                usage_pct = (real_balance_data['locked'] / real_balance_data['total']) * 100
                st.progress(usage_pct / 100)
                st.caption(f"자산 활용률: {usage_pct:.1f}%")

            # 데이터 업데이트 시간 표시
            st.caption(f"마지막 업데이트: {datetime.now().strftime('%H:%M:%S')}")

            # 자산 구성 상세 (확장 가능)
            if st.button("📊 자산 구성 상세 보기", key="asset_breakdown"):
                show_asset_breakdown(real_balance_data.get('asset_breakdown', []))
        else:
            st.warning("⚠️ 잔고 정보를 가져올 수 없습니다.")
            st.info("API 키 설정을 확인하거나 설정 페이지에서 연결을 테스트해보세요.")
    else:
        st.error("❌ API 연결 오류")
        st.warning("설정 페이지에서 API 키를 확인하세요.")

    st.markdown("---")

    # 거래 설정
    st.markdown("**⚙️ 현재 거래 설정:**")
    trading_settings = user_data['trading_settings']

    st.write(f"• 리스크 비율: {trading_settings['risk_percentage']:.1f}%")
    st.write(f"• 최대 포지션: {trading_settings['max_positions']}개")
    st.write(f"• 일일 손실 한도: {trading_settings['daily_loss_limit']:.1f}%")

    # 모니터링 심볼
    if trading_settings['symbols']:
        st.write(f"• 모니터링 심볼: {', '.join(trading_settings['symbols'])}")

    # 실시간 가격 정보 (선택적)
    if api_status['connected'] and st.button("📊 실시간 시장 가격", use_container_width=True):
        show_current_prices(trading_settings['symbols'])

def show_current_prices(symbols: list):
    """실시간 가격 정보 표시"""
    try:
        from binance_testnet_connector import BinanceTestnetConnector

        connector = BinanceTestnetConnector()

        st.markdown("#### 📊 실시간 시장 가격")

        for symbol in symbols:
            try:
                price_result = connector.get_current_price(symbol)
                if price_result and price_result.get('success'):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**{symbol}**")
                    with col2:
                        st.write(f"${price_result['price']:,.2f}")
                else:
                    st.warning(f"⚠️ {symbol} 가격 조회 실패")
            except Exception as e:
                st.error(f"{symbol} 가격 조회 오류: {e}")

    except Exception as e:
        st.error(f"가격 조회 시스템 오류: {e}")

def show_asset_breakdown(balances: list):
    """자산 구성 상세 표시 - USDT 환산값 포함"""
    try:
        from binance_testnet_connector import BinanceTestnetConnector
        connector = BinanceTestnetConnector()

        st.markdown("#### 📊 자산 구성 상세 (USDT 환산)")

        asset_data = []
        total_usdt_value = 0.0

        for balance in balances:
            asset = balance['asset']
            total = balance['total']

            if total > 0:  # 잔고가 있는 자산만 표시
                if asset == 'USDT':
                    usdt_value = total
                    current_price = 1.0
                else:
                    try:
                        symbol = f"{asset}USDT"
                        price_result = connector.get_current_price(symbol)
                        if price_result and price_result.get('success'):
                            current_price = price_result['price']
                            usdt_value = total * current_price
                        else:
                            current_price = 0.0
                            usdt_value = 0.0
                    except:
                        current_price = 0.0
                        usdt_value = 0.0

                if usdt_value > 0:  # USDT 환산값이 있는 경우만 표시
                    asset_data.append({
                        'Asset': asset,
                        'Balance': f"{total:.6f}",
                        'Price (USDT)': f"{current_price:.2f}" if asset != 'USDT' else '1.00',
                        'Value (USDT)': f"{usdt_value:.2f}",
                        'Percentage': 0  # 나중에 계산
                    })
                    total_usdt_value += usdt_value

        # 비율 계산
        for item in asset_data:
            value = float(item['Value (USDT)'])
            percentage = (value / total_usdt_value * 100) if total_usdt_value > 0 else 0
            item['Percentage'] = f"{percentage:.1f}%"

        if asset_data:
            df = pd.DataFrame(asset_data)
            st.dataframe(df, use_container_width=True)

            # 총 자산 표시
            st.markdown(f"**총 자산 가치: {total_usdt_value:.2f} USDT**")
        else:
            st.info("표시할 자산이 없습니다.")

    except Exception as e:
        st.error(f"자산 구성 조회 오류: {e}")

def get_usdt_trading_pairs(trading_settings) -> list:
    """USDT 거래 페어만 반환"""
    default_pairs = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'BNBUSDT', 'SOLUSDT']

    if not trading_settings or not trading_settings.symbols:
        return default_pairs

    try:
        saved_symbols = eval(trading_settings.symbols) if isinstance(trading_settings.symbols, str) else trading_settings.symbols
        # USDT 페어만 필터링
        usdt_pairs = [symbol for symbol in saved_symbols if symbol.endswith('USDT')]
        return usdt_pairs if usdt_pairs else default_pairs
    except:
        return default_pairs

def render_quick_actions(user_id: int):
    """빠른 작업 렌더링"""
    st.markdown("### ⚡ 빠른 작업")

    # 자동매매 제어
    if st.button("🚀 자동매매 시작", use_container_width=True):
        handle_start_auto_trading(user_id)

    if st.button("🛑 자동매매 중지", use_container_width=True):
        handle_stop_auto_trading(user_id)

    if st.button("📊 실시간 상태", use_container_width=True):
        show_real_time_status(user_id)

    if st.button("🔄 설정 새로고침", use_container_width=True):
        st.rerun()

def load_user_data(user_id: int) -> dict:
    """사용자 데이터 로드 - 실제 API 연동"""
    try:
        db_manager = get_db_manager()
        api_manager = get_api_key_manager()

        # 기본 사용자 정보
        user = db_manager.get_user_by_id(user_id)
        trading_settings = db_manager.get_user_trading_settings(user_id)

        # API 키 조회 및 실제 API 연결 테스트
        api_key_record = db_manager.get_user_api_key(user_id, "binance", is_testnet=True)
        api_status = {'connected': False, 'exchange': 'binance', 'testnet': True}
        real_balance_data = None

        if api_key_record:
            try:
                # 실제 API 키 복호화
                credentials = api_manager.get_api_credentials(user_id, "binance", is_testnet=True)
                if not credentials:
                    logger.warning(f"API 키 복호화 실패 - user_id: {user_id}")
                    api_status['connected'] = False
                    # 에러 반환 대신 계속 진행하여 기본값 반환
                else:
                    api_key, api_secret = credentials

                    # 실제 계좌 정보 조회
                    from binance_testnet_connector import BinanceTestnetConnector

                    connector = BinanceTestnetConnector()
                    connector.api_key = api_key
                    connector.secret_key = api_secret
                    connector.session.headers.update({'X-MBX-APIKEY': api_key})

                    logger.info(f"API 연결 시도 - user_id: {user_id}, testnet: True")
                    account_result = connector.get_account_info()

                    if account_result and account_result.get('success'):
                        api_status['connected'] = True
                        balances = account_result.get('balances', [])
                        logger.info(f"계좌 정보 조회 성공 - 자산 수: {len(balances)}")

                        # 모든 자산을 USDT 기준으로 계산
                        total_usdt_value = 0.0
                        free_usdt_value = 0.0
                        locked_usdt_value = 0.0

                        for balance in balances:
                            asset = balance['asset']
                            total = balance['total']
                            free = balance['free']
                            locked = balance['locked']

                            if total > 0:  # 잔고가 있는 자산만 처리
                                if asset == 'USDT':
                                    # USDT는 1:1 비율
                                    total_usdt_value += total
                                    free_usdt_value += free
                                    locked_usdt_value += locked
                                    logger.info(f"USDT 잔고: {total}")
                                else:
                                    # 다른 암호화폐는 USDT로 환산
                                    try:
                                        symbol = f"{asset}USDT"
                                        price_result = connector.get_current_price(symbol)
                                        if price_result and price_result.get('success'):
                                            current_price = price_result['price']
                                            asset_usdt_value = total * current_price
                                            total_usdt_value += asset_usdt_value
                                            free_usdt_value += free * current_price
                                            locked_usdt_value += locked * current_price
                                            logger.info(f"{asset} 환산: {total} * {current_price} = {asset_usdt_value} USDT")
                                    except Exception as price_error:
                                        logger.warning(f"{asset} 가격 조회 실패: {price_error}")

                        real_balance_data = {
                            'total': total_usdt_value,
                            'free': free_usdt_value,
                            'locked': locked_usdt_value,
                            'asset_breakdown': balances  # 원본 자산 정보 보관
                        }
                        logger.info(f"총 USDT 환산 자산: {total_usdt_value}")
                    else:
                        error_msg = account_result.get('error', '알 수 없는 오류') if account_result else 'API 응답 없음'
                        logger.error(f"계좌 정보 조회 실패: {error_msg}")
                        api_status['connected'] = False

            except Exception as e:
                logger.error(f"API 연결 중 예외 발생 - user_id: {user_id}, error: {e}")
                api_status['connected'] = False

        # 거래 통계
        recent_trades = db_manager.get_user_trades(user_id, limit=10)
        active_session = db_manager.get_active_trading_session(user_id)

        # 실제 잔고 사용 또는 기본값
        total_balance = real_balance_data['total'] if real_balance_data else 0.0
        free_balance = real_balance_data['free'] if real_balance_data else 0.0

        # 어제 잔고와 비교하여 변화율 계산 (임시로 모의 데이터)
        balance_change = 2.5 if total_balance > 0 else 0.0

        return {
            'total_balance': total_balance,
            'free_balance': free_balance,
            'balance_change': balance_change,
            'active_positions': len([t for t in recent_trades if t.side == 'BUY']),
            'position_change': 1 if recent_trades else 0,
            'today_trades': len([t for t in recent_trades if t.timestamp.date() == datetime.utcnow().date()]),
            'success_rate': 75.0 if recent_trades else 0.0,
            'auto_trading_enabled': user.trading_enabled if user else False,
            'api_status': api_status,
            'real_balance_data': real_balance_data,
            'trading_settings': {
                'risk_percentage': trading_settings.risk_percentage if trading_settings else 2.0,
                'max_positions': trading_settings.max_positions if trading_settings else 3,
                'daily_loss_limit': trading_settings.daily_loss_limit if trading_settings else 5.0,
                'symbols': get_usdt_trading_pairs(trading_settings)  # USDT 페어만 사용
            },
            'recent_trades': [
                {
                    'timestamp': trade.timestamp,
                    'symbol': trade.symbol,
                    'side': trade.side,
                    'amount': trade.amount,
                    'price': trade.price,
                    'profit_loss': trade.profit_loss or 0.0
                }
                for trade in recent_trades
            ],
            'profit_history': []  # 실제로는 계산된 수익률 히스토리
        }

    except Exception as e:
        st.error(f"사용자 데이터 로드 오류: {e}")
        return {
            'total_balance': 0.0,
            'balance_change': 0.0,
            'active_positions': 0,
            'position_change': 0,
            'today_trades': 0,
            'success_rate': 0.0,
            'auto_trading_enabled': False,
            'api_status': {'connected': False, 'exchange': '', 'testnet': True},
            'trading_settings': {
                'risk_percentage': 2.0,
                'max_positions': 3,
                'daily_loss_limit': 5.0,
                'symbols': []
            },
            'recent_trades': [],
            'profit_history': []
        }

def handle_start_auto_trading(user_id: int):
    """자동매매 시작 처리"""
    try:
        # 사용자 거래 활성화
        from auth import get_user_manager
        user_manager = get_user_manager()
        result = user_manager.enable_trading(user_id, True)

        if result['success']:
            st.success("🚀 자동매매가 시작되었습니다!")
            st.info("백그라운드 거래 봇이 활성 사용자 목록을 업데이트할 때까지 최대 5분 정도 소요될 수 있습니다.")
        else:
            st.error(result['message'])

    except Exception as e:
        st.error(f"자동매매 시작 오류: {e}")

def handle_stop_auto_trading(user_id: int):
    """자동매매 중지 처리"""
    try:
        # 사용자 거래 비활성화
        from auth import get_user_manager
        user_manager = get_user_manager()
        result = user_manager.enable_trading(user_id, False)

        if result['success']:
            st.warning("🛑 자동매매가 중지되었습니다!")
            st.info("현재 열린 포지션은 유지되며, 새로운 거래만 중지됩니다.")
        else:
            st.error(result['message'])

    except Exception as e:
        st.error(f"자동매매 중지 오류: {e}")

def show_real_time_status(user_id: int):
    """실시간 상태 표시"""
    st.info("실시간 상태 모니터링 기능은 개발 중입니다.")
    # TODO: 백그라운드 거래 봇과의 통신 구현

def handle_logout():
    """로그아웃 처리"""
    auth_manager = get_auth_manager()
    auth_manager.destroy_session()
    st.success("로그아웃되었습니다.")
    st.switch_page("pages/login.py")

if __name__ == "__main__":
    main()