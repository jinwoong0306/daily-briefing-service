import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../shared/widgets/app_text_field_widget.dart';
import '../../../shared/widgets/primary_button_widget.dart';
import '../widgets/auth_logo_widget.dart';

class SignupScreen extends StatelessWidget {
  const SignupScreen({super.key});

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
              const AppTextFieldWidget(label: '이름', hintText: '이름을 입력해 주세요'),
              const SizedBox(height: 16),
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
                label: '계정 만들기',
                onPressed: () => context.go('/onboarding'),
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
}
