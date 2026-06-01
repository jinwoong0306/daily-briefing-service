/// 아침 브리핑 로컬/서버 수신 시각(시) — 밤 사이 수집된 뉴스를 오전에만 전달.
class BriefingDeliveryTime {
  BriefingDeliveryTime._();

  static const int minHour = 7;
  static const int maxHour = 12;

  static List<int> get allowedHours =>
      List<int>.generate(maxHour - minHour + 1, (int i) => minHour + i);

  /// 서버나 이전 설정에서 범위 밖 값이 오면 안전한 기본값으로 맞춤.
  static int normalizeHour(int hour) {
    if (hour < minHour || hour > maxHour) {
      return 8;
    }
    return hour;
  }
}
