"""
Binance Futures API client for USDT-M Futures trading
"""

import os
import ccxt
from typing import Dict, List, Optional, Any
from decimal import Decimal
from binance.client import Client
from binance.exceptions import BinanceAPIException
import logging

logger = logging.getLogger(__name__)


class BinanceFuturesClient:
    def __init__(self, api_key: str, api_secret: str):
        """Initialize Binance Futures client for LIVE TRADING ONLY"""
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://fapi.binance.com"

        # Initialize python-binance client for LIVE futures trading
        self.client = Client(
            api_key,
            api_secret,
            testnet=False  # LIVE TRADING ONLY
        )

        # Initialize ccxt client for LIVE futures trading
        self.ccxt_client = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'sandbox': False,  # LIVE TRADING ONLY
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',  # Use futures API by default
            }
        })

    def test_connection(self) -> Dict[str, Any]:
        """Test futures API connection"""
        try:
            # Test futures connectivity
            account_info = self.client.futures_account()

            return {
                "success": True,
                "message": "LIVE Futures connection successful",
                "trading_mode": "LIVE",
                "can_trade": account_info.get('canTrade', False),
                "can_withdraw": account_info.get('canWithdraw', False),
                "can_deposit": account_info.get('canDeposit', False),
                "account_type": "FUTURES",
                "total_wallet_balance": float(account_info.get('totalWalletBalance', 0)),
                "total_unrealized_pnl": float(account_info.get('totalUnrealizedProfit', 0))
            }
        except BinanceAPIException as e:
            logger.error(f"Binance Futures API error: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": e.code if hasattr(e, 'code') else None
            }
        except Exception as e:
            logger.error(f"Futures connection test failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_account_info(self) -> Dict[str, Any]:
        """Get futures account information"""
        try:
            account = self.client.futures_account()
            return {
                "success": True,
                "data": {
                    "can_trade": account.get('canTrade', False),
                    "can_withdraw": account.get('canWithdraw', False),
                    "can_deposit": account.get('canDeposit', False),
                    "account_type": "FUTURES",
                    "total_wallet_balance": float(account.get('totalWalletBalance', 0)),
                    "total_unrealized_pnl": float(account.get('totalUnrealizedProfit', 0)),
                    "total_margin_balance": float(account.get('totalMarginBalance', 0)),
                    "available_balance": float(account.get('availableBalance', 0)),
                    "max_withdraw_amount": float(account.get('maxWithdrawAmount', 0)),
                    "balances": [
                        {
                            "asset": balance["asset"],
                            "wallet_balance": float(balance["walletBalance"]),
                            "unrealized_profit": float(balance["unrealizedProfit"]),
                            "margin_balance": float(balance["marginBalance"]),
                            "available_balance": float(balance["availableBalance"]),
                            "max_withdraw_amount": float(balance["maxWithdrawAmount"])
                        }
                        for balance in account.get("assets", [])
                        if float(balance["walletBalance"]) > 0 or float(balance["unrealizedProfit"]) != 0
                    ]
                }
            }
        except Exception as e:
            logger.error(f"Failed to get futures account info: {e}")
            return {"success": False, "error": str(e)}

    def get_positions(self) -> Dict[str, Any]:
        """Get current futures positions"""
        try:
            positions = self.client.futures_position_information()
            active_positions = []

            for position in positions:
                position_amt = float(position.get('positionAmt', 0))
                if position_amt != 0:  # Only include positions with size
                    active_positions.append({
                        "symbol": position["symbol"],
                        "position_amt": position_amt,
                        "entry_price": float(position.get('entryPrice', 0)),
                        "mark_price": float(position.get('markPrice', 0)),
                        "unrealized_pnl": float(position.get('unRealizedProfit', 0)),
                        "percentage": float(position.get('percentage', 0)),
                        "side": "LONG" if position_amt > 0 else "SHORT",
                        "leverage": int(position.get('leverage', 1)),
                        "margin_type": position.get('marginType', 'cross').lower(),
                        "isolated_margin": float(position.get('isolatedMargin', 0)),
                        "liquidation_price": float(position.get('liquidationPrice', 0)) if position.get('liquidationPrice') != '0' else None
                    })

            return {
                "success": True,
                "data": active_positions
            }
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return {"success": False, "error": str(e)}

    def get_24hr_ticker(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get futures 24hr ticker statistics"""
        try:
            if symbol:
                ticker = self.client.futures_ticker(symbol=symbol)
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
                        "quote_volume": float(ticker["quoteVolume"]),
                        "count": ticker["count"],
                        "open_interest": float(ticker.get("openInterest", 0))
                    }
                }
            else:
                tickers = self.client.futures_ticker()
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
                            "quote_volume": float(ticker["quoteVolume"]),
                            "count": ticker["count"],
                            "open_interest": float(ticker.get("openInterest", 0))
                        }
                        for ticker in tickers
                    ]
                }
        except Exception as e:
            logger.error(f"Failed to get futures 24hr ticker: {e}")
            return {"success": False, "error": str(e)}

    def place_order(self,
                   symbol: str,
                   side: str,
                   type: str,
                   quantity: float,
                   price: Optional[float] = None,
                   time_in_force: str = "GTC",
                   reduce_only: bool = False,
                   close_position: bool = False) -> Dict[str, Any]:
        """Place a futures order"""
        try:
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

            if reduce_only:
                order_params["reduceOnly"] = True

            if close_position:
                order_params["closePosition"] = True

            # LIVE TRADING - Real orders only
            result = self.client.futures_create_order(**order_params)
            return {
                "success": True,
                "message": "LIVE futures order placed successfully - REAL MONEY",
                "data": {
                    "order_id": result["orderId"],
                    "symbol": result["symbol"],
                    "status": result["status"],
                    "type": result["type"],
                    "side": result["side"],
                    "quantity": float(result["origQty"]),
                    "price": float(result["price"]) if result.get("price") and result["price"] != "0" else None,
                    "executed_qty": float(result["executedQty"]),
                    "cumulative_quote_qty": float(result["cumQuoteQty"]),
                    "time": result["updateTime"],
                    "reduce_only": result.get("reduceOnly", False),
                    "close_position": result.get("closePosition", False)
                }
            }

        except BinanceAPIException as e:
            logger.error(f"Binance Futures API error placing order: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": e.code if hasattr(e, 'code') else None
            }
        except Exception as e:
            logger.error(f"Failed to place futures order: {e}")
            return {"success": False, "error": str(e)}

    def get_open_orders(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get open futures orders"""
        try:
            if symbol:
                orders = self.client.futures_get_open_orders(symbol=symbol)
            else:
                orders = self.client.futures_get_open_orders()

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
                        "price": float(order["price"]) if order.get("price") else None,
                        "executed_qty": float(order["executedQty"]),
                        "cumulative_quote_qty": float(order["cumQuote"]),
                        "time": order["time"],
                        "reduce_only": order.get("reduceOnly", False),
                        "close_position": order.get("closePosition", False)
                    }
                    for order in orders
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get open futures orders: {e}")
            return {"success": False, "error": str(e)}

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel a futures order"""
        try:
            result = self.client.futures_cancel_order(symbol=symbol, orderId=order_id)
            return {
                "success": True,
                "data": {
                    "order_id": result["orderId"],
                    "symbol": result["symbol"],
                    "status": result["status"]
                }
            }
        except Exception as e:
            logger.error(f"Failed to cancel futures order: {e}")
            return {"success": False, "error": str(e)}

    def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """Set leverage for a symbol"""
        try:
            result = self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
            return {
                "success": True,
                "data": {
                    "symbol": result["symbol"],
                    "leverage": result["leverage"],
                    "max_notional_value": result.get("maxNotionalValue", "")
                }
            }
        except Exception as e:
            logger.error(f"Failed to set leverage: {e}")
            return {"success": False, "error": str(e)}

    def set_margin_type(self, symbol: str, margin_type: str) -> Dict[str, Any]:
        """Set margin type for a symbol (ISOLATED or CROSSED)"""
        try:
            result = self.client.futures_change_margin_type(symbol=symbol, marginType=margin_type.upper())
            return {
                "success": True,
                "data": {
                    "symbol": symbol,
                    "margin_type": margin_type.upper()
                }
            }
        except BinanceAPIException as e:
            # Margin type might already be set
            if e.code == -4046:
                return {
                    "success": True,
                    "message": f"Margin type {margin_type.upper()} already set for {symbol}",
                    "data": {
                        "symbol": symbol,
                        "margin_type": margin_type.upper()
                    }
                }
            logger.error(f"Failed to set margin type: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Failed to set margin type: {e}")
            return {"success": False, "error": str(e)}

    def get_exchange_info(self) -> Dict[str, Any]:
        """Get futures exchange information"""
        try:
            info = self.client.futures_exchange_info()
            return {
                "success": True,
                "data": {
                    "timezone": info.get("timezone"),
                    "server_time": info.get("serverTime"),
                    "symbols": [
                        {
                            "symbol": symbol["symbol"],
                            "base_asset": symbol["baseAsset"],
                            "quote_asset": symbol["quoteAsset"],
                            "status": symbol["status"],
                            "contract_type": symbol.get("contractType"),
                            "delivery_date": symbol.get("deliveryDate"),
                            "onboard_date": symbol.get("onboardDate"),
                            "price_precision": symbol["pricePrecision"],
                            "quantity_precision": symbol["quantityPrecision"],
                            "base_asset_precision": symbol["baseAssetPrecision"],
                            "quote_precision": symbol["quotePrecision"]
                        }
                        for symbol in info.get("symbols", [])
                        if symbol.get("contractType") == "PERPETUAL" and symbol.get("quoteAsset") == "USDT"
                    ]
                }
            }
        except Exception as e:
            logger.error(f"Failed to get exchange info: {e}")
            return {"success": False, "error": str(e)}

    def emergency_stop(self) -> Dict[str, Any]:
        """긴급 정지: 모든 선물 주문 취소 및 포지션 청산"""
        try:
            results = []

            # 1. 모든 열린 주문 취소
            open_orders = self.client.futures_get_open_orders()
            for order in open_orders:
                try:
                    cancel_result = self.client.futures_cancel_order(
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
            positions = self.client.futures_position_information()
            for position in positions:
                position_amt = float(position.get('positionAmt', 0))

                if position_amt != 0:  # 포지션이 있는 경우
                    symbol = position["symbol"]
                    side = "SELL" if position_amt > 0 else "BUY"  # 반대 방향으로 청산
                    quantity = abs(position_amt)

                    try:
                        # 시장가 청산 주문 (closePosition=True 사용)
                        sell_result = self.client.futures_create_order(
                            symbol=symbol,
                            side=side,
                            type="MARKET",
                            closePosition=True  # 전체 포지션 청산
                        )
                        results.append({
                            "action": "emergency_close_position",
                            "symbol": symbol,
                            "side": side,
                            "quantity": quantity,
                            "success": True,
                            "order_id": sell_result["orderId"]
                        })
                    except Exception as e:
                        results.append({
                            "action": "emergency_close_position",
                            "symbol": symbol,
                            "side": side,
                            "quantity": quantity,
                            "success": False,
                            "error": str(e)
                        })

            return {
                "success": True,
                "message": "Futures emergency stop executed",
                "results": results
            }

        except Exception as e:
            logger.error(f"Futures emergency stop failed: {e}")
            return {"success": False, "error": str(e)}

    def cancel_all_orders(self) -> Dict[str, Any]:
        """모든 열린 선물 주문 취소"""
        try:
            open_orders = self.client.futures_get_open_orders()
            results = []

            for order in open_orders:
                try:
                    result = self.client.futures_cancel_order(
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
                "message": f"Cancelled {len(results)} futures orders",
                "results": results
            }

        except Exception as e:
            logger.error(f"Failed to cancel all futures orders: {e}")
            return {"success": False, "error": str(e)}