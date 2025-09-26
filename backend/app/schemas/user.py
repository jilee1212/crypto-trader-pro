"""User-related Pydantic schemas."""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    """Schema for user creation."""
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Schema for user updates."""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    max_daily_loss_percent: Optional[str] = None
    max_position_size_percent: Optional[str] = None


class UserLogin(BaseModel):
    """Schema for user login."""
    username: str
    password: str


class APIKeyUpdate(BaseModel):
    """Schema for updating API keys."""
    binance_api_key: Optional[str] = None
    binance_api_secret: Optional[str] = None
    use_testnet: bool = True


class UserResponse(UserBase):
    """Schema for user response."""
    id: UUID
    is_verified: bool
    use_testnet: bool
    max_daily_loss_percent: str
    max_position_size_percent: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True