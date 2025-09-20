"""
Utility modules for Crypto Trader Pro.

This module provides essential utilities for cryptocurrency trading including:
- Market data collection and API integration (MarketDataCollector)
- Custom exception handling system (TradingBotException and derivatives)
- Input validation and data sanitization (validation helpers)
- Error handling decorators and utilities

Version: 1.0.0
"""

from .market_data import MarketDataCollector, calculate_price_change, validate_ohlcv_data
from .exceptions import (
    TradingBotException,
    APIConnectionError,
    InvalidSymbolError,
    RateLimitError,
    DataValidationError,
    InsufficientDataError,
    NetworkTimeoutError,
    TradingError,
    RiskManagementError,
    ConfigurationError,
    StrategyError,
    ErrorCodes,
    handle_api_error,
    validate_trading_params
)
from .validation_helpers import (
    validate_symbol,
    validate_limit,
    validate_interval,
    validate_price,
    validate_amount,
    validate_percentage,
    validate_ohlcv_candle,
    validate_orderbook_data,
    validate_ticker_data,
    sanitize_input,
    validate_trading_params as validate_trading_params_decorator
)

__version__ = "1.0.0"
__author__ = "Crypto Trader Pro Team"

__all__ = [
    # Market data collection
    'MarketDataCollector',
    'calculate_price_change',
    'validate_ohlcv_data',

    # Exception handling
    'TradingBotException',
    'APIConnectionError',
    'InvalidSymbolError',
    'RateLimitError',
    'DataValidationError',
    'InsufficientDataError',
    'NetworkTimeoutError',
    'TradingError',
    'RiskManagementError',
    'ConfigurationError',
    'StrategyError',
    'ErrorCodes',
    'handle_api_error',
    'validate_trading_params',

    # Validation helpers
    'validate_symbol',
    'validate_limit',
    'validate_interval',
    'validate_price',
    'validate_amount',
    'validate_percentage',
    'validate_ohlcv_candle',
    'validate_orderbook_data',
    'validate_ticker_data',
    'sanitize_input',
    'validate_trading_params_decorator'
]