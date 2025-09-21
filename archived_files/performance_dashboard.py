#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from performance_analyzer import PerformanceAnalyzer
from report_generator import ReportGenerator
import os

def main():
    st.set_page_config(
        page_title="Crypto Trader Pro - 성과 분석",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("📊 Crypto Trader Pro - 종합 성과 분석")

    # 사이드바 메뉴
    with st.sidebar:
        st.header("분석 메뉴")
        analysis_type = st.selectbox(
            "분석 유형 선택",
            ["실시간 성과 대시보드", "상세 분석 리포트", "백테스팅 비교", "리포트 생성"]
        )

        st.header("데이터 필터")
        date_range = st.date_input(
            "분석 기간",
            value=[datetime.now() - timedelta(days=30), datetime.now()],
            max_value=datetime.now()
        )

        symbols = st.multiselect(
            "분석 대상 코인",
            ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT"],
            default=["BTCUSDT", "ETHUSDT"]
        )

    # 성과 분석기 초기화
    analyzer = PerformanceAnalyzer()
    report_gen = ReportGenerator()

    if analysis_type == "실시간 성과 대시보드":
        show_realtime_dashboard(analyzer)
    elif analysis_type == "상세 분석 리포트":
        show_detailed_analysis(analyzer)
    elif analysis_type == "백테스팅 비교":
        show_backtest_comparison(analyzer)
    elif analysis_type == "리포트 생성":
        show_report_generation(report_gen)

def show_realtime_dashboard(analyzer):
    """실시간 성과 대시보드"""
    st.header("📈 실시간 성과 대시보드")

    # 성과 지표 계산
    metrics = analyzer.calculate_performance_metrics()

    if not metrics:
        st.warning("분석할 거래 데이터가 없습니다.")
        return

    # 주요 지표 카드
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_return = metrics.get('total_return_pct', 0)
        st.metric(
            "총 수익률",
            f"{total_return:.2f}%",
            delta=f"{total_return:.2f}%" if total_return >= 0 else f"{total_return:.2f}%"
        )

    with col2:
        net_pnl = metrics.get('net_pnl', 0)
        st.metric(
            "순 손익",
            f"{net_pnl:.2f} USDT",
            delta=f"{net_pnl:.2f}" if net_pnl >= 0 else f"{net_pnl:.2f}"
        )

    with col3:
        win_rate = metrics.get('win_rate', 0)
        st.metric(
            "승률",
            f"{win_rate:.1f}%",
            delta=f"{win_rate - 50:.1f}%" if win_rate >= 50 else f"{win_rate - 50:.1f}%"
        )

    with col4:
        sharpe_ratio = metrics.get('sharpe_ratio', 0)
        st.metric(
            "샤프 비율",
            f"{sharpe_ratio:.2f}",
            delta=f"{sharpe_ratio - 1:.2f}" if sharpe_ratio >= 1 else f"{sharpe_ratio - 1:.2f}"
        )

    # 차트 섹션
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("누적 수익률 곡선")
        cumulative_chart = analyzer.create_cumulative_return_chart()
        st.plotly_chart(cumulative_chart, use_container_width=True)

    with col2:
        st.subheader("거래별 손익 분포")
        pnl_hist = analyzer.create_pnl_histogram()
        st.plotly_chart(pnl_hist, use_container_width=True)

    # 시간대별 & 코인별 분석
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("시간대별 거래 성과")
        hourly_chart = analyzer.create_hourly_performance_chart()
        st.plotly_chart(hourly_chart, use_container_width=True)

    with col2:
        st.subheader("코인별 수익률 비교")
        symbol_chart = analyzer.create_symbol_performance_chart()
        st.plotly_chart(symbol_chart, use_container_width=True)

    # 상세 메트릭스 테이블
    st.subheader("📋 상세 성과 지표")

    metrics_df = pd.DataFrame([
        {"지표": "총 거래 횟수", "값": f"{metrics.get('total_trades', 0)}회"},
        {"지표": "승리 거래", "값": f"{metrics.get('winning_trades', 0)}회"},
        {"지표": "패배 거래", "값": f"{metrics.get('losing_trades', 0)}회"},
        {"지표": "평균 수익", "값": f"{metrics.get('avg_win', 0):.4f} USDT"},
        {"지표": "평균 손실", "값": f"{metrics.get('avg_loss', 0):.4f} USDT"},
        {"지표": "손익비", "값": f"{metrics.get('profit_factor', 0):.2f}"},
        {"지표": "최대 연속 수익", "값": f"{metrics.get('consecutive_wins', 0)}회"},
        {"지표": "최대 연속 손실", "값": f"{metrics.get('consecutive_losses', 0)}회"},
        {"지표": "최대 드로우다운", "값": f"{metrics.get('max_drawdown', 0):.2f}%"},
        {"지표": "총 수수료", "값": f"{metrics.get('total_fees', 0):.4f} USDT"}
    ])

    st.dataframe(metrics_df, use_container_width=True)

def show_detailed_analysis(analyzer):
    """상세 분석 리포트"""
    st.header("🔍 상세 분석 리포트")

    if analyzer.trading_data.empty:
        st.warning("분석할 거래 데이터가 없습니다.")
        return

    # 월별 성과 요약
    st.subheader("📅 월별 성과 요약")
    monthly_chart = analyzer.create_monthly_summary_chart()
    st.plotly_chart(monthly_chart, use_container_width=True)

    # 거래 히스토리 테이블
    st.subheader("📊 거래 히스토리")

    # 데이터 준비
    df = analyzer.trading_data.copy()
    df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
    df['pnl'] = df['pnl'].round(4)
    df['pnl_percentage'] = df['pnl_percentage'].round(2)

    # 컬럼 선택 및 표시
    display_columns = ['timestamp', 'symbol', 'trade_amount', 'pnl', 'pnl_percentage', 'source']
    df_display = df[display_columns].copy()
    df_display.columns = ['시간', '심볼', '거래금액', '손익', '손익률(%)', '소스']

    # 손익에 따른 색상 표시를 위한 스타일링
    def color_pnl(val):
        if isinstance(val, (int, float)):
            color = 'color: green' if val > 0 else 'color: red' if val < 0 else 'color: black'
            return color
        return ''

    styled_df = df_display.style.applymap(color_pnl, subset=['손익', '손익률(%)'])
    st.dataframe(styled_df, use_container_width=True)

    # 통계 요약
    st.subheader("📈 통계 요약")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info(f"""
        **기본 통계**
        - 평균 거래 금액: {df['trade_amount'].mean():.2f} USDT
        - 중간값 손익: {df['pnl'].median():.4f} USDT
        - 표준편차: {df['pnl'].std():.4f} USDT
        """)

    with col2:
        st.info(f"""
        **위험 지표**
        - VaR (95%): {df['pnl'].quantile(0.05):.4f} USDT
        - 최대 손실: {df['pnl'].min():.4f} USDT
        - 최대 수익: {df['pnl'].max():.4f} USDT
        """)

    with col3:
        st.info(f"""
        **거래 패턴**
        - 가장 활발한 시간: {df['timestamp'].str.split().str[1].str[:2].mode().iloc[0] if not df.empty else 'N/A'}시
        - 주요 거래 코인: {df['symbol'].mode().iloc[0] if not df.empty else 'N/A'}
        - 평균 보유 시간: 추정 2-4시간
        """)

def show_backtest_comparison(analyzer):
    """백테스팅 비교"""
    st.header("🔄 백테스팅 vs 실거래 비교")

    # 비교 데이터 생성
    comparison = analyzer.compare_with_backtest()

    if not comparison:
        st.warning("비교할 데이터가 없습니다.")
        return

    # 비교 차트
    metrics = ['total_return', 'sharpe_ratio', 'win_rate']
    backtest_values = [comparison['backtest'][m] for m in metrics]
    live_values = [comparison['live_trading'][m] for m in metrics]

    fig = go.Figure(data=[
        go.Bar(name='백테스팅', x=['총 수익률(%)', '샤프 비율', '승률(%)'], y=backtest_values),
        go.Bar(name='실거래', x=['총 수익률(%)', '샤프 비율', '승률(%)'], y=live_values)
    ])

    fig.update_layout(
        title='백테스팅 vs 실거래 성과 비교',
        barmode='group',
        yaxis_title='값'
    )

    st.plotly_chart(fig, use_container_width=True)

    # 차이점 분석
    st.subheader("📋 차이점 분석")

    differences_data = []
    for key, diff in comparison['differences'].items():
        differences_data.append({
            '지표': key,
            '백테스팅': comparison['backtest'][key],
            '실거래': comparison['live_trading'][key],
            '절대차이': f"{diff['absolute']:.2f}",
            '상대차이(%)': f"{diff['percentage']:.1f}%"
        })

    differences_df = pd.DataFrame(differences_data)
    st.dataframe(differences_df, use_container_width=True)

    # 슬리피지 및 수수료 영향 분석
    st.subheader("💰 슬리피지 및 수수료 영향")

    col1, col2 = st.columns(2)

    with col1:
        st.info("""
        **주요 차이점 원인**
        - 슬리피지: 시장가 주문 시 예상가격과 실제체결가격 차이
        - 거래 수수료: 백테스팅에서 과소평가된 실제 비용
        - 네트워크 지연: 신호 생성과 실제 주문 사이의 시간차
        - 시장 충격: 대량 주문이 시장가격에 미치는 영향
        """)

    with col2:
        st.warning("""
        **개선 방안**
        - 지정가 주문 활용으로 슬리피지 최소화
        - 거래량이 많은 시간대 선택
        - 포지션 크기 최적화
        - 실시간 스프레드 모니터링
        """)

def show_report_generation(report_gen):
    """리포트 생성"""
    st.header("📄 리포트 생성")

    # 리포트 유형 선택
    report_type = st.selectbox(
        "리포트 유형",
        ["일일 거래 요약", "주간 성과 분석", "월간 종합 리포트"]
    )

    # 날짜 선택
    if report_type == "일일 거래 요약":
        selected_date = st.date_input("리포트 날짜", value=datetime.now())
        format_type = st.selectbox("출력 형식", ["HTML", "PDF"])

        if st.button("일일 리포트 생성"):
            with st.spinner("리포트 생성 중..."):
                try:
                    date_str = selected_date.strftime('%Y-%m-%d')
                    filename = report_gen.generate_daily_report(
                        date_str,
                        'html' if format_type == 'HTML' else 'pdf'
                    )
                    st.success(f"리포트가 생성되었습니다: {filename}")

                    # HTML 파일인 경우 미리보기 제공
                    if filename.endswith('.html') and os.path.exists(filename):
                        with open(filename, 'r', encoding='utf-8') as f:
                            html_content = f.read()
                        st.components.v1.html(html_content, height=600, scrolling=True)

                except Exception as e:
                    st.error(f"리포트 생성 실패: {e}")

    elif report_type == "주간 성과 분석":
        week_start = st.date_input("주 시작일 (월요일)", value=datetime.now() - timedelta(days=datetime.now().weekday()))

        if st.button("주간 리포트 생성"):
            with st.spinner("리포트 생성 중..."):
                try:
                    week_start_str = week_start.strftime('%Y-%m-%d')
                    filename = report_gen.generate_weekly_report(week_start_str)
                    st.success(f"리포트가 생성되었습니다: {filename}")

                    if os.path.exists(filename):
                        with open(filename, 'r', encoding='utf-8') as f:
                            html_content = f.read()
                        st.components.v1.html(html_content, height=800, scrolling=True)

                except Exception as e:
                    st.error(f"리포트 생성 실패: {e}")

    elif report_type == "월간 종합 리포트":
        selected_month = st.selectbox(
            "리포트 월",
            [datetime.now().strftime('%Y-%m'), (datetime.now() - timedelta(days=30)).strftime('%Y-%m')]
        )

        if st.button("월간 리포트 생성"):
            with st.spinner("리포트 생성 중..."):
                try:
                    filename = report_gen.generate_monthly_report(selected_month)
                    st.success(f"리포트가 생성되었습니다: {filename}")

                    if os.path.exists(filename):
                        with open(filename, 'r', encoding='utf-8') as f:
                            html_content = f.read()
                        st.components.v1.html(html_content, height=1000, scrolling=True)

                except Exception as e:
                    st.error(f"리포트 생성 실패: {e}")

    # 기존 리포트 목록
    st.subheader("📁 기존 리포트")

    if os.path.exists('reports'):
        report_files = [f for f in os.listdir('reports') if f.endswith(('.html', '.pdf'))]
        if report_files:
            selected_file = st.selectbox("기존 리포트 선택", report_files)

            if st.button("리포트 열기"):
                file_path = os.path.join('reports', selected_file)
                if selected_file.endswith('.html'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    st.components.v1.html(html_content, height=800, scrolling=True)
                else:
                    st.info("PDF 파일은 다운로드하여 확인하세요.")
        else:
            st.info("생성된 리포트가 없습니다.")
    else:
        st.info("reports 폴더가 없습니다.")

if __name__ == "__main__":
    main()