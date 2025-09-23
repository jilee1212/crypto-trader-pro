# 🚀 Freqtrade Phase 5A - Docker 기반 자동매매 시스템

## 📋 개요

Crypto Trader Pro 프로젝트의 Phase 5A로, 기존 시스템과 병렬로 운영되는 Freqtrade 기반 자동매매 환경입니다.

### 🎯 목표
- 기존 ai_trading_signals.py 시스템과 독립적 운영
- Docker 기반 컨테이너화된 안정적 환경
- 바이낸스 테스트넷 API 연동
- 보수적 RSI 전략 기반 거래
- PM2와 통합 가능한 프로세스 관리

### 🏗️ 아키텍처

```
freqtrade_setup/
├── docker-compose.yml          # Docker 서비스 정의
├── config/
│   └── config.json            # Freqtrade 메인 설정
├── user_data/
│   ├── strategies/
│   │   └── RSIStrategy.py     # 기본 RSI 전략
│   ├── data/                  # 가격 데이터 저장소
│   └── backtest_results/      # 백테스팅 결과
├── logs/                      # 로그 파일
├── deploy_freqtrade.sh        # 서버 배포 스크립트
├── setup_api_keys.sh          # API 키 설정 스크립트
└── README.md                  # 이 파일
```

## 🚀 빠른 시작

### 1. 서버 배포 (Vultr Ubuntu 24.04)

```bash
# 1. 프로젝트를 서버에 업로드
scp -r freqtrade_setup/ linuxuser@141.164.42.93:/tmp/

# 2. 서버 접속
ssh linuxuser@141.164.42.93

# 3. 배포 스크립트 실행
cd /tmp/freqtrade_setup
chmod +x deploy_freqtrade.sh
./deploy_freqtrade.sh
```

### 2. API 키 설정

```bash
# Freqtrade 디렉토리로 이동
cd /opt/crypto-trader/freqtrade

# API 키 설정 스크립트 실행
chmod +x setup_api_keys.sh
./setup_api_keys.sh
```

### 3. 서비스 확인

```bash
# 컨테이너 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs -f

# 웹 UI 접속
curl http://localhost:8081
```

## 🔧 설정 구성

### config.json 주요 설정

```json
{
    "max_open_trades": 3,           // 최대 동시 거래 수
    "stake_amount": 100,            // 거래당 투자 금액 (USDT)
    "dry_run": true,                // 페이퍼 트레이딩 모드
    "dry_run_wallet": 1000,         // 가상 자금
    "trading_mode": "spot",         // 현물 거래
    "exchange": {
        "name": "binance",
        "ccxt_config": {
            "sandbox": true         // 테스트넷 모드
        }
    }
}
```

### RSIStrategy 특징

- **진입 조건**: RSI < 30, 볼린저밴드 하단, MACD 상승, 거래량 증가
- **청산 조건**: RSI > 70, 볼린저밴드 상단, MACD 하락
- **리스크 관리**: 10% 손절매, 4% 익절 설정
- **타임프레임**: 5분봉 기준

## 📊 모니터링 및 관리

### 1. 웹 인터페이스

- **Freqtrade API**: http://your-server:8080
- **Freqtrade UI**: http://your-server:8081
- **통합 접속**: http://your-server/freqtrade/

### 2. 명령어 모음

```bash
# 서비스 관리
docker-compose up -d          # 서비스 시작
docker-compose down           # 서비스 중지
docker-compose restart       # 서비스 재시작
docker-compose logs -f       # 실시간 로그

# 백테스팅
docker-compose exec freqtrade freqtrade backtesting \
    --config /freqtrade/config/config.json \
    --strategy RSIStrategy \
    --timerange 20241201-20241222

# 데이터 다운로드
docker-compose exec freqtrade freqtrade download-data \
    --config /freqtrade/config/config.json \
    --days 30 \
    --timeframes 5m 1h 1d

# 전략 테스트
docker-compose exec freqtrade freqtrade test-strategy \
    --strategy RSIStrategy \
    --config /freqtrade/config/config.json
```

### 3. 모니터링 스크립트

```bash
# 시스템 상태 확인
./monitor_freqtrade.sh

# 실시간 통계
curl http://localhost:8080/api/v1/status | jq '.'
```

## 🔗 기존 시스템과의 통합

### PM2 통합

```bash
# PM2로 Freqtrade 관리
pm2 start freqtrade_pm2.js

# 전체 시스템 상태 확인
pm2 status

# 통합 로그 확인
pm2 logs
```

### Nginx 통합

기존 crypto-trader Nginx 설정에 자동으로 통합:

```nginx
# /freqtrade/ 경로로 접속 가능
location /freqtrade/ {
    proxy_pass http://localhost:8081/;
    # ... proxy 설정
}
```

## 📈 백테스팅 및 최적화

### 1. 기본 백테스팅

```bash
# 최근 30일 데이터로 백테스팅
docker-compose exec freqtrade freqtrade backtesting \
    --config /freqtrade/config/config.json \
    --strategy RSIStrategy \
    --timerange 20241122-20241222 \
    --enable-protections
```

### 2. 하이퍼옵트 최적화

```bash
# RSI 파라미터 최적화
docker-compose exec freqtrade freqtrade hyperopt \
    --config /freqtrade/config/config.json \
    --hyperopt-loss SharpeHyperOptLoss \
    --strategy RSIStrategy \
    --epochs 100
```

### 3. 성과 분석

```bash
# 백테스팅 결과 분석
docker-compose exec freqtrade freqtrade plot-dataframe \
    --config /freqtrade/config/config.json \
    --strategy RSIStrategy \
    --export-filename user_data/plot.html
```

## 🛡️ 보안 및 주의사항

### 1. API 키 보안

```bash
# 설정 파일 권한 확인
ls -la config/config.json    # 600 권한 유지

# API 키 백업
cp config/config.json config/config.json.backup
```

### 2. 리스크 관리

- **Dry-run 모드 유지**: 충분한 검증 후 실거래 전환
- **소액 테스트**: 실거래 시 소액으로 시작
- **정기 모니터링**: 일일 성과 및 시스템 상태 확인
- **비상 정지**: 예상치 못한 손실 시 즉시 중지

### 3. 시스템 안정성

```bash
# 정기 백업
tar -czf freqtrade_backup_$(date +%Y%m%d).tar.gz \
    config/ user_data/ logs/

# 로그 로테이션
find logs/ -name "*.log" -size +100M -delete

# 리소스 모니터링
docker stats
```

## 🚨 문제 해결

### 1. 일반적인 문제

**컨테이너 시작 실패**
```bash
# 로그 확인
docker-compose logs

# 포트 충돌 확인
ss -tlnp | grep -E ':(8080|8081)'

# 컨테이너 재시작
docker-compose down && docker-compose up -d
```

**API 연결 실패**
```bash
# 네트워크 확인
ping api.binance.com

# 설정 파일 검증
docker-compose exec freqtrade freqtrade show_config

# API 키 재설정
./setup_api_keys.sh
```

### 2. 성능 문제

**메모리 부족**
```bash
# 메모리 사용량 확인
free -h

# 컨테이너 리소스 제한
# docker-compose.yml에 memory 제한 추가
```

**디스크 공간 부족**
```bash
# 디스크 사용량 확인
df -h

# 오래된 로그 정리
find logs/ -name "*.log" -mtime +7 -delete

# 백테스팅 결과 정리
find user_data/backtest_results/ -mtime +30 -delete
```

## 📞 지원 및 문의

### GitHub Repository
- **메인 프로젝트**: https://github.com/jilee1212/crypto-trader-pro
- **Issues**: 버그 리포트 및 기능 요청

### 문서
- **Freqtrade 공식 문서**: https://www.freqtrade.io/
- **Binance API 문서**: https://binance-docs.github.io/

---

**⚠️ 면책 조항**: 이 소프트웨어는 교육 및 연구 목적으로 제작되었습니다. 암호화폐 거래는 높은 위험을 수반하며, 투자 손실에 대한 책임은 사용자에게 있습니다.