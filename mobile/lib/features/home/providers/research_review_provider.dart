import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

part 'research_review_provider.g.dart';

// ──────────────────────────────────────────
// 기존 데이터 클래스 보존 (다른 파일이 참조 가능)
// ──────────────────────────────────────────

class LearningTimeDifficulty {
  final double estimatedHours;
  final String difficulty; // 'beginner' | 'intermediate' | 'advanced'

  const LearningTimeDifficulty({
    required this.estimatedHours,
    required this.difficulty,
  });

  factory LearningTimeDifficulty.fromJson(Map<String, dynamic> json) =>
      LearningTimeDifficulty(
        estimatedHours: (json['estimated_hours'] as num?)?.toDouble() ?? 0.0,
        difficulty: json['difficulty'] as String? ?? 'beginner',
      );
}

class HonestBoxData {
  final String content;
  final String severity; // 'standard' | 'high'

  const HonestBoxData({required this.content, required this.severity});

  factory HonestBoxData.fromJson(Map<String, dynamic> json) => HonestBoxData(
        content: json['content'] as String? ?? '',
        severity: json['severity'] as String? ?? 'standard',
      );
}

class ReviewPayload {
  final String oneLineDefinition;
  final String keyConcepts;
  final String problemsSolved;
  final String whyItMatters;
  final String vsExistingTech;
  final String userRelevance;
  final String learningGoals;
  final LearningTimeDifficulty learningTimeDifficulty;
  final String practicalApplicability;
  final String risks;
  final String recommendationReason;
  final List<String> referenceSources;
  final HonestBoxData honestBox;

  const ReviewPayload({
    required this.oneLineDefinition,
    required this.keyConcepts,
    required this.problemsSolved,
    required this.whyItMatters,
    required this.vsExistingTech,
    required this.userRelevance,
    required this.learningGoals,
    required this.learningTimeDifficulty,
    required this.practicalApplicability,
    required this.risks,
    required this.recommendationReason,
    required this.referenceSources,
    required this.honestBox,
  });

  factory ReviewPayload.fromJson(Map<String, dynamic> json) => ReviewPayload(
        oneLineDefinition: json['one_line_definition'] as String? ?? '',
        keyConcepts: json['key_concepts'] as String? ?? '',
        problemsSolved: json['problems_solved'] as String? ?? '',
        whyItMatters: json['why_it_matters'] as String? ?? '',
        vsExistingTech: json['vs_existing_tech'] as String? ?? '',
        userRelevance: json['user_relevance'] as String? ?? '',
        learningGoals: json['learning_goals'] as String? ?? '',
        learningTimeDifficulty: LearningTimeDifficulty.fromJson(
          (json['learning_time_difficulty'] as Map<String, dynamic>?) ?? {},
        ),
        practicalApplicability: json['practical_applicability'] as String? ?? '',
        risks: json['risks'] as String? ?? '',
        recommendationReason: json['recommendation_reason'] as String? ?? '',
        referenceSources: (json['reference_sources'] as List<dynamic>?)
                ?.map((e) => e?.toString() ?? '')
                .toList() ??
            [],
        honestBox: HonestBoxData.fromJson(
          (json['honest_box'] as Map<String, dynamic>?) ?? {},
        ),
      );
}

class ResearchReview {
  final String reviewId;
  final String signalId;
  final String signalTitle;
  final ReviewPayload payload;
  final String? barGateOverride;
  final String status;

  const ResearchReview({
    required this.reviewId,
    required this.signalId,
    required this.signalTitle,
    required this.payload,
    this.barGateOverride,
    required this.status,
  });
}

// ──────────────────────────────────────────
// 새 ReviewState sealed class
// ──────────────────────────────────────────

sealed class ReviewState {}

class ReviewGenerating extends ReviewState {}

class ReviewCompleted extends ReviewState {
  final ResearchReview review;
  ReviewCompleted(this.review);
}

class ReviewFailed extends ReviewState {}

// ──────────────────────────────────────────
// StreamProvider
// ──────────────────────────────────────────

@riverpod
Stream<ReviewState> reviewState(ReviewStateRef ref, String signalId) async* {
  RealtimeChannel? channel;
  StreamController<ReviewState>? controller;
  ref.onDispose(
    () {
      final ch = channel;
      if (ch != null) Supabase.instance.client.removeChannel(ch);
      final c = controller;
      if (c != null && !c.isClosed) c.close();
    },
  );

  // 초기 fetch: status 제한 없이 최신 review 조회
  final initialRow = await Supabase.instance.client
      .from('reviews')
      .select('id, status, result, bar_gate_override, signals(title)')
      .eq('signal_id', signalId)
      .eq('playbook_type', 'ai_research')
      .order('created_at', ascending: false)
      .limit(1)
      .maybeSingle();

  final initialStatus = initialRow?['status'] as String?;

  if (initialStatus == 'completed') {
    final review = _parseReview(signalId, initialRow!);
    if (review != null) {
      yield ReviewCompleted(review);
    } else {
      yield ReviewFailed();
    }
    return;
  }

  // pending/processing → generating + Realtime 구독
  if (initialStatus == 'pending' || initialStatus == 'processing') {
    yield ReviewGenerating();
    final reviewId = initialRow!['id'] as String;
    controller = StreamController<ReviewState>();
    channel = _subscribeRealtime(signalId, reviewId, controller);
    yield* controller.stream;
    return;
  }

  // null ���는 failed → trigger API 호출
  yield ReviewGenerating();
  final reviewId = await _triggerReview(signalId);
  if (reviewId == null) {
    yield ReviewFailed();
    return;
  }

  controller = StreamController<ReviewState>();
  channel = _subscribeRealtime(signalId, reviewId, controller);
  yield* controller.stream;
}

RealtimeChannel _subscribeRealtime(
  String signalId,
  String reviewId,
  StreamController<ReviewState> controller,
) {
  return Supabase.instance.client
      .channel('review-$reviewId')
      .onPostgresChanges(
        event: PostgresChangeEvent.update,
        schema: 'public',
        table: 'reviews',
        filter: PostgresChangeFilter(
          type: PostgresChangeFilterType.eq,
          column: 'id',
          value: reviewId,
        ),
        callback: (payload) async {
          final newRow = payload.newRecord;
          final status = newRow['status'] as String?;
          if (status == 'completed') {
            final review = await _fetchCompletedReview(signalId, reviewId);
            if (!controller.isClosed) {
              controller.add(review != null ? ReviewCompleted(review) : ReviewFailed());
              controller.close();
            }
          } else if (status == 'failed') {
            if (!controller.isClosed) {
              controller.add(ReviewFailed());
              controller.close();
            }
          }
        },
      )
      .subscribe();
}

Future<String?> _triggerReview(String signalId) async {
  try {
    final session = Supabase.instance.client.auth.currentSession;
    final token = session?.accessToken ?? '';
    const fastapiUrl = String.fromEnvironment(
      'FASTAPI_URL',
      defaultValue: 'http://localhost:8000',
    );
    final response = await http.post(
      Uri.parse('$fastapiUrl/api/v1/reviews/trigger'),
      headers: {
        'Content-Type': 'application/json',
        if (token.isNotEmpty) 'Authorization': 'Bearer $token',
      },
      body: jsonEncode({'signal_id': signalId}),
    );
    final body = jsonDecode(response.body) as Map<String, dynamic>;
    return body['data']?['review_id'] as String?;
  } catch (_) {
    return null;
  }
}

Future<ResearchReview?> _fetchCompletedReview(String signalId, String reviewId) async {
  final response = await Supabase.instance.client
      .from('reviews')
      .select('id, result, bar_gate_override, signals(title)')
      .eq('id', reviewId)
      .eq('status', 'completed')
      .maybeSingle();
  if (response == null) return null;
  return _parseReview(signalId, response);
}

ResearchReview? _parseReview(String signalId, Map<String, dynamic> row) {
  final signals = row['signals'] as Map<String, dynamic>?;
  final signalTitle = signals?['title'] as String? ?? '';
  final resultJson = row['result'] as Map<String, dynamic>?;
  final payloadJson = resultJson?['payload'] as Map<String, dynamic>?;
  if (payloadJson == null) return null;
  return ResearchReview(
    reviewId: row['id']?.toString() ?? '',
    signalId: signalId,
    signalTitle: signalTitle,
    payload: ReviewPayload.fromJson(payloadJson),
    barGateOverride: row['bar_gate_override'] as String?,
    status: row['status'] as String? ?? 'completed',
  );
}
