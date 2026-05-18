import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/config/app_config.dart';
import '../features/briefing/widgets/feedback_button_widget.dart';
import 'api_exception.dart';
import 'api_response_parser.dart';
import 'session_store.dart';

class BriefingActionsApiService {
  Future<void> saveFeedback({
    required String articleId,
    required FeedbackType feedbackType,
  }) async {
    final String token = _requireToken();
    final Uri uri = Uri.parse('${AppConfig.apiBaseUrl}/briefings/$articleId/feedback');
    final http.Response response = await http.post(
      uri,
      headers: <String, String>{
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode(<String, dynamic>{
        'feedback_type': feedbackType == FeedbackType.like ? 'like' : 'dislike',
      }),
    );
    _assertSuccess(response, fallback: '피드백 저장에 실패했습니다.');
  }

  Future<void> saveBookmark(String articleId) async {
    final String token = _requireToken();
    final Uri uri = Uri.parse('${AppConfig.apiBaseUrl}/briefings/$articleId/bookmark');
    final http.Response response = await http.put(
      uri,
      headers: <String, String>{'Authorization': 'Bearer $token'},
    );
    _assertSuccess(response, fallback: '북마크 저장에 실패했습니다.');
  }

  Future<void> removeBookmark(String articleId) async {
    final String token = _requireToken();
    final Uri uri = Uri.parse('${AppConfig.apiBaseUrl}/briefings/$articleId/bookmark');
    final http.Response response = await http.delete(
      uri,
      headers: <String, String>{'Authorization': 'Bearer $token'},
    );
    _assertSuccess(response, fallback: '북마크 해제에 실패했습니다.');
  }

  String _requireToken() {
    final String? token = SessionStore.accessToken;
    if (token == null || token.isEmpty) {
      throw ApiException('로그인이 필요합니다.');
    }
    return token;
  }

  void _assertSuccess(http.Response response, {required String fallback}) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return;
    }
    final Map<String, dynamic> jsonBody = ApiResponseParser.decodeJsonObject(
      response.body,
    );
    throw ApiException(
      ApiResponseParser.extractErrorMessage(jsonBody, fallback: fallback),
      statusCode: response.statusCode,
    );
  }
}
