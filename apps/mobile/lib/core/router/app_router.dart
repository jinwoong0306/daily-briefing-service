import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/screens/login_screen.dart';
import '../../features/auth/screens/signup_screen.dart';
import '../../features/briefing/models/briefing_model.dart';
import '../../features/briefing/screens/briefing_detail_screen.dart';
import '../../features/briefing/screens/briefing_feed_screen.dart';
import '../../features/onboarding/screens/onboarding_screen.dart';
import '../../features/settings/screens/settings_screen.dart';

class AppRouter {
  static final GoRouter router = GoRouter(
    initialLocation: '/',
    errorBuilder: (BuildContext context, GoRouterState state) {
      return Scaffold(
        body: Center(
          child: Text(
            '화면 경로를 찾을 수 없습니다.',
            style: Theme.of(context).textTheme.titleMedium,
          ),
        ),
      );
    },
    routes: <RouteBase>[
      GoRoute(
        path: '/',
        redirect: (BuildContext context, GoRouterState state) => '/login',
      ),
      GoRoute(
        path: '/login',
        name: 'login',
        builder: (BuildContext context, GoRouterState state) {
          return const LoginScreen();
        },
      ),
      GoRoute(
        path: '/signup',
        name: 'signup',
        builder: (BuildContext context, GoRouterState state) {
          return const SignupScreen();
        },
      ),
      GoRoute(
        path: '/onboarding',
        name: 'onboarding',
        builder: (BuildContext context, GoRouterState state) {
          return const OnboardingScreen();
        },
      ),
      GoRoute(
        path: '/briefing',
        name: 'briefing',
        builder: (BuildContext context, GoRouterState state) {
          return const BriefingFeedScreen();
        },
      ),
      GoRoute(
        path: '/briefing/:id',
        name: 'briefingDetail',
        builder: (BuildContext context, GoRouterState state) {
          final String id = state.pathParameters['id'] ?? '';
          final BriefingModel? briefing =
              state.extra is BriefingModel
              ? state.extra as BriefingModel
              : BriefingModel.findById(id);
          return BriefingDetailScreen(briefing: briefing);
        },
      ),
      GoRoute(
        path: '/settings',
        name: 'settings',
        builder: (BuildContext context, GoRouterState state) {
          return const SettingsScreen();
        },
      ),
    ],
  );
}
