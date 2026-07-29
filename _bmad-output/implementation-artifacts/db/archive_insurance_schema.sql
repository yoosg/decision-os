-- ============================================================
-- Decision OS — Insurance Playbook Schema (보관용)
-- 원본: 001_initial_schema.sql (2026-07-22 이전)
-- 보관 이유: MVP가 AI Research Playbook으로 전환됨.
--            Insurance Playbook 구현 시 참고용으로 보존.
-- ============================================================

-- ============================================================
-- Insurance Playbook Tables (AD-4)
-- ============================================================

-- 보험 계약
CREATE TABLE IF NOT EXISTS public.insurance_policies (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id          UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    insurer_name        TEXT NOT NULL,
    product_name        TEXT NOT NULL,
    policy_number       TEXT,
    policy_type         TEXT NOT NULL
                            CHECK (policy_type IN ('life', 'health', 'auto', 'fire', 'other')),
    premium_amount      BIGINT,
    premium_cycle       TEXT
                            CHECK (premium_cycle IN ('monthly', 'quarterly', 'annual')),
    coverage_start_date DATE,
    coverage_end_date   DATE,
    coverage_details    JSONB,
    raw_document_url    TEXT,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 보험 청구 이력
CREATE TABLE IF NOT EXISTS public.insurance_claims (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    policy_id       UUID REFERENCES public.insurance_policies(id) ON DELETE SET NULL,
    review_id       UUID REFERENCES public.reviews(id)            ON DELETE SET NULL,
    claim_date      DATE NOT NULL,
    hospital_name   TEXT,
    diagnosis_code  TEXT,
    treatment_type  TEXT
                        CHECK (treatment_type IN ('입원', '외래', '처방')),
    receipt_amount  BIGINT,
    claimed_amount  BIGINT,
    received_amount BIGINT,
    status          TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'submitted', 'approved', 'rejected', 'skipped')),
    receipt_url     TEXT,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 보험 문서 (메타데이터 + 원문 전체) — Chunk와 분리
CREATE TABLE IF NOT EXISTS public.insurance_documents (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id     UUID NOT NULL REFERENCES public.projects(id)           ON DELETE CASCADE,
    policy_id      UUID REFERENCES public.insurance_policies(id)          ON DELETE CASCADE,
    document_type  TEXT NOT NULL
                       CHECK (document_type IN ('policy_terms', 'receipt', 'claim_form', 'other')),
    file_url       TEXT NOT NULL,
    file_name      TEXT NOT NULL,
    parsed_content TEXT,            -- OCR / LLM 파싱 원문 (청킹 전 전체 텍스트)
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 보험 문서 청크 (RAG 벡터 검색 대상) — 문서 메타데이터와 분리
CREATE TABLE IF NOT EXISTS public.insurance_document_chunks (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES public.insurance_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content     TEXT NOT NULL,
    embedding   VECTOR(1536),       -- OpenAI text-embedding-3-small
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (document_id, chunk_index)
);

-- ============================================================
-- Indexes (Insurance)
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_ins_policies_project   ON public.insurance_policies(project_id);
CREATE INDEX IF NOT EXISTS idx_ins_claims_project     ON public.insurance_claims(project_id);
CREATE INDEX IF NOT EXISTS idx_ins_claims_policy      ON public.insurance_claims(policy_id);
CREATE INDEX IF NOT EXISTS idx_ins_claims_review      ON public.insurance_claims(review_id);
CREATE INDEX IF NOT EXISTS idx_ins_docs_project       ON public.insurance_documents(project_id);
CREATE INDEX IF NOT EXISTS idx_ins_docs_policy        ON public.insurance_documents(policy_id);
CREATE INDEX IF NOT EXISTS idx_ins_chunks_document    ON public.insurance_document_chunks(document_id);

CREATE INDEX IF NOT EXISTS idx_ins_chunks_embedding
    ON public.insurance_document_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ============================================================
-- RLS (Insurance)
-- ============================================================

ALTER TABLE public.insurance_policies        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.insurance_claims          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.insurance_documents       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.insurance_document_chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "ins_policies_own" ON public.insurance_policies
    USING (EXISTS (
        SELECT 1 FROM public.projects p WHERE p.id = project_id AND p.user_id = auth.uid()
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.projects p WHERE p.id = project_id AND p.user_id = auth.uid()
    ));

CREATE POLICY "ins_claims_own" ON public.insurance_claims
    USING (EXISTS (
        SELECT 1 FROM public.projects p WHERE p.id = project_id AND p.user_id = auth.uid()
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.projects p WHERE p.id = project_id AND p.user_id = auth.uid()
    ));

CREATE POLICY "ins_documents_own" ON public.insurance_documents
    USING (EXISTS (
        SELECT 1 FROM public.projects p WHERE p.id = project_id AND p.user_id = auth.uid()
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.projects p WHERE p.id = project_id AND p.user_id = auth.uid()
    ));

CREATE POLICY "ins_chunks_select" ON public.insurance_document_chunks FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.insurance_documents d
        JOIN public.projects p ON p.id = d.project_id
        WHERE d.id = document_id AND p.user_id = auth.uid()
    ));

-- ============================================================
-- Triggers (Insurance)
-- ============================================================

CREATE TRIGGER trg_insurance_policies_updated_at
    BEFORE UPDATE ON public.insurance_policies
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TRIGGER trg_insurance_claims_updated_at
    BEFORE UPDATE ON public.insurance_claims
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ============================================================
-- Storage Buckets (Insurance)
-- 대시보드 또는 API로 별도 생성
-- bucket: receipts         (영수증 원본, private)
-- bucket: policy-documents (보험증서, private)
-- ============================================================

-- ============================================================
-- decisions.choice (Insurance 기준)
-- CHECK (choice IN ('accept', 'postpone', 'ignore'))
--
-- outcomes.status (Insurance 기준)
-- CHECK (status IN ('approved', 'partial', 'rejected', 'cancelled', 'pending'))
-- 컬럼: description TEXT, amount_received BIGINT, satisfaction SMALLINT
--
-- memories.memory_type (Insurance 기준)
-- CHECK (memory_type IN ('decision_pattern', 'preference', 'outcome_insight', 'context'))
-- ============================================================
