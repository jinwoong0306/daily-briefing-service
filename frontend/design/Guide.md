# Frontend Implementation Guide

## 1. 기술 스택 및 환경
- Flutter 버전: `3.41.6`
- Dart 버전: `3.11.4`
- 타깃 플랫폼: Android 우선 (모바일 퍼스트), 이후 Web/Desktop은 레이아웃 확장 대응

현재 `pubspec.yaml` 기준 의존성:
- `flutter` (SDK): 기본 UI 프레임워크
- `cupertino_icons`: iOS 스타일 아이콘 지원

사용 예정 패키지 목록(선정 이유):
- `go_router`: 화면 전환/딥링크 대응 가능한 선언형 라우팅
- `google_fonts`: UI 시안의 `Manrope`, `Inter` 타이포 즉시 반영
- `intl`: 날짜/시간(예: "좋은 아침", 브리핑 날짜, 시간 포맷) 지역화 처리
- `flutter_riverpod`: 온보딩 선택 상태, 탭 상태, 피드/피드백 UI 상태 분리
- `cached_network_image`: 피드 썸네일 로딩 UX 개선(placeholder/error 처리)
- `flutter_svg`: 아이콘/일러스트 SVG 에셋 대응
- `flutter_animate`: 과한 모션 없이 카드/버튼/탭 전환 애니메이션 일관화

## 2. 디자인 시스템
- `UI/` 폴더 전체(`.md`, `.html`, `.png`) 분석 기준으로 도출

컬러 팔레트(핵심 토큰):
- Primary 계열
  - `#0064FF`, `#0051D2`, `#004ECB`
  - Deep Navy Accent: `#000666`, `#1A237E`
  - Primary Container: `#7A9DFF`
- Neutral/Surface 계열
  - Aura Surface: `#F8F5FF`, `#F1EFFF`, `#E7E6FF`, `#D9DAFF`, `#E0E0FF`
  - White Editorial Surface: `#FFFFFF`, `#F9F9F9`, `#F3F3F4`, `#EEEEEE`, `#E8E8E8`, `#E2E2E2`
  - Text: `#282B51`, `#1A1C1C`, Secondary Text: `#555881`, `#424656`
  - Outline Variant(저강도): `#A7AAD7`, `#C2C6D8`
- Secondary/Tertiary
  - Secondary: `#4650B7`, `#425BA0`
  - Secondary Container: `#CBCEFF`
  - Tertiary Accent: `#8D3A8A`, Editorial Warm Accent: `#A03200`
- Error
  - `#B31B25`, `#BA1A1A`, Error Container: `#FFDAD6`/`#FB5151`

그라디언트 규칙:
- Signature/Aura Gradient: `135deg`, `#0051D2 -> #7A9DFF`
- Deep Gradient Variant: `135deg`, `#000666 -> #1A237E`

폰트/타이포그래피 규칙:
- Headline/Display: `Manrope` (Bold/ExtraBold 중심)
- Body/Label: `Inter` 또는 `Manrope` (시안별 혼용, 구현은 `Manrope 우선 + Inter 보조`)
- 권장 스케일
  - Display LG: 48~56
  - Headline LG: 32
  - Title: 20~24
  - Body: 16 (line-height 1.5~1.6)
  - Label: 10~12 (대문자/트래킹 증가)

공통 컴포넌트 목록:
- 버튼: Primary(그라디언트/솔리드), Secondary(저강도 톤), Tertiary(Text)
- 피드 카드: 키워드 태그 + 제목 + 3줄 요약 + 원문 액션
- 칩/토글: 관심 키워드 선택, 선택 상태 강조
- 탭/세그먼트: `전체/IT/경제/...` 수평 스크롤
- 피드백 카드: Helpful/Not for me, 추가 코멘트 textarea
- 시간 선택 UI: AM/PM + 시/분 카드형 피커
- Empty State 블록: 메시지 + 대체 탐색 CTA
- 하단 네비게이션: Home/Explore/Saved/Settings
- 상단 앱바: 브랜드 + 검색/프로필/설정

레이아웃/간격 규칙:
- 모바일 기본 좌우 패딩: 24~32px
- 섹션 간격: 24/32/40px 계층화
- 카드 라운드: 16~32px
- 1px divider 지양, 배경 톤 차/공백으로 구획
- 필요 시 Glassmorphism: `surface 70~80% + blur 20px`

반응형 레이아웃 전략:
- Mobile-first (`360x800`~`430x932`) 기준 설계
- `>=600`: 2열 또는 상세+보조 패널 분리
- `>=1024`: 상단 탭 + 사이드 내비/보조 패널 확장
- 텍스트/카드 밀도는 화면 폭 증가 시 컬럼/간격으로 조정, 폰트 급격 확장 금지

## 3. 폴더 구조 설계
```text
lib/
├── main.dart
├── core/           ← 상수, 테마, 라우터
├── features/       ← 기능별 모듈 (auth, briefing, settings 등)
│   └── [feature]/
│       ├── screens/
│       ├── widgets/
│       └── models/
├── shared/         ← 공통 위젯, 유틸리티
└── services/       ← API 호출 추상화 레이어
```

권장 feature 분리:
- `features/auth/`: 로그인/회원가입
- `features/onboarding/`: 키워드 + 시간 설정
- `features/briefing/`: 메인 피드/상세/피드백/빈 상태
- `features/settings/`: 수신/알림/키워드 상세 설정

## 4. 구현 단계별 계획 (백로그 기반)

### Step 1 — 기반 구축
- 프로젝트 초기 설정 (패키지, 테마, 라우터)
- 로그인/회원가입 화면 (US-001, US-002 연동 준비)
- 온보딩 키워드 선택 화면 (US-003)

산출물:
- 앱 전역 Theme(색상/타이포/컴포넌트 토큰)
- 기본 라우팅 스켈레톤
- Auth/Onboarding 핵심 화면 UI 및 목업 상태 연결

### Step 2 — 메인 피드
- 메인 브리핑 피드 기본 UI (UI-001)
- 브리핑 상세 뷰 (UI-002)
- 기본 피드백 버튼 (UI-004)

산출물:
- 카드형 피드 리스트, 카테고리 탭, 원문 CTA
- 상세 뷰 정보 구조 + 피드백 인라인 액션

### Step 3 — 알림 및 설정
- 브리핑 수신 기본 설정 화면 (US-004)
- FCM 기본 알림 UI 연동 (UI-003)

산출물:
- 수신 시간/빈도/토픽 설정 UI
- 알림 권한 상태/가이드 UI(플랫폼 분기 포함)

### Step 4 — 고급 기능 (P2)
- 무한 스크롤 + 풀투리프레시 (IMP-007)
- 저장/공유/관련 기사 추천 UI (IMP-008)
- 키워드 상세 설정 (IMP-002)
- 알림 시간 상세 설정 (IMP-003)

산출물:
- 리스트 확장 UX, 저장/공유 진입, 추천 카드 모듈
- 상세 토픽/시간 커스터마이징

## 5. 인수 조건 매핑
- Step 1
  - AC-US-001: 로그인 화면 기본 입력/액션 UI 제공
  - AC-US-002: 회원가입 화면 및 검증 상태 UI 제공
  - AC-US-003: 키워드 다중선택 + 최소 선택 가이드 + 시간 선택 UI 제공
- Step 2
  - AC-UI-001: 메인 피드에서 카테고리별 카드 리스트 확인 가능
  - AC-UI-002: 브리핑 상세에서 제목/요약/원문 액션 노출
  - AC-UI-004: Helpful/Not for me 피드백 UI 상호작용 가능
- Step 3
  - AC-US-004: 기본 수신설정(시간/상태) 화면에서 변경 가능
  - AC-UI-003: 알림 관련 UI(권한/상태/안내) 접근 가능
- Step 4
  - AC-IMP-007: 풀투리프레시/추가 로딩 상태 시각 피드백 제공
  - AC-IMP-008: 저장/공유/관련기사 추천 UI 진입 가능
  - AC-IMP-002: 키워드 상세 설정(추가/삭제/우선순위) 가능
  - AC-IMP-003: 알림 시간 상세 옵션(요일/시간대) 설정 가능

## 6. 주요 의존성 및 API 연동 전략
- Mock 데이터 우선 개발 후 백엔드 API 연결 전략
  - 초기 단계는 feature별 로컬 JSON/더미 모델로 화면 완성
  - 상태별(로딩/성공/빈 상태/에러) UI를 먼저 고정
  - API 연결 시 `services/` 레이어만 교체하고 화면 위젯 구조는 유지
- BE-005 (`GET /api/v1/briefings/today`) 연동 준비 방식
  - `services/briefing_service.dart` 인터페이스 선구현
  - 응답 모델 매핑 클래스(`briefing_model.dart`) 사전 정의
  - Mock -> Real 전환 시 파서/에러 핸들링만 교체
  - 캐시 정책(당일 브리핑)과 빈 응답(empty state) UI 분기 유지

## 7. 성능 목표
- 초기 로딩 < 2초 (3G 기준)
- 스크롤 60fps 유지
- 애니메이션 전환 지연 < 100ms

