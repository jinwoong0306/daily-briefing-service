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
  String _selectedCategory = '전체';

  List<String> get _tabs {
    final Set<String> categories = BriefingModel.mockBriefings
        .map((BriefingModel e) => e.category)
        .toSet();
    return <String>['전체', ...categories];
    // TODO: connect API
  }

  List<BriefingModel> get _items {
    if (_selectedCategory == '전체') {
      return BriefingModel.mockBriefings;
    }
    return BriefingModel.mockBriefings
        .where((BriefingModel e) => e.category == _selectedCategory)
        .toList();
    // TODO: connect API
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
              ],
            ),
          ),
          const SizedBox(height: 4),
          Expanded(
            child: _items.isEmpty
                ? _EmptyFeed(category: _selectedCategory)
                : ListView.separated(
                    padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
                    itemCount: _items.length,
                    separatorBuilder: (BuildContext context, int index) =>
                        const SizedBox(height: 16),
                    itemBuilder: (BuildContext context, int index) {
                      final BriefingModel item = _items[index];
                      return BriefingCard(
                        item: item,
                        onTap: () => context.go('/briefing/${item.id}'),
                        onFeedback: (FeedbackType type) {
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
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: 0,
        onDestinationSelected: (int index) {
          if (index == 3) {
            context.go('/settings');
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
