#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st
from typing import Dict, List, Tuple, Optional
import sqlite3

class PerformanceAnalyzer:
    def __init__(self, db_path: str = "data/trading_data.db"):
        self.db_path = db_path
        self.trading_data = pd.DataFrame()
        self.load_trading_data()

    def load_trading_data(self):
        """거래 데이터를 다양한 소스에서 로드"""
        data_sources = []

        # JSON 파일에서 데이터 로드
        json_files = [f for f in os.listdir('.') if f.startswith('trading_test_report_') and f.endswith('.json')]
        for file in json_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'trading_results' in data and 'test_info' in data:
                        trade_data = {
                            'timestamp': data['test_info']['test_time'],
                            'symbol': data['test_info']['symbol'],
                            'trade_amount': data['test_info']['trade_amount'],
                            'buy_price': data['trading_results']['avg_buy_price'],
                            'sell_price': data['trading_results']['avg_sell_price'],
                            'quantity': data['trading_results']['buy_quantity'],
                            'pnl': data['trading_results']['net_pnl'],
                            'pnl_percentage': data['trading_results']['pnl_percentage'],
                            'fees': data['trading_results']['total_fees'],
                            'source': 'test_trade'
                        }
                        data_sources.append(trade_data)
            except Exception as e:
                st.warning(f"JSON 파일 로드 실패: {file} - {e}")

        # SQLite DB에서 데이터 로드 (있는 경우)
        if os.path.exists(self.db_path):
            try:
                conn = sqlite3.connect(self.db_path)
                trades_df = pd.read_sql_query("SELECT * FROM trades", conn)
                conn.close()

                for _, row in trades_df.iterrows():
                    trade_data = {
                        'timestamp': row.get('timestamp', datetime.now().isoformat()),
                        'symbol': row.get('symbol', 'BTCUSDT'),
                        'trade_amount': row.get('amount', 0),
                        'buy_price': row.get('buy_price', 0),
                        'sell_price': row.get('sell_price', 0),
                        'quantity': row.get('quantity', 0),
                        'pnl': row.get('pnl', 0),
                        'pnl_percentage': row.get('pnl_percentage', 0),
                        'fees': row.get('fees', 0),
                        'source': 'database'
                    }
                    data_sources.append(trade_data)
            except Exception as e:
                st.warning(f"데이터베이스 로드 실패: {e}")

        # 샘플 데이터 생성 (실제 데이터가 없는 경우)
        if not data_sources:
            data_sources = self.generate_sample_data()

        self.trading_data = pd.DataFrame(data_sources)
        if not self.trading_data.empty:
            self.trading_data['timestamp'] = pd.to_datetime(self.trading_data['timestamp'])
            self.trading_data = self.trading_data.sort_values('timestamp')

    def generate_sample_data(self) -> List[Dict]:
        """분석용 샘플 거래 데이터 생성"""
        np.random.seed(42)
        sample_data = []

        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']
        base_date = datetime.now() - timedelta(days=30)

        for i in range(50):
            timestamp = base_date + timedelta(hours=i*12)
            symbol = np.random.choice(symbols)

            # 승률 60% 정도로 설정
            is_profit = np.random.random() < 0.6

            if is_profit:
                pnl_pct = np.random.normal(2.5, 1.5)  # 평균 2.5% 수익
            else:
                pnl_pct = np.random.normal(-1.8, 1.0)  # 평균 -1.8% 손실

            trade_amount = np.random.uniform(10, 100)
            pnl = trade_amount * (pnl_pct / 100)

            sample_data.append({
                'timestamp': timestamp.isoformat(),
                'symbol': symbol,
                'trade_amount': trade_amount,
                'buy_price': np.random.uniform(20000, 70000),
                'sell_price': np.random.uniform(20000, 70000),
                'quantity': trade_amount / 50000,
                'pnl': pnl,
                'pnl_percentage': pnl_pct,
                'fees': trade_amount * 0.001,
                'source': 'sample'
            })

        return sample_data

    def calculate_performance_metrics(self) -> Dict:
        """종합 성과 지표 계산"""
        if self.trading_data.empty:
            return {}

        df = self.trading_data.copy()

        # 기본 지표
        total_trades = len(df)
        winning_trades = len(df[df['pnl'] > 0])
        losing_trades = len(df[df['pnl'] <= 0])

        total_pnl = df['pnl'].sum()
        total_fees = df['fees'].sum()
        net_pnl = total_pnl - total_fees

        initial_capital = 10000  # 가정 초기 자본
        total_return_pct = (net_pnl / initial_capital) * 100

        # 승률
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0

        # 평균 수익/손실
        avg_win = df[df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = df[df['pnl'] <= 0]['pnl'].mean() if losing_trades > 0 else 0

        # 손익비 (Profit Factor)
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0

        # 최대 연속 수익/손실
        df['is_win'] = df['pnl'] > 0
        consecutive_wins = self.calculate_max_consecutive(df['is_win'], True)
        consecutive_losses = self.calculate_max_consecutive(df['is_win'], False)

        # 누적 수익률로 최대 드로우다운 계산
        df['cumulative_pnl'] = df['pnl'].cumsum()
        df['cumulative_return'] = (df['cumulative_pnl'] / initial_capital) * 100

        peak = df['cumulative_return'].expanding().max()
        drawdown = df['cumulative_return'] - peak
        max_drawdown = drawdown.min()

        # 샤프 비율 (일간 수익률 기준)
        daily_returns = df.groupby(df['timestamp'].dt.date)['pnl'].sum()
        sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() != 0 else 0

        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'total_pnl': total_pnl,
            'total_fees': total_fees,
            'net_pnl': net_pnl,
            'total_return_pct': total_return_pct,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'consecutive_wins': consecutive_wins,
            'consecutive_losses': consecutive_losses,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio
        }

    def calculate_max_consecutive(self, series: pd.Series, value: bool) -> int:
        """최대 연속 발생 횟수 계산"""
        groups = (series != series.shift()).cumsum()
        return series.groupby(groups).sum().where(series.groupby(groups).first() == value, 0).max()

    def create_cumulative_return_chart(self) -> go.Figure:
        """누적 수익률 곡선 차트"""
        if self.trading_data.empty:
            return go.Figure()

        df = self.trading_data.copy()
        df['cumulative_pnl'] = df['pnl'].cumsum()

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['cumulative_pnl'],
            mode='lines',
            name='누적 손익',
            line=dict(color='#1f77b4', width=2)
        ))

        fig.update_layout(
            title='일별 누적 수익률 곡선',
            xaxis_title='날짜',
            yaxis_title='누적 손익 (USDT)',
            hovermode='x unified'
        )

        return fig

    def create_pnl_histogram(self) -> go.Figure:
        """거래별 손익 히스토그램"""
        if self.trading_data.empty:
            return go.Figure()

        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=self.trading_data['pnl'],
            nbinsx=20,
            name='거래 손익 분포',
            marker_color='lightblue',
            opacity=0.7
        ))

        fig.update_layout(
            title='거래별 손익 히스토그램',
            xaxis_title='손익 (USDT)',
            yaxis_title='거래 횟수',
            bargap=0.1
        )

        return fig

    def create_hourly_performance_chart(self) -> go.Figure:
        """시간대별 거래 성과 분석"""
        if self.trading_data.empty:
            return go.Figure()

        df = self.trading_data.copy()
        df['hour'] = df['timestamp'].dt.hour
        hourly_stats = df.groupby('hour')['pnl'].agg(['mean', 'count']).reset_index()

        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('시간대별 평균 손익', '시간대별 거래 횟수'),
            vertical_spacing=0.1
        )

        fig.add_trace(go.Bar(
            x=hourly_stats['hour'],
            y=hourly_stats['mean'],
            name='평균 손익',
            marker_color='green'
        ), row=1, col=1)

        fig.add_trace(go.Bar(
            x=hourly_stats['hour'],
            y=hourly_stats['count'],
            name='거래 횟수',
            marker_color='blue'
        ), row=2, col=1)

        fig.update_layout(title='시간대별 거래 성과 분석')
        return fig

    def create_symbol_performance_chart(self) -> go.Figure:
        """코인별 수익률 비교"""
        if self.trading_data.empty:
            return go.Figure()

        symbol_stats = self.trading_data.groupby('symbol').agg({
            'pnl': ['sum', 'mean', 'count']
        }).round(2)
        symbol_stats.columns = ['총손익', '평균손익', '거래횟수']
        symbol_stats = symbol_stats.reset_index()

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=symbol_stats['symbol'],
            y=symbol_stats['총손익'],
            name='총 손익',
            text=symbol_stats['총손익'],
            textposition='auto'
        ))

        fig.update_layout(
            title='코인별 수익률 비교',
            xaxis_title='심볼',
            yaxis_title='총 손익 (USDT)'
        )

        return fig

    def create_monthly_summary_chart(self) -> go.Figure:
        """월별 성과 요약 차트"""
        if self.trading_data.empty:
            return go.Figure()

        df = self.trading_data.copy()
        df['year_month'] = df['timestamp'].dt.to_period('M')
        monthly_stats = df.groupby('year_month').agg({
            'pnl': ['sum', 'count'],
            'trade_amount': 'sum'
        }).round(2)

        monthly_stats.columns = ['월별손익', '거래횟수', '거래금액']
        monthly_stats = monthly_stats.reset_index()
        monthly_stats['year_month'] = monthly_stats['year_month'].astype(str)

        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('월별 손익', '월별 거래 현황'),
            specs=[[{"secondary_y": False}], [{"secondary_y": True}]]
        )

        fig.add_trace(go.Bar(
            x=monthly_stats['year_month'],
            y=monthly_stats['월별손익'],
            name='월별 손익',
            marker_color='green'
        ), row=1, col=1)

        fig.add_trace(go.Bar(
            x=monthly_stats['year_month'],
            y=monthly_stats['거래횟수'],
            name='거래 횟수',
            marker_color='blue'
        ), row=2, col=1)

        fig.update_layout(title='월별 성과 요약')
        return fig

    def generate_daily_report(self, date: str = None) -> Dict:
        """일일 거래 요약 리포트 생성"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        df = self.trading_data[self.trading_data['timestamp'].dt.date == pd.to_datetime(date).date()]

        if df.empty:
            return {'date': date, 'message': '해당 날짜의 거래 데이터가 없습니다.'}

        daily_stats = {
            'date': date,
            'total_trades': len(df),
            'winning_trades': len(df[df['pnl'] > 0]),
            'total_pnl': df['pnl'].sum(),
            'total_fees': df['fees'].sum(),
            'win_rate': (len(df[df['pnl'] > 0]) / len(df)) * 100,
            'best_trade': df.loc[df['pnl'].idxmax()].to_dict() if not df.empty else {},
            'worst_trade': df.loc[df['pnl'].idxmin()].to_dict() if not df.empty else {},
            'symbols_traded': df['symbol'].unique().tolist(),
            'total_volume': df['trade_amount'].sum()
        }

        return daily_stats

    def compare_with_backtest(self, backtest_results: Dict = None) -> Dict:
        """백테스팅 결과와 실거래 결과 비교"""
        if backtest_results is None:
            # 샘플 백테스팅 결과
            backtest_results = {
                'total_return': 15.5,
                'sharpe_ratio': 1.8,
                'max_drawdown': -8.2,
                'win_rate': 65.0,
                'total_trades': 45
            }

        live_metrics = self.calculate_performance_metrics()

        comparison = {
            'live_trading': {
                'total_return': live_metrics.get('total_return_pct', 0),
                'sharpe_ratio': live_metrics.get('sharpe_ratio', 0),
                'max_drawdown': live_metrics.get('max_drawdown', 0),
                'win_rate': live_metrics.get('win_rate', 0),
                'total_trades': live_metrics.get('total_trades', 0)
            },
            'backtest': backtest_results,
            'differences': {}
        }

        # 차이점 계산
        for key in backtest_results.keys():
            live_value = comparison['live_trading'].get(key, 0)
            backtest_value = backtest_results[key]
            difference = live_value - backtest_value
            comparison['differences'][key] = {
                'absolute': difference,
                'percentage': (difference / backtest_value * 100) if backtest_value != 0 else 0
            }

        return comparison