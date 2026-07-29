# IDEA.md

# Decision OS MVP

## Vision

Decision OS는 AI 챗봇이 아니다.

사용자가 중요한 결정을 내릴 때마다 AI가 상황을 검토(Review)하고,
사용자의 선택(Decision)을 기록하며,
결과(Outcome)를 학습하여 더 나은 판단을 돕는 **Decision Operating System**이다.

보험은 첫 번째 Playbook이며,
향후 Career, Investment, Home 등 다양한 도메인으로 확장 가능한 플랫폼을 목표로 한다.

---

# Core Philosophy

기존 AI

```
질문
↓

답변
↓

종료
```

Decision OS

```
상황(Context)
↓

Review
↓

Decision
↓

Outcome
↓

Memory
↓

Next Review
```

AI의 역할은 답변이 아니라 **검토(Review)** 이다.

사용자의 역할은 질문이 아니라 **의사결정(Decision)** 이다.

---

# MVP Goal

보험 도메인을 첫 번째 Playbook으로 구현한다.

MVP에서는

* 보험 현황 자동 등록
* AI Review 생성
* 보험금 청구 지원
* Decision Memory 저장

까지 구현한다.

---

# Product Structure

```
Decision OS

├── Decision Engine
│
└── Playbooks
      └── Insurance
```

Decision Engine은 모든 도메인이 공유한다.

Insurance는 첫 번째 Playbook이다.

---

# Core Flow

```
Project 생성

↓

Review 생성

↓

Decision

↓

Outcome

↓

Memory 저장

↓

다음 Review
```

이 Flow는 모든 Playbook에서 동일하다.

---

# User Journey

## 1. 프로젝트 생성

사용자

↓

보험 자동 조회(API)

↓

Insurance Project 생성

↓

AI 초기 분석

예시

```
보험 6건

월 보험료

182,000원

보장 적정

중복 보장 일부 존재
```

---

## 2. 평상시

사용자는 앱을 거의 사용하지 않는다.

Decision OS는 사용자의 현재 상태를 유지한다.

---

## 3. 이벤트 발생

예시

* 병원 방문
* 수술
* 보험 갱신
* 약관 변경

사용자는

```
병원에 다녀왔어요
```

버튼을 누른다.

또는

영수증을 촬영한다.

---

## 4. Event Intake

입력 최소화가 핵심이다.

예시

```
영수증 촬영

↓

OCR

↓

병원명

진료일

금액

진료 유형 추출

↓

사용자 확인

↓

이벤트 생성
```

AI는 사용자가 긴 내용을 입력하지 않도록 도와준다.

---

## 5. Review 생성

예시

```
청구 가능한 보험

2건

필요 서류

- 진단서

- 입퇴원 확인서

- 영수증

추천

청구 진행
```

---

## 6. Decision

사용자는

```
채택

보류

무시
```

중 하나를 선택한다.

Decision가 저장된다.

---

## 7. Outcome

예시

```
보험금

320만원 지급
```

Outcome이 저장된다.

---

## 8. Memory

Review

↓

Decision

↓

Outcome

을 하나의 Timeline으로 저장한다.

이후 AI는 과거 Decision을 참고하여 새로운 Review를 생성한다.

---

# Screen Structure

## Home

목적

현재 검토가 필요한 내용을 보여준다.

구성

* 새로운 Review
* 최근 Decision
* 최근 Outcome
* 프로젝트 목록

---

## Project

보험 프로젝트 현황

예시

* 보험 건강도
* 월 보험료
* 보험 개수
* 다음 Review
* 최근 변경사항

---

## Review

AI 검토 화면

포함 내용

* 현재 상황
* AI 판단
* 근거
* 위험 요소
* 추천 Action

---

## Decision

사용자 선택

* 채택
* 보류
* 무시

선택 결과는 Memory에 저장된다.

---

## Memory

과거 Review

↓

Decision

↓

Outcome

을 시간순으로 확인한다.

---

# Insurance Playbook

## 목적

보험을 이해하기 쉽게 관리하고

결정이 필요한 순간마다 AI Review를 제공한다.

---

## 주요 기능

### 보험 자동 조회

보험 API 연동

↓

가입 보험 프로젝트 생성

---

### 보험 건강도

예시

```
보험 건강도

92점
```

구성 요소

* 보장 적절성
* 중복 여부
* 보험료 수준
* 갱신 위험

---

### 보험금 청구 지원

사용자

↓

영수증 촬영

↓

OCR

↓

청구 가능한 보험 분석

↓

필요 서류 안내

↓

청구 완료 기록

---

### Review Trigger

Review가 생성되는 대표 상황

* 보험 갱신
* 약관 변경
* 병원 방문
* 청구 완료
* 사용자의 수동 요청

---

# AI 역할

AI는 답변만 하지 않는다.

AI는

* 현재 상태 분석
* Review 생성
* Decision 이유 기록
* Outcome 회고
* 다음 Review 시점 판단

을 수행한다.

---

# Decision Memory

저장 항목

```
Context

Review

Decision

Reason

Outcome

Retrospective
```

Memory는 다음 Review 생성 시 활용된다.

---

# External Integrations (MVP)

보험

* 보험 조회 API
* OCR
* LLM

OCR는 입력 피로를 줄이기 위한 용도로 사용한다.

완전 자동 감지가 목적이 아니다.

---

# Future Playbooks

동일한 Decision Engine을 사용한다.

```
Insurance

Career

Investment

Home

Study
```

Playbook만 추가하여 확장한다.

---

# Success Metrics

MVP 성공 기준

* 보험 프로젝트 생성 완료
* 보험 자동 조회 성공
* Review 생성 성공
* Decision 저장 성공
* 청구 지원 성공
* Memory 저장 성공

---

# Non Goals (MVP 제외)

다음 기능은 MVP 범위에 포함하지 않는다.

* 자동 보험금 청구
* 보험사별 심사 자동화
* 다중 Playbook 연동
* AI가 사용자를 대신하여 의사결정
* 완전 자동 이벤트 감지

---

# Long-term Vision

Decision OS는 보험 서비스가 아니다.

보험은 첫 번째 Playbook이다.

장기적으로는 사용자의 중요한 의사결정을 하나의 플랫폼에서 관리한다.

```
Decision OS

├ Insurance
├ Career
├ Investment
├ Home
└ Study
```

모든 Playbook은 동일한 Decision Engine 위에서 동작하며,

사용자의 과거 Decision과 Outcome을 기반으로 점점 더 개인화된 Review를 제공하는 것이 최종 목표이다.
