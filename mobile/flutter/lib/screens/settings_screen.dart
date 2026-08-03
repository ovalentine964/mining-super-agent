import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/locale_provider.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final localeProvider = Provider.of<LocaleProvider>(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        children: [
          const _SectionHeader('Language'),
          _LanguageTile(
            language: 'English',
            locale: const Locale('en'),
            current: localeProvider.locale,
            onTap: () => localeProvider.setLocale(const Locale('en')),
          ),
          _LanguageTile(
            language: 'Swahili',
            locale: const Locale('sw'),
            current: localeProvider.locale,
            onTap: () => localeProvider.setLocale(const Locale('sw')),
          ),
          _LanguageTile(
            language: 'Luo',
            locale: const Locale('luo'),
            current: localeProvider.locale,
            onTap: () => localeProvider.setLocale(const Locale('luo')),
          ),
          const Divider(),
          const _SectionHeader('Server'),
          ListTile(
            title: const Text('API Server'),
            subtitle: const Text('http://localhost:8000'),
            trailing: const Icon(Icons.edit),
            onTap: () {
              // TODO: Server configuration
            },
          ),
          const Divider(),
          const _SectionHeader('About'),
          const ListTile(
            title: Text('Sovereign Resource DAO'),
            subtitle: Text('Version 1.0.0\nAI-powered mineral identification for Kenyan miners'),
          ),
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  const _SectionHeader(this.title);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: Text(title, style: TextStyle(
        fontSize: 14,
        fontWeight: FontWeight.bold,
        color: Theme.of(context).colorScheme.primary,
      )),
    );
  }
}

class _LanguageTile extends StatelessWidget {
  final String language;
  final Locale locale;
  final Locale current;
  final VoidCallback onTap;

  const _LanguageTile({
    required this.language,
    required this.locale,
    required this.current,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isSelected = locale == current;
    return ListTile(
      title: Text(language),
      trailing: isSelected ? Icon(Icons.check, color: Theme.of(context).colorScheme.primary) : null,
      onTap: onTap,
    );
  }
}
