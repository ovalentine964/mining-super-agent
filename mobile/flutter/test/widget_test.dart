import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:sovereign_resource_dao/main.dart';
import 'package:sovereign_resource_dao/models/observation.dart';
import 'package:sovereign_resource_dao/services/locale_provider.dart';

void main() {
  group('MiningApp Widget Tests', () {
    testWidgets('App renders home screen with menu cards', (WidgetTester tester) async {
      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider(create: (_) => LocaleProvider()),
          ],
          child: const MaterialApp(home: MiningApp()),
        ),
      );

      // Allow async initialization
      await tester.pumpAndSettle(const Duration(seconds: 2));

      // Verify the app title appears
      expect(find.text('Sovereign Resource DAO'), findsOneWidget);

      // Verify menu cards exist
      expect(find.byIcon(Icons.camera_alt), findsOneWidget);
      expect(find.byIcon(Icons.trending_up), findsOneWidget);
      expect(find.byIcon(Icons.description), findsOneWidget);
      expect(find.byIcon(Icons.settings), findsOneWidget);
    });

    testWidgets('Settings screen shows language options', (WidgetTester tester) async {
      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider(create: (_) => LocaleProvider()),
          ],
          child: const MaterialApp(home: MiningApp()),
        ),
      );

      await tester.pumpAndSettle(const Duration(seconds: 2));

      // Tap on Settings
      await tester.tap(find.byIcon(Icons.settings));
      await tester.pumpAndSettle();

      // Verify language options
      expect(find.text('Language'), findsOneWidget);
      expect(find.text('English'), findsOneWidget);
      expect(find.text('Swahili'), findsOneWidget);
      expect(find.text('Luo (Dholuo)'), findsOneWidget);
      expect(find.text('Kamba (Kikamba)'), findsOneWidget);
      expect(find.text('Luhya (Oluluyia)'), findsOneWidget);
    });
  });

  group('Observation Model Tests', () {
    test('Observation serialization roundtrip', () {
      final obs = Observation(
        id: 1,
        title: 'Gold Sample',
        description: 'Found near river',
        rockType: 'Quartz',
        mineral: 'Gold',
        confidence: 0.85,
        latitude: -1.2921,
        longitude: 36.8219,
        observedAt: DateTime(2024, 6, 15, 10, 30),
        synced: false,
      );

      final map = obs.toMap();
      final restored = Observation.fromMap(map);

      expect(restored.id, equals(1));
      expect(restored.title, equals('Gold Sample'));
      expect(restored.rockType, equals('Quartz'));
      expect(restored.mineral, equals('Gold'));
      expect(restored.confidence, equals(0.85));
      expect(restored.latitude, equals(-1.2921));
      expect(restored.longitude, equals(36.8219));
      expect(restored.synced, isFalse);
    });

    test('Observation copyWith works', () {
      final obs = Observation(
        title: 'Test',
        rockType: 'Granite',
        observedAt: DateTime(2024, 1, 1),
      );

      final updated = obs.copyWith(mineral: 'Copper', confidence: 0.7);

      expect(updated.mineral, equals('Copper'));
      expect(updated.confidence, equals(0.7));
      expect(updated.title, equals('Test'));
      expect(updated.rockType, equals('Granite'));
    });

    test('Observation handles null fields gracefully', () {
      final obs = Observation(
        observedAt: DateTime.now(),
      );

      final map = obs.toMap();
      final restored = Observation.fromMap(map);

      expect(restored.title, equals(''));
      expect(restored.mineral, equals(''));
      expect(restored.confidence, equals(0.0));
      expect(restored.synced, isFalse);
    });
  });

  group('LocaleProvider Tests', () {
    test('Default locale is Swahili', () {
      final provider = LocaleProvider();
      expect(provider.locale.languageCode, equals('sw'));
    });

    test('Supported locales include all 5 languages', () {
      final locales = LocaleProvider.supportedLocales;
      expect(locales.length, equals(5));

      final codes = locales.map((l) => l.languageCode).toList();
      expect(codes, contains('en'));
      expect(codes, contains('sw'));
      expect(codes, contains('luo'));
      expect(codes, contains('kam'));
      expect(codes, contains('luy'));
    });

    test('getLanguageName returns correct names', () {
      expect(LocaleProvider.getLanguageName('en'), equals('English'));
      expect(LocaleProvider.getLanguageName('sw'), equals('Swahili'));
      expect(LocaleProvider.getLanguageName('luo'), equals('Luo (Dholuo)'));
      expect(LocaleProvider.getLanguageName('kam'), equals('Kamba (Kikamba)'));
      expect(LocaleProvider.getLanguageName('luy'), equals('Luhya (Oluluyia)'));
    });
  });
}
