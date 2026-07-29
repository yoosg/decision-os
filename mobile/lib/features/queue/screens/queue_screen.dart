import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
import '../providers/queue_provider.dart';
import '../widgets/queue_item.dart';
import '../widgets/reschedule_sheet.dart';

const List<(String, String)> _kGroupOrder = [
  ('today', 'Today'),
  ('this_week', 'This Week'),
  ('later', 'Later'),
];

class QueueScreen extends ConsumerWidget {
  const QueueScreen({super.key});

  Future<void> _handleReschedule(
    BuildContext context,
    WidgetRef ref,
    QueueItemData item,
  ) async {
    final messenger = ScaffoldMessenger.of(context);
    final newTiming = await showRescheduleSheet(context, currentTiming: item.queueTiming);
    if (newTiming == null) return;
    try {
      await ref.read(queueItemsProvider.notifier).reschedule(item.decisionId, newTiming);
    } catch (e) {
      messenger.showSnackBar(
        const SnackBar(
          content: Text('저장 중 오류가 발생했습니다. 다시 시도해 주세요.'),
          duration: Duration(seconds: 3),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final itemsAsync = ref.watch(queueItemsProvider);
    final minutesAsync = ref.watch(estimatedLearningMinutesProvider);

    return Scaffold(
      backgroundColor: AppColors.surfaceRaised,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
          child: itemsAsync.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (_, __) => Text(
              '보관함을 불러오지 못했습니다.',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: AppColors.textSecondary,
                  ),
            ),
            data: (items) {
              final estimatedMinutes = minutesAsync.valueOrNull ?? 30;
              final groups = <String, List<QueueItemData>>{
                'today': [],
                'this_week': [],
                'later': [],
              };
              for (final item in items) {
                groups[item.queueTiming]?.add(item);
              }
              final isEmpty = groups.values.every((g) => g.isEmpty);

              if (isEmpty) {
                return Text(
                  '보관함에 저장된 학습 항목이 없습니다. 기술 소식을 읽고 "나중에 학습"을 선택하면 여기에 저장됩니다.',
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                        color: AppColors.textSecondary,
                      ),
                );
              }

              return ListView(
                children: [
                  for (final (key, label) in _kGroupOrder)
                    if (groups[key]!.isNotEmpty) ...[
                      Text(label, style: Theme.of(context).textTheme.displayMedium),
                      const SizedBox(height: 12),
                      for (final item in groups[key]!) ...[
                        QueueItem(
                          title: item.title,
                          queueTiming: item.queueTiming,
                          estimatedMinutes: estimatedMinutes,
                          isOverdue: item.isOverdue,
                          onTap: () => context.push('/queue/review/${item.signalId}'),
                          onReschedule: () => _handleReschedule(context, ref, item),
                        ),
                        const SizedBox(height: 10),
                      ],
                      const SizedBox(height: 14),
                    ],
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}
