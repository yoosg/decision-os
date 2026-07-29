# Decision OS PRD Update Guide (AI Research Playbook)

## 목적

기존 Decision OS의 철학과 Core Loop는 유지한다.

첫 번째 Playbook만 **Insurance → AI Research**로 변경한다.

제품 방향은 **"오늘 중요한 AI 뉴스"**가 아니라 **"오늘 내가 배워야 할 AI
기술"**이다.

------------------------------------------------------------------------

# 유지 사항

## Decision OS Core

``` text
Event
 ↓
Review
 ↓
Decision
 ↓
Outcome
 ↓
Memory
```

공통 Core는 변경하지 않는다.

-   Event : 의사결정이 필요한 상황
-   Review : 판단을 위한 근거
-   Decision : 사용자 선택
-   Outcome : 실제 결과
-   Memory : 다음 추천을 위한 기억

AI Research의 **Signal은 Event의 도메인 표현**이다.

------------------------------------------------------------------------

# 변경 사항

## First Playbook

Insurance → AI Research

MVP 대상

-   AI를 사용하는 개발자
-   AI Engineer 준비
-   AI Agent / LLM App 개발자

------------------------------------------------------------------------

# Product Vision

> 오늘 수백 개의 AI 정보를 보여주는 서비스가 아니라, 오늘 내가 배워야 할
> AI 기술을 추천하고 이해·학습·적용까지 돕는 AI Research OS

------------------------------------------------------------------------

# User Flow

``` text
Daily Brief
 ↓
Signal
 ↓
Research Review
 ↓
Learn Now / Queue / Ignore
 ↓
Learning
 ↓
Outcome
 ↓
Memory
```

------------------------------------------------------------------------

# Signal

Signal은 기사 하나가 아니다.

하나의 기술 또는 변화에 대한 여러 출처를 묶은 Decision Event이다.

예시

    Claude Code Update

    ├ Official Blog
    ├ Github
    ├ Reddit
    ├ HN
    ├ Youtube

------------------------------------------------------------------------

# Research Review

Review는 단순 요약이 아니다.

사용자가 "배울지 말지" 결정할 수 있도록 충분한 설명을 제공해야 한다.

필수 포함 항목

-   한 줄 정의
-   핵심 개념 설명
-   해결하는 문제
-   왜 중요한가
-   기존 기술과 차이
-   사용자(Project/Role) 관련성
-   학습 목표
-   예상 학습 시간
-   난이도
-   실무 적용 가능성
-   위험 요소
-   추천 이유
-   참고 출처

사용자는 Review 하나만 읽어도 해당 기술의 기본 개념을 이해할 수 있어야
한다.

------------------------------------------------------------------------

# Decision

CTA는 다음 세 가지다.

-   Learn Now
-   Queue
-   Ignore

Queue는

-   Today
-   This Week
-   Later

정도로 단순하게 시작한다.

------------------------------------------------------------------------

# Learning

Learn Now를 선택하면

-   공식 문서
-   핵심 자료
-   Github
-   실습 예제
-   적용 아이디어

를 기반으로 Learning Path를 생성한다.

------------------------------------------------------------------------

# Outcome

Outcome 상태

-   Completed
-   Applied
-   Dropped
-   Not Useful

피드백

-   유용했는가
-   적용했는가
-   실제 학습 시간
-   메모

------------------------------------------------------------------------

# Memory

Memory는 다음 추천을 위한 사용자 모델이다.

구성

-   Preference
-   Skill
-   Project
-   Decision History
-   Outcome History

Memory를 기반으로 Daily Brief와 추천 품질을 개선한다.

------------------------------------------------------------------------

# Agent Workflow

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

각 Agent는 사용자에게 노출되지 않는 내부 Workflow이다.

------------------------------------------------------------------------

# MVP Scope

포함

-   온보딩
-   Daily Brief
-   Signal 생성
-   Research Review
-   Learn / Queue / Ignore
-   Learning Path
-   Outcome 기록
-   Memory
-   개인화 추천

제외

-   보험 Playbook
-   투자 / 커리어 Playbook
-   Sandbox 실행
-   Github 자동 수정
-   완전 자율 Agent

------------------------------------------------------------------------

# 제품 원칙

## Review Before Action

충분히 이해한 뒤 결정한다.

## Recommendation, Not Automation

AI는 추천하고 사용자가 결정한다.

## Explain Before Recommend

추천 전에 기술을 설명한다.

## Decision Must Lead To Learning

결정은 학습으로 이어져야 한다.

## Memory Improves Recommendation

모든 결과는 다음 추천 품질을 높인다.

------------------------------------------------------------------------

# BMAD 수정 요청

1.  Decision OS Core는 유지한다.
2.  첫 Playbook을 AI Research로 변경한다.
3.  Insurance 요구사항은 Future Playbooks로 이동한다.
4.  Research Review에 기술 설명을 반드시 포함한다.
5.  제품 방향은 "AI 뉴스"가 아니라 "오늘 배워야 할 AI"이다.
6.  Recommendation → Learning → Outcome → Memory Loop를 중심으로 PRD를
    수정한다.
