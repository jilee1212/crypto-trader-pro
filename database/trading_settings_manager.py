"""
Trading Settings Manager - 거래 설정 관리
사용자별 주문 한도 및 거래 설정 관리
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from database.database_manager import get_db_manager
from database.models import TradingSettings

logger = logging.getLogger(__name__)

class TradingSettingsManager:
    """거래 설정 관리자"""

    def __init__(self):
        self.db_manager = get_db_manager()

    def get_user_trading_settings(self, user_id: int) -> Optional[Dict[str, Any]]:
        """사용자 거래 설정 조회"""
        try:
            with self.db_manager.get_session() as session:
                settings = session.query(TradingSettings).filter_by(user_id=user_id).first()

                if settings:
                    return {
                        'max_order_amount': settings.max_order_amount,
                        'default_order_amount': settings.default_order_amount,
                        'use_balance_percentage': settings.use_balance_percentage,
                        'balance_percentage': settings.balance_percentage,
                        'trading_mode': settings.trading_mode,
                        'risk_percentage': settings.risk_percentage,
                        'max_positions': settings.max_positions,
                        'daily_loss_limit': settings.daily_loss_limit,
                        'auto_trading_enabled': settings.auto_trading_enabled
                    }
                else:
                    # 기본 설정 반환
                    return self._get_default_settings()

        except Exception as e:
            logger.error(f"Error getting trading settings for user {user_id}: {e}")
            return self._get_default_settings()

    def save_user_trading_settings(self, user_id: int, settings: Dict[str, Any]) -> bool:
        """사용자 거래 설정 저장"""
        try:
            with self.db_manager.get_session() as session:
                # 기존 설정 조회 또는 새 설정 생성
                existing = session.query(TradingSettings).filter_by(user_id=user_id).first()

                if existing:
                    # 기존 설정 업데이트
                    existing.max_order_amount = settings.get('max_order_amount', 50.0)
                    existing.default_order_amount = settings.get('default_order_amount', 10.0)
                    existing.use_balance_percentage = settings.get('use_balance_percentage', False)
                    existing.balance_percentage = settings.get('balance_percentage', 2.0)
                    existing.trading_mode = settings.get('trading_mode', 'conservative')
                    existing.risk_percentage = settings.get('risk_percentage', 2.0)
                    existing.max_positions = settings.get('max_positions', 3)
                    existing.daily_loss_limit = settings.get('daily_loss_limit', 5.0)
                    existing.auto_trading_enabled = settings.get('auto_trading_enabled', False)
                else:
                    # 새 설정 생성
                    new_settings = TradingSettings(
                        user_id=user_id,
                        max_order_amount=settings.get('max_order_amount', 50.0),
                        default_order_amount=settings.get('default_order_amount', 10.0),
                        use_balance_percentage=settings.get('use_balance_percentage', False),
                        balance_percentage=settings.get('balance_percentage', 2.0),
                        trading_mode=settings.get('trading_mode', 'conservative'),
                        risk_percentage=settings.get('risk_percentage', 2.0),
                        max_positions=settings.get('max_positions', 3),
                        daily_loss_limit=settings.get('daily_loss_limit', 5.0),
                        auto_trading_enabled=settings.get('auto_trading_enabled', False)
                    )
                    session.add(new_settings)

                session.commit()
                logger.info(f"Trading settings saved for user {user_id}")
                return True

        except Exception as e:
            logger.error(f"Error saving trading settings for user {user_id}: {e}")
            return False

    def get_trading_mode_settings(self, mode: str) -> Dict[str, Any]:
        """거래 모드별 프리셋 설정"""
        presets = {
            'conservative': {
                'max_order_amount': 30.0,
                'default_order_amount': 8.0,
                'balance_percentage': 1.0,
                'risk_percentage': 1.0,
                'max_positions': 2,
                'daily_loss_limit': 3.0
            },
            'balanced': {
                'max_order_amount': 100.0,
                'default_order_amount': 15.0,
                'balance_percentage': 2.0,
                'risk_percentage': 2.0,
                'max_positions': 3,
                'daily_loss_limit': 5.0
            },
            'aggressive': {
                'max_order_amount': 500.0,
                'default_order_amount': 50.0,
                'balance_percentage': 5.0,
                'risk_percentage': 3.0,
                'max_positions': 5,
                'daily_loss_limit': 10.0
            }
        }
        return presets.get(mode, presets['conservative'])

    def validate_order_amount(self, user_id: int, symbol: str, amount: float) -> Dict[str, Any]:
        """주문 금액 유효성 검사"""
        settings = self.get_user_trading_settings(user_id)

        validation_result = {
            'valid': True,
            'message': '',
            'suggested_amount': None,
            'max_allowed': settings['max_order_amount'],
            'min_required': 5.0  # 기본 최소값, 나중에 거래소별로 업데이트
        }

        # 최대 한도 검사
        if amount > settings['max_order_amount']:
            validation_result['valid'] = False
            validation_result['message'] = f"최대 주문 한도 ${settings['max_order_amount']:.1f} USDT를 초과했습니다"
            validation_result['suggested_amount'] = settings['max_order_amount']

        return validation_result

    def calculate_recommended_amount(self, user_id: int, symbol: str, account_balance: float) -> Dict[str, float]:
        """권장 주문 금액 계산"""
        settings = self.get_user_trading_settings(user_id)

        if settings['use_balance_percentage']:
            # 잔고 비율 기반 계산
            percentage_amount = account_balance * (settings['balance_percentage'] / 100)
            recommended = min(percentage_amount, settings['max_order_amount'])
        else:
            # 고정 금액 사용
            recommended = settings['default_order_amount']

        # 거래 모드별 추가 권장사항
        mode_settings = self.get_trading_mode_settings(settings['trading_mode'])

        return {
            'conservative': min(recommended * 0.7, mode_settings['default_order_amount']),
            'recommended': recommended,
            'aggressive': min(recommended * 1.5, settings['max_order_amount'])
        }

    def get_coin_specific_settings(self, user_id: int, symbol: str) -> Dict[str, Any]:
        """코인별 개별 설정 조회"""
        try:
            with self.db_manager.get_session() as session:
                settings = session.query(TradingSettings).filter_by(user_id=user_id).first()

                if settings and settings.symbols:
                    import json
                    coin_settings = json.loads(settings.symbols)
                    return coin_settings.get(symbol, {})

                return {}
        except Exception as e:
            logger.error(f"Error getting coin-specific settings for {symbol}: {e}")
            return {}

    def save_coin_specific_settings(self, user_id: int, symbol: str, coin_settings: Dict[str, Any]) -> bool:
        """코인별 개별 설정 저장"""
        try:
            with self.db_manager.get_session() as session:
                settings = session.query(TradingSettings).filter_by(user_id=user_id).first()

                if settings:
                    import json
                    current_symbols = json.loads(settings.symbols) if settings.symbols else {}
                    current_symbols[symbol] = coin_settings
                    settings.symbols = json.dumps(current_symbols)
                    session.commit()
                    logger.info(f"Coin-specific settings saved for {symbol}")
                    return True

                return False
        except Exception as e:
            logger.error(f"Error saving coin-specific settings for {symbol}: {e}")
            return False

    def get_favorite_coins(self, user_id: int) -> List[str]:
        """즐겨찾기 코인 목록 조회"""
        try:
            with self.db_manager.get_session() as session:
                settings = session.query(TradingSettings).filter_by(user_id=user_id).first()

                if settings and settings.strategy_config:
                    import json
                    config = json.loads(settings.strategy_config)
                    return config.get('favorite_coins', [])

                return ['BTC/USDT', 'ETH/USDT', 'XRP/USDT']  # 기본 즐겨찾기
        except Exception as e:
            logger.error(f"Error getting favorite coins: {e}")
            return ['BTC/USDT', 'ETH/USDT', 'XRP/USDT']

    def save_favorite_coins(self, user_id: int, coins: List[str]) -> bool:
        """즐겨찾기 코인 목록 저장"""
        try:
            with self.db_manager.get_session() as session:
                settings = session.query(TradingSettings).filter_by(user_id=user_id).first()

                if settings:
                    import json
                    config = json.loads(settings.strategy_config) if settings.strategy_config else {}
                    config['favorite_coins'] = coins
                    settings.strategy_config = json.dumps(config)
                    session.commit()
                    logger.info(f"Favorite coins saved: {coins}")
                    return True

                return False
        except Exception as e:
            logger.error(f"Error saving favorite coins: {e}")
            return False

    def get_trading_schedule(self, user_id: int) -> Dict[str, Any]:
        """거래 시간 제한 설정 조회"""
        try:
            with self.db_manager.get_session() as session:
                settings = session.query(TradingSettings).filter_by(user_id=user_id).first()

                if settings and settings.strategy_config:
                    import json
                    config = json.loads(settings.strategy_config)
                    return config.get('trading_schedule', {
                        'enabled': False,
                        'start_time': '09:00',
                        'end_time': '18:00',
                        'weekend_trading': True,
                        'max_daily_trades': 20
                    })

                return {
                    'enabled': False,
                    'start_time': '09:00',
                    'end_time': '18:00',
                    'weekend_trading': True,
                    'max_daily_trades': 20
                }
        except Exception as e:
            logger.error(f"Error getting trading schedule: {e}")
            return {'enabled': False}

    def save_trading_schedule(self, user_id: int, schedule: Dict[str, Any]) -> bool:
        """거래 시간 제한 설정 저장"""
        try:
            with self.db_manager.get_session() as session:
                settings = session.query(TradingSettings).filter_by(user_id=user_id).first()

                if settings:
                    import json
                    config = json.loads(settings.strategy_config) if settings.strategy_config else {}
                    config['trading_schedule'] = schedule
                    settings.strategy_config = json.dumps(config)
                    session.commit()
                    logger.info(f"Trading schedule saved")
                    return True

                return False
        except Exception as e:
            logger.error(f"Error saving trading schedule: {e}")
            return False

    def can_trade_now(self, user_id: int) -> Dict[str, Any]:
        """현재 시간에 거래 가능한지 확인"""
        schedule = self.get_trading_schedule(user_id)

        if not schedule.get('enabled', False):
            return {'can_trade': True, 'reason': None}

        from datetime import datetime, time
        import calendar

        now = datetime.now()
        current_time = now.time()
        current_weekday = now.weekday()  # 0=월요일, 6=일요일

        # 주말 거래 확인
        if not schedule.get('weekend_trading', True) and current_weekday >= 5:
            return {'can_trade': False, 'reason': '주말 거래가 비활성화되어 있습니다'}

        # 시간 제한 확인
        start_time = time.fromisoformat(schedule.get('start_time', '09:00'))
        end_time = time.fromisoformat(schedule.get('end_time', '18:00'))

        if not (start_time <= current_time <= end_time):
            return {
                'can_trade': False,
                'reason': f'거래 시간이 아닙니다 (허용 시간: {start_time} - {end_time})'
            }

        return {'can_trade': True, 'reason': None}

    def calculate_dynamic_order_amount(self, user_id: int, symbol: str, account_balance: float, volatility: float = None) -> Dict[str, float]:
        """변동성을 고려한 동적 주문 금액 계산"""
        settings = self.get_user_trading_settings(user_id)
        coin_settings = self.get_coin_specific_settings(user_id, symbol)

        base_amount = settings['default_order_amount']

        # 코인별 설정이 있으면 우선 적용
        if coin_settings.get('custom_amount'):
            base_amount = coin_settings['custom_amount']

        # 잔고 비율 기반 계산
        if settings['use_balance_percentage']:
            percentage_amount = account_balance * (settings['balance_percentage'] / 100)
            base_amount = min(percentage_amount, settings['max_order_amount'])

        # 변동성 조정 (높은 변동성일 때 주문 금액 축소)
        if volatility is not None:
            if volatility > 5.0:  # 5% 이상 변동성
                volatility_factor = 0.7  # 30% 축소
            elif volatility > 3.0:  # 3% 이상 변동성
                volatility_factor = 0.85  # 15% 축소
            else:
                volatility_factor = 1.0  # 조정 없음

            base_amount *= volatility_factor

        # 거래 모드별 조정
        mode_settings = self.get_trading_mode_settings(settings['trading_mode'])

        return {
            'conservative': min(base_amount * 0.7, mode_settings['default_order_amount']),
            'recommended': min(base_amount, settings['max_order_amount']),
            'aggressive': min(base_amount * 1.3, settings['max_order_amount'])
        }

    def export_settings(self, user_id: int) -> Dict[str, Any]:
        """설정 내보내기"""
        try:
            settings = self.get_user_trading_settings(user_id)
            schedule = self.get_trading_schedule(user_id)
            favorites = self.get_favorite_coins(user_id)

            return {
                'trading_settings': settings,
                'trading_schedule': schedule,
                'favorite_coins': favorites,
                'export_timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error exporting settings: {e}")
            return {}

    def import_settings(self, user_id: int, settings_data: Dict[str, Any]) -> bool:
        """설정 가져오기"""
        try:
            # 거래 설정 가져오기
            if 'trading_settings' in settings_data:
                self.save_user_trading_settings(user_id, settings_data['trading_settings'])

            # 거래 스케줄 가져오기
            if 'trading_schedule' in settings_data:
                self.save_trading_schedule(user_id, settings_data['trading_schedule'])

            # 즐겨찾기 코인 가져오기
            if 'favorite_coins' in settings_data:
                self.save_favorite_coins(user_id, settings_data['favorite_coins'])

            logger.info(f"Settings imported successfully for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error importing settings: {e}")
            return False

    def get_risk_settings(self, user_id: int) -> Dict[str, Any]:
        """리스크 관리 설정 조회"""
        try:
            with self.db_manager.get_session() as session:
                settings = session.query(TradingSettings).filter_by(user_id=user_id).first()

                if settings:
                    return {
                        'position_risk_percent': settings.position_risk_percent,
                        'consecutive_loss_limit': settings.consecutive_loss_limit,
                        'auto_protection_enabled': settings.auto_protection_enabled,
                        'max_leverage': settings.max_leverage,
                        'preferred_order_type': settings.preferred_order_type,
                        'daily_loss_limit': settings.daily_loss_limit
                    }
                else:
                    return self._get_default_risk_settings()

        except Exception as e:
            logger.error(f"Error getting risk settings for user {user_id}: {e}")
            return self._get_default_risk_settings()

    def save_risk_settings(self, user_id: int, risk_settings: Dict[str, Any]) -> bool:
        """리스크 관리 설정 저장"""
        try:
            with self.db_manager.get_session() as session:
                settings = session.query(TradingSettings).filter_by(user_id=user_id).first()

                if settings:
                    # 리스크 설정 업데이트
                    settings.position_risk_percent = risk_settings.get('position_risk_percent', 3.0)
                    settings.consecutive_loss_limit = risk_settings.get('consecutive_loss_limit', 3)
                    settings.auto_protection_enabled = risk_settings.get('auto_protection_enabled', True)
                    settings.max_leverage = risk_settings.get('max_leverage', 10.0)
                    settings.preferred_order_type = risk_settings.get('preferred_order_type', 'limit')
                    settings.daily_loss_limit = risk_settings.get('daily_loss_limit', 5.0)

                    session.commit()
                    logger.info(f"Risk settings saved for user {user_id}")
                    return True
                else:
                    # 새 설정 생성 (기본값 + 리스크 설정)
                    default_settings = self._get_default_settings()
                    default_settings.update(risk_settings)
                    return self.save_user_trading_settings(user_id, default_settings)

        except Exception as e:
            logger.error(f"Error saving risk settings for user {user_id}: {e}")
            return False

    def get_position_limits(self, user_id: int, account_balance: float) -> Dict[str, Any]:
        """계좌 잔고 기반 포지션 한도 계산"""
        risk_settings = self.get_risk_settings(user_id)
        general_settings = self.get_user_trading_settings(user_id)

        # 리스크 기반 최대 포지션 크기
        max_risk_amount = account_balance * (risk_settings['position_risk_percent'] / 100)

        # 일일 손실 한도 기반 잔여 허용 리스크
        daily_limit = account_balance * (risk_settings['daily_loss_limit'] / 100)

        return {
            'max_risk_per_position': max_risk_amount,
            'daily_loss_limit': daily_limit,
            'max_leverage': risk_settings['max_leverage'],
            'max_positions': general_settings['max_positions'],
            'preferred_order_type': risk_settings['preferred_order_type']
        }

    def validate_position_risk(self, user_id: int, position_risk: float,
                              account_balance: float) -> Dict[str, Any]:
        """포지션 리스크 유효성 검사"""
        limits = self.get_position_limits(user_id, account_balance)

        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'risk_level': 'normal'
        }

        # 리스크 한도 검사
        if position_risk > limits['max_risk_per_position']:
            validation_result['valid'] = False
            validation_result['errors'].append(
                f"포지션 리스크 ${position_risk:.2f}가 한도 ${limits['max_risk_per_position']:.2f}를 초과합니다"
            )

        # 리스크 레벨 판정
        risk_ratio = position_risk / limits['max_risk_per_position']
        if risk_ratio > 0.8:
            validation_result['risk_level'] = 'high'
            validation_result['warnings'].append("높은 리스크 포지션입니다")
        elif risk_ratio > 0.5:
            validation_result['risk_level'] = 'medium'

        return validation_result

    def _get_default_risk_settings(self) -> Dict[str, Any]:
        """기본 리스크 설정"""
        return {
            'position_risk_percent': 3.0,
            'consecutive_loss_limit': 3,
            'auto_protection_enabled': True,
            'max_leverage': 10.0,
            'preferred_order_type': 'limit',
            'daily_loss_limit': 5.0
        }

    def _get_default_settings(self) -> Dict[str, Any]:
        """기본 거래 설정"""
        return {
            'max_order_amount': 50.0,
            'default_order_amount': 10.0,
            'use_balance_percentage': False,
            'balance_percentage': 2.0,
            'trading_mode': 'conservative',
            'risk_percentage': 2.0,
            'max_positions': 3,
            'daily_loss_limit': 5.0,
            'auto_trading_enabled': False,
            # 리스크 설정 기본값 포함
            'position_risk_percent': 3.0,
            'consecutive_loss_limit': 3,
            'auto_protection_enabled': True,
            'max_leverage': 10.0,
            'preferred_order_type': 'limit'
        }

# 싱글톤 인스턴스
_trading_settings_manager = None

def get_trading_settings_manager() -> TradingSettingsManager:
    """거래 설정 관리자 인스턴스 반환"""
    global _trading_settings_manager
    if _trading_settings_manager is None:
        _trading_settings_manager = TradingSettingsManager()
    return _trading_settings_manager