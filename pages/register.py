"""
Registration Page for Crypto Trader Pro
사용자 회원가입 페이지
"""

import streamlit as st
import sys
import os
import re

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from auth import get_auth_manager, get_user_manager, SessionManager

def main():
    """회원가입 페이지 메인 함수"""
    st.set_page_config(
        page_title="회원가입 - Crypto Trader Pro",
        page_icon="👤",
        layout="centered"
    )

    # 세션 상태 초기화
    SessionManager.init_session_state()

    # 이미 로그인된 경우 대시보드로 리다이렉트
    auth_manager = get_auth_manager()
    if auth_manager.is_authenticated():
        st.switch_page("pages/dashboard.py")
        return

    # 회원가입 페이지 UI
    render_register_page()

def render_register_page():
    """회원가입 페이지 렌더링"""
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0;'>
        <h1>🚀 Crypto Trader Pro</h1>
        <h3>👤 회원가입</h3>
        <p style='color: #666;'>24시간 무인 자동매매 시스템 계정을 생성하세요</p>
    </div>
    """, unsafe_allow_html=True)

    # 회원가입 폼
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            with st.form("register_form"):
                st.markdown("### 계정 정보 입력")

                # 사용자명
                username = st.text_input(
                    "사용자명 *",
                    placeholder="영문, 숫자, 언더스코어 3-20자",
                    help="영문, 숫자, 언더스코어(_)만 사용 가능, 3-20자"
                )

                # 이메일
                email = st.text_input(
                    "이메일 *",
                    placeholder="email@example.com",
                    help="유효한 이메일 주소를 입력하세요"
                )

                # 패스워드
                password = st.text_input(
                    "패스워드 *",
                    type="password",
                    placeholder="안전한 패스워드를 입력하세요",
                    help="최소 8자, 대소문자, 숫자, 특수문자 포함"
                )

                # 패스워드 확인
                password_confirm = st.text_input(
                    "패스워드 확인 *",
                    type="password",
                    placeholder="패스워드를 다시 입력하세요"
                )

                # 패스워드 강도 표시
                if password:
                    password_strength = check_password_strength(password)
                    display_password_strength(password_strength)

                # 이용약관 동의
                terms_agreed = st.checkbox(
                    "이용약관 및 개인정보처리방침에 동의합니다 *",
                    help="서비스 이용을 위해 필수 동의 항목입니다"
                )

                # 리스크 경고 동의
                risk_agreed = st.checkbox(
                    "투자 리스크에 대해 충분히 이해하고 동의합니다 *",
                    help="암호화폐 거래는 높은 위험을 수반할 수 있습니다"
                )

                col_register, col_login = st.columns(2)

                with col_register:
                    register_submitted = st.form_submit_button(
                        "👤 계정 생성",
                        use_container_width=True
                    )

                with col_login:
                    if st.form_submit_button("🔐 로그인", use_container_width=True):
                        st.switch_page("pages/login.py")

            # 회원가입 처리
            if register_submitted:
                handle_registration(
                    username, email, password, password_confirm,
                    terms_agreed, risk_agreed
                )

    # 보안 및 개인정보 안내
    render_security_info()

    # 푸터
    render_footer()

def handle_registration(username: str, email: str, password: str,
                       password_confirm: str, terms_agreed: bool, risk_agreed: bool):
    """회원가입 처리"""
    try:
        # 입력 값 검증
        validation_errors = validate_registration_input(
            username, email, password, password_confirm, terms_agreed, risk_agreed
        )

        if validation_errors:
            for error in validation_errors:
                st.error(error)
            return

        # 사용자 생성
        user_manager = get_user_manager()
        result = user_manager.create_user(username, email, password)

        if result['success']:
            st.success("🎉 계정이 성공적으로 생성되었습니다!")
            st.success("이제 로그인하여 거래를 시작할 수 있습니다.")

            # 자동 로그인 처리
            auth_result = user_manager.authenticate_user(username, password)
            if auth_result['success']:
                auth_manager = get_auth_manager()
                user_data = auth_result['user']

                session_created = auth_manager.create_session(
                    user_data['id'],
                    user_data['username']
                )

                if session_created:
                    st.balloons()
                    import time
                    time.sleep(2)
                    st.switch_page("pages/dashboard.py")

        else:
            st.error(result['message'])

    except Exception as e:
        st.error(f"회원가입 중 오류가 발생했습니다: {str(e)}")

def validate_registration_input(username: str, email: str, password: str,
                               password_confirm: str, terms_agreed: bool,
                               risk_agreed: bool) -> list:
    """회원가입 입력 값 검증"""
    errors = []

    # 필수 필드 체크
    if not username:
        errors.append("사용자명을 입력해주세요.")
    if not email:
        errors.append("이메일을 입력해주세요.")
    if not password:
        errors.append("패스워드를 입력해주세요.")
    if not password_confirm:
        errors.append("패스워드 확인을 입력해주세요.")

    # 사용자명 형식 체크
    if username and not validate_username(username):
        errors.append("사용자명은 3-20자의 영문, 숫자, 언더스코어만 사용 가능합니다.")

    # 이메일 형식 체크
    if email and not validate_email(email):
        errors.append("유효한 이메일 주소를 입력해주세요.")

    # 패스워드 일치 체크
    if password and password_confirm and password != password_confirm:
        errors.append("패스워드가 일치하지 않습니다.")

    # 패스워드 강도 체크
    if password:
        auth_manager = get_auth_manager()
        password_validation = auth_manager.validate_password_strength(password)
        if not password_validation['valid']:
            errors.extend(password_validation['messages'])

    # 동의 체크
    if not terms_agreed:
        errors.append("이용약관에 동의해주세요.")
    if not risk_agreed:
        errors.append("투자 리스크에 대한 동의가 필요합니다.")

    return errors

def validate_username(username: str) -> bool:
    """사용자명 형식 검증"""
    if len(username) < 3 or len(username) > 20:
        return False
    pattern = r'^[a-zA-Z0-9_]+$'
    return bool(re.match(pattern, username))

def validate_email(email: str) -> bool:
    """이메일 형식 검증"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def check_password_strength(password: str) -> dict:
    """패스워드 강도 체크"""
    auth_manager = get_auth_manager()
    return auth_manager.validate_password_strength(password)

def display_password_strength(strength_info: dict):
    """패스워드 강도 표시"""
    if strength_info['score'] >= 4:
        st.success(f"패스워드 강도: {strength_info['strength']} ✅")
    elif strength_info['score'] >= 3:
        st.warning(f"패스워드 강도: {strength_info['strength']} ⚠️")
    else:
        st.error(f"패스워드 강도: {strength_info['strength']} ❌")

    if strength_info['messages']:
        with st.expander("패스워드 요구사항"):
            for message in strength_info['messages']:
                st.write(f"• {message}")

def render_security_info():
    """보안 정보 표시"""
    with st.expander("🔒 보안 및 개인정보 보호"):
        st.markdown("""
        **데이터 보안:**
        - 모든 패스워드는 bcrypt로 암호화되어 저장됩니다
        - API 키는 Fernet 암호화로 안전하게 보관됩니다
        - JWT 토큰 기반 세션 관리로 보안을 강화합니다

        **개인정보 처리:**
        - 최소한의 정보만 수집합니다 (사용자명, 이메일)
        - 개인정보는 서비스 제공 목적으로만 사용됩니다
        - 제3자에게 개인정보를 제공하지 않습니다

        **투자 리스크:**
        - 암호화폐 거래는 높은 변동성과 손실 위험을 수반합니다
        - 투자 원금 손실 가능성이 있습니다
        - 충분한 학습과 연습 후 거래를 시작하세요
        """)

def render_footer():
    """푸터 렌더링"""
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.8rem;'>
        <p>🛡️ 안전하고 투명한 자동매매 플랫폼</p>
        <p>⚠️ 교육 및 연구 목적으로만 사용하세요</p>
        <p>📧 지원: support@cryptotrader.pro</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()