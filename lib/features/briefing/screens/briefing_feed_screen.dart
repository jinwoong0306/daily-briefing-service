import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../services/api_exception.dart';
import '../../../services/briefing_actions_api_service.dart';
import '../../../services/briefings_api_service.dart';
import '../../../services/keywords_api_service.dart';
import '../models/briefing_model.dart';
import '../widgets/briefing_card.dart';
import '../widgets/feedback_button_widget.dart';

enum _SavedSortOption { latest, readTimeAsc, categoryAsc }

class BriefingFeedScreen extends StatefulWidget {
  const BriefingFeedScreen({super.key});

  @override
  State<BriefingFeedScreen> createState() => _BriefingFeedScreenState();
}

class _BriefingFeedScreenState extends State<BriefingFeedScreen> {
  static const double _horizontalInset = 22;
  static const FlutterSecureStorage _storage = FlutterSecureStorage();
  static const String _collapsedKeywordsStorageKey =
      'briefing_collapsed_keywords';
  static const String _readArticleIdsStorageKey = 'briefing_read_article_ids';

  final BriefingsApiService _briefingsApiService = BriefingsApiService();
  final BriefingActionsApiService _briefingActionsApiService =
      BriefingActionsApiService();
  final KeywordsApiService _keywordsApiService = KeywordsApiService();
  String _selectedCategory = '전체';
  bool _isLoading = true;
  String? _errorMessage;
  List<BriefingModel> _briefings = <BriefingModel>[];
  List<BriefingKeywordSectionModel> _groupedSections =
      <BriefingKeywordSectionModel>[];
  final Set<String> _collapsedKeywords = <String>{};
  final Set<String> _readArticleIds = <String>{};
  List<String> _preferredKeywordOrder = <String>[];
  int _selectedNavIndex = 0;
  _SavedSortOption _savedSortOption = _SavedSortOption.latest;
  String _savedSearchQuery = '';
  final TextEditingController _savedSearchController =
      TextEditingController();
  String? _lastAppliedRouteTab;

  @override
  void initState() {
    super.initState();
    _loadCollapsedKeywords();
    _loadReadArticleIds();
    _loadBriefings();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final String? routeTab = GoRouterState.of(context).uri.queryParameters['tab'];
    if (routeTab == null || routeTab == _lastAppliedRouteTab) {
      return;
    }
    _lastAppliedRouteTab = routeTab;
    _applyRouteTab(routeTab);
  }

  @override
  void dispose() {
    _savedSearchController.dispose();
    super.dispose();
  }

  List<String> get _tabs {
    if (_selectedNavIndex == 0 && _groupedSections.isNotEmpty) {
      final List<String> ordered = <String>[];
      final Set<String> seen = <String>{};
      for (final BriefingKeywordSectionModel section in _groupedSections) {
        final String keyword = section.keyword.trim();
        if (keyword.isEmpty || seen.contains(keyword)) {
          continue;
        }
        seen.add(keyword);
        ordered.add(keyword);
      }
      final List<String> remaining = _groupedSections
          .expand((BriefingKeywordSectionModel s) => s.items)
          .map((BriefingModel e) => e.category)
          .followedBy(
            _groupedSections.map((BriefingKeywordSectionModel s) => s.keyword),
          )
          .where((String category) => !seen.contains(category))
          .toSet()
          .toList()
        ..sort();
      return <String>['전체', ...ordered, ...remaining];
    }

    if (_selectedNavIndex == 0 &&
        _groupedSections.isEmpty &&
        _preferredKeywordOrder.isNotEmpty) {
      return <String>['전체', ..._preferredKeywordOrder];
    }

    final List<String> categories = _briefings
        .map((BriefingModel e) => e.category)
        .toSet()
        .toList()
      ..sort();
    return <String>['전체', ...categories];
  }

  List<BriefingModel> get _items {
    final List<BriefingModel> categoryFiltered = _selectedCategory == '전체'
        ? _briefings
        : _briefings
        .where((BriefingModel e) => e.category == _selectedCategory)
        .toList();

    if (_selectedNavIndex != 2) {
      return categoryFiltered;
    }

    final String query = _savedSearchQuery.trim().toLowerCase();
    final List<BriefingModel> searchFiltered = query.isEmpty
        ? categoryFiltered
        : categoryFiltered.where((BriefingModel item) {
            final String title = item.title.toLowerCase();
            final String source = item.sourceName.toLowerCase();
            return title.contains(query) || source.contains(query);
          }).toList();

    final List<BriefingModel> sorted = List<BriefingModel>.from(searchFiltered);
    switch (_savedSortOption) {
      case _SavedSortOption.latest:
        sorted.sort(
          (BriefingModel a, BriefingModel b) =>
              b.publishedAt.compareTo(a.publishedAt),
        );
        break;
      case _SavedSortOption.readTimeAsc:
        sorted.sort(
          (BriefingModel a, BriefingModel b) =>
              a.readTimeMinutes.compareTo(b.readTimeMinutes),
        );
        break;
      case _SavedSortOption.categoryAsc:
        sorted.sort((BriefingModel a, BriefingModel b) {
          final int byCategory = a.category.compareTo(b.category);
          if (byCategory != 0) {
            return byCategory;
          }
          return b.publishedAt.compareTo(a.publishedAt);
        });
        break;
    }
    return sorted;
  }

  List<BriefingKeywordSectionModel> get _homeSections {
    if (_selectedNavIndex != 0 || _groupedSections.isEmpty) {
      return <BriefingKeywordSectionModel>[];
    }
    if (_selectedCategory == '전체') {
      return _groupedSections;
    }
    return _groupedSections
        .where((BriefingKeywordSectionModel section) {
          if (section.keyword == _selectedCategory) {
            return true;
          }
          return section.items.any(
            (BriefingModel item) => item.category == _selectedCategory,
          );
        })
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    final DateTime now = DateTime.now();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Daily Briefing'),
        actions: <Widget>[
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: CircleAvatar(
              radius: 16,
              backgroundColor: AppColors.surfaceHigh,
              child: const Icon(Icons.person_rounded, size: 18),
            ),
          ),
        ],
      ),
      body: Column(
        children: <Widget>[
          Padding(
            padding: const EdgeInsets.fromLTRB(_horizontalInset, 10, _horizontalInset, 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  '${now.year}.${now.month.toString().padLeft(2, '0')}.${now.day.toString().padLeft(2, '0')}',
                  style: Theme.of(
                    context,
                  ).textTheme.labelSmall?.copyWith(color: AppColors.primary),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 6),
                Center(
                  child: Text(
                    '좋은 아침입니다,\n오늘의 Daily Briefing 입니다.',
                    textAlign: TextAlign.center,
                    style: Theme.of(
                      context,
                    ).textTheme.headlineMedium?.copyWith(
                      fontSize: 27,
                      height: 1.24,
                    ),
                  ),
                ),
                const SizedBox(height: 14),
                SizedBox(
                  height: 42,
                  child: ListView.separated(
                    scrollDirection: Axis.horizontal,
                    itemCount: _tabs.length,
                    separatorBuilder: (BuildContext context, int index) =>
                        const SizedBox(width: 8),
                    itemBuilder: (BuildContext context, int index) {
                      final String tab = _tabs[index];
                      final bool selected = _selectedCategory == tab;
                      return ChoiceChip(
                        label: Text(tab),
                        selected: selected,
                        showCheckmark: false,
                        onSelected: (_) {
                          setState(() => _selectedCategory = tab);
                        },
                      );
                    },
                  ),
                ),
                if (_selectedNavIndex == 0 && _homeSections.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 8),
                  Row(
                    children: <Widget>[
                      Text(
                        '섹션 ${_homeSections.length}개',
                        style: Theme.of(context).textTheme.labelMedium?.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                      const Spacer(),
                      TextButton(
                        onPressed: _expandAllSections,
                        child: const Text('전체 펼치기'),
                      ),
                      TextButton(
                        onPressed: _collapseAllSections,
                        child: const Text('전체 접기'),
                      ),
                    ],
                  ),
                ],
                if (_selectedNavIndex == 2) ...<Widget>[
                  const SizedBox(height: 10),
                  TextField(
                    controller: _savedSearchController,
                    onChanged: (String value) {
                      setState(() => _savedSearchQuery = value);
                    },
                    decoration: InputDecoration(
                      prefixIcon: const Icon(Icons.search_rounded),
                      hintText: '저장한 브리핑 검색 (제목/출처)',
                      suffixIcon: _savedSearchQuery.isEmpty
                          ? null
                          : IconButton(
                              onPressed: () {
                                _savedSearchController.clear();
                                setState(() => _savedSearchQuery = '');
                              },
                              icon: const Icon(Icons.close_rounded),
                              tooltip: '검색어 지우기',
                            ),
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    '검색 결과 ${_items.length}건',
                    style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: <Widget>[
                      Text(
                        '정렬',
                        style: Theme.of(context).textTheme.labelMedium,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: SingleChildScrollView(
                          scrollDirection: Axis.horizontal,
                          child: Row(
                            children: <Widget>[
                              ChoiceChip(
                                label: const Text('최신순'),
                                selected:
                                    _savedSortOption == _SavedSortOption.latest,
                                showCheckmark: false,
                                onSelected: (_) {
                                  setState(
                                    () => _savedSortOption =
                                        _SavedSortOption.latest,
                                  );
                                },
                              ),
                              const SizedBox(width: 8),
                              ChoiceChip(
                                label: const Text('읽기시간 짧은순'),
                                selected: _savedSortOption ==
                                    _SavedSortOption.readTimeAsc,
                                showCheckmark: false,
                                onSelected: (_) {
                                  setState(
                                    () => _savedSortOption =
                                        _SavedSortOption.readTimeAsc,
                                  );
                                },
                              ),
                              const SizedBox(width: 8),
                              ChoiceChip(
                                label: const Text('카테고리순'),
                                selected: _savedSortOption ==
                                    _SavedSortOption.categoryAsc,
                                showCheckmark: false,
                                onSelected: (_) {
                                  setState(
                                    () => _savedSortOption =
                                        _SavedSortOption.categoryAsc,
                                  );
                                },
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 4),
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _errorMessage != null
                ? _ErrorFeed(
                    message: _errorMessage!,
                    onRetry: _loadBriefings,
                    onRefresh: _onRefreshCurrentTab,
                  )
                : _homeSections.isNotEmpty
                ? RefreshIndicator(
                    onRefresh: _onRefreshCurrentTab,
                    child: ListView.separated(
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.fromLTRB(
                        _horizontalInset,
                        8,
                        _horizontalInset,
                        24,
                      ),
                      itemCount: _homeSections.length,
                      separatorBuilder: (BuildContext context, int index) =>
                          const SizedBox(height: 16),
                      itemBuilder: (BuildContext context, int index) {
                        final BriefingKeywordSectionModel section =
                            _homeSections[index];
                        return _KeywordSectionCard(
                          section: section,
                          collapsed: _collapsedKeywords.contains(section.keyword),
                          readArticleIds: _readArticleIds,
                          onToggleCollapse: () => _toggleSection(section.keyword),
                          onOpen: _openDetail,
                          onFeedback: _submitFeedback,
                          onBookmarkToggle: _toggleBookmark,
                        );
                      },
                    ),
                  )
                : _items.isEmpty
                ? _EmptyFeed(
                    category: _selectedCategory,
                    onRefresh: _onRefreshCurrentTab,
                  )
                : RefreshIndicator(
                    onRefresh: _onRefreshCurrentTab,
                    child: ListView.separated(
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.fromLTRB(
                        _horizontalInset,
                        8,
                        _horizontalInset,
                        24,
                      ),
                      itemCount: _items.length,
                      separatorBuilder: (BuildContext context, int index) =>
                          const SizedBox(height: 16),
                      itemBuilder: (BuildContext context, int index) {
                        final BriefingModel item = _items[index];
                        return BriefingCard(
                          item: item,
                          isRead: _readArticleIds.contains(item.id),
                          onTap: () => _openDetail(item),
                          onFeedback: (FeedbackType type) =>
                              _submitFeedback(item, type),
                          onBookmarkToggle: () => _toggleBookmark(item),
                        );
                      },
                    ),
                  ),
          ),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedNavIndex,
        onDestinationSelected: (int index) {
          if (index == 3) {
            context.go('/settings');
            return;
          }
          setState(() => _selectedNavIndex = index);
          if (index == 2) {
            _loadBookmarkedBriefings();
            return;
          }
          if (index == 0) {
            _loadBriefings();
          }
        },
        destinations: const <NavigationDestination>[
          NavigationDestination(icon: Icon(Icons.home_rounded), label: '홈'),
          NavigationDestination(icon: Icon(Icons.explore_rounded), label: '탐색'),
          NavigationDestination(
            icon: Icon(Icons.bookmark_rounded),
            label: '저장',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_rounded),
            label: '설정',
          ),
        ],
      ),
    );
  }

  Future<void> _loadBriefings() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      List<BriefingKeywordSectionModel> groupedResponse =
          <BriefingKeywordSectionModel>[];
      try {
        groupedResponse = await _briefingsApiService.getTodayBriefingsGrouped();
      } on ApiException {
        groupedResponse = <BriefingKeywordSectionModel>[];
      }

      try {
        final KeywordsResponseModel keywordsResponse = await _keywordsApiService
            .getKeywords();
        _preferredKeywordOrder = keywordsResponse.keywords;
      } on ApiException {
        _preferredKeywordOrder = <String>[];
      } catch (_) {
        _preferredKeywordOrder = <String>[];
      }

      groupedResponse = _sortSectionsByPreference(groupedResponse);
      final List<BriefingModel> response = groupedResponse
          .expand((BriefingKeywordSectionModel section) => section.items)
          .toList();
      final List<BriefingModel> fallbackResponse = response.isNotEmpty
          ? response
          : await _briefingsApiService.getTodayBriefingsLegacy();
      if (!mounted) {
        return;
      }
      setState(() {
        _groupedSections = groupedResponse;
        _briefings = fallbackResponse;
        _collapsedKeywords.removeWhere(
          (String keyword) => !_groupedSections.any(
            (BriefingKeywordSectionModel section) => section.keyword == keyword,
          ),
        );
        if (!_tabs.contains(_selectedCategory)) {
          _selectedCategory = '전체';
        }
      });
      unawaited(_persistCollapsedKeywords());
    } on ApiException catch (error) {
      if (!mounted) {
        return;
      }
      setState(() => _errorMessage = error.toString());
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() => _errorMessage = '브리핑을 불러오지 못했습니다.');
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _loadBookmarkedBriefings() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _selectedCategory = '전체';
    });
    try {
      final List<BriefingModel> response = await _briefingsApiService
          .getBookmarkedBriefings();
      if (!mounted) {
        return;
      }
      setState(() {
        _groupedSections = <BriefingKeywordSectionModel>[];
        _briefings = response;
      });
    } on ApiException catch (error) {
      if (!mounted) {
        return;
      }
      setState(() => _errorMessage = error.toString());
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() => _errorMessage = '저장된 브리핑을 불러오지 못했습니다.');
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _submitFeedback(BriefingModel item, FeedbackType type) async {
    try {
      await _briefingActionsApiService.saveFeedback(
        articleId: item.id,
        feedbackType: type,
      );
      final String text = type == FeedbackType.like ? '도움이 됐어요' : '취향이 아니에요';
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('피드백이 저장되었습니다: $text')));
      _refreshItem(
        item.id,
        (BriefingModel current) => current.copyWith(
          feedbackType: type == FeedbackType.like ? 'like' : 'dislike',
        ),
      );
    } on ApiException catch (error) {
      _showMessage(error.toString());
    } catch (_) {
      _showMessage('피드백 저장 중 오류가 발생했습니다.');
    }
  }

  Future<void> _toggleBookmark(BriefingModel item) async {
    try {
      if (item.isBookmarked) {
        await _briefingActionsApiService.removeBookmark(item.id);
      } else {
        await _briefingActionsApiService.saveBookmark(item.id);
      }
      if (_selectedNavIndex == 2 && item.isBookmarked) {
        setState(() {
          _briefings = _briefings
              .where((BriefingModel e) => e.id != item.id)
              .toList();
          _groupedSections = _groupedSections
              .map((BriefingKeywordSectionModel section) {
                return BriefingKeywordSectionModel(
                  keyword: section.keyword,
                  headline: section.headline,
                  summary: section.summary,
                  items: section.items
                      .where((BriefingModel e) => e.id != item.id)
                      .toList(),
                );
              })
              .where((BriefingKeywordSectionModel section) => section.items.isNotEmpty)
              .toList();
        });
      } else {
        _refreshItem(
          item.id,
          (BriefingModel current) =>
              current.copyWith(isBookmarked: !current.isBookmarked),
        );
      }
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(item.isBookmarked ? '북마크가 해제되었습니다.' : '북마크에 저장되었습니다.')),
      );
    } on ApiException catch (error) {
      _showMessage(error.toString());
    } catch (_) {
      _showMessage('북마크 처리 중 오류가 발생했습니다.');
    }
  }

  void _refreshItem(
    String id,
    BriefingModel Function(BriefingModel current) builder,
  ) {
    if (!mounted) {
      return;
    }
    setState(() {
      _briefings = _briefings
          .map((BriefingModel item) => item.id == id ? builder(item) : item)
          .toList();
      _groupedSections = _groupedSections
          .map((BriefingKeywordSectionModel section) {
            return BriefingKeywordSectionModel(
              keyword: section.keyword,
              headline: section.headline,
              summary: section.summary,
              items: section.items
                  .map((BriefingModel item) => item.id == id ? builder(item) : item)
                  .toList(),
            );
          })
          .toList();
    });
  }

  Future<void> _openDetail(BriefingModel item) async {
    _markAsRead(item.id);
    final dynamic result = await context.push(
      '/briefing/${item.id}',
      extra: item,
    );
    if (result is BriefingModel) {
      _refreshItem(item.id, (_) => result);
    }
  }

  void _showMessage(String message) {
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  void _toggleSection(String keyword) {
    setState(() {
      if (_collapsedKeywords.contains(keyword)) {
        _collapsedKeywords.remove(keyword);
      } else {
        _collapsedKeywords.add(keyword);
      }
    });
    unawaited(_persistCollapsedKeywords());
  }

  void _expandAllSections() {
    setState(() {
      _collapsedKeywords.clear();
    });
    unawaited(_persistCollapsedKeywords());
  }

  void _collapseAllSections() {
    setState(() {
      _collapsedKeywords
        ..clear()
        ..addAll(
          _groupedSections.map((BriefingKeywordSectionModel s) => s.keyword),
        );
    });
    unawaited(_persistCollapsedKeywords());
  }

  Future<void> _onRefreshCurrentTab() async {
    if (_selectedNavIndex == 2) {
      await _loadBookmarkedBriefings();
      return;
    }
    await _loadBriefings();
  }

  Future<void> _loadCollapsedKeywords() async {
    try {
      final String? raw = await _storage.read(key: _collapsedKeywordsStorageKey);
      if (raw == null || raw.isEmpty) {
        return;
      }
      final dynamic decoded = jsonDecode(raw);
      if (decoded is! List) {
        return;
      }
      if (!mounted) {
        return;
      }
      setState(() {
        _collapsedKeywords
          ..clear()
          ..addAll(decoded.whereType<String>());
      });
    } catch (_) {}
  }

  Future<void> _persistCollapsedKeywords() async {
    final String encoded = jsonEncode(_collapsedKeywords.toList());
    await _storage.write(key: _collapsedKeywordsStorageKey, value: encoded);
  }

  Future<void> _loadReadArticleIds() async {
    try {
      final String? raw = await _storage.read(key: _readArticleIdsStorageKey);
      if (raw == null || raw.isEmpty) {
        return;
      }
      final dynamic decoded = jsonDecode(raw);
      if (decoded is! List) {
        return;
      }
      if (!mounted) {
        return;
      }
      setState(() {
        _readArticleIds
          ..clear()
          ..addAll(decoded.whereType<String>());
      });
    } catch (_) {}
  }

  Future<void> _persistReadArticleIds() async {
    final List<String> ids = _readArticleIds.toList();
    if (ids.length > 500) {
      ids.removeRange(0, ids.length - 500);
    }
    await _storage.write(
      key: _readArticleIdsStorageKey,
      value: jsonEncode(ids),
    );
  }

  void _markAsRead(String articleId) {
    if (articleId.isEmpty || _readArticleIds.contains(articleId)) {
      return;
    }
    setState(() {
      _readArticleIds.add(articleId);
    });
    unawaited(_persistReadArticleIds());
  }

  List<BriefingKeywordSectionModel> _sortSectionsByPreference(
    List<BriefingKeywordSectionModel> sections,
  ) {
    if (sections.isEmpty || _preferredKeywordOrder.isEmpty) {
      return sections;
    }
    final Map<String, int> priorityIndex = <String, int>{
      for (int i = 0; i < _preferredKeywordOrder.length; i++)
        _preferredKeywordOrder[i]: i,
    };
    final List<BriefingKeywordSectionModel> sorted =
        List<BriefingKeywordSectionModel>.from(sections);
    sorted.sort((BriefingKeywordSectionModel a, BriefingKeywordSectionModel b) {
      final int? aIndex = priorityIndex[a.keyword];
      final int? bIndex = priorityIndex[b.keyword];
      if (aIndex != null && bIndex != null) {
        return aIndex.compareTo(bIndex);
      }
      if (aIndex != null) {
        return -1;
      }
      if (bIndex != null) {
        return 1;
      }
      return a.keyword.compareTo(b.keyword);
    });
    return sorted;
  }

  void _applyRouteTab(String routeTab) {
    final String normalized = routeTab.trim().toLowerCase();
    final int nextIndex;
    switch (normalized) {
      case 'home':
        nextIndex = 0;
        break;
      case 'explore':
        nextIndex = 1;
        break;
      case 'saved':
        nextIndex = 2;
        break;
      default:
        return;
    }
    if (_selectedNavIndex == nextIndex) {
      return;
    }
    setState(() {
      _selectedNavIndex = nextIndex;
      _selectedCategory = '전체';
    });
    if (nextIndex == 2) {
      _loadBookmarkedBriefings();
      return;
    }
    _loadBriefings();
  }
}

class _EmptyFeed extends StatelessWidget {
  const _EmptyFeed({required this.category, required this.onRefresh});

  final String category;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: onRefresh,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: <Widget>[
          Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                const Icon(
                  Icons.inbox_outlined,
                  size: 44,
                  color: AppColors.textSecondary,
                ),
                const SizedBox(height: 12),
                Text(
                  '$category 카테고리의 브리핑이 없습니다.',
                  style: Theme.of(context).textTheme.titleLarge,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 6),
                Text(
                  '아래로 당겨 새로고침하거나 다른 카테고리를 선택해 보세요.',
                  style: Theme.of(context).textTheme.bodyMedium,
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ErrorFeed extends StatelessWidget {
  const _ErrorFeed({
    required this.message,
    required this.onRetry,
    required this.onRefresh,
  });

  final String message;
  final VoidCallback onRetry;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: onRefresh,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: <Widget>[
          Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                const Icon(
                  Icons.error_outline_rounded,
                  size: 42,
                  color: AppColors.error,
                ),
                const SizedBox(height: 12),
                Text(message, textAlign: TextAlign.center),
                const SizedBox(height: 12),
                FilledButton(
                  onPressed: onRetry,
                  child: const Text('다시 시도'),
                ),
                const SizedBox(height: 8),
                Text(
                  '아래로 당겨 새로고침할 수 있습니다.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _KeywordSectionCard extends StatelessWidget {
  const _KeywordSectionCard({
    required this.section,
    required this.collapsed,
    required this.readArticleIds,
    required this.onToggleCollapse,
    required this.onOpen,
    required this.onFeedback,
    required this.onBookmarkToggle,
  });

  final BriefingKeywordSectionModel section;
  final bool collapsed;
  final Set<String> readArticleIds;
  final VoidCallback onToggleCollapse;
  final Future<void> Function(BriefingModel item) onOpen;
  final Future<void> Function(BriefingModel item, FeedbackType type) onFeedback;
  final Future<void> Function(BriefingModel item) onBookmarkToggle;

  @override
  Widget build(BuildContext context) {
    final int freshCount = _freshItemCount();
    final DateTime? lastUpdated = _lastUpdatedAt();
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFE7ECF5)),
        boxShadow: const <BoxShadow>[
          BoxShadow(
            color: Color(0x12282B51),
            blurRadius: 18,
            offset: Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Row(
                  children: <Widget>[
                    Text(
                      section.keyword,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: AppColors.primary.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Text(
                        '${section.items.length}',
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: AppColors.primaryDark,
                        ),
                      ),
                    ),
                    if (freshCount > 0) ...<Widget>[
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: AppColors.error.withValues(alpha: 0.14),
                          borderRadius: BorderRadius.circular(999),
                        ),
                        child: Text(
                          'NEW $freshCount',
                          style: Theme.of(
                            context,
                          ).textTheme.labelSmall?.copyWith(
                            color: AppColors.error,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              TextButton.icon(
                onPressed: onToggleCollapse,
                icon: Icon(
                  collapsed
                      ? Icons.keyboard_arrow_down_rounded
                      : Icons.keyboard_arrow_up_rounded,
                ),
                label: Text(collapsed ? '펼치기' : '접기'),
              ),
            ],
          ),
          if (lastUpdated != null) ...<Widget>[
            Text(
              '업데이트 ${_formatUpdated(lastUpdated)}',
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(height: 4),
          ],
          if (section.headline.isNotEmpty) ...<Widget>[
            const SizedBox(height: 6),
            Text(
              section.headline,
              style: Theme.of(
                context,
              ).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600),
            ),
          ],
          if (section.summary.isNotEmpty) ...<Widget>[
            const SizedBox(height: 6),
            Text(
              section.summary,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
            ),
          ],
          if (!collapsed) ...<Widget>[
            const SizedBox(height: 10),
            if (section.items.isEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text(
                  '표시할 기사가 없습니다.',
                  style: Theme.of(
                    context,
                  ).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
                ),
              ),
            ...section.items.map((BriefingModel item) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: BriefingCard(
                  item: item,
                  isRead: readArticleIds.contains(item.id),
                  onTap: () => onOpen(item),
                  onFeedback: (FeedbackType type) => onFeedback(item, type),
                  onBookmarkToggle: () => onBookmarkToggle(item),
                ),
              );
            }),
          ],
        ],
      ),
    );
  }

  int _freshItemCount() {
    final DateTime threshold = DateTime.now().subtract(
      const Duration(hours: 12),
    );
    return section.items
        .where((BriefingModel item) => item.publishedAt.isAfter(threshold))
        .length;
  }

  DateTime? _lastUpdatedAt() {
    if (section.items.isEmpty) {
      return null;
    }
    final List<DateTime> sorted = section.items
        .map((BriefingModel item) => item.publishedAt)
        .toList()
      ..sort((DateTime a, DateTime b) => b.compareTo(a));
    return sorted.first;
  }

  String _formatUpdated(DateTime value) {
    final String hh = value.hour.toString().padLeft(2, '0');
    final String mm = value.minute.toString().padLeft(2, '0');
    return '$hh:$mm';
  }
}
