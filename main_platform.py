"""
Main Platform Router for Crypto Trader Pro
24시간 무인 자동매매 시스템 - 인증 기반 메인 라우터
"""

import streamlit as st
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from auth import get_auth_manager, SessionManager

def main():
    """메인 플랫폼 라우터"""
    st.set_page_config(
        page_title="Crypto Trader Pro",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 세션 상태 초기화
    SessionManager.init_session_state()

    # 인증 상태 확인
    auth_manager = get_auth_manager()

    if auth_manager.is_authenticated():
        # 인증된 사용자 - 대시보드로 리다이렉트
        current_user = auth_manager.get_current_user()
        if current_user:
            render_authenticated_home(current_user)
        else:
            # 세션 오류 - 로그인 페이지로
            auth_manager.destroy_session()
            st.switch_page("pages/login.py")
    else:
        # 미인증 사용자 - 로그인 페이지로
        st.switch_page("pages/login.py")

def render_authenticated_home(user_info: dict):
    """인증된 사용자 홈 렌더링"""
    # 환영 메시지 표시 후 대시보드로 이동
    st.markdown("""
    <div style='text-align: center; padding: 3rem 0;'>
        <h1>🚀 Crypto Trader Pro</h1>
        <h3>24시간 무인 자동매매 시스템</h3>
        <p style='color: #666; font-size: 1.2rem;'>환영합니다! 대시보드로 이동합니다...</p>
    </div>
    """, unsafe_allow_html=True)

    # 자동으로 대시보드로 이동
    st.switch_page("pages/dashboard.py")

if __name__ == "__main__":
    main()