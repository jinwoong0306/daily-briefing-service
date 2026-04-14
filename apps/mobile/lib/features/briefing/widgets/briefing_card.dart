import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../models/briefing_model.dart';
import 'feedback_button_widget.dart';

class BriefingCard extends StatelessWidget {
  const BriefingCard({
    required this.item,
    required this.onTap,
    required this.onFeedback,
    super.key,
  });

  final BriefingModel item;
  final VoidCallback onTap;
  final ValueChanged<FeedbackType> onFeedback;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(24),
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(24),
          boxShadow: AppColors.cardShadow,
        ),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            ClipRRect(
              borderRadius: BorderRadius.circular(16),
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
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: AppColors.primary.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(999),
              ),
              child: Text(
                item.category,
                style: Theme.of(
                  context,
                ).textTheme.labelSmall?.copyWith(color: AppColors.primaryDark),
              ),
            ),
            const SizedBox(height: 10),
            Text(item.title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Text(
              item.summary,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
            ),
            const SizedBox(height: 12),
            ...item.highlights.take(2).map((String point) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    const Padding(
                      padding: EdgeInsets.only(top: 6),
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
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ),
                  ],
                ),
              );
            }),
            const SizedBox(height: 6),
            Row(
              children: <Widget>[
                TextButton(onPressed: onTap, child: const Text('원문 보기')),
                const Spacer(),
                IconButton(
                  onPressed: () => onFeedback(FeedbackType.like),
                  icon: const Icon(Icons.thumb_up_alt_outlined),
                  tooltip: '도움이 됐어요',
                ),
                IconButton(
                  onPressed: () => onFeedback(FeedbackType.dislike),
                  icon: const Icon(Icons.thumb_down_alt_outlined),
                  tooltip: '취향이 아니에요',
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
