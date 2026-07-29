import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../home/providers/research_review_provider.dart';

part 'chain_detail_provider.g.dart';

class ChainSignal {
  final String id;
  final String title;
  final String status; // raw | processed | archived
  const ChainSignal({required this.id, required this.title, required this.status});
}

class ChainDecision {
  final String choice; // learn_now | queue | ignore
  final DateTime createdAt;
  const ChainDecision({required this.choice, required this.createdAt});
}

class ChainOutcome {
  final String status; // completed | applied | dropped | not_useful
  final bool? useful;
  final int? actualLearningTimeMin;
  final String? appliedProjectNote;
  final String? memo;
  final DateTime createdAt;
  const ChainOutcome({
    required this.status,
    required this.useful,
    required this.actualLearningTimeMin,
    required this.appliedProjectNote,
    required this.memo,
    required this.createdAt,
  });
}

class ChainDetailData {
  final ChainSignal signal;
  final ReviewPayload? reviewPayload;
  final ChainDecision? decision;
  final ChainOutcome? outcome;
  const ChainDetailData({
    required this.signal,
    required this.reviewPayload,
    required this.decision,
    required this.outcome,
  });
}

@riverpod
Future<ChainDetailData?> chainDetail(ChainDetailRef ref, String signalId) async {
  final client = Supabase.instance.client;

  // 1. Signal
  final signalRow = await client
      .from('signals')
      .select('id, title, status')
      .eq('id', signalId)
      .maybeSingle();
  if (signalRow == null) return null;

  final signal = ChainSignal(
    id: signalRow['id'] as String,
    title: signalRow['title'] as String? ?? '',
    status: signalRow['status'] as String? ?? '',
  );

  // 2. Review (완료된 최신 1건)
  final reviewRow = await client
      .from('reviews')
      .select('id, status, result, created_at')
      .eq('signal_id', signalId)
      .eq('status', 'completed')
      .order('created_at', ascending: false)
      .limit(1)
      .maybeSingle();

  ReviewPayload? reviewPayload;
  if (reviewRow != null) {
    final resultJson = reviewRow['result'] as Map<String, dynamic>?;
    final payloadJson = resultJson?['payload'] as Map<String, dynamic>?;
    if (payloadJson != null) reviewPayload = ReviewPayload.fromJson(payloadJson);
  }

  // 3. Decision (review 있을 때만, 최신 1건, choice 필터 없음)
  ChainDecision? decision;
  String? decisionId;
  if (reviewRow != null) {
    final decisionRow = await client
        .from('decisions')
        .select('id, choice, queue_timing, created_at')
        .eq('review_id', reviewRow['id'] as String)
        .order('created_at', ascending: false)
        .limit(1)
        .maybeSingle();
    if (decisionRow != null) {
      decisionId = decisionRow['id'] as String;
      decision = ChainDecision(
        choice: decisionRow['choice'] as String,
        createdAt: DateTime.parse(decisionRow['created_at'] as String),
      );
    }
  }

  // 4. Outcome (decision 있을 때만, 최신 1건)
  ChainOutcome? outcome;
  if (decisionId != null) {
    final outcomeRow = await client
        .from('outcomes')
        .select('id, status, useful, actual_learning_time_min, applied_project_note, memo, created_at')
        .eq('decision_id', decisionId)
        .order('created_at', ascending: false)
        .limit(1)
        .maybeSingle();
    if (outcomeRow != null) {
      outcome = ChainOutcome(
        status: outcomeRow['status'] as String,
        useful: outcomeRow['useful'] as bool?,
        actualLearningTimeMin: outcomeRow['actual_learning_time_min'] as int?,
        appliedProjectNote: outcomeRow['applied_project_note'] as String?,
        memo: outcomeRow['memo'] as String?,
        createdAt: DateTime.parse(outcomeRow['created_at'] as String),
      );
    }
  }

  return ChainDetailData(
    signal: signal,
    reviewPayload: reviewPayload,
    decision: decision,
    outcome: outcome,
  );
}
