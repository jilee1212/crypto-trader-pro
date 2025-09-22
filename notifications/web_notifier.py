"""
Web Dashboard Notification System for Crypto Trader Pro
웹 대시보드 알림 시스템
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
import os

from .base_notifier import BaseNotifier, NotificationMessage, NotificationType

logger = logging.getLogger(__name__)

class WebNotifier(BaseNotifier):
    """웹 대시보드 알림 클래스"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.db_path = config.get('db_path', 'crypto_trader.db')
        self.max_notifications = config.get('max_notifications', 100)
        self.retention_days = config.get('retention_days', 30)

        # 알림 테이블 생성
        self._create_notification_table()

    def _create_notification_table(self):
        """웹 알림 테이블 생성"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS web_notifications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        type TEXT NOT NULL,
                        title TEXT NOT NULL,
                        message TEXT NOT NULL,
                        data TEXT,
                        priority TEXT DEFAULT 'normal',
                        is_read BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)

                # 인덱스 생성
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_web_notifications_user_id
                    ON web_notifications (user_id)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_web_notifications_created_at
                    ON web_notifications (created_at)
                """)

                conn.commit()
                self.logger.info("Web notifications table created/verified")

        except Exception as e:
            self.logger.error(f"Failed to create web notifications table: {e}")
            raise

    async def send_notification(self, message: NotificationMessage) -> bool:
        """웹 알림 저장"""
        try:
            # 알림을 데이터베이스에 저장
            success = self._store_notification(message)

            if success:
                # 오래된 알림 정리
                self._cleanup_old_notifications(message.user_id)
                self.logger.info(f"Web notification stored for user {message.user_id}")

            return success

        except Exception as e:
            self.logger.error(f"Web notification error: {e}")
            return False

    def _store_notification(self, message: NotificationMessage) -> bool:
        """알림을 데이터베이스에 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                data_json = json.dumps(message.data) if message.data else None

                cursor.execute("""
                    INSERT INTO web_notifications
                    (user_id, type, title, message, data, priority, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    message.user_id,
                    message.type.value,
                    message.title,
                    message.message,
                    data_json,
                    message.priority,
                    message.timestamp
                ))

                conn.commit()
                return True

        except Exception as e:
            self.logger.error(f"Failed to store web notification: {e}")
            return False

    def get_user_notifications(
        self,
        user_id: int,
        limit: int = 50,
        unread_only: bool = False,
        include_read: bool = True
    ) -> List[Dict[str, Any]]:
        """사용자 알림 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # 쿼리 조건 구성
                conditions = ["user_id = ?"]
                params = [user_id]

                if unread_only:
                    conditions.append("is_read = FALSE")
                elif not include_read:
                    conditions.append("is_read = FALSE")

                where_clause = " AND ".join(conditions)

                cursor.execute(f"""
                    SELECT
                        id, user_id, type, title, message, data, priority,
                        is_read, created_at
                    FROM web_notifications
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ?
                """, params + [limit])

                notifications = []
                for row in cursor.fetchall():
                    notification = dict(row)
                    # JSON 데이터 파싱
                    if notification['data']:
                        try:
                            notification['data'] = json.loads(notification['data'])
                        except json.JSONDecodeError:
                            notification['data'] = None

                    notifications.append(notification)

                return notifications

        except Exception as e:
            self.logger.error(f"Failed to get user notifications: {e}")
            return []

    def mark_as_read(self, user_id: int, notification_ids: List[int]) -> bool:
        """알림을 읽음으로 표시"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 여러 ID를 한번에 처리
                placeholders = ','.join(['?' for _ in notification_ids])
                cursor.execute(f"""
                    UPDATE web_notifications
                    SET is_read = TRUE
                    WHERE user_id = ? AND id IN ({placeholders})
                """, [user_id] + notification_ids)

                conn.commit()
                self.logger.info(f"Marked {len(notification_ids)} notifications as read for user {user_id}")
                return True

        except Exception as e:
            self.logger.error(f"Failed to mark notifications as read: {e}")
            return False

    def mark_all_as_read(self, user_id: int) -> bool:
        """모든 알림을 읽음으로 표시"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    UPDATE web_notifications
                    SET is_read = TRUE
                    WHERE user_id = ? AND is_read = FALSE
                """, (user_id,))

                updated_count = cursor.rowcount
                conn.commit()

                self.logger.info(f"Marked {updated_count} notifications as read for user {user_id}")
                return True

        except Exception as e:
            self.logger.error(f"Failed to mark all notifications as read: {e}")
            return False

    def delete_notification(self, user_id: int, notification_id: int) -> bool:
        """알림 삭제"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    DELETE FROM web_notifications
                    WHERE user_id = ? AND id = ?
                """, (user_id, notification_id))

                deleted = cursor.rowcount > 0
                conn.commit()

                if deleted:
                    self.logger.info(f"Deleted notification {notification_id} for user {user_id}")

                return deleted

        except Exception as e:
            self.logger.error(f"Failed to delete notification: {e}")
            return False

    def get_unread_count(self, user_id: int) -> int:
        """읽지 않은 알림 개수"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT COUNT(*) FROM web_notifications
                    WHERE user_id = ? AND is_read = FALSE
                """, (user_id,))

                count = cursor.fetchone()[0]
                return count

        except Exception as e:
            self.logger.error(f"Failed to get unread count: {e}")
            return 0

    def _cleanup_old_notifications(self, user_id: int):
        """오래된 알림 정리"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 보존 기간 초과된 알림 삭제
                cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
                cursor.execute("""
                    DELETE FROM web_notifications
                    WHERE user_id = ? AND created_at < ?
                """, (user_id, cutoff_date))

                # 최대 개수 초과 시 오래된 것부터 삭제
                cursor.execute("""
                    DELETE FROM web_notifications
                    WHERE user_id = ? AND id NOT IN (
                        SELECT id FROM web_notifications
                        WHERE user_id = ?
                        ORDER BY created_at DESC
                        LIMIT ?
                    )
                """, (user_id, user_id, self.max_notifications))

                conn.commit()

        except Exception as e:
            self.logger.error(f"Failed to cleanup old notifications: {e}")

    def get_notification_stats(self, user_id: int) -> Dict[str, Any]:
        """알림 통계 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 전체 통계
                cursor.execute("""
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN is_read = FALSE THEN 1 ELSE 0 END) as unread,
                        COUNT(CASE WHEN created_at >= datetime('now', '-24 hours') THEN 1 END) as today
                    FROM web_notifications
                    WHERE user_id = ?
                """, (user_id,))

                stats = cursor.fetchone()

                # 유형별 통계
                cursor.execute("""
                    SELECT type, COUNT(*) as count
                    FROM web_notifications
                    WHERE user_id = ? AND created_at >= datetime('now', '-7 days')
                    GROUP BY type
                    ORDER BY count DESC
                """, (user_id,))

                type_stats = {row[0]: row[1] for row in cursor.fetchall()}

                return {
                    'total': stats[0],
                    'unread': stats[1],
                    'today': stats[2],
                    'by_type': type_stats
                }

        except Exception as e:
            self.logger.error(f"Failed to get notification stats: {e}")
            return {'total': 0, 'unread': 0, 'today': 0, 'by_type': {}}