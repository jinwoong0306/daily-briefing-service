import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/config/app_config.dart';
import 'api_exception.dart';
import 'session_store.dart';

class AuthApiService {
  Future<void> login({
    required String email,
    required String password,
  }) async {
    await _authenticate(
      endpoint: '/auth/login',
      payload: <String, dynamic>{'email': email.trim(), 'password': password},
    );
  }

  Future<void> register({
    required String name,
    required String email,
    required String password,
  }) async {
    await _authenticate(
      endpoint: '/auth/register',
      payload: <String, dynamic>{
        'name': name.trim(),
        'email': email.trim(),
        'password': password,
      },
    );
  }

  Future<void> _authenticate({
    required String endpoint,
    required Map<String, dynamic> payload,
  }) async {
    final Uri uri = Uri.parse('${AppConfig.apiBaseUrl}$endpoint');
    final http.Response response = await http.post(
      uri,
      headers: <String, String>{'Content-Type': 'application/json'},
      body: jsonEncode(payload),
    );

    final Map<String, dynamic> jsonBody = _decodeJsonObject(response.body);
    if (response.statusCode >= 200 && response.statusCode < 300) {
      final dynamic token = jsonBody['access_token'];
      if (token is! String || token.isEmpty) {
        throw ApiException('토큰이 응답에 없습니다.');
      }
      SessionStore.accessToken = token;
      return;
    }

    throw ApiException(
      _extractErrorMessage(jsonBody, fallback: '인증 요청이 실패했습니다.'),
      statusCode: response.statusCode,
    );
  }

  Map<String, dynamic> _decodeJsonObject(String source) {
    if (source.isEmpty) {
      return <String, dynamic>{};
    }
    final dynamic decoded = jsonDecode(source);
    if (decoded is Map<String, dynamic>) {
      return decoded;
    }
    return <String, dynamic>{};
  }

  String _extractErrorMessage(
    Map<String, dynamic> jsonBody, {
    required String fallback,
  }) {
    final dynamic detail = jsonBody['detail'];
    if (detail is String && detail.isNotEmpty) {
      return detail;
    }
    return fallback;
  }
}
