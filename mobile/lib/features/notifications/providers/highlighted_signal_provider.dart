import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'highlighted_signal_provider.g.dart';

/// 홈 화면에서 강조(하이라이트)할 Signal id 상태 (Story 5.3).
///
/// Push 탭(딥링크) 또는 foreground 수신 시 대상 signal_id를 set하고,
/// 홈 SignalCard가 이를 watch해 해당 카드를 강조한다. 카드 탭/소비 시 clear.
/// `daily_brief_provider.dart`의 SeenSignalIds와 동일한 @riverpod class 스타일.
@riverpod
class HighlightedSignal extends _$HighlightedSignal {
  @override
  String? build() => null;

  void set(String signalId) => state = signalId;

  void clear() => state = null;
}
