import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:decision_os/core/theme/app_theme.dart';

void main() {
  group('AppTheme', () {
    late ThemeData theme;

    setUp(() {
      theme = buildAppTheme();
    });

    test('uses Material 3', () {
      expect(theme.useMaterial3, isTrue);
    });

    test('splash is disabled (NoSplash)', () {
      expect(theme.splashFactory, equals(NoSplash.splashFactory));
    });

    test('highlightColor is transparent', () {
      expect(theme.highlightColor, equals(Colors.transparent));
    });

    test('primary color matches accent primary', () {
      expect(theme.colorScheme.primary, equals(AppColors.accentPrimary));
    });

    test('scaffold background is surfaceRaised', () {
      expect(theme.scaffoldBackgroundColor, equals(AppColors.surfaceRaised));
    });

    test('card elevation is 0', () {
      expect(theme.cardTheme.elevation, equals(0));
    });

    test('card border radius is 16', () {
      final shape = theme.cardTheme.shape as RoundedRectangleBorder;
      final radius = shape.borderRadius as BorderRadius;
      expect(radius.topLeft.x, equals(16));
    });

    test('displayLarge font size is 30', () {
      expect(theme.textTheme.displayLarge?.fontSize, equals(30));
    });

    test('displayLarge font weight is 700', () {
      expect(theme.textTheme.displayLarge?.fontWeight, equals(FontWeight.w700));
    });

    test('labelSmall font size is 10 (badge)', () {
      expect(theme.textTheme.labelSmall?.fontSize, equals(10));
    });
  });

  group('AppColors', () {
    test('textPrimary is #0D0D0D', () {
      expect(AppColors.textPrimary.value, equals(0xFF0D0D0D));
    });

    test('accentPrimary is #0D0D0D', () {
      expect(AppColors.accentPrimary.value, equals(0xFF0D0D0D));
    });

    test('statusPositive is #16A34A', () {
      expect(AppColors.statusPositive.value, equals(0xFF16A34A));
    });

    test('error is #EF4444', () {
      expect(AppColors.error.value, equals(0xFFEF4444));
    });
  });
}
