import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'core/config/app_config.dart';
import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';
import 'services/local_notification_service.dart';
import 'services/session_store.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  if (AppConfig.isSupabaseConfigured) {
    await Supabase.initialize(
      url: AppConfig.supabaseUrl,
      anonKey: AppConfig.supabaseAnonKey,
    );
  }
  await SessionStore.initialize();
  runApp(const DailyBriefingApp());
}

class DailyBriefingApp extends StatefulWidget {
  const DailyBriefingApp({super.key});

  @override
  State<DailyBriefingApp> createState() => _DailyBriefingAppState();
}

class _DailyBriefingAppState extends State<DailyBriefingApp> {
  late final GoRouter _router;

  @override
  void initState() {
    super.initState();
    _router = AppRouter.createRouter();
    unawaited(LocalNotificationService().registerRouter(_router));
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Daily Briefing',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      routerConfig: _router,
    );
  }
}
