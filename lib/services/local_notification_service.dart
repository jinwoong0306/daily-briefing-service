import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:go_router/go_router.dart';
import 'package:timezone/data/latest.dart' as tz_data;
import 'package:timezone/timezone.dart' as tz;

import 'session_store.dart';

/// 로컬 예약 알림 탭 시 이동할 경로 (go_router location).
const String kDailyBriefingNotificationPayload = '/briefing?tab=home';

class LocalNotificationService {
  LocalNotificationService._();
  static final LocalNotificationService _instance = LocalNotificationService._();
  factory LocalNotificationService() => _instance;

  static const int dailyBriefingNotificationId = 1001;
  static const String _androidChannelId = 'daily_briefing_channel';
  static const String _androidChannelName = 'Daily Briefing 알림';
  static const String _androidChannelDescription = '사용자 설정 시간의 브리핑 알림';

  final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();
  bool _pluginInited = false;
  GoRouter? _router;

  Future<void> registerRouter(GoRouter router) async {
    _router = router;
    await _ensurePlugin();
    await _processColdStartNotification(router);
  }

  Future<void> _ensurePlugin() async {
    if (_pluginInited) {
      return;
    }
    tz_data.initializeTimeZones();
    const AndroidInitializationSettings androidInit =
        AndroidInitializationSettings('@mipmap/ic_launcher');
    const DarwinInitializationSettings iosInit = DarwinInitializationSettings();
    const InitializationSettings initSettings = InitializationSettings(
      android: androidInit,
      iOS: iosInit,
    );
    await _plugin.initialize(
      initSettings,
      onDidReceiveNotificationResponse: _onNotificationTapped,
    );
    _pluginInited = true;
  }

  void _onNotificationTapped(NotificationResponse response) {
    final GoRouter? router = _router;
    if (router == null) {
      return;
    }
    unawaited(_navigateFromPayload(response.payload, router));
  }

  Future<void> _processColdStartNotification(GoRouter router) async {
    final NotificationAppLaunchDetails? details =
        await _plugin.getNotificationAppLaunchDetails();
    if (details == null || details.didNotificationLaunchApp != true) {
      return;
    }
    final String? payload = details.notificationResponse?.payload;
    if (payload == null || payload.isEmpty) {
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(_navigateFromPayload(payload, router));
    });
  }

  Future<void> _navigateFromPayload(String? payload, GoRouter router) async {
    if (payload == null || payload.trim().isEmpty) {
      return;
    }
    if (!SessionStore.isAuthenticated) {
      return;
    }
    String location = payload.trim();
    if (!location.startsWith('/')) {
      location = '/$location';
    }
    router.go(location);
  }

  Future<bool> requestPermission() async {
    await _ensurePlugin();
    final AndroidFlutterLocalNotificationsPlugin? androidImpl = _plugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>();
    final bool androidGranted =
        await androidImpl?.requestNotificationsPermission() ?? true;
    final IOSFlutterLocalNotificationsPlugin? iosImpl = _plugin
        .resolvePlatformSpecificImplementation<
            IOSFlutterLocalNotificationsPlugin>();
    final bool iosGranted =
        await iosImpl?.requestPermissions(alert: true, badge: true, sound: true) ??
            true;
    return androidGranted && iosGranted;
  }

  Future<String> getPermissionStatus() async {
    await _ensurePlugin();
    final AndroidFlutterLocalNotificationsPlugin? androidImpl = _plugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>();
    final bool? androidGranted = await androidImpl?.areNotificationsEnabled();
    if (androidGranted == false) {
      return '거부됨';
    }
    return '허용됨';
  }

  Future<bool> isDailyBriefingScheduled() async {
    await _ensurePlugin();
    final List<PendingNotificationRequest> pending =
        await _plugin.pendingNotificationRequests();
    return pending.any(
      (PendingNotificationRequest request) =>
          request.id == dailyBriefingNotificationId,
    );
  }

  Future<void> scheduleDailyBriefingNotification({
    required bool enabled,
    required int hour,
    required int minute,
    required List<String> keywords,
    String timezoneName = 'Asia/Seoul',
    String deepLinkLocation = kDailyBriefingNotificationPayload,
  }) async {
    await _ensurePlugin();
    await _plugin.cancel(dailyBriefingNotificationId);
    if (!enabled) {
      return;
    }
    final bool allowed = await _isPermissionGranted();
    if (!allowed) {
      return;
    }
    tz.Location location;
    try {
      location = tz.getLocation(timezoneName);
    } catch (_) {
      location = tz.getLocation('Asia/Seoul');
    }
    final tz.TZDateTime now = tz.TZDateTime.now(location);
    tz.TZDateTime scheduled = tz.TZDateTime(
      location,
      now.year,
      now.month,
      now.day,
      hour,
      minute,
    );
    if (!scheduled.isAfter(now)) {
      scheduled = scheduled.add(const Duration(days: 1));
    }

    final String title = 'Daily Briefing 알림';
    final String body = _buildBody(keywords);
    const NotificationDetails details = NotificationDetails(
      android: AndroidNotificationDetails(
        _androidChannelId,
        _androidChannelName,
        channelDescription: _androidChannelDescription,
        importance: Importance.max,
        priority: Priority.high,
      ),
      iOS: DarwinNotificationDetails(),
    );

    await _plugin.zonedSchedule(
      dailyBriefingNotificationId,
      title,
      body,
      scheduled,
      details,
      androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      uiLocalNotificationDateInterpretation:
          UILocalNotificationDateInterpretation.absoluteTime,
      matchDateTimeComponents: DateTimeComponents.time,
      payload: deepLinkLocation,
    );
  }

  String _buildBody(List<String> keywords) {
    final List<String> cleaned = keywords
        .map((String keyword) => keyword.trim())
        .where((String keyword) => keyword.isNotEmpty)
        .toList();
    if (cleaned.isEmpty) {
      return '설정한 시간입니다. 오늘의 브리핑을 확인해 주세요.';
    }
    final String joined = cleaned.take(3).join(', ');
    return '$joined 키워드 브리핑이 준비되었습니다. 지금 확인해 보세요.';
  }

  Future<bool> _isPermissionGranted() async {
    final AndroidFlutterLocalNotificationsPlugin? androidImpl = _plugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>();
    final bool? androidGranted = await androidImpl?.areNotificationsEnabled();
    if (androidGranted == false) {
      return false;
    }
    return true;
  }
}
