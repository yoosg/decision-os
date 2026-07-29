import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'providers/highlighted_signal_provider.dart';

/// FCM 메시지 → 액션 매핑 (순수 로직 분리, 테스트 용이성).
///
/// 딥링크는 **항상 `/home` 랜딩**(UX-DR16) — Research Review 직접 이동 금지(AC-1).

String? _signalId(RemoteMessage message) {
  final raw = message.data['signal_id'];
  if (raw is String && raw.isNotEmpty) return raw;
  return null;
}

/// background(onMessageOpenedApp) / terminated(getInitialMessage) 탭 처리.
/// signal_id가 있으면 홈으로 라우팅 후 해당 카드 하이라이트 set (AC-1, AC-5).
void handleMessageOpened(RemoteMessage message, GoRouter router, WidgetRef ref) {
  final signalId = _signalId(message);
  if (signalId == null) return;
  // 항상 홈 랜딩 (Research Review 직접 딥링크 금지)
  router.go('/home');
  // 라우팅 직후 하이라이트 set — 홈이 마운트되며 watch (Task 10.3)
  ref.read(highlightedSignalProvider.notifier).set(signalId);
}

/// foreground(onMessage) 수신 처리 — 내비게이션 없음(AC-4, 현재 화면 유지).
/// signal_id가 있으면 하이라이트만 set(홈에 있을 때만 카드 강조가 보임).
void handleForegroundMessage(RemoteMessage message, WidgetRef ref) {
  final signalId = _signalId(message);
  if (signalId == null) return;
  ref.read(highlightedSignalProvider.notifier).set(signalId);
}
