"""
Risk Management API endpoints for Futures Trading
AI 기반 리스크 관리 API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ...db.database import get_db
from ...auth.jwt_handler import get_current_user
from ...models.user import User
from ...core.ai_risk_manager import AIRiskManager, FuturesRiskMonitor
from ...schemas.risk_management import (
    RiskCalculationRequest,
    RiskCalculationResponse,
    PositionRiskAssessment,
    PortfolioRiskAssessment,
    OptimalStopLossRequest,
    OptimalStopLossResponse,
    MultiScenarioRequest,
    MultiScenarioResponse
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/risk", tags=["risk-management"])


@router.post("/calculate-position", response_model=RiskCalculationResponse)
async def calculate_position_size(
    request: RiskCalculationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI 기반 포지션 사이징 계산"""
    try:
        # 사용자 계좌 잔고 조회 (실제 구현에서는 바이낸스 API에서 조회)
        account_balance = request.account_balance or 1000.0  # 기본값 또는 DB에서 조회

        # AI 리스크 관리자 초기화
        risk_manager = AIRiskManager(
            account_balance=account_balance,
            risk_percentage=request.risk_percentage
        )

        # 포지션 사이징 계산
        calculation_result = risk_manager.calculate_position_size(
            entry_price=request.entry_price,
            stop_loss_price=request.stop_loss_price
        )

        return RiskCalculationResponse(**calculation_result)

    except Exception as e:
        logger.error(f"Position calculation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"포지션 계산 실패: {str(e)}"
        )


@router.post("/calculate-scenarios", response_model=MultiScenarioResponse)
async def calculate_multiple_scenarios(
    request: MultiScenarioRequest,
    current_user: User = Depends(get_current_user)
):
    """여러 손절가 시나리오에 대한 리스크 계산"""
    try:
        risk_manager = AIRiskManager(
            account_balance=request.account_balance,
            risk_percentage=request.risk_percentage
        )

        scenarios = risk_manager.calculate_multiple_scenarios(
            entry_price=request.entry_price,
            stop_loss_prices=request.stop_loss_prices
        )

        return MultiScenarioResponse(
            entry_price=request.entry_price,
            scenarios=scenarios,
            account_balance=request.account_balance,
            risk_percentage=request.risk_percentage
        )

    except Exception as e:
        logger.error(f"Multi scenario calculation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"시나리오 계산 실패: {str(e)}"
        )


@router.post("/optimal-stop-range", response_model=OptimalStopLossResponse)
async def get_optimal_stop_loss_range(
    request: OptimalStopLossRequest,
    current_user: User = Depends(get_current_user)
):
    """최적 손절가 범위 계산"""
    try:
        risk_manager = AIRiskManager(
            account_balance=request.account_balance,
            risk_percentage=request.risk_percentage
        )

        optimal_range = risk_manager.get_optimal_stop_loss_range(
            entry_price=request.entry_price,
            min_leverage=request.min_leverage,
            max_leverage=request.max_leverage
        )

        return OptimalStopLossResponse(**optimal_range)

    except Exception as e:
        logger.error(f"Optimal stop loss calculation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"최적 손절가 계산 실패: {str(e)}"
        )


@router.get("/assess-portfolio")
async def assess_portfolio_risk(
    current_user: User = Depends(get_current_user)
):
    """포트폴리오 리스크 평가"""
    try:
        # 실제 구현에서는 바이낸스 API에서 포지션 정보를 가져와야 함
        # 여기서는 Mock 데이터 사용
        mock_positions = [
            {
                "symbol": "BTCUSDT",
                "side": "LONG",
                "entry_price": 42000,
                "mark_price": 43250,
                "unrealized_pnl": 62.5,
                "initial_margin": 210.0,
                "liquidation_price": 38500.0
            }
        ]

        mock_account_info = {
            "total_wallet_balance": 1000.0,
            "total_margin_balance": 1125.5,
            "available_balance": 900.0
        }

        risk_monitor = FuturesRiskMonitor()
        portfolio_risk = risk_monitor.assess_portfolio_risk(
            positions=mock_positions,
            account_info=mock_account_info
        )

        return portfolio_risk

    except Exception as e:
        logger.error(f"Portfolio risk assessment error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"포트폴리오 리스크 평가 실패: {str(e)}"
        )


# Mock 엔드포인트들 (테스트용)
@router.post("/calculate-position/mock")
async def calculate_position_size_mock(request: RiskCalculationRequest):
    """Mock 포지션 사이징 계산"""
    try:
        # 예시 계산
        account_balance = 1000.0
        risk_percentage = 3.0

        # Mock 계산 결과
        mock_result = {
            "position_value": 2857.14,
            "position_quantity": 0.068,
            "leverage": 5,
            "seed_usage_percent": 57.1,
            "margin_used": 571.43,
            "actual_multiplier": 2.857,
            "target_multiplier": 2.857,
            "target_risk_amount": 30.0,
            "actual_risk_amount": 30.0,
            "risk_accuracy": 100.0,
            "risk_percentage": 3.0,
            "entry_price": request.entry_price,
            "stop_loss_price": request.stop_loss_price,
            "price_diff_percent": 1.05,
            "account_balance": account_balance,
            "remaining_balance": 428.57,
            "optimization_notes": "최적 조합 발견 (오차: 0.00%)",
            "is_optimal": True,
            "warnings": [],
            "risk_level": "MEDIUM"
        }

        return mock_result

    except Exception as e:
        logger.error(f"Mock calculation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mock 계산 실패: {str(e)}"
        )


@router.get("/assess-portfolio/mock")
async def assess_portfolio_risk_mock():
    """Mock 포트폴리오 리스크 평가"""
    return {
        "portfolio_risk_level": "MEDIUM",
        "total_balance": 1000.0,
        "total_unrealized_pnl": 125.5,
        "portfolio_pnl_percent": 12.55,
        "overall_margin_ratio": 42.3,
        "position_count": 2,
        "critical_positions": 0,
        "high_risk_positions": 0,
        "position_risks": [
            {
                "symbol": "BTCUSDT",
                "risk_level": "LOW",
                "margin_ratio": 21.0,
                "liquidation_distance": 45.2,
                "pnl_percent": 6.25,
                "alerts": [],
                "requires_action": False
            },
            {
                "symbol": "ETHUSDT",
                "risk_level": "MEDIUM",
                "margin_ratio": 35.5,
                "liquidation_distance": 32.1,
                "pnl_percent": 3.8,
                "alerts": ["경고: 마진 비율 보통 수준"],
                "requires_action": False
            }
        ],
        "requires_immediate_action": False,
        "recommendation": "리스크 모니터링 강화 및 신중한 거래 진행"
    }


@router.get("/leverage-options")
async def get_leverage_options():
    """사용 가능한 레버리지 옵션 조회"""
    return {
        "available_leverages": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
        "recommended_max": 10,
        "safety_max": 5,
        "risk_levels": {
            "VERY_LOW": [1, 2],
            "LOW": [3, 4, 5],
            "MEDIUM": [6, 7, 8],
            "HIGH": [9, 10, 11, 12],
            "VERY_HIGH": [13, 14, 15, 16, 17, 18, 19, 20]
        }
    }


@router.get("/risk-presets")
async def get_risk_presets():
    """사전 정의된 리스크 설정 프리셋"""
    return {
        "conservative": {
            "risk_percentage": 1.0,
            "max_leverage": 3,
            "description": "보수적 - 안전한 거래"
        },
        "moderate": {
            "risk_percentage": 2.0,
            "max_leverage": 5,
            "description": "보통 - 균형잡힌 거래"
        },
        "aggressive": {
            "risk_percentage": 3.0,
            "max_leverage": 10,
            "description": "공격적 - 높은 수익 추구"
        },
        "high_risk": {
            "risk_percentage": 5.0,
            "max_leverage": 20,
            "description": "고위험 - 전문가용"
        }
    }