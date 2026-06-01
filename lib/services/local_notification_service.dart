import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart' show PlatformException;
import 'package:flutter/widgets.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:go_router/go_router.dart';
import 'package:timezone/data/latest.dart' as tz_data;
import 'package:timezone/timezone.dart' as tz;

import 'session_store.dart';

/// Android에서「정확한 알람 설정 열기」동작 결과.
enum AndroidExactAlarmPromptOutcome {
  /// 웹·iOS 등 또는 플러그인 없음
  skipped,
  /// 이미 허용됨 — 시스템 화면을 열지 않음
  alreadyGranted,
  /// 미허용이었고 시스템 설정 화면을 연 뒤 사용자가 돌아옴
  settingsOpened,
}

/// 로컬 예약 알림 탭 시 이동할 경로 (go_router location).
const String kDailyBriefingNotificationPayload = '/briefing?tab=home';

class LocalNotificationService {
  LocalNotificationService._();
  static final LocalNotificationService _instance = LocalNotificationService._();
  factory LocalNotificationService() => _instance;

  static const int dailyBriefingNotificationId = 1001;
  /// 이전 채널은 importance/사운드가 고정돼 있을 수 있어 알람용 새 id 사용.
  static const String _androidChannelId = 'daily_briefing_alarm_v2';
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
    await _ensureAndroidNotificationChannel();
    _pluginInited = true;
  }

  Future<void> _ensureAndroidNotificationChannel() async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) {
      return;
    }
    final AndroidFlutterLocalNotificationsPlugin? android = _plugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>();
    const AndroidNotificationChannel channel = AndroidNotificationChannel(
      _androidChannelId,
      _androidChannelName,
      description: _androidChannelDescription,
      importance: Importance.max,
      playSound: true,
      enableVibration: true,
      audioAttributesUsage: AudioAttributesUsage.alarm,
    );
    await android?.createNotificationChannel(channel);
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

  /// [enabled]가 true인데 예약·대기 목록 반영에 실패하면 false.
  Future<bool> scheduleDailyBriefingNotification({
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
      return true;
    }
    final bool allowed = await _isPermissionGranted();
    if (!allowed) {
      return false;
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
    // 저장 시각이 수신 시·분과 같으면 오늘 16:30:00 < now 때문에 내일로 미뤄지는 것을 방지한다.
    if (!scheduled.isAfter(now)) {
      if (now.hour == hour && now.minute == minute) {
        scheduled = now.add(const Duration(seconds: 3));
      } else {
        scheduled = scheduled.add(const Duration(days: 1));
      }
    }

    final String title = 'Daily Briefing 알림';
    final String body = _buildBody(keywords);
    final NotificationDetails details = NotificationDetails(
      android: AndroidNotificationDetails(
        _androidChannelId,
        _androidChannelName,
        channelDescription: _androidChannelDescription,
        importance: Importance.max,
        priority: Priority.high,
        category: AndroidNotificationCategory.alarm,
        audioAttributesUsage: AudioAttributesUsage.alarm,
      ),
      iOS: const DarwinNotificationDetails(),
    );

    await _zonedScheduleDailyBriefing(
      scheduled: scheduled,
      title: title,
      body: body,
      details: details,
      deepLinkLocation: deepLinkLocation,
    );

    if (kIsWeb) {
      return true;
    }
    final List<PendingNotificationRequest> pending =
        await _plugin.pendingNotificationRequests();
    return pending.any(
      (PendingNotificationRequest request) =>
          request.id == dailyBriefingNotificationId,
    );
  }

  /// Android: 알람 시계(상단 예고) → 정확+유휴 → 느슨한 알람 순으로 시도.
  Future<void> _zonedScheduleDailyBriefing({
    required tz.TZDateTime scheduled,
    required String title,
    required String body,
    required NotificationDetails details,
    required String deepLinkLocation,
  }) async {
    Future<void> doSchedule(AndroidScheduleMode mode) async {
      await _plugin.zonedSchedule(
        dailyBriefingNotificationId,
        title,
        body,
        scheduled,
        details,
        androidScheduleMode: mode,
        matchDateTimeComponents: DateTimeComponents.time,
        payload: deepLinkLocation,
      );
    }

    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) {
      await doSchedule(AndroidScheduleMode.exactAllowWhileIdle);
      return;
    }

    final List<AndroidScheduleMode> modes = <AndroidScheduleMode>[
      AndroidScheduleMode.alarmClock,
      AndroidScheduleMode.exactAllowWhileIdle,
      AndroidScheduleMode.inexactAllowWhileIdle,
    ];

    PlatformException? lastExact;
    for (final AndroidScheduleMode mode in modes) {
      try {
        await doSchedule(mode);
        return;
      } on PlatformException catch (e) {
        if (e.code == 'exact_alarms_not_permitted' &&
            mode != AndroidScheduleMode.inexactAllowWhileIdle) {
          lastExact = e;
          continue;
        }
        rethrow;
      }
    }
    final PlatformException? failedExact = lastExact;
    if (failedExact != null) {
      throw failedExact;
    }
    throw StateError('Android 알림 스케줄에 실패했습니다.');
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

  /// Android 12+ 정확한 알람. null이면 이 플랫폼에서는 UI에 줄 필요 없음.
  Future<String?> getAndroidExactAlarmStatusLabel() async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) {
      return null;
    }
    await _ensurePlugin();
    final AndroidFlutterLocalNotificationsPlugin? android = _plugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>();
    final bool? can = await android?.canScheduleExactNotifications();
    if (can == null) {
      return '확인 불가';
    }
    return can ? '허용됨' : '미허용(설정에서 켜기)';
  }

  /// 이미 허용이면 화면을 열지 않고 [alreadyGranted].
  /// 미허용이면 시스템 설정을 연 뒤 [settingsOpened].
  Future<AndroidExactAlarmPromptOutcome>
      promptAndroidExactAlarmSettingsIfNeeded() async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) {
      return AndroidExactAlarmPromptOutcome.skipped;
    }
    await _ensurePlugin();
    final AndroidFlutterLocalNotificationsPlugin? android = _plugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>();
    if (android == null) {
      return AndroidExactAlarmPromptOutcome.skipped;
    }
    final bool? can = await android.canScheduleExactNotifications();
    if (can == true) {
      return AndroidExactAlarmPromptOutcome.alreadyGranted;
    }
    await android.requestExactAlarmsPermission();
    return AndroidExactAlarmPromptOutcome.settingsOpened;
  }

  /// 진단용: 단발 예약(반복 없음). AlarmManager·리시버가 동작하는지 확인.
  Future<bool> scheduleDiagnosticNotificationInSeconds(int seconds) async {
    if (seconds < 5 || seconds > 300) {
      return false;
    }
    if (kIsWeb) {
      return false;
    }
    await _ensurePlugin();
    const int diagnosticId = 10998;
    await _plugin.cancel(diagnosticId);
    if (!await _isPermissionGranted()) {
      return false;
    }
    final tz.Location location = tz.getLocation('Asia/Seoul');
    final tz.TZDateTime when =
        tz.TZDateTime.now(location).add(Duration(seconds: seconds));
    final NotificationDetails details = NotificationDetails(
      android: AndroidNotificationDetails(
        _androidChannelId,
        _androidChannelName,
        channelDescription: _androidChannelDescription,
        importance: Importance.max,
        priority: Priority.high,
        category: AndroidNotificationCategory.alarm,
        audioAttributesUsage: AudioAttributesUsage.alarm,
      ),
      iOS: const DarwinNotificationDetails(),
    );
    try {
      await _plugin.zonedSchedule(
        diagnosticId,
        '브리핑 알림 진단',
        '$seconds초 후에 이 알림이 보이면 예약 경로는 정상입니다.',
        when,
        details,
        androidScheduleMode: defaultTargetPlatform == TargetPlatform.android
            ? AndroidScheduleMode.alarmClock
            : AndroidScheduleMode.exactAllowWhileIdle,
        payload: '',
      );
      return true;
    } on Object {
      return false;
    }
  }
}
