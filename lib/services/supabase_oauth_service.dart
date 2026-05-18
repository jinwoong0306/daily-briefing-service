import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../core/config/app_config.dart';
import 'api_exception.dart';

class SupabaseOAuthService {
  Future<String> signInWithGoogleAndGetAccessToken() async {
    if (!AppConfig.isSupabaseConfigured) {
      throw ApiException('Supabase 설정이 필요합니다. SUPABASE_URL, SUPABASE_ANON_KEY를 확인해 주세요.');
    }
    final GoTrueClient auth = Supabase.instance.client.auth;
    final bool launched = await auth.signInWithOAuth(
      OAuthProvider.google,
      redirectTo: kIsWeb ? null : 'io.supabase.flutter://login-callback/',
    );
    if (!launched) {
      throw ApiException('Google OAuth 화면을 열지 못했습니다.');
    }

    final Session? current = auth.currentSession;
    if (current?.accessToken != null && current!.accessToken.isNotEmpty) {
      return current.accessToken;
    }

    try {
      final AuthState state = await auth.onAuthStateChange
          .where(
            (AuthState change) =>
                change.event == AuthChangeEvent.signedIn &&
                change.session?.accessToken.isNotEmpty == true,
          )
          .first
          .timeout(const Duration(minutes: 2));
      return state.session!.accessToken;
    } on TimeoutException {
      throw ApiException('Google 인증이 완료되지 않았습니다. 다시 시도해 주세요.');
    }
  }
}
