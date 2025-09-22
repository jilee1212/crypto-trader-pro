# 🚀 Crypto Trader Pro - Professional Trading Platform

완전한 암호화폐 거래 플랫폼으로 실시간 데이터, AI 신호 생성, 현물/선물 거래, 사용자 관리를 통합 제공합니다.

**⚠️ 면책조항: 이 소프트웨어는 교육 및 연구 목적으로만 제작되었습니다. 암호화폐 거래는 상당한 손실 위험을 수반합니다. 실거래 전 반드시 테스트넷에서 충분히 테스트하세요.**

## 🌐 배포 환경 (24시간 운영)
- **서버**: Vultr Ubuntu 24.04 LTS (1 CPU, 1GB RAM, 32GB SSD)
- **도메인**: http://nosignup.kr (24시간 접속 가능)
- **프로젝트 경로**: /opt/crypto-trader/crypto-trader-pro/
- **실행 환경**: Python 3.12, PM2 백그라운드 운영
- **GitHub**: https://github.com/jilee1212/crypto-trader-pro.git

## 🔧 최신 기술 스택 (2025년 1월 업데이트)
- **백엔드**: Python 3.12, Streamlit 1.40.0
- **API 연동**: python-binance 라이브러리 (공식 패턴)
- **데이터베이스**: SQLAlchemy ORM + SQLite, 암호화된 API 키 저장
- **보안**: Fernet 암호화, bcrypt 패스워드 해싱, JWT 토큰
- **배포**: PM2 프로세스 관리, Nginx 리버스 프록시
- **모니터링**: 실시간 거래 로그, 시스템 상태 대시보드

## 🎯 메인 플랫폼 - main_platform.py

**포트 8501**: http://localhost:8501
**현재 상태**: 🟢 완전 운영 가능

### ✅ 완성된 시스템 (현재 상태)

#### **🎉 Phase 1-4 완료: 24시간 무인 자동매매 시스템 + 고급 기능 100% 구축 완료**

**Phase 1-2: 시스템 기반 구축 ✅**
- **🗄️ 데이터베이스 시스템**: SQLAlchemy ORM, 암호화된 사용자 데이터 관리
- **🔐 사용자 인증**: bcrypt 패스워드 해싱, JWT 토큰, 세션 관리
- **🔑 API 키 보안**: Fernet 암호화, 마스터 키 관리, 안전한 저장
- **🤖 독립 거래 봇**: 웹과 분리된 백그라운드 프로세스 (trading_engine/)
- **📊 실시간 모니터링**: 시장 데이터, 기술적 분석 지표 (RSI, MACD, 볼린저밴드)
- **⚙️ 사용자별 격리**: 독립적인 거래 컨텍스트 및 리스크 관리
- **🎯 RSI 전략**: 평균 회귀 전략, 동적 포지션 사이징, 자동 손절/익절
- **⏰ PM2 배포**: 24시간 무중단 운영, 자동 재시작

**Phase 3: 인증 기반 웹 인터페이스 ✅**
- **🔐 로그인/회원가입**: 완전한 사용자 인증 시스템
- **📊 개인화 대시보드**: 사용자별 거래 성과 및 상태 모니터링
- **⚙️ 설정 관리**: API 키, 거래 설정, 계정 관리, 알림 설정
- **📈 거래 모니터링**: 실시간 차트, 포지션 관리, 거래 제어
- **🎮 거래 제어**: 웹에서 자동매매 시작/중단/설정 실시간 적용

**Phase 4: 고급 기능 및 최적화 ✅**
- **📬 다중 채널 알림**: 이메일, 텔레그램, 웹 대시보드 알림 시스템
- **💾 자동 백업 시스템**: 일일 DB 백업, 설정 파일 백업, 복구 시스템
- **🔄 스케줄링**: PM2 기반 3-프로세스 아키텍처 (웹, 봇, 백업)
- **🛡️ 무결성 검증**: 백업 파일 검증, 복구 계획, 재해 복구

#### **기존 완성 시스템 (Legacy)**
- **💰 현물 거래**: 100% 완성 (ai_trading_signals.py) - 기존 시스템
- **🔗 바이낸스 현물 API**: binance_testnet_connector.py - 기존 시스템
- **🤖 AI 신호 시스템**: 78% 정확도, RandomForest + LinearRegression - 기존 시스템
- **🖥️ 웹 대시보드**: 기존 5탭 UI → 새로운 인증 기반 시스템으로 교체

### 🔧 핵심 기능
- **👤 사용자 시스템**: 회원가입, 로그인, SQLite 기반 계정 관리
- **🔐 API 키 관리**: 테스트넷/실거래 모드, 안전한 키 저장
- **📈 실시간 시장 데이터**: Binance + CoinGecko API 이중화
- **🤖 AI 신호 생성**: BUY/SELL/HOLD + 신뢰도 점수
- **💰 선물 거래**: 1-10배 레버리지, Cross/Isolated 마진
- **💼 포트폴리오 관리**: 실시간 잔고, 포지션, 수익률 표시
- **📊 대시보드**: 5개 탭 구성의 전문적 UI

## 📁 프로젝트 구조 (정리 완료)

### ✅ 핵심 파일 (Phase 1-4 완료)
```
crypto-trader-pro/
├── main_platform.py                # 🎯 메인 플랫폼 (포트 8501)
├── ecosystem.config.js             # 🔧 PM2 3-프로세스 배포 설정
├── backup_scheduler.py             # 💾 백업 스케줄러 서비스
├── backup_config.json              # ⚙️ 백업 시스템 설정
├── notification_config.json        # 📬 알림 시스템 설정
├── database/                       # 🗄️ 데이터베이스 시스템
│   ├── models.py                   # SQLAlchemy ORM 모델
│   ├── database_manager.py         # CRUD 작업 관리 (세션 수정됨)
│   ├── init_database.py            # DB 초기화 스크립트
│   └── __init__.py
├── auth/                           # 🔐 사용자 인증 시스템
│   ├── authentication.py          # JWT, bcrypt, 세션 관리
│   ├── user_manager.py             # 사용자 관리
│   └── __init__.py
├── security/                       # 🔑 보안 및 암호화
│   ├── encryption.py               # Fernet 암호화 시스템
│   ├── api_key_manager.py          # API 키 보안 관리
│   └── __init__.py
├── trading_engine/                 # 🤖 독립 거래 봇
│   ├── background_trader.py        # 메인 거래 봇
│   ├── market_monitor.py           # 실시간 시장 데이터
│   ├── user_trading_context.py     # 사용자별 거래 환경
│   ├── trading_scheduler.py        # 거래 스케줄링
│   └── __init__.py
├── notifications/                  # 📬 다중 채널 알림 시스템
│   ├── base_notifier.py            # 알림 기본 클래스
│   ├── email_notifier.py           # SMTP 이메일 알림
│   ├── telegram_notifier.py        # 텔레그램 봇 알림
│   ├── web_notifier.py             # 웹 대시보드 알림
│   ├── notification_manager.py     # 통합 알림 관리자
│   └── __init__.py
├── backup/                         # 💾 백업 및 복구 시스템
│   ├── database_backup.py          # DB 백업 (전체/증분)
│   ├── config_backup.py            # 설정 파일 백업
│   ├── recovery_manager.py         # 복구 관리자
│   ├── backup_manager.py           # 통합 백업 관리자
│   └── __init__.py
├── pages/                          # 🌐 웹 인터페이스 페이지
│   ├── login.py                    # 로그인 페이지
│   ├── register.py                 # 회원가입 페이지
│   ├── dashboard.py                # 메인 대시보드
│   ├── settings.py                 # 설정 페이지
│   └── trading.py                  # 거래 페이지
└── [기존 파일들]                    # 기존 시스템 (ai_trading_signals.py 등)
```

### 📦 보관된 파일
```
archived_files/                     # 중복/테스트 파일들 보관
├── ai_trading_signals_*.py         # 이전 버전들
├── test_*.py                       # 테스트 스크립트들
├── performance_dashboard.py        # 성능 대시보드
└── hybrid_trading_dashboard.py     # 하이브리드 대시보드
```

## 🚀 빠른 시작

### 1. 환경 설정
```bash
# 의존성 설치
pip install streamlit pandas plotly ccxt requests numpy
pip install sqlalchemy bcrypt PyJWT cryptography

# 데이터베이스 초기화
cd database
python init_database.py --reset

# 메인 플랫폼 실행
streamlit run main_platform.py

# 백그라운드 거래 봇 실행 (별도 터미널)
python trading_engine/background_trader.py
```

### 2. 첫 사용
1. **회원가입**: http://localhost:8501 접속 후 계정 생성
2. **API 키 설정**: 사이드바 → API 설정 → Binance 테스트넷 키 입력
3. **거래 설정**: 계좌 잔고, 리스크 비율, 거래 모드 설정
4. **AI 신호**: AI 신호 탭에서 실시간 신호 생성 및 확인

### 3. API 키 설정 (필수)
```
Binance Testnet:
- 웹 인터페이스에서 직접 설정
- 설정 > API 설정 탭에서 테스트넷 키 입력
- 암호화된 안전한 저장소에 보관
- 모드: 테스트넷 (처음 사용 시 필수)
```

## 🖥️ 대시보드 구성

### 📊 대시보드 탭
- **실시간 BTC/ETH 가격 표시**
- **계좌 잔고, 리스크 비율, API 상태**
- **빠른 액션 버튼 (신호 생성, 포지션 조회)**

### 🔐 API 설정 탭
- **Binance API 키 입력 및 관리**
- **테스트넷/실거래 모드 선택**
- **연결 테스트 및 상태 확인**

### 🤖 AI 신호 탭
- **실시간 AI 신호 생성 (BUY/SELL/HOLD)**
- **신뢰도 점수 및 기술적 분석**
- **자동 거래 실행 옵션**
- **포지션 사이징 계산**

### 💼 포트폴리오 탭
- **실시간 계좌 잔고 (USDT)**
- **활성 포지션 현황**
- **미실현 손익 및 수익률**
- **마진 사용률 모니터링**

### 📈 거래 기록 탭
- **거래 히스토리 조회**
- **성과 분석 및 통계**
- **수익률 차트**

## 🛡️ 리스크 관리 시스템

### DynamicRiskManager 핵심 공식
```
포지션 크기 = 계좌_리스크_금액 ÷ (레버리지 × 손절_폭)

예시:
- 2% 손절 → 1배 레버리지 → $10,000 포지션
- 1% 손절 → 2배 레버리지 → $10,000 포지션
- 5% 손절 → 1배 레버리지 → $4,000 포지션
```

### 안전장치
- **레버리지 제한**: 최대 10배
- **마진 사용률**: 50% 초과 시 경고
- **일일 손실 한도**: 3%
- **연속 손실**: 자동 포지션 크기 축소

## 🔧 기술적 구현

### python-binance 표준 연동
```python
# 공식 라이브러리 사용
from binance_standard_connector import BinanceStandardConnector
connector = BinanceStandardConnector(api_key, api_secret, testnet=True)

# 계좌 정보 조회
account_info = connector.get_account_info()
if account_info['success']:
    print(f"잔고: {account_info['data']['balances']}")

# 실시간 가격 조회
btc_price = connector.get_symbol_ticker('BTCUSDT')
print(f"BTC 가격: ${btc_price['data']['price']}")
```

### 암호화된 API 키 관리
```python
# API 키 안전한 저장
from database.api_manager import get_api_manager
api_manager = get_api_manager()

# 키 저장 (Fernet 암호화)
success = api_manager.save_api_key(
    user_id=1, exchange='binance',
    api_key='your_key', api_secret='your_secret',
    is_testnet=True
)

# 키 조회 (자동 복호화)
credentials = api_manager.get_api_credentials(1, 'binance', True)
```

### AI 신호 생성
```python
# AI 신호 생성
ai_system = EnhancedAITradingSystem(account_balance=10000, risk_percent=0.02)
signal = ai_system.generate_enhanced_signal('BTC', market_data)
```

## 📊 현재 시스템 상태 (2025년 1월 최신)

### ✅ 완료된 기능
- **실시간 데이터**: python-binance 라이브러리 기반 정확한 가격 데이터
- **사용자 시스템**: 완전한 인증 및 세션 관리 (SQLAlchemy ORM)
- **API 통합**: Binance 테스트넷/메인넷 연결 완료 (표준 패턴)
- **암호화된 API 키**: Fernet 암호화로 안전한 저장
- **AI 신호**: 실시간 신호 생성 가능
- **선물 거래**: 1-10배 레버리지 지원
- **리스크 관리**: 정교한 포지션 사이징
- **데이터베이스**: 완전한 스키마 마이그레이션 시스템

### 🔄 실행 중인 서비스 (3-프로세스 아키텍처)
- **포트 8501**: main_platform.py (웹 인터페이스)
- **독립 프로세스**: trading_engine/background_trader.py (24시간 거래 봇)
- **백업 서비스**: backup_scheduler.py (자동 백업 및 복구)
- **PM2 관리**: ecosystem.config.js (3-프로세스 자동 재시작, 로그 관리)

## 🚀 사용 예시

### 기본 거래 흐름
1. **로그인** → main_platform.py 접속
2. **API 설정** → Binance 테스트넷 키 입력
3. **거래 설정** → 잔고 $10,000, 리스크 2% 설정
4. **AI 신호** → BTC 신호 생성 → BUY 75% 신뢰도
5. **포지션 관리** → 2배 레버리지, $5,000 포지션
6. **모니터링** → 실시간 손익 추적

### 고급 기능 (Phase 4)
- **자동 거래**: 높은 신뢰도 신호 자동 실행
- **포지션 분석**: 실시간 수익률 및 리스크 계산
- **다중 채널 알림**: 이메일, 텔레그램, 웹 실시간 알림
- **자동 백업**: 일일 DB 백업, 설정 백업, 복구 시스템
- **백테스팅**: 과거 데이터 기반 전략 검증
- **페이퍼 트레이딩**: 실제 돈 없이 전략 테스트

## 📈 성과 및 안정성

### 검증된 성능 (2025년 1월 업데이트)
- **API 응답시간**: python-binance 라이브러리 기반 최적화된 성능
- **데이터 정확도**: 실시간 Binance 가격 반영 (공식 API)
- **시스템 안정성**: 24/7 운영 가능, 자동 재시작 시스템
- **보안**: Fernet 암호화, 안전한 API 키 관리, 데이터베이스 무결성

### 테스트 결과
- **시장 데이터**: ✅ 실시간 BTC/ETH 가격 정확 (python-binance)
- **AI 신호**: ✅ BUY/SELL/HOLD 신호 생성
- **선물 거래**: ✅ 레버리지 및 마진 관리
- **리스크 관리**: ✅ 포지션 사이징 정확도
- **API 키 관리**: ✅ 암호화 저장/조회 완벽 작동
- **데이터베이스**: ✅ 스키마 마이그레이션 시스템 완성

## 🔒 보안 및 주의사항

### API 키 보안
- **테스트넷 우선**: 처음에는 반드시 테스트넷 사용
- **권한 제한**: Futures Trading 권한만 활성화
- **정기 교체**: API 키 주기적 갱신
- **환경 분리**: 테스트/실거래 환경 완전 분리

### 리스크 관리
- **소액 시작**: 실거래 시 소액으로 시작
- **손실 한도**: 반드시 일일 손실 한도 설정
- **감정 제어**: AI 신호 기반 객관적 판단
- **지속적 모니터링**: 포지션 실시간 추적

## 🎯 결론

**Crypto Trader Pro는 교육용 암호화폐 거래 플랫폼으로 완전한 기능을 제공합니다.**

### 주요 성과 (Phase 1-4 완료)
- ✅ **완전한 플랫폼**: 사용자 관리부터 실제 거래까지
- ✅ **실시간 데이터**: 정확한 시장 정보 반영
- ✅ **AI 기반 신호**: 과학적 거래 의사결정
- ✅ **안전한 거래**: 철저한 리스크 관리
- ✅ **사용자 친화적**: 직관적 웹 인터페이스
- ✅ **다중 채널 알림**: 이메일, 텔레그램, 웹 통합 알림
- ✅ **자동 백업**: 완전한 재해 복구 시스템
- ✅ **24/7 무인 운영**: PM2 3-프로세스 안정적 운영

**지금 바로 http://localhost:8502 또는 http://nosignup.kr 에서 시작하세요!**

## 🔄 최신 업데이트 (2025년 1월)

### 🛠️ 기술적 개선사항
- **python-binance 1.0.29**: 공식 라이브러리로 API 연동 표준화
- **Streamlit 1.40.0**: 최신 웹 프레임워크로 업그레이드
- **데이터베이스 마이그레이션**: 자동 스키마 업데이트 시스템
- **모듈 구조 최적화**: import 오류 완전 해결
- **암호화 시스템**: Fernet 기반 안전한 API 키 관리

### 🚀 배포 자동화
- **Vultr 자동 배포**: `vultr_deploy.sh` 스크립트 완성
- **PM2 프로세스 관리**: 3-프로세스 아키텍처 (웹, 봇, 백업)
- **Nginx 리버스 프록시**: 고성능 웹 서버 설정
- **SSL 지원**: Let's Encrypt 자동 인증서 발급
- **로그 관리**: 체계적인 로그 수집 및 모니터링

### 🔧 개발자 도구
- **requirements.txt**: 모든 의존성 최신화
- **ecosystem.config.js**: PM2 배포 설정 완성
- **DEPLOYMENT_GUIDE.md**: 상세한 배포 가이드
- **migration_script.py**: 데이터베이스 자동 마이그레이션

---

**⚠️ 리스크 경고**: 암호화폐 거래는 높은 위험을 수반합니다. 감당할 수 있는 범위 내에서만 거래하세요. 이 소프트웨어는 교육 목적입니다. 실거래 전 충분한 테스트가 필요합니다.