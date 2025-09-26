"""
Trading configuration for Binance mainnet
"""

from typing import Dict

# 바이낸스 메인넷 최소 주문 금액 (USDT)
BINANCE_MIN_ORDER_AMOUNTS: Dict[str, float] = {
    "BTCUSDT": 10.0,
    "ETHUSDT": 10.0,
    "BNBUSDT": 10.0,
    "ADAUSDT": 5.0,
    "XRPUSDT": 5.0,
    "SOLUSDT": 10.0,
    "DOTUSDT": 5.0,
    "MATICUSDT": 5.0,
    "LTCUSDT": 10.0,
    "AVAXUSDT": 10.0,
    "ATOMUSDT": 5.0,
    "LINKUSDT": 10.0,
    "UNIUSDT": 10.0,
    "VETUSDT": 5.0,
    "TRXUSDT": 5.0,
}

# 기본 최소 주문 금액 (해당 심볼이 목록에 없는 경우)
DEFAULT_MIN_ORDER_AMOUNT = 10.0

# 주요 거래쌍 목록
MAJOR_TRADING_PAIRS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT",
    "SOLUSDT", "DOTUSDT", "MATICUSDT", "LTCUSDT", "AVAXUSDT",
    "ATOMUSDT", "LINKUSDT", "UNIUSDT", "VETUSDT", "TRXUSDT"
]

def get_min_order_amount(symbol: str) -> float:
    """특정 심볼의 최소 주문 금액을 반환"""
    return BINANCE_MIN_ORDER_AMOUNTS.get(symbol, DEFAULT_MIN_ORDER_AMOUNT)

def validate_order_amount(symbol: str, amount: float) -> bool:
    """주문 금액이 최소 요구사항을 만족하는지 확인"""
    min_amount = get_min_order_amount(symbol)
    return amount >= min_amount

# 긴급 정지 기능을 위한 설정
EMERGENCY_STOP_ENABLED = True
MAX_DAILY_TRADES_LIMIT = 1000  # 하루 최대 거래 횟수 (기술적 제한)