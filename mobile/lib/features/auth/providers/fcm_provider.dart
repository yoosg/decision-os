import 'dart:convert';
import 'dart:io';

import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:http/http.dart' as http;
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

part 'fcm_provider.g.dart';

/// FCM 토큰을 FastAPI에 등록. 세션 없음 또는 토큰 없음 시 무시 (best-effort).
Future<void> registerFcmTokenWithToken(String token) async {
  final session = Supabase.instance.client.auth.currentSession;
  if (session == null) return;

  final platform = Platform.isIOS ? 'ios' : 'android';
  const apiBase = String.fromEnvironment(
    'FASTAPI_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  try {
    await http.post(
      Uri.parse('$apiBase/api/v1/devices/register'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ${session.accessToken}',
      },
      body: jsonEncode({'fcm_token': token, 'platform': platform}),
    );
  } catch (_) {
    // best-effort: 실패 시 무시 — 다음 로그인/오픈 시 재시도
  }
}

@riverpod
Future<void> registerFcmToken(RegisterFcmTokenRef ref) async {
  final token = await FirebaseMessaging.instance.getToken();
  if (token == null) return;
  await registerFcmTokenWithToken(token);
}
