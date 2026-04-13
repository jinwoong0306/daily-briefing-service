import 'package:flutter/material.dart';

class KeywordChipWidget extends StatelessWidget {
  const KeywordChipWidget({
    required this.label,
    required this.isSelected,
    required this.onTap,
    super.key,
  });

  final String label;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ChoiceChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (_) => onTap(),
      selectedShadowColor: Colors.transparent,
      showCheckmark: false,
      labelPadding: const EdgeInsets.symmetric(horizontal: 8),
    );
  }
}
