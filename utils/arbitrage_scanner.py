"""
Arbitrage opportunity scanner for cryptocurrency trading bot.
Scans multiple exchanges for price differences and calculates profit potential.

Features:
- Multi-exchange price comparison (Binance, Coinbase, Kraken)
- Real-time arbitrage opportunity detection
- Fee-inclusive profit calculations
- Minimum profit threshold filtering (0.5%+)
- Risk assessment and execution time estimation
"""

import time
import ccxt
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from .market_data import MarketDataCollector
from .exceptions import (
    APIConnectionError,
    InvalidSymbolError,
    RateLimitError,
    DataValidationError,
    InsufficientDataError,
    NetworkTimeoutError
)

# Set up logging
logger = logging.getLogger(__name__)


class ExchangeManager:
    """
    Manages connections to multiple cryptocurrency exchanges.
    Provides unified interface for price data collection across exchanges.
    """

    def __init__(self,
                 exchanges: List[str] = None,
                 testnet: bool = True,
                 api_credentials: Dict[str, Dict[str, str]] = None):
        """
        Initialize exchange manager with multiple exchange connections.

        Args:
            exchanges (List[str]): List of exchange names to connect to
            testnet (bool): Use testnet/sandbox mode
            api_credentials (Dict[str, Dict[str, str]]): API credentials per exchange
        """
        if exchanges is None:
            exchanges = ['binance', 'coinbase', 'kraken']

        self.exchanges = {}
        self.testnet = testnet
        self.api_credentials = api_credentials or {}

        # Exchange-specific fee structures (maker/taker fees in %)
        self.exchange_fees = {
            'binance': {'maker': 0.1, 'taker': 0.1},
            'coinbase': {'maker': 0.5, 'taker': 0.5},
            'kraken': {'maker': 0.16, 'taker': 0.26}
        }

        # Initialize exchange connections
        self._initialize_exchanges(exchanges)

        logger.info(f"ExchangeManager initialized with {len(self.exchanges)} exchanges: {list(self.exchanges.keys())}")

    def _initialize_exchanges(self, exchange_names: List[str]):
        """Initialize connections to specified exchanges."""
        for exchange_name in exchange_names:
            try:
                # Get credentials for this exchange
                credentials = self.api_credentials.get(exchange_name, {})

                # Initialize exchange with appropriate settings
                if exchange_name == 'binance':
                    exchange = ccxt.binance({
                        'apiKey': credentials.get('api_key', ''),
                        'secret': credentials.get('api_secret', ''),
                        'sandbox': self.testnet,
                        'timeout': 30000,
                        'enableRateLimit': True,
                    })
                elif exchange_name == 'coinbase':
                    exchange = ccxt.coinbase({
                        'apiKey': credentials.get('api_key', ''),
                        'secret': credentials.get('api_secret', ''),
                        'passphrase': credentials.get('passphrase', ''),
                        'sandbox': self.testnet,
                        'timeout': 30000,
                        'enableRateLimit': True,
                    })
                elif exchange_name == 'kraken':
                    exchange = ccxt.kraken({
                        'apiKey': credentials.get('api_key', ''),
                        'secret': credentials.get('api_secret', ''),
                        'timeout': 30000,
                        'enableRateLimit': True,
                    })
                else:
                    logger.warning(f"Unsupported exchange: {exchange_name}")
                    continue

                self.exchanges[exchange_name] = exchange
                logger.debug(f"Successfully initialized {exchange_name} exchange")

            except Exception as e:
                logger.error(f"Failed to initialize {exchange_name}: {e}")
                # Continue with other exchanges even if one fails

    def get_price(self, exchange_name: str, symbol: str) -> Optional[float]:
        """
        Get current price from specific exchange.

        Args:
            exchange_name (str): Name of the exchange
            symbol (str): Trading symbol (e.g., 'BTC/USDT')

        Returns:
            Optional[float]: Current price or None if failed
        """
        if exchange_name not in self.exchanges:
            logger.error(f"Exchange {exchange_name} not available")
            return None

        try:
            exchange = self.exchanges[exchange_name]
            ticker = exchange.fetch_ticker(symbol)
            return float(ticker['last']) if ticker['last'] else None

        except Exception as e:
            logger.error(f"Failed to get price from {exchange_name} for {symbol}: {e}")
            return None

    def get_fees(self, exchange_name: str) -> Dict[str, float]:
        """
        Get trading fees for specified exchange.

        Args:
            exchange_name (str): Name of the exchange

        Returns:
            Dict[str, float]: Dictionary with maker and taker fees
        """
        return self.exchange_fees.get(exchange_name, {'maker': 0.25, 'taker': 0.25})

    def is_symbol_available(self, exchange_name: str, symbol: str) -> bool:
        """
        Check if symbol is available on specified exchange.

        Args:
            exchange_name (str): Name of the exchange
            symbol (str): Trading symbol

        Returns:
            bool: True if symbol is available
        """
        if exchange_name not in self.exchanges:
            return False

        try:
            exchange = self.exchanges[exchange_name]
            if not hasattr(exchange, 'markets') or not exchange.markets:
                exchange.load_markets()
            return symbol in exchange.markets
        except Exception as e:
            logger.error(f"Failed to check symbol availability on {exchange_name}: {e}")
            return False


class ArbitrageScanner:
    """
    Advanced arbitrage opportunity scanner for cryptocurrency trading.

    Features:
    - Multi-exchange price monitoring
    - Real-time arbitrage detection
    - Fee-inclusive profit calculations
    - Risk assessment and filtering
    """

    def __init__(self,
                 exchanges: List[str] = None,
                 min_profit_threshold: float = 0.5,
                 testnet: bool = True,
                 api_credentials: Dict[str, Dict[str, str]] = None,
                 enable_rate_limiting: bool = True):
        """
        Initialize arbitrage scanner.

        Args:
            exchanges (List[str]): List of exchanges to monitor
            min_profit_threshold (float): Minimum profit percentage (default: 0.5%)
            testnet (bool): Use testnet mode
            api_credentials (Dict): API credentials for exchanges
            enable_rate_limiting (bool): Enable rate limiting for API calls
        """
        self.min_profit_threshold = min_profit_threshold
        self.testnet = testnet
        self.enable_rate_limiting = enable_rate_limiting

        # Initialize exchange manager
        self.exchange_manager = ExchangeManager(
            exchanges=exchanges,
            testnet=testnet,
            api_credentials=api_credentials
        )

        # Initialize market data collector for primary exchange (Binance)
        self.market_data = MarketDataCollector(
            testnet=testnet,
            enable_rate_limiting=enable_rate_limiting
        )

        # Statistics tracking
        self.scan_count = 0
        self.opportunities_found = 0
        self.total_scan_time = 0

        logger.info(f"ArbitrageScanner initialized: {len(self.exchange_manager.exchanges)} exchanges, "
                   f"min_profit={min_profit_threshold}%")

    def scan_arbitrage_opportunities(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        Scan for arbitrage opportunities across multiple exchanges.

        Args:
            symbols (List[str]): List of trading symbols to scan

        Returns:
            List[Dict[str, Any]]: List of arbitrage opportunities with profit calculations
        """
        start_time = time.time()
        opportunities = []

        logger.info(f"Scanning arbitrage opportunities for {len(symbols)} symbols across "
                   f"{len(self.exchange_manager.exchanges)} exchanges")

        # Use ThreadPoolExecutor for concurrent price fetching
        with ThreadPoolExecutor(max_workers=min(len(symbols) * len(self.exchange_manager.exchanges), 10)) as executor:
            # Submit all price fetch tasks
            future_to_details = {}

            for symbol in symbols:
                for exchange_name in self.exchange_manager.exchanges:
                    # Check if symbol is available on this exchange
                    if not self.exchange_manager.is_symbol_available(exchange_name, symbol):
                        logger.debug(f"Symbol {symbol} not available on {exchange_name}")
                        continue

                    future = executor.submit(self._fetch_price_with_retry, exchange_name, symbol)
                    future_to_details[future] = (exchange_name, symbol)

            # Collect results
            price_data = {}
            for future in as_completed(future_to_details):
                exchange_name, symbol = future_to_details[future]
                try:
                    price = future.result(timeout=30)  # 30 second timeout
                    if price is not None:
                        if symbol not in price_data:
                            price_data[symbol] = {}
                        price_data[symbol][exchange_name] = price
                        logger.debug(f"Price fetched: {symbol} on {exchange_name} = {price}")
                except Exception as e:
                    logger.error(f"Failed to fetch price for {symbol} on {exchange_name}: {e}")

        # Analyze price differences for arbitrage opportunities
        for symbol, exchange_prices in price_data.items():
            if len(exchange_prices) < 2:
                logger.debug(f"Insufficient price data for {symbol}: only {len(exchange_prices)} exchanges")
                continue

            opportunities.extend(self._analyze_arbitrage_opportunities(symbol, exchange_prices))

        # Filter opportunities by minimum profit threshold
        filtered_opportunities = [
            opp for opp in opportunities
            if opp['net_profit_percent'] >= self.min_profit_threshold
        ]

        # Sort by profit percentage (descending)
        filtered_opportunities.sort(key=lambda x: x['net_profit_percent'], reverse=True)

        # Update statistics
        scan_time = time.time() - start_time
        self.scan_count += 1
        self.opportunities_found += len(filtered_opportunities)
        self.total_scan_time += scan_time

        logger.info(f"Arbitrage scan completed in {scan_time:.2f}s: "
                   f"{len(filtered_opportunities)} opportunities found (min {self.min_profit_threshold}%)")

        return filtered_opportunities

    def _fetch_price_with_retry(self, exchange_name: str, symbol: str, max_retries: int = 3) -> Optional[float]:
        """
        Fetch price with retry logic and rate limiting.

        Args:
            exchange_name (str): Exchange name
            symbol (str): Trading symbol
            max_retries (int): Maximum retry attempts

        Returns:
            Optional[float]: Price or None if failed
        """
        for attempt in range(max_retries):
            try:
                # Apply rate limiting if enabled
                if self.enable_rate_limiting:
                    time.sleep(0.1)  # Simple rate limiting - 10 calls per second max

                price = self.exchange_manager.get_price(exchange_name, symbol)
                if price is not None:
                    return price

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 0.5  # Exponential backoff
                    logger.debug(f"Retry {attempt + 1} for {symbol} on {exchange_name} in {wait_time}s")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All retries failed for {symbol} on {exchange_name}: {e}")

        return None

    def _analyze_arbitrage_opportunities(self, symbol: str, exchange_prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Analyze price differences and calculate arbitrage opportunities.

        Args:
            symbol (str): Trading symbol
            exchange_prices (Dict[str, float]): Prices from different exchanges

        Returns:
            List[Dict[str, Any]]: List of arbitrage opportunities
        """
        opportunities = []

        # Get all exchange combinations
        exchange_names = list(exchange_prices.keys())

        for i, buy_exchange in enumerate(exchange_names):
            for j, sell_exchange in enumerate(exchange_names):
                if i >= j:  # Avoid duplicate pairs and self-comparison
                    continue

                buy_price = exchange_prices[buy_exchange]
                sell_price = exchange_prices[sell_exchange]

                # Calculate gross profit
                if buy_price > 0:
                    gross_profit_percent = ((sell_price - buy_price) / buy_price) * 100
                else:
                    continue

                # Skip if gross profit is too low
                if gross_profit_percent < 0.1:  # Less than 0.1% gross profit
                    continue

                # Calculate net profit including fees
                net_profit_data = self._calculate_net_profit(
                    symbol, buy_exchange, sell_exchange, buy_price, sell_price
                )

                if net_profit_data['net_profit_percent'] > 0:
                    opportunity = {
                        'symbol': symbol,
                        'buy_exchange': buy_exchange,
                        'sell_exchange': sell_exchange,
                        'buy_price': buy_price,
                        'sell_price': sell_price,
                        'gross_profit_percent': round(gross_profit_percent, 3),
                        'net_profit_percent': round(net_profit_data['net_profit_percent'], 3),
                        'net_profit_amount': round(net_profit_data['net_profit_amount'], 6),
                        'total_fees_percent': round(net_profit_data['total_fees_percent'], 3),
                        'estimated_execution_time_seconds': net_profit_data['execution_time'],
                        'risk_level': self._assess_risk_level(net_profit_data['net_profit_percent']),
                        'timestamp': datetime.now().isoformat(),
                        'data_age_seconds': 0  # Real-time data
                    }
                    opportunities.append(opportunity)

        return opportunities

    def _calculate_net_profit(self, symbol: str, buy_exchange: str, sell_exchange: str,
                            buy_price: float, sell_price: float, trade_amount_usdt: float = 1000) -> Dict[str, Any]:
        """
        Calculate net profit including all fees and costs.

        Args:
            symbol (str): Trading symbol
            buy_exchange (str): Exchange to buy from
            sell_exchange (str): Exchange to sell to
            buy_price (float): Buy price
            sell_price (float): Sell price
            trade_amount_usdt (float): Trade amount in USDT for calculation

        Returns:
            Dict[str, Any]: Net profit calculation details
        """
        # Get fee structures
        buy_fees = self.exchange_manager.get_fees(buy_exchange)
        sell_fees = self.exchange_manager.get_fees(sell_exchange)

        # Calculate trade amounts
        crypto_amount = trade_amount_usdt / buy_price

        # Calculate buy costs (including taker fees)
        buy_fee_amount = trade_amount_usdt * (buy_fees['taker'] / 100)
        total_buy_cost = trade_amount_usdt + buy_fee_amount

        # Calculate sell proceeds (including taker fees)
        gross_sell_amount = crypto_amount * sell_price
        sell_fee_amount = gross_sell_amount * (sell_fees['taker'] / 100)
        net_sell_amount = gross_sell_amount - sell_fee_amount

        # Calculate net profit
        net_profit_amount = net_sell_amount - total_buy_cost
        net_profit_percent = (net_profit_amount / total_buy_cost) * 100

        # Total fees percentage
        total_fees_amount = buy_fee_amount + sell_fee_amount
        total_fees_percent = (total_fees_amount / trade_amount_usdt) * 100

        # Estimate execution time (simplified)
        execution_time = self._estimate_execution_time(buy_exchange, sell_exchange)

        return {
            'net_profit_amount': net_profit_amount,
            'net_profit_percent': net_profit_percent,
            'total_fees_percent': total_fees_percent,
            'buy_fee_percent': buy_fees['taker'],
            'sell_fee_percent': sell_fees['taker'],
            'execution_time': execution_time
        }

    def _estimate_execution_time(self, buy_exchange: str, sell_exchange: str) -> int:
        """
        Estimate execution time for arbitrage trade.

        Args:
            buy_exchange (str): Buy exchange
            sell_exchange (str): Sell exchange

        Returns:
            int: Estimated execution time in seconds
        """
        # Base execution times per exchange (in seconds)
        base_times = {
            'binance': 2,
            'coinbase': 5,
            'kraken': 8
        }

        buy_time = base_times.get(buy_exchange, 10)
        sell_time = base_times.get(sell_exchange, 10)

        # Add transfer time if different exchanges
        transfer_time = 30 if buy_exchange != sell_exchange else 0

        return buy_time + sell_time + transfer_time

    def _assess_risk_level(self, profit_percent: float) -> str:
        """
        Assess risk level based on profit percentage.

        Args:
            profit_percent (float): Net profit percentage

        Returns:
            str: Risk level ('low', 'medium', 'high')
        """
        if profit_percent >= 2.0:
            return 'low'
        elif profit_percent >= 1.0:
            return 'medium'
        else:
            return 'high'

    def get_supported_symbols(self) -> List[str]:
        """
        Get list of symbols supported across multiple exchanges.

        Returns:
            List[str]: List of commonly supported symbols
        """
        if not self.exchange_manager.exchanges:
            return []

        # Get symbols from first exchange
        first_exchange_name = list(self.exchange_manager.exchanges.keys())[0]
        first_exchange = self.exchange_manager.exchanges[first_exchange_name]

        try:
            if not hasattr(first_exchange, 'markets') or not first_exchange.markets:
                first_exchange.load_markets()

            all_symbols = set(first_exchange.markets.keys())

            # Find intersection with other exchanges
            for exchange_name, exchange in self.exchange_manager.exchanges.items():
                if exchange_name == first_exchange_name:
                    continue

                try:
                    if not hasattr(exchange, 'markets') or not exchange.markets:
                        exchange.load_markets()

                    exchange_symbols = set(exchange.markets.keys())
                    all_symbols = all_symbols.intersection(exchange_symbols)

                except Exception as e:
                    logger.error(f"Failed to load markets for {exchange_name}: {e}")

            # Filter for major trading pairs
            major_symbols = [
                symbol for symbol in all_symbols
                if any(quote in symbol for quote in ['USDT', 'USD', 'EUR', 'BTC', 'ETH'])
            ]

            return sorted(major_symbols)

        except Exception as e:
            logger.error(f"Failed to get supported symbols: {e}")
            return ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']  # Fallback symbols

    def get_scanner_stats(self) -> Dict[str, Any]:
        """
        Get scanner performance statistics.

        Returns:
            Dict[str, Any]: Scanner statistics
        """
        avg_scan_time = self.total_scan_time / max(self.scan_count, 1)
        opportunities_per_scan = self.opportunities_found / max(self.scan_count, 1)

        return {
            'total_scans': self.scan_count,
            'total_opportunities_found': self.opportunities_found,
            'opportunities_per_scan': round(opportunities_per_scan, 2),
            'average_scan_time_seconds': round(avg_scan_time, 2),
            'total_scan_time_seconds': round(self.total_scan_time, 2),
            'min_profit_threshold_percent': self.min_profit_threshold,
            'active_exchanges': list(self.exchange_manager.exchanges.keys()),
            'exchange_count': len(self.exchange_manager.exchanges)
        }

    def reset_stats(self):
        """Reset scanner statistics."""
        self.scan_count = 0
        self.opportunities_found = 0
        self.total_scan_time = 0
        logger.info("Scanner statistics reset")


# Utility functions for arbitrage analysis

def calculate_arbitrage_profit(buy_price: float, sell_price: float,
                             buy_fee_percent: float, sell_fee_percent: float,
                             amount: float = 1000) -> Dict[str, float]:
    """
    Calculate arbitrage profit for given parameters.

    Args:
        buy_price (float): Price to buy at
        sell_price (float): Price to sell at
        buy_fee_percent (float): Buy fee percentage
        sell_fee_percent (float): Sell fee percentage
        amount (float): Trade amount in quote currency

    Returns:
        Dict[str, float]: Profit calculation details
    """
    # Calculate amounts
    crypto_amount = amount / buy_price

    # Buy costs
    buy_fee = amount * (buy_fee_percent / 100)
    total_buy_cost = amount + buy_fee

    # Sell proceeds
    gross_sell = crypto_amount * sell_price
    sell_fee = gross_sell * (sell_fee_percent / 100)
    net_sell = gross_sell - sell_fee

    # Profit
    net_profit = net_sell - total_buy_cost
    profit_percent = (net_profit / total_buy_cost) * 100

    return {
        'net_profit': net_profit,
        'profit_percent': profit_percent,
        'total_fees': buy_fee + sell_fee,
        'total_cost': total_buy_cost,
        'net_proceeds': net_sell
    }


def filter_arbitrage_opportunities(opportunities: List[Dict[str, Any]],
                                 min_profit: float = 0.5,
                                 max_risk: str = 'high',
                                 max_execution_time: int = 300) -> List[Dict[str, Any]]:
    """
    Filter arbitrage opportunities based on criteria.

    Args:
        opportunities (List[Dict[str, Any]]): List of opportunities
        min_profit (float): Minimum profit percentage
        max_risk (str): Maximum risk level ('low', 'medium', 'high')
        max_execution_time (int): Maximum execution time in seconds

    Returns:
        List[Dict[str, Any]]: Filtered opportunities
    """
    risk_levels = {'low': 3, 'medium': 2, 'high': 1}
    max_risk_value = risk_levels.get(max_risk, 1)

    filtered = []
    for opp in opportunities:
        # Check profit threshold
        if opp['net_profit_percent'] < min_profit:
            continue

        # Check risk level
        opp_risk_value = risk_levels.get(opp['risk_level'], 1)
        if opp_risk_value > max_risk_value:
            continue

        # Check execution time
        if opp['estimated_execution_time_seconds'] > max_execution_time:
            continue

        filtered.append(opp)

    return filtered