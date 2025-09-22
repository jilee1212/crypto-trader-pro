"""
Database Initialization Script
데이터베이스 초기화 및 설정 스크립트
"""

import os
import sys
import logging
from datetime import datetime

# 상위 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database_manager import DatabaseManager
from database.models import Base

# 로그 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_database(db_path: str = "crypto_trader.db", reset: bool = False):
    """
    데이터베이스 초기화

    Args:
        db_path: 데이터베이스 파일 경로
        reset: True면 기존 데이터베이스 삭제 후 재생성
    """
    try:
        # 기존 데이터베이스 삭제 (reset=True인 경우)
        if reset and os.path.exists(db_path):
            os.remove(db_path)
            logger.info(f"Existing database {db_path} removed")

        # 데이터베이스 매니저 생성
        db_manager = DatabaseManager(db_path)
        logger.info(f"Database initialized successfully at {db_path}")

        # 데이터베이스 테이블 생성 확인
        with db_manager.get_session() as session:
            # 테이블 생성 확인 쿼리
            from sqlalchemy import text
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"Created tables: {', '.join(tables)}")

        # 테스트 사용자 생성 (개발용)
        create_test_data(db_manager)

        return db_manager

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

def create_test_data(db_manager: DatabaseManager):
    """
    테스트용 초기 데이터 생성
    """
    try:
        # 테스트 사용자 생성
        import bcrypt

        test_users = [
            {
                "username": "admin",
                "email": "admin@cryptotrader.com",
                "password": "admin123"
            },
            {
                "username": "trader1",
                "email": "trader1@example.com",
                "password": "trader123"
            }
        ]

        for user_data in test_users:
            # 패스워드 해싱
            password_hash = bcrypt.hashpw(
                user_data["password"].encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8')

            # 사용자 생성
            user = db_manager.create_user(
                username=user_data["username"],
                email=user_data["email"],
                password_hash=password_hash
            )

            if user:
                # 새 세션에서 사용자 ID 확인
                user_id = user.id
                logger.info(f"Test user created: {user.username} (ID: {user_id})")

                # 거래 설정 업데이트
                db_manager.update_trading_settings(
                    user_id=user_id,
                    risk_percentage=1.5,
                    max_positions=5,
                    daily_loss_limit=3.0,
                    symbols='["BTCUSDT", "ETHUSDT", "ADAUSDT"]'
                )

                # 테스트 API 키 저장 (테스트넷)
                with db_manager.get_session() as api_session:
                    from database.models import ApiKey
                    test_api_key = ApiKey(
                        user_id=user_id,
                        exchange="binance",
                        api_key="test_api_key_encrypted",
                        api_secret="test_api_secret_encrypted",
                        is_testnet=True
                    )
                    api_session.add(test_api_key)
                    api_session.commit()

        logger.info("Test data created successfully")

    except Exception as e:
        logger.error(f"Error creating test data: {e}")

def verify_database_structure(db_manager: DatabaseManager):
    """
    데이터베이스 구조 검증
    """
    try:
        with db_manager.get_session() as session:
            from sqlalchemy import text
            # 각 테이블의 레코드 수 확인
            tables_info = {
                'users': session.execute(text("SELECT COUNT(*) FROM users")).fetchone()[0],
                'api_keys': session.execute(text("SELECT COUNT(*) FROM api_keys")).fetchone()[0],
                'trading_settings': session.execute(text("SELECT COUNT(*) FROM trading_settings")).fetchone()[0],
                'trading_sessions': session.execute(text("SELECT COUNT(*) FROM trading_sessions")).fetchone()[0],
                'trade_history': session.execute(text("SELECT COUNT(*) FROM trade_history")).fetchone()[0],
                'notification_settings': session.execute(text("SELECT COUNT(*) FROM notification_settings")).fetchone()[0]
            }

            logger.info("Database structure verification:")
            for table, count in tables_info.items():
                logger.info(f"  {table}: {count} records")

            # 외래 키 제약 조건 확인
            session.execute(text("PRAGMA foreign_keys=ON"))
            logger.info("Foreign key constraints enabled")

            return True

    except Exception as e:
        logger.error(f"Database structure verification failed: {e}")
        return False

def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='Initialize Crypto Trader Pro Database')
    parser.add_argument('--reset', action='store_true', help='Reset existing database')
    parser.add_argument('--db-path', default='crypto_trader.db', help='Database file path')
    parser.add_argument('--no-test-data', action='store_true', help='Skip creating test data')
    parser.add_argument('--verify', action='store_true', help='Verify database structure only')

    args = parser.parse_args()

    try:
        if args.verify:
            # 기존 데이터베이스 검증만 수행
            if os.path.exists(args.db_path):
                db_manager = DatabaseManager(args.db_path)
                verify_database_structure(db_manager)
                db_manager.close()
            else:
                logger.error(f"Database file {args.db_path} not found")
                return

        else:
            # 데이터베이스 초기화
            logger.info("Starting database initialization...")
            db_manager = init_database(args.db_path, args.reset)

            # 구조 검증
            verify_database_structure(db_manager)

            # 데이터베이스 통계 출력
            stats = db_manager.get_database_stats()
            logger.info(f"Database statistics: {stats}")

            db_manager.close()
            logger.info("Database initialization completed successfully!")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()