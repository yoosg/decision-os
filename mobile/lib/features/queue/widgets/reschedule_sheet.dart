import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../core/theme/app_theme.dart';

const List<(String, String)> kTimingOptions = [
  ('Today', 'today'),
  ('This Week', 'this_week'),
  ('Later', 'later'),
];

class RescheduleSheet extends StatelessWidget {
  final String currentTiming;

  const RescheduleSheet({super.key, required this.currentTiming});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 12,
        bottom: MediaQuery.of(context).viewInsets.bottom + 40,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // drag handle
          Container(
            width: 36,
            height: 4,
            decoration: BoxDecoration(
              color: const Color(0xFFDDDDDD),
              borderRadius: BorderRadius.circular(9999),
            ),
          ),
          const SizedBox(height: 16),
          Align(
            alignment: Alignment.centerLeft,
            child: Text('일정 변경', style: Theme.of(context).textTheme.titleLarge),
          ),
          const SizedBox(height: 12),
          ...kTimingOptions.map((entry) {
            final isSelected = entry.$2 == currentTiming;
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: SizedBox(
                width: double.infinity,
                child: OutlinedButton(
                  style: OutlinedButton.styleFrom(
                    minimumSize: const Size.fromHeight(44),
                    shape: const StadiumBorder(),
                    side: isSelected
                        ? const BorderSide(color: AppColors.accentPrimary, width: 1.5)
                        : null,
                  ),
                  onPressed: () {
                    HapticFeedback.mediumImpact();
                    Navigator.of(context).pop(entry.$2);
                  },
                  child: Text(entry.$1),
                ),
              ),
            );
          }),
        ],
      ),
    );
  }
}

Future<String?> showRescheduleSheet(
  BuildContext context, {
  required String currentTiming,
}) {
  return showModalBottomSheet<String>(
    context: context,
    isDismissible: true,
    enableDrag: true,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
    ),
    // WCAG 2.2 AA Reduce Motion (Story 5.4 AC-B3): reduce-motion 시 슬라이드업 → 즉시 표시.
    sheetAnimationStyle: MediaQuery.disableAnimationsOf(context)
        ? AnimationStyle.noAnimation
        : null,
    builder: (_) => RescheduleSheet(currentTiming: currentTiming),
  );
}
