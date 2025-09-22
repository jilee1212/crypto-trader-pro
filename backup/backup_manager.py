"""
Backup Manager for Crypto Trader Pro
백업 관리 시스템 통합 관리자
"""

import asyncio
import schedule
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
import threading

from .database_backup import DatabaseBackup
from .config_backup import ConfigBackup
from .recovery_manager import RecoveryManager

logger = logging.getLogger(__name__)

class BackupManager:
    """백업 시스템 통합 관리자"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('enabled', True)
        self.auto_backup_enabled = config.get('auto_backup_enabled', True)

        # 백업 컴포넌트 초기화
        self.database_backup = DatabaseBackup(config.get('database', {}))
        self.config_backup = ConfigBackup(config.get('config', {}))
        self.recovery_manager = RecoveryManager(config.get('recovery', {}))

        # 스케줄링
        self.scheduler_thread = None
        self.is_running = False

        # 자동 백업 설정
        if self.auto_backup_enabled:
            self._setup_automatic_backups()

    def _setup_automatic_backups(self):
        """자동 백업 스케줄 설정"""
        try:
            # 일일 전체 백업 (오전 2시)
            schedule.every().day.at("02:00").do(self._scheduled_full_backup)

            # 4시간마다 증분 백업
            schedule.every(4).hours.do(self._scheduled_incremental_backup)

            # 주간 설정 백업 (일요일 오전 3시)
            schedule.every().sunday.at("03:00").do(self._scheduled_config_backup)

            # 월간 정리 작업 (매월 1일 오전 4시) - 30일마다 실행
            schedule.every(30).days.do(self._scheduled_cleanup)

            logger.info("Automatic backup schedule configured")

        except Exception as e:
            logger.error(f"Failed to setup automatic backups: {e}")

    def start_scheduler(self):
        """백업 스케줄러 시작"""
        if not self.auto_backup_enabled or self.is_running:
            return

        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("Backup scheduler started")

    def stop_scheduler(self):
        """백업 스케줄러 중지"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("Backup scheduler stopped")

    def _run_scheduler(self):
        """스케줄러 실행"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # 1분마다 체크
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)

    def _scheduled_full_backup(self):
        """스케줄된 전체 백업"""
        try:
            logger.info("Starting scheduled full backup")
            backup_path = self.database_backup.create_full_backup()
            if backup_path:
                logger.info(f"Scheduled full backup completed: {backup_path}")
            else:
                logger.error("Scheduled full backup failed")
        except Exception as e:
            logger.error(f"Scheduled full backup error: {e}")

    def _scheduled_incremental_backup(self):
        """스케줄된 증분 백업"""
        try:
            logger.info("Starting scheduled incremental backup")
            backup_path = self.database_backup.create_incremental_backup()
            if backup_path:
                logger.info(f"Scheduled incremental backup completed: {backup_path}")
            else:
                logger.error("Scheduled incremental backup failed")
        except Exception as e:
            logger.error(f"Scheduled incremental backup error: {e}")

    def _scheduled_config_backup(self):
        """스케줄된 설정 백업"""
        try:
            logger.info("Starting scheduled config backup")
            backup_path = self.config_backup.create_full_config_backup()
            if backup_path:
                logger.info(f"Scheduled config backup completed: {backup_path}")
            else:
                logger.error("Scheduled config backup failed")
        except Exception as e:
            logger.error(f"Scheduled config backup error: {e}")

    def _scheduled_cleanup(self):
        """스케줄된 정리 작업"""
        try:
            logger.info("Starting scheduled cleanup")
            self.database_backup.cleanup_old_backups()
            self.config_backup.cleanup_old_config_backups()
            logger.info("Scheduled cleanup completed")
        except Exception as e:
            logger.error(f"Scheduled cleanup error: {e}")

    # 수동 백업 메서드들
    def create_full_system_backup(self) -> Dict[str, Optional[str]]:
        """전체 시스템 백업"""
        results = {}

        try:
            logger.info("Starting full system backup")

            # 데이터베이스 백업
            db_backup = self.database_backup.create_full_backup()
            results['database'] = db_backup

            # 설정 백업
            config_backup = self.config_backup.create_full_config_backup()
            results['config'] = config_backup

            # 환경 스냅샷
            env_snapshot = self.config_backup.create_environment_snapshot()
            results['environment'] = env_snapshot

            success_count = sum(1 for v in results.values() if v is not None)
            logger.info(f"Full system backup completed: {success_count}/3 components successful")

        except Exception as e:
            logger.error(f"Full system backup error: {e}")

        return results

    def create_user_backup(self, user_id: int) -> Optional[str]:
        """특정 사용자 백업"""
        try:
            logger.info(f"Starting user backup for user {user_id}")
            backup_path = self.database_backup.export_user_data(user_id)

            if backup_path:
                logger.info(f"User backup completed: {backup_path}")
            else:
                logger.error(f"User backup failed for user {user_id}")

            return backup_path

        except Exception as e:
            logger.error(f"User backup error: {e}")
            return None

    def restore_system(self, backup_type: str, backup_path: str) -> bool:
        """시스템 복원"""
        try:
            logger.info(f"Starting system restore: {backup_type} from {backup_path}")

            if backup_type == 'database_full':
                success = self.recovery_manager.restore_database(backup_path)
            elif backup_type == 'database_incremental':
                success = self.recovery_manager.restore_incremental_backup(backup_path)
            elif backup_type == 'config':
                success = self.recovery_manager.restore_config(backup_path)
            elif backup_type == 'user_data':
                success = self.recovery_manager.restore_user_data(backup_path)
            else:
                logger.error(f"Unknown backup type: {backup_type}")
                return False

            if success:
                logger.info("System restore completed successfully")
            else:
                logger.error("System restore failed")

            return success

        except Exception as e:
            logger.error(f"System restore error: {e}")
            return False

    def get_backup_status(self) -> Dict[str, Any]:
        """백업 상태 조회"""
        try:
            # 데이터베이스 백업 통계
            db_stats = self.database_backup.get_backup_stats()

            # 설정 백업 목록
            config_backups = self.config_backup.list_config_backups()

            # 복구 옵션
            recovery_options = self.recovery_manager.list_recovery_options()

            # 다음 스케줄된 백업
            next_jobs = []
            if self.auto_backup_enabled:
                for job in schedule.jobs:
                    next_jobs.append({
                        'job': str(job.job_func),
                        'next_run': job.next_run
                    })

            return {
                'enabled': self.enabled,
                'auto_backup_enabled': self.auto_backup_enabled,
                'scheduler_running': self.is_running,
                'database_stats': db_stats,
                'config_backups_count': len(config_backups),
                'recovery_options': {
                    'database_backups': len(recovery_options.get('database_backups', [])),
                    'config_backups': len(recovery_options.get('config_backups', [])),
                    'user_exports': len(recovery_options.get('user_exports', []))
                },
                'next_scheduled_jobs': next_jobs
            }

        except Exception as e:
            logger.error(f"Failed to get backup status: {e}")
            return {}

    def verify_all_backups(self) -> Dict[str, List[Dict[str, Any]]]:
        """모든 백업 파일 검증"""
        verification_results = {
            'database_backups': [],
            'config_backups': []
        }

        try:
            # 데이터베이스 백업 검증
            db_backups = self.database_backup.list_backups()
            for backup in db_backups:
                is_valid = self.database_backup.verify_backup(backup['path'])
                verification_results['database_backups'].append({
                    'filename': backup['filename'],
                    'valid': is_valid,
                    'size': backup['size'],
                    'created': backup['created']
                })

            # 설정 백업 검증
            config_backups = self.config_backup.list_config_backups()
            for backup in config_backups:
                is_valid = self.config_backup.verify_config_backup(backup['path'])
                verification_results['config_backups'].append({
                    'filename': backup['filename'],
                    'valid': is_valid,
                    'size': backup['size'],
                    'created': backup['created']
                })

        except Exception as e:
            logger.error(f"Backup verification error: {e}")

        return verification_results

    def cleanup_all_old_backups(self):
        """모든 오래된 백업 정리"""
        try:
            logger.info("Starting cleanup of all old backups")

            self.database_backup.cleanup_old_backups()
            self.config_backup.cleanup_old_config_backups()

            logger.info("Cleanup of all old backups completed")

        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    def get_recovery_recommendations(self) -> List[Dict[str, Any]]:
        """복구 권장사항"""
        recommendations = []

        try:
            status = self.get_backup_status()
            db_stats = status.get('database_stats', {})

            # 최근 백업 확인
            latest_backup = db_stats.get('latest_backup')
            if latest_backup:
                days_since_backup = (datetime.utcnow() - latest_backup).days
                if days_since_backup > 7:
                    recommendations.append({
                        'type': 'warning',
                        'title': '오래된 백업',
                        'message': f'마지막 백업이 {days_since_backup}일 전입니다. 새로운 백업을 생성하세요.',
                        'action': 'create_full_backup'
                    })

            # 백업 부족 확인
            total_backups = db_stats.get('total_backups', 0)
            if total_backups < 3:
                recommendations.append({
                    'type': 'info',
                    'title': '백업 부족',
                    'message': '최소 3개 이상의 백업을 유지하는 것을 권장합니다.',
                    'action': 'create_more_backups'
                })

            # 스케줄러 상태 확인
            if not status.get('scheduler_running', False):
                recommendations.append({
                    'type': 'warning',
                    'title': '자동 백업 비활성화',
                    'message': '자동 백업 스케줄러가 실행되지 않고 있습니다.',
                    'action': 'start_scheduler'
                })

        except Exception as e:
            logger.error(f"Failed to get recovery recommendations: {e}")

        return recommendations