-- Pipeline support schema for the Python news crawling / AI briefing pipeline.
-- Run after init_schema.sql, or merge these statements into the initial schema.

ALTER TABLE public.articles
ADD COLUMN IF NOT EXISTS keyword text,
ADD COLUMN IF NOT EXISTS source_type text;

ALTER TABLE public.articles
ALTER COLUMN created_at SET DEFAULT now();

ALTER TABLE public.articles
ALTER COLUMN retry_count SET DEFAULT 0;

ALTER TABLE public.articles
DROP CONSTRAINT IF EXISTS articles_retry_count_check;

ALTER TABLE public.articles
ADD CONSTRAINT articles_retry_count_check
CHECK (retry_count >= 0 AND retry_count <= 3);

CREATE TABLE IF NOT EXISTS public.pipeline_runs (
  id BIGSERIAL PRIMARY KEY,
  pipeline_name TEXT NOT NULL,
  window_start TIMESTAMPTZ NOT NULL,
  window_end TIMESTAMPTZ NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed')),
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_name_started
ON public.pipeline_runs (pipeline_name, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_name_status_ended
ON public.pipeline_runs (pipeline_name, status, window_end DESC);

CREATE TABLE IF NOT EXISTS public.user_push_tokens (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL,
  platform TEXT NOT NULL CHECK (platform IN ('ios', 'android')),
  token TEXT NOT NULL UNIQUE,
  enabled BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_push_tokens_user_enabled
ON public.user_push_tokens (user_id, enabled);

ALTER TABLE public.user_push_tokens ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS policy_push_tokens_owner ON public.user_push_tokens;
CREATE POLICY policy_push_tokens_owner
ON public.user_push_tokens
FOR ALL
TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);
