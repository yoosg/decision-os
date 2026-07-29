import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';
import '../../../core/theme/app_theme.dart';
import '../../notifications/providers/highlighted_signal_provider.dart';
import '../providers/daily_brief_provider.dart';
import '../widgets/signal_card.dart';
import '../widgets/three_dot_loading_indicator.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  bool _isOptimisticPending = false;

  static const _apiBase = String.fromEnvironment(
    'FASTAPI_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  Future<void> _handleRetry() async {
    if (_isOptimisticPending) return;
    setState(() => _isOptimisticPending = true);
    final session = Supabase.instance.client.auth.currentSession;
    try {
      await http.post(
        Uri.parse('$_apiBase/api/v1/daily-briefs/trigger'),
        headers: session != null
            ? {'Authorization': 'Bearer ${session.accessToken}'}
            : {},
      );
    } catch (_) {
      // 네트워크 오류 — 생성 중 상태 유지
    }
  }

  @override
  Widget build(BuildContext context) {
    final briefAsync = ref.watch(dailyBriefStreamProvider);
    final seenIds = ref.watch(seenSignalIdsProvider);
    final highlightedId = ref.watch(highlightedSignalProvider);

    return Scaffold(
      backgroundColor: AppColors.surfaceRaised,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.baseline,
                textBaseline: TextBaseline.alphabetic,
                children: [
                  Text(
                    '오늘의 AI 기술 브리핑',
                    style: Theme.of(context).textTheme.displayMedium,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    _todayDisplay(),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          fontSize: 11,
                          color: AppColors.textSecondary,
                        ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              briefAsync.when(
                loading: () => _buildGenerating(),
                error: (_, __) => _buildFailed(),
                data: (brief) {
                  if (_isOptimisticPending &&
                      (brief == null || brief.status == 'failed')) {
                    return _buildGenerating();
                  }
                  return _buildContent(brief, seenIds, highlightedId);
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildContent(
    DailyBrief? brief,
    Set<String> seenIds,
    String? highlightedId,
  ) {
    if (brief == null ||
        brief.status == 'pending' ||
        brief.status == 'processing') {
      return _buildGenerating();
    }
    if (brief.status == 'failed') {
      return _buildFailed();
    }

    final signalsAsync = ref.watch(dailyBriefSignalsProvider(brief.id));
    return signalsAsync.when(
      loading: () => _buildGenerating(),
      error: (_, __) => _buildGenerating(),
      data: (signals) {
        if (signals.isEmpty) return _buildNoSignals();
        final allSeen = signals.every((s) => seenIds.contains(s.signalId));
        return _buildSignalList(signals, seenIds, allSeen, highlightedId);
      },
    );
  }

  Widget _buildGenerating() {
    // WCAG 2.2 AA (Story 5.4 AC-B6): TalkBack이 생성 진행을 인지하도록 라이브 리전.
    return Semantics(
      liveRegion: true,
      container: true,
      label: '오늘의 브리핑을 생성하는 중입니다.',
      child: ExcludeSemantics(
        child: Row(
          children: [
            Text(
              '오늘의 브리핑을 생성하는 중입니다.',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: AppColors.textSecondary,
                  ),
            ),
            const SizedBox(width: 4),
            const ThreeDotLoadingIndicator(),
          ],
        ),
      ),
    );
  }

  Widget _buildFailed() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '오늘의 브리핑을 생성하지 못했습니다.',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                color: AppColors.textSecondary,
              ),
        ),
        const SizedBox(height: 12),
        SizedBox(
          height: 44,
          child: FilledButton(
            onPressed: _isOptimisticPending ? null : _handleRetry,
            child: const Text('다시 시도하기'),
          ),
        ),
      ],
    );
  }

  Widget _buildNoSignals() {
    return Builder(builder: (ctx) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '오늘은 새로운 기술 소식이 없습니다. 어제 보관함에 저장한 항목을 이어서 학습할 수 있습니다.',
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  color: AppColors.textSecondary,
                ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            height: 44,
            child: FilledButton(
              onPressed: () => ctx.go('/queue'),
              child: const Text('보관함 보기'),
            ),
          ),
        ],
      );
    });
  }

  Widget _buildSignalList(
    List<SignalItem> signals,
    Set<String> seenIds,
    bool allSeen,
    String? highlightedId,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ...signals.map((signal) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: SignalCard(
                signal: signal,
                isSeen: seenIds.contains(signal.signalId),
                isHighlighted: highlightedId == signal.signalId,
                onTap: () {
                  ref.read(seenSignalIdsProvider.notifier).mark(signal.signalId);
                  // 하이라이트 소비: 카드 탭 시 해제 (설계 결정 7 / Task 13.4)
                  if (highlightedId == signal.signalId) {
                    ref.read(highlightedSignalProvider.notifier).clear();
                  }
                  context.push('/home/review/${signal.signalId}');
                },
              ),
            )),
        if (allSeen)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Center(
              child: Text(
                '오늘 브리핑을 모두 확인했습니다.',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      fontSize: 11,
                      color: AppColors.textSecondary,
                    ),
              ),
            ),
          ),
      ],
    );
  }

  String _todayDisplay() {
    final now = DateTime.now();
    return '${now.year}.${now.month.toString().padLeft(2, '0')}.${now.day.toString().padLeft(2, '0')}';
  }
}
