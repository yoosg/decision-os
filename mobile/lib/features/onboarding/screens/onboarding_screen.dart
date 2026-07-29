import 'dart:convert';

import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../../core/theme/app_theme.dart';
import '../providers/onboarding_provider.dart';

class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  // 0=Welcome 1=Role 2=Experience 3=TechStack 4=ProjectGoal 5=Interests 6=DailyTime 7=BriefGenerating 8=NotificationPermission
  int _step = 0;

  String? _selectedRole;
  String? _selectedExperience;
  String? _selectedProjectGoal;
  int? _selectedDailyLearningTimeMin;
  final Set<String> _selectedTechStack = {};
  final Set<String> _selectedInterests = {};

  bool _isLoading = false;

  bool get _isCTAEnabled {
    switch (_step) {
      case 0:
        return true;
      case 1:
        return _selectedRole != null;
      case 2:
        return _selectedExperience != null;
      case 3:
        return _selectedTechStack.isNotEmpty;
      case 4:
        return _selectedProjectGoal != null;
      case 5:
        return _selectedInterests.isNotEmpty;
      case 6:
        return _selectedDailyLearningTimeMin != null;
      default:
        return false;
    }
  }

  void _goBack() {
    if (_step > 0 && _step < 7) setState(() => _step--);
  }

  void _goNext() => setState(() => _step++);

  Future<void> _submitOnboarding() async {
    setState(() => _isLoading = true);
    try {
      await _callOnboardingCompleteApi();
      if (!mounted) return;
      setState(() { _isLoading = false; _step = 7; });
      await Future.delayed(const Duration(seconds: 5));
      if (mounted) setState(() { _step = 8; });
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('오류가 발생했습니다. 다시 시도해 주세요.')),
      );
    }
  }

  Future<void> _callOnboardingCompleteApi() async {
    final session = Supabase.instance.client.auth.currentSession;
    if (session == null) throw Exception('No session');

    const apiBase = String.fromEnvironment(
      'FASTAPI_BASE_URL',
      defaultValue: 'http://localhost:8000',
    );

    final response = await http.post(
      Uri.parse('$apiBase/api/v1/onboarding/complete'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ${session.accessToken}',
      },
      body: jsonEncode({
        'role': _selectedRole,
        'experience_level': _selectedExperience,
        'tech_stack': _selectedTechStack.toList(),
        'project_goal': _selectedProjectGoal,
        'interests': _selectedInterests.toList(),
        'daily_learning_time_min': _selectedDailyLearningTimeMin,
      }),
    ).timeout(const Duration(seconds: 30));

    if (response.statusCode != 200) {
      throw Exception('Onboarding complete API failed: ${response.statusCode}');
    }
  }

  Future<void> _requestNotificationPermission() async {
    try {
      await FirebaseMessaging.instance.requestPermission(
        alert: true,
        badge: true,
        sound: true,
      );
    } catch (_) {
      // 권한 요청 실패해도 온보딩 완료 처리
    } finally {
      await _markNotificationPermissionRequested();
      await _completeOnboarding();
    }
  }

  Future<void> _skipNotificationPermission() async {
    await _markNotificationPermissionRequested();
    await _completeOnboarding();
  }

  Future<void> _markNotificationPermissionRequested() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(kNotificationPermissionRequestedKey, true);
  }

  Future<void> _completeOnboarding() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(kOnboardingCompletedKey, true);
    ref.read(onboardingCompletedProvider.notifier).state = true;
    if (mounted) context.go('/home');
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: _step != 7 && _step != 8,
      child: Scaffold(
        backgroundColor: AppColors.surfaceBase,
        appBar: _step == 0 || _step >= 7
            ? null
            : AppBar(
                backgroundColor: AppColors.surfaceBase,
                elevation: 0,
                scrolledUnderElevation: 0,
                leading: IconButton(
                  icon: const Icon(Icons.chevron_left, color: AppColors.textPrimary),
                  onPressed: _goBack,
                ),
              ),
        body: SafeArea(child: _buildStep()),
      ),
    );
  }

  Widget _buildStep() {
    switch (_step) {
      case 0:
        return _buildWelcome();
      case 1:
        return _buildRole();
      case 2:
        return _buildExperience();
      case 3:
        return _buildTechStack();
      case 4:
        return _buildProjectGoal();
      case 5:
        return _buildInterests();
      case 6:
        return _buildDailyTime();
      case 7:
        return _buildBriefGenerating();
      case 8:
        return _buildNotificationPermission();
      default:
        return const SizedBox.shrink();
    }
  }

  // ── Step 0: Welcome ──────────────────────────────────────────────
  Widget _buildWelcome() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 80),
          Text(
            '오늘 배워야 할 AI,\n매일 브리핑해드립니다',
            style: Theme.of(context).textTheme.displayLarge?.copyWith(
              fontSize: 28,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            'AI 기술의 변화 속에서 오늘 배울 것을 추천받으세요.',
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const Spacer(),
          _PrimaryCTA(
            label: '시작하기',
            enabled: true,
            onPressed: _goNext,
          ),
          const SizedBox(height: 40),
        ],
      ),
    );
  }

  // ── Step 1: Role ─────────────────────────────────────────────────
  Widget _buildRole() {
    final options = [
      ('Frontend Developer', 'frontend'),
      ('Backend Developer', 'backend'),
      ('AI Engineer', 'ai_engineer'),
      ('Product Manager', 'pm'),
      ('Designer', 'designer'),
      ('Student', 'student'),
      ('기타', 'other'),
    ];
    return _buildSingleSelectStep(
      question: '어떤 역할을 맡고 계신가요?',
      options: options,
      selected: _selectedRole,
      onSelect: (v) => setState(() => _selectedRole = v),
      onNext: _goNext,
    );
  }

  // ── Step 2: Experience ───────────────────────────────────────────
  Widget _buildExperience() {
    final options = [
      ('입문', 'beginner'),
      ('중급', 'intermediate'),
      ('고급', 'advanced'),
    ];
    return _buildSingleSelectStep(
      question: 'AI 기술 경험 수준을 선택해 주세요.',
      options: options,
      selected: _selectedExperience,
      onSelect: (v) => setState(() => _selectedExperience = v),
      onNext: _goNext,
    );
  }

  // ── Step 3: Tech Stack (multi-select) ────────────────────────────
  Widget _buildTechStack() {
    final options = ['React', 'Next.js', 'Python', 'FastAPI', 'LangGraph', 'MCP', 'Claude Code', '기타'];
    return _buildMultiSelectStep(
      question: '주로 사용하는 기술 스택을 선택해 주세요.',
      options: options,
      selected: _selectedTechStack,
      onToggle: (v) => setState(() {
        if (_selectedTechStack.contains(v)) {
          _selectedTechStack.remove(v);
        } else {
          _selectedTechStack.add(v);
        }
      }),
      onNext: _goNext,
    );
  }

  // ── Step 4: Project/Goal ─────────────────────────────────────────
  Widget _buildProjectGoal() {
    final options = [
      ('AI 사이드 프로젝트 개발', 'ai_side_project'),
      ('RAG 서비스 구축', 'rag_service'),
      ('Agent Architecture 학습', 'agent_architecture'),
      ('업무 자동화', 'work_automation'),
      ('AI 도입 검토', 'ai_adoption'),
      ('기타', 'other'),
    ];
    return _buildSingleSelectStep(
      question: '현재 무엇을 만들거나 배우고 계신가요?',
      options: options,
      selected: _selectedProjectGoal,
      onSelect: (v) => setState(() => _selectedProjectGoal = v),
      onNext: _goNext,
    );
  }

  // ── Step 5: Interests (multi-select) ────────────────────────────
  Widget _buildInterests() {
    final options = ['Agent', 'RAG', 'MCP', 'Coding Agent', 'Local LLM', 'AI UX', '기타'];
    return _buildMultiSelectStep(
      question: '관심 있는 기술 영역을 선택해 주세요.',
      options: options,
      selected: _selectedInterests,
      onToggle: (v) => setState(() {
        if (_selectedInterests.contains(v)) {
          _selectedInterests.remove(v);
        } else {
          _selectedInterests.add(v);
        }
      }),
      onNext: _goNext,
    );
  }

  // ── Step 6: Daily Learning Time ──────────────────────────────────
  Widget _buildDailyTime() {
    final options = [
      ('15분', 15),
      ('30분', 30),
      ('1시간', 60),
    ];
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 32),
          Text(
            '하루에 AI 학습에 투자할 수 있는 시간은?',
            style: Theme.of(context).textTheme.displayMedium,
          ),
          const SizedBox(height: 24),
          ...options.map((opt) {
            final label = opt.$1;
            final value = opt.$2;
            final selected = _selectedDailyLearningTimeMin == value;
            return Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _OptionCard(
                label: label,
                selected: selected,
                onTap: () => setState(() => _selectedDailyLearningTimeMin = value),
              ),
            );
          }),
          const Spacer(),
          _PrimaryCTA(
            label: '완료',
            enabled: _selectedDailyLearningTimeMin != null,
            onPressed: _isLoading ? null : _submitOnboarding,
          ),
          const SizedBox(height: 40),
        ],
      ),
    );
  }

  // ── Step 7: Brief Generating ─────────────────────────────────────
  Widget _buildBriefGenerating() {
    return Container(
      color: AppColors.surfaceRaised,
      child: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                '오늘의 브리핑을\n생성 중입니다.',
                style: Theme.of(context).textTheme.displayLarge,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),
              Text(
                '프로필을 기반으로 가장 관련성 높은 AI 기술을 찾고 있습니다.',
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  color: AppColors.textSecondary,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 32),
              const _ThreeDotLoadingIndicator(),
            ],
          ),
        ),
      ),
    );
  }

  // ── Step 8: Notification Permission ─────────────────────────────
  Widget _buildNotificationPermission() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 80),
          Text(
            '매일 AI 기술 브리핑을\n받아보시겠어요?',
            style: Theme.of(context).textTheme.displayLarge?.copyWith(fontSize: 28),
          ),
          const SizedBox(height: 16),
          Text(
            '매일 09:00에 오늘 배울 기술 브리핑을 보내드립니다.',
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const Spacer(),
          _PrimaryCTA(
            label: '허용',
            enabled: true,
            onPressed: _requestNotificationPermission,
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            height: 52,
            child: OutlinedButton(
              onPressed: _skipNotificationPermission,
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: AppColors.borderCard),
                foregroundColor: AppColors.textPrimary,
              ),
              child: Text(
                '나중에',
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ),
          ),
          const SizedBox(height: 40),
        ],
      ),
    );
  }

  // ── Shared Builders ───────────────────────────────────────────────
  Widget _buildSingleSelectStep({
    required String question,
    required List<(String, String)> options,
    required String? selected,
    required ValueChanged<String> onSelect,
    required VoidCallback onNext,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 32),
          Text(question, style: Theme.of(context).textTheme.displayMedium),
          const SizedBox(height: 24),
          Expanded(
            child: ListView(
              children: options.map((opt) {
                final label = opt.$1;
                final value = opt.$2;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: _OptionCard(
                    label: label,
                    selected: selected == value,
                    onTap: () => onSelect(value),
                  ),
                );
              }).toList(),
            ),
          ),
          _PrimaryCTA(
            label: '다음',
            enabled: selected != null,
            onPressed: onNext,
          ),
          const SizedBox(height: 40),
        ],
      ),
    );
  }

  Widget _buildMultiSelectStep({
    required String question,
    required List<String> options,
    required Set<String> selected,
    required ValueChanged<String> onToggle,
    required VoidCallback onNext,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 32),
          Text(question, style: Theme.of(context).textTheme.displayMedium),
          const SizedBox(height: 24),
          Expanded(
            child: SingleChildScrollView(
              child: Wrap(
                spacing: 10,
                runSpacing: 10,
                children: options.map((value) {
                  final isSelected = selected.contains(value);
                  return FilterChip(
                    label: Text(value),
                    selected: isSelected,
                    onSelected: (_) => onToggle(value),
                    selectedColor: AppColors.accentPrimary,
                    checkmarkColor: AppColors.accentForeground,
                    labelStyle: TextStyle(
                      color: isSelected ? AppColors.accentForeground : AppColors.textPrimary,
                      fontSize: 15,
                      fontWeight: FontWeight.w500,
                    ),
                    shape: const StadiumBorder(),
                    side: BorderSide(
                      color: isSelected ? AppColors.accentPrimary : AppColors.borderCard,
                    ),
                    backgroundColor: AppColors.surfaceBase,
                    showCheckmark: false,
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  );
                }).toList(),
              ),
            ),
          ),
          const SizedBox(height: 16),
          _PrimaryCTA(
            label: '다음',
            enabled: selected.isNotEmpty,
            onPressed: onNext,
          ),
          const SizedBox(height: 40),
        ],
      ),
    );
  }
}

// ── Shared Widgets ─────────────────────────────────────────────────

class _OptionCard extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _OptionCard({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.surfaceCard,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: selected ? AppColors.accentPrimary : AppColors.borderCard,
            width: selected ? 1.5 : 1,
          ),
        ),
        constraints: const BoxConstraints(minHeight: 52),
        child: Text(
          label,
          style: Theme.of(context).textTheme.bodyLarge,
        ),
      ),
    );
  }
}

class _PrimaryCTA extends StatelessWidget {
  final String label;
  final bool enabled;
  final VoidCallback? onPressed;

  const _PrimaryCTA({
    required this.label,
    required this.enabled,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 52,
      child: FilledButton(
        onPressed: enabled ? onPressed : null,
        child: Text(
          label,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
            color: AppColors.accentForeground,
          ),
        ),
      ),
    );
  }
}

class _ThreeDotLoadingIndicator extends StatefulWidget {
  const _ThreeDotLoadingIndicator();

  @override
  State<_ThreeDotLoadingIndicator> createState() => _ThreeDotLoadingIndicatorState();
}

class _ThreeDotLoadingIndicatorState extends State<_ThreeDotLoadingIndicator>
    with TickerProviderStateMixin {
  late final List<AnimationController> _controllers;
  late final List<Animation<double>> _animations;

  @override
  void initState() {
    super.initState();
    _controllers = List.generate(3, (i) {
      return AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 600),
      );
    });
    _animations = _controllers.map((c) {
      return Tween<double>(begin: 0, end: -8).animate(
        CurvedAnimation(parent: c, curve: Curves.easeInOut),
      );
    }).toList();

    for (int i = 0; i < 3; i++) {
      Future.delayed(Duration(milliseconds: i * 200), () {
        if (mounted) {
          _controllers[i].repeat(reverse: true);
        }
      });
    }
  }

  @override
  void dispose() {
    for (final c in _controllers) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final reduceMotion = MediaQuery.disableAnimationsOf(context);
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(3, (i) {
        final dot = Container(
          width: 10,
          height: 10,
          decoration: const BoxDecoration(
            color: AppColors.accentPrimary,
            shape: BoxShape.circle,
          ),
        );
        if (reduceMotion) {
          return Padding(
            padding: const EdgeInsets.symmetric(horizontal: 5),
            child: dot,
          );
        }
        return AnimatedBuilder(
          animation: _animations[i],
          builder: (_, child) => Padding(
            padding: const EdgeInsets.symmetric(horizontal: 5),
            child: Transform.translate(
              offset: Offset(0, _animations[i].value),
              child: child,
            ),
          ),
          child: dot,
        );
      }),
    );
  }
}
