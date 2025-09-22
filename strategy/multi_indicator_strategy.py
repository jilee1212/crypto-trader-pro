"""
다중 지표 전략 시스템
사용자가 여러 지표를 선택하고 조건을 설정할 수 있는 전략 빌더
"""

import streamlit as st
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class IndicatorType(Enum):
    """지표 유형"""
    TREND = "추세"
    MOMENTUM = "모멘텀"
    VOLATILITY = "변동성"
    VOLUME = "거래량"

class SignalCondition(Enum):
    """신호 조건"""
    GREATER_THAN = "초과"
    LESS_THAN = "미만"
    EQUALS = "같음"
    CROSSOVER_UP = "상향 돌파"
    CROSSOVER_DOWN = "하향 돌파"
    BETWEEN = "범위 내"

@dataclass
class IndicatorConfig:
    """지표 설정"""
    name: str
    type: IndicatorType
    parameters: Dict[str, Any]
    buy_condition: Dict[str, Any]
    sell_condition: Dict[str, Any]
    weight: float = 1.0
    enabled: bool = True

class MultiIndicatorStrategy:
    """다중 지표 전략 클래스"""

    def __init__(self):
        self.available_indicators = self._initialize_indicators()
        self.strategy_templates = self._initialize_templates()

    def _initialize_indicators(self) -> Dict[str, Dict[str, Any]]:
        """사용 가능한 지표들 초기화"""
        return {
            # 추세 지표
            "RSI": {
                "name": "RSI (상대강도지수)",
                "type": IndicatorType.MOMENTUM,
                "description": "과매수/과매도 구간을 판단하는 모멘텀 지표",
                "parameters": {
                    "period": {"type": "int", "default": 14, "min": 5, "max": 50, "label": "기간"}
                },
                "conditions": {
                    "oversold": {"default": 30, "label": "과매도 기준"},
                    "overbought": {"default": 70, "label": "과매수 기준"}
                }
            },
            "MACD": {
                "name": "MACD (이동평균수렴확산)",
                "type": IndicatorType.TREND,
                "description": "추세 전환을 감지하는 지표",
                "parameters": {
                    "fast_period": {"type": "int", "default": 12, "min": 5, "max": 30, "label": "빠른 이동평균"},
                    "slow_period": {"type": "int", "default": 26, "min": 15, "max": 50, "label": "느린 이동평균"},
                    "signal_period": {"type": "int", "default": 9, "min": 5, "max": 15, "label": "신호선 기간"}
                },
                "conditions": {
                    "bullish_signal": "MACD가 신호선을 상향 돌파",
                    "bearish_signal": "MACD가 신호선을 하향 돌파"
                }
            },
            "Bollinger_Bands": {
                "name": "볼린저 밴드",
                "type": IndicatorType.VOLATILITY,
                "description": "가격의 상대적 고점과 저점을 판단",
                "parameters": {
                    "period": {"type": "int", "default": 20, "min": 10, "max": 50, "label": "기간"},
                    "std_dev": {"type": "float", "default": 2.0, "min": 1.0, "max": 3.0, "label": "표준편차 배수"}
                },
                "conditions": {
                    "lower_band_touch": "가격이 하단 밴드 접촉",
                    "upper_band_touch": "가격이 상단 밴드 접촉"
                }
            },
            "SMA": {
                "name": "단순이동평균 (SMA)",
                "type": IndicatorType.TREND,
                "description": "기본적인 추세 확인 지표",
                "parameters": {
                    "period": {"type": "int", "default": 20, "min": 5, "max": 200, "label": "기간"}
                },
                "conditions": {
                    "price_above": "가격이 이동평균 위",
                    "price_below": "가격이 이동평균 아래"
                }
            },
            "EMA": {
                "name": "지수이동평균 (EMA)",
                "type": IndicatorType.TREND,
                "description": "최근 가격에 더 큰 가중치를 주는 이동평균",
                "parameters": {
                    "period": {"type": "int", "default": 20, "min": 5, "max": 200, "label": "기간"}
                },
                "conditions": {
                    "price_above": "가격이 EMA 위",
                    "price_below": "가격이 EMA 아래"
                }
            },
            "Stochastic": {
                "name": "스토캐스틱",
                "type": IndicatorType.MOMENTUM,
                "description": "가격의 상대적 위치를 나타내는 모멘텀 지표",
                "parameters": {
                    "k_period": {"type": "int", "default": 14, "min": 5, "max": 30, "label": "%K 기간"},
                    "d_period": {"type": "int", "default": 3, "min": 1, "max": 10, "label": "%D 기간"}
                },
                "conditions": {
                    "oversold": {"default": 20, "label": "과매도 기준"},
                    "overbought": {"default": 80, "label": "과매수 기준"}
                }
            },
            "OBV": {
                "name": "온밸런스볼륨 (OBV)",
                "type": IndicatorType.VOLUME,
                "description": "가격과 거래량의 관계를 분석",
                "parameters": {},
                "conditions": {
                    "volume_trend_up": "거래량 트렌드 상승",
                    "volume_trend_down": "거래량 트렌드 하락"
                }
            },
            "ATR": {
                "name": "평균진폭 (ATR)",
                "type": IndicatorType.VOLATILITY,
                "description": "변동성 측정 지표",
                "parameters": {
                    "period": {"type": "int", "default": 14, "min": 5, "max": 30, "label": "기간"}
                },
                "conditions": {
                    "high_volatility": "높은 변동성",
                    "low_volatility": "낮은 변동성"
                }
            }
        }

    def _initialize_templates(self) -> Dict[str, Dict[str, Any]]:
        """사전 정의된 전략 템플릿"""
        return {
            "보수적 전략": {
                "description": "안정적인 수익을 추구하는 보수적 전략",
                "indicators": ["RSI", "SMA", "Bollinger_Bands"],
                "entry_rules": {"min_signals": 3, "total_indicators": 3},
                "settings": {
                    "RSI": {"period": 21, "oversold": 25, "overbought": 75},
                    "SMA": {"period": 50},
                    "Bollinger_Bands": {"period": 20, "std_dev": 2.5}
                }
            },
            "균형 전략": {
                "description": "리스크와 수익의 균형을 맞춘 전략",
                "indicators": ["RSI", "MACD", "SMA"],
                "entry_rules": {"min_signals": 2, "total_indicators": 3},
                "settings": {
                    "RSI": {"period": 14, "oversold": 30, "overbought": 70},
                    "MACD": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
                    "SMA": {"period": 20}
                }
            },
            "적극적 전략": {
                "description": "높은 수익을 추구하는 적극적 전략",
                "indicators": ["RSI", "MACD", "Stochastic", "EMA"],
                "entry_rules": {"min_signals": 2, "total_indicators": 4},
                "settings": {
                    "RSI": {"period": 7, "oversold": 35, "overbought": 65},
                    "MACD": {"fast_period": 8, "slow_period": 21, "signal_period": 5},
                    "Stochastic": {"k_period": 14, "d_period": 3},
                    "EMA": {"period": 10}
                }
            },
            "트렌드 추종": {
                "description": "추세를 따라가는 전략",
                "indicators": ["MACD", "SMA", "EMA"],
                "entry_rules": {"min_signals": 2, "total_indicators": 3},
                "settings": {
                    "MACD": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
                    "SMA": {"period": 50},
                    "EMA": {"period": 20}
                }
            },
            "변동성 활용": {
                "description": "변동성을 활용한 전략",
                "indicators": ["Bollinger_Bands", "ATR", "RSI"],
                "entry_rules": {"min_signals": 2, "total_indicators": 3},
                "settings": {
                    "Bollinger_Bands": {"period": 20, "std_dev": 2.0},
                    "ATR": {"period": 14},
                    "RSI": {"period": 14}
                }
            }
        }

    def show_strategy_selector(self) -> Optional[Dict[str, Any]]:
        """전략 선택 인터페이스"""
        st.markdown("### 🎯 다중 지표 전략 설정")
        st.markdown("자동매매 시작 전에 사용할 전략을 선택하고 설정하세요.")

        # 전략 선택 방식
        strategy_mode = st.radio(
            "전략 설정 방식",
            ["📋 템플릿 사용", "🔧 직접 설정"],
            key="strategy_mode"
        )

        if strategy_mode == "📋 템플릿 사용":
            return self._show_template_selector()
        else:
            return self._show_custom_strategy_builder()

    def _show_template_selector(self) -> Optional[Dict[str, Any]]:
        """템플릿 선택 인터페이스"""
        st.markdown("#### 📋 사전 정의된 전략 템플릿")

        template_names = list(self.strategy_templates.keys())
        selected_template = st.selectbox(
            "전략 템플릿 선택",
            template_names,
            key="strategy_template"
        )

        if selected_template:
            template = self.strategy_templates[selected_template]

            # 템플릿 정보 표시
            st.info(f"**{selected_template}**\n{template['description']}")

            # 사용 지표 표시
            with st.expander("📊 사용 지표 및 설정", expanded=True):
                for indicator_name in template['indicators']:
                    indicator_info = self.available_indicators[indicator_name]
                    settings = template.get('settings', {}).get(indicator_name, {})

                    st.markdown(f"**{indicator_info['name']}**")
                    st.write(f"- 유형: {indicator_info['type'].value}")
                    st.write(f"- 설명: {indicator_info['description']}")

                    if settings:
                        st.write("- 설정:")
                        for key, value in settings.items():
                            st.write(f"  - {key}: {value}")

            # 진입 조건 표시
            entry_rules = template['entry_rules']
            st.markdown("#### ⚡ 진입 조건")
            st.write(f"- **최소 신호 수**: {entry_rules['min_signals']}개")
            st.write(f"- **총 지표 수**: {entry_rules['total_indicators']}개")
            st.write(f"- **조건**: {entry_rules['total_indicators']}개 지표 중 {entry_rules['min_signals']}개 이상 신호 발생 시 진입")

            # 추가 설정
            st.markdown("#### ⚙️ 추가 설정")

            col1, col2 = st.columns(2)

            with col1:
                risk_level = st.selectbox(
                    "리스크 수준",
                    ["낮음", "보통", "높음"],
                    index=1,
                    key="template_risk_level"
                )

                position_size = st.slider(
                    "포지션 크기 (%)",
                    min_value=1,
                    max_value=10,
                    value=3,
                    key="template_position_size"
                )

            with col2:
                take_profit = st.number_input(
                    "목표 수익률 (%)",
                    min_value=0.5,
                    max_value=20.0,
                    value=3.0,
                    step=0.5,
                    key="template_take_profit"
                )

                stop_loss = st.number_input(
                    "손절 비율 (%)",
                    min_value=0.5,
                    max_value=10.0,
                    value=2.0,
                    step=0.5,
                    key="template_stop_loss"
                )

            # 전략 설정 확인
            if st.button("✅ 이 전략으로 설정", type="primary", key="confirm_template"):
                strategy_config = {
                    "name": selected_template,
                    "type": "template",
                    "template": template,
                    "additional_settings": {
                        "risk_level": risk_level,
                        "position_size_pct": position_size,
                        "take_profit_pct": take_profit,
                        "stop_loss_pct": stop_loss
                    }
                }

                st.success(f"✅ '{selected_template}' 전략이 설정되었습니다!")
                st.json(strategy_config)
                return strategy_config

        return None

    def _show_custom_strategy_builder(self) -> Optional[Dict[str, Any]]:
        """맞춤 전략 빌더"""
        st.markdown("#### 🔧 맞춤 전략 만들기")

        # 지표 선택
        st.markdown("##### 1. 사용할 지표 선택")

        selected_indicators = []
        indicator_configs = {}

        # 지표 유형별로 구분하여 표시
        for indicator_type in IndicatorType:
            with st.expander(f"{indicator_type.value} 지표", expanded=False):
                type_indicators = [
                    name for name, info in self.available_indicators.items()
                    if info['type'] == indicator_type
                ]

                for indicator_name in type_indicators:
                    indicator_info = self.available_indicators[indicator_name]

                    # 지표 선택 체크박스
                    if st.checkbox(
                        f"{indicator_info['name']}",
                        key=f"select_{indicator_name}",
                        help=indicator_info['description']
                    ):
                        selected_indicators.append(indicator_name)

                        # 파라미터 설정
                        st.markdown(f"**{indicator_info['name']} 설정**")
                        params = {}

                        for param_name, param_info in indicator_info.get('parameters', {}).items():
                            if param_info['type'] == 'int':
                                params[param_name] = st.slider(
                                    param_info['label'],
                                    min_value=param_info['min'],
                                    max_value=param_info['max'],
                                    value=param_info['default'],
                                    key=f"{indicator_name}_{param_name}"
                                )
                            elif param_info['type'] == 'float':
                                params[param_name] = st.number_input(
                                    param_info['label'],
                                    min_value=param_info['min'],
                                    max_value=param_info['max'],
                                    value=param_info['default'],
                                    step=0.1,
                                    key=f"{indicator_name}_{param_name}"
                                )

                        # 조건 설정
                        conditions = indicator_info.get('conditions', {})
                        if conditions:
                            st.markdown("**진입/청산 조건**")
                            for condition_name, condition_desc in conditions.items():
                                if isinstance(condition_desc, dict):
                                    st.number_input(
                                        condition_desc['label'],
                                        value=condition_desc['default'],
                                        key=f"{indicator_name}_{condition_name}"
                                    )

                        indicator_configs[indicator_name] = {
                            'parameters': params,
                            'weight': st.slider(
                                f"{indicator_info['name']} 가중치",
                                min_value=0.5,
                                max_value=2.0,
                                value=1.0,
                                step=0.1,
                                key=f"{indicator_name}_weight"
                            )
                        }

        if selected_indicators:
            st.markdown("##### 2. 진입 조건 설정")

            col1, col2 = st.columns(2)

            with col1:
                min_signals = st.slider(
                    "최소 필요 신호 수",
                    min_value=1,
                    max_value=len(selected_indicators),
                    value=min(2, len(selected_indicators)),
                    key="custom_min_signals"
                )

                use_weighted = st.checkbox(
                    "가중치 기반 평가 사용",
                    key="custom_use_weighted"
                )

                if use_weighted:
                    weight_threshold = st.slider(
                        "가중치 합계 임계값",
                        min_value=1.0,
                        max_value=sum(config['weight'] for config in indicator_configs.values()),
                        value=2.0,
                        step=0.1,
                        key="custom_weight_threshold"
                    )

            with col2:
                st.markdown("**선택된 지표**")
                for indicator in selected_indicators:
                    weight = indicator_configs[indicator]['weight']
                    st.write(f"- {self.available_indicators[indicator]['name']} (가중치: {weight})")

                st.markdown(f"**진입 조건**")
                if use_weighted:
                    st.write(f"- 가중치 합계 {weight_threshold} 이상")
                else:
                    st.write(f"- {len(selected_indicators)}개 중 {min_signals}개 이상 신호")

            # 전략 저장
            if st.button("💾 맞춤 전략 저장", type="primary", key="save_custom_strategy"):
                custom_strategy = {
                    "name": "맞춤 전략",
                    "type": "custom",
                    "indicators": selected_indicators,
                    "indicator_configs": indicator_configs,
                    "entry_rules": {
                        "min_signals": min_signals,
                        "total_indicators": len(selected_indicators),
                        "use_weighted": use_weighted,
                        "weight_threshold": weight_threshold if use_weighted else None
                    }
                }

                st.success("✅ 맞춤 전략이 저장되었습니다!")
                st.json(custom_strategy)
                return custom_strategy

        else:
            st.info("👆 사용할 지표를 선택해주세요.")

        return None