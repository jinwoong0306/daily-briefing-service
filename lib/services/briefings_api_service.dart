import 'package:http/http.dart' as http;

import '../core/config/app_config.dart';
import '../features/briefing/models/briefing_model.dart';
import 'api_exception.dart';
import 'api_response_parser.dart';
import 'session_store.dart';

class BriefingsApiService {
  Future<List<BriefingKeywordSectionModel>> getTodayBriefingsGrouped() async {
    final String? token = SessionStore.accessToken;
    if (token == null || token.isEmpty) {
      throw ApiException('로그인이 필요합니다.');
    }
    return _getTodayBriefingsGrouped(token);
  }

  Future<List<BriefingModel>> getTodayBriefings() async {
    final String? token = SessionStore.accessToken;
    if (token == null || token.isEmpty) {
      throw ApiException('로그인이 필요합니다.');
    }

    try {
      final List<BriefingKeywordSectionModel> grouped =
          await _getTodayBriefingsGrouped(token);
      if (grouped.isNotEmpty) {
        final List<BriefingModel> flattened = grouped
            .expand((BriefingKeywordSectionModel section) => section.items)
            .toList();
        BriefingModel.cacheItems(flattened);
        return flattened;
      }
    } on ApiException {
      // grouped 응답이 없거나 실패하면 기존 today 응답으로 폴백
    } catch (_) {}

    return _getBriefings('/briefings/today', fallback: '브리핑 조회에 실패했습니다.');
  }

  Future<List<BriefingModel>> getTodayBriefingsLegacy() async {
    return _getBriefings('/briefings/today', fallback: '브리핑 조회에 실패했습니다.');
  }

  Future<List<BriefingModel>> getBookmarkedBriefings() async {
    return _getBriefings('/briefings/bookmarks', fallback: '저장된 브리핑 조회에 실패했습니다.');
  }

  Future<List<BriefingModel>> _getBriefings(
    String endpoint, {
    required String fallback,
  }) async {
    final String? token = SessionStore.accessToken;
    if (token == null || token.isEmpty) {
      throw ApiException('로그인이 필요합니다.');
    }

    final Uri uri = Uri.parse('${AppConfig.apiBaseUrl}$endpoint');
    final http.Response response = await http.get(
      uri,
      headers: <String, String>{'Authorization': 'Bearer $token'},
    );

    final Map<String, dynamic> jsonBody = ApiResponseParser.decodeJsonObject(
      response.body,
    );
    if (response.statusCode >= 200 && response.statusCode < 300) {
      final dynamic items = jsonBody['items'];
      if (items is List) {
        final List<BriefingModel> briefings = items
            .whereType<Map<String, dynamic>>()
            .map(BriefingModel.fromJson)
            .toList();
        BriefingModel.cacheItems(briefings);
        return briefings;
      }
      return <BriefingModel>[];
    }

    throw ApiException(
      ApiResponseParser.extractErrorMessage(
        jsonBody,
        fallback: fallback,
      ),
      statusCode: response.statusCode,
    );
  }

  Future<List<BriefingKeywordSectionModel>> _getTodayBriefingsGrouped(
    String token,
  ) async {
    final Uri uri = Uri.parse('${AppConfig.apiBaseUrl}/briefings/today/grouped');
    final http.Response response = await http.get(
      uri,
      headers: <String, String>{'Authorization': 'Bearer $token'},
    );

    final Map<String, dynamic> jsonBody = ApiResponseParser.decodeJsonObject(
      response.body,
    );
    if (response.statusCode >= 200 && response.statusCode < 300) {
      final dynamic keywords = jsonBody['keywords'];
      if (keywords is! List) {
        return <BriefingKeywordSectionModel>[];
      }

      final List<BriefingKeywordSectionModel> sections =
          <BriefingKeywordSectionModel>[];
      for (final dynamic keywordBlock in keywords) {
        if (keywordBlock is! Map<String, dynamic>) {
          continue;
        }
        final String keyword = (keywordBlock['keyword']?.toString() ?? '기타')
            .trim();
        final String sectionHeadline =
            (keywordBlock['headline']?.toString() ?? '').trim();
        final String sectionSummary =
            (keywordBlock['summary']?.toString() ?? '').trim();
        final dynamic rawItems = keywordBlock['items'];
        if (rawItems is! List) {
          continue;
        }
        final List<BriefingModel> items = <BriefingModel>[];
        for (final dynamic item in rawItems) {
          if (item is! Map<String, dynamic>) {
            continue;
          }
          final String title = (item['title']?.toString() ?? '').trim();
          if (title.isEmpty) {
            continue;
          }
          final String summary =
              (item['summary']?.toString() ?? '').trim().isNotEmpty
              ? item['summary'].toString().trim()
              : (sectionSummary.isNotEmpty ? sectionSummary : title);

          final String id = (item['id']?.toString() ?? '').trim().isNotEmpty
              ? item['id'].toString().trim()
              : '${keyword}_${title.hashCode.abs()}';
          final DateTime publishedAt =
              DateTime.tryParse(item['pub_date']?.toString() ?? '') ??
              DateTime.now();

          items.add(
            BriefingModel(
              id: id,
              category: keyword,
              title: title,
              summary: summary,
              highlights: <String>[summary],
              imageUrl: (() {
                final String value =
                    (item['image_url']?.toString() ?? '').trim();
                if (value.isNotEmpty) {
                  return value;
                }
                final String url = (item['url']?.toString() ?? '').trim();
                if (url.isNotEmpty) {
                  return 'https://image.thum.io/get/width/1200/noanimate/$url';
                }
                return 'https://picsum.photos/seed/$id/1200/675';
              })(),
              sourceName:
                  (item['source_type']?.toString() ?? 'Redis Feed').trim(),
              publishedAt: publishedAt,
              readTimeMinutes: 1,
              originalUrl: item['url']?.toString(),
            ),
          );
        }
        sections.add(
          BriefingKeywordSectionModel(
            keyword: keyword,
            headline: sectionHeadline,
            summary: sectionSummary,
            items: items,
          ),
        );
      }

      return sections;
    }

    throw ApiException(
      ApiResponseParser.extractErrorMessage(
        jsonBody,
        fallback: '브리핑 조회에 실패했습니다.',
      ),
      statusCode: response.statusCode,
    );
  }
}

class BriefingKeywordSectionModel {
  const BriefingKeywordSectionModel({
    required this.keyword,
    required this.headline,
    required this.summary,
    required this.items,
  });

  final String keyword;
  final String headline;
  final String summary;
  final List<BriefingModel> items;
}
