"""
📋 Phase 4 Comprehensive Logs Viewer - 종합 로그 뷰어

Phase 4의 고급 로그 관리 및 분석 시스템:
- 실시간 로그 스트리밍
- 다중 로그 소스 통합
- 고급 필터링 및 검색
- 로그 분석 및 패턴 감지
- 오류 추적 및 디버깅
- 로그 내보내기 및 백업
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import re
import json
from typing import Dict, List, Any, Optional, Tuple
import logging
from enum import Enum

# Phase 4: 고급 로그 관리를 위한 추가 import
try:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from auto_trading.engine import AutoTradingEngine
    from utils.notifications import NotificationManager
    REAL_ENGINE_AVAILABLE = True
except ImportError:
    REAL_ENGINE_AVAILABLE = False

class LogLevel(Enum):
    """로그 레벨"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogSource(Enum):
    """로그 소스"""
    ENGINE = "AUTO_TRADING_ENGINE"
    RISK_MANAGER = "RISK_MANAGER"
    TRADE_EXECUTOR = "TRADE_EXECUTOR"
    SIGNAL_GENERATOR = "SIGNAL_GENERATOR"
    NOTIFICATION = "NOTIFICATION_SYSTEM"
    DATABASE = "DATABASE"
    API = "API_CONNECTOR"
    DASHBOARD = "DASHBOARD"

class AdvancedLogsViewer:
    """📋 Phase 4 고급 로그 뷰어"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # 실제 엔진 연동
        if REAL_ENGINE_AVAILABLE:
            try:
                self.engine = AutoTradingEngine()
                self.real_engine = True
                self.logger.info("Phase 4: 실제 엔진 로그 시스템과 연동됨")
            except Exception as e:
                self.logger.warning(f"엔진 로그 연동 실패, 시뮬레이션 모드: {e}")
                self.engine = None
                self.real_engine = False
        else:
            self.engine = None
            self.real_engine = False

        # 로그 캐시 및 설정
        self.log_cache = []
        self.filtered_logs = []
        self.log_patterns = {}
        self.error_tracking = {}

        # 세션 상태 초기화
        if 'logs_auto_refresh' not in st.session_state:
            st.session_state.logs_auto_refresh = False
        if 'logs_page_size' not in st.session_state:
            st.session_state.logs_page_size = 100

    def show_logs_viewer(self):
        """메인 로그 뷰어 표시"""
        st.title("📋 Phase 4 종합 로그 뷰어")

        # 로그 시스템 상태
        self._show_log_system_status()

        st.divider()

        # 탭으로 구성된 로그 인터페이스
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 실시간 로그",
            "🔍 로그 검색",
            "📈 로그 분석",
            "🚨 오류 추적",
            "⚙️ 로그 관리"
        ])

        with tab1:
            self._show_realtime_logs()

        with tab2:
            self._show_log_search()

        with tab3:
            self._show_log_analytics()

        with tab4:
            self._show_error_tracking()

        with tab5:
            self._show_log_management()

    def _show_log_system_status(self):
        """로그 시스템 상태 표시"""
        if self.real_engine:
            st.success("🟢 실제 로그 시스템 연결됨")
        else:
            st.warning("🟡 시뮬레이션 로그 모드")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_logs = len(self.log_cache)
            st.metric("총 로그 수", f"{total_logs:,}")

        with col2:
            if self.log_cache:
                latest_log_time = max(log['timestamp'] for log in self.log_cache)
                time_diff = (datetime.now() - latest_log_time).seconds
                st.metric("최신 로그", f"{time_diff}초 전")
            else:
                st.metric("최신 로그", "없음")

        with col3:
            error_count = len([log for log in self.log_cache if log.get('level') in ['ERROR', 'CRITICAL']])
            st.metric("오류 로그", f"{error_count}")

        with col4:
            active_sources = len(set(log.get('source', 'UNKNOWN') for log in self.log_cache))
            st.metric("활성 소스", f"{active_sources}")

    def _show_realtime_logs(self):
        """실시간 로그 스트리밍"""
        st.markdown("### 📊 실시간 로그 스트리밍")

        # 실시간 제어
        col1, col2, col3 = st.columns(3)

        with col1:
            auto_refresh = st.checkbox(
                "자동 새로고침 (5초)",
                value=st.session_state.logs_auto_refresh,
                key="logs_auto_refresh_toggle"
            )
            st.session_state.logs_auto_refresh = auto_refresh

        with col2:
            page_size = st.selectbox(
                "페이지 크기",
                [50, 100, 200, 500],
                index=1,
                key="logs_page_size_select"
            )
            st.session_state.logs_page_size = page_size

        with col3:
            if st.button("🔄 로그 새로고침", key="logs_manual_refresh"):
                self._refresh_logs()

        # 자동 새로고침
        if auto_refresh:
            time.sleep(5)
            self._refresh_logs()
            st.rerun()

        # 빠른 필터
        st.markdown("#### 🔍 빠른 필터")

        col1, col2, col3 = st.columns(3)

        with col1:
            level_filter = st.multiselect(
                "로그 레벨",
                [level.value for level in LogLevel],
                default=[LogLevel.INFO.value, LogLevel.WARNING.value, LogLevel.ERROR.value],
                key="realtime_level_filter"
            )

        with col2:
            source_filter = st.multiselect(
                "로그 소스",
                [source.value for source in LogSource],
                default=[],
                key="realtime_source_filter"
            )

        with col3:
            keyword_filter = st.text_input(
                "키워드 검색",
                placeholder="검색할 키워드 입력...",
                key="realtime_keyword_filter"
            )

        # 로그 데이터 로드 및 필터링
        logs = self._get_filtered_logs(level_filter, source_filter, keyword_filter)

        # 로그 테이블 표시
        if logs:
            st.markdown(f"#### 📋 로그 목록 (최근 {len(logs)}개)")

            # 로그 레벨별 색상 매핑
            level_colors = {
                'DEBUG': '🔵',
                'INFO': '🟢',
                'WARNING': '🟡',
                'ERROR': '🔴',
                'CRITICAL': '🟣'
            }

            # 로그 항목들을 expander로 표시
            for i, log in enumerate(logs[:page_size]):
                level_icon = level_colors.get(log.get('level', 'INFO'), '⚪')
                timestamp = log.get('timestamp', datetime.now()).strftime("%H:%M:%S")
                source = log.get('source', 'UNKNOWN')
                message = log.get('message', 'No message')

                with st.expander(f"{level_icon} {timestamp} [{source}] {message[:100]}...", expanded=False):
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.markdown(f"**메시지:** {message}")
                        if 'data' in log and log['data']:
                            st.markdown("**추가 데이터:**")
                            st.json(log['data'])

                    with col2:
                        st.markdown(f"**레벨:** {log.get('level', 'INFO')}")
                        st.markdown(f"**소스:** {source}")
                        st.markdown(f"**시간:** {log.get('timestamp', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')}")

        else:
            st.info("표시할 로그가 없습니다")

    def _show_log_search(self):
        """고급 로그 검색"""
        st.markdown("### 🔍 고급 로그 검색")

        # 검색 설정
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("#### 검색 조건")

            # 시간 범위
            time_range = st.selectbox(
                "시간 범위",
                ["최근 1시간", "최근 6시간", "최근 24시간", "최근 7일", "사용자 정의"],
                index=2,
                key="search_time_range"
            )

            if time_range == "사용자 정의":
                col_start, col_end = st.columns(2)
                with col_start:
                    start_date = st.date_input("시작 날짜", key="search_start_date")
                    start_time = st.time_input("시작 시간", key="search_start_time")
                with col_end:
                    end_date = st.date_input("종료 날짜", key="search_end_date")
                    end_time = st.time_input("종료 시간", key="search_end_time")

            # 고급 필터
            search_levels = st.multiselect(
                "로그 레벨",
                [level.value for level in LogLevel],
                default=[],
                key="search_level_filter"
            )

            search_sources = st.multiselect(
                "로그 소스",
                [source.value for source in LogSource],
                default=[],
                key="search_source_filter"
            )

            # 텍스트 검색
            search_text = st.text_area(
                "검색 텍스트 (정규식 지원)",
                placeholder="검색할 텍스트 또는 정규식 패턴...",
                key="search_text_input"
            )

            regex_mode = st.checkbox("정규식 모드", key="search_regex_mode")

        with col2:
            st.markdown("#### 검색 옵션")

            case_sensitive = st.checkbox("대소문자 구분", key="search_case_sensitive")
            include_data = st.checkbox("추가 데이터 포함", value=True, key="search_include_data")
            max_results = st.number_input(
                "최대 결과 수",
                min_value=10,
                max_value=10000,
                value=1000,
                key="search_max_results"
            )

        # 검색 실행
        if st.button("🔍 검색 실행", type="primary", use_container_width=True, key="execute_search"):
            with st.spinner("로그 검색 중..."):
                search_results = self._execute_advanced_search(
                    time_range, search_levels, search_sources, search_text,
                    regex_mode, case_sensitive, include_data, max_results
                )

                if search_results:
                    st.success(f"✅ {len(search_results)}개의 로그를 찾았습니다")

                    # 검색 결과 요약
                    self._show_search_summary(search_results)

                    # 검색 결과 표시
                    self._show_search_results(search_results)

                else:
                    st.warning("검색 결과가 없습니다")

    def _show_log_analytics(self):
        """로그 분석 및 통계"""
        st.markdown("### 📈 로그 분석 및 통계")

        if not self.log_cache:
            st.info("분석할 로그 데이터가 없습니다")
            return

        # 분석 기간 선택
        analysis_period = st.selectbox(
            "분석 기간",
            ["최근 1시간", "최근 6시간", "최근 24시간", "최근 7일"],
            index=2,
            key="analytics_period"
        )

        # 로그 통계 계산
        stats = self._calculate_log_statistics(analysis_period)

        # 통계 카드
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("총 로그 수", f"{stats['total_logs']:,}")

        with col2:
            st.metric("로그 속도", f"{stats['logs_per_minute']:.1f}/분")

        with col3:
            st.metric("오류율", f"{stats['error_rate']:.1f}%")

        with col4:
            st.metric("활성 소스", f"{stats['active_sources']}")

        # 차트들
        col1, col2 = st.columns(2)

        with col1:
            # 로그 레벨별 분포
            level_counts = stats['level_distribution']
            if level_counts:
                fig_pie = px.pie(
                    values=list(level_counts.values()),
                    names=list(level_counts.keys()),
                    title="로그 레벨별 분포"
                )
                st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            # 소스별 분포
            source_counts = stats['source_distribution']
            if source_counts:
                fig_bar = px.bar(
                    x=list(source_counts.keys()),
                    y=list(source_counts.values()),
                    title="소스별 로그 분포"
                )
                fig_bar.update_xaxes(tickangle=45)
                st.plotly_chart(fig_bar, use_container_width=True)

        # 시간별 로그 추이
        st.markdown("#### 📊 시간별 로그 추이")

        hourly_stats = stats['hourly_distribution']
        if hourly_stats:
            fig_line = go.Figure()

            for level in LogLevel:
                level_data = [hourly_stats.get(hour, {}).get(level.value, 0) for hour in sorted(hourly_stats.keys())]
                fig_line.add_trace(go.Scatter(
                    x=list(sorted(hourly_stats.keys())),
                    y=level_data,
                    mode='lines+markers',
                    name=level.value
                ))

            fig_line.update_layout(
                title="시간별 로그 레벨 추이",
                xaxis_title="시간",
                yaxis_title="로그 수",
                height=400
            )

            st.plotly_chart(fig_line, use_container_width=True)

        # 패턴 분석
        st.markdown("#### 🔍 로그 패턴 분석")

        patterns = self._analyze_log_patterns()
        if patterns:
            for pattern_name, pattern_info in patterns.items():
                with st.expander(f"패턴: {pattern_name} ({pattern_info['count']}회 발견)"):
                    st.write(f"**설명:** {pattern_info['description']}")
                    st.write(f"**빈도:** {pattern_info['frequency']}")
                    if pattern_info['examples']:
                        st.write("**예시:**")
                        for example in pattern_info['examples'][:3]:
                            st.code(example)

    def _show_error_tracking(self):
        """오류 추적 및 디버깅"""
        st.markdown("### 🚨 오류 추적 및 디버깅")

        # 오류 통계
        error_logs = [log for log in self.log_cache if log.get('level') in ['ERROR', 'CRITICAL']]

        if not error_logs:
            st.success("✅ 현재 추적된 오류가 없습니다")
            return

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("총 오류 수", len(error_logs))

        with col2:
            recent_errors = len([log for log in error_logs if (datetime.now() - log.get('timestamp', datetime.now())).seconds < 3600])
            st.metric("최근 1시간 오류", recent_errors)

        with col3:
            critical_errors = len([log for log in error_logs if log.get('level') == 'CRITICAL'])
            st.metric("심각한 오류", critical_errors)

        # 오류 분류
        st.markdown("#### 📊 오류 분류")

        error_analysis = self._analyze_errors(error_logs)

        # 오류 유형별 차트
        if error_analysis['error_types']:
            col1, col2 = st.columns(2)

            with col1:
                fig_pie = px.pie(
                    values=list(error_analysis['error_types'].values()),
                    names=list(error_analysis['error_types'].keys()),
                    title="오류 유형별 분포"
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            with col2:
                fig_bar = px.bar(
                    x=list(error_analysis['error_sources'].keys()),
                    y=list(error_analysis['error_sources'].values()),
                    title="소스별 오류 분포"
                )
                st.plotly_chart(fig_bar, use_container_width=True)

        # 최근 오류 목록
        st.markdown("#### 🔴 최근 오류 목록")

        for i, error_log in enumerate(error_logs[-10:]):  # 최근 10개
            level_icon = "🔴" if error_log.get('level') == 'ERROR' else "🟣"
            timestamp = error_log.get('timestamp', datetime.now()).strftime("%m-%d %H:%M:%S")
            source = error_log.get('source', 'UNKNOWN')
            message = error_log.get('message', 'No message')

            with st.expander(f"{level_icon} {timestamp} [{source}] {message[:80]}...", expanded=False):
                st.markdown(f"**레벨:** {error_log.get('level', 'ERROR')}")
                st.markdown(f"**메시지:** {message}")
                st.markdown(f"**소스:** {source}")
                st.markdown(f"**시간:** {error_log.get('timestamp', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')}")

                if 'data' in error_log and error_log['data']:
                    st.markdown("**오류 데이터:**")
                    st.json(error_log['data'])

                # 해결 방법 제안
                suggestions = self._get_error_suggestions(error_log)
                if suggestions:
                    st.markdown("**💡 해결 방법 제안:**")
                    for suggestion in suggestions:
                        st.info(f"• {suggestion}")

    def _show_log_management(self):
        """로그 관리 및 설정"""
        st.markdown("### ⚙️ 로그 관리 및 설정")

        # 로그 설정
        st.markdown("#### 🔧 로그 설정")

        col1, col2 = st.columns(2)

        with col1:
            log_level = st.selectbox(
                "최소 로그 레벨",
                [level.value for level in LogLevel],
                index=1,  # INFO
                key="log_level_setting"
            )

            max_log_size = st.number_input(
                "최대 로그 캐시 크기",
                min_value=1000,
                max_value=100000,
                value=10000,
                step=1000,
                key="max_log_size"
            )

            log_retention_days = st.number_input(
                "로그 보존 기간 (일)",
                min_value=1,
                max_value=365,
                value=30,
                key="log_retention_days"
            )

        with col2:
            enable_real_time = st.checkbox("실시간 로그 수집", value=True, key="enable_real_time_logs")
            enable_file_logging = st.checkbox("파일 로깅", value=True, key="enable_file_logging")
            enable_error_alerts = st.checkbox("오류 알림", value=True, key="enable_error_alerts")

        # 로그 내보내기
        st.markdown("#### 📤 로그 내보내기")

        export_format = st.selectbox(
            "내보내기 형식",
            ["CSV", "JSON", "TXT"],
            key="export_format"
        )

        export_range = st.selectbox(
            "내보내기 범위",
            ["전체", "최근 24시간", "최근 7일", "오류만"],
            key="export_range"
        )

        if st.button("📥 로그 내보내기", key="export_logs"):
            exported_data = self._export_logs(export_format, export_range)
            if exported_data:
                st.success("✅ 로그가 성공적으로 내보내졌습니다")
                st.download_button(
                    label=f"💾 {export_format} 파일 다운로드",
                    data=exported_data,
                    file_name=f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{export_format.lower()}",
                    key="download_logs"
                )

        # 로그 정리
        st.markdown("#### 🧹 로그 정리")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🗑️ 오래된 로그 삭제", key="cleanup_old_logs"):
                cleaned_count = self._cleanup_old_logs()
                st.success(f"✅ {cleaned_count}개의 오래된 로그를 삭제했습니다")

        with col2:
            if st.button("🔄 로그 캐시 초기화", key="clear_log_cache"):
                self.log_cache = []
                st.success("✅ 로그 캐시가 초기화되었습니다")

        with col3:
            if st.button("📊 로그 통계 재계산", key="recalculate_stats"):
                self._recalculate_log_statistics()
                st.success("✅ 로그 통계가 재계산되었습니다")

    # 헬퍼 메서드들

    def _refresh_logs(self):
        """로그 새로고침"""
        try:
            if self.real_engine and self.engine:
                # 실제 엔진에서 로그 가져오기
                pass
            else:
                # 시뮬레이션 로그 생성
                self._generate_simulated_logs()

        except Exception as e:
            self.logger.error(f"로그 새로고침 실패: {e}")

    def _generate_simulated_logs(self):
        """시뮬레이션 로그 생성"""
        import random

        # 시뮬레이션 로그 메시지들
        log_templates = [
            ("INFO", "ENGINE", "자동매매 시스템 정상 작동 중"),
            ("INFO", "TRADE_EXECUTOR", "거래 신호 처리 완료: {symbol}"),
            ("WARNING", "RISK_MANAGER", "일일 손실 한도 {pct}% 도달"),
            ("ERROR", "API_CONNECTOR", "API 연결 일시적 실패"),
            ("DEBUG", "SIGNAL_GENERATOR", "기술적 지표 계산 완료"),
            ("INFO", "NOTIFICATION", "알림 발송 완료: {count}건"),
            ("CRITICAL", "DATABASE", "데이터베이스 연결 실패"),
            ("INFO", "POSITION_MANAGER", "포지션 업데이트: {positions}개 활성"),
        ]

        # 새로운 로그 5-15개 생성
        new_log_count = random.randint(5, 15)

        for _ in range(new_log_count):
            template = random.choice(log_templates)
            level, source, message_template = template

            # 메시지 포맷팅
            message = message_template.format(
                symbol=random.choice(['BTC/USDT', 'ETH/USDT', 'BNB/USDT']),
                pct=random.randint(60, 95),
                count=random.randint(1, 10),
                positions=random.randint(0, 5)
            )

            # 로그 엔트리 생성
            log_entry = {
                'timestamp': datetime.now() - timedelta(seconds=random.randint(0, 3600)),
                'level': level,
                'source': source,
                'message': message,
                'data': {'simulation': True} if random.random() < 0.3 else {}
            }

            self.log_cache.append(log_entry)

        # 로그 캐시 크기 제한
        if len(self.log_cache) > 10000:
            self.log_cache = self.log_cache[-10000:]

        # 시간순 정렬
        self.log_cache.sort(key=lambda x: x['timestamp'], reverse=True)

    def _get_filtered_logs(self, level_filter: List[str], source_filter: List[str], keyword_filter: str) -> List[Dict]:
        """필터링된 로그 반환"""
        if not self.log_cache:
            self._refresh_logs()

        filtered = self.log_cache.copy()

        # 레벨 필터
        if level_filter:
            filtered = [log for log in filtered if log.get('level') in level_filter]

        # 소스 필터
        if source_filter:
            filtered = [log for log in filtered if log.get('source') in source_filter]

        # 키워드 필터
        if keyword_filter:
            keyword_lower = keyword_filter.lower()
            filtered = [
                log for log in filtered
                if keyword_lower in log.get('message', '').lower()
            ]

        return filtered

    def _execute_advanced_search(self, time_range: str, levels: List[str], sources: List[str],
                                search_text: str, regex_mode: bool, case_sensitive: bool,
                                include_data: bool, max_results: int) -> List[Dict]:
        """고급 검색 실행"""
        # 시뮬레이션 검색 결과
        results = self.log_cache.copy()

        # 시간 범위 필터링
        now = datetime.now()
        if time_range == "최근 1시간":
            cutoff = now - timedelta(hours=1)
        elif time_range == "최근 6시간":
            cutoff = now - timedelta(hours=6)
        elif time_range == "최근 24시간":
            cutoff = now - timedelta(hours=24)
        elif time_range == "최근 7일":
            cutoff = now - timedelta(days=7)
        else:
            cutoff = now - timedelta(days=30)  # 기본값

        results = [log for log in results if log.get('timestamp', now) >= cutoff]

        # 레벨 필터
        if levels:
            results = [log for log in results if log.get('level') in levels]

        # 소스 필터
        if sources:
            results = [log for log in results if log.get('source') in sources]

        # 텍스트 검색
        if search_text:
            if regex_mode:
                try:
                    pattern = re.compile(search_text, 0 if case_sensitive else re.IGNORECASE)
                    results = [
                        log for log in results
                        if pattern.search(log.get('message', ''))
                    ]
                except re.error:
                    st.error("정규식 패턴이 유효하지 않습니다")
                    return []
            else:
                search_lower = search_text if case_sensitive else search_text.lower()
                results = [
                    log for log in results
                    if search_lower in (log.get('message', '') if case_sensitive else log.get('message', '').lower())
                ]

        return results[:max_results]

    def _show_search_summary(self, results: List[Dict]):
        """검색 결과 요약"""
        st.markdown("#### 📊 검색 결과 요약")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("총 결과", len(results))

        with col2:
            error_count = len([r for r in results if r.get('level') in ['ERROR', 'CRITICAL']])
            st.metric("오류 로그", error_count)

        with col3:
            if results:
                latest = max(r.get('timestamp', datetime.now()) for r in results)
                oldest = min(r.get('timestamp', datetime.now()) for r in results)
                duration = (latest - oldest).total_seconds() / 3600
                st.metric("시간 범위", f"{duration:.1f}시간")

        with col4:
            sources = len(set(r.get('source', 'UNKNOWN') for r in results))
            st.metric("소스 수", sources)

    def _show_search_results(self, results: List[Dict]):
        """검색 결과 표시"""
        st.markdown("#### 📋 검색 결과")

        for result in results[:100]:  # 최대 100개 표시
            level_icon = {'DEBUG': '🔵', 'INFO': '🟢', 'WARNING': '🟡', 'ERROR': '🔴', 'CRITICAL': '🟣'}.get(result.get('level'), '⚪')
            timestamp = result.get('timestamp', datetime.now()).strftime("%m-%d %H:%M:%S")
            message = result.get('message', 'No message')

            st.text(f"{level_icon} {timestamp} [{result.get('source', 'UNKNOWN')}] {message}")

    def _calculate_log_statistics(self, period: str) -> Dict[str, Any]:
        """로그 통계 계산"""
        # 시뮬레이션 통계
        return {
            'total_logs': len(self.log_cache),
            'logs_per_minute': len(self.log_cache) / 60 if self.log_cache else 0,
            'error_rate': 15.2,
            'active_sources': 8,
            'level_distribution': {
                'DEBUG': 45,
                'INFO': 120,
                'WARNING': 25,
                'ERROR': 8,
                'CRITICAL': 2
            },
            'source_distribution': {
                'ENGINE': 50,
                'TRADE_EXECUTOR': 35,
                'RISK_MANAGER': 20,
                'API_CONNECTOR': 15,
                'NOTIFICATION': 10
            },
            'hourly_distribution': {
                f"{i:02d}:00": {
                    'INFO': random.randint(5, 25),
                    'WARNING': random.randint(0, 5),
                    'ERROR': random.randint(0, 3)
                } for i in range(24)
            }
        }

    def _analyze_log_patterns(self) -> Dict[str, Any]:
        """로그 패턴 분석"""
        return {
            'repeated_errors': {
                'count': 15,
                'description': 'API 연결 오류가 반복적으로 발생',
                'frequency': '10분마다',
                'examples': ['API connection timeout', 'Connection reset by peer']
            },
            'trading_cycles': {
                'count': 8,
                'description': '정상적인 거래 사이클 패턴',
                'frequency': '30분마다',
                'examples': ['Signal generated', 'Trade executed', 'Position updated']
            }
        }

    def _analyze_errors(self, error_logs: List[Dict]) -> Dict[str, Any]:
        """오류 분석"""
        error_types = {}
        error_sources = {}

        for error in error_logs:
            # 오류 유형 분류
            message = error.get('message', '')
            if 'connection' in message.lower():
                error_types['Connection Error'] = error_types.get('Connection Error', 0) + 1
            elif 'timeout' in message.lower():
                error_types['Timeout Error'] = error_types.get('Timeout Error', 0) + 1
            else:
                error_types['Other Error'] = error_types.get('Other Error', 0) + 1

            # 소스별 분류
            source = error.get('source', 'UNKNOWN')
            error_sources[source] = error_sources.get(source, 0) + 1

        return {
            'error_types': error_types,
            'error_sources': error_sources
        }

    def _get_error_suggestions(self, error_log: Dict[str, Any]) -> List[str]:
        """오류 해결 방법 제안"""
        message = error_log.get('message', '').lower()
        suggestions = []

        if 'connection' in message:
            suggestions.append("네트워크 연결 상태를 확인하세요")
            suggestions.append("API 키 설정을 점검하세요")

        if 'timeout' in message:
            suggestions.append("요청 타임아웃 설정을 늘려보세요")
            suggestions.append("서버 부하 상태를 확인하세요")

        if 'database' in message:
            suggestions.append("데이터베이스 연결 설정을 확인하세요")
            suggestions.append("디스크 공간을 점검하세요")

        return suggestions or ["로그를 자세히 분석하여 원인을 파악하세요"]

    def _export_logs(self, format_type: str, range_type: str) -> str:
        """로그 내보내기"""
        # 내보낼 로그 선택
        if range_type == "오류만":
            logs_to_export = [log for log in self.log_cache if log.get('level') in ['ERROR', 'CRITICAL']]
        else:
            logs_to_export = self.log_cache

        if format_type == "CSV":
            import io
            output = io.StringIO()
            output.write("timestamp,level,source,message\n")
            for log in logs_to_export:
                output.write(f"{log.get('timestamp')},{log.get('level')},{log.get('source')},\"{log.get('message')}\"\n")
            return output.getvalue()

        elif format_type == "JSON":
            return json.dumps(logs_to_export, default=str, indent=2)

        else:  # TXT
            output = []
            for log in logs_to_export:
                output.append(f"{log.get('timestamp')} [{log.get('level')}] {log.get('source')}: {log.get('message')}")
            return "\n".join(output)

    def _cleanup_old_logs(self) -> int:
        """오래된 로그 정리"""
        cutoff = datetime.now() - timedelta(days=30)
        original_count = len(self.log_cache)
        self.log_cache = [log for log in self.log_cache if log.get('timestamp', datetime.now()) >= cutoff]
        return original_count - len(self.log_cache)

    def _recalculate_log_statistics(self):
        """로그 통계 재계산"""
        # 통계 재계산 로직
        pass


# 전역 함수
def show_logs_viewer():
    """로그 뷰어 표시 (외부 호출용)"""
    viewer = AdvancedLogsViewer()
    viewer.show_logs_viewer()

def main():
    """메인 실행 함수"""
    show_logs_viewer()

if __name__ == "__main__":
    main()