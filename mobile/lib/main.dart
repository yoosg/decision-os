import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';
import 'features/auth/providers/fcm_provider.dart';
import 'features/notifications/fcm_message_handler.dart';
import 'features/onboarding/providers/onboarding_provider.dart';
// firebase_options.dart는 `flutterfire configure` 실행 후 실제 값으로 교체하세요.
import 'firebase_options.dart';

// 데모/로컬: Firebase가 placeholder 설정으로 초기화 실패해도 앱이 죽지 않도록 준비 여부 플래그.
bool firebaseReady = false;

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
  SystemChrome.setSystemUIOverlayStyle(SystemUiOverlayStyle.dark);

  // Firebase 초기화 (FCM용) — firebase_options.dart는 FlutterFire CLI로 생성.
  // ⚠️ placeholder 설정(로컬/데모)에서는 네이티브 FIRApp이 잘못된 GOOGLE_APP_ID로 NSException을
  //    던져 앱이 크래시하며, 이 네이티브 예외는 Dart try/catch로 못 잡는다. 그래서 설정이 실제 값일
  //    때만 초기화하고, placeholder면 스킵한다(FCM 없이 앱은 정상 동작 — AD-5 safe degradation).
  final fbOptions = DefaultFirebaseOptions.currentPlatform;
  final fbConfigured =
      fbOptions.appId != 'PLACEHOLDER' && fbOptions.apiKey != 'PLACEHOLDER';
  if (fbConfigured) {
    try {
      await Firebase.initializeApp(options: fbOptions);
      firebaseReady = true;
      // iOS 알림 권한 요청 (Story 5.3) — 거부해도 앱 정상 동작 (best-effort)
      await FirebaseMessaging.instance.requestPermission();
      // foreground OS 알림 배너 억제 (AC-4 — foreground 알림 미표시)
      await FirebaseMessaging.instance.setForegroundNotificationPresentationOptions(
        alert: false,
        badge: false,
        sound: false,
      );
    } catch (_) {}
  }

  // Supabase 초기화 (Story 1.1 Deferred)
  const supabaseUrl = String.fromEnvironment('SUPABASE_URL');
  const supabaseAnonKey = String.fromEnvironment('SUPABASE_ANON_KEY');
  if (supabaseUrl.isEmpty || supabaseAnonKey.isEmpty) {
    throw StateError(
      'SUPABASE_URL and SUPABASE_ANON_KEY must be set via --dart-define. '
      'Example: flutter run --dart-define=SUPABASE_URL=https://xxx.supabase.co '
      '--dart-define=SUPABASE_ANON_KEY=your-anon-key',
    );
  }
  await Supabase.initialize(
    url: supabaseUrl,
    anonKey: supabaseAnonKey,
  );

  // FCM 토큰 갱신 시 자동 재등록 (Firebase 미초기화 시 스킵)
  if (firebaseReady) {
    FirebaseMessaging.instance.onTokenRefresh.listen(
      (newToken) { registerFcmTokenWithToken(newToken).ignore(); },
      onError: (_) {},
    );
  }

  // 온보딩 완료 여부 읽기 (AC-1, AC-6)
  bool isOnboardingCompleted = false;
  try {
    final prefs = await SharedPreferences.getInstance();
    isOnboardingCompleted = prefs.getBool(kOnboardingCompletedKey) ?? false;
  } catch (_) {}

  runApp(
    ProviderScope(
      overrides: [
        onboardingCompletedProvider.overrideWith((ref) => isOnboardingCompleted),
      ],
      child: const MyApp(),
    ),
  );
}

class MyApp extends ConsumerStatefulWidget {
  const MyApp({super.key});

  @override
  ConsumerState<MyApp> createState() => _MyAppState();
}

class _MyAppState extends ConsumerState<MyApp> {
  StreamSubscription<RemoteMessage>? _onMessageSub;
  StreamSubscription<RemoteMessage>? _onOpenedSub;

  @override
  void initState() {
    super.initState();

    // foreground/background 수신 리스너 (Firebase 미초기화 시 스킵 — 데모 안전)
    if (firebaseReady) {
      // foreground 수신 — OS 알림 미표시 + 홈 하이라이트 (AC-4)
      _onMessageSub = FirebaseMessaging.onMessage.listen(
        (message) => handleForegroundMessage(message, ref),
        onError: (_) {},
      );
      // background(미포커스) 탭 → /home 라우팅 + 하이라이트 (AC-5 And절)
      _onOpenedSub = FirebaseMessaging.onMessageOpenedApp.listen(
        (message) => handleMessageOpened(message, ref.read(appRouterProvider), ref),
        onError: (_) {},
      );
    }

    // terminated 상태에서 탭으로 앱이 열린 경우 — 라우터 준비 후 첫 프레임에서 처리 (AC-5)
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      try {
        final initial = await FirebaseMessaging.instance.getInitialMessage();
        if (initial != null && mounted) {
          handleMessageOpened(initial, ref.read(appRouterProvider), ref);
        }
      } catch (_) {}
    });
  }

  @override
  void dispose() {
    _onMessageSub?.cancel();
    _onOpenedSub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final router = ref.watch(appRouterProvider);
    return MaterialApp.router(
      title: 'Decision OS',
      theme: buildAppTheme(),
      routerConfig: router,
    );
  }
}
