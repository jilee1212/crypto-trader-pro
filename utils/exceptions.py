"""
Custom exceptions for cryptocurrency trading bot.
Defines all possible exception scenarios that can occur during trading operations.
"""

from typing import Optional, Dict, Any


class TradingBotException(Exception):
    """
    Base exception class for all trading bot related errors.

    Attributes:
        message (str): Human readable error message
        error_code (str): Unique error code for identification
        details (dict): Additional error details
    """

    def __init__(self, message: str, error_code: str = "GENERIC_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging purposes."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


class APIConnectionError(TradingBotException):
    """
    Raised when connection to exchange API fails.

    Common causes:
    - Network connectivity issues
    - Exchange server downtime
    - Invalid API credentials
    - SSL/TLS certificate errors
    """

    def __init__(self, message: str = "Failed to connect to exchange API",
                 exchange: str = "", status_code: Optional[int] = None, **kwargs):
        details = {
            "exchange": exchange,
            "status_code": status_code
        }
        details.update(kwargs)
        super().__init__(message, "API_CONNECTION_ERROR", details)


class InvalidSymbolError(TradingBotException):
    """
    Raised when an invalid trading symbol is provided.

    Examples:
    - Symbol not supported by exchange
    - Malformed symbol format
    - Delisted trading pair
    """

    def __init__(self, symbol: str, exchange: str = "",
                 message: str = "Invalid trading symbol provided", **kwargs):
        details = {
            "symbol": symbol,
            "exchange": exchange
        }
        details.update(kwargs)
        super().__init__(f"{message}: {symbol}", "INVALID_SYMBOL_ERROR", details)


class RateLimitError(TradingBotException):
    """
    Raised when API rate limit is exceeded.

    Attributes:
        retry_after (int): Seconds to wait before next request
        current_limit (int): Current rate limit
        requests_made (int): Number of requests made
    """

    def __init__(self, message: str = "API rate limit exceeded",
                 retry_after: int = 60, current_limit: int = 0,
                 requests_made: int = 0, **kwargs):
        details = {
            "retry_after": retry_after,
            "current_limit": current_limit,
            "requests_made": requests_made
        }
        details.update(kwargs)
        super().__init__(message, "RATE_LIMIT_ERROR", details)


class DataValidationError(TradingBotException):
    """
    Raised when data validation fails.

    Common scenarios:
    - Invalid price or volume data
    - Missing required fields
    - Data type mismatches
    - Out of range values
    """

    def __init__(self, field: str, value: Any = None, expected_type: str = "",
                 message: str = "Data validation failed", **kwargs):
        details = {
            "field": field,
            "value": value,
            "expected_type": expected_type
        }
        details.update(kwargs)
        super().__init__(f"{message} for field: {field}", "DATA_VALIDATION_ERROR", details)


class InsufficientDataError(TradingBotException):
    """
    Raised when there is not enough data for analysis.

    Common scenarios:
    - Not enough historical data for indicators
    - Missing recent market data
    - Incomplete order book data
    """

    def __init__(self, data_type: str, required_count: int = 0,
                 available_count: int = 0,
                 message: str = "Insufficient data for analysis", **kwargs):
        details = {
            "data_type": data_type,
            "required_count": required_count,
            "available_count": available_count
        }
        details.update(kwargs)
        super().__init__(
            f"{message}: {data_type} (need {required_count}, got {available_count})",
            "INSUFFICIENT_DATA_ERROR",
            details
        )


class NetworkTimeoutError(TradingBotException):
    """
    Raised when network request times out.

    Attributes:
        timeout_duration (float): Timeout duration in seconds
        request_url (str): URL that timed out
        retry_count (int): Number of retries attempted
    """

    def __init__(self, timeout_duration: float = 30.0, request_url: str = "",
                 retry_count: int = 0,
                 message: str = "Network request timed out", **kwargs):
        details = {
            "timeout_duration": timeout_duration,
            "request_url": request_url,
            "retry_count": retry_count
        }
        details.update(kwargs)
        super().__init__(message, "NETWORK_TIMEOUT_ERROR", details)


class TradingError(TradingBotException):
    """
    Raised when trading operation fails.

    Common scenarios:
    - Insufficient balance
    - Order placement failures
    - Order cancellation failures
    - Position management errors
    """

    def __init__(self, symbol: str, operation: str,
                 message: str = "Trading operation failed", **kwargs):
        details = {
            "symbol": symbol,
            "operation": operation
        }
        details.update(kwargs)
        super().__init__(f"{message}: {operation} for {symbol}", "TRADING_ERROR", details)


class RiskManagementError(TradingBotException):
    """
    Raised when risk management rules are violated.

    Common scenarios:
    - Position size exceeds limits
    - Daily loss limit reached
    - Stop loss not set
    - Risk/reward ratio violation
    """

    def __init__(self, risk_type: str, current_value: float, limit_value: float,
                 message: str = "Risk management violation", **kwargs):
        details = {
            "risk_type": risk_type,
            "current_value": current_value,
            "limit_value": limit_value
        }
        details.update(kwargs)
        super().__init__(
            f"{message}: {risk_type} ({current_value} exceeds {limit_value})",
            "RISK_MANAGEMENT_ERROR",
            details
        )


class ConfigurationError(TradingBotException):
    """
    Raised when configuration is invalid or missing.

    Common scenarios:
    - Missing API keys
    - Invalid configuration values
    - Required settings not provided
    """

    def __init__(self, config_key: str,
                 message: str = "Configuration error", **kwargs):
        details = {
            "config_key": config_key
        }
        details.update(kwargs)
        super().__init__(f"{message}: {config_key}", "CONFIGURATION_ERROR", details)


class StrategyError(TradingBotException):
    """
    Raised when trading strategy encounters an error.

    Common scenarios:
    - Strategy initialization failure
    - Signal generation errors
    - Strategy validation failures
    """

    def __init__(self, strategy_name: str,
                 message: str = "Strategy error", **kwargs):
        details = {
            "strategy_name": strategy_name
        }
        details.update(kwargs)
        super().__init__(f"{message} in strategy: {strategy_name}", "STRATEGY_ERROR", details)


# Utility functions for exception handling

def handle_api_error(func):
    """
    Decorator to handle common API errors.

    Usage:
        @handle_api_error
        def fetch_market_data():
            # API call here
            pass
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if "timeout" in str(e).lower():
                raise NetworkTimeoutError(message=str(e))
            elif "rate limit" in str(e).lower():
                raise RateLimitError(message=str(e))
            elif "connection" in str(e).lower():
                raise APIConnectionError(message=str(e))
            else:
                raise TradingBotException(message=str(e), error_code="UNKNOWN_API_ERROR")
    return wrapper


def validate_trading_params(symbol: str, amount: float, price: float):
    """
    Validate trading parameters and raise appropriate exceptions.

    Args:
        symbol (str): Trading symbol
        amount (float): Order amount
        price (float): Order price

    Raises:
        DataValidationError: If any parameter is invalid
    """
    if not symbol or not isinstance(symbol, str):
        raise DataValidationError("symbol", symbol, "non-empty string")

    if amount <= 0:
        raise DataValidationError("amount", amount, "positive number")

    if price <= 0:
        raise DataValidationError("price", price, "positive number")


# Error code constants for easy reference
class ErrorCodes:
    """Constants for error codes used throughout the application."""

    API_CONNECTION_ERROR = "API_CONNECTION_ERROR"
    INVALID_SYMBOL_ERROR = "INVALID_SYMBOL_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    DATA_VALIDATION_ERROR = "DATA_VALIDATION_ERROR"
    INSUFFICIENT_DATA_ERROR = "INSUFFICIENT_DATA_ERROR"
    NETWORK_TIMEOUT_ERROR = "NETWORK_TIMEOUT_ERROR"
    TRADING_ERROR = "TRADING_ERROR"
    RISK_MANAGEMENT_ERROR = "RISK_MANAGEMENT_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    STRATEGY_ERROR = "STRATEGY_ERROR"