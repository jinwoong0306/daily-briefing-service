import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/primary_button_widget.dart';
import '../models/onboarding_preferences_model.dart';
import '../widgets/keyword_chip_widget.dart';
import '../widgets/time_selector_widget.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  static const List<String> _allKeywords = <String>[
    'IT/과학',
    '경제',
    '정치',
    '엔터테인먼트',
    '스포츠',
    '헬스',
    '아트&컬처',
    '월드 뉴스',
  ];

  final Set<String> _selectedKeywords = <String>{'IT/과학', '엔터테인먼트'};
  int _hour = 8;
  int _minute = 0;
  bool _isAm = true;

  @override
  Widget build(BuildContext context) {
    final bool canContinue = _selectedKeywords.length >= 3;

    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(24, 20, 24, 28),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'STEP 1 / 3',
                style: Theme.of(
                  context,
                ).textTheme.labelSmall?.copyWith(color: AppColors.primary),
              ),
              const SizedBox(height: 12),
              Text(
                '맞춤형 데일리 브리핑 설정',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 10),
              Text(
                '관심 주제를 선택하면 아침마다 핵심 뉴스만 간결하게 전달해 드립니다.',
                style: Theme.of(context).textTheme.bodyLarge,
              ),
              const SizedBox(height: 28),
              Row(
                children: <Widget>[
                  Text('관심 키워드', style: Theme.of(context).textTheme.titleLarge),
                  const Spacer(),
                  Text(
                    '최소 3개 선택',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Wrap(
                spacing: 8,
                runSpacing: 10,
                children: _allKeywords.map((String keyword) {
                  return KeywordChipWidget(
                    label: keyword,
                    isSelected: _selectedKeywords.contains(keyword),
                    onTap: () => _toggleKeyword(keyword),
                  );
                }).toList(),
              ),
              const SizedBox(height: 24),
              TimeSelectorWidget(
                hour: _hour,
                minute: _minute,
                isAm: _isAm,
                onHourChanged: (int value) => setState(() => _hour = value),
                onMinuteChanged: (int value) => setState(() => _minute = value),
                onPeriodChanged: (bool value) => setState(() => _isAm = value),
              ),
              const SizedBox(height: 24),
              _PreviewCard(keywords: _selectedKeywords.toList()),
              const SizedBox(height: 20),
              PrimaryButtonWidget(
                label: '시작하기',
                icon: Icons.arrow_forward_rounded,
                onPressed: canContinue ? _onContinue : null,
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _toggleKeyword(String keyword) {
    setState(() {
      if (_selectedKeywords.contains(keyword)) {
        _selectedKeywords.remove(keyword);
      } else {
        _selectedKeywords.add(keyword);
      }
    });
  }

  void _onContinue() {
    final OnboardingPreferencesModel preferences = OnboardingPreferencesModel(
      keywords: _selectedKeywords.toList(),
      hour: _hour,
      minute: _minute,
      isAm: _isAm,
    );

    context.go('/briefing', extra: preferences);
  }
}

class _PreviewCard extends StatelessWidget {
  const _PreviewCard({required this.keywords});

  final List<String> keywords;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[AppColors.primaryDark, AppColors.primaryContainer],
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            '라이브 프리뷰',
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: Colors.white.withValues(alpha: 0.8),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '내일 아침 브리핑에 포함될 주제',
            style: Theme.of(
              context,
            ).textTheme.titleLarge?.copyWith(color: Colors.white),
          ),
          const SizedBox(height: 12),
          Text(
            keywords.join(' · '),
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
              color: Colors.white.withValues(alpha: 0.92),
            ),
          ),
        ],
      ),
    );
  }
}
