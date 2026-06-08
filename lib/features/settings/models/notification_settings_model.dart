class NotificationSettingsModel {
  const NotificationSettingsModel({
    required this.pushEnabled,
    required this.morningBriefingEnabled,
    required this.hour,
    required this.minute,
    required this.isAm,
    required this.permissionStatus,
    required this.fcmLinked,
    required this.timezone,
    required this.version,
  });

  final bool pushEnabled;
  final bool morningBriefingEnabled;
  final int hour;
  final int minute;
  final bool isAm;
  final String permissionStatus;
  final bool fcmLinked;
  final String timezone;
  final String version;

  NotificationSettingsModel copyWith({
    bool? pushEnabled,
    bool? morningBriefingEnabled,
    int? hour,
    int? minute,
    bool? isAm,
    String? permissionStatus,
    bool? fcmLinked,
    String? timezone,
    String? version,
  }) {
    return NotificationSettingsModel(
      pushEnabled: pushEnabled ?? this.pushEnabled,
      morningBriefingEnabled:
          morningBriefingEnabled ?? this.morningBriefingEnabled,
      hour: hour ?? this.hour,
      minute: minute ?? this.minute,
      isAm: isAm ?? this.isAm,
      permissionStatus: permissionStatus ?? this.permissionStatus,
      fcmLinked: fcmLinked ?? this.fcmLinked,
      timezone: timezone ?? this.timezone,
      version: version ?? this.version,
    );
  }
}
