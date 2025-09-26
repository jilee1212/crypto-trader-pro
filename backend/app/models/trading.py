"""Trading-related models for orders, portfolios, and transactions."""

from sqlalchemy import Column, String, Numeric, Boolean, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from .base import BaseModel, UUID


class OrderStatus(str, PyEnum):
    """Order status enumeration."""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PARTIAL = "partial"


class OrderSide(str, PyEnum):
    """Order side enumeration."""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, PyEnum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class TradingPair(BaseModel):
    """Trading pair information."""

    __tablename__ = "trading_pairs"

    symbol = Column(String(20), unique=True, nullable=False, index=True)
    base_asset = Column(String(10), nullable=False)
    quote_asset = Column(String(10), nullable=False)
    is_active = Column(Boolean, default=True)

    # Trading constraints
    min_qty = Column(Numeric(20, 8))
    max_qty = Column(Numeric(20, 8))
    step_size = Column(Numeric(20, 8))
    min_price = Column(Numeric(20, 8))
    max_price = Column(Numeric(20, 8))
    tick_size = Column(Numeric(20, 8))
    min_notional = Column(Numeric(20, 8))


class Order(BaseModel):
    """Order model for tracking trades."""

    __tablename__ = "orders"

    user_id = Column(UUID(), ForeignKey("users.id"), nullable=False)
    trading_pair_id = Column(UUID(), ForeignKey("trading_pairs.id"), nullable=False)

    # Order details
    exchange_order_id = Column(String(100), unique=True, index=True)
    symbol = Column(String(20), nullable=False)
    side = Column(Enum(OrderSide), nullable=False)
    type = Column(Enum(OrderType), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)

    # Quantities and prices
    quantity = Column(Numeric(20, 8), nullable=False)
    filled_quantity = Column(Numeric(20, 8), default=0)
    price = Column(Numeric(20, 8))
    stop_price = Column(Numeric(20, 8))
    average_price = Column(Numeric(20, 8))

    # Fees and costs
    fee = Column(Numeric(20, 8), default=0)
    fee_asset = Column(String(10))
    total_cost = Column(Numeric(20, 8))

    # Additional info
    time_in_force = Column(String(10), default="GTC")
    client_order_id = Column(String(100))
    error_message = Column(Text)

    # Relationships
    user = relationship("User", back_populates="orders")
    trading_pair = relationship("TradingPair")


class Portfolio(BaseModel):
    """User portfolio holdings."""

    __tablename__ = "portfolios"

    user_id = Column(UUID(), ForeignKey("users.id"), nullable=False)
    asset = Column(String(10), nullable=False, index=True)

    # Balances
    free_balance = Column(Numeric(20, 8), default=0)
    locked_balance = Column(Numeric(20, 8), default=0)

    # Calculated fields
    total_balance = Column(Numeric(20, 8), default=0)
    usd_value = Column(Numeric(20, 8), default=0)
    average_buy_price = Column(Numeric(20, 8))

    # Performance tracking
    unrealized_pnl = Column(Numeric(20, 8), default=0)
    realized_pnl = Column(Numeric(20, 8), default=0)
    total_invested = Column(Numeric(20, 8), default=0)

    # Relationships
    user = relationship("User", back_populates="portfolios")

    # Unique constraint on user_id and asset
    __table_args__ = (
        {"schema": None},
    )


class Transaction(BaseModel):
    """Transaction history for all portfolio changes."""

    __tablename__ = "transactions"

    user_id = Column(UUID(), ForeignKey("users.id"), nullable=False)
    order_id = Column(UUID(), ForeignKey("orders.id"))

    # Transaction details
    transaction_type = Column(String(20), nullable=False)  # trade, deposit, withdrawal, fee
    asset = Column(String(10), nullable=False)
    amount = Column(Numeric(20, 8), nullable=False)
    price = Column(Numeric(20, 8))
    fee = Column(Numeric(20, 8), default=0)
    fee_asset = Column(String(10))

    # Balance tracking
    balance_before = Column(Numeric(20, 8))
    balance_after = Column(Numeric(20, 8))

    # Additional info
    description = Column(Text)
    exchange_transaction_id = Column(String(100))

    # Relationships
    user = relationship("User", back_populates="transactions")
    order = relationship("Order")