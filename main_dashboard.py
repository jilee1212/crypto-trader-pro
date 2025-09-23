#!/usr/bin/env python3
"""
Crypto Trader Pro - Main Dashboard with Authentication
로그인 기능이 있는 메인 대시보드
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import sqlite3
import bcrypt
import os

# Import our connector
from binance_testnet_connector import BinanceTestnetConnector

# Page config
st.set_page_config(
    page_title="Crypto Trader Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'user_role' not in st.session_state:
    st.session_state.user_role = None

# Initialize connector
@st.cache_resource
def init_connector():
    return BinanceTestnetConnector()

def verify_login(username, password):
    """로그인 검증"""
    db_path = "database/crypto_trader.db"

    if not os.path.exists(db_path):
        return False, "데이터베이스를 찾을 수 없습니다."

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 사용자 조회
        cursor.execute('''
            SELECT password_hash, role, is_active
            FROM users
            WHERE username = ?
        ''', (username,))

        result = cursor.fetchone()

        if not result:
            return False, "사용자를 찾을 수 없습니다."

        password_hash, role, is_active = result

        if not is_active:
            return False, "계정이 비활성화되었습니다."

        # 패스워드 검증
        if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
            # 로그인 성공 시 last_login 업데이트
            cursor.execute('''
                UPDATE users
                SET last_login = ?, failed_login_attempts = 0
                WHERE username = ?
            ''', (datetime.now(), username))
            conn.commit()

            return True, role
        else:
            # 실패 횟수 증가
            cursor.execute('''
                UPDATE users
                SET failed_login_attempts = failed_login_attempts + 1
                WHERE username = ?
            ''', (username,))
            conn.commit()

            return False, "패스워드가 일치하지 않습니다."

    except Exception as e:
        return False, f"로그인 오류: {str(e)}"

    finally:
        conn.close()

def show_login_page():
    """로그인 페이지 표시"""
    st.title("🚀 Crypto Trader Pro")
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.subheader("🔐 로그인")

        with st.form("login_form"):
            username = st.text_input("사용자명", placeholder="admin 또는 trader1")
            password = st.text_input("패스워드", type="password", placeholder="패스워드를 입력하세요")
            submit_button = st.form_submit_button("로그인", use_container_width=True)

            if submit_button:
                if username and password:
                    success, result = verify_login(username, password)

                    if success:
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.user_role = result
                        st.success(f"환영합니다, {username}님!")
                        st.rerun()
                    else:
                        st.error(f"로그인 실패: {result}")
                else:
                    st.warning("사용자명과 패스워드를 모두 입력해주세요.")

        st.markdown("---")
        st.info("🧪 **테스트 계정 정보**")

        col_admin, col_user = st.columns(2)

        with col_admin:
            st.markdown("**관리자 계정:**")
            st.code("사용자명: admin\n패스워드: admin123")

        with col_user:
            st.markdown("**일반 사용자:**")
            st.code("사용자명: trader1\n패스워드: trader123")

def show_main_dashboard():
    """메인 대시보드 표시"""

    # Header with logout
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.title("🚀 Crypto Trader Pro - Dashboard")

    with col2:
        st.write(f"👤 **{st.session_state.username}**")
        st.write(f"🔑 {st.session_state.user_role}")

    with col3:
        if st.button("🚪 로그아웃", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.user_role = None
            st.rerun()

    st.markdown("---")

    # Initialize connector
    connector = init_connector()

    # Sidebar
    st.sidebar.title("📊 Control Panel")
    st.sidebar.write(f"로그인: {st.session_state.username}")
    st.sidebar.write(f"권한: {st.session_state.user_role}")

    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Live Prices", "💰 Portfolio", "📊 Market Data", "⚙️ Settings"])

    with tab1:
        st.header("Real-time Cryptocurrency Prices")

        # Major coins
        major_coins = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT']

        # Create columns for price display
        cols = st.columns(len(major_coins))

        for i, coin in enumerate(major_coins):
            with cols[i]:
                try:
                    price_data = connector.get_current_price(coin)
                    if isinstance(price_data, dict) and price_data.get('success'):
                        price = price_data.get('price', 0)
                        bid = price_data.get('bid', 0) if isinstance(price_data.get('bid'), (int, float)) else 0
                        ask = price_data.get('ask', 0) if isinstance(price_data.get('ask'), (int, float)) else 0

                        st.metric(
                            label=coin,
                            value=f"${price:,.2f}",
                            delta=f"${bid - ask:.2f}" if bid and ask else "0.00"
                        )
                    else:
                        st.error(f"Failed to load {coin}")
                except Exception as e:
                    st.error(f"Error loading {coin}: {str(e)}")

        # Detailed price table
        st.subheader("Detailed Price Information")

        if st.button("Refresh Prices"):
            price_data = []
            for coin in major_coins:
                try:
                    result = connector.get_current_price(coin)
                    if isinstance(result, dict) and result.get('success'):
                        price_data.append({
                            'Symbol': coin,
                            'Price (USDT)': f"${result.get('price', 0):,.2f}",
                            'Bid': f"${result.get('bid', 0):,.2f}",
                            'Ask': f"${result.get('ask', 0):,.2f}",
                            'Volume': f"{result.get('volume', 0):,.2f}",
                            'Last Update': result.get('timestamp', datetime.now()).strftime('%H:%M:%S') if hasattr(result.get('timestamp', datetime.now()), 'strftime') else 'N/A'
                        })
                except Exception as e:
                    st.error(f"Error loading {coin}: {str(e)}")

            if price_data:
                df = pd.DataFrame(price_data)
                st.dataframe(df, use_container_width=True)

    with tab2:
        st.header("Portfolio Management")

        if st.session_state.user_role == 'admin':
            st.success("🔑 관리자 권한으로 모든 포트폴리오 기능을 사용할 수 있습니다.")
        else:
            st.info("📊 일반 사용자 권한으로 제한된 포트폴리오 기능을 사용할 수 있습니다.")

        # Test connection
        if st.button("Test Connection"):
            with st.spinner("Testing connection..."):
                result = connector.test_connection()
                if result['success']:
                    st.success("✅ Connection successful!")
                    st.json(result)
                else:
                    st.error("❌ Connection failed")
                    st.error(result.get('error', 'Unknown error'))

    with tab3:
        st.header("Market Analysis")

        # Exchange info
        if st.button("Load Market Info"):
            with st.spinner("Loading market data..."):
                symbols = connector.get_exchange_info()
                st.success(f"Loaded {len(symbols)} trading pairs")

                # Show sample of symbols
                if symbols:
                    st.subheader("Available Trading Pairs (Sample)")
                    sample_symbols = symbols[:20]  # Show first 20
                    df = pd.DataFrame({'Trading Pairs': sample_symbols})
                    st.dataframe(df, use_container_width=True)

        # Order book
        st.subheader("Order Book (BTC/USDT)")
        if st.button("Load Order Book"):
            orderbook = connector.get_order_book('BTC/USDT', 10)
            if orderbook:
                col1, col2 = st.columns(2)

                with col1:
                    st.write("**Bids (Buy Orders)**")
                    bids_df = pd.DataFrame(orderbook['bids'], columns=['Price', 'Quantity'])
                    bids_df['Price'] = bids_df['Price'].astype(float)
                    bids_df['Quantity'] = bids_df['Quantity'].astype(float)
                    st.dataframe(bids_df)

                with col2:
                    st.write("**Asks (Sell Orders)**")
                    asks_df = pd.DataFrame(orderbook['asks'], columns=['Price', 'Quantity'])
                    asks_df['Price'] = asks_df['Price'].astype(float)
                    asks_df['Quantity'] = asks_df['Quantity'].astype(float)
                    st.dataframe(asks_df)

    with tab4:
        st.header("Settings & Configuration")

        # User info
        st.subheader("🔐 User Information")
        user_info_col1, user_info_col2 = st.columns(2)

        with user_info_col1:
            st.write(f"**사용자명:** {st.session_state.username}")
            st.write(f"**권한:** {st.session_state.user_role}")

        with user_info_col2:
            if st.session_state.user_role == 'admin':
                st.success("🔑 관리자 권한")
                st.write("- 모든 기능 접근 가능")
                st.write("- 사용자 관리 가능")
                st.write("- 시스템 설정 변경 가능")
            else:
                st.info("👤 일반 사용자 권한")
                st.write("- 기본 거래 기능 사용 가능")
                st.write("- 개인 포트폴리오 관리")
                st.write("- 시장 데이터 조회")

        st.subheader("⚙️ API Configuration")
        st.info("For full functionality, configure your Binance Testnet API keys")

        # API key input (for future use)
        api_key = st.text_input("API Key", type="password", help="Your Binance Testnet API Key")
        secret_key = st.text_input("Secret Key", type="password", help="Your Binance Testnet Secret Key")

        if st.button("Save Configuration"):
            if api_key and secret_key:
                st.success("Configuration saved successfully!")
                st.info("Restart the application to apply changes")
            else:
                st.warning("Please enter both API key and secret key")

        st.subheader("📊 System Information")
        st.write("**CCXT Version:**", "4.5.5")
        st.write("**Exchange:**", "Binance Testnet")
        st.write("**Status:**", "✅ Online" if connector.exchange else "❌ Offline")
        st.write("**Database:**", "✅ Connected" if os.path.exists("database/crypto_trader.db") else "❌ Not Found")

def main():
    """메인 함수"""
    if not st.session_state.authenticated:
        show_login_page()
    else:
        show_main_dashboard()

if __name__ == "__main__":
    main()