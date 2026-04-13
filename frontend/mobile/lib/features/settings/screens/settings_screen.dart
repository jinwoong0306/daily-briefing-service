import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/primary_button_widget.dart';
import '../models/notification_settings_model.dart';
import '../widgets/notification_status_card.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  NotificationSettingsModel _settings = const NotificationSettingsModel(
    pushEnabled: true,
    morningBriefingEnabled: true,
    weekendEnabled: false,
    onlyImportantEnabled: true,
    hour: 8,
    minute: 0,
    isAm: true,
    permissionStatus: '허용됨',
    fcmLinked: true,
  );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          onPressed: () => context.go('/briefing'),
          icon: const Icon(Icons.arrow_back_ios_new_rounded),
        ),
        title: const Text('수신 및 알림 설정'),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
        children: <Widget>[
          Text(
            '브리핑 수신 기본 설정',
            style: Theme.of(
              context,
            ).textTheme.headlineMedium?.copyWith(fontSize: 28),
          ),
          const SizedBox(height: 8),
          Text(
            'US-004 기준으로 아침 브리핑 수신 설정과 알림 상태를 관리합니다.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(18),
            ),
            child: Column(
              children: <Widget>[
                _SettingSwitchTile(
                  title: '푸시 알림',
                  subtitle: '브리핑 및 시스템 알림을 수신합니다.',
                  value: _settings.pushEnabled,
                  onChanged: (bool value) {
                    setState(() {
                      _settings = _settings.copyWith(pushEnabled: value);
                    });
                  },
                ),
                const Divider(height: 24),
                _SettingSwitchTile(
                  title: '아침 브리핑 자동 수신',
                  subtitle: '설정한 시간에 요약 브리핑을 받습니다.',
                  value: _settings.morningBriefingEnabled,
                  onChanged: (bool value) {
                    setState(() {
                      _settings = _settings.copyWith(
                        morningBriefingEnabled: value,
                      );
                    });
                  },
                ),
                const Divider(height: 24),
                _SettingSwitchTile(
                  title: '주말 브리핑 수신',
                  subtitle: '토/일에도 브리핑을 받습니다.',
                  value: _settings.weekendEnabled,
                  onChanged: (bool value) {
                    setState(() {
                      _settings = _settings.copyWith(weekendEnabled: value);
                    });
                  },
                ),
                const Divider(height: 24),
                _SettingSwitchTile(
                  title: '핵심 뉴스만 받기',
                  subtitle: '중요도 높은 브리핑만 우선 제공합니다.',
                  value: _settings.onlyImportantEnabled,
                  onChanged: (bool value) {
                    setState(() {
                      _settings = _settings.copyWith(
                        onlyImportantEnabled: value,
                      );
                    });
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(18),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  '브리핑 수신 시간',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 6),
                Text(
                  '알림 시간 상세 설정은 Step 4에서 확장됩니다.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 12),
                Row(
                  children: <Widget>[
                    Expanded(
                      child: _DropdownTimeField(
                        label: '시',
                        value: _settings.hour,
                        items: List<int>.generate(12, (int i) => i + 1),
                        onChanged: (int value) {
                          setState(() {
                            _settings = _settings.copyWith(hour: value);
                          });
                        },
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: _DropdownTimeField(
                        label: '분',
                        value: _settings.minute,
                        items: List<int>.generate(6, (int i) => i * 10),
                        onChanged: (int value) {
                          setState(() {
                            _settings = _settings.copyWith(minute: value);
                          });
                        },
                      ),
                    ),
                    const SizedBox(width: 8),
                    SegmentedButton<bool>(
                      segments: const <ButtonSegment<bool>>[
                        ButtonSegment<bool>(value: true, label: Text('AM')),
                        ButtonSegment<bool>(value: false, label: Text('PM')),
                      ],
                      selected: <bool>{_settings.isAm},
                      onSelectionChanged: (Set<bool> value) {
                        setState(() {
                          _settings = _settings.copyWith(isAm: value.first);
                        });
                      },
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          NotificationStatusCard(
            permissionStatus: _settings.permissionStatus,
            fcmLinked: _settings.fcmLinked,
            onRequestPermission: () {
              setState(() {
                _settings = _settings.copyWith(
                  permissionStatus: '요청됨',
                  fcmLinked: true,
                );
              });
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('알림 권한 요청 UI가 표시되었습니다.')),
              );
            },
          ),
          const SizedBox(height: 20),
          PrimaryButtonWidget(
            label: '설정 저장',
            onPressed: () {
              ScaffoldMessenger.of(
                context,
              ).showSnackBar(const SnackBar(content: Text('설정이 저장되었습니다.')));
            },
          ),
          const SizedBox(height: 10),
          Text(
            'UI-003: FCM 연동은 백엔드/실서비스 설정 단계에서 활성화됩니다.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          // TODO: connect API
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: 3,
        onDestinationSelected: (int index) {
          if (index == 0) {
            context.go('/briefing');
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

class _SettingSwitchTile extends StatelessWidget {
  const _SettingSwitchTile({
    required this.title,
    required this.subtitle,
    required this.value,
    required this.onChanged,
  });

  final String title;
  final String subtitle;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                title,
                style: Theme.of(
                  context,
                ).textTheme.titleLarge?.copyWith(fontSize: 18),
              ),
              const SizedBox(height: 4),
              Text(subtitle, style: Theme.of(context).textTheme.bodyMedium),
            ],
          ),
        ),
        const SizedBox(width: 8),
        Switch(value: value, onChanged: onChanged),
      ],
    );
  }
}

class _DropdownTimeField extends StatelessWidget {
  const _DropdownTimeField({
    required this.label,
    required this.value,
    required this.items,
    required this.onChanged,
  });

  final String label;
  final int value;
  final List<int> items;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.surfaceLow,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.labelSmall),
          const Spacer(),
          DropdownButton<int>(
            value: value,
            underline: const SizedBox.shrink(),
            items: items
                .map(
                  (int item) => DropdownMenuItem<int>(
                    value: item,
                    child: Text(item.toString().padLeft(2, '0')),
                  ),
                )
                .toList(),
            onChanged: (int? next) {
              if (next != null) {
                onChanged(next);
              }
            },
          ),
        ],
      ),
    );
  }
}
