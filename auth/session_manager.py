"""
Session Manager for Multi-Port Dashboard System
포트간 세션 상태 공유를 위한 데이터베이스 기반 세션 관리
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
import secrets
from database.database_manager import get_db_manager
from database.models import UserSession, User
from auth.user_manager import get_user_manager
from auth.authentication import AuthenticationManager

logger = logging.getLogger(__name__)

class SessionManager:
    """다중 포트 환경에서 세션 상태를 공유하는 관리자"""

    def __init__(self):
        self.db_manager = get_db_manager()
        self.user_manager = get_user_manager()
        self.auth_manager = AuthenticationManager()

    def create_session(self, user_id: int, username: str) -> Optional[str]:
        """
        새 세션 생성

        Args:
            user_id: 사용자 ID
            username: 사용자명

        Returns:
            생성된 세션 ID 또는 None
        """
        try:
            with self.db_manager.get_session() as session:
                # 기존 세션 비활성화
                existing_sessions = session.query(UserSession).filter_by(
                    username=username, is_active=True
                ).all()

                for old_session in existing_sessions:
                    old_session.is_active = False

                # 새 세션 생성
                session_id = secrets.token_urlsafe(32)
                new_session = UserSession(
                    user_id=user_id,
                    username=username,
                    session_id=session_id,
                    created_at=datetime.utcnow(),
                    last_activity=datetime.utcnow(),
                    is_active=True
                )

                session.add(new_session)
                session.commit()

                logger.info(f"Session created for user: {username}")
                return session_id

        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None

    def get_active_session(self, username: str) -> Optional[Dict[str, Any]]:
        """
        데이터베이스에서 활성 세션 조회

        Args:
            username: 사용자명

        Returns:
            활성 세션 정보 또는 None
        """
        try:
            with self.db_manager.get_session() as session:
                # 활성 세션 조회 (최근 1시간 이내)
                cutoff_time = datetime.utcnow() - timedelta(hours=1)

                user_session = session.query(UserSession).filter(
                    UserSession.username == username,
                    UserSession.is_active == True,
                    UserSession.last_activity > cutoff_time
                ).order_by(UserSession.last_activity.desc()).first()

                if user_session:
                    return {
                        'user_id': user_session.user_id,
                        'username': user_session.username,
                        'session_id': user_session.session_id,
                        'created_at': user_session.created_at,
                        'last_activity': user_session.last_activity
                    }

                return None

        except Exception as e:
            logger.error(f"Error getting active session: {e}")
            return None

    def update_session_activity(self, username: str) -> bool:
        """
        세션 활동 시간 업데이트

        Args:
            username: 사용자명

        Returns:
            업데이트 성공 여부
        """
        try:
            with self.db_manager.get_session() as session:
                # 활성 세션 찾기
                user_session = session.query(UserSession).filter_by(
                    username=username, is_active=True
                ).first()

                if user_session:
                    user_session.last_activity = datetime.utcnow()
                    session.commit()
                    return True

                return False

        except Exception as e:
            logger.error(f"Error updating session activity: {e}")
            return False

    def load_session_into_streamlit(self, username: str) -> bool:
        """
        데이터베이스 세션을 Streamlit 세션에 로드

        Args:
            username: 사용자명

        Returns:
            로드 성공 여부
        """
        try:
            # 활성 세션 조회
            session_data = self.get_active_session(username)

            if not session_data:
                return False

            # 사용자 정보 조회
            with self.db_manager.get_session() as session:
                user = session.query(User).filter_by(username=username).first()
                if not user:
                    return False

                # Streamlit 세션에 저장
                st.session_state.user = {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': 'user'  # 기본 역할
                }
                st.session_state.authenticated = True
                st.session_state.login_time = session_data['created_at']

            # 세션 활동 시간 업데이트
            self.update_session_activity(username)

            logger.info(f"Session loaded for user: {username}")
            return True

        except Exception as e:
            logger.error(f"Error loading session: {e}")
            return False

    def check_and_restore_session(self) -> bool:
        """
        현재 페이지에서 세션 확인 및 복원

        Returns:
            세션 복원 성공 여부
        """
        try:
            # 이미 Streamlit 세션이 있으면 활동 시간만 업데이트
            if 'user' in st.session_state and st.session_state.user:
                username = st.session_state.user['username']
                self.update_session_activity(username)
                return True

            # URL 파라미터에서 사용자명 확인 (로그인 직후 리디렉션용)
            query_params = st.query_params
            if 'user' in query_params:
                username = query_params['user']
                return self.load_session_into_streamlit(username)

            # 마지막으로 최근 활성 세션이 있는지 확인
            with self.db_manager.get_session() as session:
                cutoff_time = datetime.utcnow() - timedelta(minutes=10)

                user_session = session.query(UserSession).filter(
                    UserSession.is_active == True,
                    UserSession.last_activity > cutoff_time
                ).order_by(UserSession.last_activity.desc()).first()

                if user_session:
                    return self.load_session_into_streamlit(user_session.username)

            return False

        except Exception as e:
            logger.error(f"Error checking session: {e}")
            return False

    def get_session_info(self) -> Dict[str, Any]:
        """
        현재 세션 정보 반환

        Returns:
            세션 정보 딕셔너리
        """
        if 'user' in st.session_state and st.session_state.user:
            return {
                'authenticated': True,
                'user': st.session_state.user,
                'login_time': st.session_state.get('login_time', 'Unknown')
            }
        else:
            return {
                'authenticated': False,
                'user': None,
                'login_time': None
            }

# 글로벌 세션 매니저 인스턴스
_session_manager = None

def get_session_manager() -> SessionManager:
    """세션 매니저 인스턴스 반환"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager

def init_session_for_dashboard() -> bool:
    """
    대시보드 초기화 시 호출할 세션 복원 함수

    Returns:
        세션 복원 성공 여부 (True면 로그인됨, False면 로그인 필요)
    """
    session_manager = get_session_manager()
    return session_manager.check_and_restore_session()