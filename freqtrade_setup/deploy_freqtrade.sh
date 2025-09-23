#!/bin/bash

# Freqtrade Docker 배포 스크립트
# Vultr Ubuntu 24.04 LTS 서버용

set -e

echo "🚀 Freqtrade Phase 5A 배포 시작..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 시스템 정보 확인
log_info "시스템 정보 확인 중..."
uname -a
df -h
free -h

# Docker 설치 확인 및 설치
log_info "Docker 설치 확인 중..."
if ! command -v docker &> /dev/null; then
    log_warn "Docker가 설치되지 않음. 설치 시작..."

    # Docker 공식 GPG 키 추가
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl gnupg lsb-release

    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    # Docker 리포지토리 추가
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Docker 설치
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

    # Docker 서비스 시작
    sudo systemctl start docker
    sudo systemctl enable docker

    # 현재 사용자를 docker 그룹에 추가
    sudo usermod -aG docker $USER

    log_info "Docker 설치 완료"
else
    log_info "Docker가 이미 설치되어 있음"
fi

# Docker Compose 설치 확인
log_info "Docker Compose 설치 확인 중..."
if ! command -v docker-compose &> /dev/null; then
    log_warn "Docker Compose가 설치되지 않음. 설치 시작..."

    sudo curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose

    log_info "Docker Compose 설치 완료"
else
    log_info "Docker Compose가 이미 설치되어 있음"
fi

# Freqtrade 디렉토리 생성
FREQTRADE_DIR="/opt/crypto-trader/freqtrade"
log_info "Freqtrade 디렉토리 생성: $FREQTRADE_DIR"

sudo mkdir -p $FREQTRADE_DIR
sudo chown -R $USER:$USER $FREQTRADE_DIR
cd $FREQTRADE_DIR

# 기존 설정 파일들 복사 (GitHub에서 가져오거나 로컬에서 업로드)
log_info "Freqtrade 설정 파일 복사 중..."

# 디렉토리 구조 생성
mkdir -p user_data/strategies user_data/data user_data/backtest_results config logs

# 프로젝트 저장소에서 Freqtrade 설정 가져오기
PROJECT_DIR="/opt/crypto-trader/crypto-trader-pro"
if [ -d "$PROJECT_DIR/freqtrade_setup" ]; then
    log_info "로컬 Freqtrade 설정을 복사 중..."
    cp -r $PROJECT_DIR/freqtrade_setup/* $FREQTRADE_DIR/
else
    log_warn "로컬 설정이 없음. 기본 설정으로 진행..."

    # 기본 docker-compose.yml 생성
    cat > docker-compose.yml << 'EOF'
---
version: '3.8'

services:
  freqtrade:
    image: freqtradeorg/freqtrade:stable
    restart: unless-stopped
    container_name: freqtrade_trader
    volumes:
      - "./user_data:/freqtrade/user_data"
      - "./config:/freqtrade/config"
      - "./logs:/freqtrade/logs"
    ports:
      - "8080:8080"
    command: >
      trade
      --logfile /freqtrade/logs/freqtrade.log
      --db-url sqlite:////freqtrade/user_data/tradesv3.sqlite
      --config /freqtrade/config/config.json
      --strategy RSIStrategy
    environment:
      - FREQTRADE_USER_DATA_DIR=/freqtrade/user_data
    networks:
      - freqtrade_network

  freqtrade_ui:
    image: freqtradeorg/freqtrade:stable
    restart: unless-stopped
    container_name: freqtrade_ui
    volumes:
      - "./user_data:/freqtrade/user_data"
      - "./config:/freqtrade/config"
      - "./logs:/freqtrade/logs"
    ports:
      - "8081:8080"
    command: >
      webserver
      --config /freqtrade/config/config.json
      --db-url sqlite:////freqtrade/user_data/tradesv3.sqlite
    depends_on:
      - freqtrade
    networks:
      - freqtrade_network

networks:
  freqtrade_network:
    driver: bridge

volumes:
  freqtrade_data:
  freqtrade_logs:
EOF
fi

# 권한 설정
log_info "파일 권한 설정 중..."
sudo chown -R $USER:$USER $FREQTRADE_DIR
find $FREQTRADE_DIR -type f -name "*.json" -exec chmod 600 {} \;
find $FREQTRADE_DIR -type f -name "*.py" -exec chmod 644 {} \;

# Docker 이미지 다운로드
log_info "Freqtrade Docker 이미지 다운로드 중..."
docker pull freqtradeorg/freqtrade:stable

# 초기 데이터 다운로드 (백테스팅용)
log_info "초기 데이터 다운로드 중..."
docker run --rm -v "$(pwd)/user_data:/freqtrade/user_data" -v "$(pwd)/config:/freqtrade/config" \
    freqtradeorg/freqtrade:stable download-data \
    --config /freqtrade/config/config.json \
    --days 30 \
    --timeframes 5m 1h 1d \
    --exchange binance

# 서비스 시작 (dry-run 모드)
log_info "Freqtrade 서비스 시작 중 (Dry-run 모드)..."
docker-compose up -d

# 서비스 상태 확인
sleep 10
log_info "서비스 상태 확인 중..."
docker-compose ps
docker-compose logs --tail=20

# PM2 integration을 위한 스크립트 생성
log_info "PM2 통합 스크립트 생성 중..."
cat > freqtrade_pm2.js << 'EOF'
module.exports = {
  apps: [
    {
      name: 'freqtrade-trader',
      script: 'docker-compose',
      args: 'up freqtrade',
      cwd: '/opt/crypto-trader/freqtrade',
      restart_delay: 10000,
      max_restarts: 5,
      exec_mode: 'fork',
      env: {
        NODE_ENV: 'production'
      }
    },
    {
      name: 'freqtrade-ui',
      script: 'docker-compose',
      args: 'up freqtrade_ui',
      cwd: '/opt/crypto-trader/freqtrade',
      restart_delay: 10000,
      max_restarts: 5,
      exec_mode: 'fork',
      env: {
        NODE_ENV: 'production'
      }
    }
  ]
};
EOF

# 방화벽 설정 업데이트
log_info "방화벽 설정 업데이트 중..."
sudo ufw allow 8080/tcp comment "Freqtrade API"
sudo ufw allow 8081/tcp comment "Freqtrade UI"
sudo ufw reload

# Nginx 설정 업데이트 (기존 crypto-trader와 통합)
log_info "Nginx 설정 업데이트 중..."
cat > /tmp/freqtrade.conf << 'EOF'
# Freqtrade API
location /freqtrade/api/ {
    proxy_pass http://localhost:8080/api/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_cache_bypass $http_upgrade;
}

# Freqtrade UI
location /freqtrade/ {
    proxy_pass http://localhost:8081/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_cache_bypass $http_upgrade;
}
EOF

if [ -f "/etc/nginx/sites-available/crypto-trader" ]; then
    # 기존 설정에 Freqtrade 설정 추가
    sudo cp /etc/nginx/sites-available/crypto-trader /etc/nginx/sites-available/crypto-trader.backup
    sudo sed -i '/location \/ {/i\\n    # Freqtrade 설정\n    include /etc/nginx/conf.d/freqtrade.conf;\n' /etc/nginx/sites-available/crypto-trader
    sudo cp /tmp/freqtrade.conf /etc/nginx/conf.d/freqtrade.conf
    sudo nginx -t && sudo systemctl reload nginx
    log_info "Nginx 설정 업데이트 완료"
else
    log_warn "기존 Nginx 설정이 없음. 수동으로 설정 필요"
fi

# 모니터링 스크립트 생성
log_info "모니터링 스크립트 생성 중..."
cat > monitor_freqtrade.sh << 'EOF'
#!/bin/bash

echo "=== Freqtrade 시스템 상태 ===="
echo "현재 시간: $(date)"
echo

echo "=== Docker 컨테이너 상태 ==="
docker-compose ps
echo

echo "=== 최근 로그 (마지막 20줄) ==="
docker-compose logs --tail=20
echo

echo "=== 시스템 리소스 ==="
echo "메모리 사용량:"
free -h
echo
echo "디스크 사용량:"
df -h
echo

echo "=== 네트워크 포트 상태 ==="
ss -tlnp | grep -E ':(8080|8081)'
echo

echo "=== Freqtrade 통계 ==="
curl -s http://localhost:8080/api/v1/status | jq '.'
EOF

chmod +x monitor_freqtrade.sh

log_info "✅ Freqtrade Phase 5A 배포 완료!"
log_info ""
log_info "📊 접속 정보:"
log_info "  - Freqtrade API: http://$(curl -s ifconfig.me):8080"
log_info "  - Freqtrade UI: http://$(curl -s ifconfig.me):8081"
log_info "  - 통합 UI: http://$(curl -s ifconfig.me)/freqtrade/"
log_info ""
log_info "🔧 관리 명령어:"
log_info "  - 상태 확인: docker-compose ps"
log_info "  - 로그 확인: docker-compose logs -f"
log_info "  - 재시작: docker-compose restart"
log_info "  - 중지: docker-compose down"
log_info ""
log_info "📈 모니터링:"
log_info "  - 실행: ./monitor_freqtrade.sh"
log_info ""
log_warn "⚠️  주의사항:"
log_warn "  - 현재 DRY-RUN 모드로 실행 중"
log_warn "  - API 키 설정이 필요함 (config/config.json)"
log_warn "  - 실거래 전 충분한 백테스팅 필요"