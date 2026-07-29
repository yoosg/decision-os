// 참고: mobile/lib/features/profile/screens/profile_screen.dart는 이 스토리와 무관한
// app_settings 패키지 버전 드리프트(AppSettings.openNotificationSettings 미존재, 5.2.0 기준)로
// 컴파일이 깨져 있다(사전 존재 이슈, Story 5.1 범위 밖). 이 테스트는 해당 파일을 import하지 않도록
// 프로필 탭을 플레이스홀더 Scaffold로 대체한 로컬 라우터를 사용한다.

import 'package:decision_os/core/theme/app_theme.dart';
import 'package:decision_os/features/history/screens/history_screen.dart';
import 'package:decision_os/features/home/screens/home_screen.dart';
import 'package:decision_os/features/queue/providers/queue_provider.dart';
import 'package:decision_os/features/queue/screens/queue_screen.dart';
import 'package:decision_os/features/queue/widgets/queue_item.dart';
import 'package:decision_os/features/queue/widgets/reschedule_sheet.dart';
import 'package:decision_os/features/shell/shell_scaffold.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

Widget _buildTestApp(Widget child) => MaterialApp(
      theme: buildAppTheme(),
      home: Scaffold(body: child),
    );

QueueItemData _item({
  String decisionId = 'd1',
  String signalId = 's1',
  String title = 'LLM Agents 최신 동향',
  String queueTiming = 'today',
  DateTime? updatedAt,
}) =>
    QueueItemData(
      decisionId: decisionId,
      signalId: signalId,
      title: title,
      queueTiming: queueTiming,
      updatedAt: updatedAt ?? DateTime.now(),
    );

class _FakeQueueItems extends QueueItems {
  final List<QueueItemData> _initial;
  _FakeQueueItems(this._initial);

  @override
  Future<List<QueueItemData>> build() async => _initial;
}

GoRouter _buildTestRouter({required List<QueueItemData> queueItems}) {
  final homeNavKey = GlobalKey<NavigatorState>(debugLabel: 'home');
  final queueNavKey = GlobalKey<NavigatorState>(debugLabel: 'queue');
  final historyNavKey = GlobalKey<NavigatorState>(debugLabel: 'history');
  final profileNavKey = GlobalKey<NavigatorState>(debugLabel: 'profile');

  return GoRouter(
    initialLocation: '/queue',
    routes: [
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) => ShellScaffold(navigationShell: shell),
        branches: [
          StatefulShellBranch(
            navigatorKey: homeNavKey,
            routes: [GoRoute(path: '/home', builder: (_, __) => const HomeScreen())],
          ),
          StatefulShellBranch(
            navigatorKey: queueNavKey,
            routes: [
              GoRoute(
                path: '/queue',
                builder: (_, __) => const QueueScreen(),
                routes: [
                  GoRoute(
                    path: 'review/:signalId',
                    builder: (_, state) => Scaffold(
                      body: Text('Research Review: ${state.pathParameters['signalId']}'),
                    ),
                  ),
                ],
              ),
            ],
          ),
          StatefulShellBranch(
            navigatorKey: historyNavKey,
            routes: [GoRoute(path: '/history', builder: (_, __) => const HistoryScreen())],
          ),
          StatefulShellBranch(
            navigatorKey: profileNavKey,
            routes: [
              GoRoute(
                path: '/profile',
                builder: (_, __) => const Scaffold(body: Text('Profile placeholder')),
              ),
            ],
          ),
        ],
      ),
    ],
  );
}

void main() {
  group('QueueItem', () {
    testWidgets('queueTiming에 맞는 배지 텍스트가 표시된다', (tester) async {
      await tester.pumpWidget(_buildTestApp(QueueItem(
        title: 'LLM Agents 최신 동향',
        queueTiming: 'this_week',
        estimatedMinutes: 30,
        isOverdue: false,
        onTap: () {},
        onReschedule: () {},
      )));
      expect(find.text('THIS WEEK'), findsOneWidget);
    });

    testWidgets('isOverdue=false면 미완료 배지가 없다', (tester) async {
      await tester.pumpWidget(_buildTestApp(QueueItem(
        title: '제목',
        queueTiming: 'today',
        estimatedMinutes: 30,
        isOverdue: false,
        onTap: () {},
        onReschedule: () {},
      )));
      expect(find.text('미완료'), findsNothing);
    });

    testWidgets('isOverdue=true면 미완료 배지가 표시된다', (tester) async {
      await tester.pumpWidget(_buildTestApp(QueueItem(
        title: '제목',
        queueTiming: 'today',
        estimatedMinutes: 30,
        isOverdue: true,
        onTap: () {},
        onReschedule: () {},
      )));
      expect(find.text('미완료'), findsOneWidget);
    });

    testWidgets('메인 탭과 일정 변경 탭이 서로 독립된 콜백을 호출한다', (tester) async {
      var tapped = false;
      var rescheduled = false;
      await tester.pumpWidget(_buildTestApp(QueueItem(
        title: '제목',
        queueTiming: 'today',
        estimatedMinutes: 30,
        isOverdue: false,
        onTap: () => tapped = true,
        onReschedule: () => rescheduled = true,
      )));

      await tester.tap(find.byType(InkWell).first);
      expect(tapped, isTrue);
      expect(rescheduled, isFalse);

      await tester.tap(find.byType(TextButton));
      expect(rescheduled, isTrue);
      expect(tapped, isTrue); // 여전히 1회 호출 상태 유지 — 서로 간섭하지 않음
    });

    testWidgets('Semantics composite label — 메인/일정 변경 각각 별도로 부여된다', (tester) async {
      final handle = tester.ensureSemantics();
      await tester.pumpWidget(_buildTestApp(QueueItem(
        title: 'LLM Agents 최신 동향',
        queueTiming: 'today',
        estimatedMinutes: 30,
        isOverdue: false,
        onTap: () {},
        onReschedule: () {},
      )));

      expect(
        find.bySemanticsLabel('Today 예약됨, LLM Agents 최신 동향, 약 30분'),
        findsOneWidget,
      );
      expect(
        find.bySemanticsLabel('일정 변경 — LLM Agents 최신 동향'),
        findsOneWidget,
      );
      handle.dispose();
    });
  });

  group('RescheduleSheet', () {
    testWidgets('현재 선택된 타이밍 옵션에 강조 보더가 적용된다', (tester) async {
      await tester.pumpWidget(_buildTestApp(const RescheduleSheet(currentTiming: 'later')));

      final laterButton = tester.widget<OutlinedButton>(
        find.widgetWithText(OutlinedButton, 'Later'),
      );
      final todayButton = tester.widget<OutlinedButton>(
        find.widgetWithText(OutlinedButton, 'Today'),
      );

      final laterSide = laterButton.style?.side?.resolve({});
      final todaySide = todayButton.style?.side?.resolve({});
      expect(laterSide?.width, 1.5);
      expect(todaySide, isNull);
    });

    testWidgets('옵션 탭 시 Navigator.pop으로 선택값이 반환된다', (tester) async {
      String? result;
      await tester.pumpWidget(MaterialApp(
        theme: buildAppTheme(),
        home: Builder(
          builder: (context) => Scaffold(
            body: ElevatedButton(
              onPressed: () async {
                result = await showRescheduleSheet(context, currentTiming: 'today');
              },
              child: const Text('open'),
            ),
          ),
        ),
      ));

      await tester.tap(find.text('open'));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(OutlinedButton, 'This Week'));
      await tester.pumpAndSettle();

      expect(result, 'this_week');
    });
  });

  group('QueueScreen 그룹핑', () {
    testWidgets('항목이 있는 그룹만 헤딩이 표시되고 빈 그룹은 숨겨진다', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            queueItemsProvider.overrideWith(() => _FakeQueueItems([
                  _item(decisionId: 'd1', queueTiming: 'today'),
                  _item(decisionId: 'd2', queueTiming: 'later'),
                ])),
            estimatedLearningMinutesProvider.overrideWith((ref) async => 30),
          ],
          child: const MaterialApp(home: QueueScreen()),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Today'), findsOneWidget);
      expect(find.text('Later'), findsOneWidget);
      expect(find.text('This Week'), findsNothing);
    });

    testWidgets('큐 항목이 하나도 없으면 빈 상태 메시지가 표시된다', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            queueItemsProvider.overrideWith(() => _FakeQueueItems([])),
            estimatedLearningMinutesProvider.overrideWith((ref) async => 30),
          ],
          child: const MaterialApp(home: QueueScreen()),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.text('큐에 저장된 학습 항목이 없습니다. Signal을 읽고 Queue를 선택하면 여기에 저장됩니다.'),
        findsOneWidget,
      );
    });
  });

  group('큐 브랜치 라우팅', () {
    testWidgets('QueueItem 탭 시 /queue/review/:signalId로 push되고 큐 탭(index 1)이 유지된다',
        (tester) async {
      final router = _buildTestRouter(queueItems: [_item(signalId: 'sig-42')]);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            queueItemsProvider.overrideWith(
              () => _FakeQueueItems([_item(signalId: 'sig-42')]),
            ),
            estimatedLearningMinutesProvider.overrideWith((ref) async => 30),
          ],
          child: MaterialApp.router(routerConfig: router),
        ),
      );
      await tester.pumpAndSettle();

      final navBarBefore = tester.widget<BottomNavigationBar>(find.byType(BottomNavigationBar));
      expect(navBarBefore.currentIndex, 1);

      await tester.tap(find.byType(InkWell).first);
      await tester.pumpAndSettle();

      expect(find.text('Research Review: sig-42'), findsOneWidget);
      final navBarAfter = tester.widget<BottomNavigationBar>(find.byType(BottomNavigationBar));
      expect(navBarAfter.currentIndex, 1);
    });
  });
}
