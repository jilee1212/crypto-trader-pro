"""
User Management System for Crypto Trader Pro
사용자 관리 시스템
"""

import re
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from database.database_manager import get_db_manager
from database.models import User
from .authentication import get_auth_manager

# 로그 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserManager:
    """사용자 관리 클래스"""

    def __init__(self):
        self.db_manager = get_db_manager()
        self.auth_manager = get_auth_manager()

    def create_user(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """
        새 사용자 생성

        Args:
            username: 사용자명
            email: 이메일
            password: 패스워드

        Returns:
            생성 결과
        """
        try:
            # 입력 값 검증
            validation_result = self._validate_user_input(username, email, password)
            if not validation_result['valid']:
                return validation_result

            # 패스워드 해싱
            password_hash = self.auth_manager.hash_password(password)

            # 사용자 생성
            user = self.db_manager.create_user(
                username=username,
                email=email,
                password_hash=password_hash
            )

            if user:
                logger.info(f"User created successfully: {username}")
                return {
                    'success': True,
                    'message': '사용자가 성공적으로 생성되었습니다.',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email
                    }
                }
            else:
                return {
                    'success': False,
                    'message': '사용자 생성에 실패했습니다. 사용자명 또는 이메일이 이미 존재할 수 있습니다.'
                }

        except Exception as e:
            logger.error(f"User creation error: {e}")
            return {
                'success': False,
                'message': f'사용자 생성 중 오류가 발생했습니다: {str(e)}'
            }

    def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """
        사용자 인증

        Args:
            username: 사용자명 또는 이메일
            password: 패스워드

        Returns:
            인증 결과
        """
        try:
            # 사용자 조회 (사용자명 또는 이메일로)
            user = self._get_user_by_username_or_email(username)

            if not user:
                return {
                    'success': False,
                    'message': '존재하지 않는 사용자입니다.'
                }

            # 계정 활성 상태 확인
            if not user.is_active:
                return {
                    'success': False,
                    'message': '비활성화된 계정입니다. 관리자에게 문의하세요.'
                }

            # 패스워드 검증
            if not self.auth_manager.verify_password(password, user.password_hash):
                return {
                    'success': False,
                    'message': '잘못된 패스워드입니다.'
                }

            # 로그인 시간 업데이트
            self.db_manager.update_user_login(user.id)

            logger.info(f"User authenticated successfully: {user.username}")
            return {
                'success': True,
                'message': '로그인 성공',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'trading_enabled': user.trading_enabled
                }
            }

        except Exception as e:
            logger.error(f"User authentication error: {e}")
            return {
                'success': False,
                'message': f'인증 중 오류가 발생했습니다: {str(e)}'
            }

    def change_password(self, user_id: int, current_password: str, new_password: str) -> Dict[str, Any]:
        """
        패스워드 변경

        Args:
            user_id: 사용자 ID
            current_password: 현재 패스워드
            new_password: 새 패스워드

        Returns:
            변경 결과
        """
        try:
            # 사용자 조회
            user = self.db_manager.get_user_by_id(user_id)
            if not user:
                return {
                    'success': False,
                    'message': '사용자를 찾을 수 없습니다.'
                }

            # 현재 패스워드 확인
            if not self.auth_manager.verify_password(current_password, user.password_hash):
                return {
                    'success': False,
                    'message': '현재 패스워드가 일치하지 않습니다.'
                }

            # 새 패스워드 강도 검증
            password_validation = self.auth_manager.validate_password_strength(new_password)
            if not password_validation['valid']:
                return {
                    'success': False,
                    'message': '새 패스워드가 보안 요구사항을 만족하지 않습니다.',
                    'details': password_validation['messages']
                }

            # 새 패스워드 해싱
            new_password_hash = self.auth_manager.hash_password(new_password)

            # 데이터베이스 업데이트
            with self.db_manager.get_session() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if user:
                    user.password_hash = new_password_hash
                    session.commit()

            logger.info(f"Password changed for user: {user.username}")
            return {
                'success': True,
                'message': '패스워드가 성공적으로 변경되었습니다.'
            }

        except Exception as e:
            logger.error(f"Password change error: {e}")
            return {
                'success': False,
                'message': f'패스워드 변경 중 오류가 발생했습니다: {str(e)}'
            }

    def update_user_profile(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """
        사용자 프로필 업데이트

        Args:
            user_id: 사용자 ID
            **kwargs: 업데이트할 필드들

        Returns:
            업데이트 결과
        """
        try:
            allowed_fields = ['email']  # 업데이트 가능한 필드들

            # 입력 값 검증
            if 'email' in kwargs:
                if not self._validate_email(kwargs['email']):
                    return {
                        'success': False,
                        'message': '유효하지 않은 이메일 형식입니다.'
                    }

                # 이메일 중복 체크
                existing_user = self.db_manager.get_user_by_email(kwargs['email'])
                if existing_user and existing_user.id != user_id:
                    return {
                        'success': False,
                        'message': '이미 사용 중인 이메일입니다.'
                    }

            # 데이터베이스 업데이트
            with self.db_manager.get_session() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    return {
                        'success': False,
                        'message': '사용자를 찾을 수 없습니다.'
                    }

                for field, value in kwargs.items():
                    if field in allowed_fields and hasattr(user, field):
                        setattr(user, field, value)

                session.commit()

            logger.info(f"User profile updated: {user.username}")
            return {
                'success': True,
                'message': '프로필이 성공적으로 업데이트되었습니다.'
            }

        except Exception as e:
            logger.error(f"Profile update error: {e}")
            return {
                'success': False,
                'message': f'프로필 업데이트 중 오류가 발생했습니다: {str(e)}'
            }

    def activate_user(self, user_id: int, active: bool = True) -> Dict[str, Any]:
        """
        사용자 계정 활성화/비활성화

        Args:
            user_id: 사용자 ID
            active: 활성화 상태

        Returns:
            처리 결과
        """
        try:
            with self.db_manager.get_session() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    return {
                        'success': False,
                        'message': '사용자를 찾을 수 없습니다.'
                    }

                user.is_active = active
                session.commit()

            action = "활성화" if active else "비활성화"
            logger.info(f"User {action}: {user.username}")
            return {
                'success': True,
                'message': f'계정이 성공적으로 {action}되었습니다.'
            }

        except Exception as e:
            logger.error(f"User activation error: {e}")
            return {
                'success': False,
                'message': f'계정 {action} 중 오류가 발생했습니다: {str(e)}'
            }

    def enable_trading(self, user_id: int, enabled: bool = True) -> Dict[str, Any]:
        """
        사용자 거래 활성화/비활성화

        Args:
            user_id: 사용자 ID
            enabled: 거래 활성화 상태

        Returns:
            처리 결과
        """
        try:
            success = self.db_manager.enable_user_trading(user_id, enabled)

            if success:
                action = "활성화" if enabled else "비활성화"
                return {
                    'success': True,
                    'message': f'거래가 성공적으로 {action}되었습니다.'
                }
            else:
                return {
                    'success': False,
                    'message': '사용자를 찾을 수 없습니다.'
                }

        except Exception as e:
            logger.error(f"Trading enable error: {e}")
            return {
                'success': False,
                'message': f'거래 설정 중 오류가 발생했습니다: {str(e)}'
            }

    def get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        사용자 정보 조회

        Args:
            user_id: 사용자 ID

        Returns:
            사용자 정보
        """
        try:
            user = self.db_manager.get_user_by_id(user_id)
            if not user:
                return None

            return {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'created_at': user.created_at,
                'last_login': user.last_login,
                'is_active': user.is_active,
                'trading_enabled': user.trading_enabled
            }

        except Exception as e:
            logger.error(f"Get user info error: {e}")
            return None

    def get_user_list(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        사용자 목록 조회

        Args:
            active_only: 활성 사용자만 조회

        Returns:
            사용자 목록
        """
        try:
            with self.db_manager.get_session() as session:
                query = session.query(User)
                if active_only:
                    query = query.filter(User.is_active == True)

                users = query.all()

                return [{
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'created_at': user.created_at,
                    'last_login': user.last_login,
                    'is_active': user.is_active,
                    'trading_enabled': user.trading_enabled
                } for user in users]

        except Exception as e:
            logger.error(f"Get user list error: {e}")
            return []

    def _get_user_by_username_or_email(self, identifier: str) -> Optional[User]:
        """사용자명 또는 이메일로 사용자 조회"""
        if '@' in identifier:
            return self.db_manager.get_user_by_email(identifier)
        else:
            return self.db_manager.get_user_by_username(identifier)

    def _validate_user_input(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """사용자 입력 값 검증"""
        result = {'valid': True, 'messages': []}

        # 사용자명 검증
        if not self._validate_username(username):
            result['valid'] = False
            result['messages'].append('사용자명은 3-20자의 영문, 숫자, 언더스코어만 사용 가능합니다.')

        # 이메일 검증
        if not self._validate_email(email):
            result['valid'] = False
            result['messages'].append('유효하지 않은 이메일 형식입니다.')

        # 패스워드 강도 검증
        password_validation = self.auth_manager.validate_password_strength(password)
        if not password_validation['valid']:
            result['valid'] = False
            result['messages'].extend(password_validation['messages'])

        return result

    def _validate_username(self, username: str) -> bool:
        """사용자명 형식 검증"""
        if not username or len(username) < 3 or len(username) > 20:
            return False

        # 영문, 숫자, 언더스코어만 허용
        pattern = r'^[a-zA-Z0-9_]+$'
        return bool(re.match(pattern, username))

    def _validate_email(self, email: str) -> bool:
        """이메일 형식 검증"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

# 전역 사용자 매니저 인스턴스
_user_manager = None

def get_user_manager() -> UserManager:
    """싱글톤 사용자 매니저 인스턴스 반환"""
    global _user_manager
    if _user_manager is None:
        _user_manager = UserManager()
    return _user_manager