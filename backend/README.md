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
- `POST /api/v1/auth/token` (Swagger Authorize OAuth2 password flow 전용)
- `GET /api/v1/users/keywords` (Bearer 토큰 필요)
- `PUT /api/v1/users/keywords` (Bearer 토큰 필요)
- `GET /api/v1/users/notifications` (Bearer 토큰 필요)
- `PUT /api/v1/users/notifications` (Bearer 토큰 필요)

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
- `BE-003`: 키워드/알림 설정 조회·수정 API + 인증 스코프 검증
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
