import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../../features/auth/screens/signin_screen.dart';
import '../../features/auth/screens/signup_screen.dart';
import '../../features/shell/shell_scaffold.dart';
import '../../features/home/screens/home_screen.dart';
import '../../features/home/screens/contextual_chat_screen.dart';
import '../../features/home/screens/learning_path_screen.dart';
import '../../features/home/screens/outcome_screen.dart';
import '../../features/home/screens/research_review_screen.dart';
import '../../features/queue/screens/queue_screen.dart';
import '../../features/history/screens/history_screen.dart';
import '../../features/history/screens/chain_detail_screen.dart';
import '../../features/profile/screens/profile_screen.dart';
import '../../features/onboarding/screens/onboarding_screen.dart';
import '../../features/onboarding/providers/onboarding_provider.dart';

part 'app_router.g.dart';

final _homeNavKey    = GlobalKey<NavigatorState>(debugLabel: 'home');
final _queueNavKey   = GlobalKey<NavigatorState>(debugLabel: 'queue');
final _historyNavKey = GlobalKey<NavigatorState>(debugLabel: 'history');
final _profileNavKey = GlobalKey<NavigatorState>(debugLabel: 'profile');

class _GoRouterAuthNotifier extends ChangeNotifier {
  late final StreamSubscription<AuthState> _sub;

  _GoRouterAuthNotifier() {
    _sub = Supabase.instance.client.auth.onAuthStateChange
        .listen((_) => notifyListeners(), onError: (_) {});
  }

  @override
  void dispose() {
    _sub.cancel();
    super.dispose();
  }
}

@riverpod
GoRouter appRouter(AppRouterRef ref) {
  final notifier = _GoRouterAuthNotifier();
  ref.onDispose(notifier.dispose);

  final isOnboardingDone = ref.watch(onboardingCompletedProvider);

  final router = GoRouter(
    initialLocation: '/signin',
    refreshListenable: notifier,
    redirect: (context, state) {
      final session = Supabase.instance.client.auth.currentSession;
      final loc = state.matchedLocation;
      final isAuthRoute = loc == '/signin' || loc == '/signup';
      final isOnboardingRoute = loc.startsWith('/onboarding');

      if (session == null && !isAuthRoute) return '/signin';
      if (session != null && isAuthRoute) {
        return isOnboardingDone ? '/home' : '/onboarding';
      }
      if (session != null && !isOnboardingDone && !isOnboardingRoute) {
        return '/onboarding';
      }
      if (session != null && isOnboardingDone && isOnboardingRoute) {
        return '/home';
      }
      return null;
    },
    routes: [
      GoRoute(path: '/signin', builder: (_, __) => const SignInScreen()),
      GoRoute(path: '/signup', builder: (_, __) => const SignUpScreen()),
      GoRoute(path: '/onboarding', builder: (_, __) => const OnboardingScreen()),
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) => ShellScaffold(navigationShell: shell),
        branches: [
          StatefulShellBranch(
            navigatorKey: _homeNavKey,
            routes: [
              GoRoute(
                path: '/home',
                builder: (_, __) => const HomeScreen(),
                routes: [
                  GoRoute(
                    path: 'review/:signalId',
                    builder: (_, state) => ResearchReviewScreen(
                      signalId: state.pathParameters['signalId']!,
                    ),
                    routes: [
                      GoRoute(
                        path: 'learning-path',
                        builder: (_, state) => LearningPathScreen(
                          signalId: state.pathParameters['signalId']!,
                        ),
                      ),
                      GoRoute(
                        path: 'outcome',
                        builder: (_, state) => OutcomeScreen(
                          signalId: state.pathParameters['signalId']!,
                        ),
                      ),
                      GoRoute(
                        path: 'chat',
                        builder: (_, state) => ContextualChatScreen(
                          signalId: state.pathParameters['signalId']!,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ),
          StatefulShellBranch(
            navigatorKey: _queueNavKey,
            routes: [
              GoRoute(
                path: '/queue',
                builder: (_, __) => const QueueScreen(),
                routes: [
                  GoRoute(
                    path: 'review/:signalId',
                    builder: (_, state) => ResearchReviewScreen(
                      signalId: state.pathParameters['signalId']!,
                    ),
                  ),
                ],
              ),
            ],
          ),
          StatefulShellBranch(
            navigatorKey: _historyNavKey,
            routes: [
              GoRoute(
                path: '/history',
                builder: (_, __) => const HistoryScreen(),
                routes: [
                  GoRoute(
                    path: 'chain/:signalId',
                    builder: (_, state) => ChainDetailScreen(
                      signalId: state.pathParameters['signalId']!,
                    ),
                  ),
                ],
              ),
            ],
          ),
          StatefulShellBranch(
            navigatorKey: _profileNavKey,
            routes: [GoRoute(path: '/profile', builder: (_, __) => const ProfileScreen())],
          ),
        ],
      ),
    ],
  );
  ref.onDispose(router.dispose);
  return router;
}
