#!/usr/bin/env python3
"""
Binance Testnet Connector using CCXT Official Examples
Simple implementation starting with account balance functionality
Based on: https://docs.ccxt.com/
"""

import ccxt
import os
from datetime import datetime
import logging

class BinanceTestnetConnector:
    """
    Simple Binance Testnet connector using CCXT official patterns
    Starting with basic account balance functionality
    """

    def __init__(self, api_key=None, secret_key=None):
        """
        Initialize Binance Testnet connection using CCXT
        """
        # Get API credentials from environment or parameters
        self.api_key = api_key or os.getenv('BINANCE_TESTNET_API_KEY', '')
        self.secret_key = secret_key or os.getenv('BINANCE_TESTNET_SECRET_KEY', '')

        # Initialize exchange with CCXT official pattern
        try:
            self.exchange = ccxt.binance({
                'apiKey': self.api_key,
                'secret': self.secret_key,
                'sandbox': True,  # Enable testnet mode
                'enableRateLimit': True,  # Enable rate limiting
                'options': {
                    'defaultType': 'spot',  # Use spot trading
                }
            })

            # Set testnet URLs
            self.exchange.set_sandbox_mode(True)

            print("[OK] CCXT Binance Testnet initialized successfully")

        except Exception as e:
            print(f"[ERROR] Failed to initialize CCXT exchange: {e}")
            self.exchange = None

    def test_connection(self):
        """
        Test connection to Binance Testnet
        Returns: dict with success status and basic info
        """
        try:
            if not self.exchange:
                return {
                    'success': False,
                    'error': 'Exchange not initialized',
                    'timestamp': datetime.now()
                }

            # Test connection with exchange info - no API key required
            markets = self.exchange.load_markets()

            return {
                'success': True,
                'exchange': 'Binance Testnet',
                'total_markets': len(markets),
                'has_api_key': bool(self.api_key),
                'timestamp': datetime.now()
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now()
            }

    def get_account_balance(self):
        """
        Get account balance using CCXT official method
        Returns: dict with balance information
        """
        try:
            if not self.exchange:
                return {
                    'success': False,
                    'error': 'Exchange not initialized'
                }

            if not self.api_key or not self.secret_key:
                return {
                    'success': False,
                    'error': 'API credentials required for balance check'
                }

            # Use CCXT official fetch_balance method
            balance = self.exchange.fetch_balance()

            # Extract useful balance information
            balances = {}
            for currency, data in balance.items():
                if currency not in ['info', 'free', 'used', 'total']:
                    if data['total'] > 0:  # Only show non-zero balances
                        balances[currency] = {
                            'free': data['free'],
                            'used': data['used'],
                            'total': data['total']
                        }

            return {
                'success': True,
                'balances': balances,
                'timestamp': datetime.now()
            }

        except ccxt.AuthenticationError as e:
            return {
                'success': False,
                'error': f'Authentication failed: {str(e)}'
            }
        except ccxt.NetworkError as e:
            return {
                'success': False,
                'error': f'Network error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }

    def get_current_price(self, symbol='BTC/USDT'):
        """
        Get current price for a symbol using CCXT official method
        Args: symbol (str): Trading pair symbol (e.g., 'BTC/USDT')
        Returns: dict with price information
        """
        try:
            if not self.exchange:
                return {
                    'success': False,
                    'error': 'Exchange not initialized'
                }

            # Use CCXT official fetch_ticker method
            ticker = self.exchange.fetch_ticker(symbol)

            return {
                'success': True,
                'symbol': ticker['symbol'],
                'price': ticker['last'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'volume': ticker['baseVolume'],
                'timestamp': datetime.fromtimestamp(ticker['timestamp'] / 1000)
            }

        except ccxt.BadSymbol as e:
            return {
                'success': False,
                'error': f'Invalid symbol {symbol}: {str(e)}'
            }
        except ccxt.NetworkError as e:
            return {
                'success': False,
                'error': f'Network error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }

    def get_exchange_info(self):
        """
        Get exchange information
        Returns: list of available symbols
        """
        try:
            if not self.exchange:
                return []

            markets = self.exchange.load_markets()
            return list(markets.keys())

        except Exception as e:
            print(f"[ERROR] Failed to get exchange info: {e}")
            return []

    def get_order_book(self, symbol='BTC/USDT', limit=10):
        """
        Get order book for a symbol
        Args:
            symbol (str): Trading pair symbol
            limit (int): Number of orders to fetch
        Returns: dict with bids and asks
        """
        try:
            if not self.exchange:
                return None

            # Use CCXT official fetch_order_book method
            orderbook = self.exchange.fetch_order_book(symbol, limit)

            return {
                'bids': orderbook['bids'][:limit],
                'asks': orderbook['asks'][:limit],
                'timestamp': datetime.fromtimestamp(orderbook['timestamp'] / 1000)
            }

        except Exception as e:
            print(f"[ERROR] Failed to get order book: {e}")
            return None

# Test the connector if run directly
if __name__ == "__main__":
    print("=== Testing New CCXT Binance Testnet Connector ===")

    # Initialize connector
    connector = BinanceTestnetConnector()

    # Test 1: Connection test
    print("\n1. Testing connection...")
    result = connector.test_connection()
    print(f"Connection test: {result}")

    # Test 2: Get current price (no API key required)
    print("\n2. Testing current price...")
    price_result = connector.get_current_price('BTC/USDT')
    print(f"BTC/USDT price: {price_result}")

    # Test 3: Account balance (requires API key)
    print("\n3. Testing account balance...")
    balance_result = connector.get_account_balance()
    print(f"Account balance: {balance_result}")

    print("\n=== Test completed ===")