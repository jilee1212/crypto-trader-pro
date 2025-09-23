# 🚀 Crypto Trader Pro - Advanced Multi-Dashboard Trading Platform

Professional multi-port trading platform with seamless user flow, database-based session management, and real Binance mainnet integration.

**⚠️ 면책조항: 이 소프트웨어는 교육 및 연구 목적으로만 제작되었습니다. 암호화폐 거래는 상당한 손실 위험을 수반합니다. 실거래 전 반드시 테스트에서 충분히 검증하세요.**

## 🎯 시스템 현황 (2025년 9월 23일)

### ✅ Phase 7.1-7.3 완료: AI 리스크 관리 시스템
- **정밀 포지션 계산**: 현물/선물 자동 선택, 레버리지 최적화
- **지정가 주문 시스템**: OCO 주문, 손절/익절 자동 설정
- **AI 신호 통합**: 신뢰도 기반 자동 실행 시스템
- **보호시스템**: 거래 차단 이슈로 일시 비활성화

### ✅ Phase 6.1-6.5 완료: 유동적 주문 한도 시스템
- **동적 최소 금액 조회**: 거래소별 실시간 최소 금액 캐싱
- **사용자 맞춤 한도**: 설정 가능한 주문 상한/하한
- **스마트 주문 제안**: 리스크 기반 최적 금액 추천
- **다단계 검증**: 주문 실행 전 종합 유효성 검사

### ✅ 이전 단계 (안정적 운영 중)
- **단일 포트 통합**: main_app.py 기반 통합 대시보드
- **세션 관리**: 데이터베이스 기반 사용자 인증
- **실거래 시스템**: 바이낸스 메인넷 USDT-M 선물

## 🔧 최신 기술 스택 (2025년 9월 업데이트)

### AI 리스크 관리 시스템
- **RiskCalculator**: 정밀한 포지션 사이징 엔진
- **OrderManager**: 지정가 + OCO 주문 관리 시스템
- **AISignalManager**: 신뢰도 기반 자동 실행
- **Dynamic Order Limits**: 거래소별 실시간 최소 금액 조회

### 핵심 플랫폼
- **Unified Dashboard**: 단일 포트 통합 인터페이스 (main_app.py)
- **Database Session Management**: SQLAlchemy 2.0 + 안전한 사용자 인증
- **Real Trading Integration**: Binance USDT-M Futures mainnet
- **Advanced Risk Controls**: 수학적 정밀성 + 안전성 보장

### 거래 시스템
- **BinanceMainnetConnector**: Real USDT-M Futures trading
- **CCXT 4.5+**: Professional exchange API integration
- **Smart Position Sizing**: 레버리지 자동 최적화
- **Encrypted API Storage**: Database-based secure credential management

### UI/UX 시스템
- **Streamlit Multi-App**: Responsive web dashboard
- **Session Restoration**: Automatic login state persistence
- **Real-time Updates**: Live price feeds, account balance monitoring
- **Professional Interface**: Trading-focused UI design

## 🎯 시스템 구성

### 🔐 Multi-Dashboard User Flow (NEW - Phase 6)
**3-Port Seamless Architecture**

#### 🔹 Login Dashboard (Port 8501)
**URL**: http://localhost:8501
**파일**: `login_app.py`
**기능**:
- 사용자 로그인/회원가입 시스템
- bcrypt 패스워드 해싱
- Database session 생성
- Safe Dashboard로 자동 리디렉션

#### 🔹 Safety Test Dashboard (Port 8506)
**URL**: http://localhost:8506
**파일**: `safe_mainnet_dashboard.py`
**기능**:
- **Real Binance Mainnet API 테스트**
- XRP/USDT Long/Short 실거래 검증
- API 키 검증 및 암호화 저장
- Emergency stop 및 안전 기능
- Main Dashboard 자동 이동

#### 🔹 Main Trading Dashboard (Port 8507)
**URL**: http://localhost:8507
**파일**: `main_dashboard.py`
**기능**:
- **Full Mainnet Trading Interface**
- 저장된 API 키 자동 로드
- 실시간 계정 정보 및 포지션 관리
- 빠른 거래 인터페이스 (Long/Short)
- 미체결 주문 관리

### 💾 Database Architecture
**Session Management System**
- **UserSession Model**: 포트간 세션 공유
- **API Key Storage**: 암호화된 자격증명 관리
- **User Management**: 계정 생성/인증 시스템
- **Cross-Port State**: URL 파라미터 + DB 복원

### 🔒 Security Features
- **Encrypted API Keys**: Fernet 암호화 저장
- **Session Timeout**: 1시간 자동 만료
- **Emergency Controls**: 즉시 거래 중단 기능
- **Safety Limits**: 최대 주문 금액, 포지션 크기 제한

## 🚀 빠른 시작

### 1. 시스템 요구사항
```bash
# Python 패키지 설치
pip install streamlit pandas plotly ccxt bcrypt sqlalchemy cryptography python-binance
```

### 2. 데이터베이스 초기화
```bash
# 테스트 계정 생성 (선택사항)
python -c "
from database.database_manager import get_db_manager
from database.models import User
import bcrypt

db_manager = get_db_manager()
with db_manager.get_session() as session:
    hashed_password = bcrypt.hashpw('testpass'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    new_user = User(username='testuser', password_hash=hashed_password, email='test@example.com')
    session.add(new_user)
    session.commit()
    print('Test user created: testuser/testpass')
"
```

### 3. 시스템 실행
```bash
# 터미널 1: Login Dashboard
streamlit run login_app.py --server.port 8501

# 터미널 2: Safety Test Dashboard
streamlit run safe_mainnet_dashboard.py --server.port 8506

# 터미널 3: Main Trading Dashboard
streamlit run main_dashboard.py --server.port 8507
```

### 4. 사용자 플로우
1. **http://localhost:8501** → 로그인 또는 회원가입
2. **자동 이동** → Safety Test에서 API 키 입력 및 실거래 검증
3. **자동 이동** → Main Dashboard에서 실제 거래 시작

## 💰 Trading Features

### Real Mainnet Trading
- **Binance USDT-M Futures**: 실제 메인넷 거래
- **검증된 거래쌍**: XRP/USDT, BTC/USDT, ETH/USDT
- **레버리지 지원**: 1x-5x 레버리지 거래
- **양방향 거래**: Long/Short 포지션 지원

### Safety Features
- **Emergency Stop**: 모든 거래 즉시 중단
- **Position Limits**: 최대 포지션 크기 제한
- **Order Limits**: 주문당 최대 금액 제한
- **Observation Mode**: 실거래 전 관찰 모드

### Real Trading Examples (Verified)
- **성공한 실거래**: XRP/USDT Long 포지션 (Order ID: 122138483629)
- **청산 완료**: XRP/USDT Short 포지션 (Order ID: 122138542108)
- **계정 연동**: 실제 바이낸스 퓨처스 계정 잔고 조회

## 🔧 핵심 기능

### 1. Multi-Port Session Management
```python
# 세션 생성 (Login Dashboard)
session_manager = get_session_manager()
session_id = session_manager.create_session(user_id, username)

# 세션 복원 (Other Dashboards)
restored = session_manager.check_and_restore_session()
```

### 2. API Key Management
```python
# API 키 저장 (암호화)
api_manager = get_api_manager()
saved = api_manager.save_api_key(user_id, 'binance', api_key, api_secret, is_testnet=False)

# API 키 조회 (복호화)
credentials = api_manager.get_api_credentials(user_id, 'binance', is_testnet=False)
```

### 3. Real Trading Integration
```python
# 메인넷 커넥터 초기화
connector = BinanceMainnetConnector(api_key, api_secret)

# 실제 주문 실행
result = connector.place_order('XRP/USDT', 'buy', quantity, order_type='market')
```

## 📁 프로젝트 구조 (현재 상태)

```
crypto-trader-pro/
├── 🔐 Multi-Dashboard System
│   ├── login_app.py                    # 로그인 대시보드 (8501)
│   ├── safe_mainnet_dashboard.py       # Safety Test (8506)
│   └── main_dashboard.py               # Main Trading (8507)
│
├── 🗄️ Database System
│   ├── database/
│   │   ├── database_manager.py         # DB 연결 관리
│   │   ├── models.py                   # User, UserSession, ApiKey 모델
│   │   └── api_manager.py              # API 키 암호화 저장
│   │
│   └── auth/
│       ├── user_manager.py             # 사용자 관리
│       ├── authentication.py           # 인증 시스템
│       └── session_manager.py          # 세션 관리 (NEW)
│
├── 🔌 Trading Connectors
│   ├── binance_mainnet_connector.py    # 메인넷 거래 (실거래)
│   └── binance_testnet_connector.py    # 테스트넷 거래
│
├── 📊 Legacy Dashboards (기존)
│   ├── streamlit_app.py                # 기본 대시보드
│   └── main.py                         # 기존 메인 앱
│
└── 📋 Configuration
    ├── pages/                          # Dashboard 페이지들
    └── config/                         # 설정 파일들
```

## 🔄 User Flow Details

### Complete Journey
1. **로그인 단계** (8501)
   - 새 사용자: 회원가입 → 계정 생성
   - 기존 사용자: 로그인 → 세션 생성
   - 자동 리디렉션: `http://localhost:8506?user=username`

2. **Safety Test 단계** (8506)
   - 세션 복원: URL 파라미터에서 사용자 정보 로드
   - API 키 입력: Binance API 키 + 시크릿 입력
   - 실거래 검증: 실제 XRP/USDT Long/Short 거래
   - API 키 저장: 암호화하여 데이터베이스 저장
   - 자동 이동: `http://localhost:8507?user=username`

3. **Main Trading 단계** (8507)
   - 세션 + API 검증: 로그인 상태 + API 키 존재 확인
   - 자동 API 로드: 저장된 암호화 키 자동 로드
   - 실거래 대시보드: 계정 정보, 포지션, 주문 관리
   - Full Trading: Long/Short, 주문 취소, Emergency Stop

## 📊 실제 거래 성과

### 검증된 거래 (Real Orders)
- **XRP/USDT Long**: Order ID 122138483629 ✅ 성공
- **XRP/USDT Short**: Order ID 122138542108 ✅ 성공
- **거래 금액**: $2.80 ~ $5.00 범위 (Safety 설정)
- **레버리지**: 1x (안전 설정)

### API 연동 상태
- **Binance USDT-M Futures**: ✅ 완전 연동
- **실시간 계정 정보**: ✅ 잔고, 포지션 조회
- **실시간 가격**: ✅ BTC, ETH, XRP 등
- **주문 관리**: ✅ 신규 주문, 취소, 조회

## 🔒 보안 및 안전 기능

### API Key Security
- **Fernet Encryption**: 대칭키 암호화로 안전한 저장
- **Database Storage**: SQLite/PostgreSQL 암호화 저장
- **Auto-load**: 로그인 시 자동 복호화 로드
- **Testnet First**: 테스트넷 검증 후 메인넷 사용

### Trading Safety
- **Emergency Stop**: 전체 거래 즉시 중단
- **Position Limits**: 최대 $50 포지션 크기
- **Order Limits**: 주문당 최대 $5 (안전 설정)
- **Observation Mode**: 실거래 전 관찰 모드

### Session Security
- **Database Sessions**: 포트간 안전한 세션 공유
- **Auto Timeout**: 1시간 비활성 시 자동 만료
- **Encrypted Storage**: 세션 정보 암호화 저장
- **URL Parameter**: 안전한 리디렉션 방식

## 🎯 시스템 상태

### ✅ 완료된 기능 (Phase 6)
- **Multi-Dashboard Flow**: 3-포트 시스템 완전 구현
- **Database Session Management**: 포트간 세션 공유 완료
- **Real Mainnet Trading**: 바이낸스 메인넷 실거래 검증
- **API Key Encryption**: 안전한 자격증명 저장/로드
- **User Flow UX**: 로그인부터 거래까지 자연스러운 플로우
- **Safety Features**: Emergency stop, limits, observation mode

### 🔄 현재 실행 중
- **Port 8501**: Login Dashboard (login_app.py)
- **Port 8506**: Safety Test Dashboard (safe_mainnet_dashboard.py)
- **Port 8507**: Main Trading Dashboard (main_dashboard.py)

### 📈 검증 완료
- **Session Restoration**: URL 파라미터 → 데이터베이스 세션 복원 ✅
- **API Integration**: BinanceMainnetConnector 실거래 연동 ✅
- **User Flow**: 로그인 → Safety → Main 완전한 플로우 ✅
- **Security**: 암호화, 세션 관리, 안전 기능 ✅

## 🚀 프로젝트 성과

**Crypto Trader Pro**는 교육용 다중 대시보드 거래 플랫폼에서 **전문 실거래 플랫폼**으로 진화했습니다.

### 🏆 주요 달성 성과 (Phase 6)
- ✅ **Seamless User Flow**: 로그인부터 실거래까지 자연스러운 3단계 플로우
- ✅ **Real Mainnet Trading**: 바이낸스 USDT-M 퓨처스 실거래 시스템
- ✅ **Database Session Management**: 포트간 세션 상태 공유 완전 구현
- ✅ **Professional Security**: API 키 암호화, 세션 관리, 거래 안전 기능
- ✅ **Verified Trading**: 실제 XRP/USDT 거래 성공 (Order ID 확인)
- ✅ **Emergency Controls**: 즉시 거래 중단, 포지션 관리, 리스크 제한

### 🌐 시스템 아키텍처
- **Multi-Port Design**: 기능별 분리된 3개 대시보드
- **Database-Driven**: SQLAlchemy 기반 데이터 영속성
- **API Integration**: CCXT + python-binance 이중 연동
- **Security-First**: 암호화, 인증, 세션 관리 최우선

---

**⚠️ 리스크 경고**: 암호화폐 거래는 높은 위험을 수반합니다. 이 시스템은 교육 목적으로 제작되었습니다. 실거래 시 충분한 이해와 주의가 필요합니다. 감당할 수 있는 범위 내에서만 거래하세요.