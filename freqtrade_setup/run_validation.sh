#!/bin/bash

# Complete AI Model Validation and Performance Testing Script
# Validates AI model porting and compares strategy performance

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

echo "🔍 AI Model Validation & Performance Testing"
echo "=============================================="

# 기본 설정
SYMBOL=${1:-"BTC/USDT"}
TIMEFRAME=${2:-"5m"}
VALIDATION_DAYS=${3:-30}
BACKTEST_TIMERANGE=${4:-"20241201-20241222"}

log_info "Configuration:"
log_info "  Symbol: $SYMBOL"
log_info "  Timeframe: $TIMEFRAME"
log_info "  Validation Days: $VALIDATION_DAYS"
log_info "  Backtest Timerange: $BACKTEST_TIMERANGE"
echo

# 1. 환경 확인
log_step "1. Environment Check"

# Docker 실행 확인
if ! command -v docker-compose &> /dev/null; then
    log_error "docker-compose not found. Please install Docker Compose."
    exit 1
fi

# Freqtrade 컨테이너 확인
if ! docker-compose ps | grep -q "freqtrade"; then
    log_warn "Freqtrade containers not running. Starting them..."
    docker-compose up -d
    sleep 10
fi

# Python 환경 확인
if ! python3 -c "import pandas, numpy, sklearn, ccxt, talib" 2>/dev/null; then
    log_error "Required Python packages not available."
    log_info "Please install: pip install pandas numpy scikit-learn ccxt TA-Lib"
    exit 1
fi

log_info "✅ Environment check passed"
echo

# 2. AI 모델 훈련 (필요한 경우)
log_step "2. AI Model Training"

if [ ! -f "user_data/models/signal_model.pkl" ]; then
    log_info "AI models not found. Training new models..."

    python3 train_ai_models.py \
        --symbol "$SYMBOL" \
        --timeframe "$TIMEFRAME" \
        --days 90 \
        --exchange binance \
        --sandbox

    if [ $? -eq 0 ]; then
        log_info "✅ AI model training completed"
    else
        log_error "❌ AI model training failed"
        exit 1
    fi
else
    log_info "✅ AI models already exist"
fi
echo

# 3. 모델 성능 검증
log_step "3. AI Model Performance Validation"

log_info "Running performance validation..."
python3 performance_validator.py \
    --symbol "$SYMBOL" \
    --timeframe "$TIMEFRAME" \
    --days "$VALIDATION_DAYS"

if [ $? -eq 0 ]; then
    log_info "✅ Performance validation completed"
else
    log_warn "⚠️  Performance validation had issues (continuing...)"
fi
echo

# 4. 백테스팅 비교
log_step "4. Strategy Backtest Comparison"

log_info "Running backtest comparison..."
python3 backtest_comparison.py \
    --timerange "$BACKTEST_TIMERANGE" \
    --days 60

if [ $? -eq 0 ]; then
    log_info "✅ Backtest comparison completed"
else
    log_warn "⚠️  Backtest comparison had issues (continuing...)"
fi
echo

# 5. 시스템 상태 확인
log_step "5. System Status Check"

log_info "=== Docker Container Status ==="
docker-compose ps

log_info "=== Port Status ==="
ss -tlnp | grep -E ':(8080|8081)' || true

log_info "=== Disk Usage ==="
du -sh user_data/ logs/ 2>/dev/null || true

echo

# 6. 결과 요약
log_step "6. Results Summary"

echo
log_info "=== VALIDATION RESULTS ==="

# 검증 결과 파일 확인
LATEST_VALIDATION=$(ls -t user_data/validation_results/validation_metrics_*.json 2>/dev/null | head -n 1)
if [ -n "$LATEST_VALIDATION" ]; then
    log_info "📊 Latest validation results: $LATEST_VALIDATION"

    # JSON 파일에서 주요 메트릭 추출 (jq가 있는 경우)
    if command -v jq &> /dev/null; then
        echo
        log_info "🤖 Original AI System:"
        jq -r '.original_ai | "  Signal Accuracy: \(.signal_accuracy | tostring), Total Signals: \(.total_signals | tostring), Avg Confidence: \(.avg_confidence | tostring)"' "$LATEST_VALIDATION" 2>/dev/null || echo "  Data extraction failed"

        log_info "🚀 Freqtrade AI System:"
        jq -r '.freqtrade_ai | "  Signal Accuracy: \(.signal_accuracy | tostring), Total Signals: \(.total_signals | tostring), Avg Confidence: \(.avg_confidence | tostring)"' "$LATEST_VALIDATION" 2>/dev/null || echo "  Data extraction failed"

        log_info "🔄 System Comparison:"
        jq -r '.comparison | "  Overall Agreement: \(.overall_agreement | tostring), Buy Agreement: \(.buy_signal_agreement | tostring), Sell Agreement: \(.sell_signal_agreement | tostring)"' "$LATEST_VALIDATION" 2>/dev/null || echo "  Data extraction failed"
    fi
else
    log_warn "No validation results found"
fi

# 백테스팅 결과 파일 확인
LATEST_BACKTEST=$(ls -t user_data/comparison_results/backtest_comparison_*.json 2>/dev/null | head -n 1)
if [ -n "$LATEST_BACKTEST" ]; then
    log_info "📈 Latest backtest comparison: $LATEST_BACKTEST"

    if command -v jq &> /dev/null; then
        echo
        log_info "📊 Strategy Performance:"
        jq -r 'to_entries[] | "  \(.key): \(.value.total_return_pct // 0)% return, \(.value.winrate // 0)% winrate"' "$LATEST_BACKTEST" 2>/dev/null || echo "  Data extraction failed"
    fi
else
    log_warn "No backtest comparison results found"
fi

echo

# 7. 다음 단계 안내
log_step "7. Next Steps"

echo
log_info "🎯 RECOMMENDED ACTIONS:"
echo

echo "📊 Review Results:"
echo "  1. Check validation_results/ for detailed AI model comparison"
echo "  2. Check comparison_results/ for strategy backtest analysis"
echo "  3. Review logs/ for any errors or warnings"
echo

echo "🔧 If Results Look Good:"
echo "  1. Run longer backtesting periods (3-6 months)"
echo "  2. Test with different market conditions"
echo "  3. Consider paper trading (dry-run) for real-time validation"
echo "  4. Optimize strategy parameters with hyperopt"
echo

echo "⚠️  If Issues Found:"
echo "  1. Review AITradingStrategy.py for potential bugs"
echo "  2. Retrain models with more data"
echo "  3. Adjust confidence thresholds"
echo "  4. Compare with original ai_trading_signals.py behavior"
echo

echo "🚀 Production Readiness:"
echo "  1. Run 30+ days of paper trading"
echo "  2. Monitor signal accuracy in real-time"
echo "  3. Set up alerts for system health"
echo "  4. Create backup and recovery procedures"
echo

# 최종 상태
if [ -f "user_data/models/signal_model.pkl" ] && [ -n "$LATEST_VALIDATION" ]; then
    log_info "🎉 AI Model Validation Pipeline Completed Successfully!"
    log_info "Your AI trading strategy is ready for extended testing."
else
    log_warn "⚠️  Validation pipeline completed with some issues."
    log_info "Please review the output above and address any problems."
fi

echo
log_info "📁 All results saved in:"
log_info "  - user_data/validation_results/ (model validation)"
log_info "  - user_data/comparison_results/ (strategy comparison)"
log_info "  - user_data/backtest_results/ (individual backtests)"

echo
log_info "🌐 Web Interfaces:"
log_info "  - Freqtrade UI: http://localhost:8081"
log_info "  - Freqtrade API: http://localhost:8080"
log_info "  - API Docs: http://localhost:8080/docs"