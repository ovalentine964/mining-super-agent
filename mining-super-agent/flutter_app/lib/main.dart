import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';

import 'screens/home_screen.dart';
import 'services/offline_sync.dart';
import 'services/api_client.dart';
import 'services/app_localizations.dart';
import 'services/locale_provider.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Lock portrait for consistent layout
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
  ]);

  // Initialize offline sync
  await OfflineSyncService.initialize();

  runApp(const MiningSuperAgentApp());
}

class MiningSuperAgentApp extends StatelessWidget {
  const MiningSuperAgentApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => LocaleProvider()),
        ChangeNotifierProvider(create: (_) => OfflineSyncService()),
        Provider(create: (_) => ApiClient()),
      ],
      child: Consumer<LocaleProvider>(
        builder: (context, localeProvider, _) {
          return MaterialApp(
            title: 'Mining Super-Agent',
            debugShowCheckedModeBanner: false,

            // Theme — Mining-themed earth tones
            theme: _buildMiningTheme(Brightness.light),
            darkTheme: _buildMiningTheme(Brightness.dark),
            themeMode: ThemeMode.system,

            // Localization
            locale: localeProvider.locale,
            supportedLocales: const [
              Locale('sw'), // Swahili
              Locale('en'), // English
              Locale('luo'), // Luo
              Locale('kam'), // Kamba
              Locale('luy'), // Luhya
            ],
            localizationsDelegates: const [
              AppLocalizations.delegate,
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],

            // Navigation
            home: const HomeScreen(),
          );
        },
      ),
    );
  }

  ThemeData _buildMiningTheme(Brightness brightness) {
    // Mining-themed colors: earth, gold, copper, stone
    const primarySeed = Color(0xFF8B6914); // Gold ore
    const secondary = Color(0xFFB87333); // Copper
    const tertiary = Color(0xFF4A7C59); // Forest green
    const surface = Color(0xFFF5F0E8); // Sandstone

    final colorScheme = ColorScheme.fromSeed(
      seedColor: primarySeed,
      brightness: brightness,
      secondary: secondary,
      tertiary: tertiary,
      surface: brightness == Brightness.light ? surface : const Color(0xFF1A1A1A),
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      fontFamily: 'NotoSans',

      // Large touch targets for miners (48dp minimum)
      materialTapTargetSize: MaterialTapTargetSize.padded,

      appBarTheme: AppBarTheme(
        centerTitle: true,
        elevation: 0,
        backgroundColor: colorScheme.surface,
        foregroundColor: colorScheme.onSurface,
        titleTextStyle: TextStyle(
          fontFamily: 'NotoSans',
          fontSize: 20,
          fontWeight: FontWeight.w700,
          color: colorScheme.onSurface,
        ),
      ),

      cardTheme: CardTheme(
        elevation: 2,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        clipBehavior: Clip.antiAlias,
      ),

      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          minimumSize: const Size(88, 56), // 56dp height
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: const TextStyle(
            fontFamily: 'NotoSans',
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),

      inputDecorationTheme: InputDecorationTheme(
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      ),

      textTheme: const TextTheme(
        headlineLarge: TextStyle(fontSize: 28, fontWeight: FontWeight.w700),
        headlineMedium: TextStyle(fontSize: 24, fontWeight: FontWeight.w600),
        titleLarge: TextStyle(fontSize: 20, fontWeight: FontWeight.w600),
        titleMedium: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        bodyLarge: TextStyle(fontSize: 16, fontWeight: FontWeight.w400),
        bodyMedium: TextStyle(fontSize: 14, fontWeight: FontWeight.w400),
        labelLarge: TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
      ),
    );
  }
}
