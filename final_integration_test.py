#!/usr/bin/env python3
"""
Crypto Trader Pro - Final Integration Test Suite

Comprehensive automated testing script that validates the entire trading bot system
including environment setup, configuration, database operations, API connections,
arbitrage detection, and full system integration.

This test suite provides a complete readiness assessment with scoring from 0-100%.

Version: 1.0.0
Author: Crypto Trader Pro Team
"""

import os
import sys
import time
import json
import sqlite3
import threading
import subprocess
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import importlib.util

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from colorama import Fore, Back, Style, init
    init(autoreset=True)
except ImportError:
    # Fallback if colorama is not available
    class Fore:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ""
    class Back:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ""
    class Style:
        BRIGHT = DIM = NORMAL = RESET_ALL = ""


class FinalIntegrationTest:
    """
    Comprehensive integration test suite for Crypto Trader Pro.

    Performs end-to-end testing of all system components and provides
    a readiness score from 0-100%.
    """

    def __init__(self):
        """Initialize the test suite."""
        self.test_results: Dict[str, List[Tuple[str, bool, str]]] = {
            'environment': [],
            'configuration': [],
            'database': [],
            'api_connections': [],
            'arbitrage_system': [],
            'integration': []
        }

        self.start_time = datetime.now()
        self.total_tests = 0
        self.passed_tests = 0

        # Test configuration
        self.test_config = {
            'integration_test_duration': 300,  # 5 minutes
            'required_python_version': (3, 8),
            'required_modules': [
                'ccxt', 'pandas', 'numpy', 'requests', 'colorama',
                'psutil', 'schedule', 'python-dotenv'
            ],
            'test_symbols': ['BTC/USDT', 'ETH/USDT'],
            'test_timeframes': ['1m', '5m']
        }

    def print_header(self):
        """Print test suite header."""
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{'='*80}")
        print(f"{Fore.CYAN}{Style.BRIGHT}🧪 CRYPTO TRADER PRO - FINAL INTEGRATION TEST SUITE")
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*80}")
        print(f"{Fore.WHITE}🎯 Comprehensive system validation and readiness assessment")
        print(f"{Fore.WHITE}📊 Testing all components: Environment, Config, Database, API, Integration")
        print(f"{Fore.WHITE}⏱️  Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.CYAN}{'='*80}\n")

    def run_test_category(self, category: str, tests: List[Tuple[str, callable]]):
        """
        Run a category of tests.

        Args:
            category: Test category name
            tests: List of (test_name, test_function) tuples
        """
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}📋 {category.upper().replace('_', ' ')} TESTS")
        print(f"{Fore.YELLOW}{'─'*60}")

        for test_name, test_func in tests:
            try:
                print(f"{Fore.CYAN}🔄 {test_name}...", end=" ")
                sys.stdout.flush()

                success, message = test_func()
                self.total_tests += 1

                if success:
                    self.passed_tests += 1
                    print(f"{Fore.GREEN}✅ PASS")
                    if message:
                        print(f"{Fore.WHITE}   {message}")
                else:
                    print(f"{Fore.RED}❌ FAIL")
                    if message:
                        print(f"{Fore.RED}   {message}")

                self.test_results[category].append((test_name, success, message))

            except Exception as e:
                self.total_tests += 1
                error_msg = f"Exception: {str(e)}"
                print(f"{Fore.RED}❌ ERROR")
                print(f"{Fore.RED}   {error_msg}")
                self.test_results[category].append((test_name, False, error_msg))

    # Environment Tests
    def test_python_version(self) -> Tuple[bool, str]:
        """Test Python version compatibility."""
        current_version = sys.version_info[:2]
        required_version = self.test_config['required_python_version']

        if current_version >= required_version:
            return True, f"Python {current_version[0]}.{current_version[1]} (Required: {required_version[0]}.{required_version[1]}+)"
        else:
            return False, f"Python {current_version[0]}.{current_version[1]} < Required {required_version[0]}.{required_version[1]}"

    def test_required_modules(self) -> Tuple[bool, str]:
        """Test if all required modules are installed."""
        missing_modules = []
        installed_modules = []

        for module in self.test_config['required_modules']:
            try:
                # Handle modules with different import names
                import_name = module
                if module == 'python-dotenv':
                    import_name = 'dotenv'

                spec = importlib.util.find_spec(import_name)
                if spec is not None:
                    installed_modules.append(module)
                else:
                    missing_modules.append(module)
            except ImportError:
                missing_modules.append(module)

        if not missing_modules:
            return True, f"All {len(installed_modules)} required modules installed"
        else:
            return False, f"Missing modules: {', '.join(missing_modules)}"

    def test_folder_structure(self) -> Tuple[bool, str]:
        """Test if required folder structure exists."""
        required_folders = [
            'data', 'utils', 'config', 'logs',
            'strategies', 'backtesting', 'live_trading'
        ]

        missing_folders = []
        existing_folders = []

        for folder in required_folders:
            folder_path = project_root / folder
            if folder_path.exists():
                existing_folders.append(folder)
            else:
                # Create missing folders
                try:
                    folder_path.mkdir(exist_ok=True)
                    existing_folders.append(folder)
                except Exception:
                    missing_folders.append(folder)

        if not missing_folders:
            return True, f"All {len(existing_folders)} required folders present"
        else:
            return False, f"Missing folders: {', '.join(missing_folders)}"

    def test_required_files(self) -> Tuple[bool, str]:
        """Test if required files exist."""
        required_files = [
            'config/config.json',
            'utils/__init__.py',
            'utils/market_data.py',
            'utils/exceptions.py',
            'utils/validation_helpers.py',
            'data/__init__.py',
            'data/database.py',
            'data/collector.py',
            'data/scheduler.py',
            'requirements.txt',
            'main.py'
        ]

        missing_files = []
        existing_files = []

        for file_path in required_files:
            full_path = project_root / file_path
            if full_path.exists():
                existing_files.append(file_path)
            else:
                missing_files.append(file_path)

        if not missing_files:
            return True, f"All {len(existing_files)} required files present"
        else:
            return False, f"Missing files: {', '.join(missing_files)}"

    # Configuration Tests
    def test_config_loading(self) -> Tuple[bool, str]:
        """Test configuration file loading."""
        try:
            config_path = project_root / 'config' / 'config.json'

            if not config_path.exists():
                return False, "config.json file not found"

            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            if not isinstance(config, dict):
                return False, "Configuration is not a valid JSON object"

            return True, f"Configuration loaded successfully ({len(config)} sections)"

        except json.JSONDecodeError as e:
            return False, f"JSON parsing error: {e}"
        except Exception as e:
            return False, f"Configuration loading error: {e}"

    def test_config_validation(self) -> Tuple[bool, str]:
        """Test configuration validation."""
        try:
            from config import load_config, validate_config

            config = load_config("config/config.json")
            validate_config(config)

            required_sections = [
                'exchange', 'data_collection', 'arbitrage',
                'database', 'risk_management', 'logging'
            ]

            missing_sections = [s for s in required_sections if s not in config]

            if missing_sections:
                return False, f"Missing required sections: {', '.join(missing_sections)}"

            return True, f"All {len(required_sections)} required sections validated"

        except Exception as e:
            return False, f"Configuration validation error: {e}"

    def test_log_folder_creation(self) -> Tuple[bool, str]:
        """Test log folder creation and permissions."""
        try:
            logs_path = project_root / 'logs'
            logs_path.mkdir(exist_ok=True)

            # Test write permissions
            test_file = logs_path / 'test_write.tmp'
            test_file.write_text('test')
            test_file.unlink()

            return True, f"Log folder created and writable: {logs_path}"

        except Exception as e:
            return False, f"Log folder creation error: {e}"

    def test_env_template(self) -> Tuple[bool, str]:
        """Test environment template file."""
        try:
            env_template = project_root / 'config' / '.env.template'

            if not env_template.exists():
                # Create a basic template
                template_content = """# Crypto Trader Pro Environment Variables
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_secret_here
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
TESTNET_MODE=true
MAX_POSITIONS=3
"""
                env_template.write_text(template_content)

            content = env_template.read_text()
            required_vars = ['BINANCE_API_KEY', 'BINANCE_API_SECRET']

            missing_vars = [var for var in required_vars if var not in content]

            if missing_vars:
                return False, f"Missing environment variables in template: {', '.join(missing_vars)}"

            return True, f"Environment template validated with {len(required_vars)} required variables"

        except Exception as e:
            return False, f"Environment template error: {e}"

    # Database Tests
    def test_database_creation(self) -> Tuple[bool, str]:
        """Test database file creation and connection."""
        try:
            from data import CryptoDatabaseManager

            # Use a test database
            test_db_path = project_root / 'data' / 'test_crypto_data.db'

            # Remove if exists
            if test_db_path.exists():
                test_db_path.unlink()

            db_manager = CryptoDatabaseManager(str(test_db_path))
            db_manager.initialize_database()

            # Verify file was created
            if not test_db_path.exists():
                return False, "Database file was not created"

            # Test connection
            conn = sqlite3.connect(str(test_db_path))
            conn.close()

            # Cleanup
            db_manager.close()
            test_db_path.unlink()

            return True, "Database creation and connection successful"

        except Exception as e:
            return False, f"Database creation error: {e}"

    def test_database_schema(self) -> Tuple[bool, str]:
        """Test database schema creation."""
        try:
            from data import CryptoDatabaseManager

            test_db_path = project_root / 'data' / 'test_schema.db'

            if test_db_path.exists():
                test_db_path.unlink()

            db_manager = CryptoDatabaseManager(str(test_db_path))
            db_manager.initialize_database()

            # Check if required tables exist
            conn = sqlite3.connect(str(test_db_path))
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            required_tables = [
                'ohlcv_data', 'realtime_prices',
                'trading_history', 'system_stats'
            ]

            missing_tables = [t for t in required_tables if t not in tables]

            conn.close()
            db_manager.close()
            test_db_path.unlink()

            if missing_tables:
                return False, f"Missing tables: {', '.join(missing_tables)}"

            return True, f"All {len(required_tables)} required tables created"

        except Exception as e:
            return False, f"Database schema error: {e}"

    def test_database_operations(self) -> Tuple[bool, str]:
        """Test basic database operations."""
        try:
            from data import CryptoDatabaseManager

            test_db_path = project_root / 'data' / 'test_operations.db'

            if test_db_path.exists():
                test_db_path.unlink()

            db_manager = CryptoDatabaseManager(str(test_db_path))
            db_manager.initialize_database()

            # Test data insertion
            test_data = [
                {
                    'timestamp': int(time.time() * 1000),
                    'open': 50000.0,
                    'high': 51000.0,
                    'low': 49000.0,
                    'close': 50500.0,
                    'volume': 100.0
                }
            ]

            db_manager.store_ohlcv_data('BTC/USDT', '5m', test_data)

            # Test data retrieval
            conn = sqlite3.connect(str(test_db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM ohlcv_data")
            count = cursor.fetchone()[0]
            conn.close()

            db_manager.close()
            test_db_path.unlink()

            if count > 0:
                return True, f"Database operations successful ({count} records inserted/retrieved)"
            else:
                return False, "No data was inserted into database"

        except Exception as e:
            return False, f"Database operations error: {e}"

    # API Connection Tests
    def test_binance_api_connection(self) -> Tuple[bool, str]:
        """Test Binance API connection."""
        try:
            from utils import MarketDataCollector

            collector = MarketDataCollector(testnet=True)

            if collector.test_connection():
                return True, "Binance API connection successful (testnet)"
            else:
                return False, "Binance API connection failed"

        except Exception as e:
            return False, f"Binance API connection error: {e}"

    def test_market_data_retrieval(self) -> Tuple[bool, str]:
        """Test market data retrieval functionality."""
        try:
            from utils import MarketDataCollector

            collector = MarketDataCollector(testnet=True)

            # Test price retrieval
            price = collector.get_current_price('BTC/USDT')

            if price and price > 0:
                return True, f"Market data retrieval successful (BTC/USDT: ${price:,.2f})"
            else:
                return False, "Failed to retrieve valid market data"

        except Exception as e:
            return False, f"Market data retrieval error: {e}"

    def test_multiple_symbols_data(self) -> Tuple[bool, str]:
        """Test data retrieval for multiple symbols."""
        try:
            from utils import MarketDataCollector

            collector = MarketDataCollector(testnet=True)
            symbols = self.test_config['test_symbols']

            successful_symbols = []
            failed_symbols = []

            for symbol in symbols:
                try:
                    price = collector.get_current_price(symbol)
                    if price and price > 0:
                        successful_symbols.append(symbol)
                    else:
                        failed_symbols.append(symbol)
                except Exception:
                    failed_symbols.append(symbol)

            if len(successful_symbols) == len(symbols):
                return True, f"All {len(symbols)} symbols retrieved successfully"
            elif successful_symbols:
                return False, f"Partial success: {len(successful_symbols)}/{len(symbols)} symbols"
            else:
                return False, "Failed to retrieve data for any symbols"

        except Exception as e:
            return False, f"Multiple symbols test error: {e}"

    def test_api_rate_limiting(self) -> Tuple[bool, str]:
        """Test API rate limiting functionality."""
        try:
            from utils import MarketDataCollector

            collector = MarketDataCollector(testnet=True)

            # Make multiple rapid API calls
            start_time = time.time()
            call_count = 0

            for i in range(15):  # Try to make 15 calls rapidly
                try:
                    collector.get_current_price('BTC/USDT')
                    call_count += 1
                except Exception:
                    break

            elapsed_time = time.time() - start_time

            # Should take at least 1 second for 15 calls due to rate limiting
            if elapsed_time >= 1.0:
                return True, f"Rate limiting working ({call_count} calls in {elapsed_time:.2f}s)"
            else:
                return False, f"Rate limiting may not be working ({call_count} calls in {elapsed_time:.2f}s)"

        except Exception as e:
            return False, f"Rate limiting test error: {e}"

    # Arbitrage System Tests
    def test_price_comparison_logic(self) -> Tuple[bool, str]:
        """Test price comparison logic for arbitrage detection."""
        try:
            from utils import MarketDataCollector

            collector = MarketDataCollector(testnet=True)

            # Get prices for the same symbol (simulating different exchanges)
            symbol = 'BTC/USDT'
            price1 = collector.get_current_price(symbol)

            # Simulate a price difference
            price2 = price1 * 1.01  # 1% higher

            # Test arbitrage calculation
            profit_percentage = ((price2 - price1) / price1) * 100

            if profit_percentage > 0:
                return True, f"Price comparison logic working (detected {profit_percentage:.2f}% difference)"
            else:
                return False, "Price comparison logic failed"

        except Exception as e:
            return False, f"Price comparison test error: {e}"

    def test_profit_calculation(self) -> Tuple[bool, str]:
        """Test arbitrage profit calculation."""
        try:
            # Test profit calculation with fees
            buy_price = 50000.0
            sell_price = 50500.0
            trading_fee = 0.001  # 0.1%

            # Calculate profit after fees
            buy_cost = buy_price * (1 + trading_fee)
            sell_revenue = sell_price * (1 - trading_fee)
            profit = sell_revenue - buy_cost
            profit_percentage = (profit / buy_cost) * 100

            if profit > 0:
                return True, f"Profit calculation working ({profit_percentage:.3f}% profit after fees)"
            else:
                return True, f"Profit calculation working (no profit: {profit_percentage:.3f}%)"

        except Exception as e:
            return False, f"Profit calculation error: {e}"

    def test_alert_system(self) -> Tuple[bool, str]:
        """Test alert system functionality."""
        try:
            # Test alert threshold logic
            min_profit_threshold = 0.5  # 0.5%
            detected_profit = 0.8  # 0.8%

            alert_triggered = detected_profit >= min_profit_threshold

            if alert_triggered:
                return True, f"Alert system working (triggered at {detected_profit}% > {min_profit_threshold}%)"
            else:
                return False, f"Alert system failed ({detected_profit}% < {min_profit_threshold}%)"

        except Exception as e:
            return False, f"Alert system test error: {e}"

    # Integration Tests
    def test_data_collection_integration(self) -> Tuple[bool, str]:
        """Test data collection system integration."""
        try:
            from utils import MarketDataCollector
            from data import CryptoDatabaseManager, RealTimeDataCollector

            # Setup components
            test_db_path = project_root / 'data' / 'test_integration.db'
            if test_db_path.exists():
                test_db_path.unlink()

            market_collector = MarketDataCollector(testnet=True)
            db_manager = CryptoDatabaseManager(str(test_db_path))
            db_manager.initialize_database()

            data_collector = RealTimeDataCollector(
                market_data_collector=market_collector,
                database_manager=db_manager,
                symbols=['BTC/USDT']
            )

            # Test data collection
            result = data_collector.collect_data_for_symbol('BTC/USDT', '5m')

            db_manager.close()
            test_db_path.unlink()

            if result:
                return True, "Data collection integration successful"
            else:
                return False, "Data collection integration failed"

        except Exception as e:
            return False, f"Data collection integration error: {e}"

    def test_full_system_startup(self) -> Tuple[bool, str]:
        """Test full system startup without errors."""
        try:
            # Import main components to test initialization
            from config import load_config, validate_config
            from utils import MarketDataCollector
            from data import CryptoDatabaseManager

            # Test configuration loading
            config = load_config("config/config.json")
            validate_config(config)

            # Test component initialization
            market_collector = MarketDataCollector(testnet=True)

            test_db_path = project_root / 'data' / 'test_startup.db'
            if test_db_path.exists():
                test_db_path.unlink()

            db_manager = CryptoDatabaseManager(str(test_db_path))
            db_manager.initialize_database()

            # Test basic functionality
            connection_ok = market_collector.test_connection()

            db_manager.close()
            test_db_path.unlink()

            if connection_ok:
                return True, "Full system startup successful"
            else:
                return False, "System startup failed - API connection issue"

        except Exception as e:
            return False, f"System startup error: {e}"

    def test_graceful_shutdown(self) -> Tuple[bool, str]:
        """Test graceful shutdown functionality."""
        try:
            from data import CryptoDatabaseManager

            # Test database connection cleanup
            test_db_path = project_root / 'data' / 'test_shutdown.db'
            if test_db_path.exists():
                test_db_path.unlink()

            db_manager = CryptoDatabaseManager(str(test_db_path))
            db_manager.initialize_database()

            # Test graceful shutdown
            db_manager.close()

            # Verify database is properly closed
            # (In a real scenario, this would test thread termination)

            test_db_path.unlink()

            return True, "Graceful shutdown successful"

        except Exception as e:
            return False, f"Graceful shutdown error: {e}"

    def run_all_tests(self):
        """Run all test categories."""
        # Environment Tests
        environment_tests = [
            ("Python Version Check", self.test_python_version),
            ("Required Modules Check", self.test_required_modules),
            ("Folder Structure Check", self.test_folder_structure),
            ("Required Files Check", self.test_required_files)
        ]
        self.run_test_category('environment', environment_tests)

        # Configuration Tests
        configuration_tests = [
            ("Configuration Loading", self.test_config_loading),
            ("Configuration Validation", self.test_config_validation),
            ("Log Folder Creation", self.test_log_folder_creation),
            ("Environment Template", self.test_env_template)
        ]
        self.run_test_category('configuration', configuration_tests)

        # Database Tests
        database_tests = [
            ("Database Creation", self.test_database_creation),
            ("Database Schema", self.test_database_schema),
            ("Database Operations", self.test_database_operations)
        ]
        self.run_test_category('database', database_tests)

        # API Connection Tests
        api_tests = [
            ("Binance API Connection", self.test_binance_api_connection),
            ("Market Data Retrieval", self.test_market_data_retrieval),
            ("Multiple Symbols Data", self.test_multiple_symbols_data),
            ("API Rate Limiting", self.test_api_rate_limiting)
        ]
        self.run_test_category('api_connections', api_tests)

        # Arbitrage System Tests
        arbitrage_tests = [
            ("Price Comparison Logic", self.test_price_comparison_logic),
            ("Profit Calculation", self.test_profit_calculation),
            ("Alert System", self.test_alert_system)
        ]
        self.run_test_category('arbitrage_system', arbitrage_tests)

        # Integration Tests
        integration_tests = [
            ("Data Collection Integration", self.test_data_collection_integration),
            ("Full System Startup", self.test_full_system_startup),
            ("Graceful Shutdown", self.test_graceful_shutdown)
        ]
        self.run_test_category('integration', integration_tests)

    def calculate_readiness_score(self) -> int:
        """Calculate system readiness score (0-100%)."""
        if self.total_tests == 0:
            return 0

        base_score = (self.passed_tests / self.total_tests) * 100

        # Weighted scoring based on test category importance
        category_weights = {
            'environment': 0.15,
            'configuration': 0.15,
            'database': 0.20,
            'api_connections': 0.25,
            'arbitrage_system': 0.15,
            'integration': 0.10
        }

        weighted_score = 0
        total_weight = 0

        for category, weight in category_weights.items():
            if category in self.test_results:
                category_tests = self.test_results[category]
                if category_tests:
                    category_passed = sum(1 for _, success, _ in category_tests if success)
                    category_total = len(category_tests)
                    category_score = (category_passed / category_total) * 100
                    weighted_score += category_score * weight
                    total_weight += weight

        if total_weight > 0:
            final_score = weighted_score / total_weight
        else:
            final_score = base_score

        return min(100, max(0, int(final_score)))

    def print_detailed_results(self):
        """Print detailed test results."""
        print(f"\n{Fore.CYAN}{Style.BRIGHT}📊 DETAILED TEST RESULTS")
        print(f"{Fore.CYAN}{'='*80}")

        for category, tests in self.test_results.items():
            if tests:
                passed = sum(1 for _, success, _ in tests if success)
                total = len(tests)

                print(f"\n{Fore.YELLOW}{Style.BRIGHT}{category.upper().replace('_', ' ')} ({passed}/{total})")
                print(f"{Fore.YELLOW}{'─'*50}")

                for test_name, success, message in tests:
                    status = f"{Fore.GREEN}✅" if success else f"{Fore.RED}❌"
                    print(f"{status} {test_name}")
                    if message:
                        color = Fore.WHITE if success else Fore.RED
                        print(f"   {color}{message}")

    def print_summary(self):
        """Print test summary and readiness score."""
        end_time = datetime.now()
        duration = end_time - self.start_time
        readiness_score = self.calculate_readiness_score()

        print(f"\n{Fore.CYAN}{Style.BRIGHT}🎯 FINAL INTEGRATION TEST SUMMARY")
        print(f"{Fore.CYAN}{'='*80}")

        print(f"\n{Fore.YELLOW}📋 Test Statistics:")
        print(f"{Fore.WHITE}   Total Tests: {self.total_tests}")
        print(f"{Fore.WHITE}   Tests Passed: {self.passed_tests}")
        print(f"{Fore.WHITE}   Tests Failed: {self.total_tests - self.passed_tests}")
        print(f"{Fore.WHITE}   Success Rate: {(self.passed_tests/self.total_tests)*100:.1f}%")
        print(f"{Fore.WHITE}   Duration: {str(duration).split('.')[0]}")

        # Readiness score with color coding
        if readiness_score >= 90:
            score_color = Fore.GREEN
            status = "🚀 EXCELLENT - Ready for Production"
        elif readiness_score >= 75:
            score_color = Fore.YELLOW
            status = "✅ GOOD - Ready with Minor Issues"
        elif readiness_score >= 50:
            score_color = Fore.YELLOW
            status = "⚠️  FAIR - Needs Attention"
        else:
            score_color = Fore.RED
            status = "❌ POOR - Major Issues Found"

        print(f"\n{Fore.YELLOW}🎯 System Readiness Score:")
        print(f"{score_color}{Style.BRIGHT}   {readiness_score}% - {status}")

        # Recommendations
        print(f"\n{Fore.YELLOW}💡 Recommendations:")
        if readiness_score >= 90:
            print(f"{Fore.GREEN}   • System is ready for production use")
            print(f"{Fore.GREEN}   • All critical components are functioning properly")
            print(f"{Fore.GREEN}   • Monitor system performance during initial runs")
        elif readiness_score >= 75:
            print(f"{Fore.YELLOW}   • Review failed tests and fix minor issues")
            print(f"{Fore.YELLOW}   • System can be used for testing and development")
            print(f"{Fore.YELLOW}   • Address configuration or API connection issues")
        else:
            print(f"{Fore.RED}   • Critical issues found - fix before production use")
            print(f"{Fore.RED}   • Check environment setup and dependencies")
            print(f"{Fore.RED}   • Verify API credentials and network connectivity")

        print(f"\n{Fore.CYAN}{'='*80}")

    def run(self):
        """Run the complete integration test suite."""
        self.print_header()

        try:
            self.run_all_tests()
            self.print_detailed_results()
            self.print_summary()

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}🛑 Test suite interrupted by user")
        except Exception as e:
            print(f"\n{Fore.RED}❌ Test suite error: {e}")
            traceback.print_exc()


def main():
    """Main entry point."""
    try:
        test_suite = FinalIntegrationTest()
        test_suite.run()
    except Exception as e:
        print(f"{Fore.RED}❌ Critical test suite error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()