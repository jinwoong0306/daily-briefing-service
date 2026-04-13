-- ==========================================
-- 1. 필수 확장 기능 및 기본 테이블 생성
-- ==========================================

-- AI 벡터 유사도 검색 및 크론(스케줄러) 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- 기사(Articles) 테이블: 뉴스 수집 및 AI 처리 상태 관리
CREATE TABLE IF NOT EXISTS public.articles (
    id bigserial PRIMARY KEY,
    url text UNIQUE NOT NULL,                       -- 중복 수집 방지
    title text NOT NULL,
    content text,
    pub_date timestamp with time zone NOT NULL,
    status smallint DEFAULT 0 CHECK (status IN (0, 1, 2)), -- 0:Pending, 1:Completed, 2:Failed
    retry_count int DEFAULT 0 CHECK (retry_count <= 3),    -- 최대 3회 재시도
    embedding vector(1536),                         -- OpenAI 임베딩용 (1536차원)
    created_at timestamp with time zone DEFAULT now()
);

-- 사용자 관심 키워드(User Keywords) 테이블
CREATE TABLE IF NOT EXISTS public.user_keywords (
    id bigserial PRIMARY KEY,
    user_id uuid NOT NULL,                          -- Supabase Auth 사용자 ID 연동
    keyword text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    UNIQUE(user_id, keyword)                        -- 중복 키워드 방지
);

-- ==========================================
-- 2. 성능 최적화 인덱스(Index) 설정
-- ==========================================

-- 요약 대기열 인덱스: Pending(status=0) 상태인 기사를 최신순으로 빠르게 조회
CREATE INDEX IF NOT EXISTS idx_articles_status_pending 
ON public.articles (pub_date DESC) WHERE status = 0;

-- AI 처리 실패 건 재시도 인덱스: 실패(status=2)했으나 재시도 횟수가 남은 기사 조회
CREATE INDEX IF NOT EXISTS idx_articles_retry_queue 
ON public.articles (retry_count, pub_date DESC) WHERE status = 2 AND retry_count < 3;

-- HNSW 벡터 인덱스: 고속 벡터 유사도 검색을 위한 인덱스 (Cosine 거리 기준)
CREATE INDEX IF NOT EXISTS idx_articles_embedding_hnsw 
ON public.articles USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=256);

-- ==========================================
-- 3. 운영 자동화 및 보안 정책(RLS)
-- ==========================================

-- 14일 경과 데이터 자동 삭제 스케줄: 매일 새벽 3시에 실행
SELECT cron.schedule('daily-cleanup-0300', '0 3 * * *', $$
    DELETE FROM public.articles WHERE pub_date < now() - interval '14 days';
$$);

-- Autovacuum 임계치 조정: 잦은 삽입/삭제가 발생하는 articles 테이블 성능 유지
ALTER TABLE public.articles SET (autovacuum_vacuum_scale_factor = 0.05);

-- RLS 보안 정책 활성화: 사용자가 본인의 키워드만 CRUD 할 수 있도록 제한
ALTER TABLE public.user_keywords ENABLE ROW LEVEL SECURITY;

-- 기존 정책이 있을 경우 삭제 후 재생성 (중복 방지)
DROP POLICY IF EXISTS policy_keywords_owner ON public.user_keywords;
CREATE POLICY policy_keywords_owner ON public.user_keywords
FOR ALL TO authenticated USING (auth.uid() = user_id);