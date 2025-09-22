"""
Database Manager for Crypto Trader Pro
데이터베이스 CRUD 작업 및 연결 관리
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
import os
import logging
from typing import List, Optional, Dict, Any

from .models import Base, User, ApiKey, TradingSettings, TradingSession, TradeHistory, NotificationSettings

# 로그 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """데이터베이스 관리 클래스"""

    def __init__(self, db_path: str = "crypto_trader.db"):
        """
        데이터베이스 매니저 초기화

        Args:
            db_path: SQLite 데이터베이스 파일 경로
        """
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # 데이터베이스 테이블 생성
        self.create_tables()

    def create_tables(self):
        """모든 테이블 생성"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error creating tables: {e}")
            raise

    @contextmanager
    def get_session(self):
        """데이터베이스 세션 컨텍스트 매니저"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    # ============================================================================
    # User 관련 메서드
    # ============================================================================

    def create_user(self, username: str, email: str, password_hash: str) -> Optional[User]:
        """새 사용자 생성"""
        try:
            with self.get_session() as session:
                # 중복 체크
                existing_user = session.query(User).filter(
                    (User.username == username) | (User.email == email)
                ).first()

                if existing_user:
                    logger.warning(f"User already exists: {username} or {email}")
                    return None

                user = User(
                    username=username,
                    email=email,
                    password_hash=password_hash
                )
                session.add(user)
                session.flush()  # ID 할당을 위해

                # 사용자 ID 저장 (세션 밖에서 사용하기 위해)
                user_id = user.id

                # 기본 거래 설정 생성
                self._create_default_trading_settings(session, user_id)
                # 기본 알림 설정 생성
                self._create_default_notification_settings(session, user_id)

                logger.info(f"User created successfully: {username}")

            # 새 세션에서 사용자 조회하여 반환
            return self.get_user_by_username(username)

        except SQLAlchemyError as e:
            logger.error(f"Error creating user: {e}")
            return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """사용자명으로 사용자 조회"""
        try:
            with self.get_session() as session:
                user = session.query(User).filter(User.username == username).first()
                if user:
                    # 객체를 세션에서 분리 (detach)
                    session.expunge(user)
                return user
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by username: {e}")
            return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """이메일로 사용자 조회"""
        try:
            with self.get_session() as session:
                user = session.query(User).filter(User.email == email).first()
                if user:
                    # 객체를 세션에서 분리 (detach)
                    session.expunge(user)
                return user
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by email: {e}")
            return None

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """ID로 사용자 조회"""
        try:
            with self.get_session() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if user:
                    # 객체를 세션에서 분리 (detach)
                    session.expunge(user)
                return user
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by ID: {e}")
            return None

    def update_user_login(self, user_id: int) -> bool:
        """사용자 로그인 시간 업데이트"""
        try:
            with self.get_session() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if user:
                    from datetime import datetime
                    user.last_login = datetime.utcnow()
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"Error updating user login: {e}")
            return False

    def enable_user_trading(self, user_id: int, enabled: bool = True) -> bool:
        """사용자 거래 활성화/비활성화"""
        try:
            with self.get_session() as session:
                user = session.query(User).filter(User.id == user_id).first()
                if user:
                    user.trading_enabled = enabled
                    logger.info(f"User {user_id} trading {'enabled' if enabled else 'disabled'}")
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"Error updating user trading status: {e}")
            return False

    def get_active_trading_users(self) -> List[User]:
        """거래 활성화된 사용자 목록 조회"""
        try:
            with self.get_session() as session:
                users = session.query(User).filter(
                    User.is_active == True,
                    User.trading_enabled == True
                ).all()
                # 모든 객체를 세션에서 분리 (detach)
                for user in users:
                    session.expunge(user)
                return users
        except SQLAlchemyError as e:
            logger.error(f"Error getting active trading users: {e}")
            return []

    # ============================================================================
    # API Key 관련 메서드
    # ============================================================================

    def save_api_key(self, user_id: int, exchange: str, api_key: str,
                     api_secret: str, is_testnet: bool = True) -> Optional[ApiKey]:
        """API 키 저장 (암호화된 상태로)"""
        try:
            with self.get_session() as session:
                # 기존 API 키 비활성화
                existing_keys = session.query(ApiKey).filter(
                    ApiKey.user_id == user_id,
                    ApiKey.exchange == exchange,
                    ApiKey.is_testnet == is_testnet
                ).all()

                for key in existing_keys:
                    key.is_active = False

                # 새 API 키 추가
                new_key = ApiKey(
                    user_id=user_id,
                    exchange=exchange,
                    api_key=api_key,  # 실제로는 암호화된 상태로 저장
                    api_secret=api_secret,  # 실제로는 암호화된 상태로 저장
                    is_testnet=is_testnet
                )
                session.add(new_key)
                session.flush()  # Ensure object is created in database

                # 객체를 세션에서 분리 (detach)
                session.expunge(new_key)

                logger.info(f"API key saved for user {user_id}, exchange {exchange}")
                return new_key

        except SQLAlchemyError as e:
            logger.error(f"Error saving API key: {e}")
            return None

    def get_user_api_key(self, user_id: int, exchange: str,
                         is_testnet: bool = True) -> Optional[ApiKey]:
        """사용자의 활성 API 키 조회"""
        try:
            with self.get_session() as session:
                api_key = session.query(ApiKey).filter(
                    ApiKey.user_id == user_id,
                    ApiKey.exchange == exchange,
                    ApiKey.is_testnet == is_testnet,
                    ApiKey.is_active == True
                ).first()
                if api_key:
                    # 객체를 세션에서 분리 (detach)
                    session.expunge(api_key)
                return api_key
        except SQLAlchemyError as e:
            logger.error(f"Error getting user API key: {e}")
            return None

    def delete_api_key(self, user_id: int, api_key_id: int) -> bool:
        """API 키 삭제"""
        try:
            with self.get_session() as session:
                api_key = session.query(ApiKey).filter(
                    ApiKey.id == api_key_id,
                    ApiKey.user_id == user_id
                ).first()

                if api_key:
                    session.delete(api_key)
                    logger.info(f"API key {api_key_id} deleted for user {user_id}")
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"Error deleting API key: {e}")
            return False

    # ============================================================================
    # Trading Settings 관련 메서드
    # ============================================================================

    def _create_default_trading_settings(self, session: Session, user_id: int):
        """기본 거래 설정 생성"""
        default_settings = TradingSettings(
            user_id=user_id,
            risk_percentage=2.0,
            max_positions=3,
            daily_loss_limit=5.0,
            auto_trading_enabled=False,
            symbols='["BTCUSDT", "ETHUSDT"]'
        )
        session.add(default_settings)

    def get_user_trading_settings(self, user_id: int) -> Optional[TradingSettings]:
        """사용자 거래 설정 조회"""
        try:
            with self.get_session() as session:
                settings = session.query(TradingSettings).filter(
                    TradingSettings.user_id == user_id
                ).first()
                if settings:
                    # 객체를 세션에서 분리 (detach)
                    session.expunge(settings)
                return settings
        except SQLAlchemyError as e:
            logger.error(f"Error getting trading settings: {e}")
            return None

    def update_trading_settings(self, user_id: int, **kwargs) -> bool:
        """거래 설정 업데이트"""
        try:
            with self.get_session() as session:
                settings = session.query(TradingSettings).filter(
                    TradingSettings.user_id == user_id
                ).first()

                if settings:
                    for key, value in kwargs.items():
                        if hasattr(settings, key):
                            setattr(settings, key, value)

                    from datetime import datetime
                    settings.updated_at = datetime.utcnow()

                    logger.info(f"Trading settings updated for user {user_id}")
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"Error updating trading settings: {e}")
            return False

    # ============================================================================
    # Trading Session 관련 메서드
    # ============================================================================

    def start_trading_session(self, user_id: int) -> Optional[TradingSession]:
        """거래 세션 시작"""
        try:
            with self.get_session() as session:
                # 기존 활성 세션 종료
                active_sessions = session.query(TradingSession).filter(
                    TradingSession.user_id == user_id,
                    TradingSession.is_active == True
                ).all()

                for active_session in active_sessions:
                    from datetime import datetime
                    active_session.session_end = datetime.utcnow()
                    active_session.is_active = False

                # 새 세션 생성
                new_session = TradingSession(user_id=user_id)
                session.add(new_session)
                session.flush()

                logger.info(f"Trading session started for user {user_id}")
                return new_session

        except SQLAlchemyError as e:
            logger.error(f"Error starting trading session: {e}")
            return None

    def end_trading_session(self, user_id: int, session_id: int) -> bool:
        """거래 세션 종료"""
        try:
            with self.get_session() as session:
                trading_session = session.query(TradingSession).filter(
                    TradingSession.id == session_id,
                    TradingSession.user_id == user_id,
                    TradingSession.is_active == True
                ).first()

                if trading_session:
                    from datetime import datetime
                    trading_session.session_end = datetime.utcnow()
                    trading_session.is_active = False

                    logger.info(f"Trading session {session_id} ended for user {user_id}")
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"Error ending trading session: {e}")
            return False

    def get_active_trading_session(self, user_id: int) -> Optional[TradingSession]:
        """활성 거래 세션 조회"""
        try:
            with self.get_session() as session:
                trading_session = session.query(TradingSession).filter(
                    TradingSession.user_id == user_id,
                    TradingSession.is_active == True
                ).first()
                if trading_session:
                    # 객체를 세션에서 분리 (detach)
                    session.expunge(trading_session)
                return trading_session
        except SQLAlchemyError as e:
            logger.error(f"Error getting active trading session: {e}")
            return None

    # ============================================================================
    # Trade History 관련 메서드
    # ============================================================================

    def record_trade(self, user_id: int, session_id: Optional[int], symbol: str,
                     side: str, amount: float, price: float,
                     profit_loss: Optional[float] = None,
                     signal_confidence: Optional[int] = None) -> Optional[TradeHistory]:
        """거래 기록 저장"""
        try:
            with self.get_session() as session:
                trade = TradeHistory(
                    user_id=user_id,
                    session_id=session_id,
                    symbol=symbol,
                    side=side,
                    amount=amount,
                    price=price,
                    profit_loss=profit_loss,
                    signal_confidence=signal_confidence
                )
                session.add(trade)

                # 세션 거래 수 업데이트
                if session_id:
                    trading_session = session.query(TradingSession).filter(
                        TradingSession.id == session_id
                    ).first()
                    if trading_session:
                        trading_session.total_trades += 1
                        if profit_loss:
                            trading_session.profit_loss += profit_loss

                logger.info(f"Trade recorded: {symbol} {side} {amount} @ {price}")
                return trade

        except SQLAlchemyError as e:
            logger.error(f"Error recording trade: {e}")
            return None

    def get_user_trades(self, user_id: int, limit: int = 100) -> List[TradeHistory]:
        """사용자 거래 기록 조회"""
        try:
            with self.get_session() as session:
                trades = session.query(TradeHistory).filter(
                    TradeHistory.user_id == user_id
                ).order_by(TradeHistory.timestamp.desc()).limit(limit).all()
                # 모든 객체를 세션에서 분리 (detach)
                for trade in trades:
                    session.expunge(trade)
                return trades
        except SQLAlchemyError as e:
            logger.error(f"Error getting user trades: {e}")
            return []

    def get_session_trades(self, session_id: int) -> List[TradeHistory]:
        """세션별 거래 기록 조회"""
        try:
            with self.get_session() as session:
                trades = session.query(TradeHistory).filter(
                    TradeHistory.session_id == session_id
                ).order_by(TradeHistory.timestamp.desc()).all()
                # 모든 객체를 세션에서 분리 (detach)
                for trade in trades:
                    session.expunge(trade)
                return trades
        except SQLAlchemyError as e:
            logger.error(f"Error getting session trades: {e}")
            return []

    # ============================================================================
    # Notification Settings 관련 메서드
    # ============================================================================

    def _create_default_notification_settings(self, session: Session, user_id: int):
        """기본 알림 설정 생성"""
        default_notification = NotificationSettings(user_id=user_id)
        session.add(default_notification)

    def get_user_notification_settings(self, user_id: int) -> Optional[NotificationSettings]:
        """사용자 알림 설정 조회"""
        try:
            with self.get_session() as session:
                settings = session.query(NotificationSettings).filter(
                    NotificationSettings.user_id == user_id
                ).first()
                if settings:
                    # 객체를 세션에서 분리 (detach)
                    session.expunge(settings)
                return settings
        except SQLAlchemyError as e:
            logger.error(f"Error getting notification settings: {e}")
            return None

    def update_notification_settings(self, user_id: int, **kwargs) -> bool:
        """알림 설정 업데이트"""
        try:
            with self.get_session() as session:
                settings = session.query(NotificationSettings).filter(
                    NotificationSettings.user_id == user_id
                ).first()

                if settings:
                    for key, value in kwargs.items():
                        if hasattr(settings, key):
                            setattr(settings, key, value)

                    from datetime import datetime
                    settings.updated_at = datetime.utcnow()

                    logger.info(f"Notification settings updated for user {user_id}")
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"Error updating notification settings: {e}")
            return False

    # ============================================================================
    # 데이터베이스 유틸리티 메서드
    # ============================================================================

    def backup_database(self, backup_path: str) -> bool:
        """데이터베이스 백업"""
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backed up to {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error backing up database: {e}")
            return False

    def get_database_stats(self) -> Dict[str, Any]:
        """데이터베이스 통계 조회"""
        try:
            with self.get_session() as session:
                stats = {
                    'total_users': session.query(User).count(),
                    'active_users': session.query(User).filter(User.is_active == True).count(),
                    'trading_enabled_users': session.query(User).filter(User.trading_enabled == True).count(),
                    'total_trades': session.query(TradeHistory).count(),
                    'active_sessions': session.query(TradingSession).filter(TradingSession.is_active == True).count(),
                    'total_api_keys': session.query(ApiKey).filter(ApiKey.is_active == True).count()
                }
                return stats
        except SQLAlchemyError as e:
            logger.error(f"Error getting database stats: {e}")
            return {}

    def close(self):
        """데이터베이스 연결 종료"""
        self.engine.dispose()
        logger.info("Database connection closed")

# 전역 데이터베이스 매니저 인스턴스
_db_manager = None

def get_db_manager() -> DatabaseManager:
    """싱글톤 데이터베이스 매니저 인스턴스 반환"""
    global _db_manager
    if _db_manager is None:
        db_path = os.path.join(os.path.dirname(__file__), "..", "crypto_trader.db")
        _db_manager = DatabaseManager(db_path)
    return _db_manager