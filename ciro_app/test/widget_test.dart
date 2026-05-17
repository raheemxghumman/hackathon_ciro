import 'package:flutter_test/flutter_test.dart';

import 'package:ciro_app/main.dart';

void main() {
  testWidgets('CIRO app boots', (WidgetTester tester) async {
    await tester.pumpWidget(const CIROApp());
    expect(find.text('CIRO'), findsOneWidget);
  });
}
