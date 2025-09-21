#!/usr/bin/env python3
"""
24시간 무인 AI 트레이딩 엔진
Autonomous Trading Engine for 24/7 Operation

Features:
- 5분마다 AI 신호 생성 및 체크
- 자동 주문 실행 및 포지션 관리
- 네트워크 복원력 및 에러 복구
- 안전 장치 및 리스크 관리
- 종합 로깅 및 성과 분석
"""

import os
import sys
import time
import json
import csv
import threading
import schedule
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
from pathlib import Path

# Import trading components
try:
    from ai_live_trading_system import AILiveTradingSystem, TradingMode, SignalType
    from binance_testnet_connector import BinanceTestnetConnector
    from ai_trading_signals_coingecko import CoinGeckoConnector
except ImportError as e:
    print(f"[ERROR] Required components not found: {e}")
    sys.exit(1)

@dataclass
class SystemStatus:
    """시스템 상태 정보"""
    start_time: datetime
    uptime_hours: float
    total_trades: int
    successful_trades: int
    failed_trades: int
    total_pnl: float
    daily_pnl: float
    consecutive_losses: int
    api_errors: int
    network_errors: int
    last_signal_time: Optional[datetime]
    current_positions: int
    trading_enabled: bool
    emergency_stop: bool

@dataclass
class PerformanceMetrics:
    """성과 지표"""
    timestamp: datetime
    total_pnl: float
    daily_pnl: float
    hourly_pnl: float
    total_trades: int
    win_rate: float
    avg_profit: float
    avg_loss: float
    max_drawdown: float
    current_positions: int
    trading_volume: float

class AutonomousTradingEngine:
    """24시간 무인 트레이딩 엔진"""

    def __init__(self, config_file: str = 'autonomous_config.json'):
        """Initialize autonomous trading engine"""
        self.config_file = config_file
        self.config = self.load_config()

        # Initialize components
        self.trading_system = AILiveTradingSystem(TradingMode.DEMO)
        self.binance = BinanceTestnetConnector()
        self.coingecko = CoinGeckoConnector()

        # System state
        self.start_time = datetime.now()
        self.running = False
        self.pause_until = None
        self.system_status = SystemStatus(
            start_time=self.start_time,
            uptime_hours=0,
            total_trades=0,
            successful_trades=0,
            failed_trades=0,
            total_pnl=0.0,
            daily_pnl=0.0,
            consecutive_losses=0,
            api_errors=0,
            network_errors=0,
            last_signal_time=None,
            current_positions=0,
            trading_enabled=True,
            emergency_stop=False
        )

        # Initialize logging
        self.setup_logging()

        # Initialize data storage
        self.setup_data_storage()

        # Performance tracking
        self.performance_history: List[PerformanceMetrics] = []

        self.logger.info("Autonomous Trading Engine initialized")

    def load_config(self) -> Dict[str, Any]:
        """설정 파일 로드"""
        default_config = {
            "trading": {
                "symbols": ["BTCUSDT", "ETHUSDT"],
                "max_daily_loss": 100.0,
                "max_consecutive_losses": 3,
                "position_size_percent": 2.0,
                "trading_hours": {
                    "enabled": True,
                    "start_hour": 0,
                    "end_hour": 24
                },
                "weekend_trading": False
            },
            "signals": {
                "generation_interval_minutes": 5,
                "min_confidence": 0.6,
                "timeout_seconds": 30
            },
            "safety": {
                "pause_duration_hours": 1,
                "emergency_stop_loss": 200.0,
                "max_positions": 3,
                "unusual_market_threshold": 0.1
            },
            "monitoring": {
                "api_check_interval_seconds": 60,
                "performance_report_interval_hours": 1,
                "backup_data_sources": True
            },
            "logging": {
                "level": "INFO",
                "max_file_size_mb": 10,
                "backup_count": 5
            }
        }

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                # Merge with defaults
                return {**default_config, **config}
            except Exception as e:
                print(f"[WARNING] Failed to load config, using defaults: {e}")

        # Save default config
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2)

        return default_config

    def setup_logging(self):
        """로깅 시스템 설정"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # Main logger
        self.logger = logging.getLogger("AutonomousTrading")
        self.logger.setLevel(getattr(logging, self.config['logging']['level']))

        # File handler with rotation
        log_file = log_dir / f"autonomous_trading_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def setup_data_storage(self):
        """데이터 저장소 설정"""
        self.data_dir = Path("trading_data")
        self.data_dir.mkdir(exist_ok=True)

        # Performance data file
        self.performance_file = self.data_dir / f"performance_{datetime.now().strftime('%Y%m%d')}.csv"

        # Trading log file
        self.trading_log_file = self.data_dir / f"trades_{datetime.now().strftime('%Y%m%d')}.csv"

        # System status file
        self.status_file = self.data_dir / "system_status.json"

    def save_system_status(self):
        """시스템 상태 저장"""
        try:
            status_dict = asdict(self.system_status)
            status_dict['start_time'] = self.system_status.start_time.isoformat()
            if self.system_status.last_signal_time:
                status_dict['last_signal_time'] = self.system_status.last_signal_time.isoformat()

            with open(self.status_file, 'w') as f:
                json.dump(status_dict, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save system status: {e}")

    def check_trading_conditions(self) -> bool:
        """거래 조건 확인"""
        try:
            current_time = datetime.now()

            # Check if system is paused
            if self.pause_until and current_time < self.pause_until:
                return False

            # Check emergency stop
            if self.system_status.emergency_stop:
                return False

            # Check trading hours
            if self.config['trading']['trading_hours']['enabled']:
                start_hour = self.config['trading']['trading_hours']['start_hour']
                end_hour = self.config['trading']['trading_hours']['end_hour']
                current_hour = current_time.hour

                if not (start_hour <= current_hour < end_hour):
                    return False

            # Check weekend trading
            if not self.config['trading']['weekend_trading']:
                if current_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
                    return False

            # Check consecutive losses
            max_losses = self.config['trading']['max_consecutive_losses']
            if self.system_status.consecutive_losses >= max_losses:
                self.logger.warning(f"Max consecutive losses reached: {self.system_status.consecutive_losses}")
                self.pause_trading(hours=self.config['safety']['pause_duration_hours'])
                return False

            # Check daily loss limit
            max_daily_loss = self.config['trading']['max_daily_loss']
            if self.system_status.daily_pnl <= -max_daily_loss:
                self.logger.warning(f"Daily loss limit reached: ${self.system_status.daily_pnl:.2f}")
                self.pause_trading(hours=24)  # Pause until next day
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error checking trading conditions: {e}")
            return False

    def pause_trading(self, hours: float):
        """거래 일시 중단"""
        self.pause_until = datetime.now() + timedelta(hours=hours)
        self.logger.info(f"Trading paused until {self.pause_until}")

    def check_api_connectivity(self) -> bool:
        """API 연결 상태 확인"""
        try:
            # Test Binance connection
            binance_result = self.binance.test_connection()
            if not binance_result:
                self.system_status.api_errors += 1
                return False

            # Test CoinGecko connection
            test_data = self.coingecko.get_ohlc_data('bitcoin', 1)
            if test_data is None:
                self.system_status.api_errors += 1
                return False

            return True

        except Exception as e:
            self.logger.error(f"API connectivity check failed: {e}")
            self.system_status.network_errors += 1
            return False

    def generate_and_process_signals(self):
        """신호 생성 및 처리"""
        try:
            if not self.check_trading_conditions():
                return

            symbols = self.config['trading']['symbols']

            for symbol in symbols:
                self.logger.info(f"Generating signal for {symbol}")

                try:
                    signal = self.trading_system.generate_trading_signal(symbol)

                    if signal and signal.signal != SignalType.HOLD:
                        self.system_status.last_signal_time = datetime.now()

                        if signal.confidence >= self.config['signals']['min_confidence']:
                            self.logger.info(f"Signal: {signal.signal.value} {symbol} (confidence: {signal.confidence:.2%})")

                            # Execute trade
                            success = self.execute_trade_from_signal(signal)
                            if success:
                                self.system_status.successful_trades += 1
                                self.system_status.total_trades += 1
                            else:
                                self.system_status.failed_trades += 1
                                self.system_status.total_trades += 1
                        else:
                            self.logger.info(f"Signal confidence too low: {signal.confidence:.2%}")

                except Exception as e:
                    self.logger.error(f"Signal generation failed for {symbol}: {e}")

        except Exception as e:
            self.logger.error(f"Signal processing error: {e}")

    def execute_trade_from_signal(self, signal) -> bool:
        """신호로부터 거래 실행"""
        try:
            # Check position limits
            current_positions = len(self.trading_system.current_positions)
            max_positions = self.config['safety']['max_positions']

            if current_positions >= max_positions:
                self.logger.warning(f"Max positions reached: {current_positions}")
                return False

            # Execute trade
            success = self.trading_system.execute_trade(signal)

            if success:
                self.log_trade(signal, "EXECUTED")
                self.logger.info(f"Trade executed: {signal.signal.value} {signal.symbol}")
            else:
                self.log_trade(signal, "FAILED")
                self.logger.warning(f"Trade execution failed: {signal.signal.value} {signal.symbol}")

            return success

        except Exception as e:
            self.logger.error(f"Trade execution error: {e}")
            return False

    def log_trade(self, signal, status: str):
        """거래 로그 기록"""
        try:
            trade_data = {
                'timestamp': datetime.now().isoformat(),
                'symbol': signal.symbol,
                'signal': signal.signal.value,
                'confidence': signal.confidence,
                'price': signal.price,
                'status': status
            }

            # CSV 파일에 기록
            file_exists = self.trading_log_file.exists()
            with open(self.trading_log_file, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=trade_data.keys())
                if not file_exists:
                    writer.writeheader()
                writer.writerow(trade_data)

        except Exception as e:
            self.logger.error(f"Failed to log trade: {e}")

    def monitor_positions(self):
        """포지션 모니터링"""
        try:
            if not self.trading_system.current_positions:
                return

            self.trading_system.update_positions()

            # Check for stop loss/take profit triggers
            closed_positions = []

            for symbol, position in self.trading_system.current_positions.items():
                if position.side == 'LONG':
                    if position.current_price <= position.stop_loss:
                        self.logger.info(f"Stop loss triggered for {symbol}: ${position.current_price:.2f}")
                        self.trading_system._close_position(symbol, "STOP_LOSS")
                        closed_positions.append(symbol)
                    elif position.current_price >= position.take_profit:
                        self.logger.info(f"Take profit triggered for {symbol}: ${position.current_price:.2f}")
                        self.trading_system._close_position(symbol, "TAKE_PROFIT")
                        closed_positions.append(symbol)

                else:  # SHORT
                    if position.current_price >= position.stop_loss:
                        self.logger.info(f"Stop loss triggered for {symbol}: ${position.current_price:.2f}")
                        self.trading_system._close_position(symbol, "STOP_LOSS")
                        closed_positions.append(symbol)
                    elif position.current_price <= position.take_profit:
                        self.logger.info(f"Take profit triggered for {symbol}: ${position.current_price:.2f}")
                        self.trading_system._close_position(symbol, "TAKE_PROFIT")
                        closed_positions.append(symbol)

            # Update system status
            self.system_status.current_positions = len(self.trading_system.current_positions)

        except Exception as e:
            self.logger.error(f"Position monitoring error: {e}")

    def generate_performance_report(self):
        """성과 리포트 생성"""
        try:
            current_time = datetime.now()
            status = self.trading_system.get_status_report()

            # Calculate metrics
            total_pnl = status.get('daily_stats', {}).get('pnl', 0)
            hourly_pnl = 0  # Calculate from recent trades

            if self.trading_system.trading_history:
                recent_trades = [
                    trade for trade in self.trading_system.trading_history
                    if trade['timestamp'] > current_time - timedelta(hours=1)
                ]
                hourly_pnl = sum(trade['pnl'] for trade in recent_trades)

            # Calculate win rate
            if self.system_status.total_trades > 0:
                win_rate = self.system_status.successful_trades / self.system_status.total_trades
            else:
                win_rate = 0

            metrics = PerformanceMetrics(
                timestamp=current_time,
                total_pnl=total_pnl,
                daily_pnl=status.get('daily_stats', {}).get('pnl', 0),
                hourly_pnl=hourly_pnl,
                total_trades=self.system_status.total_trades,
                win_rate=win_rate,
                avg_profit=0,  # Calculate from history
                avg_loss=0,    # Calculate from history
                max_drawdown=0,  # Calculate from history
                current_positions=len(self.trading_system.current_positions),
                trading_volume=status.get('daily_stats', {}).get('volume', 0)
            )

            self.performance_history.append(metrics)

            # Save to CSV
            metrics_dict = asdict(metrics)
            metrics_dict['timestamp'] = metrics.timestamp.isoformat()

            file_exists = self.performance_file.exists()
            with open(self.performance_file, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=metrics_dict.keys())
                if not file_exists:
                    writer.writeheader()
                writer.writerow(metrics_dict)

            self.logger.info(f"Performance report: PnL=${total_pnl:.2f}, Trades={self.system_status.total_trades}, Win Rate={win_rate:.1%}")

        except Exception as e:
            self.logger.error(f"Performance report generation failed: {e}")

    def emergency_stop(self):
        """긴급 정지"""
        self.logger.critical("EMERGENCY STOP ACTIVATED")
        self.system_status.emergency_stop = True
        self.trading_system.emergency_stop_trading()

        # Close all positions
        for symbol in list(self.trading_system.current_positions.keys()):
            try:
                self.trading_system._close_position(symbol, "EMERGENCY_STOP")
                self.logger.info(f"Emergency position closure: {symbol}")
            except Exception as e:
                self.logger.error(f"Failed to close position {symbol}: {e}")

    def daily_reset(self):
        """일일 리셋"""
        try:
            self.logger.info("Performing daily reset")

            # Reset daily counters
            self.system_status.daily_pnl = 0.0
            self.system_status.consecutive_losses = 0

            # Generate daily summary
            self.generate_daily_summary()

            # Archive old logs if needed
            self.archive_old_logs()

        except Exception as e:
            self.logger.error(f"Daily reset failed: {e}")

    def generate_daily_summary(self):
        """일일 요약 생성"""
        try:
            current_time = datetime.now()

            summary = {
                'date': current_time.strftime('%Y-%m-%d'),
                'total_trades': self.system_status.total_trades,
                'successful_trades': self.system_status.successful_trades,
                'failed_trades': self.system_status.failed_trades,
                'total_pnl': self.system_status.total_pnl,
                'api_errors': self.system_status.api_errors,
                'network_errors': self.system_status.network_errors,
                'uptime_hours': (current_time - self.start_time).total_seconds() / 3600
            }

            summary_file = self.data_dir / f"daily_summary_{current_time.strftime('%Y%m%d')}.json"
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)

            self.logger.info(f"Daily summary saved: {summary_file}")

        except Exception as e:
            self.logger.error(f"Daily summary generation failed: {e}")

    def archive_old_logs(self):
        """오래된 로그 아카이브"""
        try:
            archive_days = 7
            cutoff_date = datetime.now() - timedelta(days=archive_days)

            for log_file in self.data_dir.glob("*.log"):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    archive_dir = self.data_dir / "archive"
                    archive_dir.mkdir(exist_ok=True)
                    log_file.rename(archive_dir / log_file.name)

        except Exception as e:
            self.logger.error(f"Log archiving failed: {e}")

    def setup_schedule(self):
        """스케줄 설정"""
        # Signal generation every 5 minutes
        schedule.every(self.config['signals']['generation_interval_minutes']).minutes.do(
            self.generate_and_process_signals
        )

        # Position monitoring every minute
        schedule.every(1).minutes.do(self.monitor_positions)

        # API connectivity check
        schedule.every(self.config['monitoring']['api_check_interval_seconds']).seconds.do(
            self.check_api_connectivity
        )

        # Performance report every hour
        schedule.every(self.config['monitoring']['performance_report_interval_hours']).hours.do(
            self.generate_performance_report
        )

        # Daily reset at midnight
        schedule.every().day.at("00:00").do(self.daily_reset)

        # Save system status every 5 minutes
        schedule.every(5).minutes.do(self.save_system_status)

    def run_scheduler(self):
        """스케줄러 실행"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"Scheduler error: {e}")
                time.sleep(5)

    def start(self):
        """시스템 시작"""
        try:
            self.logger.info("Starting Autonomous Trading Engine")

            # Initial system checks
            if not self.check_api_connectivity():
                self.logger.error("Initial API connectivity check failed")
                return False

            self.running = True
            self.system_status.trading_enabled = True

            # Setup scheduler
            self.setup_schedule()

            # Start scheduler in separate thread
            scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
            scheduler_thread.start()

            self.logger.info("Autonomous Trading Engine started successfully")

            # Main loop
            try:
                while self.running:
                    # Update uptime
                    self.system_status.uptime_hours = (
                        datetime.now() - self.start_time
                    ).total_seconds() / 3600

                    # Check for emergency conditions
                    if self.system_status.total_pnl <= -self.config['safety']['emergency_stop_loss']:
                        self.emergency_stop()
                        break

                    time.sleep(10)  # Main loop interval

            except KeyboardInterrupt:
                self.logger.info("Shutdown requested by user")
                self.stop()

        except Exception as e:
            self.logger.critical(f"Critical error in main loop: {e}")
            self.emergency_stop()

    def stop(self):
        """시스템 정지"""
        self.logger.info("Stopping Autonomous Trading Engine")
        self.running = False
        self.system_status.trading_enabled = False

        # Generate final report
        self.generate_performance_report()
        self.generate_daily_summary()
        self.save_system_status()

        self.logger.info("Autonomous Trading Engine stopped")

    def get_status(self) -> Dict[str, Any]:
        """현재 상태 반환"""
        return {
            'system_status': asdict(self.system_status),
            'current_time': datetime.now().isoformat(),
            'config': self.config,
            'pause_until': self.pause_until.isoformat() if self.pause_until else None
        }

def main():
    """메인 실행 함수"""
    engine = AutonomousTradingEngine()

    try:
        engine.start()
    except Exception as e:
        print(f"[CRITICAL] Engine startup failed: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())