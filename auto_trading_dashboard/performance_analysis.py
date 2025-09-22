"""
📈 Phase 5 종합 성과 분석 모듈 (Comprehensive Performance Analysis)
거래 성과, 리스크 메트릭, 포트폴리오 분석, 벤치마킹, 성과 리포트 생성
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import statistics
import math
from dataclasses import dataclass
from enum import Enum
import io
import base64

class AnalysisPeriod(Enum):
    """분석 기간"""
    DAILY = "일별"
    WEEKLY = "주별"
    MONTHLY = "월별"
    QUARTERLY = "분기별"
    YEARLY = "연별"

class BenchmarkType(Enum):
    """벤치마크 유형"""
    BTC = "Bitcoin"
    ETH = "Ethereum"
    SPY = "S&P 500"
    MARKET_INDEX = "Market Index"
    CUSTOM = "사용자 정의"

@dataclass
class PerformanceMetrics:
    """성과 지표 클래스"""
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    var_95: float
    cvar_95: float
    alpha: float
    beta: float
    information_ratio: float

class ComprehensivePerformanceAnalysis:
    """📈 Phase 5 종합 성과 분석 시스템"""

    def __init__(self):
        self.initialize_session_state()

    def initialize_session_state(self):
        """세션 상태 초기화"""
        if 'trading_data' not in st.session_state:
            st.session_state.trading_data = self.generate_sample_trading_data()

        if 'benchmark_data' not in st.session_state:
            st.session_state.benchmark_data = self.generate_benchmark_data()

        if 'analysis_settings' not in st.session_state:
            st.session_state.analysis_settings = self.get_default_analysis_settings()

        if 'performance_reports' not in st.session_state:
            st.session_state.performance_reports = []

    def show_performance_analysis_dashboard(self):
        """성과 분석 대시보드 표시"""
        st.title("📈 종합 성과 분석")
        st.markdown("**Phase 5: 고급 성과 분석 및 벤치마킹 시스템**")

        # 분석 설정 패널
        self.show_analysis_settings()

        # 탭 구성
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 성과 개요", "📈 수익률 분석", "📉 리스크 분석",
            "🏆 벤치마킹", "📋 상세 리포트", "⚙️ 설정"
        ])

        with tab1:
            self.show_performance_overview()

        with tab2:
            self.show_returns_analysis()

        with tab3:
            self.show_risk_analysis()

        with tab4:
            self.show_benchmarking_analysis()

        with tab5:
            self.show_detailed_reports()

        with tab6:
            self.show_analysis_settings_tab()

    def show_analysis_settings(self):
        """분석 설정 패널"""
        with st.expander("⚙️ 분석 설정", expanded=False):
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                analysis_period = st.selectbox(
                    "분석 기간",
                    [period.value for period in AnalysisPeriod],
                    index=2,  # 월별
                    key="analysis_period_select"
                )

            with col2:
                start_date = st.date_input(
                    "시작 날짜",
                    value=datetime.now() - timedelta(days=365),
                    key="analysis_start_date"
                )

            with col3:
                end_date = st.date_input(
                    "종료 날짜",
                    value=datetime.now(),
                    key="analysis_end_date"
                )

            with col4:
                benchmark = st.selectbox(
                    "벤치마크",
                    [bench.value for bench in BenchmarkType],
                    index=0,  # BTC
                    key="benchmark_select"
                )

            # 설정 업데이트
            st.session_state.analysis_settings.update({
                'period': analysis_period,
                'start_date': start_date,
                'end_date': end_date,
                'benchmark': benchmark
            })

    def show_performance_overview(self):
        """성과 개요 탭"""
        st.subheader("📊 성과 개요")

        # 핵심 지표 카드
        metrics = self.calculate_performance_metrics()
        self.show_key_metrics_cards(metrics)

        st.divider()

        # 성과 요약 차트
        col1, col2 = st.columns(2)

        with col1:
            self.plot_equity_curve()

        with col2:
            self.plot_monthly_returns_heatmap()

        st.divider()

        # 거래 요약
        self.show_trading_summary()

    def show_key_metrics_cards(self, metrics: PerformanceMetrics):
        """핵심 지표 카드 표시"""
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric(
                "총 수익률",
                f"{metrics.total_return:.2f}%",
                delta=f"{metrics.total_return - 10:.2f}% vs 목표"
            )

        with col2:
            st.metric(
                "연간 수익률",
                f"{metrics.annualized_return:.2f}%",
                delta=f"{metrics.annualized_return - 15:.2f}% vs 목표"
            )

        with col3:
            color = "normal" if metrics.sharpe_ratio > 1.0 else "inverse"
            st.metric(
                "샤프 비율",
                f"{metrics.sharpe_ratio:.2f}",
                delta=f"{metrics.sharpe_ratio - 1.0:.2f}",
                delta_color=color
            )

        with col4:
            color = "inverse" if metrics.max_drawdown < -10 else "normal"
            st.metric(
                "최대 낙폭",
                f"{metrics.max_drawdown:.2f}%",
                delta=f"{metrics.max_drawdown + 5:.2f}% vs 목표",
                delta_color=color
            )

        with col5:
            color = "normal" if metrics.win_rate > 60 else "inverse"
            st.metric(
                "승률",
                f"{metrics.win_rate:.1f}%",
                delta=f"{metrics.win_rate - 60:.1f}% vs 목표",
                delta_color=color
            )

        # 추가 지표
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("변동성", f"{metrics.volatility:.2f}%")

        with col2:
            st.metric("소르티노 비율", f"{metrics.sortino_ratio:.2f}")

        with col3:
            st.metric("칼마 비율", f"{metrics.calmar_ratio:.2f}")

        with col4:
            st.metric("VaR (95%)", f"{metrics.var_95:.2f}%")

        with col5:
            st.metric("수익 팩터", f"{metrics.profit_factor:.2f}")

    def plot_equity_curve(self):
        """자산 곡선 플롯"""
        data = st.session_state.trading_data

        fig = go.Figure()

        # 포트폴리오 가치
        fig.add_trace(go.Scatter(
            x=data['date'],
            y=data['portfolio_value'],
            mode='lines',
            name='포트폴리오',
            line=dict(color='blue', width=2)
        ))

        # 벤치마크 (선택사항)
        if st.session_state.analysis_settings.get('show_benchmark', True):
            benchmark_data = st.session_state.benchmark_data
            fig.add_trace(go.Scatter(
                x=benchmark_data['date'],
                y=benchmark_data['value'],
                mode='lines',
                name='벤치마크 (BTC)',
                line=dict(color='orange', width=2, dash='dash')
            ))

        fig.update_layout(
            title="📈 자산 곡선 (Equity Curve)",
            xaxis_title="날짜",
            yaxis_title="가치 ($)",
            height=400,
            hovermode='x unified'
        )

        st.plotly_chart(fig, use_container_width=True)

    def plot_monthly_returns_heatmap(self):
        """월별 수익률 히트맵"""
        data = st.session_state.trading_data.copy()
        data['year'] = data['date'].dt.year
        data['month'] = data['date'].dt.month

        # 월별 수익률 계산
        monthly_returns = data.groupby(['year', 'month'])['daily_return'].sum().reset_index()

        if len(monthly_returns) > 0:
            pivot_table = monthly_returns.pivot(index='year', columns='month', values='daily_return')

            fig = px.imshow(
                pivot_table.fillna(0),
                labels=dict(x="월", y="년", color="수익률 (%)"),
                x=[f"{i}월" for i in range(1, 13)],
                y=pivot_table.index,
                color_continuous_scale='RdYlGn',
                title="📅 월별 수익률 히트맵",
                aspect="auto"
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("월별 수익률 데이터가 충분하지 않습니다.")

    def show_trading_summary(self):
        """거래 요약"""
        st.subheader("💼 거래 요약")

        trades_data = self.get_trades_summary()

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 📊 거래 통계")

            summary_df = pd.DataFrame([
                ["총 거래 수", f"{trades_data['total_trades']:,}"],
                ["수익 거래", f"{trades_data['winning_trades']:,}"],
                ["손실 거래", f"{trades_data['losing_trades']:,}"],
                ["승률", f"{trades_data['win_rate']:.1f}%"],
                ["평균 수익", f"${trades_data['avg_win']:.2f}"],
                ["평균 손실", f"${trades_data['avg_loss']:.2f}"],
                ["수익/손실 비율", f"{trades_data['profit_loss_ratio']:.2f}"],
                ["최대 연속 승리", f"{trades_data['max_consecutive_wins']}"],
                ["최대 연속 손실", f"{trades_data['max_consecutive_losses']}"]
            ], columns=["항목", "값"])

            st.dataframe(summary_df, hide_index=True, use_container_width=True)

        with col2:
            # 거래 분포 차트
            fig = go.Figure(data=[
                go.Bar(name='수익 거래', x=['거래 결과'], y=[trades_data['winning_trades']], marker_color='green'),
                go.Bar(name='손실 거래', x=['거래 결과'], y=[trades_data['losing_trades']], marker_color='red')
            ])

            fig.update_layout(
                title="거래 결과 분포",
                barmode='group',
                height=300
            )

            st.plotly_chart(fig, use_container_width=True)

    def show_returns_analysis(self):
        """수익률 분석 탭"""
        st.subheader("📈 수익률 분석")

        # 수익률 분포 분석
        col1, col2 = st.columns(2)

        with col1:
            self.plot_returns_distribution()

        with col2:
            self.plot_rolling_returns()

        st.divider()

        # 기간별 수익률 분석
        self.show_period_returns_analysis()

        st.divider()

        # 수익률 통계
        self.show_returns_statistics()

    def plot_returns_distribution(self):
        """수익률 분포 플롯"""
        data = st.session_state.trading_data
        returns = data['daily_return'].dropna()

        fig = go.Figure()

        # 히스토그램
        fig.add_trace(go.Histogram(
            x=returns,
            nbinsx=50,
            name='수익률 분포',
            opacity=0.7
        ))

        # 정규분포 곡선
        x_range = np.linspace(returns.min(), returns.max(), 100)
        normal_curve = np.exp(-0.5 * ((x_range - returns.mean()) / returns.std()) ** 2)
        normal_curve = normal_curve / normal_curve.max() * len(returns) / 10

        fig.add_trace(go.Scatter(
            x=x_range,
            y=normal_curve,
            mode='lines',
            name='정규분포',
            line=dict(color='red', dash='dash')
        ))

        fig.update_layout(
            title="📊 일일 수익률 분포",
            xaxis_title="수익률 (%)",
            yaxis_title="빈도",
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    def plot_rolling_returns(self):
        """롤링 수익률 플롯"""
        data = st.session_state.trading_data.copy()

        # 롤링 수익률 계산
        data['rolling_30d'] = data['daily_return'].rolling(window=30).mean()
        data['rolling_90d'] = data['daily_return'].rolling(window=90).mean()

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=data['date'],
            y=data['rolling_30d'],
            mode='lines',
            name='30일 평균',
            line=dict(color='blue', width=1)
        ))

        fig.add_trace(go.Scatter(
            x=data['date'],
            y=data['rolling_90d'],
            mode='lines',
            name='90일 평균',
            line=dict(color='red', width=2)
        ))

        fig.update_layout(
            title="📈 롤링 평균 수익률",
            xaxis_title="날짜",
            yaxis_title="평균 수익률 (%)",
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    def show_period_returns_analysis(self):
        """기간별 수익률 분석"""
        st.subheader("📅 기간별 수익률")

        data = st.session_state.trading_data.copy()

        # 기간별 수익률 계산
        period_returns = self.calculate_period_returns(data)

        # 테이블 표시
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 📊 기간별 통계")
            period_stats_df = pd.DataFrame([
                ["일별 평균", f"{period_returns['daily']['mean']:.3f}%"],
                ["주별 평균", f"{period_returns['weekly']['mean']:.2f}%"],
                ["월별 평균", f"{period_returns['monthly']['mean']:.2f}%"],
                ["분기별 평균", f"{period_returns['quarterly']['mean']:.2f}%"],
                ["연별 평균", f"{period_returns['yearly']['mean']:.2f}%"]
            ], columns=["기간", "평균 수익률"])

            st.dataframe(period_stats_df, hide_index=True)

        with col2:
            st.markdown("#### 📈 변동성 분석")
            volatility_df = pd.DataFrame([
                ["일별 변동성", f"{period_returns['daily']['std']:.3f}%"],
                ["주별 변동성", f"{period_returns['weekly']['std']:.2f}%"],
                ["월별 변동성", f"{period_returns['monthly']['std']:.2f}%"],
                ["연간 변동성", f"{period_returns['daily']['std'] * np.sqrt(252):.2f}%"]
            ], columns=["기간", "변동성"])

            st.dataframe(volatility_df, hide_index=True)

        # 기간별 수익률 차트
        self.plot_period_returns_chart(period_returns)

    def show_returns_statistics(self):
        """수익률 통계"""
        st.subheader("📊 수익률 상세 통계")

        data = st.session_state.trading_data
        returns = data['daily_return'].dropna()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("#### 📈 기본 통계")
            basic_stats = pd.DataFrame([
                ["평균", f"{returns.mean():.4f}%"],
                ["중앙값", f"{returns.median():.4f}%"],
                ["표준편차", f"{returns.std():.4f}%"],
                ["최솟값", f"{returns.min():.4f}%"],
                ["최댓값", f"{returns.max():.4f}%"]
            ], columns=["통계", "값"])

            st.dataframe(basic_stats, hide_index=True)

        with col2:
            st.markdown("#### 📊 분포 통계")
            dist_stats = pd.DataFrame([
                ["왜도", f"{returns.skew():.4f}"],
                ["첨도", f"{returns.kurtosis():.4f}"],
                ["5% VaR", f"{returns.quantile(0.05):.4f}%"],
                ["95% VaR", f"{returns.quantile(0.95):.4f}%"]
            ], columns=["통계", "값"])

            st.dataframe(dist_stats, hide_index=True)

        with col3:
            st.markdown("#### 🎯 위험 조정 수익률")
            risk_adjusted = pd.DataFrame([
                ["샤프 비율", f"{self.calculate_sharpe_ratio(returns):.4f}"],
                ["소르티노 비율", f"{self.calculate_sortino_ratio(returns):.4f}"],
                ["칼마 비율", f"{self.calculate_calmar_ratio(returns):.4f}"],
                ["정보 비율", f"{self.calculate_information_ratio(returns):.4f}"]
            ], columns=["지표", "값"])

            st.dataframe(risk_adjusted, hide_index=True)

    def show_risk_analysis(self):
        """리스크 분석 탭"""
        st.subheader("📉 리스크 분석")

        # 드로다운 분석
        col1, col2 = st.columns(2)

        with col1:
            self.plot_drawdown_analysis()

        with col2:
            self.plot_var_analysis()

        st.divider()

        # 리스크 지표 요약
        self.show_risk_metrics_summary()

        st.divider()

        # 상관관계 분석
        self.show_correlation_analysis()

    def plot_drawdown_analysis(self):
        """드로다운 분석 플롯"""
        data = st.session_state.trading_data.copy()

        # 드로다운 계산
        peak = data['portfolio_value'].expanding().max()
        drawdown = (data['portfolio_value'] - peak) / peak * 100

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=data['date'],
            y=drawdown,
            fill='tozeroy',
            name='드로다운',
            line=dict(color='red'),
            fillcolor='rgba(255, 0, 0, 0.3)'
        ))

        # 최대 드로다운 표시
        max_dd_idx = drawdown.idxmin()
        max_dd_value = drawdown.min()

        fig.add_trace(go.Scatter(
            x=[data.loc[max_dd_idx, 'date']],
            y=[max_dd_value],
            mode='markers',
            name=f'최대 드로다운: {max_dd_value:.2f}%',
            marker=dict(color='red', size=10, symbol='circle')
        ))

        fig.update_layout(
            title="📉 드로다운 분석",
            xaxis_title="날짜",
            yaxis_title="드로다운 (%)",
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    def plot_var_analysis(self):
        """VaR 분석 플롯"""
        data = st.session_state.trading_data
        returns = data['daily_return'].dropna()

        # VaR 계산
        var_95 = returns.quantile(0.05)
        var_99 = returns.quantile(0.01)

        fig = go.Figure()

        # 히스토그램
        fig.add_trace(go.Histogram(
            x=returns,
            nbinsx=50,
            name='수익률 분포',
            opacity=0.7
        ))

        # VaR 라인
        fig.add_vline(
            x=var_95,
            line_dash="dash",
            line_color="red",
            annotation_text=f"VaR 95%: {var_95:.2f}%"
        )

        fig.add_vline(
            x=var_99,
            line_dash="dash",
            line_color="darkred",
            annotation_text=f"VaR 99%: {var_99:.2f}%"
        )

        fig.update_layout(
            title="📊 Value at Risk (VaR) 분석",
            xaxis_title="수익률 (%)",
            yaxis_title="빈도",
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    def show_risk_metrics_summary(self):
        """리스크 지표 요약"""
        st.subheader("📊 리스크 지표 요약")

        data = st.session_state.trading_data
        returns = data['daily_return'].dropna()
        portfolio_values = data['portfolio_value']

        # 리스크 지표 계산
        risk_metrics = self.calculate_comprehensive_risk_metrics(returns, portfolio_values)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("#### 📉 드로다운 지표")
            dd_metrics = pd.DataFrame([
                ["최대 드로다운", f"{risk_metrics['max_drawdown']:.2f}%"],
                ["평균 드로다운", f"{risk_metrics['avg_drawdown']:.2f}%"],
                ["드로다운 기간", f"{risk_metrics['drawdown_duration']}일"],
                ["회복 기간", f"{risk_metrics['recovery_time']}일"]
            ], columns=["지표", "값"])

            st.dataframe(dd_metrics, hide_index=True)

        with col2:
            st.markdown("#### 📊 VaR 지표")
            var_metrics = pd.DataFrame([
                ["VaR 95%", f"{risk_metrics['var_95']:.2f}%"],
                ["VaR 99%", f"{risk_metrics['var_99']:.2f}%"],
                ["CVaR 95%", f"{risk_metrics['cvar_95']:.2f}%"],
                ["CVaR 99%", f"{risk_metrics['cvar_99']:.2f}%"]
            ], columns=["지표", "값"])

            st.dataframe(var_metrics, hide_index=True)

        with col3:
            st.markdown("#### 📈 변동성 지표")
            vol_metrics = pd.DataFrame([
                ["일일 변동성", f"{risk_metrics['daily_volatility']:.2f}%"],
                ["연간 변동성", f"{risk_metrics['annual_volatility']:.2f}%"],
                ["하방 편차", f"{risk_metrics['downside_deviation']:.2f}%"],
                ["상방 편차", f"{risk_metrics['upside_deviation']:.2f}%"]
            ], columns=["지표", "값"])

            st.dataframe(vol_metrics, hide_index=True)

    def show_correlation_analysis(self):
        """상관관계 분석"""
        st.subheader("🔗 상관관계 분석")

        # 포트폴리오와 벤치마크 간 상관관계
        portfolio_returns = st.session_state.trading_data['daily_return'].dropna()
        benchmark_returns = st.session_state.benchmark_data['daily_return'].dropna()

        # 데이터 길이 맞추기
        min_length = min(len(portfolio_returns), len(benchmark_returns))
        portfolio_returns = portfolio_returns.iloc[-min_length:]
        benchmark_returns = benchmark_returns.iloc[-min_length:]

        correlation = portfolio_returns.corr(benchmark_returns)

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "포트폴리오 vs 벤치마크 상관관계",
                f"{correlation:.4f}",
                delta="낮은 상관관계" if abs(correlation) < 0.5 else "높은 상관관계"
            )

            # 베타 계산
            beta = np.cov(portfolio_returns, benchmark_returns)[0, 1] / np.var(benchmark_returns)
            st.metric("베타 (β)", f"{beta:.4f}")

            # 알파 계산 (간단한 버전)
            alpha = portfolio_returns.mean() - beta * benchmark_returns.mean()
            st.metric("알파 (α)", f"{alpha:.4f}%")

        with col2:
            # 산점도
            fig = px.scatter(
                x=benchmark_returns,
                y=portfolio_returns,
                title="포트폴리오 vs 벤치마크 상관관계",
                labels={'x': '벤치마크 수익률 (%)', 'y': '포트폴리오 수익률 (%)'},
                trendline="ols"
            )

            st.plotly_chart(fig, use_container_width=True)

    def show_benchmarking_analysis(self):
        """벤치마킹 분석 탭"""
        st.subheader("🏆 벤치마킹 분석")

        # 성과 비교 차트
        self.plot_performance_comparison()

        st.divider()

        # 비교 지표 테이블
        self.show_comparison_metrics()

        st.divider()

        # 롤링 비교 분석
        self.show_rolling_comparison()

    def plot_performance_comparison(self):
        """성과 비교 차트"""
        portfolio_data = st.session_state.trading_data
        benchmark_data = st.session_state.benchmark_data

        fig = go.Figure()

        # 정규화된 성과 (시작점을 100으로)
        portfolio_normalized = (portfolio_data['portfolio_value'] / portfolio_data['portfolio_value'].iloc[0]) * 100
        benchmark_normalized = (benchmark_data['value'] / benchmark_data['value'].iloc[0]) * 100

        fig.add_trace(go.Scatter(
            x=portfolio_data['date'],
            y=portfolio_normalized,
            mode='lines',
            name='포트폴리오',
            line=dict(color='blue', width=2)
        ))

        fig.add_trace(go.Scatter(
            x=benchmark_data['date'],
            y=benchmark_normalized,
            mode='lines',
            name='벤치마크 (BTC)',
            line=dict(color='orange', width=2, dash='dash')
        ))

        fig.update_layout(
            title="📊 성과 비교 (정규화)",
            xaxis_title="날짜",
            yaxis_title="정규화된 가치",
            height=500,
            hovermode='x unified'
        )

        st.plotly_chart(fig, use_container_width=True)

    def show_comparison_metrics(self):
        """비교 지표 테이블"""
        st.subheader("📊 성과 지표 비교")

        # 포트폴리오 지표
        portfolio_metrics = self.calculate_performance_metrics()

        # 벤치마크 지표 (간단 계산)
        benchmark_data = st.session_state.benchmark_data
        benchmark_returns = benchmark_data['daily_return'].dropna()

        benchmark_metrics = PerformanceMetrics(
            total_return=((benchmark_data['value'].iloc[-1] / benchmark_data['value'].iloc[0]) - 1) * 100,
            annualized_return=self.calculate_annualized_return(benchmark_returns),
            volatility=benchmark_returns.std() * np.sqrt(252),
            sharpe_ratio=self.calculate_sharpe_ratio(benchmark_returns),
            sortino_ratio=self.calculate_sortino_ratio(benchmark_returns),
            calmar_ratio=self.calculate_calmar_ratio(benchmark_returns),
            max_drawdown=self.calculate_max_drawdown(benchmark_data['value']),
            win_rate=len(benchmark_returns[benchmark_returns > 0]) / len(benchmark_returns) * 100,
            profit_factor=0.0,  # 간단화
            var_95=benchmark_returns.quantile(0.05),
            cvar_95=benchmark_returns[benchmark_returns <= benchmark_returns.quantile(0.05)].mean(),
            alpha=0.0,  # 간단화
            beta=1.0,   # 간단화
            information_ratio=0.0  # 간단화
        )

        # 비교 테이블 생성
        comparison_df = pd.DataFrame({
            '지표': [
                '총 수익률 (%)',
                '연간 수익률 (%)',
                '변동성 (%)',
                '샤프 비율',
                '소르티노 비율',
                '최대 낙폭 (%)',
                '승률 (%)',
                'VaR 95% (%)'
            ],
            '포트폴리오': [
                f"{portfolio_metrics.total_return:.2f}",
                f"{portfolio_metrics.annualized_return:.2f}",
                f"{portfolio_metrics.volatility:.2f}",
                f"{portfolio_metrics.sharpe_ratio:.2f}",
                f"{portfolio_metrics.sortino_ratio:.2f}",
                f"{portfolio_metrics.max_drawdown:.2f}",
                f"{portfolio_metrics.win_rate:.1f}",
                f"{portfolio_metrics.var_95:.2f}"
            ],
            '벤치마크': [
                f"{benchmark_metrics.total_return:.2f}",
                f"{benchmark_metrics.annualized_return:.2f}",
                f"{benchmark_metrics.volatility:.2f}",
                f"{benchmark_metrics.sharpe_ratio:.2f}",
                f"{benchmark_metrics.sortino_ratio:.2f}",
                f"{benchmark_metrics.max_drawdown:.2f}",
                f"{benchmark_metrics.win_rate:.1f}",
                f"{benchmark_metrics.var_95:.2f}"
            ],
            '차이': [
                f"{portfolio_metrics.total_return - benchmark_metrics.total_return:+.2f}",
                f"{portfolio_metrics.annualized_return - benchmark_metrics.annualized_return:+.2f}",
                f"{portfolio_metrics.volatility - benchmark_metrics.volatility:+.2f}",
                f"{portfolio_metrics.sharpe_ratio - benchmark_metrics.sharpe_ratio:+.2f}",
                f"{portfolio_metrics.sortino_ratio - benchmark_metrics.sortino_ratio:+.2f}",
                f"{portfolio_metrics.max_drawdown - benchmark_metrics.max_drawdown:+.2f}",
                f"{portfolio_metrics.win_rate - benchmark_metrics.win_rate:+.1f}",
                f"{portfolio_metrics.var_95 - benchmark_metrics.var_95:+.2f}"
            ]
        })

        st.dataframe(comparison_df, hide_index=True, use_container_width=True)

    def show_rolling_comparison(self):
        """롤링 비교 분석"""
        st.subheader("📈 롤링 성과 비교")

        portfolio_data = st.session_state.trading_data.copy()
        benchmark_data = st.session_state.benchmark_data.copy()

        # 롤링 샤프 비율 계산
        window = 30
        portfolio_data['rolling_sharpe'] = portfolio_data['daily_return'].rolling(window).apply(
            lambda x: self.calculate_sharpe_ratio(x) if len(x) == window else np.nan
        )
        benchmark_data['rolling_sharpe'] = benchmark_data['daily_return'].rolling(window).apply(
            lambda x: self.calculate_sharpe_ratio(x) if len(x) == window else np.nan
        )

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=portfolio_data['date'],
            y=portfolio_data['rolling_sharpe'],
            mode='lines',
            name='포트폴리오 샤프 비율',
            line=dict(color='blue')
        ))

        fig.add_trace(go.Scatter(
            x=benchmark_data['date'],
            y=benchmark_data['rolling_sharpe'],
            mode='lines',
            name='벤치마크 샤프 비율',
            line=dict(color='orange', dash='dash')
        ))

        fig.update_layout(
            title=f"📊 롤링 샤프 비율 ({window}일)",
            xaxis_title="날짜",
            yaxis_title="샤프 비율",
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    def show_detailed_reports(self):
        """상세 리포트 탭"""
        st.subheader("📋 상세 성과 리포트")

        # 리포트 생성 옵션
        col1, col2 = st.columns(2)

        with col1:
            report_type = st.selectbox(
                "리포트 유형",
                ["종합 리포트", "리스크 리포트", "거래 리포트", "벤치마크 리포트"],
                key="report_type_select"
            )

            report_period = st.selectbox(
                "리포트 기간",
                ["지난 30일", "지난 90일", "지난 1년", "전체 기간"],
                key="report_period_select"
            )

        with col2:
            include_charts = st.checkbox("차트 포함", value=True, key="include_charts")
            include_detailed_trades = st.checkbox("상세 거래 내역 포함", value=False, key="include_detailed_trades")

        # 리포트 생성 버튼
        if st.button("📊 리포트 생성", type="primary", key="generate_report"):
            report_content = self.generate_performance_report(
                report_type, report_period, include_charts, include_detailed_trades
            )

            st.markdown("### 📄 생성된 리포트")
            st.markdown(report_content)

            # 리포트 다운로드 옵션
            self.show_report_download_options(report_content)

        # 저장된 리포트 목록
        self.show_saved_reports()

    def show_analysis_settings_tab(self):
        """분석 설정 탭"""
        st.subheader("⚙️ 분석 설정")

        settings = st.session_state.analysis_settings

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 📊 계산 설정")

            risk_free_rate = st.number_input(
                "무위험 수익률 (%)",
                min_value=0.0,
                max_value=10.0,
                value=settings.get('risk_free_rate', 2.0),
                step=0.1,
                key="risk_free_rate_setting"
            )

            confidence_level = st.slider(
                "VaR 신뢰도 수준 (%)",
                min_value=90,
                max_value=99,
                value=settings.get('confidence_level', 95),
                key="confidence_level_setting"
            )

            rolling_window = st.number_input(
                "롤링 윈도우 (일)",
                min_value=7,
                max_value=365,
                value=settings.get('rolling_window', 30),
                key="rolling_window_setting"
            )

        with col2:
            st.markdown("#### 🎨 표시 설정")

            show_benchmark = st.checkbox(
                "벤치마크 표시",
                value=settings.get('show_benchmark', True),
                key="show_benchmark_setting"
            )

            currency_format = st.selectbox(
                "통화 형식",
                ["USD ($)", "KRW (₩)", "BTC (₿)"],
                index=0,
                key="currency_format_setting"
            )

            decimal_places = st.number_input(
                "소수점 자릿수",
                min_value=1,
                max_value=6,
                value=settings.get('decimal_places', 2),
                key="decimal_places_setting"
            )

        # 설정 저장
        settings.update({
            'risk_free_rate': risk_free_rate,
            'confidence_level': confidence_level,
            'rolling_window': rolling_window,
            'show_benchmark': show_benchmark,
            'currency_format': currency_format,
            'decimal_places': decimal_places
        })

        if st.button("💾 설정 저장", key="save_analysis_settings"):
            st.session_state.analysis_settings = settings
            st.success("✅ 분석 설정이 저장되었습니다!")

    # 계산 메서드들
    def calculate_performance_metrics(self) -> PerformanceMetrics:
        """성과 지표 계산"""
        data = st.session_state.trading_data
        returns = data['daily_return'].dropna()
        portfolio_values = data['portfolio_value']

        return PerformanceMetrics(
            total_return=((portfolio_values.iloc[-1] / portfolio_values.iloc[0]) - 1) * 100,
            annualized_return=self.calculate_annualized_return(returns),
            volatility=returns.std() * np.sqrt(252),
            sharpe_ratio=self.calculate_sharpe_ratio(returns),
            sortino_ratio=self.calculate_sortino_ratio(returns),
            calmar_ratio=self.calculate_calmar_ratio(returns),
            max_drawdown=self.calculate_max_drawdown(portfolio_values),
            win_rate=len(returns[returns > 0]) / len(returns) * 100,
            profit_factor=self.calculate_profit_factor(returns),
            var_95=returns.quantile(0.05),
            cvar_95=returns[returns <= returns.quantile(0.05)].mean(),
            alpha=0.0,  # 간단화
            beta=1.0,   # 간단화
            information_ratio=self.calculate_information_ratio(returns)
        )

    def calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """샤프 비율 계산"""
        if len(returns) < 2 or returns.std() == 0:
            return 0.0

        excess_returns = returns - (risk_free_rate / 252)
        return (excess_returns.mean() / returns.std()) * np.sqrt(252)

    def calculate_sortino_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """소르티노 비율 계산"""
        if len(returns) < 2:
            return 0.0

        excess_returns = returns - (risk_free_rate / 252)
        downside_returns = returns[returns < 0]

        if len(downside_returns) == 0:
            return float('inf')

        downside_deviation = downside_returns.std()
        if downside_deviation == 0:
            return float('inf')

        return (excess_returns.mean() / downside_deviation) * np.sqrt(252)

    def calculate_calmar_ratio(self, returns: pd.Series) -> float:
        """칼마 비율 계산"""
        if len(returns) < 2:
            return 0.0

        annualized_return = self.calculate_annualized_return(returns)

        # 포트폴리오 가치로부터 최대 드로다운 계산
        portfolio_values = st.session_state.trading_data['portfolio_value']
        max_dd = abs(self.calculate_max_drawdown(portfolio_values))

        if max_dd == 0:
            return float('inf')

        return annualized_return / max_dd

    def calculate_information_ratio(self, returns: pd.Series) -> float:
        """정보 비율 계산"""
        if len(returns) < 2:
            return 0.0

        # 벤치마크 대비 초과 수익률
        benchmark_returns = st.session_state.benchmark_data['daily_return'].dropna()

        if len(benchmark_returns) != len(returns):
            min_length = min(len(returns), len(benchmark_returns))
            returns = returns.iloc[-min_length:]
            benchmark_returns = benchmark_returns.iloc[-min_length:]

        excess_returns = returns - benchmark_returns
        tracking_error = excess_returns.std()

        if tracking_error == 0:
            return 0.0

        return excess_returns.mean() / tracking_error * np.sqrt(252)

    def calculate_annualized_return(self, returns: pd.Series) -> float:
        """연간 수익률 계산"""
        if len(returns) < 2:
            return 0.0

        cumulative_return = (1 + returns).prod() - 1
        years = len(returns) / 252  # 252 trading days per year

        if years <= 0:
            return 0.0

        return ((1 + cumulative_return) ** (1 / years) - 1) * 100

    def calculate_max_drawdown(self, portfolio_values: pd.Series) -> float:
        """최대 드로다운 계산"""
        peak = portfolio_values.expanding().max()
        drawdown = (portfolio_values - peak) / peak * 100
        return drawdown.min()

    def calculate_profit_factor(self, returns: pd.Series) -> float:
        """수익 팩터 계산"""
        winning_returns = returns[returns > 0]
        losing_returns = returns[returns < 0]

        total_profits = winning_returns.sum()
        total_losses = abs(losing_returns.sum())

        if total_losses == 0:
            return float('inf') if total_profits > 0 else 0.0

        return total_profits / total_losses

    # 헬퍼 메서드들 (간단한 구현)
    def generate_sample_trading_data(self) -> pd.DataFrame:
        """샘플 거래 데이터 생성"""
        days = 365
        dates = pd.date_range(start=datetime.now() - timedelta(days=days), periods=days, freq='D')

        # 랜덤 워크 생성
        returns = np.random.normal(0.001, 0.02, days)  # 평균 0.1%, 표준편차 2%
        portfolio_values = [100000]  # 초기 자본 $100,000

        for ret in returns[1:]:
            portfolio_values.append(portfolio_values[-1] * (1 + ret))

        daily_returns = [0] + [((portfolio_values[i] / portfolio_values[i-1]) - 1) * 100 for i in range(1, len(portfolio_values))]

        return pd.DataFrame({
            'date': dates,
            'portfolio_value': portfolio_values,
            'daily_return': daily_returns
        })

    def generate_benchmark_data(self) -> pd.DataFrame:
        """벤치마크 데이터 생성"""
        days = 365
        dates = pd.date_range(start=datetime.now() - timedelta(days=days), periods=days, freq='D')

        # BTC 유사 랜덤 워크
        returns = np.random.normal(0.0005, 0.04, days)  # 더 높은 변동성
        values = [50000]  # BTC 초기 가격

        for ret in returns[1:]:
            values.append(values[-1] * (1 + ret))

        daily_returns = [0] + [((values[i] / values[i-1]) - 1) * 100 for i in range(1, len(values))]

        return pd.DataFrame({
            'date': dates,
            'value': values,
            'daily_return': daily_returns
        })

    def get_default_analysis_settings(self) -> Dict[str, Any]:
        """기본 분석 설정"""
        return {
            'period': '월별',
            'start_date': datetime.now() - timedelta(days=365),
            'end_date': datetime.now(),
            'benchmark': 'Bitcoin',
            'risk_free_rate': 2.0,
            'confidence_level': 95,
            'rolling_window': 30,
            'show_benchmark': True,
            'currency_format': 'USD ($)',
            'decimal_places': 2
        }

    def get_trades_summary(self) -> Dict[str, Any]:
        """거래 요약 데이터 (시뮬레이션)"""
        return {
            'total_trades': 156,
            'winning_trades': 89,
            'losing_trades': 67,
            'win_rate': 57.1,
            'avg_win': 125.50,
            'avg_loss': -87.25,
            'profit_loss_ratio': 1.44,
            'max_consecutive_wins': 8,
            'max_consecutive_losses': 5
        }

    def calculate_period_returns(self, data: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """기간별 수익률 계산"""
        returns = data['daily_return'].dropna()

        return {
            'daily': {
                'mean': returns.mean(),
                'std': returns.std()
            },
            'weekly': {
                'mean': returns.mean() * 7,
                'std': returns.std() * np.sqrt(7)
            },
            'monthly': {
                'mean': returns.mean() * 30,
                'std': returns.std() * np.sqrt(30)
            },
            'quarterly': {
                'mean': returns.mean() * 90,
                'std': returns.std() * np.sqrt(90)
            },
            'yearly': {
                'mean': returns.mean() * 252,
                'std': returns.std() * np.sqrt(252)
            }
        }

    def plot_period_returns_chart(self, period_returns: Dict[str, Dict[str, float]]):
        """기간별 수익률 차트"""
        periods = ['daily', 'weekly', 'monthly', 'quarterly', 'yearly']
        means = [period_returns[period]['mean'] for period in periods]
        stds = [period_returns[period]['std'] for period in periods]

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=periods,
            y=means,
            name='평균 수익률',
            error_y=dict(type='data', array=stds),
            marker_color='blue'
        ))

        fig.update_layout(
            title="📊 기간별 평균 수익률",
            xaxis_title="기간",
            yaxis_title="수익률 (%)",
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    def calculate_comprehensive_risk_metrics(self, returns: pd.Series, portfolio_values: pd.Series) -> Dict[str, float]:
        """종합 리스크 지표 계산"""
        # 드로다운 계산
        peak = portfolio_values.expanding().max()
        drawdown = (portfolio_values - peak) / peak * 100

        return {
            'max_drawdown': drawdown.min(),
            'avg_drawdown': drawdown[drawdown < 0].mean() if len(drawdown[drawdown < 0]) > 0 else 0,
            'drawdown_duration': 30,  # 시뮬레이션
            'recovery_time': 15,      # 시뮬레이션
            'var_95': returns.quantile(0.05),
            'var_99': returns.quantile(0.01),
            'cvar_95': returns[returns <= returns.quantile(0.05)].mean(),
            'cvar_99': returns[returns <= returns.quantile(0.01)].mean(),
            'daily_volatility': returns.std(),
            'annual_volatility': returns.std() * np.sqrt(252),
            'downside_deviation': returns[returns < 0].std(),
            'upside_deviation': returns[returns > 0].std()
        }

    def generate_performance_report(self, report_type: str, report_period: str,
                                  include_charts: bool, include_detailed_trades: bool) -> str:
        """성과 리포트 생성"""
        metrics = self.calculate_performance_metrics()

        report = f"""
# 📊 {report_type} - {report_period}

## 요약
- **생성 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **분석 기간**: {report_period}
- **총 수익률**: {metrics.total_return:.2f}%
- **연간 수익률**: {metrics.annualized_return:.2f}%
- **샤프 비율**: {metrics.sharpe_ratio:.2f}
- **최대 낙폭**: {metrics.max_drawdown:.2f}%

## 핵심 지표
| 지표 | 값 |
|------|-----|
| 승률 | {metrics.win_rate:.1f}% |
| 변동성 | {metrics.volatility:.2f}% |
| VaR (95%) | {metrics.var_95:.2f}% |
| 소르티노 비율 | {metrics.sortino_ratio:.2f} |

---
*이 리포트는 자동매매 시스템에서 생성되었습니다.*
        """

        return report

    def show_report_download_options(self, report_content: str):
        """리포트 다운로드 옵션"""
        col1, col2 = st.columns(2)

        with col1:
            if st.button("📄 텍스트 다운로드", key="download_txt"):
                st.download_button(
                    label="TXT 다운로드",
                    data=report_content,
                    file_name=f"performance_report_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime='text/plain'
                )

        with col2:
            if st.button("📊 PDF 다운로드", key="download_pdf"):
                st.info("PDF 다운로드 기능은 구현 예정입니다.")

    def show_saved_reports(self):
        """저장된 리포트 목록"""
        st.markdown("#### 📁 저장된 리포트")

        if st.session_state.performance_reports:
            for i, report in enumerate(st.session_state.performance_reports):
                with st.expander(f"리포트 {i+1}: {report.get('date', 'Unknown')}"):
                    st.write(report.get('content', '내용 없음'))
        else:
            st.info("저장된 리포트가 없습니다.")

# 메인 실행 함수
def main():
    """메인 실행 함수"""
    analysis = ComprehensivePerformanceAnalysis()
    analysis.show_performance_analysis_dashboard()

if __name__ == "__main__":
    main()