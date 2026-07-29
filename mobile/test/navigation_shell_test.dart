import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:decision_os/features/shell/shell_scaffold.dart';
import 'package:decision_os/features/home/screens/home_screen.dart';
import 'package:decision_os/features/queue/screens/queue_screen.dart';
import 'package:decision_os/features/history/screens/history_screen.dart';
import 'package:decision_os/features/profile/screens/profile_screen.dart';

GoRouter _buildTestRouter() {
  final homeNavKey    = GlobalKey<NavigatorState>(debugLabel: 'home');
  final queueNavKey   = GlobalKey<NavigatorState>(debugLabel: 'queue');
  final historyNavKey = GlobalKey<NavigatorState>(debugLabel: 'history');
  final profileNavKey = GlobalKey<NavigatorState>(debugLabel: 'profile');

  return GoRouter(
    initialLocation: '/home',
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
            routes: [GoRoute(path: '/queue', builder: (_, __) => const QueueScreen())],
          ),
          StatefulShellBranch(
            navigatorKey: historyNavKey,
            routes: [GoRoute(path: '/history', builder: (_, __) => const HistoryScreen())],
          ),
          StatefulShellBranch(
            navigatorKey: profileNavKey,
            routes: [GoRoute(path: '/profile', builder: (_, __) => const ProfileScreen())],
          ),
        ],
      ),
    ],
  );
}

void main() {
  group('ShellScaffold', () {
    testWidgets('BottomNavigationBar에 4개 탭 항목이 표시된다', (tester) async {
      final router = _buildTestRouter();
      await tester.pumpWidget(MaterialApp.router(routerConfig: router));
      await tester.pumpAndSettle();

      expect(find.byType(BottomNavigationBar), findsOneWidget);

      final navBar = tester.widget<BottomNavigationBar>(find.byType(BottomNavigationBar));
      expect(navBar.items.length, 4);
      expect(navBar.items[0].label, '홈');
      expect(navBar.items[1].label, '큐');
      expect(navBar.items[2].label, '히스토리');
      expect(navBar.items[3].label, '프로필');
    });

    testWidgets('탭 전환 시 currentIndex가 업데이트된다', (tester) async {
      final router = _buildTestRouter();
      await tester.pumpWidget(MaterialApp.router(routerConfig: router));
      await tester.pumpAndSettle();

      final navBar = tester.widget<BottomNavigationBar>(find.byType(BottomNavigationBar));
      expect(navBar.currentIndex, 0);

      await tester.tap(find.descendant(
        of: find.byType(BottomNavigationBar),
        matching: find.text('큐'),
      ));
      await tester.pumpAndSettle();

      final navBarAfter = tester.widget<BottomNavigationBar>(find.byType(BottomNavigationBar));
      expect(navBarAfter.currentIndex, 1);
    });
  });
}
