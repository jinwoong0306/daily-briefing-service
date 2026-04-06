import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/config/app_config.dart';
import 'api_exception.dart';
import 'session_store.dart';

class KeywordsApiService {
  Future<void> saveKeywords(List<String> keywords) async {
    final String? token = SessionStore.accessToken;
    if (token == null || token.isEmpty) {
      throw ApiException('로그인이 필요합니다.');
    }

    final Uri uri = Uri.parse('${AppConfig.apiBaseUrl}/users/keywords');
    final http.Response response = await http.put(
      uri,
      headers: <String, String>{
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode(<String, dynamic>{'keywords': keywords}),
    );

    if (response.statusCode >= 200 && response.statusCode < 300) {
      return;
    }

    final Map<String, dynamic> jsonBody = _decodeJsonObject(response.body);
    final dynamic detail = jsonBody['detail'];
    throw ApiException(
      detail is String && detail.isNotEmpty ? detail : '키워드 저장에 실패했습니다.',
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
}
