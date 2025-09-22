"""
🤖 AutoTradingEngine - 자동매매 메인 엔진

24시간 무인 자동매매 시스템의 핵심 엔진
- 거래 루프 관리
- 컴포넌트 간 조율
- 시작/중단 제어
- 안전장치 운영
"""

import asyncio
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass
from enum import Enum

import sys
import os
# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

try:
    from auto_trading.config_manager import ConfigManager
    from auto_trading.market_monitor import MarketMonitor
    from auto_trading.signal_generator import AISignalGenerator
    from auto_trading.trade_executor import TradeExecutor
    from auto_trading.position_manager import PositionManager
    from auto_trading.risk_manager import RiskManager, EmergencyStop, SafetySystem
    from utils.notifications import NotificationManager, NotificationType, NotificationPriority
except ImportError as e:
    # 대체 임포트 (시뮬레이션 모드)
    print(f"ImportError in engine.py: {e}")

    # 임시 클래스들 정의
    class ConfigManager:
        def __init__(self): pass
    class MarketMonitor:
        def __init__(self): pass
    class AISignalGenerator:
        def __init__(self): pass
    class TradeExecutor:
        def __init__(self): pass
    class PositionManager:
        def __init__(self): pass
    class RiskManager:
        def __init__(self): pass
    class EmergencyStop:
        def __init__(self): pass
    class SafetySystem:
        def __init__(self): pass
    class NotificationManager:
        def __init__(self): pass
    class NotificationType:
        SYSTEM_ERROR = "SYSTEM_ERROR"
    class NotificationPriority:
        HIGH = 3

class TradingStatus(Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    ERROR = "ERROR"
    EMERGENCY_STOP = "EMERGENCY_STOP"

@dataclass
class EngineStats:
    start_time: Optional[datetime] = None
    total_trades: int = 0
    successful_trades: int = 0
    total_pnl: float = 0.0
    today_pnl: float = 0.0
    active_positions: int = 0
    signals_generated: int = 0
    errors_count: int = 0

class AutoTradingEngine:
    """
    🤖 자동매매 메인 엔진

    기능:
    - 24시간 무인 거래 실행
    - AI 신호 기반 자동 매매
    - 실시간 리스크 관리
    - 안전장치 운영
    """

    def __init__(self, config_path: str = None):
        """엔진 초기화"""
        self.logger = logging.getLogger(__name__)

        # 상태 관리
        self.status = TradingStatus.STOPPED
        self.stats = EngineStats()
        self._stop_event = threading.Event()
        self._trading_thread = None

        # 컴포넌트 초기화
        self.config_manager = ConfigManager(config_path)
        self.market_monitor = MarketMonitor(self.config_manager)
        self.signal_generator = AISignalGenerator(self.config_manager)
        self.trade_executor = TradeExecutor(self.config_manager)
        self.position_manager = PositionManager(self.config_manager)
        self.risk_manager = RiskManager(self.config_manager)

        # Phase 3: 안전 시스템 및 알림 시스템 초기화
        self.emergency_stop = EmergencyStop(self.config_manager, self.position_manager)
        self.safety_system = SafetySystem(
            self.config_manager, self.risk_manager,
            self.emergency_stop, self.position_manager
        )

        # 알림 시스템 초기화
        notification_config = self.config_manager.get_config().get('notifications', {})
        self.notification_manager = NotificationManager(notification_config)

        # 안전 검사 스케줄러
        self.safety_check_interval = 60  # 60초마다 안전 검사
        self.last_safety_check = datetime.now()

        # 설정 로드
        self.config = self.config_manager.get_config()

        self.logger.info("AutoTradingEngine Phase 3 초기화 완료 (안전 시스템 + 알림 시스템)")

    def start_trading(self) -> bool:
        """
        자동매매 시작

        Returns:
            bool: 시작 성공 여부
        """
        try:
            if self.status == TradingStatus.RUNNING:
                self.logger.warning("자동매매가 이미 실행 중입니다")
                return False

            self.logger.info("자동매매 시작 중...")
            self.status = TradingStatus.STARTING

            # 사전 검사 실행
            if not self._pre_trading_checks():
                self.status = TradingStatus.ERROR
                return False

            # 통계 초기화
            self.stats.start_time = datetime.now()
            self._stop_event.clear()

            # 거래 스레드 시작
            self._trading_thread = threading.Thread(
                target=self._trading_loop,
                daemon=True
            )
            self._trading_thread.start()

            self.status = TradingStatus.RUNNING
            self.logger.info("🚀 자동매매 시작됨")
            return True

        except Exception as e:
            self.logger.error(f"자동매매 시작 실패: {e}")
            self.status = TradingStatus.ERROR
            return False

    def stop_trading(self, emergency: bool = False) -> bool:
        """
        자동매매 중단

        Args:
            emergency: 긴급 중단 여부

        Returns:
            bool: 중단 성공 여부
        """
        try:
            if self.status not in [TradingStatus.RUNNING, TradingStatus.STARTING]:
                self.logger.warning("자동매매가 실행 중이 아닙니다")
                return False

            if emergency:
                self.logger.critical("🚨 긴급 중단 실행")
                self.status = TradingStatus.EMERGENCY_STOP
            else:
                self.logger.info("자동매매 중단 중...")
                self.status = TradingStatus.STOPPING

            # 중단 이벤트 설정
            self._stop_event.set()

            # 거래 스레드 종료 대기
            if self._trading_thread and self._trading_thread.is_alive():
                self._trading_thread.join(timeout=30)

            # 긴급 중단 시 포지션 청산 (선택적)
            if emergency and self.config.get('emergency_liquidation', False):
                self._emergency_liquidation()

            self.status = TradingStatus.STOPPED
            self.logger.info("⏸️ 자동매매 중단됨")
            return True

        except Exception as e:
            self.logger.error(f"자동매매 중단 실패: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """
        현재 상태 반환

        Returns:
            Dict: 엔진 상태 정보
        """
        uptime = None
        if self.stats.start_time:
            uptime = datetime.now() - self.stats.start_time

        return {
            'status': self.status.value,
            'uptime': str(uptime) if uptime else None,
            'stats': {
                'total_trades': self.stats.total_trades,
                'successful_trades': self.stats.successful_trades,
                'success_rate': (
                    self.stats.successful_trades / max(self.stats.total_trades, 1) * 100
                ),
                'total_pnl': self.stats.total_pnl,
                'today_pnl': self.stats.today_pnl,
                'active_positions': self.stats.active_positions,
                'signals_generated': self.stats.signals_generated,
                'errors_count': self.stats.errors_count
            },
            'config': {
                'trading_interval': self.config.get('trading_interval', 300),
                'max_positions': self.config.get('max_positions', 5),
                'symbols': self.config.get('symbols', []),
                'risk_level': self.config.get('risk_level', 'CONSERVATIVE')
            }
        }

    def _pre_trading_checks(self) -> bool:
        """거래 시작 전 사전 검사"""
        self.logger.info("사전 검사 실행 중...")

        # 1. 설정 유효성 검사
        if not self.config_manager.validate_config():
            self.logger.error("설정 유효성 검사 실패")
            return False

        # 2. API 연결 확인
        if not self.trade_executor.test_connection():
            self.logger.error("거래소 API 연결 실패")
            return False

        # 3. 리스크 관리 검사
        if not self.risk_manager.pre_trading_check():
            self.logger.error("리스크 관리 검사 실패")
            return False

        # 4. 시장 데이터 확인
        if not self.market_monitor.test_data_feed():
            self.logger.error("시장 데이터 연결 실패")
            return False

        self.logger.info("✅ 모든 사전 검사 통과")
        return True

    def _trading_loop(self):
        """메인 거래 루프 (Phase 3 Enhanced)"""
        self.logger.info("Phase 3 거래 루프 시작 (고급 안전 시스템)")

        # 알림 워커 시작
        asyncio.run(self.notification_manager.start_worker())

        # 시작 알림 발송
        asyncio.run(self.notification_manager.send_notification(
            NotificationType.SYSTEM_STARTUP,
            title="자동매매 시스템 시작",
            message="자동매매 시스템이 성공적으로 시작되었습니다",
            priority=NotificationPriority.HIGH
        ))

        while not self._stop_event.is_set():
            try:
                # 1. Phase 3: 다층 안전장치 검사
                safety_passed, safety_checks = asyncio.run(self.safety_system.run_all_safety_checks())

                if not safety_passed:
                    critical_failures = [c for c in safety_checks if not c.passed and self.safety_system._is_critical_failure(c)]
                    if critical_failures:
                        self.logger.critical(f"심각한 안전 검사 실패: {[c.name for c in critical_failures]}")
                        asyncio.run(self._trigger_emergency_stop("안전 검사 실패", critical_failures))
                        break
                    else:
                        self.logger.warning("일부 안전 검사 실패 - 거래 일시 중단")
                        self._pause_trading()
                        continue

                # 2. 긴급 상황 모니터링
                is_emergency, trigger, message = self.emergency_stop.check_emergency_conditions()
                if is_emergency:
                    self.logger.critical(f"긴급 상황 감지: {message}")
                    asyncio.run(self._trigger_emergency_stop(message, trigger))
                    break

                # 3. 기존 리스크 매니저 검사 (하위 호환성)
                if not self.risk_manager.safety_check():
                    self.logger.warning("기본 안전장치 활성화 - 거래 일시 중단")
                    self._pause_trading()
                    continue

                # 4. 시장 데이터 수집
                market_data = self.market_monitor.collect_data()
                if not market_data:
                    self.logger.warning("시장 데이터 수집 실패")
                    continue

                # 5. AI 신호 생성
                signals = self.signal_generator.generate_signals(market_data)
                self.stats.signals_generated += len(signals)

                # 6. 신호 처리 및 거래 실행
                for signal in signals:
                    if self._stop_event.is_set():
                        break

                    # 다층 리스크 검증
                    if not self.risk_manager.validate_signal(signal):
                        continue

                    # 거래 실행
                    execution_result = self.trade_executor.execute_signal(signal)
                    if execution_result:
                        self.stats.total_trades += 1
                        self.stats.successful_trades += 1

                        # 거래 실행 알림
                        asyncio.run(self.notification_manager.send_notification(
                            NotificationType.TRADE_EXECUTED,
                            data={
                                'symbol': signal.symbol,
                                'side': signal.signal_type,
                                'price': signal.entry_price,
                                'quantity': execution_result.get('quantity', 0)
                            }
                        ))
                    else:
                        self.stats.total_trades += 1

                # 7. 포지션 관리
                self.position_manager.manage_positions()
                self.stats.active_positions = self.position_manager.get_active_count()

                # 8. 성과 업데이트
                self._update_performance()

                # 9. 주기적 안전 검사 (빠른 검사)
                current_time = datetime.now()
                if (current_time - self.last_safety_check).seconds >= self.safety_check_interval:
                    self._perform_periodic_safety_check()
                    self.last_safety_check = current_time

                # 대기
                interval = self.config.get('trading_interval', 300)
                self._stop_event.wait(interval)

            except Exception as e:
                self.logger.error(f"거래 루프 오류: {e}")
                self.stats.errors_count += 1

                # 시스템 오류 알림
                asyncio.run(self.notification_manager.send_notification(
                    NotificationType.SYSTEM_ERROR,
                    data={'error': str(e)},
                    priority=NotificationPriority.CRITICAL
                ))

                # 연속 오류 시 긴급 중단
                if self.stats.errors_count > 10:
                    self.logger.critical("연속 오류 발생 - 긴급 중단 실행")
                    asyncio.run(self._trigger_emergency_stop("연속 시스템 오류", None))
                    break

                # 오류 복구 대기
                time.sleep(60)

        # 종료 알림
        asyncio.run(self.notification_manager.send_notification(
            NotificationType.SYSTEM_SHUTDOWN,
            title="자동매매 시스템 종료",
            message="자동매매 시스템이 안전하게 종료되었습니다",
            priority=NotificationPriority.HIGH
        ))

        # 알림 워커 종료
        asyncio.run(self.notification_manager.stop_worker())

        self.logger.info("Phase 3 거래 루프 종료")

    def _pause_trading(self):
        """거래 일시 중단"""
        self.logger.info("거래 일시 중단 - 5분 후 재시도")
        self._stop_event.wait(300)  # 5분 대기

    def _update_performance(self):
        """성과 업데이트"""
        try:
            pnl_data = self.position_manager.calculate_pnl()
            self.stats.total_pnl = pnl_data.get('total_pnl', 0)
            self.stats.today_pnl = pnl_data.get('today_pnl', 0)
        except Exception as e:
            self.logger.error(f"성과 업데이트 실패: {e}")

    def _emergency_liquidation(self):
        """긴급 포지션 청산"""
        try:
            self.logger.critical("긴급 포지션 청산 실행")
            self.position_manager.liquidate_all_positions()
        except Exception as e:
            self.logger.error(f"긴급 청산 실패: {e}")

    async def _trigger_emergency_stop(self, reason: str, trigger_data: Any = None):
        """긴급 중단 실행"""
        try:
            self.logger.critical(f"긴급 중단 트리거: {reason}")

            # 긴급 중단 시스템 활성화
            from .risk_manager import EmergencyStopTrigger
            success = self.emergency_stop.trigger_emergency_stop(
                trigger=EmergencyStopTrigger.SYSTEM_ERROR,
                message=reason,
                data={'trigger_data': trigger_data}
            )

            if success:
                self.status = TradingStatus.EMERGENCY_STOP
                self._stop_event.set()

                # 긴급 알림 발송
                await self.notification_manager.send_notification(
                    NotificationType.EMERGENCY_STOP,
                    data={'reason': reason, 'action': '시스템 중단'},
                    priority=NotificationPriority.EMERGENCY
                )

        except Exception as e:
            self.logger.error(f"긴급 중단 처리 실패: {e}")

    def _perform_periodic_safety_check(self):
        """주기적 안전 검사 (빠른 검사)"""
        try:
            # 기본적인 상태 확인
            current_positions = self.position_manager.get_active_count()
            max_positions = self.risk_manager.max_positions

            if current_positions >= max_positions:
                self.logger.warning(f"포지션 한도 근접: {current_positions}/{max_positions}")

            # 일일 손실 확인
            daily_pnl = self.stats.today_pnl
            daily_limit = self.risk_manager.loss_limits.daily_limit_amount

            if daily_pnl <= -daily_limit * 0.8:  # 80% 도달 시 경고
                asyncio.run(self.notification_manager.send_notification(
                    NotificationType.DAILY_LOSS_WARNING,
                    data={
                        'loss': daily_pnl,
                        'threshold': 80.0
                    },
                    priority=NotificationPriority.HIGH
                ))

        except Exception as e:
            self.logger.error(f"주기적 안전 검사 실패: {e}")

    def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 조회 (Phase 3 Enhanced)"""
        try:
            base_status = {
                'status': self.status.value,
                'uptime': (datetime.now() - self.stats.start_time).total_seconds() if self.stats.start_time else 0,
                'stats': {
                    'total_trades': self.stats.total_trades,
                    'successful_trades': self.stats.successful_trades,
                    'success_rate': (self.stats.successful_trades / self.stats.total_trades * 100) if self.stats.total_trades > 0 else 0,
                    'total_pnl': self.stats.total_pnl,
                    'today_pnl': self.stats.today_pnl,
                    'active_positions': self.stats.active_positions,
                    'signals_generated': self.stats.signals_generated,
                    'errors_count': self.stats.errors_count
                }
            }

            # Phase 3 추가 정보
            phase3_status = {
                'safety_system': self.safety_system.get_safety_status(),
                'emergency_system': self.emergency_stop.get_emergency_status(),
                'notification_system': self.notification_manager.get_notification_status(),
                'last_safety_check': self.last_safety_check.isoformat()
            }

            base_status.update(phase3_status)
            return base_status

        except Exception as e:
            self.logger.error(f"시스템 상태 조회 실패: {e}")
            return {'error': str(e)}

    def get_dashboard_data(self) -> Dict[str, Any]:
        """대시보드용 데이터 조회"""
        try:
            return {
                'system_status': self.get_system_status(),
                'recent_notifications': self.notification_manager.get_dashboard_messages(20),
                'safety_status': self.safety_system.get_safety_status(),
                'emergency_status': self.emergency_stop.get_emergency_status()
            }
        except Exception as e:
            self.logger.error(f"대시보드 데이터 조회 실패: {e}")
            return {'error': str(e)}

    def manual_emergency_stop(self, reason: str = "수동 중단"):
        """수동 긴급 중단"""
        try:
            self.logger.info(f"수동 긴급 중단 요청: {reason}")
            asyncio.run(self._trigger_emergency_stop(reason, None))
            return True
        except Exception as e:
            self.logger.error(f"수동 긴급 중단 실패: {e}")
            return False

    def reset_emergency_mode(self):
        """긴급 모드 해제"""
        try:
            if self.emergency_stop.reset_emergency_mode():
                if self.status == TradingStatus.EMERGENCY_STOP:
                    self.status = TradingStatus.STOPPED
                self.logger.info("긴급 모드가 해제되었습니다")
                return True
            return False
        except Exception as e:
            self.logger.error(f"긴급 모드 해제 실패: {e}")
            return False

    def __del__(self):
        """소멸자 - 리소스 정리"""
        if self.status == TradingStatus.RUNNING:
            self.stop_trading()