"""FastAPI application entry point."""

import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .api.v1.api import api_router

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("fastapi")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Advanced cryptocurrency trading platform API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# 요청/응답 로깅 미들웨어
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """모든 HTTP 요청을 로깅합니다."""
    start_time = time.time()

    # 요청 정보 로깅
    print(f"\n🌐 HTTP 요청: {request.method} {request.url}")
    print(f"📍 엔드포인트: {request.url.path}")
    print(f"🔗 클라이언트: {request.client.host if request.client else 'Unknown'}")
    logger.info(f"REQUEST: {request.method} {request.url.path}")

    # 요청 처리
    response = await call_next(request)

    # 처리 시간 계산
    process_time = time.time() - start_time

    # 응답 정보 로깅
    print(f"✅ 응답 상태: {response.status_code}")
    print(f"⏱️  처리 시간: {process_time:.4f}초")
    logger.info(f"RESPONSE: {response.status_code} | Time: {process_time:.4f}s")
    print("=" * 50)

    return response

# Set CORS middleware - Specific origins for credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:8080"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "environment": settings.ENVIRONMENT}