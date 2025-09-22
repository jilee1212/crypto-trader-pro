"""
Encryption System for Crypto Trader Pro
API 키 및 민감 정보 암호화 시스템
"""

import os
import base64
import hashlib
import secrets
import logging
from typing import Optional, Union, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# 로그 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EncryptionManager:
    """암호화 관리 클래스"""

    def __init__(self, master_key: Optional[str] = None):
        """
        암호화 매니저 초기화

        Args:
            master_key: 마스터 키 (없으면 자동 생성/로드)
        """
        self.master_key = master_key or self._get_or_create_master_key()
        self.fernet = self._create_fernet_instance()

    def _get_or_create_master_key(self) -> str:
        """
        마스터 키 생성 또는 로드

        Returns:
            마스터 키
        """
        key_file = os.path.join(os.path.dirname(__file__), "..", ".master_key")

        if os.path.exists(key_file):
            try:
                with open(key_file, 'rb') as f:
                    return f.read().decode('utf-8')
            except Exception as e:
                logger.warning(f"Failed to load master key: {e}")
                # 기존 키 파일에 문제가 있으면 새로 생성

        # 새 마스터 키 생성
        master_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')

        try:
            with open(key_file, 'wb') as f:
                f.write(master_key.encode('utf-8'))

            # 파일 권한 설정 (읽기 전용)
            os.chmod(key_file, 0o600)
            logger.info("New master key generated and saved")

        except Exception as e:
            logger.error(f"Failed to save master key: {e}")
            # 파일 저장에 실패해도 메모리에서 사용

        return master_key

    def _create_fernet_instance(self) -> Fernet:
        """
        Fernet 암호화 인스턴스 생성

        Returns:
            Fernet 인스턴스
        """
        try:
            # 마스터 키를 사용하여 Fernet 키 생성
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'crypto_trader_salt',  # 실제로는 랜덤 솔트 사용
                iterations=100000,
            )

            key = base64.urlsafe_b64encode(
                kdf.derive(self.master_key.encode('utf-8'))
            )

            return Fernet(key)

        except Exception as e:
            logger.error(f"Failed to create Fernet instance: {e}")
            raise

    def encrypt(self, data: Union[str, bytes]) -> str:
        """
        데이터 암호화

        Args:
            data: 암호화할 데이터

        Returns:
            암호화된 데이터 (Base64 인코딩)
        """
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')

            encrypted = self.fernet.encrypt(data)
            return base64.urlsafe_b64encode(encrypted).decode('utf-8')

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, encrypted_data: str) -> str:
        """
        데이터 복호화

        Args:
            encrypted_data: 암호화된 데이터 (Base64 인코딩)

        Returns:
            복호화된 데이터
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted = self.fernet.decrypt(encrypted_bytes)
            return decrypted.decode('utf-8')

        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def encrypt_api_credentials(self, api_key: str, api_secret: str) -> Tuple[str, str]:
        """
        API 자격 증명 암호화

        Args:
            api_key: API 키
            api_secret: API 시크릿

        Returns:
            (암호화된 API 키, 암호화된 API 시크릿)
        """
        try:
            encrypted_key = self.encrypt(api_key)
            encrypted_secret = self.encrypt(api_secret)

            logger.info("API credentials encrypted successfully")
            return encrypted_key, encrypted_secret

        except Exception as e:
            logger.error(f"API credentials encryption failed: {e}")
            raise

    def decrypt_api_credentials(self, encrypted_key: str, encrypted_secret: str) -> Tuple[str, str]:
        """
        API 자격 증명 복호화

        Args:
            encrypted_key: 암호화된 API 키
            encrypted_secret: 암호화된 API 시크릿

        Returns:
            (API 키, API 시크릿)
        """
        try:
            api_key = self.decrypt(encrypted_key)
            api_secret = self.decrypt(encrypted_secret)

            logger.info("API credentials decrypted successfully")
            return api_key, api_secret

        except Exception as e:
            logger.error(f"API credentials decryption failed: {e}")
            raise

    def generate_api_key_hash(self, api_key: str) -> str:
        """
        API 키 해시 생성 (검증용)

        Args:
            api_key: API 키

        Returns:
            해시값
        """
        return hashlib.sha256(api_key.encode('utf-8')).hexdigest()

    def verify_encryption_integrity(self, original_data: str, encrypted_data: str) -> bool:
        """
        암호화 무결성 검증

        Args:
            original_data: 원본 데이터
            encrypted_data: 암호화된 데이터

        Returns:
            무결성 검증 결과
        """
        try:
            decrypted = self.decrypt(encrypted_data)
            return original_data == decrypted
        except Exception:
            return False

class SecureStorage:
    """보안 저장소 클래스"""

    def __init__(self, encryption_manager: EncryptionManager):
        self.encryption = encryption_manager

    def store_sensitive_data(self, file_path: str, data: dict) -> bool:
        """
        민감한 데이터를 암호화하여 저장

        Args:
            file_path: 저장할 파일 경로
            data: 저장할 데이터

        Returns:
            저장 성공 여부
        """
        try:
            import json

            # 데이터를 JSON으로 직렬화
            json_data = json.dumps(data, ensure_ascii=False, indent=2)

            # 암호화
            encrypted_data = self.encryption.encrypt(json_data)

            # 파일에 저장
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(encrypted_data)

            # 파일 권한 설정
            os.chmod(file_path, 0o600)

            logger.info(f"Sensitive data stored securely: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to store sensitive data: {e}")
            return False

    def load_sensitive_data(self, file_path: str) -> Optional[dict]:
        """
        암호화된 민감한 데이터 로드

        Args:
            file_path: 파일 경로

        Returns:
            복호화된 데이터 또는 None
        """
        try:
            import json

            if not os.path.exists(file_path):
                return None

            # 암호화된 데이터 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                encrypted_data = f.read()

            # 복호화
            decrypted_data = self.encryption.decrypt(encrypted_data)

            # JSON 파싱
            data = json.loads(decrypted_data)

            logger.info(f"Sensitive data loaded successfully: {file_path}")
            return data

        except Exception as e:
            logger.error(f"Failed to load sensitive data: {e}")
            return None

class PasswordManager:
    """패스워드 관리 클래스"""

    @staticmethod
    def generate_secure_password(length: int = 16) -> str:
        """
        보안 패스워드 생성

        Args:
            length: 패스워드 길이

        Returns:
            생성된 패스워드
        """
        import string

        if length < 8:
            length = 8

        # 문자 세트 정의
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?"

        # 각 카테고리에서 최소 1개씩 선택
        password = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
            secrets.choice(symbols)
        ]

        # 나머지 길이를 모든 문자로 채움
        all_chars = lowercase + uppercase + digits + symbols
        for _ in range(length - 4):
            password.append(secrets.choice(all_chars))

        # 패스워드 섞기
        secrets.SystemRandom().shuffle(password)

        return ''.join(password)

    @staticmethod
    def generate_api_key() -> str:
        """
        API 키 형태의 문자열 생성

        Returns:
            API 키 형태 문자열
        """
        return secrets.token_urlsafe(32)

    @staticmethod
    def mask_sensitive_string(sensitive_string: str, visible_chars: int = 4) -> str:
        """
        민감한 문자열 마스킹

        Args:
            sensitive_string: 마스킹할 문자열
            visible_chars: 보여줄 문자 수

        Returns:
            마스킹된 문자열
        """
        if len(sensitive_string) <= visible_chars:
            return "*" * len(sensitive_string)

        visible_part = sensitive_string[:visible_chars]
        masked_part = "*" * (len(sensitive_string) - visible_chars)

        return visible_part + masked_part

# 전역 암호화 매니저 인스턴스
_encryption_manager = None

def get_encryption_manager() -> EncryptionManager:
    """싱글톤 암호화 매니저 인스턴스 반환"""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager

def get_secure_storage() -> SecureStorage:
    """보안 저장소 인스턴스 반환"""
    return SecureStorage(get_encryption_manager())