import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../shared/widgets/app_text_field_widget.dart';
import '../../../shared/widgets/primary_button_widget.dart';
import '../widgets/auth_logo_widget.dart';

class SignupScreen extends StatefulWidget {
  const SignupScreen({super.key});

  @override
  State<SignupScreen> createState() => _SignupScreenState();
}

class _SignupScreenState extends State<SignupScreen> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();

  final RegExp _emailRegExp = RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$');

  String? _nameError;
  String? _emailError;
  String? _passwordError;
  String? _submitError;
  bool _isSubmitting = false;

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  bool _isValidEmail(String value) {
    return _emailRegExp.hasMatch(value);
  }

  void _validateName(String value) {
    final String trimmedValue = value.trim();
    final bool isValid = trimmedValue.isNotEmpty;

    setState(() {
      _nameError = isValid ? null : '이름을 입력해 주세요.';
      _submitError = null;
    });
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
    final String nameValue = _nameController.text.trim();
    final String emailValue = _emailController.text.trim();
    final String passwordValue = _passwordController.text;

    final bool nameValid = nameValue.isNotEmpty;
    final bool emailValid = _isValidEmail(emailValue);
    final bool passwordValid = passwordValue.length >= 6;

    debugPrint('[Validation] field=email value=$emailValue valid=$emailValid');
    debugPrint(
      '[Validation] field=password length=${passwordValue.length} valid=$passwordValid',
    );

    setState(() {
      _nameError = nameValid ? null : '이름을 입력해 주세요.';
      _emailError = emailValid ? null : '올바른 이메일 형식이 아닙니다.';
      _passwordError = passwordValid ? null : '비밀번호는 6자 이상이어야 합니다.';
      _submitError = null;
    });

    return nameValid && emailValid && passwordValid;
  }

  Future<int> _requestSignup({
    required String name,
    required String email,
    required String password,
  }) async {
    // TODO: connect API
    await Future<void>.delayed(const Duration(milliseconds: 250));
    return 200;
  }

  Future<void> _submitSignup() async {
    FocusScope.of(context).unfocus();

    if (!_validateFormForSubmit()) {
      _formKey.currentState?.validate();
      return;
    }

    final String name = _nameController.text.trim();
    final String email = _emailController.text.trim();
    final String password = _passwordController.text;

    debugPrint('[SUBMIT] signup request: email=$email');

    setState(() {
      _isSubmitting = true;
    });

    try {
      final int response = await _requestSignup(
        name: name,
        email: email,
        password: password,
      );
      if (!mounted) {
        return;
      }
      debugPrint('[SUBMIT] signup response: status=$response');
      context.go('/onboarding');
    } catch (e) {
      debugPrint('[SUBMIT] signup failed: error=$e');
      if (!mounted) {
        return;
      }
      setState(() {
        _submitError = '회원가입에 실패했습니다. 다시 시도해 주세요.';
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
                  textInputAction: TextInputAction.next,
                  onChanged: _validateName,
                  validator: (_) => _nameError,
                ),
                const SizedBox(height: 16),
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
                  onFieldSubmitted: (_) => _submitSignup(),
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
                  label: _isSubmitting ? '회원가입 중...' : '계정 만들기',
                  onPressed: _isSubmitting ? null : _submitSignup,
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
      ),
    );
  }
}
