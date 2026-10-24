import 'package:flutter/material.dart';

class PrimaryButtonWidget extends StatelessWidget {
  const PrimaryButtonWidget({
    required this.label,
    required this.onPressed,
    this.icon,
    super.key,
  });

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final ButtonStyle style = ElevatedButton.styleFrom(
      padding: const EdgeInsets.symmetric(vertical: 16),
    );

    if (icon == null) {
      return SizedBox(
        width: double.infinity,
        child: ElevatedButton(
          onPressed: onPressed,
          style: style,
          child: Text(label),
        ),
      );
    }

    return SizedBox(
      width: double.infinity,
      child: ElevatedButton.icon(
        onPressed: onPressed,
        style: style,
        icon: Icon(icon, size: 20),
        label: Text(label),
      ),
    );
  }
}
