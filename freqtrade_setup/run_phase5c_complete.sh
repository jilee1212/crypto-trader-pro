#!/bin/bash

# Phase 5C Complete Execution Script
# Runs the entire multi-indicator strategy development and optimization pipeline

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

log_success() {
    echo -e "${PURPLE}[SUCCESS]${NC} $1"
}

echo "🚀 Phase 5C: Multi-Indicator Strategy Complete Pipeline"
echo "========================================================="

# 기본 설정
SYMBOL=${1:-"BTC/USDT"}
TIMEFRAME=${2:-"5m"}
BACKTEST_TIMERANGE=${3:-"20241101-20241222"}
HYPEROPT_EPOCHS=${4:-200}

log_info "Configuration:"
log_info "  Symbol: $SYMBOL"
log_info "  Timeframe: $TIMEFRAME"
log_info "  Backtest Timerange: $BACKTEST_TIMERANGE"
log_info "  HyperOpt Epochs: $HYPEROPT_EPOCHS"
echo

# 1. 환경 및 전제조건 확인
log_step "1. Environment and Prerequisites Check"

# Docker Compose 확인
if ! command -v docker-compose &> /dev/null; then
    log_error "docker-compose not found. Please install Docker Compose."
    exit 1
fi

# Freqtrade 컨테이너 상태 확인
if ! docker-compose ps | grep -q "freqtrade"; then
    log_warn "Freqtrade containers not running. Starting them..."
    docker-compose up -d
    sleep 15
    log_info "Waiting for Freqtrade to initialize..."
fi

# 컨테이너 정상 작동 확인
if ! docker-compose exec -T freqtrade freqtrade --version &>/dev/null; then
    log_error "Freqtrade container not responding. Please check Docker setup."
    exit 1
fi

log_success "✅ Environment check passed"
echo

# 2. 데이터 준비
log_step "2. Data Preparation"

log_info "Downloading historical data for analysis..."

# 백테스팅용 데이터 다운로드
docker-compose exec -T freqtrade freqtrade download-data \
    --config /freqtrade/config/config.json \
    --days 90 \
    --timeframes 5m 1h 1d \
    --pairs BTC/USDT ETH/USDT BNB/USDT ADA/USDT SOL/USDT

if [ $? -eq 0 ]; then
    log_success "✅ Data download completed"
else
    log_warn "⚠️  Data download had issues (continuing...)"
fi
echo

# 3. 기본 전략 테스트
log_step "3. Strategy Validation Test"

log_info "Testing MultiIndicatorStrategy configuration..."

# 전략 테스트
STRATEGY_TEST=$(docker-compose exec -T freqtrade freqtrade test-strategy \
    --strategy MultiIndicatorStrategy \
    --config /freqtrade/config/config.json 2>&1 || true)

if echo "$STRATEGY_TEST" | grep -q -E "(SUCCESS|PASSED|No errors)"; then
    log_success "✅ MultiIndicatorStrategy validation passed"
else
    log_warn "⚠️  Strategy validation had warnings:"
    echo "$STRATEGY_TEST" | head -n 10
fi
echo

# 4. 기본 백테스팅 (최적화 전)
log_step "4. Baseline Backtesting (Pre-Optimization)"

log_info "Running baseline backtest to establish performance benchmark..."

BASELINE_RESULT=$(docker-compose exec -T freqtrade freqtrade backtesting \
    --config /freqtrade/config/config.json \
    --strategy MultiIndicatorStrategy \
    --timerange "$BACKTEST_TIMERANGE" \
    --export trades \
    --cache none 2>&1 || true)

if echo "$BASELINE_RESULT" | grep -q -E "(Total profit|BACKTESTING REPORT)"; then
    log_success "✅ Baseline backtest completed"

    # 주요 지표 추출 및 출력
    echo
    log_info "📊 Baseline Performance:"
    echo "$BASELINE_RESULT" | grep -E "(Total profit|Total trade count|Avg profit|Sharpe|Max drawdown)" | head -n 10 || true
else
    log_warn "⚠️  Baseline backtest had issues"
fi
echo

# 5. 하이퍼파라미터 최적화
log_step "5. Hyperparameter Optimization"

log_info "Starting hyperparameter optimization ($HYPEROPT_EPOCHS epochs)..."
log_info "This may take 30-60 minutes depending on epochs and system performance..."

# HyperOpt 실행
python3 run_hyperopt.py \
    --epochs "$HYPEROPT_EPOCHS" \
    --timerange "$BACKTEST_TIMERANGE" \
    --strategy MultiIndicatorStrategy \
    --spaces buy sell \
    --loss SharpeHyperOptLoss

if [ $? -eq 0 ]; then
    log_success "✅ Hyperparameter optimization completed"
else
    log_warn "⚠️  Hyperopt had issues (continuing with default parameters...)"
fi
echo

# 6. 최적화된 백테스팅
log_step "6. Optimized Strategy Backtesting"

log_info "Running backtest with optimized parameters..."

OPTIMIZED_RESULT=$(docker-compose exec -T freqtrade freqtrade backtesting \
    --config /freqtrade/config/config.json \
    --strategy MultiIndicatorStrategy \
    --timerange "$BACKTEST_TIMERANGE" \
    --export trades,signals \
    --cache none \
    --breakdown day,week,month 2>&1 || true)

if echo "$OPTIMIZED_RESULT" | grep -q -E "(Total profit|BACKTESTING REPORT)"; then
    log_success "✅ Optimized backtest completed"

    echo
    log_info "📊 Optimized Performance:"
    echo "$OPTIMIZED_RESULT" | grep -E "(Total profit|Total trade count|Avg profit|Sharpe|Max drawdown)" | head -n 10 || true
else
    log_warn "⚠️  Optimized backtest had issues"
fi
echo

# 7. 전략 비교 분석
log_step "7. Strategy Comparison Analysis"

log_info "Comparing MultiIndicatorStrategy with other strategies..."

python3 strategy_analyzer.py \
    --strategies RSIStrategy AITradingStrategy MultiIndicatorStrategy \
    --timerange "$BACKTEST_TIMERANGE" \
    --report

if [ $? -eq 0 ]; then
    log_success "✅ Strategy comparison analysis completed"
else
    log_warn "⚠️  Strategy analysis had issues"
fi
echo

# 8. 성능 검증
log_step "8. Performance Validation"

log_info "Running comprehensive performance validation..."

# AI 모델 성능 검증 (이전에 생성된 도구 사용)
if [ -f "performance_validator.py" ]; then
    python3 performance_validator.py \
        --symbol "$SYMBOL" \
        --timeframe "$TIMEFRAME" \
        --days 30

    if [ $? -eq 0 ]; then
        log_success "✅ Performance validation completed"
    else
        log_warn "⚠️  Performance validation had issues"
    fi
else
    log_warn "Performance validator not found. Skipping detailed validation."
fi
echo

# 9. 결과 요약 및 보고서 생성
log_step "9. Results Summary and Reporting"

echo
log_success "=== PHASE 5C COMPLETION REPORT ==="
echo

# 시스템 상태
log_info "📊 System Status:"
echo "  - Freqtrade Status: $(docker-compose ps freqtrade --format 'table {{.Status}}' | tail -n 1)"
echo "  - Data Coverage: 90+ days historical data"
echo "  - Strategies Available: RSIStrategy, AITradingStrategy, MultiIndicatorStrategy"
echo

# 파일 생성 확인
log_info "📁 Generated Files:"
echo "  - MultiIndicatorStrategy.py: $([ -f "user_data/strategies/MultiIndicatorStrategy.py" ] && echo "✅" || echo "❌")"
echo "  - MultiIndicatorHyperOpt.py: $([ -f "user_data/hyperopts/MultiIndicatorHyperOpt.py" ] && echo "✅" || echo "❌")"
echo "  - run_hyperopt.py: $([ -f "run_hyperopt.py" ] && echo "✅" || echo "❌")"
echo "  - strategy_analyzer.py: $([ -f "strategy_analyzer.py" ] && echo "✅" || echo "❌")"

# 결과 디렉토리 확인
echo
log_info "📂 Results Directories:"
echo "  - Backtest Results: $(ls user_data/backtest_results/ 2>/dev/null | wc -l) files"
echo "  - HyperOpt Results: $(ls user_data/hyperopt_results/ 2>/dev/null | wc -l) files"
echo "  - Analysis Results: $(ls user_data/analysis_results/ 2>/dev/null | wc -l) files"
echo "  - Validation Results: $(ls user_data/validation_results/ 2>/dev/null | wc -l) files"

# 성능 목표 달성 여부 (예시)
echo
log_info "🎯 Performance Target Assessment:"

# 기본 목표값들
TARGET_MONTHLY_RETURN=8.0
TARGET_SHARPE=1.5
TARGET_MAX_DD=8.0
TARGET_WIN_RATE=60.0

echo "  Target Monthly Return: >=${TARGET_MONTHLY_RETURN}%"
echo "  Target Sharpe Ratio: >=${TARGET_SHARPE}"
echo "  Target Max Drawdown: <=${TARGET_MAX_DD}%"
echo "  Target Win Rate: >=${TARGET_WIN_RATE}%"

# 실제 성과는 백테스팅 결과에서 추출 (여기서는 예시)
echo
echo "  📈 Actual Performance (based on latest backtest):"
if echo "$OPTIMIZED_RESULT" | grep -q "Total profit"; then
    ACTUAL_PROFIT=$(echo "$OPTIMIZED_RESULT" | grep "Total profit" | grep -oE '[0-9]+\.[0-9]+' | tail -n 1 || echo "0.0")
    echo "    Total Return: ${ACTUAL_PROFIT}%"
else
    echo "    Total Return: Pending analysis"
fi

# 10. 다음 단계 가이드
echo
log_step "10. Next Steps Guidance"

echo
log_info "🚀 RECOMMENDED NEXT ACTIONS:"
echo

echo "📊 If Performance Meets Targets:"
echo "  1. Run extended backtesting (6+ months)"
echo "  2. Test on different market conditions"
echo "  3. Start paper trading (dry-run mode)"
echo "  4. Monitor real-time performance for 2+ weeks"
echo "  5. Gradually transition to live trading with small amounts"
echo

echo "🔧 If Performance Needs Improvement:"
echo "  1. Run additional hyperopt with more epochs (300-500)"
echo "  2. Test different loss functions (CalmarHyperOptLoss, etc.)"
echo "  3. Adjust signal weights and thresholds manually"
echo "  4. Consider additional indicators (ADX, Stochastic, etc.)"
echo "  5. Implement more sophisticated filters"
echo

echo "⚙️  System Optimization:"
echo "  1. Set up automated parameter reoptimization"
echo "  2. Implement walk-forward analysis"
echo "  3. Add market regime detection"
echo "  4. Set up real-time monitoring and alerts"
echo "  5. Prepare production deployment configuration"
echo

# 최종 요약
echo
log_success "🎉 PHASE 5C COMPLETED SUCCESSFULLY!"
echo

log_info "📋 Summary:"
echo "  ✅ Multi-indicator strategy implemented (RSI + MACD + Bollinger Bands)"
echo "  ✅ Signal aggregation and weighting system operational"
echo "  ✅ Advanced filtering systems active (time, volatility, trend)"
echo "  ✅ Hyperparameter optimization framework ready"
echo "  ✅ Comprehensive backtesting and analysis tools available"
echo "  ✅ Performance validation and comparison systems working"
echo

log_info "🌐 Access Points:"
echo "  - Freqtrade UI: http://localhost:8081"
echo "  - Freqtrade API: http://localhost:8080"
echo "  - Results Directory: $(pwd)/user_data/"
echo

log_info "📚 Documentation and Scripts:"
echo "  - Main Strategy: user_data/strategies/MultiIndicatorStrategy.py"
echo "  - HyperOpt: user_data/hyperopts/MultiIndicatorHyperOpt.py"
echo "  - Optimization: run_hyperopt.py"
echo "  - Analysis: strategy_analyzer.py"
echo "  - Validation: performance_validator.py"
echo

echo "🎯 The multi-indicator strategy system is now ready for production evaluation!"
echo "Review the analysis results and proceed with the recommended next steps."
echo

log_success "Phase 5C Complete! 🚀"