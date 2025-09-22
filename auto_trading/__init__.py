"""
🤖 Crypto Trader Pro - Auto Trading System

고급 자동매매 시스템 패키지

Author: Crypto Trader Pro Team
Version: 1.0.0
"""

from .engine import AutoTradingEngine
from .config_manager import ConfigManager
from .market_monitor import MarketMonitor
from .signal_generator import AISignalGenerator
from .trade_executor import TradeExecutor
from .position_manager import PositionManager
from .risk_manager import RiskManager

__version__ = "1.0.0"
__author__ = "Crypto Trader Pro Team"

__all__ = [
    'AutoTradingEngine',
    'ConfigManager',
    'MarketMonitor',
    'AISignalGenerator',
    'TradeExecutor',
    'PositionManager',
    'RiskManager'
]