# 🤖 Crypto Trader Pro - 고급 자동매매 시스템

## 📋 시스템 개요

### 목표
- 24시간 무인 자동매매 시스템 구축
- 실시간 시장 모니터링 및 AI 기반 거래 실행
- 포괄적인 리스크 관리 및 안전장치
- 사용자 친화적인 제어 인터페이스

### 핵심 특징
- **완전 자동화**: 사용자 개입 없이 24/7 거래 실행
- **AI 기반 신호**: 고도화된 AI 시스템으로 매매 신호 생성
- **다중 안전장치**: 리스크 관리, 긴급 중단, 손실 제한
- **실시간 모니터링**: 웹 대시보드를 통한 실시간 제어 및 모니터링
- **완전한 제어**: 언제든지 시작/중단/설정 변경 가능

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                   Crypto Trader Pro                        │
│                  Auto Trading System                       │
├─────────────────────────────────────────────────────────────┤
│  Web Dashboard (Streamlit)                                 │
│  ├── 제어 패널 (시작/중단/설정)                               │
│  ├── 실시간 모니터링                                        │
│  ├── 자동매매 로그                                          │
│  └── 성과 분석                                              │
├─────────────────────────────────────────────────────────────┤
│  Auto Trading Engine (Background Process)                  │
│  ├── Market Monitor (시장 데이터 수집)                       │
│  ├── AI Signal Generator (신호 생성)                        │
│  ├── Trade Executor (거래 실행)                             │
│  ├── Position Manager (포지션 관리)                         │
│  └── Risk Manager (리스크 관리)                             │
├─────────────────────────────────────────────────────────────┤
│  Database Layer                                            │
│  ├── Trading Config (설정)                                 │
│  ├── Trading Log (거래 기록)                               │
│  ├── Performance Data (성과 데이터)                        │
│  └── System Status (시스템 상태)                           │
├─────────────────────────────────────────────────────────────┤
│  External APIs                                             │
│  ├── Binance API (거래소)                                  │
│  ├── Market Data API (시장 데이터)                         │
│  └── Notification API (알림)                               │
└─────────────────────────────────────────────────────────────┘
```

## 📁 프로젝트 구조

```
crypto-trader-pro/
├── main_platform.py                    # 메인 대시보드
├── dashboard_components.py             # 대시보드 컴포넌트
├── trading_functions.py                # 거래 함수들
├── ui_helpers.py                       # UI 헬퍼
│
├── auto_trading/                       # 자동매매 시스템
│   ├── __init__.py
│   ├── engine.py                       # 메인 엔진
│   ├── market_monitor.py               # 시장 모니터링
│   ├── signal_generator.py             # AI 신호 생성기
│   ├── trade_executor.py               # 거래 실행기
│   ├── position_manager.py             # 포지션 관리자
│   ├── risk_manager.py                 # 리스크 관리자
│   └── config_manager.py               # 설정 관리자
│
├── auto_trading_dashboard/             # 자동매매 대시보드
│   ├── __init__.py
│   ├── control_panel.py                # 제어 패널
│   ├── monitoring.py                   # 실시간 모니터링
│   ├── logs_viewer.py                  # 로그 뷰어
│   └── performance_tracker.py          # 성과 추적
│
├── database/                           # 데이터베이스
│   ├── __init__.py
│   ├── auto_trading_db.py              # 자동매매 DB
│   └── models.py                       # 데이터 모델
│
├── utils/                              # 유틸리티
│   ├── __init__.py
│   ├── notifications.py               # 알림 시스템
│   ├── security.py                     # 보안 유틸
│   └── helpers.py                      # 헬퍼 함수들
│
└── config/                             # 설정 파일들
    ├── auto_trading_config.json        # 자동매매 설정
    ├── risk_config.json                # 리스크 관리 설정
    └── notification_config.json        # 알림 설정
```

## 🔧 핵심 컴포넌트

### 1. AutoTradingEngine
- 메인 자동매매 엔진
- 거래 루프 관리
- 시작/중단 제어
- 컴포넌트 간 조율

### 2. MarketMonitor
- 실시간 시장 데이터 수집
- 시장 이상 감지
- 가격 변동 모니터링

### 3. AISignalGenerator
- AI 기반 매매 신호 생성
- 신호 품질 검증
- 신호 기록 관리

### 4. TradeExecutor
- 실제 거래 실행
- 주문 관리
- 거래 확인

### 5. PositionManager
- 포지션 추적
- 포지션 청산
- 포지션 최적화

### 6. RiskManager
- 리스크 검증
- 포지션 크기 계산
- 긴급 중단 조건 확인

## 🛡️ 안전장치

### 다중 안전 시스템
- **일일 손실 제한**: 설정된 % 이상 손실 시 자동 중단
- **포지션 한도**: 동시 포지션 수 제한
- **API 연결 모니터링**: 연결 끊김 시 안전 모드
- **시장 변동성 검사**: 급격한 변동 시 거래 중단
- **계좌 잔고 확인**: 최소 잔고 이하 시 거래 중단

### 긴급 중단 시스템
- **수동 중단**: 사용자가 언제든지 중단 가능
- **자동 중단**: 위험 조건 감지 시 자동 중단
- **포지션 청산**: 선택적 포지션 청산 기능
- **알림 발송**: 중단 시 즉시 알림

## 📊 데이터베이스 설계

### auto_trading_config 테이블
```sql
CREATE TABLE auto_trading_config (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    is_enabled BOOLEAN DEFAULT FALSE,
    trading_mode TEXT DEFAULT 'CONSERVATIVE',
    max_daily_loss_pct REAL DEFAULT 3.0,
    max_positions INTEGER DEFAULT 5,
    trading_interval INTEGER DEFAULT 300,
    symbols TEXT, -- JSON array
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### auto_trading_logs 테이블
```sql
CREATE TABLE auto_trading_logs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    timestamp TIMESTAMP,
    log_level TEXT, -- INFO, WARNING, ERROR
    component TEXT, -- ENGINE, MONITOR, EXECUTOR
    message TEXT,
    data TEXT -- JSON data
);
```

### ai_signals_log 테이블
```sql
CREATE TABLE ai_signals_log (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    symbol TEXT,
    signal_type TEXT, -- BUY, SELL, HOLD
    confidence_score INTEGER,
    entry_price REAL,
    stop_loss REAL,
    take_profit REAL,
    executed BOOLEAN DEFAULT FALSE,
    execution_price REAL,
    created_at TIMESTAMP,
    executed_at TIMESTAMP
);
```

## 🔔 알림 시스템

### 알림 유형
- **거래 실행 알림**: 매매 체결 시
- **수익 목표 달성**: 목표 수익률 달성 시
- **손절 실행**: 손절매 체결 시
- **일일 손실 경고**: 손실 한도 근접 시
- **시스템 오류**: 시스템 오류 발생 시
- **긴급 중단**: 긴급 중단 실행 시

### 알림 채널
- **대시보드**: 실시간 알림 표시
- **이메일**: 중요 알림 이메일 발송
- **Discord**: 즉석 메시지 알림
- **Telegram**: 모바일 푸시 알림

## 🚀 구현 로드맵

### Phase 1: 기본 인프라 (1일)
- [x] 파일 구조 생성
- [ ] 데이터베이스 스키마 구축
- [ ] 기본 설정 시스템

### Phase 2: 핵심 엔진 (2-3일)
- [ ] AutoTradingEngine 구현
- [ ] MarketMonitor 구현
- [ ] AISignalGenerator 통합

### Phase 3: 안전 시스템 (1-2일)
- [ ] RiskManager 구현
- [ ] EmergencyStop 시스템
- [ ] 안전장치 테스트

### Phase 4: 제어 인터페이스 (1-2일)
- [ ] 제어 패널 구현
- [ ] 실시간 모니터링
- [ ] 로그 뷰어

### Phase 5: 고급 기능 (1-2일)
- [ ] 알림 시스템
- [ ] 성과 분석
- [ ] 백테스팅 기능

## ⚙️ 설정 예시

### auto_trading_config.json
```json
{
    "engine": {
        "trading_interval": 300,
        "max_concurrent_positions": 5,
        "enable_paper_trading": false
    },
    "risk_management": {
        "daily_loss_limit_pct": 3.0,
        "position_size_pct": 2.0,
        "stop_loss_pct": 1.0,
        "take_profit_pct": 2.0
    },
    "symbols": ["BTC/USDT", "ETH/USDT"],
    "notifications": {
        "enabled": true,
        "channels": ["dashboard", "email"],
        "trade_notifications": true,
        "error_notifications": true
    }
}
```

## 🎯 사용법

### 1. 자동매매 시작
1. 메인 대시보드에서 "자동매매" 탭 클릭
2. 설정 확인 및 조정
3. "자동매매 시작" 버튼 클릭
4. 실시간 모니터링 시작

### 2. 설정 관리
- **거래 모드**: Conservative, Balanced, Aggressive
- **리스크 설정**: 일일 손실 한도, 포지션 크기
- **알림 설정**: 알림 채널 및 유형 선택
- **거래 대상**: 거래할 암호화폐 선택

### 3. 모니터링
- **실시간 지표**: 활성 신호, 오늘 거래, 수익률
- **거래 로그**: 실시간 거래 기록 확인
- **성과 차트**: 수익률 및 거래 성과 시각화
- **시스템 상태**: 엔진 상태 및 연결 상태

### 4. 제어
- **일시 중단**: 거래 일시 중단 (포지션 유지)
- **완전 중단**: 모든 거래 중단 및 포지션 청산
- **긴급 중단**: 즉시 모든 거래 중단

## 🛠️ 내일 시작 가이드

### 시작 명령어
```
"고급 자동매매 시스템 구현을 시작하겠습니다. AUTO_TRADING_ARCHITECTURE.md 문서를 기반으로 Phase 1: 기본 인프라 구축부터 진행하겠습니다."
```

### 첫 번째 작업
1. `auto_trading/` 디렉토리 구조 생성
2. 데이터베이스 스키마 업데이트
3. 기본 설정 파일 생성
4. `AutoTradingEngine` 클래스 스켈레톤 구현

### 예상 소요 시간
- Phase 1 완료: 1일
- 전체 시스템 완료: 5-7일
- 테스트 및 최적화: 2-3일

---

**🚨 중요 주의사항**

이 시스템은 실제 자금으로 자동 거래를 수행합니다. 반드시:
1. 충분한 테스트 후 소액으로 시작
2. 리스크 설정을 보수적으로 설정
3. 정기적인 모니터링 수행
4. 시장 상황에 따른 설정 조정

자동매매는 높은 수익을 보장하지 않으며, 손실 위험이 항상 존재합니다.