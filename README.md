# 🚀 Crypto Trader Pro - Advanced Cryptocurrency Trading Platform

완전 자동화된 24시간 무인 자동매매 시스템과 Freqtrade 기반 고급 트레이딩 플랫폼입니다.

**⚠️ 면책조항: 이 소프트웨어는 교육 및 연구 목적으로만 제작되었습니다. 암호화폐 거래는 상당한 손실 위험을 수반합니다. 실거래 전 반드시 테스트넷에서 충분히 테스트하세요.**

## 🎯 시스템 현황 (2025년 9월 23일)

### ✅ Phase 1-4 완료: 24시간 무인 자동매매 시스템
- **운영 서버**: Vultr Ubuntu 24.04 LTS (http://nosignup.kr)
- **시스템 상태**: 24시간 안정적 운영 중
- **PM2 관리**: 3-프로세스 아키텍처 (웹, 봇, 백업)
- **고급 기능**: 다중 채널 알림, 자동 백업, 사용자 인증

### 🚀 Phase 5C-5D 완료: Freqtrade 고급 시스템
- **다중 지표 전략**: RSI + MACD + 볼린저 밴드 통합
- **AI 모델 포팅**: 기존 RandomForest + LinearRegression 모델 완전 이식
- **24/7 운영 최적화**: PM2 + Docker + 실시간 모니터링
- **백테스팅 & 최적화**: 하이퍼파라미터 튜닝, 성능 검증 완료

## 🔧 최신 기술 스택 (2025년 9월 업데이트)

### 핵심 플랫폼
- **Freqtrade 0.29+**: 검증된 암호화폐 트레이딩 프레임워크
- **Python 3.12**: 최신 언어 기능 및 성능 최적화
- **Docker**: 컨테이너 기반 배포 및 격리
- **PM2**: 3-프로세스 관리 (웹, 트레이더, 백업)

### 데이터 & 인프라
- **SQLAlchemy 2.0**: ORM 기반 데이터베이스 관리
- **CCXT**: 거래소 API 통합 표준 라이브러리
- **PostgreSQL**: 운영 환경 데이터베이스 (SQLite 개발용)
- **Nginx**: 리버스 프록시 및 로드 밸런싱

### AI/ML & 전략
- **RandomForest + LinearRegression**: 검증된 AI 모델
- **RSI + MACD + Bollinger Bands**: 다중 지표 전략
- **하이퍼파라미터 최적화**: Freqtrade Hyperopt 활용
- **백테스팅**: 전략 성능 검증 및 최적화

### 모니터링 & 운영
- **Streamlit**: 실시간 대시보드 및 웹 인터페이스
- **Telegram/Email**: 다중 채널 알림 시스템
- **자동 백업**: 일일/주간/월간 백업 스케줄링
- **성능 모니터링**: 실시간 지표 추적 및 분석

## 🎯 시스템 구성

### 🚀 Freqtrade 트레이딩 시스템 (Phase 5C-5D 완료)
**배포 경로**: `/home/linuxuser/crypto-trader-pro/freqtrade_setup/`
**현재 상태**: 🟢 24/7 운영 준비 완료

#### ✅ 핵심 구성 요소
- **🤖 다중 지표 전략**: MultiIndicatorStrategy.py (RSI+MACD+볼린저밴드)
- **🧠 AI 모델 통합**: 기존 RandomForest+LinearRegression 모델 포팅
- **📊 실시간 모니터링**: realtime_dashboard.py (포트 8083)
- **🔗 통합 브리지**: integration_bridge.py (포트 8082)
- **💾 자동 백업**: freqtrade_backup.py (일일/주간/월간)
- **⚡ 성능 최적화**: performance_optimizer.py

#### 🌐 서비스 포트 구성
- **8080**: Freqtrade API 서버
- **8081**: Freqtrade Web UI
- **8082**: Integration Bridge API
- **8083**: Real-time Dashboard (Streamlit)

### 📊 기존 대시보드 시스템 (Phase 1-4)
**포트 8501**: http://localhost:8501 (로컬) / http://nosignup.kr (운영)
**현재 상태**: 🟢 24시간 안정적 운영 중

#### ✅ 구현된 기능
- **🔐 사용자 인증**: JWT 기반 로그인/로그아웃 시스템
- **👤 테스트 계정**: admin/admin123, trader1/trader123
- **📈 실시간 가격**: BTC, ETH, BNB, ADA, SOL 실시간 모니터링
- **💰 포트폴리오**: 계정 잔고 관리 및 거래 이력
- **📊 시장 데이터**: 주문서, 2,154개 거래쌍 정보
- **🔔 알림 시스템**: 이메일, 텔레그램 다중 채널 지원

### 📈 간단 대시보드 (인증 없음) - streamlit_app.py
**별도 실행**: `streamlit run streamlit_app.py`
**현재 상태**: 🟢 기본 기능 작동

#### ✅ 구현된 기능
- **📈 실시간 가격**: 주요 암호화폐 가격 모니터링
- **📊 시장 데이터**: 기본적인 시장 정보
- **💰 포트폴리오**: 기본 포트폴리오 뷰
- **⚙️ 설정**: 기본 설정 관리

### 🔧 CCXT 커넥터 - binance_testnet_connector.py (새로 구현됨)
**현재 상태**: 🟢 CCXT 표준 패턴으로 완전 재구현

#### ✅ 구현된 기능
- **📡 연결 테스트**: Binance Testnet 연결 확인 (2,154 거래쌍)
- **💰 계정 잔고**: `fetch_balance()` CCXT 표준 메서드
- **📈 실시간 가격**: `fetch_ticker()` 공식 API
- **📊 주문서**: `fetch_order_book()` 표준 패턴
- **🔒 안전한 초기화**: sandbox 모드, 에러 처리

## 🔧 핵심 기능 (현재 구현됨)
- **👤 사용자 시스템**: 로그인/로그아웃, SQLite 기반 계정 관리
- **🔐 API 키 관리**: Binance Testnet 연동, 안전한 키 저장
- **📈 실시간 시장 데이터**: CCXT 기반 Binance 공식 API
- **💼 포트폴리오 관리**: 실시간 잔고 조회 (API 키 필요)
- **📊 대시보드**: 4개 탭 구성 (가격, 포트폴리오, 시장데이터, 설정)

## 📁 프로젝트 구조 (현재 상태)

### ✅ 핵심 파일 (실행 가능)
```
crypto-trader-pro/
├── main_dashboard.py              # 🎯 메인 대시보드 (인증 포함) - 포트 8501
├── streamlit_app.py               # 📈 간단 대시보드 (인증 없음)
├── binance_testnet_connector.py   # 🔧 CCXT 기반 API 커넥터 (새로 구현)
├── setup_test_users.py            # 👤 테스트 계정 설정 스크립트
├── database/                      # 🗄️ 데이터베이스 (SQLite)
│   └── crypto_trader.db           # 사용자 데이터베이스
└── [기타 파일들]                   # 이전 버전 파일들
```

### 📊 현재 실행 중인 앱들
- **main_dashboard.py**: 인증 기능이 있는 완전한 대시보드
- **streamlit_app.py**: 기본 암호화폐 대시보드
- **main.py**: (실행 중 - 별도 포트)

## 🚀 빠른 시작

### 로컬 개발 환경 (3분 설정)
```bash
# 1. 의존성 설치
pip install streamlit pandas plotly ccxt bcrypt

# 2. 테스트 계정 생성
python setup_test_users.py

# 3. 메인 대시보드 실행
streamlit run main_dashboard.py
```

### Freqtrade 시스템 배포 (운영 환경)
```bash
# 1. Freqtrade 설정 디렉토리로 이동
cd freqtrade_setup

# 2. 로컬 테스트 (DRY-RUN 모드)
./run_phase5d_complete.sh local

# 3. 프로덕션 서버 배포 (Vultr)
./run_phase5d_complete.sh production 141.164.42.93 linuxuser
```

### 첫 사용자 가이드
1. **기본 대시보드**: http://localhost:8501 접속
2. **테스트 계정**: admin/admin123 또는 trader1/trader123
3. **Freqtrade 대시보드**: http://localhost:8083 (배포 후)
4. **API 키 설정**: Settings 탭에서 Binance Testnet 키 입력

### 3. 테스트 계정 정보
```
관리자 계정:
- 사용자명: admin
- 패스워드: admin123
- 권한: 모든 기능 접근 가능

일반 사용자:
- 사용자명: trader1
- 패스워드: trader123
- 권한: 기본 거래 기능
```

## 🖥️ 대시보드 구성

### 📈 Live Prices 탭
- **실시간 암호화폐 가격**: BTC, ETH, BNB, ADA, SOL
- **가격 메트릭**: 현재 가격, 매수/매도 호가, 거래량
- **새로고침 기능**: 실시간 가격 업데이트

### 💰 Portfolio 탭
- **연결 테스트**: Binance Testnet API 상태 확인
- **계정 잔고**: API 키 연동 후 실제 잔고 표시
- **권한별 접근**: 관리자/일반사용자 권한 구분

### 📊 Market Data 탭
- **거래쌍 정보**: 2,154개 Binance 거래쌍 목록
- **주문서 데이터**: BTC/USDT 매수/매도 주문 현황
- **시장 분석**: 실시간 시장 데이터

### ⚙️ Settings 탭
- **사용자 정보**: 로그인 정보, 권한 상태
- **API 설정**: Binance Testnet API 키 관리
- **시스템 정보**: CCXT 버전, 연결 상태, 데이터베이스 상태

## 🔧 기술적 구현

### CCXT 표준 연동
```python
# CCXT 공식 라이브러리 사용
from binance_testnet_connector import BinanceTestnetConnector
connector = BinanceTestnetConnector(api_key, secret_key)

# 연결 테스트
result = connector.test_connection()
if result['success']:
    print(f"연결 성공: {result['total_markets']}개 거래쌍")

# 실시간 가격 조회
price_data = connector.get_current_price('BTC/USDT')
if price_data['success']:
    print(f"BTC 가격: ${price_data['price']:,.2f}")

# 계좌 잔고 조회
balance = connector.get_account_balance()
if balance['success']:
    print(f"잔고: {balance['balances']}")
```

### 사용자 인증 시스템
```python
# bcrypt 패스워드 해싱
import bcrypt
password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# 로그인 검증
def verify_login(username, password):
    # 데이터베이스에서 사용자 조회
    cursor.execute('SELECT password_hash FROM users WHERE username = ?', (username,))
    result = cursor.fetchone()

    # 패스워드 검증
    return bcrypt.checkpw(password.encode('utf-8'), result[0].encode('utf-8'))
```

### 실시간 데이터 처리
```python
# 안전한 데이터 추출
def get_current_price(self, symbol='BTC/USDT'):
    try:
        ticker = self.exchange.fetch_ticker(symbol)
        return {
            'success': True,
            'symbol': ticker['symbol'],
            'price': ticker['last'],
            'bid': ticker['bid'],
            'ask': ticker['ask'],
            'volume': ticker['baseVolume']
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}
```

## 📊 현재 시스템 상태 (2025년 9월 최신)

### ✅ 완료된 기능
- **실시간 데이터**: CCXT 라이브러리 기반 정확한 Binance 가격 데이터
- **사용자 인증**: bcrypt 기반 안전한 로그인/로그아웃 시스템
- **API 통합**: Binance Testnet 연결 완료 (CCXT 표준 패턴)
- **대시보드**: 4탭 구성의 직관적 웹 인터페이스
- **시장 데이터**: 2,154개 거래쌍, 실시간 주문서, 가격 정보
- **테스트 계정**: admin, trader1 계정으로 즉시 테스트 가능
- **에러 처리**: 안전한 데이터 추출, 네트워크 오류 처리

### 🔄 현재 실행 중인 서비스
- **포트 8501**: main_dashboard.py (인증 기반 메인 대시보드)
- **별도 포트**: streamlit_app.py (간단 대시보드)
- **API 커넥터**: binance_testnet_connector.py (CCXT 기반)

## 🚀 사용 예시

### 기본 사용 흐름
1. **로그인** → http://localhost:8501 접속
2. **테스트 계정** → admin/admin123 또는 trader1/trader123 입력
3. **실시간 가격** → Live Prices 탭에서 BTC, ETH 등 가격 확인
4. **API 설정** → Settings 탭에서 Binance Testnet 키 입력 (선택)
5. **포트폴리오** → Portfolio 탭에서 계정 잔고 확인
6. **시장 데이터** → Market Data 탭에서 주문서, 거래쌍 정보 확인

### 현재 가능한 기능
- **실시간 모니터링**: 주요 암호화폐 가격 실시간 추적
- **연결 테스트**: Binance Testnet API 상태 확인
- **시장 분석**: 2,154개 거래쌍 정보, 주문서 데이터
- **안전한 인증**: bcrypt 기반 사용자 로그인 시스템
- **권한 관리**: 관리자/일반사용자 권한 구분

## 📈 성과 및 안정성

### 검증된 성능 (2025년 9월 업데이트)
- **API 응답시간**: CCXT 라이브러리 기반 최적화된 성능
- **데이터 정확도**: 실시간 Binance 가격 반영 (CCXT 공식 패턴)
- **시스템 안정성**: 로컬 개발 환경에서 안정적 운영
- **보안**: bcrypt 패스워드 해싱, 안전한 세션 관리

### 테스트 결과
- **연결 테스트**: ✅ Binance Testnet 연결 성공 (2,154 거래쌍)
- **실시간 가격**: ✅ BTC $112,508.44 정확 반영 (CCXT)
- **사용자 인증**: ✅ 로그인/로그아웃 시스템 완벽 작동
- **대시보드**: ✅ 4개 탭 모든 기능 정상 작동
- **API 키 관리**: ✅ Settings 탭에서 안전한 키 관리
- **에러 처리**: ✅ 네트워크 오류, 인증 오류 적절히 처리

## 🔒 보안 및 주의사항

### API 키 보안
- **테스트넷 우선**: 처음에는 반드시 Binance Testnet 사용
- **권한 제한**: 필요한 권한만 최소한으로 설정
- **안전한 저장**: 환경 변수 또는 설정 파일에 안전하게 보관
- **정기 교체**: API 키 주기적 갱신 권장

### 사용자 보안
- **강력한 패스워드**: bcrypt 해싱으로 안전하게 보호
- **세션 관리**: 자동 로그아웃, 안전한 세션 처리
- **권한 분리**: 관리자/일반사용자 권한 명확히 구분

## 🎯 프로젝트 성과

**Crypto Trader Pro는 Phase 1-4 완료된 24시간 무인 자동매매 시스템과 Phase 5C-5D 완료된 Freqtrade 고급 시스템을 통합한 전문 트레이딩 플랫폼입니다.**

### 🏆 주요 달성 성과
- ✅ **24/7 자동매매**: PM2 3-프로세스 관리로 안정적 운영
- ✅ **Freqtrade 통합**: 검증된 프레임워크 기반 고급 전략 구현
- ✅ **AI 모델 포팅**: RandomForest+LinearRegression → Freqtrade 전략 완전 이식
- ✅ **다중 지표 전략**: RSI+MACD+볼린저밴드 가중치 기반 신호 집계
- ✅ **24/7 모니터링**: 실시간 대시보드, 다중 채널 알림, 자동 백업
- ✅ **운영 최적화**: 99.9% 목표 가동률, <5분 자동 복구, 완전 자동화

### 🌐 배포 환경
- **개발 환경**: http://localhost:8501 (로컬 개발용)
- **운영 환경**: http://nosignup.kr (Vultr 서버 24시간 운영)
- **Freqtrade 시스템**: Phase 5D 완료, 운영 배포 준비 완료

## 🔄 최신 업데이트 (2025년 9월)

### 🛠️ 기술적 개선사항
- **CCXT 4.5.5**: 암호화폐 거래소 연동 표준 라이브러리
- **Streamlit 최신 버전**: 반응형 웹 대시보드
- **bcrypt 패스워드 해싱**: 안전한 사용자 인증
- **SQLite 데이터베이스**: 가벼운 로컬 데이터 저장
- **에러 처리 강화**: 네트워크, 인증, 데이터 오류 안전 처리

### 🚀 구현 완료
- **main_dashboard.py**: 인증 기반 완전한 대시보드
- **streamlit_app.py**: 기본 암호화폐 모니터링 도구
- **binance_testnet_connector.py**: CCXT 표준 패턴 API 커넥터
- **setup_test_users.py**: 테스트 계정 자동 생성 시스템

---

**⚠️ 리스크 경고**: 암호화폐 거래는 높은 위험을 수반합니다. 감당할 수 있는 범위 내에서만 거래하세요. 이 소프트웨어는 교육 목적입니다. 실거래 전 충분한 테스트가 필요합니다.