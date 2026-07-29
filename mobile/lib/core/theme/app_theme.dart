import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class AppColors {
  static const surfaceBase      = Color(0xFFFFFFFF);
  static const surfaceRaised    = Color(0xFFF9F9F9);
  static const surfaceCard      = Color(0xFFF2F2F2);
  static const surfaceCardAlt   = Color(0xFFECECEC);
  static const textPrimary      = Color(0xFF0D0D0D);
  static const textSecondary    = Color(0xFF595D6A);
  static const textTertiary     = Color(0xFF9CA3AF);
  static const textDisabled     = Color(0xFFD1D1D1);
  static const borderSubtle     = Color(0xFFE5E5E5);
  static const borderCard       = Color(0xFFDCDCDC);
  static const accentPrimary    = Color(0xFF0D0D0D);
  static const accentForeground = Color(0xFFFFFFFF);
  static const statusPositive   = Color(0xFF16A34A);
  static const statusPositiveBg = Color(0xFFDCFCE7);
  static const statusWarning    = Color(0xFFB45309);
  static const statusUncertain  = Color(0xFF6B7280);
  static const error            = Color(0xFFEF4444);
  static const errorBg          = Color(0xFFFEF2F2);
  static const surfaceHonestBox = Color(0xFFF5F5F5);
}

ThemeData buildAppTheme() {
  return ThemeData(
    useMaterial3: true,
    splashFactory: NoSplash.splashFactory,  // 잉크/리플 전면 금지 (UX-DR15)
    highlightColor: Colors.transparent,
    colorScheme: const ColorScheme.light(
      surface:      AppColors.surfaceBase,
      primary:      AppColors.accentPrimary,
      onPrimary:    AppColors.accentForeground,
      secondary:    AppColors.textSecondary,
      onSecondary:  AppColors.surfaceBase,
      error:        AppColors.error,
      onError:      AppColors.surfaceBase,
      onSurface:    AppColors.textPrimary,
    ),
    textTheme: const TextTheme(
      // screen-title: 28-30px/700/-0.5px
      displayLarge:  TextStyle(fontSize: 30, fontWeight: FontWeight.w700, letterSpacing: -0.5),
      // section-title: 22-24px/700/-0.3px
      displayMedium: TextStyle(fontSize: 24, fontWeight: FontWeight.w700, letterSpacing: -0.3),
      // body-large: 17px/600/-0.2px
      titleLarge:    TextStyle(fontSize: 17, fontWeight: FontWeight.w600, letterSpacing: -0.2),
      // body-card: 16px/600
      titleMedium:   TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
      // body: 15px/500 (bodyLarge + bodyMedium 모두 설정 — Text() 기본 슬롯 일치)
      bodyLarge:     TextStyle(fontSize: 15, fontWeight: FontWeight.w500),
      bodyMedium:    TextStyle(fontSize: 15, fontWeight: FontWeight.w500),
      // label: 13px/600
      labelLarge:    TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
      // caption: 11-12px/500
      bodySmall:     TextStyle(fontSize: 12, fontWeight: FontWeight.w500, letterSpacing: 0.4),
      // badge: 10px/700/uppercase/0.5px
      labelSmall:    TextStyle(fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 0.5),
    ),
    cardTheme: const CardThemeData(
      color: AppColors.surfaceCard,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.all(Radius.circular(16)),
      ),
    ),
    // 버튼 형태: pill radius (DESIGN.md --radius-pill: 9999px)
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        shape: const StadiumBorder(),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        shape: const StadiumBorder(),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        shape: const StadiumBorder(),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        shape: const StadiumBorder(),
      ),
    ),
    bottomSheetTheme: const BottomSheetThemeData(
      backgroundColor: AppColors.surfaceBase,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(24),
          topRight: Radius.circular(24),
        ),
      ),
    ),
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      backgroundColor: AppColors.surfaceBase,
      selectedItemColor: AppColors.textPrimary,
      unselectedItemColor: AppColors.textSecondary,
      elevation: 0,
    ),
    dividerColor: AppColors.borderSubtle,
    scaffoldBackgroundColor: AppColors.surfaceRaised,
  );
}
