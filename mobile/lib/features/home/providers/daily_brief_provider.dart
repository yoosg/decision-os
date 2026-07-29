import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

part 'daily_brief_provider.g.dart';

class DailyBrief {
  final String id;
  final String userId;
  final String briefDate;
  final String status; // pending | processing | completed | failed
  final String? errorMessage;
  final String? generatedAt;

  const DailyBrief({
    required this.id,
    required this.userId,
    required this.briefDate,
    required this.status,
    this.errorMessage,
    this.generatedAt,
  });

  factory DailyBrief.fromJson(Map<String, dynamic> json) => DailyBrief(
        id: json['id'] as String,
        userId: json['user_id'] as String,
        briefDate: json['brief_date'] as String,
        status: json['status'] as String,
        errorMessage: json['error_message'] as String?,
        generatedAt: json['generated_at'] as String?,
      );
}

class SignalItem {
  final String signalId;
  final String title;
  final String? summary;
  final int sourceCount;
  final int position;

  const SignalItem({
    required this.signalId,
    required this.title,
    this.summary,
    required this.sourceCount,
    required this.position,
  });
}

String _todayISO() {
  final now = DateTime.now();
  return '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
}

@riverpod
Stream<DailyBrief?> dailyBriefStream(DailyBriefStreamRef ref) {
  final userId = Supabase.instance.client.auth.currentUser?.id ?? '';
  final today = _todayISO();

  return Supabase.instance.client
      .from('daily_briefs')
      .stream(primaryKey: ['id'])
      .eq('user_id', userId)
      .map((rows) {
        final todayRows = rows
            .where((r) => r['brief_date'] == today)
            .toList()
          ..sort((a, b) {
            final aTime = a['generated_at'] as String? ?? '';
            final bTime = b['generated_at'] as String? ?? '';
            return bTime.compareTo(aTime);
          });
        if (todayRows.isEmpty) return null;
        return DailyBrief.fromJson(todayRows.first);
      });
}

@riverpod
Future<List<SignalItem>> dailyBriefSignals(
  DailyBriefSignalsRef ref,
  String briefId,
) async {
  final response = await Supabase.instance.client
      .from('daily_brief_signals')
      .select('signal_id, position, relevance_score, signals(id, title, summary)')
      .eq('daily_brief_id', briefId)
      .order('position', ascending: true);

  final signalIds = (response as List).map((r) => r['signal_id'] as String).toList();

  Map<String, int> sourceCounts = {};
  if (signalIds.isNotEmpty) {
    final sources = await Supabase.instance.client
        .from('signal_sources')
        .select('signal_id')
        .inFilter('signal_id', signalIds);
    for (final row in sources as List) {
      final sid = row['signal_id'] as String;
      sourceCounts[sid] = (sourceCounts[sid] ?? 0) + 1;
    }
  }

  return (response as List).map((row) {
    final sig = row['signals'] as Map<String, dynamic>?;
    final signalId = row['signal_id'] as String;
    return SignalItem(
      signalId: signalId,
      title: sig?['title'] as String? ?? '',
      summary: sig?['summary'] as String?,
      sourceCount: sourceCounts[signalId] ?? 5,
      position: row['position'] as int,
    );
  }).toList();
}

@riverpod
class SeenSignalIds extends _$SeenSignalIds {
  @override
  Set<String> build() => {};

  void mark(String id) => state = {...state, id};
}
