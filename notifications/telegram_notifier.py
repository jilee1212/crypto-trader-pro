"""
Telegram Notification System for Crypto Trader Pro
텔레그램 봇 알림 시스템
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional
import json
import logging

from .base_notifier import BaseNotifier, NotificationMessage, NotificationType

logger = logging.getLogger(__name__)

class TelegramNotifier(BaseNotifier):
    """텔레그램 봇 알림 클래스"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bot_token = config.get('bot_token', '')
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

        # HTTP 세션 재사용
        self.session: Optional[aiohttp.ClientSession] = None

    async def send_notification(self, message: NotificationMessage) -> bool:
        """텔레그램 알림 전송"""
        try:
            # 사용자 Chat ID 조회
            chat_id = self._get_user_chat_id(message.user_id)
            if not chat_id:
                self.logger.warning(f"No Telegram chat ID found for user {message.user_id}")
                return False

            # 메시지 포맷팅
            formatted_message = self._format_telegram_message(message)

            # 텔레그램 API로 메시지 전송
            success = await self._send_telegram_message(chat_id, formatted_message)

            if success:
                self.logger.info(f"Telegram message sent successfully to user {message.user_id}")
            else:
                self.logger.error(f"Failed to send Telegram message to user {message.user_id}")

            return success

        except Exception as e:
            self.logger.error(f"Telegram notification error: {e}")
            return False

    async def _send_telegram_message(self, chat_id: str, message: str, parse_mode: str = "MarkdownV2") -> bool:
        """텔레그램 메시지 전송"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            url = f"{self.api_url}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }

            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    return True
                else:
                    response_text = await response.text()
                    self.logger.error(f"Telegram API error: {response.status} - {response_text}")
                    return False

        except Exception as e:
            self.logger.error(f"Failed to send Telegram message: {e}")
            return False

    def _get_user_chat_id(self, user_id: int) -> str:
        """사용자 텔레그램 Chat ID 조회"""
        # TODO: 실제 구현에서는 데이터베이스에서 조회
        # 임시로 테스트 Chat ID 반환
        test_chat_ids = {
            1: "123456789",  # admin 테스트 Chat ID
            2: "987654321"   # trader1 테스트 Chat ID
        }
        return test_chat_ids.get(user_id, "")

    def _format_telegram_message(self, message: NotificationMessage) -> str:
        """텔레그램 메시지 포맷팅 (MarkdownV2)"""
        # 특수 문자 이스케이프 (MarkdownV2 요구사항)
        def escape_markdown(text: str) -> str:
            chars_to_escape = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
            for char in chars_to_escape:
                text = text.replace(char, f'\\{char}')
            return text

        # 우선순위 이모지
        priority_emojis = {
            "low": "🔵",
            "normal": "🟢",
            "high": "🟡",
            "urgent": "🔴"
        }

        # 알림 유형별 이모지
        type_emojis = {
            NotificationType.TRADE_EXECUTED: "✅",
            NotificationType.SIGNAL_GENERATED: "📡",
            NotificationType.POSITION_OPENED: "📈",
            NotificationType.POSITION_CLOSED: "📉",
            NotificationType.STOP_LOSS_TRIGGERED: "🛑",
            NotificationType.TAKE_PROFIT_TRIGGERED: "💰",
            NotificationType.BALANCE_LOW: "⚠️",
            NotificationType.ERROR_OCCURRED: "❌",
            NotificationType.SYSTEM_STATUS: "🔧",
            NotificationType.DAILY_REPORT: "📊"
        }

        priority_emoji = priority_emojis.get(message.priority, "🟢")
        type_emoji = type_emojis.get(message.type, "📢")

        # 메시지 헤더
        header = f"{type_emoji} *Crypto Trader Pro*\n"
        header += f"{priority_emoji} *{escape_markdown(message.title)}*\n\n"

        # 메시지 본문
        content = escape_markdown(message.message) + "\n\n"

        # 상세 정보
        if message.data:
            content += "*📊 상세 정보:*\n"
            for key, value in message.data.items():
                escaped_key = escape_markdown(str(key))
                escaped_value = escape_markdown(str(value))
                content += f"• *{escaped_key}:* `{escaped_value}`\n"
            content += "\n"

        # 시간 정보
        timestamp = message.timestamp.strftime('%Y\\-m\\-d %H:%M:%S UTC')
        footer = f"⏰ {timestamp}\n"
        footer += "_Crypto Trader Pro \\- 24시간 무인 자동매매 시스템_"

        return header + content + footer

    async def send_image(self, chat_id: str, image_path: str, caption: str = "") -> bool:
        """이미지 전송 (차트, 그래프 등)"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            url = f"{self.api_url}/sendPhoto"

            with open(image_path, 'rb') as image_file:
                data = aiohttp.FormData()
                data.add_field('chat_id', chat_id)
                data.add_field('photo', image_file, filename='chart.png')
                if caption:
                    data.add_field('caption', caption)
                    data.add_field('parse_mode', 'MarkdownV2')

                async with self.session.post(url, data=data) as response:
                    return response.status == 200

        except Exception as e:
            self.logger.error(f"Failed to send Telegram image: {e}")
            return False

    async def get_bot_info(self) -> Dict[str, Any]:
        """봇 정보 조회"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            url = f"{self.api_url}/getMe"

            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {}

        except Exception as e:
            self.logger.error(f"Failed to get bot info: {e}")
            return {}

    async def test_connection(self) -> bool:
        """텔레그램 봇 연결 테스트"""
        try:
            bot_info = await self.get_bot_info()
            if bot_info.get('ok'):
                bot_data = bot_info.get('result', {})
                self.logger.info(f"Telegram bot connected: @{bot_data.get('username', 'unknown')}")
                return True
            else:
                self.logger.error("Telegram bot connection failed")
                return False

        except Exception as e:
            self.logger.error(f"Telegram connection test error: {e}")
            return False

    async def close(self):
        """리소스 정리"""
        if self.session:
            await self.session.close()
            self.session = None

    def __del__(self):
        """소멸자"""
        if self.session and not self.session.closed:
            asyncio.create_task(self.close())