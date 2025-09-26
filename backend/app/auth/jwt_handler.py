"""JWT token handling utilities."""

from datetime import datetime, timedelta
from typing import Optional, Union, TYPE_CHECKING
from jose import JWTError, jwt
from passlib.context import CryptContext
from uuid import UUID
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from ..core.config import settings
from ..schemas.auth import TokenData

if TYPE_CHECKING:
    from ..models.user import User

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[TokenData]:
    """Verify JWT token and return token data."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        # Check token type
        if payload.get("type") != token_type:
            return None

        user_id: str = payload.get("sub")
        username: str = payload.get("username")

        if user_id is None:
            return None

        token_data = TokenData(
            user_id=UUID(user_id),
            username=username
        )
        return token_data

    except (JWTError, ValueError):
        return None


# HTTP Bearer for regular API endpoints
security = HTTPBearer()


async def get_current_user(
    token: str = Depends(security)
) -> "User":
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Extract token string from HTTPAuthorizationCredentials
    token_str = token.credentials if hasattr(token, 'credentials') else str(token)

    # Verify token
    token_data = verify_token(token_str)
    if token_data is None:
        raise credentials_exception

    # Import here to avoid circular import
    from ..db.database import SessionLocal
    from ..models.user import User

    # Create database session
    db = SessionLocal()
    try:
        # Get user from database
        user = db.query(User).filter(User.id == token_data.user_id).first()
        if user is None:
            raise credentials_exception

        return user
    finally:
        db.close()


async def get_current_user_ws(token: str) -> "User":
    """Get current authenticated user from JWT token for WebSocket connections."""
    from ..db.database import SessionLocal

    db = SessionLocal()
    try:
        # Verify token
        token_data = verify_token(token)
        if token_data is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )

        # Import User model
        from ..models.user import User

        # Get user from database
        user = db.query(User).filter(User.id == token_data.user_id).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        return user

    finally:
        db.close()