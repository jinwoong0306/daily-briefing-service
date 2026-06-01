import 'package:flutter/material.dart';

import '../../../core/constants/briefing_delivery_time.dart';
import '../../../core/theme/app_colors.dart';

class TimeSelectorWidget extends StatelessWidget {
  const TimeSelectorWidget({
    required this.hour,
    required this.minute,
    required this.onHourChanged,
    required this.onMinuteChanged,
    super.key,
  });

  /// 24시간제 시 (7~12, 오전만).
  final int hour;
  final int minute;
  final ValueChanged<int> onHourChanged;
  final ValueChanged<int> onMinuteChanged;

  @override
  Widget build(BuildContext context) {
    final int safeHour = BriefingDeliveryTime.normalizeHour(hour);

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
              '뉴스는 밤 사이 수집되며, 오전 ${BriefingDeliveryTime.minHour}시~${BriefingDeliveryTime.maxHour}시 사이에만 수신 시각을 정할 수 있습니다.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 16),
            Row(
              children: <Widget>[
                Expanded(
                  child: _NumberPickerCard(
                    label: '시 (${BriefingDeliveryTime.minHour}~${BriefingDeliveryTime.maxHour})',
                    value: safeHour,
                    items: BriefingDeliveryTime.allowedHours,
                    onChanged: onHourChanged,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _NumberPickerCard(
                    label: '분',
                    value: minute,
                    items: List<int>.generate(6, (int i) => i * 10),
                    onChanged: onMinuteChanged,
                  ),
                ),
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
  final int value;
  final List<int> items;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    final int safeValue = items.contains(value) ? value : items.first;

    return DecoratedBox(
      decoration: BoxDecoration(
        color: AppColors.surfaceLow,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        child: Row(
          children: <Widget>[
            Expanded(
              child: Text(
                label,
                style: Theme.of(
                  context,
                ).textTheme.labelSmall?.copyWith(color: AppColors.textSecondary),
              ),
            ),
            DropdownButton<int>(
              value: safeValue,
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
