class OnboardingPreferencesModel {
  const OnboardingPreferencesModel({
    required this.keywords,
    required this.hour,
    required this.minute,
  });

  final List<String> keywords;
  final int hour;
  final int minute;
}
