import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';

enum FeedbackType { like, dislike }

class FeedbackButtonWidget extends StatelessWidget {
  const FeedbackButtonWidget({
    required this.selectedType,
    required this.onChanged,
    super.key,
  });

  final FeedbackType? selectedType;
  final ValueChanged<FeedbackType> onChanged;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        Expanded(
          child: _FeedbackOption(
            label: '도움이 됐어요',
            icon: Icons.thumb_up_alt_rounded,
            selected: selectedType == FeedbackType.like,
            onTap: () => onChanged(FeedbackType.like),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _FeedbackOption(
            label: '취향이 아니에요',
            icon: Icons.thumb_down_alt_rounded,
            selected: selectedType == FeedbackType.dislike,
            onTap: () => onChanged(FeedbackType.dislike),
          ),
        ),
      ],
    );
  }
}

class _FeedbackOption extends StatelessWidget {
  const _FeedbackOption({
    required this.label,
    required this.icon,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(14),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          color: selected
              ? AppColors.primary.withValues(alpha: 0.1)
              : AppColors.surfaceLow,
          border: Border.all(
            color: selected
                ? AppColors.primary
                : AppColors.outlineVariant.withValues(alpha: 0.35),
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            Icon(
              icon,
              size: 18,
              color: selected ? AppColors.primary : AppColors.textSecondary,
            ),
            const SizedBox(width: 8),
            Flexible(
              child: Text(
                label,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: selected ? AppColors.primary : AppColors.textSecondary,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
