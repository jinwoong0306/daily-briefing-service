# News Crawling and AI Briefing Pipeline

This folder contains the scheduled Python pipeline for the Daily Briefing service.

## Flow

```text
Supabase user_keywords
-> news crawling
-> local staging cache
-> clustering
-> Supabase articles upload
-> AI selection and summary
-> Redis temporary briefing cache
-> push delivery boundary
```

## Setup

```bash
cd backend/pipeline
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r ../requirements.txt
cp .env.example .env
cp config.example.json config.json
```

Fill `.env` with server-only credentials. Do not commit `.env` or `config.json`.

Required values:

```env
OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
NAVER_CLIENT_ID="YOUR_NAVER_CLIENT_ID"
NAVER_CLIENT_SECRET="YOUR_NAVER_CLIENT_SECRET"
SUPABASE_URL="https://YOUR-PROJECT-REF.supabase.co"
SUPABASE_SERVICE_ROLE_KEY="YOUR_SUPABASE_SERVICE_ROLE_KEY"
REDIS_URL="rediss://default:YOUR_UPSTASH_TOKEN@YOUR_UPSTASH_HOST.upstash.io:6379"
THUMBNAIL_FETCH_TIMEOUT_SECONDS="5"
```

## Manual Run

```bash
cd backend/pipeline
source .venv/bin/activate
python main.py collect
python main.py finalize
python main.py brief
python main.py deliver
```

Mode summary:

```text
collect  : read Supabase user_keywords, crawl news, and append to cache/staging
finalize : cluster staged news and upload articles to Supabase
brief    : select/summarize articles with the configured AI model and save Redis briefings
deliver  : read user Redis briefings and run the app-push delivery boundary
```

## Redis Keys

```text
briefing:{YYYY-MM-DD}:keyword:{URL_ENCODED_KEYWORD}
briefing:{YYYY-MM-DD}:user:{USER_ID}
```

User-level keys are the recommended target for app APIs.

## Cron Example, KST

```cron
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
CRON_TZ=Asia/Seoul
PROJECT_DIR=/home/<WSL_USER>/daily-briefing-service/backend/pipeline
PYTHON_BIN=/home/<WSL_USER>/daily-briefing-service/backend/pipeline/.venv/bin/python

0 20,22 * * * /usr/bin/flock -n /tmp/news_main_pipeline.lock /bin/bash -lc 'cd "$PROJECT_DIR" && "$PYTHON_BIN" main.py collect >> "$PROJECT_DIR/logs/collect.log" 2>&1'
0 0,2,4,6 * * * /usr/bin/flock -n /tmp/news_main_pipeline.lock /bin/bash -lc 'cd "$PROJECT_DIR" && "$PYTHON_BIN" main.py collect >> "$PROJECT_DIR/logs/collect.log" 2>&1'
10 6 * * * /usr/bin/flock -n /tmp/news_main_pipeline.lock /bin/bash -lc 'cd "$PROJECT_DIR" && "$PYTHON_BIN" main.py finalize >> "$PROJECT_DIR/logs/finalize.log" 2>&1'
30 6 * * * /usr/bin/flock -n /tmp/news_main_pipeline.lock /bin/bash -lc 'cd "$PROJECT_DIR" && "$PYTHON_BIN" main.py brief >> "$PROJECT_DIR/logs/brief.log" 2>&1'
0 8 * * * /usr/bin/flock -n /tmp/news_main_pipeline.lock /bin/bash -lc 'cd "$PROJECT_DIR" && "$PYTHON_BIN" main.py deliver >> "$PROJECT_DIR/logs/deliver.log" 2>&1'
```

Create runtime directories before enabling cron:

```bash
mkdir -p logs cache/staging
```

## Redis Inspection

```bash
cd backend/pipeline
source .venv/bin/activate
python - <<'PY'
from redis_cache import get_redis_client, get_json
from datetime import datetime
from zoneinfo import ZoneInfo

date = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
client = get_redis_client()
print("Redis connected:", bool(client and client.ping()))

for key in sorted(client.scan_iter(f"briefing:{date}:keyword:*")):
    key = key.decode() if isinstance(key, bytes) else key
    data = get_json(key) or {}
    print("\nKEY:", key)
    print("keyword:", data.get("keyword"))
    print("candidate_count:", data.get("candidate_count"))
    print("selected_count:", data.get("selected_count"))
    print("summary_status:", data.get("summary_status"))
    print("summary:", data.get("summary"))
PY
```


## Thumbnail Fields

During `brief`, the pipeline fetches thumbnails only for AI-selected articles. It reads common article metadata such as `og:image`, `og:image:secure_url`, `twitter:image`, and `image_src`, then stores the result in Redis item payloads.

```json
{
  "title": "Article title",
  "url": "https://example.com/news",
  "thumbnail_url": "https://example.com/thumbnail.jpg",
  "thumbnail_status": "found"
}
```

`thumbnail_status` is one of `found`, `missing`, or `error`. If `thumbnail_url` is `null`, the app should display a default image.
