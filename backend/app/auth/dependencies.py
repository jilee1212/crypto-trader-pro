"""FastAPI dependencies for authentication."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from uuid import UUID

from ..db.database import get_db
from ..models.user import User
from ..schemas.auth import TokenData
from .jwt_handler import verify_token

# Security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    print("\n🔐 get_current_user() 호출됨")
    print(f"🗄️ DB 세션 ID: {id(db)}")
    print(f"🔑 JWT 토큰 수신됨 (길이: {len(credentials.credentials)})")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Verify token
    print("🔍 JWT 토큰 검증 중...")
    token_data: TokenData = verify_token(credentials.credentials)
    if token_data is None or token_data.user_id is None:
        print("❌ JWT 토큰 검증 실패")
        raise credentials_exception

    print(f"✅ JWT 토큰 검증 성공 - user_id: {token_data.user_id}")

    # Get user from database
    print("📋 데이터베이스에서 User 조회 중...")
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        print(f"❌ User 조회 실패 - user_id: {token_data.user_id}")
        raise credentials_exception

    print(f"✅ User 조회 성공 - username: {user.username}, user_id: {user.id}")
    print(f"👤 User 객체 ID: {id(user)}")
    print(f"🏷️ User 객체가 바인딩된 세션 ID: {id(db)}")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user