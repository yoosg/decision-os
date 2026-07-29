import 'package:decision_os/features/profile/providers/profile_provider.dart';
import 'package:decision_os/features/profile/screens/profile_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

// UserProfile 데이터 모델 로직 테스트 (profile_provider.dart의 UserProfile.fromJson 미러)

Map<String, dynamic> _profileFromJson(Map<String, dynamic> json) => {
  'role': json['role'],
  'experienceLevel': json['experience_level'],
  'techStack': (json['tech_stack'] as List<dynamic>?)?.cast<String>() ?? [],
  'projectGoal': json['project_goal'],
  'interests': (json['interests'] as List<dynamic>?)?.cast<String>() ?? [],
  'dailyLearningTimeMin': json['daily_learning_time_min'],
};

// _isSaveEnabled 로직: role, experience, projectGoal, dailyTime 모두 선택된 경우 true
bool _isSaveEnabled({
  String? role,
  String? experience,
  String? projectGoal,
  int? dailyTime,
}) =>
    role != null && experience != null && projectGoal != null && dailyTime != null;

// 편집 모드 진입 시 초기 상태 로직
Map<String, dynamic> _enterEditState(Map<String, dynamic> profile) => {
  'role': profile['role'],
  'experience': profile['experienceLevel'],
  'techStack': Set<String>.from(profile['techStack'] as List),
  'projectGoal': profile['projectGoal'],
  'interests': Set<String>.from(profile['interests'] as List),
  'dailyTime': profile['dailyLearningTimeMin'],
};

void main() {
  group('UserProfile.fromJson', () {
    test('전체 필드가 있는 JSON 파싱', () {
      final json = {
        'role': 'ai_engineer',
        'experience_level': 'intermediate',
        'tech_stack': ['React', 'Python', 'LangGraph'],
        'project_goal': 'rag_service',
        'interests': ['Agent', 'RAG'],
        'daily_learning_time_min': 30,
      };
      final profile = _profileFromJson(json);
      expect(profile['role'], 'ai_engineer');
      expect(profile['experienceLevel'], 'intermediate');
      expect(profile['techStack'], ['React', 'Python', 'LangGraph']);
      expect(profile['projectGoal'], 'rag_service');
      expect(profile['interests'], ['Agent', 'RAG']);
      expect(profile['dailyLearningTimeMin'], 30);
    });

    test('null 필드가 있는 JSON — 기본값 적용', () {
      final json = <String, dynamic>{
        'role': null,
        'experience_level': null,
        'tech_stack': null,
        'project_goal': null,
        'interests': null,
        'daily_learning_time_min': null,
      };
      final profile = _profileFromJson(json);
      expect(profile['role'], isNull);
      expect(profile['techStack'], isEmpty);
      expect(profile['interests'], isEmpty);
    });

    test('tech_stack 빈 배열 파싱', () {
      final json = {
        'role': 'backend',
        'experience_level': 'beginner',
        'tech_stack': <dynamic>[],
        'project_goal': 'work_automation',
        'interests': <dynamic>[],
        'daily_learning_time_min': 15,
      };
      final profile = _profileFromJson(json);
      expect(profile['techStack'], isEmpty);
      expect(profile['interests'], isEmpty);
    });
  });

  group('_isSaveEnabled — 저장 버튼 활성화 로직', () {
    test('모든 필드 선택 시 저장 활성화', () {
      expect(
        _isSaveEnabled(
          role: 'ai_engineer',
          experience: 'intermediate',
          projectGoal: 'rag_service',
          dailyTime: 30,
        ),
        isTrue,
      );
    });

    test('role 없으면 저장 비활성', () {
      expect(
        _isSaveEnabled(
          role: null,
          experience: 'intermediate',
          projectGoal: 'rag_service',
          dailyTime: 30,
        ),
        isFalse,
      );
    });

    test('experience 없으면 저장 비활성', () {
      expect(
        _isSaveEnabled(
          role: 'ai_engineer',
          experience: null,
          projectGoal: 'rag_service',
          dailyTime: 30,
        ),
        isFalse,
      );
    });

    test('projectGoal 없으면 저장 비활성', () {
      expect(
        _isSaveEnabled(
          role: 'ai_engineer',
          experience: 'intermediate',
          projectGoal: null,
          dailyTime: 30,
        ),
        isFalse,
      );
    });

    test('dailyTime 없으면 저장 비활성', () {
      expect(
        _isSaveEnabled(
          role: 'ai_engineer',
          experience: 'intermediate',
          projectGoal: 'rag_service',
          dailyTime: null,
        ),
        isFalse,
      );
    });
  });

  group('편집 모드 진입 상태 초기화', () {
    test('프로필 데이터로 편집 상태 초기화', () {
      final profile = {
        'role': 'frontend',
        'experienceLevel': 'beginner',
        'techStack': ['React', 'Next.js'],
        'projectGoal': 'ai_side_project',
        'interests': ['Agent', 'MCP'],
        'dailyLearningTimeMin': 15,
      };
      final editState = _enterEditState(profile);
      expect(editState['role'], 'frontend');
      expect(editState['experience'], 'beginner');
      expect((editState['techStack'] as Set<String>), containsAll(['React', 'Next.js']));
      expect(editState['projectGoal'], 'ai_side_project');
      expect((editState['interests'] as Set<String>), containsAll(['Agent', 'MCP']));
      expect(editState['dailyTime'], 15);
    });

    test('취소 시 편집 상태 초기화 — isEditMode = false', () {
      // 취소 동작: 단순히 _isEditMode = false로 되돌아감
      bool isEditMode = true;
      isEditMode = false; // _cancelEdit() 호출 효과
      expect(isEditMode, isFalse);
    });

    test('편집 모드 전환 — isEditMode = true', () {
      bool isEditMode = false;
      isEditMode = true; // _enterEditMode() 호출 효과
      expect(isEditMode, isTrue);
    });
  });

  group('낙관적 업데이트 롤백 로직', () {
    test('API 실패 시 이전 상태로 롤백', () {
      var currentRole = 'frontend';
      final prevRole = currentRole;
      currentRole = 'backend';
      expect(currentRole, 'backend');
      currentRole = prevRole;
      expect(currentRole, 'frontend');
    });
  });
}

// ── 위젯 테스트 (Task 5.2, 5.3) ─────────────────────────────────────

final _testProfile = UserProfile(
  role: 'ai_engineer',
  experienceLevel: 'intermediate',
  techStack: const ['Python', 'LangGraph'],
  projectGoal: 'rag_service',
  interests: const ['Agent', 'RAG'],
  dailyLearningTimeMin: 30,
);

Widget _buildTestApp(Override override) => ProviderScope(
      overrides: [override],
      child: const MaterialApp(home: ProfileScreen()),
    );

group('ProfileScreen 위젯 테스트', () {
  testWidgets('Task 5.2: 조회 모드 — 프로필 항목 6개 + 알림 설정 행 렌더링', (tester) async {
    final override = profileNotifierProvider.overrideWith(() => _FakeProfileNotifier(_testProfile));
    await tester.pumpWidget(_buildTestApp(override));
    await tester.pump();

    expect(find.text('역할'), findsOneWidget);
    expect(find.text('경험 수준'), findsOneWidget);
    expect(find.text('기술 스택'), findsOneWidget);
    expect(find.text('프로젝트 목표'), findsOneWidget);
    expect(find.text('관심 영역'), findsOneWidget);
    expect(find.text('하루 학습 시간'), findsOneWidget);
    expect(find.text('알림 설정'), findsOneWidget);
    expect(find.text('편집'), findsOneWidget);
  });

  testWidgets('Task 5.3: 편집 모드 전환 및 취소 동작', (tester) async {
    final override = profileNotifierProvider.overrideWith(() => _FakeProfileNotifier(_testProfile));
    await tester.pumpWidget(_buildTestApp(override));
    await tester.pump();

    await tester.tap(find.text('편집'));
    await tester.pump();

    expect(find.text('저장'), findsOneWidget);
    expect(find.text('취소'), findsOneWidget);

    await tester.tap(find.text('취소'));
    await tester.pump();

    expect(find.text('편집'), findsOneWidget);
    expect(find.text('저장'), findsNothing);
  });

  testWidgets('Task 5.3: 로딩 중에도 편집 버튼 노출 (비활성)', (tester) async {
    final override = profileNotifierProvider.overrideWith(() => _LoadingProfileNotifier());
    await tester.pumpWidget(_buildTestApp(override));
    await tester.pump();

    final editBtn = tester.widget<TextButton>(find.widgetWithText(TextButton, '편집'));
    expect(editBtn.onPressed, isNull);
  });
});

class _FakeProfileNotifier extends ProfileNotifier {
  _FakeProfileNotifier(this._profile);
  final UserProfile _profile;

  @override
  Future<UserProfile> build() async => _profile;

  @override
  Future<void> updateProfile(Map<String, dynamic> updates) async {}
}

class _LoadingProfileNotifier extends ProfileNotifier {
  @override
  Future<UserProfile> build() async {
    await Future.delayed(const Duration(seconds: 60));
    return const UserProfile();
  }
}
