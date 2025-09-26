# React + FastAPI 암호화폐 거래 플랫폼 아키텍처

## 전략적 접근

### 기존 시스템 문제점 분석
- **복잡한 Streamlit 구조**: 다중 포트, 세션 관리 복잡성
- **오류 누적**: 기존 코드의 기술적 부채
- **확장성 한계**: Streamlit의 구조적 제약

### 새로운 접근 방향
- **Clean Slate**: 처음부터 모던한 구조로 재구축
- **Industry Standards**: 검증된 패턴과 도구 사용
- **Progressive Enhancement**: 기본 기능부터 점진적 확장

---

## 시스템 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────┐
│                    Vultr Server (nosignup.kr)              │
├─────────────────────────────────────────────────────────────┤
│  Nginx Reverse Proxy (Port 80/443)                         │
│  ├── Static Files → React SPA                              │
│  ├── /api/* → FastAPI Backend                              │
│  └── /ws/* → WebSocket Connections                         │
├─────────────────────────────────────────────────────────────┤
│  React Frontend (Port 3000)                                │
│  ├── Modern Trading UI                                     │
│  ├── Real-time Charts                                      │
│  ├── Portfolio Management                                  │
│  └── User Authentication                                   │
├─────────────────────────────────────────────────────────────┤
│  FastAPI Backend (Port 8000)                               │
│  ├── REST API Endpoints                                    │
│  ├── WebSocket Handlers                                    │
│  ├── Authentication & Authorization                        │
│  └── Business Logic                                        │
├─────────────────────────────────────────────────────────────┤
│  Trading Engine (Background Service)                       │
│  ├── Market Data Collection                                │
│  ├── Strategy Execution                                    │
│  ├── Risk Management                                       │
│  └── Order Management                                      │
├─────────────────────────────────────────────────────────────┤
│  Data Layer                                                │
│  ├── PostgreSQL (Production)                               │
│  ├── Redis (Caching & Sessions)                            │
│  └── File Storage (Logs & Backups)                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Frontend: React 시스템 설계

### 기술 스택 (Modern & Popular)
```json
{
  "framework": "React 18 + TypeScript",
  "build_tool": "Vite",
  "ui_library": "Ant Design (antd)",
  "state_management": "Zustand",
  "data_fetching": "TanStack Query",
  "routing": "React Router v6",
  "charts": "TradingView Charting Library",
  "styling": "Styled Components + Ant Design",
  "icons": "Ant Design Icons + Lucide React"
}
```

### 프로젝트 구조
```
frontend/
├── public/
│   ├── index.html
│   ├── favicon.ico
│   └── manifest.json
├── src/
│   ├── components/           # 재사용 가능한 컴포넌트
│   │   ├── layout/          
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Layout.tsx
│   │   ├── trading/
│   │   │   ├── OrderForm.tsx
│   │   │   ├── OrderBook.tsx
│   │   │   ├── PositionList.tsx
│   │   │   └── TradeHistory.tsx
│   │   ├── charts/
│   │   │   ├── TradingViewChart.tsx
│   │   │   ├── PortfolioChart.tsx
│   │   │   └── MarketOverview.tsx
│   │   └── common/
│   │       ├── LoadingSpinner.tsx
│   │       ├── ErrorBoundary.tsx
│   │       └── ConfirmModal.tsx
│   ├── pages/               # 페이지 컴포넌트
│   │   ├── auth/
│   │   │   ├── LoginPage.tsx
│   │   │   └── RegisterPage.tsx
│   │   ├── DashboardPage.tsx
│   │   ├── TradingPage.tsx
│   │   ├── PortfolioPage.tsx
│   │   ├── MarketPage.tsx
│   │   └── SettingsPage.tsx
│   ├── hooks/               # Custom Hooks
│   │   ├── useAuth.ts
│   │   ├── useWebSocket.ts
│   │   ├── useMarketData.ts
│   │   └── useTradingActions.ts
│   ├── services/            # API 서비스
│   │   ├── api.ts          # Axios 설정
│   │   ├── auth.service.ts
│   │   ├── trading.service.ts
│   │   ├── market.service.ts
│   │   └── websocket.service.ts
│   ├── stores/              # Zustand 스토어
│   │   ├── authStore.ts
│   │   ├── marketStore.ts
│   │   ├── tradingStore.ts
│   │   └── uiStore.ts
│   ├── types/               # TypeScript 타입
│   │   ├── auth.types.ts
│   │   ├── trading.types.ts
│   │   ├── market.types.ts
│   │   └── api.types.ts
│   ├── utils/               # 유틸리티
│   │   ├── formatters.ts    # 숫자, 날짜 포맷팅
│   │   ├── validators.ts    # 입력값 검증
│   │   ├── constants.ts     # 상수 정의
│   │   └── helpers.ts       # 헬퍼 함수
│   ├── styles/              # 글로벌 스타일
│   │   ├── globals.css
│   │   └── antd-theme.ts
│   ├── App.tsx
│   ├── main.tsx
│   └── vite-env.d.ts
├── package.json
├── vite.config.ts
├── tsconfig.json
└── tailwind.config.js
```

### UI 레이아웃 설계 (대중적 패턴)
```typescript
// 표준적인 거래 플랫폼 레이아웃
interface MainLayout {
  header: {
    logo: string
    navigation: NavItem[]
    userMenu: UserMenuProps
    notifications: NotificationProps
  }
  sidebar: {
    tradingPairs: TradingPair[]
    watchlist: Watchlist
    quickActions: QuickAction[]
  }
  main: {
    chart: TradingViewChart        // 메인 차트 (60% 너비)
    orderForm: OrderForm           // 주문 폼 (40% 너비)
    orderbook: OrderBook           // 호가창
    trades: RecentTrades           // 최근 거래
    positions: UserPositions       // 내 포지션
    history: TradeHistory         // 거래 내역
  }
}
```

---

## Backend: FastAPI 시스템 설계

### 기술 스택
```python
# 메인 프레임워크
fastapi = "^0.104.1"
uvicorn = "^0.24.0"

# 데이터베이스
sqlalchemy = "^2.0.23"
asyncpg = "^0.29.0"        # PostgreSQL 비동기 드라이버
alembic = "^1.13.0"        # DB 마이그레이션

# 인증 & 보안
python-jose = "^3.3.0"    # JWT
passlib = "^1.7.4"        # 패스워드 해싱
python-multipart = "^0.0.6"
cryptography = "^41.0.7"

# 캐싱 & 세션
redis = "^5.0.1"
python-redis = "^5.0.1"

# 외부 API
httpx = "^0.25.2"          # 비동기 HTTP 클라이언트
websockets = "^12.0"
ccxt = "^4.1.49"           # 거래소 연동

# 유틸리티
pydantic = "^2.5.0"
python-dotenv = "^1.0.0"
celery = "^5.3.4"          # 백그라운드 작업
```

### 프로젝트 구조
```
backend/
├── app/
│   ├── api/                    # API 라우터
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py        # 인증 엔드포인트
│   │   │   ├── users.py       # 사용자 관리
│   │   │   ├── trading.py     # 거래 관련
│   │   │   ├── market.py      # 시장 데이터
│   │   │   ├── portfolio.py   # 포트폴리오
│   │   │   └── admin.py       # 관리자 기능
│   │   └── deps.py            # 의존성 주입
│   ├── core/                  # 핵심 설정
│   │   ├── __init__.py
│   │   ├── config.py          # 환경 설정
│   │   ├── security.py        # JWT, 암호화
│   │   ├── database.py        # DB 연결 설정
│   │   └── exceptions.py      # 커스텀 예외
│   ├── crud/                  # 데이터베이스 작업
│   │   ├── __init__.py
│   │   ├── base.py           # 기본 CRUD 클래스
│   │   ├── user.py
│   │   ├── trading.py
│   │   └── market.py
│   ├── models/                # SQLAlchemy 모델
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── trading.py
│   │   ├── market.py
│   │   └── base.py
│   ├── schemas/               # Pydantic 스키마
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── trading.py
│   │   ├── market.py
│   │   └── common.py
│   ├── services/              # 비즈니스 로직
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── trading_service.py
│   │   ├── market_service.py
│   │   ├── portfolio_service.py
│   │   └── notification_service.py
│   ├── utils/                 # 유틸리티
│   │   ├── __init__.py
│   │   ├── security.py       # 보안 유틸리티
│   │   ├── validators.py     # 검증 함수
│   │   ├── formatters.py     # 데이터 포맷팅
│   │   └── constants.py      # 상수
│   ├── websocket/             # WebSocket 핸들러
│   │   ├── __init__.py
│   │   ├── manager.py        # 연결 관리
│   │   ├── handlers.py       # 메시지 핸들러
│   │   └── events.py         # 이벤트 타입
│   ├── main.py               # FastAPI 앱
│   └── __init__.py
├── alembic/                  # DB 마이그레이션
│   ├── versions/
│   ├── env.py
│   └── alembic.ini
├── trading_engine/           # 백그라운드 거래 엔진
│   ├── __init__.py
│   ├── main.py              # 메인 거래 루프
│   ├── strategies/          # 거래 전략
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── rsi_strategy.py
│   ├── data/                # 데이터 수집
│   │   ├── __init__.py
│   │   ├── collectors.py
│   │   └── processors.py
│   ├── risk/                # 리스크 관리
│   │   ├── __init__.py
│   │   └── manager.py
│   └── execution/           # 주문 실행
│       ├── __init__.py
│       └── engine.py
├── tests/                   # 테스트
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

### API 엔드포인트 설계
```python
# 인증 API
POST   /api/v1/auth/login          # 로그인
POST   /api/v1/auth/register       # 회원가입
POST   /api/v1/auth/refresh        # 토큰 갱신
DELETE /api/v1/auth/logout         # 로그아웃

# 사용자 API  
GET    /api/v1/users/me            # 내 프로필
PUT    /api/v1/users/me            # 프로필 수정
POST   /api/v1/users/me/api-keys   # API 키 등록
GET    /api/v1/users/me/api-keys   # API 키 조회

# 시장 데이터 API
GET    /api/v1/market/symbols      # 거래쌍 목록
GET    /api/v1/market/tickers      # 현재 가격
GET    /api/v1/market/orderbook/{symbol}  # 호가창
GET    /api/v1/market/trades/{symbol}     # 최근 거래
GET    /api/v1/market/klines/{symbol}     # 캔들 데이터

# 거래 API
POST   /api/v1/trading/orders      # 주문 생성
GET    /api/v1/trading/orders      # 주문 조회
DELETE /api/v1/trading/orders/{id} # 주문 취소
GET    /api/v1/trading/positions   # 포지션 조회
GET    /api/v1/trading/balance     # 잔고 조회

# 포트폴리오 API
GET    /api/v1/portfolio/summary   # 포트폴리오 요약
GET    /api/v1/portfolio/history   # 거래 내역
GET    /api/v1/portfolio/performance # 성과 분석

# WebSocket 엔드포인트
WS     /ws/market/{symbol}         # 시장 데이터 스트림
WS     /ws/trading                 # 거래 업데이트
WS     /ws/notifications           # 알림
```

---

## 데이터베이스 설계

### 스키마 설계 (Simple & Clean)
```sql
-- 사용자 테이블
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API 키 테이블 (암호화 저장)
CREATE TABLE user_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    exchange VARCHAR(50) NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    api_secret_encrypted TEXT NOT NULL,
    is_testnet BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 거래 주문 테이블
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL, -- 'buy' or 'sell'
    type VARCHAR(20) NOT NULL, -- 'market', 'limit', 'stop'
    quantity DECIMAL(20,8) NOT NULL,
    price DECIMAL(20,8),
    status VARCHAR(20) NOT NULL, -- 'pending', 'filled', 'cancelled'
    exchange_order_id VARCHAR(100),
    filled_quantity DECIMAL(20,8) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 거래 내역 테이블
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    order_id UUID REFERENCES orders(id),
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity DECIMAL(20,8) NOT NULL,
    price DECIMAL(20,8) NOT NULL,
    fee DECIMAL(20,8) DEFAULT 0,
    fee_currency VARCHAR(10),
    executed_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 포지션 테이블
CREATE TABLE positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL, -- 'long' or 'short'
    size DECIMAL(20,8) NOT NULL,
    entry_price DECIMAL(20,8) NOT NULL,
    mark_price DECIMAL(20,8),
    unrealized_pnl DECIMAL(20,8) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, exchange, symbol, side)
);

-- 사용자 설정 테이블
CREATE TABLE user_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    trading_enabled BOOLEAN DEFAULT false,
    max_position_size DECIMAL(20,8) DEFAULT 1000,
    risk_per_trade DECIMAL(5,2) DEFAULT 2.0,
    daily_loss_limit DECIMAL(5,2) DEFAULT 5.0,
    notification_preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);
```

### 인덱스 최적화
```sql
-- 성능 최적화를 위한 인덱스
CREATE INDEX idx_orders_user_status ON orders(user_id, status);
CREATE INDEX idx_trades_user_symbol ON trades(user_id, symbol);
CREATE INDEX idx_trades_executed_at ON trades(executed_at DESC);
CREATE INDEX idx_positions_user_exchange ON positions(user_id, exchange);
```

---

## 거래 엔진 설계

### 아키텍처 (Celery 기반)
```python
# trading_engine/main.py
from celery import Celery
from .strategies import RSIStrategy, MACDStrategy
from .data.collectors import BinanceDataCollector
from .execution.engine import OrderExecutionEngine

app = Celery('trading_engine')

@app.task
def collect_market_data():
    """시장 데이터 수집 작업"""
    collector = BinanceDataCollector()
    return collector.collect_all_symbols()

@app.task
def execute_strategy(user_id: str, strategy_name: str):
    """전략 실행 작업"""
    strategy = get_strategy(strategy_name)
    signals = strategy.generate_signals(user_id)
    
    if signals:
        engine = OrderExecutionEngine(user_id)
        return engine.execute_signals(signals)

@app.task
def monitor_positions(user_id: str):
    """포지션 모니터링"""
    # 리스크 관리, 손절/익절 체크
    pass
```

### 전략 시스템 (플러그인 방식)
```python
# trading_engine/strategies/base.py
from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    def __init__(self, name: str, parameters: dict):
        self.name = name
        self.parameters = parameters
    
    @abstractmethod
    def generate_signals(self, market_data: dict) -> list:
        """거래 신호 생성"""
        pass
    
    @abstractmethod
    def validate_signal(self, signal: dict) -> bool:
        """신호 유효성 검증"""
        pass

# trading_engine/strategies/rsi_strategy.py
class RSIStrategy(BaseStrategy):
    def generate_signals(self, market_data: dict) -> list:
        # RSI 기반 신호 생성 로직
        signals = []
        
        for symbol, data in market_data.items():
            rsi = calculate_rsi(data['prices'])
            
            if rsi < 30:  # 과매도
                signals.append({
                    'symbol': symbol,
                    'action': 'buy',
                    'quantity': self.calculate_position_size(),
                    'confidence': (30 - rsi) / 30
                })
            elif rsi > 70:  # 과매수
                signals.append({
                    'symbol': symbol,
                    'action': 'sell',
                    'quantity': self.calculate_position_size(),
                    'confidence': (rsi - 70) / 30
                })
        
        return signals
```

---

## 배포 및 인프라

### Docker 구성
```yaml
# docker-compose.yml
version: '3.8'

services:
  # PostgreSQL
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: crypto_trading
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  # Redis
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # FastAPI Backend
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/crypto_trading
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis

  # React Frontend (Development)
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules

  # Celery Worker
  celery-worker:
    build: ./backend
    command: celery -A trading_engine.main worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/crypto_trading
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis

  # Celery Beat (Scheduler)
  celery-beat:
    build: ./backend
    command: celery -A trading_engine.main beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/crypto_trading
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis

volumes:
  postgres_data:
```

### PM2 Ecosystem (Production)
```javascript
// ecosystem.config.js
module.exports = {
  apps: [
    {
      name: 'crypto-api',
      script: 'uvicorn',
      args: 'app.main:app --host 0.0.0.0 --port 8000 --workers 4',
      cwd: './backend',
      instances: 1,
      autorestart: true,
      watch: false,
      env: {
        NODE_ENV: 'production',
        DATABASE_URL: 'postgresql://user:pass@localhost:5432/crypto_trading',
        REDIS_URL: 'redis://localhost:6379'
      }
    },
    {
      name: 'celery-worker',
      script: 'celery',
      args: '-A trading_engine.main worker --loglevel=info --concurrency=4',
      cwd: './backend',
      instances: 1,
      autorestart: true
    },
    {
      name: 'celery-beat',
      script: 'celery',
      args: '-A trading_engine.main beat --loglevel=info',
      cwd: './backend',
      instances: 1,
      autorestart: true
    }
  ]
};
```

### Nginx 설정
```nginx
# /etc/nginx/sites-available/crypto-trading
server {
    listen 80;
    server_name nosignup.kr;
    
    # React 정적 파일
    location / {
        root /opt/crypto-trader/frontend/dist;
        try_files $uri $uri/ /index.html;
        
        # 캐싱 설정
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # API 프록시
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # CORS 헤더
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Accept,Authorization,Cache-Control,Content-Type,DNT,If-Modified-Since,Keep-Alive,Origin,User-Agent,X-Requested-With' always;
    }
    
    # WebSocket 프록시
    location /ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Gzip 압축
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
}
```

---

## 개발 단계별 계획

### Phase 1: 기본 인프라 구축 (1주)
**목표**: 기본적인 CRUD API와 인증 시스템

```
□ FastAPI 프로젝트 초기화
□ PostgreSQL + Redis 연동
□ JWT 기반 인증 시스템
□ 기본 사용자 관리 API
□ 데이터베이스 스키마 생성
```

### Phase 2: React 프론트엔드 구축 (1주)
**목표**: 기본적인 UI와 인증 플로우

```
□ React + TypeScript 프로젝트 초기화
□ Ant Design UI 컴포넌트 설정
□ 인증 (로그인/회원가입) 페이지
□ 기본 레이아웃 및 네비게이션
□ API 연동 및 상태 관리
```

### Phase 3: 거래 기능 구현 (1주)
**목표**: 기본적인 거래 기능과 포트폴리오

```
□ 거래소 API 연동 (Binance)
□ 시장 데이터 API
□ 기본 주문 기능 (시장가/지정가)
□ 포트폴리오 조회
□ 실시간 데이터 (WebSocket)
```

### Phase 4: 고급 기능 확장 (2주)
**목표**: 차트, 전략, 자동 거래

```
□ TradingView 차트 통합
□ 기본 거래 전략 (RSI)
□ 백그라운드 거래 엔진
□ 리스크 관리 시스템
□ 알림 시스템
```

### Phase 5: 배포 및 최적화 (1주)
**목표**: 프로덕션 배포 및 성능 최적화

```
□ Vultr 서버 환경 설정
□ Nginx 설정 및 SSL
□ PM2 배포 설정
□ 모니터링 및 로깅
□ 성능 최적화
```

---

## Claude Code 구현 지시사항

### Step 1: FastAPI 백엔드 초기화
```
완전히 새로운 FastAPI 프로젝트를 생성해주세요.

요구사항:
- 현대적인 FastAPI 구조 (v0.104+)
- PostgreSQL + SQLAlchemy 2.0 비동기
- JWT 인증 시스템
- Pydantic v2 스키마
- 프로젝트 구조는 위 아키텍처 문서 참조

기본 엔드포인트:
- 인증 API (로그인, 회원가입, 토큰 갱신)
- 사용자 API (프로필 관리)
- 헬스체크 API

데이터베이스:
- 위에서 정의한 기본 스키마 구현
- Alembic 마이그레이션 설정
```

### Step 2: React 프론트엔드 초기화
```
현대적인 React 프로젝트를 생성해주세요.

요구사항:
- Vite + React 18 + TypeScript
- Ant Design (antd) UI 라이브러리
- Zustand 상태 관리
- TanStack Query (React Query)
- React Router v6

기본 구조:
- 로그인/회원가입 페이지
- 메인 레이아웃 (헤더, 사이드바)
- 대시보드 페이지 (기본)
- API 서비스 설정
- 인증 상태 관리
```

### Step 3: 기본 연동 및 배포 설정
```
백엔드와 프론트엔드를 연동하고 기본 배포 설정을 구성해주세요.

요구사항:
- CORS 설정
- API 연동 테스트
- Docker Compose 개발 환경
- 기본 Nginx 설정
- PM2 배포 설정 (Vultr 서버용)

검증사항:
- 로그인/회원가입 전체 플로우 작동
- 인증 토큰 관리 정상 작동
- 기본 대시보드 표시
```

이 아키텍처는 업계 표준을 따르는 확장 가능한 구조로, 점진적으로 기능을 추가할 수 있도록 설계되었습니다.