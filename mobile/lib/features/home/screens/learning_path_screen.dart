import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/theme/app_theme.dart';
import '../providers/learning_path_provider.dart';
import '../providers/research_review_provider.dart';
import '../widgets/three_dot_loading_indicator.dart';

const Map<String, String> _kTypeLabels = {
  'official_docs': '공식 문서',
  'core_material': '핵심 자료',
  'github': 'GitHub',
  'practice_example': '실습 예제',
  'applied_idea': '적용 아이디어',
};

class LearningPathScreen extends ConsumerStatefulWidget {
  final String signalId;

  const LearningPathScreen({super.key, required this.signalId});

  @override
  ConsumerState<LearningPathScreen> createState() => _LearningPathScreenState();
}

class _LearningPathScreenState extends ConsumerState<LearningPathScreen>
    with WidgetsBindingObserver {
  bool _hasVisitedExternal = false;
  bool _showOutcomePrompt = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && _hasVisitedExternal && mounted) {
      setState(() => _showOutcomePrompt = true);
    }
  }

  void _onVisitExternal() {
    setState(() => _hasVisitedExternal = true);
  }

  String _headerTitle() {
    final reviewAsync = ref.watch(reviewStateProvider(widget.signalId));
    final state = reviewAsync.valueOrNull;
    if (state is ReviewCompleted) {
      return '${state.review.signalTitle} Learning Path';
    }
    return 'Learning Path';
  }

  @override
  Widget build(BuildContext context) {
    final pathAsync = ref.watch(learningPathControllerProvider(widget.signalId));

    return Scaffold(
      backgroundColor: AppColors.surfaceRaised,
      appBar: AppBar(
        backgroundColor: AppColors.surfaceRaised,
        elevation: 0,
        title: Text(
          _headerTitle(),
          style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: AppColors.textSecondary,
              ),
        ),
      ),
      body: pathAsync.when(
        loading: () => const _GeneratingBody(),
        error: (_, __) => _FailedBody(
          onRetry: () => ref.read(learningPathControllerProvider(widget.signalId).notifier).retry(),
        ),
        data: (state) => switch (state) {
          LearningPathGenerating() => const _GeneratingBody(),
          LearningPathReady(:final resources) => _ReadyBody(
              resources: resources,
              showOutcomePrompt: _showOutcomePrompt,
              onVisitExternal: _onVisitExternal,
              onRecordOutcome: () => context.push('/home/review/${widget.signalId}/outcome'),
            ),
          LearningPathFailed() => _FailedBody(
              onRetry: () => ref.read(learningPathControllerProvider(widget.signalId).notifier).retry(),
            ),
        },
      ),
    );
  }
}

class _GeneratingBody extends StatelessWidget {
  const _GeneratingBody();

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
        child: Row(
          children: [
            Text(
              '학습 경로를 생성하는 중입니다.',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: AppColors.textSecondary,
                  ),
            ),
            const SizedBox(width: 8),
            const ThreeDotLoadingIndicator(),
          ],
        ),
      ),
    );
  }
}

class _FailedBody extends StatelessWidget {
  final VoidCallback onRetry;

  const _FailedBody({required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '학습 경로를 생성하지 못했습니다.',
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.accentPrimary,
                foregroundColor: AppColors.accentForeground,
              ),
              onPressed: onRetry,
              child: const Text('다시 시도하기'),
            ),
            const SizedBox(height: 8),
            TextButton(
              onPressed: () => context.go('/home'),
              child: const Text('홈으로 돌아가기'),
            ),
          ],
        ),
      ),
    );
  }
}

class _ReadyBody extends StatelessWidget {
  final List<LearningPathResource> resources;
  final bool showOutcomePrompt;
  final VoidCallback onVisitExternal;
  final VoidCallback onRecordOutcome;

  const _ReadyBody({
    required this.resources,
    required this.showOutcomePrompt,
    required this.onVisitExternal,
    required this.onRecordOutcome,
  });

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        SafeArea(
          bottom: false,
          child: ListView.separated(
            padding: EdgeInsets.fromLTRB(20, 20, 20, showOutcomePrompt ? 120 : 24),
            itemCount: resources.length,
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemBuilder: (context, index) => _LearningPathCard(
              resource: resources[index],
              onVisit: onVisitExternal,
            ),
          ),
        ),
        if (showOutcomePrompt)
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: SafeArea(
              top: false,
              child: Container(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
                decoration: const BoxDecoration(
                  color: AppColors.surfaceBase,
                  border: Border(top: BorderSide(color: AppColors.borderSubtle)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      '학습을 완료했나요? 결과를 기록해 주세요.',
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                            color: AppColors.textPrimary,
                          ),
                    ),
                    const SizedBox(height: 8),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.accentPrimary,
                        foregroundColor: AppColors.accentForeground,
                      ),
                      onPressed: onRecordOutcome,
                      child: const Text('결과 기록하기'),
                    ),
                  ],
                ),
              ),
            ),
          ),
      ],
    );
  }
}

bool _isSafeExternalUrl(String url) {
  final uri = Uri.tryParse(url);
  return uri != null && (uri.scheme == 'http' || uri.scheme == 'https');
}

class _LearningPathCard extends StatelessWidget {
  final LearningPathResource resource;
  final VoidCallback onVisit;

  const _LearningPathCard({required this.resource, required this.onVisit});

  Future<void> _handleTap(BuildContext context) async {
    final uri = Uri.tryParse(resource.url);
    if (uri == null || (uri.scheme != 'http' && uri.scheme != 'https')) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('링크를 열 수 없습니다.')),
      );
      return;
    }
    final opened = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (opened) onVisit();
  }

  @override
  Widget build(BuildContext context) {
    final label = _kTypeLabels[resource.type] ?? resource.type;
    final hasUrl = resource.url.isNotEmpty && _isSafeExternalUrl(resource.url);
    final isEnglishLabel = resource.type == 'github';

    return Material(
      color: AppColors.surfaceCard,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: hasUrl ? () => _handleTap(context) : null,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Semantics(
                      label: label,
                      excludeSemantics: true,
                      child: isEnglishLabel
                          ? Localizations.override(
                              context: context,
                              locale: const Locale('en'),
                              child: Text(
                                label,
                                style: const TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: 1.0,
                                  color: AppColors.textSecondary,
                                ),
                              ),
                            )
                          : Text(
                              label,
                              style: const TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w700,
                                letterSpacing: 1.0,
                                color: AppColors.textSecondary,
                              ),
                            ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      resource.title,
                      style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                            color: AppColors.textPrimary,
                          ),
                    ),
                    if (resource.descriptor.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(
                        resource.descriptor,
                        style: const TextStyle(fontSize: 13, color: AppColors.textSecondary),
                      ),
                    ],
                  ],
                ),
              ),
              if (hasUrl) ...[
                const SizedBox(width: 12),
                const Icon(Icons.open_in_new, size: 14, color: AppColors.textTertiary),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
