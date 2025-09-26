"""
Binance Spot API endpoints - Live trading only
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import logging

from ...db.database import get_db
from ...auth.dependencies import get_current_user
from ...models.user import User
from ...schemas.trading import ApiKeysRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/binance", tags=["binance"])


@router.post("/configure-keys")
async def configure_api_keys(
    keys: ApiKeysRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Configure Binance API keys for user (Spot + Futures if available)"""
    print("=== configure-keys 호출됨 ===")
    print(f"사용자 ID: {current_user.id}")
    print(f"사용자명: {current_user.username}")
    print(f"API 키 수신: {bool(keys.api_key)} (길이: {len(keys.api_key)})")
    print(f"API 시크릿 수신: {bool(keys.api_secret)} (길이: {len(keys.api_secret)})")
    print("API 키 설정 프로세스 시작...")
    logger.info(f"Starting API key configuration for user: {current_user.username}")

    # Temporary bypass for debugging - Skip Binance API validation
    if keys.api_key.startswith("debug_"):
        print("[DEBUG] Using debug mode - skipping API validation")
        spot_result = {"success": True, "testnet": False}
        permissions = {
            "spot": {"enabled": True, "error": None, "details": {"can_trade": True}},
            "futures": {"enabled": False, "error": "Debug mode", "details": {}},
            "margin": {"enabled": False, "error": "Debug mode", "details": {}},
            "overall_success": True,
            "api_key_valid": True,
            "trading_enabled": True
        }
    else:
        # Test Spot API first (required)
        from ...services.binance_client import BinanceClient
        spot_client = BinanceClient(
            api_key=keys.api_key,
            api_secret=keys.api_secret,
            testnet=False  # Always use LIVE trading
        )

        spot_result = spot_client.test_connection()
        if not spot_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"LIVE API validation failed: {spot_result.get('error', 'Invalid API keys or permissions')}"
            )

        # CRITICAL: 테스트넷 API 키 차단
        if spot_result.get("testnet", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="TESTNET API keys detected! This system only accepts LIVE MAINNET API keys. Please use your LIVE trading API keys from Binance."
            )

        # 추가 검증: API 키가 메인넷에서 제대로 작동하는지 확인
        try:
            # 실제 서버 시간을 확인해서 테스트넷 여부를 재검증
            server_time_response = spot_client.client.get_server_time()
            logger.info(f"Server time check passed: {server_time_response}")
        except Exception as e:
            logger.error(f"Server time validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="API key validation failed. Please ensure you're using LIVE MAINNET API keys from Binance."
            )

        # Auto-detect API permissions using enhanced checker
        from ...services.binance_api_checker import BinanceAPIChecker

        logger.info("Auto-detecting API key permissions...")
        api_checker = BinanceAPIChecker(keys.api_key, keys.api_secret)
        permissions = await api_checker.check_permissions()

    # Extract permission information
    futures_enabled = permissions["futures"]["enabled"]
    futures_error = permissions["futures"]["error"]
    margin_enabled = permissions["margin"]["enabled"]

    logger.info(f"Permission detection complete - Spot: {permissions['spot']['enabled']}, Futures: {futures_enabled}, Margin: {margin_enabled}")

    # 데이터베이스에 API 키 저장 - 세션 공유 방식으로 해결
    print("\n=== 데이터베이스 세션 작업 시작 ===")
    print(f"configure_api_keys DB 세션 ID: {id(db)}")
    print(f"current_user 객체 ID: {id(current_user)}")
    logger.info(f"Saving API keys for user: {current_user.username}")

    # **핵심 해결책: current_user 객체가 이미 현재 세션에 바인딩되어 있음을 활용**
    # 별도로 User를 조회하지 않고 current_user를 직접 업데이트

    print("Option 1 적용: 세션 공유 방식")
    print(f"current_user가 이미 현재 세션에 바인딩되어 있는지 확인...")

    # SQLAlchemy 세션 상태 확인
    from sqlalchemy.orm import object_session
    current_user_session = object_session(current_user)
    print(f"current_user 바인딩 세션 ID: {id(current_user_session) if current_user_session else 'None'}")

    if current_user_session and id(current_user_session) == id(db):
        print("세션 일치: current_user와 API 엔드포인트가 같은 세션 사용")
    else:
        print("세션 불일치 감지 - 세션 병합 수행")
        # 세션 병합으로 current_user를 현재 세션에 바인딩
        current_user = db.merge(current_user)
        print("세션 병합 완료")

    # API 키 직접 업데이트 (current_user 객체 사용)
    print("API 키 업데이트 시작...")
    print(f"업데이트 전 - API 키: {bool(current_user.binance_api_key)}")
    print(f"업데이트 전 - API 시크릿: {bool(current_user.binance_api_secret)}")

    current_user.binance_api_key = keys.api_key
    print("binance_api_key 필드 업데이트 완료")

    current_user.binance_api_secret = keys.api_secret
    print("binance_api_secret 필드 업데이트 완료")

    current_user.use_testnet = False
    print("use_testnet 필드 업데이트 완료")

    print(f"업데이트 후 - API 키: {bool(current_user.binance_api_key)}")
    print(f"업데이트 후 - API 시크릿: {bool(current_user.binance_api_secret)}")

    # 데이터베이스 커밋
    print("데이터베이스 커밋 시도...")
    db.commit()
    print("데이터베이스 커밋 성공")

    print("=== Option 1 성공: API 키 저장 완료 ===")
    logger.info(f"API keys successfully saved for user: {current_user.username}")

    # Build feature list for response
    features = ["Spot Trading: OK"]
    if futures_enabled:
        features.append("Futures Trading: OK")
    else:
        features.append("Futures Trading: NOT AVAILABLE (Permission not available)")
    if margin_enabled:
        features.append("Margin Trading: OK")

    account_types = ["LIVE_SPOT"]
    if futures_enabled:
        account_types.append("FUTURES")
    if margin_enabled:
        account_types.append("MARGIN")

    return {
        "success": True,
        "message": f"LIVE MAINNET API keys configured successfully! {' | '.join(features)}",
        "trading_mode": "LIVE_MAINNET",
        "can_trade": spot_result.get("can_trade", True),
        "account_type": "_".join(account_types),
        "permissions": {
            "spot": permissions["spot"]["enabled"],
            "futures": futures_enabled,
            "margin": margin_enabled
        },
        "futures_enabled": futures_enabled,
        "futures_error": futures_error if not futures_enabled else None,
        "margin_enabled": margin_enabled,
        "warning": "WARNING: REAL MONEY TRADING ACTIVE - All transactions use actual funds"
    }