# 🚀 Vultr 배포 가이드 - Crypto Trader Pro

## 📋 배포 전 준비사항

### 1. Vultr 서버 스펙
```
- OS: Ubuntu 24.04 LTS x64
- Plan: Regular Performance (1 CPU, 1GB RAM, 32GB SSD)
- 추천 위치: Seoul (가장 낮은 지연시간)
- IPv4: 활성화 필요
```

### 2. 도메인 설정 (선택사항)
```
- 도메인: nosignup.kr
- A 레코드: @ → [서버 IP]
- A 레코드: www → [서버 IP]
- TTL: 300초 (빠른 전파)
```

## 🛠️ 배포 단계

### 1단계: 서버 접속
```bash
# SSH로 서버 접속
ssh root@[서버IP]

# 사용자 생성 (보안상 권장)
adduser crypto
usermod -aG sudo crypto
su - crypto
```

### 2단계: 자동 배포 스크립트 실행
```bash
# 배포 스크립트 다운로드
wget https://raw.githubusercontent.com/jilee1212/crypto-trader-pro/main/vultr_deploy.sh

# 실행 권한 부여
chmod +x vultr_deploy.sh

# 배포 실행
./vultr_deploy.sh
```

### 3단계: 배포 확인
```bash
# PM2 상태 확인
pm2 status

# 로그 확인
pm2 logs

# Nginx 상태 확인
sudo systemctl status nginx

# 포트 확인
sudo netstat -tlnp | grep :8501
```

## 🌐 접속 확인

### 웹 인터페이스
- **로컬**: http://localhost:8501
- **도메인**: http://nosignup.kr
- **IP**: http://[서버IP]

### 시스템 상태
```bash
# PM2 대시보드
pm2 monit

# 시스템 리소스
htop

# 디스크 사용량
df -h
```

## 🔧 운영 관리

### PM2 명령어
```bash
# 전체 재시작
pm2 restart all

# 특정 앱 재시작
pm2 restart crypto-trader-web
pm2 restart crypto-trader-bot
pm2 restart crypto-trader-backup

# 로그 실시간 확인
pm2 logs --lines 50

# 앱 중지/시작
pm2 stop all
pm2 start all
```

### 업데이트 배포
```bash
cd /opt/crypto-trader/crypto-trader-pro

# 최신 코드 가져오기
git pull origin main

# 의존성 업데이트
source crypto_env/bin/activate
pip install --upgrade -r requirements.txt

# 서비스 재시작
pm2 restart all
```

### 백업 관리
```bash
# 수동 백업 실행
cd /opt/crypto-trader/crypto-trader-pro
source crypto_env/bin/activate
python backup_scheduler.py --manual

# 백업 파일 확인
ls -la backups/

# 백업 복원
python backup/recovery_manager.py --restore latest
```

## 📊 모니터링

### 시스템 모니터링
```bash
# CPU/메모리 사용률
htop

# 디스크 사용률
df -h

# 네트워크 상태
ss -tlnp

# 프로세스 확인
ps aux | grep streamlit
ps aux | grep python
```

### 로그 모니터링
```bash
# 웹 서버 로그
pm2 logs crypto-trader-web

# 거래 봇 로그
pm2 logs crypto-trader-bot

# 백업 서비스 로그
pm2 logs crypto-trader-backup

# Nginx 로그
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## 🔒 보안 설정

### 방화벽 확인
```bash
# UFW 상태
sudo ufw status

# 열린 포트 확인
sudo netstat -tlnp
```

### SSL 인증서 설치 (선택사항)
```bash
# Certbot 설치
sudo apt install certbot python3-certbot-nginx

# SSL 인증서 발급
sudo certbot --nginx -d nosignup.kr -d www.nosignup.kr

# 자동 갱신 설정
sudo systemctl enable certbot.timer
```

### API 키 보안
```bash
# 암호화 키 파일 권한 확인
ls -la database/encryption.key
chmod 600 database/encryption.key

# 데이터베이스 권한 확인
ls -la crypto_trading.db
chmod 600 crypto_trading.db
```

## 🚨 문제 해결

### 일반적인 문제들

#### 1. Streamlit 시작 실패
```bash
# 포트 충돌 확인
sudo lsof -i :8501

# 프로세스 종료
sudo pkill -f streamlit

# PM2 재시작
pm2 restart crypto-trader-web
```

#### 2. 데이터베이스 오류
```bash
# 데이터베이스 재초기화
cd /opt/crypto-trader/crypto-trader-pro
source crypto_env/bin/activate
python database/init_database.py --reset
```

#### 3. API 연결 실패
```bash
# 네트워크 연결 확인
ping api.binance.com

# 방화벽 설정 확인
sudo ufw status

# API 키 확인 (앱 내에서)
```

#### 4. Nginx 설정 오류
```bash
# 설정 파일 테스트
sudo nginx -t

# Nginx 재시작
sudo systemctl restart nginx

# 로그 확인
sudo tail -f /var/log/nginx/error.log
```

### 응급 복구
```bash
# PM2 프로세스 완전 재시작
pm2 kill
pm2 start ecosystem.config.js

# 시스템 재부팅
sudo reboot

# 백업에서 복원
cd /opt/crypto-trader/crypto-trader-pro
source crypto_env/bin/activate
python backup/recovery_manager.py --restore latest
```

## 📈 성능 최적화

### 시스템 최적화
```bash
# 메모리 사용량 확인
free -h

# PM2 메모리 제한 설정 (ecosystem.config.js)
max_memory_restart: '512M'  # 거래 봇용
max_memory_restart: '1G'    # 웹서버용
```

### 로그 관리
```bash
# PM2 로그 로테이션
pm2 install pm2-logrotate

# 로그 파일 정리
pm2 flush
```

## 🎯 운영 체크리스트

### 일일 점검
- [ ] PM2 상태 확인 (`pm2 status`)
- [ ] 웹사이트 접속 확인
- [ ] 시스템 리소스 확인 (`htop`)
- [ ] 로그 에러 확인 (`pm2 logs`)

### 주간 점검
- [ ] 시스템 업데이트 (`sudo apt update && sudo apt upgrade`)
- [ ] 백업 파일 확인
- [ ] 디스크 사용량 점검 (`df -h`)
- [ ] SSL 인증서 만료 확인

### 월간 점검
- [ ] 보안 업데이트 확인
- [ ] 성능 최적화 검토
- [ ] 백업 복원 테스트
- [ ] 의존성 패키지 업데이트

## 📞 지원 및 문의

### GitHub 이슈
- Repository: https://github.com/jilee1212/crypto-trader-pro
- Issues: 버그 리포트 및 기능 요청

### 문서
- README.md: 프로젝트 개요
- API 문서: 각 모듈별 상세 설명

---

**⚠️ 중요 알림**:
- 실거래 전 반드시 테스트넷에서 충분히 테스트하세요
- 정기적인 백업을 유지하세요
- 시스템 보안을 항상 최신으로 유지하세요