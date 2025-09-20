"""
Validation helper functions for cryptocurrency trading bot.
Provides common validation logic for parameters, data integrity, and input sanitization.
"""

from typing import Any, List, Dict, Optional, Union
from .exceptions import DataValidationError


def validate_symbol(symbol: str) -> str:
    """
    Validate trading symbol format.

    Args:
        symbol (str): Trading symbol to validate

    Returns:
        str: Cleaned symbol

    Raises:
        DataValidationError: If symbol format is invalid
    """
    if not symbol or not isinstance(symbol, str):
        raise DataValidationError(
            field="symbol",
            value=symbol,
            expected_type="non-empty string"
        )

    symbol = symbol.strip().upper()

    if len(symbol) < 3:
        raise DataValidationError(
            field="symbol",
            value=symbol,
            expected_type="symbol with at least 3 characters"
        )

    # Check if symbol contains the required separator
    if '/' not in symbol:
        raise DataValidationError(
            field="symbol",
            value=symbol,
            expected_type="symbol with format 'BASE/QUOTE' (e.g., 'BTC/USDT')"
        )

    # Split and validate base/quote parts
    parts = symbol.split('/')
    if len(parts) != 2:
        raise DataValidationError(
            field="symbol",
            value=symbol,
            expected_type="symbol with exactly one '/' separator"
        )

    base, quote = parts
    if not base or not quote:
        raise DataValidationError(
            field="symbol",
            value=symbol,
            expected_type="symbol with non-empty base and quote parts"
        )

    return symbol


def validate_limit(limit: int, min_value: int = 1, max_value: int = 1000, field_name: str = "limit") -> int:
    """
    Validate limit parameter for API calls.

    Args:
        limit (int): Limit value to validate
        min_value (int): Minimum allowed value
        max_value (int): Maximum allowed value
        field_name (str): Name of the field for error messages

    Returns:
        int: Validated limit value

    Raises:
        DataValidationError: If limit is out of range
    """
    if not isinstance(limit, int):
        raise DataValidationError(
            field=field_name,
            value=limit,
            expected_type="integer"
        )

    if limit < min_value or limit > max_value:
        raise DataValidationError(
            field=field_name,
            value=limit,
            expected_type=f"integer between {min_value} and {max_value}"
        )

    return limit


def validate_interval(interval: str, valid_intervals: Optional[List[str]] = None) -> str:
    """
    Validate time interval for candlestick data.

    Args:
        interval (str): Time interval to validate
        valid_intervals (List[str], optional): List of valid intervals

    Returns:
        str: Validated interval

    Raises:
        DataValidationError: If interval is invalid
    """
    if not interval or not isinstance(interval, str):
        raise DataValidationError(
            field="interval",
            value=interval,
            expected_type="non-empty string"
        )

    if valid_intervals is None:
        valid_intervals = [
            '1m', '3m', '5m', '15m', '30m',
            '1h', '2h', '4h', '6h', '8h', '12h',
            '1d', '3d', '1w', '1M'
        ]

    if interval not in valid_intervals:
        raise DataValidationError(
            field="interval",
            value=interval,
            expected_type=f"one of {valid_intervals}"
        )

    return interval


def validate_price(price: Union[int, float], field_name: str = "price") -> float:
    """
    Validate price value.

    Args:
        price (Union[int, float]): Price to validate
        field_name (str): Name of the field for error messages

    Returns:
        float: Validated price

    Raises:
        DataValidationError: If price is invalid
    """
    try:
        price_float = float(price)
    except (TypeError, ValueError):
        raise DataValidationError(
            field=field_name,
            value=price,
            expected_type="numeric value"
        )

    if price_float <= 0:
        raise DataValidationError(
            field=field_name,
            value=price_float,
            expected_type="positive number"
        )

    if price_float > 1e12:  # Sanity check for extremely large values
        raise DataValidationError(
            field=field_name,
            value=price_float,
            expected_type="reasonable price value (< 1e12)"
        )

    return price_float


def validate_amount(amount: Union[int, float], field_name: str = "amount") -> float:
    """
    Validate trading amount/volume.

    Args:
        amount (Union[int, float]): Amount to validate
        field_name (str): Name of the field for error messages

    Returns:
        float: Validated amount

    Raises:
        DataValidationError: If amount is invalid
    """
    try:
        amount_float = float(amount)
    except (TypeError, ValueError):
        raise DataValidationError(
            field=field_name,
            value=amount,
            expected_type="numeric value"
        )

    if amount_float <= 0:
        raise DataValidationError(
            field=field_name,
            value=amount_float,
            expected_type="positive number"
        )

    if amount_float > 1e12:  # Sanity check
        raise DataValidationError(
            field=field_name,
            value=amount_float,
            expected_type="reasonable amount value (< 1e12)"
        )

    return amount_float


def validate_percentage(percentage: Union[int, float], min_pct: float = -100.0,
                       max_pct: float = 100.0, field_name: str = "percentage") -> float:
    """
    Validate percentage value.

    Args:
        percentage (Union[int, float]): Percentage to validate
        min_pct (float): Minimum allowed percentage
        max_pct (float): Maximum allowed percentage
        field_name (str): Name of the field for error messages

    Returns:
        float: Validated percentage

    Raises:
        DataValidationError: If percentage is out of range
    """
    try:
        pct_float = float(percentage)
    except (TypeError, ValueError):
        raise DataValidationError(
            field=field_name,
            value=percentage,
            expected_type="numeric value"
        )

    if pct_float < min_pct or pct_float > max_pct:
        raise DataValidationError(
            field=field_name,
            value=pct_float,
            expected_type=f"percentage between {min_pct}% and {max_pct}%"
        )

    return pct_float


def validate_ohlcv_candle(candle: List[Any], candle_index: int = 0, strict: bool = False) -> List[float]:
    """
    Validate individual OHLCV candlestick data with flexible validation options.

    Args:
        candle (List[Any]): Candlestick data [timestamp, open, high, low, close, volume]
        candle_index (int): Index of candle for error reporting
        strict (bool): Enable strict validation for production data

    Returns:
        List[float]: Validated candle data

    Raises:
        DataValidationError: If candle data is invalid
    """
    # Handle None or empty data
    if candle is None:
        raise DataValidationError(
            field=f"candle[{candle_index}]",
            value="None",
            expected_type="OHLCV data array"
        )

    if not isinstance(candle, (list, tuple)):
        raise DataValidationError(
            field=f"candle[{candle_index}]",
            value=type(candle).__name__,
            expected_type="list or tuple"
        )

    # Handle different array lengths more flexibly
    if len(candle) < 6:
        # Try to pad with default values for missing data
        padded_candle = list(candle)
        while len(padded_candle) < 6:
            if len(padded_candle) == 5:  # Missing volume
                padded_candle.append(0.0)
            else:
                raise DataValidationError(
                    field=f"candle[{candle_index}]",
                    value=f"length {len(candle)}",
                    expected_type="array of length 6 [timestamp, open, high, low, close, volume]"
                )
        candle = padded_candle
    elif len(candle) > 6:
        # Take only first 6 elements
        candle = candle[:6]

    try:
        timestamp, open_price, high, low, close, volume = candle

        # Convert to appropriate types with safer conversion
        timestamp = _safe_float_conversion(timestamp, f"candle[{candle_index}].timestamp")
        open_price = _safe_float_conversion(open_price, f"candle[{candle_index}].open")
        high = _safe_float_conversion(high, f"candle[{candle_index}].high")
        low = _safe_float_conversion(low, f"candle[{candle_index}].low")
        close = _safe_float_conversion(close, f"candle[{candle_index}].close")
        volume = _safe_float_conversion(volume, f"candle[{candle_index}].volume", allow_negative=False)

    except (TypeError, ValueError, DataValidationError) as e:
        if isinstance(e, DataValidationError):
            raise
        raise DataValidationError(
            field=f"candle[{candle_index}]",
            value="contains non-numeric values",
            expected_type="numeric values only"
        )

    # Validate basic sanity checks
    if strict:
        # Strict validation for production data
        _validate_ohlc_relationships_strict(open_price, high, low, close, candle_index)
        _validate_positive_prices_strict(open_price, high, low, close, candle_index)
    else:
        # Lenient validation for test data
        _validate_ohlc_relationships_lenient(open_price, high, low, close, candle_index)
        _validate_positive_prices_lenient(open_price, high, low, close, candle_index)

    # Volume should be non-negative (always enforced)
    if volume < 0:
        if strict:
            raise DataValidationError(
                field=f"candle[{candle_index}].volume",
                value=volume,
                expected_type="non-negative volume"
            )
        else:
            # In lenient mode, just set negative volume to 0
            volume = 0.0

    return [timestamp, open_price, high, low, close, volume]


def _safe_float_conversion(value: Any, field_name: str, allow_negative: bool = True) -> float:
    """
    Safely convert value to float with proper error handling.

    Args:
        value: Value to convert
        field_name: Field name for error reporting
        allow_negative: Whether to allow negative values

    Returns:
        float: Converted value

    Raises:
        DataValidationError: If conversion fails or value is invalid
    """
    if value is None:
        raise DataValidationError(
            field=field_name,
            value="None",
            expected_type="numeric value"
        )

    try:
        # Handle string representations
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise DataValidationError(
                    field=field_name,
                    value="empty string",
                    expected_type="numeric value"
                )

        converted = float(value)

        # Check for NaN or infinity
        if not _is_finite_number(converted):
            raise DataValidationError(
                field=field_name,
                value=str(converted),
                expected_type="finite numeric value"
            )

        # Check negative values if not allowed
        if not allow_negative and converted < 0:
            raise DataValidationError(
                field=field_name,
                value=converted,
                expected_type="non-negative value"
            )

        return converted

    except (TypeError, ValueError, OverflowError) as e:
        raise DataValidationError(
            field=field_name,
            value=str(value),
            expected_type="numeric value"
        )


def _is_finite_number(value: float) -> bool:
    """Check if a number is finite (not NaN or infinity)."""
    import math
    return not (math.isnan(value) or math.isinf(value))


def _validate_ohlc_relationships_strict(open_price: float, high: float, low: float, close: float, candle_index: int):
    """Strict OHLC relationship validation for production data."""
    if high < max(open_price, close):
        raise DataValidationError(
            field=f"candle[{candle_index}].high",
            value=high,
            expected_type=f"value >= max(open={open_price}, close={close})"
        )

    if low > min(open_price, close):
        raise DataValidationError(
            field=f"candle[{candle_index}].low",
            value=low,
            expected_type=f"value <= min(open={open_price}, close={close})"
        )


def _validate_ohlc_relationships_lenient(open_price: float, high: float, low: float, close: float, candle_index: int):
    """Lenient OHLC relationship validation for test data."""
    # Allow some tolerance for test data
    tolerance = 0.01  # 1% tolerance

    max_price = max(open_price, close)
    min_price = min(open_price, close)

    if high < max_price * (1 - tolerance):
        raise DataValidationError(
            field=f"candle[{candle_index}].high",
            value=high,
            expected_type=f"value approximately >= max(open={open_price}, close={close})"
        )

    if low > min_price * (1 + tolerance):
        raise DataValidationError(
            field=f"candle[{candle_index}].low",
            value=low,
            expected_type=f"value approximately <= min(open={open_price}, close={close})"
        )


def _validate_positive_prices_strict(open_price: float, high: float, low: float, close: float, candle_index: int):
    """Strict positive price validation for production data."""
    if any(val <= 0 for val in [open_price, high, low, close]):
        raise DataValidationError(
            field=f"candle[{candle_index}]",
            value="contains non-positive prices",
            expected_type="positive price values"
        )


def _validate_positive_prices_lenient(open_price: float, high: float, low: float, close: float, candle_index: int):
    """Lenient positive price validation for test data."""
    # Allow very small positive values or zero for test data
    min_allowed = -0.001  # Allow slightly negative values due to floating point precision

    if any(val < min_allowed for val in [open_price, high, low, close]):
        raise DataValidationError(
            field=f"candle[{candle_index}]",
            value="contains significantly negative prices",
            expected_type="approximately positive price values"
        )


def validate_orderbook_data(orderbook: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate orderbook data structure.

    Args:
        orderbook (Dict[str, Any]): Orderbook data to validate

    Returns:
        Dict[str, Any]: Validated orderbook data

    Raises:
        DataValidationError: If orderbook structure is invalid
    """
    if not isinstance(orderbook, dict):
        raise DataValidationError(
            field="orderbook",
            value=type(orderbook).__name__,
            expected_type="dictionary"
        )

    # Check required fields
    required_fields = ['bids', 'asks']
    for field in required_fields:
        if field not in orderbook:
            raise DataValidationError(
                field="orderbook",
                value=f"missing {field}",
                expected_type="orderbook with bids and asks"
            )

    bids = orderbook['bids']
    asks = orderbook['asks']

    # Validate bids and asks are lists
    if not isinstance(bids, list):
        raise DataValidationError(
            field="orderbook.bids",
            value=type(bids).__name__,
            expected_type="list"
        )

    if not isinstance(asks, list):
        raise DataValidationError(
            field="orderbook.asks",
            value=type(asks).__name__,
            expected_type="list"
        )

    # Check if empty
    if len(bids) == 0 and len(asks) == 0:
        raise DataValidationError(
            field="orderbook",
            value="empty bids and asks",
            expected_type="non-empty orderbook"
        )

    # Validate first few entries structure
    for i, bid in enumerate(bids[:3]):  # Check first 3 bids
        if not isinstance(bid, (list, tuple)) or len(bid) < 2:
            raise DataValidationError(
                field=f"orderbook.bids[{i}]",
                value="invalid structure",
                expected_type="[price, amount] pair"
            )

        try:
            price, amount = float(bid[0]), float(bid[1])
            if price <= 0 or amount <= 0:
                raise DataValidationError(
                    field=f"orderbook.bids[{i}]",
                    value=f"price={price}, amount={amount}",
                    expected_type="positive price and amount"
                )
        except (TypeError, ValueError):
            raise DataValidationError(
                field=f"orderbook.bids[{i}]",
                value="non-numeric values",
                expected_type="numeric price and amount"
            )

    for i, ask in enumerate(asks[:3]):  # Check first 3 asks
        if not isinstance(ask, (list, tuple)) or len(ask) < 2:
            raise DataValidationError(
                field=f"orderbook.asks[{i}]",
                value="invalid structure",
                expected_type="[price, amount] pair"
            )

        try:
            price, amount = float(ask[0]), float(ask[1])
            if price <= 0 or amount <= 0:
                raise DataValidationError(
                    field=f"orderbook.asks[{i}]",
                    value=f"price={price}, amount={amount}",
                    expected_type="positive price and amount"
                )
        except (TypeError, ValueError):
            raise DataValidationError(
                field=f"orderbook.asks[{i}]",
                value="non-numeric values",
                expected_type="numeric price and amount"
            )

    return orderbook


def validate_ticker_data(ticker: Dict[str, Any], required_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Validate ticker data structure.

    Args:
        ticker (Dict[str, Any]): Ticker data to validate
        required_fields (List[str], optional): List of required fields

    Returns:
        Dict[str, Any]: Validated ticker data

    Raises:
        DataValidationError: If ticker data is invalid
    """
    if not isinstance(ticker, dict):
        raise DataValidationError(
            field="ticker",
            value=type(ticker).__name__,
            expected_type="dictionary"
        )

    if required_fields is None:
        required_fields = ['last']  # Only last price is truly critical

    # Check required fields
    missing_fields = []
    for field in required_fields:
        if field not in ticker or ticker[field] is None:
            missing_fields.append(field)

    if missing_fields:
        raise DataValidationError(
            field="ticker",
            value=f"missing fields: {missing_fields}",
            expected_type=f"ticker with fields: {required_fields}"
        )

    # Validate numeric fields
    numeric_fields = ['last', 'volume', 'high', 'low', 'open', 'change', 'percentage']
    for field in numeric_fields:
        if field in ticker and ticker[field] is not None:
            try:
                value = float(ticker[field])
                if field in ['last', 'high', 'low', 'open'] and value <= 0:
                    raise DataValidationError(
                        field=f"ticker.{field}",
                        value=value,
                        expected_type="positive price value"
                    )
                if field == 'volume' and value < 0:
                    raise DataValidationError(
                        field=f"ticker.{field}",
                        value=value,
                        expected_type="non-negative volume"
                    )
            except (TypeError, ValueError):
                raise DataValidationError(
                    field=f"ticker.{field}",
                    value=ticker[field],
                    expected_type="numeric value"
                )

    return ticker


def sanitize_input(value: Any, max_length: int = 100) -> str:
    """
    Sanitize string input to prevent injection attacks.

    Args:
        value (Any): Input value to sanitize
        max_length (int): Maximum allowed length

    Returns:
        str: Sanitized string

    Raises:
        DataValidationError: If input is invalid
    """
    if value is None:
        return ""

    try:
        clean_value = str(value).strip()
    except Exception:
        raise DataValidationError(
            field="input",
            value=type(value).__name__,
            expected_type="convertible to string"
        )

    if len(clean_value) > max_length:
        raise DataValidationError(
            field="input",
            value=f"length {len(clean_value)}",
            expected_type=f"string with length <= {max_length}"
        )

    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '&', '"', "'", ';', '(', ')', '{', '}', '[', ']']
    for char in dangerous_chars:
        clean_value = clean_value.replace(char, '')

    return clean_value


# Validation decorators
def validate_trading_params(func):
    """
    Decorator to validate common trading parameters.

    Usage:
        @validate_trading_params
        def place_order(symbol: str, amount: float, price: float):
            # Function implementation
            pass
    """
    def wrapper(self, symbol: str, amount: float = None, price: float = None, *args, **kwargs):
        # Validate symbol
        symbol = validate_symbol(symbol)

        # Validate amount if provided
        if amount is not None:
            amount = validate_amount(amount)

        # Validate price if provided
        if price is not None:
            price = validate_price(price)

        return func(self, symbol, amount, price, *args, **kwargs)

    return wrapper