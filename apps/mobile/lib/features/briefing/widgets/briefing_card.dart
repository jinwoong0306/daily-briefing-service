import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../models/briefing_model.dart';
import 'feedback_button_widget.dart';

class BriefingCard extends StatelessWidget {
  const BriefingCard({
    required this.item,
    required this.onTap,
    required this.onFeedback,
    required this.onBookmarkToggle,
    this.isRead = false,
    super.key,
  });

  final BriefingModel item;
  final VoidCallback onTap;
  final ValueChanged<FeedbackType> onFeedback;
  final VoidCallback onBookmarkToggle;
  final bool isRead;

  @override
  Widget build(BuildContext context) {
    final String originalUrl = (item.originalUrl ?? '').trim();
    final List<String> imageCandidates = <String>[
      item.imageUrl.trim(),
      if (originalUrl.isNotEmpty)
        'https://image.thum.io/get/width/1200/noanimate/$originalUrl',
      'https://picsum.photos/seed/${item.id}/1200/675',
      'https://placehold.co/1200x675/png?text=Daily+Briefing',
    ].where((String url) => url.isNotEmpty).toSet().toList();

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
                child: _NetworkImageWithFallback(urls: imageCandidates),
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
            if (isRead) ...<Widget>[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: AppColors.surfaceLow,
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(
                    color: AppColors.outlineVariant.withValues(alpha: 0.5),
                  ),
                ),
                child: Text(
                  '읽음',
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ),
            ],
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
                  onPressed: onBookmarkToggle,
                  icon: Icon(
                    item.isBookmarked
                        ? Icons.bookmark_rounded
                        : Icons.bookmark_border_rounded,
                  ),
                  tooltip: item.isBookmarked ? '저장 취소' : '저장',
                ),
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

class _NetworkImageWithFallback extends StatefulWidget {
  const _NetworkImageWithFallback({required this.urls});

  final List<String> urls;

  @override
  State<_NetworkImageWithFallback> createState() =>
      _NetworkImageWithFallbackState();
}

class _NetworkImageWithFallbackState extends State<_NetworkImageWithFallback> {
  int _index = 0;
  bool _scheduledNext = false;

  void _tryNextUrl() {
    if (_scheduledNext || _index >= widget.urls.length - 1) {
      return;
    }
    _scheduledNext = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _index += 1;
        _scheduledNext = false;
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    if (widget.urls.isEmpty) {
      return Container(
        color: AppColors.surfaceHigh,
        alignment: Alignment.center,
        child: const Icon(Icons.image_not_supported_rounded),
      );
    }

    return Image.network(
      widget.urls[_index],
      fit: BoxFit.cover,
      errorBuilder:
          (BuildContext context, Object error, StackTrace? stackTrace) {
            if (_index < widget.urls.length - 1) {
              _tryNextUrl();
              return Container(
                color: AppColors.surfaceHigh,
                alignment: Alignment.center,
                child: const SizedBox(
                  width: 24,
                  height: 24,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
              );
            }
            return Container(
              color: AppColors.surfaceHigh,
              alignment: Alignment.center,
              child: const Icon(Icons.image_not_supported_rounded),
            );
          },
    );
  }
}
