#!/usr/bin/env python3
"""
Test Platform - 플랫폼 기본 동작 테스트
"""

import sys
import os
import streamlit as st

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """모든 모듈 import 테스트"""
    try:
        st.write("🔄 모듈 import 테스트 중...")

        # UI Helpers 테스트
        try:
            from ui_helpers import get_css_styles
            st.write("✅ ui_helpers 모듈 로딩 성공")
        except Exception as e:
            st.error(f"❌ ui_helpers 모듈 로딩 실패: {e}")

        # Trading Functions 테스트
        try:
            from trading_functions import get_user_api_keys, get_real_account_balance
            st.write("✅ trading_functions 모듈 로딩 성공")
        except Exception as e:
            st.error(f"❌ trading_functions 모듈 로딩 실패: {e}")

        # Dashboard Components 테스트
        try:
            from dashboard_components import show_main_dashboard
            st.write("✅ dashboard_components 모듈 로딩 성공")
        except Exception as e:
            st.error(f"❌ dashboard_components 모듈 로딩 실패: {e}")

        # Main Platform 테스트
        try:
            from main_platform import init_database, hash_password
            st.write("✅ main_platform 모듈 로딩 성공")
        except Exception as e:
            st.error(f"❌ main_platform 모듈 로딩 실패: {e}")

        st.write("🎯 모든 모듈 테스트 완료!")

    except Exception as e:
        st.error(f"❌ 전체 테스트 실패: {e}")

def main():
    st.set_page_config(
        page_title="Platform Test",
        page_icon="🧪",
        layout="wide"
    )

    st.title("🧪 Crypto Trader Pro - Platform Test")

    test_imports()

    st.markdown("---")

    if st.button("🚀 실제 플랫폼 시작"):
        try:
            from main_platform import main as run_main
            run_main()
        except Exception as e:
            st.error(f"플랫폼 시작 실패: {e}")

if __name__ == "__main__":
    main()