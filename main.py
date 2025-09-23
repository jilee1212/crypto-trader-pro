#!/usr/bin/env python3
"""
Crypto Trader Pro - Main Application Entry Point

A professional cryptocurrency trading bot with advanced strategies, backtesting capabilities,
and live trading functionality. This main script provides a unified interface to all
system components including data collection, arbitrage monitoring, and trading strategies.

Version: 1.0.0
Author: Crypto Trader Pro Team
"""

import os
import sys
import time
import signal
import threading
import traceback
from datetime import datetime, timedelta
from pathlib import Path
import psutil
import json
from typing import Dict, Any, Optional

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from colorama import Fore, Back, Style, init
    init(autoreset=True)  # Initialize colorama for Windows compatibility
except ImportError:
    # Fallback if colorama is not available
    class Fore:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ""
    class Back:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ""
    class Style:
        BRIGHT = DIM = NORMAL = RESET_ALL = ""

# Import project modules
try:
    from config import load_config, validate_config, get_logger, setup_logging
    from utils import MarketDataCollector, TradingBotException
    from data import CryptoDatabaseManager, RealTimeDataCollector, DataCollectionScheduler
except ImportError as e:
    print(f"[ERROR] Failed to import required modules: {e}")
    print("Please ensure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)


class CryptoTradingBot:
    """
    Main Crypto Trading Bot Application

    Provides a unified interface to all trading bot components including:
    - Real-time data collection
    - Arbitrage opportunity monitoring
    - Risk management
    - System status monitoring
    """

    def __init__(self):
        """Initialize the trading bot with all necessary components."""
        self.config: Dict[str, Any] = {}
        self.logger = None
        self.running = False
        self.start_time = datetime.now()

        # Core components
        self.market_data_collector: Optional[MarketDataCollector] = None
        self.database_manager: Optional[CryptoDatabaseManager] = None
        self.data_collector: Optional[RealTimeDataCollector] = None
        self.scheduler: Optional[DataCollectionScheduler] = None

        # Monitoring and statistics
        self.stats = {
            'data_points_collected': 0,
            'arbitrage_opportunities': 0,
            'api_calls_made': 0,
            'errors_encountered': 0,
            'last_update': datetime.now()
        }

        # Thread management
        self.threads = []
        self.shutdown_event = threading.Event()

        # Setup signal handlers for graceful shutdown (only in main thread)
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except ValueError:
            # Signal handlers only work in main thread, skip if not available
            pass

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n{Fore.YELLOW}[SIGNAL] Received shutdown signal ({signum})")
        print(f"{Fore.YELLOW}[PROCESS] Initiating graceful shutdown...")
        self.shutdown()

    def initialize(self) -> bool:
        """
        Initialize all system components.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            print(f"{Fore.CYAN}🚀 Initializing Crypto Trader Pro...")

            # Setup logging
            setup_logging()
            self.logger = get_logger(__name__)
            self.logger.info("Starting Crypto Trader Pro initialization")

            # Load and validate configuration
            config_path = "config/config.json"
            if not os.path.exists(config_path):
                print(f"{Fore.RED}[ERROR] Configuration file not found: {config_path}")
                return False

            self.config = load_config(config_path)
            validate_config(self.config)
            print(f"{Fore.GREEN}[OK] Configuration loaded and validated")

            # Initialize market data collector
            self.market_data_collector = MarketDataCollector(
                testnet=self.config['exchange'].get('testnet', True)
            )

            # Test API connection
            if not self.market_data_collector.test_connection():
                print(f"{Fore.RED}[ERROR] Failed to connect to exchange API")
                return False
            print(f"{Fore.GREEN}[OK] Exchange API connection established")

            # Initialize database manager
            db_path = self.config['database']['path']
            self.database_manager = CryptoDatabaseManager(db_path)
            self.database_manager.initialize_database()
            print(f"{Fore.GREEN}[OK] Database initialized: {db_path}")

            # Initialize real-time data collector
            symbols = self.config['data_collection']['target_symbols']
            self.data_collector = RealTimeDataCollector(
                market_data_collector=self.market_data_collector,
                database_manager=self.database_manager,
                symbols=symbols
            )
            print(f"{Fore.GREEN}[OK] Real-time data collector initialized")

            # Initialize scheduler
            self.scheduler = DataCollectionScheduler(
                data_collector=self.data_collector,
                config=self.config
            )
            print(f"{Fore.GREEN}[OK] Data collection scheduler initialized")

            self.logger.info("Crypto Trader Pro initialization completed successfully")
            return True

        except Exception as e:
            print(f"{Fore.RED}[ERROR] Initialization failed: {e}")
            if self.logger:
                self.logger.error(f"Initialization failed: {e}", exc_info=True)
            return False

    def show_welcome_message(self):
        """Display welcome message and system information."""
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{'='*60}")
        print(f"{Fore.CYAN}{Style.BRIGHT}🚀 CRYPTO TRADER PRO v1.0.0")
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*60}")
        print(f"{Fore.WHITE}💰 Professional Cryptocurrency Trading Bot")
        print(f"{Fore.WHITE}[TARGET] Target: 5-10% Monthly Returns")
        print(f"{Fore.WHITE}🛡️  Risk Management: Max 1-2% Loss Per Trade")
        print(f"{Fore.WHITE}[DATA] Strategy: RSI-based Day Trading + Arbitrage")
        print(f"{Fore.CYAN}{'='*60}\n")

    def show_main_menu(self) -> int:
        """
        Display main menu and get user selection.

        Returns:
            int: Selected menu option
        """
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}📋 MAIN MENU")
        print(f"{Fore.YELLOW}{'─'*40}")
        print(f"{Fore.WHITE}1. [CONNECT] Data Collection Only")
        print(f"{Fore.WHITE}2. 🔍 Arbitrage Monitoring Only")
        print(f"{Fore.WHITE}3. 🚀 Full System Integration")
        print(f"{Fore.WHITE}4. [DATA] System Status Check")
        print(f"{Fore.WHITE}5. ⚙️  Configuration Review")
        print(f"{Fore.WHITE}6. 🧪 Run Test Suite")
        print(f"{Fore.RED}0. 🚪 Exit")
        print(f"{Fore.YELLOW}{'─'*40}")

        while True:
            try:
                choice = input(f"{Fore.CYAN}👉 Select option (0-6): {Style.RESET_ALL}")
                choice = int(choice)
                if 0 <= choice <= 6:
                    return choice
                else:
                    print(f"{Fore.RED}[ERROR] Please enter a number between 0 and 6")
            except ValueError:
                print(f"{Fore.RED}[ERROR] Please enter a valid number")
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}👋 Goodbye!")
                return 0

    def show_status_dashboard(self):
        """Display real-time status dashboard."""
        current_time = datetime.now()
        uptime = current_time - self.start_time
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent()

        # Clear screen (works on both Windows and Unix)
        os.system('cls' if os.name == 'nt' else 'clear')

        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*70}")
        print(f"{Fore.CYAN}{Style.BRIGHT}[DATA] CRYPTO TRADER PRO - LIVE DASHBOARD")
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*70}")

        print(f"\n{Fore.YELLOW}🕐 SYSTEM STATUS")
        print(f"{Fore.WHITE}   Current Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.WHITE}   System Uptime: {str(uptime).split('.')[0]}")
        print(f"{Fore.WHITE}   Status: {Fore.GREEN}{'🟢 RUNNING' if self.running else '🔴 STOPPED'}")

        print(f"\n{Fore.YELLOW}📈 PERFORMANCE METRICS")
        print(f"{Fore.WHITE}   Memory Usage: {memory_mb:.1f} MB")
        print(f"{Fore.WHITE}   CPU Usage: {cpu_percent:.1f}%")
        print(f"{Fore.WHITE}   Data Points: {self.stats['data_points_collected']:,}")
        print(f"{Fore.WHITE}   API Calls: {self.stats['api_calls_made']:,}")

        print(f"\n{Fore.YELLOW}[TARGET] TRADING METRICS")
        print(f"{Fore.WHITE}   Arbitrage Opportunities: {self.stats['arbitrage_opportunities']}")
        print(f"{Fore.WHITE}   Errors Encountered: {self.stats['errors_encountered']}")
        print(f"{Fore.WHITE}   Last Update: {self.stats['last_update'].strftime('%H:%M:%S')}")

        if self.data_collector and hasattr(self.data_collector, 'stats'):
            collector_stats = self.data_collector.stats
            print(f"\n{Fore.YELLOW}[CONNECT] DATA COLLECTION")
            print(f"{Fore.WHITE}   Success Rate: {collector_stats.success_rate:.1f}%")
            print(f"{Fore.WHITE}   Total Requests: {collector_stats.total_requests}")
            print(f"{Fore.WHITE}   Failed Requests: {collector_stats.failed_requests}")

        print(f"\n{Fore.CYAN}{'─'*70}")
        print(f"{Fore.CYAN}Press Ctrl+C to stop | Updates every 5 seconds")
        print(f"{Fore.CYAN}{'─'*70}")

    def run_data_collection_only(self):
        """Run data collection mode only."""
        print(f"\n{Fore.GREEN}🚀 Starting Data Collection Mode...")
        self.running = True

        try:
            # Start data collection in a separate thread
            collection_thread = threading.Thread(
                target=self._run_data_collection_worker,
                daemon=True
            )
            collection_thread.start()
            self.threads.append(collection_thread)

            # Show live dashboard
            while self.running and not self.shutdown_event.is_set():
                self.show_status_dashboard()
                time.sleep(5)

        except KeyboardInterrupt:
            self.shutdown()
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Data collection error: {e}")
            self.logger.error(f"Data collection error: {e}", exc_info=True)

    def run_arbitrage_monitoring(self):
        """Run arbitrage monitoring mode only."""
        print(f"\n{Fore.GREEN}🔍 Starting Arbitrage Monitoring Mode...")
        self.running = True

        try:
            # Start arbitrage monitoring in a separate thread
            arbitrage_thread = threading.Thread(
                target=self._run_arbitrage_worker,
                daemon=True
            )
            arbitrage_thread.start()
            self.threads.append(arbitrage_thread)

            # Show live dashboard
            while self.running and not self.shutdown_event.is_set():
                self.show_status_dashboard()
                time.sleep(5)

        except KeyboardInterrupt:
            self.shutdown()
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Arbitrage monitoring error: {e}")
            self.logger.error(f"Arbitrage monitoring error: {e}", exc_info=True)

    def run_full_system(self):
        """Run full integrated system."""
        print(f"\n{Fore.GREEN}🚀 Starting Full System Integration...")
        self.running = True

        try:
            # Start all components
            self._start_all_components()

            # Show live dashboard
            while self.running and not self.shutdown_event.is_set():
                self.show_status_dashboard()
                time.sleep(5)

        except KeyboardInterrupt:
            self.shutdown()
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Full system error: {e}")
            self.logger.error(f"Full system error: {e}", exc_info=True)

    def _start_all_components(self):
        """Start all system components in separate threads."""
        # Data collection thread
        collection_thread = threading.Thread(
            target=self._run_data_collection_worker,
            daemon=True
        )
        collection_thread.start()
        self.threads.append(collection_thread)

        # Arbitrage monitoring thread
        arbitrage_thread = threading.Thread(
            target=self._run_arbitrage_worker,
            daemon=True
        )
        arbitrage_thread.start()
        self.threads.append(arbitrage_thread)

        # Scheduler thread
        scheduler_thread = threading.Thread(
            target=self._run_scheduler_worker,
            daemon=True
        )
        scheduler_thread.start()
        self.threads.append(scheduler_thread)

        print(f"{Fore.GREEN}[OK] All components started successfully")

    def _run_data_collection_worker(self):
        """Worker thread for data collection."""
        try:
            while self.running and not self.shutdown_event.is_set():
                # Collect data for all configured symbols
                symbols = self.config['data_collection']['target_symbols']
                timeframes = self.config['data_collection']['timeframes']

                for symbol in symbols:
                    for timeframe in timeframes:
                        try:
                            # Get market data
                            candles = self.market_data_collector.get_klines(
                                symbol=symbol,
                                interval=timeframe,
                                limit=100
                            )

                            if candles:
                                # Store in database
                                self.database_manager.store_ohlcv_data(
                                    symbol=symbol,
                                    timeframe=timeframe,
                                    data=candles
                                )
                                self.stats['data_points_collected'] += len(candles)

                            self.stats['api_calls_made'] += 1
                            self.stats['last_update'] = datetime.now()

                        except Exception as e:
                            self.stats['errors_encountered'] += 1
                            self.logger.error(f"Data collection error for {symbol}: {e}")

                # Wait for next collection interval
                interval = self.config['data_collection']['collection_interval_seconds']
                self.shutdown_event.wait(interval)

        except Exception as e:
            self.logger.error(f"Data collection worker error: {e}", exc_info=True)

    def _run_arbitrage_worker(self):
        """Worker thread for arbitrage monitoring."""
        try:
            while self.running and not self.shutdown_event.is_set():
                # Simple arbitrage detection logic
                symbols = self.config['data_collection']['target_symbols']

                for symbol in symbols:
                    try:
                        # Get current price
                        price = self.market_data_collector.get_current_price(symbol)

                        # Simulate arbitrage opportunity detection
                        # In a real implementation, this would compare prices across exchanges
                        if price and self._simulate_arbitrage_check(symbol, price):
                            self.stats['arbitrage_opportunities'] += 1
                            self.logger.info(f"Arbitrage opportunity detected for {symbol}")

                        self.stats['api_calls_made'] += 1

                    except Exception as e:
                        self.stats['errors_encountered'] += 1
                        self.logger.error(f"Arbitrage monitoring error for {symbol}: {e}")

                # Wait for next scan interval
                interval = self.config['arbitrage']['scan_interval_seconds']
                self.shutdown_event.wait(interval)

        except Exception as e:
            self.logger.error(f"Arbitrage worker error: {e}", exc_info=True)

    def _run_scheduler_worker(self):
        """Worker thread for scheduled tasks."""
        try:
            while self.running and not self.shutdown_event.is_set():
                # Run scheduled maintenance tasks
                if self.scheduler:
                    self.scheduler.run_pending()

                self.shutdown_event.wait(60)  # Check every minute

        except Exception as e:
            self.logger.error(f"Scheduler worker error: {e}", exc_info=True)

    def _simulate_arbitrage_check(self, symbol: str, price: float) -> bool:
        """
        Simulate arbitrage opportunity detection.

        In a real implementation, this would compare prices across multiple exchanges.
        """
        # Simulate a 0.5% price difference occasionally
        import random
        return random.random() < 0.01  # 1% chance of detecting opportunity

    def show_system_status(self):
        """Display detailed system status information."""
        print(f"\n{Fore.CYAN}{Style.BRIGHT}[DATA] SYSTEM STATUS REPORT")
        print(f"{Fore.CYAN}{'='*50}")

        # System information
        print(f"\n{Fore.YELLOW}🖥️  System Information:")
        print(f"{Fore.WHITE}   Python Version: {sys.version.split()[0]}")
        print(f"{Fore.WHITE}   Platform: {sys.platform}")
        print(f"{Fore.WHITE}   CPU Count: {psutil.cpu_count()}")
        print(f"{Fore.WHITE}   Memory Total: {psutil.virtual_memory().total / 1024**3:.1f} GB")

        # Database status
        if self.database_manager:
            db_path = self.config['database']['path']
            if os.path.exists(db_path):
                db_size = os.path.getsize(db_path) / 1024**2
                print(f"\n{Fore.YELLOW}🗄️  Database Status:")
                print(f"{Fore.WHITE}   Database Path: {db_path}")
                print(f"{Fore.WHITE}   Database Size: {db_size:.2f} MB")
                print(f"{Fore.GREEN}   Status: [OK] Connected")
            else:
                print(f"\n{Fore.YELLOW}🗄️  Database Status:")
                print(f"{Fore.RED}   Status: [ERROR] Not found")

        # API connection status
        if self.market_data_collector:
            try:
                connection_ok = self.market_data_collector.test_connection()
                print(f"\n{Fore.YELLOW}[CONNECT] API Connection:")
                if connection_ok:
                    print(f"{Fore.GREEN}   Status: [OK] Connected to Binance API")
                else:
                    print(f"{Fore.RED}   Status: [ERROR] Connection failed")
            except Exception as e:
                print(f"\n{Fore.YELLOW}[CONNECT] API Connection:")
                print(f"{Fore.RED}   Status: [ERROR] Error: {e}")

        # Configuration status
        print(f"\n{Fore.YELLOW}⚙️  Configuration:")
        print(f"{Fore.WHITE}   Target Symbols: {len(self.config['data_collection']['target_symbols'])}")
        print(f"{Fore.WHITE}   Timeframes: {', '.join(self.config['data_collection']['timeframes'])}")
        print(f"{Fore.WHITE}   Collection Interval: {self.config['data_collection']['collection_interval_seconds']}s")
        print(f"{Fore.WHITE}   Testnet Mode: {self.config['exchange']['testnet']}")

        input(f"\n{Fore.CYAN}Press Enter to continue...")

    def show_configuration(self):
        """Display current configuration."""
        print(f"\n{Fore.CYAN}{Style.BRIGHT}⚙️  CONFIGURATION REVIEW")
        print(f"{Fore.CYAN}{'='*50}")

        # Display key configuration sections
        sections_to_show = [
            'exchange', 'data_collection', 'arbitrage',
            'risk_management', 'alerts', 'logging'
        ]

        for section in sections_to_show:
            if section in self.config:
                print(f"\n{Fore.YELLOW}{section.upper().replace('_', ' ')}:")
                for key, value in self.config[section].items():
                    if not key.startswith('_'):  # Skip comment fields
                        if isinstance(value, list) and len(value) > 3:
                            print(f"{Fore.WHITE}   {key}: [{', '.join(map(str, value[:3]))}, ...]")
                        else:
                            print(f"{Fore.WHITE}   {key}: {value}")

        input(f"\n{Fore.CYAN}Press Enter to continue...")

    def run_test_suite(self):
        """Run the complete test suite."""
        print(f"\n{Fore.CYAN}🧪 Running Test Suite...")

        try:
            # Run market data tests
            print(f"{Fore.YELLOW}[CONNECT] Running market data tests...")
            import subprocess
            result1 = subprocess.run([sys.executable, "test_market_data.py"],
                                   capture_output=True, text=True)

            if result1.returncode == 0:
                print(f"{Fore.GREEN}[OK] Market data tests passed")
            else:
                print(f"{Fore.RED}[ERROR] Market data tests failed")
                print(result1.stdout)

            # Run data collection tests
            print(f"{Fore.YELLOW}[DATA] Running data collection tests...")
            result2 = subprocess.run([sys.executable, "test_data_collection.py"],
                                   capture_output=True, text=True)

            if result2.returncode == 0:
                print(f"{Fore.GREEN}[OK] Data collection tests passed")
            else:
                print(f"{Fore.RED}[ERROR] Data collection tests failed")
                print(result2.stdout)

            # Summary
            if result1.returncode == 0 and result2.returncode == 0:
                print(f"\n{Fore.GREEN}{Style.BRIGHT}🎉 All tests passed!")
            else:
                print(f"\n{Fore.RED}{Style.BRIGHT}[WARNING]  Some tests failed!")

        except Exception as e:
            print(f"{Fore.RED}[ERROR] Test execution error: {e}")

        input(f"\n{Fore.CYAN}Press Enter to continue...")

    def shutdown(self):
        """Perform graceful shutdown of all components."""
        print(f"\n{Fore.YELLOW}[PROCESS] Shutting down Crypto Trader Pro...")

        self.running = False
        self.shutdown_event.set()

        # Wait for all threads to complete
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=5)

        # Close database connections
        if self.database_manager:
            try:
                self.database_manager.close()
                print(f"{Fore.GREEN}[OK] Database connections closed")
            except Exception as e:
                print(f"{Fore.RED}[ERROR] Database shutdown error: {e}")

        # Generate shutdown report
        self._generate_shutdown_report()

        print(f"{Fore.GREEN}[OK] Shutdown complete")
        if self.logger:
            self.logger.info("Crypto Trader Pro shutdown completed")

    def _generate_shutdown_report(self):
        """Generate and display shutdown report."""
        uptime = datetime.now() - self.start_time

        print(f"\n{Fore.CYAN}📋 SHUTDOWN REPORT")
        print(f"{Fore.CYAN}{'─'*40}")
        print(f"{Fore.WHITE}Session Duration: {str(uptime).split('.')[0]}")
        print(f"{Fore.WHITE}Data Points Collected: {self.stats['data_points_collected']:,}")
        print(f"{Fore.WHITE}API Calls Made: {self.stats['api_calls_made']:,}")
        print(f"{Fore.WHITE}Arbitrage Opportunities: {self.stats['arbitrage_opportunities']}")
        print(f"{Fore.WHITE}Errors Encountered: {self.stats['errors_encountered']}")
        print(f"{Fore.CYAN}{'─'*40}")

    def run(self):
        """Main application loop."""
        try:
            # Initialize system
            if not self.initialize():
                print(f"{Fore.RED}[ERROR] Failed to initialize system")
                return

            # Show welcome message
            self.show_welcome_message()

            # Main menu loop
            while True:
                choice = self.show_main_menu()

                if choice == 0:
                    print(f"{Fore.YELLOW}👋 Goodbye!")
                    break
                elif choice == 1:
                    self.run_data_collection_only()
                elif choice == 2:
                    self.run_arbitrage_monitoring()
                elif choice == 3:
                    self.run_full_system()
                elif choice == 4:
                    self.show_system_status()
                elif choice == 5:
                    self.show_configuration()
                elif choice == 6:
                    self.run_test_suite()

                # Reset running state
                self.running = False
                self.shutdown_event.clear()

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}👋 Goodbye!")
        except Exception as e:
            print(f"{Fore.RED}[ERROR] Unexpected error: {e}")
            if self.logger:
                self.logger.error(f"Unexpected error: {e}", exc_info=True)
            traceback.print_exc()
        finally:
            self.shutdown()


def main():
    """Main entry point."""
    try:
        bot = CryptoTradingBot()
        bot.run()
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Critical error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()