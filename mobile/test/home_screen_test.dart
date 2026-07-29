import 'package:decision_os/core/theme/app_theme.dart';
import 'package:decision_os/features/home/providers/daily_brief_provider.dart';
import 'package:decision_os/features/home/widgets/signal_card.dart';
import 'package:decision_os/features/home/widgets/three_dot_loading_indicator.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

const _testSignal = SignalItem(
  signalId: 'sig-001',
  title: 'LLM Agents 최신 동향',
  summary: 'AI 에이전트 프레임워크의 핵심 변화',
  sourceCount: 7,
  position: 0,
);

Widget _buildTestApp(Widget child) => MaterialApp(
      theme: buildAppTheme(),
      home: Scaffold(body: child),
    );

void main() {
  group('SignalCard', () {
    testWidgets('탭 타겟 최소 44px 이상', (tester) async {
      await tester.pumpWidget(_buildTestApp(
        SignalCard(signal: _testSignal, isSeen: false, onTap: () {}),
      ));

      final container = tester.widget<Container>(
        find
            .descendant(
              of: find.byType(GestureDetector),
              matching: find.byType(Container),
            )
            .first,
      );
      final constraints = container.constraints;
      expect(constraints?.minHeight, greaterThanOrEqualTo(44));
    });

    testWidgets('isSeen=false일 때 NEW 배지 표시', (tester) async {
      await tester.pumpWidget(_buildTestApp(
        SignalCard(signal: _testSignal, isSeen: false, onTap: () {}),
      ));
      expect(find.text('NEW'), findsOneWidget);
    });

    testWidgets('isSeen=true일 때 NEW 배지 없음', (tester) async {
      await tester.pumpWidget(_buildTestApp(
        SignalCard(signal: _testSignal, isSeen: true, onTap: () {}),
      ));
      expect(find.text('NEW'), findsNothing);
    });

    testWidgets('탭 후 onTap 콜백 호출', (tester) async {
      var tapped = false;
      await tester.pumpWidget(_buildTestApp(
        SignalCard(
          signal: _testSignal,
          isSeen: false,
          onTap: () => tapped = true,
        ),
      ));
      await tester.tap(find.byType(GestureDetector));
      expect(tapped, isTrue);
    });

    testWidgets('Semantics composite label — NEW 포함 (isSeen=false)', (tester) async {
      final handle = tester.ensureSemantics();
      await tester.pumpWidget(_buildTestApp(
        SignalCard(signal: _testSignal, isSeen: false, onTap: () {}),
      ));

      final semanticsCard = tester.getSemantics(find.byType(SignalCard));
      expect(semanticsCard.label, contains('NEW'));
      expect(semanticsCard.label, contains('출처 7개'));
      expect(semanticsCard.label, contains('읽기 약 5분'));
      handle.dispose();
    });

    testWidgets('Semantics composite label — seen이면 NEW 없음', (tester) async {
      final handle = tester.ensureSemantics();
      await tester.pumpWidget(_buildTestApp(
        SignalCard(signal: _testSignal, isSeen: true, onTap: () {}),
      ));

      final semanticsCard = tester.getSemantics(find.byType(SignalCard));
      expect(semanticsCard.label, isNot(contains('NEW')));
      handle.dispose();
    });

    testWidgets('제목과 출처 메타가 렌더링됨', (tester) async {
      await tester.pumpWidget(_buildTestApp(
        SignalCard(signal: _testSignal, isSeen: false, onTap: () {}),
      ));
      expect(find.text('LLM Agents 최신 동향'), findsOneWidget);
      expect(find.text('출처 7개 · 읽기 약 5분'), findsOneWidget);
    });
  });

  group('ThreeDotLoadingIndicator', () {
    testWidgets('기본: 세 개의 점 렌더링', (tester) async {
      await tester.pumpWidget(_buildTestApp(const ThreeDotLoadingIndicator()));
      // 타이머 기간(0ms, 200ms, 400ms) 이상 진행
      await tester.pump(const Duration(milliseconds: 500));
      expect(find.text('·'), findsNWidgets(3));
    });

    testWidgets('disableAnimations=true: 정적 점 3개 표시', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: buildAppTheme(),
          home: MediaQuery(
            data: const MediaQueryData(disableAnimations: true),
            child: const Scaffold(body: ThreeDotLoadingIndicator()),
          ),
        ),
      );
      expect(find.text('·'), findsNWidgets(3));
    });
  });
}
