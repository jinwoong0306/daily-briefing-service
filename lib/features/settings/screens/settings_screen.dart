import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../services/api_exception.dart';
import '../../../services/keywords_api_service.dart';
import '../../../services/local_notification_service.dart';
import '../../../services/notification_settings_api_service.dart';
import '../../../services/session_store.dart';
import '../../onboarding/widgets/keyword_chip_widget.dart';
import '../../../shared/widgets/primary_button_widget.dart';
import '../models/notification_settings_model.dart';
import '../widgets/notification_status_card.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final NotificationSettingsApiService _notificationApiService =
      NotificationSettingsApiService();
  final KeywordsApiService _keywordsApiService = KeywordsApiService();
  final LocalNotificationService _localNotificationService =
      LocalNotificationService();
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

  Set<String> _selectedKeywords = <String>{};
  String? _keywordsVersion;
  NotificationSettingsModel _settings = const NotificationSettingsModel(
    pushEnabled: true,
    morningBriefingEnabled: true,
    hour: 8,
    minute: 0,
    isAm: true,
    permissionStatus: '허용됨',
    fcmLinked: false,
    timezone: 'Asia/Seoul',
    version: '',
  );
  bool _isLoading = true;
  bool _isSaving = false;
  bool _isKeywordSaving = false;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          onPressed: () => context.go('/briefing'),
          icon: const Icon(Icons.arrow_back_ios_new_rounded),
        ),
        title: const Text('수신 및 알림 설정'),
        actions: <Widget>[
          IconButton(
            onPressed: () async {
              await SessionStore.clear();
              if (!context.mounted) {
                return;
              }
              context.go('/login');
            },
            icon: const Icon(Icons.logout_rounded),
            tooltip: '로그아웃',
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
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
            '아침 브리핑 수신 설정과 알림 상태를 관리합니다.',
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
                  '관심 키워드 설정',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 6),
                Text(
                  '최소 1개, 최대 3개까지 선택해서 저장할 수 있습니다.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 12),
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
                const SizedBox(height: 10),
                Text(
                  '선택 ${_selectedKeywords.length}/3',
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton(
                    onPressed: _isKeywordSaving ? null : _saveKeywords,
                    child: Text(_isKeywordSaving ? '키워드 저장 중...' : '키워드 저장'),
                  ),
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
                  '24시간제로 원하는 수신 시간을 설정할 수 있습니다.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 12),
                Row(
                  children: <Widget>[
                    Expanded(
                      child: _DropdownTimeField(
                        label: '시(00~23)',
                        value: _settings.hour,
                        items: List<int>.generate(24, (int i) => i),
                        onChanged: (int value) {
                          setState(() {
                            _settings = _settings.copyWith(
                              hour: value,
                              isAm: value < 12,
                            );
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
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          NotificationStatusCard(
            permissionStatus: _settings.permissionStatus,
            fcmLinked: _settings.fcmLinked,
            onRequestPermission: _requestNotificationPermission,
          ),
          const SizedBox(height: 20),
                PrimaryButtonWidget(
                  label: _isSaving ? '저장 중...' : '설정 저장',
                  onPressed: _isSaving ? null : _saveNotificationSettings,
                ),
              ],
            ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: 3,
        onDestinationSelected: (int index) {
          if (index == 0) {
            context.go('/briefing?tab=home');
            return;
          }
          if (index == 1) {
            context.go('/briefing?tab=explore');
            return;
          }
          if (index == 2) {
            context.go('/briefing?tab=saved');
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

  Future<void> _loadSettings() async {
    await Future.wait(<Future<void>>[
      _loadNotificationSettings(),
      _loadKeywords(),
    ]);
    await _syncLocalNotificationSchedule();
    if (mounted) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _loadNotificationSettings() async {
    try {
      final NotificationSettingsDto dto = await _notificationApiService
          .getSettings();
      if (!mounted) {
        return;
      }
      setState(() {
        _settings = _settings.copyWith(
          pushEnabled: dto.enabled,
          morningBriefingEnabled: dto.enabled,
          hour: dto.deliveryHour,
          minute: dto.deliveryMinute,
          isAm: dto.deliveryHour < 12,
          timezone: dto.timezone,
          version: dto.version,
        );
      });
    } on ApiException catch (error) {
      _showMessage(error.toString());
    } catch (_) {
      _showMessage('알림 설정을 불러오지 못했습니다.');
    }
  }

  Future<void> _loadKeywords() async {
    try {
      final KeywordsResponseModel dto = await _keywordsApiService.getKeywords();
      if (!mounted) {
        return;
      }
      setState(() {
        _selectedKeywords = dto.keywords.toSet();
        _keywordsVersion = dto.version;
      });
    } on ApiException catch (error) {
      _showMessage(error.toString());
    } catch (_) {
      _showMessage('키워드를 불러오지 못했습니다.');
    }
  }

  Future<void> _saveNotificationSettings() async {
    setState(() => _isSaving = true);

    try {
      final NotificationSettingsDto dto = await _notificationApiService
          .updateSettings(
            enabled: _settings.pushEnabled && _settings.morningBriefingEnabled,
            deliveryHour: _settings.hour,
            deliveryMinute: _settings.minute,
            timezone: _settings.timezone,
            expectedVersion: _settings.version.isEmpty ? null : _settings.version,
          );
      if (!mounted) {
        return;
      }
      setState(() {
        _settings = _settings.copyWith(
          pushEnabled: dto.enabled,
          morningBriefingEnabled: dto.enabled,
          hour: dto.deliveryHour,
          minute: dto.deliveryMinute,
          isAm: dto.deliveryHour < 12,
          timezone: dto.timezone,
          version: dto.version,
        );
      });
      await _syncLocalNotificationSchedule();
      _showMessage('설정이 저장되었습니다.');
    } on ApiException catch (error) {
      _showMessage(error.toString());
    } catch (_) {
      _showMessage('설정 저장 중 오류가 발생했습니다.');
    } finally {
      if (mounted) {
        setState(() => _isSaving = false);
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

  void _toggleKeyword(String keyword) {
    setState(() {
      if (_selectedKeywords.contains(keyword)) {
        _selectedKeywords.remove(keyword);
        return;
      }
      if (_selectedKeywords.length >= 3) {
        _showMessage('키워드는 최대 3개까지 선택할 수 있습니다.');
        return;
      }
      _selectedKeywords.add(keyword);
    });
  }

  Future<void> _saveKeywords() async {
    if (_selectedKeywords.isEmpty) {
      _showMessage('키워드를 최소 1개 이상 선택해 주세요.');
      return;
    }
    setState(() => _isKeywordSaving = true);
    try {
      final KeywordsResponseModel dto = await _keywordsApiService.saveKeywords(
        _selectedKeywords.toList(),
        expectedVersion: _keywordsVersion,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _selectedKeywords = dto.keywords.toSet();
        _keywordsVersion = dto.version;
      });
      await _syncLocalNotificationSchedule();
      _showMessage('키워드가 저장되었습니다.');
    } on ApiException catch (error) {
      if (error.statusCode == 409) {
        await _loadKeywords();
        _showMessage('다른 기기에서 변경되어 새로고침 후 다시 시도해 주세요.');
      } else {
        _showMessage(error.toString());
      }
    } catch (_) {
      _showMessage('키워드 저장 중 오류가 발생했습니다.');
    } finally {
      if (mounted) {
        setState(() => _isKeywordSaving = false);
      }
    }
  }

  Future<void> _requestNotificationPermission() async {
    try {
      final bool granted = await _localNotificationService.requestPermission();
      await _refreshLocalNotificationStatus();
      if (!mounted) {
        return;
      }
      _showMessage(granted ? '알림 권한이 허용되었습니다.' : '알림 권한이 거부되었습니다.');
    } catch (_) {
      _showMessage('알림 권한 요청 중 오류가 발생했습니다.');
    }
  }

  Future<void> _syncLocalNotificationSchedule() async {
    try {
      await _localNotificationService.scheduleDailyBriefingNotification(
        enabled: _settings.pushEnabled && _settings.morningBriefingEnabled,
        hour: _settings.hour,
        minute: _settings.minute,
        keywords: _selectedKeywords.toList(),
        timezoneName: _settings.timezone,
      );
      await _refreshLocalNotificationStatus();
    } catch (_) {}
  }

  Future<void> _refreshLocalNotificationStatus() async {
    final String permissionStatus =
        await _localNotificationService.getPermissionStatus();
    final bool scheduled =
        await _localNotificationService.isDailyBriefingScheduled();
    if (!mounted) {
      return;
    }
    setState(() {
      _settings = _settings.copyWith(
        permissionStatus: permissionStatus,
        fcmLinked: scheduled,
      );
    });
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
