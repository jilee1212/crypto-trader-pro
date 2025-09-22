#!/usr/bin/env python3
"""
Main Platform - Crypto Trader Pro
메인 플랫폼 - 앱 구조, 인증, 데이터베이스 초기화
"""

import streamlit as st
import sqlite3
import hashlib
import time
import sys
import os

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import UI helpers
from ui_helpers import get_css_styles

# 페이지 설정
st.set_page_config(
    page_title="Crypto Trader Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일 적용
st.markdown(get_css_styles(), unsafe_allow_html=True)

# 데이터베이스 초기화
def init_database():
    """사용자 데이터베이스 초기화"""
    conn = sqlite3.connect('crypto_trader_users.db')
    cursor = conn.cursor()

    # 사용자 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            api_key_encrypted TEXT,
            secret_key_encrypted TEXT,
            is_testnet BOOLEAN DEFAULT 1,
            account_balance REAL DEFAULT 10000.0,
            risk_percentage REAL DEFAULT 2.0
        )
    ''')

    # 거래 기록 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            symbol TEXT NOT NULL,
            signal TEXT NOT NULL,
            entry_price REAL,
            exit_price REAL,
            quantity REAL,
            leverage INTEGER,
            profit_loss REAL,
            confidence_score INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # 설정 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            trading_mode TEXT DEFAULT 'HYBRID',
            auto_trading BOOLEAN DEFAULT 0,
            max_leverage INTEGER DEFAULT 10,
            max_margin_usage REAL DEFAULT 50.0,
            daily_risk_limit REAL DEFAULT 5.0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    conn.commit()
    conn.close()

# 비밀번호 해시 함수
def hash_password(password):
    """비밀번호 해시화"""
    return hashlib.sha256(password.encode()).hexdigest()

# 사용자 인증 함수들
def register_user(username, email, password):
    """사용자 회원가입"""
    try:
        conn = sqlite3.connect('crypto_trader_users.db')
        cursor = conn.cursor()

        password_hash = hash_password(password)

        cursor.execute('''
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
        ''', (username, email, password_hash))

        user_id = cursor.lastrowid

        # 기본 설정 추가
        cursor.execute('''
            INSERT INTO user_settings (user_id) VALUES (?)
        ''', (user_id,))

        conn.commit()
        conn.close()
        return True, "회원가입이 완료되었습니다!"

    except sqlite3.IntegrityError:
        return False, "이미 존재하는 사용자명 또는 이메일입니다."
    except Exception as e:
        return False, f"회원가입 중 오류가 발생했습니다: {e}"

def login_user(username, password):
    """사용자 로그인"""
    try:
        conn = sqlite3.connect('crypto_trader_users.db')
        cursor = conn.cursor()

        password_hash = hash_password(password)

        cursor.execute('''
            SELECT id, username, email FROM users
            WHERE username = ? AND password_hash = ?
        ''', (username, password_hash))

        user = cursor.fetchone()
        conn.close()

        if user:
            return True, {
                'id': user[0],
                'username': user[1],
                'email': user[2]
            }
        else:
            return False, "잘못된 사용자명 또는 비밀번호입니다."

    except Exception as e:
        return False, f"로그인 중 오류가 발생했습니다: {e}"

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

# 로그인/회원가입 페이지
def show_auth_page():
    """인증 페이지 표시"""
    st.markdown("""
    <div class="main-header">
        <h1>🚀 Crypto Trader Pro</h1>
        <p>AI 기반 암호화폐 자동 거래 플랫폼</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        tab1, tab2 = st.tabs(["🔑 로그인", "📝 회원가입"])

        with tab1:
            st.markdown("### 로그인")

            with st.form("login_form"):
                username = st.text_input("사용자명", placeholder="사용자명을 입력하세요")
                password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")

                submitted = st.form_submit_button("로그인", use_container_width=True)

                if submitted:
                    if username and password:
                        success, result = login_user(username, password)
                        if success:
                            st.session_state.logged_in = True
                            st.session_state.user = result
                            st.rerun()
                        else:
                            st.error(result)
                    else:
                        st.error("모든 필드를 입력해주세요.")

        with tab2:
            st.markdown("### 회원가입")

            with st.form("register_form"):
                new_username = st.text_input("사용자명", placeholder="사용자명을 입력하세요")
                new_email = st.text_input("이메일", placeholder="이메일을 입력하세요")
                new_password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")
                confirm_password = st.text_input("비밀번호 확인", type="password", placeholder="비밀번호를 다시 입력하세요")

                submitted = st.form_submit_button("회원가입", use_container_width=True)

                if submitted:
                    if all([new_username, new_email, new_password, confirm_password]):
                        if new_password == confirm_password:
                            if len(new_password) >= 6:
                                success, message = register_user(new_username, new_email, new_password)
                                if success:
                                    st.success(message)
                                else:
                                    st.error(message)
                            else:
                                st.error("비밀번호는 최소 6자 이상이어야 합니다.")
                        else:
                            st.error("비밀번호가 일치하지 않습니다.")
                    else:
                        st.error("모든 필드를 입력해주세요.")

# 메인 애플리케이션
def main():
    """메인 애플리케이션"""

    # 데이터베이스 초기화
    init_database()

    # 세션 상태 초기화
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    # 로그인 상태에 따른 페이지 표시
    if not st.session_state.logged_in:
        show_auth_page()
    else:
        from dashboard_components import show_main_dashboard
        show_main_dashboard()

if __name__ == "__main__":
    main()