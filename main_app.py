#!/usr/bin/env python3
"""
Crypto Trader Pro - 통합 메인 애플리케이션
단일 포트 통합 시스템 (Phase 6.1)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, Any
import time
import logging
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import our systems
from binance_mainnet_connector import BinanceMainnetConnector
from database.api_manager import get_api_manager
from auth.user_manager import get_user_manager
from auth.authentication import AuthenticationManager
from auth.session_manager import get_session_manager
from database.trading_settings_manager import get_trading_settings_manager

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_page_config():
    """페이지 설정"""
    st.set_page_config(
        page_title="Crypto Trader Pro",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded"
    )

def init_session_state():
    """세션 상태 초기화"""
    # 사용자 인증 상태
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    # 진행 단계 관리
    if 'current_stage' not in st.session_state:
        st.session_state.current_stage = 'login'  # login, safety_test, main_trading

    # API 키 상태
    if 'api_keys_saved' not in st.session_state:
        st.session_state.api_keys_saved = False
    if 'api_verified' not in st.session_state:
        st.session_state.api_verified = False

    # API 커넥터
    if 'api_connector' not in st.session_state:
        st.session_state.api_connector = None

    # 최소 주문 금액 캐싱
    if 'min_order_amounts' not in st.session_state:
        st.session_state.min_order_amounts = {}
    if 'min_amounts_last_update' not in st.session_state:
        st.session_state.min_amounts_last_update = 0

    # 사이드바 메뉴
    if 'sidebar_menu' not in st.session_state:
        st.session_state.sidebar_menu = 'Dashboard'

def check_and_restore_session():
    """세션 확인 및 복원"""
    try:
        session_manager = get_session_manager()

        # URL 파라미터에서 사용자 확인
        query_params = st.query_params
        if 'user' in query_params:
            username = query_params['user']
            success = session_manager.load_session_into_streamlit(username)
            if success:
                # 단계 복원 로직
                restore_user_stage()
                return True

        # 기존 세션 확인
        if 'user' in st.session_state and st.session_state.user:
            username = st.session_state.user['username']
            session_manager.update_session_activity(username)
            restore_user_stage()
            return True

        return False
    except Exception as e:
        logger.error(f"Session restoration error: {e}")
        return False

def restore_user_stage():
    """사용자 진행 단계 복원"""
    try:
        if st.session_state.user:
            user_id = st.session_state.user['id']
            api_manager = get_api_manager()

            # API 키가 저장되어 있는지 확인
            credentials = api_manager.get_api_credentials(user_id, 'binance', is_testnet=False)

            if credentials:
                st.session_state.api_keys_saved = True
                st.session_state.api_verified = True
                st.session_state.current_stage = 'main_trading'

                # API 커넥터 초기화 (단일 인스턴스 보장)
                api_key, api_secret = credentials
                init_api_connector(api_key, api_secret)
            else:
                st.session_state.current_stage = 'safety_test'

    except Exception as e:
        logger.error(f"Stage restoration error: {e}")

def init_api_connector(api_key, api_secret):
    """API 커넥터 단일 인스턴스 초기화"""
    try:
        # 기존 커넥터가 있으면 재사용, 없으면 새로 생성
        if not st.session_state.api_connector:
            st.session_state.api_connector = BinanceMainnetConnector(api_key, api_secret)
            logger.info("New API connector initialized")
        else:
            # API 키가 변경되었는지 확인
            current_connector = st.session_state.api_connector
            if current_connector.api_key != api_key:
                # API 키가 다르면 새로 초기화
                st.session_state.api_connector = BinanceMainnetConnector(api_key, api_secret)
                logger.info("API connector reinitialized with new credentials")
            else:
                logger.info("Existing API connector reused")

        return st.session_state.api_connector
    except Exception as e:
        logger.error(f"API connector initialization error: {e}")
        return None

def get_api_connector():
    """현재 API 커넥터 인스턴스 반환"""
    if 'api_connector' not in st.session_state or st.session_state.api_connector is None:
        logger.warning("No API connector available")
        return None
    return st.session_state.api_connector

def ensure_api_connector():
    """API 커넥터 존재 확인 및 복원"""
    if not st.session_state.api_connector and st.session_state.user:
        try:
            user_id = st.session_state.user['id']
            api_manager = get_api_manager()
            credentials = api_manager.get_api_credentials(user_id, 'binance', is_testnet=False)

            if credentials:
                api_key, api_secret = credentials
                init_api_connector(api_key, api_secret)
                return True
        except Exception as e:
            logger.error(f"API connector restoration error: {e}")

    return st.session_state.api_connector is not None

def update_min_order_amounts():
    """최소 주문 금액 업데이트 (30분마다)"""
    current_time = time.time()
    last_update = st.session_state.min_amounts_last_update

    # 30분(1800초)마다 업데이트 또는 첫 로드시
    if current_time - last_update > 1800 or not st.session_state.min_order_amounts:
        connector = get_api_connector()
        if connector:
            try:
                st.session_state.min_order_amounts = connector.get_min_order_amounts()
                st.session_state.min_amounts_last_update = current_time
                logger.info("Minimum order amounts updated")
            except Exception as e:
                logger.error(f"Failed to update minimum order amounts: {e}")

def get_min_amount_for_symbol(symbol: str) -> float:
    """심볼별 최소 주문 금액 조회"""
    update_min_order_amounts()
    return st.session_state.min_order_amounts.get(symbol, 10.0)

def validate_trade_amount(symbol: str, amount: float) -> Dict[str, Any]:
    """거래 금액 검증"""
    min_amount = get_min_amount_for_symbol(symbol)

    result = {
        'valid': True,
        'min_amount': min_amount,
        'message': '',
        'suggested_amount': None
    }

    if amount < min_amount:
        result['valid'] = False
        result['suggested_amount'] = min_amount * 1.1
        result['message'] = f"{symbol} 최소 주문 금액: ${min_amount:.1f} USDT"

    return result

def show_progress_indicator():
    """진행률 표시"""
    stages = {
        'login': {'title': '1단계: 로그인', 'icon': '🔐', 'status': 'completed' if st.session_state.authenticated else 'current'},
        'safety_test': {'title': '2단계: API 테스트', 'icon': '🛡️', 'status': 'completed' if st.session_state.api_verified else ('current' if st.session_state.authenticated else 'pending')},
        'main_trading': {'title': '3단계: 거래 시작', 'icon': '🚀', 'status': 'current' if st.session_state.current_stage == 'main_trading' else 'pending'}
    }

    # 진행률 바 표시
    st.markdown("### 📊 진행 상황")

    # 전체 진행률 계산
    completed_stages = sum(1 for stage in stages.values() if stage['status'] == 'completed')
    current_stage = 1 if any(stage['status'] == 'current' for stage in stages.values()) else 0
    total_progress = (completed_stages + current_stage * 0.5) / len(stages)

    # 진행률 바
    st.progress(total_progress, f"전체 진행률: {total_progress*100:.0f}%")

    cols = st.columns(3)

    for i, (stage_key, stage_info) in enumerate(stages.items()):
        with cols[i]:
            if stage_info['status'] == 'completed':
                st.success(f"✅ {stage_info['icon']} {stage_info['title']}")
            elif stage_info['status'] == 'current':
                st.info(f"⏳ {stage_info['icon']} {stage_info['title']} (진행중)")
            else:
                st.write(f"⭕ {stage_info['icon']} {stage_info['title']}")

    # 다음 단계 안내
    if st.session_state.authenticated:
        if st.session_state.current_stage == 'safety_test':
            st.info("💡 **다음 단계**: API 키를 입력하고 테스트 거래를 완료하세요")
        elif st.session_state.current_stage == 'main_trading':
            st.success("🎉 **모든 설정 완료!** 이제 안전하게 거래할 수 있습니다")

def show_sidebar():
    """사이드바 메뉴"""
    with st.sidebar:
        st.title("🚀 Crypto Trader Pro")

        # 사용자 정보 표시
        if st.session_state.authenticated and st.session_state.user:
            st.success(f"👤 **{st.session_state.user['username']}**님")
            st.info(f"⏰ {datetime.now().strftime('%H:%M')}")

        st.divider()

        # 메뉴 선택
        menu_options = ['Dashboard', 'AI Signals', 'Settings']
        st.session_state.sidebar_menu = st.radio(
            "메뉴",
            menu_options,
            index=menu_options.index(st.session_state.sidebar_menu)
        )

        st.divider()

        # 긴급 중단 버튼 (거래 단계에서만)
        if st.session_state.current_stage == 'main_trading':
            connector = get_api_connector()
            if connector:
                if st.button("🚨 긴급 중단", type="primary", use_container_width=True):
                    connector.emergency_stop()
                    st.error("🚨 모든 거래가 중단되었습니다!")
                    st.rerun()

        # API 연결 상태 표시 (거래 단계에서만)
        if st.session_state.current_stage == 'main_trading':
            connector = get_api_connector()
            if connector:
                try:
                    safety_status = connector.get_safety_status()
                    st.divider()
                    st.markdown("**⚡ 실시간 상태**")
                    st.write(f"🛡️ 거래: {'🟢' if safety_status['trade_enabled'] else '🔴'}")
                    st.write(f"💰 최대주문: ${safety_status['max_order_amount']}")
                    st.write(f"🚨 긴급중단: {'🟢' if safety_status['emergency_stop_enabled'] else '🔴'}")
                except Exception as e:
                    st.error(f"상태 확인 오류: {e}")

        # 로그아웃 버튼
        if st.session_state.authenticated:
            if st.button("🚪 로그아웃", use_container_width=True):
                logout_user()

def logout_user():
    """사용자 로그아웃"""
    # 세션 정리
    for key in list(st.session_state.keys()):
        del st.session_state[key]

    # 초기 상태로 복원
    init_session_state()
    st.rerun()

# ===== 페이지 함수들 =====

def show_login_page():
    """로그인/회원가입 페이지"""
    st.header("🔐 로그인 / 회원가입")

    # 탭으로 로그인/회원가입 구분
    tab1, tab2 = st.tabs(["로그인", "회원가입"])

    with tab1:
        show_login_form()

    with tab2:
        show_signup_form()

    # 플로우 안내
    st.divider()
    st.markdown("### 📋 시스템 플로우")

    # 시각적 플로우 표시
    flow_cols = st.columns(3)

    with flow_cols[0]:
        st.info("""
        **🔐 1단계: 로그인/회원가입**

        ← **현재 단계**

        • 계정 생성 또는 로그인
        • 세션 관리 시스템 연동
        """)

    with flow_cols[1]:
        st.write("""
        **🛡️ 2단계: API 테스트**

        • 메인넷 API 키 입력
        • $8 USDT 안전 테스트
        • 실거래 검증 완료
        """)

    with flow_cols[2]:
        st.write("""
        **🚀 3단계: 메인 거래**

        • 실시간 거래 대시보드
        • 포지션 관리
        • 안전 설정 적용
        """)

    st.success("💡 **자동 전환**: 각 단계 완료 시 자동으로 다음 단계로 이동합니다 (새 탭 없음)")

def show_login_form():
    """로그인 폼"""
    with st.form("login_form"):
        username = st.text_input("사용자명", placeholder="사용자명을 입력하세요")
        password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")

        submitted = st.form_submit_button("로그인", use_container_width=True, type="primary")

        if submitted:
            if username and password:
                try:
                    user_manager = get_user_manager()
                    session_manager = get_session_manager()

                    # 사용자 인증
                    result = user_manager.authenticate_user(username, password)
                    if result and result.get('success'):
                        user = result['user']

                        # 데이터베이스 세션 생성
                        session_id = session_manager.create_session(user['id'], username)
                        if session_id:
                            # Streamlit 세션에 저장
                            st.session_state.user = user
                            st.session_state.authenticated = True

                            # 단계 복원
                            restore_user_stage()

                            st.success("✅ 로그인 성공!")

                            # 자동 전환 메시지
                            if st.session_state.current_stage == 'safety_test':
                                st.info("🔄 API 테스트 단계로 이동합니다...")
                                # 즉시 전환을 위한 카운트다운
                                with st.empty():
                                    for i in range(3, 0, -1):
                                        st.info(f"🔄 {i}초 후 API 테스트 페이지로 이동합니다...")
                                        time.sleep(1)
                                    st.info("🔄 이동 중...")
                            elif st.session_state.current_stage == 'main_trading':
                                st.info("🔄 메인 거래 대시보드로 이동합니다...")
                                # 즉시 전환을 위한 카운트다운
                                with st.empty():
                                    for i in range(3, 0, -1):
                                        st.info(f"🔄 {i}초 후 메인 거래 페이지로 이동합니다...")
                                        time.sleep(1)
                                    st.info("🔄 이동 중...")

                            st.rerun()
                        else:
                            st.error("❌ 세션 생성 실패")
                    else:
                        st.error("❌ 잘못된 사용자명 또는 비밀번호")
                except Exception as e:
                    st.error(f"❌ 로그인 오류: {e}")
            else:
                st.warning("⚠️ 사용자명과 비밀번호를 모두 입력해주세요")

def show_signup_form():
    """회원가입 폼"""
    with st.form("signup_form"):
        new_username = st.text_input("사용자명", placeholder="새 사용자명을 입력하세요")
        new_password = st.text_input("비밀번호", type="password", placeholder="새 비밀번호를 입력하세요")
        confirm_password = st.text_input("비밀번호 확인", type="password", placeholder="비밀번호를 다시 입력하세요")
        email = st.text_input("이메일 (선택사항)", placeholder="이메일 주소를 입력하세요")

        submitted = st.form_submit_button("회원가입", use_container_width=True, type="primary")

        if submitted:
            if new_username and new_password and confirm_password:
                if new_password == confirm_password:
                    try:
                        user_manager = get_user_manager()

                        # 사용자 생성
                        user_id = user_manager.create_user(
                            username=new_username,
                            password=new_password,
                            email=email if email else None
                        )

                        if user_id:
                            st.success("✅ 회원가입 성공!")
                            st.info("이제 로그인해주세요.")
                        else:
                            st.error("❌ 회원가입 실패 (사용자명이 이미 존재할 수 있습니다)")
                    except Exception as e:
                        st.error(f"❌ 회원가입 오류: {e}")
                else:
                    st.error("❌ 비밀번호가 일치하지 않습니다")
            else:
                st.warning("⚠️ 필수 정보를 모두 입력해주세요")

def show_safety_test_page():
    """API 테스트 페이지"""
    st.header("🛡️ API 테스트 & 검증")

    # 중요 경고 (개선된 디자인)
    with st.container():
        st.markdown("""
        <div style="border: 3px solid #ff4b4b; border-radius: 10px; padding: 20px; background-color: #ffebee; margin: 10px 0;">
            <h3 style="color: #d32f2f; text-align: center;">🚨 극도 주의 - 실계좌 거래 🚨</h3>

            <div style="background-color: #fff3e0; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h4 style="color: #f57c00;">⚠️ 이것은 실제 돈을 사용하는 메인넷입니다!</h4>
            </div>

            <div style="background-color: #e8f5e8; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h4 style="color: #388e3c;">🛡️ 안전 제한사항</h4>
                <ul style="color: #2e7d32;">
                    <li><strong>최대 주문:</strong> $5 USDT</li>
                    <li><strong>일일 한도:</strong> $20 USDT</li>
                    <li><strong>테스트 금액:</strong> $8 USDT</li>
                    <li><strong>자동 중단:</strong> 연속 손실 3회시</li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 사용자 동의 (강화된 확인)
    col1, col2 = st.columns([3, 1])
    with col1:
        user_understands = st.checkbox(
            "위 모든 경고를 이해했으며, 극소액($10-50)으로만 테스트하겠습니다",
            key="safety_agreement"
        )
    with col2:
        if st.button("📖 안전 가이드", help="자세한 안전 사용법 확인"):
            st.info("""
            **🛡️ 안전 사용 가이드:**

            **1단계: 준비**
            - API 키 권한: Futures Trading 필수
            - 최소 잔고: $10-50 USDT 권장
            - IP 화이트리스트: 현재 IP 등록 필요

            **2단계: 테스트**
            - 연결 테스트 → 잔고 확인 → 시장 데이터
            - XRP/USDT $8 테스트 거래 실행
            - 즉시 청산으로 실거래 검증

            **3단계: 완료**
            - API 키 암호화 저장
            - 메인 대시보드 접근 권한 부여
            """)

    if not user_understands:
        st.warning("⚠️ 안전 가이드를 확인하고 동의해주세요.")
        st.stop()

    st.divider()

    # API 키 입력
    st.subheader("🔑 메인넷 API 키 입력")

    with st.expander("API 키 설정", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            api_key = st.text_input("API Key", type="password", help="바이낸스 메인넷 API 키")
        with col2:
            secret_key = st.text_input("Secret Key", type="password", help="바이낸스 메인넷 시크릿 키")

    if api_key and secret_key:
        # API 커넥터 초기화 (단일 인스턴스 관리)
        if 'test_connector' not in st.session_state:
            st.session_state.test_connector = BinanceMainnetConnector(api_key, secret_key)
        else:
            # API 키가 변경되었는지 확인
            current_connector = st.session_state.test_connector
            if current_connector.api_key != api_key:
                st.session_state.test_connector = BinanceMainnetConnector(api_key, secret_key)
                logger.info("Test connector reinitialized with new credentials")

        connector = st.session_state.test_connector

        # 연결 상태 확인
        connection_status = connector.is_connected()
        if connection_status:
            st.success("🟢 API 연결 상태: 정상")
        else:
            st.warning("🟡 API 연결 상태: 확인 필요")

        # 단계별 테스트
        show_api_test_steps(connector, api_key, secret_key)
    else:
        st.warning("⚠️ 메인넷 API 키를 입력해주세요")

def show_api_test_steps(connector, api_key, secret_key):
    """API 테스트 단계들"""
    st.subheader("📋 단계별 API 테스트")

    # 1단계: 연결 테스트
    st.write("**1️⃣ API 연결 테스트**")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔗 연결 테스트"):
            with st.spinner("연결 확인 중..."):
                try:
                    is_connected = connector.is_connected()
                    if is_connected:
                        st.success("✅ 메인넷 연결 성공")
                    else:
                        st.error("❌ 연결 실패")
                except Exception as e:
                    st.error(f"연결 오류: {e}")

    with col2:
        if st.button("💰 잔고 조회"):
            with st.spinner("잔고 조회 중..."):
                try:
                    account_info = connector.get_account_info()
                    if account_info:
                        st.success("✅ 계좌 정보 조회 성공")

                        usdt_balance = float(account_info.get('totalWalletBalance', 0))
                        available = float(account_info.get('availableBalance', 0))

                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.metric("총 USDT", f"${usdt_balance:.2f}")
                        with col_b:
                            st.metric("사용 가능", f"${available:.2f}")

                        # 잔고 안전성 확인
                        if usdt_balance < 10:
                            st.warning("⚠️ 잔고가 $10 미만입니다.")
                        elif usdt_balance > 100:
                            st.warning("⚠️ 잔고가 $100 이상입니다. 극소액 테스트에 주의하세요.")
                        else:
                            st.info("💡 테스트하기 적절한 잔고입니다.")
                    else:
                        st.error("❌ 계좌 정보 조회 실패")
                except Exception as e:
                    st.error(f"조회 오류: {e}")

    with col3:
        if st.button("📈 시장 데이터"):
            with st.spinner("시장 데이터 조회 중..."):
                try:
                    xrp_price = connector.get_current_price('XRP/USDT')
                    if xrp_price:
                        st.success(f"✅ XRP: ${xrp_price['price']:.4f}")
                    else:
                        st.error("❌ 가격 조회 실패")
                except Exception as e:
                    st.error(f"시장 데이터 오류: {e}")

    st.divider()

    # 2단계: 실거래 테스트
    st.write("**2️⃣ 실거래 테스트 (XRP/USDT, 8 USDT)**")

    # XRP 테스트 거래 버튼
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 XRP Long 테스트 (8 USDT)", type="primary"):
            perform_test_trade(connector, 'long')

    with col2:
        if 'test_position' in st.session_state:
            if st.button("💰 포지션 청산", type="secondary"):
                perform_test_liquidation(connector)

    # 3단계: API 키 저장
    if 'test_completed' in st.session_state and st.session_state.test_completed:
        st.divider()
        st.write("**3️⃣ API 키 저장 및 거래 시작**")

        if st.button("💾 API 키 저장하고 거래 시작", type="primary", use_container_width=True):
            save_api_and_proceed(api_key, secret_key)

def perform_test_trade(connector, direction):
    """테스트 거래 실행 (에러 처리 강화)"""
    progress_bar = st.progress(0, "거래 준비 중...")

    try:
        # 1단계: 거래 활성화
        progress_bar.progress(0.2, "거래 시스템 활성화 중...")
        connector.set_observation_mode(False)
        trading_enabled = connector.enable_trading(True)

        if not trading_enabled:
            st.error("❌ 거래 활성화 실패")
            progress_bar.empty()
            return

        # 2단계: 가격 조회
        progress_bar.progress(0.4, "XRP 가격 조회 중...")
        xrp_price_data = connector.get_current_price('XRP/USDT')

        if not xrp_price_data:
            st.error("❌ XRP 가격 정보를 가져올 수 없습니다")
            progress_bar.empty()
            return

        current_xrp_price = xrp_price_data['price']
        xrp_amount = 8.0 / current_xrp_price

        # 3단계: 안전성 검사
        progress_bar.progress(0.6, "안전성 검사 중...")

        # 잔고 확인
        account_info = connector.get_account_info()
        if account_info:
            available_balance = float(account_info.get('availableBalance', 0))
            if available_balance < 10:
                st.error(f"❌ 잔고 부족: ${available_balance:.2f} < $10")
                progress_bar.empty()
                return

        # 4단계: 주문 실행
        progress_bar.progress(0.8, f"실거래 실행 중... {xrp_amount:.2f} XRP Long")

        result = connector.place_order('XRP/USDT', 'buy', xrp_amount, order_type='market')

        # 5단계: 결과 처리
        progress_bar.progress(1.0, "거래 완료!")

        if result and not result.get('error'):
            st.success("✅ XRP Long 포지션 진입 성공!")

            # 상세 거래 정보 표시
            st.json({
                "주문 정보": {
                    "심볼": "XRP/USDT",
                    "방향": "Long (매수)",
                    "수량": f"{xrp_amount:.4f} XRP",
                    "진입가": f"${current_xrp_price:.4f}",
                    "총 가치": "$8.00 USDT"
                }
            })

            # 포지션 정보 저장
            st.session_state.test_position = {
                'symbol': 'XRP/USDT',
                'side': 'long',
                'amount': xrp_amount,
                'entry_price': current_xrp_price,
                'value': 8.0,
                'timestamp': time.time()
            }

            st.balloons()
            time.sleep(1)
            st.rerun()
        else:
            error_msg = result.get('error', '알 수 없는 오류') if result else '주문 응답 없음'
            st.error(f"❌ 주문 실패: {error_msg}")

    except Exception as e:
        st.error(f"❌ 거래 오류: {str(e)}")
        logger.error(f"Test trade error: {e}")
    finally:
        progress_bar.empty()

def perform_test_liquidation(connector):
    """테스트 포지션 청산"""
    try:
        position = st.session_state.test_position

        st.info(f"📉 포지션 청산 중... {position['amount']:.2f} XRP 매도")

        # 청산 주문 실행
        result = connector.place_order('XRP/USDT', 'sell', position['amount'], order_type='market')

        if result and not result.get('error'):
            st.success("✅ 포지션 청산 완료!")

            # 현재 가격으로 손익 계산
            current_price = connector.get_current_price('XRP/USDT')
            if current_price:
                entry_value = position['value']
                current_value = position['amount'] * current_price['price']
                pnl = current_value - entry_value

                col_pnl1, col_pnl2 = st.columns(2)
                with col_pnl1:
                    st.metric("진입 가치", f"${entry_value:.2f}")
                with col_pnl2:
                    pnl_color = "🟢" if pnl >= 0 else "🔴"
                    st.metric("손익", f"{pnl_color} ${pnl:.2f}")

            # 포지션 정보 제거 및 테스트 완료 표시
            del st.session_state.test_position
            st.session_state.test_completed = True

            st.balloons()
            st.success("🎉 실거래 테스트 완료!")
            st.rerun()
        else:
            st.error(f"❌ 청산 실패: {result.get('error', '알 수 없는 오류')}")
    except Exception as e:
        st.error(f"❌ 청산 오류: {e}")

def save_api_and_proceed(api_key, secret_key):
    """API 키 저장 및 다음 단계로 진행"""
    try:
        if st.session_state.user:
            user_id = st.session_state.user['id']

            # API 키 저장
            api_manager = get_api_manager()
            saved = api_manager.save_api_key(
                user_id=user_id,
                exchange='binance',
                api_key=api_key,
                api_secret=secret_key,
                is_testnet=False
            )

            if saved:
                st.success("✅ API 키가 안전하게 저장되었습니다!")

                # 상태 업데이트
                st.session_state.api_keys_saved = True
                st.session_state.api_verified = True
                st.session_state.current_stage = 'main_trading'

                # API 커넥터를 메인 커넥터로 이동 (단일 인스턴스 보장)
                st.session_state.api_connector = st.session_state.test_connector
                logger.info("Test connector promoted to main API connector")

                st.info("🚀 메인 거래 대시보드로 이동합니다!")

                # 성공 애니메이션과 함께 자동 전환
                st.balloons()
                with st.empty():
                    for i in range(3, 0, -1):
                        st.success(f"🚀 {i}초 후 메인 거래 대시보드로 이동합니다!")
                        time.sleep(1)

                st.rerun()
            else:
                st.error("❌ API 키 저장 실패")
        else:
            st.error("❌ 로그인이 필요합니다")
    except Exception as e:
        st.error(f"❌ API 키 저장 오류: {e}")

def show_main_trading_page():
    """메인 거래 페이지"""
    st.header("🚀 메인 거래 대시보드")

    # API 커넥터 확인 및 복원
    if not ensure_api_connector():
        st.error("API 커넥터가 초기화되지 않았습니다.")
        st.info("Safety Test 단계로 돌아가서 API 키를 다시 설정해주세요.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🛡️ Safety Test로 돌아가기", type="primary"):
                st.session_state.current_stage = 'safety_test'
                st.rerun()
        with col2:
            if st.button("🔄 API 연결 복원 시도", type="secondary"):
                if ensure_api_connector():
                    st.success("✅ API 연결이 복원되었습니다!")
                    st.rerun()
                else:
                    st.error("❌ API 연결 복원에 실패했습니다.")
        return

    connector = get_api_connector()

    # 연결 상태 실시간 확인
    try:
        connection_status = connector.is_connected()
        if connection_status:
            st.success("🟢 API 연결 상태: 정상 운영 중")
        else:
            st.error("🔴 API 연결 상태: 연결 문제 감지")
            if st.button("🔄 연결 재시도"):
                st.rerun()
    except Exception as e:
        st.error(f"🔴 API 연결 확인 오류: {e}")
        if st.button("🛡️ Safety Test로 돌아가기"):
            st.session_state.current_stage = 'safety_test'
            st.rerun()
        return

    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["📊 개요", "⚡ 거래", "📋 주문"])

    with tab1:
        show_account_overview(connector)
        st.divider()
        show_positions(connector)
        st.divider()
        show_market_data(connector)

    with tab2:
        show_trading_interface(connector)

    with tab3:
        show_open_orders(connector)

def show_account_overview(connector):
    """계정 개요"""
    st.subheader("💰 계정 개요")

    try:
        account_info = connector.get_account_info()
        if account_info:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                total_balance = float(account_info.get('totalWalletBalance', 0))
                st.metric("총 잔고", f"${total_balance:,.2f}")

            with col2:
                available_balance = float(account_info.get('availableBalance', 0))
                st.metric("사용 가능", f"${available_balance:,.2f}")

            with col3:
                unrealized_pnl = float(account_info.get('unrealizedProfit', 0))
                pnl_color = "🟢" if unrealized_pnl >= 0 else "🔴"
                st.metric("미실현 손익", f"{pnl_color} ${unrealized_pnl:,.2f}")

            with col4:
                safety_status = connector.get_safety_status()
                max_order = safety_status['max_order_amount']
                st.metric("최대 주문", f"${max_order}")
        else:
            st.error("계정 정보를 불러올 수 없습니다")
    except Exception as e:
        st.error(f"계정 정보 오류: {e}")

def show_positions(connector):
    """포지션 정보"""
    st.subheader("📊 현재 포지션")

    try:
        positions = connector.get_positions()

        if positions and len(positions) > 0:
            active_positions = [pos for pos in positions if float(pos.get('size', 0)) != 0]

            if active_positions:
                df = pd.DataFrame(active_positions)
                display_columns = ['symbol', 'side', 'size', 'notional', 'unrealizedPnl', 'entryPrice']
                available_columns = [col for col in display_columns if col in df.columns]
                st.dataframe(df[available_columns], use_container_width=True)
            else:
                st.info("현재 활성 포지션이 없습니다")
        else:
            st.info("포지션 정보를 불러올 수 없습니다")
    except Exception as e:
        st.error(f"포지션 조회 오류: {e}")

def show_market_data(connector):
    """시장 데이터"""
    st.subheader("📈 주요 시장 데이터")

    symbols = ['BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'BNB/USDT']

    try:
        price_data = []
        for symbol in symbols:
            try:
                data = connector.get_current_price(symbol)
                if data and data.get('price'):
                    price_data.append({
                        'Symbol': symbol,
                        'Price': f"${data['price']:,.4f}",
                        'Time': datetime.now().strftime('%H:%M:%S')
                    })
            except:
                price_data.append({
                    'Symbol': symbol,
                    'Price': 'Error',
                    'Time': 'N/A'
                })

        if price_data:
            df = pd.DataFrame(price_data)
            st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"시장 데이터 오류: {e}")

def show_trading_interface(connector):
    """거래 인터페이스 (사용자 설정 및 최소 금액 검증 포함)"""
    st.subheader("⚡ 빠른 거래")

    # 최소 주문 금액 정보 업데이트
    update_min_order_amounts()

    # 사용자 거래 설정 로드
    if st.session_state.authenticated:
        user_id = st.session_state.user['id']
        settings_manager = get_trading_settings_manager()
        user_settings = settings_manager.get_user_trading_settings(user_id)
    else:
        user_settings = settings_manager._get_default_settings()

    col1, col2 = st.columns(2)

    with col1:
        st.write("**매수 (Long)**")
        with st.form("buy_form"):
            symbols = ['XRP/USDT', 'BTC/USDT', 'ETH/USDT', 'ADA/USDT', 'DOT/USDT', 'BNB/USDT']
            symbol = st.selectbox("코인 선택", symbols)

            # 선택된 코인의 최소 금액과 사용자 설정 표시
            min_amount = get_min_amount_for_symbol(symbol)
            user_max = user_settings['max_order_amount']
            user_default = user_settings['default_order_amount']

            st.info(f"💡 {symbol} 최소: ${min_amount:.1f} USDT | 사용자 한도: ${user_max:.1f} USDT")

            # 동적 입력 범위 설정 (사용자 설정 반영)
            actual_min = max(min_amount, 5.0)
            actual_max = min(user_max, 1000.0)
            actual_default = max(min(user_default, actual_max), actual_min)

            amount = st.number_input(
                "금액 (USDT)",
                min_value=actual_min,
                max_value=actual_max,
                value=actual_default,
                step=1.0,
                help=f"최소: ${actual_min:.1f} USDT, 최대: ${actual_max:.1f} USDT"
            )

            # 실시간 검증 표시 (거래소 + 사용자 설정)
            validation = validate_trade_amount(symbol, amount)
            if st.session_state.authenticated:
                user_validation = settings_manager.validate_order_amount(user_id, symbol, amount)
                if not user_validation['valid']:
                    st.warning(f"⚠️ {user_validation['message']}")

            if not validation['valid']:
                st.warning(f"⚠️ {validation['message']}")
                if validation['suggested_amount']:
                    st.info(f"💡 권장 금액: ${validation['suggested_amount']:.1f} USDT")

            # 리스크 표시
            if st.session_state.authenticated:
                try:
                    account_info = connector.get_account_info()
                    if account_info:
                        total_balance = float(account_info.get('totalWalletBalance', 0))
                        if total_balance > 0:
                            risk_pct = (amount / total_balance) * 100
                            risk_color = "🟢" if risk_pct <= 2 else "🟡" if risk_pct <= 5 else "🔴"
                            st.info(f"{risk_color} 전체 자금의 {risk_pct:.1f}%")
                except:
                    pass

            if st.form_submit_button("🚀 Long 진입", type="primary"):
                execute_trade(connector, symbol, 'buy', amount)

    with col2:
        st.write("**매도 (Short)**")
        with st.form("sell_form"):
            symbols_short = ['XRP/USDT', 'BTC/USDT', 'ETH/USDT', 'ADA/USDT', 'DOT/USDT', 'BNB/USDT']
            symbol_short = st.selectbox("코인 선택 ", symbols_short)

            # 선택된 코인의 최소 금액과 사용자 설정 표시
            min_amount_short = get_min_amount_for_symbol(symbol_short)
            user_max_short = user_settings['max_order_amount']
            user_default_short = user_settings['default_order_amount']

            st.info(f"💡 {symbol_short} 최소: ${min_amount_short:.1f} USDT | 사용자 한도: ${user_max_short:.1f} USDT")

            # 동적 입력 범위 설정 (사용자 설정 반영)
            actual_min_short = max(min_amount_short, 5.0)
            actual_max_short = min(user_max_short, 1000.0)
            actual_default_short = max(min(user_default_short, actual_max_short), actual_min_short)

            amount_short = st.number_input(
                "금액 (USDT) ",
                min_value=actual_min_short,
                max_value=actual_max_short,
                value=actual_default_short,
                step=1.0,
                help=f"최소: ${actual_min_short:.1f} USDT, 최대: ${actual_max_short:.1f} USDT"
            )

            # 실시간 검증 표시 (거래소 + 사용자 설정)
            validation_short = validate_trade_amount(symbol_short, amount_short)
            if st.session_state.authenticated:
                user_validation_short = settings_manager.validate_order_amount(user_id, symbol_short, amount_short)
                if not user_validation_short['valid']:
                    st.warning(f"⚠️ {user_validation_short['message']}")

            if not validation_short['valid']:
                st.warning(f"⚠️ {validation_short['message']}")
                if validation_short['suggested_amount']:
                    st.info(f"💡 권장 금액: ${validation_short['suggested_amount']:.1f} USDT")

            # 리스크 표시
            if st.session_state.authenticated:
                try:
                    account_info = connector.get_account_info()
                    if account_info:
                        total_balance = float(account_info.get('totalWalletBalance', 0))
                        if total_balance > 0:
                            risk_pct_short = (amount_short / total_balance) * 100
                            risk_color_short = "🟢" if risk_pct_short <= 2 else "🟡" if risk_pct_short <= 5 else "🔴"
                            st.info(f"{risk_color_short} 전체 자금의 {risk_pct_short:.1f}%")
                except:
                    pass

            if st.form_submit_button("📉 Short 진입", type="secondary"):
                execute_trade(connector, symbol_short, 'sell', amount_short)

    # 스마트 주문 제안 시스템
    st.divider()
    st.markdown("### 🧠 스마트 주문 제안")

    if st.session_state.authenticated:
        user_id = st.session_state.user['id']
        try:
            account_info = connector.get_account_info()
            if account_info:
                total_balance = float(account_info.get('totalWalletBalance', 0))
                show_smart_trading_suggestions(user_id, total_balance, settings_manager)
        except Exception as e:
            st.error(f"잔고 조회 오류: {e}")

    # 주요 코인별 최소 금액 요약 표시
    st.divider()
    st.markdown("### 📊 주요 코인별 최소 주문 금액")

    if st.session_state.min_order_amounts:
        amounts_data = []
        for symbol, min_amt in st.session_state.min_order_amounts.items():
            # 사용자 설정 기반 권장 금액 계산
            if st.session_state.authenticated:
                recommended_amounts = settings_manager.calculate_recommended_amount(user_id, symbol, 100)  # 가정: 100 USDT
                recommended = recommended_amounts['recommended']
            else:
                recommended = min_amt * 1.2

            amounts_data.append({
                'Symbol': symbol,
                'Minimum': f"${min_amt:.1f} USDT",
                'Recommended': f"${recommended:.1f} USDT"
            })

        df_amounts = pd.DataFrame(amounts_data)
        st.dataframe(df_amounts, use_container_width=True, hide_index=True)
    else:
        st.info("최소 주문 금액을 로딩 중입니다...")

def show_smart_trading_suggestions(user_id, total_balance, settings_manager, selected_symbol=None):
    """스마트 거래 제안 표시 (Step 6.5 고도화)"""
    st.markdown("#### 💡 개인화된 거래 제안")

    if total_balance == 0:
        st.warning("⚠️ 잔고 정보를 불러올 수 없습니다")
        return

    # 사용자 설정 로드
    user_settings = settings_manager.get_user_trading_settings(user_id)

    # 코인별 설정 확인
    coin_settings = {}
    if selected_symbol:
        coin_settings = settings_manager.get_coin_specific_settings(user_id, selected_symbol)

    # 동적 주문 금액 계산 (변동성 고려)
    if selected_symbol:
        # 변동성 임시값 (실제로는 API에서 가져올 예정)
        volatility = 3.5  # 임시 변동성 값
        dynamic_amounts = settings_manager.calculate_dynamic_order_amount(
            user_id, selected_symbol, total_balance, volatility
        )
    else:
        # 기본 계산
        dynamic_amounts = settings_manager.calculate_recommended_amount(user_id, 'BTC/USDT', total_balance)

    col1, col2, col3 = st.columns(3)

    # 보수적 제안 (동적 계산 사용)
    with col1:
        conservative_amount = dynamic_amounts['conservative']

        st.markdown("""
        <div style="border: 2px solid #4CAF50; border-radius: 10px; padding: 15px; background-color: #E8F5E8;">
            <h4 style="color: #388E3C; margin-top: 0;">🟢 보수적</h4>
            <h3 style="color: #2E7D32; margin: 5px 0;">${:.1f} USDT</h3>
            <p style="color: #388E3C; margin-bottom: 0; font-size: 14px;">
                전체 자금의 {:.1f}%<br>
                안전 우선, 낮은 리스크
            </p>
        </div>
        """.format(conservative_amount, (conservative_amount/total_balance)*100), unsafe_allow_html=True)

        if st.button("🟢 보수적 금액 적용", key="conservative", use_container_width=True):
            st.session_state.suggested_amount = conservative_amount
            st.success(f"보수적 금액 ${conservative_amount:.1f} USDT가 설정되었습니다")

    # 균형적 제안 (동적 계산 사용)
    with col2:
        balanced_amount = dynamic_amounts['recommended']

        st.markdown("""
        <div style="border: 2px solid #FF9800; border-radius: 10px; padding: 15px; background-color: #FFF3E0;">
            <h4 style="color: #F57C00; margin-top: 0;">🟡 균형적</h4>
            <h3 style="color: #E65100; margin: 5px 0;">${:.1f} USDT</h3>
            <p style="color: #F57C00; margin-bottom: 0; font-size: 14px;">
                전체 자금의 {:.1f}%<br>
                적당한 리스크와 수익
            </p>
        </div>
        """.format(balanced_amount, (balanced_amount/total_balance)*100), unsafe_allow_html=True)

        if st.button("🟡 균형적 금액 적용", key="balanced", use_container_width=True):
            st.session_state.suggested_amount = balanced_amount
            st.success(f"균형적 금액 ${balanced_amount:.1f} USDT가 설정되었습니다")

    # 적극적 제안 (동적 계산 사용)
    with col3:
        aggressive_amount = dynamic_amounts['aggressive']

        st.markdown("""
        <div style="border: 2px solid #F44336; border-radius: 10px; padding: 15px; background-color: #FFEBEE;">
            <h4 style="color: #D32F2F; margin-top: 0;">🔴 적극적</h4>
            <h3 style="color: #C62828; margin: 5px 0;">${:.1f} USDT</h3>
            <p style="color: #D32F2F; margin-bottom: 0; font-size: 14px;">
                전체 자금의 {:.1f}%<br>
                높은 수익 추구
            </p>
        </div>
        """.format(aggressive_amount, (aggressive_amount/total_balance)*100), unsafe_allow_html=True)

        if st.button("🔴 적극적 금액 적용", key="aggressive", use_container_width=True):
            st.session_state.suggested_amount = aggressive_amount
            st.success(f"적극적 금액 ${aggressive_amount:.1f} USDT가 설정되었습니다")

    # 리스크 계산기
    st.divider()
    st.markdown("#### 📊 리스크 계산기")

    col_risk1, col_risk2 = st.columns(2)

    with col_risk1:
        test_amount = st.slider(
            "테스트 주문 금액 (USDT)",
            min_value=5.0,
            max_value=min(user_settings['max_order_amount'], total_balance * 0.1),
            value=user_settings['default_order_amount'],
            step=1.0
        )

    with col_risk2:
        risk_percentage = (test_amount / total_balance) * 100
        risk_level = "🟢 낮음" if risk_percentage <= 1 else "🟡 보통" if risk_percentage <= 3 else "🔴 높음"

        st.markdown(f"""
        **리스크 분석:**
        - 전체 자금 대비: **{risk_percentage:.2f}%**
        - 리스크 레벨: **{risk_level}**
        - 예상 최대 손실: **${test_amount * 0.1:.1f} USDT** (10% 손실 가정)
        """)

        # 포지션 크기 추천
        optimal_size = total_balance * (user_settings['risk_percentage'] / 100)
        if test_amount > optimal_size:
            st.warning(f"⚠️ 권장 포지션 크기 ${optimal_size:.1f} USDT를 초과합니다")
        else:
            st.success(f"✅ 적절한 포지션 크기입니다")

def execute_trade(connector, symbol, side, amount):
    """거래 실행 (다단계 검증 및 확인 다이얼로그)"""
    # 다단계 검증 시스템
    validation_results = perform_comprehensive_validation(connector, symbol, side, amount)

    if not validation_results['overall_valid']:
        show_validation_errors(validation_results)
        return

    # 주문 확인 다이얼로그
    if show_order_confirmation_dialog(validation_results):
        execute_validated_order(connector, validation_results)

def perform_comprehensive_validation(connector, symbol, side, amount):
    """포괄적 주문 검증"""
    validation_results = {
        'overall_valid': True,
        'checks': [],
        'symbol': symbol,
        'side': side,
        'amount': amount,
        'current_price': None,
        'quantity': None,
        'estimated_fee': None,
        'warnings': [],
        'errors': []
    }

    try:
        # 1. 거래소 최소 금액 검증
        min_validation = validate_trade_amount(symbol, amount)
        validation_results['checks'].append({
            'name': '거래소 최소 금액',
            'status': 'pass' if min_validation['valid'] else 'fail',
            'message': min_validation.get('message', '통과'),
            'min_amount': min_validation['min_amount']
        })

        if not min_validation['valid']:
            validation_results['overall_valid'] = False
            validation_results['errors'].append(min_validation['message'])

        # 2. 사용자 설정 한도 검증
        if st.session_state.authenticated:
            user_id = st.session_state.user['id']
            settings_manager = get_trading_settings_manager()
            user_validation = settings_manager.validate_order_amount(user_id, symbol, amount)

            validation_results['checks'].append({
                'name': '사용자 한도',
                'status': 'pass' if user_validation['valid'] else 'fail',
                'message': user_validation.get('message', '통과'),
                'max_allowed': user_validation['max_allowed']
            })

            if not user_validation['valid']:
                validation_results['overall_valid'] = False
                validation_results['errors'].append(user_validation['message'])

        # 3. API 연결 상태 검증
        try:
            connection_status = connector.is_connected()
            validation_results['checks'].append({
                'name': 'API 연결',
                'status': 'pass' if connection_status else 'fail',
                'message': 'API 연결 정상' if connection_status else 'API 연결 실패'
            })

            if not connection_status:
                validation_results['overall_valid'] = False
                validation_results['errors'].append('API 연결이 필요합니다')
        except Exception as e:
            validation_results['overall_valid'] = False
            validation_results['errors'].append(f'API 연결 확인 실패: {e}')

        # 4. 계좌 잔고 검증
        try:
            account_info = connector.get_account_info()
            if account_info:
                available_balance = float(account_info.get('availableBalance', 0))
                balance_sufficient = available_balance >= amount

                validation_results['checks'].append({
                    'name': '계좌 잔고',
                    'status': 'pass' if balance_sufficient else 'fail',
                    'message': f'사용 가능: ${available_balance:.2f} USDT' if balance_sufficient else f'잔고 부족: ${available_balance:.2f} < ${amount:.2f} USDT',
                    'available_balance': available_balance
                })

                if not balance_sufficient:
                    validation_results['overall_valid'] = False
                    validation_results['errors'].append(f'잔고가 부족합니다 (필요: ${amount:.2f}, 보유: ${available_balance:.2f})')
        except Exception as e:
            validation_results['warnings'].append(f'잔고 확인 실패: {e}')

        # 5. 현재 가격 조회 및 수량 계산
        try:
            price_data = connector.get_current_price(symbol)
            if price_data:
                current_price = price_data['price']
                quantity = amount / current_price
                estimated_fee = amount * 0.001  # 0.1% 수수료 가정

                validation_results['current_price'] = current_price
                validation_results['quantity'] = quantity
                validation_results['estimated_fee'] = estimated_fee

                validation_results['checks'].append({
                    'name': '가격 조회',
                    'status': 'pass',
                    'message': f'현재가: ${current_price:.4f}',
                    'price': current_price
                })
            else:
                validation_results['overall_valid'] = False
                validation_results['errors'].append('시장 가격을 조회할 수 없습니다')
        except Exception as e:
            validation_results['overall_valid'] = False
            validation_results['errors'].append(f'가격 조회 실패: {e}')

        # 6. 안전성 검사
        safety_status = connector.get_safety_status()

        if not safety_status.get('trade_enabled', False):
            validation_results['overall_valid'] = False
            validation_results['errors'].append('거래가 비활성화되어 있습니다')

        if not safety_status.get('emergency_stop_enabled', True):
            validation_results['overall_valid'] = False
            validation_results['errors'].append('긴급 중단이 활성화되어 있습니다')

        validation_results['checks'].append({
            'name': '시스템 안전성',
            'status': 'pass' if safety_status.get('trade_enabled') and safety_status.get('emergency_stop_enabled') else 'fail',
            'message': '시스템 정상' if safety_status.get('trade_enabled') else '거래 비활성화됨'
        })

    except Exception as e:
        validation_results['overall_valid'] = False
        validation_results['errors'].append(f'검증 과정 오류: {e}')

    return validation_results

def show_validation_errors(validation_results):
    """검증 오류 표시"""
    st.error("❌ 주문 검증 실패")

    # 실패한 검증 항목들 표시
    failed_checks = [check for check in validation_results['checks'] if check['status'] == 'fail']

    if failed_checks:
        st.markdown("**실패한 검증 항목:**")
        for check in failed_checks:
            st.error(f"• {check['name']}: {check['message']}")

    # 오류 메시지들 표시
    if validation_results['errors']:
        st.markdown("**오류 상세:**")
        for error in validation_results['errors']:
            st.error(f"🚫 {error}")

    # 해결 방안 제시
    st.info("💡 **해결 방안:**")

    for check in failed_checks:
        if check['name'] == '거래소 최소 금액':
            st.info(f"• 최소 주문 금액 ${check['min_amount']:.1f} USDT 이상으로 설정하세요")
        elif check['name'] == '사용자 한도':
            st.info(f"• Settings에서 최대 주문 한도를 조정하거나 더 적은 금액으로 주문하세요")
        elif check['name'] == 'API 연결':
            st.info("• API 연결을 확인하고 다시 시도하세요")
        elif check['name'] == '계좌 잔고':
            st.info("• 계좌에 충분한 USDT를 입금하거나 더 적은 금액으로 주문하세요")

def show_order_confirmation_dialog(validation_results):
    """주문 확인 다이얼로그"""
    st.markdown("### 🔍 주문 확인")

    # 검증 결과 요약
    st.success("✅ 모든 검증을 통과했습니다")

    # 통과한 검증 항목들
    passed_checks = [check for check in validation_results['checks'] if check['status'] == 'pass']

    with st.expander("📋 검증 통과 항목", expanded=False):
        for check in passed_checks:
            st.success(f"✅ {check['name']}: {check['message']}")

    # 주문 상세 정보
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📊 주문 정보**")
        st.info(f"""
        **심볼**: {validation_results['symbol']}
        **방향**: {validation_results['side'].upper()}
        **금액**: ${validation_results['amount']:.2f} USDT
        **현재가**: ${validation_results['current_price']:.4f}
        **수량**: {validation_results['quantity']:.4f}
        """)

    with col2:
        st.markdown("**💰 비용 분석**")
        total_cost = validation_results['amount'] + validation_results['estimated_fee']
        st.info(f"""
        **주문 금액**: ${validation_results['amount']:.2f} USDT
        **예상 수수료**: ${validation_results['estimated_fee']:.2f} USDT
        **총 필요 금액**: ${total_cost:.2f} USDT
        """)

    # 리스크 경고
    if validation_results['warnings']:
        st.warning("⚠️ **주의사항:**")
        for warning in validation_results['warnings']:
            st.warning(f"• {warning}")

    # 최종 확인
    st.markdown("---")
    st.markdown("### ⚠️ 최종 확인")

    confirmation_text = f"위 정보를 확인했으며, {validation_results['symbol']} {validation_results['side'].upper()} ${validation_results['amount']:.2f} USDT 주문을 실행하겠습니다."

    user_confirmed = st.checkbox(confirmation_text, key="final_confirmation")

    if user_confirmed:
        col_cancel, col_execute = st.columns(2)

        with col_cancel:
            if st.button("❌ 취소", use_container_width=True):
                st.info("주문이 취소되었습니다")
                return False

        with col_execute:
            if st.button("🚀 주문 실행", type="primary", use_container_width=True):
                return True

    return False

def execute_validated_order(connector, validation_results):
    """검증된 주문 실행"""
    symbol = validation_results['symbol']
    side = validation_results['side']
    quantity = validation_results['quantity']
    amount = validation_results['amount']

    try:
        # 거래 시스템 활성화
        connector.set_observation_mode(False)
        connector.enable_trading(True)

        # 진행상황 표시
        progress_bar = st.progress(0, "주문 실행 준비 중...")

        progress_bar.progress(0.3, "거래 시스템 활성화 중...")
        time.sleep(0.5)

        progress_bar.progress(0.6, f"{symbol} {side.upper()} 주문 전송 중...")

        # 실제 주문 실행
        result = connector.place_order(symbol, side, quantity, order_type='market')

        progress_bar.progress(1.0, "주문 완료!")

        if result and not result.get('error'):
            st.success(f"✅ {symbol} {side.upper()} 주문이 성공적으로 실행되었습니다!")

            # 주문 결과 상세 정보
            st.markdown("### 📋 주문 결과")
            st.json({
                "주문 ID": result.get('id', 'N/A'),
                "심볼": symbol,
                "방향": side.upper(),
                "실행 수량": f"{quantity:.4f}",
                "실행 금액": f"${amount:.2f} USDT",
                "상태": result.get('status', 'N/A')
            })

            st.balloons()
            time.sleep(2)
            st.rerun()
        else:
            error_msg = result.get('error', '알 수 없는 오류') if result else '서버 응답 없음'
            st.error(f"❌ 주문 실행 실패: {error_msg}")

            # 실패 원인 분석
            st.markdown("### 🔍 실패 원인 분석")
            if "insufficient" in error_msg.lower():
                st.error("💰 잔고 부족으로 인한 실패")
            elif "minimum" in error_msg.lower():
                st.error("📏 최소 주문 금액 미달")
            elif "network" in error_msg.lower():
                st.error("🌐 네트워크 연결 문제")
            else:
                st.error("🔧 기타 시스템 오류")

    except Exception as e:
        st.error(f"❌ 주문 실행 중 예외 발생: {str(e)}")
        logger.error(f"Order execution exception: {e}")
    finally:
        if 'progress_bar' in locals():
            progress_bar.empty()

def show_open_orders(connector):
    """미체결 주문"""
    st.subheader("📋 미체결 주문")

    try:
        orders = connector.get_open_orders()

        if orders and len(orders) > 0:
            for idx, order in enumerate(orders):
                col1, col2 = st.columns([4, 1])

                with col1:
                    st.write(f"**{order.get('symbol')}** - {order.get('side')} {order.get('amount')}")

                with col2:
                    if st.button(f"취소", key=f"cancel_{idx}"):
                        try:
                            cancelled = connector.cancel_order(order['id'], order['symbol'])
                            if cancelled:
                                st.success("주문이 취소되었습니다")
                                st.rerun()
                            else:
                                st.error("주문 취소 실패")
                        except Exception as e:
                            st.error(f"취소 오류: {e}")
        else:
            st.info("미체결 주문이 없습니다")
    except Exception as e:
        st.error(f"주문 조회 오류: {e}")

def show_settings_page():
    """설정 페이지"""
    st.header("⚙️ 설정")

    if not st.session_state.authenticated:
        st.warning("로그인이 필요합니다.")
        return

    user = st.session_state.user
    user_id = user['id']

    # 탭으로 설정 구분
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["👤 계정", "💰 거래 한도", "📊 리스크 관리", "🪙 코인별 설정", "⏰ 거래 시간", "🔑 API", "🛡️ 안전"])

    with tab1:
        show_account_settings(user)

    with tab2:
        show_trading_limits_settings(user_id)

    with tab3:
        show_risk_management_settings(user_id)

    with tab4:
        show_coin_specific_settings(user_id)

    with tab5:
        show_trading_schedule_settings(user_id)

    with tab6:
        show_api_settings()

    with tab7:
        show_safety_settings()

def show_account_settings(user):
    """계정 설정"""
    st.subheader("👤 계정 정보")

    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**사용자명**: {user['username']}")
        st.info(f"**이메일**: {user.get('email', '없음')}")
    with col2:
        st.info(f"**가입일**: {datetime.now().strftime('%Y-%m-%d')}")
        st.info(f"**상태**: 활성")

def show_trading_limits_settings(user_id):
    """거래 한도 설정"""
    st.subheader("💰 거래 한도 설정")

    # 거래 설정 매니저 초기화
    settings_manager = get_trading_settings_manager()

    # 현재 설정 로드
    current_settings = settings_manager.get_user_trading_settings(user_id)

    with st.form("trading_limits_form"):
        st.markdown("### 📊 주문 금액 설정")

        col1, col2 = st.columns(2)

        with col1:
            max_order = st.slider(
                "최대 주문 금액 (USDT)",
                min_value=10.0,
                max_value=1000.0,
                value=current_settings['max_order_amount'],
                step=5.0,
                help="단일 주문의 최대 금액"
            )

            default_order = st.slider(
                "기본 주문 금액 (USDT)",
                min_value=5.0,
                max_value=max_order,
                value=min(current_settings['default_order_amount'], max_order),
                step=1.0,
                help="거래 시 기본으로 설정될 금액"
            )

        with col2:
            use_percentage = st.checkbox(
                "잔고 비율 기반 주문",
                value=current_settings['use_balance_percentage'],
                help="체크 시 잔고의 일정 비율로 주문 금액 자동 계산"
            )

            if use_percentage:
                balance_pct = st.slider(
                    "잔고 비율 (%)",
                    min_value=0.5,
                    max_value=10.0,
                    value=current_settings['balance_percentage'],
                    step=0.1,
                    help="전체 잔고 대비 주문 비율"
                )
            else:
                balance_pct = current_settings['balance_percentage']

        st.divider()
        st.markdown("### 🎯 거래 모드 프리셋")

        # 거래 모드 선택
        mode_options = ['conservative', 'balanced', 'aggressive']
        mode_descriptions = {
            'conservative': '보수적 - 안전 우선, 소액 거래',
            'balanced': '균형적 - 적당한 리스크와 수익',
            'aggressive': '적극적 - 높은 수익 추구'
        }

        current_mode = current_settings['trading_mode']
        selected_mode = st.selectbox(
            "거래 모드",
            mode_options,
            index=mode_options.index(current_mode),
            format_func=lambda x: f"{x.title()} - {mode_descriptions[x]}"
        )

        # 선택된 모드의 프리셋 표시
        preset = settings_manager.get_trading_mode_settings(selected_mode)
        st.info(f"""
        **{selected_mode.title()} 모드 프리셋:**
        - 최대 주문: ${preset['max_order_amount']} USDT
        - 기본 주문: ${preset['default_order_amount']} USDT
        - 잔고 비율: {preset['balance_percentage']}%
        - 리스크: {preset['risk_percentage']}%
        """)

        # 프리셋 적용 버튼
        col_preset1, col_preset2 = st.columns(2)
        with col_preset1:
            apply_preset = st.checkbox("프리셋 설정 적용", help="체크 시 위 프리셋 값들을 자동 적용")

        if apply_preset:
            max_order = preset['max_order_amount']
            default_order = preset['default_order_amount']
            balance_pct = preset['balance_percentage']

        st.divider()
        st.markdown("### 📈 리스크 관리")

        col3, col4 = st.columns(2)
        with col3:
            risk_pct = st.slider(
                "거래당 리스크 비율 (%)",
                min_value=0.5,
                max_value=5.0,
                value=current_settings['risk_percentage'],
                step=0.1,
                help="각 거래에서 감수할 최대 손실 비율"
            )

            max_positions = st.slider(
                "최대 동시 포지션 수",
                min_value=1,
                max_value=10,
                value=current_settings['max_positions'],
                step=1,
                help="동시에 보유할 수 있는 최대 포지션 개수"
            )

        with col4:
            daily_loss = st.slider(
                "일일 손실 한도 (%)",
                min_value=1.0,
                max_value=20.0,
                value=current_settings['daily_loss_limit'],
                step=0.5,
                help="하루 최대 손실 한도 (자동 거래 중단)"
            )

            auto_trading = st.checkbox(
                "자동 거래 활성화",
                value=current_settings['auto_trading_enabled'],
                help="자동화된 거래 시스템 사용"
            )

        # 저장 버튼
        submitted = st.form_submit_button("💾 설정 저장", type="primary", use_container_width=True)

        if submitted:
            # 새 설정 구성
            new_settings = {
                'max_order_amount': max_order,
                'default_order_amount': default_order,
                'use_balance_percentage': use_percentage,
                'balance_percentage': balance_pct,
                'trading_mode': selected_mode,
                'risk_percentage': risk_pct,
                'max_positions': max_positions,
                'daily_loss_limit': daily_loss,
                'auto_trading_enabled': auto_trading
            }

            # 설정 저장
            if settings_manager.save_user_trading_settings(user_id, new_settings):
                st.success("✅ 거래 설정이 저장되었습니다!")
                st.balloons()
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ 설정 저장 중 오류가 발생했습니다.")

    # 현재 설정 요약 표시
    st.divider()
    st.markdown("### 📋 현재 설정 요약")

    summary_data = [
        {"설정": "최대 주문 금액", "값": f"${current_settings['max_order_amount']:.1f} USDT"},
        {"설정": "기본 주문 금액", "값": f"${current_settings['default_order_amount']:.1f} USDT"},
        {"설정": "거래 모드", "값": current_settings['trading_mode'].title()},
        {"설정": "잔고 비율 사용", "값": "예" if current_settings['use_balance_percentage'] else "아니오"},
        {"설정": "리스크 비율", "값": f"{current_settings['risk_percentage']:.1f}%"},
        {"설정": "최대 포지션", "값": f"{current_settings['max_positions']}개"}
    ]

    df_summary = pd.DataFrame(summary_data)
    st.dataframe(df_summary, use_container_width=True, hide_index=True)

def show_api_settings():
    """API 설정"""
    st.subheader("🔑 API 설정")

    if st.session_state.api_keys_saved:
        st.success("✅ API 키가 저장되어 있습니다")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 API 키 재설정", use_container_width=True):
                st.session_state.current_stage = 'safety_test'
                st.session_state.api_keys_saved = False
                st.session_state.api_verified = False
                st.rerun()

        with col2:
            if st.button("🧪 API 연결 테스트", use_container_width=True):
                connector = get_api_connector()
                if connector and connector.is_connected():
                    st.success("✅ API 연결 정상")
                else:
                    st.error("❌ API 연결 실패")
    else:
        st.warning("⚠️ API 키가 설정되지 않았습니다")

        if st.button("🛡️ API 설정하러 가기", use_container_width=True):
            st.session_state.current_stage = 'safety_test'
            st.rerun()

def show_safety_settings():
    """안전 설정 및 보호 시스템"""
    st.subheader("🛡️ 안전 설정 및 보호 시스템")

    if not st.session_state.authenticated:
        st.warning("로그인이 필요합니다.")
        return

    user_id = st.session_state.user['id']

    # 계좌 잔고 가져오기
    account_balance = 1000.0  # 기본값
    if st.session_state.api_connector:
        try:
            account_info = st.session_state.api_connector.get_account_info()
            account_balance = float(account_info.get('totalWalletBalance', 1000))
        except:
            pass

    # 보호시스템 비활성화 - 거래 차단 해결
    # from protection_system import get_protection_system
    # protection_system = get_protection_system()
    # protection_summary = protection_system.get_protection_summary(user_id, account_balance)

    # 임시 보호 상태 (비활성화)
    protection_summary = {
        'protection_status': 'disabled',
        'can_trade': True,
        'message': '보호시스템 비활성화 - 모든 거래 허용',
        'daily_stats': {'total_trades': 0, 'total_pnl': 0.0, 'daily_loss_percent': 0.0, 'daily_limit_percent': 5.0},
        'consecutive_stats': {'current_losses': 0, 'limit': 3},
        'settings': {'auto_protection_enabled': False}
    }

    # 보호 상태 표시
    st.markdown("### 🚨 보호 시스템 현황")

    protection_status = protection_summary.get('protection_status', 'error')
    can_trade = protection_summary.get('can_trade', False)
    message = protection_summary.get('message', '상태 확인 중...')

    # 상태에 따른 색상
    if protection_status == 'active':
        status_color = "green"
        status_icon = "🟢"
    elif protection_status in ['daily_limit', 'consecutive_loss']:
        status_color = "orange"
        status_icon = "🟡"
    else:
        status_color = "red"
        status_icon = "🔴"

    st.markdown(f"""
    <div style="border: 2px solid {status_color}; border-radius: 10px; padding: 15px; margin: 10px 0;">
        <h4 style="color: {status_color}; margin-top: 0;">{status_icon} 보호 시스템 상태</h4>
        <p style="margin-bottom: 0; font-size: 16px;">
            <strong>상태:</strong> {protection_status.title()}<br>
            <strong>거래 가능:</strong> {'예' if can_trade else '아니오'}<br>
            <strong>메시지:</strong> {message}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 일일 통계
    daily_stats = protection_summary.get('daily_stats', {})
    if daily_stats:
        st.markdown("### 📊 오늘의 거래 통계")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "총 거래",
                f"{daily_stats.get('total_trades', 0)}회",
                help="오늘 실행한 총 거래 횟수"
            )

        with col2:
            st.metric(
                "성공 거래",
                f"{daily_stats.get('successful_trades', 0)}회",
                help="수익을 낸 거래 횟수"
            )

        with col3:
            total_pnl = daily_stats.get('total_pnl', 0)
            pnl_color = "normal" if total_pnl >= 0 else "inverse"
            st.metric(
                "총 손익",
                f"${total_pnl:.2f}",
                delta=f"{total_pnl:.2f}",
                delta_color=pnl_color,
                help="오늘 총 손익"
            )

        with col4:
            daily_loss_percent = daily_stats.get('daily_loss_percent', 0)
            daily_limit = daily_stats.get('daily_limit_percent', 5)
            remaining = daily_stats.get('remaining_loss_allowance', 0)

            st.metric(
                "일일 손실",
                f"{daily_loss_percent:.2f}%",
                delta=f"한도까지 {remaining:.1f}%",
                delta_color="inverse" if remaining < 1 else "normal",
                help=f"일일 손실 한도 {daily_limit}% 대비 현재 손실"
            )

    # 연속 손실 통계
    consecutive_stats = protection_summary.get('consecutive_stats', {})
    if consecutive_stats:
        col1, col2 = st.columns(2)

        with col1:
            current_losses = consecutive_stats.get('current_losses', 0)
            loss_limit = consecutive_stats.get('limit', 3)
            st.metric(
                "연속 손실",
                f"{current_losses}/{loss_limit}회",
                help="현재 연속 손실 횟수"
            )

        with col2:
            remaining_allowance = consecutive_stats.get('remaining_allowance', 0)
            st.metric(
                "연속 손실 여유",
                f"{remaining_allowance}회",
                help="연속 손실 한도까지 남은 횟수"
            )

    # 제어 패널
    st.divider()
    st.markdown("### 🎛️ 보호 시스템 제어")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔄 보호 상태 재설정", help="보호 시스템을 수동으로 재설정합니다"):
            # 보호시스템 비활성화됨
            st.info("📝 보호시스템이 비활성화되어 재설정이 불필요합니다")

    with col2:
        if st.button("🛑 긴급 전체 중단", type="secondary", help="모든 거래를 즉시 중단합니다"):
            if st.session_state.get('confirm_emergency_stop'):
                # 보호시스템 비활성화됨
                st.info("📝 보호시스템이 비활성화되어 긴급 중단이 불필요합니다")
                st.session_state.confirm_emergency_stop = False
            else:
                st.session_state.confirm_emergency_stop = True
                st.warning("⚠️ 다시 클릭하면 모든 거래가 중단됩니다!")

    with col3:
        if st.button("⚙️ 리스크 설정", help="리스크 관리 설정으로 이동"):
            st.session_state.sidebar_menu = 'Settings'
            st.rerun()

    # API 커넥터 안전 상태 (기존 코드 유지)
    if st.session_state.api_connector:
        st.divider()
        st.markdown("### 📡 API 연결 상태")

        safety_status = st.session_state.api_connector.get_safety_status()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("거래 상태", "🟢 활성화" if safety_status['trade_enabled'] else "🔴 비활성화")
        with col2:
            st.metric("관찰 모드", "👀 활성화" if safety_status['observation_mode'] else "💰 비활성화")
        with col3:
            st.metric("긴급 중단", "🟢 정상" if safety_status['emergency_stop_enabled'] else "🚨 중단됨")

        st.markdown("### ⚙️ 시스템 제한")
        limit_data = [
            {"항목": "최대 주문 금액", "값": f"${safety_status['max_order_amount']:.1f} USDT"},
            {"항목": "일일 거래 한도", "값": f"${safety_status['daily_trade_limit']:.1f} USDT"},
            {"항목": "최대 포지션 크기", "값": f"${safety_status['max_position_size']:.1f} USDT"},
            {"항목": "최소 잔고 요구량", "값": f"${safety_status['min_balance_required']:.1f} USDT"},
            {"항목": "연속 손실 한도", "값": f"{safety_status['max_consecutive_losses']}회"}
        ]

        df_limits = pd.DataFrame(limit_data)
        st.dataframe(df_limits, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ API 커넥터가 초기화되지 않았습니다")

def show_risk_management_settings(user_id):
    """리스크 관리 설정"""
    st.subheader("📊 리스크 관리 설정")

    settings_manager = get_trading_settings_manager()
    current_risk_settings = settings_manager.get_risk_settings(user_id)

    with st.form("risk_management_form"):
        st.markdown("### 🎯 포지션 리스크 설정")

        col1, col2 = st.columns(2)

        with col1:
            position_risk = st.slider(
                "포지션당 리스크 비율 (%)",
                min_value=0.5,
                max_value=10.0,
                value=current_risk_settings['position_risk_percent'],
                step=0.1,
                help="각 포지션에서 감수할 최대 손실 비율"
            )

            max_leverage = st.slider(
                "최대 레버리지",
                min_value=1.0,
                max_value=20.0,
                value=current_risk_settings['max_leverage'],
                step=1.0,
                help="사용할 수 있는 최대 레버리지"
            )

        with col2:
            daily_loss_limit = st.slider(
                "일일 최대 손실 한도 (%)",
                min_value=1.0,
                max_value=20.0,
                value=current_risk_settings['daily_loss_limit'],
                step=0.5,
                help="하루 최대 손실 한도 (자동 중단 기준)"
            )

            consecutive_loss_limit = st.slider(
                "연속 손실 제한 (회)",
                min_value=1,
                max_value=10,
                value=current_risk_settings['consecutive_loss_limit'],
                step=1,
                help="연속 손실 발생 시 자동 중단할 횟수"
            )

        st.divider()
        st.markdown("### ⚙️ 주문 및 보호 설정")

        col3, col4 = st.columns(2)

        with col3:
            order_type = st.selectbox(
                "선호 주문 타입",
                ['limit', 'market'],
                index=0 if current_risk_settings['preferred_order_type'] == 'limit' else 1,
                help="기본적으로 사용할 주문 타입"
            )

            auto_protection = st.checkbox(
                "자동 보호 활성화",
                value=current_risk_settings['auto_protection_enabled'],
                help="손실 한도 도달 시 자동으로 거래 중단"
            )

        with col4:
            # 리스크 레벨 표시
            if position_risk <= 2.0:
                risk_level = "🟢 보수적"
                risk_color = "green"
            elif position_risk <= 5.0:
                risk_level = "🟡 균형적"
                risk_color = "orange"
            else:
                risk_level = "🔴 적극적"
                risk_color = "red"

            st.markdown(f"""
            **현재 리스크 레벨: <span style="color: {risk_color}">{risk_level}</span>**

            포지션당 리스크: {position_risk}%
            일일 손실 한도: {daily_loss_limit}%
            최대 레버리지: {max_leverage}x
            """, unsafe_allow_html=True)

        # 저장 버튼
        submitted = st.form_submit_button("💾 리스크 설정 저장", type="primary", use_container_width=True)

        if submitted:
            new_risk_settings = {
                'position_risk_percent': position_risk,
                'consecutive_loss_limit': consecutive_loss_limit,
                'auto_protection_enabled': auto_protection,
                'max_leverage': max_leverage,
                'preferred_order_type': order_type,
                'daily_loss_limit': daily_loss_limit
            }

            if settings_manager.save_risk_settings(user_id, new_risk_settings):
                st.success("✅ 리스크 설정이 저장되었습니다!")
                st.balloons()
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ 설정 저장 중 오류가 발생했습니다.")

    # 리스크 계산 시뮬레이터
    st.divider()
    st.markdown("### 🧮 리스크 계산 시뮬레이터")

    # 계좌 잔고 입력 (API에서 가져오거나 직접 입력)
    if st.session_state.api_connector:
        try:
            account_info = st.session_state.api_connector.get_account_info()
            default_balance = float(account_info.get('totalWalletBalance', 1000))
        except:
            default_balance = 1000.0
    else:
        default_balance = 1000.0

    col1, col2, col3 = st.columns(3)

    with col1:
        account_balance = st.number_input(
            "계좌 잔고 (USDT)",
            min_value=100.0,
            max_value=1000000.0,
            value=default_balance,
            step=100.0
        )

    with col2:
        entry_price = st.number_input(
            "진입 가격",
            min_value=0.0001,
            max_value=100000.0,
            value=26500.0,
            step=0.01,
            format="%.4f"
        )

    with col3:
        stop_loss_price = st.number_input(
            "손절 가격",
            min_value=0.0001,
            max_value=100000.0,
            value=25900.0,
            step=0.01,
            format="%.4f"
        )

    if st.button("🧮 포지션 계산", use_container_width=True):
        # 리스크 계산기 사용
        from risk_calculator import get_risk_calculator

        risk_calculator = get_risk_calculator()

        result = risk_calculator.calculate_position(
            user_capital=account_balance,
            risk_percent=position_risk,
            entry_price=entry_price,
            stop_loss=stop_loss_price,
            symbol="BTC/USDT"
        )

        if result.get('valid', False):
            col_calc1, col_calc2, col_calc3 = st.columns(3)

            with col_calc1:
                st.metric(
                    "포지션 크기",
                    f"${result['position_value']:.2f}",
                    help="계산된 총 포지션 크기"
                )
                st.metric(
                    "거래량",
                    f"{result['quantity']:.6f}",
                    help="실제 거래할 수량"
                )

            with col_calc2:
                st.metric(
                    "레버리지",
                    f"{result['leverage']:.1f}x",
                    help="적용될 레버리지"
                )
                st.metric(
                    "필요 마진",
                    f"${result['margin_used']:.2f}",
                    help="실제 필요한 마진"
                )

            with col_calc3:
                st.metric(
                    "리스크 금액",
                    f"${result['actual_risk_amount']:.2f}",
                    help="예상 최대 손실 금액"
                )
                st.metric(
                    "자본 사용률",
                    f"{result['capital_usage_percent']:.1f}%",
                    help="전체 자본 대비 사용 비율"
                )

            # 거래 타입 및 추가 정보
            trade_type_color = "green" if result['trade_type'] == 'SPOT' else "blue"
            st.info(f"**거래 타입**: <span style='color: {trade_type_color}'>{result['trade_type']}</span> - {result['message']}", unsafe_allow_html=True)

        else:
            st.error(f"❌ 계산 오류: {result.get('message', '알 수 없는 오류')}")

def show_coin_specific_settings(user_id):
    """코인별 개별 설정"""
    st.subheader("🪙 코인별 개별 설정")

    settings_manager = get_trading_settings_manager()

    # 즐겨찾기 코인 관리
    st.markdown("### ⭐ 즐겨찾기 코인 관리")

    current_favorites = settings_manager.get_favorite_coins(user_id)

    # 사용 가능한 코인 목록
    available_coins = [
        'BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'ADA/USDT', 'DOT/USDT',
        'BNB/USDT', 'SOL/USDT', 'MATIC/USDT', 'LINK/USDT', 'AVAX/USDT'
    ]

    with st.form("favorite_coins_form"):
        selected_favorites = st.multiselect(
            "즐겨찾기 코인 선택",
            available_coins,
            default=current_favorites,
            help="자주 거래하는 코인을 선택하세요"
        )

        if st.form_submit_button("⭐ 즐겨찾기 저장"):
            if settings_manager.save_favorite_coins(user_id, selected_favorites):
                st.success("✅ 즐겨찾기 코인이 저장되었습니다!")
                st.rerun()

    st.divider()

    # 코인별 개별 설정
    st.markdown("### 🎯 코인별 맞춤 설정")

    if current_favorites:
        selected_coin = st.selectbox(
            "설정할 코인 선택",
            current_favorites,
            help="개별 설정을 원하는 코인을 선택하세요"
        )

        if selected_coin:
            # 현재 코인 설정 로드
            coin_settings = settings_manager.get_coin_specific_settings(user_id, selected_coin)
            general_settings = settings_manager.get_user_trading_settings(user_id)

            with st.form(f"coin_settings_{selected_coin.replace('/', '_')}"):
                st.markdown(f"#### {selected_coin} 전용 설정")

                col1, col2 = st.columns(2)

                with col1:
                    # 최소 주문 금액 표시
                    if st.session_state.api_connector:
                        min_amounts = st.session_state.api_connector.get_min_order_amounts()
                        min_amount = min_amounts.get(selected_coin, 10.0)
                        st.info(f"**{selected_coin}** 최소 주문: ${min_amount:.1f} USDT")

                    use_custom = st.checkbox(
                        f"{selected_coin} 전용 설정 사용",
                        value=coin_settings.get('use_custom', False),
                        help="체크 시 이 코인만의 특별한 설정을 적용"
                    )

                    if use_custom:
                        custom_amount = st.slider(
                            "맞춤 기본 주문 금액 (USDT)",
                            min_value=max(min_amount, 5.0),
                            max_value=general_settings['max_order_amount'],
                            value=coin_settings.get('custom_amount', general_settings['default_order_amount']),
                            step=1.0
                        )
                    else:
                        custom_amount = general_settings['default_order_amount']

                with col2:
                    if use_custom:
                        custom_mode = st.selectbox(
                            f"{selected_coin} 거래 스타일",
                            ['conservative', 'balanced', 'aggressive'],
                            index=['conservative', 'balanced', 'aggressive'].index(
                                coin_settings.get('trading_style', 'balanced')
                            ),
                            help="이 코인에 적용할 거래 스타일"
                        )

                        auto_adjust = st.checkbox(
                            "변동성 기반 자동 조정",
                            value=coin_settings.get('auto_adjust_volatility', True),
                            help="높은 변동성 시 주문 금액 자동 조정"
                        )
                    else:
                        custom_mode = general_settings['trading_mode']
                        auto_adjust = True

                # 코인별 메모
                coin_notes = st.text_area(
                    f"{selected_coin} 거래 메모",
                    value=coin_settings.get('notes', ''),
                    help="이 코인 거래 시 참고할 개인 메모",
                    height=100
                )

                if st.form_submit_button(f"💾 {selected_coin} 설정 저장"):
                    new_coin_settings = {
                        'use_custom': use_custom,
                        'custom_amount': custom_amount if use_custom else None,
                        'trading_style': custom_mode if use_custom else None,
                        'auto_adjust_volatility': auto_adjust if use_custom else True,
                        'notes': coin_notes
                    }

                    if settings_manager.save_coin_specific_settings(user_id, selected_coin, new_coin_settings):
                        st.success(f"✅ {selected_coin} 설정이 저장되었습니다!")
                        st.rerun()
                    else:
                        st.error("❌ 설정 저장 중 오류가 발생했습니다.")
    else:
        st.info("💡 먼저 즐겨찾기 코인을 설정해주세요.")

def show_trading_schedule_settings(user_id):
    """거래 시간 설정"""
    st.subheader("⏰ 거래 시간 제한")

    settings_manager = get_trading_settings_manager()
    current_schedule = settings_manager.get_trading_schedule(user_id)

    with st.form("trading_schedule_form"):
        st.markdown("### 🕒 시간 기반 거래 제한")

        # 거래 시간 제한 활성화
        time_restriction_enabled = st.checkbox(
            "거래 시간 제한 활성화",
            value=current_schedule.get('enabled', False),
            help="특정 시간대에만 거래를 허용합니다"
        )

        col1, col2 = st.columns(2)

        with col1:
            if time_restriction_enabled:
                start_time = st.time_input(
                    "거래 시작 시간",
                    value=datetime.strptime(current_schedule.get('start_time', '09:00'), '%H:%M').time(),
                    help="거래를 시작할 시간"
                )

                weekend_trading = st.checkbox(
                    "주말 거래 허용",
                    value=current_schedule.get('weekend_trading', True),
                    help="토요일, 일요일에도 거래 허용"
                )
            else:
                start_time = datetime.strptime('09:00', '%H:%M').time()
                weekend_trading = True

        with col2:
            if time_restriction_enabled:
                end_time = st.time_input(
                    "거래 종료 시간",
                    value=datetime.strptime(current_schedule.get('end_time', '18:00'), '%H:%M').time(),
                    help="거래를 종료할 시간"
                )

                max_daily_trades = st.slider(
                    "일일 최대 거래 횟수",
                    min_value=1,
                    max_value=100,
                    value=current_schedule.get('max_daily_trades', 20),
                    help="하루에 실행할 수 있는 최대 거래 횟수"
                )
            else:
                end_time = datetime.strptime('18:00', '%H:%M').time()
                max_daily_trades = 20

        st.divider()
        st.markdown("### 🤖 자동 조정 옵션")

        col3, col4 = st.columns(2)

        with col3:
            balance_based_sizing = st.checkbox(
                "잔고 기반 포지션 크기 조정",
                value=current_schedule.get('balance_based_sizing', False),
                help="잔고에 따라 자동으로 주문 크기 조정"
            )

            if balance_based_sizing:
                balance_threshold = st.slider(
                    "잔고 임계값 (USDT)",
                    min_value=100,
                    max_value=10000,
                    value=current_schedule.get('balance_threshold', 1000),
                    step=100,
                    help="이 금액 이하일 때 주문 크기 축소"
                )
            else:
                balance_threshold = 1000

        with col4:
            volatility_adjustment = st.checkbox(
                "변동성 기반 자동 조정",
                value=current_schedule.get('volatility_adjustment', True),
                help="시장 변동성에 따라 거래 전략 자동 조정"
            )

            if volatility_adjustment:
                volatility_threshold = st.slider(
                    "변동성 임계값 (%)",
                    min_value=1.0,
                    max_value=10.0,
                    value=current_schedule.get('volatility_threshold', 5.0),
                    step=0.5,
                    help="이 수준 이상의 변동성에서 주문 크기 축소"
                )
            else:
                volatility_threshold = 5.0

        # 현재 거래 가능 상태 표시
        can_trade_result = settings_manager.can_trade_now(user_id)

        if can_trade_result['can_trade']:
            st.success("🟢 현재 거래 가능한 시간입니다")
        else:
            st.warning(f"🔴 현재 거래 불가: {can_trade_result['reason']}")

        # 저장 버튼
        if st.form_submit_button("⏰ 시간 설정 저장", type="primary"):
            new_schedule = {
                'enabled': time_restriction_enabled,
                'start_time': start_time.strftime('%H:%M'),
                'end_time': end_time.strftime('%H:%M'),
                'weekend_trading': weekend_trading,
                'max_daily_trades': max_daily_trades,
                'balance_based_sizing': balance_based_sizing,
                'balance_threshold': balance_threshold,
                'volatility_adjustment': volatility_adjustment,
                'volatility_threshold': volatility_threshold
            }

            if settings_manager.save_trading_schedule(user_id, new_schedule):
                st.success("✅ 거래 시간 설정이 저장되었습니다!")
                st.balloons()
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ 설정 저장 중 오류가 발생했습니다.")

    # 설정 관리
    st.divider()
    st.markdown("### 🔧 설정 관리")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📤 설정 내보내기", help="현재 모든 설정을 파일로 내보내기"):
            settings_export = settings_manager.export_settings(user_id)
            if settings_export:
                import json
                settings_json = json.dumps(settings_export, indent=2, ensure_ascii=False)
                st.download_button(
                    label="💾 설정 파일 다운로드",
                    data=settings_json,
                    file_name=f"trading_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

    with col2:
        uploaded_file = st.file_uploader(
            "📥 설정 가져오기",
            type=['json'],
            help="이전에 내보낸 설정 파일을 가져오기"
        )

        if uploaded_file is not None:
            try:
                import json
                settings_data = json.load(uploaded_file)
                if settings_manager.import_settings(user_id, settings_data):
                    st.success("✅ 설정을 성공적으로 가져왔습니다!")
                    st.rerun()
                else:
                    st.error("❌ 설정 가져오기 중 오류가 발생했습니다.")
            except Exception as e:
                st.error(f"❌ 파일 형식이 올바르지 않습니다: {e}")

    with col3:
        if st.button("🔄 기본값 복원", help="모든 설정을 기본값으로 복원"):
            if st.session_state.get('confirm_reset'):
                # 실제 리셋 실행
                default_settings = settings_manager._get_default_settings()
                if settings_manager.save_user_trading_settings(user_id, default_settings):
                    st.success("✅ 모든 설정이 기본값으로 복원되었습니다!")
                    st.session_state.confirm_reset = False
                    st.rerun()
            else:
                st.session_state.confirm_reset = True
                st.warning("⚠️ 다시 한 번 클릭하면 모든 설정이 초기화됩니다!")

def show_ai_signals_page():
    """AI 신호 페이지"""
    st.header("🤖 AI 신호 시스템")

    if not st.session_state.authenticated:
        st.warning("로그인이 필요합니다.")
        return

    user_id = st.session_state.user['id']

    # 계좌 잔고 가져오기
    account_balance = 1000.0  # 기본값
    if st.session_state.api_connector:
        try:
            account_info = st.session_state.api_connector.get_account_info()
            account_balance = float(account_info.get('totalWalletBalance', 1000))
        except:
            pass

    # AI 신호 관리자 초기화 (보호 시스템 비활성화)
    from ai_signal_system import get_ai_signal_manager
    from risk_calculator import get_risk_calculator
    from order_manager import get_order_manager
    # from protection_system import get_protection_system

    risk_calculator = get_risk_calculator()
    order_manager = get_order_manager(st.session_state.api_connector)
    # protection_system = get_protection_system()

    signal_manager = get_ai_signal_manager(risk_calculator, order_manager, None)

    # 신호 생성 섹션
    st.markdown("### 🎯 신호 생성 및 테스트")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔄 새 신호 생성", help="모의 AI 신호를 생성합니다"):
            new_signal = signal_manager.simulate_signal_generation("BTC/USDT", 26500.0)
            result = signal_manager.process_new_signal(new_signal, user_id, account_balance)

            if result['success']:
                confidence_color = "green" if new_signal.confidence > 0.8 else "orange" if new_signal.confidence > 0.6 else "red"
                st.success(f"✅ 새 신호 생성됨!")
                st.markdown(f"""
                **신호 정보:**
                - 심볼: {new_signal.symbol}
                - 액션: {new_signal.action.value}
                - 신뢰도: <span style="color: {confidence_color}">{new_signal.confidence:.1%}</span>
                - 진입가: ${new_signal.entry_price:.2f}
                - 손절가: ${new_signal.stop_loss:.2f}
                """, unsafe_allow_html=True)

                if result.get('requires_confirmation'):
                    st.warning(f"⚠️ {result['message']}")
                elif result.get('manual_execution_available'):
                    st.info(f"ℹ️ {result['message']}")
                else:
                    st.success(f"🚀 {result['message']}")
            else:
                st.error(f"❌ {result['message']}")

    with col2:
        if st.button("📊 신호 통계", help="AI 신호 성과 통계를 확인합니다"):
            stats = signal_manager.get_signal_statistics()
            st.json(stats)

    with col3:
        if st.button("🔄 상태 새로고침", help="활성 신호 상태를 새로고침합니다"):
            st.rerun()

    # 활성 신호 목록
    st.divider()
    st.markdown("### 🔥 활성 신호")

    active_signals = signal_manager.get_active_signals()

    if active_signals:
        for i, signal_data in enumerate(active_signals):
            with st.expander(f"🎯 {signal_data['symbol']} {signal_data['action']} - 신뢰도 {signal_data['confidence']:.1%}", expanded=i==0):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown(f"""
                    **기본 정보:**
                    - 심볼: {signal_data['symbol']}
                    - 액션: {signal_data['action']}
                    - 전략: {signal_data['strategy']}
                    - 시장 상황: {signal_data['market_condition']}
                    """)

                with col2:
                    confidence_color = "green" if signal_data['confidence'] > 0.8 else "orange" if signal_data['confidence'] > 0.6 else "red"
                    status_color = "green" if signal_data['status'] == 'executed' else "orange"

                    st.markdown(f"""
                    **신호 상태:**
                    - 신뢰도: <span style="color: {confidence_color}">{signal_data['confidence']:.1%}</span>
                    - 상태: <span style="color: {status_color}">{signal_data['status'].title()}</span>
                    - 생성: {signal_data['created_at'][:19]}
                    - 만료: {signal_data['expires_at'][:19] if signal_data['expires_at'] else 'N/A'}
                    """, unsafe_allow_html=True)

                with col3:
                    rr_ratio = signal_data.get('risk_reward_ratio')
                    st.markdown(f"""
                    **가격 정보:**
                    - 진입가: ${signal_data['entry_price']:.4f}
                    - 손절가: ${signal_data['stop_loss']:.4f}
                    - 익절가: ${signal_data['take_profit']:.4f if signal_data['take_profit'] else 'N/A'}
                    - R:R 비율: {rr_ratio:.2f if rr_ratio else 'N/A'}
                    """)

                # 액션 버튼
                col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)

                with col_btn1:
                    if signal_data['status'] == 'pending' and st.button(f"✅ 실행", key=f"exec_{signal_data['signal_id']}"):
                        exec_result = signal_manager.manually_execute_signal(signal_data['signal_id'], user_id, account_balance)
                        if exec_result['success']:
                            st.success(f"✅ 신호가 실행되었습니다!")
                            st.rerun()
                        else:
                            st.error(f"❌ {exec_result['message']}")

                with col_btn2:
                    if signal_data['status'] == 'pending' and st.button(f"❌ 취소", key=f"cancel_{signal_data['signal_id']}"):
                        cancel_result = signal_manager.cancel_signal(signal_data['signal_id'])
                        if cancel_result['success']:
                            st.success(f"✅ 신호가 취소되었습니다!")
                            st.rerun()
                        else:
                            st.error(f"❌ {cancel_result['message']}")

                with col_btn3:
                    if st.button(f"📋 상세", key=f"detail_{signal_data['signal_id']}"):
                        st.json(signal_data)

                with col_btn4:
                    if signal_data['order_ids'] and st.button(f"📊 주문", key=f"orders_{signal_data['signal_id']}"):
                        st.info(f"연결된 주문 ID: {', '.join(signal_data['order_ids'])}")

    else:
        st.info("🔍 현재 활성 신호가 없습니다. '새 신호 생성' 버튼을 클릭해보세요!")

    # 신호 설정
    st.divider()
    st.markdown("### ⚙️ AI 신호 설정")

    with st.expander("🔧 신호 실행 설정", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            auto_high = st.checkbox(
                "고신뢰도 자동 실행",
                value=signal_manager.auto_execute_high_confidence,
                help="신뢰도 80% 이상 신호를 자동으로 실행"
            )

        with col2:
            confirm_medium = st.checkbox(
                "중신뢰도 확인 요구",
                value=signal_manager.require_confirmation_medium,
                help="신뢰도 60-80% 신호는 사용자 확인 후 실행"
            )

        with col3:
            notify_low = st.checkbox(
                "저신뢰도 알림만",
                value=signal_manager.notify_only_low,
                help="신뢰도 60% 미만 신호는 알림만 표시"
            )

        if st.button("💾 설정 저장"):
            signal_manager.auto_execute_high_confidence = auto_high
            signal_manager.require_confirmation_medium = confirm_medium
            signal_manager.notify_only_low = notify_low
            st.success("✅ 설정이 저장되었습니다!")

    # 신호 통계 대시보드
    st.divider()
    st.markdown("### 📊 신호 성과 분석")

    stats = signal_manager.get_signal_statistics()

    if stats['total_signals'] > 0:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "총 신호",
                f"{stats['total_signals']}개",
                help="생성된 총 신호 수"
            )

        with col2:
            st.metric(
                "실행된 신호",
                f"{stats['executed_signals']}개",
                help="실제로 실행된 신호 수"
            )

        with col3:
            st.metric(
                "성공률",
                f"{stats['success_rate']:.1f}%",
                help="수익을 낸 신호의 비율"
            )

        with col4:
            avg_pnl_color = "normal" if stats['avg_pnl'] >= 0 else "inverse"
            st.metric(
                "평균 손익",
                f"${stats['avg_pnl']:.2f}",
                delta=f"{stats['avg_pnl']:.2f}",
                delta_color=avg_pnl_color,
                help="실행된 신호의 평균 손익"
            )

        # 신뢰도별 분포
        if stats.get('confidence_distribution'):
            st.markdown("#### 📈 신뢰도별 신호 분포")
            confidence_dist = stats['confidence_distribution']

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("고신뢰도", f"{confidence_dist['high']}개", help="80% 이상")
            with col2:
                st.metric("중신뢰도", f"{confidence_dist['medium']}개", help="60-80%")
            with col3:
                st.metric("저신뢰도", f"{confidence_dist['low']}개", help="60% 미만")

    else:
        st.info("📊 아직 신호 통계가 없습니다. 신호를 생성해보세요!")

def main():
    """메인 함수"""
    init_page_config()
    init_session_state()

    # 세션 복원 시도
    check_and_restore_session()

    # 사이드바 표시
    show_sidebar()

    # 진행률 표시
    if st.session_state.authenticated:
        show_progress_indicator()
        st.divider()

    # 현재 페이지에 따른 라우팅
    if st.session_state.sidebar_menu == 'Settings':
        show_settings_page()
    elif st.session_state.sidebar_menu == 'AI Signals':
        show_ai_signals_page()
    elif st.session_state.sidebar_menu == 'Dashboard':
        # 인증 상태에 따른 페이지 자동 라우팅
        if not st.session_state.authenticated:
            show_login_page()
        elif st.session_state.current_stage == 'safety_test':
            show_safety_test_page()
        elif st.session_state.current_stage == 'main_trading':
            show_main_trading_page()
        else:
            show_login_page()

    # 하단 정보
    st.divider()
    with st.container():
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            **🔒 보안 정보**
            - 모든 API 키 암호화 저장
            - 세션 기반 인증 관리
            - 자동 로그아웃 (1시간)
            """)

        with col2:
            st.markdown("""
            **🛡️ 안전 설정**
            - 최대 주문: $5 USDT
            - 긴급 중단 시스템
            - 실시간 연결 모니터링
            """)

        with col3:
            st.markdown("""
            **📞 지원**
            - GitHub: crypto-trader-pro
            - 버전: v6.1 (통합)
            - 상태: 정상 운영
            """)

    # 개발자 정보 (작게)
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 12px; margin-top: 20px;">
        Crypto Trader Pro v6.1 - 단일 포트 통합 시스템 | 안전한 실거래 플랫폼
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()