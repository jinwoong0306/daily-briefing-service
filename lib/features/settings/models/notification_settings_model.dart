class NotificationSettingsModel {
  const NotificationSettingsModel({
    required this.pushEnabled,
    required this.morningBriefingEnabled,
    required this.weekendEnabled,
    required this.onlyImportantEnabled,
    required this.hour,
    required this.minute,
    required this.isAm,
    required this.permissionStatus,
    required this.fcmLinked,
  });

  final bool pushEnabled;
  final bool morningBriefingEnabled;
  final bool weekendEnabled;
  final bool onlyImportantEnabled;
  final int hour;
  final int minute;
  final bool isAm;
  final String permissionStatus;
  final bool fcmLinked;

  NotificationSettingsModel copyWith({
    bool? pushEnabled,
    bool? morningBriefingEnabled,
    bool? weekendEnabled,
    bool? onlyImportantEnabled,
    int? hour,
    int? minute,
    bool? isAm,
    String? permissionStatus,
    bool? fcmLinked,
  }) {
    return NotificationSettingsModel(
      pushEnabled: pushEnabled ?? this.pushEnabled,
      morningBriefingEnabled:
          morningBriefingEnabled ?? this.morningBriefingEnabled,
      weekendEnabled: weekendEnabled ?? this.weekendEnabled,
      onlyImportantEnabled: onlyImportantEnabled ?? this.onlyImportantEnabled,
      hour: hour ?? this.hour,
      minute: minute ?? this.minute,
      isAm: isAm ?? this.isAm,
      permissionStatus: permissionStatus ?? this.permissionStatus,
      fcmLinked: fcmLinked ?? this.fcmLinked,
    );
  }
}
