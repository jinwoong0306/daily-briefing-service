# Daily Briefing 백엔드 실행 가이드 (FastAPI)

## 빠른 실행 순서 (권장)

아래 4개만 순서대로 실행하면 됩니다.

1. 터미널 A(백엔드):

```bash
cd d:\news\daily-briefing-service\backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

2. 터미널 B(앱):

```bash
cd d:\news\daily-briefing-service
flutter pub get
flutter emulators --launch Pixel_7_API_36_1
copy frontend.env.example frontend.env
flutter run -d emulator-5554 --no-enable-impeller --dart-define-from-file=frontend.env
```

3. 점검 URL:
- [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- [http://127.0.0.1:8000/health/db](http://127.0.0.1:8000/health/db)

4. Gemini 한줄요약 사용 전 확인:
- `frontend.env`에 `GEMINI_API_KEY=<실제키>` 입력
- 앱은 반드시 `--dart-define-from-file=frontend.env` 옵션으로 실행
- 이미 실행 중이었다면 앱을 완전히 종료 후 재실행

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
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<supabase-anon-key>
```

`backend/.env`는 서버 전용 설정 파일입니다.  
`DATABASE_URL`, `JWT_SECRET_KEY` 같은 서버 비밀값은 Flutter 실행 옵션으로 넘기지 않습니다.

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

### 2-2-1. Flutter 런타임 환경파일 준비

```bash
copy frontend.env.example frontend.env
```

`frontend.env`에는 아래 항목을 넣습니다.

```env
API_BASE_URL=http://10.0.2.2:8000/api/v1
GEMINI_API_KEY=<실제 Gemini API 키>
GEMINI_MODEL=gemini-2.5-flash
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<supabase-anon-key>
```

### 2-3. 에뮬레이터 실행

```bash
flutter emulators --launch Pixel_7_API_36_1
```

### 2-4. 앱 실행

```bash
flutter run -d emulator-5554 --no-enable-impeller --dart-define-from-file=frontend.env
```

`Gemini` 한줄요약 사용 시 `frontend.env`의 `GEMINI_API_KEY`가 반드시 필요합니다.

## 3) 현재 구현된 API

- `GET /health`
- `GET /health/db`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/google/supabase`
- `POST /api/v1/auth/token` (Swagger Authorize OAuth2 password flow 전용)
- `GET /api/v1/briefings/today`
- `GET /api/v1/briefings/today/grouped` (Redis 사용자 브리핑 원본 구조 조회)
- `GET /api/v1/ingest/redis/keys` (Bearer 토큰 필요)
- `POST /api/v1/ingest/redis/pull?key=<redis-key>&limit=50` (Bearer 토큰 필요)
- `POST /api/v1/ingest/redis/pull/batch?match=briefing:*&per_key_limit=30&max_keys=10` (Bearer 토큰 필요)
- `GET /api/v1/users/keywords` (Bearer 토큰 필요)
- `PUT /api/v1/users/keywords` (Bearer 토큰 필요)
- `GET /api/v1/users/notifications` (Bearer 토큰 필요)
- `PUT /api/v1/users/notifications` (Bearer 토큰 필요)
- `GET /api/v1/users/profile` (Bearer 토큰 필요)

## 3-1) Redis 뉴스 적재 연동

`backend/.env`에 아래 값을 넣습니다.

```env
REDIS_URL=redis://default:<password>@<host>:6379
REDIS_SCAN_COUNT=200
INGEST_ADMIN_EMAILS=admin1@example.com,admin2@example.com
INGEST_SCHEDULER_ENABLED=true
INGEST_SCHEDULER_INTERVAL_MINUTES=5
INGEST_BATCH_MATCH=briefing:*
INGEST_BATCH_PER_KEY_LIMIT=30
INGEST_BATCH_MAX_KEYS=10
```

- `INGEST_ADMIN_EMAILS`가 설정된 경우, 해당 이메일 사용자만 ingest API를 호출할 수 있습니다.
- `INGEST_SCHEDULER_ENABLED=true`면 서버 실행 중 배치 적재가 주기적으로 자동 수행됩니다.

사용 순서:

1. 로그인으로 `access_token` 발급
2. Redis 키 목록 확인

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/ingest/redis/keys" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

3. 확인된 키를 `articles` 테이블로 적재

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/ingest/redis/pull?key=<REDIS_KEY>&limit=50" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

4. 패턴 기반 일괄 적재 (권장)

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/ingest/redis/pull/batch?match=briefing:*&per_key_limit=30&max_keys=10" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

- `match`: 스캔할 Redis 키 패턴
- `per_key_limit`: 키별로 읽을 최대 레코드 수
- `max_keys`: 한 번에 처리할 최대 키 개수

## 4) 실패 응답 포맷 표준

모든 실패 응답은 다음 형식으로 반환됩니다.

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": []
  }
}
```

- `error.code`: 오류 유형 (`UNAUTHORIZED`, `CONFLICT`, `VALIDATION_ERROR` 등)
- `error.message`: 사용자 친화적인 오류 메시지
- `error.details`: 유효성 검증 실패 시 필드별 상세 정보

## 5) 요청/응답 샘플

### 5-1. 회원가입

요청:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"user1@example.com\",\"password\":\"password123\",\"name\":\"User One\"}"
```

응답:

```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user1@example.com",
    "name": "User One",
    "created_at": "2026-04-05T12:00:00Z"
  }
}
```

### 5-2. 로그인

요청:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"user1@example.com\",\"password\":\"password123\"}"
```

### 5-3. 키워드 조회/수정

조회:

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/users/keywords" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

수정:

```bash
curl -X PUT "http://127.0.0.1:8000/api/v1/users/keywords" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d "{\"keywords\":[\"AI\",\"Tech\",\"Economy\"]}"
```

### 5-4. 알림 설정 조회/수정

조회:

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/users/notifications" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

수정:

```bash
curl -X PUT "http://127.0.0.1:8000/api/v1/users/notifications" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d "{\"enabled\":true,\"delivery_hour\":8,\"delivery_minute\":30,\"timezone\":\"Asia/Seoul\"}"
```

- `delivery_hour`는 **7~12(오전)** 만 허용됩니다. (밤 사이 수집된 뉴스를 오전 브리핑으로만 전달)

## 6) 토큰 발급/검증 로그 확인

아래 명령으로 서버 로그에서 토큰 발급/검증 관련 로그를 확인할 수 있습니다.

```bash
python -m uvicorn app.main:app --reload --log-level info
```

로그 예시:

- `Issued access token for user_id=1 via register`
- `Issued access token for user_id=1 via login`
- `Validated access token for user_id=1`

## 7) 기본 API 테스트 실행

```bash
python -m pytest -q
```

## 8) 구현 범위 요약

- `BE-001`: FastAPI 기본 서버, 라우터 구조, 헬스체크
- `BE-002`: Supabase(Postgres) 전용 DB 연결
- `BE-004`: 키워드/알림 설정 조회·수정 API, 사용자 프로필 조회 API + 인증 스코프 검증
- `US-001`: 이메일 회원가입/로그인, 토큰 발급
- `US-003`: 사용자 키워드 저장/조회/수정

## 9) 비기능(NFR) 구현 내역

### 9-1. 인증 보안/성능

- `JWT` 유효기간: 기본 7일 (`ACCESS_TOKEN_EXPIRE_MINUTES=10080`)
- 토큰 검증 성능 로그: 검증 시 `elapsed_ms`, `avg_ms`, `p95_ms`를 함께 기록
- 로그인 무차별 대입 방지: 동일 `IP + 이메일` 기준 분당 10회 제한(초과 시 `429`)

관련 로그 예시:

- `Validated access token for user_id=7 (elapsed_ms=5.21, avg_ms=7.43, p95_ms=12.80)`
- `Token validation exceeded 50ms threshold: 73.10ms`
- `Too many login attempts. Try again in a minute.`

### 9-2. 설정 API 성능

- 설정 캐시 TTL: 5분 (`CACHE_TTL_SECONDS=300`)
  - `GET /users/keywords`, `GET /users/notifications` 응답 캐시
  - 설정 변경(`PUT`) 시 캐시 무효화
- 설정 변경 API 성능 로그: `elapsed_ms`, `avg_ms`, `p95_ms` 기록
  - 키워드: `Settings update metrics (keywords) ...`
  - 알림설정: `Settings update metrics (notifications) ...`
- 동시 수정 충돌 방지(낙관적 락)
  - `GET` 응답의 `version`을 `PUT`의 `expected_version`으로 전달
  - 불일치 시 `409 CONFLICT` 반환

## 10) NFR 증적 수집 방법

### JWT payload(exp) 캡처

```bash
python - <<'PY'
import base64, json
token = "여기에_발급된_access_token"
payload = token.split(".")[1]
payload += "=" * (-len(payload) % 4)
print(json.dumps(json.loads(base64.urlsafe_b64decode(payload)), indent=2))
PY
```

### 토큰 검증 평균/95%ile 로그

- 서버 로그에서 `Validated access token ... avg_ms=... p95_ms=...` 라인 캡처

### Rate limit 차단 로그

- 같은 계정으로 로그인 실패를 연속 시도해 `429 TOO_MANY_REQUESTS` 응답 캡처

### 설정 API 응답시간 로그

- `PUT /users/keywords`, `PUT /users/notifications` 호출 후
  `Settings update metrics (...) elapsed_ms=... avg_ms=... p95_ms=...` 로그 캡처

### 캐시 TTL 설정 캡처

- `.env` 또는 설정값(`CACHE_TTL_SECONDS=300`) + 코드(`TTLCache`) 화면 캡처

### 동시 수정 충돌 테스트 로그

- 최신 `version` 없이 또는 오래된 `expected_version`으로 `PUT` 호출 시
  `409 CONFLICT` 응답 캡처

## 11) 배포 전 체크리스트

- `JWT_SECRET_KEY`를 기본값(`change-this-secret-in-production`)에서 강한 랜덤 값으로 교체
- `INGEST_ADMIN_EMAILS`를 실제 운영 관리자 계정으로 설정
- `INGEST_SCHEDULER_ENABLED=true`일 때 주기/배치량이 인프라 한도 내인지 점검
  - 기본 권장값: `INGEST_SCHEDULER_INTERVAL_MINUTES=5`, `INGEST_BATCH_PER_KEY_LIMIT=30`, `INGEST_BATCH_MAX_KEYS=10`
- 서버 프로세스는 하나만 실행해서 중복 스케줄러 실행을 방지
- Flutter는 `frontend.env`만 주입하고 `backend/.env`(서버 비밀값)는 클라이언트에 전달하지 않기
