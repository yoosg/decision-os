import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

part 'history_provider.g.dart';

class HistoryItemData {
  final String decisionId;
  final String signalId;
  final String title;
  final String choice; // learn_now | queue | ignore
  final String? outcomeStatus; // completed | applied | dropped | not_useful | null
  final DateTime createdAt;

  const HistoryItemData({
    required this.decisionId,
    required this.signalId,
    required this.title,
    required this.choice,
    required this.outcomeStatus,
    required this.createdAt,
  });
}

// ─── KST 월 그룹핑/포맷 헬퍼 (Web Task 1 로직을 Dart 로 이식) ─────────────────

String kstYearMonth(DateTime dt) {
  final kst = dt.toUtc().add(const Duration(hours: 9));
  return '${kst.year}-${kst.month.toString().padLeft(2, '0')}';
}

String formatMonthDivider(String yearMonth) {
  final parts = yearMonth.split('-');
  return '${parts[0]}년 ${int.parse(parts[1])}월';
}

String formatCardDate(DateTime dt) {
  final kst = dt.toUtc().add(const Duration(hours: 9));
  return '${kst.month}월 ${kst.day}일';
}

// ─── Provider ─────────────────────────────────────────────────────────────

@riverpod
Future<List<HistoryItemData>> historyItems(HistoryItemsRef ref) async {
  // 순수 읽기 — RLS 가 자동 필터링 (AD-3/AD-9). nested embed → Future 쿼리만 사용(.stream 미지원)
  final response = await Supabase.instance.client
      .from('decisions')
      .select(
        'id, choice, created_at, '
        'reviews!inner(signal_id, signals(id, title, status)), '
        'outcomes(status, created_at)',
      )
      .order('created_at', ascending: false);

  final items = <HistoryItemData>[];
  for (final row in response as List) {
    final review = row['reviews'] as Map<String, dynamic>?;
    final signal = review?['signals'] as Map<String, dynamic>?;
    if (review == null || signal == null) continue;

    // outcomes 는 1:N 임베드 → 배열. created_at 내림차순 최신 1건만 사용 (설계 결정 2)
    final outcomes = (row['outcomes'] as List?)?.cast<Map<String, dynamic>>() ?? [];
    String? outcomeStatus;
    if (outcomes.isNotEmpty) {
      outcomes.sort((a, b) => (b['created_at'] as String).compareTo(a['created_at'] as String));
      outcomeStatus = outcomes.first['status'] as String?;
    }

    items.add(HistoryItemData(
      decisionId: row['id'] as String,
      signalId: review['signal_id'] as String? ?? '',
      title: signal['title'] as String? ?? '',
      choice: row['choice'] as String,
      outcomeStatus: outcomeStatus,
      createdAt: DateTime.parse(row['created_at'] as String),
    ));
  }
  return items;
}
