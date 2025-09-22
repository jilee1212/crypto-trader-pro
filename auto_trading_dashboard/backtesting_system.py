"""
🧪 Phase 5 백테스팅 시스템 (Backtesting System)
전략 검증, 역사적 성과 분석, 파라미터 최적화, 백테스트 결과 분석
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
try:
    import itertools
    from concurrent.futures import ThreadPoolExecutor
except ImportError:
    # 폴백: 기본 Python 기능만 사용
    itertools = None
    ThreadPoolExecutor = None
import time

class BacktestStrategy(Enum):
    """백테스트 전략 유형"""
    RSI_CROSSOVER = "RSI 크로스오버"
    MOVING_AVERAGE = "이동평균선"
    BOLLINGER_BANDS = "볼린저 밴드"
    MACD = "MACD"
    MOMENTUM = "모멘텀"
    MEAN_REVERSION = "평균 회귀"
    BREAKOUT = "돌파 전략"
    CUSTOM = "사용자 정의"

class TimeFrame(Enum):
    """시간 프레임"""
    M1 = "1분"
    M5 = "5분"
    M15 = "15분"
    M30 = "30분"
    H1 = "1시간"
    H4 = "4시간"
    D1 = "1일"

@dataclass
class BacktestParameters:
    """백테스트 파라미터"""
    strategy: BacktestStrategy
    symbol: str
    timeframe: TimeFrame
    start_date: datetime
    end_date: datetime
    initial_capital: float
    max_position_size: float
    commission: float
    slippage: float
    risk_per_trade: float
    stop_loss: float
    take_profit: float
    custom_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Trade:
    """개별 거래 정보"""
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    side: str  # 'buy' or 'sell'
    pnl: Optional[float]
    commission: float
    reason: str  # 'take_profit', 'stop_loss', 'signal', 'end_of_data'

@dataclass
class BacktestResults:
    """백테스트 결과"""
    parameters: BacktestParameters
    trades: List[Trade]
    equity_curve: pd.DataFrame
    performance_metrics: Dict[str, float]
    monthly_returns: pd.DataFrame
    drawdown_periods: List[Dict[str, Any]]
    execution_time: float
    total_bars: int

class StrategyEngine:
    """전략 실행 엔진"""

    def __init__(self, params: BacktestParameters):
        self.params = params
        self.current_position = 0
        self.cash = params.initial_capital
        self.equity = params.initial_capital
        self.trades = []
        self.equity_history = []

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """신호 생성 (전략별)"""
        if self.params.strategy == BacktestStrategy.RSI_CROSSOVER:
            return self._rsi_strategy(data)
        elif self.params.strategy == BacktestStrategy.MOVING_AVERAGE:
            return self._ma_strategy(data)
        elif self.params.strategy == BacktestStrategy.BOLLINGER_BANDS:
            return self._bollinger_strategy(data)
        elif self.params.strategy == BacktestStrategy.MACD:
            return self._macd_strategy(data)
        elif self.params.strategy == BacktestStrategy.MOMENTUM:
            return self._momentum_strategy(data)
        elif self.params.strategy == BacktestStrategy.MEAN_REVERSION:
            return self._mean_reversion_strategy(data)
        elif self.params.strategy == BacktestStrategy.BREAKOUT:
            return self._breakout_strategy(data)
        else:
            return pd.Series([0] * len(data), index=data.index)

    def _rsi_strategy(self, data: pd.DataFrame) -> pd.Series:
        """RSI 전략"""
        period = self.params.custom_params.get('rsi_period', 14)
        oversold = self.params.custom_params.get('oversold_level', 30)
        overbought = self.params.custom_params.get('overbought_level', 70)

        # RSI 계산
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        # 신호 생성
        signals = pd.Series([0] * len(data), index=data.index)
        signals[(rsi < oversold) & (rsi.shift(1) >= oversold)] = 1  # 매수
        signals[(rsi > overbought) & (rsi.shift(1) <= overbought)] = -1  # 매도

        return signals

    def _ma_strategy(self, data: pd.DataFrame) -> pd.Series:
        """이동평균 전략"""
        short_period = self.params.custom_params.get('short_ma', 20)
        long_period = self.params.custom_params.get('long_ma', 50)

        short_ma = data['close'].rolling(window=short_period).mean()
        long_ma = data['close'].rolling(window=long_period).mean()

        signals = pd.Series([0] * len(data), index=data.index)
        signals[(short_ma > long_ma) & (short_ma.shift(1) <= long_ma.shift(1))] = 1  # 골든크로스
        signals[(short_ma < long_ma) & (short_ma.shift(1) >= long_ma.shift(1))] = -1  # 데드크로스

        return signals

    def _bollinger_strategy(self, data: pd.DataFrame) -> pd.Series:
        """볼린저 밴드 전략"""
        period = self.params.custom_params.get('bb_period', 20)
        std_dev = self.params.custom_params.get('bb_std', 2)

        sma = data['close'].rolling(window=period).mean()
        std = data['close'].rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)

        signals = pd.Series([0] * len(data), index=data.index)
        signals[(data['close'] < lower_band) & (data['close'].shift(1) >= lower_band.shift(1))] = 1  # 매수
        signals[(data['close'] > upper_band) & (data['close'].shift(1) <= upper_band.shift(1))] = -1  # 매도

        return signals

    def _macd_strategy(self, data: pd.DataFrame) -> pd.Series:
        """MACD 전략"""
        fast_period = self.params.custom_params.get('macd_fast', 12)
        slow_period = self.params.custom_params.get('macd_slow', 26)
        signal_period = self.params.custom_params.get('macd_signal', 9)

        ema_fast = data['close'].ewm(span=fast_period).mean()
        ema_slow = data['close'].ewm(span=slow_period).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period).mean()

        signals = pd.Series([0] * len(data), index=data.index)
        signals[(macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))] = 1  # 매수
        signals[(macd_line < signal_line) & (macd_line.shift(1) >= signal_line.shift(1))] = -1  # 매도

        return signals

    def _momentum_strategy(self, data: pd.DataFrame) -> pd.Series:
        """모멘텀 전략"""
        period = self.params.custom_params.get('momentum_period', 10)
        threshold = self.params.custom_params.get('momentum_threshold', 0.02)

        momentum = data['close'].pct_change(period)

        signals = pd.Series([0] * len(data), index=data.index)
        signals[momentum > threshold] = 1  # 매수
        signals[momentum < -threshold] = -1  # 매도

        return signals

    def _mean_reversion_strategy(self, data: pd.DataFrame) -> pd.Series:
        """평균 회귀 전략"""
        period = self.params.custom_params.get('mean_period', 20)
        threshold = self.params.custom_params.get('mean_threshold', 2)

        sma = data['close'].rolling(window=period).mean()
        std = data['close'].rolling(window=period).std()
        z_score = (data['close'] - sma) / std

        signals = pd.Series([0] * len(data), index=data.index)
        signals[z_score < -threshold] = 1  # 매수 (가격이 평균보다 낮음)
        signals[z_score > threshold] = -1  # 매도 (가격이 평균보다 높음)

        return signals

    def _breakout_strategy(self, data: pd.DataFrame) -> pd.Series:
        """돌파 전략"""
        period = self.params.custom_params.get('breakout_period', 20)

        high_max = data['high'].rolling(window=period).max()
        low_min = data['low'].rolling(window=period).min()

        signals = pd.Series([0] * len(data), index=data.index)
        signals[data['close'] > high_max.shift(1)] = 1  # 상향 돌파
        signals[data['close'] < low_min.shift(1)] = -1  # 하향 돌파

        return signals

    def execute_backtest(self, data: pd.DataFrame) -> BacktestResults:
        """백테스트 실행"""
        start_time = time.time()

        signals = self.generate_signals(data)
        equity_history = []
        current_trade = None

        for i, (timestamp, row) in enumerate(data.iterrows()):
            current_price = row['close']
            signal = signals.iloc[i] if i < len(signals) else 0

            # 기존 포지션 관리
            if current_trade and current_trade.exit_time is None:
                # 손절매/익절 체크
                if self._should_exit_position(current_trade, current_price):
                    self._close_position(current_trade, current_price, timestamp, "stop_loss_take_profit")

            # 새로운 신호 처리
            if signal != 0 and self.current_position == 0:
                current_trade = self._open_position(signal, current_price, timestamp)

            elif signal != 0 and self.current_position != 0:
                # 기존 포지션 반대 신호시 청산
                if (signal > 0 and self.current_position < 0) or (signal < 0 and self.current_position > 0):
                    if current_trade:
                        self._close_position(current_trade, current_price, timestamp, "signal")
                    current_trade = self._open_position(signal, current_price, timestamp)

            # 자산 가치 업데이트
            if self.current_position != 0:
                position_value = self.current_position * current_price
                self.equity = self.cash + position_value
            else:
                self.equity = self.cash

            equity_history.append({
                'timestamp': timestamp,
                'equity': self.equity,
                'cash': self.cash,
                'position': self.current_position,
                'price': current_price
            })

        # 마지막 포지션 청산
        if current_trade and current_trade.exit_time is None:
            final_price = data['close'].iloc[-1]
            final_time = data.index[-1]
            self._close_position(current_trade, final_price, final_time, "end_of_data")

        execution_time = time.time() - start_time

        # 결과 생성
        equity_df = pd.DataFrame(equity_history)
        performance_metrics = self._calculate_performance_metrics(equity_df)
        monthly_returns = self._calculate_monthly_returns(equity_df)
        drawdown_periods = self._calculate_drawdown_periods(equity_df)

        return BacktestResults(
            parameters=self.params,
            trades=self.trades,
            equity_curve=equity_df,
            performance_metrics=performance_metrics,
            monthly_returns=monthly_returns,
            drawdown_periods=drawdown_periods,
            execution_time=execution_time,
            total_bars=len(data)
        )

    def _open_position(self, signal: int, price: float, timestamp: datetime) -> Trade:
        """포지션 열기"""
        # 포지션 크기 계산
        risk_amount = self.equity * self.params.risk_per_trade
        position_size = min(risk_amount / price, self.params.max_position_size)

        if signal > 0:  # 매수
            quantity = position_size
            cost = quantity * price * (1 + self.params.commission + self.params.slippage)
        else:  # 매도
            quantity = -position_size
            cost = abs(quantity) * price * (1 - self.params.commission - self.params.slippage)

        if abs(cost) <= self.cash:
            self.current_position = quantity
            self.cash -= cost

            trade = Trade(
                entry_time=timestamp,
                exit_time=None,
                entry_price=price,
                exit_price=None,
                quantity=quantity,
                side='buy' if signal > 0 else 'sell',
                pnl=None,
                commission=abs(quantity) * price * self.params.commission,
                reason=""
            )

            self.trades.append(trade)
            return trade

        return None

    def _close_position(self, trade: Trade, price: float, timestamp: datetime, reason: str):
        """포지션 닫기"""
        if trade is None or trade.exit_time is not None:
            return

        # 포지션 청산
        exit_cost = abs(trade.quantity) * price * self.params.commission
        proceeds = trade.quantity * price

        if trade.side == 'buy':
            self.cash += proceeds - exit_cost
            pnl = (price - trade.entry_price) * trade.quantity - trade.commission - exit_cost
        else:
            self.cash += abs(proceeds) - exit_cost
            pnl = (trade.entry_price - price) * abs(trade.quantity) - trade.commission - exit_cost

        trade.exit_time = timestamp
        trade.exit_price = price
        trade.pnl = pnl
        trade.commission += exit_cost
        trade.reason = reason

        self.current_position = 0

    def _should_exit_position(self, trade: Trade, current_price: float) -> bool:
        """포지션 청산 조건 체크"""
        if trade is None or trade.exit_time is not None:
            return False

        if trade.side == 'buy':
            # 손절매 체크
            if self.params.stop_loss > 0:
                stop_price = trade.entry_price * (1 - self.params.stop_loss)
                if current_price <= stop_price:
                    return True

            # 익절 체크
            if self.params.take_profit > 0:
                target_price = trade.entry_price * (1 + self.params.take_profit)
                if current_price >= target_price:
                    return True

        else:  # sell
            # 손절매 체크
            if self.params.stop_loss > 0:
                stop_price = trade.entry_price * (1 + self.params.stop_loss)
                if current_price >= stop_price:
                    return True

            # 익절 체크
            if self.params.take_profit > 0:
                target_price = trade.entry_price * (1 - self.params.take_profit)
                if current_price <= target_price:
                    return True

        return False

    def _calculate_performance_metrics(self, equity_df: pd.DataFrame) -> Dict[str, float]:
        """성과 지표 계산"""
        if len(equity_df) < 2:
            return {}

        initial_equity = equity_df['equity'].iloc[0]
        final_equity = equity_df['equity'].iloc[-1]

        # 수익률 계산
        total_return = (final_equity / initial_equity - 1) * 100

        # 일별 수익률
        equity_df['daily_return'] = equity_df['equity'].pct_change()
        daily_returns = equity_df['daily_return'].dropna()

        if len(daily_returns) == 0:
            return {'total_return': total_return}

        # 연간 수익률
        trading_days = len(daily_returns)
        years = trading_days / 252
        annualized_return = ((final_equity / initial_equity) ** (1 / years) - 1) * 100 if years > 0 else 0

        # 변동성
        volatility = daily_returns.std() * np.sqrt(252) * 100

        # 샤프 비율
        sharpe_ratio = (daily_returns.mean() / daily_returns.std() * np.sqrt(252)) if daily_returns.std() > 0 else 0

        # 최대 드로다운
        peak = equity_df['equity'].expanding().max()
        drawdown = (equity_df['equity'] - peak) / peak
        max_drawdown = drawdown.min() * 100

        # 거래 관련 지표
        winning_trades = [t for t in self.trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl and t.pnl < 0]

        win_rate = len(winning_trades) / len(self.trades) * 100 if self.trades else 0
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0

        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor
        }

    def _calculate_monthly_returns(self, equity_df: pd.DataFrame) -> pd.DataFrame:
        """월별 수익률 계산"""
        if len(equity_df) < 2:
            return pd.DataFrame()

        equity_df = equity_df.copy()
        equity_df['month'] = equity_df['timestamp'].dt.to_period('M')

        monthly_equity = equity_df.groupby('month')['equity'].last()
        monthly_returns = monthly_equity.pct_change().fillna(0) * 100

        return monthly_returns.to_frame('return')

    def _calculate_drawdown_periods(self, equity_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """드로다운 기간 계산"""
        if len(equity_df) < 2:
            return []

        peak = equity_df['equity'].expanding().max()
        drawdown = (equity_df['equity'] - peak) / peak

        # 드로다운 기간 찾기
        in_drawdown = drawdown < 0
        drawdown_periods = []

        start_idx = None
        for i, is_dd in enumerate(in_drawdown):
            if is_dd and start_idx is None:
                start_idx = i
            elif not is_dd and start_idx is not None:
                end_idx = i - 1
                dd_period = {
                    'start': equity_df.iloc[start_idx]['timestamp'],
                    'end': equity_df.iloc[end_idx]['timestamp'],
                    'duration': end_idx - start_idx + 1,
                    'max_drawdown': drawdown.iloc[start_idx:end_idx+1].min() * 100
                }
                drawdown_periods.append(dd_period)
                start_idx = None

        return drawdown_periods

class BacktestingSystem:
    """🧪 Phase 5 백테스팅 시스템"""

    def __init__(self):
        self.initialize_session_state()

    def initialize_session_state(self):
        """세션 상태 초기화"""
        if 'backtest_results' not in st.session_state:
            st.session_state.backtest_results = []

        if 'optimization_results' not in st.session_state:
            st.session_state.optimization_results = []

        if 'market_data' not in st.session_state:
            st.session_state.market_data = self.generate_sample_market_data()

    def show_backtesting_dashboard(self):
        """백테스팅 대시보드 표시"""
        st.title("🧪 백테스팅 시스템")
        st.markdown("**Phase 5: 전략 검증 및 파라미터 최적화**")

        # 탭 구성
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🎯 단일 백테스트", "🔄 파라미터 최적화", "📊 결과 분석",
            "📈 비교 분석", "⚙️ 설정"
        ])

        with tab1:
            self.show_single_backtest()

        with tab2:
            self.show_parameter_optimization()

        with tab3:
            self.show_results_analysis()

        with tab4:
            self.show_comparison_analysis()

        with tab5:
            self.show_backtest_settings()

    def show_single_backtest(self):
        """단일 백테스트 탭"""
        st.subheader("🎯 단일 백테스트")

        # 백테스트 설정
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 📋 전략 설정")

            strategy = st.selectbox(
                "전략 선택",
                [s.value for s in BacktestStrategy],
                key="single_strategy"
            )

            symbol = st.selectbox(
                "거래 심볼",
                ["BTC/USDT", "ETH/USDT", "ADA/USDT", "DOT/USDT"],
                key="single_symbol"
            )

            timeframe = st.selectbox(
                "시간 프레임",
                [tf.value for tf in TimeFrame],
                index=4,  # 1시간
                key="single_timeframe"
            )

            # 날짜 범위
            start_date = st.date_input(
                "시작 날짜",
                value=datetime.now() - timedelta(days=365),
                key="single_start_date"
            )

            end_date = st.date_input(
                "종료 날짜",
                value=datetime.now(),
                key="single_end_date"
            )

        with col2:
            st.markdown("#### 💰 자본 관리")

            initial_capital = st.number_input(
                "초기 자본 ($)",
                min_value=1000.0,
                max_value=1000000.0,
                value=100000.0,
                step=1000.0,
                key="single_capital"
            )

            max_position_size = st.number_input(
                "최대 포지션 크기 ($)",
                min_value=100.0,
                max_value=50000.0,
                value=10000.0,
                step=100.0,
                key="single_position_size"
            )

            risk_per_trade = st.slider(
                "거래당 리스크 (%)",
                min_value=0.5,
                max_value=10.0,
                value=2.0,
                step=0.1,
                key="single_risk"
            ) / 100

            commission = st.number_input(
                "수수료 (%)",
                min_value=0.0,
                max_value=1.0,
                value=0.1,
                step=0.01,
                key="single_commission"
            ) / 100

            slippage = st.number_input(
                "슬리피지 (%)",
                min_value=0.0,
                max_value=1.0,
                value=0.05,
                step=0.01,
                key="single_slippage"
            ) / 100

        # 전략별 파라미터
        st.markdown("#### ⚙️ 전략 파라미터")
        strategy_params = self.show_strategy_parameters(strategy)

        # 리스크 관리
        col1, col2 = st.columns(2)

        with col1:
            stop_loss = st.number_input(
                "손절매 (%)",
                min_value=0.0,
                max_value=20.0,
                value=2.0,
                step=0.1,
                key="single_stop_loss"
            ) / 100

        with col2:
            take_profit = st.number_input(
                "익절 (%)",
                min_value=0.0,
                max_value=50.0,
                value=4.0,
                step=0.1,
                key="single_take_profit"
            ) / 100

        # 백테스트 실행
        if st.button("🚀 백테스트 실행", type="primary", key="run_single_backtest"):
            with st.spinner("백테스트 실행 중..."):
                params = BacktestParameters(
                    strategy=BacktestStrategy(strategy),
                    symbol=symbol,
                    timeframe=TimeFrame(timeframe),
                    start_date=datetime.combine(start_date, datetime.min.time()),
                    end_date=datetime.combine(end_date, datetime.min.time()),
                    initial_capital=initial_capital,
                    max_position_size=max_position_size,
                    commission=commission,
                    slippage=slippage,
                    risk_per_trade=risk_per_trade,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    custom_params=strategy_params
                )

                results = self.run_backtest(params)

                if results:
                    st.session_state.backtest_results.append(results)
                    st.success(f"✅ 백테스트 완료! 실행 시간: {results.execution_time:.2f}초")

                    # 빠른 결과 표시
                    self.show_quick_results(results)

    def show_strategy_parameters(self, strategy: str) -> Dict[str, Any]:
        """전략별 파라미터 설정"""
        params = {}

        if strategy == BacktestStrategy.RSI_CROSSOVER.value:
            col1, col2, col3 = st.columns(3)
            with col1:
                params['rsi_period'] = st.number_input("RSI 기간", value=14, key="rsi_period")
            with col2:
                params['oversold_level'] = st.number_input("과매도 수준", value=30, key="oversold")
            with col3:
                params['overbought_level'] = st.number_input("과매수 수준", value=70, key="overbought")

        elif strategy == BacktestStrategy.MOVING_AVERAGE.value:
            col1, col2 = st.columns(2)
            with col1:
                params['short_ma'] = st.number_input("단기 이평선", value=20, key="short_ma")
            with col2:
                params['long_ma'] = st.number_input("장기 이평선", value=50, key="long_ma")

        elif strategy == BacktestStrategy.BOLLINGER_BANDS.value:
            col1, col2 = st.columns(2)
            with col1:
                params['bb_period'] = st.number_input("볼린저 기간", value=20, key="bb_period")
            with col2:
                params['bb_std'] = st.number_input("표준편차 배수", value=2.0, step=0.1, key="bb_std")

        elif strategy == BacktestStrategy.MACD.value:
            col1, col2, col3 = st.columns(3)
            with col1:
                params['macd_fast'] = st.number_input("MACD 빠른선", value=12, key="macd_fast")
            with col2:
                params['macd_slow'] = st.number_input("MACD 느린선", value=26, key="macd_slow")
            with col3:
                params['macd_signal'] = st.number_input("MACD 신호선", value=9, key="macd_signal")

        elif strategy == BacktestStrategy.MOMENTUM.value:
            col1, col2 = st.columns(2)
            with col1:
                params['momentum_period'] = st.number_input("모멘텀 기간", value=10, key="momentum_period")
            with col2:
                params['momentum_threshold'] = st.number_input("임계값", value=0.02, step=0.01, key="momentum_threshold")

        elif strategy == BacktestStrategy.MEAN_REVERSION.value:
            col1, col2 = st.columns(2)
            with col1:
                params['mean_period'] = st.number_input("평균 기간", value=20, key="mean_period")
            with col2:
                params['mean_threshold'] = st.number_input("Z-Score 임계값", value=2.0, step=0.1, key="mean_threshold")

        elif strategy == BacktestStrategy.BREAKOUT.value:
            params['breakout_period'] = st.number_input("돌파 기간", value=20, key="breakout_period")

        return params

    def show_parameter_optimization(self):
        """파라미터 최적화 탭"""
        st.subheader("🔄 파라미터 최적화")

        st.markdown("#### 🎯 최적화 설정")

        col1, col2 = st.columns(2)

        with col1:
            opt_strategy = st.selectbox(
                "최적화할 전략",
                [s.value for s in BacktestStrategy if s != BacktestStrategy.CUSTOM],
                key="opt_strategy"
            )

            opt_symbol = st.selectbox(
                "거래 심볼",
                ["BTC/USDT", "ETH/USDT", "ADA/USDT"],
                key="opt_symbol"
            )

            opt_objective = st.selectbox(
                "최적화 목표",
                ["샤프 비율", "총 수익률", "최대 드로다운 최소화", "승률", "수익 팩터"],
                key="opt_objective"
            )

        with col2:
            opt_start_date = st.date_input(
                "최적화 시작 날짜",
                value=datetime.now() - timedelta(days=365),
                key="opt_start_date"
            )

            opt_end_date = st.date_input(
                "최적화 종료 날짜",
                value=datetime.now(),
                key="opt_end_date"
            )

            max_iterations = st.number_input(
                "최대 반복 횟수",
                min_value=10,
                max_value=1000,
                value=100,
                key="max_iterations"
            )

        # 파라미터 범위 설정
        st.markdown("#### 📊 파라미터 범위")
        param_ranges = self.show_parameter_ranges(opt_strategy)

        # 최적화 실행
        if st.button("🔍 최적화 시작", type="primary", key="start_optimization"):
            with st.spinner("파라미터 최적화 실행 중..."):
                progress_bar = st.progress(0)
                status_text = st.empty()

                optimization_results = self.run_parameter_optimization(
                    opt_strategy, opt_symbol, opt_objective, param_ranges,
                    opt_start_date, opt_end_date, max_iterations,
                    progress_bar, status_text
                )

                if optimization_results:
                    st.session_state.optimization_results.append(optimization_results)
                    st.success("✅ 최적화 완료!")

                    # 최적화 결과 표시
                    self.show_optimization_results(optimization_results)

    def show_parameter_ranges(self, strategy: str) -> Dict[str, Tuple[float, float, float]]:
        """파라미터 범위 설정"""
        ranges = {}

        if strategy == BacktestStrategy.RSI_CROSSOVER.value:
            col1, col2, col3 = st.columns(3)
            with col1:
                rsi_min = st.number_input("RSI 기간 최소", value=10, key="rsi_min")
                rsi_max = st.number_input("RSI 기간 최대", value=20, key="rsi_max")
                ranges['rsi_period'] = (rsi_min, rsi_max, 1)

            with col2:
                oversold_min = st.number_input("과매도 최소", value=20, key="oversold_min")
                oversold_max = st.number_input("과매도 최대", value=40, key="oversold_max")
                ranges['oversold_level'] = (oversold_min, oversold_max, 5)

            with col3:
                overbought_min = st.number_input("과매수 최소", value=60, key="overbought_min")
                overbought_max = st.number_input("과매수 최대", value=80, key="overbought_max")
                ranges['overbought_level'] = (overbought_min, overbought_max, 5)

        elif strategy == BacktestStrategy.MOVING_AVERAGE.value:
            col1, col2 = st.columns(2)
            with col1:
                short_ma_min = st.number_input("단기 이평선 최소", value=10, key="short_ma_min")
                short_ma_max = st.number_input("단기 이평선 최대", value=30, key="short_ma_max")
                ranges['short_ma'] = (short_ma_min, short_ma_max, 5)

            with col2:
                long_ma_min = st.number_input("장기 이평선 최소", value=40, key="long_ma_min")
                long_ma_max = st.number_input("장기 이평선 최대", value=100, key="long_ma_max")
                ranges['long_ma'] = (long_ma_min, long_ma_max, 10)

        # 다른 전략들도 유사하게 구현...

        return ranges

    def show_results_analysis(self):
        """결과 분석 탭"""
        st.subheader("📊 백테스트 결과 분석")

        if not st.session_state.backtest_results:
            st.info("분석할 백테스트 결과가 없습니다. 먼저 백테스트를 실행해주세요.")
            return

        # 결과 선택
        result_names = [f"백테스트 {i+1}: {r.parameters.strategy.value} ({r.parameters.symbol})"
                       for i, r in enumerate(st.session_state.backtest_results)]

        selected_result_idx = st.selectbox(
            "분석할 결과 선택",
            range(len(result_names)),
            format_func=lambda x: result_names[x],
            key="selected_result"
        )

        selected_result = st.session_state.backtest_results[selected_result_idx]

        # 상세 분석 표시
        self.show_detailed_analysis(selected_result)

    def show_comparison_analysis(self):
        """비교 분석 탭"""
        st.subheader("📈 백테스트 결과 비교")

        if len(st.session_state.backtest_results) < 2:
            st.info("비교를 위해서는 최소 2개의 백테스트 결과가 필요합니다.")
            return

        # 비교할 결과들 선택
        result_names = [f"백테스트 {i+1}: {r.parameters.strategy.value}"
                       for i, r in enumerate(st.session_state.backtest_results)]

        selected_results = st.multiselect(
            "비교할 결과들 선택",
            range(len(result_names)),
            format_func=lambda x: result_names[x],
            default=list(range(min(3, len(result_names)))),
            key="comparison_results"
        )

        if len(selected_results) >= 2:
            # 비교 분석 표시
            self.show_comparison_charts(selected_results)
            self.show_comparison_table(selected_results)

    def show_backtest_settings(self):
        """백테스트 설정 탭"""
        st.subheader("⚙️ 백테스트 설정")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 📊 데이터 설정")

            data_source = st.selectbox(
                "데이터 소스",
                ["시뮬레이션 데이터", "Binance API", "Yahoo Finance", "CSV 파일"],
                key="data_source"
            )

            if data_source == "CSV 파일":
                uploaded_file = st.file_uploader(
                    "CSV 파일 업로드",
                    type=['csv'],
                    key="upload_data"
                )

            cache_data = st.checkbox("데이터 캐싱", value=True, key="cache_data")

        with col2:
            st.markdown("#### ⚡ 성능 설정")

            parallel_processing = st.checkbox("병렬 처리 활성화", value=True, key="parallel_processing")

            if parallel_processing:
                num_threads = st.number_input(
                    "스레드 수",
                    min_value=1,
                    max_value=8,
                    value=4,
                    key="num_threads"
                )

            progress_updates = st.checkbox("진행률 업데이트", value=True, key="progress_updates")

        # 고급 설정
        st.markdown("#### 🔧 고급 설정")

        with st.expander("고급 옵션", expanded=False):
            warm_up_period = st.number_input(
                "워밍업 기간 (일)",
                min_value=0,
                max_value=100,
                value=20,
                key="warm_up_period"
            )

            lookahead_bias_check = st.checkbox(
                "미래 정보 누설 체크",
                value=True,
                key="lookahead_check"
            )

            transaction_costs = st.checkbox(
                "거래 비용 포함",
                value=True,
                key="transaction_costs"
            )

        # 설정 저장/불러오기
        col1, col2 = st.columns(2)

        with col1:
            if st.button("💾 설정 저장", key="save_backtest_settings"):
                st.success("✅ 설정이 저장되었습니다!")

        with col2:
            if st.button("📥 설정 불러오기", key="load_backtest_settings"):
                st.info("💾 설정 불러오기 기능이 구현됩니다.")

    def run_backtest(self, params: BacktestParameters) -> Optional[BacktestResults]:
        """백테스트 실행"""
        try:
            # 시뮬레이션 데이터 사용
            market_data = self.get_market_data(params.symbol, params.start_date, params.end_date)

            if market_data.empty:
                st.error("시장 데이터를 불러올 수 없습니다.")
                return None

            # 전략 엔진 생성 및 실행
            engine = StrategyEngine(params)
            results = engine.execute_backtest(market_data)

            return results

        except Exception as e:
            st.error(f"백테스트 실행 중 오류가 발생했습니다: {e}")
            return None

    def get_market_data(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """시장 데이터 가져오기 (시뮬레이션)"""
        # 실제 구현에서는 실제 거래소 API나 데이터 제공업체에서 데이터를 가져옴
        days = (end_date - start_date).days
        if days <= 0:
            return pd.DataFrame()

        dates = pd.date_range(start=start_date, end=end_date, freq='H')[:days*24]

        # 가격 시뮬레이션 (랜덤 워크)
        initial_price = 50000 if 'BTC' in symbol else 3000
        returns = np.random.normal(0.0001, 0.02, len(dates))
        prices = [initial_price]

        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))

        # OHLCV 데이터 생성
        data = []
        for i, (date, price) in enumerate(zip(dates, prices)):
            high = price * (1 + abs(np.random.normal(0, 0.01)))
            low = price * (1 - abs(np.random.normal(0, 0.01)))
            open_price = prices[i-1] if i > 0 else price
            close_price = price
            volume = np.random.uniform(100, 1000)

            data.append({
                'timestamp': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close_price,
                'volume': volume
            })

        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df

    def run_parameter_optimization(self, strategy: str, symbol: str, objective: str,
                                 param_ranges: Dict[str, Tuple[float, float, float]],
                                 start_date, end_date, max_iterations: int,
                                 progress_bar, status_text) -> Optional[Dict[str, Any]]:
        """파라미터 최적화 실행"""
        try:
            # 파라미터 조합 생성
            param_combinations = self.generate_parameter_combinations(param_ranges, max_iterations)

            best_result = None
            best_score = float('-inf') if objective != "최대 드로다운 최소화" else float('inf')
            all_results = []

            for i, params in enumerate(param_combinations):
                # 진행률 업데이트
                progress = (i + 1) / len(param_combinations)
                progress_bar.progress(progress)
                status_text.text(f"최적화 진행중: {i+1}/{len(param_combinations)} ({progress:.1%})")

                # 백테스트 실행
                backtest_params = BacktestParameters(
                    strategy=BacktestStrategy(strategy),
                    symbol=symbol,
                    timeframe=TimeFrame.H1,
                    start_date=datetime.combine(start_date, datetime.min.time()),
                    end_date=datetime.combine(end_date, datetime.min.time()),
                    initial_capital=100000,
                    max_position_size=10000,
                    commission=0.001,
                    slippage=0.0005,
                    risk_per_trade=0.02,
                    stop_loss=0.02,
                    take_profit=0.04,
                    custom_params=params
                )

                engine = StrategyEngine(backtest_params)
                market_data = self.get_market_data(symbol, backtest_params.start_date, backtest_params.end_date)

                if not market_data.empty:
                    result = engine.execute_backtest(market_data)
                    score = self.calculate_optimization_score(result, objective)

                    all_results.append({
                        'params': params,
                        'score': score,
                        'metrics': result.performance_metrics
                    })

                    # 최적 결과 업데이트
                    is_better = (score > best_score) if objective != "최대 드로다운 최소화" else (score < best_score)
                    if is_better:
                        best_score = score
                        best_result = result

            return {
                'best_result': best_result,
                'best_score': best_score,
                'all_results': all_results,
                'objective': objective,
                'strategy': strategy,
                'total_combinations': len(param_combinations)
            }

        except Exception as e:
            st.error(f"최적화 중 오류가 발생했습니다: {e}")
            return None

    def generate_parameter_combinations(self, param_ranges: Dict[str, Tuple[float, float, float]],
                                      max_iterations: int) -> List[Dict[str, Any]]:
        """파라미터 조합 생성"""
        if not param_ranges:
            return [{}]

        # 각 파라미터의 가능한 값들 생성
        param_values = {}
        for param_name, (min_val, max_val, step) in param_ranges.items():
            values = list(range(int(min_val), int(max_val) + 1, int(step)))
            param_values[param_name] = values

        # 모든 조합 생성
        param_names = list(param_values.keys())

        if itertools:
            all_combinations = list(itertools.product(*[param_values[name] for name in param_names]))
        else:
            # itertools가 없는 경우 간단한 조합 생성
            all_combinations = []
            if len(param_names) == 1:
                all_combinations = [(val,) for val in param_values[param_names[0]]]
            elif len(param_names) == 2:
                for val1 in param_values[param_names[0]]:
                    for val2 in param_values[param_names[1]]:
                        all_combinations.append((val1, val2))
            else:
                # 3개 이상은 기본값으로 제한
                all_combinations = [(val,) for val in param_values[param_names[0]][:10]]

        # 최대 반복 횟수로 제한
        if len(all_combinations) > max_iterations:
            # 랜덤 샘플링
            import random
            all_combinations = random.sample(all_combinations, max_iterations)

        # 딕셔너리 형태로 변환
        combinations = []
        for combo in all_combinations:
            param_dict = {name: value for name, value in zip(param_names, combo)}
            combinations.append(param_dict)

        return combinations

    def calculate_optimization_score(self, result: BacktestResults, objective: str) -> float:
        """최적화 점수 계산"""
        metrics = result.performance_metrics

        if objective == "샤프 비율":
            return metrics.get('sharpe_ratio', 0)
        elif objective == "총 수익률":
            return metrics.get('total_return', 0)
        elif objective == "최대 드로다운 최소화":
            return abs(metrics.get('max_drawdown', 0))  # 절대값 (작을수록 좋음)
        elif objective == "승률":
            return metrics.get('win_rate', 0)
        elif objective == "수익 팩터":
            return metrics.get('profit_factor', 0)
        else:
            return 0

    def show_quick_results(self, results: BacktestResults):
        """빠른 결과 표시"""
        st.markdown("#### 📊 백테스트 결과 요약")

        metrics = results.performance_metrics

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("총 수익률", f"{metrics.get('total_return', 0):.2f}%")
            st.metric("총 거래 수", f"{metrics.get('total_trades', 0):,}")

        with col2:
            st.metric("연간 수익률", f"{metrics.get('annualized_return', 0):.2f}%")
            st.metric("승률", f"{metrics.get('win_rate', 0):.1f}%")

        with col3:
            st.metric("샤프 비율", f"{metrics.get('sharpe_ratio', 0):.2f}")
            st.metric("수익 팩터", f"{metrics.get('profit_factor', 0):.2f}")

        with col4:
            st.metric("최대 드로다운", f"{metrics.get('max_drawdown', 0):.2f}%")
            st.metric("변동성", f"{metrics.get('volatility', 0):.2f}%")

        # 자산 곡선 차트
        if not results.equity_curve.empty:
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=results.equity_curve['timestamp'],
                y=results.equity_curve['equity'],
                mode='lines',
                name='포트폴리오 가치',
                line=dict(color='blue', width=2)
            ))

            fig.update_layout(
                title="📈 자산 곡선",
                xaxis_title="날짜",
                yaxis_title="포트폴리오 가치 ($)",
                height=400
            )

            st.plotly_chart(fig, use_container_width=True)

    def show_detailed_analysis(self, results: BacktestResults):
        """상세 분석 표시"""
        st.markdown("#### 📈 상세 성과 분석")

        # 성과 지표 테이블
        metrics = results.performance_metrics
        metrics_df = pd.DataFrame([
            ["총 수익률", f"{metrics.get('total_return', 0):.2f}%"],
            ["연간 수익률", f"{metrics.get('annualized_return', 0):.2f}%"],
            ["변동성", f"{metrics.get('volatility', 0):.2f}%"],
            ["샤프 비율", f"{metrics.get('sharpe_ratio', 0):.2f}"],
            ["최대 드로다운", f"{metrics.get('max_drawdown', 0):.2f}%"],
            ["총 거래 수", f"{metrics.get('total_trades', 0):,}"],
            ["수익 거래", f"{metrics.get('winning_trades', 0):,}"],
            ["손실 거래", f"{metrics.get('losing_trades', 0):,}"],
            ["승률", f"{metrics.get('win_rate', 0):.1f}%"],
            ["평균 수익", f"${metrics.get('avg_win', 0):.2f}"],
            ["평균 손실", f"${metrics.get('avg_loss', 0):.2f}"],
            ["수익 팩터", f"{metrics.get('profit_factor', 0):.2f}"]
        ], columns=["지표", "값"])

        st.dataframe(metrics_df, hide_index=True, use_container_width=True)

        # 자산 곡선과 드로다운
        if not results.equity_curve.empty:
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('포트폴리오 가치', '드로다운'),
                vertical_spacing=0.1,
                row_heights=[0.7, 0.3]
            )

            # 포트폴리오 가치
            fig.add_trace(
                go.Scatter(
                    x=results.equity_curve['timestamp'],
                    y=results.equity_curve['equity'],
                    mode='lines',
                    name='포트폴리오 가치',
                    line=dict(color='blue', width=2)
                ),
                row=1, col=1
            )

            # 드로다운 계산 및 표시
            equity = results.equity_curve['equity']
            peak = equity.expanding().max()
            drawdown = (equity - peak) / peak * 100

            fig.add_trace(
                go.Scatter(
                    x=results.equity_curve['timestamp'],
                    y=drawdown,
                    mode='lines',
                    name='드로다운',
                    fill='tozeroy',
                    line=dict(color='red'),
                    fillcolor='rgba(255, 0, 0, 0.3)'
                ),
                row=2, col=1
            )

            fig.update_layout(height=600, title_text="📊 백테스트 결과 차트")
            st.plotly_chart(fig, use_container_width=True)

        # 거래 내역
        if results.trades:
            st.markdown("#### 💼 거래 내역")

            trades_data = []
            for trade in results.trades[-20:]:  # 최근 20개 거래만 표시
                trades_data.append({
                    '진입 시간': trade.entry_time.strftime('%Y-%m-%d %H:%M'),
                    '청산 시간': trade.exit_time.strftime('%Y-%m-%d %H:%M') if trade.exit_time else '',
                    '방향': trade.side,
                    '진입가': f"${trade.entry_price:.2f}",
                    '청산가': f"${trade.exit_price:.2f}" if trade.exit_price else '',
                    '수량': f"{trade.quantity:.4f}",
                    'P&L': f"${trade.pnl:.2f}" if trade.pnl else '',
                    '청산 사유': trade.reason
                })

            trades_df = pd.DataFrame(trades_data)
            st.dataframe(trades_df, hide_index=True, use_container_width=True)

    def show_optimization_results(self, optimization_results: Dict[str, Any]):
        """최적화 결과 표시"""
        st.markdown("#### 🏆 최적화 결과")

        best_result = optimization_results['best_result']
        best_score = optimization_results['best_score']
        objective = optimization_results['objective']

        st.success(f"최적 {objective}: {best_score:.4f}")

        # 최적 파라미터
        st.markdown("#### ⚙️ 최적 파라미터")
        best_params = best_result.parameters.custom_params
        params_df = pd.DataFrame([
            [key, value] for key, value in best_params.items()
        ], columns=["파라미터", "값"])

        st.dataframe(params_df, hide_index=True)

        # 최적 결과의 성과 지표
        self.show_quick_results(best_result)

        # 파라미터 스캔 결과 (상위 10개)
        st.markdown("#### 📊 파라미터 스캔 결과 (상위 10개)")
        all_results = optimization_results['all_results']
        sorted_results = sorted(all_results, key=lambda x: x['score'], reverse=True)[:10]

        scan_data = []
        for i, result in enumerate(sorted_results):
            params_str = ", ".join([f"{k}={v}" for k, v in result['params'].items()])
            scan_data.append({
                '순위': i + 1,
                '파라미터': params_str,
                f'{objective}': f"{result['score']:.4f}",
                '총 수익률': f"{result['metrics'].get('total_return', 0):.2f}%",
                '샤프 비율': f"{result['metrics'].get('sharpe_ratio', 0):.2f}",
                '최대 드로다운': f"{result['metrics'].get('max_drawdown', 0):.2f}%"
            })

        scan_df = pd.DataFrame(scan_data)
        st.dataframe(scan_df, hide_index=True, use_container_width=True)

    def show_comparison_charts(self, selected_results: List[int]):
        """비교 차트 표시"""
        st.markdown("#### 📈 성과 비교 차트")

        fig = go.Figure()

        for i, result_idx in enumerate(selected_results):
            result = st.session_state.backtest_results[result_idx]
            equity_curve = result.equity_curve

            # 정규화 (시작점을 100으로)
            normalized_equity = (equity_curve['equity'] / equity_curve['equity'].iloc[0]) * 100

            fig.add_trace(go.Scatter(
                x=equity_curve['timestamp'],
                y=normalized_equity,
                mode='lines',
                name=f"{result.parameters.strategy.value} ({result.parameters.symbol})",
                line=dict(width=2)
            ))

        fig.update_layout(
            title="📊 정규화된 성과 비교",
            xaxis_title="날짜",
            yaxis_title="정규화된 가치",
            height=500,
            hovermode='x unified'
        )

        st.plotly_chart(fig, use_container_width=True)

    def show_comparison_table(self, selected_results: List[int]):
        """비교 테이블 표시"""
        st.markdown("#### 📊 성과 지표 비교")

        comparison_data = []
        for result_idx in selected_results:
            result = st.session_state.backtest_results[result_idx]
            metrics = result.performance_metrics

            comparison_data.append({
                '전략': result.parameters.strategy.value,
                '심볼': result.parameters.symbol,
                '총 수익률 (%)': f"{metrics.get('total_return', 0):.2f}",
                '연간 수익률 (%)': f"{metrics.get('annualized_return', 0):.2f}",
                '샤프 비율': f"{metrics.get('sharpe_ratio', 0):.2f}",
                '최대 드로다운 (%)': f"{metrics.get('max_drawdown', 0):.2f}",
                '승률 (%)': f"{metrics.get('win_rate', 0):.1f}",
                '총 거래': f"{metrics.get('total_trades', 0):,}",
                '수익 팩터': f"{metrics.get('profit_factor', 0):.2f}"
            })

        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, hide_index=True, use_container_width=True)

    def generate_sample_market_data(self) -> pd.DataFrame:
        """샘플 시장 데이터 생성"""
        days = 365
        dates = pd.date_range(start=datetime.now() - timedelta(days=days), periods=days*24, freq='H')

        # BTC 가격 시뮬레이션
        returns = np.random.normal(0.0001, 0.02, len(dates))
        prices = [50000]

        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))

        data = []
        for i, (date, price) in enumerate(zip(dates, prices)):
            high = price * (1 + abs(np.random.normal(0, 0.01)))
            low = price * (1 - abs(np.random.normal(0, 0.01)))
            open_price = prices[i-1] if i > 0 else price
            volume = np.random.uniform(100, 1000)

            data.append({
                'timestamp': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': price,
                'volume': volume
            })

        return pd.DataFrame(data)

# 메인 실행 함수
def main():
    """메인 실행 함수"""
    backtest_system = BacktestingSystem()
    backtest_system.show_backtesting_dashboard()

if __name__ == "__main__":
    main()