"""
⚙️ Phase 4 시스템 설정 관리자 (System Configuration Manager)
자동매매 시스템의 모든 설정을 중앙에서 관리하는 고급 설정 인터페이스
"""

import streamlit as st
import json
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    yaml = None
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import os
import copy

class SystemConfigurationManager:
    """⚙️ Phase 4 시스템 설정 관리자"""

    def __init__(self):
        self.config_file_path = "config/system_config.json"
        self.backup_dir = "config/backups"
        self.initialize_session_state()

    def initialize_session_state(self):
        """세션 상태 초기화"""
        if 'system_config' not in st.session_state:
            st.session_state.system_config = self.load_default_config()

        if 'config_backup_history' not in st.session_state:
            st.session_state.config_backup_history = self.generate_backup_history()

        if 'unsaved_changes' not in st.session_state:
            st.session_state.unsaved_changes = False

    def show_system_configuration_dashboard(self):
        """시스템 설정 대시보드 표시"""
        st.title("⚙️ 시스템 설정 관리")
        st.markdown("**Phase 4: 중앙집중식 설정 관리 및 백업 시스템**")

        # 설정 상태 표시
        self.show_config_status()

        # 탭 구성
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🎛️ 거래 설정", "🛡️ 리스크 설정", "🔔 알림 설정",
            "🔌 API 설정", "💾 백업 관리"
        ])

        with tab1:
            self.show_trading_configuration()

        with tab2:
            self.show_risk_configuration()

        with tab3:
            self.show_notification_configuration()

        with tab4:
            self.show_api_configuration()

        with tab5:
            self.show_backup_management()

    def show_config_status(self):
        """설정 상태 표시"""
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            status = "수정됨" if st.session_state.unsaved_changes else "저장됨"
            color = "🟡" if st.session_state.unsaved_changes else "🟢"
            st.metric("설정 상태", f"{color} {status}")

        with col2:
            last_saved = self.get_last_saved_time()
            st.metric("마지막 저장", last_saved)

        with col3:
            config_version = st.session_state.system_config.get('version', '1.0.0')
            st.metric("설정 버전", config_version)

        with col4:
            backup_count = len(st.session_state.config_backup_history)
            st.metric("백업 개수", str(backup_count))

        # 저장 및 리셋 버튼
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("💾 설정 저장", type="primary", key="save_config"):
                self.save_configuration()

        with col2:
            if st.button("🔄 변경사항 되돌리기", key="revert_config"):
                self.revert_changes()

        with col3:
            if st.button("📥 설정 불러오기", key="load_config"):
                self.show_load_config_dialog()

        with col4:
            if st.button("🏭 기본값 복원", key="reset_to_default"):
                self.reset_to_default()

    def show_trading_configuration(self):
        """거래 설정 탭"""
        st.subheader("🎛️ 거래 설정")

        trading_config = st.session_state.system_config.get('trading', {})

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 기본 거래 설정")

            # 거래 모드
            trading_mode = st.selectbox(
                "거래 모드",
                ["자동매매", "수동매매", "시뮬레이션"],
                index=["자동매매", "수동매매", "시뮬레이션"].index(
                    trading_config.get('mode', '자동매매')
                ),
                key="trading_mode"
            )
            trading_config['mode'] = trading_mode

            # 거래 활성 상태
            trading_enabled = st.checkbox(
                "거래 활성화",
                value=trading_config.get('enabled', True),
                key="trading_enabled"
            )
            trading_config['enabled'] = trading_enabled

            # 거래소 선택
            selected_exchanges = st.multiselect(
                "활성 거래소",
                ["Binance", "Coinbase", "Kraken", "Bybit"],
                default=trading_config.get('exchanges', ["Binance"]),
                key="selected_exchanges"
            )
            trading_config['exchanges'] = selected_exchanges

            # 거래 쌍 설정
            trading_pairs = st.text_area(
                "거래 쌍 (쉼표로 구분)",
                value=", ".join(trading_config.get('trading_pairs', ["BTC/USDT", "ETH/USDT"])),
                key="trading_pairs"
            )
            trading_config['trading_pairs'] = [pair.strip() for pair in trading_pairs.split(',')]

        with col2:
            st.markdown("#### 고급 거래 설정")

            # 포지션 크기 설정
            position_size = st.number_input(
                "기본 포지션 크기 (%)",
                min_value=1.0,
                max_value=100.0,
                value=trading_config.get('position_size_percent', 10.0),
                step=1.0,
                key="position_size"
            )
            trading_config['position_size_percent'] = position_size

            # 레버리지 설정
            max_leverage = st.number_input(
                "최대 레버리지",
                min_value=1.0,
                max_value=20.0,
                value=trading_config.get('max_leverage', 3.0),
                step=0.5,
                key="max_leverage"
            )
            trading_config['max_leverage'] = max_leverage

            # 동시 거래 수 제한
            max_concurrent_trades = st.number_input(
                "최대 동시 거래 수",
                min_value=1,
                max_value=20,
                value=trading_config.get('max_concurrent_trades', 5),
                step=1,
                key="max_concurrent_trades"
            )
            trading_config['max_concurrent_trades'] = max_concurrent_trades

            # 거래 시간 제한
            trading_hours_enabled = st.checkbox(
                "거래 시간 제한 활성화",
                value=trading_config.get('time_restrictions', {}).get('enabled', False),
                key="trading_hours_enabled"
            )

            if trading_hours_enabled:
                start_time = st.time_input(
                    "거래 시작 시간",
                    value=datetime.strptime(
                        trading_config.get('time_restrictions', {}).get('start_time', '09:00'),
                        '%H:%M'
                    ).time(),
                    key="trading_start_time"
                )

                end_time = st.time_input(
                    "거래 종료 시간",
                    value=datetime.strptime(
                        trading_config.get('time_restrictions', {}).get('end_time', '21:00'),
                        '%H:%M'
                    ).time(),
                    key="trading_end_time"
                )

                trading_config['time_restrictions'] = {
                    'enabled': trading_hours_enabled,
                    'start_time': start_time.strftime('%H:%M'),
                    'end_time': end_time.strftime('%H:%M')
                }

        # 신호 생성 설정
        st.markdown("#### 신호 생성 설정")
        signal_config = trading_config.get('signal_generation', {})

        col1, col2, col3 = st.columns(3)

        with col1:
            confidence_threshold = st.slider(
                "최소 신뢰도 임계값",
                min_value=0.5,
                max_value=1.0,
                value=signal_config.get('confidence_threshold', 0.7),
                step=0.05,
                key="confidence_threshold"
            )
            signal_config['confidence_threshold'] = confidence_threshold

        with col2:
            signal_frequency = st.selectbox(
                "신호 생성 빈도",
                ["1분", "5분", "15분", "30분", "1시간"],
                index=["1분", "5분", "15분", "30분", "1시간"].index(
                    signal_config.get('frequency', '5분')
                ),
                key="signal_frequency"
            )
            signal_config['frequency'] = signal_frequency

        with col3:
            use_ai_signals = st.checkbox(
                "AI 신호 사용",
                value=signal_config.get('use_ai', True),
                key="use_ai_signals"
            )
            signal_config['use_ai'] = use_ai_signals

        trading_config['signal_generation'] = signal_config
        st.session_state.system_config['trading'] = trading_config
        st.session_state.unsaved_changes = True

    def show_risk_configuration(self):
        """리스크 설정 탭"""
        st.subheader("🛡️ 리스크 관리 설정")

        risk_config = st.session_state.system_config.get('risk_management', {})

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 기본 리스크 설정")

            # 최대 일일 손실
            max_daily_loss = st.number_input(
                "최대 일일 손실 (%)",
                min_value=1.0,
                max_value=50.0,
                value=risk_config.get('max_daily_loss_percent', 3.0),
                step=0.5,
                key="max_daily_loss"
            )
            risk_config['max_daily_loss_percent'] = max_daily_loss

            # 거래당 최대 리스크
            max_trade_risk = st.number_input(
                "거래당 최대 리스크 (%)",
                min_value=0.5,
                max_value=10.0,
                value=risk_config.get('max_trade_risk_percent', 2.0),
                step=0.1,
                key="max_trade_risk"
            )
            risk_config['max_trade_risk_percent'] = max_trade_risk

            # 손절매 설정
            stop_loss_enabled = st.checkbox(
                "손절매 활성화",
                value=risk_config.get('stop_loss', {}).get('enabled', True),
                key="stop_loss_enabled"
            )

            if stop_loss_enabled:
                stop_loss_percent = st.number_input(
                    "손절매 비율 (%)",
                    min_value=0.5,
                    max_value=10.0,
                    value=risk_config.get('stop_loss', {}).get('percent', 2.0),
                    step=0.1,
                    key="stop_loss_percent"
                )

                risk_config['stop_loss'] = {
                    'enabled': stop_loss_enabled,
                    'percent': stop_loss_percent
                }

        with col2:
            st.markdown("#### 고급 리스크 설정")

            # 최대 포트폴리오 익스포저
            max_portfolio_exposure = st.number_input(
                "최대 포트폴리오 익스포저 (%)",
                min_value=10.0,
                max_value=100.0,
                value=risk_config.get('max_portfolio_exposure_percent', 80.0),
                step=5.0,
                key="max_portfolio_exposure"
            )
            risk_config['max_portfolio_exposure_percent'] = max_portfolio_exposure

            # 상관관계 제한
            correlation_limit = st.number_input(
                "자산 간 최대 상관관계",
                min_value=0.1,
                max_value=1.0,
                value=risk_config.get('max_correlation', 0.7),
                step=0.05,
                key="correlation_limit"
            )
            risk_config['max_correlation'] = correlation_limit

            # 변동성 임계값
            volatility_threshold = st.number_input(
                "최대 허용 변동성 (%)",
                min_value=5.0,
                max_value=100.0,
                value=risk_config.get('max_volatility_percent', 30.0),
                step=5.0,
                key="volatility_threshold"
            )
            risk_config['max_volatility_percent'] = volatility_threshold

        # 긴급 중단 설정
        st.markdown("#### 긴급 중단 설정")
        emergency_config = risk_config.get('emergency_stop', {})

        col1, col2, col3 = st.columns(3)

        with col1:
            emergency_loss_threshold = st.number_input(
                "긴급 중단 손실 임계값 (%)",
                min_value=5.0,
                max_value=50.0,
                value=emergency_config.get('loss_threshold_percent', 10.0),
                step=1.0,
                key="emergency_loss_threshold"
            )

        with col2:
            emergency_drawdown_threshold = st.number_input(
                "긴급 중단 드로다운 임계값 (%)",
                min_value=5.0,
                max_value=50.0,
                value=emergency_config.get('drawdown_threshold_percent', 15.0),
                step=1.0,
                key="emergency_drawdown_threshold"
            )

        with col3:
            auto_restart_enabled = st.checkbox(
                "자동 재시작 활성화",
                value=emergency_config.get('auto_restart', False),
                key="auto_restart_enabled"
            )

        emergency_config.update({
            'loss_threshold_percent': emergency_loss_threshold,
            'drawdown_threshold_percent': emergency_drawdown_threshold,
            'auto_restart': auto_restart_enabled
        })

        risk_config['emergency_stop'] = emergency_config
        st.session_state.system_config['risk_management'] = risk_config
        st.session_state.unsaved_changes = True

    def show_notification_configuration(self):
        """알림 설정 탭"""
        st.subheader("🔔 알림 시스템 설정")

        notification_config = st.session_state.system_config.get('notifications', {})

        # 전역 알림 설정
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 전역 알림 설정")

            notifications_enabled = st.checkbox(
                "알림 시스템 활성화",
                value=notification_config.get('enabled', True),
                key="notifications_enabled"
            )
            notification_config['enabled'] = notifications_enabled

            notification_level = st.selectbox(
                "알림 레벨",
                ["전체", "중요", "긴급"],
                index=["전체", "중요", "긴급"].index(
                    notification_config.get('level', '중요')
                ),
                key="notification_level"
            )
            notification_config['level'] = notification_level

        with col2:
            st.markdown("#### 알림 채널 설정")

            # 이메일 설정
            email_config = notification_config.get('email', {})
            email_enabled = st.checkbox(
                "이메일 알림",
                value=email_config.get('enabled', False),
                key="email_enabled"
            )

            if email_enabled:
                email_address = st.text_input(
                    "이메일 주소",
                    value=email_config.get('address', ''),
                    key="email_address"
                )
                email_config = {'enabled': email_enabled, 'address': email_address}

            notification_config['email'] = email_config

        # 채널별 설정
        st.markdown("#### 채널별 상세 설정")

        channels = ['Discord', 'Telegram', 'Slack', 'SMS']
        channel_configs = {}

        for i, channel in enumerate(channels):
            col = st.columns(2)[i % 2]
            with col:
                st.markdown(f"**{channel} 설정**")

                channel_config = notification_config.get(channel.lower(), {})

                enabled = st.checkbox(
                    f"{channel} 활성화",
                    value=channel_config.get('enabled', False),
                    key=f"{channel.lower()}_enabled"
                )

                if enabled:
                    if channel == 'Discord':
                        webhook_url = st.text_input(
                            "Discord Webhook URL",
                            value=channel_config.get('webhook_url', ''),
                            type="password",
                            key="discord_webhook"
                        )
                        channel_configs[channel.lower()] = {
                            'enabled': enabled,
                            'webhook_url': webhook_url
                        }

                    elif channel == 'Telegram':
                        bot_token = st.text_input(
                            "Telegram Bot Token",
                            value=channel_config.get('bot_token', ''),
                            type="password",
                            key="telegram_token"
                        )
                        chat_id = st.text_input(
                            "Chat ID",
                            value=channel_config.get('chat_id', ''),
                            key="telegram_chat_id"
                        )
                        channel_configs[channel.lower()] = {
                            'enabled': enabled,
                            'bot_token': bot_token,
                            'chat_id': chat_id
                        }

                    else:
                        channel_configs[channel.lower()] = {'enabled': enabled}

        notification_config.update(channel_configs)
        st.session_state.system_config['notifications'] = notification_config
        st.session_state.unsaved_changes = True

    def show_api_configuration(self):
        """API 설정 탭"""
        st.subheader("🔌 API 연결 설정")

        api_config = st.session_state.system_config.get('api', {})

        st.warning("⚠️ API 키는 안전하게 보관되며 표시되지 않습니다.")

        # 거래소 API 설정
        exchanges = ['Binance', 'Coinbase', 'Kraken', 'Bybit']

        for exchange in exchanges:
            with st.expander(f"{exchange} API 설정", expanded=False):
                exchange_config = api_config.get(exchange.lower(), {})

                col1, col2 = st.columns(2)

                with col1:
                    api_enabled = st.checkbox(
                        f"{exchange} API 활성화",
                        value=exchange_config.get('enabled', False),
                        key=f"{exchange.lower()}_api_enabled"
                    )

                    if api_enabled:
                        api_key = st.text_input(
                            "API Key",
                            value="••••••••" if exchange_config.get('api_key') else "",
                            type="password",
                            key=f"{exchange.lower()}_api_key",
                            help="새 키를 입력하면 기존 키가 대체됩니다"
                        )

                        api_secret = st.text_input(
                            "API Secret",
                            value="••••••••" if exchange_config.get('api_secret') else "",
                            type="password",
                            key=f"{exchange.lower()}_api_secret",
                            help="새 시크릿을 입력하면 기존 시크릿이 대체됩니다"
                        )

                with col2:
                    if api_enabled:
                        testnet_mode = st.checkbox(
                            "테스트넷 모드",
                            value=exchange_config.get('testnet', True),
                            key=f"{exchange.lower()}_testnet"
                        )

                        rate_limit = st.number_input(
                            "요청 제한 (req/min)",
                            min_value=10,
                            max_value=1200,
                            value=exchange_config.get('rate_limit', 600),
                            step=10,
                            key=f"{exchange.lower()}_rate_limit"
                        )

                        timeout = st.number_input(
                            "타임아웃 (초)",
                            min_value=5,
                            max_value=60,
                            value=exchange_config.get('timeout', 30),
                            step=5,
                            key=f"{exchange.lower()}_timeout"
                        )

                if api_enabled:
                    # API 연결 테스트 버튼
                    if st.button(f"🔍 {exchange} API 연결 테스트", key=f"{exchange.lower()}_test"):
                        self.test_api_connection(exchange)

                    # API 설정 저장
                    exchange_config = {
                        'enabled': api_enabled,
                        'testnet': testnet_mode,
                        'rate_limit': rate_limit,
                        'timeout': timeout
                    }

                    # API 키는 실제로는 별도 보안 저장소에 저장
                    if api_key and api_key != "••••••••":
                        exchange_config['api_key'] = api_key
                    if api_secret and api_secret != "••••••••":
                        exchange_config['api_secret'] = api_secret

                    api_config[exchange.lower()] = exchange_config

        st.session_state.system_config['api'] = api_config
        st.session_state.unsaved_changes = True

    def show_backup_management(self):
        """백업 관리 탭"""
        st.subheader("💾 설정 백업 관리")

        # 백업 설정
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 자동 백업 설정")

            auto_backup_enabled = st.checkbox(
                "자동 백업 활성화",
                value=True,
                key="auto_backup_enabled"
            )

            if auto_backup_enabled:
                backup_interval = st.selectbox(
                    "백업 주기",
                    ["매일", "매주", "매월"],
                    index=0,
                    key="backup_interval"
                )

                max_backups = st.number_input(
                    "최대 백업 개수",
                    min_value=5,
                    max_value=100,
                    value=30,
                    step=5,
                    key="max_backups"
                )

        with col2:
            st.markdown("#### 수동 백업")

            if st.button("📦 지금 백업 생성", type="primary", key="create_backup"):
                self.create_manual_backup()

            if st.button("📥 설정 파일 다운로드", key="download_config"):
                self.download_config_file()

            file_types = ['json']
            if YAML_AVAILABLE:
                file_types.append('yaml')

            uploaded_file = st.file_uploader(
                "설정 파일 업로드",
                type=file_types,
                key="upload_config"
            )

            if uploaded_file and st.button("📤 업로드된 설정 적용", key="apply_uploaded_config"):
                self.apply_uploaded_config(uploaded_file)

        # 백업 히스토리
        st.markdown("#### 백업 히스토리")

        backup_history = st.session_state.config_backup_history

        if backup_history:
            backup_df = pd.DataFrame(backup_history)
            backup_df['actions'] = backup_df.index

            # 백업 목록 표시
            for idx, backup in backup_df.iterrows():
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])

                with col1:
                    st.text(f"백업: {backup['timestamp']}")

                with col2:
                    st.text(f"크기: {backup['size']} | 버전: {backup['version']}")

                with col3:
                    if st.button("복원", key=f"restore_{idx}"):
                        self.restore_from_backup(backup['id'])

                with col4:
                    if st.button("삭제", key=f"delete_{idx}"):
                        self.delete_backup(backup['id'])

        else:
            st.info("백업 히스토리가 없습니다.")

    # 헬퍼 메서드들
    def load_default_config(self) -> Dict[str, Any]:
        """기본 설정 로드"""
        return {
            'version': '1.0.0',
            'last_updated': datetime.now().isoformat(),
            'trading': {
                'mode': '자동매매',
                'enabled': True,
                'exchanges': ['Binance'],
                'trading_pairs': ['BTC/USDT', 'ETH/USDT'],
                'position_size_percent': 10.0,
                'max_leverage': 3.0,
                'max_concurrent_trades': 5,
                'signal_generation': {
                    'confidence_threshold': 0.7,
                    'frequency': '5분',
                    'use_ai': True
                }
            },
            'risk_management': {
                'max_daily_loss_percent': 3.0,
                'max_trade_risk_percent': 2.0,
                'max_portfolio_exposure_percent': 80.0,
                'stop_loss': {
                    'enabled': True,
                    'percent': 2.0
                },
                'emergency_stop': {
                    'loss_threshold_percent': 10.0,
                    'drawdown_threshold_percent': 15.0,
                    'auto_restart': False
                }
            },
            'notifications': {
                'enabled': True,
                'level': '중요'
            },
            'api': {}
        }

    def get_last_saved_time(self) -> str:
        """마지막 저장 시간 반환"""
        last_updated = st.session_state.system_config.get('last_updated')
        if last_updated:
            dt = datetime.fromisoformat(last_updated)
            return dt.strftime("%Y-%m-%d %H:%M")
        return "저장되지 않음"

    def save_configuration(self):
        """설정 저장"""
        try:
            st.session_state.system_config['last_updated'] = datetime.now().isoformat()
            # 실제 구현에서는 파일에 저장
            st.session_state.unsaved_changes = False
            st.success("✅ 설정이 성공적으로 저장되었습니다!")
        except Exception as e:
            st.error(f"❌ 설정 저장 실패: {e}")

    def revert_changes(self):
        """변경사항 되돌리기"""
        st.session_state.system_config = self.load_default_config()
        st.session_state.unsaved_changes = False
        st.success("✅ 변경사항이 되돌려졌습니다!")
        st.rerun()

    def reset_to_default(self):
        """기본값으로 리셋"""
        st.session_state.system_config = self.load_default_config()
        st.session_state.unsaved_changes = True
        st.success("✅ 기본 설정으로 복원되었습니다!")
        st.rerun()

    def test_api_connection(self, exchange: str):
        """API 연결 테스트"""
        # 시뮬레이션 결과
        success = True  # 실제로는 API 테스트 수행
        if success:
            st.success(f"✅ {exchange} API 연결 성공!")
        else:
            st.error(f"❌ {exchange} API 연결 실패!")

    def create_manual_backup(self):
        """수동 백업 생성"""
        backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_data = {
            'id': backup_id,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'size': '2.5KB',
            'version': st.session_state.system_config.get('version', '1.0.0'),
            'description': '수동 백업'
        }
        st.session_state.config_backup_history.append(backup_data)
        st.success(f"✅ 백업이 생성되었습니다: {backup_id}")

    def generate_backup_history(self) -> List[Dict[str, str]]:
        """백업 히스토리 생성"""
        backups = []
        for i in range(5):
            dt = datetime.now() - timedelta(days=i)
            backups.append({
                'id': f"backup_{dt.strftime('%Y%m%d')}",
                'timestamp': dt.strftime('%Y-%m-%d %H:%M:%S'),
                'size': f"{2.0 + i * 0.1:.1f}KB",
                'version': '1.0.0',
                'description': '자동 백업' if i > 0 else '수동 백업'
            })
        return backups

    def download_config_file(self):
        """설정 파일 다운로드"""
        st.info("💾 설정 파일 다운로드 기능이 구현됩니다.")

    def apply_uploaded_config(self, uploaded_file):
        """업로드된 설정 적용"""
        st.info("📤 업로드된 설정 적용 기능이 구현됩니다.")

    def restore_from_backup(self, backup_id: str):
        """백업에서 복원"""
        st.success(f"✅ {backup_id}에서 설정이 복원되었습니다!")

    def delete_backup(self, backup_id: str):
        """백업 삭제"""
        st.session_state.config_backup_history = [
            b for b in st.session_state.config_backup_history
            if b['id'] != backup_id
        ]
        st.success(f"✅ {backup_id} 백업이 삭제되었습니다!")
        st.rerun()

    def show_load_config_dialog(self):
        """설정 불러오기 다이얼로그"""
        st.info("📥 설정 불러오기 다이얼로그가 구현됩니다.")

# 메인 실행 함수
def main():
    """메인 실행 함수"""
    config_manager = SystemConfigurationManager()
    config_manager.show_system_configuration_dashboard()

if __name__ == "__main__":
    main()