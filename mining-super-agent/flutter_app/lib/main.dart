import 'package:flutter/material.dart';
import 'screens/home_screen.dart';
import 'services/app_localizations.dart';
import 'services/locale_provider.dart';
import 'package:provider/provider.dart';

void main() {
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => LocaleProvider()),
      ],
      child: const MiningApp(),
    ),
  );
}

class MiningApp extends StatelessWidget {
  const MiningApp({super.key});

  @override
  Widget build(BuildContext context) {
    final localeProvider = Provider.of<LocaleProvider>(context);

    return MaterialApp(
      title: 'Mining Super-Agent',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF8B6914), // Gold color
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      locale: localeProvider.locale,
      supportedLocales: const [
        Locale('en'), // English
        Locale('sw'), // Swahili
        Locale('luo'), // Luo
      ],
      home: const HomeScreen(),
    );
  }
}
