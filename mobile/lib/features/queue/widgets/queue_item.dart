import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';

String timingLabelEn(String timing) => switch (timing) {
      'today' => 'Today',
      'this_week' => 'This Week',
      _ => 'Later',
    };

class QueueItem extends StatelessWidget {
  final String title;
  final String queueTiming;
  final int estimatedMinutes;
  final bool isOverdue;
  final VoidCallback onTap;
  final VoidCallback onReschedule;

  const QueueItem({
    super.key,
    required this.title,
    required this.queueTiming,
    required this.estimatedMinutes,
    required this.isOverdue,
    required this.onTap,
    required this.onReschedule,
  });

  @override
  Widget build(BuildContext context) {
    final label = timingLabelEn(queueTiming);

    return ConstrainedBox(
      constraints: const BoxConstraints(minHeight: 44),
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.surfaceCard,
          borderRadius: BorderRadius.circular(16),
        ),
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Semantics(
                // WCAG 2.2 AA (Story 5.4 AC-B2): 미완료(overdue)를 색상 텍스트(ExcludeSemantics)만이
                // 아니라 composite label에도 포함하여 TalkBack이 인지하도록 함.
                label:
                    '$label 예약됨, $title, 약 $estimatedMinutes분${isOverdue ? ', 미완료' : ''}',
                button: true,
                child: ExcludeSemantics(
                  child: InkWell(
                    onTap: onTap,
                    splashFactory: NoSplash.splashFactory,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: AppColors.surfaceCardAlt,
                                borderRadius: BorderRadius.circular(9999),
                              ),
                              child: Text(
                                label.toUpperCase(),
                                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                      color: AppColors.textSecondary,
                                    ),
                              ),
                            ),
                            if (isOverdue) ...[
                              const SizedBox(width: 6),
                              Text(
                                '미완료',
                                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                      color: AppColors.statusWarning,
                                    ),
                              ),
                            ],
                          ],
                        ),
                        const SizedBox(height: 6),
                        Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Text(title, style: Theme.of(context).textTheme.titleMedium),
                                  const SizedBox(height: 2),
                                  Text(
                                    '약 $estimatedMinutes분',
                                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                          color: AppColors.textSecondary,
                                        ),
                                  ),
                                ],
                              ),
                            ),
                            const Icon(Icons.chevron_right, size: 16, color: AppColors.textTertiary),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            Semantics(
              label: '일정 변경 — $title',
              button: true,
              child: ExcludeSemantics(
                child: TextButton(
                  onPressed: onReschedule,
                  style: TextButton.styleFrom(
                    minimumSize: const Size(0, 44),
                    padding: const EdgeInsets.symmetric(horizontal: 4),
                    splashFactory: NoSplash.splashFactory,
                  ),
                  child: Text(
                    '일정 변경',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: AppColors.textSecondary,
                          decoration: TextDecoration.underline,
                        ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
