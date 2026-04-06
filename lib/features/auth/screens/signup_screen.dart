import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../services/api_exception.dart';
import '../../../services/auth_api_service.dart';
import '../../../services/session_store.dart';
import '../../../shared/widgets/app_text_field_widget.dart';
import '../../../shared/widgets/primary_button_widget.dart';
import '../widgets/auth_logo_widget.dart';

class SignupScreen extends StatefulWidget {
  const SignupScreen({super.key});

  @override
  State<SignupScreen> createState() => _SignupScreenState();
}

class _SignupScreenState extends State<SignupScreen> {
  final AuthApiService _authApiService = AuthApiService();
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();

  bool _isSubmitting = false;

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(24, 20, 24, 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: const <Widget>[AuthLogoWidget(), Text('도움말')],
              ),
              const SizedBox(height: 44),
              Text('회원가입', style: Theme.of(context).textTheme.headlineMedium),
              const SizedBox(height: 8),
              Text(
                '계정을 만들고 맞춤형 아침 브리핑을 시작해 보세요.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 28),
              AppTextFieldWidget(
                label: '이름',
                hintText: '이름을 입력해 주세요',
                controller: _nameController,
              ),
              const SizedBox(height: 16),
              AppTextFieldWidget(
                label: '이메일',
                hintText: 'name@company.com',
                keyboardType: TextInputType.emailAddress,
                controller: _emailController,
              ),
              const SizedBox(height: 16),
              AppTextFieldWidget(
                label: '비밀번호',
                hintText: '비밀번호를 입력해 주세요',
                obscureText: true,
                controller: _passwordController,
              ),
              const SizedBox(height: 24),
              PrimaryButtonWidget(
                label: _isSubmitting ? '생성 중...' : '계정 만들기',
                onPressed: _isSubmitting ? null : _onSignupPressed,
              ),
              const SizedBox(height: 16),
              Center(
                child: TextButton(
                  onPressed: () => context.go('/login'),
                  child: const Text('이미 계정이 있으신가요? 로그인'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _onSignupPressed() async {
    final String name = _nameController.text.trim();
    final String email = _emailController.text.trim();
    final String password = _passwordController.text;
    if (name.isEmpty || email.isEmpty || password.isEmpty) {
      _showMessage('이름, 이메일, 비밀번호를 모두 입력해 주세요.');
      return;
    }

    if (password.length < 8) {
      _showMessage('비밀번호는 8자 이상이어야 합니다.');
      return;
    }

    setState(() => _isSubmitting = true);
    try {
      await _authApiService.register(
        name: name,
        email: email,
        password: password,
      );
      if (!mounted) {
        return;
      }
      // 회원가입 직후 재로그인 UX를 위해 발급 토큰을 비우고 로그인 화면으로 이동
      SessionStore.accessToken = null;
      _showMessage('회원가입 완료! 로그인해 주세요.');
      context.go('/login');
    } on ApiException catch (error) {
      _showMessage(error.toString());
    } catch (_) {
      _showMessage('회원가입 중 오류가 발생했습니다.');
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  void _showMessage(String message) {
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }
}
