"""
Futures trading schemas for Binance USDT-M Futures
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from decimal import Decimal

class ApiKeysRequest(BaseModel):
    api_key: str
    api_secret: str
    testnet: bool = False


class FuturesAccountInfoResponse(BaseModel):
    success: bool
    data: Optional['FuturesAccountData'] = None
    error: Optional[str] = None


class FuturesAccountData(BaseModel):
    can_trade: bool
    can_withdraw: bool
    can_deposit: bool
    account_type: str
    total_wallet_balance: float
    total_unrealized_pnl: float
    total_margin_balance: float
    available_balance: float
    max_withdraw_amount: float
    balances: List['FuturesBalance']


class FuturesBalance(BaseModel):
    asset: str
    wallet_balance: float
    unrealized_profit: float
    margin_balance: float
    available_balance: float
    max_withdraw_amount: float


class PositionInfo(BaseModel):
    symbol: str
    position_amt: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    percentage: float
    side: Literal["LONG", "SHORT"]
    leverage: int
    margin_type: Literal["cross", "isolated"]
    isolated_margin: float
    liquidation_price: Optional[float] = None


class PositionsResponse(BaseModel):
    success: bool
    data: Optional[List[PositionInfo]] = None
    error: Optional[str] = None


class FuturesTickerData(BaseModel):
    symbol: str
    price_change: float
    price_change_percent: float
    last_price: float
    high_price: float
    low_price: float
    volume: float
    quote_volume: float
    count: int
    open_interest: float


class FuturesMarketDataResponse(BaseModel):
    success: bool
    data: Optional[List[FuturesTickerData]] = None
    error: Optional[str] = None


class FuturesOrderRequest(BaseModel):
    symbol: str
    side: Literal["BUY", "SELL"]
    type: Literal["MARKET", "LIMIT", "STOP", "STOP_MARKET", "TAKE_PROFIT", "TAKE_PROFIT_MARKET"]
    quantity: Optional[float] = None
    price: Optional[float] = None
    time_in_force: Optional[Literal["GTC", "IOC", "FOK", "GTX"]] = "GTC"
    reduce_only: Optional[bool] = False
    close_position: Optional[bool] = False
    stop_price: Optional[float] = None
    working_type: Optional[Literal["MARK_PRICE", "CONTRACT_PRICE"]] = "CONTRACT_PRICE"


class FuturesOrderInfo(BaseModel):
    order_id: int
    symbol: str
    status: str
    type: str
    side: str
    quantity: float
    price: Optional[float] = None
    executed_qty: float
    cumulative_quote_qty: float
    time: int
    reduce_only: bool = False
    close_position: bool = False


class FuturesOrderResponse(BaseModel):
    success: bool
    data: Optional[FuturesOrderInfo] = None
    message: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[int] = None


class OpenFuturesOrdersResponse(BaseModel):
    success: bool
    data: Optional[List[FuturesOrderInfo]] = None
    error: Optional[str] = None


class LeverageRequest(BaseModel):
    symbol: str
    leverage: int = Field(..., ge=1, le=125, description="Leverage between 1 and 125")


class LeverageResponse(BaseModel):
    success: bool
    data: Optional['LeverageData'] = None
    error: Optional[str] = None


class LeverageData(BaseModel):
    symbol: str
    leverage: int
    max_notional_value: str


class MarginTypeRequest(BaseModel):
    symbol: str
    margin_type: Literal["ISOLATED", "CROSSED"]


class MarginTypeResponse(BaseModel):
    success: bool
    data: Optional['MarginTypeData'] = None
    message: Optional[str] = None
    error: Optional[str] = None


class MarginTypeData(BaseModel):
    symbol: str
    margin_type: str


class FuturesExchangeInfoResponse(BaseModel):
    success: bool
    data: Optional['FuturesExchangeData'] = None
    error: Optional[str] = None


class FuturesExchangeData(BaseModel):
    timezone: str
    server_time: int
    symbols: List['FuturesSymbolInfo']


class FuturesSymbolInfo(BaseModel):
    symbol: str
    base_asset: str
    quote_asset: str
    status: str
    contract_type: Optional[str] = None
    delivery_date: Optional[int] = None
    onboard_date: Optional[int] = None
    price_precision: int
    quantity_precision: int
    base_asset_precision: int
    quote_precision: int


class FuturesTestResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    testnet: bool
    can_trade: Optional[bool] = None
    can_withdraw: Optional[bool] = None
    can_deposit: Optional[bool] = None
    account_type: Optional[str] = None
    total_wallet_balance: Optional[float] = None
    total_unrealized_pnl: Optional[float] = None


class EmergencyStopResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[List[dict]] = None
    error: Optional[str] = None


# Update forward references
FuturesAccountInfoResponse.model_rebuild()
LeverageResponse.model_rebuild()
MarginTypeResponse.model_rebuild()
FuturesExchangeInfoResponse.model_rebuild()