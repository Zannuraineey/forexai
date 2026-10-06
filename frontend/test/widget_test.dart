import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/main.dart';

void main() {
  testWidgets('ForexAIApp smoke test', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const ForexAIApp());

    // Verify app bar title
    expect(find.text('Forex AI Market Platform'), findsOneWidget);
    expect(find.text('Dashboard'), findsOneWidget);
    expect(find.text('AI Analysis'), findsOneWidget);
    expect(find.text('Instructions'), findsOneWidget);
  });
}
