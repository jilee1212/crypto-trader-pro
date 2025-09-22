"""
SQLAlchemy ORM Models for Crypto Trader Pro
24시간 무인 자동매매 시스템의 데이터베이스 모델
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    """사용자 테이블"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    trading_enabled = Column(Boolean, default=False)

    # 관계 설정
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    trading_settings = relationship("TradingSettings", back_populates="user", cascade="all, delete-orphan")
    trading_sessions = relationship("TradingSession", back_populates="user", cascade="all, delete-orphan")
    trades = relationship("TradeHistory", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

class ApiKey(Base):
    """API 키 테이블 (암호화 저장)"""
    __tablename__ = 'api_keys'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    exchange = Column(String(50), nullable=False)  # 'binance', 'bybit', etc.
    api_key = Column(Text, nullable=False)  # 암호화된 API 키
    api_secret = Column(Text, nullable=False)  # 암호화된 API 시크릿
    is_testnet = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계 설정
    user = relationship("User", back_populates="api_keys")

    def __repr__(self):
        return f"<ApiKey(id={self.id}, user_id={self.user_id}, exchange='{self.exchange}', testnet={self.is_testnet})>"

class TradingSettings(Base):
    """거래 설정 테이블"""
    __tablename__ = 'trading_settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    risk_percentage = Column(Float, default=2.0)  # 거래당 리스크 비율 (%)
    max_positions = Column(Integer, default=3)  # 최대 동시 포지션 수
    daily_loss_limit = Column(Float, default=5.0)  # 일일 손실 한도 (%)
    auto_trading_enabled = Column(Boolean, default=False)  # 자동 거래 활성화
    strategy_config = Column(Text, nullable=True)  # JSON 형태의 전략 설정
    symbols = Column(Text, nullable=True)  # JSON 배열 형태의 거래 심볼
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계 설정
    user = relationship("User", back_populates="trading_settings")

    def __repr__(self):
        return f"<TradingSettings(id={self.id}, user_id={self.user_id}, risk={self.risk_percentage}%)>"

class TradingSession(Base):
    """활성 거래 세션 테이블"""
    __tablename__ = 'trading_sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    session_start = Column(DateTime, default=datetime.utcnow)
    session_end = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    total_trades = Column(Integer, default=0)
    profit_loss = Column(Float, default=0.0)  # 세션 총 손익

    # 관계 설정
    user = relationship("User", back_populates="trading_sessions")
    trades = relationship("TradeHistory", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TradingSession(id={self.id}, user_id={self.user_id}, active={self.is_active}, pnl={self.profit_loss})>"

class TradeHistory(Base):
    """거래 기록 테이블"""
    __tablename__ = 'trade_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    session_id = Column(Integer, ForeignKey('trading_sessions.id'), nullable=True)
    symbol = Column(String(20), nullable=False)  # 'BTCUSDT', 'ETHUSDT', etc.
    side = Column(String(10), nullable=False)  # 'BUY', 'SELL'
    amount = Column(Float, nullable=False)  # 거래 수량
    price = Column(Float, nullable=False)  # 거래 가격
    timestamp = Column(DateTime, default=datetime.utcnow)
    profit_loss = Column(Float, nullable=True)  # 개별 거래 손익
    signal_confidence = Column(Integer, nullable=True)  # AI 신호 신뢰도 (0-100)

    # 관계 설정
    user = relationship("User", back_populates="trades")
    session = relationship("TradingSession", back_populates="trades")

    def __repr__(self):
        return f"<TradeHistory(id={self.id}, symbol='{self.symbol}', side='{self.side}', amount={self.amount}, price={self.price})>"

class NotificationSettings(Base):
    """알림 설정 테이블"""
    __tablename__ = 'notification_settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    email_enabled = Column(Boolean, default=True)
    telegram_enabled = Column(Boolean, default=False)
    telegram_chat_id = Column(String(50), nullable=True)
    web_notifications = Column(Boolean, default=True)
    notify_trades = Column(Boolean, default=True)
    notify_profit_loss = Column(Boolean, default=True)
    notify_errors = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<NotificationSettings(user_id={self.user_id}, email={self.email_enabled}, telegram={self.telegram_enabled})>"