import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../../../core/theme/app_theme.dart';
import '../providers/fcm_provider.dart';

// Supabase(bcrypt)는 72바이트 초과 비밀번호를 잘라내므로 상한을 72자로 맞춘다.
const int _passwordMaxLength = 72;

class SignUpScreen extends ConsumerStatefulWidget {
  const SignUpScreen({super.key});

  @override
  ConsumerState<SignUpScreen> createState() => _SignUpScreenState();
}

class _SignUpScreenState extends ConsumerState<SignUpScreen> {
  final _emailCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _confirmPasswordCtrl = TextEditingController();
  bool _isLoading = false;
  String? _error;

  @override
  void dispose() {
    _emailCtrl.dispose();
    _passwordCtrl.dispose();
    _confirmPasswordCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.surfaceRaised,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 48),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                '계정 만들기',
                style: Theme.of(context).textTheme.displayLarge,
              ),
              const SizedBox(height: 8),
              const Text(
                '오늘의 AI 기술 브리핑을 받아보세요',
                style: TextStyle(fontSize: 14, color: AppColors.textSecondary),
              ),
              const SizedBox(height: 32),
              TextField(
                controller: _emailCtrl,
                keyboardType: TextInputType.emailAddress,
                autocorrect: false,
                decoration: const InputDecoration(
                  labelText: '이메일',
                  hintText: '이메일',
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.all(Radius.circular(12)),
                  ),
                  contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _passwordCtrl,
                obscureText: true,
                inputFormatters: [
                  LengthLimitingTextInputFormatter(_passwordMaxLength),
                ],
                decoration: const InputDecoration(
                  labelText: '비밀번호 (8자 이상)',
                  hintText: '비밀번호 (8자 이상)',
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.all(Radius.circular(12)),
                  ),
                  contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _confirmPasswordCtrl,
                obscureText: true,
                inputFormatters: [
                  LengthLimitingTextInputFormatter(_passwordMaxLength),
                ],
                onSubmitted: (_) => _isLoading ? null : _signUp(),
                decoration: const InputDecoration(
                  labelText: '비밀번호 확인',
                  hintText: '비밀번호를 다시 입력해 주세요',
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.all(Radius.circular(12)),
                  ),
                  contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                ),
              ),
              const SizedBox(height: 12),
              if (_error != null)
                Text(
                  _error!,
                  style: const TextStyle(
                    color: AppColors.error,
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              const SizedBox(height: 8),
              ElevatedButton(
                onPressed: _isLoading ? null : _signUp,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.accentPrimary,
                  foregroundColor: AppColors.accentForeground,
                  minimumSize: const Size(double.infinity, 52),
                  shape: const StadiumBorder(),
                  textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
                ),
                child: _isLoading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                          color: Colors.white,
                          strokeWidth: 2,
                        ),
                      )
                    : const Text('시작하기'),
              ),
              const SizedBox(height: 24),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Text(
                    '이미 계정이 있으신가요? ',
                    style: TextStyle(fontSize: 13, color: AppColors.textSecondary),
                  ),
                  GestureDetector(
                    onTap: () => context.go('/signin'),
                    child: const Text(
                      '로그인',
                      style: TextStyle(
                        fontSize: 13,
                        color: AppColors.textPrimary,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _signUp() async {
    if (_passwordCtrl.text.length < 8) {
      setState(() => _error = '비밀번호는 8자 이상이어야 합니다.');
      return;
    }
    if (_passwordCtrl.text.length > _passwordMaxLength) {
      setState(() => _error = '비밀번호는 $_passwordMaxLength자 이하여야 합니다.');
      return;
    }
    if (_passwordCtrl.text != _confirmPasswordCtrl.text) {
      setState(() => _error = '비밀번호가 일치하지 않습니다.');
      return;
    }
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response = await Supabase.instance.client.auth.signUp(
        email: _emailCtrl.text.trim(),
        password: _passwordCtrl.text,
      );
      if (response.session == null) {
        // 이메일 확인이 필요한 Supabase 설정인 경우
        setState(() => _error = '이메일을 확인해 주세요. 받은 편지함의 링크를 클릭한 후 로그인해 주세요.');
        return;
      }
      // FCM 토큰 등록 (best-effort)
      ref.read(registerFcmTokenProvider.future).ignore();
      // handle_new_user() 트리거가 user_profiles 생성 (onboarding_completed: false)
      if (mounted) context.go('/onboarding');
    } on AuthException catch (e) {
      setState(() => _error = _mapAuthError(e.message));
    } catch (e) {
      setState(() => _error = '회원가입 중 오류가 발생했습니다. 다시 시도해 주세요.');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  String _mapAuthError(String msg) {
    if (msg.contains('already registered') || msg.contains('User already registered')) {
      return '이미 등록된 이메일입니다.';
    }
    if (msg.contains('invalid email')) return '올바른 이메일 형식이 아닙니다.';
    if (msg.contains('Password should be at least')) return '비밀번호는 8자 이상이어야 합니다.';
    return '회원가입 중 오류가 발생했습니다. 다시 시도해 주세요.';
  }
}
