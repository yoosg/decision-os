# 배포 가이드 (Deployment)

Decision OS를 실제로 띄우는 절차. **web + backend는 Railway**, **Flutter 앱은 Firebase App Distribution(테스트 배포)** 로 나간다.

> 비유: 요리(코드)는 다 됐고, 이제 **손님상에 내가는 서빙** 단계다.
> web/backend는 "가게(Railway)"에 올리고, 앱은 "시식단(테스터)"에게만 돌린다.

---

## 0. 준비물 (계정/도구)

| 항목 | 용도 | 확인 |
|------|------|------|
| GitHub 계정 | 코드 저장 + Railway 자동배포 연동 | - |
| Railway 계정 | web/backend 호스팅 (https://railway.app) | - |
| Supabase 프로젝트 | 이미 사용 중 (URL/키 준비돼 있음) | ✅ |
| OpenAI API 키 | LLM/임베딩 | - |
| Firebase 프로젝트 | 앱 테스트 배포 + FCM 푸시 | ✅ (mobile 이미 연동) |
| Firebase CLI | App Distribution 업로드 (`npm i -g firebase-tools`) | - |

**배포 순서 의존성(중요):** 백엔드 먼저 → 백엔드 URL 확보 → 웹에 그 URL 넣고 배포 → 백엔드 CORS에 웹 URL 등록. 한 번 왕복한다.

---

## 1. GitHub 저장소 만들고 push

현재 로컬 `main` 브랜치만 있고 원격이 없다. 먼저 GitHub로 올린다.

```bash
# (1) 배포할 변경사항 커밋 — 지금 커밋 안 된 변경이 여러 개 있음
git add -A
git commit -m "chore: 배포 설정 추가 및 Epic 6 작업 반영"

# (2) GitHub에 비공개 저장소 생성 + push (gh CLI 사용 시)
gh repo create decision-os --private --source=. --remote=origin --push

#  또는 웹에서 빈 repo를 만든 뒤:
# git remote add origin https://github.com/<네계정>/decision-os.git
# git push -u origin main
```

> 🔒 안전 확인 완료: `.gitignore`가 `.env`/`.env.local`/서비스계정 파일을 모두 제외한다. 비밀키는 GitHub에 올라가지 않는다. (env는 Railway 대시보드에 직접 입력한다.)

---

## 2. Railway — 백엔드(`api/`) 서비스

Railway는 **모노레포**를 서비스별 "Root Directory"로 나눠 배포한다. 백엔드/웹을 한 프로젝트 안 두 서비스로 만든다.

1. Railway 대시보드 → **New Project** → **Deploy from GitHub repo** → `decision-os` 선택
2. 생성된 서비스 → **Settings**
   - **Root Directory** = `api`
   - Build/Start는 `api/railway.json`이 자동 적용됨:
     - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
     - Healthcheck: `/api/v1/health`
3. **Variables** 탭에 아래 환경변수 입력 (`api/.env.example` 참고):

   | 변수 | 값 |
   |------|-----|
   | `SUPABASE_URL` | Supabase 프로젝트 URL |
   | `SUPABASE_SERVICE_ROLE_KEY` | Supabase service_role 키 |
   | `SUPABASE_JWT_SECRET` | Supabase JWT 시크릿 (없으면 인증 API 전부 401) |
   | `OPENAI_API_KEY` | OpenAI 키 |
   | `OPENAI_MODEL` | `gpt-4o` |
   | `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` |
   | `FIREBASE_SERVICE_ACCOUNT_JSON` | 서비스계정 JSON **전체를 한 줄 문자열로** (푸시 안 쓰면 비워도 됨) |
   | `CORS_ORIGINS` | 일단 `["http://localhost:3000"]` — 웹 배포 후 4단계에서 수정 |
   | `COLLECTOR_MODE` | `real` |

4. **Settings → Networking → Generate Domain** 으로 공개 URL 발급.
   → 예: `https://decision-os-api.up.railway.app` — **이 주소를 복사해 둔다(웹에서 사용).**
5. 배포 로그에서 `APScheduler started`, `Supabase connection verified` 뜨는지 확인.
   브라우저로 `https://<백엔드주소>/api/v1/health` 열어 응답 오면 성공.

> ⚠️ 스케줄러 주의: 백엔드는 in-process 스케줄러(APScheduler)를 돌린다(매일 06/09/10/20시 KST 작업). **인스턴스를 여러 개로 늘리면 작업이 중복 실행**되므로 `numReplicas: 1` 유지(railway.json에 이미 설정됨).

---

## 3. Railway — 웹(`web/`) 서비스

1. 같은 프로젝트에서 **New → GitHub Repo(같은 repo)** 로 서비스 하나 더 추가
2. **Settings → Root Directory** = `web` (`web/railway.json` 자동 적용: `npm run start`)
3. **Variables**:

   | 변수 | 값 |
   |------|-----|
   | `NEXT_PUBLIC_SUPABASE_URL` | Supabase URL |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon 키 |
   | `NEXT_PUBLIC_FASTAPI_URL` | **2단계에서 복사한 백엔드 주소** (예: `https://decision-os-api.up.railway.app`) |

   > 🧠 프론트 개발자 포인트: `NEXT_PUBLIC_*` 값은 **빌드 시점에 번들 안으로 박힌다**(런타임에 안 읽음). 그래서 이 값들은 **빌드 전에 반드시 세팅**돼 있어야 하고, 나중에 바꾸면 **재배포(재빌드)** 해야 반영된다. 마치 인쇄된 전단지 — 주소 바꾸려면 다시 찍어야 한다.

4. **Generate Domain** 으로 웹 공개 URL 발급 → 예: `https://decision-os-web.up.railway.app`

---

## 4. CORS 연결 (백엔드 ↔ 웹)

웹 주소가 나왔으니 백엔드가 그 웹을 허용하도록 한다.

1. **백엔드 서비스 Variables** → `CORS_ORIGINS` 수정:
   ```
   ["https://decision-os-web.up.railway.app"]
   ```
   (로컬도 같이 허용하려면: `["http://localhost:3000","https://decision-os-web.up.railway.app"]`)
2. 저장하면 백엔드 자동 재배포됨.
3. 웹에서 로그인 → 온보딩 → 데일리 브리핑까지 실제로 API가 붙는지 확인.

---

## 5. Flutter 앱 — Firebase App Distribution (테스트 배포)

앱은 스토어 정식 배포가 아니라 **테스터에게만** APK를 돌린다.

**최초 1회 세팅**
1. `npm install -g firebase-tools` → `firebase login`
2. Firebase 콘솔 → 프로젝트 설정 → 내 앱에서 **Android App ID** 확인
   (형식: `1:1234567890:android:abcdef...`)
3. 콘솔 → **App Distribution** → 테스터 그룹 생성(예: `testers`) + 테스터 이메일 추가

**배포 실행** (`mobile/` 기준)
```bash
FIREBASE_ANDROID_APP_ID="1:xxxx:android:yyyy" \
SUPABASE_URL="https://xxxx.supabase.co" \
SUPABASE_ANON_KEY="your-anon-key" \
FASTAPI_URL="https://decision-os-api.up.railway.app" \
./scripts/distribute_appdistribution.sh
```
- 스크립트가 `flutter build apk --release` → Firebase 업로드까지 수행
- 테스터에게 설치 초대 메일 발송됨
- 릴리스 노트/그룹 바꾸려면: `RELEASE_NOTES="..." TESTER_GROUPS="qa" ...`

> ⚠️ 앱은 실행 시 `SUPABASE_URL`, `SUPABASE_ANON_KEY` 를 `--dart-define`으로 받아야 하며,
> **없으면 시작하자마자 크래시**한다(안전장치). 백엔드 주소는 `FASTAPI_URL` 키(기본값 `localhost:8000`).
> 위 스크립트가 이 세 값을 환경변수로 받아 자동으로 dart-define에 넣어준다.

---

## 6. 배포 후 점검 체크리스트

- [ ] `GET /api/v1/health` 200 응답
- [ ] 백엔드 로그에 `Supabase connection verified` + `APScheduler started`
- [ ] 웹 로그인/온보딩 정상 (CORS 에러 없음 — 브라우저 콘솔 확인)
- [ ] 웹 네트워크 탭에서 API 요청이 `localhost`가 아닌 Railway 백엔드로 감
- [ ] 앱 테스터가 초대 메일로 설치 성공

### 자주 나는 문제
| 증상 | 원인 | 해결 |
|------|------|------|
| 웹이 계속 `localhost:8000` 호출 | `NEXT_PUBLIC_FASTAPI_URL` 미설정 or 빌드 후 변경 | 값 세팅 후 **재배포** |
| 브라우저 CORS 에러 | 백엔드 `CORS_ORIGINS`에 웹 도메인 없음 | 4단계 수정 |
| 인증 API가 401 | `SUPABASE_JWT_SECRET` 누락 | 백엔드 Variables 추가 |
| 스케줄 작업 2번 실행 | 인스턴스 2개 이상 | `numReplicas: 1` 유지 |
| 푸시 안 감 | `FIREBASE_SERVICE_ACCOUNT_JSON` 누락/형식오류 | JSON 전체를 한 줄로 재입력 |
