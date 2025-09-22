# 🚀 Vultr 빠른 배포 가이드

## 📋 Vultr 서버 생성

### 1. Vultr 계정 생성 및 서버 주문
```
1. https://vultr.com 접속
2. 계정 생성 및 로그인
3. Deploy New Server 클릭
4. Server Type: Regular Performance
5. Server Size: $6/month (1 CPU, 1GB RAM, 32GB SSD)
6. Server Location: Seoul (낮은 지연시간)
7. Operating System: Ubuntu 24.04 LTS x64
8. Deploy Now 클릭
```

### 2. 서버 정보 확인
```
- IP 주소: 배포 후 확인
- Username: root
- Password: 자동 생성 (이메일 확인)
```

## 🔧 원클릭 배포 명령어

### SSH 접속
```bash
# Windows (PowerShell/Command Prompt)
ssh root@[서버IP주소]

# 비밀번호 입력 (이메일에서 확인)
```

### 자동 배포 실행
```bash
# 배포 스크립트 다운로드 및 실행
curl -fsSL https://raw.githubusercontent.com/jilee1212/crypto-trader-pro/main/vultr_deploy.sh | bash
```

## ⏱️ 배포 소요시간
- **전체 배포**: 약 5-10분
- **패키지 설치**: 2-3분
- **프로젝트 클론**: 1분
- **의존성 설치**: 2-3분
- **서비스 시작**: 1분

## 🌐 배포 완료 확인

### 웹사이트 접속
```
http://[서버IP주소]
또는
http://nosignup.kr (도메인 설정 시)
```

### 서비스 상태 확인
```bash
# PM2 상태 확인
pm2 status

# 로그 확인
pm2 logs

# Nginx 상태
sudo systemctl status nginx

# 포트 확인
sudo netstat -tlnp | grep :8501
```

## 🔄 서비스 관리 명령어

### PM2 명령어
```bash
# 모든 서비스 재시작
pm2 restart all

# 특정 서비스 재시작
pm2 restart crypto-trader-web

# 로그 실시간 확인
pm2 logs --lines 50

# 서비스 중지/시작
pm2 stop all
pm2 start all
```

### 업데이트 배포
```bash
cd /opt/crypto-trader/crypto-trader-pro
git pull origin main
pm2 restart all
```

## 🎯 첫 사용자 가이드

### 1. 웹사이트 접속
- http://[서버IP] 접속

### 2. 계정 생성
- 회원가입 버튼 클릭
- 사용자명, 이메일, 비밀번호 입력

### 3. API 키 설정
- 로그인 후 설정 탭 이동
- Binance 테스트넷 API 키 입력

### 4. 거래 시작
- 대시보드에서 실시간 데이터 확인
- AI 신호 생성 및 거래 실행

## 🔒 보안 설정 (선택사항)

### 도메인 연결
```bash
# /etc/nginx/sites-available/crypto-trader 수정
sudo nano /etc/nginx/sites-available/crypto-trader

# server_name 변경
server_name your-domain.com www.your-domain.com;

# Nginx 재시작
sudo systemctl reload nginx
```

### SSL 인증서 설치
```bash
# Certbot 설치
sudo apt install certbot python3-certbot-nginx

# SSL 인증서 발급
sudo certbot --nginx -d your-domain.com

# 자동 갱신 설정
sudo systemctl enable certbot.timer
```

## 🚨 문제 해결

### 일반적인 문제
```bash
# 1. 서비스가 시작되지 않는 경우
pm2 kill
pm2 start ecosystem.config.js

# 2. 포트 충돌
sudo lsof -i :8501
sudo pkill -f streamlit

# 3. Nginx 오류
sudo nginx -t
sudo systemctl restart nginx

# 4. 데이터베이스 오류
cd /opt/crypto-trader/crypto-trader-pro
python database/init_database.py --reset
```

### 로그 확인
```bash
# 애플리케이션 로그
pm2 logs crypto-trader-web

# Nginx 로그
sudo tail -f /var/log/nginx/error.log

# 시스템 로그
sudo journalctl -f
```

## 📊 모니터링

### 시스템 리소스
```bash
# CPU/메모리 사용률
htop

# 디스크 사용률
df -h

# 네트워크 상태
ss -tlnp
```

### 성능 최적화
```bash
# PM2 모니터링
pm2 monit

# 메모리 정리
pm2 restart all
```

## 🎉 배포 성공!

✅ **웹사이트**: http://[서버IP]
✅ **24/7 운영**: PM2 자동 관리
✅ **자동 백업**: 일일 데이터베이스 백업
✅ **보안**: 방화벽 + API 키 암호화
✅ **모니터링**: 실시간 로그 및 상태

---

**🔥 Crypto Trader Pro가 성공적으로 배포되었습니다!**

**지원**: GitHub Issues - https://github.com/jilee1212/crypto-trader-pro/issues