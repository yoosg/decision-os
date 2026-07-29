#!/usr/bin/env bash
#
# Firebase App Distribution 으로 Android 테스트 빌드를 배포하는 스크립트.
#
# 사전 준비 (최초 1회):
#   1) Firebase CLI 설치:   npm install -g firebase-tools
#   2) 로그인:              firebase login
#   3) Firebase 콘솔에서 이 앱의 Android App ID 확인
#      (프로젝트 설정 > 내 앱 > "앱 ID", 형식: 1:1234567890:android:abcdef...)
#   4) 콘솔 > App Distribution 에서 테스터 그룹 생성 (예: "testers")
#
# 사용법:
#   FIREBASE_ANDROID_APP_ID="1:xxxx:android:yyyy" \
#   ./scripts/distribute_appdistribution.sh
#
# 필수 환경변수 (앱이 --dart-define 없이 실행되면 시작 즉시 크래시함):
#   SUPABASE_URL        Supabase 프로젝트 URL
#   SUPABASE_ANON_KEY   Supabase anon 키
#
# 옵션 환경변수:
#   FASTAPI_URL     백엔드 주소 (기본: Railway 배포면 백엔드 URL 권장, 미지정 시 앱 기본값 localhost:8000)
#   TESTER_GROUPS   테스터 그룹 별칭 (기본: "testers")
#   RELEASE_NOTES   릴리스 노트 (기본: git 최신 커밋 메시지)
#
set -euo pipefail

cd "$(dirname "$0")/.."   # mobile/ 디렉토리로 이동

: "${FIREBASE_ANDROID_APP_ID:?FIREBASE_ANDROID_APP_ID 를 설정하세요 (Firebase 콘솔의 Android App ID)}"
: "${SUPABASE_URL:?SUPABASE_URL 를 설정하세요 (없으면 앱이 실행 즉시 크래시함)}"
: "${SUPABASE_ANON_KEY:?SUPABASE_ANON_KEY 를 설정하세요 (없으면 앱이 실행 즉시 크래시함)}"
FASTAPI_URL="${FASTAPI_URL:-}"
TESTER_GROUPS="${TESTER_GROUPS:-testers}"
RELEASE_NOTES="${RELEASE_NOTES:-$(git log -1 --pretty=%B 2>/dev/null || echo 'test build')}"

DART_DEFINES=(
  --dart-define=SUPABASE_URL="$SUPABASE_URL"
  --dart-define=SUPABASE_ANON_KEY="$SUPABASE_ANON_KEY"
)
if [[ -n "$FASTAPI_URL" ]]; then
  DART_DEFINES+=(--dart-define=FASTAPI_URL="$FASTAPI_URL")
fi

echo "▶ 1/3 flutter pub get"
flutter pub get

echo "▶ 2/3 release APK 빌드 (flutter build apk --release)"
flutter build apk --release "${DART_DEFINES[@]}"

APK_PATH="build/app/outputs/flutter-apk/app-release.apk"
if [[ ! -f "$APK_PATH" ]]; then
  echo "✗ APK를 찾을 수 없습니다: $APK_PATH" >&2
  exit 1
fi

echo "▶ 3/3 Firebase App Distribution 업로드"
firebase appdistribution:distribute "$APK_PATH" \
  --app "$FIREBASE_ANDROID_APP_ID" \
  --groups "$TESTER_GROUPS" \
  --release-notes "$RELEASE_NOTES"

echo "✅ 배포 완료 — 테스터에게 설치 초대 메일이 발송됩니다."
