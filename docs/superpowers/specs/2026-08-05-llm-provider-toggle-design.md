# LLM 프로바이더 토글 (OpenAI ↔ Gemini) — 설계 스펙

- 날짜: 2026-08-05
- 상태: 설계 승인됨 (구현 계획 대기)
- 배경: OpenAI 크레딧 소진(429 insufficient_quota)으로 daily brief 파이프라인의 `build_signals`
  단계가 전부 실패 → 오늘(2026-08-05) 신호 41개가 `raw`에 멈춤. 테스트용으로 Gemini 프리티어를
  쓸 수 있도록 LLM 텍스트 생성 경로를 프로바이더 토글 가능하게 만든다.

## 목표 / 비목표

**목표**
- `LLM_PROVIDER` 플래그 하나로 OpenAI ↔ Gemini를 토글한다.
- 텍스트 생성 6개 메서드(`generate`, `build_signal_title_summary`, `chat`,
  `generate_learning_path`, `extract_memory`)를 Gemini로도 수행할 수 있게 한다.
- Gemini 프리티어 rate-limit(429)에서 살아남도록 재시도/백오프를 넣는다.
- 프로바이더 생성 지점을 팩토리 한 곳으로 통일한다.

**비목표 (이번 범위 아님)**
- 임베딩 프로바이더 전환 — 임베딩은 **항상 OpenAI 유지**(아래 결정 참조).
- `memories.embedding` 벡터 재임베딩/DB 마이그레이션.
- OpenAI Responses API 사용 규칙(AD-6) 변경.

## 핵심 결정

1. **토글 범위 = 텍스트 생성만.** 임베딩(`embed_text`)은 항상 OpenAI로 위임한다.
   - 이유: `memories.embedding`은 `vector(1536)`이고 기존 메모리가 전부 OpenAI 임베딩 공간에
     저장돼 있다. Gemini 임베딩은 좌표계가 달라(코사인 유사도 비교 불가) 섞으면 RAG 품질이
     깨진다. 임베딩 실패는 기존 **콜드스타트 폴백**으로 안전 저하되므로 브리핑 생성은 지속된다.
2. **Gemini 기본 모델 = `gemini-2.5-flash`** (env `GEMINI_MODEL`로 변경 가능).
3. **프리티어 전용.** rate-limit 방어(재시도/백오프 + 선택적 throttle)를 필수로 포함.
4. **프롬프트·검증 로직은 공유 모듈로 추출**해 두 프로바이더가 재사용한다(드리프트 방지).

## 아키텍처

```
settings.llm_provider ("openai" | "gemini")
        │
   get_llm_provider()            # pipeline/llm/factory.py (신규)
        ├─ "openai" → OpenAIProvider(api_key, model, embedding_model)
        └─ "gemini" → GeminiProvider(
                          gemini_api_key, gemini_model,
                          openai_api_key, embedding_model)  # 임베딩용 OpenAI 키 함께 주입
```

- 현재 `OpenAIProvider(...)`를 직접 생성하는 7개 호출부를 모두 `get_llm_provider()` 호출로 교체:
  `routers/chat.py`, `pipeline/coach.py`, `pipeline/reviewer.py`,
  `pipeline/orchestrator.py`(2곳), `pipeline/memory_manager.py`,
  그리고 일회성 `_resume_brief_2026_08_05.py`.
- 토글 지점이 팩토리 한 곳으로 통일된다.

### GeminiProvider

- SDK: `google-genai` (`from google import genai`).
- 텍스트 생성: `client.models.generate_content(model, contents, config=...)`
  - JSON 메서드: `config`에 `system_instruction` + `response_mime_type="application/json"` 지정
    → 마크다운 코드펜스 없는 순수 JSON 수신(OpenAI의 "input에 json 단어" 꼼수 불필요).
  - `chat`(비-JSON): `system_instruction`만, `response_mime_type` 미지정.
- 파싱/검증은 공유 헬퍼 재사용:
  - `generate`: 13개 `REQUIRED_SECTIONS` 존재 검사.
  - `generate_learning_path`: `resources` 길이 5 + 각 항목 키/URL 스킴 검증.
  - `extract_memory`: `memory_type`이 `ALLOWED_MEMORY_TYPES`인지 + `summary` 비어있지 않은지.
- **`embed_text`는 내부 OpenAI 임베더에 위임**(composition):
  `self._embedder = OpenAIProvider(api_key=openai_api_key, embedding_model=embedding_model)`
  후 `return self._embedder.embed_text(text)`. 기존 검증(1536차원)까지 그대로 재사용.
- 에러 표준화: Gemini 예외(rate-limit 포함)를 `LLMProviderError`로 감싼다.

### 프리티어 rate-limit 방어

- GeminiProvider 내부 호출을 재시도 래퍼로 감싼다:
  - 429/ResourceExhausted 감지 시 지수 백오프(예: 2s → 4s → 8s), 최대 재시도 횟수는 상수/설정.
  - 백오프 소진 시 `LLMProviderError`로 상위 폴백에 위임.
- 선택적 호출 간 throttle 딜레이(env, 기본 0) — 분당 제한 회피용.
- **재실행 안전성**: `build_signals`는 이미 `processed`된 신호를 건너뛰므로, 일일 한도로 배치가
  중간에 끊겨도 복구 스크립트를 다시 돌리면 남은 신호만 이어서 처리된다.

## 공유 모듈 추출 (가벼운 리팩터)

- 신규 `pipeline/llm/prompts.py`(또는 `base.py` 확장)로 이동:
  - 시스템 프롬프트 상수: `RESEARCH_REVIEW_SYSTEM_PROMPT`, `SIGNAL_BUILD_PROMPT`,
    `CONTEXTUAL_CHAT_SYSTEM_PROMPT`, `LEARNING_PATH_SYSTEM_PROMPT`,
    `MEMORY_EXTRACTION_SYSTEM_PROMPT`.
  - 상수: `LEARNING_PATH_RESOURCE_TYPES`, `ALLOWED_MEMORY_TYPES`.
  - user content 빌더: `_build_user_content`, `_build_learning_path_content`,
    `_build_memory_content`, signal 출처 포맷팅 → 공유 순수 함수로.
  - 검증 헬퍼: `_validate_learning_path_resources`, 13섹션/메모리 검증 → 공유 함수로.
- `OpenAIProvider`는 이 상수/헬퍼를 import해서 쓰도록 수정(동작 불변).

## 설정 / 환경변수

`core/config.py`:
- `llm_provider: Literal["openai", "gemini"] = "openai"` (오타 방지)
- `gemini_api_key: str = Field(default="", repr=False)`
- `gemini_model: str = "gemini-2.5-flash"`
- (선택) `gemini_request_delay_sec: float = 0.0`, `gemini_max_retries: int = 4`

`.env`:
```
LLM_PROVIDER=gemini
GEMINI_API_KEY=...        # 현재 '#'로 주석 처리됨 → 활성화 필요
GEMINI_MODEL=gemini-2.5-flash
```

의존성: `google-genai`를 `requirements.txt`(또는 pyproject)에 추가.

## 에러 처리 & 폴백

- 모든 Gemini 예외 → `LLMProviderError`로 표준화 → 기존 상위 로직(예: recommender 콜드스타트,
  build_signals의 per-signal skip) 그대로 동작.
- 임베딩 실패(OpenAI 크레딧 없음 등) → 기존 콜드스타트 폴백 유지.

## 테스트 (TDD)

- `factory`: `llm_provider` 값에 따라 올바른 프로바이더 타입 반환.
- `GeminiProvider` 각 메서드: SDK를 모킹해 JSON 파싱 + 검증(성공/필드 누락/타입 오류) 경로.
- `embed_text` 위임: 내부 OpenAI 임베더 호출 확인(모킹).
- rate-limit 재시도: 429 → 백오프 후 성공 / 재시도 소진 → `LLMProviderError`.
- 공유 헬퍼: 기존 OpenAI 검증 테스트가 리팩터 후에도 통과.

## 롤아웃 / 검증

1. `.env`에서 `GEMINI_API_KEY` 주석 해제 + `LLM_PROVIDER=gemini` 설정.
2. `api/_resume_brief_2026_08_05.py` 재실행 → 41개 신호 처리 + 브리핑 생성 확인.
3. 홈(`/home`) 재접속 → "생성 중" 무한 로딩 해소, 브리핑 표시 확인.
4. `LLM_PROVIDER=openai`로 되돌려 토글 동작 확인.
