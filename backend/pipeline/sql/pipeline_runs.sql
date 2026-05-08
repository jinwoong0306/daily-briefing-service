-- 증분 수집 실행 이력 추적용 테이블
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
