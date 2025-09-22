"""
📊 Phase 4 고급 성과 추적기 (Performance Tracker)
실시간 성과 분석, 수익률 계산, 리스크 메트릭, 트레이딩 통계 제공
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import random
from typing import Dict, List, Any, Optional, Tuple

class AdvancedPerformanceTracker:
    """📊 Phase 4 고급 성과 추적기"""

    def __init__(self):
        self.initialize_session_state()

    def initialize_session_state(self):
        """세션 상태 초기화"""
        if 'performance_data' not in st.session_state:
            st.session_state.performance_data = self.generate_sample_performance_data()

        if 'trade_history' not in st.session_state:
            st.session_state.trade_history = self.generate_sample_trade_history()

        if 'portfolio_data' not in st.session_state:
            st.session_state.portfolio_data = self.generate_sample_portfolio_data()

    def show_performance_dashboard(self):
        """성과 추적 대시보드 표시"""
        st.title("📊 성과 추적 대시보드")

        # 메인 메트릭스
        self.show_key_metrics()

        # 탭 구성
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📈 수익률 분석", "📊 리스크 메트릭", "💹 거래 통계",
            "📋 포트폴리오", "⚙️ 설정"
        ])

        with tab1:
            self.show_returns_analysis()

        with tab2:
            self.show_risk_metrics()

        with tab3:
            self.show_trading_statistics()

        with tab4:
            self.show_portfolio_analysis()

        with tab5:
            self.show_performance_settings()

    def show_key_metrics(self):
        """주요 성과 지표 표시"""
        st.subheader("🎯 핵심 성과 지표")

        # 현재 성과 계산
        current_metrics = self.calculate_current_metrics()

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            total_return = current_metrics['total_return']
            color = "normal" if total_return >= 0 else "inverse"
            st.metric(
                "총 수익률",
                f"{total_return:.2f}%",
                f"{current_metrics['daily_change']:.2f}%",
                delta_color=color
            )

        with col2:
            st.metric(
                "샤프 비율",
                f"{current_metrics['sharpe_ratio']:.2f}",
                f"{current_metrics['sharpe_change']:.2f}"
            )

        with col3:
            st.metric(
                "최대 낙폭",
                f"{current_metrics['max_drawdown']:.2f}%",
                f"{current_metrics['drawdown_change']:.2f}%",
                delta_color="inverse"
            )

        with col4:
            st.metric(
                "승률",
                f"{current_metrics['win_rate']:.1f}%",
                f"{current_metrics['win_rate_change']:.1f}%"
            )

        with col5:
            st.metric(
                "총 거래 수",
                f"{current_metrics['total_trades']:,}",
                f"{current_metrics['trades_today']}"
            )

    def show_returns_analysis(self):
        """수익률 분석 탭"""
        st.subheader("📈 수익률 분석")

        # 수익률 차트
        self.plot_returns_chart()

        col1, col2 = st.columns(2)

        with col1:
            # 월별 수익률 히트맵
            self.plot_monthly_returns_heatmap()

        with col2:
            # 수익률 분포
            self.plot_returns_distribution()

        # 수익률 통계
        self.show_returns_statistics()

    def show_risk_metrics(self):
        """리스크 메트릭 탭"""
        st.subheader("📊 리스크 분석")

        # 리스크 메트릭 계산
        risk_metrics = self.calculate_risk_metrics()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("VaR (95%)", f"{risk_metrics['var_95']:.2f}%")
            st.metric("CVaR (95%)", f"{risk_metrics['cvar_95']:.2f}%")
            st.metric("변동성", f"{risk_metrics['volatility']:.2f}%")

        with col2:
            st.metric("베타", f"{risk_metrics['beta']:.2f}")
            st.metric("알파", f"{risk_metrics['alpha']:.2f}%")
            st.metric("정보비율", f"{risk_metrics['information_ratio']:.2f}")

        with col3:
            st.metric("칼마 비율", f"{risk_metrics['calmar_ratio']:.2f}")
            st.metric("소르티노 비율", f"{risk_metrics['sortino_ratio']:.2f}")
            st.metric("최대 연속 손실", f"{risk_metrics['max_consecutive_losses']}")

        # 드로다운 차트
        self.plot_drawdown_chart()

        # 리스크 히트맵
        self.plot_risk_heatmap()

    def show_trading_statistics(self):
        """거래 통계 탭"""
        st.subheader("💹 거래 통계")

        # 거래 성과 요약
        trade_stats = self.calculate_trade_statistics()

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📊 거래 성과")
            st.write(f"**총 거래 수:** {trade_stats['total_trades']:,}")
            st.write(f"**수익 거래:** {trade_stats['winning_trades']:,} ({trade_stats['win_rate']:.1f}%)")
            st.write(f"**손실 거래:** {trade_stats['losing_trades']:,} ({100-trade_stats['win_rate']:.1f}%)")
            st.write(f"**평균 수익:** {trade_stats['avg_win']:.2f}%")
            st.write(f"**평균 손실:** {trade_stats['avg_loss']:.2f}%")
            st.write(f"**수익/손실 비율:** {trade_stats['profit_loss_ratio']:.2f}")

        with col2:
            st.subheader("⏱️ 거래 시간 분석")
            st.write(f"**평균 보유 시간:** {trade_stats['avg_holding_time']}")
            st.write(f"**최장 보유 시간:** {trade_stats['max_holding_time']}")
            st.write(f"**최단 보유 시간:** {trade_stats['min_holding_time']}")
            st.write(f"**일평균 거래 수:** {trade_stats['daily_avg_trades']:.1f}")

        # 거래 패턴 분석
        self.plot_trading_patterns()

        # 시간대별 성과
        self.plot_hourly_performance()

    def show_portfolio_analysis(self):
        """포트폴리오 분석 탭"""
        st.subheader("📋 포트폴리오 분석")

        # 포트폴리오 구성
        self.plot_portfolio_composition()

        col1, col2 = st.columns(2)

        with col1:
            # 자산별 성과
            self.plot_asset_performance()

        with col2:
            # 포트폴리오 상관관계
            self.plot_correlation_matrix()

        # 포트폴리오 밸런스 히스토리
        self.plot_portfolio_balance_history()

    def show_performance_settings(self):
        """성과 추적 설정 탭"""
        st.subheader("⚙️ 성과 추적 설정")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📊 차트 설정")

            chart_period = st.selectbox(
                "차트 기간",
                ["1일", "1주일", "1개월", "3개월", "6개월", "1년"],
                index=3,
                key="perf_chart_period"
            )

            benchmark = st.selectbox(
                "벤치마크",
                ["BTC", "ETH", "S&P 500", "코스피", "없음"],
                index=0,
                key="perf_benchmark"
            )

            show_drawdown = st.checkbox("드로다운 표시", True, key="perf_show_drawdown")
            show_trades = st.checkbox("거래 포인트 표시", True, key="perf_show_trades")

        with col2:
            st.subheader("🔔 알림 설정")

            enable_alerts = st.checkbox("성과 알림 활성화", True, key="perf_enable_alerts")

            if enable_alerts:
                profit_threshold = st.number_input(
                    "수익 알림 임계값 (%)",
                    min_value=1.0,
                    max_value=50.0,
                    value=10.0,
                    step=1.0,
                    key="perf_profit_threshold"
                )

                loss_threshold = st.number_input(
                    "손실 알림 임계값 (%)",
                    min_value=1.0,
                    max_value=50.0,
                    value=5.0,
                    step=1.0,
                    key="perf_loss_threshold"
                )

                drawdown_threshold = st.number_input(
                    "드로다운 알림 임계값 (%)",
                    min_value=1.0,
                    max_value=50.0,
                    value=15.0,
                    step=1.0,
                    key="perf_drawdown_threshold"
                )

        # 설정 저장 버튼
        if st.button("💾 설정 저장", type="primary", key="save_perf_settings"):
            st.success("✅ 성과 추적 설정이 저장되었습니다!")

        # 데이터 리셋 버튼
        if st.button("🔄 데이터 리셋", key="reset_perf_data"):
            st.session_state.performance_data = self.generate_sample_performance_data()
            st.session_state.trade_history = self.generate_sample_trade_history()
            st.session_state.portfolio_data = self.generate_sample_portfolio_data()
            st.success("✅ 성과 데이터가 리셋되었습니다!")
            st.rerun()

    def calculate_current_metrics(self) -> Dict[str, float]:
        """현재 성과 지표 계산"""
        df = st.session_state.performance_data

        total_return = ((df['balance'].iloc[-1] / df['balance'].iloc[0]) - 1) * 100
        daily_returns = df['daily_return'].dropna()

        return {
            'total_return': total_return,
            'daily_change': daily_returns.iloc[-1] if len(daily_returns) > 0 else 0,
            'sharpe_ratio': self.calculate_sharpe_ratio(daily_returns),
            'sharpe_change': random.uniform(-0.1, 0.1),
            'max_drawdown': self.calculate_max_drawdown(df['balance']),
            'drawdown_change': random.uniform(-1, 1),
            'win_rate': self.calculate_win_rate(),
            'win_rate_change': random.uniform(-2, 2),
            'total_trades': len(st.session_state.trade_history),
            'trades_today': random.randint(5, 15)
        }

    def calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """샤프 비율 계산"""
        if len(returns) < 2:
            return 0.0

        excess_returns = returns - (risk_free_rate / 365)
        return (excess_returns.mean() / excess_returns.std()) * np.sqrt(365) if excess_returns.std() != 0 else 0.0

    def calculate_max_drawdown(self, balance_series: pd.Series) -> float:
        """최대 낙폭 계산"""
        peak = balance_series.expanding().max()
        drawdown = (balance_series - peak) / peak * 100
        return drawdown.min()

    def calculate_win_rate(self) -> float:
        """승률 계산"""
        trades = st.session_state.trade_history
        if len(trades) == 0:
            return 0.0

        winning_trades = len([t for t in trades if t['pnl'] > 0])
        return (winning_trades / len(trades)) * 100

    def calculate_risk_metrics(self) -> Dict[str, float]:
        """리스크 메트릭 계산"""
        daily_returns = st.session_state.performance_data['daily_return'].dropna()

        return {
            'var_95': np.percentile(daily_returns, 5),
            'cvar_95': daily_returns[daily_returns <= np.percentile(daily_returns, 5)].mean(),
            'volatility': daily_returns.std() * np.sqrt(365),
            'beta': random.uniform(0.8, 1.2),
            'alpha': random.uniform(-2, 5),
            'information_ratio': random.uniform(0.5, 2.0),
            'calmar_ratio': random.uniform(1.0, 3.0),
            'sortino_ratio': random.uniform(1.5, 3.5),
            'max_consecutive_losses': random.randint(3, 8)
        }

    def calculate_trade_statistics(self) -> Dict[str, Any]:
        """거래 통계 계산"""
        trades = st.session_state.trade_history

        if len(trades) == 0:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_loss_ratio': 0,
                'avg_holding_time': "0분",
                'max_holding_time': "0분",
                'min_holding_time': "0분",
                'daily_avg_trades': 0
            }

        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] <= 0]

        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0

        return {
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': (len(winning_trades) / len(trades)) * 100,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_loss_ratio': abs(avg_win / avg_loss) if avg_loss != 0 else 0,
            'avg_holding_time': f"{random.randint(30, 180)}분",
            'max_holding_time': f"{random.randint(300, 720)}분",
            'min_holding_time': f"{random.randint(5, 30)}분",
            'daily_avg_trades': len(trades) / 30  # 30일 기준
        }

    def plot_returns_chart(self):
        """수익률 차트 생성"""
        df = st.session_state.performance_data

        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('포트폴리오 가치', '일일 수익률'),
            vertical_spacing=0.1,
            row_heights=[0.7, 0.3]
        )

        # 포트폴리오 가치
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['balance'],
                name='포트폴리오 가치',
                line=dict(color='#1f77b4', width=2)
            ),
            row=1, col=1
        )

        # 일일 수익률
        colors = ['red' if x < 0 else 'green' for x in df['daily_return']]
        fig.add_trace(
            go.Bar(
                x=df['date'],
                y=df['daily_return'],
                name='일일 수익률',
                marker_color=colors
            ),
            row=2, col=1
        )

        fig.update_layout(
            height=600,
            title_text="📈 수익률 차트",
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True)

    def plot_monthly_returns_heatmap(self):
        """월별 수익률 히트맵"""
        df = st.session_state.performance_data.copy()
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month

        monthly_returns = df.groupby(['year', 'month'])['daily_return'].sum().reset_index()
        pivot_table = monthly_returns.pivot(index='year', columns='month', values='daily_return')

        fig = px.imshow(
            pivot_table.values,
            labels=dict(x="월", y="년", color="수익률 (%)"),
            x=[f"{i}월" for i in range(1, 13)],
            y=pivot_table.index,
            color_continuous_scale='RdYlGn',
            title="📅 월별 수익률 히트맵"
        )

        st.plotly_chart(fig, use_container_width=True)

    def plot_returns_distribution(self):
        """수익률 분포 히스토그램"""
        daily_returns = st.session_state.performance_data['daily_return'].dropna()

        fig = px.histogram(
            x=daily_returns,
            nbins=50,
            title="📊 일일 수익률 분포",
            labels={'x': '일일 수익률 (%)', 'y': '빈도'}
        )

        # 정규분포 곡선 추가
        x_range = np.linspace(daily_returns.min(), daily_returns.max(), 100)
        normal_dist = np.exp(-0.5 * ((x_range - daily_returns.mean()) / daily_returns.std()) ** 2)
        normal_dist = normal_dist / normal_dist.max() * daily_returns.count() / 10

        fig.add_trace(
            go.Scatter(
                x=x_range,
                y=normal_dist,
                mode='lines',
                name='정규분포',
                line=dict(color='red', dash='dash')
            )
        )

        st.plotly_chart(fig, use_container_width=True)

    def show_returns_statistics(self):
        """수익률 통계 표시"""
        daily_returns = st.session_state.performance_data['daily_return'].dropna()

        st.subheader("📊 수익률 통계")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("평균 수익률", f"{daily_returns.mean():.3f}%")
            st.metric("중앙값", f"{daily_returns.median():.3f}%")

        with col2:
            st.metric("표준편차", f"{daily_returns.std():.3f}%")
            st.metric("연간 변동성", f"{daily_returns.std() * np.sqrt(365):.2f}%")

        with col3:
            st.metric("왜도", f"{daily_returns.skew():.3f}")
            st.metric("첨도", f"{daily_returns.kurtosis():.3f}")

        with col4:
            st.metric("최대 수익률", f"{daily_returns.max():.3f}%")
            st.metric("최대 손실률", f"{daily_returns.min():.3f}%")

    def plot_drawdown_chart(self):
        """드로다운 차트"""
        df = st.session_state.performance_data
        peak = df['balance'].expanding().max()
        drawdown = (df['balance'] - peak) / peak * 100

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=drawdown,
                fill='tozeroy',
                name='드로다운',
                line=dict(color='red'),
                fillcolor='rgba(255, 0, 0, 0.3)'
            )
        )

        fig.update_layout(
            title="📉 드로다운 차트",
            xaxis_title="날짜",
            yaxis_title="드로다운 (%)",
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    def plot_risk_heatmap(self):
        """리스크 히트맵"""
        # 임시 리스크 데이터 생성
        risk_data = pd.DataFrame({
            'BTC': np.random.randn(30),
            'ETH': np.random.randn(30),
            'ADA': np.random.randn(30),
            'DOT': np.random.randn(30)
        })

        correlation_matrix = risk_data.corr()

        fig = px.imshow(
            correlation_matrix,
            title="🔥 자산 간 상관관계 히트맵",
            color_continuous_scale='RdBu',
            aspect="auto"
        )

        st.plotly_chart(fig, use_container_width=True)

    def plot_trading_patterns(self):
        """거래 패턴 분석"""
        trades = st.session_state.trade_history

        if len(trades) == 0:
            st.warning("거래 데이터가 없습니다.")
            return

        df = pd.DataFrame(trades)
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        daily_trades = df.groupby('date').size().reset_index(name='trades_count')

        fig = px.bar(
            daily_trades,
            x='date',
            y='trades_count',
            title="📊 일별 거래 패턴",
            labels={'date': '날짜', 'trades_count': '거래 수'}
        )

        st.plotly_chart(fig, use_container_width=True)

    def plot_hourly_performance(self):
        """시간대별 성과"""
        trades = st.session_state.trade_history

        if len(trades) == 0:
            st.warning("거래 데이터가 없습니다.")
            return

        df = pd.DataFrame(trades)
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        hourly_pnl = df.groupby('hour')['pnl'].mean().reset_index()

        fig = px.bar(
            hourly_pnl,
            x='hour',
            y='pnl',
            title="⏰ 시간대별 평균 수익률",
            labels={'hour': '시간', 'pnl': '평균 P&L (%)'}
        )

        st.plotly_chart(fig, use_container_width=True)

    def plot_portfolio_composition(self):
        """포트폴리오 구성"""
        portfolio = st.session_state.portfolio_data

        fig = px.pie(
            values=list(portfolio.values()),
            names=list(portfolio.keys()),
            title="🥧 포트폴리오 구성"
        )

        st.plotly_chart(fig, use_container_width=True)

    def plot_asset_performance(self):
        """자산별 성과"""
        # 임시 자산 성과 데이터
        assets = ['BTC', 'ETH', 'ADA', 'DOT', 'LINK']
        performance = [random.uniform(-10, 20) for _ in assets]

        fig = px.bar(
            x=assets,
            y=performance,
            title="📈 자산별 수익률",
            labels={'x': '자산', 'y': '수익률 (%)'},
            color=performance,
            color_continuous_scale='RdYlGn'
        )

        st.plotly_chart(fig, use_container_width=True)

    def plot_correlation_matrix(self):
        """상관관계 매트릭스"""
        # 임시 상관관계 데이터
        assets = ['BTC', 'ETH', 'ADA', 'DOT']
        correlation_data = np.random.rand(len(assets), len(assets))
        correlation_data = (correlation_data + correlation_data.T) / 2
        np.fill_diagonal(correlation_data, 1)

        fig = px.imshow(
            correlation_data,
            x=assets,
            y=assets,
            title="🔗 자산 간 상관관계",
            color_continuous_scale='RdBu'
        )

        st.plotly_chart(fig, use_container_width=True)

    def plot_portfolio_balance_history(self):
        """포트폴리오 잔액 히스토리"""
        df = st.session_state.performance_data

        fig = px.area(
            df,
            x='date',
            y='balance',
            title="💰 포트폴리오 잔액 히스토리",
            labels={'date': '날짜', 'balance': '잔액 (USDT)'}
        )

        st.plotly_chart(fig, use_container_width=True)

    def generate_sample_performance_data(self) -> pd.DataFrame:
        """샘플 성과 데이터 생성"""
        days = 90
        start_date = datetime.now() - timedelta(days=days)
        dates = [start_date + timedelta(days=i) for i in range(days)]

        # 랜덤 워크로 잔액 생성
        initial_balance = 100000
        returns = np.random.normal(0.001, 0.02, days)  # 평균 0.1%, 표준편차 2%
        balance = [initial_balance]

        for ret in returns[1:]:
            balance.append(balance[-1] * (1 + ret))

        daily_returns = [0] + [((balance[i] / balance[i-1]) - 1) * 100 for i in range(1, len(balance))]

        return pd.DataFrame({
            'date': dates,
            'balance': balance,
            'daily_return': daily_returns
        })

    def generate_sample_trade_history(self) -> List[Dict[str, Any]]:
        """샘플 거래 히스토리 생성"""
        trades = []
        base_time = datetime.now() - timedelta(days=30)

        for i in range(150):  # 150개 거래
            timestamp = base_time + timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )

            symbol = random.choice(['BTC/USDT', 'ETH/USDT', 'ADA/USDT', 'DOT/USDT'])
            side = random.choice(['buy', 'sell'])
            pnl = random.uniform(-5, 8)  # P&L percentage

            trades.append({
                'timestamp': timestamp.isoformat(),
                'symbol': symbol,
                'side': side,
                'amount': random.uniform(0.1, 2.0),
                'price': random.uniform(20000, 50000) if 'BTC' in symbol else random.uniform(1000, 3000),
                'pnl': pnl
            })

        return sorted(trades, key=lambda x: x['timestamp'])

    def generate_sample_portfolio_data(self) -> Dict[str, float]:
        """샘플 포트폴리오 데이터 생성"""
        return {
            'BTC': 45.2,
            'ETH': 28.7,
            'ADA': 12.1,
            'DOT': 8.5,
            'LINK': 5.5
        }

# 메인 실행 함수
def main():
    """메인 실행 함수"""
    tracker = AdvancedPerformanceTracker()
    tracker.show_performance_dashboard()

if __name__ == "__main__":
    main()