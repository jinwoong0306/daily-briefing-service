import 'dart:convert';

class ApiResponseParser {
  const ApiResponseParser._();

  static Map<String, dynamic> decodeJsonObject(String source) {
    if (source.isEmpty) {
      return <String, dynamic>{};
    }
    final dynamic decoded = jsonDecode(source);
    if (decoded is Map<String, dynamic>) {
      return decoded;
    }
    return <String, dynamic>{};
  }

  static String extractErrorMessage(
    Map<String, dynamic> jsonBody, {
    required String fallback,
  }) {
    final dynamic error = jsonBody['error'];
    if (error is Map<String, dynamic>) {
      final dynamic message = error['message'];
      if (message is String && message.isNotEmpty) {
        return message;
      }
    }

    final dynamic detail = jsonBody['detail'];
    if (detail is String && detail.isNotEmpty) {
      return detail;
    }

    return fallback;
  }
}
