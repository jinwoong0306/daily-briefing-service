import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../models/briefing_model.dart';
import '../widgets/briefing_card.dart';
import '../widgets/feedback_button_widget.dart';

class BriefingFeedScreen extends StatefulWidget {
  const BriefingFeedScreen({super.key});

  @override
  State<BriefingFeedScreen> createState() => _BriefingFeedScreenState();
}

class _BriefingFeedScreenState extends State<BriefingFeedScreen> {
  static const String _allCategory = '전체';
  static const String _savedOnlyCategory = '저장됨';

  String _selectedCategory = _allCategory;
  String _searchQuery = '';
  int _selectedNavIndex = 0;

  final TextEditingController _searchController = TextEditingController();
  final Set<String> _readIds = <String>{};
  late List<BriefingModel> _briefings;

  @override
  void initState() {
    super.initState();
    _briefings = List<BriefingModel>.from(BriefingModel.mockBriefings);
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<String> get _tabs {
    final Set<String> categories = _briefings
        .map((BriefingModel e) => e.category)
        .toSet();
    return <String>[_allCategory, ...categories, _savedOnlyCategory];
    // TODO: connect API
  }

  List<BriefingModel> get _items {
    Iterable<BriefingModel> filtered = _briefings;

    if (_selectedNavIndex == 2 || _selectedCategory == _savedOnlyCategory) {
      filtered = filtered.where((BriefingModel e) => e.isBookmarked);
    } else if (_selectedCategory != _allCategory) {
      filtered = filtered.where(
        (BriefingModel e) => e.category == _selectedCategory,
      );
    }

    if (_searchQuery.trim().isNotEmpty) {
      final String query = _searchQuery.trim().toLowerCase();
      filtered = filtered.where((BriefingModel e) {
        return e.title.toLowerCase().contains(query) ||
            e.summary.toLowerCase().contains(query) ||
            e.category.toLowerCase().contains(query);
      });
    }

    if (_selectedNavIndex == 1) {
      final List<BriefingModel> sorted = filtered.toList()
        ..sort((BriefingModel a, BriefingModel b) {
          return b.publishedAt.compareTo(a.publishedAt);
        });
      return sorted;
    }

    return filtered.toList();
    // TODO: connect API
  }

  void _toggleBookmark(String id) {
    setState(() {
      _briefings = _briefings.map((BriefingModel item) {
        if (item.id != id) {
          return item;
        }
        return item.copyWith(isBookmarked: !item.isBookmarked);
      }).toList();
    });
  }

  void _markAsRead(String id) {
    setState(() {
      _readIds.add(id);
    });
  }

  void _setFeedback(String id, FeedbackType type) {
    final String next = type == FeedbackType.like ? 'like' : 'dislike';
    setState(() {
      _briefings = _briefings.map((BriefingModel item) {
        if (item.id != id) {
          return item;
        }
        return item.copyWith(feedbackType: next);
      }).toList();
    });
  }

  Future<void> _refreshFeed() async {
    // TODO: connect API
    await Future<void>.delayed(const Duration(milliseconds: 300));
    if (!mounted) {
      return;
    }
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final DateTime now = DateTime.now();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Daily Briefing'),
        actions: <Widget>[
          IconButton(
            onPressed: () {},
            icon: const Icon(Icons.search_rounded),
            tooltip: '검색',
          ),
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
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  '${now.year}.${now.month.toString().padLeft(2, '0')}.${now.day.toString().padLeft(2, '0')}',
                  style: Theme.of(
                    context,
                  ).textTheme.labelSmall?.copyWith(color: AppColors.primary),
                ),
                const SizedBox(height: 6),
                Text(
                  '좋은 아침입니다. 오늘의 브리핑입니다.',
                  style: Theme.of(
                    context,
                  ).textTheme.headlineMedium?.copyWith(fontSize: 30),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _searchController,
                  onChanged: (String value) {
                    setState(() {
                      _searchQuery = value;
                    });
                  },
                  decoration: InputDecoration(
                    hintText: '브리핑 검색',
                    prefixIcon: const Icon(Icons.search_rounded),
                    suffixIcon: _searchQuery.isEmpty
                        ? null
                        : IconButton(
                            onPressed: () {
                              setState(() {
                                _searchQuery = '';
                                _searchController.clear();
                              });
                            },
                            icon: const Icon(Icons.close_rounded),
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
                          setState(() {
                            _selectedCategory = tab;
                            if (tab == _savedOnlyCategory) {
                              _selectedNavIndex = 2;
                            } else if (_selectedNavIndex == 2) {
                              _selectedNavIndex = 0;
                            }
                          });
                        },
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 4),
          Expanded(
            child: _items.isEmpty
                ? _EmptyFeed(category: _selectedCategory)
                : RefreshIndicator(
                    onRefresh: _refreshFeed,
                    child: ListView.separated(
                      padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
                      itemCount: _items.length,
                      separatorBuilder: (BuildContext context, int index) =>
                          const SizedBox(height: 16),
                      itemBuilder: (BuildContext context, int index) {
                        final BriefingModel item = _items[index];
                        return BriefingCard(
                          item: item,
                          isRead: _readIds.contains(item.id),
                          onTap: () {
                            _markAsRead(item.id);
                            context.go('/briefing/${item.id}', extra: item);
                          },
                          onBookmarkToggle: () => _toggleBookmark(item.id),
                          onFeedback: (FeedbackType type) {
                            _setFeedback(item.id, type);
                            final String text = type == FeedbackType.like
                                ? '도움이 됐어요'
                                : '취향이 아니에요';
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text('피드백이 저장되었습니다: $text')),
                            );
                          },
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
          if (index == 0) {
            setState(() {
              _selectedNavIndex = 0;
              if (_selectedCategory == _savedOnlyCategory) {
                _selectedCategory = _allCategory;
              }
            });
            return;
          }
          if (index == 1) {
            setState(() {
              _selectedNavIndex = 1;
              if (_selectedCategory == _savedOnlyCategory) {
                _selectedCategory = _allCategory;
              }
            });
            return;
          }
          if (index == 2) {
            setState(() {
              _selectedNavIndex = 2;
              _selectedCategory = _savedOnlyCategory;
            });
            return;
          }
          if (index == 3) {
            context.go('/settings');
          }
        },
        destinations: const <NavigationDestination>[
          NavigationDestination(icon: Icon(Icons.home_rounded), label: '홈'),
          NavigationDestination(icon: Icon(Icons.explore_rounded), label: '탐색'),
          NavigationDestination(icon: Icon(Icons.bookmark_rounded), label: '저장'),
          NavigationDestination(icon: Icon(Icons.settings_rounded), label: '설정'),
        ],
      ),
    );
  }
}

class _EmptyFeed extends StatelessWidget {
  const _EmptyFeed({required this.category});

  final String category;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
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
              '다른 카테고리를 선택해 보세요.',
              style: Theme.of(context).textTheme.bodyMedium,
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
