import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';
import '../providers/research_review_provider.dart';

/// Research Review 의 12개 섹션 + 참고 출처 + HonestBox 렌더링만 담당하는 순수 위젯.
///
/// 뒤로가기 / 타이틀 / "AI에게 질문하기" 링크 / _DynamicContextStickyBar 는 포함하지 않는다
/// (이들은 Home/Queue 전용 인터랙티브 UI). Home 화면은 섹션 gating 을 위해
/// [sectionKeys] 와 [focusNodes] 를 전달하고, 읽기 전용 Chain 상세(History)는 생략한다.
class ReviewSections extends StatelessWidget {
  final ReviewPayload payload;
  final Map<String, GlobalKey>? sectionKeys;
  final Map<String, FocusNode>? focusNodes;

  const ReviewSections({
    super.key,
    required this.payload,
    this.sectionKeys,
    this.focusNodes,
  });

  @override
  Widget build(BuildContext context) {
    final p = payload;

    final difficultyLabel = {
          'beginner': '입문',
          'intermediate': '중급',
          'advanced': '고급',
        }[p.learningTimeDifficulty.difficulty] ??
        p.learningTimeDifficulty.difficulty;
    final learningTimeText =
        '${p.learningTimeDifficulty.estimatedHours.toStringAsFixed(0)}시간 · $difficultyLabel';

    Widget section(String label, String key, String content,
        {bool showProfileLabel = false}) {
      return _ReviewSection(
        data: _SectionData(label, key, content, showProfileLabel: showProfileLabel),
        globalKey: sectionKeys?[key],
        focusNode: focusNodes?[key],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Section 1-6
        section('핵심 한 줄 요약', 'one_line_definition', p.oneLineDefinition),
        section('핵심 개념 설명', 'key_concepts', p.keyConcepts),
        section('해결하는 문제', 'problems_solved', p.problemsSolved),
        section('왜 지금 중요한가', 'why_it_matters', p.whyItMatters),
        section('기존 기술과의 차이', 'vs_existing_tech', p.vsExistingTech),
        section('사용자 관련성', 'user_relevance', p.userRelevance,
            showProfileLabel: true),

        // Section 7-9 (not required)
        section('학습 목표', 'learning_goals', p.learningGoals),
        section('예상 학습 시간 + 난이도', 'learning_time_difficulty', learningTimeText),
        section('실무 적용 가능성', 'practical_applicability', p.practicalApplicability),

        // Section 10-11 (required)
        section('위험 요소', 'risks', p.risks),
        section('추천 이유', 'recommendation_reason', p.recommendationReason),

        // Section 12: 참고 출처
        _ReferenceSourcesSection(sources: p.referenceSources),

        const SizedBox(height: 16),

        // Section 13: HonestBox
        if (p.honestBox.content.isNotEmpty) ...[
          _HonestBox(
            content: p.honestBox.content,
            severity: p.honestBox.severity,
          ),
          const SizedBox(height: 16),
        ],
      ],
    );
  }
}

// ─── _SectionData ────────────────────────────────────────────────────────

class _SectionData {
  final String label;
  final String sectionKey;
  final String content;
  final bool showProfileLabel;

  const _SectionData(
    this.label,
    this.sectionKey,
    this.content, {
    this.showProfileLabel = false,
  });
}

// ─── _ReviewSection ───────────────────────────────────────────────────────

class _ReviewSection extends StatelessWidget {
  final _SectionData data;
  final GlobalKey? globalKey;
  final FocusNode? focusNode;

  const _ReviewSection({required this.data, this.globalKey, this.focusNode});

  @override
  Widget build(BuildContext context) {
    final heading = Semantics(
      header: true,
      child: Text(
        data.label,
        key: globalKey ?? Key('section-${data.sectionKey}'),
        style: Theme.of(context).textTheme.titleLarge,
      ),
    );
    return Padding(
      padding: const EdgeInsets.only(bottom: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          focusNode != null
              ? Focus(focusNode: focusNode, child: heading)
              : heading,
          if (data.showProfileLabel) ...[
            const SizedBox(height: 4),
            Text(
              '현재 프로필 기준',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppColors.textSecondary,
                    fontSize: 11,
                  ),
            ),
          ],
          const SizedBox(height: 8),
          Text(
            data.content,
            style: Theme.of(context).textTheme.bodyLarge,
          ),
        ],
      ),
    );
  }
}

// ─── _ReferenceSourcesSection ─────────────────────────────────────────────

class _ReferenceSourcesSection extends StatelessWidget {
  final List<String> sources;

  const _ReferenceSourcesSection({required this.sources});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Semantics(
            header: true,
            child: Text(
              '참고 출처',
              key: const Key('section-reference_sources'),
              style: Theme.of(context).textTheme.titleLarge,
            ),
          ),
          const SizedBox(height: 8),
          ...sources.map((url) => GestureDetector(
                onTap: () {},
                child: Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text(
                    url,
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                          color: AppColors.textSecondary,
                          decoration: TextDecoration.underline,
                        ),
                  ),
                ),
              )),
        ],
      ),
    );
  }
}

// ─── _HonestBox ───────────────────────────────────────────────────────────

class _HonestBox extends StatelessWidget {
  final String content;
  final String severity;

  const _HonestBox({required this.content, required this.severity});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surfaceHonestBox,
        borderRadius: BorderRadius.circular(12),
        border: severity == 'high'
            ? const Border(
                left: BorderSide(
                  color: AppColors.statusWarning,
                  width: 3,
                ),
              )
            : null,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // WCAG 2.2 AA (Story 5.4 AC-B2): high severity를 색상(border)만으로 전달하지 않도록
          // 도형 기반 글리프(⚠) + Semantics label 병행.
          Semantics(
            label: severity == 'high'
                ? '주의 필요: AI가 놓쳤을 수 있는 점'
                : 'AI가 놓쳤을 수 있는 점',
            child: ExcludeSemantics(
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (severity == 'high') ...[
                    Text(
                      '⚠',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            fontSize: 11,
                            color: AppColors.statusWarning,
                          ),
                    ),
                    const SizedBox(width: 4),
                  ],
                  Text(
                    'AI가 놓쳤을 수 있는 점',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: AppColors.textSecondary,
                          letterSpacing: 0.5,
                        ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            content,
            style: Theme.of(context).textTheme.bodyLarge,
          ),
        ],
      ),
    );
  }
}
