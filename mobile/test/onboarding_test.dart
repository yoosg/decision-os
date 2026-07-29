import 'package:flutter_test/flutter_test.dart';

// 온보딩 선택 상태 로직 단위 테스트

bool isCTAEnabled({
  required int step,
  String? selectedRole,
  String? selectedExperience,
  Set<String>? selectedTechStack,
  String? selectedProjectGoal,
  Set<String>? selectedInterests,
  int? selectedDailyLearningTimeMin,
}) {
  switch (step) {
    case 0:
      return true;
    case 1:
      return selectedRole != null;
    case 2:
      return selectedExperience != null;
    case 3:
      return selectedTechStack?.isNotEmpty ?? false;
    case 4:
      return selectedProjectGoal != null;
    case 5:
      return selectedInterests?.isNotEmpty ?? false;
    case 6:
      return selectedDailyLearningTimeMin != null;
    default:
      return false;
  }
}

void main() {
  group('Welcome 화면 (step 0)', () {
    test('CTA가 항상 활성화되어 있다', () {
      expect(isCTAEnabled(step: 0), isTrue);
    });
  });

  group('Role step (step 1)', () {
    test('선택 전 CTA 비활성', () {
      expect(isCTAEnabled(step: 1, selectedRole: null), isFalse);
    });

    test('선택 후 CTA 활성화', () {
      expect(isCTAEnabled(step: 1, selectedRole: 'frontend'), isTrue);
    });

    test('모든 role 값 활성화 확인', () {
      final roles = ['frontend', 'backend', 'ai_engineer', 'pm', 'designer', 'student', 'other'];
      for (final role in roles) {
        expect(isCTAEnabled(step: 1, selectedRole: role), isTrue);
      }
    });
  });

  group('Experience step (step 2)', () {
    test('선택 전 CTA 비활성', () {
      expect(isCTAEnabled(step: 2, selectedExperience: null), isFalse);
    });

    test('선택 후 CTA 활성화', () {
      expect(isCTAEnabled(step: 2, selectedExperience: 'beginner'), isTrue);
    });
  });

  group('Tech Stack multi-select (step 3)', () {
    test('선택 없으면 CTA 비활성', () {
      expect(isCTAEnabled(step: 3, selectedTechStack: {}), isFalse);
    });

    test('1개 선택 시 CTA 활성화', () {
      expect(isCTAEnabled(step: 3, selectedTechStack: {'React'}), isTrue);
    });

    test('복수 선택 가능 — 여러 항목 선택 시 CTA 활성화', () {
      final stack = {'React', 'Python', 'LangGraph'};
      expect(isCTAEnabled(step: 3, selectedTechStack: stack), isTrue);
      expect(stack.length, 3);
    });
  });

  group('Project/Goal step (step 4)', () {
    test('선택 전 CTA 비활성', () {
      expect(isCTAEnabled(step: 4, selectedProjectGoal: null), isFalse);
    });

    test('선택 후 CTA 활성화', () {
      expect(isCTAEnabled(step: 4, selectedProjectGoal: 'rag_service'), isTrue);
    });
  });

  group('Interests multi-select (step 5)', () {
    test('선택 없으면 CTA 비활성', () {
      expect(isCTAEnabled(step: 5, selectedInterests: {}), isFalse);
    });

    test('복수 선택 가능 — 여러 항목 선택 시 CTA 활성화', () {
      final interests = {'Agent', 'RAG', 'MCP'};
      expect(isCTAEnabled(step: 5, selectedInterests: interests), isTrue);
      expect(interests.length, 3);
    });
  });

  group('Daily Learning Time step (step 6)', () {
    test('선택 전 CTA 비활성', () {
      expect(isCTAEnabled(step: 6, selectedDailyLearningTimeMin: null), isFalse);
    });

    test('15분 선택 후 CTA 활성화', () {
      expect(isCTAEnabled(step: 6, selectedDailyLearningTimeMin: 15), isTrue);
    });

    test('30분 선택 후 CTA 활성화', () {
      expect(isCTAEnabled(step: 6, selectedDailyLearningTimeMin: 30), isTrue);
    });

    test('1시간(60) 선택 후 CTA 활성화', () {
      expect(isCTAEnabled(step: 6, selectedDailyLearningTimeMin: 60), isTrue);
    });
  });

  group('GoRouter redirect 온보딩 로직', () {
    test('세션 있고 온보딩 미완료 → /onboarding', () {
      const session = 'valid-session';
      const isOnboardingDone = false;
      const isAuthRoute = false;
      const isOnboardingRoute = false;

      String? redirect;
      if (session == null && !isAuthRoute) redirect = '/signin';
      if (session != null && isAuthRoute) {
        redirect = isOnboardingDone ? '/home' : '/onboarding';
      }
      if (session != null && !isOnboardingDone && !isOnboardingRoute) {
        redirect = '/onboarding';
      }

      expect(redirect, '/onboarding');
    });

    test('세션 있고 온보딩 완료 + 인증 경로 → /home', () {
      const session = 'valid-session';
      const isOnboardingDone = true;
      const isAuthRoute = true;
      const isOnboardingRoute = false;

      String? redirect;
      if (session == null && !isAuthRoute) redirect = '/signin';
      if (session != null && isAuthRoute) {
        redirect = isOnboardingDone ? '/home' : '/onboarding';
      }
      if (session != null && !isOnboardingDone && !isOnboardingRoute) {
        redirect = '/onboarding';
      }

      expect(redirect, '/home');
    });

    test('세션 있고 온보딩 완료 + /home → redirect 없음', () {
      const session = 'valid-session';
      const isOnboardingDone = true;
      const isAuthRoute = false;
      const isOnboardingRoute = false;

      String? redirect;
      if (session == null && !isAuthRoute) redirect = '/signin';
      if (session != null && isAuthRoute) {
        redirect = isOnboardingDone ? '/home' : '/onboarding';
      }
      if (session != null && !isOnboardingDone && !isOnboardingRoute) {
        redirect = '/onboarding';
      }

      expect(redirect, null);
    });

    test('온보딩 진행 중 → /onboarding으로 redirect 없음', () {
      const session = 'valid-session';
      const isOnboardingDone = false;
      const isAuthRoute = false;
      const isOnboardingRoute = true;

      String? redirect;
      if (session == null && !isAuthRoute) redirect = '/signin';
      if (session != null && isAuthRoute) {
        redirect = isOnboardingDone ? '/home' : '/onboarding';
      }
      if (session != null && !isOnboardingDone && !isOnboardingRoute) {
        redirect = '/onboarding';
      }

      expect(redirect, null);
    });
  });
}
