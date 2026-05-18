class BriefingModel {
  const BriefingModel({
    required this.id,
    required this.category,
    required this.title,
    required this.summary,
    required this.highlights,
    required this.imageUrl,
    required this.sourceName,
    required this.publishedAt,
    required this.readTimeMinutes,
    this.originalUrl,
    this.isBookmarked = false,
    this.feedbackType,
  });

  final String id;
  final String category;
  final String title;
  final String summary;
  final List<String> highlights;
  final String imageUrl;
  final String sourceName;
  final DateTime publishedAt;
  final int readTimeMinutes;
  final String? originalUrl;
  final bool isBookmarked;
  final String? feedbackType;

  static final Map<String, BriefingModel> _cache = <String, BriefingModel>{};

  static String _fallbackThumbnail({
    required String id,
    required String? originalUrl,
  }) {
    final String url = (originalUrl ?? '').trim();
    if (url.isNotEmpty) {
      return 'https://image.thum.io/get/width/1200/noanimate/$url';
    }
    return 'https://picsum.photos/seed/$id/1200/675';
  }

  static void cacheItems(List<BriefingModel> items) {
    _cache
      ..clear()
      ..addEntries(items.map((BriefingModel item) => MapEntry<String, BriefingModel>(item.id, item)));
  }

  factory BriefingModel.fromJson(Map<String, dynamic> json) {
    final dynamic id = json['id'];
    final dynamic category = json['category'];
    final dynamic title = json['title'];
    final dynamic summary = json['summary'];
    final dynamic highlights = json['highlights'];
    final dynamic imageUrl = json['image_url'];
    final dynamic sourceName = json['source_name'];
    final dynamic publishedAt = json['published_at'];
    final dynamic readTimeMinutes = json['read_time_minutes'];
    final dynamic originalUrl = json['original_url'];

    return BriefingModel(
      id: id?.toString() ?? '',
      category: category is String ? category : '기타',
      title: title is String ? title : '제목 없음',
      summary: summary is String ? summary : '',
      highlights: highlights is List
          ? highlights.whereType<String>().toList()
          : <String>[],
      imageUrl: imageUrl is String && imageUrl.isNotEmpty
          ? imageUrl
          : _fallbackThumbnail(
              id: id?.toString() ?? '',
              originalUrl: originalUrl is String ? originalUrl : null,
            ),
      sourceName: sourceName is String ? sourceName : 'News Source',
      publishedAt: DateTime.tryParse(publishedAt?.toString() ?? '') ?? DateTime.now(),
      readTimeMinutes: readTimeMinutes is int ? readTimeMinutes : 1,
      originalUrl: originalUrl is String ? originalUrl : null,
      isBookmarked: json['is_bookmarked'] == true,
      feedbackType: json['feedback_type'] is String
          ? json['feedback_type'] as String
          : null,
    );
  }

  BriefingModel copyWith({
    String? id,
    String? category,
    String? title,
    String? summary,
    List<String>? highlights,
    String? imageUrl,
    String? sourceName,
    DateTime? publishedAt,
    int? readTimeMinutes,
    String? originalUrl,
    bool? isBookmarked,
    String? feedbackType,
  }) {
    return BriefingModel(
      id: id ?? this.id,
      category: category ?? this.category,
      title: title ?? this.title,
      summary: summary ?? this.summary,
      highlights: highlights ?? this.highlights,
      imageUrl: imageUrl ?? this.imageUrl,
      sourceName: sourceName ?? this.sourceName,
      publishedAt: publishedAt ?? this.publishedAt,
      readTimeMinutes: readTimeMinutes ?? this.readTimeMinutes,
      originalUrl: originalUrl ?? this.originalUrl,
      isBookmarked: isBookmarked ?? this.isBookmarked,
      feedbackType: feedbackType ?? this.feedbackType,
    );
  }

  static BriefingModel? findById(String id) {
    return _cache[id];
  }
}
