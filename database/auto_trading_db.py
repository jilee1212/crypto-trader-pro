"""
🗄️ AutoTradingDB - 자동매매 데이터베이스 관리자

자동매매 시스템 전용 데이터베이스 관리
- 설정 저장/로드
- 거래 로그 기록
- 성과 데이터 추적
- 시스템 상태 관리
"""

import sqlite3
import threading
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging
from contextlib import contextmanager
from pathlib import Path

from .models import AutoTradingConfig, AutoTradingLog, AISignalLog, PerformanceData

class AutoTradingDB:
    """
    🗄️ 자동매매 데이터베이스 관리자

    기능:
    - 자동매매 설정 관리
    - 거래 로그 저장
    - AI 신호 기록
    - 성과 데이터 추적
    """

    def __init__(self, db_path: str = "data/auto_trading.db"):
        """데이터베이스 초기화"""
        self.logger = logging.getLogger(__name__)
        self.db_path = db_path
        self._lock = threading.Lock()

        # 데이터베이스 디렉토리 생성
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # 테이블 생성
        self._create_tables()

        self.logger.info("AutoTradingDB 초기화 완료")

    @contextmanager
    def get_connection(self):
        """데이터베이스 연결 컨텍스트 매니저"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
        finally:
            if conn:
                conn.close()

    def _create_tables(self):
        """테이블 생성"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 자동매매 설정 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS auto_trading_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER DEFAULT 1,
                    is_enabled BOOLEAN DEFAULT FALSE,
                    trading_mode TEXT DEFAULT 'CONSERVATIVE',
                    max_daily_loss_pct REAL DEFAULT 3.0,
                    max_positions INTEGER DEFAULT 5,
                    trading_interval INTEGER DEFAULT 300,
                    symbols TEXT,  -- JSON array
                    risk_config TEXT,  -- JSON object
                    notification_config TEXT,  -- JSON object
                    custom_settings TEXT,  -- JSON object
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 자동매매 로그 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS auto_trading_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER DEFAULT 1,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    log_level TEXT NOT NULL,  -- INFO, WARNING, ERROR, CRITICAL
                    component TEXT NOT NULL,  -- ENGINE, MONITOR, EXECUTOR, etc.
                    message TEXT NOT NULL,
                    data TEXT,  -- JSON data
                    error_traceback TEXT
                )
            """)

            # AI 신호 로그 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_signals_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER DEFAULT 1,
                    symbol TEXT NOT NULL,
                    signal_type TEXT NOT NULL,  -- BUY, SELL, HOLD
                    confidence_score INTEGER NOT NULL,
                    entry_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    position_size REAL,
                    executed BOOLEAN DEFAULT FALSE,
                    execution_price REAL,
                    execution_quantity REAL,
                    pnl REAL DEFAULT 0.0,
                    signal_data TEXT,  -- JSON data
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    executed_at TIMESTAMP
                )
            """)

            # 성과 데이터 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER DEFAULT 1,
                    date DATE NOT NULL,
                    total_trades INTEGER DEFAULT 0,
                    successful_trades INTEGER DEFAULT 0,
                    total_pnl REAL DEFAULT 0.0,
                    daily_pnl REAL DEFAULT 0.0,
                    total_volume REAL DEFAULT 0.0,
                    max_drawdown REAL DEFAULT 0.0,
                    active_positions INTEGER DEFAULT 0,
                    system_uptime INTEGER DEFAULT 0,  -- seconds
                    error_count INTEGER DEFAULT 0,
                    performance_metrics TEXT,  -- JSON object
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, date)
                )
            """)

            # 시스템 상태 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component TEXT NOT NULL,
                    status TEXT NOT NULL,  -- RUNNING, STOPPED, ERROR
                    last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,  -- JSON object
                    UNIQUE(component)
                )
            """)

            # 인덱스 생성
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_logs_timestamp
                ON auto_trading_logs(timestamp)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_signals_symbol_created
                ON ai_signals_log(symbol, created_at)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_performance_date
                ON performance_data(date)
            """)

            conn.commit()

    # 설정 관리 메서드들
    def save_config(self, config: AutoTradingConfig) -> bool:
        """자동매매 설정 저장"""
        try:
            with self._lock:
                with self.get_connection() as conn:
                    cursor = conn.cursor()

                    cursor.execute("""
                        INSERT OR REPLACE INTO auto_trading_config
                        (user_id, is_enabled, trading_mode, max_daily_loss_pct,
                         max_positions, trading_interval, symbols, risk_config,
                         notification_config, custom_settings, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        config.user_id,
                        config.is_enabled,
                        config.trading_mode,
                        config.max_daily_loss_pct,
                        config.max_positions,
                        config.trading_interval,
                        json.dumps(config.symbols),
                        json.dumps(config.risk_config),
                        json.dumps(config.notification_config),
                        json.dumps(config.custom_settings),
                        datetime.now()
                    ))

                    conn.commit()
                    return True

        except Exception as e:
            self.logger.error(f"설정 저장 실패: {e}")
            return False

    def load_config(self, user_id: int = 1) -> Optional[AutoTradingConfig]:
        """자동매매 설정 로드"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM auto_trading_config
                    WHERE user_id = ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, (user_id,))

                row = cursor.fetchone()
                if row:
                    return AutoTradingConfig(
                        id=row['id'],
                        user_id=row['user_id'],
                        is_enabled=bool(row['is_enabled']),
                        trading_mode=row['trading_mode'],
                        max_daily_loss_pct=row['max_daily_loss_pct'],
                        max_positions=row['max_positions'],
                        trading_interval=row['trading_interval'],
                        symbols=json.loads(row['symbols'] or '[]'),
                        risk_config=json.loads(row['risk_config'] or '{}'),
                        notification_config=json.loads(row['notification_config'] or '{}'),
                        custom_settings=json.loads(row['custom_settings'] or '{}'),
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    )

                return None

        except Exception as e:
            self.logger.error(f"설정 로드 실패: {e}")
            return None

    # 로그 관리 메서드들
    def add_log(self, log: AutoTradingLog) -> bool:
        """로그 추가"""
        try:
            with self._lock:
                with self.get_connection() as conn:
                    cursor = conn.cursor()

                    cursor.execute("""
                        INSERT INTO auto_trading_logs
                        (user_id, log_level, component, message, data, error_traceback)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        log.user_id,
                        log.log_level,
                        log.component,
                        log.message,
                        json.dumps(log.data) if log.data else None,
                        log.error_traceback
                    ))

                    conn.commit()
                    return True

        except Exception as e:
            self.logger.error(f"로그 추가 실패: {e}")
            return False

    def get_logs(self, user_id: int = 1, limit: int = 100,
                 level: str = None, component: str = None) -> List[AutoTradingLog]:
        """로그 조회"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                query = """
                    SELECT * FROM auto_trading_logs
                    WHERE user_id = ?
                """
                params = [user_id]

                if level:
                    query += " AND log_level = ?"
                    params.append(level)

                if component:
                    query += " AND component = ?"
                    params.append(component)

                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                logs = []
                for row in rows:
                    logs.append(AutoTradingLog(
                        id=row['id'],
                        user_id=row['user_id'],
                        timestamp=row['timestamp'],
                        log_level=row['log_level'],
                        component=row['component'],
                        message=row['message'],
                        data=json.loads(row['data']) if row['data'] else None,
                        error_traceback=row['error_traceback']
                    ))

                return logs

        except Exception as e:
            self.logger.error(f"로그 조회 실패: {e}")
            return []

    # AI 신호 관리 메서드들
    def add_signal(self, signal: AISignalLog) -> bool:
        """AI 신호 추가"""
        try:
            with self._lock:
                with self.get_connection() as conn:
                    cursor = conn.cursor()

                    cursor.execute("""
                        INSERT INTO ai_signals_log
                        (user_id, symbol, signal_type, confidence_score, entry_price,
                         stop_loss, take_profit, position_size, signal_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        signal.user_id,
                        signal.symbol,
                        signal.signal_type,
                        signal.confidence_score,
                        signal.entry_price,
                        signal.stop_loss,
                        signal.take_profit,
                        signal.position_size,
                        json.dumps(signal.signal_data) if signal.signal_data else None
                    ))

                    conn.commit()
                    return True

        except Exception as e:
            self.logger.error(f"신호 추가 실패: {e}")
            return False

    def update_signal_execution(self, signal_id: int, execution_price: float,
                               execution_quantity: float) -> bool:
        """신호 실행 정보 업데이트"""
        try:
            with self._lock:
                with self.get_connection() as conn:
                    cursor = conn.cursor()

                    cursor.execute("""
                        UPDATE ai_signals_log
                        SET executed = TRUE, execution_price = ?,
                            execution_quantity = ?, executed_at = ?
                        WHERE id = ?
                    """, (execution_price, execution_quantity, datetime.now(), signal_id))

                    conn.commit()
                    return cursor.rowcount > 0

        except Exception as e:
            self.logger.error(f"신호 실행 업데이트 실패: {e}")
            return False

    # 성과 데이터 관리 메서드들
    def update_performance(self, performance: PerformanceData) -> bool:
        """성과 데이터 업데이트"""
        try:
            with self._lock:
                with self.get_connection() as conn:
                    cursor = conn.cursor()

                    cursor.execute("""
                        INSERT OR REPLACE INTO performance_data
                        (user_id, date, total_trades, successful_trades, total_pnl,
                         daily_pnl, total_volume, max_drawdown, active_positions,
                         system_uptime, error_count, performance_metrics)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        performance.user_id,
                        performance.date,
                        performance.total_trades,
                        performance.successful_trades,
                        performance.total_pnl,
                        performance.daily_pnl,
                        performance.total_volume,
                        performance.max_drawdown,
                        performance.active_positions,
                        performance.system_uptime,
                        performance.error_count,
                        json.dumps(performance.performance_metrics)
                    ))

                    conn.commit()
                    return True

        except Exception as e:
            self.logger.error(f"성과 데이터 업데이트 실패: {e}")
            return False

    def get_performance_history(self, user_id: int = 1,
                               days: int = 30) -> List[PerformanceData]:
        """성과 기록 조회"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                start_date = (datetime.now() - timedelta(days=days)).date()

                cursor.execute("""
                    SELECT * FROM performance_data
                    WHERE user_id = ? AND date >= ?
                    ORDER BY date DESC
                """, (user_id, start_date))

                rows = cursor.fetchall()
                return [PerformanceData(**dict(row)) for row in rows]

        except Exception as e:
            self.logger.error(f"성과 기록 조회 실패: {e}")
            return []

    # 시스템 상태 관리
    def update_system_status(self, component: str, status: str,
                           metadata: Dict[str, Any] = None) -> bool:
        """시스템 상태 업데이트"""
        try:
            with self._lock:
                with self.get_connection() as conn:
                    cursor = conn.cursor()

                    cursor.execute("""
                        INSERT OR REPLACE INTO system_status
                        (component, status, last_heartbeat, metadata)
                        VALUES (?, ?, ?, ?)
                    """, (
                        component,
                        status,
                        datetime.now(),
                        json.dumps(metadata) if metadata else None
                    ))

                    conn.commit()
                    return True

        except Exception as e:
            self.logger.error(f"시스템 상태 업데이트 실패: {e}")
            return False

    def get_system_status(self) -> Dict[str, Dict[str, Any]]:
        """전체 시스템 상태 조회"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM system_status
                    ORDER BY last_heartbeat DESC
                """)

                rows = cursor.fetchall()
                status = {}

                for row in rows:
                    status[row['component']] = {
                        'status': row['status'],
                        'last_heartbeat': row['last_heartbeat'],
                        'metadata': json.loads(row['metadata']) if row['metadata'] else {}
                    }

                return status

        except Exception as e:
            self.logger.error(f"시스템 상태 조회 실패: {e}")
            return {}

    # 유틸리티 메서드들
    def cleanup_old_logs(self, days: int = 30) -> bool:
        """오래된 로그 정리"""
        try:
            with self._lock:
                with self.get_connection() as conn:
                    cursor = conn.cursor()

                    cutoff_date = datetime.now() - timedelta(days=days)

                    cursor.execute("""
                        DELETE FROM auto_trading_logs
                        WHERE timestamp < ?
                    """, (cutoff_date,))

                    deleted_count = cursor.rowcount
                    conn.commit()

                    self.logger.info(f"{deleted_count}개의 오래된 로그 삭제됨")
                    return True

        except Exception as e:
            self.logger.error(f"로그 정리 실패: {e}")
            return False

    def get_database_stats(self) -> Dict[str, Any]:
        """데이터베이스 통계"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                stats = {}

                # 테이블별 레코드 수
                tables = ['auto_trading_config', 'auto_trading_logs',
                         'ai_signals_log', 'performance_data', 'system_status']

                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[f"{table}_count"] = cursor.fetchone()[0]

                # 데이터베이스 크기
                cursor.execute("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()")
                stats['database_size_bytes'] = cursor.fetchone()[0]

                return stats

        except Exception as e:
            self.logger.error(f"데이터베이스 통계 조회 실패: {e}")
            return {}

    def close(self):
        """데이터베이스 연결 종료"""
        # SQLite는 자동으로 연결이 닫히므로 특별한 처리 불필요
        self.logger.info("AutoTradingDB 종료")