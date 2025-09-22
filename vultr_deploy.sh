#!/bin/bash

# Crypto Trader Pro - Vultr 배포 스크립트
# 2025년 1월 업데이트 - python-binance 표준 패턴 적용

echo "🚀 Crypto Trader Pro - Vultr 배포 시작"
echo "======================================"

# 1. 시스템 업데이트
echo "📦 시스템 패키지 업데이트..."
sudo apt update && sudo apt upgrade -y

# 2. Python 3.12 설치
echo "🐍 Python 3.12 설치..."
sudo apt install -y python3.12 python3.12-venv python3.12-dev python3-pip

# 3. Node.js 및 PM2 설치
echo "📦 Node.js 및 PM2 설치..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pm2

# 4. Nginx 설치 및 설정
echo "🌐 Nginx 설치..."
sudo apt install -y nginx

# 5. 프로젝트 디렉토리 생성
echo "📁 프로젝트 디렉토리 설정..."
sudo mkdir -p /opt/crypto-trader
sudo chown -R $USER:$USER /opt/crypto-trader
cd /opt/crypto-trader

# 6. GitHub에서 프로젝트 클론
echo "📂 GitHub에서 프로젝트 클론..."
if [ -d "crypto-trader-pro" ]; then
    echo "기존 프로젝트 업데이트..."
    cd crypto-trader-pro
    git pull origin main
else
    echo "새 프로젝트 클론..."
    git clone https://github.com/jilee1212/crypto-trader-pro.git
    cd crypto-trader-pro
fi

# 7. Python 가상환경 생성
echo "🔧 Python 가상환경 설정..."
python3.12 -m venv crypto_env
source crypto_env/bin/activate

# 8. Python 의존성 설치
echo "📦 Python 패키지 설치..."
pip install --upgrade pip
pip install streamlit==1.40.0
pip install pandas plotly ccxt requests numpy
pip install sqlalchemy bcrypt PyJWT cryptography
pip install python-binance==1.0.29
pip install yfinance

# 9. 데이터베이스 초기화
echo "💾 데이터베이스 초기화..."
python database/init_database.py --reset

# 10. Nginx 설정
echo "🌐 Nginx 설정 생성..."
sudo tee /etc/nginx/sites-available/crypto-trader > /dev/null <<EOF
server {
    listen 80;
    server_name nosignup.kr www.nosignup.kr;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 86400;
    }

    # WebSocket 지원
    location /_stcore/stream {
        proxy_pass http://localhost:8501/_stcore/stream;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# 11. Nginx 활성화
echo "🔗 Nginx 사이트 활성화..."
sudo ln -sf /etc/nginx/sites-available/crypto-trader /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# 12. PM2 ecosystem 파일 생성
echo "⚙️ PM2 설정 파일 생성..."
tee ecosystem.config.js > /dev/null <<EOF
module.exports = {
  apps: [
    {
      name: 'crypto-trader-web',
      script: 'crypto_env/bin/streamlit',
      args: 'run main_platform.py --server.port=8501 --server.address=0.0.0.0',
      cwd: '/opt/crypto-trader/crypto-trader-pro',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production'
      },
      error_file: './logs/web-error.log',
      out_file: './logs/web-out.log',
      log_file: './logs/web-combined.log'
    },
    {
      name: 'crypto-trader-bot',
      script: 'crypto_env/bin/python',
      args: 'trading_engine/background_trader.py',
      cwd: '/opt/crypto-trader/crypto-trader-pro',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      env: {
        NODE_ENV: 'production'
      },
      error_file: './logs/bot-error.log',
      out_file: './logs/bot-out.log',
      log_file: './logs/bot-combined.log'
    },
    {
      name: 'crypto-trader-backup',
      script: 'crypto_env/bin/python',
      args: 'backup_scheduler.py',
      cwd: '/opt/crypto-trader/crypto-trader-pro',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '256M',
      env: {
        NODE_ENV: 'production'
      },
      error_file: './logs/backup-error.log',
      out_file: './logs/backup-out.log',
      log_file: './logs/backup-combined.log'
    }
  ]
};
EOF

# 13. 로그 디렉토리 생성
echo "📝 로그 디렉토리 생성..."
mkdir -p logs

# 14. PM2로 애플리케이션 시작
echo "🚀 PM2로 애플리케이션 시작..."
pm2 start ecosystem.config.js
pm2 save
pm2 startup

# 15. 방화벽 설정
echo "🔒 방화벽 설정..."
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw --force enable

# 16. 배포 완료 메시지
echo ""
echo "✅ 배포 완료!"
echo "=================="
echo "🌐 웹사이트: http://nosignup.kr"
echo "📊 PM2 상태: pm2 status"
echo "📝 로그 확인: pm2 logs"
echo ""
echo "🔧 주요 명령어:"
echo "  - pm2 restart all    # 모든 프로세스 재시작"
echo "  - pm2 stop all       # 모든 프로세스 중지"
echo "  - pm2 logs           # 실시간 로그 확인"
echo "  - sudo systemctl reload nginx  # Nginx 재시작"
echo ""
echo "📍 프로젝트 경로: /opt/crypto-trader/crypto-trader-pro"
echo "🔑 데이터베이스: crypto_trading.db (SQLite)"
echo ""
echo "⚠️  보안 알림:"
echo "  - API 키는 테스트넷으로 시작하세요"
echo "  - 정기적으로 백업을 확인하세요"
echo "  - 시스템 업데이트를 유지하세요"
echo ""
echo "🎉 Crypto Trader Pro가 성공적으로 배포되었습니다!"