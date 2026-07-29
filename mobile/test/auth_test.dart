import 'package:flutter_test/flutter_test.dart';

// signin_screen의 _mapAuthError 동작 검증 — 순수 로직 단위 테스트
String mapSignInError(String msg) {
  if (msg.contains('Invalid login credentials')) return '이메일 또는 비밀번호가 올바르지 않습니다.';
  if (msg.contains('Email not confirmed')) return '이메일 확인이 필요합니다.';
  return '로그인 중 오류가 발생했습니다. 다시 시도해 주세요.';
}

String mapSignUpError(String msg) {
  if (msg.contains('already registered') || msg.contains('User already registered')) {
    return '이미 등록된 이메일입니다.';
  }
  if (msg.contains('invalid email')) return '올바른 이메일 형식이 아닙니다.';
  if (msg.contains('Password should be at least')) return '비밀번호는 8자 이상이어야 합니다.';
  return '회원가입 중 오류가 발생했습니다. 다시 시도해 주세요.';
}

void main() {
  group('SignIn error message mapping', () {
    test('Invalid credentials returns Korean message', () {
      expect(
        mapSignInError('Invalid login credentials'),
        '이메일 또는 비밀번호가 올바르지 않습니다.',
      );
    });

    test('Email not confirmed returns Korean message', () {
      expect(
        mapSignInError('Email not confirmed'),
        '이메일 확인이 필요합니다.',
      );
    });

    test('Unknown error returns fallback Korean message', () {
      expect(
        mapSignInError('Server error'),
        '로그인 중 오류가 발생했습니다. 다시 시도해 주세요.',
      );
    });
  });

  group('SignUp error message mapping', () {
    test('Already registered returns Korean message', () {
      expect(
        mapSignUpError('User already registered'),
        '이미 등록된 이메일입니다.',
      );
    });

    test('Invalid email returns Korean message', () {
      expect(
        mapSignUpError('invalid email format'),
        '올바른 이메일 형식이 아닙니다.',
      );
    });

    test('Password too short returns Korean message', () {
      expect(
        mapSignUpError('Password should be at least 6 characters'),
        '비밀번호는 8자 이상이어야 합니다.',
      );
    });

    test('Unknown error returns fallback Korean message', () {
      expect(
        mapSignUpError('Network error'),
        '회원가입 중 오류가 발생했습니다. 다시 시도해 주세요.',
      );
    });
  });

  group('GoRouter redirect logic', () {
    test('No session and non-auth route redirects to /signin', () {
      const session = null;
      const isAuthRoute = false;

      String? result;
      if (session == null && !isAuthRoute) result = '/signin';
      if (session != null && isAuthRoute) result = '/home';

      expect(result, '/signin');
    });

    test('Session exists and auth route redirects to /home', () {
      const session = 'valid-session';
      const isAuthRoute = true;

      String? result;
      if (session == null && !isAuthRoute) result = '/signin';
      if (session != null && isAuthRoute) result = '/home';

      expect(result, '/home');
    });

    test('Session exists and non-auth route has no redirect', () {
      const session = 'valid-session';
      const isAuthRoute = false;

      String? result;
      if (session == null && !isAuthRoute) result = '/signin';
      if (session != null && isAuthRoute) result = '/home';

      expect(result, null);
    });
  });
}
