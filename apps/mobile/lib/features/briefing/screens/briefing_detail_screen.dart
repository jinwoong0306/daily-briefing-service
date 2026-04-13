import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/primary_button_widget.dart';
import '../models/briefing_model.dart';
import '../widgets/feedback_button_widget.dart';

class BriefingDetailScreen extends StatefulWidget {
  const BriefingDetailScreen({required this.briefing, super.key});

  final BriefingModel? briefing;

  @override
  State<BriefingDetailScreen> createState() => _BriefingDetailScreenState();
}

class _BriefingDetailScreenState extends State<BriefingDetailScreen> {
  FeedbackType? _selectedFeedback;

  @override
  Widget build(BuildContext context) {
    final BriefingModel? item = widget.briefing;
    if (item == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('브리핑 상세')),
        body: Center(
          child: Text(
            '브리핑을 찾을 수 없습니다.',
            style: Theme.of(context).textTheme.titleLarge,
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          onPressed: () => context.pop(),
          icon: const Icon(Icons.arrow_back_ios_new_rounded),
        ),
        title: const Text('브리핑 상세'),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
        children: <Widget>[
          ClipRRect(
            borderRadius: BorderRadius.circular(20),
            child: AspectRatio(
              aspectRatio: 16 / 9,
              child: Image.network(
                item.imageUrl,
                fit: BoxFit.cover,
                errorBuilder:
                    (
                      BuildContext context,
                      Object error,
                      StackTrace? stackTrace,
                    ) => Container(
                      color: AppColors.surfaceHigh,
                      alignment: Alignment.center,
                      child: const Icon(Icons.image_not_supported_rounded),
                    ),
              ),
            ),
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  item.category,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: AppColors.primaryDark,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: AppColors.surfaceLow,
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  '${item.readTimeMinutes}분 읽기',
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(item.title, style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 10),
          Text(
            item.summary,
            style: Theme.of(
              context,
            ).textTheme.bodyLarge?.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 16),
          Text('핵심 요약', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          ...item.highlights.map((String point) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  const Padding(
                    padding: EdgeInsets.only(top: 7),
                    child: Icon(
                      Icons.circle,
                      size: 6,
                      color: AppColors.primary,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      point,
                      style: Theme.of(context).textTheme.bodyLarge,
                    ),
                  ),
                ],
              ),
            );
          }),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppColors.surfaceLow,
              borderRadius: BorderRadius.circular(14),
              boxShadow: AppColors.panelShadow,
            ),
            child: Row(
              children: <Widget>[
                const Icon(
                  Icons.article_outlined,
                  color: AppColors.textSecondary,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    '${item.sourceName} · ${item.publishedAt.year}.${item.publishedAt.month.toString().padLeft(2, '0')}.${item.publishedAt.day.toString().padLeft(2, '0')}',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          Text('이 브리핑은 어땠나요?', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          FeedbackButtonWidget(
            selectedType: _selectedFeedback,
            onChanged: (FeedbackType value) {
              setState(() => _selectedFeedback = value);
              final String text = value == FeedbackType.like
                  ? '도움이 됐어요'
                  : '취향이 아니에요';
              ScaffoldMessenger.of(
                context,
              ).showSnackBar(SnackBar(content: Text('피드백이 저장되었습니다: $text')));
            },
          ),
          const SizedBox(height: 20),
          PrimaryButtonWidget(
            label: '원문 기사 보기',
            icon: Icons.open_in_new_rounded,
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('원문 연결은 API 연동 단계에서 활성화됩니다.')),
              );
            },
          ),
        ],
      ),
    );
  }
}
