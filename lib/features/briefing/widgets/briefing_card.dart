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
      if (originalUrl.isNotEmpty)
        'https://image.thum.io/get/width/1200/noanimate/${Uri.encodeComponent(originalUrl)}',
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
          boxShadow: const <BoxShadow>[
            BoxShadow(
              color: Color(0x14282B51),
              blurRadius: 24,
              offset: Offset(0, 8),
            ),
          ],
        ),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: AspectRatio(
                aspectRatio: 16 / 9,
                child: _NetworkImageWithFallback(
                  urls: imageCandidates,
                ),
              ),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: AppColors.primary.withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(999),
              ),
              child: Text(
                item.category,
                style: Theme.of(
                  context,
                ).textTheme.labelSmall?.copyWith(
                  color: AppColors.primaryDark,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            if (isRead) ...<Widget>[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: const Color(0xFFF1F4F8),
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(color: const Color(0xFFD8E0EB)),
                ),
                child: Text(
                  '읽음',
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: const Color(0xFF5A6472),
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
                  tooltip: item.isBookmarked ? '저장 해제' : '저장',
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

class _ImageErrorPlaceholder extends StatelessWidget {
  const _ImageErrorPlaceholder();

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFFF3F4F6),
      alignment: Alignment.center,
      child: const Icon(Icons.image_not_supported_rounded),
    );
  }
}

class _NetworkImageWithFallback extends StatefulWidget {
  const _NetworkImageWithFallback({required this.urls});

  final List<String> urls;

  @override
  State<_NetworkImageWithFallback> createState() => _NetworkImageWithFallbackState();
}

class _NetworkImageWithFallbackState extends State<_NetworkImageWithFallback> {
  int _index = 0;
  bool _scheduledNext = false;
  bool _resolved = false;
  bool _loadingTimedOut = false;
  static const Duration _candidateTimeout = Duration(seconds: 4);

  @override
  void initState() {
    super.initState();
    _startTimeoutWatcher();
  }

  @override
  void didUpdateWidget(covariant _NetworkImageWithFallback oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.urls.join('|') != widget.urls.join('|')) {
      _index = 0;
      _scheduledNext = false;
      _resolved = false;
      _loadingTimedOut = false;
      _startTimeoutWatcher();
    }
  }

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
        _resolved = false;
        _loadingTimedOut = false;
      });
      _startTimeoutWatcher();
    });
  }

  void _startTimeoutWatcher() {
    Future<void>.delayed(_candidateTimeout, () {
      if (!mounted || _resolved || _index >= widget.urls.length - 1) {
        return;
      }
      setState(() => _loadingTimedOut = true);
      _tryNextUrl();
    });
  }

  @override
  Widget build(BuildContext context) {
    if (widget.urls.isEmpty || _index >= widget.urls.length) {
      return const _ImageErrorPlaceholder();
    }
    final String currentUrl = widget.urls[_index];
    return Image.network(
      currentUrl,
      fit: BoxFit.cover,
      loadingBuilder: (
        BuildContext context,
        Widget child,
        ImageChunkEvent? loadingProgress,
      ) {
        if (loadingProgress == null) {
          _resolved = true;
          return child;
        }
        if (_loadingTimedOut && _index >= widget.urls.length - 1) {
          return const _ImageErrorPlaceholder();
        }
        return const _ImageShimmerPlaceholder();
      },
      errorBuilder: (BuildContext context, Object error, StackTrace? stackTrace) {
        if (_index >= widget.urls.length - 1) {
          return const _ImageErrorPlaceholder();
        }
        _tryNextUrl();
        return const _ImageShimmerPlaceholder();
      },
    );
  }
}

class _ImageShimmerPlaceholder extends StatefulWidget {
  const _ImageShimmerPlaceholder();

  @override
  State<_ImageShimmerPlaceholder> createState() =>
      _ImageShimmerPlaceholderState();
}

class _ImageShimmerPlaceholderState extends State<_ImageShimmerPlaceholder>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final CurvedAnimation _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1450),
    )..repeat();
    _animation = CurvedAnimation(parent: _controller, curve: Curves.easeInOut);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (BuildContext context, Widget? child) {
        final double shift = (_animation.value * 3.2) - 1.6;
        return ShaderMask(
          shaderCallback: (Rect bounds) {
            return LinearGradient(
              begin: Alignment(-0.8 + shift, -0.2),
              end: Alignment(0.8 + shift, 0.2),
              colors: const <Color>[
                Color(0xFFE6EBF3),
                Color(0xFFF9FBFE),
                Color(0xFFE6EBF3),
              ],
              stops: const <double>[0.18, 0.5, 0.82],
            ).createShader(bounds);
          },
          blendMode: BlendMode.srcATop,
          child: Container(
            color: const Color(0xFFE8EDF5),
            alignment: Alignment.center,
            child: const Icon(
              Icons.image_outlined,
              color: Color(0xFFC2CADA),
            ),
          ),
        );
      },
    );
  }
}
