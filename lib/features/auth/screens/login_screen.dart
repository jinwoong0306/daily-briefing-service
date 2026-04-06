import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../services/api_exception.dart';
import '../../../services/auth_api_service.dart';
import '../../../shared/widgets/app_text_field_widget.dart';
import '../../../shared/widgets/primary_button_widget.dart';
import '../widgets/auth_logo_widget.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final AuthApiService _authApiService = AuthApiService();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();

  bool _isSubmitting = false;

  @override
  void dispose() {
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
              Text(
                '다시 오신 것을 환영합니다',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 8),
              Text(
                '아침 브리핑을 빠르게 확인하려면 로그인해 주세요.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 28),
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
                label: _isSubmitting ? '로그인 중...' : '로그인',
                onPressed: _isSubmitting ? null : _onLoginPressed,
              ),
              const SizedBox(height: 16),
              Center(
                child: TextButton(
                  onPressed: () => context.go('/signup'),
                  child: const Text('계정이 없으신가요? 회원가입'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _onLoginPressed() async {
    final String email = _emailController.text.trim();
    final String password = _passwordController.text;
    if (email.isEmpty || password.isEmpty) {
      _showMessage('이메일과 비밀번호를 입력해 주세요.');
      return;
    }

    setState(() => _isSubmitting = true);
    try {
      await _authApiService.login(email: email, password: password);
      if (!mounted) {
        return;
      }
      context.go('/onboarding');
    } on ApiException catch (error) {
      _showMessage(error.toString());
    } catch (_) {
      _showMessage('로그인 중 오류가 발생했습니다.');
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
