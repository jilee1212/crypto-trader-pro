"""
Portfolio service for real-time account balance and portfolio management
"""

from typing import Dict, List, Any, Optional
from ..services.binance_client import BinanceClient
from ..services.binance_futures_client import BinanceFuturesClient
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class PortfolioService:
    def __init__(self, binance_client: BinanceClient, futures_client: Optional[BinanceFuturesClient] = None):
        self.spot_client = binance_client
        self.futures_client = futures_client

    async def get_account_balance(self) -> Dict[str, Any]:
        """계정 잔고 조회 with detailed logging"""
        try:
            logger.info("Fetching account balance from Binance API")
            results = {
                "success": True,
                "spot": {"balances": []},
                "futures": {"balances": [], "enabled": False},
                "total_value_usdt": 0.0,
                "last_updated": None
            }

            # Spot 계정 조회
            try:
                logger.debug("Fetching spot account information...")
                spot_account = self.spot_client.get_account_info()

                if spot_account.get("success", False):
                    spot_balances = []
                    total_spot_value = 0.0

                    for balance in spot_account.get("data", {}).get("balances", []):
                        asset = balance["asset"]
                        free = float(balance["free"])
                        locked = float(balance["locked"])
                        total = free + locked

                        if total > 0:  # Only include assets with balance
                            balance_info = {
                                "asset": asset,
                                "free": free,
                                "locked": locked,
                                "total": total,
                                "usd_value": 0.0  # Will be calculated later
                            }

                            # Calculate USD value for USDT
                            if asset == "USDT":
                                balance_info["usd_value"] = total
                                total_spot_value += total

                            spot_balances.append(balance_info)

                    results["spot"]["balances"] = spot_balances
                    results["total_value_usdt"] += total_spot_value
                    logger.info(f"Spot account: {len(spot_balances)} assets, total USDT value: {total_spot_value}")

                else:
                    logger.error(f"Spot account fetch failed: {spot_account.get('error', 'Unknown error')}")

            except Exception as e:
                logger.error(f"Error fetching spot account: {e}")
                results["spot"]["error"] = str(e)

            # Futures 계정 조회 (권한 있는 경우)
            if self.futures_client:
                try:
                    logger.debug("Fetching futures account information...")
                    futures_account = self.futures_client.get_account_info()

                    if futures_account.get("success", False):
                        futures_data = futures_account.get("data", {})
                        futures_balances = []

                        total_futures_value = float(futures_data.get("total_wallet_balance", 0))

                        for balance in futures_data.get("balances", []):
                            asset = balance["asset"]
                            wallet_balance = float(balance["wallet_balance"])
                            unrealized_profit = float(balance["unrealized_profit"])
                            margin_balance = float(balance["margin_balance"])

                            if wallet_balance > 0 or unrealized_profit != 0:
                                futures_balances.append({
                                    "asset": asset,
                                    "wallet_balance": wallet_balance,
                                    "unrealized_profit": unrealized_profit,
                                    "margin_balance": margin_balance,
                                    "available_balance": float(balance.get("available_balance", 0))
                                })

                        results["futures"] = {
                            "enabled": True,
                            "balances": futures_balances,
                            "total_wallet_balance": total_futures_value,
                            "total_unrealized_pnl": float(futures_data.get("total_unrealized_pnl", 0)),
                            "total_margin_balance": float(futures_data.get("total_margin_balance", 0))
                        }

                        results["total_value_usdt"] += total_futures_value
                        logger.info(f"Futures account: {len(futures_balances)} assets, total value: {total_futures_value}")

                    else:
                        logger.warning(f"Futures account fetch failed: {futures_account.get('error', 'Unknown error')}")
                        results["futures"]["error"] = futures_account.get("error", "Unknown error")

                except Exception as e:
                    logger.warning(f"Error fetching futures account (continuing without futures): {e}")
                    results["futures"]["error"] = str(e)

            # Set timestamp
            from datetime import datetime
            results["last_updated"] = datetime.utcnow().isoformat()

            logger.info(f"Portfolio fetch completed - Total value: {results['total_value_usdt']} USDT")
            return results

        except Exception as e:
            logger.error(f"Portfolio service error: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to fetch portfolio: {str(e)}")

    async def get_positions(self) -> Dict[str, Any]:
        """Get current trading positions"""
        try:
            results = {
                "success": True,
                "spot_positions": [],
                "futures_positions": []
            }

            # Get futures positions if available
            if self.futures_client:
                try:
                    positions_response = self.futures_client.get_positions()
                    if positions_response.get("success", False):
                        results["futures_positions"] = positions_response.get("data", [])
                        logger.info(f"Found {len(results['futures_positions'])} active futures positions")
                    else:
                        logger.warning(f"Failed to get futures positions: {positions_response.get('error', 'Unknown error')}")
                except Exception as e:
                    logger.warning(f"Error getting futures positions: {e}")

            return results

        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to get positions: {str(e)}")

    async def calculate_portfolio_performance(self) -> Dict[str, Any]:
        """Calculate portfolio performance metrics"""
        try:
            # This would be implemented with historical data
            # For now, return basic structure
            return {
                "success": True,
                "performance": {
                    "daily_pnl": 0.0,
                    "daily_pnl_percent": 0.0,
                    "total_realized_pnl": 0.0,
                    "total_unrealized_pnl": 0.0,
                    "roi": 0.0
                },
                "message": "Portfolio performance calculation not fully implemented yet"
            }
        except Exception as e:
            logger.error(f"Error calculating portfolio performance: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to calculate performance: {str(e)}")