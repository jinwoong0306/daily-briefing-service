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

  static final List<BriefingModel> mockBriefings = <BriefingModel>[
    // TODO: connect API
    BriefingModel(
      id: 'b001',
      category: 'IT/과학',
      title: 'AI 반도체 수요 증가로 클라우드 인프라 투자 확대',
      summary:
          '글로벌 클라우드 기업들이 AI 연산 수요 대응을 위해 데이터센터 증설과 전력 효율 개선에 대규모 투자를 진행하고 있습니다.',
      highlights: <String>[
        '하반기 GPU 서버 발주량이 전년 대비 증가',
        '전력 효율 중심 아키텍처 전환 가속',
        '중소 SaaS도 AI 추론 워크로드 채택 확대',
      ],
      imageUrl:
          'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&q=80',
      sourceName: 'Tech Daily',
      publishedAt: DateTime(2026, 4, 5, 7, 40),
      readTimeMinutes: 4,
    ),
    BriefingModel(
      id: 'b002',
      category: '경제',
      title: '환율 안정세 속 수출주 중심 매수세 유입',
      summary:
          '외환 변동성이 완화되며 수출 비중이 높은 업종 중심으로 매수세가 유입되고, 시장은 실적 시즌 가이던스를 주목하고 있습니다.',
      highlights: <String>[
        'IT·자동차 업종 거래대금 비중 상승',
        '원자재 가격 둔화로 마진 방어 기대',
        '실적 가이던스 상향 여부가 단기 분수령',
      ],
      imageUrl:
          'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1200&q=80',
      sourceName: 'Market Insight',
      publishedAt: DateTime(2026, 4, 5, 7, 20),
      readTimeMinutes: 3,
    ),
    BriefingModel(
      id: 'b003',
      category: '정치',
      title: '디지털 공공서비스 통합 정책 초안 공개',
      summary: '정부가 인증·민원·데이터 연계를 하나의 사용자 경험으로 묶는 디지털 공공서비스 통합 초안을 공개했습니다.',
      highlights: <String>[
        '모바일 중심 민원 처리 UX 표준 제시',
        '기관 간 데이터 연계 절차 단순화',
        '보안·개인정보 보호 가이드라인 동시 발표',
      ],
      imageUrl:
          'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1200&q=80',
      sourceName: 'Policy Brief',
      publishedAt: DateTime(2026, 4, 5, 6, 50),
      readTimeMinutes: 5,
    ),
  ];

  static BriefingModel? findById(String id) {
    for (final BriefingModel item in mockBriefings) {
      if (item.id == id) {
        return item;
      }
    }
    return null;
  }
}
