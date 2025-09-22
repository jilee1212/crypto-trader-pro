"""
Settings Page for Crypto Trader Pro
사용자 설정 페이지
"""

import streamlit as st
import sys
import os
import json

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from auth import get_auth_manager, get_user_manager, SessionManager
from database import get_db_manager
from database.api_manager import get_api_manager

def main():
    """설정 페이지 메인 함수"""
    st.set_page_config(
        page_title="설정 - Crypto Trader Pro",
        page_icon="⚙️",
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

    # 설정 페이지 렌더링
    render_settings_page(current_user)

def render_settings_page(user_info: dict):
    """설정 페이지 렌더링"""
    # 헤더
    render_header()

    # 뒤로가기 버튼
    if st.button("← 대시보드로 돌아가기"):
        st.switch_page("pages/dashboard.py")

    # 설정 탭
    tabs = st.tabs(["🔐 API 키 관리", "⚙️ 거래 설정", "👤 계정 설정", "🔔 알림 설정"])

    with tabs[0]:
        render_api_settings(user_info['user_id'])

    with tabs[1]:
        render_trading_settings(user_info['user_id'])

    with tabs[2]:
        render_account_settings(user_info)

    with tabs[3]:
        render_notification_settings(user_info['user_id'])

def render_header():
    """헤더 렌더링"""
    st.markdown("""
    <div style='background: linear-gradient(90deg, #2d5aa0 0%, #1f4e79 100%);
                padding: 1rem; border-radius: 10px; margin-bottom: 2rem;'>
        <h1 style='color: white; margin: 0;'>⚙️ 설정</h1>
        <p style='color: #e0e0e0; margin: 0;'>계정 및 거래 설정 관리</p>
    </div>
    """, unsafe_allow_html=True)

def render_api_settings(user_id: int):
    """API 키 설정 렌더링"""
    st.markdown("### 🔐 API 키 관리")

    api_manager = get_api_manager()

    # 현재 API 키 목록
    api_keys_dict = api_manager.list_user_api_keys(user_id)
    api_keys = []
    for key_name, info in api_keys_dict.items():
        api_keys.append({
            'id': key_name,
            'exchange': info['exchange'],
            'is_testnet': info['is_testnet'],
            'created_at': info['created_at'],
            'api_key_masked': '***' + key_name[-4:] if len(key_name) > 4 else '***'
        })

    if api_keys:
        st.markdown("#### 현재 등록된 API 키")
        for api_key in api_keys:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

                with col1:
                    st.write(f"**{api_key['exchange'].upper()}**")
                    st.write(f"키: {api_key['api_key_masked']}")

                with col2:
                    st.write(f"모드: {'테스트넷' if api_key['is_testnet'] else '실거래'}")
                    st.write(f"등록일: {api_key['created_at'].strftime('%Y-%m-%d')}")

                with col3:
                    if st.button("🔍 테스트", key=f"test_{api_key['id']}"):
                        test_api_connection(user_id, api_key['exchange'], api_key['is_testnet'])

                with col4:
                    if st.button("🗑️ 삭제", key=f"delete_{api_key['id']}"):
                        delete_api_key(user_id, api_key['exchange'], api_key['is_testnet'])

                st.divider()

    # 새 API 키 추가
    st.markdown("#### 새 API 키 추가")

    with st.form("add_api_key"):
        col1, col2 = st.columns(2)

        with col1:
            exchange = st.selectbox(
                "거래소",
                ["binance"],
                help="현재 바이낸스만 지원됩니다"
            )

            is_testnet = st.radio(
                "모드",
                [True, False],
                format_func=lambda x: "테스트넷" if x else "실거래",
                index=0,
                help="처음 사용 시 테스트넷을 권장합니다"
            )

        with col2:
            api_key = st.text_input(
                "API 키",
                type="password",
                help="바이낸스에서 발급받은 API 키를 입력하세요"
            )

            api_secret = st.text_input(
                "API 시크릿",
                type="password",
                help="바이낸스에서 발급받은 API 시크릿을 입력하세요"
            )

        if st.form_submit_button("💾 API 키 저장", use_container_width=True):
            save_api_key(user_id, exchange, api_key, api_secret, is_testnet)

    # API 키 발급 안내
    render_api_guide()

def render_trading_settings(user_id: int):
    """거래 설정 렌더링"""
    st.markdown("### ⚙️ 거래 설정")

    db_manager = get_db_manager()
    trading_settings = db_manager.get_user_trading_settings(user_id)

    with st.form("trading_settings"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 리스크 관리")

            risk_percentage = st.slider(
                "거래당 리스크 비율 (%)",
                min_value=0.5,
                max_value=10.0,
                value=trading_settings.risk_percentage if trading_settings else 2.0,
                step=0.1,
                help="각 거래에서 위험할 수 있는 자본의 비율"
            )

            daily_loss_limit = st.slider(
                "일일 손실 한도 (%)",
                min_value=1.0,
                max_value=20.0,
                value=trading_settings.daily_loss_limit if trading_settings else 5.0,
                step=0.5,
                help="하루 최대 손실 허용 한도"
            )

            max_positions = st.number_input(
                "최대 동시 포지션 수",
                min_value=1,
                max_value=10,
                value=trading_settings.max_positions if trading_settings else 3,
                help="동시에 열 수 있는 최대 포지션 수"
            )

        with col2:
            st.markdown("#### 거래 전략")

            # 현재 심볼 목록
            current_symbols = ['BTCUSDT', 'ETHUSDT']
            if trading_settings and trading_settings.symbols:
                try:
                    current_symbols = json.loads(trading_settings.symbols)
                except:
                    pass

            symbols = st.multiselect(
                "모니터링 심볼",
                ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT", "DOTUSDT", "LINKUSDT"],
                default=current_symbols,
                help="자동매매로 거래할 암호화폐 선택"
            )

            auto_trading_enabled = st.checkbox(
                "자동매매 활성화",
                value=trading_settings.auto_trading_enabled if trading_settings else False,
                help="체크하면 자동으로 거래를 실행합니다"
            )

            # 전략 설정
            st.markdown("#### 전략 파라미터")

            strategy_type = st.selectbox(
                "거래 전략",
                ["rsi_mean_reversion", "macd_trend", "bollinger_bands"],
                format_func=lambda x: {
                    "rsi_mean_reversion": "RSI 평균 회귀",
                    "macd_trend": "MACD 트렌드",
                    "bollinger_bands": "볼린저 밴드"
                }[x],
                help="사용할 거래 전략 선택"
            )

            rsi_oversold = st.number_input(
                "RSI 과매도 기준",
                min_value=10,
                max_value=40,
                value=30,
                help="RSI 과매도 신호 기준값"
            )

            rsi_overbought = st.number_input(
                "RSI 과매수 기준",
                min_value=60,
                max_value=90,
                value=70,
                help="RSI 과매수 신호 기준값"
            )

        if st.form_submit_button("💾 설정 저장", use_container_width=True):
            save_trading_settings(
                user_id, risk_percentage, daily_loss_limit, max_positions,
                symbols, auto_trading_enabled, strategy_type,
                rsi_oversold, rsi_overbought
            )

def render_account_settings(user_info: dict):
    """계정 설정 렌더링"""
    st.markdown("### 👤 계정 설정")

    user_manager = get_user_manager()
    user_details = user_manager.get_user_info(user_info['user_id'])

    if not user_details:
        st.error("사용자 정보를 가져올 수 없습니다.")
        return

    # 계정 정보 표시
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 기본 정보")
        st.info(f"**사용자명:** {user_details['username']}")
        st.info(f"**이메일:** {user_details['email']}")
        st.info(f"**가입일:** {user_details['created_at'].strftime('%Y-%m-%d')}")

        if user_details['last_login']:
            st.info(f"**마지막 로그인:** {user_details['last_login'].strftime('%Y-%m-%d %H:%M')}")

    with col2:
        st.markdown("#### 계정 상태")
        status_color = "🟢" if user_details['is_active'] else "🔴"
        st.info(f"**계정 상태:** {status_color} {'활성' if user_details['is_active'] else '비활성'}")

        trading_color = "🟢" if user_details['trading_enabled'] else "🔴"
        st.info(f"**거래 상태:** {trading_color} {'활성' if user_details['trading_enabled'] else '비활성'}")

    # 이메일 변경
    st.markdown("#### 이메일 변경")
    with st.form("change_email"):
        new_email = st.text_input(
            "새 이메일",
            placeholder="new@example.com"
        )

        if st.form_submit_button("이메일 변경"):
            change_email(user_info['user_id'], new_email)

    # 패스워드 변경
    st.markdown("#### 패스워드 변경")
    with st.form("change_password"):
        current_password = st.text_input("현재 패스워드", type="password")
        new_password = st.text_input("새 패스워드", type="password")
        confirm_password = st.text_input("새 패스워드 확인", type="password")

        if st.form_submit_button("패스워드 변경"):
            change_password(user_info['user_id'], current_password, new_password, confirm_password)

def render_notification_settings(user_id: int):
    """알림 설정 렌더링"""
    st.markdown("### 🔔 알림 설정")

    db_manager = get_db_manager()
    notification_settings = db_manager.get_user_notification_settings(user_id)

    with st.form("notification_settings"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 알림 채널")

            email_enabled = st.checkbox(
                "이메일 알림",
                value=notification_settings.email_enabled if notification_settings else True,
                help="중요한 알림을 이메일로 받습니다"
            )

            web_notifications = st.checkbox(
                "웹 알림",
                value=notification_settings.web_notifications if notification_settings else True,
                help="대시보드에서 실시간 알림을 받습니다"
            )

            telegram_enabled = st.checkbox(
                "텔레그램 알림",
                value=notification_settings.telegram_enabled if notification_settings else False,
                help="텔레그램 봇을 통한 알림"
            )

            if telegram_enabled:
                telegram_chat_id = st.text_input(
                    "텔레그램 채팅 ID",
                    value=notification_settings.telegram_chat_id if notification_settings else "",
                    help="텔레그램 봇에서 /start 명령으로 채팅 ID를 확인하세요"
                )

        with col2:
            st.markdown("#### 알림 유형")

            notify_trades = st.checkbox(
                "거래 실행 알림",
                value=notification_settings.notify_trades if notification_settings else True,
                help="매수/매도 거래 실행 시 알림"
            )

            notify_profit_loss = st.checkbox(
                "손익 알림",
                value=notification_settings.notify_profit_loss if notification_settings else True,
                help="중요한 손익 발생 시 알림"
            )

            notify_errors = st.checkbox(
                "오류 알림",
                value=notification_settings.notify_errors if notification_settings else True,
                help="시스템 오류 발생 시 알림"
            )

        if st.form_submit_button("💾 알림 설정 저장", use_container_width=True):
            save_notification_settings(
                user_id, email_enabled, web_notifications, telegram_enabled,
                telegram_chat_id if telegram_enabled else None,
                notify_trades, notify_profit_loss, notify_errors
            )

def save_api_key(user_id: int, exchange: str, api_key: str, api_secret: str, is_testnet: bool):
    """API 키 저장"""
    if not api_key or not api_secret:
        st.error("API 키와 시크릿을 모두 입력해주세요.")
        return

    try:
        api_manager = get_api_manager()
        success = api_manager.save_api_key(
            user_id, exchange, api_key, api_secret, is_testnet
        )

        if success:
            st.success("✅ API 키가 성공적으로 저장되었습니다!")

            # 연결 테스트 수행
            test_result = api_manager.validate_api_connection(user_id, exchange, is_testnet)
            if test_result['success']:
                st.success("🔗 API 연결 테스트 성공!")
                if 'account_info' in test_result:
                    account_info = test_result['account_info']
                    st.info("\ud83d\udcca 계좌 정보 조회 성공")
            else:
                st.warning(f"⚠️ API 연결 테스트 실패: {test_result.get('error', '알 수 없는 오류')}")

            st.rerun()
        else:
            st.error("API 키 저장에 실패했습니다.")

    except Exception as e:
        st.error(f"API 키 저장 오류: {e}")

def test_api_connection(user_id: int, exchange: str, is_testnet: bool):
    """API 연결 테스트"""
    try:
        api_manager = get_api_manager()
        result = api_manager.validate_api_connection(user_id, exchange, is_testnet)

        if result['success']:
            st.success("🔗 API 연결 성공!")
            if 'account_info' in result:
                account_info = result['account_info']
                st.info(f"계좌 정보 조회 성공 - 거래소: {account_info['exchange']}")
        else:
            st.error(f"❌ API 연결 실패: {result.get('error', '알 수 없는 오류')}")

    except Exception as e:
        st.error(f"API 연결 테스트 오류: {e}")

def delete_api_key(user_id: int, exchange: str, is_testnet: bool):
    """API 키 삭제"""
    try:
        api_manager = get_api_manager()
        success = api_manager.delete_api_key(user_id, exchange, is_testnet)

        if success:
            st.success("🗑️ API 키가 삭제되었습니다.")
            st.rerun()
        else:
            st.error("API 키 삭제에 실패했습니다.")

    except Exception as e:
        st.error(f"API 키 삭제 오류: {e}")

def save_trading_settings(user_id: int, risk_percentage: float, daily_loss_limit: float,
                         max_positions: int, symbols: list, auto_trading_enabled: bool,
                         strategy_type: str, rsi_oversold: int, rsi_overbought: int):
    """거래 설정 저장"""
    try:
        db_manager = get_db_manager()

        # 전략 설정 JSON 생성
        strategy_config = {
            'strategy_type': strategy_type,
            'rsi_oversold': rsi_oversold,
            'rsi_overbought': rsi_overbought,
            'stop_loss_pct': 2.0,
            'take_profit_pct': 4.0,
            'min_signal_confidence': 70
        }

        result = db_manager.update_trading_settings(
            user_id=user_id,
            risk_percentage=risk_percentage,
            daily_loss_limit=daily_loss_limit,
            max_positions=max_positions,
            auto_trading_enabled=auto_trading_enabled,
            symbols=json.dumps(symbols),
            strategy_config=json.dumps(strategy_config)
        )

        if result:
            st.success("✅ 거래 설정이 저장되었습니다!")
            st.rerun()
        else:
            st.error("거래 설정 저장에 실패했습니다.")

    except Exception as e:
        st.error(f"거래 설정 저장 오류: {e}")

def change_email(user_id: int, new_email: str):
    """이메일 변경"""
    if not new_email:
        st.error("새 이메일을 입력해주세요.")
        return

    try:
        user_manager = get_user_manager()
        result = user_manager.update_user_profile(user_id, email=new_email)

        if result['success']:
            st.success("✅ 이메일이 변경되었습니다!")
            st.rerun()
        else:
            st.error(result['message'])

    except Exception as e:
        st.error(f"이메일 변경 오류: {e}")

def change_password(user_id: int, current_password: str, new_password: str, confirm_password: str):
    """패스워드 변경"""
    if not all([current_password, new_password, confirm_password]):
        st.error("모든 필드를 입력해주세요.")
        return

    if new_password != confirm_password:
        st.error("새 패스워드가 일치하지 않습니다.")
        return

    try:
        user_manager = get_user_manager()
        result = user_manager.change_password(user_id, current_password, new_password)

        if result['success']:
            st.success("✅ 패스워드가 변경되었습니다!")
        else:
            st.error(result['message'])

    except Exception as e:
        st.error(f"패스워드 변경 오류: {e}")

def save_notification_settings(user_id: int, email_enabled: bool, web_notifications: bool,
                              telegram_enabled: bool, telegram_chat_id: str,
                              notify_trades: bool, notify_profit_loss: bool, notify_errors: bool):
    """알림 설정 저장"""
    try:
        db_manager = get_db_manager()
        result = db_manager.update_notification_settings(
            user_id=user_id,
            email_enabled=email_enabled,
            web_notifications=web_notifications,
            telegram_enabled=telegram_enabled,
            telegram_chat_id=telegram_chat_id,
            notify_trades=notify_trades,
            notify_profit_loss=notify_profit_loss,
            notify_errors=notify_errors
        )

        if result:
            st.success("✅ 알림 설정이 저장되었습니다!")
            st.rerun()
        else:
            st.error("알림 설정 저장에 실패했습니다.")

    except Exception as e:
        st.error(f"알림 설정 저장 오류: {e}")

def render_api_guide():
    """API 키 발급 안내"""
    with st.expander("📋 바이낸스 API 키 발급 안내"):
        st.markdown("""
        **바이낸스 API 키 발급 방법:**

        1. **바이낸스 계정 로그인**
           - https://www.binance.com 접속
           - 계정에 로그인

        2. **API 관리 페이지 이동**
           - 우상단 계정 아이콘 클릭
           - "API Management" 선택

        3. **새 API 키 생성**
           - "Create API" 버튼 클릭
           - API 키 이름 입력 (예: CryptoTraderPro)

        4. **권한 설정**
           - ✅ Enable Reading
           - ✅ Enable Spot & Margin Trading
           - ✅ Enable Futures (선물 거래용)
           - ❌ Enable Withdrawals (출금 권한은 비활성화 권장)

        5. **보안 설정**
           - 2FA 인증 완료
           - IP 접근 제한 설정 (선택사항)

        **⚠️ 보안 주의사항:**
        - API 키와 시크릿은 절대 타인과 공유하지 마세요
        - 처음에는 반드시 테스트넷으로 시작하세요
        - 정기적으로 API 키를 교체하세요
        """)

if __name__ == "__main__":
    main()