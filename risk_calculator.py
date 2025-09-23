"""
Risk Calculator - 정밀한 포지션 사이징 시스템
사용자 설정 리스크 기반의 포지션 계산 및 레버리지 결정
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import math

logger = logging.getLogger(__name__)

class RiskCalculator:
    """핵심 리스크 계산 엔진"""

    def __init__(self):
        # 거래소에서 지원하는 레버리지 목록
        self.available_leverages = [1, 2, 3, 5, 10, 15, 20]

        # 최소/최대 포지션 제한
        self.min_position_value = 5.0  # 최소 5 USDT
        self.max_leverage = 20.0       # 최대 20x 레버리지

    def calculate_position(self, user_capital: float, risk_percent: float,
                          entry_price: float, stop_loss: float,
                          symbol: str = None) -> Dict[str, Any]:
        """
        사용자 설정 리스크 기반 최적 포지션 계산

        Args:
            user_capital: 사용자 총 자본 (USDT)
            risk_percent: 허용 리스크 비율 (1-10%)
            entry_price: 진입 가격
            stop_loss: 손절 가격
            symbol: 거래 심볼 (선택사항)

        Returns:
            포지션 계산 결과 딕셔너리
        """
        try:
            # 입력값 검증
            if not self._validate_inputs(user_capital, risk_percent, entry_price, stop_loss):
                return self._get_error_result("입력값이 유효하지 않습니다")

            # 기본 계산
            target_risk_amount = user_capital * (risk_percent / 100)
            price_diff_percent = abs(entry_price - stop_loss) / entry_price

            if price_diff_percent == 0:
                return self._get_error_result("진입가와 손절가가 동일합니다")

            # 필요한 포지션 크기 계산
            required_position_value = target_risk_amount / price_diff_percent
            calculated_leverage = required_position_value / user_capital

            # 거래 타입 결정 (현물 vs 선물)
            if calculated_leverage <= 1.0:
                # 현물 거래 (1x 이하)
                result = self._calculate_spot_position(
                    user_capital, target_risk_amount, required_position_value,
                    price_diff_percent, entry_price, stop_loss
                )
            else:
                # 선물 거래 (1x 초과)
                result = self._calculate_futures_position(
                    user_capital, target_risk_amount, required_position_value,
                    calculated_leverage, price_diff_percent, entry_price, stop_loss
                )

            # 추가 정보 추가
            result.update({
                'symbol': symbol or 'UNKNOWN',
                'timestamp': datetime.now().isoformat(),
                'risk_percent_input': risk_percent,
                'price_diff_percent': price_diff_percent * 100,
                'target_risk_amount': target_risk_amount,
                'calculated_leverage': calculated_leverage
            })

            return result

        except Exception as e:
            logger.error(f"Position calculation error: {e}")
            return self._get_error_result(f"계산 중 오류 발생: {str(e)}")

    def _calculate_spot_position(self, user_capital: float, target_risk_amount: float,
                               required_position_value: float, price_diff_percent: float,
                               entry_price: float, stop_loss: float) -> Dict[str, Any]:
        """현물 거래 포지션 계산"""

        # 사용 가능한 자본 범위 내에서 포지션 조정
        if required_position_value > user_capital:
            # 자본 초과 시 최대한 활용
            actual_position_value = user_capital
            actual_risk = actual_position_value * price_diff_percent
            margin_used = actual_position_value
            capital_usage_percent = 100.0
        else:
            # 계산된 포지션 그대로 사용
            actual_position_value = required_position_value
            actual_risk = target_risk_amount
            margin_used = required_position_value
            capital_usage_percent = (margin_used / user_capital) * 100

        # 거래량 계산
        quantity = actual_position_value / entry_price

        return {
            'trade_type': 'SPOT',
            'position_value': actual_position_value,
            'quantity': quantity,
            'leverage': 1.0,
            'margin_used': margin_used,
            'capital_usage_percent': capital_usage_percent,
            'actual_risk_amount': actual_risk,
            'actual_risk_percent': (actual_risk / user_capital) * 100,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'valid': True,
            'message': f'현물 거래 - 자본의 {capital_usage_percent:.1f}% 사용'
        }

    def _calculate_futures_position(self, user_capital: float, target_risk_amount: float,
                                  required_position_value: float, calculated_leverage: float,
                                  price_diff_percent: float, entry_price: float,
                                  stop_loss: float) -> Dict[str, Any]:
        """선물 거래 포지션 계산"""

        # 최적 레버리지 선택
        actual_leverage = self._select_optimal_leverage(calculated_leverage)

        # 마진 계산
        if actual_leverage <= calculated_leverage:
            # 낮은 레버리지 선택 시: 마진 조정
            margin_used = required_position_value / actual_leverage
            if margin_used > user_capital:
                margin_used = user_capital
                actual_position_value = margin_used * actual_leverage
            else:
                actual_position_value = required_position_value
        else:
            # 높은 레버리지 선택 시: 자본 100% 활용
            margin_used = user_capital
            actual_position_value = margin_used * actual_leverage

        # 실제 리스크 계산
        actual_risk = actual_position_value * price_diff_percent
        capital_usage_percent = (margin_used / user_capital) * 100

        # 거래량 계산
        quantity = actual_position_value / entry_price

        return {
            'trade_type': 'FUTURES',
            'position_value': actual_position_value,
            'quantity': quantity,
            'leverage': actual_leverage,
            'margin_used': margin_used,
            'capital_usage_percent': capital_usage_percent,
            'actual_risk_amount': actual_risk,
            'actual_risk_percent': (actual_risk / user_capital) * 100,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'valid': True,
            'message': f'선물 거래 {actual_leverage}x - 마진 {margin_used:.0f} USDT'
        }

    def _select_optimal_leverage(self, calculated_leverage: float) -> float:
        """계산된 레버리지에 가장 가까운 사용 가능한 레버리지 선택"""

        # 최대 레버리지 제한
        calculated_leverage = min(calculated_leverage, self.max_leverage)

        # 가장 가까운 레버리지 찾기
        best_leverage = min(self.available_leverages,
                           key=lambda x: abs(x - calculated_leverage))

        return float(best_leverage)

    def _validate_inputs(self, user_capital: float, risk_percent: float,
                        entry_price: float, stop_loss: float) -> bool:
        """입력값 검증"""

        if user_capital <= 0:
            logger.warning("Invalid user capital")
            return False

        if not (0.1 <= risk_percent <= 20.0):
            logger.warning("Risk percent out of range")
            return False

        if entry_price <= 0 or stop_loss <= 0:
            logger.warning("Invalid prices")
            return False

        if abs(entry_price - stop_loss) / entry_price > 0.5:  # 50% 이상 차이
            logger.warning("Price difference too large")
            return False

        return True

    def _get_error_result(self, message: str) -> Dict[str, Any]:
        """오류 결과 반환"""
        return {
            'valid': False,
            'message': message,
            'trade_type': None,
            'position_value': 0,
            'quantity': 0,
            'leverage': 0,
            'margin_used': 0,
            'capital_usage_percent': 0,
            'actual_risk_amount': 0,
            'actual_risk_percent': 0
        }

    def get_risk_levels(self, user_capital: float, entry_price: float,
                       stop_loss: float, symbol: str = None) -> Dict[str, Any]:
        """다양한 리스크 레벨별 포지션 제안"""

        risk_levels = {
            'conservative': 1.0,  # 1%
            'moderate': 2.5,      # 2.5%
            'aggressive': 5.0     # 5%
        }

        results = {}

        for level, risk_percent in risk_levels.items():
            result = self.calculate_position(
                user_capital, risk_percent, entry_price, stop_loss, symbol
            )
            results[level] = result

        return results

    def calculate_stop_loss_from_risk(self, user_capital: float, risk_percent: float,
                                    entry_price: float, position_value: float,
                                    direction: str = 'LONG') -> float:
        """리스크와 포지션 크기로부터 손절가 계산"""

        target_risk_amount = user_capital * (risk_percent / 100)
        price_diff = target_risk_amount / (position_value / entry_price)

        if direction.upper() == 'LONG':
            stop_loss = entry_price - price_diff
        else:  # SHORT
            stop_loss = entry_price + price_diff

        return max(stop_loss, 0)  # 음수 방지


# 싱글톤 인스턴스
_risk_calculator = None

def get_risk_calculator() -> RiskCalculator:
    """리스크 계산기 인스턴스 반환"""
    global _risk_calculator
    if _risk_calculator is None:
        _risk_calculator = RiskCalculator()
    return _risk_calculator