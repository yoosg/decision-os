import 'package:app_settings/app_settings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../providers/profile_provider.dart';

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  bool _isEditMode = false;
  bool _isSaving = false;

  String? _editRole;
  String? _editExperience;
  final Set<String> _editTechStack = {};
  String? _editProjectGoal;
  final Set<String> _editInterests = {};
  int? _editDailyTime;

  bool get _isSaveEnabled =>
      !_isSaving &&
      _editRole != null &&
      _editExperience != null &&
      _editProjectGoal != null &&
      _editDailyTime != null;

  void _enterEditMode(UserProfile profile) {
    setState(() {
      _isEditMode = true;
      _editRole = profile.role;
      _editExperience = profile.experienceLevel;
      _editTechStack
        ..clear()
        ..addAll(profile.techStack);
      _editProjectGoal = profile.projectGoal;
      _editInterests
        ..clear()
        ..addAll(profile.interests);
      _editDailyTime = profile.dailyLearningTimeMin;
    });
  }

  void _cancelEdit() => setState(() {
        _isEditMode = false;
        _editRole = null;
        _editExperience = null;
        _editTechStack.clear();
        _editProjectGoal = null;
        _editInterests.clear();
        _editDailyTime = null;
      });

  Future<void> _saveProfile() async {
    setState(() => _isSaving = true);
    try {
      await ref.read(profileNotifierProvider.notifier).updateProfile({
        if (_editRole != null) 'role': _editRole,
        if (_editExperience != null) 'experience_level': _editExperience,
        'tech_stack': _editTechStack.toList(),
        if (_editProjectGoal != null) 'project_goal': _editProjectGoal,
        'interests': _editInterests.toList(),
        if (_editDailyTime != null) 'daily_learning_time_min': _editDailyTime,
      });
      if (!mounted) return;
      setState(() => _isEditMode = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('프로필이 업데이트됐습니다. 다음 브리핑에 반영됩니다.'),
          duration: Duration(seconds: 3),
        ),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('업데이트에 실패했습니다. 다시 시도해 주세요.')),
      );
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final profileAsync = ref.watch(profileNotifierProvider);
    return Scaffold(
      backgroundColor: AppColors.surfaceRaised,
      appBar: AppBar(
        title: Text('프로필', style: Theme.of(context).textTheme.displayMedium),
        backgroundColor: AppColors.surfaceRaised,
        elevation: 0,
        scrolledUnderElevation: 0,
        actions: [
          if (!_isEditMode)
            TextButton(
              onPressed: profileAsync.valueOrNull != null
                  ? () => _enterEditMode(profileAsync.requireValue)
                  : null,
              child: const Text('편집'),
            ),
        ],
      ),
      body: profileAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('프로필을 불러오지 못했습니다.'),
              const SizedBox(height: 12),
              TextButton(
                onPressed: () => ref.invalidate(profileNotifierProvider),
                child: const Text('다시 시도'),
              ),
            ],
          ),
        ),
        data: (profile) =>
            _isEditMode ? _buildEditMode() : _buildViewMode(profile),
      ),
    );
  }

  Widget _buildViewMode(UserProfile profile) {
    return ListView(
      children: [
        _ProfileRow(label: '역할', value: _roleLabel(profile.role)),
        _ProfileRow(label: '경험 수준', value: _experienceLabel(profile.experienceLevel)),
        _ProfileRow(
          label: '기술 스택',
          value: profile.techStack.isEmpty ? '—' : profile.techStack.join(', '),
        ),
        _ProfileRow(label: '프로젝트 목표', value: _goalLabel(profile.projectGoal)),
        _ProfileRow(
          label: '관심 영역',
          value: profile.interests.isEmpty ? '—' : profile.interests.join(', '),
        ),
        _ProfileRow(label: '하루 학습 시간', value: _dailyTimeLabel(profile.dailyLearningTimeMin)),
        const Divider(height: 1),
        ListTile(
          contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
          title: const Text('알림 설정'),
          subtitle: const Text('기기 설정에서 알림을 허용할 수 있습니다.'),
          trailing: const Icon(Icons.chevron_right),
          onTap: () => AppSettings.openAppSettings(type: AppSettingsType.notification),
        ),
      ],
    );
  }

  Widget _buildEditMode() {
    return Column(
      children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            children: [
              const SizedBox(height: 16),
              const _SectionLabel(label: '역할'),
              ..._roleOptions.map((opt) => _OptionCardTile(
                    label: opt.$1,
                    selected: _editRole == opt.$2,
                    onTap: () => setState(() => _editRole = opt.$2),
                  )),
              const SizedBox(height: 20),
              const _SectionLabel(label: '경험 수준'),
              ..._experienceOptions.map((opt) => _OptionCardTile(
                    label: opt.$1,
                    selected: _editExperience == opt.$2,
                    onTap: () => setState(() => _editExperience = opt.$2),
                  )),
              const SizedBox(height: 20),
              const _SectionLabel(label: '기술 스택'),
              _MultiSelectPills(
                options: _techStackOptions,
                selected: _editTechStack,
                onToggle: (v) => setState(() {
                  if (_editTechStack.contains(v)) {
                    _editTechStack.remove(v);
                  } else {
                    _editTechStack.add(v);
                  }
                }),
              ),
              const SizedBox(height: 20),
              const _SectionLabel(label: '프로젝트 목표'),
              ..._goalOptions.map((opt) => _OptionCardTile(
                    label: opt.$1,
                    selected: _editProjectGoal == opt.$2,
                    onTap: () => setState(() => _editProjectGoal = opt.$2),
                  )),
              const SizedBox(height: 20),
              const _SectionLabel(label: '관심 영역'),
              _MultiSelectPills(
                options: _interestOptions,
                selected: _editInterests,
                onToggle: (v) => setState(() {
                  if (_editInterests.contains(v)) {
                    _editInterests.remove(v);
                  } else {
                    _editInterests.add(v);
                  }
                }),
              ),
              const SizedBox(height: 20),
              const _SectionLabel(label: '하루 학습 시간'),
              ..._dailyTimeOptions.map((opt) => _OptionCardTile(
                    label: opt.$1,
                    selected: _editDailyTime == opt.$2,
                    onTap: () => setState(() => _editDailyTime = opt.$2),
                  )),
              const SizedBox(height: 24),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 40),
          child: Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: _cancelEdit,
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: AppColors.borderCard),
                    foregroundColor: AppColors.textPrimary,
                    minimumSize: const Size.fromHeight(52),
                  ),
                  child: Text(
                    '취소',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: FilledButton(
                  onPressed: _isSaveEnabled ? _saveProfile : null,
                  style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
                  child: Text(
                    '저장',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          color: AppColors.accentForeground,
                        ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

// ── 조회 행 ─────────────────────────────────────────────────────────

class _ProfileRow extends StatelessWidget {
  final String label;
  final String value;

  const _ProfileRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
      title: Text(
        label,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
      ),
      subtitle: Text(
        value,
        style: Theme.of(context).textTheme.bodyLarge,
      ),
    );
  }
}

// ── 편집 섹션 레이블 ─────────────────────────────────────────────────

class _SectionLabel extends StatelessWidget {
  final String label;

  const _SectionLabel({required this.label});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Text(
        label,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
      ),
    );
  }
}

// ── 단일 선택 옵션 카드 ──────────────────────────────────────────────

class _OptionCardTile extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _OptionCardTile({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
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
        child: Text(label, style: Theme.of(context).textTheme.bodyLarge),
      ),
    );
  }
}

// ── 멀티 선택 pill ───────────────────────────────────────────────────

class _MultiSelectPills extends StatelessWidget {
  final List<String> options;
  final Set<String> selected;
  final ValueChanged<String> onToggle;

  const _MultiSelectPills({
    required this.options,
    required this.selected,
    required this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    return Wrap(
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
    );
  }
}

// ── 라벨 매핑 ────────────────────────────────────────────────────────

const _roleOptions = [
  ('Frontend Developer', 'frontend'),
  ('Backend Developer', 'backend'),
  ('AI Engineer', 'ai_engineer'),
  ('Product Manager', 'pm'),
  ('Designer', 'designer'),
  ('Student', 'student'),
  ('기타', 'other'),
];

const _experienceOptions = [
  ('입문', 'beginner'),
  ('중급', 'intermediate'),
  ('고급', 'advanced'),
];

const _goalOptions = [
  ('AI 사이드 프로젝트 개발', 'ai_side_project'),
  ('RAG 서비스 구축', 'rag_service'),
  ('Agent Architecture 학습', 'agent_architecture'),
  ('업무 자동화', 'work_automation'),
  ('AI 도입 검토', 'ai_adoption'),
  ('기타', 'other'),
];

const _dailyTimeOptions = [
  ('15분', 15),
  ('30분', 30),
  ('1시간', 60),
];

const _techStackOptions = ['React', 'Next.js', 'Python', 'FastAPI', 'LangGraph', 'MCP', 'Claude Code', '기타'];
const _interestOptions = ['Agent', 'RAG', 'MCP', 'Coding Agent', 'Local LLM', 'AI UX', '기타'];

String _roleLabel(String? value) {
  return switch (value) {
    'frontend' => 'Frontend Developer',
    'backend' => 'Backend Developer',
    'ai_engineer' => 'AI Engineer',
    'pm' => 'Product Manager',
    'designer' => 'Designer',
    'student' => 'Student',
    'other' => '기타',
    _ => '—',
  };
}

String _experienceLabel(String? value) {
  return switch (value) {
    'beginner' => '입문',
    'intermediate' => '중급',
    'advanced' => '고급',
    _ => '—',
  };
}

String _goalLabel(String? value) {
  return switch (value) {
    'ai_side_project' => 'AI 사이드 프로젝트 개발',
    'rag_service' => 'RAG 서비스 구축',
    'agent_architecture' => 'Agent Architecture 학습',
    'work_automation' => '업무 자동화',
    'ai_adoption' => 'AI 도입 검토',
    'other' => '기타',
    _ => '—',
  };
}

String _dailyTimeLabel(int? value) {
  return switch (value) {
    15 => '15분',
    30 => '30분',
    60 => '1시간',
    _ => '—',
  };
}
