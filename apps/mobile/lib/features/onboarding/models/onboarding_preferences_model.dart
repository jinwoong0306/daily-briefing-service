class OnboardingPreferencesModel {
  const OnboardingPreferencesModel({
    required this.keywords,
    required this.hour,
    required this.minute,
    required this.isAm,
  });

  final List<String> keywords;
  final int hour;
  final int minute;
  final bool isAm;
}
