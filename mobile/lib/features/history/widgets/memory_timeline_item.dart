import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';

// ─── Outcome 라벨/색상/글리프 매핑 (Web OUTCOME_OPTIONS 재사용 상당) ──────────
// Flutter 쪽 _kOutcomeOptions 는 outcome_screen.dart 에 private 로 존재하므로
// 여기서는 히스토리 전용 매핑을 정의한다(라벨 문자열은 동일).
const Map<String, String> kOutcomeEnglishLabel = {
  'completed': 'Completed',
  'applied': 'Applied',
  'dropped': 'Dropped',
  'not_useful': 'Not Useful',
};
const Map<String, String> kOutcomeKoreanLabel = {
  'completed': '학습을 완료했습니다',
  'applied': '실제 프로젝트에 적용했습니다',
  'dropped': '학습을 중단했습니다',
  'not_useful': '현재 상황에 맞지 않았습니다',
};
const Map<String, Color> _kOutcomeColor = {
  'completed': AppColors.statusPositive,
  'applied': AppColors.statusPositive,
  'dropped': AppColors.textPrimary,
  'not_useful': AppColors.textSecondary,
};
const Map<String, String> _kOutcomeGlyph = {
  'completed': '✓',
  'applied': '→',
  'dropped': '✕',
  'not_useful': '−',
};
const Map<String, String> kDecisionTypeLabel = {
  'learn_now': 'LEARN NOW',
  'queue': 'QUEUE',
  'ignore': 'IGNORE',
};

// ─── 도트 스타일 ──────────────────────────────────────────────────────────

sealed class TimelineDotStyle {
  const TimelineDotStyle();
}

class DecisionDot extends TimelineDotStyle {
  final String choice; // learn_now | queue | ignore
  const DecisionDot(this.choice);
}

class OutcomeDot extends TimelineDotStyle {
  final String status; // completed | applied | dropped | not_useful
  const OutcomeDot(this.status);
}

class OutcomePendingDot extends TimelineDotStyle {
  const OutcomePendingDot();
}

// 결정/Outcome 상태 → 도트 스타일 (설계 결정 1, AC-2/AC-5) — Web resolveDotStyle 과 동일 규칙
TimelineDotStyle resolveDotStyle({required String choice, String? outcomeStatus}) {
  if (outcomeStatus != null) return OutcomeDot(outcomeStatus);
  if (choice == 'learn_now') return const OutcomePendingDot();
  return DecisionDot(choice);
}

Color dotColor(TimelineDotStyle style) => switch (style) {
      OutcomeDot(:final status) => _kOutcomeColor[status] ?? AppColors.textSecondary,
      OutcomePendingDot() => AppColors.textSecondary,
      DecisionDot() => AppColors.textPrimary,
    };

String? dotGlyph(TimelineDotStyle style) => switch (style) {
      OutcomeDot(:final status) => _kOutcomeGlyph[status],
      OutcomePendingDot() => '?',
      DecisionDot() => null,
    };

String dotTypeLabel(TimelineDotStyle style) => switch (style) {
      OutcomeDot(:final status) =>
        (kOutcomeEnglishLabel[status] ?? status).toUpperCase(),
      OutcomePendingDot() => 'IN PROGRESS',
      DecisionDot(:final choice) => kDecisionTypeLabel[choice] ?? choice.toUpperCase(),
    };

// AC-2: Outcome 도트만 composite Semantics label. Decision 스타일은 null(카드 텍스트로 전달).
String? dotSemanticsLabel(TimelineDotStyle style, String title) => switch (style) {
      OutcomeDot(:final status) =>
        '${kOutcomeEnglishLabel[status] ?? status} 결과 — $title',
      OutcomePendingDot() => '미완료 결과 — $title',
      DecisionDot() => null,
    };

// ─── 공용 도트 위젯 (memory_timeline_item + chain_detail_screen 공유, Task 16.3) ──

class TimelineDot extends StatelessWidget {
  final Color color;
  final String? glyph;

  const TimelineDot({super.key, required this.color, this.glyph});

  factory TimelineDot.forStyle(TimelineDotStyle style) =>
      TimelineDot(color: dotColor(style), glyph: dotGlyph(style));

  @override
  Widget build(BuildContext context) {
    final g = glyph;
    return Container(
      width: 12,
      height: 12,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        border: Border.all(color: AppColors.surfaceBase, width: 2),
      ),
      child: g == null
          ? null
          : ExcludeSemantics(
              child: Text(
                g,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 8,
                  fontWeight: FontWeight.w700,
                  height: 1,
                ),
              ),
            ),
    );
  }
}

// ─── MemoryTimelineItem ───────────────────────────────────────────────────

class MemoryTimelineItem extends StatelessWidget {
  final String title;
  final String dateLabel; // "M월 D일"
  final TimelineDotStyle dotStyle;
  final VoidCallback onTap;

  const MemoryTimelineItem({
    super.key,
    required this.title,
    required this.dateLabel,
    required this.dotStyle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final semanticsLabel = dotSemanticsLabel(dotStyle, title);

    final card = ConstrainedBox(
      constraints: const BoxConstraints(minHeight: 44),
      child: IntrinsicHeight(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // 좌측 spine + 도트
            SizedBox(
              width: 12,
              child: Stack(
                clipBehavior: Clip.none,
                children: [
                  Positioned(
                    left: 5,
                    top: 0,
                    bottom: 0,
                    child: Container(width: 2, color: AppColors.borderSubtle),
                  ),
                  Positioned(top: 14, left: 0, child: TimelineDot.forStyle(dotStyle)),
                ],
              ),
            ),
            const SizedBox(width: 12),
            // 카드 (AC-3)
            Expanded(
              child: Container(
                // 웹(memory-timeline-item paddingBottom:10)과 동일 — 카드 사이 간격.
                // margin으로 주면 좌측 spine(stretch)은 이 간격 아래까지 이어져 연속선 유지.
                margin: const EdgeInsets.only(bottom: 10),
                decoration: BoxDecoration(
                  color: AppColors.surfaceCard,
                  borderRadius: BorderRadius.circular(12),
                ),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      dotTypeLabel(dotStyle),
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                            color: AppColors.textSecondary,
                            letterSpacing: 0.5,
                          ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      title,
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      dateLabel,
                      style: const TextStyle(
                        fontSize: 12,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );

    final tappable = InkWell(
      onTap: onTap,
      splashFactory: NoSplash.splashFactory,
      child: card,
    );

    // AC-2: Outcome/미완료 도트는 composite label + glyph ExcludeSemantics(TimelineDot 내부 처리)
    if (semanticsLabel != null) {
      return Semantics(
        button: true,
        label: semanticsLabel,
        child: ExcludeSemantics(child: tappable),
      );
    }
    return tappable;
  }
}
