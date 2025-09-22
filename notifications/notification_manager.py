"""
Notification Manager for Crypto Trader Pro
알림 시스템 통합 관리자
"""

import asyncio
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from .base_notifier import BaseNotifier, NotificationMessage, NotificationType
from .email_notifier import EmailNotifier
from .telegram_notifier import TelegramNotifier
from .web_notifier import WebNotifier

logger = logging.getLogger(__name__)

class NotificationManager:
    """알림 시스템 통합 관리자"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.notifiers: Dict[str, BaseNotifier] = {}
        self.enabled = config.get('enabled', True)

        # 알림 채널 초기화
        self._initialize_notifiers()

    def _initialize_notifiers(self):
        """알림 채널 초기화"""
        try:
            # 이메일 알림
            if self.config.get('email', {}).get('enabled', False):
                self.notifiers['email'] = EmailNotifier(self.config['email'])
                logger.info("Email notifier initialized")

            # 텔레그램 알림
            if self.config.get('telegram', {}).get('enabled', False):
                self.notifiers['telegram'] = TelegramNotifier(self.config['telegram'])
                logger.info("Telegram notifier initialized")

            # 웹 알림 (항상 활성화)
            web_config = self.config.get('web', {})
            web_config['enabled'] = True  # 웹 알림은 항상 활성화
            self.notifiers['web'] = WebNotifier(web_config)
            logger.info("Web notifier initialized")

        except Exception as e:
            logger.error(f"Failed to initialize notifiers: {e}")

    async def send_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        priority: str = "normal",
        channels: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """알림 전송"""
        if not self.enabled:
            logger.warning("Notification manager is disabled")
            return {}

        # 알림 메시지 생성
        notification = NotificationMessage(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            data=data,
            priority=priority,
            timestamp=datetime.utcnow()
        )

        # 사용자 알림 설정 조회
        user_settings = self._get_user_notification_settings(user_id)

        # 전송할 채널 결정
        if channels is None:
            channels = list(self.notifiers.keys())

        # 병렬로 알림 전송
        results = {}
        tasks = []

        for channel in channels:
            if channel in self.notifiers:
                notifier = self.notifiers[channel]
                if notifier.should_send(notification, user_settings.get(channel, {})):
                    tasks.append(self._send_single_notification(channel, notifier, notification))

        if tasks:
            channel_results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(channel_results):
                channel = channels[i] if i < len(channels) else f"unknown_{i}"
                if isinstance(result, Exception):
                    logger.error(f"Notification failed for channel {channel}: {result}")
                    results[channel] = False
                else:
                    results[channel] = result

        return results

    async def _send_single_notification(
        self,
        channel: str,
        notifier: BaseNotifier,
        notification: NotificationMessage
    ) -> bool:
        """단일 채널 알림 전송"""
        try:
            return await notifier.send_notification(notification)
        except Exception as e:
            logger.error(f"Failed to send notification via {channel}: {e}")
            return False

    def _get_user_notification_settings(self, user_id: int) -> Dict[str, Any]:
        """사용자 알림 설정 조회"""
        # TODO: 실제 구현에서는 데이터베이스에서 조회
        # 임시 기본 설정 반환
        return {
            'email': {
                'trade_executed_enabled': True,
                'signal_generated_enabled': False,
                'position_opened_enabled': True,
                'position_closed_enabled': True,
                'stop_loss_triggered_enabled': True,
                'take_profit_triggered_enabled': True,
                'balance_low_enabled': True,
                'error_occurred_enabled': True,
                'system_status_enabled': False,
                'daily_report_enabled': True,
                'min_priority': 'normal'
            },
            'telegram': {
                'trade_executed_enabled': True,
                'signal_generated_enabled': True,
                'position_opened_enabled': True,
                'position_closed_enabled': True,
                'stop_loss_triggered_enabled': True,
                'take_profit_triggered_enabled': True,
                'balance_low_enabled': True,
                'error_occurred_enabled': True,
                'system_status_enabled': True,
                'daily_report_enabled': False,
                'min_priority': 'normal'
            },
            'web': {
                'trade_executed_enabled': True,
                'signal_generated_enabled': True,
                'position_opened_enabled': True,
                'position_closed_enabled': True,
                'stop_loss_triggered_enabled': True,
                'take_profit_triggered_enabled': True,
                'balance_low_enabled': True,
                'error_occurred_enabled': True,
                'system_status_enabled': True,
                'daily_report_enabled': True,
                'min_priority': 'low'
            }
        }

    # 편의 메서드들
    async def send_trade_executed(
        self,
        user_id: int,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        pnl: Optional[float] = None
    ):
        """거래 실행 알림"""
        data = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price
        }
        if pnl is not None:
            data['pnl'] = pnl

        await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.TRADE_EXECUTED,
            title=f"거래 실행: {symbol}",
            message=f"{side} {quantity} {symbol} @ ${price:,.2f}",
            data=data,
            priority="normal"
        )

    async def send_signal_generated(
        self,
        user_id: int,
        symbol: str,
        signal: str,
        confidence: float,
        price: float
    ):
        """AI 신호 생성 알림"""
        await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.SIGNAL_GENERATED,
            title=f"AI 신호: {symbol}",
            message=f"{signal} 신호 ({confidence:.1f}% 신뢰도)",
            data={
                'symbol': symbol,
                'signal': signal,
                'confidence': confidence,
                'price': price
            },
            priority="normal"
        )

    async def send_position_opened(
        self,
        user_id: int,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        leverage: int
    ):
        """포지션 개시 알림"""
        await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.POSITION_OPENED,
            title=f"포지션 개시: {symbol}",
            message=f"{side} {quantity} {symbol} @ ${entry_price:,.2f} ({leverage}x)",
            data={
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'entry_price': entry_price,
                'leverage': leverage
            },
            priority="normal"
        )

    async def send_position_closed(
        self,
        user_id: int,
        symbol: str,
        side: str,
        quantity: float,
        exit_price: float,
        pnl: float,
        pnl_percentage: float
    ):
        """포지션 종료 알림"""
        priority = "high" if pnl < 0 else "normal"

        await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.POSITION_CLOSED,
            title=f"포지션 종료: {symbol}",
            message=f"{side} {quantity} {symbol} @ ${exit_price:,.2f} | PnL: ${pnl:,.2f} ({pnl_percentage:+.2f}%)",
            data={
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'exit_price': exit_price,
                'pnl': pnl,
                'pnl_percentage': pnl_percentage
            },
            priority=priority
        )

    async def send_error_notification(
        self,
        user_id: int,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """오류 알림"""
        await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.ERROR_OCCURRED,
            title=f"시스템 오류: {error_type}",
            message=error_message,
            data=context,
            priority="high"
        )

    async def send_daily_report(
        self,
        user_id: int,
        total_trades: int,
        total_pnl: float,
        win_rate: float,
        best_trade: float,
        worst_trade: float
    ):
        """일일 리포트 알림"""
        await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.DAILY_REPORT,
            title="일일 거래 리포트",
            message=f"총 {total_trades}건 거래 | PnL: ${total_pnl:,.2f} | 승률: {win_rate:.1f}%",
            data={
                'total_trades': total_trades,
                'total_pnl': total_pnl,
                'win_rate': win_rate,
                'best_trade': best_trade,
                'worst_trade': worst_trade
            },
            priority="normal"
        )

    async def test_all_channels(self, user_id: int) -> Dict[str, bool]:
        """모든 알림 채널 테스트"""
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.SYSTEM_STATUS,
            title="알림 시스템 테스트",
            message="모든 알림 채널이 정상적으로 작동합니다.",
            priority="low"
        )

    async def close(self):
        """리소스 정리"""
        for notifier in self.notifiers.values():
            if hasattr(notifier, 'close'):
                await notifier.close()

    def get_web_notifier(self) -> Optional[WebNotifier]:
        """웹 알림 클래스 반환"""
        return self.notifiers.get('web')