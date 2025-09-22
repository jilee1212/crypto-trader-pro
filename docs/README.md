# 📚 Crypto Trader Pro - 문서 목록

이 폴더에는 Crypto Trader Pro 프로젝트의 모든 문서가 정리되어 있습니다.

**🎉 Phase 1-4 완료: 24시간 무인 자동매매 시스템 + 고급 기능 100% 구축 완료**

## 🎯 시작하기 (필수 문서)

### 1. [CLAUDE.md](./CLAUDE.md)
- **목적**: 프로젝트 개요 및 개발 가이드라인
- **내용**: 목표, 기술 스택, 개발 원칙, 코딩 스타일
- **대상**: 모든 개발자 (필수 읽기)

### 2. [SETUP.md](./SETUP.md)
- **목적**: 개발 환경 설정 가이드
- **내용**: Python 설치, 의존성, API 키 설정, 보안
- **대상**: 새로운 개발자, 환경 설정 시

## 🏗️ 시스템 아키텍처

### 3. [AUTO_TRADING_ARCHITECTURE.md](./AUTO_TRADING_ARCHITECTURE.md)
- **목적**: 자동매매 시스템 설계 문서
- **내용**: 시스템 구조, 컴포넌트, 데이터베이스 설계
- **대상**: 시스템 설계자, 고급 개발자

### 4. [MULTI_INDICATOR_STRATEGY_DESIGN.md](./MULTI_INDICATOR_STRATEGY_DESIGN.md)
- **목적**: 다중 지표 거래 전략 설계
- **내용**: RSI, MACD, 볼린저 밴드 통합 전략
- **대상**: 전략 개발자, 퀀트 분석가

## 🚀 배포 및 협업

### 5. [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
- **목적**: GitHub 배포 및 보안 가이드
- **내용**: Git 설정, 보안 체크리스트, 배포 절차
- **대상**: DevOps, 프로젝트 관리자

### 6. [CONTRIBUTING.md](./CONTRIBUTING.md)
- **목적**: 프로젝트 기여 가이드라인
- **내용**: 코드 스타일, PR 절차, 이슈 보고
- **대상**: 컨트리뷰터, 오픈소스 참여자

## 📈 프로젝트 관리

### 7. [UPDATED_ROADMAP_2025.md](./UPDATED_ROADMAP_2025.md)
- **목적**: 2025년 개발 로드맵
- **내용**: 단계별 개발 계획, 마일스톤, 우선순위
- **대상**: 프로젝트 매니저, 팀 리더

### 8. [README_AUTOMATED_TRADING.md](./README_AUTOMATED_TRADING.md)
- **목적**: 자동매매 기능 상세 설명
- **내용**: 자동매매 사용법, 설정, 주의사항
- **대상**: 자동매매 사용자

## 📖 문서 사용 가이드

### 🆕 새로운 개발자
1. **CLAUDE.md** → **SETUP.md** → **메인 README.md** 순서로 읽기
2. 개발 환경 설정 후 실제 코드 분석
3. 특정 기능 개발 시 해당 아키텍처 문서 참조

### 🔧 기존 개발자
- 새로운 기능 개발: **AUTO_TRADING_ARCHITECTURE.md** 참조
- 전략 개발: **MULTI_INDICATOR_STRATEGY_DESIGN.md** 참조
- 배포 준비: **DEPLOYMENT_GUIDE.md** 체크리스트 확인

### 🤝 외부 기여자
- **CONTRIBUTING.md**에서 기여 방법 확인
- **CLAUDE.md**에서 프로젝트 원칙 이해
- 이슈 생성 전 기존 문서 검토

## 🎯 클로드 AI 활용 시 권장 문서

클로드 AI에게 프로젝트 분석을 요청할 때 다음 문서들을 제공하면 최적의 결과를 얻을 수 있습니다:

### 기본 패키지 (항상 제공)
```
- docs/CLAUDE.md (프로젝트 가이드라인)
- README.md (현재 상태)
- docs/SETUP.md (환경 설정)
```

### 상황별 추가 문서
```
자동매매 개발: + docs/AUTO_TRADING_ARCHITECTURE.md
전략 개발: + docs/MULTI_INDICATOR_STRATEGY_DESIGN.md
배포 준비: + docs/DEPLOYMENT_GUIDE.md
로드맵 확인: + docs/UPDATED_ROADMAP_2025.md
```

## 📝 문서 업데이트 규칙

1. **일관성**: 모든 문서는 현재 코드베이스와 일치해야 함
2. **최신성**: 주요 변경 시 관련 문서 즉시 업데이트
3. **명확성**: 기술적 내용을 명확하고 이해하기 쉽게 작성
4. **보안**: 민감한 정보(API 키, 비밀번호) 절대 포함 금지

---

**💡 Tip**: 문서를 읽기 전에 해당 문서의 목적과 대상을 확인하여 효율적으로 학습하세요!