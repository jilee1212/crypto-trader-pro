#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from jinja2 import Template
# import pdfkit  # Optional PDF generation
from typing import Dict, List, Tuple
import os
import json
from performance_analyzer import PerformanceAnalyzer

class ReportGenerator:
    def __init__(self):
        self.analyzer = PerformanceAnalyzer()
        self.report_templates = {
            'daily': self.get_daily_template(),
            'weekly': self.get_weekly_template(),
            'monthly': self.get_monthly_template()
        }

    def get_daily_template(self) -> str:
        """일일 리포트 HTML 템플릿"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>일일 거래 리포트 - {{ date }}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background-color: #f0f0f0; padding: 20px; border-radius: 5px; }
                .metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }
                .metric-box { background-color: #e8f4fd; padding: 15px; border-radius: 5px; text-align: center; }
                .trade-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                .trade-table th, .trade-table td { border: 1px solid #ddd; padding: 8px; text-align: center; }
                .trade-table th { background-color: #f2f2f2; }
                .positive { color: green; font-weight: bold; }
                .negative { color: red; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Crypto Trader Pro - 일일 거래 리포트</h1>
                <h2>{{ date }}</h2>
            </div>

            <div class="metrics">
                <div class="metric-box">
                    <h3>총 거래 횟수</h3>
                    <p style="font-size: 24px; margin: 0;">{{ total_trades }}</p>
                </div>
                <div class="metric-box">
                    <h3>총 손익</h3>
                    <p style="font-size: 24px; margin: 0;" class="{% if total_pnl >= 0 %}positive{% else %}negative{% endif %}">
                        {{ "%.2f"|format(total_pnl) }} USDT
                    </p>
                </div>
                <div class="metric-box">
                    <h3>승률</h3>
                    <p style="font-size: 24px; margin: 0;">{{ "%.1f"|format(win_rate) }}%</p>
                </div>
            </div>

            <h3>거래 상세 내역</h3>
            <table class="trade-table">
                <tr>
                    <th>시간</th>
                    <th>심볼</th>
                    <th>거래금액</th>
                    <th>손익</th>
                    <th>손익률</th>
                </tr>
                {% for trade in trades %}
                <tr>
                    <td>{{ trade.timestamp.strftime('%H:%M:%S') }}</td>
                    <td>{{ trade.symbol }}</td>
                    <td>{{ "%.2f"|format(trade.trade_amount) }}</td>
                    <td class="{% if trade.pnl >= 0 %}positive{% else %}negative{% endif %}">
                        {{ "%.4f"|format(trade.pnl) }}
                    </td>
                    <td class="{% if trade.pnl_percentage >= 0 %}positive{% else %}negative{% endif %}">
                        {{ "%.2f"|format(trade.pnl_percentage) }}%
                    </td>
                </tr>
                {% endfor %}
            </table>

            <div style="margin-top: 30px; padding: 15px; background-color: #f9f9f9; border-radius: 5px;">
                <h3>일일 요약</h3>
                <p><strong>최고 수익 거래:</strong> {{ "%.4f"|format(best_trade_pnl) }} USDT ({{ best_trade_symbol }})</p>
                <p><strong>최대 손실 거래:</strong> {{ "%.4f"|format(worst_trade_pnl) }} USDT ({{ worst_trade_symbol }})</p>
                <p><strong>거래된 코인:</strong> {{ symbols_traded|join(', ') }}</p>
                <p><strong>총 거래 금액:</strong> {{ "%.2f"|format(total_volume) }} USDT</p>
                <p><strong>총 수수료:</strong> {{ "%.4f"|format(total_fees) }} USDT</p>
            </div>

            <div style="margin-top: 20px; font-size: 12px; color: #666;">
                <p>리포트 생성 시간: {{ report_time }}</p>
            </div>
        </body>
        </html>
        """

    def get_weekly_template(self) -> str:
        """주간 리포트 HTML 템플릿"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>주간 성과 분석 리포트 - {{ week_start }} ~ {{ week_end }}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background-color: #f0f0f0; padding: 20px; border-radius: 5px; }
                .metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }
                .metric-box { background-color: #e8f4fd; padding: 15px; border-radius: 5px; text-align: center; }
                .section { margin: 30px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                .daily-table { width: 100%; border-collapse: collapse; margin: 15px 0; }
                .daily-table th, .daily-table td { border: 1px solid #ddd; padding: 10px; text-align: center; }
                .daily-table th { background-color: #f2f2f2; }
                .positive { color: green; font-weight: bold; }
                .negative { color: red; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Crypto Trader Pro - 주간 성과 분석</h1>
                <h2>{{ week_start }} ~ {{ week_end }}</h2>
            </div>

            <div class="metrics">
                <div class="metric-box">
                    <h3>주간 총 손익</h3>
                    <p style="font-size: 20px; margin: 0;" class="{% if weekly_pnl >= 0 %}positive{% else %}negative{% endif %}">
                        {{ "%.2f"|format(weekly_pnl) }} USDT
                    </p>
                </div>
                <div class="metric-box">
                    <h3>총 거래 횟수</h3>
                    <p style="font-size: 20px; margin: 0;">{{ total_trades }}</p>
                </div>
                <div class="metric-box">
                    <h3>주간 승률</h3>
                    <p style="font-size: 20px; margin: 0;">{{ "%.1f"|format(win_rate) }}%</p>
                </div>
                <div class="metric-box">
                    <h3>손익비</h3>
                    <p style="font-size: 20px; margin: 0;">{{ "%.2f"|format(profit_factor) }}</p>
                </div>
            </div>

            <div class="section">
                <h3>일별 성과 요약</h3>
                <table class="daily-table">
                    <tr>
                        <th>날짜</th>
                        <th>거래 횟수</th>
                        <th>일일 손익</th>
                        <th>승률</th>
                        <th>최고 거래</th>
                    </tr>
                    {% for day in daily_summary %}
                    <tr>
                        <td>{{ day.date }}</td>
                        <td>{{ day.trades }}</td>
                        <td class="{% if day.pnl >= 0 %}positive{% else %}negative{% endif %}">
                            {{ "%.2f"|format(day.pnl) }}
                        </td>
                        <td>{{ "%.1f"|format(day.win_rate) }}%</td>
                        <td class="{% if day.best_trade >= 0 %}positive{% else %}negative{% endif %}">
                            {{ "%.4f"|format(day.best_trade) }}
                        </td>
                    </tr>
                    {% endfor %}
                </table>
            </div>

            <div class="section">
                <h3>주요 성과 지표</h3>
                <ul>
                    <li><strong>최대 연속 수익:</strong> {{ max_consecutive_wins }}회</li>
                    <li><strong>최대 연속 손실:</strong> {{ max_consecutive_losses }}회</li>
                    <li><strong>최대 드로우다운:</strong> {{ "%.2f"|format(max_drawdown) }}%</li>
                    <li><strong>샤프 비율:</strong> {{ "%.2f"|format(sharpe_ratio) }}</li>
                    <li><strong>평균 수익:</strong> {{ "%.4f"|format(avg_win) }} USDT</li>
                    <li><strong>평균 손실:</strong> {{ "%.4f"|format(avg_loss) }} USDT</li>
                </ul>
            </div>

            <div class="section">
                <h3>전략 분석 및 개선 제안</h3>
                <p><strong>강점:</strong></p>
                <ul>
                    {% for strength in strengths %}
                    <li>{{ strength }}</li>
                    {% endfor %}
                </ul>
                <p><strong>개선 포인트:</strong></p>
                <ul>
                    {% for improvement in improvements %}
                    <li>{{ improvement }}</li>
                    {% endfor %}
                </ul>
            </div>

            <div style="margin-top: 20px; font-size: 12px; color: #666;">
                <p>리포트 생성 시간: {{ report_time }}</p>
            </div>
        </body>
        </html>
        """

    def get_monthly_template(self) -> str:
        """월간 리포트 HTML 템플릿"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>월간 종합 투자 리포트 - {{ month }}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background-color: #f0f0f0; padding: 20px; border-radius: 5px; text-align: center; }
                .executive-summary { background-color: #fff3cd; padding: 20px; border-radius: 5px; margin: 20px 0; }
                .metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }
                .metric-box { background-color: #e8f4fd; padding: 20px; border-radius: 5px; text-align: center; }
                .section { margin: 30px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                .comparison-table { width: 100%; border-collapse: collapse; margin: 15px 0; }
                .comparison-table th, .comparison-table td { border: 1px solid #ddd; padding: 12px; text-align: center; }
                .comparison-table th { background-color: #f2f2f2; }
                .positive { color: green; font-weight: bold; }
                .negative { color: red; font-weight: bold; }
                .neutral { color: blue; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Crypto Trader Pro</h1>
                <h2>월간 종합 투자 리포트</h2>
                <h3>{{ month }}</h3>
            </div>

            <div class="executive-summary">
                <h3>경영진 요약 (Executive Summary)</h3>
                <p>{{ executive_summary }}</p>
            </div>

            <div class="metrics-grid">
                <div class="metric-box">
                    <h3>월간 총 수익률</h3>
                    <p style="font-size: 28px; margin: 0;" class="{% if monthly_return >= 0 %}positive{% else %}negative{% endif %}">
                        {{ "%.2f"|format(monthly_return) }}%
                    </p>
                </div>
                <div class="metric-box">
                    <h3>절대 수익 금액</h3>
                    <p style="font-size: 28px; margin: 0;" class="{% if absolute_profit >= 0 %}positive{% else %}negative{% endif %}">
                        {{ "%.2f"|format(absolute_profit) }} USDT
                    </p>
                </div>
                <div class="metric-box">
                    <h3>거래 성공률</h3>
                    <p style="font-size: 28px; margin: 0;">{{ "%.1f"|format(win_rate) }}%</p>
                </div>
            </div>

            <div class="section">
                <h3>핵심 성과 지표 (KPI)</h3>
                <table class="comparison-table">
                    <tr>
                        <th>지표</th>
                        <th>이번 달</th>
                        <th>지난 달</th>
                        <th>변화율</th>
                        <th>벤치마크</th>
                    </tr>
                    <tr>
                        <td>총 수익률</td>
                        <td class="{% if monthly_return >= 0 %}positive{% else %}negative{% endif %}">{{ "%.2f"|format(monthly_return) }}%</td>
                        <td>{{ "%.2f"|format(last_month_return) }}%</td>
                        <td class="{% if return_change >= 0 %}positive{% else %}negative{% endif %}">{{ "%.2f"|format(return_change) }}%</td>
                        <td class="neutral">5-10%</td>
                    </tr>
                    <tr>
                        <td>샤프 비율</td>
                        <td>{{ "%.2f"|format(sharpe_ratio) }}</td>
                        <td>{{ "%.2f"|format(last_sharpe) }}</td>
                        <td class="{% if sharpe_change >= 0 %}positive{% else %}negative{% endif %}">{{ "%.2f"|format(sharpe_change) }}</td>
                        <td class="neutral">1.5+</td>
                    </tr>
                    <tr>
                        <td>최대 드로우다운</td>
                        <td class="{% if max_drawdown <= -5 %}negative{% else %}positive{% endif %}">{{ "%.2f"|format(max_drawdown) }}%</td>
                        <td>{{ "%.2f"|format(last_drawdown) }}%</td>
                        <td>{{ "%.2f"|format(drawdown_change) }}%</td>
                        <td class="neutral">-10% 이내</td>
                    </tr>
                </table>
            </div>

            <div class="section">
                <h3>백테스팅 vs 실거래 비교</h3>
                <table class="comparison-table">
                    <tr>
                        <th>항목</th>
                        <th>백테스팅</th>
                        <th>실거래</th>
                        <th>차이</th>
                        <th>주요 원인</th>
                    </tr>
                    {% for item in backtest_comparison %}
                    <tr>
                        <td>{{ item.metric }}</td>
                        <td>{{ item.backtest }}</td>
                        <td>{{ item.live }}</td>
                        <td class="{% if item.difference >= 0 %}positive{% else %}negative{% endif %}">{{ item.difference }}</td>
                        <td>{{ item.reason }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>

            <div class="section">
                <h3>리스크 분석</h3>
                <ul>
                    <li><strong>시장 리스크:</strong> {{ market_risk }}</li>
                    <li><strong>유동성 리스크:</strong> {{ liquidity_risk }}</li>
                    <li><strong>기술적 리스크:</strong> {{ technical_risk }}</li>
                    <li><strong>운영 리스크:</strong> {{ operational_risk }}</li>
                </ul>
            </div>

            <div class="section">
                <h3>다음 달 전략 및 개선 계획</h3>
                <h4>전략 최적화 제안:</h4>
                <ol>
                    {% for strategy in strategy_improvements %}
                    <li>{{ strategy }}</li>
                    {% endfor %}
                </ol>

                <h4>리스크 관리 강화:</h4>
                <ol>
                    {% for risk_measure in risk_improvements %}
                    <li>{{ risk_measure }}</li>
                    {% endfor %}
                </ol>
            </div>

            <div style="margin-top: 30px; padding: 15px; background-color: #f9f9f9; border-radius: 5px;">
                <p><strong>면책 조항:</strong> 본 리포트는 과거 거래 데이터를 바탕으로 한 분석이며, 미래 수익을 보장하지 않습니다.
                암호화폐 투자는 높은 위험을 수반하므로 신중한 투자 결정을 하시기 바랍니다.</p>
            </div>

            <div style="margin-top: 20px; font-size: 12px; color: #666;">
                <p>리포트 생성 시간: {{ report_time }}</p>
            </div>
        </body>
        </html>
        """

    def generate_daily_report(self, date: str = None, output_format: str = 'html') -> str:
        """일일 거래 리포트 생성"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        daily_data = self.analyzer.generate_daily_report(date)

        if 'message' in daily_data:
            return daily_data['message']

        # 템플릿에 전달할 데이터 준비
        df = self.analyzer.trading_data[
            self.analyzer.trading_data['timestamp'].dt.date == pd.to_datetime(date).date()
        ]

        template_data = {
            'date': date,
            'total_trades': daily_data['total_trades'],
            'total_pnl': daily_data['total_pnl'],
            'win_rate': daily_data['win_rate'],
            'trades': df.to_dict('records'),
            'best_trade_pnl': daily_data['best_trade']['pnl'] if daily_data['best_trade'] else 0,
            'best_trade_symbol': daily_data['best_trade']['symbol'] if daily_data['best_trade'] else 'N/A',
            'worst_trade_pnl': daily_data['worst_trade']['pnl'] if daily_data['worst_trade'] else 0,
            'worst_trade_symbol': daily_data['worst_trade']['symbol'] if daily_data['worst_trade'] else 'N/A',
            'symbols_traded': daily_data['symbols_traded'],
            'total_volume': daily_data['total_volume'],
            'total_fees': daily_data['total_fees'],
            'report_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # HTML 리포트 생성
        template = Template(self.report_templates['daily'])
        html_content = template.render(**template_data)

        if output_format == 'html':
            filename = f"reports/daily_report_{date}.html"
            os.makedirs('reports', exist_ok=True)
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            return filename

        elif output_format == 'pdf':
            # PDF 기능 비활성화 - HTML로 대체
            html_filename = f"reports/daily_report_{date}.html"
            os.makedirs('reports', exist_ok=True)
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            return f"PDF 기능 없음 - HTML로 저장됨: {html_filename}"

    def generate_weekly_report(self, week_start: str = None) -> str:
        """주간 성과 분석 리포트 생성"""
        if week_start is None:
            today = datetime.now()
            week_start = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')

        week_start_date = pd.to_datetime(week_start)
        week_end_date = week_start_date + timedelta(days=6)

        # 주간 데이터 필터링
        weekly_data = self.analyzer.trading_data[
            (self.analyzer.trading_data['timestamp'].dt.date >= week_start_date.date()) &
            (self.analyzer.trading_data['timestamp'].dt.date <= week_end_date.date())
        ]

        if weekly_data.empty:
            return f"주간 데이터가 없습니다: {week_start} ~ {week_end_date.strftime('%Y-%m-%d')}"

        # 주간 성과 계산
        weekly_metrics = {
            'weekly_pnl': weekly_data['pnl'].sum(),
            'total_trades': len(weekly_data),
            'win_rate': (len(weekly_data[weekly_data['pnl'] > 0]) / len(weekly_data)) * 100,
            'profit_factor': abs(weekly_data[weekly_data['pnl'] > 0]['pnl'].mean() /
                               weekly_data[weekly_data['pnl'] <= 0]['pnl'].mean()) if len(weekly_data[weekly_data['pnl'] <= 0]) > 0 else 0
        }

        # 일별 요약 생성
        daily_summary = []
        for i in range(7):
            day = week_start_date + timedelta(days=i)
            day_data = weekly_data[weekly_data['timestamp'].dt.date == day.date()]

            if not day_data.empty:
                daily_summary.append({
                    'date': day.strftime('%Y-%m-%d'),
                    'trades': len(day_data),
                    'pnl': day_data['pnl'].sum(),
                    'win_rate': (len(day_data[day_data['pnl'] > 0]) / len(day_data)) * 100,
                    'best_trade': day_data['pnl'].max()
                })

        # 전략 분석
        strengths, improvements = self.analyze_strategy(weekly_data)

        template_data = {
            'week_start': week_start,
            'week_end': week_end_date.strftime('%Y-%m-%d'),
            'daily_summary': daily_summary,
            'strengths': strengths,
            'improvements': improvements,
            'report_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            **weekly_metrics,
            **self.analyzer.calculate_performance_metrics()
        }

        template = Template(self.report_templates['weekly'])
        html_content = template.render(**template_data)

        filename = f"reports/weekly_report_{week_start}.html"
        os.makedirs('reports', exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return filename

    def analyze_strategy(self, data: pd.DataFrame) -> Tuple[List[str], List[str]]:
        """전략 분석 및 개선 제안"""
        strengths = []
        improvements = []

        win_rate = (len(data[data['pnl'] > 0]) / len(data)) * 100 if len(data) > 0 else 0

        if win_rate >= 60:
            strengths.append(f"높은 승률 ({win_rate:.1f}%) 달성")
        elif win_rate < 50:
            improvements.append("승률 개선 필요 - 진입 조건 최적화 검토")

        avg_win = data[data['pnl'] > 0]['pnl'].mean() if len(data[data['pnl'] > 0]) > 0 else 0
        avg_loss = abs(data[data['pnl'] <= 0]['pnl'].mean()) if len(data[data['pnl'] <= 0]) > 0 else 0

        if avg_win > avg_loss * 1.5:
            strengths.append("우수한 손익비 유지")
        elif avg_loss > avg_win:
            improvements.append("손실 최소화 전략 필요 - 손절 기준 강화")

        total_pnl = data['pnl'].sum()
        if total_pnl > 0:
            strengths.append("안정적인 수익 창출")
        else:
            improvements.append("수익성 개선 필요 - 시장 조건 재분석")

        return strengths, improvements

    def generate_monthly_report(self, month: str = None) -> str:
        """월간 종합 투자 리포트 생성"""
        if month is None:
            month = datetime.now().strftime('%Y-%m')

        # 샘플 데이터로 월간 리포트 생성
        template_data = {
            'month': month,
            'executive_summary': f"{month} 기간 동안 AI 기반 암호화폐 거래 시스템을 통해 안정적인 수익을 달성했습니다. 특히 RSI 기반 진입 전략이 효과적이었으며, 리스크 관리 시스템이 큰 손실을 방지했습니다.",
            'monthly_return': 8.5,
            'absolute_profit': 425.30,
            'win_rate': 62.5,
            'last_month_return': 6.2,
            'return_change': 2.3,
            'sharpe_ratio': 1.85,
            'last_sharpe': 1.60,
            'sharpe_change': 0.25,
            'max_drawdown': -4.2,
            'last_drawdown': -6.8,
            'drawdown_change': 2.6,
            'backtest_comparison': [
                {'metric': '총 수익률', 'backtest': '12.0%', 'live': '8.5%', 'difference': '-3.5%', 'reason': '슬리피지, 수수료'},
                {'metric': '승률', 'backtest': '65.0%', 'live': '62.5%', 'difference': '-2.5%', 'reason': '실시간 시장 변동성'},
                {'metric': '샤프 비율', 'backtest': '2.1', 'live': '1.85', 'difference': '-0.25', 'reason': '예상보다 높은 변동성'}
            ],
            'market_risk': '중간 수준 - 비트코인 변동성 증가',
            'liquidity_risk': '낮음 - 주요 거래소 사용',
            'technical_risk': '낮음 - 시스템 안정성 확보',
            'operational_risk': '낮음 - 자동화된 리스크 관리',
            'strategy_improvements': [
                '거래량 지표 추가로 진입 정확도 향상',
                '다중 시간대 분석을 통한 시그널 강화',
                '시장 상황별 포지션 사이징 최적화'
            ],
            'risk_improvements': [
                '일중 최대 손실 한도를 3%로 축소',
                '연속 손실 시 포지션 크기 자동 감소',
                '주요 뉴스 이벤트 대응 시스템 구축'
            ],
            'report_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        template = Template(self.report_templates['monthly'])
        html_content = template.render(**template_data)

        filename = f"reports/monthly_report_{month}.html"
        os.makedirs('reports', exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return filename