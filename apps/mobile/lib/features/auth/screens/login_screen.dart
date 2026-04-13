import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../shared/widgets/app_text_field_widget.dart';
import '../../../shared/widgets/primary_button_widget.dart';
import '../widgets/auth_logo_widget.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();

  final RegExp _emailRegExp = RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$');

  String? _emailError;
  String? _passwordError;
  String? _submitError;
  bool _isSubmitting = false;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  bool _isValidEmail(String value) {
    return _emailRegExp.hasMatch(value);
  }

  void _validateEmail(String value) {
    final String trimmedValue = value.trim();
    final bool isValid = _isValidEmail(trimmedValue);

    debugPrint('[Validation] field=email value=$trimmedValue valid=$isValid');

    setState(() {
      _emailError = isValid ? null : '올바른 이메일 형식이 아닙니다.';
      _submitError = null;
    });
  }

  void _validatePassword(String value) {
    final bool isValid = value.length >= 6;

    debugPrint(
      '[Validation] field=password length=${value.length} valid=$isValid',
    );

    setState(() {
      _passwordError = isValid ? null : '비밀번호는 6자 이상이어야 합니다.';
      _submitError = null;
    });
  }

  bool _validateFormForSubmit() {
    final String emailValue = _emailController.text.trim();
    final String passwordValue = _passwordController.text;

    final bool emailValid = _isValidEmail(emailValue);
    final bool passwordValid = passwordValue.length >= 6;

    debugPrint('[Validation] field=email value=$emailValue valid=$emailValid');
    debugPrint(
      '[Validation] field=password length=${passwordValue.length} valid=$passwordValid',
    );

    setState(() {
      _emailError = emailValid ? null : '올바른 이메일 형식이 아닙니다.';
      _passwordError = passwordValid ? null : '비밀번호는 6자 이상이어야 합니다.';
      _submitError = null;
    });

    return emailValid && passwordValid;
  }

  Future<int> _requestLogin({
    required String email,
    required String password,
  }) async {
    // TODO: connect API
    await Future<void>.delayed(const Duration(milliseconds: 250));
    return 200;
  }

  Future<void> _submitLogin() async {
    FocusScope.of(context).unfocus();

    if (!_validateFormForSubmit()) {
      _formKey.currentState?.validate();
      return;
    }

    final String email = _emailController.text.trim();
    final String password = _passwordController.text;

    debugPrint('[SUBMIT] login request: email=$email');

    setState(() {
      _isSubmitting = true;
    });

    try {
      final int response = await _requestLogin(email: email, password: password);
      if (!mounted) {
        return;
      }
      debugPrint('[SUBMIT] login response: status=$response');
      context.go('/onboarding');
    } catch (e) {
      debugPrint('[SUBMIT] login failed: error=$e');
      if (!mounted) {
        return;
      }
      setState(() {
        _submitError = '로그인에 실패했습니다. 다시 시도해 주세요.';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(24, 20, 24, 32),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                const Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: <Widget>[AuthLogoWidget(), Text('도움말')],
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
                  textInputAction: TextInputAction.next,
                  onChanged: _validateEmail,
                  validator: (_) => _emailError,
                ),
                const SizedBox(height: 16),
                AppTextFieldWidget(
                  label: '비밀번호',
                  hintText: '비밀번호를 입력해 주세요',
                  obscureText: true,
                  controller: _passwordController,
                  textInputAction: TextInputAction.done,
                  onChanged: _validatePassword,
                  validator: (_) => _passwordError,
                  onFieldSubmitted: (_) => _submitLogin(),
                ),
                if (_submitError != null) ...<Widget>[
                  const SizedBox(height: 12),
                  Text(
                    _submitError!,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ],
                const SizedBox(height: 24),
                PrimaryButtonWidget(
                  label: _isSubmitting ? '로그인 중...' : '로그인',
                  onPressed: _isSubmitting ? null : _submitLogin,
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
      ),
    );
  }
}
