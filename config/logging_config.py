"""
로깅 설정 모듈
암호화폐 트레이딩 봇의 모든 로그 설정을 관리합니다.
"""

import os
import sys
from pathlib import Path
from loguru import logger

# 프로젝트 루트 디렉토리 설정
PROJECT_ROOT = Path(__file__).parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"

# 로그 디렉토리 생성
LOGS_DIR.mkdir(exist_ok=True)

def setup_logging():
    """
    로깅 시스템을 초기화합니다.

    로그 레벨:
    - DEBUG: 개발 및 디버깅용 상세 정보
    - INFO: 일반적인 트레이딩 정보
    - WARNING: 주의가 필요한 상황
    - ERROR: 오류 발생 시
    - CRITICAL: 시스템 중단이 필요한 심각한 오류
    """

    # 기본 핸들러 제거
    logger.remove()

    # 콘솔 출력 설정 (INFO 레벨 이상)
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        level="INFO",
        colorize=True
    )

    # 전체 로그 파일 (DEBUG 레벨 이상)
    logger.add(
        LOGS_DIR / "crypto_trader.log",
        rotation="1 day",
        retention="30 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level="DEBUG"
    )

    # 트레이딩 전용 로그 파일 (INFO 레벨 이상)
    logger.add(
        LOGS_DIR / "trading.log",
        rotation="1 day",
        retention="90 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="INFO",
        filter=lambda record: "trading" in record["name"].lower()
    )

    # 에러 전용 로그 파일 (ERROR 레벨 이상)
    logger.add(
        LOGS_DIR / "errors.log",
        rotation="1 week",
        retention="1 year",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level="ERROR"
    )

    # 백테스팅 결과 로그 파일
    logger.add(
        LOGS_DIR / "backtesting.log",
        rotation="10 MB",
        retention="6 months",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {message}",
        filter=lambda record: "backtest" in record["name"].lower()
    )

    logger.info("로깅 시스템이 초기화되었습니다.")

def get_logger(name: str):
    """
    모듈별 로거를 반환합니다.

    Args:
        name (str): 로거 이름 (보통 __name__ 사용)

    Returns:
        loguru.Logger: 설정된 로거 인스턴스
    """
    return logger.bind(name=name)

# 특별한 로거들
def get_trading_logger():
    """트레이딩 전용 로거"""
    return logger.bind(name="trading")

def get_backtest_logger():
    """백테스팅 전용 로거"""
    return logger.bind(name="backtest")

def get_risk_logger():
    """리스크 관리 전용 로거"""
    return logger.bind(name="risk_management")

def get_arbitrage_logger():
    """차익거래 전용 로거"""
    return logger.bind(name="arbitrage")

# 로그 포맷 템플릿
LOG_TEMPLATES = {
    "trade_execution": "🔄 TRADE | {symbol} | {side} | Amount: {amount} | Price: {price} | {message}",
    "signal_generated": "📊 SIGNAL | {symbol} | {signal_type} | RSI: {rsi} | {message}",
    "risk_alert": "⚠️ RISK | {symbol} | {risk_type} | Current Loss: {loss_percent}% | {message}",
    "arbitrage_opportunity": "💰 ARBITRAGE | {symbol} | Profit: {profit_percent}% | {exchange1} vs {exchange2}",
    "system_status": "🔧 SYSTEM | {component} | Status: {status} | {message}"
}

def log_trade_execution(symbol: str, side: str, amount: float, price: float, message: str = ""):
    """거래 실행 로그"""
    trading_logger = get_trading_logger()
    trading_logger.info(
        LOG_TEMPLATES["trade_execution"].format(
            symbol=symbol, side=side, amount=amount, price=price, message=message
        )
    )

def log_signal_generated(symbol: str, signal_type: str, rsi: float, message: str = ""):
    """시그널 생성 로그"""
    trading_logger = get_trading_logger()
    trading_logger.info(
        LOG_TEMPLATES["signal_generated"].format(
            symbol=symbol, signal_type=signal_type, rsi=rsi, message=message
        )
    )

def log_risk_alert(symbol: str, risk_type: str, loss_percent: float, message: str = ""):
    """리스크 알림 로그"""
    risk_logger = get_risk_logger()
    risk_logger.warning(
        LOG_TEMPLATES["risk_alert"].format(
            symbol=symbol, risk_type=risk_type, loss_percent=loss_percent, message=message
        )
    )

def log_arbitrage_opportunity(symbol: str, profit_percent: float, exchange1: str, exchange2: str):
    """차익거래 기회 로그"""
    arbitrage_logger = get_arbitrage_logger()
    arbitrage_logger.info(
        LOG_TEMPLATES["arbitrage_opportunity"].format(
            symbol=symbol, profit_percent=profit_percent, exchange1=exchange1, exchange2=exchange2
        )
    )

def log_system_status(component: str, status: str, message: str = ""):
    """시스템 상태 로그"""
    logger.info(
        LOG_TEMPLATES["system_status"].format(
            component=component, status=status, message=message
        )
    )

if __name__ == "__main__":
    # 테스트 코드
    setup_logging()

    # 다양한 로그 레벨 테스트
    logger.debug("디버그 메시지 테스트")
    logger.info("정보 메시지 테스트")
    logger.warning("경고 메시지 테스트")
    logger.error("에러 메시지 테스트")

    # 특별한 로거 테스트
    log_trade_execution("BTC/USDT", "BUY", 0.001, 45000, "RSI 기반 매수 신호")
    log_signal_generated("ETH/USDT", "SELL", 75.5, "과매수 구간 진입")
    log_risk_alert("BNB/USDT", "STOP_LOSS", 1.2, "손절매 실행")
    log_arbitrage_opportunity("BTC/USDT", 0.8, "binance", "coinbase")
    log_system_status("데이터 수집", "정상", "모든 거래소 연결 상태 양호")