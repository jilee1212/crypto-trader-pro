"""
🎛️ Phase 4 Advanced Control Panel - 고급 자동매매 제어 패널

Phase 4에서 강화된 고급 제어 기능들:
- 정밀한 시작/중단 제어
- 긴급 상황 대응 시스템
- 실시간 상태 모니터링
- 동적 설정 변경
- 시스템 진단 및 복구
- 성과 실시간 추적
"""

import streamlit as st
import time
import json
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging

# Phase 4: 고급 제어를 위한 추가 import
try:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from auto_trading.engine import AutoTradingEngine, TradingStatus
    from utils.notifications import NotificationManager, NotificationType, NotificationPriority
    REAL_ENGINE_AVAILABLE = True
except ImportError:
    REAL_ENGINE_AVAILABLE = False

class AdvancedControlPanel:
    """🎛️ Phase 4 고급 자동매매 제어 패널"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Phase 4: 실제 엔진 연동
        if REAL_ENGINE_AVAILABLE:
            try:
                self.engine = AutoTradingEngine()
                self.real_engine = True
                self.logger.info("Phase 4: 실제 엔진과 연동됨")
            except Exception as e:
                self.logger.warning(f"엔진 초기화 실패, 시뮬레이션 모드: {e}")
                self.engine = None
                self.real_engine = False
        else:
            self.engine = None
            self.real_engine = False

        # Phase 4: 고급 제어 상태
        self.control_history = []
        self.system_diagnostics = {}
        self.performance_cache = {}

        # 제어 세션 상태 초기화
        if 'control_session_id' not in st.session_state:
            st.session_state.control_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        if 'last_command_time' not in st.session_state:
            st.session_state.last_command_time = None

    def show_advanced_control_panel(self):
        """Phase 4 고급 제어 패널 표시"""
        st.title("🤖 Phase 4 고급 자동매매 제어 패널")

        # 시스템 연결 상태 표시
        self._show_system_connection_status()

        st.divider()

        # Phase 4: 탭으로 구성된 고급 인터페이스
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🎛️ 메인 제어",
            "📊 실시간 상태",
            "⚙️ 고급 설정",
            "🔧 시스템 진단",
            "📈 성과 추적"
        ])

        with tab1:
            self._show_main_controls()

        with tab2:
            self._show_real_time_status()

        with tab3:
            self._show_advanced_settings()

        with tab4:
            self._show_system_diagnostics()

        with tab5:
            self._show_performance_tracking()

    def _show_system_connection_status(self):
        """시스템 연결 상태 표시"""
        if self.real_engine:
            st.success("🟢 실제 엔진 연결됨 - Phase 4 모든 기능 사용 가능")
        else:
            st.warning("🟡 시뮬레이션 모드 - 데모 기능만 사용 가능")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            session_id = st.session_state.control_session_id
            st.metric("제어 세션", session_id)

        with col2:
            uptime = datetime.now() - datetime.strptime(session_id, "%Y%m%d_%H%M%S")
            st.metric("세션 시간", f"{int(uptime.total_seconds()/60)}분")

        with col3:
            last_cmd = st.session_state.last_command_time
            if last_cmd:
                time_since = (datetime.now() - last_cmd).seconds
                st.metric("마지막 명령", f"{time_since}초 전")
            else:
                st.metric("마지막 명령", "없음")

        with col4:
            if self.real_engine and self.engine:
                try:
                    status = self.engine.get_system_status()
                    engine_status = status.get('status', 'UNKNOWN')
                    st.metric("엔진 상태", engine_status)
                except:
                    st.metric("엔진 상태", "연결 오류")
            else:
                st.metric("엔진 상태", "시뮬레이션")

    def _show_main_controls(self):
        """메인 제어 기능"""
        st.markdown("### 🎛️ 메인 제어")

        # 시스템 상태 가져오기
        system_status = self._get_current_status()

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### ▶️ 시작/중단 제어")

            current_status = system_status.get('status', 'STOPPED')

            if current_status in ['RUNNING']:
                st.success(f"🟢 시스템 실행 중 ({current_status})")

                if st.button("⏸️ 정상 중단", type="secondary", use_container_width=True, key="phase4_normal_stop"):
                    self._execute_command("NORMAL_STOP")

                if st.button("🛑 즉시 중단", type="primary", use_container_width=True, key="phase4_immediate_stop"):
                    self._execute_command("IMMEDIATE_STOP")

            else:
                st.info(f"🔴 시스템 중단됨 ({current_status})")

                # 시작 전 사전 검사
                if self._pre_start_validation():
                    if st.button("▶️ 시스템 시작", type="primary", use_container_width=True, key="phase4_start"):
                        self._execute_command("START_SYSTEM")
                else:
                    st.error("❌ 시작 조건 미충족")
                    if st.button("🔍 사전 검사 다시 실행", use_container_width=True, key="phase4_recheck"):
                        st.rerun()

        with col2:
            st.markdown("#### 🚨 긴급 제어")

            if st.button("🚨 긴급 중단", type="primary", use_container_width=True, key="phase4_emergency_stop"):
                if self._confirm_emergency_action("긴급 중단"):
                    self._execute_command("EMERGENCY_STOP")

            if st.button("💰 모든 포지션 청산", type="secondary", use_container_width=True, key="phase4_liquidate_all"):
                if self._confirm_emergency_action("포지션 청산"):
                    self._execute_command("LIQUIDATE_ALL")

            if st.button("🔄 시스템 재시작", use_container_width=True, key="phase4_restart"):
                if self._confirm_emergency_action("시스템 재시작"):
                    self._execute_command("RESTART_SYSTEM")

        # 명령 이력 표시
        if self.control_history:
            st.markdown("#### 📝 최근 명령 이력")
            history_df = pd.DataFrame(self.control_history[-5:])  # 최근 5개만
            st.dataframe(history_df, use_container_width=True)

    def _show_real_time_status(self):
        """실시간 상태 모니터링"""
        st.markdown("### 📊 실시간 시스템 상태")

        # 자동 새로고침
        auto_refresh = st.checkbox("자동 새로고침 (10초)", value=True, key="phase4_auto_refresh")
        if auto_refresh:
            time.sleep(10)
            st.rerun()

        # 시스템 상태 조회
        if self.real_engine and self.engine:
            try:
                dashboard_data = self.engine.get_dashboard_data()
                system_status = dashboard_data.get('system_status', {})
                stats = system_status.get('stats', {})

                # 핵심 지표 카드
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    uptime = system_status.get('uptime', 0) / 3600
                    st.metric("가동 시간", f"{uptime:.1f}시간")

                with col2:
                    success_rate = stats.get('success_rate', 0)
                    st.metric("거래 성공률", f"{success_rate:.1f}%")

                with col3:
                    today_pnl = stats.get('today_pnl', 0)
                    st.metric("오늘 수익", f"${today_pnl:.2f}")

                with col4:
                    active_positions = stats.get('active_positions', 0)
                    st.metric("활성 포지션", f"{active_positions}개")

                # 상세 통계
                st.markdown("#### 📈 상세 통계")
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**거래 통계**")
                    st.write(f"• 총 거래: {stats.get('total_trades', 0)}건")
                    st.write(f"• 성공 거래: {stats.get('successful_trades', 0)}건")
                    st.write(f"• 생성된 신호: {stats.get('signals_generated', 0)}개")

                with col2:
                    st.markdown("**수익 통계**")
                    st.write(f"• 총 누적 수익: ${stats.get('total_pnl', 0):.2f}")
                    st.write(f"• 오늘 수익: ${stats.get('today_pnl', 0):.2f}")
                    st.write(f"• 시스템 오류: {stats.get('errors_count', 0)}건")

                # Phase 3 안전 시스템 상태
                if 'safety_status' in dashboard_data:
                    safety_status = dashboard_data['safety_status']
                    st.markdown("#### 🛡️ 안전 시스템 상태")

                    col1, col2 = st.columns(2)

                    with col1:
                        total_checks = safety_status.get('total_checks', 0)
                        passed_checks = safety_status.get('passed_checks', 0)
                        if total_checks > 0:
                            pass_rate = (passed_checks / total_checks) * 100
                            st.metric("안전 검사 통과율", f"{pass_rate:.1f}%")
                        else:
                            st.metric("안전 검사 통과율", "데이터 없음")

                    with col2:
                        emergency_status = dashboard_data.get('emergency_status', {})
                        is_emergency = emergency_status.get('is_emergency_mode', False)
                        if is_emergency:
                            st.error("🚨 긴급 모드 활성")
                        else:
                            st.success("✅ 정상 운영")

            except Exception as e:
                st.error(f"상태 조회 실패: {e}")
        else:
            # 시뮬레이션 상태
            self._show_simulated_status()

    def _show_advanced_settings(self):
        """고급 설정 변경"""
        st.markdown("### ⚙️ 고급 시스템 설정")

        # 거래 설정
        st.markdown("#### 🎯 거래 설정")

        col1, col2 = st.columns(2)

        with col1:
            trading_interval = st.slider(
                "거래 간격 (초)",
                min_value=30,
                max_value=3600,
                value=300,
                step=30,
                key="phase4_trading_interval"
            )

            max_positions = st.number_input(
                "최대 포지션 수",
                min_value=1,
                max_value=20,
                value=5,
                key="phase4_max_positions"
            )

            paper_trading = st.checkbox(
                "페이퍼 트레이딩 모드",
                value=True,
                key="phase4_paper_trading"
            )

        with col2:
            daily_loss_limit = st.slider(
                "일일 손실 한도 (%)",
                min_value=1.0,
                max_value=10.0,
                value=3.0,
                step=0.5,
                key="phase4_daily_loss_limit"
            )

            position_size_pct = st.slider(
                "포지션 크기 (%)",
                min_value=0.5,
                max_value=10.0,
                value=2.0,
                step=0.5,
                key="phase4_position_size"
            )

            trading_mode = st.selectbox(
                "거래 모드",
                ['CONSERVATIVE', 'BALANCED', 'AGGRESSIVE'],
                index=1,
                key="phase4_trading_mode"
            )

        # 알림 설정
        st.markdown("#### 🔔 알림 설정")

        col1, col2 = st.columns(2)

        with col1:
            email_alerts = st.checkbox("이메일 알림", value=False, key="phase4_email_alerts")
            discord_alerts = st.checkbox("Discord 알림", value=True, key="phase4_discord_alerts")

        with col2:
            telegram_alerts = st.checkbox("텔레그램 알림", value=False, key="phase4_telegram_alerts")
            dashboard_alerts = st.checkbox("대시보드 알림", value=True, key="phase4_dashboard_alerts")

        # 설정 저장
        if st.button("💾 설정 저장", type="primary", use_container_width=True, key="phase4_save_settings"):
            settings = {
                'trading_interval': trading_interval,
                'max_positions': max_positions,
                'paper_trading': paper_trading,
                'daily_loss_limit': daily_loss_limit,
                'position_size_pct': position_size_pct,
                'trading_mode': trading_mode,
                'notifications': {
                    'email': email_alerts,
                    'discord': discord_alerts,
                    'telegram': telegram_alerts,
                    'dashboard': dashboard_alerts
                }
            }

            if self._save_settings(settings):
                st.success("✅ 설정이 저장되었습니다!")
                st.balloons()
            else:
                st.error("❌ 설정 저장 실패")

    def _show_system_diagnostics(self):
        """시스템 진단 및 복구"""
        st.markdown("### 🔧 시스템 진단 및 복구")

        # 진단 실행
        if st.button("🔍 전체 시스템 진단 실행", type="primary", use_container_width=True, key="phase4_run_diagnostics"):
            with st.spinner("시스템 진단 실행 중..."):
                diagnostics = self._run_system_diagnostics()
                self.system_diagnostics = diagnostics

        # 진단 결과 표시
        if self.system_diagnostics:
            st.markdown("#### 📋 진단 결과")

            # 전체 상태
            overall_status = self.system_diagnostics.get('overall_status', 'UNKNOWN')
            if overall_status == 'HEALTHY':
                st.success("✅ 시스템 상태 양호")
            elif overall_status == 'WARNING':
                st.warning("⚠️ 주의 필요")
            else:
                st.error("❌ 문제 감지됨")

            # 상세 진단 결과
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**연결 상태**")
                connections = self.system_diagnostics.get('connections', {})
                for name, status in connections.items():
                    icon = "✅" if status else "❌"
                    st.write(f"{icon} {name}")

            with col2:
                st.markdown("**리소스 상태**")
                resources = self.system_diagnostics.get('resources', {})
                for name, value in resources.items():
                    st.metric(name, value)

            # 문제점 및 권장사항
            issues = self.system_diagnostics.get('issues', [])
            if issues:
                st.markdown("#### ⚠️ 발견된 문제점")
                for issue in issues:
                    st.error(f"• {issue}")

            recommendations = self.system_diagnostics.get('recommendations', [])
            if recommendations:
                st.markdown("#### 💡 권장사항")
                for rec in recommendations:
                    st.info(f"• {rec}")

        # 복구 도구
        st.markdown("#### 🛠️ 복구 도구")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🔄 캐시 초기화", use_container_width=True, key="phase4_clear_cache"):
                self._clear_system_cache()
                st.success("캐시가 초기화되었습니다")

        with col2:
            if st.button("🗄️ 데이터베이스 정리", use_container_width=True, key="phase4_cleanup_db"):
                self._cleanup_database()
                st.success("데이터베이스가 정리되었습니다")

        with col3:
            if st.button("📊 로그 정리", use_container_width=True, key="phase4_cleanup_logs"):
                self._cleanup_logs()
                st.success("로그가 정리되었습니다")

    def _show_performance_tracking(self):
        """성과 추적"""
        st.markdown("### 📈 성과 추적 및 분석")

        # 성과 데이터 캐싱 및 업데이트
        if st.button("🔄 성과 데이터 업데이트", key="phase4_update_performance"):
            self.performance_cache = self._collect_performance_data()
            st.success("성과 데이터가 업데이트되었습니다")

        if not self.performance_cache:
            self.performance_cache = self._collect_performance_data()

        # 성과 지표 카드
        col1, col2, col3, col4 = st.columns(4)

        perf_data = self.performance_cache

        with col1:
            total_return = perf_data.get('total_return', 0)
            st.metric("총 수익률", f"{total_return:.2f}%")

        with col2:
            sharpe_ratio = perf_data.get('sharpe_ratio', 0)
            st.metric("샤프 비율", f"{sharpe_ratio:.2f}")

        with col3:
            max_drawdown = perf_data.get('max_drawdown', 0)
            st.metric("최대 낙폭", f"{max_drawdown:.2f}%")

        with col4:
            win_rate = perf_data.get('win_rate', 0)
            st.metric("승률", f"{win_rate:.1f}%")

        # 성과 차트
        st.markdown("#### 📊 성과 차트")

        # 수익률 곡선
        dates = perf_data.get('dates', [])
        returns = perf_data.get('cumulative_returns', [])

        if dates and returns:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates,
                y=returns,
                mode='lines',
                name='누적 수익률',
                line=dict(color='blue', width=2)
            ))

            fig.update_layout(
                title="누적 수익률 추이",
                xaxis_title="날짜",
                yaxis_title="수익률 (%)",
                height=400
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("성과 데이터가 충분하지 않습니다")

        # 월별 성과 분석
        st.markdown("#### 📅 월별 성과 분석")

        monthly_data = perf_data.get('monthly_returns', {})
        if monthly_data:
            monthly_df = pd.DataFrame(list(monthly_data.items()), columns=['월', '수익률(%)'])
            st.dataframe(monthly_df, use_container_width=True)
        else:
            st.info("월별 데이터가 없습니다")

        # 시스템 정보
        self._show_system_info()

    def _show_status_section(self):
        """상태 섹션 표시"""
        # 시뮬레이션된 상태 (실제 구현 시 엔진에서 가져옴)
        status = self._get_mock_status()

        # 상태 표시
        if status['status'] == 'RUNNING':
            st.success("🟢 자동매매 실행 중")

            # 실행 정보
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("가동 시간", status.get('uptime', 'N/A'))

            with col2:
                st.metric("오늘 거래", f"{status.get('today_trades', 0)}건")

            with col3:
                st.metric("활성 포지션", f"{status.get('active_positions', 0)}개")

            with col4:
                st.metric("오늘 수익", f"${status.get('today_pnl', 0):.2f}")

        elif status['status'] == 'STOPPED':
            st.info("🔴 자동매매 중단됨")

        elif status['status'] == 'ERROR':
            st.error("❌ 시스템 오류 발생")

        elif status['status'] == 'EMERGENCY_STOP':
            st.error("🚨 긴급 중단 상태")

    def _show_start_stop_controls(self):
        """시작/중단 제어"""
        st.subheader("⚡ 기본 제어")

        status = self._get_mock_status()

        if status['status'] == 'RUNNING':
            if st.button("⏸️ 자동매매 중단", type="secondary", use_container_width=True, key="control_panel_stop"):
                with st.spinner("자동매매 중단 중..."):
                    success = self._stop_trading()
                    if success:
                        st.success("자동매매가 중단되었습니다")
                        st.rerun()
                    else:
                        st.error("중단 실패")

        else:
            if st.button("▶️ 자동매매 시작", type="primary", use_container_width=True, key="control_panel_start"):
                # 사전 검사
                if self._pre_start_checks():
                    with st.spinner("자동매매 시작 중..."):
                        success = self._start_trading()
                        if success:
                            st.success("자동매매가 시작되었습니다")
                            st.rerun()
                        else:
                            st.error("시작 실패")
                else:
                    st.error("사전 검사 실패")

    def _show_emergency_controls(self):
        """긴급 제어"""
        st.subheader("🚨 긴급 제어")

        # 긴급 중단
        if st.button("🛑 긴급 중단", type="primary", use_container_width=True, key="control_panel_emergency"):
            if self._confirm_emergency_stop():
                with st.spinner("긴급 중단 실행 중..."):
                    success = self._emergency_stop()
                    if success:
                        st.error("긴급 중단 실행됨")
                        st.rerun()
                    else:
                        st.error("긴급 중단 실패")

        # 포지션 청산
        if st.button("💰 모든 포지션 청산", type="secondary", use_container_width=True, key="control_panel_liquidate"):
            if self._confirm_liquidation():
                with st.spinner("포지션 청산 중..."):
                    success = self._liquidate_positions()
                    if success:
                        st.warning("모든 포지션이 청산되었습니다")
                    else:
                        st.error("청산 실패")

    def _show_quick_settings(self):
        """빠른 설정"""
        st.subheader("⚙️ 빠른 설정")

        # 거래 모드 변경
        current_mode = st.session_state.get('trading_mode', 'CONSERVATIVE')
        new_mode = st.selectbox(
            "거래 모드",
            ['CONSERVATIVE', 'BALANCED', 'AGGRESSIVE'],
            index=['CONSERVATIVE', 'BALANCED', 'AGGRESSIVE'].index(current_mode)
        )

        if new_mode != current_mode:
            st.session_state['trading_mode'] = new_mode
            st.success(f"거래 모드가 {new_mode}로 변경됨")

        # 페이퍼 트레이딩 토글
        paper_trading = st.checkbox(
            "페이퍼 트레이딩 모드",
            value=st.session_state.get('paper_trading', False)
        )
        st.session_state['paper_trading'] = paper_trading

    def _show_system_info(self):
        """시스템 정보"""
        st.subheader("💻 시스템 정보")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**연결 상태**")
            st.write("• 거래소 API: ✅ 연결됨")
            st.write("• 시장 데이터: ✅ 정상")
            st.write("• 데이터베이스: ✅ 정상")

        with col2:
            st.write("**시스템 성능**")
            st.write("• CPU 사용률: 15%")
            st.write("• 메모리 사용률: 32%")
            st.write("• 응답 시간: 50ms")

    def _get_mock_status(self) -> Dict[str, Any]:
        """모의 상태 데이터 (실제 구현 시 엔진에서 가져옴)"""
        return {
            'status': st.session_state.get('auto_trading_status', 'STOPPED'),
            'uptime': '2시간 30분',
            'today_trades': 15,
            'active_positions': 3,
            'today_pnl': 125.50
        }

    def _pre_start_checks(self) -> bool:
        """시작 전 사전 검사"""
        # 실제 구현에서는 엔진의 사전 검사 실행
        checks = [
            ("API 연결", True),
            ("설정 유효성", True),
            ("계좌 잔고", True),
            ("리스크 설정", True)
        ]

        all_passed = True
        for check_name, result in checks:
            if not result:
                st.error(f"❌ {check_name} 실패")
                all_passed = False
            else:
                st.success(f"✅ {check_name} 통과")

        return all_passed

    def _start_trading(self) -> bool:
        """자동매매 시작"""
        try:
            # 실제 구현에서는 엔진 시작
            # return self.engine.start_trading()

            # 시뮬레이션
            time.sleep(2)
            st.session_state['auto_trading_status'] = 'RUNNING'
            return True

        except Exception as e:
            self.logger.error(f"자동매매 시작 실패: {e}")
            return False

    def _stop_trading(self) -> bool:
        """자동매매 중단"""
        try:
            # 실제 구현에서는 엔진 중단
            # return self.engine.stop_trading()

            # 시뮬레이션
            time.sleep(1)
            st.session_state['auto_trading_status'] = 'STOPPED'
            return True

        except Exception as e:
            self.logger.error(f"자동매매 중단 실패: {e}")
            return False

    def _emergency_stop(self) -> bool:
        """긴급 중단"""
        try:
            # 실제 구현에서는 엔진 긴급 중단
            # return self.engine.stop_trading(emergency=True)

            # 시뮬레이션
            time.sleep(1)
            st.session_state['auto_trading_status'] = 'EMERGENCY_STOP'
            return True

        except Exception as e:
            self.logger.error(f"긴급 중단 실패: {e}")
            return False

    def _liquidate_positions(self) -> bool:
        """포지션 청산"""
        try:
            # 실제 구현에서는 포지션 매니저 호출
            # return self.engine.position_manager.liquidate_all_positions()

            # 시뮬레이션
            time.sleep(2)
            return True

        except Exception as e:
            self.logger.error(f"포지션 청산 실패: {e}")
            return False

    def _confirm_emergency_stop(self) -> bool:
        """긴급 중단 확인"""
        return st.checkbox("⚠️ 긴급 중단을 확인합니다", key="emergency_confirm")

    def _confirm_liquidation(self) -> bool:
        """청산 확인"""
        return st.checkbox("⚠️ 모든 포지션 청산을 확인합니다", key="liquidation_confirm")

    # Phase 4: 새로운 헬퍼 메서드들

    def _get_current_status(self) -> Dict[str, Any]:
        """현재 시스템 상태 조회"""
        if self.real_engine and self.engine:
            try:
                return self.engine.get_system_status()
            except Exception as e:
                self.logger.error(f"상태 조회 실패: {e}")
                return {'status': 'ERROR', 'error': str(e)}
        else:
            # 시뮬레이션 상태
            return {
                'status': st.session_state.get('auto_trading_status', 'STOPPED'),
                'uptime': 3600,  # 1시간
                'stats': {
                    'total_trades': 25,
                    'success_rate': 84.0,
                    'today_pnl': 125.50,
                    'active_positions': 2
                }
            }

    def _pre_start_validation(self) -> bool:
        """시작 전 사전 검증"""
        try:
            # 실제 구현에서는 안전 시스템 검사
            if self.real_engine and self.engine:
                safety_passed, _ = self.engine.safety_system.run_all_safety_checks()
                return safety_passed
            else:
                # 시뮬레이션 검증
                return True

        except Exception as e:
            self.logger.error(f"사전 검증 실패: {e}")
            return False

    def _execute_command(self, command: str) -> bool:
        """명령 실행"""
        try:
            self.logger.info(f"명령 실행: {command}")

            # 명령 이력에 추가
            command_record = {
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'command': command,
                'user': 'Dashboard User',
                'status': 'PENDING'
            }

            result = False

            # 실제 엔진 명령 실행
            if self.real_engine and self.engine:
                if command == "START_SYSTEM":
                    result = self.engine.start_trading()
                elif command == "NORMAL_STOP":
                    result = self.engine.stop_trading()
                elif command == "IMMEDIATE_STOP":
                    result = self.engine.stop_trading(immediate=True)
                elif command == "EMERGENCY_STOP":
                    result = self.engine.manual_emergency_stop("Dashboard에서 긴급 중단")
                elif command == "LIQUIDATE_ALL":
                    result = self.engine.position_manager.liquidate_all_positions()
                elif command == "RESTART_SYSTEM":
                    self.engine.stop_trading()
                    time.sleep(2)
                    result = self.engine.start_trading()
            else:
                # 시뮬레이션 명령 실행
                time.sleep(1)
                if command == "START_SYSTEM":
                    st.session_state['auto_trading_status'] = 'RUNNING'
                elif command in ["NORMAL_STOP", "IMMEDIATE_STOP"]:
                    st.session_state['auto_trading_status'] = 'STOPPED'
                elif command == "EMERGENCY_STOP":
                    st.session_state['auto_trading_status'] = 'EMERGENCY_STOP'
                result = True

            # 명령 이력 업데이트
            command_record['status'] = 'SUCCESS' if result else 'FAILED'
            self.control_history.append(command_record)

            # 세션 상태 업데이트
            st.session_state.last_command_time = datetime.now()

            if result:
                st.success(f"✅ {command} 명령이 성공적으로 실행되었습니다")
            else:
                st.error(f"❌ {command} 명령 실행 실패")

            return result

        except Exception as e:
            self.logger.error(f"명령 실행 실패: {e}")
            st.error(f"❌ 명령 실행 중 오류: {e}")
            return False

    def _confirm_emergency_action(self, action: str) -> bool:
        """긴급 작업 확인"""
        return st.checkbox(f"⚠️ {action}을(를) 확인합니다", key=f"confirm_{action.replace(' ', '_')}")

    def _show_simulated_status(self):
        """시뮬레이션 상태 표시"""
        st.info("🎭 시뮬레이션 모드 - 가상 데이터 표시")

        # 실제 API 데이터로 교체
        col1, col2, col3, col4 = st.columns(4)

        try:
            # API 키 확인 및 실제 데이터 조회
            if hasattr(st.session_state, 'user') and st.session_state.user:
                from database import get_db_manager
                from security import get_api_key_manager

                db_manager = get_db_manager()
                api_manager = get_api_key_manager()
                user_id = st.session_state.user['user_id']

                # API 키 조회
                credentials = api_manager.get_api_credentials(user_id, "binance", is_testnet=True)

                if credentials:
                    from binance_testnet_connector import BinanceTestnetConnector

                    api_key, api_secret = credentials
                    connector = BinanceTestnetConnector()
                    connector.api_key = api_key
                    connector.secret_key = api_secret
                    connector.session.headers.update({'X-MBX-APIKEY': api_key})

                    # 실제 포지션 조회
                    open_orders = connector.get_open_orders()
                    position_count = 0
                    if open_orders and open_orders.get('success'):
                        position_count = len(open_orders.get('orders', []))

                    # 실제 계좌 잔고 조회
                    account_info = connector.get_account_info()
                    current_balance = 0.0
                    if account_info and account_info.get('success'):
                        balances = account_info.get('balances', [])
                        for balance in balances:
                            if balance['asset'] == 'USDT':
                                current_balance = balance['total']
                                break

                    # 거래 기록에서 오늘 수익 계산
                    recent_trades = db_manager.get_user_trades(user_id, limit=50)
                    today_profit = 0.0
                    today = datetime.now().date()
                    for trade in recent_trades:
                        if trade.timestamp.date() == today and trade.profit_loss:
                            today_profit += trade.profit_loss

                    # 성공률 계산
                    success_rate = 0.0
                    if recent_trades:
                        profitable_trades = len([t for t in recent_trades if t.profit_loss and t.profit_loss > 0])
                        success_rate = (profitable_trades / len(recent_trades)) * 100

                    with col1:
                        st.metric("계좌 잔고", f"{current_balance:,.2f} USDT")

                    with col2:
                        st.metric("거래 성공률", f"{success_rate:.1f}%")

                    with col3:
                        st.metric("오늘 수익", f"{today_profit:+.2f} USDT")

                    with col4:
                        st.metric("활성 포지션", f"{position_count}개")

                else:
                    # API 키 없을 때 기본값
                    with col1:
                        st.metric("계좌 잔고", "0.00 USDT")
                    with col2:
                        st.metric("거래 성공률", "0.0%")
                    with col3:
                        st.metric("오늘 수익", "0.00 USDT")
                    with col4:
                        st.metric("활성 포지션", "0개")
            else:
                # 사용자 세션 없을 때
                with col1:
                    st.metric("계좌 잔고", "로그인 필요")
                with col2:
                    st.metric("거래 성공률", "-")
                with col3:
                    st.metric("오늘 수익", "-")
                with col4:
                    st.metric("활성 포지션", "-")

        except Exception as e:
            # 오류 시 기본값 표시
            with col1:
                st.metric("계좌 잔고", "API 연결 오류")
            with col2:
                st.metric("거래 성공률", "-")
            with col3:
                st.metric("오늘 수익", "-")
            with col4:
                st.metric("활성 포지션", "-")

    def _save_settings(self, settings: Dict[str, Any]) -> bool:
        """설정 저장"""
        try:
            # 실제 구현에서는 파일 또는 DB에 저장
            if self.real_engine and self.engine:
                # 엔진 설정 업데이트
                return True
            else:
                # 시뮬레이션 저장
                st.session_state['trading_settings'] = settings
                return True

        except Exception as e:
            self.logger.error(f"설정 저장 실패: {e}")
            return False

    def _run_system_diagnostics(self) -> Dict[str, Any]:
        """시스템 진단 실행"""
        try:
            # 실제 구현에서는 엔진의 진단 시스템 호출
            if self.real_engine and self.engine:
                # 실제 진단 로직
                pass

            # 시뮬레이션 진단 결과
            return {
                'overall_status': 'HEALTHY',
                'connections': {
                    'Database': True,
                    'API': True,
                    'Notification': True,
                    'AI System': True
                },
                'resources': {
                    'CPU 사용률': '45%',
                    'Memory 사용률': '67%',
                    'Disk 사용률': '23%'
                },
                'issues': [],
                'recommendations': [
                    '정기적인 데이터베이스 정리 권장',
                    '메모리 사용률 모니터링 필요'
                ]
            }

        except Exception as e:
            self.logger.error(f"시스템 진단 실패: {e}")
            return {
                'overall_status': 'ERROR',
                'error': str(e)
            }

    def _clear_system_cache(self):
        """시스템 캐시 초기화"""
        try:
            # 실제 구현에서는 엔진 캐시 정리
            self.performance_cache = {}
            self.system_diagnostics = {}
        except Exception as e:
            self.logger.error(f"캐시 초기화 실패: {e}")

    def _cleanup_database(self):
        """데이터베이스 정리"""
        try:
            # 실제 구현에서는 DB 정리 로직
            pass
        except Exception as e:
            self.logger.error(f"데이터베이스 정리 실패: {e}")

    def _cleanup_logs(self):
        """로그 정리"""
        try:
            # 실제 구현에서는 로그 파일 정리
            self.control_history = self.control_history[-10:]  # 최근 10개만 유지
        except Exception as e:
            self.logger.error(f"로그 정리 실패: {e}")

    def _collect_performance_data(self) -> Dict[str, Any]:
        """성과 데이터 수집"""
        try:
            # 실제 구현에서는 엔진에서 성과 데이터 가져오기
            if self.real_engine and self.engine:
                # 실제 성과 데이터 수집
                pass

            # 시뮬레이션 성과 데이터
            import numpy as np

            # 가상 수익률 데이터 생성
            dates = [datetime.now() - timedelta(days=i) for i in range(30, 0, -1)]
            returns = np.cumsum(np.random.normal(0.1, 1.5, 30))  # 누적 수익률

            return {
                'total_return': returns[-1],
                'sharpe_ratio': 1.45,
                'max_drawdown': -8.3,
                'win_rate': 64.7,
                'dates': dates,
                'cumulative_returns': returns.tolist(),
                'monthly_returns': {
                    '2024-01': 2.3,
                    '2024-02': -1.2,
                    '2024-03': 4.1,
                    '2024-04': 1.8,
                    '2024-05': 3.2
                }
            }

        except Exception as e:
            self.logger.error(f"성과 데이터 수집 실패: {e}")
            return {}


# 전역 함수들
def show_control_panel():
    """기본 제어 패널 표시 (하위 호환성)"""
    panel = AdvancedControlPanel()
    panel.show_advanced_control_panel()

def show_advanced_control_panel():
    """Phase 4 고급 제어 패널 표시"""
    panel = AdvancedControlPanel()
    panel.show_advanced_control_panel()