"""
선물 거래 전용 포지션 관리 시스템
Dynamic Position Management for Futures Trading
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PositionStatus(Enum):
    ACTIVE = "active"
    CLOSING = "closing"
    CLOSED = "closed"
    STOPPED = "stopped"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FuturesPosition:
    """선물 포지션 정보"""
    symbol: str
    side: str  # LONG or SHORT
    entry_price: float
    current_price: float
    quantity: float
    leverage: int
    margin_used: float
    unrealized_pnl: float
    entry_time: datetime
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    liquidation_price: Optional[float] = None
    trailing_stop_percent: Optional[float] = None
    status: PositionStatus = PositionStatus.ACTIVE
    risk_level: RiskLevel = RiskLevel.LOW

    @property
    def position_value(self) -> float:
        """포지션 가치 계산"""
        return self.quantity * self.current_price

    @property
    def pnl_percentage(self) -> float:
        """손익률 계산"""
        if self.side == "LONG":
            return ((self.current_price - self.entry_price) / self.entry_price) * 100 * self.leverage
        else:  # SHORT
            return ((self.entry_price - self.current_price) / self.entry_price) * 100 * self.leverage

    @property
    def margin_ratio(self) -> float:
        """마진 비율 계산"""
        if self.liquidation_price:
            if self.side == "LONG":
                return abs(self.current_price - self.liquidation_price) / self.current_price * 100
            else:  # SHORT
                return abs(self.liquidation_price - self.current_price) / self.current_price * 100
        return 100.0


class FuturesPositionManager:
    """선물 포지션 관리자"""

    def __init__(self):
        self.positions: Dict[str, FuturesPosition] = {}
        self.position_history: List[Dict] = []

    def add_position(self, position_data: Dict) -> FuturesPosition:
        """새 포지션 추가"""
        try:
            position = FuturesPosition(
                symbol=position_data["symbol"],
                side=position_data["side"],
                entry_price=float(position_data["entry_price"]),
                current_price=float(position_data["current_price"]),
                quantity=float(position_data["quantity"]),
                leverage=int(position_data["leverage"]),
                margin_used=float(position_data["margin_used"]),
                unrealized_pnl=float(position_data.get("unrealized_pnl", 0)),
                entry_time=datetime.now(),
                stop_loss_price=position_data.get("stop_loss_price"),
                take_profit_price=position_data.get("take_profit_price"),
                liquidation_price=position_data.get("liquidation_price"),
                trailing_stop_percent=position_data.get("trailing_stop_percent")
            )

            # 리스크 레벨 설정
            position.risk_level = self._calculate_risk_level(position)

            # 포지션 저장
            position_key = f"{position.symbol}_{position.side}"
            self.positions[position_key] = position

            logger.info(f"새 포지션 추가: {position_key} - {position.quantity}@{position.entry_price}")

            return position

        except Exception as e:
            logger.error(f"포지션 추가 실패: {e}")
            raise

    def update_position_price(self, symbol: str, side: str, current_price: float) -> Optional[FuturesPosition]:
        """포지션 현재가 업데이트"""
        position_key = f"{symbol}_{side}"

        if position_key not in self.positions:
            return None

        position = self.positions[position_key]
        position.current_price = current_price

        # PnL 업데이트
        position.unrealized_pnl = self._calculate_unrealized_pnl(position)

        # 리스크 레벨 업데이트
        position.risk_level = self._calculate_risk_level(position)

        # 트레일링 스톱 업데이트
        if position.trailing_stop_percent:
            self._update_trailing_stop(position)

        return position

    def _calculate_unrealized_pnl(self, position: FuturesPosition) -> float:
        """미실현 손익 계산"""
        price_diff = position.current_price - position.entry_price

        if position.side == "SHORT":
            price_diff = -price_diff

        return price_diff * position.quantity

    def _calculate_risk_level(self, position: FuturesPosition) -> RiskLevel:
        """리스크 레벨 계산"""
        margin_ratio = position.margin_ratio
        pnl_percent = position.pnl_percentage

        # 청산가 근접도 기준
        if margin_ratio <= 10:  # 청산가 10% 이내
            return RiskLevel.CRITICAL
        elif margin_ratio <= 25:  # 청산가 25% 이내
            return RiskLevel.HIGH
        elif margin_ratio <= 50 or pnl_percent <= -30:  # 손실 30% 이상
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _update_trailing_stop(self, position: FuturesPosition) -> None:
        """트레일링 스톱 업데이트"""
        if not position.trailing_stop_percent:
            return

        current_pnl_percent = position.pnl_percentage

        if current_pnl_percent > 0:  # 수익 상태일 때만
            if position.side == "LONG":
                new_stop = position.current_price * (1 - position.trailing_stop_percent / 100)
                if not position.stop_loss_price or new_stop > position.stop_loss_price:
                    position.stop_loss_price = new_stop
                    logger.info(f"트레일링 스톱 업데이트: {position.symbol} -> {new_stop:.4f}")
            else:  # SHORT
                new_stop = position.current_price * (1 + position.trailing_stop_percent / 100)
                if not position.stop_loss_price or new_stop < position.stop_loss_price:
                    position.stop_loss_price = new_stop
                    logger.info(f"트레일링 스톱 업데이트: {position.symbol} -> {new_stop:.4f}")

    def check_stop_conditions(self, symbol: str, side: str) -> Optional[Dict]:
        """손절/익절 조건 체크"""
        position_key = f"{symbol}_{side}"

        if position_key not in self.positions:
            return None

        position = self.positions[position_key]
        current_price = position.current_price

        # 손절가 체크
        if position.stop_loss_price:
            if position.side == "LONG" and current_price <= position.stop_loss_price:
                return {
                    "action": "STOP_LOSS",
                    "reason": f"가격이 손절가 {position.stop_loss_price} 아래로 떨어짐",
                    "current_price": current_price,
                    "trigger_price": position.stop_loss_price,
                    "pnl": position.unrealized_pnl
                }
            elif position.side == "SHORT" and current_price >= position.stop_loss_price:
                return {
                    "action": "STOP_LOSS",
                    "reason": f"가격이 손절가 {position.stop_loss_price} 위로 올라감",
                    "current_price": current_price,
                    "trigger_price": position.stop_loss_price,
                    "pnl": position.unrealized_pnl
                }

        # 익절가 체크
        if position.take_profit_price:
            if position.side == "LONG" and current_price >= position.take_profit_price:
                return {
                    "action": "TAKE_PROFIT",
                    "reason": f"가격이 익절가 {position.take_profit_price}에 도달",
                    "current_price": current_price,
                    "trigger_price": position.take_profit_price,
                    "pnl": position.unrealized_pnl
                }
            elif position.side == "SHORT" and current_price <= position.take_profit_price:
                return {
                    "action": "TAKE_PROFIT",
                    "reason": f"가격이 익절가 {position.take_profit_price}에 도달",
                    "current_price": current_price,
                    "trigger_price": position.take_profit_price,
                    "pnl": position.unrealized_pnl
                }

        return None

    def get_portfolio_summary(self) -> Dict:
        """포트폴리오 요약 정보"""
        active_positions = [pos for pos in self.positions.values()
                          if pos.status == PositionStatus.ACTIVE]

        total_margin = sum(pos.margin_used for pos in active_positions)
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in active_positions)

        # 리스크 레벨별 분류
        risk_counts = {level.value: 0 for level in RiskLevel}
        for pos in active_positions:
            risk_counts[pos.risk_level.value] += 1

        return {
            "total_positions": len(active_positions),
            "total_margin_used": total_margin,
            "total_unrealized_pnl": total_unrealized_pnl,
            "risk_distribution": risk_counts,
            "positions": [asdict(pos) for pos in active_positions]
        }

    def close_position(self, symbol: str, side: str, close_price: float, reason: str = "Manual") -> bool:
        """포지션 청산"""
        position_key = f"{symbol}_{side}"

        if position_key not in self.positions:
            return False

        position = self.positions[position_key]
        position.status = PositionStatus.CLOSED

        # 최종 PnL 계산
        final_pnl = self._calculate_unrealized_pnl(position)

        # 히스토리에 추가
        self.position_history.append({
            "symbol": position.symbol,
            "side": position.side,
            "entry_price": position.entry_price,
            "close_price": close_price,
            "quantity": position.quantity,
            "leverage": position.leverage,
            "margin_used": position.margin_used,
            "pnl": final_pnl,
            "pnl_percent": position.pnl_percentage,
            "duration": datetime.now() - position.entry_time,
            "close_reason": reason,
            "close_time": datetime.now()
        })

        # 활성 포지션에서 제거
        del self.positions[position_key]

        logger.info(f"포지션 청산: {symbol}_{side} - PnL: {final_pnl:.2f} ({reason})")

        return True