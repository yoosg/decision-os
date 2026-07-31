import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';
import '../../../core/theme/app_theme.dart';
import '../../history/providers/history_provider.dart';
import '../../queue/providers/queue_provider.dart';
import '../providers/research_review_provider.dart';
import '../widgets/review_sections.dart';

class ResearchReviewScreen extends ConsumerWidget {
  final String signalId;

  const ResearchReviewScreen({super.key, required this.signalId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final reviewAsync = ref.watch(reviewStateProvider(signalId));

    return Scaffold(
      backgroundColor: AppColors.surfaceRaised,
      body: reviewAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => _FailedBody(
          onRetry: () => ref.invalidate(reviewStateProvider(signalId)),
        ),
        data: (state) => switch (state) {
          ReviewGenerating() => _GeneratingBody(),
          ReviewCompleted(:final review) => _ReviewBody(review: review),
          ReviewFailed() => _FailedBody(
              onRetry: () => ref.invalidate(reviewStateProvider(signalId)),
            ),
        },
      ),
    );
  }
}

class _GeneratingBody extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final disableAnimations = MediaQuery.disableAnimationsOf(context);
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _BackButton(),
            const SizedBox(height: 20),
            Text(
              '리뷰를 생성하는 중입니다. 앱을 닫아도 됩니다.',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: AppColors.textSecondary,
                  ),
            ),
            const SizedBox(height: 12),
            disableAnimations
                ? Text(
                    '···',
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                          color: AppColors.textSecondary,
                        ),
                  )
                : const _DotPulse(),
            const SizedBox(height: 16),
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

class _DotPulse extends StatefulWidget {
  const _DotPulse();

  @override
  State<_DotPulse> createState() => _DotPulseState();
}

class _DotPulseState extends State<_DotPulse> with TickerProviderStateMixin {
  late final List<AnimationController> _controllers;
  late final List<Animation<double>> _animations;

  @override
  void initState() {
    super.initState();
    _controllers = List.generate(
      3,
      (i) => AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 600),
      )..repeat(reverse: true),
    );
    for (var i = 0; i < 3; i++) {
      Future.delayed(Duration(milliseconds: i * 300), () {
        if (mounted) _controllers[i].forward();
      });
    }
    _animations = _controllers
        .map(
          (c) => Tween<double>(begin: 0.3, end: 1.0).animate(
            CurvedAnimation(parent: c, curve: Curves.easeInOut),
          ),
        )
        .toList();
  }

  @override
  void dispose() {
    for (final c in _controllers) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(3, (i) {
        return Padding(
          padding: const EdgeInsets.only(right: 4),
          child: FadeTransition(
            opacity: _animations[i],
            child: Text(
              '·',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: AppColors.textSecondary,
                    fontSize: 24,
                  ),
            ),
          ),
        );
      }),
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
            _BackButton(),
            const SizedBox(height: 20),
            Text(
              '리뷰를 생성하지 못했습니다.',
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
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

// ─── REQUIRED_SECTIONS 상수 ───────────────────────────────────────────────

const _kRequiredSections = [
  'one_line_definition',
  'key_concepts',
  'problems_solved',
  'why_it_matters',
  'vs_existing_tech',
  'user_relevance',
  'risks',
  'recommendation_reason',
];

// ─── _ReviewBody (StatefulWidget) ────────────────────────────────────────

class _ReviewBody extends StatefulWidget {
  final ResearchReview review;

  const _ReviewBody({required this.review});

  @override
  State<_ReviewBody> createState() => _ReviewBodyState();
}

class _ReviewBodyState extends State<_ReviewBody> {
  final ScrollController _scrollController = ScrollController();
  final Set<String> _seenSections = {};
  bool _previousEnabled = false;

  // GlobalKeys for scroll-visibility tracking
  final _keyOneLineDef        = GlobalKey();
  final _keyKeyConcepts       = GlobalKey();
  final _keyProblemsSolved    = GlobalKey();
  final _keyWhyItMatters      = GlobalKey();
  final _keyVsExisting        = GlobalKey();
  final _keyUserRelevance     = GlobalKey();
  final _keyRisks             = GlobalKey();
  final _keyRecommendation    = GlobalKey();

  // AC-2: FocusNodes for keyboard/screen reader section tracking
  late final Map<String, FocusNode> _focusNodes;

  bool get _enabled {
    if (widget.review.barGateOverride == 'enabled') return true;
    return _kRequiredSections.every((k) => _seenSections.contains(k));
  }

  Map<String, GlobalKey> get _sectionKeyMap => {
    'one_line_definition':    _keyOneLineDef,
    'key_concepts':           _keyKeyConcepts,
    'problems_solved':        _keyProblemsSolved,
    'why_it_matters':         _keyWhyItMatters,
    'vs_existing_tech':       _keyVsExisting,
    'user_relevance':         _keyUserRelevance,
    'risks':                  _keyRisks,
    'recommendation_reason':  _keyRecommendation,
  };

  @override
  void initState() {
    super.initState();
    _previousEnabled = _enabled;
    _scrollController.addListener(_checkSectionVisibility);
    // P12: 초기 뷰포트에 이미 보이는 섹션 감지 (스크롤 없이도 unlock 가능)
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _checkSectionVisibility();
    });
    // AC-2: 키보드/스크린리더 포커스 기반 섹션 tracking
    _focusNodes = {
      'one_line_definition':   FocusNode(),
      'key_concepts':          FocusNode(),
      'problems_solved':       FocusNode(),
      'why_it_matters':        FocusNode(),
      'vs_existing_tech':      FocusNode(),
      'user_relevance':        FocusNode(),
      'risks':                 FocusNode(),
      'recommendation_reason': FocusNode(),
    };
    _focusNodes.forEach((key, node) {
      node.addListener(() {
        if (node.hasFocus) _markSectionSeen(key);
      });
    });
  }

  @override
  void dispose() {
    _scrollController.removeListener(_checkSectionVisibility);
    _scrollController.dispose();
    for (final node in _focusNodes.values) {
      node.dispose();
    }
    super.dispose();
  }

  void _checkSectionVisibility() {
    if (!mounted) return; // P3: dispose 후 setState 방지
    final screenHeight = MediaQuery.of(context).size.height;
    final threshold = screenHeight * 0.9;

    bool changed = false;
    _sectionKeyMap.forEach((key, gKey) {
      if (_seenSections.contains(key)) return;
      final ctx = gKey.currentContext;
      if (ctx == null) return;
      final box = ctx.findRenderObject() as RenderBox?;
      if (box == null) return;
      final pos = box.localToGlobal(Offset.zero);
      if (pos.dy < threshold) {
        _seenSections.add(key);
        changed = true;
      }
    });

    if (changed) {
      final wasEnabled = _previousEnabled;
      final nowEnabled = _enabled;
      setState(() {
        if (!wasEnabled && nowEnabled) _previousEnabled = true; // P13: setState 내부로 이동
      });
      if (!wasEnabled && nowEnabled) {
        SemanticsService.sendAnnouncement(
          View.of(context),
          '지금 학습 버튼을 사용할 수 있습니다',
          TextDirection.ltr,
        );
      }
    }
  }

  // AC-2: 포커스 기반 섹션 seen 처리 (키보드/스크린리더 공용)
  void _markSectionSeen(String key) {
    if (!mounted || _seenSections.contains(key)) return;
    _seenSections.add(key);
    final wasEnabled = _previousEnabled;
    final nowEnabled = _enabled;
    setState(() {
      if (!wasEnabled && nowEnabled) _previousEnabled = true; // P13
    });
    if (!wasEnabled && nowEnabled) {
      SemanticsService.sendAnnouncement(
        View.of(context),
        '지금 학습 버튼을 사용할 수 있습니다',
        TextDirection.ltr,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.review.payload;

    return Stack(
      children: [
        SafeArea(
          bottom: false,
          child: SingleChildScrollView(
            controller: _scrollController,
            // bottom 패딩은 스티키바(바닥 고정) 위로 마지막 요소('AI에게 질문하기' 링크)가
            // 가려지지 않게 여유를 둔다. 활성 상태 바는 추천 이유 텍스트까지 포함해 ~170이므로
            // 그보다 크게 잡는다.
            padding: const EdgeInsets.fromLTRB(20, 24, 20, 216),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _BackButton(),
                const SizedBox(height: 20),

                // h1: Signal 제목
                Semantics(
                  header: true,
                  child: Text(
                    widget.review.signalTitle,
                    style: Theme.of(context).textTheme.displayMedium,
                  ),
                ),
                const SizedBox(height: 24),

                // 12개 섹션 + 참고 출처 + HonestBox (공용 위젯으로 추출, Task 13)
                ReviewSections(
                  payload: p,
                  sectionKeys: _sectionKeyMap,
                  focusNodes: _focusNodes,
                ),

                // AI에게 질문하기
                GestureDetector(
                  onTap: () =>
                      context.push('/home/review/${widget.review.signalId}/chat'),
                  child: Text(
                    'AI에게 질문하기',
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          color: AppColors.textSecondary,
                          decoration: TextDecoration.underline,
                          fontSize: 13,
                        ),
                  ),
                ),
              ],
            ),
          ),
        ),

        // DynamicContextStickyBar
        Positioned(
          left: 0,
          right: 0,
          // 이 화면은 ShellScaffold(Scaffold body+bottomNavigationBar) 안에 있어
          // body 바닥이 이미 nav 위쪽이다. bottom:64로 띄우면 그 64px 틈으로 스크롤
          // 콘텐츠가 비쳐 보이므로 bottom:0으로 바닥(=nav 바로 위)에 붙인다.
          bottom: 0,
          child: _DynamicContextStickyBar(
            signalId: widget.review.signalId,
            reviewId: widget.review.reviewId,
            enabled: _enabled,
            recommendationReason: p.recommendationReason,
          ),
        ),
      ],
    );
  }
}


// ─── _DynamicContextStickyBar ─────────────────────────────────────────────

class _DynamicContextStickyBar extends ConsumerStatefulWidget {
  final String signalId;
  final String reviewId;
  final bool enabled;
  final String recommendationReason;

  const _DynamicContextStickyBar({
    required this.signalId,
    required this.reviewId,
    required this.enabled,
    required this.recommendationReason,
  });

  @override
  ConsumerState<_DynamicContextStickyBar> createState() =>
      _DynamicContextStickyBarState();
}

class _DynamicContextStickyBarState extends ConsumerState<_DynamicContextStickyBar> {
  bool _isSubmitting = false;

  Future<void> _postDecision({
    required String choice,
    String? queueTiming,
    String? memo,
  }) async {
    const fastapiUrl = String.fromEnvironment(
      'FASTAPI_URL',
      defaultValue: 'http://localhost:8000',
    );
    final session = Supabase.instance.client.auth.currentSession;
    final token = session?.accessToken;
    // P4: 세션 만료 pre-check — 빈 bearer 전송 방지
    if (token == null || token.isEmpty) {
      throw Exception('로그인 세션이 만료됐습니다. 앱을 재시작해 주세요.');
    }

    final response = await http.post(
      Uri.parse('$fastapiUrl/api/v1/decisions'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode({
        'review_id': widget.reviewId,
        'choice': choice,
        if (queueTiming != null) 'queue_timing': queueTiming,
        if (memo != null && memo.isNotEmpty) 'memo': memo,
      }),
    );
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception('Decision failed: ${response.statusCode}');
    }

    // 결정 반영: 탭 화면이 IndexedStack으로 살아있어 FutureProvider 캐시가 남으므로,
    // 보관함·히스토리를 명시적으로 무효화해 다음 진입 시 최신 상태를 다시 불러온다.
    if (mounted) {
      ref.invalidate(queueItemsProvider);
      ref.invalidate(historyItemsProvider);
    }
  }

  Future<void> _handleLearnNow() async {
    HapticFeedback.mediumImpact();
    setState(() => _isSubmitting = true);
    try {
      await _postDecision(choice: 'learn_now');
      if (mounted) context.push('/home/review/${widget.signalId}/learning-path');
    } catch (e) { // P4: 세션 만료 메시지 전달
      if (mounted) {
        final msg = e is Exception
            ? e.toString().replaceFirst('Exception: ', '')
            : '오류가 발생했습니다. 다시 시도해 주세요.';
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(msg), duration: const Duration(seconds: 3)),
        );
        setState(() => _isSubmitting = false);
      }
    }
  }

  Future<void> _handleIgnore() async {
    setState(() => _isSubmitting = true);
    try {
      await _postDecision(choice: 'ignore');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('이 Signal은 히스토리에서 다시 볼 수 있습니다.'),
            duration: Duration(seconds: 3),
          ),
        );
        context.go('/home');
      }
    } catch (e) { // P4: 세션 만료 메시지 전달
      if (mounted) {
        final msg = e is Exception
            ? e.toString().replaceFirst('Exception: ', '')
            : '오류가 발생했습니다. 다시 시도해 주세요.';
        setState(() => _isSubmitting = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(msg), duration: const Duration(seconds: 3)),
        );
      }
    }
  }

  void _showQueueBottomSheet(BuildContext context) {
    String memo = '';
    // ScaffoldMessenger를 async gap 이전에 캡처
    final messenger = ScaffoldMessenger.of(context);
    showModalBottomSheet(
      context: context,
      isDismissible: true,
      enableDrag: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      // WCAG 2.2 AA Reduce Motion (Story 5.4 AC-B3): reduce-motion 시 슬라이드업 → 즉시 표시.
      sheetAnimationStyle: MediaQuery.disableAnimationsOf(context)
          ? AnimationStyle.noAnimation
          : null,
      builder: (sheetContext) {
        return StatefulBuilder(
          builder: (ctx, setSheetState) {
            return Padding(
              padding: EdgeInsets.only(
                left: 20,
                right: 20,
                top: 12,
                bottom: MediaQuery.of(ctx).viewInsets.bottom + 40,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // drag handle
                  Container(
                    width: 36,
                    height: 4,
                    decoration: BoxDecoration(
                      color: const Color(0xFFDDDDDD),
                      borderRadius: BorderRadius.circular(9999),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: Text(
                      '언제 학습할까요?',
                      style: Theme.of(ctx).textTheme.titleLarge,
                    ),
                  ),
                  const SizedBox(height: 12),
                  ...[
                    ('오늘', 'today'),
                    ('이번 주', 'this_week'),
                    ('나중에', 'later'),
                  ].map(
                    (entry) => Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: SizedBox(
                        width: double.infinity,
                        child: OutlinedButton(
                          style: OutlinedButton.styleFrom(
                            minimumSize: const Size.fromHeight(44),
                            shape: const StadiumBorder(),
                          ),
                          onPressed: _isSubmitting // P11: 동시 탭 방지
                              ? null
                              : () async {
                                  HapticFeedback.mediumImpact();
                                  Navigator.of(sheetContext).pop();
                                  setState(() => _isSubmitting = true);
                                  try {
                                    await _postDecision(
                                      choice: 'queue',
                                      queueTiming: entry.$2,
                                      memo: memo.isNotEmpty ? memo : null,
                                    );
                                    if (mounted) {
                                      final toastMap = {
                                        'today': '오늘 학습 예정으로 저장됐습니다.',
                                        'this_week': '이번 주 학습 예정으로 저장됐습니다.',
                                        'later': '나중에 학습 예정으로 저장됐습니다.',
                                      };
                                      messenger.showSnackBar(
                                        SnackBar(
                                          content: Text(
                                            toastMap[entry.$2] ?? '저장됐습니다.',
                                          ),
                                          duration: const Duration(seconds: 3),
                                        ),
                                      );
                                      context.go('/home'); // D1: 재결정 방지
                                    }
                                  } catch (e) { // P4
                                    if (mounted) {
                                      final msg = e is Exception
                                          ? e.toString().replaceFirst('Exception: ', '')
                                          : '오류가 발생했습니다.';
                                      messenger.showSnackBar(
                                        SnackBar(content: Text(msg), duration: const Duration(seconds: 3)),
                                      );
                                    }
                                  } finally {
                                    if (mounted) setState(() => _isSubmitting = false);
                                  }
                                },
                          child: Text(entry.$1),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    decoration: const InputDecoration(
                      hintText: '메모를 남기세요 (선택)',
                      border: OutlineInputBorder(),
                    ),
                    onChanged: (v) => setSheetState(() => memo = v),
                    maxLines: 3,
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final disableAnimations = MediaQuery.disableAnimationsOf(context);

    Widget barContent;
    if (!widget.enabled) {
      barContent = Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // P16: ↑ 화살표를 스크린리더에서 제외
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                '추천 근거를 먼저 확인해 주세요 ',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      fontSize: 11,
                      color: AppColors.textSecondary,
                    ),
              ),
              ExcludeSemantics(
                child: Text(
                  '↑',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        fontSize: 11,
                        color: AppColors.textSecondary,
                      ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Semantics(
            button: true,
            label: '지금 학습 — 비활성화됨. 리뷰 내용을 먼저 읽어 주세요',
            hint: '추천 근거를 먼저 확인해 주세요', // P17
            enabled: false,
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 14),
              decoration: BoxDecoration(
                color: AppColors.textDisabled,
                borderRadius: BorderRadius.circular(9999),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.lock, size: 14, color: Colors.white),
                  const SizedBox(width: 6),
                  Text(
                    '지금 학습',
                    style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          color: Colors.white,
                          fontSize: 15,
                          fontWeight: FontWeight.w600,
                        ),
                  ),
                ],
              ),
            ),
          ),
        ],
      );
    } else {
      barContent = Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (widget.recommendationReason.isNotEmpty) ...[
            Text(
              widget.recommendationReason,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    fontSize: 12,
                    color: AppColors.textSecondary,
                  ),
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 8),
          ],
          Semantics(
            button: true,
            label: '지금 학습',
            child: SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.accentPrimary,
                  foregroundColor: Colors.white,
                  minimumSize: const Size.fromHeight(48),
                  shape: const StadiumBorder(),
                ),
                onPressed: _isSubmitting ? null : _handleLearnNow,
                child: const Text('지금 학습',
                    style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
              ),
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: Semantics(
                  button: true,
                  label: '나중에 학습 — 이 기술 소식을 보관함에 저장',
                  child: OutlinedButton(
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size.fromHeight(44),
                      shape: const StadiumBorder(),
                    ),
                    onPressed: _isSubmitting
                        ? null
                        : () => _showQueueBottomSheet(context),
                    child: const Text('나중에 학습'),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Semantics(
                  button: true,
                  label: '관심 없음 — 이 기술 소식을 넘김',
                  child: OutlinedButton(
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size.fromHeight(44),
                      shape: const StadiumBorder(),
                    ),
                    onPressed: _isSubmitting ? null : _handleIgnore,
                    child: const Text('관심 없음'),
                  ),
                ),
              ),
            ],
          ),
        ],
      );
    }

    return Container(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
      decoration: const BoxDecoration(
        color: AppColors.surfaceBase,
        border: Border(
          top: BorderSide(color: AppColors.borderSubtle),
        ),
      ),
      child: disableAnimations
          ? barContent
          : AnimatedSwitcher(
              duration: const Duration(milliseconds: 200),
              child: KeyedSubtree(
                key: ValueKey(widget.enabled),
                child: barContent,
              ),
            ),
    );
  }
}

// ─── _BackButton ──────────────────────────────────────────────────────────

class _BackButton extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => context.go('/home'),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.chevron_left, size: 20, color: AppColors.textSecondary),
          Text(
            '홈으로',
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: AppColors.textSecondary,
                ),
          ),
        ],
      ),
    );
  }
}
