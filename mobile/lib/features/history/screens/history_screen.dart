import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
import '../providers/history_provider.dart';
import '../widgets/memory_timeline_item.dart';

class HistoryScreen extends ConsumerWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final itemsAsync = ref.watch(historyItemsProvider);

    return Scaffold(
      backgroundColor: AppColors.surfaceRaised,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
          child: itemsAsync.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (_, __) => Text(
              '히스토리를 불러오지 못했습니다.',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: AppColors.textSecondary,
                  ),
            ),
            data: (items) {
              if (items.isEmpty) {
                return Text(
                  '아직 기록된 학습 결정이 없습니다. 기술 소식을 읽고 "지금 학습"을 선택하면 이곳에 기록이 시작됩니다.',
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                        color: AppColors.textSecondary,
                      ),
                );
              }

              // 이미 역시간순 정렬 — 순서 유지하며 월별 그룹핑
              final groups = <(String, List<HistoryItemData>)>[];
              for (final item in items) {
                final ym = kstYearMonth(item.createdAt);
                if (groups.isNotEmpty && groups.last.$1 == ym) {
                  groups.last.$2.add(item);
                } else {
                  groups.add((ym, [item]));
                }
              }

              return ListView(
                children: [
                  Text('히스토리', style: Theme.of(context).textTheme.displayMedium),
                  const SizedBox(height: 20),
                  for (final (yearMonth, groupItems) in groups) ...[
                    Text(
                      formatMonthDivider(yearMonth),
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: AppColors.textSecondary,
                            fontSize: 11,
                          ),
                    ),
                    const SizedBox(height: 12),
                    for (final item in groupItems)
                      MemoryTimelineItem(
                        title: item.title,
                        dateLabel: formatCardDate(item.createdAt),
                        dotStyle: resolveDotStyle(
                          choice: item.choice,
                          outcomeStatus: item.outcomeStatus,
                        ),
                        onTap: () => context.push('/history/chain/${item.signalId}'),
                      ),
                    const SizedBox(height: 24),
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
