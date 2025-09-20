"""
Real-time cryptocurrency data collection system.
Orchestrates data collection from multiple exchanges using market data collector and database storage.
"""

import json
import threading
import time
import signal
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from pathlib import Path
import logging
import psutil
import os

from utils.market_data import MarketDataCollector
from data.database import CryptoDatabaseManager
from utils.exceptions import (
    ConfigurationError,
    DataValidationError,
    APIConnectionError,
    InsufficientDataError
)

# Set up logging
logger = logging.getLogger(__name__)


class CollectionStatistics:
    """
    Thread-safe statistics tracking for data collection.
    """

    def __init__(self):
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        """Reset all statistics."""
        with self.lock:
            self.start_time = time.time()
            self.total_requests = 0
            self.successful_requests = 0
            self.failed_requests = 0
            self.total_records_inserted = 0
            self.last_collection_time = None
            self.collection_times = []
            self.errors_by_type = {}
            self.symbol_stats = {}

    def record_request(self, success: bool, symbol: str, data_type: str,
                      records_inserted: int = 0, error_type: str = None):
        """Record a data collection request."""
        with self.lock:
            self.total_requests += 1

            if success:
                self.successful_requests += 1
                self.total_records_inserted += records_inserted
            else:
                self.failed_requests += 1
                if error_type:
                    self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1

            # Track per-symbol statistics
            if symbol not in self.symbol_stats:
                self.symbol_stats[symbol] = {
                    'requests': 0, 'successes': 0, 'failures': 0, 'records': 0
                }

            self.symbol_stats[symbol]['requests'] += 1
            if success:
                self.symbol_stats[symbol]['successes'] += 1
                self.symbol_stats[symbol]['records'] += records_inserted
            else:
                self.symbol_stats[symbol]['failures'] += 1

    def record_collection_cycle(self, duration: float):
        """Record completion of a collection cycle."""
        with self.lock:
            self.last_collection_time = time.time()
            self.collection_times.append(duration)
            # Keep only last 100 collection times for average calculation
            if len(self.collection_times) > 100:
                self.collection_times.pop(0)

    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics."""
        with self.lock:
            runtime = time.time() - self.start_time
            success_rate = (self.successful_requests / max(self.total_requests, 1)) * 100
            avg_collection_time = sum(self.collection_times) / max(len(self.collection_times), 1)

            return {
                'runtime_seconds': runtime,
                'total_requests': self.total_requests,
                'successful_requests': self.successful_requests,
                'failed_requests': self.failed_requests,
                'success_rate_percent': round(success_rate, 2),
                'total_records_inserted': self.total_records_inserted,
                'requests_per_minute': round((self.total_requests / max(runtime, 1)) * 60, 2),
                'records_per_minute': round((self.total_records_inserted / max(runtime, 1)) * 60, 2),
                'last_collection_time': self.last_collection_time,
                'average_collection_cycle_seconds': round(avg_collection_time, 2),
                'errors_by_type': self.errors_by_type.copy(),
                'symbol_statistics': self.symbol_stats.copy()
            }


class RealTimeDataCollector:
    """
    Real-time cryptocurrency data collection system.

    Features:
    - Multi-threaded data collection for maximum efficiency
    - Automatic gap detection and filling
    - Real-time performance monitoring
    - Memory usage optimization
    - Graceful shutdown handling
    - Comprehensive error recovery
    """

    def __init__(self,
                 market_data_collector: Optional[MarketDataCollector] = None,
                 database_manager: Optional[CryptoDatabaseManager] = None,
                 symbols: Optional[List[str]] = None,
                 timeframes: Optional[List[str]] = None,
                 config_path: str = 'config/config.json'):
        """
        Initialize the real-time data collector.

        Args:
            market_data_collector (Optional[MarketDataCollector]): Market data collector instance
            database_manager (Optional[CryptoDatabaseManager]): Database manager instance
            symbols (Optional[List[str]]): List of symbols to collect data for
            timeframes (Optional[List[str]]): List of timeframes to collect
            config_path (str): Path to configuration file

        Raises:
            ConfigurationError: If configuration is invalid
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()

        # Initialize components (use provided instances or create new ones)
        if market_data_collector is not None:
            self.market_data_collector = market_data_collector
        else:
            self.market_data_collector = MarketDataCollector(
                testnet=self.config.get('exchange', {}).get('testnet', True)
            )

        if database_manager is not None:
            self.database_manager = database_manager
        else:
            self.database_manager = CryptoDatabaseManager(
                db_path=self.config.get('database', {}).get('path', 'data/crypto_data.db')
            )

        # Collection settings (use provided values or config defaults)
        if symbols is not None:
            self.symbols = symbols
        else:
            self.symbols = self.config.get('data_collection', {}).get('target_symbols', [
                'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'DOT/USDT'
            ])

        if timeframes is not None:
            self.timeframes = timeframes
        else:
            self.timeframes = self.config.get('data_collection', {}).get('timeframes', [
                '1m', '5m', '15m'
            ])

        self.collection_interval = self.config.get('data_collection', {}).get(
            'collection_interval_seconds', 60
        )

        self.max_workers = self.config.get('data_collection', {}).get('max_workers', 5)

        # State management
        self.is_running = False
        self.collection_thread = None
        self.statistics = CollectionStatistics()
        self.stats = self.statistics  # Alias for backward compatibility
        self.shutdown_event = threading.Event()

        # Memory management
        self.memory_check_interval = 300  # Check every 5 minutes
        self.max_memory_mb = self.config.get('data_collection', {}).get('max_memory_mb', 512)

        # Error recovery
        self.consecutive_failures = 0
        self.max_consecutive_failures = 10
        self.failure_backoff_seconds = 30

        logger.info(f"RealTimeDataCollector initialized: {len(self.symbols)} symbols, "
                   f"{len(self.timeframes)} timeframes, {self.collection_interval}s interval")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file with fallback to default config."""
        try:
            if not self.config_path.exists():
                logger.warning(f"Configuration file not found: {self.config_path}. Using default configuration.")
                return self._get_default_config()

            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            logger.info(f"Configuration loaded from {self.config_path}")
            return config

        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load configuration: {e}. Using default configuration.")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for data collection."""
        return {
            "exchange": {
                "name": "binance",
                "testnet": True
            },
            "data_collection": {
                "target_symbols": ["BTC/USDT", "ETH/USDT", "BNB/USDT"],
                "timeframes": ["1m", "5m", "15m"],
                "collection_interval_seconds": 60,
                "max_workers": 5,
                "max_memory_mb": 512
            },
            "database": {
                "path": "data/crypto_data.db"
            }
        }

    def collect_data_for_symbol(self, symbol: str, timeframe: str) -> bool:
        """
        Collect data for a specific symbol and timeframe (test-compatible method).

        Args:
            symbol (str): Trading symbol
            timeframe (str): Time interval

        Returns:
            bool: True if collection was successful, False otherwise
        """
        result = self.collect_ohlcv_data(symbol, timeframe)
        return result.get('success', False)

    def collect_ohlcv_data(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Collect OHLCV data for a specific symbol and timeframe.

        Args:
            symbol (str): Trading symbol
            timeframe (str): Time interval

        Returns:
            Dict[str, Any]: Collection result with statistics
        """
        result = {
            'symbol': symbol,
            'timeframe': timeframe,
            'success': False,
            'records_inserted': 0,
            'error': None,
            'collection_time': time.time()
        }

        try:
            # Get last timestamp from database
            last_timestamp = self.database_manager.get_latest_timestamp(symbol, timeframe)

            # Calculate how many candles to fetch
            if last_timestamp:
                # Fetch from last timestamp + 1 interval
                interval_seconds = self._get_interval_seconds(timeframe)
                since_timestamp = last_timestamp + interval_seconds

                # Calculate limit based on time gap
                current_time = int(time.time())
                time_gap = current_time - since_timestamp
                estimated_candles = min(max(int(time_gap / interval_seconds), 1), 500)
            else:
                # First time collection - get recent data
                estimated_candles = 100

            # Collect data from exchange
            ohlcv_data = self.market_data_collector.get_klines(
                symbol=symbol,
                interval=timeframe,
                limit=estimated_candles
            )

            if ohlcv_data:
                # Filter out data we already have
                if last_timestamp:
                    ohlcv_data = [candle for candle in ohlcv_data
                                 if candle[0] > last_timestamp]

                # Insert into database
                if ohlcv_data:
                    records_inserted = self.database_manager.insert_ohlcv_data(
                        symbol, timeframe, ohlcv_data
                    )
                    result['records_inserted'] = records_inserted
                    result['success'] = True

                    logger.debug(f"Collected {records_inserted} new {timeframe} candles for {symbol}")
                else:
                    result['success'] = True  # No new data, but not an error
                    logger.debug(f"No new {timeframe} data for {symbol}")
            else:
                result['error'] = "No data returned from exchange"

        except Exception as e:
            result['error'] = str(e)
            error_type = type(e).__name__
            logger.error(f"Failed to collect {timeframe} data for {symbol}: {e}")
            self.statistics.record_request(False, symbol, f"ohlcv_{timeframe}", 0, error_type)
            return result

        # Record statistics
        self.statistics.record_request(
            result['success'], symbol, f"ohlcv_{timeframe}",
            result['records_inserted'], result['error']
        )

        return result

    def collect_realtime_prices(self) -> Dict[str, Any]:
        """
        Collect real-time price data for all symbols.

        Returns:
            Dict[str, Any]: Collection results
        """
        results = {
            'success_count': 0,
            'failure_count': 0,
            'total_symbols': len(self.symbols),
            'collection_time': time.time(),
            'errors': []
        }

        try:
            # Get price data for multiple symbols efficiently
            price_data = self.market_data_collector.get_multiple_symbols_data(
                self.symbols, "ticker"
            )

            # Process results
            for symbol in self.symbols:
                try:
                    if symbol in price_data['data']:
                        ticker = price_data['data'][symbol]

                        # Prepare price data for database
                        price_record = {
                            'price': ticker['last'],
                            'volume_24h': ticker.get('volume'),
                            'price_change_24h': ticker.get('change'),
                            'price_change_percent_24h': ticker.get('percentage'),
                            'timestamp': int(time.time())
                        }

                        # Insert into database
                        if self.database_manager.insert_realtime_price(symbol, price_record):
                            results['success_count'] += 1
                            self.statistics.record_request(True, symbol, "price", 1)
                        else:
                            results['failure_count'] += 1
                            results['errors'].append(f"Database insert failed for {symbol}")
                            self.statistics.record_request(False, symbol, "price", 0, "database_error")
                    else:
                        results['failure_count'] += 1
                        error = price_data['errors'].get(symbol, "Unknown error")
                        results['errors'].append(f"{symbol}: {error}")
                        self.statistics.record_request(False, symbol, "price", 0, "api_error")

                except Exception as e:
                    results['failure_count'] += 1
                    results['errors'].append(f"{symbol}: {str(e)}")
                    self.statistics.record_request(False, symbol, "price", 0, type(e).__name__)

        except Exception as e:
            logger.error(f"Failed to collect real-time prices: {e}")
            results['errors'].append(f"Batch collection failed: {str(e)}")

        return results

    def check_and_fill_gaps(self) -> Dict[str, Any]:
        """
        Check for data gaps and attempt to fill them.

        Returns:
            Dict[str, Any]: Gap filling results
        """
        results = {
            'gaps_found': 0,
            'gaps_filled': 0,
            'symbols_checked': 0,
            'errors': []
        }

        # Check gaps for the last 24 hours
        end_time = int(time.time())
        start_time = end_time - (24 * 60 * 60)  # 24 hours ago

        for symbol in self.symbols:
            for timeframe in self.timeframes:
                try:
                    results['symbols_checked'] += 1

                    # Check for gaps
                    gaps = self.database_manager.check_data_gaps(
                        symbol, timeframe, start_time, end_time
                    )

                    results['gaps_found'] += len(gaps)

                    # Fill gaps
                    for gap_start, gap_end in gaps:
                        try:
                            # Calculate how many candles needed
                            interval_seconds = self._get_interval_seconds(timeframe)
                            candles_needed = min(int((gap_end - gap_start) / interval_seconds), 500)

                            if candles_needed > 0:
                                # Fetch historical data for gap
                                gap_data = self.market_data_collector.get_klines(
                                    symbol=symbol,
                                    interval=timeframe,
                                    limit=candles_needed
                                )

                                # Filter data to gap range
                                filtered_data = [
                                    candle for candle in gap_data
                                    if gap_start <= candle[0] <= gap_end
                                ]

                                if filtered_data:
                                    inserted = self.database_manager.insert_ohlcv_data(
                                        symbol, timeframe, filtered_data
                                    )
                                    results['gaps_filled'] += 1
                                    logger.info(f"Filled gap for {symbol} {timeframe}: "
                                              f"{inserted} records")

                        except Exception as e:
                            error_msg = f"Failed to fill gap for {symbol} {timeframe}: {e}"
                            results['errors'].append(error_msg)
                            logger.warning(error_msg)

                except Exception as e:
                    error_msg = f"Failed to check gaps for {symbol} {timeframe}: {e}"
                    results['errors'].append(error_msg)
                    logger.warning(error_msg)

        return results

    def collect_all_data(self) -> Dict[str, Any]:
        """
        Collect all data types using multi-threading.

        Returns:
            Dict[str, Any]: Complete collection results
        """
        start_time = time.time()

        results = {
            'start_time': start_time,
            'ohlcv_results': [],
            'price_results': {},
            'gap_fill_results': {},
            'total_records': 0,
            'total_errors': 0,
            'collection_duration': 0
        }

        try:
            # Collect OHLCV data using thread pool
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all OHLCV collection tasks
                future_to_task = {}

                for symbol in self.symbols:
                    for timeframe in self.timeframes:
                        future = executor.submit(self.collect_ohlcv_data, symbol, timeframe)
                        future_to_task[future] = (symbol, timeframe)

                # Collect results as they complete
                for future in as_completed(future_to_task):
                    symbol, timeframe = future_to_task[future]
                    try:
                        result = future.result(timeout=30)  # 30 second timeout per task
                        results['ohlcv_results'].append(result)

                        if result['success']:
                            results['total_records'] += result['records_inserted']
                        else:
                            results['total_errors'] += 1

                    except Exception as e:
                        error_result = {
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'success': False,
                            'error': f"Task execution failed: {str(e)}",
                            'records_inserted': 0
                        }
                        results['ohlcv_results'].append(error_result)
                        results['total_errors'] += 1

            # Collect real-time prices
            results['price_results'] = self.collect_realtime_prices()
            results['total_errors'] += results['price_results']['failure_count']

            # Check and fill gaps periodically (every 10th collection)
            if hasattr(self, '_collection_count'):
                self._collection_count += 1
            else:
                self._collection_count = 1

            if self._collection_count % 10 == 0:
                results['gap_fill_results'] = self.check_and_fill_gaps()

        except Exception as e:
            logger.error(f"Collection cycle failed: {e}")
            results['total_errors'] += 1

        # Calculate performance metrics
        results['collection_duration'] = time.time() - start_time
        self.statistics.record_collection_cycle(results['collection_duration'])

        # Update consecutive failure counter
        if results['total_errors'] == 0:
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1

        return results

    def start_collection(self):
        """
        Start the real-time data collection process.
        """
        if self.is_running:
            logger.warning("Collection is already running")
            return

        self.is_running = True
        self.shutdown_event.clear()
        self.statistics.reset()

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("Starting real-time data collection...")

        # Start collection in separate thread
        self.collection_thread = threading.Thread(target=self._collection_loop)
        self.collection_thread.daemon = True
        self.collection_thread.start()

        logger.info("Real-time data collection started successfully")

    def stop_collection(self):
        """
        Stop the real-time data collection process gracefully.
        """
        if not self.is_running:
            logger.warning("Collection is not running")
            return

        logger.info("Stopping real-time data collection...")

        self.is_running = False
        self.shutdown_event.set()

        # Wait for collection thread to finish
        if self.collection_thread and self.collection_thread.is_alive():
            self.collection_thread.join(timeout=30)

        logger.info("Real-time data collection stopped")

    def get_collection_status(self) -> Dict[str, Any]:
        """
        Get current collection status and statistics.

        Returns:
            Dict[str, Any]: Comprehensive status information
        """
        status = {
            'is_running': self.is_running,
            'consecutive_failures': self.consecutive_failures,
            'symbols': self.symbols,
            'timeframes': self.timeframes,
            'collection_interval': self.collection_interval,
            'max_workers': self.max_workers,
            'memory_usage_mb': self._get_memory_usage(),
            'database_stats': self.database_manager.get_statistics(),
            'collection_statistics': self.statistics.get_stats()
        }

        return status

    def _collection_loop(self):
        """Main collection loop running in separate thread."""
        last_memory_check = time.time()

        while self.is_running and not self.shutdown_event.is_set():
            try:
                # Check for excessive consecutive failures
                if self.consecutive_failures >= self.max_consecutive_failures:
                    logger.error(f"Too many consecutive failures ({self.consecutive_failures}). "
                               f"Backing off for {self.failure_backoff_seconds} seconds.")
                    self.shutdown_event.wait(self.failure_backoff_seconds)
                    self.consecutive_failures = 0  # Reset after backoff
                    continue

                # Perform data collection
                collection_start = time.time()
                results = self.collect_all_data()

                # Log collection summary
                logger.info(f"Collection cycle completed: {results['total_records']} records, "
                           f"{results['total_errors']} errors, "
                           f"{results['collection_duration']:.2f}s")

                # Memory management check
                current_time = time.time()
                if current_time - last_memory_check > self.memory_check_interval:
                    self._check_memory_usage()
                    last_memory_check = current_time

                # Wait for next collection interval
                sleep_time = max(0, self.collection_interval - results['collection_duration'])
                if sleep_time > 0:
                    self.shutdown_event.wait(sleep_time)

            except Exception as e:
                logger.error(f"Collection loop error: {e}")
                self.consecutive_failures += 1
                # Wait before retrying
                self.shutdown_event.wait(min(30, self.consecutive_failures * 5))

        logger.info("Collection loop terminated")

    def _get_interval_seconds(self, timeframe: str) -> int:
        """Get interval in seconds for a timeframe."""
        interval_map = {
            '1m': 60, '3m': 180, '5m': 300, '15m': 900, '30m': 1800,
            '1h': 3600, '2h': 7200, '4h': 14400, '6h': 21600, '8h': 28800, '12h': 43200,
            '1d': 86400, '3d': 259200, '1w': 604800, '1M': 2592000
        }
        return interval_map.get(timeframe, 60)

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process(os.getpid())
            return round(process.memory_info().rss / (1024 * 1024), 2)
        except Exception:
            return 0.0

    def _check_memory_usage(self):
        """Check memory usage and warn if excessive."""
        memory_mb = self._get_memory_usage()
        if memory_mb > self.max_memory_mb:
            logger.warning(f"High memory usage: {memory_mb:.1f} MB "
                          f"(limit: {self.max_memory_mb} MB)")
            # Could implement memory cleanup here

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.stop_collection()

    def cleanup(self):
        """Clean up resources."""
        try:
            self.stop_collection()
            self.database_manager.close()
            logger.info("RealTimeDataCollector cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.cleanup()
        except:
            pass  # Ignore errors during destruction


# Utility functions

def create_default_config() -> Dict[str, Any]:
    """
    Create a default configuration for the data collector.

    Returns:
        Dict[str, Any]: Default configuration
    """
    return {
        "exchange": {
            "name": "binance",
            "testnet": True
        },
        "database": {
            "path": "data/crypto_data.db"
        },
        "data_collection": {
            "symbols": ["BTC/USDT", "ETH/USDT", "BNB/USDT", "ADA/USDT", "DOT/USDT"],
            "timeframes": ["1m", "5m", "15m"],
            "interval_seconds": 60,
            "max_workers": 5,
            "max_memory_mb": 512
        }
    }


def run_data_collection(config_path: str = 'config/config.json'):
    """
    Run data collection as a standalone process.

    Args:
        config_path (str): Path to configuration file
    """
    collector = None

    try:
        collector = RealTimeDataCollector(config_path)

        # Test connections before starting
        if not collector.market_data_collector.test_connection():
            logger.error("Market data connection test failed")
            return False

        logger.info("Starting data collection process...")
        collector.start_collection()

        # Keep the main thread alive
        while collector.is_running:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Data collection failed: {e}")
    finally:
        if collector:
            collector.cleanup()

    return True


if __name__ == "__main__":
    # Set up logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )

    # Run data collection
    success = run_data_collection()
    sys.exit(0 if success else 1)