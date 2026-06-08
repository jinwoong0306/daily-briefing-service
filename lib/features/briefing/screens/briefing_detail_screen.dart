import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/theme/app_colors.dart';
import '../../../services/api_exception.dart';
import '../../../services/briefing_actions_api_service.dart';
import '../../../services/gemini_api_service.dart';
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
  final GeminiApiService _geminiApiService = GeminiApiService();
  final BriefingActionsApiService _briefingActionsApiService =
      BriefingActionsApiService();
  FeedbackType? _selectedFeedback;
  bool _isBookmarked = false;
  bool _isGenerating = false;
  String? _aiOneLineSummary;

  @override
  void initState() {
    super.initState();
    final BriefingModel? item = widget.briefing;
    _isBookmarked = item?.isBookmarked ?? false;
    final String? feedback = item?.feedbackType;
    if (feedback == 'like') {
      _selectedFeedback = FeedbackType.like;
    } else if (feedback == 'dislike') {
      _selectedFeedback = FeedbackType.dislike;
    }
  }

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
    final List<String> highlightPoints = _resolveHighlightPoints(item);

    return PopScope<BriefingModel>(
      canPop: false,
      onPopInvokedWithResult: (bool didPop, BriefingModel? result) {
        if (didPop) {
          return;
        }
        _popWithLatestState(item);
      },
      child: Scaffold(
        appBar: AppBar(
          leading: IconButton(
            onPressed: () => _popWithLatestState(item),
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
                child: _NetworkImageWithFallback(urls: imageCandidates),
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
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppColors.surfaceLow,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    const Icon(Icons.auto_awesome_rounded, size: 18),
                    const SizedBox(width: 8),
                    Text('AI 한줄요약', style: Theme.of(context).textTheme.titleLarge),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  _aiOneLineSummary ?? '아직 생성된 요약이 없습니다.',
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
                const SizedBox(height: 10),
                SizedBox(
                  height: 38,
                  child: OutlinedButton.icon(
                    onPressed: _isGenerating ? null : () => _generateAiSummary(item),
                    icon: _isGenerating
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.bolt_rounded, size: 16),
                    label: Text(_isGenerating ? '생성 중...' : 'Gemini로 생성'),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Text('핵심 요약', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          ...highlightPoints.map((String point) {
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
            onChanged: (FeedbackType value) => _saveFeedback(item.id, value),
          ),
          const SizedBox(height: 20),
          OutlinedButton.icon(
            onPressed: () => _toggleBookmark(item.id),
            icon: Icon(
              _isBookmarked
                  ? Icons.bookmark_rounded
                  : Icons.bookmark_border_rounded,
            ),
            label: Text(_isBookmarked ? '저장 해제' : '북마크 저장'),
          ),
          const SizedBox(height: 10),
            PrimaryButtonWidget(
              label: '원문 기사 보기',
              icon: Icons.open_in_new_rounded,
              onPressed: () => _openOriginalUrl(item.originalUrl),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _generateAiSummary(BriefingModel item) async {
    setState(() => _isGenerating = true);
    try {
      final String generated = await _geminiApiService.generateOneLineSummary(
        title: item.title,
        summary: item.summary,
      );
      if (!mounted) {
        return;
      }
      setState(() => _aiOneLineSummary = generated);
    } on ApiException catch (error) {
      _showMessage(error.toString());
    } catch (_) {
      _showMessage('AI 요약 생성 중 오류가 발생했습니다.');
    } finally {
      if (mounted) {
        setState(() => _isGenerating = false);
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

  Future<void> _saveFeedback(String articleId, FeedbackType type) async {
    try {
      await _briefingActionsApiService.saveFeedback(
        articleId: articleId,
        feedbackType: type,
      );
      if (!mounted) {
        return;
      }
      setState(() => _selectedFeedback = type);
      final String text = type == FeedbackType.like ? '도움이 됐어요' : '취향이 아니에요';
      _showMessage('피드백이 저장되었습니다: $text');
    } on ApiException catch (error) {
      _showMessage(error.toString());
    } catch (_) {
      _showMessage('피드백 저장 중 오류가 발생했습니다.');
    }
  }

  Future<void> _toggleBookmark(String articleId) async {
    try {
      if (_isBookmarked) {
        await _briefingActionsApiService.removeBookmark(articleId);
      } else {
        await _briefingActionsApiService.saveBookmark(articleId);
      }
      if (!mounted) {
        return;
      }
      setState(() => _isBookmarked = !_isBookmarked);
      _showMessage(_isBookmarked ? '북마크에 저장되었습니다.' : '북마크가 해제되었습니다.');
    } on ApiException catch (error) {
      _showMessage(error.toString());
    } catch (_) {
      _showMessage('북마크 처리 중 오류가 발생했습니다.');
    }
  }

  Future<void> _openOriginalUrl(String? originalUrl) async {
    if (originalUrl == null || originalUrl.isEmpty) {
      _showMessage('원문 URL이 없습니다.');
      return;
    }
    try {
      final Uri uri = Uri.parse(originalUrl);
      final bool ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (ok || !mounted) {
        return;
      }
      final ScaffoldMessengerState messenger = ScaffoldMessenger.of(context);
      messenger
        ..hideCurrentSnackBar()
        ..showSnackBar(
          SnackBar(
            content: const Text('원문을 열지 못했습니다.'),
            action: SnackBarAction(
              label: '다시 시도',
              onPressed: () => _openOriginalUrl(originalUrl),
            ),
          ),
        );
    } catch (_) {
      _showMessage('원문 URL 형식이 올바르지 않습니다.');
    }
  }

  List<String> _resolveHighlightPoints(BriefingModel item) {
    final String normalizedSummary = _normalizeText(item.summary);
    final List<String> uniqueHighlights = <String>[];
    final Set<String> seen = <String>{};
    for (final String raw in item.highlights) {
      final String point = _normalizeText(raw);
      if (point.isEmpty) {
        continue;
      }
      if (point == normalizedSummary) {
        continue;
      }
      if (seen.add(point)) {
        uniqueHighlights.add(point);
      }
    }
    if (uniqueHighlights.isNotEmpty) {
      return uniqueHighlights.take(3).toList();
    }

    final List<String> splitFromSummary = _splitSummaryToPoints(item.summary);
    if (splitFromSummary.isNotEmpty) {
      return splitFromSummary;
    }

    final String titlePoint = _normalizeText(item.title);
    if (titlePoint.isNotEmpty) {
      return <String>[titlePoint];
    }
    return <String>['핵심 내용을 불러오는 중입니다.'];
  }

  List<String> _splitSummaryToPoints(String summary) {
    final String normalized = _normalizeText(summary);
    if (normalized.isEmpty) {
      return <String>[];
    }
    final List<String> parts = normalized
        .split(RegExp(r'(?<=[.!?다])\s+|,\s+|;\s+'))
        .map(_normalizeText)
        .where((String point) => point.length >= 10)
        .toList();
    if (parts.isNotEmpty) {
      return parts.take(3).toList();
    }
    return <String>[normalized];
  }

  String _normalizeText(String value) {
    return value
        .replaceAll(RegExp(r'[\r\n]+'), ' ')
        .replaceAll(RegExp(r'\s+'), ' ')
        .trim();
  }

  BriefingModel _toUpdatedModel(BriefingModel item) {
    return item.copyWith(
      isBookmarked: _isBookmarked,
      feedbackType: _selectedFeedback == FeedbackType.like
          ? 'like'
          : _selectedFeedback == FeedbackType.dislike
          ? 'dislike'
          : null,
    );
  }

  void _popWithLatestState(BriefingModel item) {
    if (!mounted) {
      return;
    }
    context.pop(_toUpdatedModel(item));
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
      return Container(
        color: AppColors.surfaceHigh,
        alignment: Alignment.center,
        child: const Icon(Icons.image_not_supported_rounded),
      );
    }
    return Image.network(
      widget.urls[_index],
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
          return Container(
            color: AppColors.surfaceHigh,
            alignment: Alignment.center,
            child: const Icon(Icons.image_not_supported_rounded),
          );
        }
        return Container(
          color: AppColors.surfaceHigh,
          alignment: Alignment.center,
          child: const SizedBox(
            width: 24,
            height: 24,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
        );
      },
      errorBuilder: (BuildContext context, Object error, StackTrace? stackTrace) {
        if (_index >= widget.urls.length - 1) {
          return Container(
            color: AppColors.surfaceHigh,
            alignment: Alignment.center,
            child: const Icon(Icons.image_not_supported_rounded),
          );
        }
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
      },
    );
  }
}
