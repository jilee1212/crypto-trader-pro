"""
Binance API client for testnet and mainnet
"""

import os
import ccxt
from typing import Dict, List, Optional, Any
from decimal import Decimal
from binance.client import Client
from binance.exceptions import BinanceAPIException
import logging
from ..core.trading_config import validate_order_amount, get_min_order_amount

logger = logging.getLogger(__name__)


class BinanceClient:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        """Initialize Binance client"""
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet

        # Initialize python-binance client
        self.client = Client(
            api_key,
            api_secret,
            testnet=testnet
        )

        # Initialize ccxt client for additional functionality
        self.ccxt_client = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'sandbox': testnet,
            'enableRateLimit': True,
        })

    def test_connection(self) -> Dict[str, Any]:
        """Test API connection and return account info with detailed logging"""
        try:
            logger.info(f"Testing Binance API connection - testnet mode: {self.testnet}")

            # 테스트넷은 항상 차단
            if self.testnet:
                logger.error("TESTNET mode blocked - only LIVE trading allowed")
                return {
                    "success": False,
                    "error": "TESTNET mode is permanently disabled. Only LIVE MAINNET trading is allowed.",
                    "testnet": True,
                    "trading_mode": "BLOCKED"
                }

            # Test server time first
            logger.debug("Testing server connectivity...")
            server_time = self.client.get_server_time()
            logger.debug(f"Server time received: {server_time}")

            # Test account access
            logger.debug("Fetching account information...")
            account_info = self.client.get_account()
            logger.info(f"Account info retrieved - canTrade: {account_info.get('canTrade', False)}")

            return {
                "success": True,
                "message": "LIVE MAINNET connection successful",
                "testnet": False,  # 항상 False 반환
                "trading_mode": "LIVE_MAINNET",
                "can_trade": account_info.get('canTrade', False),
                "can_withdraw": account_info.get('canWithdraw', False),
                "can_deposit": account_info.get('canDeposit', False),
                "account_type": account_info.get('accountType', 'UNKNOWN'),
                "server_time": server_time.get('serverTime') if server_time else None
            }

        except BinanceAPIException as e:
            logger.error(f"Binance API error: {e}")
            error_msg = f"Binance API Error: {str(e)}"
            if hasattr(e, 'code'):
                error_msg += f" (Code: {e.code})"
                logger.error(f"Error code: {e.code}")
            return {
                "success": False,
                "error": error_msg,
                "error_code": e.code if hasattr(e, 'code') else None,
                "testnet": False,
                "trading_mode": "ERROR"
            }
        except Exception as e:
            logger.error(f"Connection test failed with unexpected error: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            return {
                "success": False,
                "error": f"Connection failed: {str(e)}",
                "testnet": False,
                "trading_mode": "ERROR"
            }

    def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        try:
            account = self.client.get_account()
            return {
                "success": True,
                "data": {
                    "can_trade": account.get('canTrade', False),
                    "can_withdraw": account.get('canWithdraw', False),
                    "can_deposit": account.get('canDeposit', False),
                    "account_type": account.get('accountType'),
                    "balances": [
                        {
                            "asset": balance["asset"],
                            "free": float(balance["free"]),
                            "locked": float(balance["locked"])
                        }
                        for balance in account["balances"]
                        if float(balance["free"]) > 0 or float(balance["locked"]) > 0
                    ]
                }
            }
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return {"success": False, "error": str(e)}

    def get_ticker_prices(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get ticker prices for symbol or all symbols"""
        try:
            if symbol:
                ticker = self.client.get_symbol_ticker(symbol=symbol)
                return {
                    "success": True,
                    "data": {
                        "symbol": ticker["symbol"],
                        "price": float(ticker["price"])
                    }
                }
            else:
                tickers = self.client.get_all_tickers()
                return {
                    "success": True,
                    "data": [
                        {
                            "symbol": ticker["symbol"],
                            "price": float(ticker["price"])
                        }
                        for ticker in tickers
                    ]
                }
        except Exception as e:
            logger.error(f"Failed to get ticker prices: {e}")
            return {"success": False, "error": str(e)}

    def get_24hr_ticker(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get 24hr ticker statistics"""
        try:
            if symbol:
                ticker = self.client.get_ticker(symbol=symbol)
                return {
                    "success": True,
                    "data": {
                        "symbol": ticker["symbol"],
                        "price_change": float(ticker["priceChange"]),
                        "price_change_percent": float(ticker["priceChangePercent"]),
                        "last_price": float(ticker["lastPrice"]),
                        "high_price": float(ticker["highPrice"]),
                        "low_price": float(ticker["lowPrice"]),
                        "volume": float(ticker["volume"]),
                        "count": ticker["count"]
                    }
                }
            else:
                tickers = self.client.get_ticker()
                return {
                    "success": True,
                    "data": [
                        {
                            "symbol": ticker["symbol"],
                            "price_change": float(ticker["priceChange"]),
                            "price_change_percent": float(ticker["priceChangePercent"]),
                            "last_price": float(ticker["lastPrice"]),
                            "high_price": float(ticker["highPrice"]),
                            "low_price": float(ticker["lowPrice"]),
                            "volume": float(ticker["volume"]),
                            "count": ticker["count"]
                        }
                        for ticker in tickers
                    ]
                }
        except Exception as e:
            logger.error(f"Failed to get 24hr ticker: {e}")
            return {"success": False, "error": str(e)}

    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> Dict[str, Any]:
        """Get kline/candlestick data"""
        try:
            klines = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )

            return {
                "success": True,
                "data": [
                    {
                        "open_time": kline[0],
                        "open": float(kline[1]),
                        "high": float(kline[2]),
                        "low": float(kline[3]),
                        "close": float(kline[4]),
                        "volume": float(kline[5]),
                        "close_time": kline[6],
                        "quote_asset_volume": float(kline[7]),
                        "number_of_trades": kline[8],
                        "taker_buy_base_asset_volume": float(kline[9]),
                        "taker_buy_quote_asset_volume": float(kline[10])
                    }
                    for kline in klines
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get klines: {e}")
            return {"success": False, "error": str(e)}

    def place_order(self,
                   symbol: str,
                   side: str,
                   type: str,
                   quantity: float,
                   price: Optional[float] = None,
                   time_in_force: str = "GTC") -> Dict[str, Any]:
        """Place a new order"""
        try:
            # 주문 금액 검증 (메인넷에서만)
            if not self.testnet:
                if type == "MARKET":
                    # 시장가 주문: quantity * 현재가격으로 추정
                    current_price = float(self.client.get_symbol_ticker(symbol=symbol)["price"])
                    order_value = quantity * current_price
                else:
                    # 지정가 주문: quantity * price
                    if price is None:
                        raise ValueError("Price is required for LIMIT orders")
                    order_value = quantity * price

                if not validate_order_amount(symbol, order_value):
                    min_amount = get_min_order_amount(symbol)
                    raise ValueError(f"Order amount {order_value:.2f} USDT is below minimum {min_amount} USDT for {symbol}")

            order_params = {
                "symbol": symbol,
                "side": side,
                "type": type,
                "quantity": quantity,
            }

            if type == "LIMIT":
                if price is None:
                    raise ValueError("Price is required for LIMIT orders")
                order_params["price"] = price
                order_params["timeInForce"] = time_in_force

            # Use test order for safety in testnet
            if self.testnet:
                result = self.client.create_test_order(**order_params)
                return {
                    "success": True,
                    "message": "Test order placed successfully",
                    "data": result
                }
            else:
                result = self.client.create_order(**order_params)
                return {
                    "success": True,
                    "data": {
                        "order_id": result["orderId"],
                        "symbol": result["symbol"],
                        "status": result["status"],
                        "type": result["type"],
                        "side": result["side"],
                        "quantity": float(result["origQty"]),
                        "price": float(result["price"]) if result["price"] != "0.00000000" else None,
                        "executed_qty": float(result["executedQty"]),
                        "cumulative_quote_qty": float(result["cummulativeQuoteQty"]),
                        "time": result["transactTime"]
                    }
                }

        except BinanceAPIException as e:
            logger.error(f"Binance API error placing order: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": e.code if hasattr(e, 'code') else None
            }
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return {"success": False, "error": str(e)}

    def get_open_orders(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get open orders"""
        try:
            if symbol:
                orders = self.client.get_open_orders(symbol=symbol)
            else:
                orders = self.client.get_open_orders()

            return {
                "success": True,
                "data": [
                    {
                        "order_id": order["orderId"],
                        "symbol": order["symbol"],
                        "status": order["status"],
                        "type": order["type"],
                        "side": order["side"],
                        "quantity": float(order["origQty"]),
                        "price": float(order["price"]),
                        "executed_qty": float(order["executedQty"]),
                        "time": order["time"]
                    }
                    for order in orders
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            return {"success": False, "error": str(e)}

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an order"""
        try:
            result = self.client.cancel_order(symbol=symbol, orderId=order_id)
            return {
                "success": True,
                "data": {
                    "order_id": result["orderId"],
                    "symbol": result["symbol"],
                    "status": result["status"]
                }
            }
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            return {"success": False, "error": str(e)}

    def emergency_stop(self) -> Dict[str, Any]:
        """긴급 정지: 모든 열린 주문 취소 및 시장가 청산"""
        try:
            results = []

            # 1. 모든 열린 주문 취소
            open_orders = self.client.get_open_orders()
            for order in open_orders:
                try:
                    cancel_result = self.client.cancel_order(
                        symbol=order["symbol"],
                        orderId=order["orderId"]
                    )
                    results.append({
                        "action": "cancel_order",
                        "symbol": order["symbol"],
                        "order_id": order["orderId"],
                        "success": True
                    })
                except Exception as e:
                    results.append({
                        "action": "cancel_order",
                        "symbol": order["symbol"],
                        "order_id": order["orderId"],
                        "success": False,
                        "error": str(e)
                    })

            # 2. 모든 포지션을 시장가로 청산
            account = self.client.get_account()
            for balance in account["balances"]:
                asset = balance["asset"]
                free_amount = float(balance["free"])

                # USDT가 아니고 잔고가 있는 경우 시장가 매도
                if asset != "USDT" and free_amount > 0:
                    symbol = f"{asset}USDT"
                    try:
                        # 시장가 매도 주문
                        sell_result = self.client.create_order(
                            symbol=symbol,
                            side="SELL",
                            type="MARKET",
                            quantity=free_amount
                        )
                        results.append({
                            "action": "emergency_sell",
                            "symbol": symbol,
                            "quantity": free_amount,
                            "success": True,
                            "order_id": sell_result["orderId"]
                        })
                    except Exception as e:
                        results.append({
                            "action": "emergency_sell",
                            "symbol": symbol,
                            "quantity": free_amount,
                            "success": False,
                            "error": str(e)
                        })

            return {
                "success": True,
                "message": "Emergency stop executed",
                "results": results
            }

        except Exception as e:
            logger.error(f"Emergency stop failed: {e}")
            return {"success": False, "error": str(e)}

    def cancel_all_orders(self) -> Dict[str, Any]:
        """모든 열린 주문 취소"""
        try:
            open_orders = self.client.get_open_orders()
            results = []

            for order in open_orders:
                try:
                    result = self.client.cancel_order(
                        symbol=order["symbol"],
                        orderId=order["orderId"]
                    )
                    results.append({
                        "symbol": order["symbol"],
                        "order_id": order["orderId"],
                        "success": True
                    })
                except Exception as e:
                    results.append({
                        "symbol": order["symbol"],
                        "order_id": order["orderId"],
                        "success": False,
                        "error": str(e)
                    })

            return {
                "success": True,
                "message": f"Cancelled {len(results)} orders",
                "results": results
            }

        except Exception as e:
            logger.error(f"Failed to cancel all orders: {e}")
            return {"success": False, "error": str(e)}