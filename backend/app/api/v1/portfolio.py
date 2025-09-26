"""
Portfolio API endpoints for real-time balance and performance tracking
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from ...db.database import get_db
from ...auth.jwt_handler import get_current_user
from ...models.user import User
from ...services.portfolio_service import PortfolioService
from ...services.binance_client import BinanceClient
from ...services.binance_futures_client import BinanceFuturesClient
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def get_portfolio_service(current_user: User = Depends(get_current_user)) -> PortfolioService:
    """Create portfolio service with user's API credentials"""
    try:
        # Check if API keys are configured
        if not current_user.binance_api_key or not current_user.binance_api_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Binance API keys not configured. Please configure your API keys first."
            )

        # Create spot client
        spot_client = BinanceClient(
            api_key=current_user.binance_api_key,
            api_secret=current_user.binance_api_secret,
            testnet=False  # Always use LIVE trading
        )

        # Try to create futures client (optional)
        futures_client = None
        try:
            futures_client = BinanceFuturesClient(
                api_key=current_user.binance_api_key,
                api_secret=current_user.binance_api_secret
            )
            logger.debug("Futures client created successfully")
        except Exception as e:
            logger.warning(f"Failed to create futures client (continuing with spot only): {e}")

        return PortfolioService(spot_client, futures_client)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating portfolio service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize portfolio service: {str(e)}"
        )


@router.get("/balance")
async def get_account_balance(
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get real-time account balance from Binance"""
    try:
        logger.info(f"Fetching portfolio balance for user: {current_user.username}")
        balance_data = await portfolio_service.get_account_balance()
        return balance_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching account balance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch account balance: {str(e)}"
        )


@router.get("/positions")
async def get_trading_positions(
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current trading positions"""
    try:
        logger.info(f"Fetching trading positions for user: {current_user.username}")
        positions_data = await portfolio_service.get_positions()
        return positions_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch positions: {str(e)}"
        )


@router.get("/performance")
async def get_portfolio_performance(
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get portfolio performance metrics"""
    try:
        logger.info(f"Calculating portfolio performance for user: {current_user.username}")
        performance_data = await portfolio_service.calculate_portfolio_performance()
        return performance_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating portfolio performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate portfolio performance: {str(e)}"
        )


@router.get("/summary")
async def get_portfolio_summary(
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get complete portfolio summary"""
    try:
        logger.info(f"Fetching portfolio summary for user: {current_user.username}")

        # Get balance and positions concurrently
        balance_data = await portfolio_service.get_account_balance()
        positions_data = await portfolio_service.get_positions()
        performance_data = await portfolio_service.calculate_portfolio_performance()

        return {
            "success": True,
            "summary": {
                "balance": balance_data,
                "positions": positions_data,
                "performance": performance_data,
                "user": current_user.username,
                "trading_mode": "LIVE_MAINNET"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching portfolio summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch portfolio summary: {str(e)}"
        )