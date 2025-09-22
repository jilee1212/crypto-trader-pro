#!/usr/bin/env python3
"""
Database Migration Script for Crypto Trader Pro
SQLite 데이터베이스 스키마 마이그레이션 - updated_at 컬럼 추가
"""

import os
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def backup_database(db_path: str) -> str:
    """데이터베이스 백업"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"

    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        logger.info(f"데이터베이스 백업 완료: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"데이터베이스 백업 실패: {e}")
        raise

def check_column_exists(cursor, table_name: str, column_name: str) -> bool:
    """컬럼 존재 여부 확인"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def migrate_api_keys_table(cursor):
    """api_keys 테이블에 updated_at 컬럼 추가"""
    table_name = "api_keys"
    column_name = "updated_at"

    if check_column_exists(cursor, table_name, column_name):
        logger.info(f"{table_name}.{column_name} 컬럼이 이미 존재합니다.")
        return

    try:
        # updated_at 컬럼 추가
        cursor.execute(f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name} DATETIME DEFAULT CURRENT_TIMESTAMP
        """)

        # 기존 레코드에 현재 시간 설정
        cursor.execute(f"""
            UPDATE {table_name}
            SET {column_name} = CURRENT_TIMESTAMP
            WHERE {column_name} IS NULL
        """)

        logger.info(f"{table_name}.{column_name} 컬럼 추가 완료")

    except Exception as e:
        logger.error(f"{table_name} 테이블 마이그레이션 실패: {e}")
        raise

def migrate_notification_settings_table(cursor):
    """notification_settings 테이블에 updated_at 컬럼 추가"""
    table_name = "notification_settings"
    column_name = "updated_at"

    # 테이블 존재 여부 확인
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name=?
    """, (table_name,))

    if not cursor.fetchone():
        logger.info(f"{table_name} 테이블이 존재하지 않습니다. 스킵합니다.")
        return

    if check_column_exists(cursor, table_name, column_name):
        logger.info(f"{table_name}.{column_name} 컬럼이 이미 존재합니다.")
        return

    try:
        cursor.execute(f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name} DATETIME DEFAULT CURRENT_TIMESTAMP
        """)

        cursor.execute(f"""
            UPDATE {table_name}
            SET {column_name} = CURRENT_TIMESTAMP
            WHERE {column_name} IS NULL
        """)

        logger.info(f"{table_name}.{column_name} 컬럼 추가 완료")

    except Exception as e:
        logger.error(f"{table_name} 테이블 마이그레이션 실패: {e}")
        raise

def migrate_trading_settings_table(cursor):
    """trading_settings 테이블에 updated_at 컬럼 추가"""
    table_name = "trading_settings"
    column_name = "updated_at"

    # 테이블 존재 여부 확인
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name=?
    """, (table_name,))

    if not cursor.fetchone():
        logger.info(f"{table_name} 테이블이 존재하지 않습니다. 스킵합니다.")
        return

    if check_column_exists(cursor, table_name, column_name):
        logger.info(f"{table_name}.{column_name} 컬럼이 이미 존재합니다.")
        return

    try:
        cursor.execute(f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name} DATETIME DEFAULT CURRENT_TIMESTAMP
        """)

        cursor.execute(f"""
            UPDATE {table_name}
            SET {column_name} = CURRENT_TIMESTAMP
            WHERE {column_name} IS NULL
        """)

        logger.info(f"{table_name}.{column_name} 컬럼 추가 완료")

    except Exception as e:
        logger.error(f"{table_name} 테이블 마이그레이션 실패: {e}")
        raise

def run_migration(db_path: str = None):
    """마이그레이션 실행"""
    if not db_path:
        # 기본 데이터베이스 경로
        current_dir = Path(__file__).parent.parent
        db_path = current_dir / "crypto_trading.db"

    if not os.path.exists(db_path):
        logger.error(f"데이터베이스 파일을 찾을 수 없습니다: {db_path}")
        return False

    logger.info(f"데이터베이스 마이그레이션 시작: {db_path}")

    try:
        # 데이터베이스 백업
        backup_path = backup_database(str(db_path))

        # 마이그레이션 실행
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()

            # 외래 키 제약 조건 비활성화
            cursor.execute("PRAGMA foreign_keys = OFF")

            try:
                # 각 테이블 마이그레이션
                migrate_api_keys_table(cursor)
                migrate_notification_settings_table(cursor)
                migrate_trading_settings_table(cursor)

                # 변경사항 커밋
                conn.commit()
                logger.info("마이그레이션 완료")

                # 외래 키 제약 조건 다시 활성화
                cursor.execute("PRAGMA foreign_keys = ON")

                # 데이터베이스 무결성 검사
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                if result[0] == "ok":
                    logger.info("데이터베이스 무결성 검사 통과")
                else:
                    logger.warning(f"데이터베이스 무결성 검사 결과: {result}")

                return True

            except Exception as e:
                conn.rollback()
                logger.error(f"마이그레이션 실패, 롤백 실행: {e}")
                raise

    except Exception as e:
        logger.error(f"마이그레이션 오류: {e}")
        logger.info(f"백업 파일에서 복원 가능: {backup_path}")
        return False

def verify_migration(db_path: str = None):
    """마이그레이션 결과 검증"""
    if not db_path:
        current_dir = Path(__file__).parent.parent
        db_path = current_dir / "crypto_trading.db"

    logger.info("마이그레이션 결과 검증 중...")

    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()

            # api_keys 테이블 스키마 확인
            cursor.execute("PRAGMA table_info(api_keys)")
            columns = [row[1] for row in cursor.fetchall()]

            if "updated_at" in columns:
                logger.info("OK: api_keys.updated_at column found")
            else:
                logger.error("ERROR: api_keys.updated_at column missing")
                return False

            # 데이터 확인
            cursor.execute("SELECT COUNT(*) FROM api_keys WHERE updated_at IS NOT NULL")
            count = cursor.fetchone()[0]
            logger.info(f"api_keys 테이블에 updated_at 값이 있는 레코드: {count}개")

            return True

    except Exception as e:
        logger.error(f"검증 오류: {e}")
        return False

if __name__ == "__main__":
    import sys

    print("Crypto Trader Pro - Database Migration")
    print("=" * 50)

    # 명령행 인수 처리
    db_path = None
    if len(sys.argv) > 1:
        db_path = sys.argv[1]

    # 마이그레이션 실행
    success = run_migration(db_path)

    if success:
        print("Migration Success!")

        # 검증 실행
        if verify_migration(db_path):
            print("Verification Complete!")
            print("\nDatabase migration completed successfully.")
        else:
            print("Verification Failed!")
            sys.exit(1)
    else:
        print("Migration Failed!")
        sys.exit(1)