"""
Trading Scheduler for Background Trading Bot
거래 스케줄링 및 동시성 관리
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict
import json

logger = logging.getLogger(__name__)

class TradingScheduler:
    """거래 스케줄러 클래스"""

    def __init__(self):
        """스케줄러 초기화"""
        self.scheduled_tasks: Dict[str, Dict] = {}
        self.user_task_queues: Dict[int, asyncio.Queue] = defaultdict(lambda: asyncio.Queue())
        self.user_workers: Dict[int, asyncio.Task] = {}
        self.is_running = False

        # 스케줄링 설정
        self.default_intervals = {
            'signal_generation': 30,  # 30초마다 신호 생성
            'position_check': 10,     # 10초마다 포지션 체크
            'risk_check': 60,         # 1분마다 리스크 체크
            'market_update': 15       # 15초마다 마켓 업데이트
        }

        logger.info("Trading Scheduler initialized")

    async def start_scheduler(self):
        """스케줄러 시작"""
        self.is_running = True
        logger.info("Trading Scheduler started")

    async def stop_scheduler(self):
        """스케줄러 중지"""
        self.is_running = False

        # 모든 사용자 워커 중지
        for user_id, worker in self.user_workers.items():
            if not worker.done():
                worker.cancel()
                try:
                    await worker
                except asyncio.CancelledError:
                    pass

        self.user_workers.clear()
        logger.info("Trading Scheduler stopped")

    async def add_user_to_scheduler(self, user_id: int, trading_context):
        """사용자를 스케줄러에 추가"""
        try:
            if user_id in self.user_workers:
                # 기존 워커가 있으면 중지
                await self.remove_user_from_scheduler(user_id)

            # 새 워커 시작
            worker = asyncio.create_task(self._user_worker(user_id, trading_context))
            self.user_workers[user_id] = worker

            logger.info(f"User {user_id} added to trading scheduler")

        except Exception as e:
            logger.error(f"Error adding user {user_id} to scheduler: {e}")

    async def remove_user_from_scheduler(self, user_id: int):
        """사용자를 스케줄러에서 제거"""
        try:
            if user_id in self.user_workers:
                worker = self.user_workers[user_id]
                if not worker.done():
                    worker.cancel()
                    try:
                        await worker
                    except asyncio.CancelledError:
                        pass

                del self.user_workers[user_id]

            # 큐 정리
            if user_id in self.user_task_queues:
                # 큐의 남은 작업들을 모두 소비
                queue = self.user_task_queues[user_id]
                while not queue.empty():
                    try:
                        queue.get_nowait()
                        queue.task_done()
                    except asyncio.QueueEmpty:
                        break

                del self.user_task_queues[user_id]

            logger.info(f"User {user_id} removed from trading scheduler")

        except Exception as e:
            logger.error(f"Error removing user {user_id} from scheduler: {e}")

    async def _user_worker(self, user_id: int, trading_context):
        """사용자별 워커 - 독립적인 거래 루프"""
        logger.info(f"Starting worker for user {user_id}")

        try:
            last_signal_time = datetime.utcnow()
            last_position_check = datetime.utcnow()
            last_risk_check = datetime.utcnow()

            while self.is_running and trading_context.is_active:
                try:
                    current_time = datetime.utcnow()

                    # 신호 생성 스케줄
                    if (current_time - last_signal_time).total_seconds() >= self.default_intervals['signal_generation']:
                        await self._schedule_signal_generation(user_id, trading_context)
                        last_signal_time = current_time

                    # 포지션 체크 스케줄
                    if (current_time - last_position_check).total_seconds() >= self.default_intervals['position_check']:
                        await self._schedule_position_check(user_id, trading_context)
                        last_position_check = current_time

                    # 리스크 체크 스케줄
                    if (current_time - last_risk_check).total_seconds() >= self.default_intervals['risk_check']:
                        await self._schedule_risk_check(user_id, trading_context)
                        last_risk_check = current_time

                    # 큐에서 대기 중인 작업 처리
                    await self._process_user_queue(user_id, trading_context)

                    # 짧은 대기
                    await asyncio.sleep(1)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in user {user_id} worker loop: {e}")
                    await asyncio.sleep(5)

        except asyncio.CancelledError:
            logger.info(f"Worker for user {user_id} cancelled")
        except Exception as e:
            logger.error(f"Worker error for user {user_id}: {e}")
        finally:
            logger.info(f"Worker for user {user_id} stopped")

    async def _schedule_signal_generation(self, user_id: int, trading_context):
        """신호 생성 스케줄링"""
        try:
            task = {
                'type': 'signal_generation',
                'user_id': user_id,
                'timestamp': datetime.utcnow(),
                'function': trading_context.process_trading_cycle
            }

            await self.user_task_queues[user_id].put(task)

        except Exception as e:
            logger.error(f"Error scheduling signal generation for user {user_id}: {e}")

    async def _schedule_position_check(self, user_id: int, trading_context):
        """포지션 체크 스케줄링"""
        try:
            if trading_context.open_positions:
                task = {
                    'type': 'position_check',
                    'user_id': user_id,
                    'timestamp': datetime.utcnow(),
                    'function': trading_context._manage_open_positions
                }

                await self.user_task_queues[user_id].put(task)

        except Exception as e:
            logger.error(f"Error scheduling position check for user {user_id}: {e}")

    async def _schedule_risk_check(self, user_id: int, trading_context):
        """리스크 체크 스케줄링"""
        try:
            task = {
                'type': 'risk_check',
                'user_id': user_id,
                'timestamp': datetime.utcnow(),
                'function': lambda: trading_context._check_risk_limits()
            }

            await self.user_task_queues[user_id].put(task)

        except Exception as e:
            logger.error(f"Error scheduling risk check for user {user_id}: {e}")

    async def _process_user_queue(self, user_id: int, trading_context):
        """사용자 큐 처리"""
        try:
            queue = self.user_task_queues[user_id]

            # 큐에서 작업 하나씩 처리 (논블로킹)
            try:
                task = queue.get_nowait()
                await self._execute_task(task, trading_context)
                queue.task_done()
            except asyncio.QueueEmpty:
                pass

        except Exception as e:
            logger.error(f"Error processing queue for user {user_id}: {e}")

    async def _execute_task(self, task: Dict, trading_context):
        """작업 실행"""
        try:
            task_type = task['type']
            function = task['function']

            # 작업 실행 시간 측정
            start_time = datetime.utcnow()

            if asyncio.iscoroutinefunction(function):
                await function()
            else:
                function()

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            # 실행 시간이 너무 길면 경고
            if execution_time > 5.0:
                logger.warning(f"Task {task_type} for user {task['user_id']} took {execution_time:.2f}s")

        except Exception as e:
            logger.error(f"Error executing task {task.get('type', 'unknown')}: {e}")

    async def schedule_custom_task(self, user_id: int, task_type: str,
                                 function: Callable, delay: int = 0):
        """커스텀 작업 스케줄링"""
        try:
            if delay > 0:
                await asyncio.sleep(delay)

            task = {
                'type': task_type,
                'user_id': user_id,
                'timestamp': datetime.utcnow(),
                'function': function
            }

            await self.user_task_queues[user_id].put(task)

        except Exception as e:
            logger.error(f"Error scheduling custom task for user {user_id}: {e}")

    def get_queue_status(self, user_id: int) -> Dict[str, Any]:
        """사용자 큐 상태 조회"""
        try:
            queue = self.user_task_queues.get(user_id)
            worker = self.user_workers.get(user_id)

            return {
                'user_id': user_id,
                'queue_size': queue.qsize() if queue else 0,
                'worker_active': worker is not None and not worker.done(),
                'worker_status': 'running' if (worker and not worker.done()) else 'stopped'
            }

        except Exception as e:
            logger.error(f"Error getting queue status for user {user_id}: {e}")
            return {'user_id': user_id, 'error': str(e)}

    def get_scheduler_status(self) -> Dict[str, Any]:
        """스케줄러 전체 상태 조회"""
        try:
            active_workers = sum(1 for worker in self.user_workers.values() if not worker.done())
            total_queue_size = sum(queue.qsize() for queue in self.user_task_queues.values())

            user_statuses = {}
            for user_id in self.user_workers.keys():
                user_statuses[user_id] = self.get_queue_status(user_id)

            return {
                'is_running': self.is_running,
                'total_users': len(self.user_workers),
                'active_workers': active_workers,
                'total_queue_size': total_queue_size,
                'intervals': self.default_intervals,
                'user_statuses': user_statuses
            }

        except Exception as e:
            logger.error(f"Error getting scheduler status: {e}")
            return {'error': str(e)}

    def update_intervals(self, new_intervals: Dict[str, int]):
        """스케줄링 간격 업데이트"""
        try:
            for key, value in new_intervals.items():
                if key in self.default_intervals and value > 0:
                    self.default_intervals[key] = value

            logger.info(f"Scheduler intervals updated: {self.default_intervals}")

        except Exception as e:
            logger.error(f"Error updating intervals: {e}")

    async def emergency_stop_user(self, user_id: int):
        """사용자 긴급 정지"""
        try:
            logger.warning(f"Emergency stop requested for user {user_id}")

            # 워커 즉시 중지
            if user_id in self.user_workers:
                worker = self.user_workers[user_id]
                worker.cancel()

            # 큐 비우기
            if user_id in self.user_task_queues:
                queue = self.user_task_queues[user_id]
                while not queue.empty():
                    try:
                        queue.get_nowait()
                        queue.task_done()
                    except asyncio.QueueEmpty:
                        break

            logger.info(f"Emergency stop completed for user {user_id}")

        except Exception as e:
            logger.error(f"Error in emergency stop for user {user_id}: {e}")

    def get_user_task_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """사용자 작업 히스토리 조회 (실제 구현 시 로깅 시스템과 연동)"""
        # 실제 구현에서는 로그 파일이나 데이터베이스에서 조회
        return []

class TaskPriority:
    """작업 우선순위 정의"""
    EMERGENCY = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3

class ScheduledTask:
    """스케줄된 작업 클래스"""

    def __init__(self, task_id: str, user_id: int, task_type: str,
                 function: Callable, priority: int = TaskPriority.NORMAL,
                 schedule_time: Optional[datetime] = None):
        self.task_id = task_id
        self.user_id = user_id
        self.task_type = task_type
        self.function = function
        self.priority = priority
        self.schedule_time = schedule_time or datetime.utcnow()
        self.created_at = datetime.utcnow()
        self.executed_at: Optional[datetime] = None
        self.status = 'pending'  # pending, executing, completed, failed

    def to_dict(self) -> Dict[str, Any]:
        """작업 정보를 딕셔너리로 변환"""
        return {
            'task_id': self.task_id,
            'user_id': self.user_id,
            'task_type': self.task_type,
            'priority': self.priority,
            'schedule_time': self.schedule_time.isoformat(),
            'created_at': self.created_at.isoformat(),
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'status': self.status
        }