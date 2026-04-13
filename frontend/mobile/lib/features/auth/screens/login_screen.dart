import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../shared/widgets/app_text_field_widget.dart';
import '../../../shared/widgets/primary_button_widget.dart';
import '../widgets/auth_logo_widget.dart';

class LoginScreen extends StatelessWidget {
  const LoginScreen({super.key});

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
              const AppTextFieldWidget(
                label: '이메일',
                hintText: 'name@company.com',
                keyboardType: TextInputType.emailAddress,
              ),
              const SizedBox(height: 16),
              const AppTextFieldWidget(
                label: '비밀번호',
                hintText: '비밀번호를 입력해 주세요',
                obscureText: true,
              ),
              const SizedBox(height: 24),
              PrimaryButtonWidget(
                label: '로그인',
                onPressed: () => context.go('/onboarding'),
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
}
