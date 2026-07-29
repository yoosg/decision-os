# Decision OS

AI 리서치 플레이북 기반 개인 의사결정 플랫폼.

## 패키지 구조

```
decision-os/
├── web/          # Next.js 웹 앱 (App Router, TypeScript)
├── api/          # FastAPI 백엔드
├── mobile/       # Flutter iOS/Android 앱
└── _bmad-output/ # 기획 산출물 (개발 대상 아님)
```

## 로컬 실행 방법

### FastAPI 백엔드 (api/)

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 환경변수 설정
uvicorn main:app --reload --port 8000
```

헬스 체크: `GET http://localhost:8000/api/v1/health`

### Next.js 웹 앱 (web/)

```bash
cd web
npm install
cp .env.local.example .env.local   # 환경변수 설정
npm run dev
```

접속: `http://localhost:3000`

### Flutter 앱 (mobile/)

```bash
cd mobile
flutter pub get
flutter run
```

## 환경변수

각 패키지의 `.env.example` / `.env.local.example` 파일을 참고하여 설정하세요.

| 변수 | 위치 | 설명 |
|------|------|------|
| `SUPABASE_URL` | `api/.env` | Supabase 프로젝트 URL |
| `SUPABASE_SERVICE_ROLE_KEY` | `api/.env` | Supabase service_role 키 (서버 전용) |
| `NEXT_PUBLIC_SUPABASE_URL` | `web/.env.local` | Supabase 프로젝트 URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `web/.env.local` | Supabase anon 키 |
| `FASTAPI_BASE_URL` | `web/.env.local` | FastAPI 백엔드 URL |

## 아키텍처

- **읽기**: Supabase SDK 직접 (anon key + JWT + RLS)
- **쓰기**: 반드시 FastAPI 경유 (service_role)
- **상태관리 (Flutter)**: Riverpod 2.x
- **모듈**: FastAPI 단일 앱, Playbook은 내부 라우터/모듈
