"""
⚙️ ConfigManager - 자동매매 설정 관리자

자동매매 시스템의 모든 설정을 관리하는 중앙 집중식 관리자
- JSON 기반 설정 파일 관리
- 실시간 설정 변경
- 설정 유효성 검증
- 기본값 관리
"""

import json
import os
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
from dataclasses import dataclass, asdict

@dataclass
class EngineConfig:
    trading_interval: int = 300  # 5분
    max_concurrent_positions: int = 5
    enable_paper_trading: bool = False
    auto_restart: bool = True

@dataclass
class RiskConfig:
    daily_loss_limit_pct: float = 3.0
    position_size_pct: float = 2.0
    stop_loss_pct: float = 1.0
    take_profit_pct: float = 2.0
    max_drawdown_pct: float = 5.0

@dataclass
class NotificationConfig:
    enabled: bool = True
    channels: List[str] = None
    trade_notifications: bool = True
    error_notifications: bool = True
    daily_summary: bool = True

    def __post_init__(self):
        if self.channels is None:
            self.channels = ["dashboard"]

class ConfigManager:
    """
    ⚙️ 자동매매 설정 관리자

    기능:
    - 설정 파일 로드/저장
    - 실시간 설정 업데이트
    - 설정 유효성 검증
    - 기본값 관리
    """

    def __init__(self, config_path: str = None):
        """설정 관리자 초기화"""
        self.logger = logging.getLogger(__name__)

        # 설정 파일 경로
        if config_path is None:
            self.config_path = os.path.join("config", "auto_trading_config.json")
        else:
            self.config_path = config_path

        # 기본 설정
        self.engine_config = EngineConfig()
        self.risk_config = RiskConfig()
        self.notification_config = NotificationConfig()

        # 추가 설정
        self.symbols = ["BTC/USDT", "ETH/USDT"]
        self.trading_mode = "CONSERVATIVE"
        self.custom_settings = {}

        # 설정 로드
        self.load_config()

        self.logger.info("ConfigManager 초기화 완료")

    def load_config(self) -> bool:
        """
        설정 파일 로드

        Returns:
            bool: 로드 성공 여부
        """
        try:
            if not os.path.exists(self.config_path):
                self.logger.info("설정 파일이 없어 기본 설정으로 생성합니다")
                self.save_config()
                return True

            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # 엔진 설정 로드
            if 'engine' in config_data:
                engine_data = config_data['engine']
                self.engine_config.trading_interval = engine_data.get(
                    'trading_interval', 300
                )
                self.engine_config.max_concurrent_positions = engine_data.get(
                    'max_concurrent_positions', 5
                )
                self.engine_config.enable_paper_trading = engine_data.get(
                    'enable_paper_trading', False
                )
                self.engine_config.auto_restart = engine_data.get(
                    'auto_restart', True
                )

            # 리스크 설정 로드
            if 'risk_management' in config_data:
                risk_data = config_data['risk_management']
                self.risk_config.daily_loss_limit_pct = risk_data.get(
                    'daily_loss_limit_pct', 3.0
                )
                self.risk_config.position_size_pct = risk_data.get(
                    'position_size_pct', 2.0
                )
                self.risk_config.stop_loss_pct = risk_data.get(
                    'stop_loss_pct', 1.0
                )
                self.risk_config.take_profit_pct = risk_data.get(
                    'take_profit_pct', 2.0
                )
                self.risk_config.max_drawdown_pct = risk_data.get(
                    'max_drawdown_pct', 5.0
                )

            # 알림 설정 로드
            if 'notifications' in config_data:
                notif_data = config_data['notifications']
                self.notification_config.enabled = notif_data.get('enabled', True)
                self.notification_config.channels = notif_data.get(
                    'channels', ["dashboard"]
                )
                self.notification_config.trade_notifications = notif_data.get(
                    'trade_notifications', True
                )
                self.notification_config.error_notifications = notif_data.get(
                    'error_notifications', True
                )
                self.notification_config.daily_summary = notif_data.get(
                    'daily_summary', True
                )

            # 기타 설정
            self.symbols = config_data.get('symbols', ["BTC/USDT", "ETH/USDT"])
            self.trading_mode = config_data.get('trading_mode', 'CONSERVATIVE')
            self.custom_settings = config_data.get('custom_settings', {})

            self.logger.info("설정 파일 로드 완료")
            return True

        except Exception as e:
            self.logger.error(f"설정 파일 로드 실패: {e}")
            return False

    def save_config(self) -> bool:
        """
        설정 파일 저장

        Returns:
            bool: 저장 성공 여부
        """
        try:
            # 디렉토리 생성
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            config_data = {
                'engine': asdict(self.engine_config),
                'risk_management': asdict(self.risk_config),
                'notifications': asdict(self.notification_config),
                'symbols': self.symbols,
                'trading_mode': self.trading_mode,
                'custom_settings': self.custom_settings,
                'last_updated': datetime.now().isoformat()
            }

            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            self.logger.info("설정 파일 저장 완료")
            return True

        except Exception as e:
            self.logger.error(f"설정 파일 저장 실패: {e}")
            return False

    def get_config(self) -> Dict[str, Any]:
        """
        전체 설정 반환

        Returns:
            Dict: 전체 설정 데이터
        """
        return {
            'engine': asdict(self.engine_config),
            'risk_management': asdict(self.risk_config),
            'notifications': asdict(self.notification_config),
            'symbols': self.symbols,
            'trading_mode': self.trading_mode,
            'custom_settings': self.custom_settings
        }

    def update_config(self, updates: Dict[str, Any]) -> bool:
        """
        설정 업데이트

        Args:
            updates: 업데이트할 설정

        Returns:
            bool: 업데이트 성공 여부
        """
        try:
            # 엔진 설정 업데이트
            if 'engine' in updates:
                engine_updates = updates['engine']
                for key, value in engine_updates.items():
                    if hasattr(self.engine_config, key):
                        setattr(self.engine_config, key, value)

            # 리스크 설정 업데이트
            if 'risk_management' in updates:
                risk_updates = updates['risk_management']
                for key, value in risk_updates.items():
                    if hasattr(self.risk_config, key):
                        setattr(self.risk_config, key, value)

            # 알림 설정 업데이트
            if 'notifications' in updates:
                notif_updates = updates['notifications']
                for key, value in notif_updates.items():
                    if hasattr(self.notification_config, key):
                        setattr(self.notification_config, key, value)

            # 기타 설정 업데이트
            if 'symbols' in updates:
                self.symbols = updates['symbols']

            if 'trading_mode' in updates:
                self.trading_mode = updates['trading_mode']

            if 'custom_settings' in updates:
                self.custom_settings.update(updates['custom_settings'])

            # 설정 저장
            self.save_config()

            self.logger.info("설정 업데이트 완료")
            return True

        except Exception as e:
            self.logger.error(f"설정 업데이트 실패: {e}")
            return False

    def validate_config(self) -> bool:
        """
        설정 유효성 검증

        Returns:
            bool: 유효성 검증 결과
        """
        try:
            # 엔진 설정 검증
            if self.engine_config.trading_interval < 60:
                self.logger.error("거래 간격은 최소 60초 이상이어야 합니다")
                return False

            if self.engine_config.max_concurrent_positions < 1:
                self.logger.error("최대 포지션 수는 1개 이상이어야 합니다")
                return False

            # 리스크 설정 검증
            if self.risk_config.daily_loss_limit_pct <= 0:
                self.logger.error("일일 손실 한도는 0보다 커야 합니다")
                return False

            if self.risk_config.position_size_pct <= 0 or self.risk_config.position_size_pct > 10:
                self.logger.error("포지션 크기는 0~10% 범위여야 합니다")
                return False

            # 심볼 검증
            if not self.symbols:
                self.logger.error("거래 심볼이 설정되지 않았습니다")
                return False

            # 거래 모드 검증
            valid_modes = ['CONSERVATIVE', 'BALANCED', 'AGGRESSIVE']
            if self.trading_mode not in valid_modes:
                self.logger.error(f"거래 모드는 {valid_modes} 중 하나여야 합니다")
                return False

            self.logger.info("✅ 설정 유효성 검증 통과")
            return True

        except Exception as e:
            self.logger.error(f"설정 검증 실패: {e}")
            return False

    def get_risk_limits(self) -> Dict[str, float]:
        """리스크 제한 설정 반환"""
        return {
            'daily_loss_limit': self.risk_config.daily_loss_limit_pct,
            'position_size': self.risk_config.position_size_pct,
            'stop_loss': self.risk_config.stop_loss_pct,
            'take_profit': self.risk_config.take_profit_pct,
            'max_drawdown': self.risk_config.max_drawdown_pct
        }

    def get_trading_symbols(self) -> List[str]:
        """거래 심볼 목록 반환"""
        return self.symbols.copy()

    def is_paper_trading(self) -> bool:
        """페이퍼 트레이딩 모드 여부"""
        return self.engine_config.enable_paper_trading

    def get_notification_settings(self) -> Dict[str, Any]:
        """알림 설정 반환"""
        return asdict(self.notification_config)