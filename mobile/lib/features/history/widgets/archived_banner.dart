import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';

// "보관된 Review" 배너 (설계 결정 3) — HonestBox 셸 구조 재사용, 중립 정보 톤
class ArchivedBanner extends StatelessWidget {
  const ArchivedBanner({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: const BoxDecoration(
        color: AppColors.surfaceCardAlt,
        borderRadius: BorderRadius.all(Radius.circular(12)),
        border: Border(
          left: BorderSide(color: AppColors.textSecondary, width: 3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '보관된 REVIEW',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textSecondary,
                  letterSpacing: 0.5,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            '이 Signal은 보관되어 최신 정보 갱신이 중단되었습니다. 아래 내용은 결정 당시 기록입니다.',
            style: Theme.of(context).textTheme.bodyLarge,
          ),
        ],
      ),
    );
  }
}
