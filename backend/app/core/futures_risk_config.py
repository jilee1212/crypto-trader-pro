"""
Futures trading risk management configuration
"""

from typing import Dict, List
from decimal import Decimal

# 선물 거래 위험 관리 설정
FUTURES_RISK_SETTINGS = {
    # 레버리지 제한 (안전성을 위한 권장 최대 레버리지)
    "max_recommended_leverage": 10,
    "max_allowed_leverage": 125,  # 바이낸스 최대값
    "default_leverage": 5,        # 기본 권장 레버리지

    # 포지션 크기 제한
    "max_position_size_usdt": 5000.0,   # 단일 포지션 최대 크기 (USDT)
    "max_total_positions": 5,           # 동시 보유 최대 포지션 수

    # 손절/익절 설정
    "default_stop_loss_pct": 2.0,       # 기본 손절선 (%)
    "default_take_profit_pct": 5.0,     # 기본 익절선 (%)
    "max_daily_loss_pct": 10.0,         # 일일 최대 손실 (%)

    # 마진 비율 경고 레벨
    "margin_ratio_warning": 80.0,       # 마진 비율 80% 경고
    "margin_ratio_danger": 90.0,        # 마진 비율 90% 위험

    # 펀딩비 모니터링
    "high_funding_rate_threshold": 0.1, # 0.1% 이상 시 경고

    # 자동 청산 보호 설정
    "liquidation_distance_warning": 10.0, # 청산가 10% 이내 경고
}

# 허용된 선물 거래 심볼 (USDT-M 영구 선물)
ALLOWED_FUTURES_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "DOTUSDT",
    "XRPUSDT", "SOLUSDT", "MATICUSDT", "LTCUSDT", "AVAXUSDT",
    "LINKUSDT", "UNIUSDT", "ATOMUSDT", "VETUSDT", "TRXUSDT",
    "AAVEUSDT", "ALGOUSDT", "SANDUSDT", "MANAUSDT", "CHZUSDT"
]

# 레버리지별 권장 포지션 크기
LEVERAGE_POSITION_SIZE_LIMITS = {
    1: {"max_usdt": 10000, "description": "Conservative - No leverage"},
    2: {"max_usdt": 8000, "description": "Low risk - 2x leverage"},
    3: {"max_usdt": 6000, "description": "Moderate risk - 3x leverage"},
    5: {"max_usdt": 4000, "description": "Medium risk - 5x leverage"},
    10: {"max_usdt": 2000, "description": "High risk - 10x leverage"},
    20: {"max_usdt": 1000, "description": "Very high risk - 20x leverage"},
    50: {"max_usdt": 500, "description": "Extremely high risk - 50x leverage"},
    125: {"max_usdt": 200, "description": "Maximum risk - 125x leverage"}
}

def get_max_position_size_for_leverage(leverage: int) -> float:
    """레버리지에 따른 권장 최대 포지션 크기 반환"""
    if leverage <= 1:
        return LEVERAGE_POSITION_SIZE_LIMITS[1]["max_usdt"]
    elif leverage <= 2:
        return LEVERAGE_POSITION_SIZE_LIMITS[2]["max_usdt"]
    elif leverage <= 3:
        return LEVERAGE_POSITION_SIZE_LIMITS[3]["max_usdt"]
    elif leverage <= 5:
        return LEVERAGE_POSITION_SIZE_LIMITS[5]["max_usdt"]
    elif leverage <= 10:
        return LEVERAGE_POSITION_SIZE_LIMITS[10]["max_usdt"]
    elif leverage <= 20:
        return LEVERAGE_POSITION_SIZE_LIMITS[20]["max_usdt"]
    elif leverage <= 50:
        return LEVERAGE_POSITION_SIZE_LIMITS[50]["max_usdt"]
    else:
        return LEVERAGE_POSITION_SIZE_LIMITS[125]["max_usdt"]

def get_risk_level_for_leverage(leverage: int) -> str:
    """레버리지에 따른 위험도 레벨 반환"""
    if leverage <= 1:
        return "VERY_LOW"
    elif leverage <= 3:
        return "LOW"
    elif leverage <= 5:
        return "MODERATE"
    elif leverage <= 10:
        return "HIGH"
    elif leverage <= 20:
        return "VERY_HIGH"
    else:
        return "EXTREME"

def calculate_liquidation_distance(entry_price: float, liquidation_price: float, side: str) -> float:
    """청산가까지의 거리 계산 (%)"""
    if liquidation_price <= 0:
        return 100.0

    if side.upper() == "LONG":
        distance = ((entry_price - liquidation_price) / entry_price) * 100
    else:  # SHORT
        distance = ((liquidation_price - entry_price) / entry_price) * 100

    return max(0, distance)

def is_high_risk_position(
    leverage: int,
    position_size_usdt: float,
    margin_ratio: float = 0,
    liquidation_distance: float = 100
) -> Dict[str, bool]:
    """포지션 위험도 평가"""
    warnings = {
        "high_leverage": leverage > FUTURES_RISK_SETTINGS["max_recommended_leverage"],
        "large_position": position_size_usdt > get_max_position_size_for_leverage(leverage),
        "high_margin_ratio": margin_ratio > FUTURES_RISK_SETTINGS["margin_ratio_warning"],
        "near_liquidation": liquidation_distance < FUTURES_RISK_SETTINGS["liquidation_distance_warning"]
    }

    return warnings

def get_suggested_stop_loss_take_profit(
    entry_price: float,
    side: str,
    leverage: int
) -> Dict[str, float]:
    """레버리지에 따른 권장 손절/익절 가격 계산"""
    # 레버리지가 높을수록 더 타이트한 손절선 권장
    stop_loss_pct = FUTURES_RISK_SETTINGS["default_stop_loss_pct"] / (leverage / 5)
    take_profit_pct = FUTURES_RISK_SETTINGS["default_take_profit_pct"]

    # 최소/최대 제한
    stop_loss_pct = max(0.5, min(stop_loss_pct, 5.0))

    if side.upper() == "LONG":
        stop_loss = entry_price * (1 - stop_loss_pct / 100)
        take_profit = entry_price * (1 + take_profit_pct / 100)
    else:  # SHORT
        stop_loss = entry_price * (1 + stop_loss_pct / 100)
        take_profit = entry_price * (1 - take_profit_pct / 100)

    return {
        "stop_loss": round(stop_loss, 6),
        "take_profit": round(take_profit, 6),
        "stop_loss_pct": stop_loss_pct,
        "take_profit_pct": take_profit_pct
    }

# 긴급 상황 감지 조건
EMERGENCY_CONDITIONS = {
    "max_daily_loss_reached": lambda daily_pnl: daily_pnl <= -FUTURES_RISK_SETTINGS["max_daily_loss_pct"],
    "margin_ratio_critical": lambda margin_ratio: margin_ratio >= FUTURES_RISK_SETTINGS["margin_ratio_danger"],
    "liquidation_imminent": lambda liq_distance: liq_distance <= 5.0,  # 청산가 5% 이내
    "account_balance_low": lambda balance: balance <= 100.0,  # 계좌 잔고 100 USDT 이하
}

def check_emergency_conditions(
    daily_pnl_pct: float = 0,
    margin_ratio: float = 0,
    liquidation_distance: float = 100,
    account_balance: float = 1000
) -> Dict[str, bool]:
    """긴급 상황 조건 확인"""
    return {
        condition_name: condition_func(value)
        for condition_name, condition_func in EMERGENCY_CONDITIONS.items()
        for value in [
            daily_pnl_pct if 'daily_loss' in condition_name else
            margin_ratio if 'margin_ratio' in condition_name else
            liquidation_distance if 'liquidation' in condition_name else
            account_balance
        ]
    }