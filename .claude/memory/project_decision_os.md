---
name: project-decision-os-state
description: decision-os 프로젝트의 현재 상태 — 완료된 아티팩트, 핵심 결정, 다음 단계
metadata:
  type: project
---

PRD와 아키텍처 스파인이 완성된 상태.

**완료된 아티팩트:**
- PRD (final): `_bmad-output/planning-artifacts/prds/prd-decision-os-2026-07-21/prd.md`
- Architecture Spine (final): `_bmad-output/planning-artifacts/architecture/architecture-decision-os-2026-07-21/ARCHITECTURE-SPINE.md`
- Architecture Overview (비개발자용): `_bmad-output/planning-artifacts/architecture/architecture-decision-os-2026-07-21/overview.md`

**핵심 결정 요약:**
- 제품: 보험 Playbook을 첫 번째로 하는 개인용 의사결정 OS (한국 시장 전용)
- 스택: Next.js + FastAPI + Supabase, Railway 배포
- 데이터 모델: Project → Review → Decision → Outcome (공통 루프) + Playbook별 테이블
- AI: ReviewContextBuilder + LLM Provider Interface(OpenAI MVP) + pgvector RAG
- Review 실행: 비동기 (BackgroundTasks, pending→processing→completed|failed)
- MVP 첫 기능: 병원 영수증 → 청구 가능 보험 분석
- Memory 테이블: MVP 제외, 실운용 후 도입

**다음 단계:**
- `/bmad-create-epics-and-stories` 또는 `/bmad-ux` 중 선택

**Why:** 두 문서 모두 완료됐으며 새 컨텍스트에서 에픽/스토리 또는 UX 설계로 이어질 예정.
**How to apply:** 새 컨텍스트에서 위 파일 경로를 참조해 컨텍스트를 복원할 것.
