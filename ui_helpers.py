"""
UI Helpers - Crypto Trader Pro
UI 헬퍼 함수들 - CSS 스타일, 차트 헬퍼, 성과 분석 등
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

def get_css_styles():
    """CSS 스타일 반환"""
    return """
    <style>
        /* 메인 헤더 스타일 */
        .main-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            border-radius: 10px;
            text-align: center;
            color: white;
            margin-bottom: 2rem;
        }

        /* 카드 스타일 */
        .card {
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
            border-left: 4px solid #667eea;
        }

        /* 메트릭 카드 */
        .metric-card {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            padding: 1rem;
            border-radius: 10px;
            text-align: center;
            color: white;
            margin: 0.5rem;
        }

        /* 성공 메시지 */
        .success-box {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 1rem;
            border-radius: 5px;
            margin: 1rem 0;
        }

        /* 경고 메시지 */
        .warning-box {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
            padding: 1rem;
            border-radius: 5px;
            margin: 1rem 0;
        }

        /* 버튼 스타일 */
        .stButton > button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            padding: 0.5rem 2rem;
            font-weight: bold;
            transition: all 0.3s ease;
        }

        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }

        /* 사이드바 스타일 */
        .sidebar .sidebar-content {
            background: #f8f9fa;
        }

        /* 입력 필드 스타일 */
        .stTextInput > div > div > input {
            border-radius: 10px;
            border: 2px solid #e9ecef;
            padding: 0.75rem;
        }

        .stTextInput > div > div > input:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
        }
    </style>
    """

def show_performance_analysis_charts(risk_data):
    """성과 분석 차트 표시"""

    st.markdown("### 📈 성과 분석 차트")

    # 탭으로 차트 구분
    chart_tab1, chart_tab2, chart_tab3, chart_tab4 = st.tabs([
        "일별 손익", "드로우다운", "승률 통계", "월별 수익률"
    ])

    with chart_tab1:
        show_daily_pnl_chart()

    with chart_tab2:
        show_drawdown_chart()

    with chart_tab3:
        show_win_rate_stats()

    with chart_tab4:
        show_monthly_returns_heatmap()

def show_daily_pnl_chart():
    """일별 손익 곡선"""
    from trading_functions import get_user_trades

    # 실제 거래 기록에서 일별 손익 데이터 가져오기
    try:
        trades = get_user_trades(st.session_state.user['id'])

        if not trades or len(trades) < 2:
            st.info("📊 일별 손익 차트를 표시하기 위해 더 많은 거래 데이터가 필요합니다.")
            return

        # 거래 데이터를 날짜별로 그룹화
        df = pd.DataFrame(trades)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date

        # 일별 손익 계산
        daily_pnl = df.groupby('date')['profit_loss'].sum().reset_index()
        daily_pnl['cumulative_pnl'] = daily_pnl['profit_loss'].cumsum()

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=daily_pnl['date'],
            y=daily_pnl['cumulative_pnl'],
            mode='lines+markers',
            name='누적 손익',
            line=dict(color='#1f77b4', width=2),
            marker=dict(size=6)
        ))

        fig.update_layout(
            title="📊 일별 누적 손익 추이",
            xaxis_title="날짜",
            yaxis_title="누적 손익 ($)",
            hovermode='x unified',
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"일별 손익 차트 생성 오류: {e}")
        st.info("📊 거래 데이터를 확인해주세요.")

def show_drawdown_chart():
    """드로우다운 차트"""
    from trading_functions import get_user_trades

    try:
        # 실제 거래 기록에서 드로우다운 계산
        trades = get_user_trades(st.session_state.user['id'])

        if not trades or len(trades) < 5:
            st.info("📉 드로우다운 차트를 표시하기 위해 더 많은 거래 데이터가 필요합니다.")
            return

        # 거래 데이터를 시간순으로 정렬
        df = pd.DataFrame(trades)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        # 누적 손익 계산
        df['cumulative_pnl'] = df['profit_loss'].cumsum()
        df['portfolio_value'] = 10000 + df['cumulative_pnl']  # 초기 자본 10000 가정

        # 드로우다운 계산
        running_max = df['portfolio_value'].expanding().max()
        drawdown = (df['portfolio_value'] - running_max) / running_max * 100

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=drawdown,
            mode='lines',
            name='드로우다운',
            line=dict(color='red', width=2),
            fill='tozeroy',
            fillcolor='rgba(255, 0, 0, 0.1)'
        ))

        fig.update_layout(
            title="📉 포트폴리오 드로우다운",
            xaxis_title="날짜",
            yaxis_title="드로우다운 (%)",
            hovermode='x unified',
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"드로우다운 차트 생성 오류: {e}")
        st.info("📉 거래 데이터를 확인해주세요.")

def show_win_rate_stats():
    """승률 및 손익비 통계"""
    from trading_functions import get_user_trades

    try:
        # 실제 거래 기록에서 승률 및 손익비 계산
        trades = get_user_trades(st.session_state.user['id'])

        if not trades or len(trades) < 5:
            st.info("🎯 승률 통계를 표시하기 위해 더 많은 거래 데이터가 필요합니다.")
            return

        col1, col2 = st.columns(2)

        with col1:
            # 실제 승률 계산
            winning_trades = [t for t in trades if t['profit_loss'] > 0]
            win_rate = (len(winning_trades) / len(trades)) * 100
            lose_rate = 100 - win_rate

            fig_donut = go.Figure(data=[go.Pie(
                labels=['승리', '패배'],
                values=[win_rate, lose_rate],
                hole=0.6,
                marker_colors=['#00cc96', '#ff6b6b']
            )])

            fig_donut.update_layout(
                title="🎯 승률 분석",
                annotations=[dict(text=f'{win_rate:.1f}%', x=0.5, y=0.5, font_size=20, showarrow=False)],
                height=400
            )

            st.plotly_chart(fig_donut, use_container_width=True)

        with col2:
            # 실제 손익 분포
            recent_trades = trades[:10]  # 최근 10개 거래
            profit_loss_values = [t['profit_loss'] for t in recent_trades]

            fig_bar = go.Figure(data=[go.Bar(
                x=[f'Trade {i+1}' for i in range(len(profit_loss_values))],
                y=profit_loss_values,
                marker_color=['green' if pnl > 0 else 'red' for pnl in profit_loss_values]
            )])

            fig_bar.update_layout(
                title="💰 최근 거래 손익 분포",
                xaxis_title="거래",
                yaxis_title="손익 ($)",
                height=400
            )

            st.plotly_chart(fig_bar, use_container_width=True)

    except Exception as e:
        st.error(f"승률 통계 생성 오류: {e}")
        st.info("🎯 거래 데이터를 확인해주세요.")

def show_monthly_returns_heatmap():
    """월별 수익률 히트맵"""
    from trading_functions import get_user_trades

    try:
        # 실제 거래 기록에서 월별 수익률 계산
        trades = get_user_trades(st.session_state.user['id'])

        if not trades or len(trades) < 10:
            st.info("🗓️ 월별 수익률 히트맵을 표시하기 위해 더 많은 거래 데이터가 필요합니다.")
            return

        # 거래 데이터를 월별로 그룹화
        df = pd.DataFrame(trades)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['year'] = df['timestamp'].dt.year
        df['month'] = df['timestamp'].dt.month

        # 월별 수익률 계산
        monthly_returns = df.groupby(['year', 'month'])['profit_loss'].sum().reset_index()

        # 히트맵 데이터 준비
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        years = sorted(monthly_returns['year'].unique())

        returns_data = []
        for year in years:
            year_returns = []
            for month_num in range(1, 13):
                monthly_data = monthly_returns[
                    (monthly_returns['year'] == year) &
                    (monthly_returns['month'] == month_num)
                ]
                if not monthly_data.empty:
                    # 수익률을 퍼센트로 변환 (초기 자본 10000 가정)
                    monthly_return = (monthly_data['profit_loss'].iloc[0] / 10000) * 100
                    year_returns.append(monthly_return)
                else:
                    year_returns.append(None)
            returns_data.append(year_returns)

        fig_heatmap = go.Figure(data=go.Heatmap(
            z=returns_data,
            x=months,
            y=years,
            colorscale='RdYlGn',
            zmid=0,
            text=[[f'{val:.1f}%' if val is not None else '' for val in row] for row in returns_data],
            texttemplate='%{text}',
            textfont={"size": 10},
            hoverongaps=False
        ))

        fig_heatmap.update_layout(
            title="🗓️ 월별 수익률 히트맵",
            xaxis_title="월",
            yaxis_title="년도",
            height=300
        )

        st.plotly_chart(fig_heatmap, use_container_width=True)

    except Exception as e:
        st.error(f"월별 수익률 히트맵 생성 오류: {e}")
        st.info("🗓️ 거래 데이터를 확인해주세요.")

def create_metric_card(title, value, subtitle=None, color="#667eea"):
    """메트릭 카드 생성"""
    subtitle_html = f"<p style='margin: 0; font-size: 0.8rem; opacity: 0.8;'>{subtitle}</p>" if subtitle else ""

    return f"""
    <div style="
        background: {color};
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin: 0.5rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    ">
        <h4 style="margin: 0; font-size: 0.9rem;">{title}</h4>
        <h2 style="margin: 0.5rem 0; font-size: 1.5rem;">{value}</h2>
        {subtitle_html}
    </div>
    """

def create_info_card(title, content, icon="📊"):
    """정보 카드 생성"""
    return f"""
    <div style="
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
    ">
        <h4 style="margin: 0 0 1rem 0; color: #333;">{icon} {title}</h4>
        <div>{content}</div>
    </div>
    """

def create_alert_box(message, alert_type="info"):
    """알림 박스 생성"""
    colors = {
        "success": {"bg": "#d4edda", "border": "#c3e6cb", "text": "#155724"},
        "warning": {"bg": "#fff3cd", "border": "#ffeaa7", "text": "#856404"},
        "error": {"bg": "#f8d7da", "border": "#f5c6cb", "text": "#721c24"},
        "info": {"bg": "#d1ecf1", "border": "#bee5eb", "text": "#0c5460"}
    }

    color = colors.get(alert_type, colors["info"])

    return f"""
    <div style="
        background: {color['bg']};
        border: 1px solid {color['border']};
        color: {color['text']};
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    ">
        {message}
    </div>
    """

def format_currency(amount, currency="$"):
    """통화 포맷팅"""
    return f"{currency}{amount:,.2f}"

def format_percentage(value, decimal_places=2):
    """퍼센트 포맷팅"""
    return f"{value:.{decimal_places}f}%"

def get_color_by_value(value, positive_color="green", negative_color="red", neutral_color="gray"):
    """값에 따른 색상 반환"""
    if value > 0:
        return positive_color
    elif value < 0:
        return negative_color
    else:
        return neutral_color

def create_progress_bar(value, max_value, label="", color="#667eea"):
    """진행률 바 생성"""
    percentage = min((value / max_value) * 100, 100) if max_value > 0 else 0

    return f"""
    <div style="margin: 1rem 0;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
            <span>{label}</span>
            <span>{percentage:.1f}%</span>
        </div>
        <div style="
            background: #e9ecef;
            border-radius: 10px;
            height: 20px;
            overflow: hidden;
        ">
            <div style="
                background: {color};
                height: 100%;
                width: {percentage}%;
                transition: width 0.3s ease;
            "></div>
        </div>
    </div>
    """

def show_loading_spinner(text="로딩 중..."):
    """로딩 스피너 표시"""
    return f"""
    <div style="
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 2rem;
    ">
        <div style="
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin-right: 1rem;
        "></div>
        <span>{text}</span>
    </div>
    <style>
    @keyframes spin {{
        0% {{ transform: rotate(0deg); }}
        100% {{ transform: rotate(360deg); }}
    }}
    </style>
    """

def create_status_badge(status, status_map=None):
    """상태 배지 생성"""
    if status_map is None:
        status_map = {
            "active": {"color": "#28a745", "text": "활성"},
            "inactive": {"color": "#6c757d", "text": "비활성"},
            "pending": {"color": "#ffc107", "text": "대기중"},
            "error": {"color": "#dc3545", "text": "오류"},
            "success": {"color": "#28a745", "text": "성공"}
        }

    badge_info = status_map.get(status, {"color": "#6c757d", "text": status})

    return f"""
    <span style="
        background: {badge_info['color']};
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
    ">
        {badge_info['text']}
    </span>
    """

def create_data_table(data, columns=None, title=None):
    """데이터 테이블 생성"""
    if not data:
        return "<p>표시할 데이터가 없습니다.</p>"

    df = pd.DataFrame(data)

    if columns:
        df = df[columns] if all(col in df.columns for col in columns) else df

    table_html = df.to_html(
        index=False,
        classes="table table-striped",
        escape=False,
        table_id="data-table"
    )

    title_html = f"<h4>{title}</h4>" if title else ""

    return f"""
    {title_html}
    <div style="overflow-x: auto;">
        {table_html}
    </div>
    <style>
    #data-table {{
        width: 100%;
        border-collapse: collapse;
        margin: 1rem 0;
    }}
    #data-table th,
    #data-table td {{
        padding: 0.75rem;
        text-align: left;
        border-bottom: 1px solid #dee2e6;
    }}
    #data-table th {{
        background-color: #f8f9fa;
        font-weight: bold;
    }}
    #data-table tr:hover {{
        background-color: #f5f5f5;
    }}
    </style>
    """

def show_empty_state(title="데이터 없음", message="표시할 데이터가 없습니다.", icon="📭"):
    """빈 상태 표시"""
    return f"""
    <div style="
        text-align: center;
        padding: 3rem 2rem;
        color: #6c757d;
    ">
        <div style="font-size: 3rem; margin-bottom: 1rem;">{icon}</div>
        <h3 style="margin-bottom: 0.5rem; color: #495057;">{title}</h3>
        <p>{message}</p>
    </div>
    """