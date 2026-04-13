# Daily Briefing Service

뉴스 Daily Briefing을 제공하는 모노레포 기반 멀티-플랫폼 서비스입니다.

## 📁 프로젝트 구조

이 프로젝트는 모노레포(Monorepo) 구조로 관리되며, 각 부분이 독립적으로 개발되고 통합됩니다.

```
daily-briefing-service/
├── apps/
│   └── mobile/              🚀 Flutter 모바일 앱 (iOS/Android)
│       ├── lib/             # Dart 소스 코드
│       ├── test/            # 테스트 코드
│       ├── android/         # Android 네이티브 설정 (로컬만)
│       ├── ios/             # iOS 네이티브 설정 (로컬만)
│       ├── pubspec.yaml     # Flutter 의존성
│       └── analysis_options.yaml
├── backend/                 🔧 Python 백엔드 (개발 예정)
│   ├── app/                 # 메인 API 서버
│   ├── crawler/             # 뉴스 크롤러
│   └── tests/               # 테스트
├── infra/                   ⚙️  배포 & 인프라 (개발 예정)
│   └── docs/
├── design/                  🎨 UI/UX 디자인 시스템
│   ├── Guide.md             # 디자인 가이드라인
│   └── ui/                  # 디자인 산출물
├── .github/                 # GitHub 설정
├── .gitignore
└── README.md
```

## 🎯 주요 기능

### 모바일 앱 (apps/mobile)
- 뉴스 피드 표시
- 키워드 기반 뉴스 필터링
- 설정 및 알림 관리
- 심플하고 직관적인 UI

### 백엔드 (backend) - TBD
- 뉴스 크롤링 및 수집
- 뉴스 데이터 API 제공
- 추천 알고리즘

### 배포 (infra) - TBD
- Docker 컨테이너화
- Kubernetes 오케스트레이션
- CI/CD 파이프라인

## 🚀 빠른 시작

### 모바일 앱 개발

#### 요구사항
- Flutter SDK 3.11.4 이상
- Dart 3.11.4 이상
- Android SDK 또는 iOS 개발 환경

#### 설치 및 실행

```bash
# 1. 프로젝트 디렉토리 이동
cd apps/mobile

# 2. 의존성 설치
flutter pub get

# 3. 코드 분석 및 검사
flutter analyze

# 4. 앱 실행
flutter run
```

## 📱 Android 에뮬레이터 가이드

### 1. 환경 확인
```bash
flutter doctor -v
```

### 2. 에뮬레이터 목록 확인
```bash
flutter emulators
```

### 3. 에뮬레이터 실행
```bash
flutter emulators --launch <emulator_id>
```

예시:
```bash
flutter emulators --launch Pixel_9_ASCII
```

### 4. 디바이스 연결 확인
```bash
adb devices -l
flutter devices
```

### 5. 앱 실행
```bash
cd apps/mobile
flutter pub get
flutter run -d emulator-5554
```

## 🔧 트러블슈팅

### adb devices에서 offline으로 나오는 경우
```bash
adb kill-server
adb start-server
Get-Process -Name emulator,qemu-system-x86_64,adb -ErrorAction SilentlyContinue | Stop-Process -Force
flutter emulators --launch <emulator_id>
adb devices -l
```

### Windows에서 Kotlin daemon 경로 오류
```bash
$env:GRADLE_USER_HOME='C:\gradle-cache'
cd apps/mobile
flutter run -d emulator-5554
```

### Flutter pub get 오류
```bash
cd apps/mobile
flutter clean
flutter pub get
```

## 📦 개발 안내

### 디렉토리 구조 설명

**apps/mobile/lib/**
```
lib/
├── main.dart              # 앱 진입점
├── core/
│   ├── router/           # 라우팅 설정
│   └── theme/            # 테마 & 색상
├── features/             # 기능별 모듈
│   ├── auth/             # 인증 관련
│   ├── briefing/         # 뉴스 피드 메인
│   ├── onboarding/       # 초기 설정
│   └── settings/         # 사용자 설정
└── shared/
    └── widgets/          # 공통 위젯
```

### 코드 스타일 가이드
- Dart 공식 코드 스타일 준수
- `flutter analyze` 정기적 실행
- Feature 단위의 모듈화 구조

### 버전 정보
- **Dart**: 3.11.4
- **Flutter**: 3.41.6
- **go_router**: 14.8.1
- **cupertino_icons**: 1.0.8

## 🔄 Git 워크플로우

### 브랜치 전략
- `main`: 프로덕션 배포
- `develop`: 개발 메인 브랜치
- `feature/*`: 새로운 기능 개발
- `bugfix/*`: 버그 수정
- `chore/*`: 구조/설정 변경

### 커밋 컨벤션
```
feat:  새로운 기능
fix:   버그 수정
refactor: 코드 리팩토링
chore: 설정/패키지 변경
docs:  문서 업데이트
test:  테스트 추가/수정
```

## 📚 문서

- [디자인 가이드](design/Guide.md) - UI/UX 디자인 시스템
- [Flutter 공식 문서](https://flutter.dev/docs)
- [Dart 공식 문서](https://dart.dev)

## 🤝 컨트리뷰션

1. 이슈 등록 또는 기존 이슈에 댓글
2. Fork 및 feature 브랜치 생성
3. 코드 작성 및 테스트
4. Pull Request 제출

## 📝 라이센스

[라이센스 정보]

## 👥 팀

- 개발: 프로젝트 팀

---

**최종 업데이트**: 2026-04-14
**상태**: 모바일 앱 개발 중 🔨
