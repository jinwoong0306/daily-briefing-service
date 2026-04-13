import 'package:flutter_test/flutter_test.dart';

import 'package:news/main.dart';

void main() {
  testWidgets('로그인 화면이 기본으로 노출된다', (WidgetTester tester) async {
    await tester.pumpWidget(const DailyBriefingApp());
    await tester.pumpAndSettle();

    expect(find.text('다시 오신 것을 환영합니다'), findsOneWidget);
    expect(find.text('로그인'), findsOneWidget);
  });
}
