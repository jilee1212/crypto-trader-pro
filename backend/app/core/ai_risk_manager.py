"""
AI-based Dynamic Risk Management System for Futures Trading
정밀한 리스크 계산과 최적 레버리지 조합 계산 시스템
"""

from typing import Dict, Optional, List, Tuple
from decimal import Decimal, ROUND_HALF_UP
import logging

logger = logging.getLogger(__name__)


class AIRiskManager:
    """AI 기반 동적 리스크 관리 시스템"""

    def __init__(self, account_balance: float, risk_percentage: float = 3.0):
        self.account_balance = float(account_balance)
        self.risk_percentage = float(risk_percentage)
        self.target_risk_amount = self.account_balance * (self.risk_percentage / 100)
        self.risk_tolerance = 1.0  # ±1% 허용 오차
        self.max_leverage = 20  # 최대 레버리지 제한

        # 가능한 레버리지 옵션들 (바이낸스 선물 거래소 기준)
        self.leverage_options = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                               11, 12, 13, 14, 15, 16, 17, 18, 19, 20]

    def calculate_position_size(self, entry_price: float, stop_loss_price: float) -> Dict:
        """
        AI 리스크 관리 포지션 사이징 계산 (정밀 버전)

        Args:
            entry_price: 진입 예상 가격
            stop_loss_price: 손절 가격

        Returns:
            Dict: 최적화된 포지션 정보
        """
        try:
            # 입력값 검증
            if entry_price <= 0 or stop_loss_price <= 0:
                raise ValueError("가격은 0보다 큰 값이어야 합니다")

            if entry_price == stop_loss_price:
                raise ValueError("진입가와 손절가가 동일할 수 없습니다")

            # 손절 폭 계산 (백분율)
            price_diff_percent = abs(entry_price - stop_loss_price) / entry_price

            # 필요한 총 배율 계산
            required_multiplier = self.target_risk_amount / (self.account_balance * price_diff_percent)

            logger.info(f"Risk calculation: entry={entry_price}, stop={stop_loss_price}, "
                       f"diff={price_diff_percent:.4f}, required_multiplier={required_multiplier:.3f}")

            # 1배 이하인 경우
            if required_multiplier <= 1:
                leverage = 1
                seed_usage_percent = required_multiplier * 100
                actual_multiplier = required_multiplier
                optimization_notes = "레버리지 불필요 (1배 이하)"

            else:
                # 1배 초과인 경우 - 최적 레버리지와 시드 조합 계산
                best_combination = self._find_optimal_leverage_combination(required_multiplier)

                if not best_combination:
                    # 최대 레버리지로 fallback
                    leverage = self.max_leverage
                    seed_usage_percent = min((required_multiplier / self.max_leverage) * 100, 100)
                    actual_multiplier = (seed_usage_percent / 100) * leverage
                    optimization_notes = f"최대 레버리지 {self.max_leverage}배 적용 (제한)"
                else:
                    leverage = best_combination["leverage"]
                    seed_usage_percent = best_combination["seed_percent"]
                    actual_multiplier = best_combination["actual_multiplier"]
                    optimization_notes = f"최적 조합 발견 (오차: {best_combination['error_percent']:.2f}%)"

            # 포지션 크기 및 마진 계산
            position_value = self.account_balance * actual_multiplier
            margin_used = self.account_balance * (seed_usage_percent / 100)
            position_quantity = position_value / entry_price

            # 실제 손실 위험 계산
            actual_risk_amount = position_value * price_diff_percent
            risk_accuracy = self._calculate_risk_accuracy(actual_multiplier, required_multiplier)

            return {
                # 기본 정보
                "position_value": round(position_value, 2),
                "position_quantity": round(position_quantity, 6),
                "leverage": leverage,
                "seed_usage_percent": round(seed_usage_percent, 1),
                "margin_used": round(margin_used, 2),

                # 배율 정보
                "actual_multiplier": round(actual_multiplier, 3),
                "target_multiplier": round(required_multiplier, 3),

                # 리스크 정보
                "target_risk_amount": round(self.target_risk_amount, 2),
                "actual_risk_amount": round(actual_risk_amount, 2),
                "risk_accuracy": round(risk_accuracy, 1),
                "risk_percentage": self.risk_percentage,

                # 가격 정보
                "entry_price": entry_price,
                "stop_loss_price": stop_loss_price,
                "price_diff_percent": round(price_diff_percent * 100, 2),

                # 계좌 정보
                "account_balance": self.account_balance,
                "remaining_balance": round(self.account_balance - margin_used, 2),

                # 최적화 정보
                "optimization_notes": optimization_notes,
                "is_optimal": risk_accuracy >= 99.0,

                # 경고 및 상태
                "warnings": self._generate_warnings(leverage, seed_usage_percent, risk_accuracy),
                "risk_level": self._assess_risk_level(leverage, seed_usage_percent)
            }

        except Exception as e:
            logger.error(f"Position calculation error: {e}")
            raise

    def _find_optimal_leverage_combination(self, required_multiplier: float) -> Optional[Dict]:
        """최적의 레버리지와 시드 조합 찾기"""

        best_option = None
        min_error = float('inf')

        for leverage in self.leverage_options:
            if leverage > self.max_leverage:
                continue

            # 필요한 시드 비율 계산
            required_seed_percent = (required_multiplier / leverage) * 100

            # 시드 비율이 100%를 초과하는 경우 스킵
            if required_seed_percent > 100:
                continue

            # 실제 달성 가능한 배율
            actual_multiplier = (required_seed_percent / 100) * leverage

            # 목표 배율과의 오차 계산
            error = abs(actual_multiplier - required_multiplier)
            error_percent = (error / required_multiplier) * 100

            # 허용 오차 내에서 가장 좋은 조합 선택
            if error_percent <= self.risk_tolerance and error < min_error:
                min_error = error
                best_option = {
                    "leverage": leverage,
                    "seed_percent": round(required_seed_percent, 1),
                    "actual_multiplier": actual_multiplier,
                    "error_percent": round(error_percent, 2)
                }

        # 허용 오차 내 조합이 없는 경우, 가장 가까운 조합 선택
        if best_option is None:
            min_error = float('inf')
            for leverage in self.leverage_options:
                if leverage > self.max_leverage:
                    continue

                required_seed_percent = (required_multiplier / leverage) * 100
                if required_seed_percent > 100:
                    continue

                actual_multiplier = (required_seed_percent / 100) * leverage
                error = abs(actual_multiplier - required_multiplier)

                if error < min_error:
                    min_error = error
                    best_option = {
                        "leverage": leverage,
                        "seed_percent": round(required_seed_percent, 1),
                        "actual_multiplier": actual_multiplier,
                        "error_percent": round((error / required_multiplier) * 100, 2)
                    }

        return best_option

    def _calculate_risk_accuracy(self, actual_multiplier: float, target_multiplier: float) -> float:
        """리스크 정확도 계산"""
        if target_multiplier == 0:
            return 100.0

        accuracy = (1 - abs(actual_multiplier - target_multiplier) / target_multiplier) * 100
        return max(accuracy, 0)

    def _generate_warnings(self, leverage: int, seed_usage_percent: float, risk_accuracy: float) -> List[str]:
        """경고 메시지 생성"""
        warnings = []

        if leverage >= 10:
            warnings.append(f"높은 레버리지 ({leverage}배) - 주의 필요")

        if seed_usage_percent >= 90:
            warnings.append(f"높은 시드 사용률 ({seed_usage_percent}%) - 추가 자금 확보 권장")

        if risk_accuracy < 95:
            warnings.append(f"리스크 정확도 낮음 ({risk_accuracy:.1f}%) - 레버리지 제약으로 인한 오차")

        return warnings

    def _assess_risk_level(self, leverage: int, seed_usage_percent: float) -> str:
        """리스크 레벨 평가"""
        if leverage >= 15 or seed_usage_percent >= 80:
            return "HIGH"
        elif leverage >= 8 or seed_usage_percent >= 60:
            return "MEDIUM"
        elif leverage >= 4 or seed_usage_percent >= 40:
            return "LOW"
        else:
            return "VERY_LOW"

    def calculate_multiple_scenarios(self, entry_price: float, stop_loss_prices: List[float]) -> Dict:
        """여러 손절가 시나리오에 대한 계산"""
        scenarios = {}

        for stop_price in stop_loss_prices:
            try:
                result = self.calculate_position_size(entry_price, stop_price)
                scenarios[f"stop_at_{stop_price}"] = result
            except Exception as e:
                scenarios[f"stop_at_{stop_price}"] = {"error": str(e)}

        return scenarios

    def get_optimal_stop_loss_range(self, entry_price: float, min_leverage: int = 1, max_leverage: int = 10) -> Dict:
        """주어진 레버리지 범위에서 최적 손절가 범위 계산"""
        optimal_stops = []

        for leverage in range(min_leverage, max_leverage + 1):
            # 해당 레버리지에서 정확히 목표 리스크를 달성하는 손절가 계산
            required_multiplier = leverage  # 100% 시드 사용 가정
            price_diff_percent = self.target_risk_amount / (self.account_balance * required_multiplier)

            if price_diff_percent < 0.001 or price_diff_percent > 0.1:  # 0.1% ~ 10% 범위
                continue

            stop_loss_price = entry_price * (1 - price_diff_percent)
            optimal_stops.append({
                "leverage": leverage,
                "stop_loss_price": round(stop_loss_price, 6),
                "price_diff_percent": round(price_diff_percent * 100, 2)
            })

        return {
            "entry_price": entry_price,
            "optimal_stops": optimal_stops,
            "risk_amount": self.target_risk_amount,
            "risk_percentage": self.risk_percentage
        }


class FuturesRiskMonitor:
    """선물 거래 리스크 실시간 모니터링"""

    def __init__(self):
        self.max_margin_ratio = 0.75  # 75% 경고
        self.emergency_margin_ratio = 0.85  # 85% 긴급 상황
        self.max_daily_loss_percent = 10.0  # 일일 최대 손실 10%

    def assess_position_risk(self, position: Dict, account_balance: float) -> Dict:
        """개별 포지션 리스크 평가"""

        # 마진 비율 계산
        margin_ratio = position.get("initial_margin", 0) / account_balance

        # 청산가까지의 거리 계산
        entry_price = position.get("entry_price", 0)
        liquidation_price = position.get("liquidation_price", 0)
        mark_price = position.get("mark_price", entry_price)

        if liquidation_price > 0 and entry_price > 0:
            if position.get("side") == "LONG":
                liquidation_distance = ((mark_price - liquidation_price) / mark_price) * 100
            else:  # SHORT
                liquidation_distance = ((liquidation_price - mark_price) / mark_price) * 100
        else:
            liquidation_distance = 100.0

        # 미실현 손익 비율
        unrealized_pnl = position.get("unrealized_pnl", 0)
        pnl_percent = (unrealized_pnl / account_balance) * 100

        # 리스크 레벨 결정
        risk_level = "LOW"
        alerts = []

        if margin_ratio >= self.emergency_margin_ratio:
            risk_level = "CRITICAL"
            alerts.append("긴급: 마진 비율 위험 수준")
        elif margin_ratio >= self.max_margin_ratio:
            risk_level = "HIGH"
            alerts.append("경고: 마진 비율 높음")

        if liquidation_distance <= 5.0:
            risk_level = "CRITICAL"
            alerts.append("긴급: 청산가 근접")
        elif liquidation_distance <= 15.0:
            risk_level = "HIGH"
            alerts.append("경고: 청산가 접근")

        if pnl_percent <= -5.0:
            risk_level = "HIGH"
            alerts.append("경고: 큰 미실현 손실")

        return {
            "symbol": position.get("symbol"),
            "risk_level": risk_level,
            "margin_ratio": round(margin_ratio * 100, 2),
            "liquidation_distance": round(liquidation_distance, 2),
            "pnl_percent": round(pnl_percent, 2),
            "alerts": alerts,
            "requires_action": risk_level in ["HIGH", "CRITICAL"]
        }

    def assess_portfolio_risk(self, positions: List[Dict], account_info: Dict) -> Dict:
        """전체 포트폴리오 리스크 평가"""

        total_balance = account_info.get("total_wallet_balance", 0)
        total_unrealized_pnl = sum(pos.get("unrealized_pnl", 0) for pos in positions)
        total_margin_balance = account_info.get("total_margin_balance", 0)

        # 포트폴리오 지표 계산
        portfolio_pnl_percent = (total_unrealized_pnl / total_balance) * 100 if total_balance > 0 else 0
        overall_margin_ratio = (total_margin_balance / total_balance) if total_balance > 0 else 0

        # 포지션별 리스크 평가
        position_risks = [self.assess_position_risk(pos, total_balance) for pos in positions]
        critical_positions = [risk for risk in position_risks if risk["risk_level"] == "CRITICAL"]
        high_risk_positions = [risk for risk in position_risks if risk["risk_level"] == "HIGH"]

        # 전체 포트폴리오 리스크 레벨 결정
        if critical_positions or portfolio_pnl_percent <= -self.max_daily_loss_percent:
            portfolio_risk_level = "CRITICAL"
        elif high_risk_positions or portfolio_pnl_percent <= -5.0:
            portfolio_risk_level = "HIGH"
        elif overall_margin_ratio >= 0.5 or portfolio_pnl_percent <= -2.0:
            portfolio_risk_level = "MEDIUM"
        else:
            portfolio_risk_level = "LOW"

        return {
            "portfolio_risk_level": portfolio_risk_level,
            "total_balance": total_balance,
            "total_unrealized_pnl": total_unrealized_pnl,
            "portfolio_pnl_percent": round(portfolio_pnl_percent, 2),
            "overall_margin_ratio": round(overall_margin_ratio * 100, 2),
            "position_count": len(positions),
            "critical_positions": len(critical_positions),
            "high_risk_positions": len(high_risk_positions),
            "position_risks": position_risks,
            "requires_immediate_action": portfolio_risk_level == "CRITICAL",
            "recommendation": self._get_risk_recommendation(portfolio_risk_level, critical_positions, high_risk_positions)
        }

    def _get_risk_recommendation(self, risk_level: str, critical_positions: List, high_risk_positions: List) -> str:
        """리스크 상황에 따른 권장사항"""

        if risk_level == "CRITICAL":
            if critical_positions:
                return "즉시 고위험 포지션 청산 또는 마진 추가 필요"
            else:
                return "일일 손실 한도 초과 - 추가 거래 중단 권장"

        elif risk_level == "HIGH":
            return "포지션 크기 줄이기 또는 손절 설정 검토 필요"

        elif risk_level == "MEDIUM":
            return "리스크 모니터링 강화 및 신중한 거래 진행"

        else:
            return "현재 리스크 수준 양호"