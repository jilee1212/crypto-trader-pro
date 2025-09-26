"""User model for authentication and profile management."""

from sqlalchemy import Column, String, Boolean, Text
from sqlalchemy.orm import relationship
from .base import BaseModel


class User(BaseModel):
    """User model for authentication."""

    __tablename__ = "users"

    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Trading configuration
    binance_api_key = Column(Text)
    binance_api_secret = Column(Text)
    use_testnet = Column(Boolean, default=False)  # 메인넷이 기본값

    # Risk management settings (사용자 요청으로 제약 제거)
    max_daily_loss_percent = Column(String, default="100.0")  # 제한 해제
    max_position_size_percent = Column(String, default="100.0")  # 제한 해제

    # Relationships
    portfolios = relationship("Portfolio", back_populates="user")
    orders = relationship("Order", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")