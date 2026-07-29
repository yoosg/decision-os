import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

part 'learning_path_provider.g.dart';

// ──────────────────────────────────────────
// 데이터 클래스
// ──────────────────────────────────────────

class LearningPathResource {
  final String type; // 'official_docs' | 'core_material' | 'github' | 'practice_example' | 'applied_idea'
  final String title;
  final String url;
  final String descriptor;

  const LearningPathResource({
    required this.type,
    required this.title,
    required this.url,
    required this.descriptor,
  });

  factory LearningPathResource.fromJson(Map<String, dynamic> json) => LearningPathResource(
        type: json['type'] as String? ?? '',
        title: json['title'] as String? ?? '',
        url: json['url'] as String? ?? '',
        descriptor: json['descriptor'] as String? ?? '',
      );
}

// ──────────────────────────────────────────
// LearningPathState sealed class
// ──────────────────────────────────────────

sealed class LearningPathState {}

class LearningPathGenerating extends LearningPathState {}

class LearningPathReady extends LearningPathState {
  final List<LearningPathResource> resources;
  final String learningPathId;
  LearningPathReady({required this.resources, required this.learningPathId});
}

class LearningPathFailed extends LearningPathState {
  final String? learningPathId;
  LearningPathFailed({this.learningPathId});
}

// ──────────────────────────────────────────
// StreamNotifier — retry()가 명시적으로 트리거를 재호출할 수 있도록 클래스 기반으로 구성 (AD-14)
// ──────────────────────────────────────────

@riverpod
class LearningPathController extends _$LearningPathController {
  String? _decisionId;
  RealtimeChannel? _channel;
  StreamController<LearningPathState>? _controller;

  void _disposeSubscription() {
    final ch = _channel;
    if (ch != null) Supabase.instance.client.removeChannel(ch);
    _channel = null;
    final c = _controller;
    if (c != null && !c.isClosed) c.close();
    _controller = null;
  }

  Stream<LearningPathState> _startRealtimeStream(String learningPathId) {
    _disposeSubscription();
    final controller = StreamController<LearningPathState>();
    _controller = controller;
    _channel = _subscribeRealtime(learningPathId, controller);
    return controller.stream;
  }

  @override
  Stream<LearningPathState> build(String signalId) async* {
    ref.onDispose(_disposeSubscription);

    final reviewRow = await Supabase.instance.client
        .from('reviews')
        .select('id')
        .eq('signal_id', signalId)
        .eq('status', 'completed')
        .limit(1)
        .maybeSingle();
    if (reviewRow == null) {
      yield LearningPathFailed();
      return;
    }

    final decisionRow = await Supabase.instance.client
        .from('decisions')
        .select('id')
        .eq('review_id', reviewRow['id'])
        .eq('choice', 'learn_now')
        .limit(1)
        .maybeSingle();
    if (decisionRow == null) {
      yield LearningPathFailed();
      return;
    }
    final decisionId = decisionRow['id'] as String;
    _decisionId = decisionId;

    final lpRow = await Supabase.instance.client
        .from('learning_paths')
        .select('id, status, resources')
        .eq('decision_id', decisionId)
        .limit(1)
        .maybeSingle();

    if (lpRow != null) {
      final status = lpRow['status'] as String?;
      final learningPathId = lpRow['id'] as String;

      if (status == 'completed') {
        final resources = _parseResources(lpRow['resources']);
        if (resources.length == 5) {
          yield LearningPathReady(resources: resources, learningPathId: learningPathId);
        } else {
          yield LearningPathFailed(learningPathId: learningPathId);
        }
        return;
      }
      if (status == 'failed') {
        yield LearningPathFailed(learningPathId: learningPathId);
        return;
      }

      // pending | processing
      yield LearningPathGenerating();
      yield* _subscribeAndCatchUp(learningPathId);
      return;
    }

    // 신규 trigger
    yield LearningPathGenerating();
    final learningPathId = await _triggerLearningPath(decisionId);
    if (learningPathId == null) {
      yield LearningPathFailed();
      return;
    }

    yield* _subscribeAndCatchUp(learningPathId);
  }

  /// realtime 채널을 구독한 직후 현재 DB 상태를 한 번 더 확인해, 구독이 실제로 연결되기 전에
  /// 이미 발생한 completed/failed 전이를 놓치지 않도록 한다.
  Stream<LearningPathState> _subscribeAndCatchUp(String learningPathId) async* {
    final stream = _startRealtimeStream(learningPathId);
    final missed = await _checkCurrentStatus(learningPathId);
    if (missed != null) {
      _disposeSubscription();
      yield missed;
      return;
    }
    yield* stream;
  }

  /// "다시 시도하기" — DB에 남아있는 이전 실패 row 상태와 무관하게 트리거를 재호출한다.
  Future<void> retry() async {
    final decisionId = _decisionId;
    if (decisionId == null) {
      ref.invalidateSelf();
      return;
    }
    _disposeSubscription();
    state = AsyncData(LearningPathGenerating());
    final learningPathId = await _triggerLearningPath(decisionId);
    if (learningPathId == null) {
      state = AsyncData(LearningPathFailed());
      return;
    }
    await for (final s in _subscribeAndCatchUp(learningPathId)) {
      state = AsyncData(s);
    }
  }
}

/// 초기 조회 이후 realtime 채널이 실제로 연결되기까지의 시간차 동안 발생한 상태 전이를 놓치지 않도록
/// 구독 직후 현재 DB 상태를 한 번 더 확인한다.
Future<LearningPathState?> _checkCurrentStatus(String learningPathId) async {
  final row = await Supabase.instance.client
      .from('learning_paths')
      .select('status, resources')
      .eq('id', learningPathId)
      .maybeSingle();
  final status = row?['status'] as String?;
  if (status == 'completed') {
    final resources = _parseResources(row?['resources']);
    return resources.length == 5
        ? LearningPathReady(resources: resources, learningPathId: learningPathId)
        : LearningPathFailed(learningPathId: learningPathId);
  }
  if (status == 'failed') {
    return LearningPathFailed(learningPathId: learningPathId);
  }
  return null;
}

RealtimeChannel _subscribeRealtime(
  String learningPathId,
  StreamController<LearningPathState> controller,
) {
  return Supabase.instance.client
      .channel('learning-path-$learningPathId')
      .onPostgresChanges(
        event: PostgresChangeEvent.update,
        schema: 'public',
        table: 'learning_paths',
        filter: PostgresChangeFilter(
          type: PostgresChangeFilterType.eq,
          column: 'id',
          value: learningPathId,
        ),
        callback: (payload) async {
          final newRow = payload.newRecord;
          final status = newRow['status'] as String?;
          if (status == 'completed') {
            final resources = await _fetchCompletedResources(learningPathId);
            if (!controller.isClosed) {
              if (resources != null && resources.length == 5) {
                controller.add(LearningPathReady(resources: resources, learningPathId: learningPathId));
              } else {
                controller.add(LearningPathFailed(learningPathId: learningPathId));
              }
              controller.close();
            }
          } else if (status == 'failed') {
            if (!controller.isClosed) {
              controller.add(LearningPathFailed(learningPathId: learningPathId));
              controller.close();
            }
          }
        },
      )
      .subscribe();
}

Future<List<LearningPathResource>?> _fetchCompletedResources(String learningPathId) async {
  final row = await Supabase.instance.client
      .from('learning_paths')
      .select('resources')
      .eq('id', learningPathId)
      .eq('status', 'completed')
      .maybeSingle();
  if (row == null) return null;
  return _parseResources(row['resources']);
}

List<LearningPathResource> _parseResources(dynamic raw) {
  if (raw is! List) return [];
  return raw
      .whereType<Map<String, dynamic>>()
      .map(LearningPathResource.fromJson)
      .toList();
}

Future<String?> _triggerLearningPath(String decisionId) async {
  try {
    final session = Supabase.instance.client.auth.currentSession;
    final token = session?.accessToken ?? '';
    const fastapiUrl = String.fromEnvironment(
      'FASTAPI_URL',
      defaultValue: 'http://localhost:8000',
    );
    final response = await http.post(
      Uri.parse('$fastapiUrl/api/v1/learning-paths/trigger'),
      headers: {
        'Content-Type': 'application/json',
        if (token.isNotEmpty) 'Authorization': 'Bearer $token',
      },
      body: jsonEncode({'decision_id': decisionId}),
    );
    final body = jsonDecode(response.body) as Map<String, dynamic>;
    return body['data']?['learning_path_id'] as String?;
  } catch (_) {
    return null;
  }
}
