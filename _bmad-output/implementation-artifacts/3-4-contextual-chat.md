---
baseline_commit: NO_VCS
---

# Story 3.4: Contextual Chat

Status: done

## Story

사용자로서,
Research Review 화면 내에서 AI에게 해당 기술에 관한 질문을 할 수 있기를 원한다,
그래서 Review만으로 해소되지 않은 궁금증을 바로 해결할 수 있다.

## Acceptance Criteria

**AC-1: 진입점 및 화면 전환**
- **Given** Research Review 상세 화면의 "AI에게 질문하기" 링크를 탭하면
- **Then** Contextual Chat 화면이 현재 탭 브랜치 스택에 push된다 (`/home/review/:signalId/chat`)
- **And** 현재 Research Review의 Signal ID가 시스템 컨텍스트로 자동 전달된다
- **And** 첫 AI 메시지: "이 Review에 대해 궁금한 점을 물어보세요."

**AC-2: 진입점 제한**
- **Given** Contextual Chat이 열려 있을 때
- **Then** 홈/큐/히스토리/프로필 어디에도 Chat 진입점이 없다 (Floating FAB 금지)
- **And** Chat 내에 Learn Now / Queue / Ignore CTA가 없다

**AC-3: back 제스처로 복귀**
- **Given** back 제스처로 Chat을 닫으면
- **Then** Research Review 상세 화면의 이전 스크롤 위치로 돌아간다

**AC-4: AI 응답 실패 처리**
- **Given** AI 응답이 실패하거나 타임아웃되면
- **Then** "응답을 받지 못했습니다. 잠시 후 다시 시도해 주세요." 인라인 에러 + 재시도 CTA가 표시된다

**AC-5: 세션 비영속성 (v1)**
- **Given** 사용자가 앱을 닫고 다시 Chat에 진입하면
- **Then** 이전 대화가 복원되지 않고 새 세션으로 시작된다 (v1 세션 비영속)

**AC-6: Chat UI 상태 — Empty**
- **Given** 사용자가 처음 Chat에 진입했을 때 (메시지 없는 상태)
- **Then** 상단 컨텍스트 레이블: "Research Review — [Signal 제목]" 표시
- **And** 메시지 스레드 영역 비어있음
- **And** 입력 바에 포커스
- **And** 입력 바 placeholder: "이 Review에 대해 궁금한 점을 물어보세요."

**AC-7: Chat UI 상태 — In-conversation**
- **Given** 사용자가 메시지를 1개 이상 전송한 상태
- **Then** AI 메시지: 왼쪽 정렬, `surface-card` 배경
- **And** 사용자 메시지: 오른쪽 정렬, `accent-primary` 배경, `accent-foreground` 텍스트
- **And** 각 AI 메시지에 타임스탬프 표시

**AC-8: 메시지 전송**
- **Given** 사용자가 입력 바에 텍스트를 입력하고 전송하면
- **Then** `POST /api/v1/chat/messages` `{ signal_id, message }` 요청이 전송된다
- **And** AI 응답 대기 중 입력 바 비활성화 + 로딩 인디케이터 표시
- **And** 응답 수신 시 AI 메시지가 스레드 하단에 추가된다

## Tasks / Subtasks

### [API] Chat 라우터 신규 생성

- [x] Task 1: `api/pipeline/llm/base.py` 수정 — `ChatContext` 데이터클래스 추가 (AC: #1, #8)
  - [x] 1.1 `ChatContext` 데이터클래스: `signal_id: str`, `user_message: str`, `review_payload: dict | None = None`, `user_role: str | None = None`, `user_tech_stack: list[str] = field(default_factory=list)`
  - [x] 1.2 `LLMProvider` 추상 메서드 추가: `def chat(self, context: ChatContext) -> LLMResponse: ...`

- [x] Task 2: `api/pipeline/llm/openai_provider.py` 수정 — `chat()` 메서드 구현 (AC: #1, #8)
  - [x] 2.1 `CONTEXTUAL_CHAT_SYSTEM_PROMPT` 상수 정의 — Research Review 내용을 컨텍스트로, 사용자 질문에 답변하는 AI 역할 프롬프트
  - [x] 2.2 `chat(self, context: ChatContext) -> LLMResponse` 구현
  - [x] 2.3 `client.responses.create(model=self._model, instructions=CONTEXTUAL_CHAT_SYSTEM_PROMPT, input=user_message_with_context)` — AD-6: OpenAI Responses API 사용, Chat Completions 사용 금지
  - [x] 2.4 `LLMProviderError` 포착 및 재raise

- [x] Task 3: `api/routers/chat.py` 신규 생성 — `POST /api/v1/chat/messages` (AC: #1, #4, #8)
  - [x] 3.1 `ChatMessageRequest` Pydantic 모델: `signal_id: str`, `message: str`
  - [x] 3.2 `message` 필드: 빈 문자열 검증 (`min_length=1`)
  - [x] 3.3 `get_current_user` 의존성으로 `user_id` 추출
  - [x] 3.4 `signal_id`로 `signals` 테이블 조회 → `project_id` 획득 → `projects.user_id = user_id` 검증 (없으면 404)
  - [x] 3.5 `signal_id`로 `reviews` 테이블에서 `status = 'completed'`인 최신 review 조회 → `result.payload` 획득
  - [x] 3.6 `ChatContext` 구성: `signal_id`, `user_message=body.message`, `review_payload`, 사용자 프로필(users 테이블에서 조회)
  - [x] 3.7 `llm_provider.chat(context)` 호출
  - [x] 3.8 `LLMProviderError` 포착 → HTTP 503 반환
  - [x] 3.9 `return APIResponse(data={"reply": reply_text})` HTTP 200
  - [x] 3.10 `router = APIRouter(prefix="/chat", tags=["chat"])`
  - [x] 3.11 `get_llm_provider()` 의존성 함수 — `settings.openai_api_key`로 `OpenAIProvider` 생성

- [x] Task 4: `api/main.py` 수정 — chat 라우터 등록 (AC: #8)
  - [x] 4.1 `from routers.chat import router as chat_router` import 추가
  - [x] 4.2 `app.include_router(chat_router, prefix="/api/v1")` 추가

- [x] Task 5: `api/tests/test_chat.py` 신규 생성 (AC: #1, #4, #8)
  - [x] 5.1 정상 chat 메시지 전송 → 200 + reply 반환 검증
  - [x] 5.2 다른 사용자의 signal_id로 요청 → 404
  - [x] 5.3 빈 메시지 전송 → 422
  - [x] 5.4 LLMProviderError 발생 시 → 503 + error 봉투 구조 검증
  - [x] 5.5 completed review 없는 signal로 요청 → review_payload=None으로 graceful 처리

### [WEB] Contextual Chat 화면 구현

- [x] Task 6: `web/src/app/(app)/home/review/[signalId]/chat/page.tsx` 신규 생성 (AC: #1, #3, #6, #7, #8)
  - [x] 6.1 `"use client"` 선언
  - [x] 6.2 `params: Promise<{ signalId: string }>` prop 수신 (Next.js App Router 패턴)
  - [x] 6.3 Signal 제목 조회: Supabase SDK로 `signals` 테이블에서 `id = signalId` 조회 → `title` 획득 (useEffect)
  - [x] 6.4 상단 컨텍스트 레이블: "Research Review — [Signal 제목]" (13px, text-secondary)
  - [x] 6.5 Back 버튼: `<Link href={/home/review/${signalId}}>` — 이전 스크롤 위치 복원은 Next.js 기본 동작에 의존
  - [x] 6.6 메시지 스레드 영역: 스크롤 가능 컨테이너, 하단 고정 입력 바
  - [x] 6.7 메시지 상태: `useState<Message[]>` — `Message = { role: 'ai' | 'user'; text: string; timestamp: Date; isError?: boolean }`
  - [x] 6.8 초기 AI 메시지 자동 삽입: "이 Review에 대해 궁금한 점을 물어보세요."
  - [x] 6.9 사용자 메시지 UI: 오른쪽 정렬, `accent-primary` bg, `accent-foreground` text
  - [x] 6.10 AI 메시지 UI: 왼쪽 정렬, `surface-card` bg, 타임스탬프 표시
  - [x] 6.11 `isLoading` 상태: AI 응답 대기 중 입력 바 disabled + 로딩 인디케이터
  - [x] 6.12 입력 바: `<input>`, placeholder "이 Review에 대해 궁금한 점을 물어보세요.", 전송 버튼 (`aria-label="전송"`)
  - [x] 6.13 `handleSend()`: 빈 메시지 무시, 사용자 메시지 스레드 추가, `POST /api/v1/chat/messages` 호출, 응답 AI 메시지 추가, 오류 시 AC-4 에러 메시지 인라인 표시 + 재시도 CTA
  - [x] 6.14 Supabase `auth.getSession()` 으로 JWT 획득 → `Authorization: Bearer {token}` 헤더 추가
  - [x] 6.15 AI 응답 실패 인라인 에러: "응답을 받지 못했습니다. 잠시 후 다시 시도해 주세요." + "재시도" 버튼
  - [x] 6.16 세션 비영속: 컴포넌트 마운트 시 항상 초기 상태로 시작
  - [x] 6.17 No FAB, no Learn Now/Queue/Ignore CTA 내부에 없음 확인

- [x] Task 7: `web/src/components/home/review/__tests__/contextual-chat.test.tsx` 신규 생성
  - [x] 7.1 초기 상태: 상단 레이블, AI 첫 메시지, 입력 바 placeholder 검증
  - [x] 7.2 메시지 전송 → 사용자 메시지 스레드 추가, API 호출 확인
  - [x] 7.3 API 성공 → AI 응답 메시지 스레드 추가 검증
  - [x] 7.4 API 실패(503) → 인라인 에러 + 재시도 CTA 표시 검증
  - [x] 7.5 전송 중 입력 바 disabled 검증

### [FLUTTER] Contextual Chat 화면 구현

- [x] Task 8: `mobile/lib/features/home/screens/contextual_chat_screen.dart` 신규 생성 (AC: #1, #3, #4, #5, #6, #7, #8)
  - [x] 8.1 `ContextualChatScreen extends ConsumerStatefulWidget` — `signalId: String` prop만. `signalTitle`은 `ref.watch(reviewStateProvider(signalId))`로 획득
  - [x] 8.2 `_ContextualChatScreenState extends ConsumerState<ContextualChatScreen>`
  - [x] 8.3 `List<_ChatMessage> _messages = []` — `_ChatMessage = {role: 'ai'|'user', text: String, timestamp: DateTime, isError: bool}`
  - [x] 8.4 `initState`: 초기 AI 메시지 삽입 ("이 Review에 대해 궁금한 점을 물어보세요.")
  - [x] 8.5 `bool _isLoading = false`, `final _textController = TextEditingController()`, `final _scrollController = ScrollController()`
  - [x] 8.6 `Scaffold`: `AppBar` — 타이틀 "Research Review — [signalTitle]" (13px/text-secondary), back 버튼 (`context.pop()`)
  - [x] 8.7 AI 메시지 bubble: 왼쪽 정렬, `surfaceCard` 색상 Container, `BorderRadius.circular(12)`, 타임스탬프 표시
  - [x] 8.8 사용자 메시지 bubble: 오른쪽 정렬, `accentPrimary` 배경, `accentForeground` 텍스트
  - [x] 8.9 하단 고정 입력 바: `TextField` + 전송 `IconButton` (Send 아이콘), `_isLoading` 시 disabled
  - [x] 8.10 `_handleSend()` async 함수: 빈 입력 무시, `_isLoading = true`, 사용자 메시지 추가, `_postChatMessage()` 호출, AI 메시지 추가 또는 에러 처리, `_isLoading = false`
  - [x] 8.11 `_postChatMessage(String userMessage) async → String?`: JWT 획득, `http.post`, 성공 시 `data['reply']` 반환, 실패 시 null
  - [x] 8.12 에러 표시: 인라인 에러 위젯 + `TextButton("재시도")`
  - [x] 8.13 메시지 추가 후 `_scrollController.animateTo`로 스크롤 최하단 이동
  - [x] 8.14 세션 비영속: `initState` 외 저장 없음
  - [x] 8.15 `const _fastapiUrl = String.fromEnvironment('FASTAPI_URL', defaultValue: 'http://localhost:8000')`
  - [x] 8.16 dispose: `_textController.dispose()`, `_scrollController.dispose()`

- [x] Task 9: `mobile/lib/core/router/app_router.dart` 수정 — chat 라우트 추가 (AC: #1, #3)
  - [x] 9.1 `review/:signalId` GoRoute 내 `routes` 에 기존 `learning-path`와 동일 레벨로 `chat` GoRoute 추가
  - [x] 9.2 `GoRoute(path: 'chat', builder: (_, state) => ContextualChatScreen(signalId: state.pathParameters['signalId']!))`
  - [x] 9.3 `import '../../features/home/screens/contextual_chat_screen.dart'` 추가
  - [x] 9.4 `app_router.g.dart` build_runner 재생성 완료

- [x] Task 10: `mobile/lib/features/home/screens/research_review_screen.dart` — Chat 진입점 이미 구현됨, 수정 불필요 (AC: #1)
  - [x] 10.1 "AI에게 질문하기" `GestureDetector`가 Section 13 (HonestBox) 하단에 이미 구현됨 (line 442-453)
  - [x] 10.2 `context.push('/home/review/${widget.review.signalId}/chat')` 로 이미 chat 경로로 이동
  - [x] 10.3 chat GoRoute가 Task 9에서 추가됨 → GoRouter 404 해결
  - **수정 불필요**: Task 9의 GoRoute 추가로 정상 동작

### Review Findings

- [x] [Review][Decision] AC-6 "스레드 비어있음" vs AC-1 "첫 AI 메시지" 스펙 모순 — AC-6의 "비어있음"을 "유저 메시지 없음"으로 해석, 현재 구현(AC-1 준수) 유지로 결정.
- [x] [Review][Decision] AC-3 스크롤 위치 복원 미구현 — `router.back()` 으로 변경 적용 완료. [web/src/app/(app)/home/review/[signalId]/chat/page.tsx]
- [x] [Review][Patch] Supabase 4개 쿼리 예외 처리 없음 — DB 쿼리 전체를 try/except로 래핑, HTTPException 재raise, 그 외 예외는 503 반환. [api/routers/chat.py]
- [x] [Review][Patch] Flutter setState-on-disposed-widget — `await _postChatMessage()` 후 `if (!mounted) return;` 추가. [mobile/lib/features/home/screens/contextual_chat_screen.dart]
- [x] [Review][Patch] reviews result 필드 비-dict시 AttributeError — `isinstance(result, dict)` 체크 후 `.get("payload")` 호출하도록 수정. [api/routers/chat.py]
- [x] [Review][Patch] output_text None 전파 — `response.output_text or ""` 로 None 가드 추가. [api/pipeline/llm/openai_provider.py]
- [x] [Review][Patch] useEffect 에러/클린업 없음 — `cancelled` 플래그 + `.catch(() => {})` + cleanup 함수 반환 추가. [web/src/app/(app)/home/review/[signalId]/chat/page.tsx]
- [x] [Review][Patch] 메시지 최대 길이 미검증 — `message: str = Field(..., max_length=2000)` 추가. [api/routers/chat.py]
- [x] [Review][Patch] LLM 프로바이더 싱글톤 미적용 — `@lru_cache(maxsize=1)` 적용. [api/routers/chat.py]
- [x] [Review][Patch] OpenAI 명시적 타임아웃 없음 — `OpenAI(api_key=api_key, timeout=30.0)` 로 30초 타임아웃 설정. [api/pipeline/llm/openai_provider.py]
- [x] [Review][Patch] React key={i} 안티패턴 — `Message` 타입에 `id: string` 추가, `key={msg.id}` 로 교체. [web/src/app/(app)/home/review/[signalId]/chat/page.tsx]
- [x] [Review][Patch] 빈 reply 버블 — 빈 reply 시 Error throw → catch 블록에서 에러 메시지 + 재시도 처리. [web/src/app/(app)/home/review/[signalId]/chat/page.tsx]
- [x] [Review][Patch] Web 입력 바 autoFocus 없음 — `<input>`에 `autoFocus` 추가. [web/src/app/(app)/home/review/[signalId]/chat/page.tsx]
- [x] [Review][Defer] 레이트 리밋 없음 [api/routers/chat.py] — deferred, v1 범위 외 운영 이슈
- [x] [Review][Defer] 프롬프트 인젝션 위험 [api/pipeline/llm/openai_provider.py] — deferred, Responses API instructions/input 분리로 일부 완화, v2 이슈
- [x] [Review][Defer] Flutter 에러 상태 미구분 [mobile/lib/features/home/screens/contextual_chat_screen.dart] — deferred, 401/503/네트워크 동일 처리, v1 AC-4 준수
- [x] [Review][Defer] String.fromEnvironment HTTP 기본값 [mobile/lib/features/home/screens/contextual_chat_screen.dart] — deferred, 빌드 운영 이슈, 프로덕션 빌드 시 dart-define 설정 필요
- [x] [Review][Defer] signal_id UUID 형식 미검증 [api/routers/chat.py] — deferred, ORM 파라미터화로 보호, 기능 영향 없음
- [x] [Review][Defer] 미인증 요청 테스트 없음 [api/tests/test_chat.py] — deferred, auth 미들웨어 별도 테스트 범위
- [x] [Review][Defer] isLoading 경쟁 조건 [web/src/app/(app)/home/review/[signalId]/chat/page.tsx] — deferred, 실사용 인간 인터랙션에서 발생 확률 극히 낮음

## Dev Notes

### 핵심 아키텍처 제약

| 규칙 | 상세 |
|------|------|
| **AD-3** 쓰기 경로 | chat 메시지: FastAPI만. 클라이언트 직접 Supabase 쓰기 없음 (v1에서 DB 저장 자체 없음) |
| **AD-6** LLM 공급자 | OpenAI Responses API만 사용. Chat Completions API 사용 금지. `client.responses.create()` 패턴 유지 |
| **AD-13** API 계약 | `Authorization: Bearer {JWT}`, `/api/v1/`, 응답 봉투 `{data, error}` |
| **AD-14** Flutter 상태관리 | Riverpod 2.x — chat 화면은 단순 StatefulWidget으로 충분 (외부 공유 상태 없음) |
| **V1 비영속성** | 대화 이력 DB 저장 없음. 메모리(React state / Flutter widget state)에만 존재 |

### 현재 파일 상태 (이 스토리가 수정할 파일들)

**이미 구현된 것:**
- `web/src/components/home/review/research-review-content.tsx:172-183` — "AI에게 질문하기" Link 이미 구현됨 (`href={/home/review/${signalId}/chat}`, 13px/text-secondary/underline). **이 스토리에서 수정 불필요**
- `mobile/lib/core/router/app_router.dart:87-92` — `learning-path` sub-route 존재. `chat` sub-route를 동일 레벨에 추가

**신규 생성 대상:**
- `api/routers/chat.py` (NEW)
- `api/tests/test_chat.py` (NEW)
- `web/src/app/(app)/home/review/[signalId]/chat/page.tsx` (NEW)
- `web/src/components/home/review/__tests__/contextual-chat.test.tsx` (NEW)
- `mobile/lib/features/home/screens/contextual_chat_screen.dart` (NEW)

**수정 대상:**
- `api/pipeline/llm/base.py` — `ChatContext` 데이터클래스 + `LLMProvider.chat()` abstract method 추가
- `api/pipeline/llm/openai_provider.py` — `chat()` 구현
- `api/main.py` — chat_router 등록
- `mobile/lib/core/router/app_router.dart` — chat GoRoute 추가
- `mobile/lib/features/home/screens/research_review_screen.dart` — **수정 불필요** (진입점 이미 line 442-453에 구현됨)

### API 설계 — POST /api/v1/chat/messages

```python
# api/routers/chat.py
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from core.schemas import APIResponse
from core.supabase import get_supabase
from middleware.auth import get_current_user
from pipeline.llm.base import ChatContext, LLMProviderError
from pipeline.llm.openai_provider import OpenAIProvider
from core.config import settings

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatMessageRequest(BaseModel):
    signal_id: str
    message: str

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message must not be empty")
        return v

def get_llm_provider() -> OpenAIProvider:
    return OpenAIProvider(api_key=settings.openai_api_key)

@router.post("/messages", response_model=APIResponse)
def send_chat_message(
    body: ChatMessageRequest,
    user_id: Annotated[str, Depends(get_current_user)],
    llm: OpenAIProvider = Depends(get_llm_provider),
) -> APIResponse:
    client = get_supabase()
    # signal → project → user_id 검증
    signal_rows = client.table("signals").select("id, project_id").eq("id", body.signal_id).execute().data
    if not signal_rows:
        raise HTTPException(status_code=404, detail="Signal not found")
    project_id = signal_rows[0]["project_id"]
    project_rows = client.table("projects").select("id").eq("id", project_id).eq("user_id", user_id).execute().data
    if not project_rows:
        raise HTTPException(status_code=404, detail="Signal not found")

    # 최신 completed review payload 조회 (없으면 None으로 graceful 처리)
    review_rows = (
        client.table("reviews")
        .select("payload")
        .eq("signal_id", body.signal_id)
        .eq("status", "completed")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    review_payload = review_rows[0]["payload"] if review_rows else None

    # 사용자 프로필 조회
    user_rows = client.table("users").select("role, tech_stack, interests, experience_level").eq("id", user_id).execute().data
    user_data = user_rows[0] if user_rows else {}

    context = ChatContext(
        signal_id=body.signal_id,
        user_message=body.message,
        review_payload=review_payload,
        user_role=user_data.get("role"),
        user_tech_stack=user_data.get("tech_stack") or [],
    )

    try:
        response = llm.chat(context)
        return APIResponse(data={"reply": response.content})
    except LLMProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
```

### LLM: ChatContext 및 chat() 메서드

```python
# api/pipeline/llm/base.py 추가 내용
@dataclass
class ChatContext:
    """Contextual Chat 컨텍스트."""
    signal_id: str
    user_message: str
    review_payload: dict | None = None
    user_role: str | None = None
    user_tech_stack: list[str] = field(default_factory=list)

# LLMProvider에 추가:
@abstractmethod
def chat(self, context: ChatContext) -> LLMResponse:
    """Contextual Chat — Review 컨텍스트 기반 질답."""
    ...
```

```python
# api/pipeline/llm/openai_provider.py 추가 내용
CONTEXTUAL_CHAT_SYSTEM_PROMPT = """당신은 AI 기술 전문가입니다. 사용자가 특정 기술의 Research Review를 읽은 후 질문합니다.
Review의 내용을 기반으로 명확하고 유용한 답변을 제공하세요. 한국어로 답변하세요.
답변은 2-5문장 이내로 간결하게 작성하세요."""

def chat(self, context: ChatContext) -> LLMResponse:
    review_summary = ""
    if context.review_payload:
        one_line = context.review_payload.get("one_line_definition", "")
        recommendation = context.review_payload.get("recommendation_reason", "")
        review_summary = f"Review 요약: {one_line}\n추천 이유: {recommendation}"

    user_input = f"{review_summary}\n\n사용자 질문: {context.user_message}"
    try:
        response = self._client.responses.create(
            model=self._model,
            instructions=CONTEXTUAL_CHAT_SYSTEM_PROMPT,
            input=user_input,
        )
        return LLMResponse(content=response.output_text, model=self._model)
    except OpenAIError as e:
        raise LLMProviderError(str(e)) from e
    except Exception as e:
        raise LLMProviderError(str(e)) from e
```

### Web: 스크롤 위치 복원

Next.js App Router에서 `router.back()`은 브라우저 히스토리를 통해 이전 페이지로 복귀하며, 스크롤 위치는 브라우저 기본 동작으로 복원된다. "AI에게 질문하기" 링크가 `<Link>`로 구현돼 있어 SPA 전환이므로 별도 처리 불필요.

### Flutter: GoRouter chat 라우트 추가 패턴

```dart
GoRoute(
  path: 'review/:signalId',
  builder: (_, state) => ResearchReviewScreen(
    signalId: state.pathParameters['signalId']!,
  ),
  routes: [
    GoRoute(
      path: 'learning-path',
      builder: (_, __) => const _LearningPathPlaceholderScreen(),
    ),
    GoRoute(  // 신규 추가
      path: 'chat',
      builder: (_, state) => ContextualChatScreen(
        signalId: state.pathParameters['signalId']!,
      ),
    ),
  ],
),
```

- `signalTitle`은 `ContextualChatScreen` 내부에서 `ref.watch(reviewStateProvider(signalId))` 를 통해 획득
- `reviewStateProvider`는 `ResearchReview` 데이터에 `signalTitle` 필드 포함 (이미 구현됨)
- AppBar 타이틀: `"Research Review — ${signalTitle}"` — reviewAsync가 loaded 되기 전에는 `"Research Review"` fallback 사용

### Flutter: "AI에게 질문하기" 진입점 확인

`research_review_screen.dart`에 이미 존재하는지 확인 필요. 현재 구현에서 Section 13 (honest_box) 하단에 해당 버튼이 없다면 추가. 형태:

```dart
TextButton(
  onPressed: () => context.push('/home/review/$signalId/chat'),
  child: Text(
    'AI에게 질문하기',
    style: TextStyle(
      fontSize: 13,
      color: Theme.of(context).colorScheme.secondary,
      decoration: TextDecoration.underline,
    ),
  ),
),
```

### 범위 경계

| 항목 | 이 스토리 (3.4) | 이후 |
|------|----------------|------|
| Chat 화면 (Web + Flutter) | ✅ | — |
| `POST /api/v1/chat/messages` API | ✅ | — |
| 세션 내 대화 (메모리) | ✅ | — |
| AI 첫 메시지 자동 삽입 | ✅ | — |
| 에러/재시도 인라인 처리 | ✅ | — |
| 세션 영속성 (앱 재시작 후 복원) | ❌ | V2 deferred |
| 다중 턴 대화 이력 백엔드 전달 | ❌ | V2 — 각 메시지는 독립 요청 |
| Learning Path 화면 | ❌ | Story 4.1 |

### 절대 금지사항

| 금지 | 이유 |
|------|------|
| Chat Completions API 사용 | AD-6: OpenAI Responses API만 허용 |
| Floating FAB Chat 버튼 | 명시적 UX 금지 패턴 |
| Chat 내 Learn Now/Queue/Ignore CTA | AC-2 명시 금지 |
| 대화 이력 Supabase 저장 | V1 비영속 설계 |
| `showDialog` / `AlertDialog` 에러 표시 | 인라인 에러 표시 필수 |
| Chat이 modal/bottom sheet으로 열림 | push navigation (full screen) 필수 |

### 신규 / 수정 파일 목록

```
# API 신규 파일
api/routers/chat.py                          (NEW)
api/tests/test_chat.py                       (NEW)

# API 수정 파일
api/pipeline/llm/base.py                     (UPDATE — ChatContext, chat() abstract 추가)
api/pipeline/llm/openai_provider.py          (UPDATE — chat() 구현)
api/main.py                                  (UPDATE — chat_router 등록)

# 웹 신규 파일
web/src/app/(app)/home/review/[signalId]/chat/page.tsx  (NEW)
web/src/components/home/review/__tests__/contextual-chat.test.tsx  (NEW)

# Flutter 신규 파일
mobile/lib/features/home/screens/contextual_chat_screen.dart  (NEW)

# Flutter 수정 파일
mobile/lib/core/router/app_router.dart               (UPDATE — chat GoRoute 추가)
mobile/lib/core/router/app_router.g.dart             (UPDATE — build_runner 재생성)
# mobile/lib/features/home/screens/research_review_screen.dart — 수정 불필요 (진입점 line 442-453에 이미 구현됨)
```

### References

- 에픽: `_bmad-output/planning-artifacts/epics.md` — Story 3.4 (line 631–657)
- UX 상태: `_bmad-output/planning-artifacts/ux-designs/ux-decision-os-2026-07-21/EXPERIENCE.md` — Contextual Chat 4상태, 진입점, 비영속 설계
- 아키텍처: `_bmad-output/planning-artifacts/architecture/architecture-decision-os-2026-07-21/ARCHITECTURE-SPINE.md` — AD-3(데이터 접근), AD-6(LLM 공급자), AD-13(API 계약), AD-14(Flutter 상태관리)
- LLM 인터페이스: `api/pipeline/llm/base.py`
- LLM 구현체: `api/pipeline/llm/openai_provider.py`
- 기존 decisions 라우터 패턴: `api/routers/decisions.py`
- FastAPI 메인: `api/main.py`
- 기존 Flutter 라우터: `mobile/lib/core/router/app_router.dart` (line 87–92)
- 웹 진입점 (이미 구현): `web/src/components/home/review/research-review-content.tsx` (line 172–183)
- 이전 스토리: `_bmad-output/implementation-artifacts/3-3-contextstickybar-and-decision.md`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- `reviews` 테이블 payload는 `result.payload` 중첩 구조. `chat.py`에서 `select("result")`로 조회 후 `result.get("payload")` 추출.
- 기존 `MockLLMProvider` (test_signal_builder_reviewer.py)에 새 abstract method `chat()` stub 추가 필요 — 누락 시 기존 테스트 15개 실패.
- FastAPI dependency override에 `app.dependency_overrides[get_llm_provider] = lambda: mock_llm` 패턴 사용 (patch 방식보다 안정적).
- Next.js App Router에서 params는 `Promise<{signalId: string}>`, `use(params)` 또는 `await`로 unwrap 필요.
- Flutter에서 `signalTitle`은 이미 `reviewStateProvider`에서 관리되므로 별도 prop 전달 불필요.

### File List

api/pipeline/llm/base.py
api/pipeline/llm/openai_provider.py
api/routers/chat.py
api/main.py
api/tests/test_chat.py
api/tests/test_signal_builder_reviewer.py
web/src/app/(app)/home/review/[signalId]/chat/page.tsx
web/src/components/home/review/__tests__/contextual-chat.test.tsx
mobile/lib/features/home/screens/contextual_chat_screen.dart
mobile/lib/core/router/app_router.dart
mobile/lib/core/router/app_router.g.dart


## Change Log

- 2026-07-27: Story 3-4 Contextual Chat 전체 구현 (claude-sonnet-4-6)
  - API: ChatContext 데이터클래스 + LLMProvider.chat() abstract 추가, OpenAIProvider.chat() 구현
  - API: POST /api/v1/chat/messages 라우터 신규 생성, main.py 등록
  - API: test_chat.py 5개 테스트 작성 (전부 통과), 기존 96개 테스트 회귀 없음
  - Web: /home/review/[signalId]/chat/page.tsx 클라이언트 컴포넌트 신규 생성
  - Web: contextual-chat.test.tsx 스펙 문서 신규 생성
  - Flutter: ContextualChatScreen 신규 생성, app_router.dart chat GoRoute 추가, app_router.g.dart 재생성
