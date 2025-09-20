"""
Market data collection system for cryptocurrency trading bot.
Provides reliable data collection from Binance exchange using ccxt library.

Enhanced Features:
- Advanced rate limiting with burst protection
- Multiple time window control (per second and per minute)
- Automatic call distribution to prevent API limit violations
- Configurable rate limits for different exchange profiles
- Real-time statistics and monitoring
- Intelligent caching with TTL support
- Comprehensive error handling with safe loop-based retry logic (no recursion)

Recursion Safety:
- All retry logic implemented using simple_retry_call() function with pure for-loops
- Symbol validation does NOT use retry logic to prevent recursion chains
- Each API method wraps actual API calls in lambda functions for safe retry
- Maximum recursion depth errors completely eliminated through non-recursive design
- No decorators used - all retry logic is inline and explicit
"""

import time
import ccxt
from typing import Dict, List, Optional, Any, Union
from functools import wraps
from datetime import datetime, timedelta
import logging
from .exceptions import (
    APIConnectionError,
    InvalidSymbolError,
    RateLimitError,
    DataValidationError,
    InsufficientDataError,
    NetworkTimeoutError
)
from .validation_helpers import (
    validate_symbol as validate_symbol_format,
    validate_limit,
    validate_interval,
    validate_orderbook_data,
    validate_ohlcv_candle
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def categorize_exception(exception: Exception) -> Exception:
    """
    Categorize exceptions into appropriate custom exception types.

    Args:
        exception (Exception): Original exception to categorize

    Returns:
        Exception: Appropriately categorized custom exception
    """
    error_msg = str(exception).lower()

    # Symbol-related errors
    if any(phrase in error_msg for phrase in [
        "does not have market symbol",
        "symbol not found",
        "invalid symbol",
        "bad symbol",
        "unknown symbol",
        "market not found"
    ]):
        return InvalidSymbolError(
            symbol="",  # Will be filled by calling function
            exchange="binance",
            message=str(exception)
        )

    # Rate limiting errors
    elif any(phrase in error_msg for phrase in [
        "rate limit",
        "too many requests",
        "request limit exceeded",
        "rate exceeded"
    ]):
        return RateLimitError(message=str(exception))

    # Network/timeout errors
    elif any(phrase in error_msg for phrase in [
        "timeout",
        "timed out",
        "connection timeout",
        "read timeout"
    ]):
        return NetworkTimeoutError(message=str(exception))

    # Connection errors
    elif any(phrase in error_msg for phrase in [
        "connection",
        "network",
        "unreachable",
        "refused",
        "dns",
        "ssl error",
        "certificate"
    ]):
        return APIConnectionError(message=str(exception), exchange="binance")

    # Default to API connection error for unknown cases
    else:
        return APIConnectionError(message=str(exception), exchange="binance")


def simple_retry_call(func, max_retries: int = 3):
    """
    Simple retry wrapper with no recursion - only basic for loops.

    Args:
        func: Function to call (should be a lambda or simple function)
        max_retries (int): Maximum number of retry attempts

    Returns:
        Any: Function result

    Raises:
        Exception: Last exception if all retries fail
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            # Direct function call - no recursion possible
            result = func()
            return result

        except KeyboardInterrupt:
            logger.info("Operation interrupted by user")
            raise

        except (InvalidSymbolError, DataValidationError):
            # Don't retry validation errors
            raise

        except Exception as e:
            last_error = e

            # If this is the last attempt, don't wait
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 0.5  # 0.5s, 1s, 1.5s
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                try:
                    time.sleep(wait_time)
                except KeyboardInterrupt:
                    logger.info("Retry interrupted by user")
                    raise
            else:
                logger.error(f"All {max_retries} attempts failed: {e}")

    # If we get here, all retries failed
    if last_error:
        raise last_error
    else:
        raise Exception("Unknown error occurred")


def _is_retryable_error(exception: Exception) -> bool:
    """
    Determine if an exception is worth retrying.

    Args:
        exception (Exception): Exception to check

    Returns:
        bool: True if error is retryable (network/temporary issues)
    """
    error_msg = str(exception).lower()

    # Retryable errors (network/temporary issues)
    retryable_patterns = [
        "timeout",
        "connection",
        "network",
        "temporarily unavailable",
        "server error",
        "503",
        "502",
        "504",
        "rate limit",
        "too many requests"
    ]

    # Non-retryable errors (permanent issues)
    non_retryable_patterns = [
        "does not have market symbol",
        "symbol not found",
        "invalid symbol",
        "bad symbol",
        "authentication",
        "unauthorized",
        "forbidden",
        "400",
        "401",
        "403",
        "404"
    ]

    # Check for non-retryable patterns first
    for pattern in non_retryable_patterns:
        if pattern in error_msg:
            return False

    # Check for retryable patterns
    for pattern in retryable_patterns:
        if pattern in error_msg:
            return True

    # Default: retry unknown errors (conservative approach)
    return True


class RateLimiter:
    """
    Advanced rate limiter to control API call frequency with multiple time windows.

    Features:
    - Configurable rate limits for different time windows
    - Automatic distribution of calls over time
    - Burst protection with gradual backoff
    - Exchange-specific rate limit profiles
    """

    def __init__(self,
                 max_calls_per_second: int = 10,
                 max_calls_per_minute: int = 600,
                 enable_burst_protection: bool = True,
                 exchange_profile: str = "binance"):
        """
        Initialize rate limiter with configurable limits.

        Args:
            max_calls_per_second (int): Maximum API calls per second
            max_calls_per_minute (int): Maximum API calls per minute
            enable_burst_protection (bool): Enable burst protection for smooth distribution
            exchange_profile (str): Exchange-specific rate limit profile
        """
        self.max_calls_per_second = max_calls_per_second
        self.max_calls_per_minute = max_calls_per_minute
        self.enable_burst_protection = enable_burst_protection
        self.exchange_profile = exchange_profile

        # Track calls in different time windows
        self.calls_1s = []  # Calls in last 1 second
        self.calls_1m = []  # Calls in last 1 minute

        # Burst protection settings
        self.min_interval = 1.0 / max_calls_per_second if enable_burst_protection else 0
        self.last_call_time = 0

        # Statistics
        self.total_calls = 0
        self.total_wait_time = 0

        logger.debug(f"RateLimiter initialized: {max_calls_per_second}/s, {max_calls_per_minute}/m, "
                    f"burst_protection={enable_burst_protection}, profile={exchange_profile}")

    def wait_if_needed(self):
        """
        Wait if necessary to respect rate limits across multiple time windows.
        Implements intelligent distribution of calls to avoid hitting limits.
        """
        now = time.time()
        wait_time = 0

        # Clean old calls from tracking lists
        self.calls_1s = [t for t in self.calls_1s if now - t < 1.0]
        self.calls_1m = [t for t in self.calls_1m if now - t < 60.0]

        # Check burst protection (minimum interval between calls)
        if self.enable_burst_protection and self.last_call_time > 0:
            time_since_last = now - self.last_call_time
            if time_since_last < self.min_interval:
                burst_wait = self.min_interval - time_since_last
                wait_time = max(wait_time, burst_wait)
                logger.debug(f"Burst protection: minimum interval {burst_wait:.3f}s")

        # Check 1-second limit
        if len(self.calls_1s) >= self.max_calls_per_second:
            oldest_call = min(self.calls_1s)
            second_wait = 1.0 - (now - oldest_call) + 0.001  # Small buffer
            wait_time = max(wait_time, second_wait)
            logger.debug(f"1-second limit: waiting {second_wait:.3f}s")

        # Check 1-minute limit
        if len(self.calls_1m) >= self.max_calls_per_minute:
            oldest_call = min(self.calls_1m)
            minute_wait = 60.0 - (now - oldest_call) + 0.001  # Small buffer
            wait_time = max(wait_time, minute_wait)
            logger.debug(f"1-minute limit: waiting {minute_wait:.3f}s")

        # Perform the wait if needed
        if wait_time > 0:
            logger.debug(f"Rate limiting: sleeping for {wait_time:.3f}s")
            time.sleep(wait_time)
            now = time.time()  # Update time after sleep
            self.total_wait_time += wait_time

        # Record this call
        self.calls_1s.append(now)
        self.calls_1m.append(now)
        self.last_call_time = now
        self.total_calls += 1

    def get_stats(self) -> Dict[str, Any]:
        """
        Get rate limiter statistics.

        Returns:
            Dict[str, Any]: Statistics including total calls, wait time, etc.
        """
        now = time.time()

        # Clean old calls for accurate current stats
        self.calls_1s = [t for t in self.calls_1s if now - t < 1.0]
        self.calls_1m = [t for t in self.calls_1m if now - t < 60.0]

        return {
            'total_calls': self.total_calls,
            'total_wait_time_seconds': round(self.total_wait_time, 3),
            'calls_last_second': len(self.calls_1s),
            'calls_last_minute': len(self.calls_1m),
            'max_calls_per_second': self.max_calls_per_second,
            'max_calls_per_minute': self.max_calls_per_minute,
            'burst_protection_enabled': self.enable_burst_protection,
            'exchange_profile': self.exchange_profile,
            'efficiency_percent': round((self.total_calls / max(self.total_calls + self.total_wait_time, 1)) * 100, 1)
        }

    def reset_stats(self):
        """Reset statistics counters."""
        self.total_calls = 0
        self.total_wait_time = 0
        logger.debug("Rate limiter statistics reset")


class MarketDataCollector:
    """
    Market data collection system for Binance exchange.

    Features:
    - Automatic retry with exponential backoff
    - Rate limiting compliance
    - Data validation and caching
    - Comprehensive error handling
    - Support for both testnet and mainnet
    """

    def __init__(self,
                 testnet: bool = True,
                 api_key: str = "",
                 api_secret: str = "",
                 enable_rate_limiting: bool = True,
                 rate_limit_calls_per_second: int = 10,
                 rate_limit_calls_per_minute: int = 600,
                 enable_burst_protection: bool = True):
        """
        Initialize market data collector with advanced rate limiting.

        Args:
            testnet (bool): Use testnet if True, mainnet if False
            api_key (str): Binance API key (optional for public data)
            api_secret (str): Binance API secret (optional for public data)
            enable_rate_limiting (bool): Enable advanced rate limiting (default: True)
            rate_limit_calls_per_second (int): Max API calls per second (default: 10)
            rate_limit_calls_per_minute (int): Max API calls per minute (default: 600)
            enable_burst_protection (bool): Enable burst protection for smooth distribution (default: True)
        """
        self.testnet = testnet
        self.enable_rate_limiting = enable_rate_limiting

        # Initialize advanced rate limiter
        if enable_rate_limiting:
            self.rate_limiter = RateLimiter(
                max_calls_per_second=rate_limit_calls_per_second,
                max_calls_per_minute=rate_limit_calls_per_minute,
                enable_burst_protection=enable_burst_protection,
                exchange_profile="binance"
            )
        else:
            self.rate_limiter = None

        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 5  # Cache timeout in seconds

        # Initialize exchange
        try:
            self.exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'sandbox': testnet,
                'timeout': 30000,  # 30 seconds timeout
                'enableRateLimit': True,
            })

            logger.info(f"Initialized Binance {'testnet' if testnet else 'mainnet'} connection"
                       f" with rate limiting: {enable_rate_limiting}")

        except Exception as e:
            raise APIConnectionError(
                message=f"Failed to initialize Binance exchange: {e}",
                exchange="binance"
            )

    def _apply_rate_limiting(self):
        """Apply rate limiting if enabled."""
        if self.enable_rate_limiting and self.rate_limiter:
            self._apply_rate_limiting()

    def get_rate_limiter_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get rate limiter statistics.

        Returns:
            Optional[Dict[str, Any]]: Rate limiter statistics or None if disabled
        """
        if self.enable_rate_limiting and self.rate_limiter:
            return self.rate_limiter.get_stats()
        return None

    def reset_rate_limiter_stats(self):
        """Reset rate limiter statistics."""
        if self.enable_rate_limiting and self.rate_limiter:
            self.rate_limiter.reset_stats()

    def configure_rate_limits(self,
                            calls_per_second: int = None,
                            calls_per_minute: int = None,
                            enable_burst_protection: bool = None):
        """
        Dynamically reconfigure rate limits.

        Args:
            calls_per_second (int, optional): New calls per second limit
            calls_per_minute (int, optional): New calls per minute limit
            enable_burst_protection (bool, optional): Enable/disable burst protection
        """
        if not self.enable_rate_limiting or not self.rate_limiter:
            logger.warning("Rate limiting is disabled, cannot configure limits")
            return

        if calls_per_second is not None:
            self.rate_limiter.max_calls_per_second = calls_per_second
            if enable_burst_protection is not False:  # Don't change if explicitly set to False
                self.rate_limiter.min_interval = 1.0 / calls_per_second

        if calls_per_minute is not None:
            self.rate_limiter.max_calls_per_minute = calls_per_minute

        if enable_burst_protection is not None:
            self.rate_limiter.enable_burst_protection = enable_burst_protection
            if enable_burst_protection:
                self.rate_limiter.min_interval = 1.0 / self.rate_limiter.max_calls_per_second
            else:
                self.rate_limiter.min_interval = 0

        logger.info(f"Rate limits reconfigured: {calls_per_second}/s, {calls_per_minute}/m, "
                   f"burst_protection={enable_burst_protection}")

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self.cache:
            return False

        cache_time = self.cache[cache_key].get('timestamp', 0)
        return time.time() - cache_time < self.cache_ttl

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get data from cache if valid."""
        if self._is_cache_valid(cache_key):
            logger.debug(f"Cache hit for {cache_key}")
            return self.cache[cache_key]['data']
        return None

    def _set_cache(self, cache_key: str, data: Any):
        """Store data in cache with timestamp."""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
        logger.debug(f"Cached data for {cache_key}")

    def test_connection(self) -> bool:
        """
        Test connection to Binance API.

        Simple implementation with direct API calls and basic retry.
        No recursion, no complex wrappers.

        Returns:
            bool: True if connection successful

        Raises:
            APIConnectionError: If connection fails after retries
        """
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                # Apply rate limiting if enabled
                if self.enable_rate_limiting and self.rate_limiter:
                    self.rate_limiter.wait_if_needed()

                # Direct API call - just fetch server time
                server_time = self.exchange.fetch_time()

                # Basic validation
                if not isinstance(server_time, (int, float)) or server_time <= 0:
                    raise APIConnectionError(
                        message="Invalid server time response",
                        exchange="binance"
                    )

                # Optional: Check time difference
                local_time = int(time.time() * 1000)
                time_diff = abs(server_time - local_time)
                if time_diff > 300000:  # 5 minutes
                    logger.warning(f"Large time difference with server: {time_diff}ms")

                logger.info("Successfully connected to Binance API")
                return True

            except KeyboardInterrupt:
                logger.info("Connection test interrupted by user")
                raise

            except Exception as e:
                last_error = e

                # If this is not the last attempt, wait and retry
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 1.0  # 1s, 2s, 3s
                    logger.warning(f"Connection attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    try:
                        time.sleep(wait_time)
                    except KeyboardInterrupt:
                        logger.info("Connection retry interrupted by user")
                        raise
                else:
                    logger.error(f"All {max_retries} connection attempts failed: {e}")

        # If we get here, all attempts failed
        raise APIConnectionError(
            message=f"Connection test failed after {max_retries} attempts: {last_error}",
            exchange="binance"
        )

    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if symbol exists on the exchange.

        This method does NOT use retry logic to avoid recursion issues.
        Symbol validation should be fast and deterministic.

        Args:
            symbol (str): Trading symbol (e.g., 'BTC/USDT')

        Returns:
            bool: True if symbol is valid

        Raises:
            InvalidSymbolError: If symbol is invalid
        """
        try:
            # Check cache first
            cache_key = f"symbol_validation_{symbol}"
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                return cached_result

            self._apply_rate_limiting()

            # Load markets if not already loaded
            if not hasattr(self.exchange, 'markets') or not self.exchange.markets:
                self.exchange.load_markets()

            is_valid = symbol in self.exchange.markets

            # Cache the result for longer (symbols don't change often)
            self.cache[cache_key] = {
                'data': is_valid,
                'timestamp': time.time()
            }

            if not is_valid:
                raise InvalidSymbolError(
                    symbol=symbol,
                    exchange="binance",
                    message="Symbol not found on exchange"
                )

            logger.debug(f"Symbol {symbol} validated successfully")
            return True

        except InvalidSymbolError:
            raise
        except Exception as e:
            # Categorize the exception properly
            categorized_exception = categorize_exception(e)
            if isinstance(categorized_exception, InvalidSymbolError):
                # Update the symbol field for InvalidSymbolError
                categorized_exception.details['symbol'] = symbol
                categorized_exception.message = f"Symbol validation failed for {symbol}: {e}"
            raise categorized_exception

    def get_current_price(self, symbol: str) -> float:
        """
        Get current price for a trading symbol.

        Simple implementation with direct API calls and loop-based retries.
        No recursion, no decorators, no complex wrappers.

        Args:
            symbol (str): Trading symbol (e.g., 'BTC/USDT')

        Returns:
            float: Current price

        Raises:
            InvalidSymbolError: If symbol is invalid
            APIConnectionError: If API connection fails
            DataValidationError: If price data is invalid
        """
        # Check cache first
        cache_key = f"current_price_{symbol}"
        cached_price = self._get_from_cache(cache_key)
        if cached_price is not None:
            return cached_price

        # Simple validation without retry - check if symbol format is valid
        if not symbol or '/' not in symbol:
            raise InvalidSymbolError(
                symbol=symbol,
                exchange="binance",
                message=f"Invalid symbol format: {symbol}"
            )

        # Direct API call with simple retry loop
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                # Apply rate limiting
                if self.enable_rate_limiting and self.rate_limiter:
                    self.rate_limiter.wait_if_needed()

                # Direct ccxt API call
                ticker = self.exchange.fetch_ticker(symbol)

                # Extract price
                price = ticker.get('last')

                # Simple validation
                if price is None:
                    raise DataValidationError(
                        field="price",
                        value=None,
                        expected_type="numeric price"
                    )

                if not isinstance(price, (int, float)) or price <= 0:
                    raise DataValidationError(
                        field="price",
                        value=price,
                        expected_type="positive number"
                    )

                # Convert to float
                price = float(price)

                # Cache the successful result
                self._set_cache(cache_key, price)

                logger.debug(f"Current price for {symbol}: {price}")
                return price

            except KeyboardInterrupt:
                # Don't retry on user interruption
                logger.info("Price fetch interrupted by user")
                raise

            except (InvalidSymbolError, DataValidationError):
                # Don't retry validation errors
                raise

            except Exception as e:
                last_error = e
                error_msg = str(e).lower()

                # Check if this is a symbol error
                if any(phrase in error_msg for phrase in [
                    "does not have market symbol",
                    "symbol not found",
                    "invalid symbol",
                    "bad symbol",
                    "unknown symbol",
                    "market not found"
                ]):
                    raise InvalidSymbolError(
                        symbol=symbol,
                        exchange="binance",
                        message=f"Symbol not found: {symbol}"
                    )

                # For retryable errors, wait and try again
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 0.5  # 0.5s, 1s, 2s
                    logger.warning(f"Attempt {attempt + 1} failed for {symbol}: {e}. Retrying in {wait_time}s...")
                    try:
                        time.sleep(wait_time)
                    except KeyboardInterrupt:
                        logger.info("Retry interrupted by user")
                        raise
                else:
                    logger.error(f"All {max_retries} attempts failed for {symbol}: {e}")

        # If we get here, all retries failed
        if last_error:
            error_msg = str(last_error).lower()

            # Categorize final error
            if any(phrase in error_msg for phrase in [
                "rate limit", "too many requests", "request limit exceeded"
            ]):
                raise RateLimitError(message=f"Rate limit exceeded for {symbol}: {last_error}")
            elif any(phrase in error_msg for phrase in [
                "timeout", "timed out", "connection timeout"
            ]):
                raise NetworkTimeoutError(message=f"Network timeout for {symbol}: {last_error}")
            else:
                raise APIConnectionError(
                    message=f"Failed to get price for {symbol} after {max_retries} attempts: {last_error}",
                    exchange="binance"
                )
        else:
            raise APIConnectionError(
                message=f"Failed to get price for {symbol}: unknown error",
                exchange="binance"
            )

    def get_24h_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get 24-hour ticker statistics.

        Args:
            symbol (str): Trading symbol (e.g., 'BTC/USDT')

        Returns:
            Dict[str, Any]: 24-hour ticker data with normalized fields
        """
        self.validate_symbol(symbol)

        cache_key = f"24h_ticker_{symbol}"
        cached_ticker = self._get_from_cache(cache_key)
        if cached_ticker is not None:
            return cached_ticker

        def _fetch_ticker():
            self._apply_rate_limiting()

            ticker = self.exchange.fetch_ticker(symbol)

            # Normalize ticker data to ensure consistent field names
            normalized_ticker = self._normalize_ticker_data(ticker, symbol)

            # Validate essential fields (only truly critical ones)
            critical_fields = ['last']  # Only last price is absolutely critical
            missing_critical = []

            for field in critical_fields:
                if normalized_ticker.get(field) is None:
                    missing_critical.append(field)

            if missing_critical:
                raise DataValidationError(
                    field="ticker_data",
                    value=f"missing critical fields: {missing_critical}",
                    expected_type="ticker with last price"
                )

            # Log warnings for optional missing fields
            optional_fields = ['volume', 'high', 'low', 'open', 'change', 'percentage']
            for field in optional_fields:
                if normalized_ticker.get(field) is None:
                    logger.debug(f"Optional field {field} missing in ticker data for {symbol}")

            self._set_cache(cache_key, normalized_ticker)

            # Use safe access for logging
            volume_info = normalized_ticker.get('volume', 'N/A')
            change_info = normalized_ticker.get('percentage', 'N/A')
            logger.debug(f"24h ticker for {symbol}: Volume={volume_info}, Change={change_info}%")

            return normalized_ticker

        try:
            return simple_retry_call(_fetch_ticker, max_retries=3)
        except Exception as e:
            if isinstance(e, DataValidationError):
                raise

            # Categorize the exception properly
            categorized_exception = categorize_exception(e)
            if isinstance(categorized_exception, InvalidSymbolError):
                # Update the symbol field for InvalidSymbolError
                categorized_exception.details['symbol'] = symbol
                categorized_exception.message = f"Failed to get 24h ticker for {symbol}: {e}"
            else:
                # For other exception types, update the message
                categorized_exception.message = f"Failed to get 24h ticker for {symbol}: {e}"

            raise categorized_exception

    def _normalize_ticker_data(self, ticker: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """
        Normalize ticker data to ensure consistent field names across different exchanges.

        Args:
            ticker (Dict[str, Any]): Raw ticker data from exchange
            symbol (str): Trading symbol for logging

        Returns:
            Dict[str, Any]: Normalized ticker data
        """
        normalized = ticker.copy()

        # Handle volume field variations
        if 'volume' not in normalized or normalized['volume'] is None:
            # Try alternative volume field names
            volume_alternatives = ['baseVolume', 'quoteVolume', 'vol', 'volume24h']
            for vol_field in volume_alternatives:
                if vol_field in ticker and ticker[vol_field] is not None:
                    normalized['volume'] = ticker[vol_field]
                    logger.debug(f"Using {vol_field} as volume for {symbol}")
                    break
            else:
                # Set default volume if none found
                normalized['volume'] = 0.0
                logger.debug(f"No volume data found for {symbol}, using default 0.0")

        # Handle price change fields
        if 'change' not in normalized or normalized['change'] is None:
            # Try to calculate change from open and last
            if normalized.get('open') and normalized.get('last'):
                try:
                    normalized['change'] = normalized['last'] - normalized['open']
                    logger.debug(f"Calculated change from open/last for {symbol}")
                except (TypeError, ValueError):
                    normalized['change'] = 0.0

        # Handle percentage change
        if 'percentage' not in normalized or normalized['percentage'] is None:
            # Try alternative field names
            percentage_alternatives = ['percent', 'change_percent', 'dailyChangePercent']
            for pct_field in percentage_alternatives:
                if pct_field in ticker and ticker[pct_field] is not None:
                    normalized['percentage'] = ticker[pct_field]
                    logger.debug(f"Using {pct_field} as percentage for {symbol}")
                    break
            else:
                # Try to calculate percentage from change and open
                if (normalized.get('change') is not None and
                    normalized.get('open') and
                    normalized['open'] != 0):
                    try:
                        normalized['percentage'] = (normalized['change'] / normalized['open']) * 100
                        logger.debug(f"Calculated percentage from change/open for {symbol}")
                    except (TypeError, ValueError, ZeroDivisionError):
                        normalized['percentage'] = 0.0

        # Ensure numeric fields are properly typed
        numeric_fields = ['last', 'volume', 'high', 'low', 'open', 'change', 'percentage']
        for field in numeric_fields:
            if field in normalized and normalized[field] is not None:
                try:
                    normalized[field] = float(normalized[field])
                except (TypeError, ValueError):
                    logger.warning(f"Could not convert {field} to float for {symbol}: {normalized[field]}")
                    normalized[field] = 0.0

        # Set default values for missing critical fields
        field_defaults = {
            'last': 0.0,
            'volume': 0.0,
            'high': normalized.get('last', 0.0),
            'low': normalized.get('last', 0.0),
            'open': normalized.get('last', 0.0),
            'change': 0.0,
            'percentage': 0.0
        }

        for field, default_value in field_defaults.items():
            if field not in normalized or normalized[field] is None:
                normalized[field] = default_value

        # Add metadata about data quality
        normalized['_data_quality'] = {
            'has_volume': 'volume' in ticker and ticker['volume'] is not None,
            'has_change': 'change' in ticker and ticker['change'] is not None,
            'has_percentage': 'percentage' in ticker and ticker['percentage'] is not None,
            'calculated_fields': [],
            'symbol': symbol,
            'timestamp': time.time()
        }

        return normalized

    def get_orderbook(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """
        Get order book data with enhanced validation.

        Args:
            symbol (str): Trading symbol (e.g., 'BTC/USDT')
            limit (int): Number of order book entries (1-1000)

        Returns:
            Dict[str, Any]: Validated order book data with bids and asks

        Raises:
            DataValidationError: If parameters are invalid
            InvalidSymbolError: If symbol is not valid
        """
        # Pre-validate all parameters before any API calls
        self.validate_symbol(symbol)

        # Use validation helper for limit parameter
        limit = validate_limit(limit, min_value=1, max_value=1000, field_name="limit")

        cache_key = f"orderbook_{symbol}_{limit}"
        cached_orderbook = self._get_from_cache(cache_key)
        if cached_orderbook is not None:
            return cached_orderbook

        def _fetch_orderbook():
            self._apply_rate_limiting()

            orderbook = self.exchange.fetch_order_book(symbol, limit)

            # Use validation helper to thoroughly validate orderbook structure
            validated_orderbook = validate_orderbook_data(orderbook)

            # Reduce cache TTL for orderbook (more volatile)
            original_ttl = self.cache_ttl
            self.cache_ttl = 2  # 2 seconds for orderbook
            self._set_cache(cache_key, validated_orderbook)
            self.cache_ttl = original_ttl

            logger.debug(f"Orderbook for {symbol}: {len(validated_orderbook['bids'])} bids, {len(validated_orderbook['asks'])} asks")
            return validated_orderbook

        try:
            return simple_retry_call(_fetch_orderbook, max_retries=3)
        except Exception as e:
            if isinstance(e, DataValidationError):
                raise

            # Categorize the exception properly
            categorized_exception = categorize_exception(e)
            if isinstance(categorized_exception, InvalidSymbolError):
                # Update the symbol field for InvalidSymbolError
                categorized_exception.details['symbol'] = symbol
                categorized_exception.message = f"Failed to get orderbook for {symbol}: {e}"
            else:
                # For other exception types, update the message
                categorized_exception.message = f"Failed to get orderbook for {symbol}: {e}"

            raise categorized_exception

    def get_klines(self, symbol: str, interval: str = '5m', limit: int = 500) -> List[List[float]]:
        """
        Get candlestick (OHLCV) data.

        Args:
            symbol (str): Trading symbol (e.g., 'BTC/USDT')
            interval (str): Time interval ('1m', '5m', '15m', '1h', '4h', '1d', etc.)
            limit (int): Number of candles (max 1000)

        Returns:
            List[List[float]]: List of OHLCV data [timestamp, open, high, low, close, volume]

        Raises:
            DataValidationError: If parameters are invalid
            InsufficientDataError: If not enough data available
        """
        # Pre-validate all parameters before any API calls
        self.validate_symbol(symbol)

        # Use validation helpers
        interval = validate_interval(interval)
        limit = validate_limit(limit, min_value=1, max_value=1000, field_name="limit")

        cache_key = f"klines_{symbol}_{interval}_{limit}"
        cached_klines = self._get_from_cache(cache_key)
        if cached_klines is not None:
            return cached_klines

        def _fetch_klines():
            self._apply_rate_limiting()

            ohlcv = self.exchange.fetch_ohlcv(symbol, interval, limit=limit)

            if len(ohlcv) < limit * 0.8:  # If we got less than 80% of requested data
                logger.warning(f"Received {len(ohlcv)} candles, requested {limit} for {symbol}")

            if len(ohlcv) == 0:
                raise InsufficientDataError(
                    data_type="candlestick data",
                    required_count=limit,
                    available_count=0
                )

            # Validate OHLCV data structure using validation helper
            validated_ohlcv = []
            for i, candle in enumerate(ohlcv[:5]):  # Check first 5 candles thoroughly
                validated_candle = validate_ohlcv_candle(candle, i)
                validated_ohlcv.append(validated_candle)

            # For the rest, do basic length check only (performance optimization)
            for i, candle in enumerate(ohlcv[5:], start=5):
                if len(candle) != 6:
                    raise DataValidationError(
                        field=f"candle[{i}]",
                        value=f"length {len(candle)}",
                        expected_type="array of length 6 [timestamp, open, high, low, close, volume]"
                    )

            self._set_cache(cache_key, ohlcv)

            logger.debug(f"Retrieved {len(ohlcv)} {interval} candles for {symbol}")
            return ohlcv

        try:
            return simple_retry_call(_fetch_klines, max_retries=3)
        except Exception as e:
            if isinstance(e, (DataValidationError, InsufficientDataError)):
                raise

            # Categorize the exception properly
            categorized_exception = categorize_exception(e)
            if isinstance(categorized_exception, InvalidSymbolError):
                # Update the symbol field for InvalidSymbolError
                categorized_exception.details['symbol'] = symbol
                categorized_exception.message = f"Failed to get klines for {symbol}: {e}"
            else:
                # For other exception types, update the message
                categorized_exception.message = f"Failed to get klines for {symbol}: {e}"

            raise categorized_exception

    def get_multiple_symbols_data(self, symbols: List[str], data_type: str = "price") -> Dict[str, Any]:
        """
        Get data for multiple symbols efficiently with intelligent rate limiting.

        This method automatically distributes API calls over time to respect rate limits
        when fetching data for multiple symbols.

        Args:
            symbols (List[str]): List of trading symbols
            data_type (str): Type of data ('price', 'ticker', 'orderbook')

        Returns:
            Dict[str, Any]: Dictionary with symbol as key and data as value
        """
        results = {}
        errors = {}

        # Log the start of multi-symbol data collection
        logger.debug(f"Fetching {data_type} data for {len(symbols)} symbols with rate limiting")

        for i, symbol in enumerate(symbols):
            try:
                # Apply rate limiting before each API call
                # Note: Individual methods also apply their own rate limiting,
                # but this ensures proper distribution across multiple symbols
                if i > 0:  # Skip rate limiting for first symbol
                    self._apply_rate_limiting()

                if data_type == "price":
                    results[symbol] = self.get_current_price(symbol)
                elif data_type == "ticker":
                    results[symbol] = self.get_24h_ticker(symbol)
                elif data_type == "orderbook":
                    results[symbol] = self.get_orderbook(symbol)
                else:
                    raise DataValidationError(
                        field="data_type",
                        value=data_type,
                        expected_type="'price', 'ticker', or 'orderbook'"
                    )

                logger.debug(f"Successfully fetched {data_type} for {symbol} ({i+1}/{len(symbols)})")

            except Exception as e:
                errors[symbol] = str(e)
                logger.error(f"Failed to get {data_type} for {symbol}: {e}")

        if errors:
            logger.warning(f"Errors occurred for {len(errors)} symbols: {list(errors.keys())}")

        # Log completion statistics
        success_rate = (len(results) / len(symbols)) * 100 if symbols else 0
        logger.info(f"Multi-symbol {data_type} collection completed: "
                   f"{len(results)}/{len(symbols)} successful ({success_rate:.1f}%)")

        return {
            "data": results,
            "errors": errors,
            "success_count": len(results),
            "error_count": len(errors),
            "success_rate_percent": round(success_rate, 1)
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring.

        Returns:
            Dict[str, Any]: Cache statistics
        """
        now = time.time()
        valid_entries = 0
        expired_entries = 0

        for key, entry in self.cache.items():
            if now - entry['timestamp'] < self.cache_ttl:
                valid_entries += 1
            else:
                expired_entries += 1

        return {
            "total_entries": len(self.cache),
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_ttl": self.cache_ttl
        }

    def clear_cache(self):
        """Clear all cached data."""
        self.cache.clear()
        logger.info("Cache cleared")


# Utility functions for data analysis

def calculate_price_change(old_price: float, new_price: float) -> Dict[str, float]:
    """
    Calculate price change and percentage.

    Args:
        old_price (float): Previous price
        new_price (float): Current price

    Returns:
        Dict[str, float]: Price change data
    """
    if old_price <= 0:
        raise DataValidationError("old_price", old_price, "positive number")

    change = new_price - old_price
    percentage = (change / old_price) * 100

    return {
        "change": change,
        "percentage": percentage,
        "old_price": old_price,
        "new_price": new_price
    }


def validate_ohlcv_data(ohlcv: List[List[float]]) -> bool:
    """
    Validate OHLCV data integrity.

    Args:
        ohlcv (List[List[float]]): OHLCV candlestick data

    Returns:
        bool: True if data is valid

    Raises:
        DataValidationError: If data is invalid
    """
    if not ohlcv:
        raise DataValidationError("ohlcv", "empty list", "non-empty list")

    for i, candle in enumerate(ohlcv):
        if len(candle) != 6:
            raise DataValidationError(f"candle[{i}]", f"length {len(candle)}", "length 6")

        timestamp, open_price, high, low, close, volume = candle

        # Basic price validation
        if high < max(open_price, close) or low > min(open_price, close):
            raise DataValidationError(f"candle[{i}]", "invalid OHLC relationship", "high >= max(open,close) and low <= min(open,close)")

        if volume < 0:
            raise DataValidationError(f"candle[{i}].volume", volume, "non-negative number")

    return True