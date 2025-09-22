"""
Email Notification System for Crypto Trader Pro
이메일 알림 시스템
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .base_notifier import BaseNotifier, NotificationMessage
import logging

logger = logging.getLogger(__name__)

class EmailNotifier(BaseNotifier):
    """이메일 알림 클래스"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.smtp_server = config.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = config.get('smtp_port', 587)
        self.smtp_username = config.get('smtp_username', '')
        self.smtp_password = config.get('smtp_password', '')
        self.from_email = config.get('from_email', self.smtp_username)
        self.use_tls = config.get('use_tls', True)

        # 스레드 풀 실행기 (비동기 이메일 전송용)
        self.executor = ThreadPoolExecutor(max_workers=3)

    async def send_notification(self, message: NotificationMessage) -> bool:
        """이메일 알림 전송"""
        try:
            # 비동기로 이메일 전송
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._send_email_sync,
                message
            )
            return result
        except Exception as e:
            self.logger.error(f"Email notification failed: {e}")
            return False

    def _send_email_sync(self, message: NotificationMessage) -> bool:
        """동기 이메일 전송"""
        try:
            # 수신자 이메일 조회 (실제 구현에서는 데이터베이스에서 가져와야 함)
            to_email = self._get_user_email(message.user_id)
            if not to_email:
                self.logger.warning(f"No email found for user {message.user_id}")
                return False

            # 이메일 메시지 생성
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[Crypto Trader Pro] {message.title}"
            msg['From'] = self.from_email
            msg['To'] = to_email

            # HTML과 텍스트 버전 생성
            text_content = self._create_text_content(message)
            html_content = self._create_html_content(message)

            # 메시지 첨부
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            html_part = MIMEText(html_content, 'html', 'utf-8')

            msg.attach(text_part)
            msg.attach(html_part)

            # SMTP 서버 연결 및 전송
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls(context=ssl.create_default_context())

                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)

                server.send_message(msg)

            self.logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False

    def _get_user_email(self, user_id: int) -> str:
        """사용자 이메일 조회"""
        # TODO: 실제 구현에서는 데이터베이스에서 조회
        # 임시로 테스트 이메일 반환
        test_emails = {
            1: "admin@example.com",
            2: "trader1@example.com"
        }
        return test_emails.get(user_id, "")

    def _create_text_content(self, message: NotificationMessage) -> str:
        """텍스트 이메일 내용 생성"""
        content = f"""
Crypto Trader Pro 알림

제목: {message.title}
내용: {message.message}
시간: {message.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
우선순위: {message.priority.upper()}

"""
        if message.data:
            content += "\n상세 정보:\n"
            for key, value in message.data.items():
                content += f"  {key}: {value}\n"

        content += "\n\n---\nCrypto Trader Pro - 24시간 무인 자동매매 시스템"
        return content

    def _create_html_content(self, message: NotificationMessage) -> str:
        """HTML 이메일 내용 생성"""
        priority_colors = {
            "low": "#6c757d",
            "normal": "#28a745",
            "high": "#ffc107",
            "urgent": "#dc3545"
        }

        priority_color = priority_colors.get(message.priority, "#28a745")

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Crypto Trader Pro 알림</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f8f9fa; padding: 20px; }}
        .priority-badge {{ background: {priority_color}; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; }}
        .data-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        .data-table th, .data-table td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        .footer {{ background: #343a40; color: white; padding: 15px; text-align: center; border-radius: 0 0 10px 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Crypto Trader Pro</h1>
            <p>24시간 무인 자동매매 시스템</p>
        </div>

        <div class="content">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2>{message.title}</h2>
                <span class="priority-badge">{message.priority.upper()}</span>
            </div>

            <p style="font-size: 16px; line-height: 1.6;">{message.message}</p>

            <p><strong>⏰ 시간:</strong> {message.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
"""

        if message.data:
            html_content += """
            <h3>📊 상세 정보</h3>
            <table class="data-table">
"""
            for key, value in message.data.items():
                html_content += f"<tr><th>{key}</th><td>{value}</td></tr>"

            html_content += "</table>"

        html_content += """
        </div>

        <div class="footer">
            <p>Crypto Trader Pro - Professional Trading Platform</p>
            <p style="font-size: 12px; color: #adb5bd;">이 이메일은 자동으로 발송되었습니다.</p>
        </div>
    </div>
</body>
</html>
"""
        return html_content

    def test_connection(self) -> bool:
        """SMTP 연결 테스트"""
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls(context=ssl.create_default_context())

                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)

            self.logger.info("SMTP connection test successful")
            return True

        except Exception as e:
            self.logger.error(f"SMTP connection test failed: {e}")
            return False