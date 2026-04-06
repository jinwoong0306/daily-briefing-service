# Daily Briefing 백엔드 실행 가이드 (FastAPI)

## 1) 백엔드 실행 방법

### 1-1. 백엔드 폴더로 이동

```bash
cd d:\news\daily-briefing-service\backend
```

### 1-2. 의존성 설치

```bash
python -m pip install -r requirements.txt
```

### 1-3. 환경 변수 확인

`backend/.env`에 Supabase 연결 문자열이 있어야 합니다.

예시:

```env
APP_ENV=prod
DATABASE_URL=postgresql+psycopg://postgres.<project-ref>:<password>@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres?sslmode=require
AUTO_CREATE_TABLES=false
```

### 1-4. 서버 실행

```bash
python -m uvicorn app.main:app --reload
```

실행 후 확인:

- [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- [http://127.0.0.1:8000/health/db](http://127.0.0.1:8000/health/db)

## 2) Flutter 앱 실행 방법 (에뮬레이터)

백엔드 서버를 먼저 켠 상태에서, **새 터미널**에서 실행합니다.

### 2-1. 프로젝트 루트로 이동

```bash
cd d:\news\daily-briefing-service
```

### 2-2. 패키지 설치

```bash
flutter pub get
```

### 2-3. 에뮬레이터 실행

```bash
flutter emulators --launch Pixel_7_API_36_1
```

### 2-4. 앱 실행

```bash
flutter run -d emulator-5554 --no-enable-impeller
```

## 3) 현재 구현된 API

- `GET /health`
- `GET /health/db`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/users/keywords` (Bearer 토큰 필요)
- `PUT /api/v1/users/keywords` (Bearer 토큰 필요)

## 4) 구현 범위 요약

- `BE-001`: FastAPI 기본 서버, 라우터 구조, 헬스체크
- `BE-002`: Supabase(Postgres) 전용 DB 연결
- `US-001`: 이메일 회원가입/로그인, 토큰 발급
- `US-003`: 사용자 키워드 저장/조회/수정
