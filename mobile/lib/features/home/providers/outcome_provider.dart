import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

part 'outcome_provider.g.dart';

/// 클래스 기반 Notifier — submitOutcome() 명시적 메서드 노출 (AD-14, 4.1 리뷰 레슨 반영)
@riverpod
class OutcomeController extends _$OutcomeController {
  @override
  Future<String?> build(String signalId) async {
    final reviewRow = await Supabase.instance.client
        .from('reviews')
        .select('id')
        .eq('signal_id', signalId)
        .eq('status', 'completed')
        .limit(1)
        .maybeSingle();
    if (reviewRow == null) return null;

    final decisionRow = await Supabase.instance.client
        .from('decisions')
        .select('id')
        .eq('review_id', reviewRow['id'])
        .eq('choice', 'learn_now')
        .limit(1)
        .maybeSingle();
    if (decisionRow == null) return null;

    return decisionRow['id'] as String;
  }

  Future<bool> submitOutcome({
    required String status,
    required bool useful,
    int? actualLearningTimeMin,
    String? appliedProjectNote,
    String? memo,
  }) async {
    try {
      // build()의 signalId → decision_id 조회가 아직 끝나지 않았을 수 있으므로
      // state를 동기적으로 읽지 않고 future를 await해 완료를 보장한다.
      final decisionId = await future;
      if (decisionId == null) return false;

      final session = Supabase.instance.client.auth.currentSession;
      final token = session?.accessToken ?? '';
      if (token.isEmpty) return false;

      const fastapiUrl = String.fromEnvironment(
        'FASTAPI_URL',
        defaultValue: 'http://localhost:8000',
      );
      final response = await http
          .post(
            Uri.parse('$fastapiUrl/api/v1/outcomes'),
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer $token',
            },
            body: jsonEncode({
              'decision_id': decisionId,
              'status': status,
              'useful': useful,
              'actual_learning_time_min': actualLearningTimeMin,
              'applied_project_note': appliedProjectNote,
              'memo': memo,
            }),
          )
          .timeout(const Duration(seconds: 15));
      return response.statusCode == 200 || response.statusCode == 201;
    } catch (e) {
      debugPrint('submitOutcome failed: $e');
      return false;
    }
  }
}
