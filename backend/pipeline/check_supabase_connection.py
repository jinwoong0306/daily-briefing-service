"""
Supabase 연결 체크 스크립트

사용:
  python check_supabase_connection.py
"""

import os
import sys

from supabase_uploader import get_supabase_client


def main() -> int:
    client = get_supabase_client()
    if client is None:
        print("❌ Supabase 연결 정보가 없습니다. (.env의 SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY 확인)")
        return 1

    table_name = os.environ.get("SUPABASE_ARTICLES_TABLE", "articles").strip() or "articles"

    try:
        res = client.table(table_name).select("url", count="exact").limit(1).execute()
        count = res.count if hasattr(res, "count") else "unknown"
        print(f"✅ Supabase 연결 성공 (table={table_name}, count={count})")
        return 0
    except Exception as e:
        print(f"❌ Supabase 연결 실패: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
