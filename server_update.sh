#!/bin/bash

# Vultr 서버 업데이트 스크립트
# 서버에서 직접 실행: bash server_update.sh

echo "🔄 Crypto Trader Pro 서버 업데이트 시작..."
echo "📅 업데이트 시간: $(date)"

# 프로젝트 디렉토리로 이동
cd /root/crypto-trader-pro || {
    echo "❌ 프로젝트 디렉토리를 찾을 수 없습니다: /root/crypto-trader-pro"
    exit 1
}

echo "📂 현재 디렉토리: $(pwd)"

# 기존 프로세스 정리
echo "⏹️ 기존 서비스 중지..."
pkill -f "uvicorn app.main:app" 2>/dev/null || echo "백엔드 프로세스 없음"
pkill -f "npm run" 2>/dev/null || echo "프론트엔드 프로세스 없음"
sleep 2

# 백업 생성 (선택사항)
echo "💾 현재 상태 백업..."
cp -r backend/app/api/v1/binance.py backend/app/api/v1/binance.py.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || echo "백업 건너뜀"

# Git 상태 확인 및 업데이트
echo "🔍 Git 상태 확인..."
git status --porcelain
if [ $? -ne 0 ]; then
    echo "❌ Git 저장소 오류"
    exit 1
fi

# 최신 변경사항 가져오기
echo "📥 최신 변경사항 가져오기..."
git fetch origin main
if [ $? -ne 0 ]; then
    echo "❌ Git fetch 실패"
    exit 1
fi

# 로컬 변경사항이 있으면 스태시
if [ -n "$(git status --porcelain)" ]; then
    echo "💾 로컬 변경사항 임시 저장..."
    git stash push -m "Auto-stash before update $(date)"
fi

# 메인 브랜치로 업데이트
echo "🔄 메인 브랜치로 업데이트..."
git pull origin main --rebase
if [ $? -ne 0 ]; then
    echo "❌ Git pull 실패"
    exit 1
fi

echo "✅ Git 업데이트 완료"

# 백엔드 업데이트
echo "🖥️ 백엔드 업데이트 시작..."
cd backend

# Python 가상환경 확인
if [ -d "venv" ]; then
    echo "🐍 가상환경 활성화..."
    source venv/bin/activate
else
    echo "⚠️ 가상환경이 없습니다. 시스템 Python 사용..."
fi

# 의존성 업데이트
echo "📦 Python 의존성 업데이트..."
pip install -r requirements.txt --upgrade

# 데이터베이스 마이그레이션 (필요시)
if [ -f "alembic.ini" ]; then
    echo "🗄️ 데이터베이스 마이그레이션 확인..."
    alembic upgrade head 2>/dev/null || echo "마이그레이션 건너뜀"
fi

# 백엔드 서버 시작
echo "🚀 백엔드 서버 시작..."
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "백엔드 PID: $BACKEND_PID"

cd ..

# 프론트엔드 업데이트
echo "📱 프론트엔드 업데이트 시작..."
cd frontend

# Node.js 의존성 업데이트
echo "📦 npm 의존성 업데이트..."
npm install

# 프로덕션 빌드
echo "🏗️ 프로덕션 빌드..."
npm run build
if [ $? -ne 0 ]; then
    echo "❌ 프론트엔드 빌드 실패"
    exit 1
fi

# 프론트엔드 서버 시작
echo "🚀 프론트엔드 서버 시작..."
nohup npm run preview -- --port 5173 --host 0.0.0.0 > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "프론트엔드 PID: $FRONTEND_PID"

cd ..

# 로그 디렉토리 생성
mkdir -p logs

# 서버 상태 확인
echo "⏱️ 서버 시작 대기 중..."
sleep 5

echo "📊 현재 실행 중인 프로세스:"
ps aux | grep -E "(uvicorn|npm)" | grep -v grep

# 서비스 상태 확인
echo "🔍 서비스 상태 확인..."
curl -s http://localhost:8000/docs > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ 백엔드 API 정상 작동"
else
    echo "⚠️ 백엔드 API 확인 필요"
fi

curl -s http://localhost:5173 > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ 프론트엔드 정상 작동"
else
    echo "⚠️ 프론트엔드 확인 필요"
fi

echo ""
echo "🎉 서버 업데이트 완료!"
echo ""
echo "🌐 접속 정보:"
echo "   프론트엔드: http://nosignup.kr:5173"
echo "   백엔드 API: http://nosignup.kr:8000"
echo "   API 문서: http://nosignup.kr:8000/docs"
echo ""
echo "📋 로그 확인:"
echo "   백엔드: tail -f /root/crypto-trader-pro/logs/backend.log"
echo "   프론트엔드: tail -f /root/crypto-trader-pro/logs/frontend.log"
echo ""
echo "📊 프로세스 관리:"
echo "   전체 프로세스: ps aux | grep -E '(uvicorn|npm)' | grep -v grep"
echo "   백엔드 중지: pkill -f 'uvicorn app.main:app'"
echo "   프론트엔드 중지: pkill -f 'npm run'"