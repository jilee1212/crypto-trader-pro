"""
🎛️ Auto Trading Dashboard - 자동매매 대시보드

자동매매 시스템의 제어 및 모니터링 인터페이스
- 실시간 제어 패널
- 성과 모니터링
- 로그 뷰어
- 설정 관리
"""

from .control_panel import show_control_panel, show_advanced_control_panel
from .monitoring import show_real_time_monitoring
from .logs_viewer import main as show_logs_viewer
from .performance_tracker import main as show_performance_tracker
from .advanced_notifications import main as show_advanced_notifications
from .performance_analysis import main as show_performance_analysis
from .backtesting_system import main as show_backtesting_system
from .system_config import main as show_system_config

__version__ = "1.0.0"
__author__ = "Crypto Trader Pro Team"

__all__ = [
    'show_control_panel',
    'show_advanced_control_panel',
    'show_real_time_monitoring',
    'show_logs_viewer',
    'show_performance_tracker',
    'show_advanced_notifications',
    'show_performance_analysis',
    'show_backtesting_system',
    'show_system_config'
]