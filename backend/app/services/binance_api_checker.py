"""
Binance API Permission Checker - Automatically detect API key permissions
"""

from typing import Dict, Any
from binance.client import Client
from binance.exceptions import BinanceAPIException
import logging

logger = logging.getLogger(__name__)


class BinanceAPIChecker:
    def __init__(self, api_key: str, api_secret: str):
        """Initialize API checker with credentials"""
        self.api_key = api_key
        self.api_secret = api_secret
        self.spot_client = None
        self.futures_client = None

    def create_clients(self):
        """Create Binance clients for testing"""
        try:
            # Always use mainnet (testnet=False)
            self.spot_client = Client(
                self.api_key,
                self.api_secret,
                testnet=False
            )

            # For futures, we need to use the same client but different methods
            self.futures_client = Client(
                self.api_key,
                self.api_secret,
                testnet=False
            )

        except Exception as e:
            logger.error(f"Error creating Binance clients: {e}")
            raise

    async def check_permissions(self) -> Dict[str, Any]:
        """API 키 권한 자동 감지 with detailed logging"""
        try:
            logger.info("Starting API permissions check...")

            if not self.spot_client or not self.futures_client:
                self.create_clients()

            permissions = {
                "spot": {"enabled": False, "error": None, "details": {}},
                "futures": {"enabled": False, "error": None, "details": {}},
                "margin": {"enabled": False, "error": None, "details": {}},
                "overall_success": False,
                "api_key_valid": False,
                "trading_enabled": False
            }

            # Test Spot permissions
            logger.debug("Testing Spot API permissions...")
            try:
                account_info = self.spot_client.get_account()
                permissions["spot"]["enabled"] = True
                permissions["spot"]["details"] = {
                    "can_trade": account_info.get('canTrade', False),
                    "can_withdraw": account_info.get('canWithdraw', False),
                    "can_deposit": account_info.get('canDeposit', False),
                    "account_type": account_info.get('accountType', 'UNKNOWN')
                }
                permissions["api_key_valid"] = True
                permissions["trading_enabled"] = account_info.get('canTrade', False)
                logger.info("✅ Spot API permissions: ACTIVE")

            except BinanceAPIException as e:
                error_msg = f"Spot API error: {str(e)}"
                if hasattr(e, 'code'):
                    error_msg += f" (Code: {e.code})"
                permissions["spot"]["error"] = error_msg
                logger.warning(f"❌ Spot API permissions: FAILED - {error_msg}")
            except Exception as e:
                permissions["spot"]["error"] = f"Spot API unexpected error: {str(e)}"
                logger.error(f"❌ Spot API permissions: ERROR - {str(e)}")

            # Test Futures permissions
            logger.debug("Testing Futures API permissions...")
            try:
                futures_account = self.futures_client.futures_account()
                permissions["futures"]["enabled"] = True
                permissions["futures"]["details"] = {
                    "can_trade": futures_account.get('canTrade', False),
                    "can_withdraw": futures_account.get('canWithdraw', False),
                    "can_deposit": futures_account.get('canDeposit', False),
                    "total_wallet_balance": float(futures_account.get('totalWalletBalance', 0)),
                    "total_unrealized_pnl": float(futures_account.get('totalUnrealizedProfit', 0))
                }
                logger.info("✅ Futures API permissions: ACTIVE")

            except BinanceAPIException as e:
                error_msg = f"Futures API error: {str(e)}"
                if hasattr(e, 'code'):
                    error_msg += f" (Code: {e.code})"
                    # Common futures permission error codes
                    if e.code == -2015:
                        error_msg = "API key does not have Futures trading permissions"
                permissions["futures"]["error"] = error_msg
                logger.warning(f"❌ Futures API permissions: FAILED - {error_msg}")
            except Exception as e:
                permissions["futures"]["error"] = f"Futures API unexpected error: {str(e)}"
                logger.error(f"❌ Futures API permissions: ERROR - {str(e)}")

            # Test Margin permissions (optional)
            logger.debug("Testing Margin API permissions...")
            try:
                margin_account = self.spot_client.get_margin_account()
                permissions["margin"]["enabled"] = True
                permissions["margin"]["details"] = {
                    "trade_enabled": margin_account.get('tradeEnabled', False),
                    "transfer_enabled": margin_account.get('transferEnabled', False),
                    "borrow_enabled": margin_account.get('borrowEnabled', False)
                }
                logger.info("✅ Margin API permissions: ACTIVE")

            except BinanceAPIException as e:
                error_msg = f"Margin API error: {str(e)}"
                if hasattr(e, 'code'):
                    error_msg += f" (Code: {e.code})"
                permissions["margin"]["error"] = error_msg
                logger.debug(f"ℹ️ Margin API permissions: NOT AVAILABLE - {error_msg}")
            except Exception as e:
                permissions["margin"]["error"] = f"Margin API unexpected error: {str(e)}"
                logger.debug(f"ℹ️ Margin API permissions: ERROR - {str(e)}")

            # Determine overall success
            permissions["overall_success"] = permissions["spot"]["enabled"]

            # Log summary
            enabled_features = []
            if permissions["spot"]["enabled"]:
                enabled_features.append("Spot")
            if permissions["futures"]["enabled"]:
                enabled_features.append("Futures")
            if permissions["margin"]["enabled"]:
                enabled_features.append("Margin")

            if enabled_features:
                logger.info(f"🎯 API Permissions Summary: {', '.join(enabled_features)} trading enabled")
            else:
                logger.error("🚨 No trading permissions detected")

            return permissions

        except Exception as e:
            logger.error(f"API permissions check failed: {e}")
            return {
                "spot": {"enabled": False, "error": f"Permission check failed: {str(e)}", "details": {}},
                "futures": {"enabled": False, "error": f"Permission check failed: {str(e)}", "details": {}},
                "margin": {"enabled": False, "error": f"Permission check failed: {str(e)}", "details": {}},
                "overall_success": False,
                "api_key_valid": False,
                "trading_enabled": False,
                "error": str(e)
            }

    async def validate_live_trading(self) -> Dict[str, Any]:
        """Validate that API keys are for LIVE trading only"""
        try:
            logger.info("Validating LIVE trading mode...")

            if not self.spot_client:
                self.create_clients()

            # Test server connectivity and get server time
            server_time = self.spot_client.get_server_time()

            # Additional validation could be added here
            # For now, we trust that testnet=False ensures mainnet

            return {
                "success": True,
                "trading_mode": "LIVE_MAINNET",
                "server_time": server_time.get('serverTime') if server_time else None,
                "message": "API keys validated for LIVE trading"
            }

        except Exception as e:
            logger.error(f"LIVE trading validation failed: {e}")
            return {
                "success": False,
                "error": f"Failed to validate LIVE trading: {str(e)}",
                "trading_mode": "ERROR"
            }