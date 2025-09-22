"""
Login Page for Crypto Trader Pro
사용자 로그인 페이지
"""

import streamlit as st
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from auth import get_auth_manager, get_user_manager, SessionManager

def main():
    """로그인 페이지 메인 함수"""
    st.set_page_config(
        page_title="로그인 - Crypto Trader Pro",
        page_icon="🔐",
        layout="centered"
    )

    # 세션 상태 초기화
    SessionManager.init_session_state()

    # 이미 로그인된 경우 메인 대시보드로 리다이렉트
    auth_manager = get_auth_manager()
    if auth_manager.is_authenticated():
        st.switch_page("pages/dashboard.py")
        return

    # 로그인 페이지 UI
    render_login_page()

def render_login_page():
    """로그인 페이지 렌더링"""
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0;'>
        <h1>🚀 Crypto Trader Pro</h1>
        <h3>🔐 로그인</h3>
        <p style='color: #666;'>24시간 무인 자동매매 시스템에 오신 것을 환영합니다</p>
    </div>
    """, unsafe_allow_html=True)

    # 로그인 폼
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            with st.form("login_form"):
                st.markdown("### 계정 정보")

                username = st.text_input(
                    "사용자명 또는 이메일",
                    placeholder="username 또는 email@example.com"
                )

                password = st.text_input(
                    "패스워드",
                    type="password",
                    placeholder="패스워드 입력"
                )

                col_login, col_register = st.columns(2)

                with col_login:
                    login_submitted = st.form_submit_button(
                        "🔐 로그인",
                        use_container_width=True
                    )

                with col_register:
                    if st.form_submit_button("👤 회원가입", use_container_width=True):
                        st.switch_page("pages/register.py")

            # 로그인 처리
            if login_submitted:
                handle_login(username, password)

    # 테스트 계정 정보 표시
    render_test_account_info()

    # 푸터
    render_footer()

def handle_login(username: str, password: str):
    """로그인 처리"""
    if not username or not password:
        st.error("사용자명과 패스워드를 모두 입력해주세요.")
        return

    try:
        # 사용자 인증
        user_manager = get_user_manager()
        auth_result = user_manager.authenticate_user(username, password)

        if auth_result['success']:
            # 세션 생성
            auth_manager = get_auth_manager()
            user_data = auth_result['user']

            session_created = auth_manager.create_session(
                user_data['id'],
                user_data['username']
            )

            if session_created:
                st.success(f"환영합니다, {user_data['username']}님!")
                st.balloons()

                # 잠시 대기 후 대시보드로 이동
                import time
                time.sleep(1)
                st.switch_page("pages/dashboard.py")
            else:
                st.error("세션 생성에 실패했습니다. 다시 시도해주세요.")
        else:
            st.error(auth_result['message'])

    except Exception as e:
        st.error(f"로그인 중 오류가 발생했습니다: {str(e)}")

def render_test_account_info():
    """테스트 계정 정보 표시"""
    with st.expander("🧪 테스트 계정 정보"):
        st.markdown("""
        **개발/테스트용 계정:**

        **관리자 계정:**
        - 사용자명: `admin`
        - 패스워드: `admin123`

        **일반 사용자 계정:**
        - 사용자명: `trader1`
        - 패스워드: `trader123`

        ---

        **참고사항:**
        - 모든 거래는 바이낸스 테스트넷에서 실행됩니다
        - 실제 자금이 사용되지 않습니다
        - API 키 설정이 필요합니다
        """)

def render_footer():
    """푸터 렌더링"""
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.8rem;'>
        <p>🔒 모든 데이터는 암호화되어 안전하게 보관됩니다</p>
        <p>⚠️ 교육 및 연구 목적으로만 사용하세요</p>
        <p>📧 문의: admin@cryptotrader.pro</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()