import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/config/app_config.dart';
import 'api_exception.dart';
import 'api_response_parser.dart';
import 'session_store.dart';

class NotificationSettingsApiService {
  Future<NotificationSettingsDto> getSettings() async {
    final String token = _requireToken();
    final Uri uri = Uri.parse('${AppConfig.apiBaseUrl}/users/notifications');
    final http.Response response = await http.get(
      uri,
      headers: <String, String>{'Authorization': 'Bearer $token'},
    );

    final Map<String, dynamic> jsonBody = ApiResponseParser.decodeJsonObject(
      response.body,
    );
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return NotificationSettingsDto.fromJson(jsonBody);
    }

    throw ApiException(
      ApiResponseParser.extractErrorMessage(
        jsonBody,
        fallback: '알림 설정 조회에 실패했습니다.',
      ),
      statusCode: response.statusCode,
    );
  }

  Future<NotificationSettingsDto> updateSettings({
    required bool enabled,
    required int deliveryHour,
    required int deliveryMinute,
    required String timezone,
    String? expectedVersion,
  }) async {
    final String token = _requireToken();
    final Uri uri = Uri.parse('${AppConfig.apiBaseUrl}/users/notifications');
    final Map<String, dynamic> payload = <String, dynamic>{
      'enabled': enabled,
      'delivery_hour': deliveryHour,
      'delivery_minute': deliveryMinute,
      'timezone': timezone,
    };
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
      return NotificationSettingsDto.fromJson(jsonBody);
    }

    throw ApiException(
      ApiResponseParser.extractErrorMessage(
        jsonBody,
        fallback: '알림 설정 저장에 실패했습니다.',
      ),
      statusCode: response.statusCode,
    );
  }

  String _requireToken() {
    final String? token = SessionStore.accessToken;
    if (token == null || token.isEmpty) {
      throw ApiException('로그인이 필요합니다.');
    }
    return token;
  }
}

class NotificationSettingsDto {
  const NotificationSettingsDto({
    required this.enabled,
    required this.deliveryHour,
    required this.deliveryMinute,
    required this.timezone,
    required this.version,
  });

  final bool enabled;
  final int deliveryHour;
  final int deliveryMinute;
  final String timezone;
  final String version;

  factory NotificationSettingsDto.fromJson(Map<String, dynamic> json) {
    final dynamic enabled = json['enabled'];
    final dynamic deliveryHour = json['delivery_hour'];
    final dynamic deliveryMinute = json['delivery_minute'];
    final dynamic timezone = json['timezone'];
    final dynamic version = json['version'];

    if (enabled is! bool ||
        deliveryHour is! int ||
        deliveryMinute is! int ||
        timezone is! String ||
        version is! String) {
      throw ApiException('알림 설정 응답 형식이 올바르지 않습니다.');
    }

    return NotificationSettingsDto(
      enabled: enabled,
      deliveryHour: deliveryHour,
      deliveryMinute: deliveryMinute,
      timezone: timezone,
      version: version,
    );
  }
}
