# daily-briefing-service
# ☀️ Daily Briefing: 나만의 아침 뉴스 비서
> 매일 아침 08:00, 밤사이 핵심 뉴스를 AI가 요약하여 전달하는 스마트 뉴스 큐레이션 서비스

---

## 👥 팀원 및 역할 (Team Roles)
- **이종서**: Team Leader / Backend (뉴스 수집 파이프라인, API 설계)
- **길현수**: PM & AI Pipeline (LLM 프롬프트 엔지니어링, 요약 로직)
- **박재영**: Frontend & UI/UX (Next.js 웹 서비스, 리포트 대시보드)
- **장진웅**: Data/Infra & QA (DB 스키마 설계, Supabase 인프라 관리, 모니터링)

## 🛠 기술 스택 (Tech Stack)
- **Framework**: FastAPI (Backend), Next.js (Frontend)
- **Database**: PostgreSQL (Supabase - Seoul Region), pgvector
- **AI/ML**: OpenAI API (GPT-4o), LangChain
- **Infra**: Docker, Celery, Redis

---

## 🌿 브랜치 전략 (Branch Strategy)
효율적인 협업을 위해 아래와 같은 브랜치 규칙을 준수합니다.

1. **`main`**: 상용 배포 가능한 최종 결과물 (안정화된 코드만)
2. **`develop`**: 각 기능을 통합하여 테스트하는 개발 메인 브랜치
3. **`feature/기능명`**: 단위 기능 구현을 위한 개별 브랜치
   - 예: `feature/db-setup`, `feature/news-crawler`, `feature/ui-layout`

## 📝 Pull Request (PR) & 커밋 규칙
- **PR 작성**: 모든 작업은 `feature/` 브랜치에서 완료 후 `develop`으로 PR을 보냅니다.
- **코드 리뷰**: 최소 **1명 이상의 팀원 승인(Approve)**이 있어야 Merge가 가능합니다.
- **Commit Message**: `[Feat] 기능추가`, `[Fix] 버그수정`, `[Docs] 문서변경` 형식을 권장합니다.

---

## ⚙️ 초기 설정 (Environment)
백엔드 개발 시 프로젝트 루트에 `.env` 파일을 생성하고 아래 형식을 참조하세요.
(※ 실제 접속 키는 공유 보안 채널을 통해 전달합니다.)

```env
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.rrwsrnvkbciowolfjjvw.supabase.co:5432/postgres
OPENAI_API_KEY=sk-your-key-here
