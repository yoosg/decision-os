import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

part 'profile_provider.g.dart';

class UserProfile {
  final String? role;
  final String? experienceLevel;
  final List<String> techStack;
  final String? projectGoal;
  final List<String> interests;
  final int? dailyLearningTimeMin;

  const UserProfile({
    this.role,
    this.experienceLevel,
    this.techStack = const [],
    this.projectGoal,
    this.interests = const [],
    this.dailyLearningTimeMin,
  });

  factory UserProfile.fromJson(Map<String, dynamic> json) => UserProfile(
        role: json['role'] as String?,
        experienceLevel: json['experience_level'] as String?,
        techStack: (json['tech_stack'] as List<dynamic>?)?.whereType<String>().toList() ?? [],
        projectGoal: json['project_goal'] as String?,
        interests: (json['interests'] as List<dynamic>?)?.whereType<String>().toList() ?? [],
        dailyLearningTimeMin: json['daily_learning_time_min'] as int?,
      );

  UserProfile copyWith({
    String? role,
    String? experienceLevel,
    List<String>? techStack,
    String? projectGoal,
    List<String>? interests,
    int? dailyLearningTimeMin,
  }) =>
      UserProfile(
        role: role ?? this.role,
        experienceLevel: experienceLevel ?? this.experienceLevel,
        techStack: techStack ?? this.techStack,
        projectGoal: projectGoal ?? this.projectGoal,
        interests: interests ?? this.interests,
        dailyLearningTimeMin: dailyLearningTimeMin ?? this.dailyLearningTimeMin,
      );
}

@riverpod
class ProfileNotifier extends _$ProfileNotifier {
  static const _apiBase = String.fromEnvironment(
    'FASTAPI_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  @override
  Future<UserProfile> build() async {
    final session = Supabase.instance.client.auth.currentSession;
    if (session == null) throw Exception('No session');
    final response = await http.get(
      Uri.parse('$_apiBase/api/v1/users/profile'),
      headers: {'Authorization': 'Bearer ${session.accessToken}'},
    ).timeout(const Duration(seconds: 15));
    if (response.statusCode != 200) throw Exception('Failed to load profile');
    final body = jsonDecode(response.body) as Map<String, dynamic>?;
    final data = body?['data'] as Map<String, dynamic>?;
    if (data == null) throw Exception('Invalid response');
    return UserProfile.fromJson(data);
  }

  Future<void> updateProfile(Map<String, dynamic> updates) async {
    final prev = state;
    final current = state.requireValue;
    state = AsyncData(current.copyWith(
      role: updates['role'] as String?,
      experienceLevel: updates['experience_level'] as String?,
      techStack: (updates['tech_stack'] as List?)?.cast<String>(),
      projectGoal: updates['project_goal'] as String?,
      interests: (updates['interests'] as List?)?.cast<String>(),
      dailyLearningTimeMin: updates['daily_learning_time_min'] as int?,
    ));
    try {
      final session = Supabase.instance.client.auth.currentSession;
      if (session == null) throw Exception('No session');
      final response = await http.patch(
        Uri.parse('$_apiBase/api/v1/users/profile'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ${session.accessToken}',
        },
        body: jsonEncode(updates),
      ).timeout(const Duration(seconds: 15));
      if (response.statusCode != 200) throw Exception('Update failed');
    } catch (_) {
      state = prev;
      rethrow;
    }
  }
}
