# daily-briefing-service

☀️ **Daily Briefing: 나만의 아침 뉴스 비서**

매일 아침 08:00, 밤사이 핵심 뉴스를 AI가 요약하여 전달하는 스마트 뉴스 큐레이션 서비스

---

## 👥 팀원 및 역할 (Team Roles)
- 이종서: Team Leader / Backend (뉴스 수집 파이프라인, API 설계)
- 길현수: PM & AI Pipeline (LLM 프롬프트 엔지니어링, 요약 로직)
- 박재영: Frontend & UI/UX (Next.js 웹 서비스, 리포트 대시보드)
- 장진웅: Data/Infra & QA (DB 스키마 설계, Supabase 인프라 관리, 모니터링)

## 🛠 기술 스택 (Tech Stack)
- Framework: FastAPI (Backend), Next.js (Frontend)
- Database: PostgreSQL (Supabase - Seoul Region), pgvector
- AI/ML: OpenAI API (GPT-4o), LangChain
- Infra: Docker, Celery, Redis

---

## 📁 폴더 구조 (Repository Structure)
아래 구조를 기준으로 개발합니다.

```text
daily-briefing-service/ (Root)
├── .github/
│   └── workflows/
│       └── ci.yml                 # 자동화(CI) 설정
├── backend/                       # FastAPI 백엔드 관련 모든 것
│   ├── app/                       # API 비즈니스 로직
│   ├── crawler/                   # 뉴스 수집 스크립트
│   ├── tests/                     # 백엔드 테스트 코드
│   └── requirements.txt           # 백엔드 라이브러리 목록 (이 위치)
├── frontend/                      # 프론트엔드(웹/모바일/디자인)
│   ├── src/                       # (Web) 소스 코드
│   ├── public/                    # (Web) 정적 자산
│   ├── package.json               # (Web) 의존성 (추가/정리 시 이 위치)
│   ├── mobile/                    # Flutter 앱 소스
│   └── design/                    # 디자인 산출물
│       └── ui/                    # UI 산출물 (이전: infra/docs/ui)
├── infra/                         # 인프라 및 데이터베이스 설계
│   ├── supabase/                  # SQL/스키마 스크립트
│   └── docs/                      # 인프라/DB 문서 (디자인 제외)
├── .env.example                   # 환경변수 샘플 파일
└── README.md                      # 프로젝트 메인 설명서
```

> 참고: Flutter 앱은 `frontend/mobile/`, 디자인 산출물은 `frontend/design/ui/`에서 관리합니다.

---

## 🧩 `.github/` 폴더 정리 가이드
GitHub 관련 설정은 **모두 `.github/` 아래**에 모읍니다.

### 1) `.github/workflows/` (자동화)
- `ci.yml`: PR에서 빌드/린트 등 기본 검증
  - 현재 CI는 다음 파일이 있을 때만 job을 실행하도록 조건이 걸려 있습니다.
    - `backend/requirements.txt`가 있으면 `backend-ci` 실행
    - `frontend/package.json`이 있으면 `frontend-ci` 실행

권장 파일(필요 시 추가):
- `deploy.yml`: main 브랜치 배포용(추후)
- `scheduled.yml`: 매일 08:00 작업(크롤링/요약)용(추후)

### 2) PR/이슈 템플릿
협업 품질을 위해 템플릿을 추가하는 걸 권장합니다.
- PR 템플릿: `.github/PULL_REQUEST_TEMPLATE.md`
- 이슈 템플릿: `.github/ISSUE_TEMPLATE/` (GitHub Issue Forms: `*.yml`)

### 3) CODEOWNERS (선택)
리뷰 자동 할당이 필요하면 추가합니다.
- 위치: `.github/CODEOWNERS`
- 예: `backend/**`는 백엔드 담당, `frontend/**`는 프론트 담당에게 자동 리뷰 요청

### 4) Dependabot (선택)
의존성 자동 업데이트가 필요하면 추가합니다.
- 위치: `.github/dependabot.yml`

---

## 🌿 브랜치 전략 (Branch Strategy)
효율적인 협업을 위해 아래 규칙을 준수합니다.

```text
기본 개발 흐름
feature/*  →  develop  →  main
 (PR)         (PR)       (Release)

핫픽스 흐름 (긴급 버그/장애)
hotfix/*   →  main
 (PR)         (Deploy)
   └────→  develop  (동일 변경사항 backport)

예)
feature/news-crawler  →  develop  →  main
feature/ui-layout     →  develop  →  main
hotfix/login-crash    →  main  (+ develop backport)
```

- `main`: 상용 배포 가능한 최종 결과물 (안정화된 코드만)
- `develop`: 각 기능을 통합하여 테스트하는 개발 메인 브랜치
- `feature/기능명`: 단위 기능 구현을 위한 개별 브랜치
  - 예: `feature/db-setup`, `feature/news-crawler`, `feature/ui-layout`
- `hotfix/이슈명`: 운영 긴급 대응 브랜치
  - 예: `hotfix/login-crash`, `hotfix/api-timeout`

## 📝 Pull Request (PR) & 커밋 규칙
- PR 작성: 모든 작업은 `feature/*`에서 완료 후 `develop`으로 PR
- develop PR은 최소 **1명 이상의 팀원 승인(Approve)** 후 Merge
- `main` 머지는 **develop → main** 릴리즈 PR로만 진행 (핫픽스 제외)
- Commit Message 권장:
  - `[Feat]` 기능추가
  - `[Fix]` 버그수정
  - `[Docs]` 문서변경

---

## ⚙️ 초기 설정 (Environment)
로컬 개발 시 프로젝트 루트에 `.env` 파일을 만들고 아래 형식을 참조하세요.
(※ 실제 접속 키는 공유 보안 채널로 전달)

> ✅ `.env`는 커밋하지 않습니다. (`.env.example`만 유지)

```env
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.rrwsrnvkbciowolfjjvw.supabase.co:5432/postgres
OPENAI_API_KEY=sk-your-key-here
```

---

## 📱 Flutter (Mobile) 실행 가이드
Flutter 앱은 `frontend/mobile`에서 실행합니다.

```powershell
cd frontend/mobile
flutter doctor -v
flutter pub get
flutter run
```

### 트러블슈팅: `adb devices`에 `offline`으로 나오는 경우
```powershell
adb kill-server
adb start-server
Get-Process -Name emulator,qemu-system-x86_64,adb -ErrorAction SilentlyContinue | Stop-Process -Force
adb devices -l
```

### 트러블슈팅: Windows에서 Kotlin daemon 경로 오류
```powershell
$env:GRADLE_USER_HOME='C:\gradle-cache'
flutter run
```
