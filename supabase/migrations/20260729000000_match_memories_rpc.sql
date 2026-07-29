-- Story 5.4 파트 A: Memory RAG → Recommender 연동.
-- Recommender(service_role)가 후보 Signal 임베딩(query_embedding)으로 해당 사용자의
-- memories.embedding을 pgvector HNSW(코사인) 인덱스로 조회해 유사도를 산출한다.
--
-- 격리(AD-3/AD-9): Recommender는 service_role로 실행되어 memories RLS가 우회되므로,
-- 함수 본문에서 match_user_id 필터로 사용자 스코프를 명시적으로 강제한다(RLS 의존 금지).
-- 인덱스 정합: idx_memories_embedding이 vector_cosine_ops이므로 코사인 거리(<=>)를 사용해야
-- HNSW 인덱스가 활용된다(다른 연산자는 seq scan).
CREATE OR REPLACE FUNCTION public.match_memories(
    query_embedding vector(1536),
    match_user_id   uuid,
    match_count     int DEFAULT 5
)
RETURNS TABLE (
    id          uuid,
    summary     text,
    memory_type text,
    similarity  float
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT
        m.id,
        m.summary,
        m.memory_type,
        1 - (m.embedding <=> query_embedding) AS similarity
    FROM public.memories m
    WHERE m.user_id = match_user_id
      AND m.embedding IS NOT NULL
    ORDER BY m.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- 실행 권한: 파이프라인은 service_role로 호출. anon/authenticated는 이 RPC를 직접 호출할 수 없다.
REVOKE ALL ON FUNCTION public.match_memories(vector, uuid, int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.match_memories(vector, uuid, int) TO service_role;
