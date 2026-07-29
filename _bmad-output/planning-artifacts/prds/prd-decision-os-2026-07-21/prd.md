---
title: Decision OS — AI Research Playbook PRD
status: final
created: 2026-07-21
updated: 2026-07-22
---

## 1. 제품 개요

**Decision OS**는 사용자가 중요한 결정을 내릴 때 AI가 상황을 검토(Review)하고, 사용자의 선택(Decision)을 기록하며, 결과(Outcome)를 추적해 더 나은 판단을 돕는 개인용 의사결정 운영체제다.

AI Research가 첫 번째 **Playbook**이며, 이후 Insurance·Career·Investment·Real Estate 등 다양한 도메인으로 확장 가능한 플랫폼 구조를 지향한다.

Decision OS는 AI 뉴스를 많이 보여주는 서비스가 아니다. 오늘 내가 배워야 할 AI 기술을 추천하고, 이해·학습·적용까지 이어지도록 돕는 **AI Research OS**다.

---

## 2. 해결하는 문제

AI 분야는 매일 수백 개의 새로운 정보가 쏟아진다. 문제는 정보의 부족이 아니라, 무엇을 배울지 결정하기 어렵다는 것이다.

- 오늘 나온 AI 발표가 나에게 중요한지 판단하기 어렵다
- 기술을 배울지 말지 결정할 충분한 맥락을 얻기 힘들다
- 학습을 결정했어도 어디서 시작해야 할지 모른다
- 과거 학습·적용 결과가 다음 결정에 반영되지 않는다

---

## 3. 대상 사용자

AI 기술의 빠른 변화 속에서 **무엇을 배울지 결정**해야 하는 개발자.

**주요 시나리오:**
- AI를 업무에 활용하는 개발자 — 새로운 도구·모델 업데이트가 자신의 프로젝트에 적용할 만한지 판단하고 싶다
- AI Engineer 준비생 — 핵심 기술과 학습 경로를 파악해 효율적으로 공부하고 싶다
- AI Agent / LLM App 개발자 — 빠르게 변하는 프레임워크와 패턴 중 지금 써야 할 것을 골라내고 싶다

---

## 4. 핵심 개념: Decision Loop

모든 Playbook은 동일한 5단계 루프로 동작한다.

```
Event
 ↓
Review
 ↓
Decision
 ↓
Outcome
 ↓
Memory
 ↓
(다음 Event의 추천 품질 향상)
```

| 단계 | 역할 |
|------|------|
| **Event** | 판단이 필요한 상황 발생 (AI Research에서는 Signal) |
| **Review** | AI가 현재 상황을 분석하고 충분한 설명과 함께 검토 리포트 생성 |
| **Decision** | 사용자가 선택을 기록 |
| **Outcome** | 이후 결과를 기록 |
| **Memory** | 결정·결과 이력을 사용자 모델로 축적해 다음 추천 품질 향상 |

**핵심 원칙:**

- **Review Before Action** — AI는 사용자가 충분히 이해하기 전에 행동을 유도하지 않는다
- **Recommendation, Not Automation** — 분석·추천·설명은 AI가, 최종 결정은 사용자가
- **Explain Before Recommend** — 추천에는 반드시 근거 설명이 포함된다
- **Decision Must Lead To Action** — 결정은 실행으로 이어져야 한다 (AI Research에서는 학습과 적용)
- **Memory Improves Recommendation** — 모든 결과는 다음 추천 품질을 높인다

---

## 5. 기능 요구사항 — AI Research Playbook

### FR-0. 계정 및 온보딩
- FR-0.1 사용자는 계정을 생성하고 로그인할 수 있다
- FR-0.2 온보딩 시 역할(Role)과 관심 기술 영역(Project/Focus)을 입력할 수 있다
- FR-0.3 모든 학습 이력, Decision, Outcome, Memory 데이터는 사용자 계정에 귀속된다

### FR-1. Daily Brief & Signal
- FR-1.1 매일 사용자에게 관련성 높은 AI 기술 Signal을 큐레이션해 Daily Brief로 제공한다
- FR-1.2 Signal은 기사 하나가 아니라, 하나의 기술 또는 변화에 대한 여러 출처(공식 블로그, GitHub, Reddit, HN, YouTube 등)를 묶은 Decision Event다
- FR-1.3 Signal은 중복 제거 및 정규화 처리를 거쳐 생성된다
- FR-1.4 [ASSUMPTION] 개인화된 Memory를 기반으로 Signal의 우선순위와 관련성이 조정된다

### FR-2. Research Review
- FR-2.1 각 Signal에 대해 사용자가 "배울지 말지" 결정할 수 있도록 충분한 Research Review를 생성한다
- FR-2.2 Research Review는 다음 항목을 반드시 포함한다: 한 줄 정의, 핵심 개념 설명, 해결하는 문제, 왜 중요한가, 기존 기술과 차이, 사용자(Project/Role) 관련성, 학습 목표, 예상 학습 시간, 난이도, 실무 적용 가능성, 위험 요소, 추천 이유, 참고 출처
- FR-2.3 사용자는 Review 하나만 읽어도 해당 기술의 기본 개념을 이해할 수 있어야 한다

### FR-3. Decision
- FR-3.1 사용자는 각 Review에 대해 세 가지 CTA 중 하나를 선택할 수 있다: **Learn Now** / **Queue** / **Ignore**
- FR-3.2 Queue 선택 시 타이밍을 지정할 수 있다: Today / This Week / Later
- FR-3.3 결정 당시의 이유와 메모를 함께 저장할 수 있다
- FR-3.4 결정 이력을 시간순으로 조회할 수 있다

### FR-4. Learning Path
- FR-4.1 "Learn Now"를 선택하면 해당 기술에 대한 Learning Path를 생성한다
- FR-4.2 Learning Path는 공식 문서, 핵심 자료, GitHub, 실습 예제, 적용 아이디어를 기반으로 구성된다

### FR-5. Outcome 기록
- FR-5.1 사용자는 학습 결과를 Outcome으로 기록할 수 있다: Completed / Applied / Dropped / Not Useful
- FR-5.2 Outcome 기록 시 피드백을 남길 수 있다: 유용했는가, 적용했는가, 실제 학습 시간, 메모
- FR-5.3 기록된 Outcome은 이후 Signal 추천 및 Review 생성 시 맥락으로 반영된다

### FR-6. Memory & 개인화
- FR-6.1 시스템은 사용자의 Decision·Outcome 이력을 기반으로 Memory를 구축한다
- FR-6.2 Memory는 다음 항목으로 구성된다: Preference, Skill, Project, Decision History, Outcome History
- FR-6.3 Memory를 기반으로 Daily Brief와 Research Review의 추천 품질을 지속적으로 개선한다

### FR-7. 대시보드
- FR-7.1 오늘의 Daily Brief와 미결정 Signal을 한눈에 확인할 수 있는 요약 화면을 제공한다
- FR-7.2 Queue에 쌓인 학습 항목과 예정 일정을 확인할 수 있다
- FR-7.3 과거 Decision·Outcome 이력을 타임라인으로 조회할 수 있다

### FR-8. 실데이터 수집 & 시그널 품질 v2 [POST-MVP · 2026-07-29 스파이크 유래]

> v1(Epic 1~5) 완료 후, `StubCollector`(하드코딩 샘플 5건)를 실 소스로 대체하기 위한 후속 요구. 2026-07-29 실 RSS/HN 수집 스파이크에서 도출(키워드 그룹핑이 50%를 "General AI"로 뭉갬 등 확인). → Epic 6.

- FR-8.1 실제 외부 소스(RSS/Atom, HackerNews, GitHub Releases)에서 AI 기술 기사를 수집한다
- FR-8.2 수집 기사를 의미 유사도로 클러스터링하여 동일 주제를 1개 Signal(다중 출처)로 묶는다
- FR-8.3 도메인 무관/유해/저품질 기사를 시그널 생성 이전에 필터링한다
- FR-8.4 Recommender는 프로필/관심사 임베딩과 최신성·다양성·인기 피처로 시그널을 랭킹한다 (콜드 스타트 substring 매칭 제거)
- FR-8.5 노출·열람·결정 engagement를 로깅하고 추천 품질(RAG vs 콜드 스타트)을 오프라인 평가한다

---

## 6. 백엔드 Agent Workflow

아래 Agent들은 사용자에게 직접 노출되지 않는 내부 파이프라인이다.

```
Collector
 ↓
Normalizer / Deduplicator
 ↓
Signal Builder
 ↓
Reviewer
 ↓
Recommender
 ↓
Coach
 ↓
Memory Manager
```

각 Agent의 책임 범위와 트리거 조건은 아키텍처 단계에서 상세 정의한다.

---

## 7. 플랫폼 확장성 — Playbook 구조

AI Research 이후 도메인은 동일한 Decision Loop 위에 Playbook 단위로 추가된다.

**Future Playbooks (예정):** Insurance, Career, Investment, Real Estate

- 각 Playbook은 도메인별 Event 정의, Review 로직, Decision CTA, Outcome 정의를 가진다
- 공통 인프라(계정 시스템, Decision 저장소, Outcome 추적 엔진, Memory)는 플랫폼 레이어에서 관리한다
- [ASSUMPTION] Playbook은 설정 기반으로 활성화/비활성화 가능하다

---

## 8. 비기능 요구사항

| 항목 | 요구사항 |
|------|----------|
| **타겟 시장** | 한국 시장 전용; 한국어 UI 및 한국 AI 커뮤니티 맥락에서 설계한다 |
| **데이터 프라이버시** | 학습 이력, Decision, Memory 등 사용자 데이터는 사용자 계정 범위 내에서만 접근 가능해야 한다 |
| **AI 신뢰성** | Review 결과는 참고 의견임을 명시하며, 근거를 함께 제시해야 한다 |
| **폼팩터** | 모바일 웹 및 데스크탑 웹 모두 지원한다 |
| **콜드 스타트** | Memory가 없어도 Role·Focus 기반으로 기본 Daily Brief와 Review가 가능해야 한다 |

---

## 9. 범위 외 (현재 버전)

- AI Research 외 Playbook 구현 (Insurance, Career, Investment, Real Estate)
- Sandbox 코드 실행
- GitHub 자동 수정
- 완전 자율 Agent (Human-in-the-loop 없는 자동 실행)

---

## 10. 미결 사항

아키텍처 단계에서 결정할 사항:

| # | 질문 | 비고 |
|---|------|------|
| Q1 | Signal 수집 소스 및 수집 주기를 어떻게 정의할 것인가? | FR-1.1~1.3 참조 |
| Q2 | Memory 모델의 구조와 저장 방식 | FR-6 참조; 개인정보 처리 연계 |
| Q3 | Agent Workflow 각 Agent의 책임 범위와 트리거 조건 | 섹션 6 참조 |
| Q4 | [ASSUMPTION] Playbook 설정 기반 활성화 구조 | 아키텍처 단계에서 확정 |

**확정 사항:**

| # | 결정 내용 |
|---|----------|
| Q5 | 타겟 시장: 한국 전용 유지 |
| Q6 | 계정/로그인 시스템 필요 |
| Q7 | 첫 번째 Playbook: AI Research (Insurance는 Future Playbook으로 이동) |
| Q8 | Core Loop: Event→Review→Decision→Outcome→Memory 5단계 |
| Q9 | Decision CTA: Learn Now / Queue (Today·This Week·Later) / Ignore |
