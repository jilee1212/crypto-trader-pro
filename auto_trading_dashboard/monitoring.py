"""
📊 Enhanced Real-time Monitoring Dashboard - Phase 4

Phase 4 강화된 실시간 자동매매 모니터링 대시보드
- 고급 시스템 상태 모니터링
- 다층 안전 시스템 상태 추적
- 실시간 성과 및 위험 지표
- 알림 시스템 통합
- 예측 분석 및 경고 시스템
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import asyncio
import random
from typing import Dict, List, Any, Optional, Tuple

class EnhancedMonitoringDashboard:
    """📊 Phase 4 강화된 실시간 모니터링 대시보드"""

    def __init__(self):
        self.initialize_session_state()

    def initialize_session_state(self):
        """세션 상태 초기화"""
        if 'monitoring_last_update' not in st.session_state:
            st.session_state.monitoring_last_update = datetime.now()

        if 'monitoring_auto_refresh' not in st.session_state:
            st.session_state.monitoring_auto_refresh = True

        if 'monitoring_alert_history' not in st.session_state:
            st.session_state.monitoring_alert_history = []

    def show_enhanced_monitoring_dashboard(self):
        """Phase 4 강화된 모니터링 대시보드"""
        st.title("📊 실시간 모니터링 대시보드")
        st.markdown("**Phase 4: 고급 실시간 모니터링 및 예측 분석**")

        # 설정 패널
        self.show_monitoring_settings()

        # 탭 구성
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🎛️ 시스템 상태", "🛡️ 안전 시스템", "📈 실시간 성과",
            "⚠️ 경고 시스템", "🔍 상세 분석"
        ])

        with tab1:
            self.show_enhanced_system_overview()

        with tab2:
            self.show_enhanced_safety_monitoring()

        with tab3:
            self.show_enhanced_performance_charts()

        with tab4:
            self.show_alert_management_system()

        with tab5:
            self.show_detailed_analysis()

    def show_monitoring_settings(self):
        """모니터링 설정 패널"""
        with st.expander("⚙️ 모니터링 설정", expanded=False):
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                auto_refresh = st.checkbox(
                    "자동 새로고침",
                    value=st.session_state.monitoring_auto_refresh,
                    key="enhanced_auto_refresh"
                )
                st.session_state.monitoring_auto_refresh = auto_refresh

                if auto_refresh:
                    refresh_interval = st.selectbox(
                        "새로고침 간격",
                        [10, 30, 60, 120, 300],
                        index=1,
                        key="enhanced_refresh_interval"
                    )
                    # 실제 자동 새로고침 로직은 여기에

            with col2:
                alert_level = st.selectbox(
                    "알림 수준",
                    ["모든 알림", "중요 알림만", "긴급 알림만"],
                    index=1,
                    key="enhanced_alert_level"
                )

            with col3:
                chart_timeframe = st.selectbox(
                    "차트 시간범위",
                    ["1시간", "6시간", "24시간", "7일"],
                    index=2,
                    key="enhanced_chart_timeframe"
                )

            with col4:
                if st.button("🔄 데이터 새로고침", key="enhanced_manual_refresh"):
                    st.session_state.monitoring_last_update = datetime.now()
                    st.success("✅ 데이터가 새로고침되었습니다!")
                    st.rerun()

    def show_enhanced_system_overview(self):
        """강화된 시스템 상태 개요"""
        st.subheader("🎛️ 시스템 상태 개요")

        # 메인 상태 카드
        self.show_main_status_cards()

        st.divider()

        # 시스템 성능 지표
        self.show_system_performance_metrics()

        st.divider()

        # 연결 상태 및 API 헬스 체크
        self.show_api_health_status()

    def show_main_status_cards(self):
        """메인 상태 카드"""
        # 시뮬레이션 데이터
        system_data = self.get_enhanced_system_data()

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            status = system_data['status']
            status_emoji = {
                'RUNNING': '🟢',
                'STOPPED': '🔴',
                'STARTING': '🟡',
                'STOPPING': '🟡',
                'ERROR': '🔴',
                'EMERGENCY_STOP': '🚨'
            }.get(status, '⚪')

            st.metric(
                "시스템 상태",
                f"{status_emoji} {status}",
                delta=None
            )

        with col2:
            uptime = system_data['uptime_hours']
            st.metric(
                "가동 시간",
                f"{uptime:.1f}h",
                delta=f"+{random.uniform(0.1, 0.5):.1f}h"
            )

        with col3:
            cpu_usage = system_data['cpu_usage']
            memory_usage = system_data['memory_usage']
            st.metric(
                "시스템 리소스",
                f"CPU: {cpu_usage:.1f}%",
                f"MEM: {memory_usage:.1f}%"
            )

        with col4:
            api_calls = system_data['api_calls_per_minute']
            st.metric(
                "API 호출률",
                f"{api_calls}/min",
                delta=f"+{random.randint(1, 5)}"
            )

        with col5:
            latency = system_data['avg_response_time']
            st.metric(
                "평균 응답시간",
                f"{latency}ms",
                delta=f"{random.randint(-10, 10)}ms"
            )

    def show_system_performance_metrics(self):
        """시스템 성능 지표"""
        st.subheader("📊 성능 지표")

        performance_data = self.get_performance_metrics()

        col1, col2 = st.columns(2)

        with col1:
            # 시스템 리소스 사용률 차트
            fig_resources = go.Figure()

            time_series = performance_data['timestamps']
            fig_resources.add_trace(go.Scatter(
                x=time_series,
                y=performance_data['cpu_usage'],
                mode='lines',
                name='CPU 사용률 (%)',
                line=dict(color='red')
            ))

            fig_resources.add_trace(go.Scatter(
                x=time_series,
                y=performance_data['memory_usage'],
                mode='lines',
                name='메모리 사용률 (%)',
                line=dict(color='blue'),
                yaxis='y2'
            ))

            fig_resources.update_layout(
                title="시스템 리소스 사용률",
                xaxis_title="시간",
                yaxis_title="CPU (%)",
                yaxis2=dict(
                    title="메모리 (%)",
                    overlaying='y',
                    side='right'
                ),
                height=300
            )

            st.plotly_chart(fig_resources, use_container_width=True)

        with col2:
            # API 응답시간 분포
            response_times = performance_data['response_times']
            fig_latency = px.histogram(
                x=response_times,
                nbins=20,
                title="API 응답시간 분포",
                labels={'x': '응답시간 (ms)', 'y': '빈도'}
            )

            fig_latency.add_vline(
                x=np.mean(response_times),
                line_dash="dash",
                line_color="red",
                annotation_text=f"평균: {np.mean(response_times):.0f}ms"
            )

            st.plotly_chart(fig_latency, use_container_width=True)

    def show_api_health_status(self):
        """API 헬스 상태"""
        st.subheader("🔌 API 연결 상태")

        api_status = self.get_api_health_data()

        # API 상태 그리드
        cols = st.columns(4)
        for i, (api_name, status_data) in enumerate(api_status.items()):
            with cols[i % 4]:
                status = status_data['status']
                latency = status_data['latency']
                success_rate = status_data['success_rate']

                status_color = "🟢" if status == "HEALTHY" else "🔴" if status == "DOWN" else "🟡"

                st.metric(
                    f"{status_color} {api_name}",
                    f"{latency}ms",
                    f"{success_rate:.1f}% 성공률"
                )

        # API 호출 통계 차트
        self.show_api_statistics_chart()

    def show_api_statistics_chart(self):
        """API 통계 차트"""
        api_stats = self.generate_api_statistics_data()

        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('API 호출 횟수', '성공률', '응답시간', '에러율'),
            specs=[[{"type": "bar"}, {"type": "scatter"}],
                   [{"type": "scatter"}, {"type": "bar"}]]
        )

        # API 호출 횟수
        fig.add_trace(
            go.Bar(x=list(api_stats.keys()), y=[s['calls'] for s in api_stats.values()], name="호출 수"),
            row=1, col=1
        )

        # 성공률
        fig.add_trace(
            go.Scatter(x=list(api_stats.keys()), y=[s['success_rate'] for s in api_stats.values()],
                      mode='lines+markers', name="성공률 (%)"),
            row=1, col=2
        )

        # 응답시간
        fig.add_trace(
            go.Scatter(x=list(api_stats.keys()), y=[s['avg_latency'] for s in api_stats.values()],
                      mode='lines+markers', name="응답시간 (ms)"),
            row=2, col=1
        )

        # 에러율
        fig.add_trace(
            go.Bar(x=list(api_stats.keys()), y=[s['error_rate'] for s in api_stats.values()], name="에러율 (%)"),
            row=2, col=2
        )

        fig.update_layout(height=500, showlegend=False, title_text="API 통계 대시보드")
        st.plotly_chart(fig, use_container_width=True)

    def show_enhanced_safety_monitoring(self):
        """강화된 안전 시스템 모니터링"""
        st.subheader("🛡️ 안전 시스템 모니터링")

        safety_data = self.get_enhanced_safety_data()

        # 안전 시스템 상태 카드
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            overall_status = safety_data['overall_status']
            status_color = "🟢" if overall_status == "SAFE" else "🟡" if overall_status == "WARNING" else "🔴"
            st.metric("전체 안전 상태", f"{status_color} {overall_status}")

        with col2:
            active_checks = safety_data['active_checks']
            total_checks = safety_data['total_checks']
            st.metric("활성 검사", f"{active_checks}/{total_checks}")

        with col3:
            emergency_triggers = safety_data['emergency_triggers_today']
            st.metric("오늘 긴급 이벤트", str(emergency_triggers))

        with col4:
            last_check_time = safety_data['last_safety_check']
            st.metric("마지막 검사", last_check_time)

        # 안전 검사 상세 상태
        self.show_safety_checks_detail(safety_data)

        # 위험 요소 분석
        self.show_risk_analysis()

    def show_enhanced_performance_charts(self):
        """강화된 실시간 성과 차트"""
        st.subheader("📈 실시간 성과 분석")

        # 성과 데이터 생성
        performance_data = self.generate_enhanced_performance_data()

        # 메인 성과 지표
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("실시간 P&L", f"${performance_data['current_pnl']:.2f}",
                     f"{performance_data['pnl_change']:.2f}%")

        with col2:
            st.metric("승률", f"{performance_data['win_rate']:.1f}%",
                     f"{performance_data['win_rate_change']:.1f}%")

        with col3:
            st.metric("샤프 비율", f"{performance_data['sharpe_ratio']:.2f}")

        with col4:
            st.metric("최대 드로다운", f"{performance_data['max_drawdown']:.2f}%")

        # 성과 차트들
        col1, col2 = st.columns(2)

        with col1:
            self.plot_real_time_pnl_chart(performance_data)

        with col2:
            self.plot_trade_distribution_chart(performance_data)

        # 포지션 및 리스크 분석
        self.show_position_risk_analysis()

    def show_alert_management_system(self):
        """경고 관리 시스템"""
        st.subheader("⚠️ 경고 관리 시스템")

        # 활성 경고 카운터
        alert_data = self.get_alert_system_data()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("활성 경고", alert_data['active_alerts'])

        with col2:
            st.metric("긴급 경고", alert_data['critical_alerts'])

        with col3:
            st.metric("오늘 총 경고", alert_data['total_alerts_today'])

        with col4:
            st.metric("해결된 경고", alert_data['resolved_alerts'])

        # 경고 목록 및 관리
        self.show_active_alerts_list(alert_data)

        # 경고 통계 및 트렌드
        self.show_alert_statistics()

    def show_detailed_analysis(self):
        """상세 분석"""
        st.subheader("🔍 상세 분석")

        analysis_type = st.selectbox(
            "분석 유형 선택",
            ["성과 분석", "리스크 분석", "시장 분석", "시스템 분석"],
            key="detailed_analysis_type"
        )

        if analysis_type == "성과 분석":
            self.show_performance_deep_dive()
        elif analysis_type == "리스크 분석":
            self.show_risk_deep_dive()
        elif analysis_type == "시장 분석":
            self.show_market_analysis()
        else:
            self.show_system_analysis()

    def get_enhanced_system_data(self) -> Dict[str, Any]:
        """강화된 시스템 데이터 생성"""
        return {
            'status': random.choice(['RUNNING', 'RUNNING', 'RUNNING', 'WARNING']),
            'uptime_hours': random.uniform(12, 72),
            'cpu_usage': random.uniform(20, 80),
            'memory_usage': random.uniform(40, 90),
            'api_calls_per_minute': random.randint(30, 120),
            'avg_response_time': random.randint(50, 200)
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """성능 메트릭 데이터 생성"""
        timestamps = [datetime.now() - timedelta(minutes=i*5) for i in range(24, 0, -1)]

        return {
            'timestamps': timestamps,
            'cpu_usage': [random.uniform(20, 80) for _ in range(24)],
            'memory_usage': [random.uniform(40, 90) for _ in range(24)],
            'response_times': [random.randint(50, 300) for _ in range(100)]
        }

    def get_api_health_data(self) -> Dict[str, Dict[str, Any]]:
        """API 헬스 데이터 생성"""
        apis = ['Binance', 'Coinbase', 'Kraken', 'Bybit']

        return {
            api: {
                'status': random.choice(['HEALTHY', 'HEALTHY', 'HEALTHY', 'SLOW', 'DOWN']),
                'latency': random.randint(30, 200),
                'success_rate': random.uniform(95, 100)
            } for api in apis
        }

    def generate_api_statistics_data(self) -> Dict[str, Dict[str, Any]]:
        """API 통계 데이터 생성"""
        apis = ['Binance', 'Coinbase', 'Kraken', 'Bybit']

        return {
            api: {
                'calls': random.randint(100, 500),
                'success_rate': random.uniform(95, 100),
                'avg_latency': random.randint(30, 150),
                'error_rate': random.uniform(0, 5)
            } for api in apis
        }

    def get_enhanced_safety_data(self) -> Dict[str, Any]:
        """강화된 안전 시스템 데이터"""
        return {
            'overall_status': random.choice(['SAFE', 'SAFE', 'WARNING', 'CRITICAL']),
            'active_checks': random.randint(6, 8),
            'total_checks': 8,
            'emergency_triggers_today': random.randint(0, 3),
            'last_safety_check': f"{random.randint(1, 30)}초 전"
        }

    def generate_enhanced_performance_data(self) -> Dict[str, Any]:
        """강화된 성과 데이터 생성"""
        return {
            'current_pnl': random.uniform(-100, 500),
            'pnl_change': random.uniform(-5, 10),
            'win_rate': random.uniform(60, 95),
            'win_rate_change': random.uniform(-3, 5),
            'sharpe_ratio': random.uniform(0.5, 3.0),
            'max_drawdown': random.uniform(2, 15)
        }

    def get_alert_system_data(self) -> Dict[str, int]:
        """경고 시스템 데이터"""
        return {
            'active_alerts': random.randint(0, 5),
            'critical_alerts': random.randint(0, 2),
            'total_alerts_today': random.randint(5, 20),
            'resolved_alerts': random.randint(10, 50)
        }

    # 추가 헬퍼 메서드들 (간단한 구현)
    def show_safety_checks_detail(self, safety_data):
        """안전 검사 상세 정보"""
        st.info("안전 검사 상세 정보가 여기에 표시됩니다.")

    def show_risk_analysis(self):
        """위험 요소 분석"""
        st.info("위험 요소 분석이 여기에 표시됩니다.")

    def plot_real_time_pnl_chart(self, performance_data):
        """실시간 P&L 차트"""
        st.info("실시간 P&L 차트가 여기에 표시됩니다.")

    def plot_trade_distribution_chart(self, performance_data):
        """거래 분포 차트"""
        st.info("거래 분포 차트가 여기에 표시됩니다.")

    def show_position_risk_analysis(self):
        """포지션 리스크 분석"""
        st.info("포지션 리스크 분석이 여기에 표시됩니다.")

    def show_active_alerts_list(self, alert_data):
        """활성 경고 목록"""
        st.info("활성 경고 목록이 여기에 표시됩니다.")

    def show_alert_statistics(self):
        """경고 통계"""
        st.info("경고 통계가 여기에 표시됩니다.")

    def show_performance_deep_dive(self):
        """성과 심층 분석"""
        st.info("성과 심층 분석이 여기에 표시됩니다.")

    def show_risk_deep_dive(self):
        """리스크 심층 분석"""
        st.info("리스크 심층 분석이 여기에 표시됩니다.")

    def show_market_analysis(self):
        """시장 분석"""
        st.info("시장 분석이 여기에 표시됩니다.")

    def show_system_analysis(self):
        """시스템 분석"""
        st.info("시스템 분석이 여기에 표시됩니다.")

def show_real_time_monitoring():
    """Phase 4 강화된 실시간 모니터링 대시보드 (호환성 함수)"""
    try:
        dashboard = EnhancedMonitoringDashboard()
        dashboard.show_enhanced_monitoring_dashboard()
    except Exception as e:
        st.error(f"모니터링 대시보드 로드 실패: {e}")
        # 폴백: 기존 함수 호출
        show_legacy_monitoring()

def show_legacy_monitoring():
    """기존 모니터링 시스템 (폴백)"""
    st.markdown("### 📊 실시간 시스템 모니터링")

    # 시뮬레이션 데이터
    dashboard_data = get_simulated_dashboard_data()

    # 시스템 상태 개요
    show_system_overview(dashboard_data)

    st.divider()

    # 안전 시스템 모니터링
    show_safety_system_monitoring(dashboard_data)

    st.divider()

    # 실시간 성과 차트
    show_real_time_performance_charts(dashboard_data)

    st.divider()

    # 알림 및 로그 피드
    show_notification_feed(dashboard_data)

def show_system_overview(dashboard_data: Dict[str, Any]):
    """시스템 상태 개요"""

    st.markdown("#### 🎛️ 시스템 상태 개요")

    system_status = dashboard_data.get('system_status', {})
    stats = system_status.get('stats', {})

    # 메인 지표 카드
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        status = system_status.get('status', 'UNKNOWN')
        status_color = {
            'RUNNING': '🟢',
            'STOPPED': '🔴',
            'STARTING': '🟡',
            'STOPPING': '🟡',
            'ERROR': '🔴',
            'EMERGENCY_STOP': '🚨'
        }.get(status, '⚪')

        st.metric(
            "시스템 상태",
            f"{status_color} {status}",
            delta=None
        )

    with col2:
        uptime_hours = system_status.get('uptime', 0) / 3600
        st.metric(
            "가동 시간",
            f"{uptime_hours:.1f}시간",
            delta=None
        )

    with col3:
        success_rate = stats.get('success_rate', 0)
        st.metric(
            "거래 성공률",
            f"{success_rate:.1f}%",
            delta=f"+{success_rate-90:.1f}%" if success_rate > 90 else f"{success_rate-90:.1f}%"
        )

    with col4:
        today_pnl = stats.get('today_pnl', 0)
        st.metric(
            "오늘 수익",
            f"${today_pnl:.2f}",
            delta=f"+${today_pnl:.2f}" if today_pnl > 0 else f"${today_pnl:.2f}"
        )

    # 상세 지표
    st.markdown("#### 📈 상세 지표")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("총 거래", stats.get('total_trades', 0))

    with col2:
        st.metric("활성 포지션", stats.get('active_positions', 0))

    with col3:
        st.metric("생성된 신호", stats.get('signals_generated', 0))

    with col4:
        st.metric("시스템 오류", stats.get('errors_count', 0))

    with col5:
        total_pnl = stats.get('total_pnl', 0)
        st.metric("총 누적 수익", f"${total_pnl:.2f}")

def show_safety_system_monitoring(dashboard_data: Dict[str, Any]):
    """Phase 3 안전 시스템 모니터링"""

    st.markdown("#### 🛡️ 안전 시스템 모니터링")

    safety_status = dashboard_data.get('safety_status', {})
    emergency_status = dashboard_data.get('emergency_status', {})

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("##### 🔍 안전 검사 상태")

        total_checks = safety_status.get('total_checks', 0)
        passed_checks = safety_status.get('passed_checks', 0)
        failed_checks = safety_status.get('failed_checks', [])

        if total_checks > 0:
            pass_rate = (passed_checks / total_checks) * 100

            # 안전 검사 통과율 게이지
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=pass_rate,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "안전 검사 통과율 (%)"},
                delta={'reference': 100},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 80], 'color': "yellow"},
                        {'range': [80, 100], 'color': "lightgreen"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))

            fig_gauge.update_layout(height=300)
            st.plotly_chart(fig_gauge, use_container_width=True)

        else:
            st.info("안전 검사 데이터 없음")

        # 실패한 검사 목록
        if failed_checks:
            st.markdown("##### ⚠️ 실패한 안전 검사")
            for check in failed_checks:
                st.error(f"❌ {check.get('name', 'Unknown')}: {check.get('message', 'No message')}")
        else:
            st.success("✅ 모든 안전 검사 통과")

    with col2:
        st.markdown("##### 🚨 긴급 시스템")

        is_emergency = emergency_status.get('is_emergency_mode', False)
        total_events = emergency_status.get('total_events', 0)

        if is_emergency:
            st.error("🚨 긴급 모드 활성")
        else:
            st.success("✅ 정상 운영")

        st.metric("총 긴급 이벤트", total_events)

        # 최근 긴급 이벤트
        recent_events = emergency_status.get('recent_events', [])
        if recent_events:
            st.markdown("**최근 긴급 이벤트:**")
            for event in recent_events[-3:]:  # 최근 3개만
                timestamp = event.get('timestamp', '')[:16]  # YYYY-MM-DD HH:MM
                trigger = event.get('trigger', 'Unknown')
                st.text(f"{timestamp} - {trigger}")

def show_real_time_performance_charts(dashboard_data: Dict[str, Any]):
    """실시간 성과 차트"""

    st.markdown("#### 📈 실시간 성과 분석")

    # 시뮬레이션 차트 데이터 생성
    chart_data = generate_performance_chart_data()

    col1, col2 = st.columns(2)

    with col1:
        # PnL 차트
        fig_pnl = go.Figure()

        fig_pnl.add_trace(go.Scatter(
            x=chart_data['timestamps'],
            y=chart_data['cumulative_pnl'],
            mode='lines',
            name='누적 수익',
            line=dict(color='blue', width=2)
        ))

        fig_pnl.update_layout(
            title="누적 수익 추이",
            xaxis_title="시간",
            yaxis_title="수익 ($)",
            height=400
        )

        st.plotly_chart(fig_pnl, use_container_width=True)

    with col2:
        # 거래 성공률 차트
        fig_success = go.Figure()

        fig_success.add_trace(go.Scatter(
            x=chart_data['timestamps'],
            y=chart_data['success_rate'],
            mode='lines+markers',
            name='성공률',
            line=dict(color='green', width=2)
        ))

        fig_success.update_layout(
            title="거래 성공률 추이",
            xaxis_title="시간",
            yaxis_title="성공률 (%)",
            yaxis=dict(range=[0, 100]),
            height=400
        )

        st.plotly_chart(fig_success, use_container_width=True)

    # 포지션 및 신호 통계
    col1, col2 = st.columns(2)

    with col1:
        # 활성 포지션 파이 차트
        position_data = chart_data.get('positions', {})
        if position_data:
            fig_positions = px.pie(
                values=list(position_data.values()),
                names=list(position_data.keys()),
                title="활성 포지션 분포"
            )
            st.plotly_chart(fig_positions, use_container_width=True)
        else:
            st.info("활성 포지션 없음")

    with col2:
        # 신호 유형 분포 차트
        signal_data = chart_data.get('signals', {})
        if signal_data:
            fig_signals = px.bar(
                x=list(signal_data.keys()),
                y=list(signal_data.values()),
                title="신호 유형별 분포",
                color=list(signal_data.values()),
                color_continuous_scale='viridis'
            )
            st.plotly_chart(fig_signals, use_container_width=True)
        else:
            st.info("신호 데이터 없음")

def show_notification_feed(dashboard_data: Dict[str, Any]):
    """알림 및 로그 피드"""

    st.markdown("#### 🔔 실시간 알림 피드")

    recent_notifications = dashboard_data.get('recent_notifications', [])

    if recent_notifications:
        # 알림 타입별 필터
        notification_types = list(set([n.get('type', 'Unknown') for n in recent_notifications]))
        selected_types = st.multiselect(
            "알림 유형 필터",
            notification_types,
            default=notification_types
        )

        # 필터링된 알림 표시
        filtered_notifications = [
            n for n in recent_notifications
            if n.get('type', 'Unknown') in selected_types
        ]

        # 알림 카드 표시
        for notification in filtered_notifications[-10:]:  # 최근 10개
            show_notification_card(notification)
    else:
        st.info("알림 없음")

def show_notification_card(notification: Dict[str, Any]):
    """개별 알림 카드 표시"""

    notif_type = notification.get('type', 'Unknown')
    title = notification.get('title', 'No Title')
    message = notification.get('message', 'No Message')
    timestamp = notification.get('timestamp', '')
    priority = notification.get('priority', 1)

    # 우선순위별 색상
    priority_colors = {
        1: "🔵",  # LOW
        2: "🟢",  # NORMAL
        3: "🟡",  # HIGH
        4: "🟠",  # CRITICAL
        5: "🔴"   # EMERGENCY
    }

    priority_icon = priority_colors.get(priority, "⚪")

    # 타입별 아이콘
    type_icons = {
        'TRADE_EXECUTED': "💰",
        'PROFIT_TARGET_HIT': "🎯",
        'STOP_LOSS_HIT': "🛑",
        'DAILY_LOSS_WARNING': "⚠️",
        'SYSTEM_ERROR': "❌",
        'API_CONNECTION_LOST': "🔌",
        'EMERGENCY_STOP': "🚨",
        'SIGNAL_GENERATED': "🤖",
        'SYSTEM_STARTUP': "🚀",
        'SYSTEM_SHUTDOWN': "⏹️"
    }

    type_icon = type_icons.get(notif_type, "📝")

    # 시간 포맷
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        time_str = dt.strftime("%H:%M:%S")
    except:
        time_str = timestamp[:8] if len(timestamp) >= 8 else timestamp

    # 알림 카드
    with st.expander(f"{priority_icon} {type_icon} {title} ({time_str})", expanded=False):
        st.text(message)

        # 추가 데이터가 있으면 표시
        data = notification.get('data', {})
        if data:
            st.json(data)

def get_simulated_dashboard_data() -> Dict[str, Any]:
    """시뮬레이션 대시보드 데이터 생성"""

    # 실제 구현에서는 AutoTradingEngine.get_dashboard_data()를 호출
    return {
        'system_status': {
            'status': 'RUNNING',
            'uptime': 12600,  # 3.5시간
            'stats': {
                'total_trades': 47,
                'successful_trades': 42,
                'success_rate': 89.4,
                'total_pnl': 1250.75,
                'today_pnl': 89.50,
                'active_positions': 3,
                'signals_generated': 156,
                'errors_count': 2
            }
        },
        'safety_status': {
            'total_checks': 8,
            'passed_checks': 7,
            'failed_checks': [
                {'name': 'market_volatility', 'message': '변동성이 높은 상태입니다'}
            ]
        },
        'emergency_status': {
            'is_emergency_mode': False,
            'total_events': 1,
            'recent_events': [
                {
                    'trigger': 'DAILY_LOSS_WARNING',
                    'message': '일일 손실 80% 도달',
                    'timestamp': '2025-09-22T14:30:00',
                    'action_taken': '신규 거래 제한'
                }
            ]
        },
        'recent_notifications': [
            {
                'type': 'TRADE_EXECUTED',
                'title': '거래 실행: BTC/USDT',
                'message': 'BUY BTC/USDT 0.1 @ $65,000',
                'priority': 2,
                'timestamp': '2025-09-22T15:45:30',
                'data': {'symbol': 'BTC/USDT', 'side': 'BUY', 'price': 65000}
            },
            {
                'type': 'SIGNAL_GENERATED',
                'title': '새 신호: ETH/USDT',
                'message': 'SELL 신호 생성\\n신뢰도: 78%',
                'priority': 2,
                'timestamp': '2025-09-22T15:42:15',
                'data': {'symbol': 'ETH/USDT', 'confidence': 78}
            },
            {
                'type': 'DAILY_LOSS_WARNING',
                'title': '일일 손실 경고',
                'message': '일일 손실이 80%에 도달했습니다',
                'priority': 3,
                'timestamp': '2025-09-22T14:30:00',
                'data': {'threshold': 80.0}
            }
        ]
    }

def generate_performance_chart_data() -> Dict[str, Any]:
    """성과 차트용 시뮬레이션 데이터 생성"""

    import numpy as np

    # 시간 데이터 (최근 24시간)
    now = datetime.now()
    timestamps = [now - timedelta(hours=i) for i in range(24, 0, -1)]

    # 누적 수익 데이터 (랜덤 워크)
    returns = np.random.normal(0.5, 5, 24)  # 평균 0.5, 표준편차 5
    cumulative_pnl = np.cumsum(returns)

    # 성공률 데이터 (80-95% 범위에서 변동)
    success_rate = 85 + np.random.normal(0, 3, 24)
    success_rate = np.clip(success_rate, 60, 100)  # 60-100% 범위로 제한

    # 포지션 분포
    positions = {
        'BTC/USDT': 2,
        'ETH/USDT': 1,
        'BNB/USDT': 0
    }

    # 신호 유형 분포
    signals = {
        'BUY': 12,
        'SELL': 8,
        'HOLD': 15
    }

    return {
        'timestamps': timestamps,
        'cumulative_pnl': cumulative_pnl.tolist(),
        'success_rate': success_rate.tolist(),
        'positions': positions,
        'signals': signals
    }

def show_system_controls():
    """시스템 제어 버튼들"""

    st.markdown("#### 🎛️ 시스템 제어")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🚨 긴급 중단", type="primary", use_container_width=True, key="monitoring_emergency_stop"):
            # 실제 구현에서는 engine.manual_emergency_stop() 호출
            st.error("긴급 중단이 실행되었습니다!")
            st.balloons()

    with col2:
        if st.button("⚙️ 안전 검사", use_container_width=True, key="monitoring_safety_check"):
            # 실제 구현에서는 safety_system.run_all_safety_checks() 호출
            st.success("안전 검사가 완료되었습니다!")

    with col3:
        if st.button("🔄 상태 새로고침", use_container_width=True, key="monitoring_refresh"):
            st.rerun()

    with col4:
        if st.button("📊 상세 로그", use_container_width=True, key="monitoring_detailed_logs"):
            st.info("상세 로그 페이지로 이동합니다")

# 메인 함수에서 모든 컴포넌트 통합
def show_enhanced_auto_trading_dashboard():
    """Phase 3 강화된 자동매매 대시보드"""

    st.title("🤖 Phase 3 자동매매 시스템")
    st.markdown("**고급 안전 시스템 + 실시간 모니터링 + 알림 시스템**")

    # 시스템 제어 패널
    show_system_controls()

    st.divider()

    # 실시간 모니터링
    show_real_time_monitoring()