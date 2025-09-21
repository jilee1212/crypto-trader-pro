#!/usr/bin/env python3
"""
Stable Platform Runner - 안정적인 플랫폼 실행기
깜빡임 없는 최적화된 버전
"""

import sys
import os
import streamlit as st

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """최적화된 메인 실행 함수"""

    # 세션 상태 초기화 (페이지 로드 시 한 번만)
    if 'platform_initialized' not in st.session_state:
        st.session_state.platform_initialized = True
        # 캐시 초기화
        cache_keys = [
            'sidebar_balance_data',
            'main_dashboard_balance',
            'dashboard_positions',
            'market_data'
        ]
        for key in cache_keys:
            if key in st.session_state:
                del st.session_state[key]

    try:
        print("🚀 Stable Crypto Trader Pro 시작 중...")

        # 메인 플랫폼 실행
        from main_platform import main as run_main_app
        run_main_app()

    except ImportError as e:
        st.error(f"❌ 모듈 import 오류: {e}")
        st.info("""
        해결 방법:
        1. 모든 필요한 Python 패키지가 설치되어 있는지 확인
        2. ai_trading_signals.py와 real_market_data.py 파일이 있는지 확인
        3. requirements.txt의 의존성 설치: pip install -r requirements.txt
        """)

    except Exception as e:
        st.error(f"❌ 애플리케이션 실행 오류: {e}")
        st.info("""
        문제 해결을 위해 다음을 확인하세요:
        1. Python 버전이 3.9 이상인지 확인
        2. 필요한 모든 파일이 현재 디렉토리에 있는지 확인
        3. 포트 8501이 사용 가능한지 확인
        """)

        # 디버그 정보
        with st.expander("🔍 디버그 정보"):
            st.write("현재 작업 디렉토리:", os.getcwd())
            st.write("Python 경로:", sys.path[:3])

            # 파일 존재 확인
            required_files = [
                'main_platform.py',
                'dashboard_components.py',
                'trading_functions.py',
                'ui_helpers.py'
            ]

            st.write("파일 존재 확인:")
            for file in required_files:
                exists = os.path.exists(file)
                st.write(f"- {file}: {'✅' if exists else '❌'}")

if __name__ == "__main__":
    main()