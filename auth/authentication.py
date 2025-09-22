"""
Authentication System for Crypto Trader Pro
사용자 인증 및 세션 관리
"""

import bcrypt
import jwt
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
import os
import secrets

# 로그 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthenticationManager:
    """사용자 인증 관리 클래스"""

    def __init__(self, secret_key: Optional[str] = None):
        """
        인증 매니저 초기화

        Args:
            secret_key: JWT 토큰 생성용 비밀 키
        """
        self.secret_key = secret_key or self._get_or_create_secret_key()
        self.token_expiry_hours = 24  # 토큰 만료 시간 (시간)

    def _get_or_create_secret_key(self) -> str:
        """JWT 비밀 키 생성 또는 조회"""
        secret_file = os.path.join(os.path.dirname(__file__), "..", ".secret_key")

        if os.path.exists(secret_file):
            with open(secret_file, 'r') as f:
                return f.read().strip()
        else:
            # 새 비밀 키 생성
            secret_key = secrets.token_urlsafe(32)
            with open(secret_file, 'w') as f:
                f.write(secret_key)
            logger.info("New JWT secret key generated")
            return secret_key

    def hash_password(self, password: str) -> str:
        """
        패스워드 해싱

        Args:
            password: 원본 패스워드

        Returns:
            해싱된 패스워드
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        패스워드 검증

        Args:
            password: 입력된 패스워드
            hashed_password: 저장된 해싱된 패스워드

        Returns:
            패스워드 일치 여부
        """
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    def generate_jwt_token(self, user_id: int, username: str) -> str:
        """
        JWT 토큰 생성

        Args:
            user_id: 사용자 ID
            username: 사용자명

        Returns:
            JWT 토큰
        """
        try:
            payload = {
                'user_id': user_id,
                'username': username,
                'exp': datetime.utcnow() + timedelta(hours=self.token_expiry_hours),
                'iat': datetime.utcnow()
            }

            token = jwt.encode(payload, self.secret_key, algorithm='HS256')
            return token

        except Exception as e:
            logger.error(f"JWT token generation error: {e}")
            return ""

    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        JWT 토큰 검증

        Args:
            token: JWT 토큰

        Returns:
            토큰이 유효하면 페이로드, 아니면 None
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None

    def create_session(self, user_id: int, username: str) -> bool:
        """
        Streamlit 세션 생성

        Args:
            user_id: 사용자 ID
            username: 사용자명

        Returns:
            세션 생성 성공 여부
        """
        try:
            # JWT 토큰 생성
            token = self.generate_jwt_token(user_id, username)

            if token:
                # Streamlit 세션에 사용자 정보 저장
                st.session_state.authenticated = True
                st.session_state.user_id = user_id
                st.session_state.username = username
                st.session_state.jwt_token = token
                st.session_state.login_time = datetime.utcnow()

                logger.info(f"Session created for user: {username}")
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"Session creation error: {e}")
            return False

    def destroy_session(self):
        """세션 삭제"""
        try:
            # Streamlit 세션에서 사용자 정보 제거
            for key in ['authenticated', 'user_id', 'username', 'jwt_token', 'login_time']:
                if key in st.session_state:
                    del st.session_state[key]

            logger.info("Session destroyed")

        except Exception as e:
            logger.error(f"Session destruction error: {e}")

    def is_authenticated(self) -> bool:
        """
        인증 상태 확인

        Returns:
            인증 상태
        """
        try:
            # 세션 상태 확인
            if not st.session_state.get('authenticated', False):
                return False

            # JWT 토큰 검증
            token = st.session_state.get('jwt_token')
            if not token:
                return False

            payload = self.verify_jwt_token(token)
            if not payload:
                # 토큰이 무효하면 세션 삭제
                self.destroy_session()
                return False

            # 사용자 ID 일치 확인
            if payload.get('user_id') != st.session_state.get('user_id'):
                self.destroy_session()
                return False

            return True

        except Exception as e:
            logger.error(f"Authentication check error: {e}")
            return False

    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """
        현재 로그인된 사용자 정보 조회

        Returns:
            사용자 정보 또는 None
        """
        if not self.is_authenticated():
            return None

        return {
            'user_id': st.session_state.get('user_id'),
            'username': st.session_state.get('username'),
            'login_time': st.session_state.get('login_time')
        }

    def refresh_token(self) -> bool:
        """
        토큰 갱신

        Returns:
            갱신 성공 여부
        """
        try:
            if not self.is_authenticated():
                return False

            user_id = st.session_state.get('user_id')
            username = st.session_state.get('username')

            # 새 토큰 생성
            new_token = self.generate_jwt_token(user_id, username)
            if new_token:
                st.session_state.jwt_token = new_token
                logger.info(f"Token refreshed for user: {username}")
                return True

            return False

        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return False

    def require_auth(self, redirect_page: str = "login"):
        """
        인증 필수 데코레이터

        Args:
            redirect_page: 리다이렉트할 페이지
        """
        if not self.is_authenticated():
            st.error("로그인이 필요합니다.")
            st.switch_page(f"pages/{redirect_page}.py")
            st.stop()

    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """
        패스워드 강도 검증

        Args:
            password: 검증할 패스워드

        Returns:
            검증 결과
        """
        result = {
            'valid': True,
            'score': 0,
            'messages': []
        }

        # 길이 체크
        if len(password) < 8:
            result['valid'] = False
            result['messages'].append("패스워드는 최소 8자 이상이어야 합니다.")
        else:
            result['score'] += 1

        # 대문자 포함 체크
        if any(c.isupper() for c in password):
            result['score'] += 1
        else:
            result['messages'].append("대문자를 포함해야 합니다.")

        # 소문자 포함 체크
        if any(c.islower() for c in password):
            result['score'] += 1
        else:
            result['messages'].append("소문자를 포함해야 합니다.")

        # 숫자 포함 체크
        if any(c.isdigit() for c in password):
            result['score'] += 1
        else:
            result['messages'].append("숫자를 포함해야 합니다.")

        # 특수문자 포함 체크
        special_chars = "!@#$%^&*(),.?\":{}|<>"
        if any(c in special_chars for c in password):
            result['score'] += 1
        else:
            result['messages'].append("특수문자를 포함해야 합니다.")

        # 최종 강도 평가
        if result['score'] < 3:
            result['valid'] = False
            result['strength'] = "약함"
        elif result['score'] < 4:
            result['strength'] = "보통"
        else:
            result['strength'] = "강함"

        return result

class SessionManager:
    """세션 관리 유틸리티 클래스"""

    @staticmethod
    def init_session_state():
        """세션 상태 초기화"""
        default_states = {
            'authenticated': False,
            'user_id': None,
            'username': None,
            'jwt_token': None,
            'login_time': None,
            'page': 'login'
        }

        for key, default_value in default_states.items():
            if key not in st.session_state:
                st.session_state[key] = default_value

    @staticmethod
    def get_session_info() -> Dict[str, Any]:
        """세션 정보 조회"""
        return {
            'authenticated': st.session_state.get('authenticated', False),
            'user_id': st.session_state.get('user_id'),
            'username': st.session_state.get('username'),
            'login_time': st.session_state.get('login_time'),
            'session_duration': (
                datetime.utcnow() - st.session_state.get('login_time')
                if st.session_state.get('login_time') else None
            )
        }

    @staticmethod
    def clear_session():
        """전체 세션 클리어"""
        for key in list(st.session_state.keys()):
            del st.session_state[key]

# 전역 인증 매니저 인스턴스
_auth_manager = None

def get_auth_manager() -> AuthenticationManager:
    """싱글톤 인증 매니저 인스턴스 반환"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthenticationManager()
    return _auth_manager