import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';
import '../../history/providers/history_provider.dart';
import '../providers/outcome_provider.dart';
import '../providers/research_review_provider.dart';

const List<({String status, String english, String korean})> _kOutcomeOptions = [
  (status: 'completed', english: 'Completed', korean: '학습을 완료했습니다'),
  (status: 'applied', english: 'Applied', korean: '실제 프로젝트에 적용했습니다'),
  (status: 'dropped', english: 'Dropped', korean: '학습을 중단했습니다'),
  (status: 'not_useful', english: 'Not Useful', korean: '현재 상황에 맞지 않았습니다'),
];

class OutcomeScreen extends ConsumerStatefulWidget {
  final String signalId;

  const OutcomeScreen({super.key, required this.signalId});

  @override
  ConsumerState<OutcomeScreen> createState() => _OutcomeScreenState();
}

class _OutcomeScreenState extends ConsumerState<OutcomeScreen> {
  String? _selectedStatus;
  bool _useful = true;
  bool _isSubmitting = false;

  final _appliedProjectNoteController = TextEditingController();
  final _learningTimeController = TextEditingController();
  final _memoController = TextEditingController();

  @override
  void dispose() {
    _appliedProjectNoteController.dispose();
    _learningTimeController.dispose();
    _memoController.dispose();
    super.dispose();
  }

  String _headerSubtitle() {
    final reviewAsync = ref.watch(reviewStateProvider(widget.signalId));
    final state = reviewAsync.valueOrNull;
    if (state is ReviewCompleted) return state.review.signalTitle;
    return '';
  }

  Future<void> _handleSubmit() async {
    final status = _selectedStatus;
    if (status == null || _isSubmitting) return;

    HapticFeedback.mediumImpact();
    setState(() => _isSubmitting = true);

    final learningTimeText = _learningTimeController.text.trim();
    final learningTimeMin = learningTimeText.isEmpty ? null : int.tryParse(learningTimeText);

    final ok = await ref.read(outcomeControllerProvider(widget.signalId).notifier).submitOutcome(
          status: status,
          useful: _useful,
          actualLearningTimeMin: learningTimeMin,
          appliedProjectNote: status == 'applied' ? _appliedProjectNoteController.text : null,
          memo: _memoController.text,
        );

    if (!mounted) return;

    if (ok) {
      // 결과 반영: 히스토리 탭이 IndexedStack으로 살아있어 캐시가 남으므로 명시적 무효화.
      ref.invalidate(historyItemsProvider);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('결과가 기록됐습니다. 다음 브리핑에 반영됩니다.'),
          duration: Duration(seconds: 3),
        ),
      );
      Future.delayed(const Duration(milliseconds: 1500), () {
        if (mounted) context.go('/home');
      });
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('오류가 발생했습니다. 다시 시도해 주세요.')),
      );
      setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final subtitle = _headerSubtitle();

    return Scaffold(
      backgroundColor: AppColors.surfaceBase,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 24, 20, 40),
          children: [
            Text(
              '학습 결과를 기록해 주세요',
              style: Theme.of(context).textTheme.displayLarge,
            ),
            if (subtitle.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                subtitle,
                style: const TextStyle(fontSize: 13, color: AppColors.textSecondary),
              ),
            ],
            const SizedBox(height: 24),
            Semantics(
              label: '학습 결과를 선택해 주세요',
              child: Column(
                children: [
                  for (final option in _kOutcomeOptions)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Semantics(
                            label: '${option.english} — ${option.korean}',
                            inMutuallyExclusiveGroup: true,
                            checked: _selectedStatus == option.status,
                            child: _OutcomeOptionCard(
                              label: option.korean,
                              selected: _selectedStatus == option.status,
                              onTap: () => setState(() => _selectedStatus = option.status),
                            ),
                          ),
                          if (option.status == 'applied' && _selectedStatus == 'applied') ...[
                            const SizedBox(height: 8),
                            TextField(
                              controller: _appliedProjectNoteController,
                              decoration: const InputDecoration(
                                hintText: '어떤 프로젝트에 적용했나요? (선택)',
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            Text('유용했나요?', style: Theme.of(context).textTheme.labelLarge),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: _UsefulPillButton(
                    label: '예',
                    selected: _useful,
                    onTap: () => setState(() => _useful = true),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _UsefulPillButton(
                    label: '아니오',
                    selected: !_useful,
                    onTap: () => setState(() => _useful = false),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Text('실제 학습 시간', style: Theme.of(context).textTheme.labelLarge),
            const SizedBox(height: 8),
            Row(
              children: [
                SizedBox(
                  width: 100,
                  child: TextField(
                    controller: _learningTimeController,
                    keyboardType: TextInputType.number,
                    inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                  ),
                ),
                const SizedBox(width: 8),
                const Text('분', style: TextStyle(color: AppColors.textSecondary)),
              ],
            ),
            const SizedBox(height: 16),
            Text('메모', style: Theme.of(context).textTheme.labelLarge),
            const SizedBox(height: 8),
            TextField(
              controller: _memoController,
              maxLines: 4,
              decoration: const InputDecoration(
                hintText: '적용 방식, 막힌 부분, 다음 단계 등을 남겨두세요',
              ),
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.accentPrimary,
                foregroundColor: AppColors.accentForeground,
                minimumSize: const Size.fromHeight(52),
                shape: const StadiumBorder(),
              ),
              onPressed: _selectedStatus == null || _isSubmitting ? null : _handleSubmit,
              child: const Text('기록하기'),
            ),
          ],
        ),
      ),
    );
  }
}

class _OutcomeOptionCard extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _OutcomeOptionCard({
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
        child: Text(label, style: Theme.of(context).textTheme.bodyLarge),
      ),
    );
  }
}

class _UsefulPillButton extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _UsefulPillButton({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return OutlinedButton(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size.fromHeight(44),
        shape: const StadiumBorder(),
        backgroundColor: selected ? AppColors.accentPrimary : null,
        foregroundColor: selected ? AppColors.accentForeground : AppColors.textPrimary,
        side: BorderSide(color: selected ? AppColors.accentPrimary : AppColors.borderSubtle),
      ),
      onPressed: onTap,
      child: Text(label),
    );
  }
}
