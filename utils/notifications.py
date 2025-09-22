"""
🔔 Notification System

자동매매 시스템을 위한 종합 알림 시스템
- 다중 채널 알림 지원
- 알림 우선순위 관리
- 템플릿 기반 메시지
- 발송 이력 관리
"""

import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import threading
from abc import ABC, abstractmethod

# 알림 관련 Enum 및 데이터 클래스

class NotificationType(Enum):
    """알림 유형"""
    TRADE_EXECUTED = "TRADE_EXECUTED"
    PROFIT_TARGET_HIT = "PROFIT_TARGET_HIT"
    STOP_LOSS_HIT = "STOP_LOSS_HIT"
    DAILY_LOSS_WARNING = "DAILY_LOSS_WARNING"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    API_CONNECTION_LOST = "API_CONNECTION_LOST"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_CLOSED = "POSITION_CLOSED"
    RISK_WARNING = "RISK_WARNING"
    SYSTEM_STARTUP = "SYSTEM_STARTUP"
    SYSTEM_SHUTDOWN = "SYSTEM_SHUTDOWN"

class NotificationPriority(Enum):
    """알림 우선순위"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5

class NotificationChannel(Enum):
    """알림 채널"""
    DASHBOARD = "dashboard"
    EMAIL = "email"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    SLACK = "slack"
    SMS = "sms"

@dataclass
class NotificationMessage:
    """알림 메시지"""
    type: NotificationType
    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    channels: List[NotificationChannel] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    sent_channels: List[NotificationChannel] = field(default_factory=list)
    failed_channels: List[NotificationChannel] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3

@dataclass
class NotificationTemplate:
    """알림 템플릿"""
    type: NotificationType
    title_template: str
    message_template: str
    default_priority: NotificationPriority = NotificationPriority.NORMAL
    default_channels: List[NotificationChannel] = field(default_factory=list)

# 알림 채널 인터페이스

class NotificationChannelInterface(ABC):
    """알림 채널 인터페이스"""

    @abstractmethod
    async def send(self, message: NotificationMessage) -> bool:
        """메시지 발송"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """채널 사용 가능 여부"""
        pass

    @abstractmethod
    def get_channel_type(self) -> NotificationChannel:
        """채널 타입 반환"""
        pass

# 구체적인 알림 채널 구현

class DashboardNotification(NotificationChannelInterface):
    """대시보드 알림"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.messages = []
        self.max_messages = 100

    async def send(self, message: NotificationMessage) -> bool:
        """대시보드에 메시지 추가"""
        try:
            # 메시지를 대시보드 큐에 추가
            self.messages.append({
                'type': message.type.value,
                'title': message.title,
                'message': message.message,
                'priority': message.priority.value,
                'timestamp': message.timestamp.isoformat(),
                'data': message.data
            })

            # 최대 메시지 수 유지
            if len(self.messages) > self.max_messages:
                self.messages.pop(0)

            self.logger.info(f"대시보드 알림 발송: {message.title}")
            return True

        except Exception as e:
            self.logger.error(f"대시보드 알림 발송 실패: {e}")
            return False

    def is_available(self) -> bool:
        return True

    def get_channel_type(self) -> NotificationChannel:
        return NotificationChannel.DASHBOARD

    def get_recent_messages(self, limit: int = 20) -> List[Dict[str, Any]]:
        """최근 메시지 조회"""
        return self.messages[-limit:] if self.messages else []

class EmailNotification(NotificationChannelInterface):
    """이메일 알림"""

    def __init__(self, smtp_config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.smtp_config = smtp_config or {}
        self.enabled = bool(smtp_config)

    async def send(self, message: NotificationMessage) -> bool:
        """이메일 발송"""
        try:
            if not self.enabled:
                self.logger.warning("이메일 설정이 없습니다")
                return False

            # 실제 이메일 발송 로직 구현
            # 현재는 로그만 출력
            self.logger.info(f"이메일 알림 발송: {message.title}")
            return True

        except Exception as e:
            self.logger.error(f"이메일 알림 발송 실패: {e}")
            return False

    def is_available(self) -> bool:
        return self.enabled

    def get_channel_type(self) -> NotificationChannel:
        return NotificationChannel.EMAIL

class DiscordNotification(NotificationChannelInterface):
    """Discord 웹훅 알림"""

    def __init__(self, webhook_url: str = None):
        self.logger = logging.getLogger(__name__)
        self.webhook_url = webhook_url
        self.enabled = bool(webhook_url)

    async def send(self, message: NotificationMessage) -> bool:
        """Discord 웹훅 발송"""
        try:
            if not self.enabled:
                self.logger.warning("Discord 웹훅 URL이 없습니다")
                return False

            # 실제 Discord 웹훅 발송 로직 구현
            # 현재는 로그만 출력
            self.logger.info(f"Discord 알림 발송: {message.title}")
            return True

        except Exception as e:
            self.logger.error(f"Discord 알림 발송 실패: {e}")
            return False

    def is_available(self) -> bool:
        return self.enabled

    def get_channel_type(self) -> NotificationChannel:
        return NotificationChannel.DISCORD

class TelegramNotification(NotificationChannelInterface):
    """텔레그램 봇 알림"""

    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.logger = logging.getLogger(__name__)
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = bool(bot_token and chat_id)

    async def send(self, message: NotificationMessage) -> bool:
        """텔레그램 메시지 발송"""
        try:
            if not self.enabled:
                self.logger.warning("텔레그램 설정이 없습니다")
                return False

            # 실제 텔레그램 API 발송 로직 구현
            # 현재는 로그만 출력
            self.logger.info(f"텔레그램 알림 발송: {message.title}")
            return True

        except Exception as e:
            self.logger.error(f"텔레그램 알림 발송 실패: {e}")
            return False

    def is_available(self) -> bool:
        return self.enabled

    def get_channel_type(self) -> NotificationChannel:
        return NotificationChannel.TELEGRAM

# 메인 알림 관리자

class NotificationManager:
    """
    🔔 알림 관리자

    기능:
    - 다중 채널 알림 발송
    - 우선순위 기반 필터링
    - 템플릿 기반 메시지 생성
    - 발송 실패 재시도
    - 알림 이력 관리
    """

    def __init__(self, config: Dict[str, Any] = None):
        """알림 관리자 초기화"""
        self.logger = logging.getLogger(__name__)
        self.config = config or {}

        # 알림 채널 초기화
        self.channels: Dict[NotificationChannel, NotificationChannelInterface] = {}
        self._initialize_channels()

        # 알림 템플릿
        self.templates: Dict[NotificationType, NotificationTemplate] = {}
        self._initialize_templates()

        # 알림 큐 및 이력
        self.notification_queue: List[NotificationMessage] = []
        self.notification_history: List[NotificationMessage] = []
        self.max_history = 1000

        # 발송 설정
        self.min_priority = NotificationPriority(
            self.config.get('min_priority', NotificationPriority.NORMAL.value)
        )
        self.rate_limits = self.config.get('rate_limits', {})
        self.last_sent_times = {}

        # 스레드 안전성
        self._lock = threading.Lock()

        # 백그라운드 처리 태스크
        self._running = False
        self._worker_task = None

        self.logger.info("NotificationManager 초기화 완료")

    def _initialize_channels(self):
        """알림 채널 초기화"""
        try:
            # 대시보드 (항상 활성화)
            self.channels[NotificationChannel.DASHBOARD] = DashboardNotification()

            # 이메일
            email_config = self.config.get('email')
            if email_config:
                self.channels[NotificationChannel.EMAIL] = EmailNotification(email_config)

            # Discord
            discord_webhook = self.config.get('discord_webhook')
            if discord_webhook:
                self.channels[NotificationChannel.DISCORD] = DiscordNotification(discord_webhook)

            # 텔레그램
            telegram_config = self.config.get('telegram')
            if telegram_config:
                self.channels[NotificationChannel.TELEGRAM] = TelegramNotification(
                    telegram_config.get('bot_token'),
                    telegram_config.get('chat_id')
                )

            active_channels = [ch.value for ch in self.channels.keys()]
            self.logger.info(f"활성 알림 채널: {active_channels}")

        except Exception as e:
            self.logger.error(f"알림 채널 초기화 실패: {e}")

    def _initialize_templates(self):
        """알림 템플릿 초기화"""
        try:
            templates_data = {
                NotificationType.TRADE_EXECUTED: NotificationTemplate(
                    type=NotificationType.TRADE_EXECUTED,
                    title_template="거래 실행: {symbol}",
                    message_template="{side} {symbol} {quantity} @ ${price:.2f}\\n손익: ${pnl:.2f}",
                    default_priority=NotificationPriority.NORMAL,
                    default_channels=[NotificationChannel.DASHBOARD]
                ),
                NotificationType.PROFIT_TARGET_HIT: NotificationTemplate(
                    type=NotificationType.PROFIT_TARGET_HIT,
                    title_template="수익 목표 달성: {symbol}",
                    message_template="🎯 {symbol} 수익 목표 달성!\\n수익: ${profit:.2f} ({profit_pct:.1f}%)",
                    default_priority=NotificationPriority.HIGH,
                    default_channels=[NotificationChannel.DASHBOARD, NotificationChannel.DISCORD]
                ),
                NotificationType.STOP_LOSS_HIT: NotificationTemplate(
                    type=NotificationType.STOP_LOSS_HIT,
                    title_template="손절 실행: {symbol}",
                    message_template="🛑 {symbol} 손절 실행\\n손실: ${loss:.2f} ({loss_pct:.1f}%)",
                    default_priority=NotificationPriority.HIGH,
                    default_channels=[NotificationChannel.DASHBOARD, NotificationChannel.DISCORD]
                ),
                NotificationType.DAILY_LOSS_WARNING: NotificationTemplate(
                    type=NotificationType.DAILY_LOSS_WARNING,
                    title_template="일일 손실 경고",
                    message_template="⚠️ 일일 손실이 {threshold:.1f}%에 도달했습니다\\n현재 손실: ${loss:.2f}",
                    default_priority=NotificationPriority.HIGH,
                    default_channels=[NotificationChannel.DASHBOARD, NotificationChannel.TELEGRAM]
                ),
                NotificationType.EMERGENCY_STOP: NotificationTemplate(
                    type=NotificationType.EMERGENCY_STOP,
                    title_template="🚨 긴급 중단",
                    message_template="긴급 중단 실행: {reason}\\n조치: {action}",
                    default_priority=NotificationPriority.EMERGENCY,
                    default_channels=[NotificationChannel.DASHBOARD, NotificationChannel.TELEGRAM, NotificationChannel.EMAIL]
                ),
                NotificationType.SYSTEM_ERROR: NotificationTemplate(
                    type=NotificationType.SYSTEM_ERROR,
                    title_template="시스템 오류",
                    message_template="❌ 시스템 오류 발생: {error}",
                    default_priority=NotificationPriority.CRITICAL,
                    default_channels=[NotificationChannel.DASHBOARD, NotificationChannel.TELEGRAM]
                ),
                NotificationType.API_CONNECTION_LOST: NotificationTemplate(
                    type=NotificationType.API_CONNECTION_LOST,
                    title_template="API 연결 끊김",
                    message_template="🔌 {exchange} API 연결이 끊어졌습니다",
                    default_priority=NotificationPriority.CRITICAL,
                    default_channels=[NotificationChannel.DASHBOARD, NotificationChannel.TELEGRAM]
                ),
                NotificationType.SIGNAL_GENERATED: NotificationTemplate(
                    type=NotificationType.SIGNAL_GENERATED,
                    title_template="새 신호: {symbol}",
                    message_template="🤖 {signal_type} 신호 생성\\n신뢰도: {confidence:.1f}%\\n가격: ${price:.2f}",
                    default_priority=NotificationPriority.NORMAL,
                    default_channels=[NotificationChannel.DASHBOARD]
                )
            }

            for template in templates_data.values():
                self.templates[template.type] = template

            self.logger.info(f"알림 템플릿 {len(self.templates)}개 초기화 완료")

        except Exception as e:
            self.logger.error(f"알림 템플릿 초기화 실패: {e}")

    async def send_notification(self, notification_type: NotificationType,
                              data: Dict[str, Any] = None,
                              title: str = None, message: str = None,
                              priority: NotificationPriority = None,
                              channels: List[NotificationChannel] = None) -> bool:
        """
        알림 발송

        Args:
            notification_type: 알림 유형
            data: 템플릿에 사용할 데이터
            title: 직접 지정할 제목 (템플릿보다 우선)
            message: 직접 지정할 메시지 (템플릿보다 우선)
            priority: 우선순위
            channels: 발송할 채널 목록

        Returns:
            발송 성공 여부
        """
        try:
            # 템플릿에서 메시지 생성
            if title is None or message is None:
                if notification_type in self.templates:
                    template = self.templates[notification_type]
                    data = data or {}

                    if title is None:
                        title = template.title_template.format(**data)
                    if message is None:
                        message = template.message_template.format(**data)
                    if priority is None:
                        priority = template.default_priority
                    if channels is None:
                        channels = template.default_channels
                else:
                    if title is None:
                        title = f"알림: {notification_type.value}"
                    if message is None:
                        message = "내용 없음"

            # 기본값 설정
            priority = priority or NotificationPriority.NORMAL
            channels = channels or [NotificationChannel.DASHBOARD]
            data = data or {}

            # 우선순위 필터링
            if priority.value < self.min_priority.value:
                self.logger.debug(f"우선순위 낮음으로 알림 무시: {title}")
                return True

            # 알림 메시지 생성
            notification = NotificationMessage(
                type=notification_type,
                title=title,
                message=message,
                priority=priority,
                channels=channels,
                data=data
            )

            # 발송 큐에 추가
            with self._lock:
                self.notification_queue.append(notification)

            self.logger.info(f"알림 큐에 추가: {title}")

            # 즉시 발송 (높은 우선순위)
            if priority.value >= NotificationPriority.HIGH.value:
                await self._process_notification(notification)

            return True

        except Exception as e:
            self.logger.error(f"알림 발송 실패: {e}")
            return False

    async def _process_notification(self, notification: NotificationMessage) -> bool:
        """개별 알림 처리"""
        try:
            success_count = 0
            total_channels = len(notification.channels)

            for channel_type in notification.channels:
                if channel_type in self.channels:
                    channel = self.channels[channel_type]

                    if not channel.is_available():
                        notification.failed_channels.append(channel_type)
                        continue

                    # 속도 제한 확인
                    if self._check_rate_limit(channel_type):
                        notification.failed_channels.append(channel_type)
                        continue

                    # 발송 시도
                    try:
                        success = await channel.send(notification)
                        if success:
                            notification.sent_channels.append(channel_type)
                            success_count += 1
                            self._update_rate_limit(channel_type)
                        else:
                            notification.failed_channels.append(channel_type)

                    except Exception as e:
                        self.logger.error(f"{channel_type.value} 채널 발송 실패: {e}")
                        notification.failed_channels.append(channel_type)

                else:
                    self.logger.warning(f"알 수 없는 채널: {channel_type}")
                    notification.failed_channels.append(channel_type)

            # 이력에 추가
            with self._lock:
                self.notification_history.append(notification)
                if len(self.notification_history) > self.max_history:
                    self.notification_history.pop(0)

            success_rate = success_count / total_channels if total_channels > 0 else 0
            self.logger.info(f"알림 발송 완료: {notification.title} ({success_count}/{total_channels} 성공)")

            return success_rate > 0.5  # 과반수 성공시 성공으로 간주

        except Exception as e:
            self.logger.error(f"알림 처리 실패: {e}")
            return False

    def _check_rate_limit(self, channel_type: NotificationChannel) -> bool:
        """속도 제한 확인"""
        try:
            if channel_type.value not in self.rate_limits:
                return False

            limit_config = self.rate_limits[channel_type.value]
            max_per_minute = limit_config.get('max_per_minute', 10)

            current_time = datetime.now()
            if channel_type not in self.last_sent_times:
                self.last_sent_times[channel_type] = []

            # 1분 이내 발송 기록 필터링
            recent_sends = [
                t for t in self.last_sent_times[channel_type]
                if current_time - t < timedelta(minutes=1)
            ]

            return len(recent_sends) >= max_per_minute

        except Exception:
            return False

    def _update_rate_limit(self, channel_type: NotificationChannel):
        """속도 제한 업데이트"""
        try:
            if channel_type not in self.last_sent_times:
                self.last_sent_times[channel_type] = []

            self.last_sent_times[channel_type].append(datetime.now())

            # 오래된 기록 정리
            cutoff_time = datetime.now() - timedelta(minutes=5)
            self.last_sent_times[channel_type] = [
                t for t in self.last_sent_times[channel_type]
                if t > cutoff_time
            ]

        except Exception:
            pass

    async def start_worker(self):
        """백그라운드 워커 시작"""
        if self._running:
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        self.logger.info("알림 워커 시작됨")

    async def stop_worker(self):
        """백그라운드 워커 중단"""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        self.logger.info("알림 워커 중단됨")

    async def _worker_loop(self):
        """백그라운드 워커 루프"""
        while self._running:
            try:
                # 큐에서 알림 처리
                notifications_to_process = []
                with self._lock:
                    notifications_to_process = self.notification_queue.copy()
                    self.notification_queue.clear()

                for notification in notifications_to_process:
                    await self._process_notification(notification)

                # 잠깐 대기
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"알림 워커 오류: {e}")
                await asyncio.sleep(5)

    def get_dashboard_messages(self, limit: int = 20) -> List[Dict[str, Any]]:
        """대시보드용 메시지 조회"""
        try:
            dashboard_channel = self.channels.get(NotificationChannel.DASHBOARD)
            if isinstance(dashboard_channel, DashboardNotification):
                return dashboard_channel.get_recent_messages(limit)
            return []
        except Exception as e:
            self.logger.error(f"대시보드 메시지 조회 실패: {e}")
            return []

    def get_notification_status(self) -> Dict[str, Any]:
        """알림 시스템 상태 조회"""
        try:
            with self._lock:
                return {
                    'worker_running': self._running,
                    'queue_size': len(self.notification_queue),
                    'history_size': len(self.notification_history),
                    'active_channels': [ch.value for ch in self.channels.keys()],
                    'available_channels': [
                        ch.value for ch, channel in self.channels.items()
                        if channel.is_available()
                    ],
                    'total_sent': len(self.notification_history),
                    'recent_activity': [
                        {
                            'type': notif.type.value,
                            'title': notif.title,
                            'timestamp': notif.timestamp.isoformat(),
                            'channels': [ch.value for ch in notif.sent_channels]
                        }
                        for notif in self.notification_history[-5:]
                    ]
                }
        except Exception as e:
            return {'error': f"상태 조회 실패: {e}"}


# 편의 함수들

async def send_trade_notification(manager: NotificationManager, symbol: str,
                                side: str, quantity: float, price: float, pnl: float = 0):
    """거래 실행 알림 발송"""
    await manager.send_notification(
        NotificationType.TRADE_EXECUTED,
        data={
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
            'pnl': pnl
        }
    )

async def send_emergency_notification(manager: NotificationManager, reason: str, action: str):
    """긴급 상황 알림 발송"""
    await manager.send_notification(
        NotificationType.EMERGENCY_STOP,
        data={
            'reason': reason,
            'action': action
        },
        priority=NotificationPriority.EMERGENCY
    )

async def send_profit_notification(manager: NotificationManager, symbol: str,
                                 profit: float, profit_pct: float):
    """수익 달성 알림 발송"""
    await manager.send_notification(
        NotificationType.PROFIT_TARGET_HIT,
        data={
            'symbol': symbol,
            'profit': profit,
            'profit_pct': profit_pct
        },
        priority=NotificationPriority.HIGH
    )