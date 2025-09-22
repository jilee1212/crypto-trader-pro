"""
API Manager - Crypto Trader Pro
API 키 관리 시스템 - 암호화 저장, 인증, 다중 거래소 지원
"""

import os
import logging
from typing import Optional, Tuple, Dict, Any
from cryptography.fernet import Fernet
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from .models import ApiKey, User
from .database_manager import get_db_manager

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIManager:
    """API 키 관리 클래스"""

    def __init__(self):
        """API 매니저 초기화"""
        self.db_manager = get_db_manager()
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)

    def _get_or_create_encryption_key(self) -> bytes:
        """암호화 키 생성 또는 로드"""
        key_file = os.path.join(os.path.dirname(__file__), 'encryption.key')

        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # 새 키 생성
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            logger.info("새로운 암호화 키가 생성되었습니다.")
            return key

    def save_api_key(self, user_id: int, exchange: str, api_key: str,
                     api_secret: str, is_testnet: bool = True) -> bool:
        """API 키 저장 (암호화)"""
        try:
            # 기존 키 삭제 (업데이트를 위해)
            self.delete_api_key(user_id, exchange, is_testnet)

            # 새 키 암호화 및 저장
            encrypted_key = self.cipher_suite.encrypt(api_key.encode())
            encrypted_secret = self.cipher_suite.encrypt(api_secret.encode())

            with self.db_manager.get_session() as session:
                api_key_obj = ApiKey(
                    user_id=user_id,
                    exchange=exchange,
                    api_key=encrypted_key,
                    api_secret=encrypted_secret,
                    is_testnet=is_testnet
                )

                session.add(api_key_obj)
                session.commit()
                session.flush()
                session.expunge(api_key_obj)

                logger.info(f"API 키가 저장되었습니다: 사용자 {user_id}, 거래소 {exchange}")
                return True

        except Exception as e:
            logger.error(f"API 키 저장 오류: {e}")
            return False

    def get_api_credentials(self, user_id: int, exchange: str,
                          is_testnet: bool = True) -> Optional[Tuple[str, str]]:
        """API 키 조회 (복호화)"""
        try:
            with self.db_manager.get_session() as session:
                api_key_obj = session.query(ApiKey).filter(
                    ApiKey.user_id == user_id,
                    ApiKey.exchange == exchange,
                    ApiKey.is_testnet == is_testnet
                ).first()

                if api_key_obj:
                    # 복호화
                    decrypted_key = self.cipher_suite.decrypt(api_key_obj.api_key).decode()
                    decrypted_secret = self.cipher_suite.decrypt(api_key_obj.api_secret).decode()

                    return (decrypted_key, decrypted_secret)

                return None

        except Exception as e:
            logger.error(f"API 키 조회 오류: {e}")
            return None

    def delete_api_key(self, user_id: int, exchange: str,
                      is_testnet: bool = True) -> bool:
        """API 키 삭제"""
        try:
            with self.db_manager.get_session() as session:
                deleted_count = session.query(ApiKey).filter(
                    ApiKey.user_id == user_id,
                    ApiKey.exchange == exchange,
                    ApiKey.is_testnet == is_testnet
                ).delete()

                session.commit()

                if deleted_count > 0:
                    logger.info(f"API 키가 삭제되었습니다: 사용자 {user_id}, 거래소 {exchange}")
                    return True
                else:
                    logger.warning(f"삭제할 API 키를 찾을 수 없습니다: 사용자 {user_id}, 거래소 {exchange}")
                    return False

        except Exception as e:
            logger.error(f"API 키 삭제 오류: {e}")
            return False

    def list_user_api_keys(self, user_id: int) -> Dict[str, Any]:
        """사용자의 모든 API 키 목록 조회"""
        try:
            with self.db_manager.get_session() as session:
                api_keys = session.query(ApiKey).filter(
                    ApiKey.user_id == user_id
                ).all()

                result = {}
                for api_key in api_keys:
                    key_name = f"{api_key.exchange}_{'testnet' if api_key.is_testnet else 'mainnet'}"
                    result[key_name] = {
                        'exchange': api_key.exchange,
                        'is_testnet': api_key.is_testnet,
                        'created_at': api_key.created_at,
                        'updated_at': api_key.updated_at
                    }

                return result

        except Exception as e:
            logger.error(f"API 키 목록 조회 오류: {e}")
            return {}

    def validate_api_connection(self, user_id: int, exchange: str,
                              is_testnet: bool = True) -> Dict[str, Any]:
        """API 연결 상태 검증"""
        try:
            credentials = self.get_api_credentials(user_id, exchange, is_testnet)

            if not credentials:
                return {
                    'success': False,
                    'error': 'API 키를 찾을 수 없습니다.'
                }

            api_key, api_secret = credentials

            # 거래소별 연결 테스트
            if exchange.lower() == 'binance':
                from binance_testnet_connector import BinanceTestnetConnector
                connector = BinanceTestnetConnector()

                # 계좌 정보 조회로 연결 테스트
                result = connector.get_account_info(api_key, api_secret)

                if result.get('success'):
                    return {
                        'success': True,
                        'message': 'API 연결이 성공했습니다.',
                        'account_info': result.get('data', {})
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('error', 'API 연결 실패')
                    }
            else:
                return {
                    'success': False,
                    'error': f'지원되지 않는 거래소: {exchange}'
                }

        except Exception as e:
            logger.error(f"API 연결 검증 오류: {e}")
            return {
                'success': False,
                'error': f'연결 검증 중 오류 발생: {str(e)}'
            }


# 싱글톤 인스턴스
_api_manager_instance = None

def get_api_manager() -> APIManager:
    """API 매니저 싱글톤 인스턴스 반환"""
    global _api_manager_instance
    if _api_manager_instance is None:
        _api_manager_instance = APIManager()
    return _api_manager_instance