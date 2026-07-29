import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

part 'queue_provider.g.dart';

class QueueItemData {
  final String decisionId;
  final String signalId;
  final String title;
  final String queueTiming;
  final DateTime updatedAt;

  const QueueItemData({
    required this.decisionId,
    required this.signalId,
    required this.title,
    required this.queueTiming,
    required this.updatedAt,
  });

  bool get isOverdue =>
      queueTiming == 'today' &&
      _kstDateStr(updatedAt).compareTo(_kstDateStr(DateTime.now())) < 0;

  QueueItemData copyWith({String? queueTiming}) => QueueItemData(
        decisionId: decisionId,
        signalId: signalId,
        title: title,
        queueTiming: queueTiming ?? this.queueTiming,
        updatedAt: updatedAt,
      );
}

String _kstDateStr(DateTime dt) {
  final kst = dt.toUtc().add(const Duration(hours: 9));
  return '${kst.year}-${kst.month.toString().padLeft(2, '0')}-${kst.day.toString().padLeft(2, '0')}';
}

Future<void> _patchQueueTiming(String decisionId, String timing) async {
  const fastapiUrl = String.fromEnvironment(
    'FASTAPI_URL',
    defaultValue: 'http://localhost:8000',
  );
  final session = Supabase.instance.client.auth.currentSession;
  final token = session?.accessToken;
  if (token == null || token.isEmpty) {
    throw Exception('로그인 세션이 만료됐습니다. 앱을 재시작해 주세요.');
  }

  final response = await http.patch(
    Uri.parse('$fastapiUrl/api/v1/decisions/$decisionId'),
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer $token',
    },
    body: jsonEncode({'queue_timing': timing}),
  );
  if (response.statusCode < 200 || response.statusCode >= 300) {
    throw Exception('Decision update failed: ${response.statusCode}');
  }
}

@riverpod
class QueueItems extends _$QueueItems {
  @override
  Future<List<QueueItemData>> build() async {
    final response = await Supabase.instance.client
        .from('decisions')
        .select('id, queue_timing, updated_at, reviews(signal_id, signals(title))')
        .eq('choice', 'queue')
        .order('created_at', ascending: true);

    return (response as List).map((row) {
      final review = row['reviews'] as Map<String, dynamic>?;
      final signal = review?['signals'] as Map<String, dynamic>?;
      return QueueItemData(
        decisionId: row['id'] as String,
        signalId: review?['signal_id'] as String? ?? '',
        title: signal?['title'] as String? ?? '',
        queueTiming: row['queue_timing'] as String,
        updatedAt: DateTime.parse(row['updated_at'] as String),
      );
    }).toList();
  }

  Future<void> reschedule(String decisionId, String newTiming) async {
    final current = state.valueOrNull ?? [];
    final index = current.indexWhere((i) => i.decisionId == decisionId);
    if (index == -1) return;
    final previousItem = current[index];

    state = AsyncData([
      for (final item in current)
        if (item.decisionId == decisionId)
          item.copyWith(queueTiming: newTiming)
        else
          item,
    ]);
    try {
      await _patchQueueTiming(decisionId, newTiming);
    } catch (e) {
      final latest = state.valueOrNull ?? current;
      state = AsyncData([
        for (final item in latest)
          if (item.decisionId == decisionId)
            previousItem
          else
            item,
      ]);
      rethrow;
    }
  }
}

@riverpod
Future<int> estimatedLearningMinutes(EstimatedLearningMinutesRef ref) async {
  final userId = Supabase.instance.client.auth.currentUser?.id;
  if (userId == null) return 30;

  final row = await Supabase.instance.client
      .from('user_profiles')
      .select('daily_learning_time_min')
      .eq('id', userId)
      .maybeSingle();

  return row?['daily_learning_time_min'] as int? ?? 30;
}
