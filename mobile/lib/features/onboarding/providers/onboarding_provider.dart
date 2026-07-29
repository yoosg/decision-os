import 'package:flutter_riverpod/flutter_riverpod.dart';

const String kOnboardingCompletedKey = 'onboarding_completed';
const String kNotificationPermissionRequestedKey = 'notification_permission_requested';

final onboardingCompletedProvider = StateProvider<bool>((ref) => false);
