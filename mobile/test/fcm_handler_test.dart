import 'package:decision_os/features/notifications/fcm_message_handler.dart';
import 'package:decision_os/features/notifications/providers/highlighted_signal_provider.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

/// go() 호출을 기록하는 테스트용 GoRouter (실제 내비게이션 없이 목적지만 캡처).
/// GoRouter 생성자를 super로 호출할 수 없어 implements + noSuchMethod로 구성.
class _RecordingRouter implements GoRouter {
  final List<String> goCalls = [];

  @override
  void go(String location, {Object? extra}) => goCalls.add(location);

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('unused in test: ${invocation.memberName}');
}

/// Consumer로 WidgetRef를 캡처해 반환한다.
Future<WidgetRef> _captureRef(WidgetTester tester) async {
  late WidgetRef captured;
  await tester.pumpWidget(
    ProviderScope(
      child: Consumer(
        builder: (context, ref, _) {
          captured = ref;
          return const SizedBox();
        },
      ),
    ),
  );
  return captured;
}

void main() {
  group('handleMessageOpened (background/terminated 탭)', () {
    testWidgets('signal_id 존재 시 /home 라우팅 + 하이라이트 set', (tester) async {
      final ref = await _captureRef(tester);
      final router = _RecordingRouter();

      handleMessageOpened(
        const RemoteMessage(data: {'type': 'daily_brief', 'signal_id': 's1'}),
        router,
        ref,
      );

      // 항상 /home 랜딩 — Research Review 경로로 직접 이동하지 않음 (AC-1)
      expect(router.goCalls, ['/home']);
      expect(router.goCalls.any((l) => l.contains('/review/')), isFalse);
      expect(ref.read(highlightedSignalProvider), 's1');
    });

    testWidgets('signal_id 없으면 라우팅하지 않음', (tester) async {
      final ref = await _captureRef(tester);
      final router = _RecordingRouter();

      handleMessageOpened(const RemoteMessage(data: {}), router, ref);

      expect(router.goCalls, isEmpty);
      expect(ref.read(highlightedSignalProvider), isNull);
    });
  });

  group('handleForegroundMessage (foreground 수신)', () {
    testWidgets('signal_id로 highlightedSignalProvider set (내비게이션 없음)', (tester) async {
      final ref = await _captureRef(tester);

      handleForegroundMessage(
        const RemoteMessage(data: {'type': 'queue_reminder', 'signal_id': 's2'}),
        ref,
      );

      expect(ref.read(highlightedSignalProvider), 's2');
    });

    testWidgets('signal_id 없으면 아무 것도 하지 않음', (tester) async {
      final ref = await _captureRef(tester);

      handleForegroundMessage(const RemoteMessage(data: {}), ref);

      expect(ref.read(highlightedSignalProvider), isNull);
    });
  });

  group('HighlightedSignal notifier', () {
    test('set/clear 동작', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      expect(container.read(highlightedSignalProvider), isNull);

      container.read(highlightedSignalProvider.notifier).set('s1');
      expect(container.read(highlightedSignalProvider), 's1');

      container.read(highlightedSignalProvider.notifier).clear();
      expect(container.read(highlightedSignalProvider), isNull);
    });
  });
}
