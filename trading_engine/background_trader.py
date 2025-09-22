"""
Background Trading Bot for Crypto Trader Pro
24시간 독립 거래 봇 - 웹 인터페이스와 분리된 백그라운드 프로세스
"""

import sys
import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import signal

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database import get_db_manager, User, TradingSettings
from database.api_manager import get_api_manager as get_api_key_manager
from .market_monitor import MarketDataMonitor
from .user_trading_context import UserTradingContext
from .trading_scheduler import TradingScheduler

# 로그 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/background_trader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BackgroundTradingBot:
    """백그라운드 거래 봇 메인 클래스"""

    def __init__(self):
        """거래 봇 초기화"""
        self.db_manager = get_db_manager()
        self.api_key_manager = get_api_key_manager()
        self.market_monitor = MarketDataMonitor()
        self.trading_scheduler = TradingScheduler()

        self.is_running = False
        self.active_users: Dict[int, UserTradingContext] = {}
        self.last_user_check = datetime.utcnow()
        self.user_check_interval = 300  # 5분마다 활성 사용자 체크

        # 시그널 핸들러 설정
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        logger.info("Background Trading Bot initialized")

    def start(self):
        """거래 봇 시작"""
        try:
            self.is_running = True
            logger.info("🚀 Background Trading Bot starting...")

            # 시작 시 활성 사용자 로드
            self._load_active_users()

            # 메인 루프 시작
            asyncio.run(self._main_loop())

        except Exception as e:
            logger.error(f"Background Trading Bot start error: {e}")
            self.stop()

    def stop(self):
        """거래 봇 중지"""
        logger.info("🛑 Background Trading Bot stopping...")
        self.is_running = False

        # 모든 사용자 거래 세션 정리
        for user_id, context in self.active_users.items():
            try:
                context.stop_trading()
                logger.info(f"Trading stopped for user {user_id}")
            except Exception as e:
                logger.error(f"Error stopping trading for user {user_id}: {e}")

        self.active_users.clear()
        logger.info("Background Trading Bot stopped")

    async def _main_loop(self):
        """메인 거래 루프"""
        logger.info("📊 Main trading loop started")

        while self.is_running:
            try:
                # 활성 사용자 체크 (5분마다)
                if datetime.utcnow() - self.last_user_check > timedelta(seconds=self.user_check_interval):
                    await self._check_active_users()
                    self.last_user_check = datetime.utcnow()

                # 시장 데이터 업데이트
                await self.market_monitor.update_market_data()

                # 각 사용자별 거래 실행
                await self._process_user_trading()

                # 1초 대기
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Main loop error: {e}")
                await asyncio.sleep(5)  # 오류 시 5초 대기

    async def _check_active_users(self):
        """활성 거래 사용자 확인 및 업데이트"""
        try:
            logger.info("🔍 Checking active trading users...")

            # 데이터베이스에서 활성 거래 사용자 조회
            active_users = self.db_manager.get_active_trading_users()

            current_user_ids = set(self.active_users.keys())
            new_user_ids = set(user.id for user in active_users)

            # 비활성화된 사용자 제거
            removed_users = current_user_ids - new_user_ids
            for user_id in removed_users:
                await self._remove_user(user_id)

            # 새로 활성화된 사용자 추가
            added_users = new_user_ids - current_user_ids
            for user_id in added_users:
                user = next((u for u in active_users if u.id == user_id), None)
                if user:
                    await self._add_user(user)

            logger.info(f"Active users: {len(self.active_users)}, Added: {len(added_users)}, Removed: {len(removed_users)}")

        except Exception as e:
            logger.error(f"Error checking active users: {e}")

    async def _add_user(self, user: User):
        """새 사용자 거래 컨텍스트 추가"""
        try:
            # 사용자 거래 설정 조회
            trading_settings = self.db_manager.get_user_trading_settings(user.id)
            if not trading_settings or not trading_settings.auto_trading_enabled:
                logger.warning(f"User {user.id} has auto trading disabled")
                return

            # API 키 조회
            api_credentials = self.api_key_manager.get_api_credentials(
                user.id, "binance", is_testnet=True
            )
            if not api_credentials:
                logger.warning(f"No API credentials found for user {user.id}")
                return

            # 사용자 거래 컨텍스트 생성
            user_context = UserTradingContext(
                user=user,
                trading_settings=trading_settings,
                api_credentials=api_credentials,
                market_monitor=self.market_monitor
            )

            # 거래 세션 시작
            success = await user_context.start_trading()
            if success:
                self.active_users[user.id] = user_context
                logger.info(f"✅ Added user {user.id} ({user.username}) to active trading")
            else:
                logger.error(f"Failed to start trading for user {user.id}")

        except Exception as e:
            logger.error(f"Error adding user {user.id}: {e}")

    async def _remove_user(self, user_id: int):
        """사용자 거래 컨텍스트 제거"""
        try:
            if user_id in self.active_users:
                context = self.active_users[user_id]
                await context.stop_trading()
                del self.active_users[user_id]
                logger.info(f"❌ Removed user {user_id} from active trading")

        except Exception as e:
            logger.error(f"Error removing user {user_id}: {e}")

    async def _process_user_trading(self):
        """모든 활성 사용자에 대해 거래 처리"""
        if not self.active_users:
            return

        # 각 사용자별 병렬 처리
        tasks = []
        for user_id, context in self.active_users.items():
            if context.is_active:
                task = asyncio.create_task(context.process_trading_cycle())
                tasks.append(task)

        if tasks:
            # 모든 거래 작업을 병렬로 실행
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 결과 처리
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    user_id = list(self.active_users.keys())[i]
                    logger.error(f"Trading error for user {user_id}: {result}")

    def _load_active_users(self):
        """시작 시 활성 사용자 로드"""
        try:
            active_users = self.db_manager.get_active_trading_users()
            logger.info(f"Found {len(active_users)} active trading users")

            for user in active_users:
                # 동기적으로 사용자 추가 (시작 시에만)
                asyncio.create_task(self._add_user(user))

        except Exception as e:
            logger.error(f"Error loading active users: {e}")

    def _signal_handler(self, signum, frame):
        """시그널 핸들러"""
        logger.info(f"Received signal {signum}, stopping bot...")
        self.stop()

    def get_status(self) -> Dict:
        """거래 봇 상태 조회"""
        return {
            'is_running': self.is_running,
            'active_users': len(self.active_users),
            'users': [
                {
                    'user_id': user_id,
                    'username': context.user.username,
                    'is_active': context.is_active,
                    'last_signal_time': context.last_signal_time,
                    'total_trades': context.total_trades,
                    'profit_loss': context.session_profit_loss
                }
                for user_id, context in self.active_users.items()
            ],
            'last_user_check': self.last_user_check,
            'market_data_status': self.market_monitor.get_status()
        }

def main():
    """메인 실행 함수"""
    try:
        # 로그 디렉토리 생성
        os.makedirs('logs', exist_ok=True)

        # 거래 봇 생성 및 시작
        bot = BackgroundTradingBot()
        bot.start()

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()