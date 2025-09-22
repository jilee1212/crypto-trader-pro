#!/bin/bash

# Vultr 서버 업데이트 스크립트
# 서버: 141.164.42.93
# 사용자: linuxuser

echo "🔄 Crypto Trader Pro - 서버 업데이트 시작"
echo "서버: 141.164.42.93"
echo "======================================"

# 1. 현재 디렉토리 확인
echo "📁 프로젝트 디렉토리 확인..."
if [ -d "/home/linuxuser/crypto-trader-pro" ]; then
    cd /home/linuxuser/crypto-trader-pro
    echo "✅ 기존 프로젝트 디렉토리 사용: $(pwd)"
elif [ -d "/opt/crypto-trader/crypto-trader-pro" ]; then
    cd /opt/crypto-trader/crypto-trader-pro
    echo "✅ 기존 프로젝트 디렉토리 사용: $(pwd)"
else
    echo "❌ 프로젝트 디렉토리를 찾을 수 없습니다."
    echo "프로젝트를 새로 클론합니다..."
    cd /home/linuxuser
    git clone https://github.com/jilee1212/crypto-trader-pro.git
    cd crypto-trader-pro
fi

# 2. PM2 프로세스 중지
echo "⏸️ 기존 서비스 중지..."
if command -v pm2 >/dev/null 2>&1; then
    pm2 stop all 2>/dev/null || echo "PM2 프로세스가 실행 중이 아닙니다."
else
    echo "PM2가 설치되지 않음 - 스킵"
fi

# 3. 백업 생성
echo "💾 데이터베이스 백업..."
if [ -f "crypto_trader.db" ]; then
    cp crypto_trader.db crypto_trader.db.backup_$(date +%Y%m%d_%H%M%S)
    echo "✅ 데이터베이스 백업 완료"
fi

# 4. 최신 코드 가져오기
echo "📥 최신 코드 가져오기..."
git stash push -m "Auto stash before update"
git pull origin main

if [ $? -eq 0 ]; then
    echo "✅ 코드 업데이트 성공"
else
    echo "❌ 코드 업데이트 실패"
    exit 1
fi

# 5. Python 환경 확인 및 의존성 설치
echo "🐍 Python 환경 설정..."
if [ -d "crypto_env" ]; then
    source crypto_env/bin/activate
    echo "✅ 기존 가상환경 활성화"
else
    python3 -m venv crypto_env
    source crypto_env/bin/activate
    echo "✅ 새 가상환경 생성"
fi

# 6. 의존성 업데이트
echo "📦 의존성 업데이트..."
pip install --upgrade pip
pip install --upgrade -r requirements.txt

# 7. 데이터베이스 마이그레이션
echo "🗄️ 데이터베이스 마이그레이션..."
if [ -f "database/migration_script.py" ]; then
    python database/migration_script.py
    echo "✅ 데이터베이스 마이그레이션 완료"
fi

# 8. 권한 설정
echo "🔐 권한 설정..."
chmod +x vultr_deploy.sh 2>/dev/null || echo "vultr_deploy.sh 없음 - 스킵"

# 9. PM2 재시작
echo "🚀 서비스 재시작..."
if command -v pm2 >/dev/null 2>&1; then
    if [ -f "ecosystem.config.js" ]; then
        pm2 start ecosystem.config.js
    else
        # 기본 Streamlit 실행
        pm2 start "streamlit run main_platform.py --server.port=8501 --server.address=0.0.0.0" --name "crypto-trader"
    fi
    pm2 save
    echo "✅ PM2 서비스 재시작 완료"
else
    # PM2가 없으면 백그라운드 실행
    nohup streamlit run main_platform.py --server.port=8501 --server.address=0.0.0.0 > streamlit.log 2>&1 &
    echo "✅ Streamlit 백그라운드 실행"
fi

# 10. 상태 확인
echo "📊 서비스 상태 확인..."
if command -v pm2 >/dev/null 2>&1; then
    pm2 status
else
    ps aux | grep streamlit | grep -v grep
fi

# 11. 포트 확인
echo "🌐 포트 확인..."
ss -tlnp | grep :8501 || netstat -tlnp | grep :8501

echo ""
echo "✅ 업데이트 완료!"
echo "=================="
echo "🌐 웹사이트: http://141.164.42.93:8501"
echo "📊 상태 확인: pm2 status"
echo "📝 로그 확인: pm2 logs"
echo ""
echo "🎉 Crypto Trader Pro 업데이트가 완료되었습니다!"