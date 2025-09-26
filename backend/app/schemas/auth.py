"""Authentication-related Pydantic schemas."""

from typing import Optional
from pydantic import BaseModel
from uuid import UUID


class Token(BaseModel):
    """JWT token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data schema."""
    user_id: Optional[UUID] = None
    username: Optional[str] = None