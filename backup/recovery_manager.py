"""
Recovery Manager for Crypto Trader Pro
복구 관리 시스템
"""

import os
import shutil
import sqlite3
import gzip
import json
import tarfile
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class RecoveryManager:
    """복구 관리자 클래스"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.project_root = config.get('project_root', '.')
        self.backup_dir = config.get('backup_dir', 'backup')
        self.recovery_dir = config.get('recovery_dir', 'backup/recovery')

        # 복구 디렉토리 생성
        os.makedirs(self.recovery_dir, exist_ok=True)

    def restore_database(self, backup_path: str, target_path: Optional[str] = None) -> bool:
        """데이터베이스 복원"""
        try:
            if target_path is None:
                target_path = 'crypto_trader.db'

            # 기존 데이터베이스 백업
            if os.path.exists(target_path):
                backup_current = f"{target_path}.before_restore_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(target_path, backup_current)
                logger.info(f"Current database backed up to: {backup_current}")

            # 압축된 백업 복원
            if backup_path.endswith('.gz'):
                with gzip.open(backup_path, 'rb') as src:
                    with open(target_path, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
            else:
                shutil.copy2(backup_path, target_path)

            # 복원된 데이터베이스 검증
            if self._verify_database(target_path):
                logger.info(f"Database restored successfully from: {backup_path}")
                return True
            else:
                logger.error("Restored database failed verification")
                return False

        except Exception as e:
            logger.error(f"Failed to restore database: {e}")
            return False

    def restore_incremental_backup(self, backup_path: str, target_db: str = 'crypto_trader.db') -> bool:
        """증분 백업 복원"""
        try:
            # 증분 백업 데이터 로드
            if backup_path.endswith('.gz'):
                with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
                    backup_data = json.load(f)
            else:
                with open(backup_path, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)

            if backup_data.get('backup_type') != 'incremental':
                logger.error("Not an incremental backup file")
                return False

            # 변경사항 적용
            changes = backup_data.get('changes', {})
            applied_count = 0

            with sqlite3.connect(target_db) as conn:
                cursor = conn.cursor()

                for table, records in changes.items():
                    try:
                        for record in records:
                            # 레코드 존재 여부 확인 후 삽입/업데이트
                            if self._record_exists(cursor, table, record):
                                self._update_record(cursor, table, record)
                            else:
                                self._insert_record(cursor, table, record)
                            applied_count += 1

                    except Exception as e:
                        logger.warning(f"Failed to apply changes to {table}: {e}")

                conn.commit()

            logger.info(f"Incremental backup restored: {applied_count} changes applied")
            return True

        except Exception as e:
            logger.error(f"Failed to restore incremental backup: {e}")
            return False

    def restore_user_data(self, export_path: str, target_user_id: Optional[int] = None) -> bool:
        """사용자 데이터 복원"""
        try:
            # 사용자 데이터 로드
            if export_path.endswith('.gz'):
                with gzip.open(export_path, 'rt', encoding='utf-8') as f:
                    user_data = json.load(f)
            else:
                with open(export_path, 'r', encoding='utf-8') as f:
                    user_data = json.load(f)

            original_user_id = user_data.get('user_id')
            restore_user_id = target_user_id or original_user_id

            if not restore_user_id:
                logger.error("No target user ID specified")
                return False

            data = user_data.get('data', {})

            with sqlite3.connect('crypto_trader.db') as conn:
                cursor = conn.cursor()

                # 사용자 정보 복원 (새 사용자인 경우만)
                if 'user' in data and target_user_id is None:
                    user_info = data['user']
                    user_info['id'] = restore_user_id
                    self._restore_user_table_data(cursor, 'users', [user_info])

                # 각 테이블별 데이터 복원
                table_mappings = {
                    'api_keys': 'api_keys',
                    'trading_settings': 'trading_settings',
                    'trade_history': 'trade_history',
                    'trading_sessions': 'trading_sessions',
                    'notification_settings': 'notification_settings',
                    'web_notifications': 'web_notifications'
                }

                for data_key, table_name in table_mappings.items():
                    if data_key in data:
                        records = data[data_key]
                        if isinstance(records, list):
                            # user_id 업데이트
                            for record in records:
                                record['user_id'] = restore_user_id
                            self._restore_user_table_data(cursor, table_name, records)
                        elif isinstance(records, dict):
                            records['user_id'] = restore_user_id
                            self._restore_user_table_data(cursor, table_name, [records])

                conn.commit()

            logger.info(f"User data restored for user ID: {restore_user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore user data: {e}")
            return False

    def restore_config(self, backup_path: str, target_dir: Optional[str] = None) -> bool:
        """설정 파일 복원"""
        try:
            if target_dir is None:
                target_dir = self.project_root

            # 현재 설정 백업
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            current_backup_dir = os.path.join(self.recovery_dir, f"current_config_{timestamp}")
            os.makedirs(current_backup_dir, exist_ok=True)

            # 주요 설정 파일들 백업
            important_files = [
                'ecosystem.config.js',
                'CLAUDE.md',
                'main_platform.py',
                '.env'
            ]

            for file in important_files:
                src_path = os.path.join(target_dir, file)
                if os.path.exists(src_path):
                    dst_path = os.path.join(current_backup_dir, file)
                    shutil.copy2(src_path, dst_path)

            # 백업에서 설정 복원
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(target_dir)

            logger.info(f"Config restored from: {backup_path}")
            logger.info(f"Previous config backed up to: {current_backup_dir}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore config: {e}")
            return False

    def _verify_database(self, db_path: str) -> bool:
        """데이터베이스 무결성 검증"""
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()

                # PRAGMA 무결성 검사
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()[0]

                if result == 'ok':
                    # 필수 테이블 존재 확인
                    required_tables = ['users', 'api_keys', 'trading_settings', 'trade_history']
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    existing_tables = [row[0] for row in cursor.fetchall()]

                    for table in required_tables:
                        if table not in existing_tables:
                            logger.error(f"Required table missing: {table}")
                            return False

                    return True
                else:
                    logger.error(f"Database integrity check failed: {result}")
                    return False

        except Exception as e:
            logger.error(f"Database verification failed: {e}")
            return False

    def _record_exists(self, cursor: sqlite3.Cursor, table: str, record: Dict[str, Any]) -> bool:
        """레코드 존재 여부 확인"""
        try:
            if 'id' in record:
                cursor.execute(f"SELECT 1 FROM {table} WHERE id = ?", (record['id'],))
                return cursor.fetchone() is not None
            return False
        except Exception:
            return False

    def _insert_record(self, cursor: sqlite3.Cursor, table: str, record: Dict[str, Any]):
        """레코드 삽입"""
        columns = list(record.keys())
        placeholders = ','.join(['?' for _ in columns])
        values = [record[col] for col in columns]

        query = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
        cursor.execute(query, values)

    def _update_record(self, cursor: sqlite3.Cursor, table: str, record: Dict[str, Any]):
        """레코드 업데이트"""
        if 'id' not in record:
            return

        set_clauses = [f"{col} = ?" for col in record.keys() if col != 'id']
        values = [record[col] for col in record.keys() if col != 'id']
        values.append(record['id'])

        query = f"UPDATE {table} SET {','.join(set_clauses)} WHERE id = ?"
        cursor.execute(query, values)

    def _restore_user_table_data(self, cursor: sqlite3.Cursor, table: str, records: List[Dict[str, Any]]):
        """사용자 테이블 데이터 복원"""
        for record in records:
            try:
                if self._record_exists(cursor, table, record):
                    self._update_record(cursor, table, record)
                else:
                    self._insert_record(cursor, table, record)
            except Exception as e:
                logger.warning(f"Failed to restore record in {table}: {e}")

    def list_recovery_options(self) -> Dict[str, List[Dict[str, Any]]]:
        """복구 옵션 목록"""
        recovery_options = {
            'database_backups': [],
            'config_backups': [],
            'user_exports': []
        }

        try:
            # 데이터베이스 백업 찾기
            db_backup_dir = os.path.join(self.backup_dir, 'database')
            if os.path.exists(db_backup_dir):
                for filename in os.listdir(db_backup_dir):
                    if filename.endswith('.db') or filename.endswith('.db.gz'):
                        file_path = os.path.join(db_backup_dir, filename)
                        recovery_options['database_backups'].append({
                            'filename': filename,
                            'path': file_path,
                            'size': os.path.getsize(file_path),
                            'created': datetime.fromtimestamp(os.path.getctime(file_path))
                        })

            # 설정 백업 찾기
            config_backup_dir = os.path.join(self.backup_dir, 'configs')
            if os.path.exists(config_backup_dir):
                for filename in os.listdir(config_backup_dir):
                    if filename.endswith('.tar.gz'):
                        file_path = os.path.join(config_backup_dir, filename)
                        recovery_options['config_backups'].append({
                            'filename': filename,
                            'path': file_path,
                            'size': os.path.getsize(file_path),
                            'created': datetime.fromtimestamp(os.path.getctime(file_path))
                        })

            # 사용자 데이터 내보내기 찾기
            for filename in os.listdir(db_backup_dir):
                if filename.startswith('user_') and filename.endswith('_export.json'):
                    file_path = os.path.join(db_backup_dir, filename)
                    recovery_options['user_exports'].append({
                        'filename': filename,
                        'path': file_path,
                        'size': os.path.getsize(file_path),
                        'created': datetime.fromtimestamp(os.path.getctime(file_path))
                    })

            # 날짜 역순 정렬
            for category in recovery_options.values():
                category.sort(key=lambda x: x['created'], reverse=True)

        except Exception as e:
            logger.error(f"Failed to list recovery options: {e}")

        return recovery_options

    def create_recovery_plan(self, scenario: str) -> Dict[str, Any]:
        """복구 계획 생성"""
        plans = {
            'full_disaster': {
                'description': '전체 시스템 재해 복구',
                'steps': [
                    '1. 최신 전체 데이터베이스 백업 복원',
                    '2. 설정 파일 복원',
                    '3. 환경 설정 복원',
                    '4. 서비스 재시작',
                    '5. 무결성 검증'
                ],
                'estimated_time': '15-30 minutes',
                'required_backups': ['database_full', 'config_full']
            },
            'data_corruption': {
                'description': '데이터 손상 복구',
                'steps': [
                    '1. 손상된 데이터베이스 백업',
                    '2. 최신 정상 백업 식별',
                    '3. 데이터베이스 복원',
                    '4. 증분 백업 적용 (있는 경우)',
                    '5. 데이터 무결성 검증'
                ],
                'estimated_time': '10-20 minutes',
                'required_backups': ['database_full', 'database_incremental']
            },
            'user_data_loss': {
                'description': '특정 사용자 데이터 복구',
                'steps': [
                    '1. 사용자 데이터 내보내기 파일 식별',
                    '2. 백업 데이터 검증',
                    '3. 사용자 데이터 복원',
                    '4. 거래 이력 검증'
                ],
                'estimated_time': '5-10 minutes',
                'required_backups': ['user_export']
            },
            'config_rollback': {
                'description': '설정 파일 롤백',
                'steps': [
                    '1. 현재 설정 백업',
                    '2. 이전 설정 복원',
                    '3. 서비스 재시작',
                    '4. 기능 테스트'
                ],
                'estimated_time': '5-15 minutes',
                'required_backups': ['config_full']
            }
        }

        return plans.get(scenario, {
            'description': '알 수 없는 복구 시나리오',
            'steps': ['수동 복구 필요'],
            'estimated_time': 'Unknown',
            'required_backups': []
        })