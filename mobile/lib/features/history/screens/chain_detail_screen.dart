import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';
import '../../home/widgets/review_sections.dart';
import '../providers/chain_detail_provider.dart';
import '../providers/history_provider.dart' show formatCardDate;
import '../widgets/archived_banner.dart';
import '../widgets/memory_timeline_item.dart';

class ChainDetailScreen extends ConsumerWidget {
  final String signalId;

  const ChainDetailScreen({super.key, required this.signalId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dataAsync = ref.watch(chainDetailProvider(signalId));

    return Scaffold(
      backgroundColor: AppColors.surfaceRaised,
      body: SafeArea(
        child: dataAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (_, __) => _Padded(
            child: Text(
              '체인 상세를 불러오지 못했습니다.',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: AppColors.textSecondary,
                  ),
            ),
          ),
          data: (data) {
            if (data == null) {
              return _Padded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const _BackButton(),
                    const SizedBox(height: 20),
                    Text(
                      '해당 기록을 찾을 수 없습니다.',
                      style: Theme.of(context).textTheme.bodyLarge,
                    ),
                  ],
                ),
              );
            }
            return _ChainDetailBody(data: data);
          },
        ),
      ),
    );
  }
}

class _Padded extends StatelessWidget {
  final Widget child;
  const _Padded({required this.child});

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
        child: child,
      );
}

class _ChainDetailBody extends StatelessWidget {
  final ChainDetailData data;
  const _ChainDetailBody({required this.data});

  @override
  Widget build(BuildContext context) {
    final signal = data.signal;
    final decision = data.decision;
    final outcome = data.outcome;
    final isLearnNow = decision?.choice == 'learn_now';

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 48),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _BackButton(),
          const SizedBox(height: 20),

          if (signal.status == 'archived') ...[
            const ArchivedBanner(),
            const SizedBox(height: 24),
          ],

          // Signal 노드
          _ChainNode(
            dot: const TimelineDot(color: AppColors.textSecondary),
            typeLabel: 'SIGNAL',
            child: Semantics(
              header: true,
              child: Text(
                signal.title,
                style: Theme.of(context).textTheme.displayMedium,
              ),
            ),
          ),

          // Review 노드
          if (data.reviewPayload != null)
            _ChainNode(
              dot: const TimelineDot(color: AppColors.textSecondary),
              typeLabel: 'REVIEW',
              child: ReviewSections(payload: data.reviewPayload!),
            ),

          // Decision 노드
          if (decision != null)
            _ChainNode(
              dot: TimelineDot.forStyle(DecisionDot(decision.choice)),
              typeLabel: 'DECISION',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    kDecisionTypeLabel[decision.choice] ?? decision.choice.toUpperCase(),
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    formatCardDate(decision.createdAt),
                    style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                  ),
                ],
              ),
            ),

          // Outcome 노드 (AC-5)
          if (outcome != null)
            _ChainNode(
              isLast: true,
              dot: TimelineDot.forStyle(OutcomeDot(outcome.status)),
              typeLabel: 'OUTCOME',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    kOutcomeKoreanLabel[outcome.status] ?? outcome.status,
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  if (outcome.actualLearningTimeMin != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      '실제 학습 시간 약 ${outcome.actualLearningTimeMin}분',
                      style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                    ),
                  ],
                  if (outcome.appliedProjectNote != null &&
                      outcome.appliedProjectNote!.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      outcome.appliedProjectNote!,
                      style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                    ),
                  ],
                  if (outcome.memo != null && outcome.memo!.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Text(outcome.memo!, style: Theme.of(context).textTheme.bodyLarge),
                  ],
                  const SizedBox(height: 6),
                  Text(
                    formatCardDate(outcome.createdAt),
                    style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                  ),
                ],
              ),
            )
          else
            // 미기록: learn_now 는 "미완료"(AC-5), queue/ignore 는 흐리게 통일 (설계 결정 1)
            Opacity(
              opacity: isLearnNow ? 1 : 0.55,
              child: const _ChainNode(
                isLast: true,
                dot: TimelineDot(color: AppColors.textSecondary, glyph: '?'),
                typeLabel: 'OUTCOME',
                child: Text(
                  '미완료',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textSecondary,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

// ─── 체인 단일 노드 (좌측 spine + 도트 + 콘텐츠) ─────────────────────────────

class _ChainNode extends StatelessWidget {
  final Widget dot;
  final String typeLabel;
  final Widget child;
  final bool isLast;

  const _ChainNode({
    required this.dot,
    required this.typeLabel,
    required this.child,
    this.isLast = false,
  });

  @override
  Widget build(BuildContext context) {
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            width: 12,
            child: Stack(
              clipBehavior: Clip.none,
              children: [
                if (!isLast)
                  Positioned(
                    left: 5,
                    top: 14,
                    bottom: 0,
                    child: Container(width: 2, color: AppColors.borderSubtle),
                  ),
                Positioned(top: 2, left: 0, child: dot),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(bottom: isLast ? 0 : 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    typeLabel,
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: AppColors.textSecondary,
                          letterSpacing: 0.5,
                        ),
                  ),
                  const SizedBox(height: 6),
                  child,
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _BackButton extends StatelessWidget {
  const _BackButton();

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => context.canPop() ? context.pop() : context.go('/history'),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.chevron_left, size: 20, color: AppColors.textSecondary),
          Text(
            '히스토리로',
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: AppColors.textSecondary,
                ),
          ),
        ],
      ),
    );
  }
}
