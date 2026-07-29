# Engagement 지표 정의 (Story 6.5)

`eval_engagement.py`가 계산하는 held-out engagement 지표의 분자/분모/출처와 해석상 한계를 정의한다.
목적: 6.1~6.4의 랭킹 고도화(RAG 재랭킹)가 콜드스타트 대비 추천 품질을 올렸는지 **데이터로** 비교.

## 코호트(variant)

- **rag**: brief 생성 시 사용자가 Memory를 보유해 RAG 재랭킹이 실제 적용된 경로(`memory_rag_applied`).
- **coldstart**: Memory 미보유 / RAG 폴백 / llm 미주입 경로(`memory_rag_coldstart`).
- **unknown**: impression 없이 후속 이벤트(open·decision 등)만 있는 이례 케이스(예: impression 로깅만 실패).
  누락하지 않고 별도 버킷으로 가시화한다(설계 D5).

variant 정본은 **impression 이벤트**에만 서버가 기록한다(D2). open·read_through·decision 이벤트는
variant를 직접 갖지 않고, `(user_id, signal_id)`로 impression과 조인해 variant를 attach한다(D5).

## 지표

| 지표 | 분자 | 분모 | 이벤트 출처 |
|---|---|---|---|
| **CTR** | `open` 이벤트 수 | `impression` 이벤트 수 | open=웹 계측 / impression=서버 정본 |
| **read-through율** | `read_through` 이벤트 수 | `open` 이벤트 수 | 둘 다 웹 계측 |
| **Learn Now율** | `decision` 중 `metadata.choice = 'learn_now'` 수 | `impression` 이벤트 수 | decision=서버(decisions 라우터) / impression=서버 |
| **Outcome 유용도** | `outcomes.useful = true` 수 | `status ∈ {completed, applied}` 인 outcome 수 | outcomes 테이블(decision→review→signal 조인으로 variant attach) |

- **분모 0 방어:** 분모가 0이면 `None`/`NaN` 대신 명시적 문자열 `"n/a"`를 출력한다(변별 불가를 표에서 가시화).
- **impression 정의:** "brief에 담겨 노출됨"(서버 정본). 사용자가 home을 안 열면 impression은 있으나 open이
  없으므로 CTR이 낮게 반영된다 — 이는 버그가 아니라 CTR의 자연스러운 정의다(D2).

## 계측 범위

- **impression**: 서버(recommender, brief 생성 시) — 배치·온디맨드 두 경로 공통(AD-15).
- **open / read_through**: **웹 클라이언트만** 계측(Flutter deferred, D3). 따라서 CTR·read-through율은
  **웹 코호트 기준**이다. Flutter 사용자의 열람은 미집계.
- **decision**: 서버(decisions 라우터) — 신규 decision insert 성공 시 1회, 멱등 재요청은 미로깅.

## 한계 (반드시 리포트에 명시)

이것은 **무작위 A/B가 아니라 관찰적 cohort 비교**다. variant는 무작위 배정이 아니라 Memory 보유 여부로
이미 갈라진 두 집단이다. Memory 보유 사용자는 원래 더 활발할 수 있어(**선택 편향**) engagement가 높게
나올 수 있으므로, variant 간 차이를 곧바로 "RAG의 인과 효과"로 해석하면 안 된다. 엄밀한 인과 추정은 향후
무작위 실험(deferred) 프레임워크에서 다룬다.
