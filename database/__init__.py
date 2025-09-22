"""
🗄️ Database Package - 데이터베이스 관리

자동매매 시스템의 데이터베이스 관리 패키지
- 자동매매 설정 저장
- 거래 로그 관리
- 성과 데이터 추적
- 시스템 상태 저장
"""

from .auto_trading_db import AutoTradingDB
from .models import (
    AutoTradingConfig,
    AutoTradingLog,
    AISignalLog,
    PerformanceData
)

__version__ = "1.0.0"
__author__ = "Crypto Trader Pro Team"

__all__ = [
    'AutoTradingDB',
    'AutoTradingConfig',
    'AutoTradingLog',
    'AISignalLog',
    'PerformanceData'
]