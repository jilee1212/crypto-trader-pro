"""
Configuration management module for Crypto Trader Pro.

This module provides configuration management and logging setup including:
- Logging configuration and initialization
- Configuration file validation and loading
- Environment variable management
- Trading parameters and exchange settings

Version: 1.0.0
"""

# Import built-in logging module
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Try to import advanced logging config if available
try:
    from .logging_config import (
        get_trading_logger,
        get_backtest_logger,
        get_risk_logger,
        get_arbitrage_logger,
        log_trade_execution,
        log_signal_generated,
        log_risk_alert,
        log_arbitrage_opportunity,
        log_system_status,
        LOG_TEMPLATES
    )
    _ADVANCED_LOGGING_AVAILABLE = True
except ImportError:
    _ADVANCED_LOGGING_AVAILABLE = False

# Global logging configuration
_LOGGING_INITIALIZED = False
_LOGGERS_CACHE: Dict[str, logging.Logger] = {}

__version__ = "1.0.0"
__author__ = "Crypto Trader Pro Team"

__all__ = [
    # Core configuration functions
    'load_config',
    'validate_config',
    'get_default_config',

    # Core logging functions (always available)
    'setup_logging',
    'get_logger'
]

# Add advanced logging functions if available
if _ADVANCED_LOGGING_AVAILABLE:
    __all__.extend([
        'get_trading_logger',
        'get_backtest_logger',
        'get_risk_logger',
        'get_arbitrage_logger',
        'log_trade_execution',
        'log_signal_generated',
        'log_risk_alert',
        'log_arbitrage_opportunity',
        'log_system_status',
        'LOG_TEMPLATES'
    ])


def setup_logging(config: Optional[Dict[str, Any]] = None, force_reinit: bool = False) -> bool:
    """
    Setup comprehensive logging system for Crypto Trader Pro.

    This function configures logging based on the provided configuration or loads
    from the default config file. It sets up both file and console logging with
    rotation, formatting, and appropriate log levels.

    Args:
        config (Optional[Dict[str, Any]]): Logging configuration dictionary
        force_reinit (bool): Force re-initialization even if already initialized

    Returns:
        bool: True if logging setup was successful

    Raises:
        Exception: If logging setup fails critically
    """
    global _LOGGING_INITIALIZED

    # Avoid re-initialization unless forced
    if _LOGGING_INITIALIZED and not force_reinit:
        return True

    try:
        # Load configuration if not provided
        if config is None:
            try:
                full_config = load_config()
                config = full_config.get('logging', {})
            except Exception:
                # Use default logging config if loading fails
                config = {
                    'level': 'INFO',
                    'file_path': 'logs/crypto_trader.log',
                    'max_file_size_mb': 50,
                    'backup_count': 5,
                    'console_logging': True
                }

        # Create logs directory
        log_file_path = Path(config.get('file_path', 'logs/crypto_trader.log'))
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)  # Capture all levels

        # Clear existing handlers to avoid duplicates
        if force_reinit:
            root_logger.handlers.clear()

        # Set up file handler with rotation
        max_bytes = int(config.get('max_file_size_mb', 50)) * 1024 * 1024
        backup_count = int(config.get('backup_count', 5))

        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_file_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )

        # Set log level for file handler
        log_level = getattr(logging, config.get('level', 'INFO').upper())
        file_handler.setLevel(log_level)

        # Create detailed formatter for file logging
        file_formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-15s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)

        # Add file handler to root logger
        root_logger.addHandler(file_handler)

        # Set up console handler if enabled
        if config.get('console_logging', True):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)

            # Create simpler formatter for console
            console_formatter = logging.Formatter(
                fmt='%(asctime)s | %(levelname)-5s | %(name)s | %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)

            root_logger.addHandler(console_handler)

        # Set up error handler for critical errors (separate file)
        error_log_path = log_file_path.parent / 'errors.log'
        error_handler = logging.handlers.RotatingFileHandler(
            filename=str(error_log_path),
            maxBytes=max_bytes // 2,  # Smaller size for error logs
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_handler)

        # Configure specific logger levels to reduce noise
        logging.getLogger('ccxt').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)

        # Log successful initialization
        logger = logging.getLogger(__name__)
        logger.info("Logging system initialized successfully")
        logger.info(f"Log file: {log_file_path}")
        logger.info(f"Log level: {config.get('level', 'INFO')}")
        logger.info(f"Console logging: {config.get('console_logging', True)}")

        _LOGGING_INITIALIZED = True
        return True

    except Exception as e:
        # Fallback to basic logging if setup fails
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        logging.error(f"Advanced logging setup failed, using basic config: {e}")
        _LOGGING_INITIALIZED = True
        return False


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance for the specified name.

    This function returns a logger with the appropriate configuration
    based on the global logging setup. It caches loggers to avoid
    recreation overhead.

    Args:
        name (str): Logger name (typically __name__ from calling module)

    Returns:
        logging.Logger: Configured logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("This is an info message")
        >>> logger.error("This is an error message")
    """
    global _LOGGERS_CACHE

    # Check cache first
    if name in _LOGGERS_CACHE:
        return _LOGGERS_CACHE[name]

    # Initialize logging if not already done
    if not _LOGGING_INITIALIZED:
        setup_logging()

    # Create and configure logger
    logger = logging.getLogger(name)

    # Cache the logger
    _LOGGERS_CACHE[name] = logger

    return logger


def load_config(config_path: str = "config/config.json") -> dict:
    """
    Load configuration from JSON file with validation.

    Args:
        config_path (str): Path to configuration file

    Returns:
        dict: Loaded configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is invalid JSON
    """
    import json
    from pathlib import Path

    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Basic validation
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a JSON object")

        return config

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in configuration file: {e}")


def validate_config(config: dict) -> bool:
    """
    Validate configuration structure and required fields.

    Args:
        config (dict): Configuration dictionary to validate

    Returns:
        bool: True if configuration is valid

    Raises:
        ValueError: If configuration is invalid
    """
    required_sections = ['exchange', 'trading', 'strategy']

    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required configuration section: {section}")

    # Validate exchange section
    exchange_config = config['exchange']
    if 'name' not in exchange_config:
        raise ValueError("Missing 'name' in exchange configuration")

    # Validate trading section
    trading_config = config['trading']
    required_trading_fields = ['max_risk_per_trade', 'daily_loss_limit', 'currencies']
    for field in required_trading_fields:
        if field not in trading_config:
            raise ValueError(f"Missing required trading field: {field}")

    # Validate strategy section
    strategy_config = config['strategy']
    required_strategy_fields = ['rsi_period', 'rsi_buy_threshold', 'rsi_sell_threshold']
    for field in required_strategy_fields:
        if field not in strategy_config:
            raise ValueError(f"Missing required strategy field: {field}")

    return True


def get_default_config() -> dict:
    """
    Get default configuration for Crypto Trader Pro.

    Returns:
        dict: Default configuration dictionary
    """
    return {
        "exchange": {
            "name": "binance",
            "testnet": True,
            "api_key": "",
            "api_secret": ""
        },
        "trading": {
            "max_risk_per_trade": 0.02,
            "daily_loss_limit": 0.03,
            "currencies": ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
        },
        "strategy": {
            "rsi_period": 14,
            "rsi_buy_threshold": 30,
            "rsi_sell_threshold": 70,
            "volume_increase_threshold": 0.2
        },
        "risk_management": {
            "stop_loss_percent": 0.01,
            "take_profit_ratio": 2.0,
            "max_open_positions": 3,
            "position_sizing_method": "kelly"
        },
        "arbitrage": {
            "exchanges": ["binance", "coinbase", "kraken"],
            "min_profit_threshold": 0.005,
            "include_fees": True
        },
        "notifications": {
            "telegram_enabled": False,
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            "email_enabled": False
        },
        "timeframes": {
            "data_collection": "5m",
            "analysis": "1h",
            "monitoring": "1m"
        }
    }


# Configuration utilities are already included in __all__ above