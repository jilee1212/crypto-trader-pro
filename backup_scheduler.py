#!/usr/bin/env python3
"""
Backup Scheduler for Crypto Trader Pro
백업 시스템 스케줄러 - PM2로 관리되는 독립 프로세스
"""

import sys
import os
import json
import signal
import time
import logging
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from backup import BackupManager

# 로그 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('backup_scheduler.log')
    ]
)
logger = logging.getLogger(__name__)

class BackupSchedulerService:
    """백업 스케줄러 서비스"""

    def __init__(self):
        self.backup_manager = None
        self.is_running = False
        self.shutdown_requested = False

        # 시그널 핸들러 등록
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """시그널 처리"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.shutdown_requested = True

    def _load_config(self) -> dict:
        """백업 설정 로드"""
        config_file = 'backup_config.json'

        # 기본 설정
        default_config = {
            "enabled": True,
            "auto_backup_enabled": True,
            "database": {
                "db_path": "crypto_trader.db",
                "backup_dir": "backup/database",
                "retention_days": 30,
                "compression": True
            },
            "config": {
                "project_root": ".",
                "backup_dir": "backup/configs",
                "retention_days": 30,
                "compression": True
            },
            "recovery": {
                "project_root": ".",
                "backup_dir": "backup",
                "recovery_dir": "backup/recovery"
            }
        }

        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"Loaded backup configuration from {config_file}")
            else:
                config = default_config
                # 기본 설정 파일 생성
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2)
                logger.info(f"Created default backup configuration: {config_file}")

        except Exception as e:
            logger.error(f"Failed to load backup config: {e}")
            config = default_config

        return config

    def start(self):
        """백업 스케줄러 시작"""
        try:
            logger.info("Starting Crypto Trader Pro Backup Scheduler")

            # 설정 로드
            config = self._load_config()

            # 백업 매니저 초기화
            self.backup_manager = BackupManager(config)

            # 스케줄러 시작
            self.backup_manager.start_scheduler()
            self.is_running = True

            logger.info("Backup scheduler started successfully")
            logger.info("Scheduled tasks:")
            logger.info("  - Full backup: Daily at 02:00")
            logger.info("  - Incremental backup: Every 4 hours")
            logger.info("  - Config backup: Weekly on Sunday at 03:00")
            logger.info("  - Cleanup: Monthly on 1st at 04:00")

            # 메인 루프
            self._run_main_loop()

        except Exception as e:
            logger.error(f"Failed to start backup scheduler: {e}")
            sys.exit(1)

    def _run_main_loop(self):
        """메인 실행 루프"""
        heartbeat_interval = 300  # 5분마다 상태 로그
        last_heartbeat = time.time()

        while not self.shutdown_requested:
            try:
                current_time = time.time()

                # 주기적 상태 로그
                if current_time - last_heartbeat >= heartbeat_interval:
                    self._log_status()
                    last_heartbeat = current_time

                # 1분 대기
                time.sleep(60)

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)

        self._shutdown()

    def _log_status(self):
        """상태 로그"""
        try:
            if self.backup_manager:
                status = self.backup_manager.get_backup_status()

                logger.info("=== Backup Scheduler Status ===")
                logger.info(f"Scheduler running: {status.get('scheduler_running', False)}")
                logger.info(f"Auto backup enabled: {status.get('auto_backup_enabled', False)}")

                db_stats = status.get('database_stats', {})
                logger.info(f"Total backups: {db_stats.get('total_backups', 0)}")
                logger.info(f"Latest backup: {db_stats.get('latest_backup', 'None')}")

                # 다음 스케줄된 작업
                next_jobs = status.get('next_scheduled_jobs', [])
                if next_jobs:
                    logger.info("Next scheduled jobs:")
                    for job in next_jobs[:3]:  # 최대 3개만 표시
                        logger.info(f"  - {job.get('job', 'Unknown')}: {job.get('next_run', 'Unknown')}")

                logger.info("================================")

        except Exception as e:
            logger.error(f"Failed to log status: {e}")

    def _shutdown(self):
        """종료 처리"""
        logger.info("Shutting down backup scheduler...")

        try:
            if self.backup_manager:
                self.backup_manager.stop_scheduler()
                logger.info("Backup scheduler stopped")

            self.is_running = False
            logger.info("Backup scheduler service terminated")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

def main():
    """메인 함수"""
    logger.info("Crypto Trader Pro Backup Scheduler starting...")

    try:
        # 필요한 디렉토리 생성
        os.makedirs('backup/database', exist_ok=True)
        os.makedirs('backup/configs', exist_ok=True)
        os.makedirs('backup/recovery', exist_ok=True)

        # 백업 스케줄러 서비스 시작
        service = BackupSchedulerService()
        service.start()

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()