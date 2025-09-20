"""
Advanced scheduling system for cryptocurrency data collection.
Provides intelligent scheduling with market awareness, resource monitoring, and failure recovery.
"""

import schedule
import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
import psutil
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum

from data.collector import RealTimeDataCollector

# Set up logging
logger = logging.getLogger(__name__)


class ScheduleStatus(Enum):
    """Enumeration for schedule execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ScheduleExecution:
    """Data class to track schedule execution details."""
    job_name: str
    scheduled_time: datetime
    actual_start_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None
    status: ScheduleStatus = ScheduleStatus.PENDING
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    resource_usage: Optional[Dict[str, float]] = None


class MarketHours:
    """Utility class to handle market hours and trading sessions."""

    @staticmethod
    def is_market_open() -> bool:
        """
        Check if cryptocurrency markets are considered 'open'.
        Crypto markets are 24/7, but we might want to reduce collection during low-activity periods.

        Returns:
            bool: True if market is considered active
        """
        # Crypto markets are 24/7, but we can define low-activity periods
        now = datetime.now()

        # Consider market less active during weekend nights (UTC)
        if now.weekday() == 6:  # Sunday
            if 22 <= now.hour or now.hour <= 6:  # Sunday 22:00 - Monday 06:00 UTC
                return False

        return True

    @staticmethod
    def get_next_market_open() -> datetime:
        """Get the next time when market is considered 'open'."""
        now = datetime.now()

        if MarketHours.is_market_open():
            return now

        # If it's weekend night, return Monday 6 AM
        if now.weekday() == 6 and (22 <= now.hour or now.hour <= 6):
            # Calculate next Monday 6 AM
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0:  # It's Sunday
                days_until_monday = 1

            next_monday = now + timedelta(days=days_until_monday)
            return next_monday.replace(hour=6, minute=0, second=0, microsecond=0)

        return now


class ResourceMonitor:
    """Monitor system resources and determine if collection should proceed."""

    def __init__(self, max_cpu_percent: float = 80.0, max_memory_percent: float = 85.0):
        self.max_cpu_percent = max_cpu_percent
        self.max_memory_percent = max_memory_percent

    def check_resources(self) -> Dict[str, Any]:
        """
        Check current system resource usage.

        Returns:
            Dict[str, Any]: Resource usage information and recommendations
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            resources = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_mb': memory.available / (1024 * 1024),
                'disk_free_gb': disk.free / (1024 * 1024 * 1024),
                'timestamp': datetime.now().isoformat()
            }

            # Determine if we should proceed with collection
            resources['should_collect'] = (
                cpu_percent < self.max_cpu_percent and
                memory.percent < self.max_memory_percent and
                disk.free > 1024 * 1024 * 1024  # At least 1GB free
            )

            resources['warnings'] = []
            if cpu_percent >= self.max_cpu_percent:
                resources['warnings'].append(f"High CPU usage: {cpu_percent:.1f}%")

            if memory.percent >= self.max_memory_percent:
                resources['warnings'].append(f"High memory usage: {memory.percent:.1f}%")

            if disk.free < 1024 * 1024 * 1024:
                resources['warnings'].append(f"Low disk space: {disk.free / (1024**3):.1f}GB")

            return resources

        except Exception as e:
            logger.error(f"Failed to check system resources: {e}")
            return {
                'should_collect': True,  # Default to allowing collection
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


class DataCollectionScheduler:
    """
    Advanced scheduling system for cryptocurrency data collection.

    Features:
    - Market-aware scheduling
    - Resource monitoring and throttling
    - Failure recovery and retry logic
    - Dynamic schedule adjustment
    - Comprehensive execution tracking
    """

    def __init__(self, data_collector: RealTimeDataCollector = None, config: Dict[str, Any] = None,
                 collector: RealTimeDataCollector = None, max_workers: int = 3):
        """
        Initialize the data collection scheduler.

        Args:
            data_collector (RealTimeDataCollector): Data collector instance (preferred parameter name)
            config (Dict[str, Any]): Configuration dictionary (optional)
            collector (RealTimeDataCollector): Data collector instance (legacy parameter name)
            max_workers (int): Maximum concurrent collection threads
        """
        # Support both parameter names for backward compatibility
        if data_collector is not None:
            self.collector = data_collector
        elif collector is not None:
            self.collector = collector
        else:
            raise ValueError("Either data_collector or collector parameter must be provided")

        self.config = config or {}
        self.max_workers = max_workers

        # Scheduling state
        self.is_running = False
        self.scheduler_thread = None
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # Monitoring and tracking
        self.resource_monitor = ResourceMonitor()
        self.execution_history: List[ScheduleExecution] = []
        self.consecutive_failures = {}  # Track failures by job type
        self.schedule_adjustments = {}  # Track dynamic adjustments

        # Configuration
        self.max_history_entries = 1000
        self.max_consecutive_failures = 3
        self.failure_backoff_multiplier = 2.0

        # Market awareness
        self.respect_market_hours = False  # Set to True to reduce weekend collection
        self.volatility_multiplier = 1.0  # Adjust frequency based on market volatility

        logger.info("DataCollectionScheduler initialized")

    def schedule_ohlcv_collection(self):
        """Schedule OHLCV data collection for different timeframes."""

        # 1-minute data collection
        schedule.every(1).minutes.do(
            self._schedule_job,
            job_name="ohlcv_1m",
            job_func=self._collect_ohlcv_data,
            timeframes=["1m"]
        ).tag("ohlcv", "high_frequency")

        # 5-minute data collection
        schedule.every(5).minutes.do(
            self._schedule_job,
            job_name="ohlcv_5m",
            job_func=self._collect_ohlcv_data,
            timeframes=["5m"]
        ).tag("ohlcv", "medium_frequency")

        # 15-minute data collection
        schedule.every(15).minutes.do(
            self._schedule_job,
            job_name="ohlcv_15m",
            job_func=self._collect_ohlcv_data,
            timeframes=["15m"]
        ).tag("ohlcv", "low_frequency")

        # 1-hour data collection (for longer-term analysis)
        schedule.every().hour.do(
            self._schedule_job,
            job_name="ohlcv_1h",
            job_func=self._collect_ohlcv_data,
            timeframes=["1h"]
        ).tag("ohlcv", "hourly")

        logger.info("OHLCV collection schedules registered")

    def schedule_realtime_collection(self):
        """Schedule real-time price data collection."""

        # High-frequency price updates
        schedule.every(30).seconds.do(
            self._schedule_job,
            job_name="realtime_prices",
            job_func=self._collect_realtime_prices
        ).tag("realtime", "high_frequency")

        # Market data summary every 5 minutes
        schedule.every(5).minutes.do(
            self._schedule_job,
            job_name="market_summary",
            job_func=self._collect_market_summary
        ).tag("realtime", "summary")

        logger.info("Real-time collection schedules registered")

    def schedule_maintenance(self):
        """Schedule maintenance and cleanup tasks."""

        # Daily cleanup at midnight
        schedule.every().day.at("00:00").do(
            self._schedule_job,
            job_name="daily_cleanup",
            job_func=self._run_daily_cleanup
        ).tag("maintenance", "daily")

        # Database optimization weekly on Sunday
        schedule.every().sunday.at("02:00").do(
            self._schedule_job,
            job_name="database_optimization",
            job_func=self._optimize_database
        ).tag("maintenance", "weekly")

        # Gap filling every hour
        schedule.every().hour.at(":30").do(
            self._schedule_job,
            job_name="gap_filling",
            job_func=self._fill_data_gaps
        ).tag("maintenance", "gap_filling")

        # Resource monitoring every 10 minutes
        schedule.every(10).minutes.do(
            self._schedule_job,
            job_name="resource_check",
            job_func=self._check_resources
        ).tag("monitoring", "resources")

        logger.info("Maintenance schedules registered")

    def start_scheduler(self):
        """Start the scheduler with all configured schedules."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        # Register all schedules
        self.schedule_ohlcv_collection()
        self.schedule_realtime_collection()
        self.schedule_maintenance()

        # Start scheduler thread
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()

        logger.info("Data collection scheduler started with all schedules")
        self._log_schedule_summary()

    def stop_scheduler(self):
        """Stop the scheduler and cleanup resources."""
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return

        logger.info("Stopping data collection scheduler...")

        self.is_running = False

        # Wait for scheduler thread to finish
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=10)

        # Shutdown executor
        self.executor.shutdown(wait=True)

        # Clear all schedules
        schedule.clear()

        logger.info("Data collection scheduler stopped")

    def get_next_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get information about upcoming scheduled runs.

        Args:
            limit (int): Maximum number of upcoming runs to return

        Returns:
            List[Dict[str, Any]]: List of upcoming runs with details
        """
        upcoming_runs = []

        for job in schedule.jobs[:limit]:
            next_run = job.next_run
            if next_run:
                run_info = {
                    'job_name': getattr(job.job_func, '__name__', 'unknown'),
                    'tags': list(job.tags) if job.tags else [],
                    'next_run': next_run.isoformat(),
                    'time_until_run': str(next_run - datetime.now()),
                    'interval': str(job.interval),
                    'unit': job.unit
                }
                upcoming_runs.append(run_info)

        # Sort by next run time
        upcoming_runs.sort(key=lambda x: x['next_run'])

        return upcoming_runs

    def get_scheduler_status(self) -> Dict[str, Any]:
        """
        Get comprehensive scheduler status information.

        Returns:
            Dict[str, Any]: Scheduler status and statistics
        """
        status = {
            'is_running': self.is_running,
            'total_jobs': len(schedule.jobs),
            'execution_history_count': len(self.execution_history),
            'resource_status': self.resource_monitor.check_resources(),
            'consecutive_failures': self.consecutive_failures.copy(),
            'schedule_adjustments': self.schedule_adjustments.copy(),
            'market_hours': {
                'is_open': MarketHours.is_market_open(),
                'next_open': MarketHours.get_next_market_open().isoformat(),
                'respect_market_hours': self.respect_market_hours
            },
            'performance_metrics': self._calculate_performance_metrics()
        }

        # Add recent execution summary
        if self.execution_history:
            recent_executions = self.execution_history[-10:]
            status['recent_executions'] = [
                {
                    'job_name': exec.job_name,
                    'status': exec.status.value,
                    'duration_seconds': exec.duration_seconds,
                    'scheduled_time': exec.scheduled_time.isoformat(),
                    'error_message': exec.error_message
                }
                for exec in recent_executions
            ]

        return status

    def adjust_schedule_frequency(self, job_tag: str, multiplier: float):
        """
        Dynamically adjust schedule frequency based on market conditions.

        Args:
            job_tag (str): Tag of jobs to adjust
            multiplier (float): Frequency multiplier (0.5 = half frequency, 2.0 = double)
        """
        if multiplier <= 0:
            logger.error("Schedule multiplier must be positive")
            return

        self.schedule_adjustments[job_tag] = {
            'multiplier': multiplier,
            'applied_at': datetime.now().isoformat(),
            'reason': f"Dynamic adjustment to {multiplier}x frequency"
        }

        logger.info(f"Adjusted schedule frequency for '{job_tag}' jobs by {multiplier}x")

    def _scheduler_loop(self):
        """Main scheduler loop running in separate thread."""
        logger.info("Scheduler loop started")

        while self.is_running:
            try:
                # Check if we should run based on market hours
                if self.respect_market_hours and not MarketHours.is_market_open():
                    logger.debug("Market is closed, skipping scheduled runs")
                    time.sleep(60)  # Check again in 1 minute
                    continue

                # Run pending jobs
                schedule.run_pending()

                # Cleanup old execution history
                self._cleanup_execution_history()

                # Sleep briefly to prevent busy waiting
                time.sleep(1)

            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                time.sleep(10)  # Wait before retrying

        logger.info("Scheduler loop terminated")

    def _schedule_job(self, job_name: str, job_func: Callable, **kwargs):
        """
        Wrapper to schedule and track job execution.

        Args:
            job_name (str): Name of the job for tracking
            job_func (Callable): Function to execute
            **kwargs: Additional arguments for the job function
        """
        execution = ScheduleExecution(
            job_name=job_name,
            scheduled_time=datetime.now()
        )

        # Check if we should skip due to consecutive failures
        if self._should_skip_job(job_name):
            execution.status = ScheduleStatus.SKIPPED
            execution.error_message = "Skipped due to consecutive failures"
            self._record_execution(execution)
            return

        # Check system resources
        resources = self.resource_monitor.check_resources()
        if not resources.get('should_collect', True):
            execution.status = ScheduleStatus.SKIPPED
            execution.error_message = f"Skipped due to resource constraints: {resources.get('warnings', [])}"
            self._record_execution(execution)
            return

        # Submit job to thread pool
        future = self.executor.submit(self._execute_job, execution, job_func, **kwargs)

        # Don't block the scheduler - job will complete asynchronously
        logger.debug(f"Scheduled job '{job_name}' for execution")

    def _execute_job(self, execution: ScheduleExecution, job_func: Callable, **kwargs):
        """
        Execute a scheduled job with full tracking.

        Args:
            execution (ScheduleExecution): Execution tracking object
            job_func (Callable): Function to execute
            **kwargs: Arguments for the function
        """
        execution.actual_start_time = datetime.now()
        execution.status = ScheduleStatus.RUNNING

        try:
            # Record initial resource usage
            execution.resource_usage = self.resource_monitor.check_resources()

            # Execute the job
            result = job_func(**kwargs)

            # Job completed successfully
            execution.completion_time = datetime.now()
            execution.status = ScheduleStatus.COMPLETED
            execution.duration_seconds = (
                execution.completion_time - execution.actual_start_time
            ).total_seconds()

            # Reset failure counter on success
            self.consecutive_failures[execution.job_name] = 0

            logger.info(f"Job '{execution.job_name}' completed successfully in {execution.duration_seconds:.2f}s")

        except Exception as e:
            execution.completion_time = datetime.now()
            execution.status = ScheduleStatus.FAILED
            execution.error_message = str(e)
            execution.duration_seconds = (
                execution.completion_time - execution.actual_start_time
            ).total_seconds()

            # Track consecutive failures
            self.consecutive_failures[execution.job_name] = (
                self.consecutive_failures.get(execution.job_name, 0) + 1
            )

            logger.error(f"Job '{execution.job_name}' failed after {execution.duration_seconds:.2f}s: {e}")

        finally:
            self._record_execution(execution)

    def _collect_ohlcv_data(self, timeframes: List[str]):
        """Collect OHLCV data for specified timeframes."""
        results = []

        for timeframe in timeframes:
            for symbol in self.collector.symbols:
                try:
                    result = self.collector.collect_ohlcv_data(symbol, timeframe)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to collect {timeframe} data for {symbol}: {e}")
                    results.append({
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'success': False,
                        'error': str(e)
                    })

        return results

    def _collect_realtime_prices(self):
        """Collect real-time price data."""
        return self.collector.collect_realtime_prices()

    def _collect_market_summary(self):
        """Collect market summary data."""
        # This could include additional market data like order book snapshots,
        # trading volume analysis, etc.
        try:
            summary_data = self.collector.market_data_collector.get_multiple_symbols_data(
                self.collector.symbols, "ticker"
            )

            # Could store market summary in database
            logger.info(f"Market summary collected: {summary_data['success_count']} symbols")
            return summary_data

        except Exception as e:
            logger.error(f"Failed to collect market summary: {e}")
            raise

    def _run_daily_cleanup(self):
        """Run daily maintenance and cleanup."""
        logger.info("Starting daily cleanup...")

        try:
            # Clean old data (keep 30 days)
            cleanup_results = self.collector.database_manager.cleanup_old_data(days=30)

            # Clean execution history
            self._cleanup_execution_history(force=True)

            # Reset failure counters
            self.consecutive_failures.clear()

            logger.info(f"Daily cleanup completed: {cleanup_results}")
            return cleanup_results

        except Exception as e:
            logger.error(f"Daily cleanup failed: {e}")
            raise

    def _optimize_database(self):
        """Run database optimization."""
        logger.info("Starting database optimization...")

        try:
            from data.database import optimize_database
            results = optimize_database(self.collector.database_manager)

            logger.info(f"Database optimization completed: saved {results.get('space_saved_mb', 0)} MB")
            return results

        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            raise

    def _fill_data_gaps(self):
        """Fill gaps in collected data."""
        logger.info("Starting gap filling...")

        try:
            results = self.collector.check_and_fill_gaps()

            if results['gaps_filled'] > 0:
                logger.info(f"Gap filling completed: {results['gaps_filled']} gaps filled")
            else:
                logger.debug("No data gaps found")

            return results

        except Exception as e:
            logger.error(f"Gap filling failed: {e}")
            raise

    def _check_resources(self):
        """Check and log system resource usage."""
        resources = self.resource_monitor.check_resources()

        if resources.get('warnings'):
            logger.warning(f"Resource warnings: {', '.join(resources['warnings'])}")
        else:
            logger.debug(f"Resource check: CPU {resources['cpu_percent']:.1f}%, "
                        f"Memory {resources['memory_percent']:.1f}%")

        return resources

    def _should_skip_job(self, job_name: str) -> bool:
        """Determine if a job should be skipped due to consecutive failures."""
        failures = self.consecutive_failures.get(job_name, 0)
        return failures >= self.max_consecutive_failures

    def _record_execution(self, execution: ScheduleExecution):
        """Record job execution in history."""
        self.execution_history.append(execution)

        # Limit history size
        if len(self.execution_history) > self.max_history_entries:
            self.execution_history = self.execution_history[-self.max_history_entries:]

    def _cleanup_execution_history(self, force: bool = False):
        """Clean up old execution history entries."""
        if force or len(self.execution_history) > self.max_history_entries:
            # Keep only recent entries
            cutoff = len(self.execution_history) - self.max_history_entries
            if cutoff > 0:
                self.execution_history = self.execution_history[cutoff:]
                logger.debug(f"Cleaned up {cutoff} old execution history entries")

    def _calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics from execution history."""
        if not self.execution_history:
            return {}

        # Get recent executions (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        recent_executions = [
            exec for exec in self.execution_history
            if exec.scheduled_time >= cutoff_time
        ]

        if not recent_executions:
            return {}

        total_executions = len(recent_executions)
        successful_executions = len([e for e in recent_executions if e.status == ScheduleStatus.COMPLETED])
        failed_executions = len([e for e in recent_executions if e.status == ScheduleStatus.FAILED])

        # Calculate average duration for successful jobs
        successful_durations = [
            e.duration_seconds for e in recent_executions
            if e.status == ScheduleStatus.COMPLETED and e.duration_seconds > 0
        ]

        avg_duration = sum(successful_durations) / len(successful_durations) if successful_durations else 0

        return {
            'last_24h_executions': total_executions,
            'success_rate_percent': round((successful_executions / total_executions) * 100, 2),
            'failed_executions': failed_executions,
            'average_duration_seconds': round(avg_duration, 2),
            'execution_frequency_per_hour': round(total_executions / 24, 2)
        }

    def _log_schedule_summary(self):
        """Log a summary of all configured schedules."""
        job_summary = {}

        for job in schedule.jobs:
            tags = ', '.join(job.tags) if job.tags else 'untagged'
            job_key = f"{job.interval} {job.unit} ({tags})"
            job_summary[job_key] = job_summary.get(job_key, 0) + 1

        logger.info("Configured schedules:")
        for schedule_desc, count in job_summary.items():
            logger.info(f"  - {schedule_desc}: {count} job(s)")


# Utility functions

def create_and_start_scheduler(data_collector: RealTimeDataCollector = None,
                             collector: RealTimeDataCollector = None,
                             config: Dict[str, Any] = None,
                             respect_market_hours: bool = False) -> DataCollectionScheduler:
    """
    Create and start a data collection scheduler.

    Args:
        data_collector (RealTimeDataCollector): Data collector instance (preferred)
        collector (RealTimeDataCollector): Data collector instance (legacy)
        config (Dict[str, Any]): Configuration dictionary
        respect_market_hours (bool): Whether to respect market hours

    Returns:
        DataCollectionScheduler: Started scheduler instance
    """
    # Support both parameter names
    if data_collector is not None:
        scheduler = DataCollectionScheduler(data_collector=data_collector, config=config)
    elif collector is not None:
        scheduler = DataCollectionScheduler(collector=collector, config=config)
    else:
        raise ValueError("Either data_collector or collector parameter must be provided")

    scheduler.respect_market_hours = respect_market_hours
    scheduler.start_scheduler()

    return scheduler


def run_scheduled_collection(config_path: str = 'config/config.json'):
    """
    Run data collection with full scheduling system.

    Args:
        config_path (str): Path to configuration file
    """
    collector = None
    scheduler = None

    try:
        # Initialize collector
        collector = RealTimeDataCollector(config_path)

        # Test connections
        if not collector.market_data_collector.test_connection():
            logger.error("Market data connection test failed")
            return False

        # Create and start scheduler
        scheduler = create_and_start_scheduler(data_collector=collector)

        logger.info("Scheduled data collection started. Press Ctrl+C to stop.")

        # Keep main thread alive
        while scheduler.is_running:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Scheduled collection failed: {e}")
    finally:
        if scheduler:
            scheduler.stop_scheduler()
        if collector:
            collector.cleanup()

    return True


if __name__ == "__main__":
    # Set up logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )

    # Run scheduled collection
    success = run_scheduled_collection()
    exit(0 if success else 1)