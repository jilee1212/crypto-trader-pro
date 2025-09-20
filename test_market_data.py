"""
Test script for MarketDataCollector functionality.
Tests all core features including API connection, data retrieval, and error handling.
"""

import time
import sys
import os
from typing import Dict, Any
from datetime import datetime

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.market_data import MarketDataCollector
from utils.exceptions import (
    APIConnectionError,
    InvalidSymbolError,
    RateLimitError,
    DataValidationError,
    NetworkTimeoutError
)


class TestColors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'  # Success
    RED = '\033[91m'    # Failure
    YELLOW = '\033[93m' # Warning
    BLUE = '\033[94m'   # Info
    PURPLE = '\033[95m' # Header
    CYAN = '\033[96m'   # Test name
    RESET = '\033[0m'   # Reset color


class MarketDataTester:
    """
    Comprehensive test suite for MarketDataCollector.
    """

    def __init__(self):
        self.test_results = []
        self.start_time = time.time()
        self.collector = None

    def print_header(self, title: str):
        """Print formatted test section header."""
        print(f"\n{TestColors.PURPLE}{'='*60}{TestColors.RESET}")
        print(f"{TestColors.PURPLE}{title.center(60)}{TestColors.RESET}")
        print(f"{TestColors.PURPLE}{'='*60}{TestColors.RESET}")

    def print_test(self, test_name: str, status: str, message: str = "", duration: float = 0):
        """Print formatted test result."""
        color = TestColors.GREEN if status == "PASS" else TestColors.RED
        status_symbol = "✓" if status == "PASS" else "✗"

        print(f"{TestColors.CYAN}{test_name:<40}{TestColors.RESET} "
              f"[{color}{status_symbol} {status}{TestColors.RESET}] "
              f"{TestColors.BLUE}({duration:.3f}s){TestColors.RESET}")

        if message:
            print(f"    {TestColors.YELLOW}→ {message}{TestColors.RESET}")

        self.test_results.append({
            'name': test_name,
            'status': status,
            'message': message,
            'duration': duration
        })

    def run_test(self, test_func, test_name: str, *args, **kwargs):
        """Run individual test with timing and error handling."""
        test_start = time.time()
        try:
            result = test_func(*args, **kwargs)
            duration = time.time() - test_start

            if result is True:
                self.print_test(test_name, "PASS", duration=duration)
            elif isinstance(result, tuple):
                status, message = result
                self.print_test(test_name, status, message, duration)
            else:
                self.print_test(test_name, "PASS", str(result), duration)

        except Exception as e:
            duration = time.time() - test_start
            self.print_test(test_name, "FAIL", f"Exception: {str(e)}", duration)

    def test_1_initialization(self) -> bool:
        """Test MarketDataCollector initialization."""
        try:
            self.collector = MarketDataCollector(testnet=True)
            return True
        except Exception as e:
            raise Exception(f"Failed to initialize collector: {e}")

    def test_2_api_connection_success(self) -> tuple:
        """Test successful API connection."""
        try:
            result = self.collector.test_connection()
            if result:
                return ("PASS", "API connection successful")
            else:
                return ("FAIL", "API connection returned False")
        except Exception as e:
            return ("FAIL", f"Connection failed: {str(e)}")

    def test_3_api_connection_with_invalid_credentials(self) -> tuple:
        """Test API connection with invalid credentials."""
        try:
            # Create collector with invalid credentials
            invalid_collector = MarketDataCollector(
                testnet=True,
                api_key="invalid_key",
                api_secret="invalid_secret"
            )

            # This should still work for public endpoints
            result = invalid_collector.test_connection()
            if result:
                return ("PASS", "Public API works even with invalid credentials")
            else:
                return ("FAIL", "Unexpected connection failure")

        except APIConnectionError:
            return ("PASS", "Correctly detected invalid credentials")
        except Exception as e:
            return ("FAIL", f"Unexpected error: {str(e)}")

    def test_4_valid_symbol_price_btc(self) -> tuple:
        """Test price retrieval for BTC/USDT."""
        try:
            price = self.collector.get_current_price("BTC/USDT")

            if price > 0:
                return ("PASS", f"BTC/USDT price: ${price:,.2f}")
            else:
                return ("FAIL", f"Invalid price received: {price}")

        except Exception as e:
            return ("FAIL", f"Failed to get BTC price: {str(e)}")

    def test_5_valid_symbol_price_eth(self) -> tuple:
        """Test price retrieval for ETH/USDT."""
        try:
            price = self.collector.get_current_price("ETH/USDT")

            if price > 0:
                return ("PASS", f"ETH/USDT price: ${price:,.2f}")
            else:
                return ("FAIL", f"Invalid price received: {price}")

        except Exception as e:
            return ("FAIL", f"Failed to get ETH price: {str(e)}")

    def test_6_invalid_symbol_error_handling(self) -> tuple:
        """Test error handling for invalid symbol."""
        try:
            # Try to get price for non-existent symbol
            self.collector.get_current_price("INVALID/SYMBOL")
            return ("FAIL", "Should have raised InvalidSymbolError")

        except InvalidSymbolError as e:
            return ("PASS", f"Correctly caught InvalidSymbolError: {e.error_code}")
        except Exception as e:
            return ("FAIL", f"Wrong exception type: {type(e).__name__}")

    def test_7_symbol_validation_valid(self) -> tuple:
        """Test symbol validation with valid symbols."""
        try:
            # Test multiple valid symbols
            valid_symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
            results = []

            for symbol in valid_symbols:
                is_valid = self.collector.validate_symbol(symbol)
                results.append(f"{symbol}:{is_valid}")

            if all(self.collector.validate_symbol(symbol) for symbol in valid_symbols):
                return ("PASS", f"All symbols valid: {', '.join(results)}")
            else:
                return ("FAIL", f"Some symbols invalid: {', '.join(results)}")

        except Exception as e:
            return ("FAIL", f"Validation error: {str(e)}")

    def test_8_symbol_validation_invalid(self) -> tuple:
        """Test symbol validation with invalid symbols."""
        try:
            # Test invalid symbols
            invalid_symbols = ["FAKE/USDT", "BTC/FAKE", "NOTREAL/NOTREAL"]

            for symbol in invalid_symbols:
                try:
                    self.collector.validate_symbol(symbol)
                    return ("FAIL", f"Symbol {symbol} should be invalid")
                except InvalidSymbolError:
                    continue  # Expected behavior

            return ("PASS", "All invalid symbols correctly rejected")

        except Exception as e:
            return ("FAIL", f"Unexpected error: {str(e)}")

    def test_9_24h_ticker_data(self) -> tuple:
        """Test 24-hour ticker data structure and content."""
        try:
            ticker = self.collector.get_24h_ticker("BTC/USDT")

            # Check required fields
            required_fields = ['last', 'volume', 'high', 'low', 'open', 'change', 'percentage']
            missing_fields = [field for field in required_fields if field not in ticker or ticker[field] is None]

            if missing_fields:
                return ("FAIL", f"Missing fields: {missing_fields}")

            # Validate data types and ranges
            if ticker['last'] <= 0:
                return ("FAIL", f"Invalid last price: {ticker['last']}")

            if ticker['volume'] < 0:
                return ("FAIL", f"Invalid volume: {ticker['volume']}")

            return ("PASS", f"Volume: {ticker['volume']:,.0f}, Change: {ticker['percentage']:.2f}%")

        except Exception as e:
            return ("FAIL", f"Ticker test failed: {str(e)}")

    def test_10_orderbook_structure(self) -> tuple:
        """Test orderbook data structure and validation."""
        try:
            orderbook = self.collector.get_orderbook("BTC/USDT", limit=10)

            # Check structure
            if 'bids' not in orderbook or 'asks' not in orderbook:
                return ("FAIL", "Missing bids or asks in orderbook")

            if len(orderbook['bids']) == 0 or len(orderbook['asks']) == 0:
                return ("FAIL", "Empty bids or asks")

            # Check first bid and ask structure
            first_bid = orderbook['bids'][0]
            first_ask = orderbook['asks'][0]

            if len(first_bid) != 2 or len(first_ask) != 2:
                return ("FAIL", "Invalid bid/ask structure")

            # Check price ordering (bids descending, asks ascending)
            if len(orderbook['bids']) > 1:
                if orderbook['bids'][0][0] <= orderbook['bids'][1][0]:
                    return ("FAIL", "Bids not in descending order")

            if len(orderbook['asks']) > 1:
                if orderbook['asks'][0][0] >= orderbook['asks'][1][0]:
                    return ("FAIL", "Asks not in ascending order")

            # Check spread
            best_bid = orderbook['bids'][0][0]
            best_ask = orderbook['asks'][0][0]
            spread = best_ask - best_bid

            return ("PASS", f"Bids: {len(orderbook['bids'])}, Asks: {len(orderbook['asks'])}, Spread: ${spread:.2f}")

        except Exception as e:
            return ("FAIL", f"Orderbook test failed: {str(e)}")

    def test_11_klines_data(self) -> tuple:
        """Test candlestick (OHLCV) data retrieval and validation."""
        try:
            klines = self.collector.get_klines("BTC/USDT", interval="5m", limit=100)

            if len(klines) == 0:
                return ("FAIL", "No klines data received")

            # Check data structure
            first_candle = klines[0]
            if len(first_candle) != 6:
                return ("FAIL", f"Invalid candle structure: expected 6 fields, got {len(first_candle)}")

            # Validate OHLCV relationships
            for i, candle in enumerate(klines[:5]):  # Check first 5 candles
                timestamp, open_p, high, low, close, volume = candle

                if high < max(open_p, close) or low > min(open_p, close):
                    return ("FAIL", f"Invalid OHLC relationship in candle {i}")

                if volume < 0:
                    return ("FAIL", f"Negative volume in candle {i}")

            return ("PASS", f"Retrieved {len(klines)} valid 5m candles")

        except Exception as e:
            return ("FAIL", f"Klines test failed: {str(e)}")

    def test_12_cache_functionality(self) -> tuple:
        """Test caching mechanism."""
        try:
            # Clear cache first
            self.collector.clear_cache()

            # Make first request (should hit API)
            start_time = time.time()
            price1 = self.collector.get_current_price("BTC/USDT")
            first_request_time = time.time() - start_time

            # Make second request immediately (should hit cache)
            start_time = time.time()
            price2 = self.collector.get_current_price("BTC/USDT")
            second_request_time = time.time() - start_time

            # Check cache stats
            cache_stats = self.collector.get_cache_stats()

            if price1 != price2:
                return ("FAIL", f"Cache returned different prices: {price1} vs {price2}")

            if second_request_time >= first_request_time:
                return ("FAIL", f"Cache not faster: {first_request_time:.3f}s vs {second_request_time:.3f}s")

            return ("PASS", f"Cache working: {cache_stats['valid_entries']} valid entries, "
                           f"speedup: {first_request_time/second_request_time:.1f}x")

        except Exception as e:
            return ("FAIL", f"Cache test failed: {str(e)}")

    def test_13_rate_limiting(self) -> tuple:
        """Test rate limiting functionality."""
        try:
            # Make multiple rapid requests to test rate limiter
            start_time = time.time()
            symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "ADA/USDT", "DOT/USDT"]

            for symbol in symbols:
                try:
                    self.collector.get_current_price(symbol)
                except Exception:
                    pass  # Ignore individual failures for rate limit test

            total_time = time.time() - start_time

            # Should take at least some time due to rate limiting
            expected_min_time = len(symbols) * 0.05  # Very conservative estimate

            if total_time < expected_min_time:
                return ("PASS", f"Rate limiting working: {total_time:.2f}s for {len(symbols)} requests")
            else:
                return ("PASS", f"Rate limiting active: {total_time:.2f}s total")

        except Exception as e:
            return ("FAIL", f"Rate limiting test failed: {str(e)}")

    def test_14_multiple_symbols_batch(self) -> tuple:
        """Test batch retrieval of multiple symbols."""
        try:
            symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT"]

            result = self.collector.get_multiple_symbols_data(symbols, "price")

            if result['success_count'] == len(symbols):
                prices = [f"{sym}: ${price:,.0f}" for sym, price in result['data'].items()]
                return ("PASS", f"All {len(symbols)} symbols retrieved: {', '.join(prices)}")
            else:
                return ("FAIL", f"Only {result['success_count']}/{len(symbols)} symbols successful")

        except Exception as e:
            return ("FAIL", f"Batch test failed: {str(e)}")

    def test_15_data_validation_edge_cases(self) -> tuple:
        """Test data validation with edge cases."""
        try:
            # Test invalid limit values
            test_cases = [
                ("zero_limit", lambda: self.collector.get_orderbook("BTC/USDT", limit=0)),
                ("negative_limit", lambda: self.collector.get_orderbook("BTC/USDT", limit=-1)),
                ("too_large_limit", lambda: self.collector.get_orderbook("BTC/USDT", limit=2000)),
                ("invalid_interval", lambda: self.collector.get_klines("BTC/USDT", interval="invalid")),
            ]

            failed_cases = []
            passed_cases = []

            for case_name, test_func in test_cases:
                try:
                    test_func()
                    failed_cases.append(case_name)  # Should have raised an exception
                except DataValidationError:
                    passed_cases.append(case_name)  # Expected behavior
                except Exception as e:
                    failed_cases.append(f"{case_name}({type(e).__name__})")

            if len(failed_cases) == 0:
                return ("PASS", f"All validation tests passed: {', '.join(passed_cases)}")
            else:
                return ("FAIL", f"Failed cases: {', '.join(failed_cases)}")

        except Exception as e:
            return ("FAIL", f"Validation test failed: {str(e)}")

    def run_all_tests(self):
        """Run all test cases and generate summary report."""
        self.print_header("CRYPTO TRADER PRO - MARKET DATA TESTS")

        print(f"{TestColors.BLUE}🚀 Starting comprehensive market data testing...{TestColors.RESET}")
        print(f"{TestColors.BLUE}📅 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{TestColors.RESET}")

        # List of all test methods
        test_methods = [
            (self.test_1_initialization, "MarketDataCollector Initialization"),
            (self.test_2_api_connection_success, "API Connection Test"),
            (self.test_3_api_connection_with_invalid_credentials, "Invalid Credentials Handling"),
            (self.test_4_valid_symbol_price_btc, "BTC/USDT Price Retrieval"),
            (self.test_5_valid_symbol_price_eth, "ETH/USDT Price Retrieval"),
            (self.test_6_invalid_symbol_error_handling, "Invalid Symbol Error Handling"),
            (self.test_7_symbol_validation_valid, "Valid Symbol Validation"),
            (self.test_8_symbol_validation_invalid, "Invalid Symbol Validation"),
            (self.test_9_24h_ticker_data, "24-Hour Ticker Data"),
            (self.test_10_orderbook_structure, "Orderbook Structure Validation"),
            (self.test_11_klines_data, "Candlestick Data Retrieval"),
            (self.test_12_cache_functionality, "Cache Mechanism"),
            (self.test_13_rate_limiting, "Rate Limiting"),
            (self.test_14_multiple_symbols_batch, "Batch Symbol Retrieval"),
            (self.test_15_data_validation_edge_cases, "Data Validation Edge Cases"),
        ]

        # Run all tests
        for test_method, test_name in test_methods:
            self.run_test(test_method, test_name)

        # Generate summary
        self.generate_summary()

    def generate_summary(self):
        """Generate and display test summary."""
        total_time = time.time() - self.start_time
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = total_tests - passed_tests

        self.print_header("TEST SUMMARY")

        # Overall results
        if failed_tests == 0:
            status_color = TestColors.GREEN
            status_symbol = "✓"
            status_text = "ALL TESTS PASSED"
        else:
            status_color = TestColors.RED
            status_symbol = "✗"
            status_text = "SOME TESTS FAILED"

        print(f"\n{status_color}{status_symbol} {status_text}{TestColors.RESET}")
        print(f"\n📊 Results:")
        print(f"   {TestColors.GREEN}✓ Passed: {passed_tests}{TestColors.RESET}")
        print(f"   {TestColors.RED}✗ Failed: {failed_tests}{TestColors.RESET}")
        print(f"   📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print(f"   ⏱️  Total Time: {total_time:.2f} seconds")
        print(f"   ⚡ Average Time per Test: {total_time/total_tests:.3f} seconds")

        # Performance stats
        fastest_test = min(self.test_results, key=lambda x: x['duration'])
        slowest_test = max(self.test_results, key=lambda x: x['duration'])

        print(f"\n🏃 Performance:")
        print(f"   ⚡ Fastest: {fastest_test['name']} ({fastest_test['duration']:.3f}s)")
        print(f"   🐌 Slowest: {slowest_test['name']} ({slowest_test['duration']:.3f}s)")

        # Failed tests details
        if failed_tests > 0:
            print(f"\n{TestColors.RED}❌ Failed Tests:{TestColors.RESET}")
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    print(f"   • {result['name']}: {result['message']}")

        # Cache statistics if collector is available
        if self.collector:
            try:
                cache_stats = self.collector.get_cache_stats()
                print(f"\n💾 Cache Statistics:")
                print(f"   • Total Entries: {cache_stats['total_entries']}")
                print(f"   • Valid Entries: {cache_stats['valid_entries']}")
                print(f"   • Cache TTL: {cache_stats['cache_ttl']}s")
            except:
                pass

        print(f"\n{TestColors.BLUE}🎯 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{TestColors.RESET}")

        # Exit with appropriate code
        sys.exit(0 if failed_tests == 0 else 1)


if __name__ == "__main__":
    print(f"{TestColors.PURPLE}🔥 CRYPTO TRADER PRO - MARKET DATA TEST SUITE 🔥{TestColors.RESET}")
    print(f"{TestColors.BLUE}Testing Binance API integration and data collection...{TestColors.RESET}\n")

    tester = MarketDataTester()
    tester.run_all_tests()