import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../providers/daily_brief_provider.dart';

class SignalCard extends StatelessWidget {
  final SignalItem signal;
  final bool isSeen;
  final bool isHighlighted;
  final VoidCallback onTap;

  const SignalCard({
    super.key,
    required this.signal,
    required this.isSeen,
    this.isHighlighted = false,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final semanticLabel =
        '${signal.title}${!isSeen ? ', NEW' : ''}${isHighlighted ? ', 알림 대상' : ''}, 출처 ${signal.sourceCount}개, 읽기 약 5분';

    return Semantics(
      label: semanticLabel,
      button: true,
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          constraints: const BoxConstraints(minHeight: 44),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            // Story 5.3 설계 결정 7: 하이라이트는 accent 보더로 표현 (isSeen NEW 배지와 구분)
            color: isHighlighted ? AppColors.surfaceCardAlt : AppColors.surfaceCard,
            borderRadius: BorderRadius.circular(16),
            border: isHighlighted
                ? Border.all(color: AppColors.accentPrimary, width: 2)
                : null,
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            signal.title,
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                  color: AppColors.textPrimary,
                                ),
                          ),
                        ),
                        if (!isSeen) ...[
                          const SizedBox(width: 8),
                          ExcludeSemantics(
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: AppColors.accentPrimary,
                                borderRadius: BorderRadius.circular(9999),
                              ),
                              child: Text(
                                'NEW',
                                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                      color: AppColors.accentForeground,
                                    ),
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                    if (signal.summary != null) ...[
                      const SizedBox(height: 4),
                      Text(
                        signal.summary!,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: AppColors.textSecondary,
                            ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                    const SizedBox(height: 2),
                    Text(
                      '출처 ${signal.sourceCount}개 · 읽기 약 5분',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            fontSize: 11,
                            color: AppColors.textTertiary,
                          ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              const Icon(
                Icons.chevron_right,
                color: AppColors.textTertiary,
                size: 20,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
