import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';

class NotificationStatusCard extends StatelessWidget {
  const NotificationStatusCard({
    required this.permissionStatus,
    required this.fcmLinked,
    required this.onRequestPermission,
    super.key,
  });

  final String permissionStatus;
  final bool fcmLinked;
  final VoidCallback onRequestPermission;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              const Icon(
                Icons.notifications_active_rounded,
                color: AppColors.primary,
              ),
              const SizedBox(width: 8),
              Text('FCM 알림 상태', style: Theme.of(context).textTheme.titleLarge),
            ],
          ),
          const SizedBox(height: 12),
          _StatusRow(label: '권한 상태', value: permissionStatus),
          _StatusRow(label: '기본 연동', value: fcmLinked ? '연결됨' : '미연결'),
          const SizedBox(height: 10),
          OutlinedButton.icon(
            onPressed: onRequestPermission,
            icon: const Icon(Icons.shield_outlined),
            label: const Text('알림 권한 요청'),
          ),
        ],
      ),
    );
  }
}

class _StatusRow extends StatelessWidget {
  const _StatusRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Text(label, style: Theme.of(context).textTheme.bodyMedium),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: AppColors.surfaceLow,
              borderRadius: BorderRadius.circular(999),
            ),
            child: Text(value, style: Theme.of(context).textTheme.labelLarge),
          ),
        ],
      ),
    );
  }
}
