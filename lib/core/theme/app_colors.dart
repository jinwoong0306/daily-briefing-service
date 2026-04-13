import 'package:flutter/material.dart';

class AppColors {
  static const Color primary = Color(0xFF0064FF);
  static const Color primaryDark = Color(0xFF0051D2);
  static const Color primaryDeep = Color(0xFF1A237E);
  static const Color primaryContainer = Color(0xFF7A9DFF);

  static const Color secondary = Color(0xFF4650B7);
  static const Color secondaryContainer = Color(0xFFCBCEFF);
  static const Color tertiary = Color(0xFF8D3A8A);

  static const Color background = Color(0xFFFFFFFF);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color surfaceLow = Color(0xFFF1EFFF);
  static const Color surfaceHigh = Color(0xFFE0E0FF);
  static const Color surfaceHighest = Color(0xFFD9DAFF);

  static const Color textPrimary = Color(0xFF282B51);
  static const Color textSecondary = Color(0xFF555881);
  static const Color outlineVariant = Color(0xFFA7AAD7);
  static const Color error = Color(0xFFB31B25);

  static const List<BoxShadow> cardShadow = <BoxShadow>[
    BoxShadow(
      color: Color(0x1A282B51),
      blurRadius: 16,
      offset: Offset(0, 6),
    ),
    BoxShadow(
      color: Color(0x24282B51),
      blurRadius: 28,
      offset: Offset(0, 12),
    ),
  ];

  static const List<BoxShadow> panelShadow = <BoxShadow>[
    BoxShadow(
      color: Color(0x1C282B51),
      blurRadius: 14,
      offset: Offset(0, 6),
    ),
  ];
}
