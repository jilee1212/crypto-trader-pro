"""Trading-related Pydantic schemas."""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from ..models.trading import OrderSide, OrderType, OrderStatus


class OrderCreate(BaseModel):
    """Schema for creating a new order."""
    symbol: str = Field(..., description="Trading pair symbol (e.g., BTCUSDT)")
    side: OrderSide = Field(..., description="Order side (buy/sell)")
    type: OrderType = Field(..., description="Order type")
    quantity: Decimal = Field(..., gt=0, description="Order quantity")
    price: Optional[Decimal] = Field(None, gt=0, description="Order price for limit orders")
    stop_price: Optional[Decimal] = Field(None, gt=0, description="Stop price for stop orders")
    time_in_force: str = Field("GTC", description="Time in force")
    client_order_id: Optional[str] = None


class OrderResponse(BaseModel):
    """Schema for order response."""
    id: UUID
    symbol: str
    side: OrderSide
    type: OrderType
    status: OrderStatus
    quantity: Decimal
    filled_quantity: Decimal
    price: Optional[Decimal]
    average_price: Optional[Decimal]
    fee: Decimal
    fee_asset: Optional[str]
    total_cost: Optional[Decimal]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PortfolioResponse(BaseModel):
    """Schema for portfolio response."""
    id: UUID
    asset: str
    free_balance: Decimal
    locked_balance: Decimal
    total_balance: Decimal
    usd_value: Decimal
    average_buy_price: Optional[Decimal]
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    total_invested: Decimal
    updated_at: datetime

    class Config:
        from_attributes = True


class TransactionResponse(BaseModel):
    """Schema for transaction response."""
    id: UUID
    transaction_type: str
    asset: str
    amount: Decimal
    price: Optional[Decimal]
    fee: Decimal
    fee_asset: Optional[str]
    balance_before: Optional[Decimal]
    balance_after: Optional[Decimal]
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TradingPairResponse(BaseModel):
    """Schema for trading pair response."""
    id: UUID
    symbol: str
    base_asset: str
    quote_asset: str
    is_active: bool
    min_qty: Optional[Decimal]
    max_qty: Optional[Decimal]
    step_size: Optional[Decimal]
    min_price: Optional[Decimal]
    max_price: Optional[Decimal]
    tick_size: Optional[Decimal]
    min_notional: Optional[Decimal]

    class Config:
        from_attributes = True


# Binance API Schemas
class ApiKeysRequest(BaseModel):
    """Schema for LIVE TRADING API keys configuration."""
    api_key: str = Field(..., description="Binance LIVE API Key")
    api_secret: str = Field(..., description="Binance LIVE API Secret")
    # testnet removed - LIVE TRADING ONLY


class ApiTestResponse(BaseModel):
    """Schema for LIVE API connection test response."""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    trading_mode: str = "LIVE"  # Always LIVE
    can_trade: Optional[bool] = None
    can_withdraw: Optional[bool] = None
    can_deposit: Optional[bool] = None
    account_type: Optional[str] = None


class BalanceInfo(BaseModel):
    """Schema for balance information."""
    asset: str
    free: float
    locked: float


class AccountInfoResponse(BaseModel):
    """Schema for account information response."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class TickerPrice(BaseModel):
    """Schema for ticker price."""
    symbol: str
    price: float


class Ticker24hr(BaseModel):
    """Schema for 24hr ticker statistics."""
    symbol: str
    price_change: float
    price_change_percent: float
    last_price: float
    high_price: float
    low_price: float
    volume: float
    count: int


class KlineData(BaseModel):
    """Schema for kline/candlestick data."""
    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: int
    quote_asset_volume: float
    number_of_trades: int
    taker_buy_base_asset_volume: float
    taker_buy_quote_asset_volume: float


class KlineResponse(BaseModel):
    """Schema for kline response."""
    success: bool
    data: Optional[List[KlineData]] = None
    error: Optional[str] = None


class BinanceOrderRequest(BaseModel):
    """Schema for Binance order request."""
    symbol: str = Field(..., description="Trading pair symbol (e.g., BTCUSDT)")
    side: Literal["BUY", "SELL"] = Field(..., description="Order side")
    type: Literal["MARKET", "LIMIT"] = Field(..., description="Order type")
    quantity: float = Field(..., gt=0, description="Order quantity")
    price: Optional[float] = Field(None, description="Price for LIMIT orders")
    time_in_force: Literal["GTC", "IOC", "FOK"] = Field(default="GTC", description="Time in force")


class BinanceOrderInfo(BaseModel):
    """Schema for Binance order information."""
    order_id: int
    symbol: str
    status: str
    type: str
    side: str
    quantity: float
    price: Optional[float] = None
    executed_qty: float
    cumulative_quote_qty: Optional[float] = None
    time: int


class BinanceOrderResponse(BaseModel):
    """Schema for Binance order response."""
    success: bool
    data: Optional[BinanceOrderInfo] = None
    message: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[int] = None


class OpenOrdersResponse(BaseModel):
    """Schema for open orders response."""
    success: bool
    data: Optional[List[BinanceOrderInfo]] = None
    error: Optional[str] = None


class CancelOrderRequest(BaseModel):
    """Schema for cancel order request."""
    symbol: str
    order_id: int


class CancelOrderResponse(BaseModel):
    """Schema for cancel order response."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class MarketDataResponse(BaseModel):
    """Schema for market data response."""
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None