"""API v1 router configuration."""

from fastapi import APIRouter

from .endpoints import auth
from . import binance, binance_futures, websocket, risk_management, ai_trading, portfolio

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(binance.router, prefix="", tags=["binance"])  # Keep for compatibility
api_router.include_router(binance_futures.router, prefix="", tags=["binance-futures"])
api_router.include_router(portfolio.router, prefix="", tags=["portfolio"])
api_router.include_router(websocket.router, prefix="", tags=["websocket"])
api_router.include_router(risk_management.router, prefix="", tags=["risk-management"])
api_router.include_router(ai_trading.router, prefix="", tags=["ai-trading"])