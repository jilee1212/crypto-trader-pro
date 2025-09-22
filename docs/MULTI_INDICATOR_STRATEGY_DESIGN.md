# 📊 다중 지표 전략 시스템 설계

## 🎯 개요
- **목표**: 여러 기술적 지표를 조합하여 더 정확한 진입/청산 신호 생성
- **방식**: N개 지표 중 M개 이상 조건 충족 시 진입 (예: 5개 중 3개 이상)
- **장점**: 잘못된 신호(False Signal) 감소, 신뢰도 향상

## 🏗️ 시스템 아키텍처

### 1. 지표 모듈 (Technical Indicators)
```
📁 indicators/
├── base_indicator.py          # 기본 지표 클래스
├── trend_indicators.py        # 추세 지표 (SMA, EMA, MACD, etc.)
├── momentum_indicators.py     # 모멘텀 지표 (RSI, Stochastic, etc.)
├── volatility_indicators.py   # 변동성 지표 (Bollinger, ATR, etc.)
├── volume_indicators.py       # 거래량 지표 (OBV, VWAP, etc.)
└── pattern_indicators.py      # 패턴 지표 (Support/Resistance, etc.)
```

### 2. 전략 조합기 (Strategy Combiner)
```
📁 strategy/
├── multi_indicator_strategy.py    # 다중 지표 전략 엔진
├── signal_aggregator.py          # 신호 집계기
├── condition_evaluator.py        # 조건 평가기
└── strategy_templates.py         # 사전 정의된 전략 템플릿
```

### 3. 백테스팅 확장
```
📁 backtesting/
├── multi_strategy_backtest.py    # 다중 전략 백테스팅
├── strategy_optimizer.py         # 전략 파라미터 최적화
└── performance_comparison.py     # 전략 성과 비교
```

## 📋 지원 지표 목록

### 🔄 추세 지표 (Trend Indicators)
1. **SMA (Simple Moving Average)** - 단순이동평균
2. **EMA (Exponential Moving Average)** - 지수이동평균
3. **MACD (Moving Average Convergence Divergence)** - MACD
4. **ADX (Average Directional Index)** - 평균방향지수
5. **Parabolic SAR** - 패러볼릭 SAR
6. **Ichimoku Cloud** - 일목균형표

### 📈 모멘텀 지표 (Momentum Indicators)
1. **RSI (Relative Strength Index)** - 상대강도지수
2. **Stochastic Oscillator** - 스토캐스틱
3. **Williams %R** - 윌리엄스 %R
4. **CCI (Commodity Channel Index)** - 상품채널지수
5. **MFI (Money Flow Index)** - 현금흐름지수
6. **ROC (Rate of Change)** - 변화율

### 📊 변동성 지표 (Volatility Indicators)
1. **Bollinger Bands** - 볼린저 밴드
2. **ATR (Average True Range)** - 평균진폭
3. **Keltner Channels** - 켈트너 채널
4. **Donchian Channels** - 돈치안 채널

### 📊 거래량 지표 (Volume Indicators)
1. **OBV (On-Balance Volume)** - 온밸런스 볼륨
2. **VWAP (Volume Weighted Average Price)** - 거래량 가중 평균가
3. **A/D Line (Accumulation/Distribution)** - 누적/분산선
4. **Chaikin Money Flow** - 차이킨 머니플로우

## ⚙️ 전략 설정 구조

### 1. 기본 전략 설정
```python
strategy_config = {
    "name": "RSI + MACD + Bollinger 전략",
    "description": "RSI, MACD, 볼린저 밴드 조합 전략",
    "indicators": [
        {
            "name": "RSI",
            "period": 14,
            "buy_condition": "< 30",
            "sell_condition": "> 70",
            "weight": 1.0
        },
        {
            "name": "MACD",
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9,
            "buy_condition": "bullish_crossover",
            "sell_condition": "bearish_crossover",
            "weight": 1.5
        },
        {
            "name": "Bollinger_Bands",
            "period": 20,
            "std_dev": 2,
            "buy_condition": "price_below_lower_band",
            "sell_condition": "price_above_upper_band",
            "weight": 1.2
        }
    ],
    "entry_rules": {
        "min_signals": 2,  # 최소 2개 신호 필요
        "total_indicators": 3,
        "weighted_threshold": 2.0  # 가중치 합계 임계값
    },
    "exit_rules": {
        "take_profit": 0.02,  # 2% 수익
        "stop_loss": 0.01,    # 1% 손절
        "trailing_stop": True
    }
}
```

### 2. 고급 조건 설정
```python
advanced_conditions = {
    "time_filters": {
        "trading_hours": "09:00-18:00",
        "avoid_weekends": True,
        "high_volatility_hours": "14:00-16:00"
    },
    "market_conditions": {
        "min_volume": 1000000,
        "max_spread": 0.001,
        "trend_filter": "uptrend_only"  # 상승장에서만 매수
    },
    "risk_management": {
        "max_positions": 5,
        "position_sizing": "kelly_criterion",
        "correlation_limit": 0.7
    }
}
```

## 🧪 백테스팅 확장 기능

### 1. 전략 비교 기능
- 여러 전략의 동시 백테스팅
- 성과 지표 비교 (Sharpe, Sortino, Calmar 비율)
- 리스크 조정 수익률 분석

### 2. 파라미터 최적화
- 그리드 서치 (Grid Search)
- 베이지안 최적화 (Bayesian Optimization)
- 유전 알고리즘 (Genetic Algorithm)

### 3. 강건성 테스트
- 워크 포워드 분석 (Walk Forward Analysis)
- 몬테카를로 시뮬레이션
- 시장 상황별 성과 분석

## 🎛️ 사용자 인터페이스

### 1. 전략 빌더
- 드래그 앤 드롭 지표 선택
- 실시간 조건 미리보기
- 백테스팅 결과 즉시 확인

### 2. 전략 라이브러리
- 사전 정의된 전략 템플릿
- 커뮤니티 전략 공유
- 성과 기반 전략 순위

### 3. 실시간 모니터링
- 지표별 신호 상태 표시
- 진입/청산 조건 달성률
- 전략 성과 실시간 추적

## 📈 구현 우선순위

### Phase 6A: 기본 다중 지표 시스템
1. 기본 지표 모듈 구현 (RSI, MACD, SMA, EMA)
2. 다중 지표 신호 집계기
3. 간단한 조건 평가기 (N개 중 M개)

### Phase 6B: 고급 전략 기능
1. 가중치 기반 신호 집계
2. 시간 필터 및 시장 조건 필터
3. 전략 템플릿 시스템

### Phase 6C: 백테스팅 확장
1. 다중 전략 백테스팅
2. 파라미터 최적화 엔진
3. 성과 비교 대시보드

### Phase 6D: 사용자 인터페이스
1. 전략 빌더 GUI
2. 실시간 전략 모니터링
3. 전략 라이브러리 관리

## 🔄 실행 흐름

```
1. 지표 계산 → 2. 신호 생성 → 3. 조건 평가 → 4. 진입/청산 결정
    ↓              ↓              ↓              ↓
 [RSI, MACD,   [매수신호 3개,  [5개 중 3개    [매수 신호
  Bollinger]    매도신호 1개]   조건 충족]     실행]
```

## 💡 확장 가능성

### 1. AI/ML 통합
- 신호 가중치 자동 조정
- 패턴 인식 기반 신호
- 강화학습 전략 최적화

### 2. 대체 데이터
- 뉴스 센티먼트 분석
- 소셜 미디어 지표
- 온체인 데이터 (암호화폐)

### 3. 포트폴리오 최적화
- 여러 자산 간 상관관계 분석
- 동적 포트폴리오 리밸런싱
- 리스크 패리티 전략

이 설계를 바탕으로 단계적으로 구현하여 더욱 정교하고 신뢰할 수 있는 자동매매 시스템을 만들 수 있습니다.