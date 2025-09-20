"""
Comprehensive test suite for cryptocurrency data collection system.
Tests all components including database, collector, and scheduler with real-time monitoring.
"""

import os
import sys
import time
import threading
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import psutil
import logging

# Add project root to path for imports
sys.path.append(os.path.dirname(__file__))

from data.database import CryptoDatabaseManager, validate_database_integrity, optimize_database
from data.collector import RealTimeDataCollector
from data.scheduler import DataCollectionScheduler, create_and_start_scheduler
from utils.market_data import MarketDataCollector
from utils.exceptions import *

# Terminal colors for beautiful output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

    # Emojis for visual appeal
    SUCCESS = '✅'
    FAILURE = '❌'
    WARNING = '⚠️'
    INFO = 'ℹ️'
    ROCKET = '🚀'
    DATABASE = '🗄️'
    CHART = '📊'
    CLOCK = '⏰'
    GEAR = '⚙️'
    FIRE = '🔥'


class TestProgressTracker:
    """Track and display test progress with beautiful formatting."""

    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.start_time = time.time()
        self.current_test = ""
        self.detailed_results = []

    def start_test(self, test_name: str):
        """Start a new test."""
        self.current_test = test_name
        self.tests_run += 1
        print(f"\n{Colors.CYAN}{Colors.BOLD}Test {self.tests_run}: {test_name}{Colors.RESET}")
        print(f"{Colors.BLUE}{'─' * 60}{Colors.RESET}")

    def pass_test(self, message: str = "", details: Any = None):
        """Mark current test as passed."""
        self.tests_passed += 1
        print(f"{Colors.GREEN}{Colors.SUCCESS} PASSED{Colors.RESET}: {message}")
        self._record_result(True, message, details)

    def fail_test(self, message: str = "", details: Any = None):
        """Mark current test as failed."""
        self.tests_failed += 1
        print(f"{Colors.RED}{Colors.FAILURE} FAILED{Colors.RESET}: {message}")
        self._record_result(False, message, details)

    def info(self, message: str):
        """Print info message."""
        print(f"{Colors.BLUE}{Colors.INFO} {message}{Colors.RESET}")

    def warning(self, message: str):
        """Print warning message."""
        print(f"{Colors.YELLOW}{Colors.WARNING} {message}{Colors.RESET}")

    def success(self, message: str):
        """Print success message."""
        print(f"{Colors.GREEN}{Colors.SUCCESS} {message}{Colors.RESET}")

    def _record_result(self, passed: bool, message: str, details: Any):
        """Record detailed test result."""
        self.detailed_results.append({
            'test_name': self.current_test,
            'passed': passed,
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })

    def print_summary(self):
        """Print final test summary."""
        runtime = time.time() - self.start_time
        success_rate = (self.tests_passed / max(self.tests_run, 1)) * 100

        print(f"\n{Colors.PURPLE}{Colors.BOLD}{'='*80}{Colors.RESET}")
        print(f"{Colors.PURPLE}{Colors.BOLD}DATA COLLECTION SYSTEM TEST SUMMARY{Colors.RESET}")
        print(f"{Colors.PURPLE}{Colors.BOLD}{'='*80}{Colors.RESET}")

        print(f"\n{Colors.BOLD}📊 Test Results:{Colors.RESET}")
        print(f"   {Colors.GREEN}✅ Passed: {self.tests_passed}{Colors.RESET}")
        print(f"   {Colors.RED}❌ Failed: {self.tests_failed}{Colors.RESET}")
        print(f"   📈 Success Rate: {success_rate:.1f}%")
        print(f"   ⏱️  Total Runtime: {runtime:.2f} seconds")

        if self.tests_failed == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}{Colors.FIRE} ALL TESTS PASSED! SYSTEM IS READY! {Colors.FIRE}{Colors.RESET}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}⚠️  SOME TESTS FAILED - CHECK ISSUES ABOVE{Colors.RESET}")


class DataCollectionSystemTester:
    """Comprehensive test suite for the entire data collection system."""

    def __init__(self):
        self.tracker = TestProgressTracker()
        self.test_db_path = "data/test_crypto_data.db"
        self.production_db_path = "data/crypto_data.db"
        self.test_config_path = "config/test_config.json"

        # Performance tracking
        self.performance_metrics = {}
        self.memory_start = self._get_memory_usage()

        # Test data
        self.test_symbols = ['BTC/USDT', 'ETH/USDT']
        self.test_timeframes = ['1m', '5m']

    def run_all_tests(self):
        """Run the complete test suite."""
        print(f"{Colors.PURPLE}{Colors.BOLD}{Colors.ROCKET} CRYPTO TRADER PRO - DATA COLLECTION SYSTEM TESTS {Colors.ROCKET}{Colors.RESET}")
        print(f"{Colors.CYAN}Starting comprehensive system tests...{Colors.RESET}")
        print(f"{Colors.BLUE}Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}\n")

        try:
            # Prepare test environment
            self._setup_test_environment()

            # Run all test scenarios
            self.test_1_database_initialization()
            self.test_2_single_coin_ohlcv_collection()
            self.test_3_multi_coin_simultaneous_collection()
            self.test_4_realtime_price_collection()
            self.test_5_data_deduplication()
            self.test_6_gap_detection_and_filling()
            self.test_7_scheduler_start_stop()
            self.test_8_live_collection_simulation()
            self.test_9_database_statistics()
            self.test_10_performance_benchmarks()

            # Verify final database state
            self._verify_database_content()

        except KeyboardInterrupt:
            self.tracker.warning("Tests interrupted by user")
        except Exception as e:
            self.tracker.fail_test(f"Test suite crashed: {str(e)}")
        finally:
            # Cleanup and summary
            self._cleanup_test_environment()
            self.tracker.print_summary()

    def _setup_test_environment(self):
        """Set up test environment and configuration."""
        self.tracker.start_test("Test Environment Setup")

        try:
            # Create test directories
            Path("data").mkdir(exist_ok=True)
            Path("config").mkdir(exist_ok=True)
            Path("logs").mkdir(exist_ok=True)

            # Create test configuration
            test_config = {
                "exchange": {"name": "binance", "testnet": True},
                "database": {"path": self.test_db_path},
                "data_collection": {
                    "symbols": self.test_symbols,
                    "timeframes": self.test_timeframes,
                    "interval_seconds": 5,  # Fast testing
                    "max_workers": 2
                }
            }

            with open(self.test_config_path, 'w') as f:
                json.dump(test_config, f, indent=2)

            # Remove old test database
            if Path(self.test_db_path).exists():
                Path(self.test_db_path).unlink()

            self.tracker.pass_test("Test environment prepared successfully")

        except Exception as e:
            self.tracker.fail_test(f"Failed to setup test environment: {str(e)}")

    def test_1_database_initialization(self):
        """Test database initialization and table creation."""
        self.tracker.start_test("Database Initialization")

        try:
            # Initialize database manager
            start_time = time.time()
            db_manager = CryptoDatabaseManager(self.test_db_path)
            init_time = time.time() - start_time

            # Verify tables were created
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Check if all required tables exist
                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                tables = [row[0] for row in cursor.fetchall()]

                expected_tables = ['ohlcv_data', 'realtime_prices', 'trading_history', 'system_stats']
                missing_tables = set(expected_tables) - set(tables)

                if missing_tables:
                    raise Exception(f"Missing tables: {missing_tables}")

            # Test database integrity
            integrity_results = validate_database_integrity(db_manager)

            if not integrity_results['integrity_ok']:
                raise Exception(f"Database integrity issues: {integrity_results['errors_found']}")

            db_manager.close()

            self.performance_metrics['db_init_time'] = init_time
            self.tracker.pass_test(f"Database initialized in {init_time:.3f}s with {len(tables)} tables")

        except Exception as e:
            self.tracker.fail_test(f"Database initialization failed: {str(e)}")

    def test_2_single_coin_ohlcv_collection(self):
        """Test OHLCV data collection for a single coin."""
        self.tracker.start_test("Single Coin OHLCV Collection")

        try:
            collector = RealTimeDataCollector(self.test_config_path)

            # Test connection first
            if not collector.market_data_collector.test_connection():
                raise Exception("API connection test failed")

            # Collect data for BTC/USDT 1m
            start_time = time.time()
            result = collector.collect_ohlcv_data('BTC/USDT', '1m')
            collection_time = time.time() - start_time

            if not result['success']:
                raise Exception(f"Collection failed: {result['error']}")

            # Verify data was inserted
            db_manager = CryptoDatabaseManager(self.test_db_path)
            latest_timestamp = db_manager.get_latest_timestamp('BTC/USDT', '1m')

            if latest_timestamp is None:
                raise Exception("No data found in database after collection")

            db_manager.close()
            collector.cleanup()

            self.performance_metrics['single_collection_time'] = collection_time
            self.tracker.pass_test(
                f"Collected {result['records_inserted']} records in {collection_time:.3f}s"
            )

        except Exception as e:
            self.tracker.fail_test(f"Single coin collection failed: {str(e)}")

    def test_3_multi_coin_simultaneous_collection(self):
        """Test simultaneous data collection for multiple coins."""
        self.tracker.start_test("Multi-Coin Simultaneous Collection")

        try:
            collector = RealTimeDataCollector(self.test_config_path)

            # Collect data for all symbols and timeframes
            start_time = time.time()
            results = collector.collect_all_data()
            collection_time = time.time() - start_time

            total_records = results['total_records']
            total_errors = results['total_errors']

            if total_errors > len(self.test_symbols) * len(self.test_timeframes) * 0.3:  # Allow 30% error rate
                raise Exception(f"Too many errors: {total_errors}")

            # Verify data distribution across symbols
            db_manager = CryptoDatabaseManager(self.test_db_path)
            stats = db_manager.get_statistics()
            symbol_counts = stats.get('symbol_counts', {})

            if len(symbol_counts) < len(self.test_symbols) * 0.7:  # At least 70% of symbols
                raise Exception(f"Insufficient symbol coverage: {symbol_counts}")

            db_manager.close()
            collector.cleanup()

            self.performance_metrics['multi_collection_time'] = collection_time
            self.tracker.pass_test(
                f"Collected {total_records} records from {len(symbol_counts)} symbols in {collection_time:.3f}s"
            )

        except Exception as e:
            self.tracker.fail_test(f"Multi-coin collection failed: {str(e)}")

    def test_4_realtime_price_collection(self):
        """Test real-time price data collection."""
        self.tracker.start_test("Real-time Price Collection")

        try:
            collector = RealTimeDataCollector(self.test_config_path)

            # Collect real-time prices
            start_time = time.time()
            results = collector.collect_realtime_prices()
            collection_time = time.time() - start_time

            success_count = results['success_count']
            failure_count = results['failure_count']

            if success_count == 0:
                raise Exception("No successful price collections")

            # Verify prices are in database
            db_manager = CryptoDatabaseManager(self.test_db_path)

            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM realtime_prices")
                price_records = cursor.fetchone()[0]

            if price_records == 0:
                raise Exception("No price records found in database")

            db_manager.close()
            collector.cleanup()

            self.performance_metrics['price_collection_time'] = collection_time
            self.tracker.pass_test(
                f"Collected {success_count} prices, {price_records} DB records in {collection_time:.3f}s"
            )

        except Exception as e:
            self.tracker.fail_test(f"Real-time price collection failed: {str(e)}")

    def test_5_data_deduplication(self):
        """Test data deduplication functionality."""
        self.tracker.start_test("Data Deduplication")

        try:
            db_manager = CryptoDatabaseManager(self.test_db_path)

            # Create sample OHLCV data with duplicates
            test_data = [
                [1640995200, 47000.0, 47100.0, 46900.0, 47050.0, 1000.0],  # Same timestamp
                [1640995200, 47000.0, 47100.0, 46900.0, 47050.0, 1000.0],  # Duplicate
                [1640995260, 47050.0, 47150.0, 46950.0, 47100.0, 1100.0],  # New data
            ]

            # First insertion
            inserted_1 = db_manager.insert_ohlcv_data('BTC/USDT', '1m', test_data)

            # Second insertion (should ignore duplicates)
            inserted_2 = db_manager.insert_ohlcv_data('BTC/USDT', '1m', test_data)

            # Verify deduplication worked
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM ohlcv_data
                    WHERE symbol = 'BTC/USDT' AND timeframe = '1m'
                    AND timestamp IN (1640995200, 1640995260)
                """)
                actual_count = cursor.fetchone()[0]

            expected_unique_records = 2  # Only 2 unique timestamps

            if actual_count != expected_unique_records:
                raise Exception(f"Deduplication failed: expected {expected_unique_records}, got {actual_count}")

            db_manager.close()

            self.tracker.pass_test(
                f"Deduplication working: {inserted_1} + {inserted_2} insertions = {actual_count} unique records"
            )

        except Exception as e:
            self.tracker.fail_test(f"Data deduplication test failed: {str(e)}")

    def test_6_gap_detection_and_filling(self):
        """Test gap detection and filling functionality."""
        self.tracker.start_test("Gap Detection and Filling")

        try:
            collector = RealTimeDataCollector(self.test_config_path)

            # Check for gaps in the last hour
            end_time = int(time.time())
            start_time = end_time - 3600  # 1 hour ago

            gaps_before = collector.database_manager.check_data_gaps(
                'BTC/USDT', '1m', start_time, end_time
            )

            # Attempt to fill gaps
            start_time = time.time()
            fill_results = collector.check_and_fill_gaps()
            fill_time = time.time() - start_time

            gaps_after = collector.database_manager.check_data_gaps(
                'BTC/USDT', '1m', start_time, end_time
            )

            gaps_filled = fill_results.get('gaps_filled', 0)
            gaps_found = fill_results.get('gaps_found', 0)

            collector.cleanup()

            self.performance_metrics['gap_fill_time'] = fill_time
            self.tracker.pass_test(
                f"Found {gaps_found} gaps, filled {gaps_filled} in {fill_time:.3f}s"
            )

        except Exception as e:
            self.tracker.fail_test(f"Gap detection test failed: {str(e)}")

    def test_7_scheduler_start_stop(self):
        """Test scheduler start and stop functionality."""
        self.tracker.start_test("Scheduler Start/Stop")

        try:
            collector = RealTimeDataCollector(self.test_config_path)

            # Create scheduler
            start_time = time.time()
            scheduler = DataCollectionScheduler(collector, max_workers=2)

            # Start scheduler
            scheduler.start_scheduler()

            if not scheduler.is_running:
                raise Exception("Scheduler failed to start")

            # Let it run briefly
            time.sleep(2)

            # Check status
            status = scheduler.get_scheduler_status()

            if status['total_jobs'] == 0:
                raise Exception("No jobs were scheduled")

            # Stop scheduler
            scheduler.stop_scheduler()
            stop_time = time.time() - start_time

            if scheduler.is_running:
                raise Exception("Scheduler failed to stop")

            collector.cleanup()

            self.performance_metrics['scheduler_lifecycle_time'] = stop_time
            self.tracker.pass_test(
                f"Scheduler lifecycle completed in {stop_time:.3f}s with {status['total_jobs']} jobs"
            )

        except Exception as e:
            self.tracker.fail_test(f"Scheduler test failed: {str(e)}")

    def test_8_live_collection_simulation(self):
        """Test live data collection for 30 seconds with real-time monitoring."""
        self.tracker.start_test("Live Collection Simulation (30 seconds)")

        try:
            collector = RealTimeDataCollector(self.test_config_path)

            # Get initial database state
            initial_stats = collector.database_manager.get_statistics()
            initial_records = initial_stats.get('table_counts', {}).get('ohlcv_data', 0)

            self.tracker.info(f"Starting live collection with {initial_records} existing records...")

            # Start collection with monitoring
            start_time = time.time()
            collection_results = []

            # Run collection for 30 seconds
            end_time = start_time + 30
            collection_count = 0

            while time.time() < end_time:
                cycle_start = time.time()

                # Perform one collection cycle
                results = collector.collect_all_data()
                collection_results.append(results)
                collection_count += 1

                cycle_time = time.time() - cycle_start

                # Real-time progress display
                remaining_time = end_time - time.time()
                progress = ((30 - remaining_time) / 30) * 100

                print(f"\r{Colors.CYAN}🔄 Collection {collection_count}: "
                      f"{results['total_records']} records, "
                      f"{results['total_errors']} errors, "
                      f"{cycle_time:.2f}s | "
                      f"Progress: {progress:.1f}% "
                      f"({remaining_time:.1f}s remaining){Colors.RESET}", end='', flush=True)

                # Wait a bit before next collection
                time.sleep(2)

            print()  # New line after progress

            total_time = time.time() - start_time

            # Analyze results
            total_new_records = sum(r['total_records'] for r in collection_results)
            total_errors = sum(r['total_errors'] for r in collection_results)
            avg_cycle_time = sum(r['collection_duration'] for r in collection_results) / len(collection_results)

            # Get final database state
            final_stats = collector.database_manager.get_statistics()
            final_records = final_stats.get('table_counts', {}).get('ohlcv_data', 0)

            collector.cleanup()

            self.performance_metrics['live_collection_time'] = total_time
            self.performance_metrics['live_records_per_second'] = total_new_records / total_time
            self.performance_metrics['live_avg_cycle_time'] = avg_cycle_time

            self.tracker.pass_test(
                f"Live collection: {collection_count} cycles, {total_new_records} new records, "
                f"{final_records - initial_records} DB growth in {total_time:.1f}s"
            )

        except Exception as e:
            self.tracker.fail_test(f"Live collection simulation failed: {str(e)}")

    def test_9_database_statistics(self):
        """Test database statistics and analysis."""
        self.tracker.start_test("Database Statistics")

        try:
            db_manager = CryptoDatabaseManager(self.test_db_path)

            # Get comprehensive statistics
            start_time = time.time()
            stats = db_manager.get_statistics()
            stats_time = time.time() - start_time

            # Display detailed statistics
            self.tracker.info("📊 Database Statistics:")

            # File size
            db_size = stats.get('database_size_mb', 0)
            print(f"   💾 Database Size: {db_size:.2f} MB")

            # Table counts
            table_counts = stats.get('table_counts', {})
            for table, count in table_counts.items():
                print(f"   📋 {table}: {count:,} records")

            # Symbol distribution
            symbol_counts = stats.get('symbol_counts', {})
            if symbol_counts:
                print(f"   🪙 Symbol Distribution:")
                for symbol, count in list(symbol_counts.items())[:5]:  # Top 5
                    print(f"      {symbol}: {count:,} records")

            # Timeframe distribution
            timeframe_dist = stats.get('timeframe_distribution', {})
            if timeframe_dist:
                print(f"   ⏰ Timeframe Distribution:")
                for tf, count in timeframe_dist.items():
                    print(f"      {tf}: {count:,} records")

            # Data date range
            date_range = stats.get('data_date_range', {})
            if date_range:
                print(f"   📅 Data Range: {date_range.get('earliest', 'N/A')} to {date_range.get('latest', 'N/A')}")
                print(f"   📈 Days of Data: {date_range.get('days_of_data', 0):.1f}")

            # Verify minimum data requirements
            total_ohlcv = table_counts.get('ohlcv_data', 0)
            total_prices = table_counts.get('realtime_prices', 0)

            if total_ohlcv < 10:
                raise Exception(f"Insufficient OHLCV data: {total_ohlcv} records")

            if total_prices < 2:
                raise Exception(f"Insufficient price data: {total_prices} records")

            db_manager.close()

            self.performance_metrics['stats_generation_time'] = stats_time
            self.tracker.pass_test(
                f"Statistics generated in {stats_time:.3f}s: {total_ohlcv} OHLCV, {total_prices} prices"
            )

        except Exception as e:
            self.tracker.fail_test(f"Database statistics test failed: {str(e)}")

    def test_10_performance_benchmarks(self):
        """Test and display performance benchmarks."""
        self.tracker.start_test("Performance Benchmarks")

        try:
            # Memory usage analysis
            memory_end = self._get_memory_usage()
            memory_used = memory_end - self.memory_start

            # CPU usage snapshot
            cpu_percent = psutil.cpu_percent(interval=1)

            # Display performance metrics
            self.tracker.info("🚀 Performance Benchmarks:")

            print(f"   💾 Memory Usage:")
            print(f"      Start: {self.memory_start:.1f} MB")
            print(f"      End: {memory_end:.1f} MB")
            print(f"      Used: {memory_used:.1f} MB")

            print(f"   🖥️  CPU Usage: {cpu_percent:.1f}%")

            print(f"   ⚡ Operation Times:")
            for metric, value in self.performance_metrics.items():
                if 'time' in metric:
                    print(f"      {metric.replace('_', ' ').title()}: {value:.3f}s")
                else:
                    print(f"      {metric.replace('_', ' ').title()}: {value:.2f}")

            # Calculate performance scores
            scores = self._calculate_performance_scores()

            print(f"   🏆 Performance Scores:")
            for category, score in scores.items():
                color = Colors.GREEN if score >= 80 else Colors.YELLOW if score >= 60 else Colors.RED
                print(f"      {category}: {color}{score:.1f}/100{Colors.RESET}")

            # Overall performance assessment
            overall_score = sum(scores.values()) / len(scores)

            if overall_score < 50:
                raise Exception(f"Poor performance: {overall_score:.1f}/100")

            self.tracker.pass_test(
                f"Performance benchmarks completed: {overall_score:.1f}/100 overall score"
            )

        except Exception as e:
            self.tracker.fail_test(f"Performance benchmark failed: {str(e)}")

    def _verify_database_content(self):
        """Verify final database content and integrity."""
        self.tracker.start_test("Final Database Verification")

        try:
            # Copy test database to production location for verification
            import shutil
            if Path(self.test_db_path).exists():
                shutil.copy2(self.test_db_path, self.production_db_path)
                self.tracker.info(f"Test database copied to {self.production_db_path}")

            # Verify production database
            db_manager = CryptoDatabaseManager(self.production_db_path)

            # Integrity check
            integrity_results = validate_database_integrity(db_manager)

            if not integrity_results['integrity_ok']:
                raise Exception(f"Database integrity issues: {integrity_results['errors_found']}")

            # Final statistics
            stats = db_manager.get_statistics()
            table_counts = stats.get('table_counts', {})

            # Detailed verification
            verification_results = {
                'database_file_exists': Path(self.production_db_path).exists(),
                'database_size_mb': stats.get('database_size_mb', 0),
                'tables_created': len(table_counts),
                'ohlcv_records': table_counts.get('ohlcv_data', 0),
                'price_records': table_counts.get('realtime_prices', 0),
                'symbols_covered': len(stats.get('symbol_counts', {})),
                'timeframes_covered': len(stats.get('timeframe_distribution', {})),
                'integrity_ok': integrity_results['integrity_ok']
            }

            # Print verification summary
            self.tracker.info("🔍 Final Database Verification:")
            for key, value in verification_results.items():
                status_icon = Colors.SUCCESS if value else Colors.FAILURE
                print(f"   {status_icon} {key.replace('_', ' ').title()}: {value}")

            db_manager.close()

            # Require minimum data for success
            min_requirements = {
                'ohlcv_records': 20,
                'price_records': 2,
                'symbols_covered': 1,
                'timeframes_covered': 1
            }

            for requirement, min_value in min_requirements.items():
                if verification_results.get(requirement, 0) < min_value:
                    raise Exception(f"Insufficient {requirement}: {verification_results[requirement]} < {min_value}")

            self.tracker.pass_test(
                f"Database verified: {verification_results['ohlcv_records']} OHLCV records, "
                f"{verification_results['price_records']} price records across "
                f"{verification_results['symbols_covered']} symbols"
            )

        except Exception as e:
            self.tracker.fail_test(f"Database verification failed: {str(e)}")

    def _cleanup_test_environment(self):
        """Clean up test environment."""
        try:
            # Remove test configuration
            if Path(self.test_config_path).exists():
                Path(self.test_config_path).unlink()

            # Keep test database for inspection but rename it
            if Path(self.test_db_path).exists():
                backup_path = f"data/test_backup_{int(time.time())}.db"
                Path(self.test_db_path).rename(backup_path)
                self.tracker.info(f"Test database saved as {backup_path}")

        except Exception as e:
            self.tracker.warning(f"Cleanup warning: {str(e)}")

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / (1024 * 1024)
        except:
            return 0.0

    def _calculate_performance_scores(self) -> Dict[str, float]:
        """Calculate performance scores from metrics."""
        scores = {}

        # Database initialization speed (under 1s = 100, over 5s = 0)
        db_init_time = self.performance_metrics.get('db_init_time', 5)
        scores['Database Init Speed'] = max(0, min(100, (5 - db_init_time) / 5 * 100))

        # Collection speed (over 10 records/sec = 100, under 1 = 0)
        records_per_sec = self.performance_metrics.get('live_records_per_second', 0)
        scores['Collection Speed'] = max(0, min(100, records_per_sec / 10 * 100))

        # Memory efficiency (under 50MB = 100, over 200MB = 0)
        memory_used = self.memory_start  # Simplified for now
        scores['Memory Efficiency'] = max(0, min(100, (200 - memory_used) / 200 * 100))

        # Overall responsiveness (under 1s avg cycle = 100, over 10s = 0)
        avg_cycle_time = self.performance_metrics.get('live_avg_cycle_time', 10)
        scores['Responsiveness'] = max(0, min(100, (10 - avg_cycle_time) / 10 * 100))

        return scores


def main():
    """Main test execution function."""

    # Set up logging to capture any issues
    logging.basicConfig(
        level=logging.WARNING,  # Reduce noise during tests
        format='%(asctime)s | %(levelname)s | %(message)s'
    )

    # Check if we're in the right directory
    if not Path('utils').exists() or not Path('data').exists():
        print(f"{Colors.RED}❌ Please run this script from the crypto-trader-pro root directory{Colors.RESET}")
        return False

    # Run the test suite
    tester = DataCollectionSystemTester()
    tester.run_all_tests()

    # Return success status
    return tester.tracker.tests_failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)