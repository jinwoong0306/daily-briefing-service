import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/config/app_config.dart';
import 'api_exception.dart';

class GeminiApiService {
  Future<String> generateOneLineSummary({
    required String title,
    required String summary,
  }) async {
    if (AppConfig.geminiApiKey.isEmpty) {
      throw ApiException(
        'GEMINI_API_KEY가 설정되지 않았습니다. --dart-define=GEMINI_API_KEY=... 또는 --dart-define-from-file=frontend.env 로 실행해 주세요.',
      );
    }

    final Uri uri = Uri.parse(AppConfig.geminiEndpoint);
    final Map<String, dynamic> body = <String, dynamic>{
      'contents': <Map<String, dynamic>>[
        <String, dynamic>{
          'parts': <Map<String, dynamic>>[
            <String, dynamic>{
              'text':
                  '다음 뉴스의 핵심을 한국어 한 줄(최대 60자)로 요약해 주세요.\n'
                      '제목: $title\n'
                      '요약: $summary',
            },
          ],
        },
      ],
      'generationConfig': <String, dynamic>{
        'temperature': 0.2,
        'maxOutputTokens': 80,
      },
    };

    final http.Response response = await http.post(
      uri,
      headers: <String, String>{
        'Content-Type': 'application/json',
        'X-goog-api-key': AppConfig.geminiApiKey,
      },
      body: jsonEncode(body),
    );

    final Map<String, dynamic> jsonBody = _decodeJsonObject(response.body);
    if (response.statusCode >= 200 && response.statusCode < 300) {
      final String? text = _extractFirstText(jsonBody);
      if (text != null && text.trim().isNotEmpty) {
        return _normalizeOneLineSummary(
          text: text,
          title: title,
          summary: summary,
        );
      }
      throw ApiException('Gemini 응답에서 요약 텍스트를 찾지 못했습니다.');
    }

    throw ApiException(
      _extractErrorMessage(jsonBody) ?? 'Gemini 요청에 실패했습니다.',
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

  String? _extractFirstText(Map<String, dynamic> jsonBody) {
    final dynamic candidates = jsonBody['candidates'];
    if (candidates is List && candidates.isNotEmpty) {
      final dynamic first = candidates.first;
      if (first is Map<String, dynamic>) {
        final dynamic content = first['content'];
        if (content is Map<String, dynamic>) {
          final dynamic parts = content['parts'];
          if (parts is List && parts.isNotEmpty) {
            final dynamic part = parts.first;
            if (part is Map<String, dynamic>) {
              final dynamic text = part['text'];
              if (text is String) {
                return text;
              }
            }
          }
        }
      }
    }
    return null;
  }

  String? _extractErrorMessage(Map<String, dynamic> jsonBody) {
    final dynamic error = jsonBody['error'];
    if (error is Map<String, dynamic>) {
      final dynamic message = error['message'];
      if (message is String && message.isNotEmpty) {
        return message;
      }
    }
    return null;
  }

  String _normalizeOneLineSummary({
    required String text,
    required String title,
    required String summary,
  }) {
    String normalized = text.trim();
    normalized = normalized.replaceAll(RegExp(r'[\r\n]+'), ' ');
    normalized = normalized.replaceAll(RegExp(r'\s+'), ' ');
    normalized = normalized
        .replaceAll('"', '')
        .replaceAll("'", '')
        .replaceAll('`', '')
        .trim();
    if (normalized.startsWith('-')) {
      normalized = normalized.substring(1).trim();
    }
    normalized = normalized.replaceFirst(RegExp(r'[.!?]+\s*$'), '').trim();

    final bool tooShort = normalized.length < 12;
    final bool tooLong = normalized.length > 80;
    final bool singleToken = normalized.split(RegExp(r'\s+')).length <= 1;
    final bool genericLabel = <String>{
      '정치',
      '경제',
      '사회',
      '스포츠',
      '연예',
      'IT',
      'IT/과학',
      '과학',
      '뉴스',
      '요약',
    }.contains(normalized);

    if (tooShort || tooLong || singleToken || genericLabel) {
      return _ensureSentenceEnding(
        _buildFallbackOneLine(title: title, summary: summary),
      );
    }
    return _ensureSentenceEnding(normalized);
  }

  String _buildFallbackOneLine({
    required String title,
    required String summary,
  }) {
    final String source = summary.trim().isNotEmpty ? summary.trim() : title.trim();
    String oneLine = source
        .replaceAll(RegExp(r'[\r\n]+'), ' ')
        .replaceAll(RegExp(r'\s+'), ' ')
        .trim();
    if (oneLine.length > 58) {
      oneLine = oneLine.substring(0, 58).trim();
    }
    if (oneLine.length < 12) {
      final String titleLine = title
          .replaceAll(RegExp(r'[\r\n]+'), ' ')
          .replaceAll(RegExp(r'\s+'), ' ')
          .trim();
      if (titleLine.length > 58) {
        return titleLine.substring(0, 58).trim();
      }
      if (titleLine.isNotEmpty) {
        return '$titleLine 관련 핵심 흐름을 한눈에 정리합니다.';
      }
      return '핵심 흐름과 쟁점을 중심으로 한줄 요약을 제공합니다.';
    }
    return oneLine;
  }

  String _ensureSentenceEnding(String value) {
    final String cleaned = value
        .replaceAll(RegExp(r'[\r\n]+'), ' ')
        .replaceAll(RegExp(r'\s+'), ' ')
        .trim();
    if (cleaned.isEmpty) {
      return '핵심 흐름을 한 줄로 정리했습니다.';
    }
    return '${cleaned.replaceFirst(RegExp(r'[.!?]+\s*$'), '').trim()}.';
  }
}
