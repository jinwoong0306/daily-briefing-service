import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/config/app_config.dart';
import 'api_response_parser.dart';
import 'api_exception.dart';
import 'session_store.dart';

class KeywordsApiService {
  Future<KeywordsResponseModel> getKeywords() async {
    final String? token = SessionStore.accessToken;
    if (token == null || token.isEmpty) {
      throw ApiException('로그인이 필요합니다.');
    }

    final Uri uri = Uri.parse('${AppConfig.apiBaseUrl}/users/keywords');
    final http.Response response = await http.get(
      uri,
      headers: <String, String>{'Authorization': 'Bearer $token'},
    );

    final Map<String, dynamic> jsonBody = ApiResponseParser.decodeJsonObject(
      response.body,
    );
    if (response.statusCode >= 200 && response.statusCode < 300) {
      final dynamic keywords = jsonBody['keywords'];
      final dynamic version = jsonBody['version'];
      if (keywords is List && version is String) {
        return KeywordsResponseModel(
          keywords: keywords.whereType<String>().toList(),
          version: version,
        );
      }
      throw ApiException('키워드 응답 형식이 올바르지 않습니다.');
    }

    throw ApiException(
      ApiResponseParser.extractErrorMessage(
        jsonBody,
        fallback: '키워드 조회에 실패했습니다.',
      ),
      statusCode: response.statusCode,
    );
  }

  Future<KeywordsResponseModel> saveKeywords(
    List<String> keywords, {
    String? expectedVersion,
  }) async {
    final String? token = SessionStore.accessToken;
    if (token == null || token.isEmpty) {
      throw ApiException('로그인이 필요합니다.');
    }

    final Uri uri = Uri.parse('${AppConfig.apiBaseUrl}/users/keywords');
    final Map<String, dynamic> payload = <String, dynamic>{'keywords': keywords};
    if (expectedVersion != null && expectedVersion.isNotEmpty) {
      payload['expected_version'] = expectedVersion;
    }

    final http.Response response = await http.put(
      uri,
      headers: <String, String>{
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode(payload),
    );

    final Map<String, dynamic> jsonBody = ApiResponseParser.decodeJsonObject(
      response.body,
    );
    if (response.statusCode >= 200 && response.statusCode < 300) {
      final dynamic responseKeywords = jsonBody['keywords'];
      final dynamic version = jsonBody['version'];
      if (responseKeywords is List && version is String) {
        return KeywordsResponseModel(
          keywords: responseKeywords.whereType<String>().toList(),
          version: version,
        );
      }
      throw ApiException('키워드 응답 형식이 올바르지 않습니다.');
    }

    throw ApiException(
      ApiResponseParser.extractErrorMessage(
        jsonBody,
        fallback: '키워드 저장에 실패했습니다.',
      ),
      statusCode: response.statusCode,
    );
  }
}

class KeywordsResponseModel {
  const KeywordsResponseModel({required this.keywords, required this.version});

  final List<String> keywords;
  final String version;
}
