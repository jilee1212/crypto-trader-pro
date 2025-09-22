"""
Base Notification System for Crypto Trader Pro
알림 시스템 기본 클래스
"""

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class NotificationType(Enum):
    """알림 유형"""
    TRADE_EXECUTED = "trade_executed"
    SIGNAL_GENERATED = "signal_generated"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    STOP_LOSS_TRIGGERED = "stop_loss_triggered"
    TAKE_PROFIT_TRIGGERED = "take_profit_triggered"
    BALANCE_LOW = "balance_low"
    ERROR_OCCURRED = "error_occurred"
    SYSTEM_STATUS = "system_status"
    DAILY_REPORT = "daily_report"

@dataclass
class NotificationMessage:
    """알림 메시지 클래스"""
    user_id: int
    type: NotificationType
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None
    priority: str = "normal"  # low, normal, high, urgent
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class BaseNotifier(ABC):
    """알림 기본 클래스"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('enabled', True)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def send_notification(self, message: NotificationMessage) -> bool:
        """알림 전송 (추상 메서드)"""
        pass

    def is_enabled(self) -> bool:
        """알림 활성화 상태 확인"""
        return self.enabled

    def format_message(self, message: NotificationMessage) -> str:
        """메시지 포맷팅"""
        timestamp = message.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        priority_emoji = {
            "low": "🔵",
            "normal": "🟢",
            "high": "🟡",
            "urgent": "🔴"
        }.get(message.priority, "🟢")

        return f"{priority_emoji} **{message.title}**\n{message.message}\n\n⏰ {timestamp}"

    def should_send(self, message: NotificationMessage, user_settings: Dict[str, Any]) -> bool:
        """알림 전송 여부 결정"""
        if not self.enabled:
            return False

        # 사용자별 알림 설정 확인
        notification_type = message.type.value
        if not user_settings.get(f"{notification_type}_enabled", True):
            return False

        # 우선순위 필터링
        min_priority = user_settings.get("min_priority", "normal")
        priority_levels = {"low": 0, "normal": 1, "high": 2, "urgent": 3}

        message_level = priority_levels.get(message.priority, 1)
        min_level = priority_levels.get(min_priority, 1)

        return message_level >= min_level