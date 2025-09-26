"""
Binance Futures API endpoints - USDT-M Futures Trading
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Dict

from ...db.database import get_db
from ...services.binance_futures_client import BinanceFuturesClient
from ...schemas.futures_trading import (
    FuturesTestResponse,
    FuturesAccountInfoResponse,
    FuturesMarketDataResponse,
    FuturesOrderRequest,
    FuturesOrderResponse,
    OpenFuturesOrdersResponse,
    PositionsResponse,
    LeverageRequest,
    LeverageResponse,
    MarginTypeRequest,
    MarginTypeResponse,
    FuturesExchangeInfoResponse,
    EmergencyStopResponse
)
from ...schemas.trading import ApiKeysRequest  # Keep this for compatibility
from ...auth.jwt_handler import get_current_user
from ...models.user import User
from ...core.futures_position_manager import FuturesPositionManager, FuturesPosition
from ...core.ai_risk_manager import AIRiskManager
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/binance/futures", tags=["binance-futures"])


@router.get("/check-ip")
async def check_server_ip():
    """서버의 외부 IP 주소 확인 - 바이낸스 IP 화이트리스트용"""
    try:
        import requests
        import aiohttp
        import asyncio

        # 여러 IP 확인 서비스를 통해 IP 확인
        ip_services = [
            "https://api.ipify.org?format=json",
            "https://httpbin.org/ip",
            "https://api64.ipify.org?format=json"
        ]

        results = {}

        # 동기적으로 requests 사용
        for i, service in enumerate(ip_services):
            try:
                response = requests.get(service, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if 'ip' in data:
                        results[f'service_{i+1}'] = data['ip']
                    elif 'origin' in data:
                        results[f'service_{i+1}'] = data['origin']
            except Exception as e:
                results[f'service_{i+1}_error'] = str(e)

        # 현재 시간 추가
        from datetime import datetime
        results['timestamp'] = datetime.now().isoformat()
        results['message'] = "이 IP를 바이낸스 API 설정에서 화이트리스트에 추가하세요"

        return results

    except Exception as e:
        return {
            "error": f"IP 확인 실패: {str(e)}",
            "message": "서버에서 외부 IP를 확인할 수 없습니다"
        }


def get_binance_futures_client(user: User) -> BinanceFuturesClient:
    """Get Binance Futures client for user"""
    if not user.binance_api_key or not user.binance_api_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Binance Futures API keys not configured"
        )

    return BinanceFuturesClient(
        api_key=user.binance_api_key,
        api_secret=user.binance_api_secret
    )


@router.post("/configure-keys")
async def configure_futures_api_keys(
    keys: ApiKeysRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Configure Binance Futures API keys for user"""
    try:
        # Test the LIVE Futures API keys first
        client = BinanceFuturesClient(
            api_key=keys.api_key,
            api_secret=keys.api_secret
        )

        test_result = client.test_connection()
        if not test_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Futures API key validation failed: {test_result.get('error', 'Unknown error')}"
            )

        # Update user's API keys if test passes
        current_user.binance_api_key = keys.api_key
        current_user.binance_api_secret = keys.api_secret
        current_user.use_testnet = False  # LIVE TRADING ONLY
        db.commit()

        return {
            "success": True,
            "message": "LIVE Futures API keys configured successfully - REAL TRADING",
            "trading_mode": "LIVE",
            "account_type": "FUTURES"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error configuring Futures API keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to configure Futures API keys"
        )


@router.get("/test-connection", response_model=FuturesTestResponse)
async def test_futures_connection(
    current_user: User = Depends(get_current_user)
):
    """Test Binance Futures API connection"""
    try:
        client = get_binance_futures_client(current_user)
        result = client.test_connection()

        return FuturesTestResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Futures connection test failed: {e}")
        return FuturesTestResponse(
            success=False,
            error=str(e),
            trading_mode="LIVE"
        )


@router.get("/account", response_model=FuturesAccountInfoResponse)
async def get_futures_account_info(
    current_user: User = Depends(get_current_user)
):
    """Get futures account information"""
    # Check if API keys are configured first
    if not current_user.binance_api_key or not current_user.binance_api_secret:
        return FuturesAccountInfoResponse(
            success=False,
            error="API keys not configured. Please configure your Binance API keys first."
        )

    try:
        client = get_binance_futures_client(current_user)
        result = client.get_account_info()

        return FuturesAccountInfoResponse(**result)

    except HTTPException as he:
        logger.error(f"HTTPException in get futures account info: {he.detail}")
        return FuturesAccountInfoResponse(
            success=False,
            error=str(he.detail)
        )
    except Exception as e:
        logger.error(f"Failed to get futures account info: {e}")
        return FuturesAccountInfoResponse(
            success=False,
            error="Failed to retrieve futures account information. Please check your API keys."
        )


@router.get("/positions", response_model=PositionsResponse)
async def get_positions(
    current_user: User = Depends(get_current_user)
):
    """Get current futures positions"""
    # Check if API keys are configured first
    if not current_user.binance_api_key or not current_user.binance_api_secret:
        return PositionsResponse(
            success=False,
            error="API keys not configured. Please configure your Binance API keys first."
        )

    try:
        client = get_binance_futures_client(current_user)
        result = client.get_positions()

        return PositionsResponse(**result)

    except HTTPException as he:
        logger.error(f"HTTPException in get positions: {he.detail}")
        return PositionsResponse(
            success=False,
            error=str(he.detail)
        )
    except Exception as e:
        logger.error(f"Failed to get positions: {e}")
        return PositionsResponse(
            success=False,
            error="Failed to retrieve positions. Please check your API keys."
        )


@router.get("/ticker/24hr", response_model=FuturesMarketDataResponse)
async def get_futures_24hr_ticker(
    symbol: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get futures 24hr ticker statistics"""
    try:
        client = get_binance_futures_client(current_user)
        result = client.get_24hr_ticker(symbol)

        return FuturesMarketDataResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get futures 24hr ticker: {e}")
        return FuturesMarketDataResponse(
            success=False,
            error=str(e)
        )


@router.get("/exchange-info", response_model=FuturesExchangeInfoResponse)
async def get_futures_exchange_info(
    current_user: User = Depends(get_current_user)
):
    """Get futures exchange information"""
    try:
        client = get_binance_futures_client(current_user)
        result = client.get_exchange_info()

        return FuturesExchangeInfoResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get exchange info: {e}")
        return FuturesExchangeInfoResponse(
            success=False,
            error=str(e)
        )


@router.post("/order", response_model=FuturesOrderResponse)
async def place_futures_order(
    order: FuturesOrderRequest,
    current_user: User = Depends(get_current_user)
):
    """Place a futures order"""
    try:
        client = get_binance_futures_client(current_user)
        result = client.place_order(
            symbol=order.symbol,
            side=order.side,
            type=order.type,
            quantity=order.quantity,
            price=order.price,
            time_in_force=order.time_in_force,
            reduce_only=order.reduce_only,
            close_position=order.close_position
        )

        return FuturesOrderResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to place futures order: {e}")
        return FuturesOrderResponse(
            success=False,
            error=str(e)
        )


@router.get("/orders/open", response_model=OpenFuturesOrdersResponse)
async def get_open_futures_orders(
    symbol: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get open futures orders"""
    try:
        client = get_binance_futures_client(current_user)
        result = client.get_open_orders(symbol)

        return OpenFuturesOrdersResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get open futures orders: {e}")
        return OpenFuturesOrdersResponse(
            success=False,
            error=str(e)
        )


@router.delete("/order")
async def cancel_futures_order(
    symbol: str,
    order_id: int,
    current_user: User = Depends(get_current_user)
):
    """Cancel a futures order"""
    try:
        client = get_binance_futures_client(current_user)
        result = client.cancel_order(symbol, order_id)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel futures order: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/leverage", response_model=LeverageResponse)
async def set_leverage(
    leverage_request: LeverageRequest,
    current_user: User = Depends(get_current_user)
):
    """Set leverage for a symbol"""
    try:
        client = get_binance_futures_client(current_user)
        result = client.set_leverage(leverage_request.symbol, leverage_request.leverage)

        return LeverageResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set leverage: {e}")
        return LeverageResponse(
            success=False,
            error=str(e)
        )


@router.post("/margin-type", response_model=MarginTypeResponse)
async def set_margin_type(
    margin_request: MarginTypeRequest,
    current_user: User = Depends(get_current_user)
):
    """Set margin type for a symbol (ISOLATED or CROSSED)"""
    try:
        client = get_binance_futures_client(current_user)
        result = client.set_margin_type(margin_request.symbol, margin_request.margin_type)

        return MarginTypeResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set margin type: {e}")
        return MarginTypeResponse(
            success=False,
            error=str(e)
        )


@router.post("/emergency-stop", response_model=EmergencyStopResponse)
async def emergency_stop_futures(
    current_user: User = Depends(get_current_user)
):
    """긴급 정지: 모든 선물 주문 취소 및 포지션 청산"""
    try:
        client = get_binance_futures_client(current_user)
        result = client.emergency_stop()

        return EmergencyStopResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Futures emergency stop failed: {e}")
        return EmergencyStopResponse(
            success=False,
            error=str(e)
        )


@router.post("/cancel-all-orders", response_model=EmergencyStopResponse)
async def cancel_all_futures_orders(
    current_user: User = Depends(get_current_user)
):
    """모든 열린 선물 주문 취소"""
    try:
        client = get_binance_futures_client(current_user)
        result = client.cancel_all_orders()

        return EmergencyStopResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cancel all futures orders failed: {e}")
        return EmergencyStopResponse(
            success=False,
            error=str(e)
        )


@router.get("/popular-pairs")
async def get_popular_futures_pairs():
    """Get popular futures trading pairs - No API key required (public data)"""
    import requests
    try:
        # Popular USDT-M futures pairs
        popular_pairs = [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "DOTUSDT",
            "XRPUSDT", "SOLUSDT", "MATICUSDT", "LTCUSDT", "AVAXUSDT",
            "LINKUSDT", "UNIUSDT", "ATOMUSDT", "VETUSDT", "TRXUSDT"
        ]

        # Use public Binance Futures API (no authentication required)
        url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
        response = requests.get(url)
        response.raise_for_status()
        all_tickers = response.json()

        # Filter for popular pairs
        popular_data = []
        ticker_dict = {ticker["symbol"]: ticker for ticker in all_tickers}

        for pair in popular_pairs:
            if pair in ticker_dict:
                ticker = ticker_dict[pair]
                popular_data.append({
                    "symbol": ticker["symbol"],
                    "price": float(ticker["lastPrice"]),
                    "change_24h": float(ticker["priceChange"]),
                    "change_percent_24h": float(ticker["priceChangePercent"]),
                    "volume_24h": float(ticker["volume"]),
                    "open_interest": 0  # Open interest requires separate API call
                })

        return {
            "success": True,
            "data": popular_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get popular futures pairs: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# Mock endpoints for testing without API keys
@router.get("/popular-pairs/mock")
async def get_popular_futures_pairs_mock():
    """Get mock popular futures trading pairs for testing"""
    return {
        "success": True,
        "data": [
            {
                "symbol": "BTCUSDT",
                "price": "43250.00",
                "change_24h": "+1250.00",
                "change_percent_24h": "+2.98",
                "volume_24h": "28567.45",
                "open_interest": "156234.50"
            },
            {
                "symbol": "ETHUSDT",
                "price": "2650.00",
                "change_24h": "-45.50",
                "change_percent_24h": "-1.69",
                "volume_24h": "156789.12",
                "open_interest": "89456.20"
            },
            {
                "symbol": "BNBUSDT",
                "price": "315.80",
                "change_24h": "+8.40",
                "change_percent_24h": "+2.73",
                "volume_24h": "45621.30",
                "open_interest": "23456.78"
            }
        ]
    }


@router.get("/ticker/24hr/mock")
async def get_futures_24hr_ticker_mock():
    """Get mock futures 24hr ticker for testing"""
    return {
        "success": True,
        "data": [
            {
                "symbol": "BTCUSDT",
                "last_price": "43250.00",
                "price_change": "+1250.00",
                "price_change_percent": "+2.98",
                "volume": "28567.45",
                "open_interest": "156234.50"
            },
            {
                "symbol": "ETHUSDT",
                "last_price": "2650.00",
                "price_change": "-45.50",
                "price_change_percent": "-1.69",
                "volume": "156789.12",
                "open_interest": "89456.20"
            }
        ]
    }


@router.get("/positions/mock")
async def get_positions_mock():
    """Get mock positions for testing"""
    return {
        "success": True,
        "data": [
            {
                "symbol": "BTCUSDT",
                "position_amt": 0.05,
                "entry_price": 42000.0,
                "mark_price": 43250.0,
                "unrealized_pnl": 62.5,
                "percentage": 2.98,
                "side": "LONG",
                "leverage": 10,
                "margin_type": "cross",
                "isolated_margin": 0.0,
                "liquidation_price": 38500.0
            }
        ]
    }


@router.get("/account/mock")
async def get_futures_account_mock():
    """Get mock futures account information for testing"""
    return {
        "success": True,
        "data": {
            "account_type": "FUTURES",
            "can_trade": True,
            "can_withdraw": True,
            "can_deposit": True,
            "total_wallet_balance": 1000.0,
            "total_unrealized_pnl": 125.50,
            "total_margin_balance": 1125.50,
            "available_balance": 900.0,
            "max_withdraw_amount": 900.0,
            "balances": [
                {
                    "asset": "USDT",
                    "wallet_balance": 1000.0,
                    "unrealized_profit": 125.50,
                    "margin_balance": 1125.50,
                    "available_balance": 900.0,
                    "max_withdraw_amount": 900.0
                }
            ]
        }
    }


@router.get("/orders/open/mock")
async def get_open_futures_orders_mock():
    """Get mock open futures orders for testing"""
    return {
        "success": True,
        "data": [
            {
                "order_id": 12345678,
                "symbol": "BTCUSDT",
                "side": "BUY",
                "type": "LIMIT",
                "quantity": 0.01,
                "price": 42000.00,
                "executed_qty": 0.0,
                "status": "NEW",
                "time": 1727236200000,
                "reduce_only": False,
                "close_position": False
            }
        ]
    }


# 글로벌 포지션 매니저
position_managers = {}  # user_id -> FuturesPositionManager


@router.post("/calculate-risk")
async def calculate_futures_risk(
    risk_data: Dict,
    current_user: User = Depends(get_current_user)
):
    """선물 거래 리스크 계산"""
    try:
        account_balance = float(risk_data["account_balance"])
        entry_price = float(risk_data["entry_price"])
        stop_loss_price = float(risk_data["stop_loss_price"])
        risk_percentage = float(risk_data.get("risk_percentage", 3.0))

        # AI 리스크 매니저 초기화
        risk_manager = AIRiskManager(account_balance, risk_percentage)

        # 포지션 사이징 계산
        result = risk_manager.calculate_position_size(entry_price, stop_loss_price)

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"Risk calculation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"리스크 계산 실패: {str(e)}"
        )


@router.get("/calculate-risk/mock")
async def calculate_futures_risk_mock():
    """Mock 리스크 계산 (테스트용)"""
    return {
        "success": True,
        "data": {
            "position_value": 1200.0,
            "position_quantity": 0.03,
            "leverage": 4,
            "seed_usage_percent": 75.0,
            "margin_used": 300.0,
            "actual_multiplier": 3.0,
            "target_multiplier": 3.0,
            "target_risk_amount": 120.0,
            "actual_risk_amount": 120.0,
            "risk_accuracy": 100.0,
            "optimization_notes": "최적 조합 발견 (오차: 0.00%)",
            "warning": None,
            "recommendation": "추천: 4배 레버리지 + 75% 시드 사용"
        }
    }


@router.post("/position/create")
async def create_position(
    position_data: Dict,
    current_user: User = Depends(get_current_user)
):
    """새 선물 포지션 생성"""
    try:
        user_id = current_user.id

        # 사용자별 포지션 매니저 초기화
        if user_id not in position_managers:
            position_managers[user_id] = FuturesPositionManager()

        manager = position_managers[user_id]

        # 포지션 생성
        position = manager.add_position(position_data)

        return {
            "success": True,
            "data": {
                "position_id": f"{position.symbol}_{position.side}",
                "symbol": position.symbol,
                "side": position.side,
                "entry_price": position.entry_price,
                "quantity": position.quantity,
                "leverage": position.leverage,
                "margin_used": position.margin_used,
                "risk_level": position.risk_level.value,
                "entry_time": position.entry_time.isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Position creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"포지션 생성 실패: {str(e)}"
        )


@router.get("/positions/portfolio")
async def get_portfolio_summary(
    current_user: User = Depends(get_current_user)
):
    """포트폴리오 요약 정보"""
    try:
        user_id = current_user.id

        if user_id not in position_managers:
            position_managers[user_id] = FuturesPositionManager()

        manager = position_managers[user_id]
        summary = manager.get_portfolio_summary()

        return {
            "success": True,
            "data": summary
        }

    except Exception as e:
        logger.error(f"Portfolio summary failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"포트폴리오 조회 실패: {str(e)}"
        )


@router.get("/positions/portfolio/mock")
async def get_portfolio_summary_mock():
    """Mock 포트폴리오 요약"""
    return {
        "success": True,
        "data": {
            "total_positions": 3,
            "total_margin_used": 1500.0,
            "total_unrealized_pnl": 125.5,
            "risk_distribution": {
                "low": 2,
                "medium": 1,
                "high": 0,
                "critical": 0
            },
            "positions": [
                {
                    "symbol": "BTCUSDT",
                    "side": "LONG",
                    "entry_price": 42000.0,
                    "current_price": 42500.0,
                    "quantity": 0.02,
                    "leverage": 5,
                    "margin_used": 500.0,
                    "unrealized_pnl": 200.0,
                    "pnl_percentage": 11.9,
                    "risk_level": "low",
                    "liquidation_price": 35000.0
                },
                {
                    "symbol": "ETHUSDT",
                    "side": "SHORT",
                    "entry_price": 3200.0,
                    "current_price": 3150.0,
                    "quantity": 0.5,
                    "leverage": 3,
                    "margin_used": 600.0,
                    "unrealized_pnl": 75.0,
                    "pnl_percentage": 3.9,
                    "risk_level": "low",
                    "liquidation_price": 4100.0
                },
                {
                    "symbol": "ADAUSDT",
                    "side": "LONG",
                    "entry_price": 1.2,
                    "current_price": 1.15,
                    "quantity": 300,
                    "leverage": 2,
                    "margin_used": 400.0,
                    "unrealized_pnl": -150.0,
                    "pnl_percentage": -8.3,
                    "risk_level": "medium",
                    "liquidation_price": 0.8
                }
            ]
        }
    }


@router.post("/position/close")
async def close_position(
    close_data: Dict,
    current_user: User = Depends(get_current_user)
):
    """포지션 청산"""
    try:
        user_id = current_user.id
        symbol = close_data["symbol"]
        side = close_data["side"]
        close_price = float(close_data["close_price"])
        reason = close_data.get("reason", "Manual")

        if user_id not in position_managers:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="포지션을 찾을 수 없습니다"
            )

        manager = position_managers[user_id]
        success = manager.close_position(symbol, side, close_price, reason)

        if success:
            return {
                "success": True,
                "message": f"포지션 청산 완료: {symbol}_{side}",
                "close_price": close_price,
                "reason": reason
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 포지션을 찾을 수 없습니다"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Position close failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"포지션 청산 실패: {str(e)}"
        )


@router.get("/trading/statistics")
async def get_trading_statistics(
    current_user: User = Depends(get_current_user)
):
    """거래 통계 정보"""
    try:
        user_id = current_user.id

        if user_id not in position_managers:
            position_managers[user_id] = FuturesPositionManager()

        manager = position_managers[user_id]

        # 간단한 통계 계산
        active_count = len([pos for pos in manager.positions.values()])
        history_count = len(manager.position_history)

        total_pnl = sum(h["pnl"] for h in manager.position_history)
        winning_trades = len([h for h in manager.position_history if h["pnl"] > 0])

        win_rate = (winning_trades / history_count * 100) if history_count > 0 else 0

        return {
            "success": True,
            "data": {
                "active_positions": active_count,
                "total_trades": history_count,
                "winning_trades": winning_trades,
                "losing_trades": history_count - winning_trades,
                "win_rate": round(win_rate, 1),
                "total_pnl": round(total_pnl, 2),
                "average_pnl": round(total_pnl / history_count, 2) if history_count > 0 else 0
            }
        }

    except Exception as e:
        logger.error(f"Trading statistics failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"거래 통계 조회 실패: {str(e)}"
        )


@router.get("/trading/statistics/mock")
async def get_trading_statistics_mock():
    """Mock 거래 통계"""
    return {
        "success": True,
        "data": {
            "active_positions": 3,
            "total_trades": 25,
            "winning_trades": 16,
            "losing_trades": 9,
            "win_rate": 64.0,
            "total_pnl": 1250.75,
            "average_pnl": 50.03,
            "daily_pnl": 125.5,
            "weekly_pnl": 890.25,
            "monthly_pnl": 1250.75
        }
    }