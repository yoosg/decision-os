// 참고(queue_test.dart와 동일): profile_screen.dart는 app_settings 버전 드리프트로 컴파일이
// 깨져 있어(사전 존재 이슈, 이 스토리 범위 밖) 라우팅 테스트는 프로필 탭을 플레이스홀더로 대체한다.

import 'package:decision_os/core/theme/app_theme.dart';
import 'package:decision_os/features/history/providers/chain_detail_provider.dart';
import 'package:decision_os/features/history/providers/history_provider.dart';
import 'package:decision_os/features/history/screens/chain_detail_screen.dart';
import 'package:decision_os/features/history/screens/history_screen.dart';
import 'package:decision_os/features/history/widgets/archived_banner.dart';
import 'package:decision_os/features/history/widgets/memory_timeline_item.dart';
import 'package:decision_os/features/shell/shell_scaffold.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

Widget _app(Widget child, {List<Override> overrides = const []}) => ProviderScope(
      overrides: overrides,
      child: MaterialApp(theme: buildAppTheme(), home: Scaffold(body: child)),
    );

void main() {
  group('KST 월 그룹핑/포맷 헬퍼 (18.2)', () {
    test('kstYearMonth — UTC → KST(+9) 월 키', () {
      expect(kstYearMonth(DateTime.utc(2026, 7, 5, 2)), '2026-07');
    });
    test('kstYearMonth — KST 로 다음 달 경계 넘김', () {
      // 2026-06-30T20:00Z + 9h = 2026-07-01 05:00 KST
      expect(kstYearMonth(DateTime.utc(2026, 6, 30, 20)), '2026-07');
    });
    test('formatMonthDivider — 앞자리 0 제거', () {
      expect(formatMonthDivider('2026-07'), '2026년 7월');
    });
    test('formatCardDate — "M월 D일"', () {
      expect(formatCardDate(DateTime.utc(2026, 7, 5, 2)), '7월 5일');
    });
  });

  group('MemoryTimelineItem 도트 스타일 3종 (18.1)', () {
    testWidgets('Decision 스타일 — LEARN NOW 라벨, glyph 없음', (tester) async {
      await tester.pumpWidget(_app(MemoryTimelineItem(
        title: '테스트 시그널',
        dateLabel: '7월 5일',
        dotStyle: const DecisionDot('learn_now'),
        onTap: () {},
      )));
      expect(find.text('LEARN NOW'), findsOneWidget);
      expect(find.text('테스트 시그널'), findsOneWidget);
    });

    testWidgets('Outcome 스타일 — APPLIED 라벨 + → glyph + composite semantics', (tester) async {
      await tester.pumpWidget(_app(MemoryTimelineItem(
        title: '적용한 시그널',
        dateLabel: '7월 5일',
        dotStyle: const OutcomeDot('applied'),
        onTap: () {},
      )));
      expect(find.text('APPLIED'), findsOneWidget);
      expect(find.text('→'), findsOneWidget);
      expect(find.bySemanticsLabel(RegExp('Applied 결과 — 적용한 시그널')), findsOneWidget);
    });

    testWidgets('Outcome-pending 스타일 — IN PROGRESS 라벨 + ? glyph', (tester) async {
      await tester.pumpWidget(_app(MemoryTimelineItem(
        title: '미완료 시그널',
        dateLabel: '7월 5일',
        dotStyle: const OutcomePendingDot(),
        onTap: () {},
      )));
      expect(find.text('IN PROGRESS'), findsOneWidget);
      expect(find.text('?'), findsOneWidget);
    });

    test('resolveDotStyle — 규칙 검증', () {
      expect(resolveDotStyle(choice: 'learn_now', outcomeStatus: 'completed'), isA<OutcomeDot>());
      expect(resolveDotStyle(choice: 'learn_now', outcomeStatus: null), isA<OutcomePendingDot>());
      expect(resolveDotStyle(choice: 'queue', outcomeStatus: null), isA<DecisionDot>());
      expect(resolveDotStyle(choice: 'ignore', outcomeStatus: null), isA<DecisionDot>());
    });
  });

  group('ChainDetailScreen (18.3)', () {
    testWidgets('archived signal 이면 ArchivedBanner 표시', (tester) async {
      await tester.pumpWidget(_app(
        const ChainDetailScreen(signalId: 'sig-archived'),
        overrides: [
          chainDetailProvider('sig-archived').overrideWith((ref) async => const ChainDetailData(
                signal: ChainSignal(id: 'sig-archived', title: '보관된 시그널', status: 'archived'),
                reviewPayload: null,
                decision: null,
                outcome: null,
              )),
        ],
      ));
      await tester.pumpAndSettle();
      expect(find.byType(ArchivedBanner), findsOneWidget);
      expect(find.text('보관된 REVIEW'), findsOneWidget);
    });

    testWidgets('Learn Now 후 Outcome 미기록이면 "미완료" 표시', (tester) async {
      await tester.pumpWidget(_app(
        const ChainDetailScreen(signalId: 'sig-pending'),
        overrides: [
          chainDetailProvider('sig-pending').overrideWith((ref) async => ChainDetailData(
                signal: const ChainSignal(id: 'sig-pending', title: '진행중 시그널', status: 'processed'),
                reviewPayload: null,
                decision: ChainDecision(choice: 'learn_now', createdAt: DateTime.utc(2026, 7, 5)),
                outcome: null,
              )),
        ],
      ));
      await tester.pumpAndSettle();
      expect(find.text('미완료'), findsOneWidget);
      expect(find.byType(ArchivedBanner), findsNothing);
    });
  });

  group('History 라우팅 (18.4)', () {
    testWidgets('항목 탭 시 chain 상세로 push되고 히스토리 탭(index 2) 유지', (tester) async {
      final historyNavKey = GlobalKey<NavigatorState>(debugLabel: 'history');
      final router = GoRouter(
        initialLocation: '/history',
        routes: [
          StatefulShellRoute.indexedStack(
            builder: (context, state, shell) => ShellScaffold(navigationShell: shell),
            branches: [
              StatefulShellBranch(
                routes: [GoRoute(path: '/home', builder: (_, __) => const Scaffold(body: Text('Home')))],
              ),
              StatefulShellBranch(
                routes: [GoRoute(path: '/queue', builder: (_, __) => const Scaffold(body: Text('Queue')))],
              ),
              StatefulShellBranch(
                navigatorKey: historyNavKey,
                routes: [
                  GoRoute(
                    path: '/history',
                    builder: (_, __) => const HistoryScreen(),
                    routes: [
                      GoRoute(
                        path: 'chain/:signalId',
                        builder: (_, state) =>
                            ChainDetailScreen(signalId: state.pathParameters['signalId']!),
                      ),
                    ],
                  ),
                ],
              ),
              StatefulShellBranch(
                routes: [GoRoute(path: '/profile', builder: (_, __) => const Scaffold(body: Text('Profile placeholder')))],
              ),
            ],
          ),
        ],
      );

      await tester.pumpWidget(ProviderScope(
        overrides: [
          historyItemsProvider.overrideWith((ref) async => [
                HistoryItemData(
                  decisionId: 'd1',
                  signalId: 'sig-42',
                  title: '라우팅 대상 시그널',
                  choice: 'learn_now',
                  outcomeStatus: null,
                  createdAt: DateTime.utc(2026, 7, 5),
                ),
              ]),
          chainDetailProvider('sig-42').overrideWith((ref) async => const ChainDetailData(
                signal: ChainSignal(id: 'sig-42', title: '라우팅 대상 시그널', status: 'processed'),
                reviewPayload: null,
                decision: null,
                outcome: null,
              )),
        ],
        child: MaterialApp.router(theme: buildAppTheme(), routerConfig: router),
      ));
      await tester.pumpAndSettle();

      // BottomNavigationBar 히스토리 탭 활성
      final navBar = tester.widget<BottomNavigationBar>(find.byType(BottomNavigationBar));
      expect(navBar.currentIndex, 2);

      // 항목 탭 → chain 상세로 이동
      await tester.tap(find.text('라우팅 대상 시그널'));
      await tester.pumpAndSettle();

      expect(find.text('히스토리로'), findsOneWidget); // ChainDetailScreen 뒤로가기
      final navBarAfter = tester.widget<BottomNavigationBar>(find.byType(BottomNavigationBar));
      expect(navBarAfter.currentIndex, 2); // 히스토리 탭 유지
    });
  });
}
