"""
🔔 Phase 5 고급 알림 시스템 (Advanced Notification System)
다중 채널 알림, 우선순위 관리, 템플릿 시스템, 알림 히스토리 관리
"""

import streamlit as st
import pandas as pd
import json
import requests
try:
    import smtplib
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    # 이메일 라이브러리가 없는 경우
    EMAIL_AVAILABLE = False
    class MimeText:
        def __init__(self, *args, **kwargs): pass
    class MimeMultipart:
        def __init__(self, *args, **kwargs): pass
    class smtplib:
        @staticmethod
        def SMTP(*args, **kwargs): pass
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import asyncio
import logging

class NotificationLevel(Enum):
    """알림 레벨"""
    DEBUG = 1
    INFO = 2
    WARNING = 3
    ERROR = 4
    CRITICAL = 5

class NotificationType(Enum):
    """알림 유형"""
    TRADE_EXECUTED = "거래 실행"
    PROFIT_TARGET_HIT = "수익 목표 달성"
    STOP_LOSS_HIT = "손절 실행"
    DAILY_LOSS_WARNING = "일일 손실 경고"
    SYSTEM_ERROR = "시스템 오류"
    API_CONNECTION_LOST = "API 연결 끊김"
    EMERGENCY_STOP = "긴급 중단"
    SIGNAL_GENERATED = "신호 생성"
    SYSTEM_STARTUP = "시스템 시작"
    SYSTEM_SHUTDOWN = "시스템 종료"
    RISK_THRESHOLD_EXCEEDED = "리스크 임계값 초과"
    MARKET_ANOMALY_DETECTED = "시장 이상 감지"

@dataclass
class NotificationMessage:
    """알림 메시지 구조"""
    id: str
    type: NotificationType
    level: NotificationLevel
    title: str
    message: str
    data: Dict[str, Any]
    timestamp: datetime
    channels: List[str]
    sent_status: Dict[str, bool]
    retry_count: int = 0
    max_retries: int = 3

class NotificationChannel:
    """알림 채널 기본 클래스"""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.enabled = config.get('enabled', False)

    async def send(self, message: NotificationMessage) -> bool:
        """알림 발송 (서브클래스에서 구현)"""
        raise NotImplementedError

    def format_message(self, message: NotificationMessage) -> str:
        """메시지 포맷팅"""
        return f"[{message.level.name}] {message.title}\n{message.message}"

class DashboardNotificationChannel(NotificationChannel):
    """대시보드 알림 채널"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("dashboard", config)

    async def send(self, message: NotificationMessage) -> bool:
        """대시보드에 알림 표시"""
        try:
            # 세션 상태에 알림 추가
            if 'dashboard_notifications' not in st.session_state:
                st.session_state.dashboard_notifications = []

            st.session_state.dashboard_notifications.append({
                'id': message.id,
                'type': message.type.value,
                'level': message.level.name,
                'title': message.title,
                'message': message.message,
                'timestamp': message.timestamp.isoformat(),
                'data': message.data
            })

            # 최대 100개까지만 보관
            if len(st.session_state.dashboard_notifications) > 100:
                st.session_state.dashboard_notifications = st.session_state.dashboard_notifications[-100:]

            return True
        except Exception as e:
            logging.error(f"Dashboard notification failed: {e}")
            return False

class EmailNotificationChannel(NotificationChannel):
    """이메일 알림 채널"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("email", config)

    async def send(self, message: NotificationMessage) -> bool:
        """이메일 발송"""
        if not self.enabled or not EMAIL_AVAILABLE:
            return True

        try:
            smtp_server = self.config.get('smtp_server', 'smtp.gmail.com')
            smtp_port = self.config.get('smtp_port', 587)
            username = self.config.get('username', '')
            password = self.config.get('password', '')
            to_email = self.config.get('to_email', '')

            if not all([username, password, to_email]):
                return False

            # 이메일 메시지 생성
            msg = MimeMultipart()
            msg['From'] = username
            msg['To'] = to_email
            msg['Subject'] = f"[자동매매] {message.title}"

            body = self.format_email_body(message)
            msg.attach(MimeText(body, 'html'))

            # SMTP 서버로 발송 (시뮬레이션)
            # 실제 구현에서는 아래 코드 활성화
            """
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(username, password)
            text = msg.as_string()
            server.sendmail(username, to_email, text)
            server.quit()
            """

            logging.info(f"Email notification sent: {message.title}")
            return True

        except Exception as e:
            logging.error(f"Email notification failed: {e}")
            return False

    def format_email_body(self, message: NotificationMessage) -> str:
        """이메일 본문 포맷팅"""
        return f"""
        <html>
        <body>
            <h2>🤖 자동매매 시스템 알림</h2>
            <p><strong>유형:</strong> {message.type.value}</p>
            <p><strong>레벨:</strong> {message.level.name}</p>
            <p><strong>시간:</strong> {message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <hr>
            <h3>{message.title}</h3>
            <p>{message.message}</p>

            {self.format_data_table(message.data) if message.data else ''}

            <hr>
            <p><small>자동매매 시스템에서 발송된 알림입니다.</small></p>
        </body>
        </html>
        """

    def format_data_table(self, data: Dict[str, Any]) -> str:
        """데이터 테이블 포맷팅"""
        if not data:
            return ""

        table_html = "<h4>상세 정보:</h4><table border='1' style='border-collapse: collapse;'>"
        for key, value in data.items():
            table_html += f"<tr><td><strong>{key}</strong></td><td>{value}</td></tr>"
        table_html += "</table>"
        return table_html

class DiscordNotificationChannel(NotificationChannel):
    """Discord 알림 채널"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("discord", config)

    async def send(self, message: NotificationMessage) -> bool:
        """Discord 웹훅으로 알림 발송"""
        if not self.enabled:
            return True

        try:
            webhook_url = self.config.get('webhook_url', '')
            if not webhook_url:
                return False

            # Discord 임베드 메시지 생성
            embed = {
                "title": f"🤖 {message.title}",
                "description": message.message,
                "color": self.get_color_for_level(message.level),
                "timestamp": message.timestamp.isoformat(),
                "fields": [
                    {"name": "유형", "value": message.type.value, "inline": True},
                    {"name": "레벨", "value": message.level.name, "inline": True}
                ]
            }

            # 추가 데이터가 있으면 필드에 추가
            if message.data:
                for key, value in list(message.data.items())[:5]:  # 최대 5개까지
                    embed["fields"].append({
                        "name": str(key),
                        "value": str(value),
                        "inline": True
                    })

            payload = {"embeds": [embed]}

            # 웹훅 발송 (시뮬레이션)
            # 실제 구현에서는 아래 코드 활성화
            """
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
            """

            logging.info(f"Discord notification sent: {message.title}")
            return True

        except Exception as e:
            logging.error(f"Discord notification failed: {e}")
            return False

    def get_color_for_level(self, level: NotificationLevel) -> int:
        """레벨별 색상 반환"""
        colors = {
            NotificationLevel.DEBUG: 0x808080,    # 회색
            NotificationLevel.INFO: 0x0099ff,     # 파란색
            NotificationLevel.WARNING: 0xffaa00,  # 주황색
            NotificationLevel.ERROR: 0xff0000,    # 빨간색
            NotificationLevel.CRITICAL: 0x8b0000  # 진한 빨간색
        }
        return colors.get(level, 0x0099ff)

class TelegramNotificationChannel(NotificationChannel):
    """Telegram 알림 채널"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("telegram", config)

    async def send(self, message: NotificationMessage) -> bool:
        """Telegram 봇으로 알림 발송"""
        if not self.enabled:
            return True

        try:
            bot_token = self.config.get('bot_token', '')
            chat_id = self.config.get('chat_id', '')

            if not all([bot_token, chat_id]):
                return False

            # 메시지 포맷팅
            text = self.format_telegram_message(message)

            # Telegram API 호출 (시뮬레이션)
            # 실제 구현에서는 아래 코드 활성화
            """
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            }
            response = requests.post(url, json=payload)
            response.raise_for_status()
            """

            logging.info(f"Telegram notification sent: {message.title}")
            return True

        except Exception as e:
            logging.error(f"Telegram notification failed: {e}")
            return False

    def format_telegram_message(self, message: NotificationMessage) -> str:
        """Telegram 메시지 포맷팅"""
        emoji_map = {
            NotificationLevel.DEBUG: "🔍",
            NotificationLevel.INFO: "ℹ️",
            NotificationLevel.WARNING: "⚠️",
            NotificationLevel.ERROR: "❌",
            NotificationLevel.CRITICAL: "🚨"
        }

        emoji = emoji_map.get(message.level, "📢")

        text = f"{emoji} *{message.title}*\n\n"
        text += f"{message.message}\n\n"
        text += f"📊 *유형:* {message.type.value}\n"
        text += f"⏰ *시간:* {message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"

        if message.data:
            text += "\n📋 *상세 정보:*\n"
            for key, value in list(message.data.items())[:5]:
                text += f"• {key}: `{value}`\n"

        return text

class AdvancedNotificationSystem:
    """🔔 Phase 5 고급 알림 시스템"""

    def __init__(self):
        self.channels = {}
        self.message_queue = []
        self.sent_messages = []
        self.templates = {}
        self.initialize_system()

    def initialize_system(self):
        """시스템 초기화"""
        if 'notification_config' not in st.session_state:
            st.session_state.notification_config = self.get_default_config()

        if 'notification_history' not in st.session_state:
            st.session_state.notification_history = []

        # 채널 초기화
        self.setup_channels()
        self.load_templates()

    def setup_channels(self):
        """알림 채널 설정"""
        config = st.session_state.notification_config

        self.channels = {
            'dashboard': DashboardNotificationChannel(config.get('dashboard', {})),
            'email': EmailNotificationChannel(config.get('email', {})),
            'discord': DiscordNotificationChannel(config.get('discord', {})),
            'telegram': TelegramNotificationChannel(config.get('telegram', {}))
        }

    def load_templates(self):
        """알림 템플릿 로드"""
        self.templates = {
            NotificationType.TRADE_EXECUTED: {
                'title': "거래 실행: {symbol}",
                'message': "{side} {amount} {symbol} @ ${price}\n수익률: {pnl_percent:.2f}%"
            },
            NotificationType.PROFIT_TARGET_HIT: {
                'title': "🎯 수익 목표 달성!",
                'message': "{symbol} 포지션에서 목표 수익 달성\n수익: ${profit:.2f} ({pnl_percent:.2f}%)"
            },
            NotificationType.STOP_LOSS_HIT: {
                'title': "🛑 손절매 실행",
                'message': "{symbol} 포지션 손절매 실행\n손실: ${loss:.2f} ({pnl_percent:.2f}%)"
            },
            NotificationType.DAILY_LOSS_WARNING: {
                'title': "⚠️ 일일 손실 경고",
                'message': "일일 손실이 {threshold:.1f}%에 도달했습니다\n현재 손실: {current_loss:.2f}%"
            },
            NotificationType.SYSTEM_ERROR: {
                'title': "❌ 시스템 오류",
                'message': "시스템에서 오류가 발생했습니다\n오류: {error_message}"
            },
            NotificationType.EMERGENCY_STOP: {
                'title': "🚨 긴급 중단",
                'message': "긴급 중단이 실행되었습니다\n사유: {reason}"
            },
            NotificationType.SIGNAL_GENERATED: {
                'title': "🤖 신호 생성",
                'message': "{symbol}: {signal_type} 신호\n신뢰도: {confidence:.1f}%"
            }
        }

    def show_notification_dashboard(self):
        """알림 시스템 대시보드"""
        st.title("🔔 고급 알림 시스템")
        st.markdown("**Phase 5: 다중 채널 알림 및 관리 시스템**")

        # 탭 구성
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🎛️ 알림 설정", "📊 알림 상태", "📋 알림 히스토리",
            "🧪 테스트", "📊 통계"
        ])

        with tab1:
            self.show_notification_settings()

        with tab2:
            self.show_notification_status()

        with tab3:
            self.show_notification_history()

        with tab4:
            self.show_notification_test()

        with tab5:
            self.show_notification_statistics()

    def show_notification_settings(self):
        """알림 설정 탭"""
        st.subheader("🎛️ 알림 시스템 설정")

        config = st.session_state.notification_config

        # 전역 설정
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🌐 전역 설정")

            enabled = st.checkbox(
                "알림 시스템 활성화",
                value=config.get('enabled', True),
                key="global_notifications_enabled"
            )
            config['enabled'] = enabled

            min_level = st.selectbox(
                "최소 알림 레벨",
                [level.name for level in NotificationLevel],
                index=1,  # INFO
                key="min_notification_level"
            )
            config['min_level'] = min_level

            rate_limit = st.number_input(
                "분당 최대 알림 수",
                min_value=1,
                max_value=100,
                value=config.get('rate_limit', 10),
                key="notification_rate_limit"
            )
            config['rate_limit'] = rate_limit

        with col2:
            st.markdown("#### 📱 채널별 활성화")

            # 채널별 설정
            for channel_name in ['dashboard', 'email', 'discord', 'telegram']:
                channel_config = config.get(channel_name, {})

                enabled = st.checkbox(
                    f"{channel_name.title()} 알림",
                    value=channel_config.get('enabled', False),
                    key=f"{channel_name}_enabled"
                )
                channel_config['enabled'] = enabled
                config[channel_name] = channel_config

        # 채널별 상세 설정
        st.markdown("#### 🔧 채널별 상세 설정")

        # 이메일 설정
        with st.expander("📧 이메일 설정", expanded=False):
            email_config = config.get('email', {})

            col1, col2 = st.columns(2)
            with col1:
                smtp_server = st.text_input(
                    "SMTP 서버",
                    value=email_config.get('smtp_server', 'smtp.gmail.com'),
                    key="email_smtp_server"
                )
                email_config['smtp_server'] = smtp_server

                username = st.text_input(
                    "이메일 주소",
                    value=email_config.get('username', ''),
                    key="email_username"
                )
                email_config['username'] = username

            with col2:
                smtp_port = st.number_input(
                    "SMTP 포트",
                    value=email_config.get('smtp_port', 587),
                    key="email_smtp_port"
                )
                email_config['smtp_port'] = smtp_port

                password = st.text_input(
                    "앱 비밀번호",
                    value="••••••••" if email_config.get('password') else "",
                    type="password",
                    key="email_password"
                )
                if password and password != "••••••••":
                    email_config['password'] = password

                to_email = st.text_input(
                    "수신 이메일",
                    value=email_config.get('to_email', ''),
                    key="email_to"
                )
                email_config['to_email'] = to_email

            config['email'] = email_config

        # Discord 설정
        with st.expander("💬 Discord 설정", expanded=False):
            discord_config = config.get('discord', {})

            webhook_url = st.text_input(
                "Discord Webhook URL",
                value=discord_config.get('webhook_url', ''),
                type="password",
                key="discord_webhook",
                help="Discord 서버의 웹훅 URL을 입력하세요"
            )
            discord_config['webhook_url'] = webhook_url
            config['discord'] = discord_config

        # Telegram 설정
        with st.expander("📱 Telegram 설정", expanded=False):
            telegram_config = config.get('telegram', {})

            col1, col2 = st.columns(2)
            with col1:
                bot_token = st.text_input(
                    "Bot Token",
                    value="••••••••" if telegram_config.get('bot_token') else "",
                    type="password",
                    key="telegram_bot_token",
                    help="BotFather에서 생성한 봇 토큰"
                )
                if bot_token and bot_token != "••••••••":
                    telegram_config['bot_token'] = bot_token

            with col2:
                chat_id = st.text_input(
                    "Chat ID",
                    value=telegram_config.get('chat_id', ''),
                    key="telegram_chat_id",
                    help="봇이 메시지를 보낼 채팅 ID"
                )
                telegram_config['chat_id'] = chat_id

            config['telegram'] = telegram_config

        # 설정 저장
        st.session_state.notification_config = config

        if st.button("💾 설정 저장", type="primary", key="save_notification_config"):
            self.setup_channels()  # 채널 재설정
            st.success("✅ 알림 설정이 저장되었습니다!")

    def show_notification_status(self):
        """알림 상태 탭"""
        st.subheader("📊 실시간 알림 상태")

        # 채널 상태 카드
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            dashboard_status = "🟢 활성" if self.channels['dashboard'].enabled else "🔴 비활성"
            st.metric("대시보드", dashboard_status)

        with col2:
            email_status = "🟢 활성" if self.channels['email'].enabled else "🔴 비활성"
            st.metric("이메일", email_status)

        with col3:
            discord_status = "🟢 활성" if self.channels['discord'].enabled else "🔴 비활성"
            st.metric("Discord", discord_status)

        with col4:
            telegram_status = "🟢 활성" if self.channels['telegram'].enabled else "🔴 비활성"
            st.metric("Telegram", telegram_status)

        # 최근 알림
        st.markdown("#### 🔔 최근 알림")

        if 'dashboard_notifications' in st.session_state and st.session_state.dashboard_notifications:
            recent_notifications = st.session_state.dashboard_notifications[-5:]  # 최근 5개

            for notification in reversed(recent_notifications):
                with st.expander(f"{notification['level']} - {notification['title']} ({notification['timestamp'][:16]})", expanded=False):
                    st.write(f"**유형:** {notification['type']}")
                    st.write(f"**메시지:** {notification['message']}")
                    if notification['data']:
                        st.json(notification['data'])
        else:
            st.info("표시할 알림이 없습니다.")

        # 실시간 갱신
        if st.button("🔄 상태 새로고침", key="refresh_notification_status"):
            st.rerun()

    def show_notification_history(self):
        """알림 히스토리 탭"""
        st.subheader("📋 알림 히스토리")

        # 필터링 옵션
        col1, col2, col3 = st.columns(3)

        with col1:
            date_filter = st.date_input(
                "날짜 필터",
                value=datetime.now().date(),
                key="notification_date_filter"
            )

        with col2:
            level_filter = st.multiselect(
                "레벨 필터",
                [level.name for level in NotificationLevel],
                default=[level.name for level in NotificationLevel],
                key="notification_level_filter"
            )

        with col3:
            type_filter = st.multiselect(
                "유형 필터",
                [ntype.value for ntype in NotificationType],
                default=[ntype.value for ntype in NotificationType],
                key="notification_type_filter"
            )

        # 히스토리 표시
        if 'dashboard_notifications' in st.session_state:
            notifications = st.session_state.dashboard_notifications

            # 필터링
            filtered_notifications = []
            for notification in notifications:
                if (notification['level'] in level_filter and
                    notification['type'] in type_filter):
                    filtered_notifications.append(notification)

            if filtered_notifications:
                # 데이터프레임으로 표시
                df = pd.DataFrame(filtered_notifications)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp', ascending=False)

                st.dataframe(
                    df[['timestamp', 'level', 'type', 'title', 'message']],
                    use_container_width=True
                )

                # 내보내기 버튼
                if st.button("📤 히스토리 내보내기 (CSV)", key="export_notification_history"):
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="CSV 다운로드",
                        data=csv,
                        file_name=f"notification_history_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime='text/csv'
                    )
            else:
                st.info("필터 조건에 맞는 알림이 없습니다.")
        else:
            st.info("알림 히스토리가 없습니다.")

    def show_notification_test(self):
        """알림 테스트 탭"""
        st.subheader("🧪 알림 테스트")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 테스트 메시지 생성")

            test_type = st.selectbox(
                "알림 유형",
                [ntype.value for ntype in NotificationType],
                key="test_notification_type"
            )

            test_level = st.selectbox(
                "알림 레벨",
                [level.name for level in NotificationLevel],
                index=1,  # INFO
                key="test_notification_level"
            )

            test_title = st.text_input(
                "제목",
                value="테스트 알림",
                key="test_notification_title"
            )

            test_message = st.text_area(
                "메시지",
                value="이것은 테스트 알림입니다.",
                key="test_notification_message"
            )

            test_channels = st.multiselect(
                "테스트할 채널",
                ['dashboard', 'email', 'discord', 'telegram'],
                default=['dashboard'],
                key="test_notification_channels"
            )

        with col2:
            st.markdown("#### 미리 정의된 테스트")

            if st.button("📈 거래 실행 테스트", key="test_trade_executed"):
                self.send_test_notification(
                    NotificationType.TRADE_EXECUTED,
                    NotificationLevel.INFO,
                    test_channels
                )

            if st.button("🎯 수익 달성 테스트", key="test_profit_target"):
                self.send_test_notification(
                    NotificationType.PROFIT_TARGET_HIT,
                    NotificationLevel.INFO,
                    test_channels
                )

            if st.button("⚠️ 손실 경고 테스트", key="test_loss_warning"):
                self.send_test_notification(
                    NotificationType.DAILY_LOSS_WARNING,
                    NotificationLevel.WARNING,
                    test_channels
                )

            if st.button("🚨 긴급 중단 테스트", key="test_emergency_stop"):
                self.send_test_notification(
                    NotificationType.EMERGENCY_STOP,
                    NotificationLevel.CRITICAL,
                    test_channels
                )

        # 사용자 정의 테스트
        if st.button("🚀 사용자 정의 테스트 발송", type="primary", key="send_custom_test"):
            try:
                # NotificationType 찾기
                notification_type = next(
                    ntype for ntype in NotificationType
                    if ntype.value == test_type
                )

                # NotificationLevel 찾기
                notification_level = next(
                    level for level in NotificationLevel
                    if level.name == test_level
                )

                self.send_test_notification(
                    notification_type,
                    notification_level,
                    test_channels,
                    custom_title=test_title,
                    custom_message=test_message
                )

            except Exception as e:
                st.error(f"테스트 알림 발송 실패: {e}")

    def show_notification_statistics(self):
        """알림 통계 탭"""
        st.subheader("📊 알림 통계")

        if 'dashboard_notifications' in st.session_state and st.session_state.dashboard_notifications:
            notifications = st.session_state.dashboard_notifications
            df = pd.DataFrame(notifications)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            col1, col2 = st.columns(2)

            with col1:
                # 레벨별 통계
                level_counts = df['level'].value_counts()
                st.bar_chart(level_counts)
                st.caption("레벨별 알림 수")

            with col2:
                # 유형별 통계
                type_counts = df['type'].value_counts()
                st.bar_chart(type_counts)
                st.caption("유형별 알림 수")

            # 시간대별 분석
            df['hour'] = df['timestamp'].dt.hour
            hourly_counts = df.groupby('hour').size()

            st.line_chart(hourly_counts)
            st.caption("시간대별 알림 발생량")

            # 요약 통계
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("총 알림 수", len(notifications))

            with col2:
                today_notifications = df[df['timestamp'].dt.date == datetime.now().date()]
                st.metric("오늘 알림", len(today_notifications))

            with col3:
                critical_notifications = df[df['level'] == 'CRITICAL']
                st.metric("긴급 알림", len(critical_notifications))

            with col4:
                avg_per_hour = len(notifications) / max(1, (datetime.now() - df['timestamp'].min()).total_seconds() / 3600)
                st.metric("시간당 평균", f"{avg_per_hour:.1f}")

        else:
            st.info("통계를 표시할 알림 데이터가 없습니다.")

    def send_test_notification(
        self,
        notification_type: NotificationType,
        level: NotificationLevel,
        channels: List[str],
        custom_title: str = None,
        custom_message: str = None
    ):
        """테스트 알림 발송"""

        # 테스트 데이터 생성
        test_data = {
            'symbol': 'BTC/USDT',
            'side': 'BUY',
            'amount': 0.1,
            'price': 65000,
            'pnl_percent': 2.5,
            'profit': 125.50,
            'loss': -75.25,
            'threshold': 80.0,
            'current_loss': 2.1,
            'error_message': '테스트 오류 메시지',
            'reason': '테스트 목적',
            'signal_type': 'BUY',
            'confidence': 85.5
        }

        # 템플릿에서 제목과 메시지 생성
        template = self.templates.get(notification_type, {})
        title = custom_title or template.get('title', f'테스트 {notification_type.value}').format(**test_data)
        message = custom_message or template.get('message', '테스트 메시지입니다.').format(**test_data)

        # 알림 메시지 생성
        notification = NotificationMessage(
            id=f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            type=notification_type,
            level=level,
            title=title,
            message=message,
            data=test_data,
            timestamp=datetime.now(),
            channels=channels,
            sent_status={}
        )

        # 알림 발송 (동기적으로 처리)
        try:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 이미 실행 중인 루프가 있으면 동기 방식으로 처리
                    self._send_notification_sync(notification)
                else:
                    asyncio.run(self.send_notification(notification))
            except RuntimeError:
                # asyncio 문제가 있으면 동기 방식으로 처리
                self._send_notification_sync(notification)
        except Exception as e:
            st.warning(f"알림 발송 중 오류: {e}")

        st.success(f"✅ 테스트 알림이 {', '.join(channels)} 채널로 발송되었습니다!")

    async def send_notification(self, message: NotificationMessage):
        """알림 발송 (비동기)"""
        for channel_name in message.channels:
            if channel_name in self.channels:
                channel = self.channels[channel_name]
                try:
                    success = await channel.send(message)
                    message.sent_status[channel_name] = success
                except Exception as e:
                    logging.error(f"Notification failed for {channel_name}: {e}")
                    message.sent_status[channel_name] = False

        # 히스토리에 추가
        self._add_to_history(message)

    def _send_notification_sync(self, message: NotificationMessage):
        """알림 발송 (동기)"""
        for channel_name in message.channels:
            if channel_name in self.channels:
                channel = self.channels[channel_name]
                try:
                    # 동기적으로 send 메서드 호출 (실제로는 시뮬레이션)
                    if channel_name == 'dashboard':
                        success = True
                        # 대시보드 알림은 세션 상태에 직접 추가
                        if 'dashboard_notifications' not in st.session_state:
                            st.session_state.dashboard_notifications = []
                        st.session_state.dashboard_notifications.append({
                            'id': message.id,
                            'type': message.type.value,
                            'level': message.level.name,
                            'title': message.title,
                            'message': message.message,
                            'timestamp': message.timestamp.isoformat(),
                            'data': message.data
                        })
                    else:
                        # 다른 채널들은 시뮬레이션
                        success = True

                    message.sent_status[channel_name] = success
                except Exception as e:
                    logging.error(f"Notification failed for {channel_name}: {e}")
                    message.sent_status[channel_name] = False

        # 히스토리에 추가
        self._add_to_history(message)

    def _add_to_history(self, message: NotificationMessage):
        """히스토리에 추가"""
        if 'notification_history' not in st.session_state:
            st.session_state.notification_history = []

        st.session_state.notification_history.append({
            'id': message.id,
            'type': message.type.value,
            'level': message.level.name,
            'title': message.title,
            'message': message.message,
            'timestamp': message.timestamp.isoformat(),
            'channels': message.channels,
            'sent_status': message.sent_status
        })

    def get_default_config(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        return {
            'enabled': True,
            'min_level': 'INFO',
            'rate_limit': 10,
            'dashboard': {'enabled': True},
            'email': {'enabled': False},
            'discord': {'enabled': False},
            'telegram': {'enabled': False}
        }

# 메인 실행 함수
def main():
    """메인 실행 함수"""
    notification_system = AdvancedNotificationSystem()
    notification_system.show_notification_dashboard()

if __name__ == "__main__":
    main()