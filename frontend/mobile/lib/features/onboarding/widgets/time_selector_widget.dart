import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';

class TimeSelectorWidget extends StatelessWidget {
  const TimeSelectorWidget({
    required this.hour,
    required this.minute,
    required this.isAm,
    required this.onHourChanged,
    required this.onMinuteChanged,
    required this.onPeriodChanged,
    super.key,
  });

  final int hour;
  final int minute;
  final bool isAm;
  final ValueChanged<int> onHourChanged;
  final ValueChanged<int> onMinuteChanged;
  final ValueChanged<bool> onPeriodChanged;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text('브리핑 수신 시간', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 4),
            Text(
              '언제 아침 브리핑을 받을지 설정해 주세요.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 16),
            Row(
              children: <Widget>[
                Expanded(
                  child: _NumberPickerCard(
                    label: '시',
                    value: hour.toString().padLeft(2, '0'),
                    items: List<int>.generate(12, (int i) => i + 1),
                    onChanged: onHourChanged,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _NumberPickerCard(
                    label: '분',
                    value: minute.toString().padLeft(2, '0'),
                    items: List<int>.generate(6, (int i) => i * 10),
                    onChanged: onMinuteChanged,
                  ),
                ),
                const SizedBox(width: 10),
                _PeriodSwitch(isAm: isAm, onChanged: onPeriodChanged),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _NumberPickerCard extends StatelessWidget {
  const _NumberPickerCard({
    required this.label,
    required this.value,
    required this.items,
    required this.onChanged,
  });

  final String label;
  final String value;
  final List<int> items;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: AppColors.surfaceLow,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        child: Row(
          children: <Widget>[
            Text(
              label,
              style: Theme.of(
                context,
              ).textTheme.labelSmall?.copyWith(color: AppColors.textSecondary),
            ),
            const Spacer(),
            DropdownButton<int>(
              value: int.parse(value),
              underline: const SizedBox.shrink(),
              dropdownColor: AppColors.surface,
              items: items
                  .map(
                    (int item) => DropdownMenuItem<int>(
                      value: item,
                      child: Text(item.toString().padLeft(2, '0')),
                    ),
                  )
                  .toList(),
              onChanged: (int? v) {
                if (v != null) {
                  onChanged(v);
                }
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _PeriodSwitch extends StatelessWidget {
  const _PeriodSwitch({required this.isAm, required this.onChanged});

  final bool isAm;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: AppColors.surfaceLow,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        children: <Widget>[
          _PeriodButton(
            label: 'AM',
            selected: isAm,
            onTap: () => onChanged(true),
          ),
          _PeriodButton(
            label: 'PM',
            selected: !isAm,
            onTap: () => onChanged(false),
          ),
        ],
      ),
    );
  }
}

class _PeriodButton extends StatelessWidget {
  const _PeriodButton({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        width: 56,
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          color: selected ? AppColors.primary : Colors.transparent,
        ),
        alignment: Alignment.center,
        child: Text(
          label,
          style: Theme.of(context).textTheme.labelLarge?.copyWith(
            color: selected ? Colors.white : AppColors.textSecondary,
          ),
        ),
      ),
    );
  }
}
