import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/locale_provider.dart';
import '../services/app_localizations.dart';

/// Settings screen — language, notifications, data usage, about.
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool _notificationsEnabled = true;
  bool _wifiOnlySync = true;
  bool _compressImages = true;
  String _selectedLanguage = 'sw';

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _notificationsEnabled = prefs.getBool('notifications') ?? true;
      _wifiOnlySync = prefs.getBool('wifi_only') ?? true;
      _compressImages = prefs.getBool('compress_images') ?? true;
      _selectedLanguage = prefs.getString('language') ?? 'sw';
    });
  }

  Future<void> _saveSetting(String key, dynamic value) async {
    final prefs = await SharedPreferences.getInstance();
    if (value is bool) {
      await prefs.setBool(key, value);
    } else if (value is String) {
      await prefs.setString(key, value);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final localeProvider = context.watch<LocaleProvider>();

    return Scaffold(
      appBar: AppBar(title: Text(l10n.settings)),
      body: ListView(
        children: [
          // Language section
          _buildSectionHeader(l10n.language, Icons.language),
          _buildLanguageSelector(l10n, localeProvider),

          const Divider(height: 1),

          // Notifications
          _buildSectionHeader(l10n.notifications, Icons.notifications),
          SwitchListTile(
            title: Text(l10n.enableNotifications),
            subtitle: Text(l10n.enableNotificationsDesc),
            value: _notificationsEnabled,
            onChanged: (value) {
              setState(() => _notificationsEnabled = value);
              _saveSetting('notifications', value);
            },
            secondary: const Icon(Icons.notifications_active),
          ),

          const Divider(height: 1),

          // Data usage
          _buildSectionHeader(l10n.dataUsage, Icons.data_usage),
          SwitchListTile(
            title: Text(l10n.wifiOnly),
            subtitle: Text(l10n.wifiOnlyDesc),
            value: _wifiOnlySync,
            onChanged: (value) {
              setState(() => _wifiOnlySync = value);
              _saveSetting('wifi_only', value);
            },
            secondary: const Icon(Icons.wifi),
          ),
          SwitchListTile(
            title: Text(l10n.compressImages),
            subtitle: Text(l10n.compressImagesDesc),
            value: _compressImages,
            onChanged: (value) {
              setState(() => _compressImages = value);
              _saveSetting('compress_images', value);
            },
            secondary: const Icon(Icons.compress),
          ),

          const Divider(height: 1),

          // About
          _buildSectionHeader(l10n.about, Icons.info),
          ListTile(
            leading: const Icon(Icons.info_outline),
            title: Text(l10n.aboutApp),
            subtitle: const Text('Mining Super-Agent v1.0.0'),
            onTap: () => _showAboutDialog(l10n),
          ),
          ListTile(
            leading: const Icon(Icons.help_outline),
            title: Text(l10n.help),
            subtitle: Text(l10n.helpDesc),
            onTap: () => _showHelpDialog(l10n),
          ),
          ListTile(
            leading: const Icon(Icons.description),
            title: Text(l10n.termsOfService),
            onTap: () {},
          ),
          ListTile(
            leading: const Icon(Icons.privacy_tip),
            title: Text(l10n.privacyPolicy),
            onTap: () {},
          ),

          const SizedBox(height: 32),

          // Version info
          Center(
            child: Text(
              'Mining Super-Agent v1.0.0\nBuilt for Kenyan miners',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.grey[500],
                fontSize: 12,
              ),
            ),
          ),
          const SizedBox(height: 32),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(String title, IconData icon) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: Row(
        children: [
          Icon(icon, size: 20, color: Theme.of(context).colorScheme.primary),
          const SizedBox(width: 8),
          Text(
            title,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: Theme.of(context).colorScheme.primary,
              letterSpacing: 0.5,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLanguageSelector(AppLocalizations l10n, LocaleProvider localeProvider) {
    final languages = [
      {'code': 'sw', 'name': 'Kiswahili', 'flag': '🇰🇪'},
      {'code': 'en', 'name': 'English', 'flag': '🇬🇧'},
      {'code': 'luo', 'name': 'Dholuo', 'flag': '🇰🇪'},
      {'code': 'kam', 'name': 'Kikamba', 'flag': '🇰🇪'},
      {'code': 'luy', 'name': 'Luluhya', 'flag': '🇰🇪'},
    ];

    return Column(
      children: languages.map((lang) {
        final isSelected = _selectedLanguage == lang['code'];
        return RadioListTile<String>(
          title: Row(
            children: [
              Text(lang['flag']!, style: const TextStyle(fontSize: 20)),
              const SizedBox(width: 8),
              Text(lang['name']!),
            ],
          ),
          value: lang['code']!,
          groupValue: _selectedLanguage,
          onChanged: (value) {
            if (value != null) {
              setState(() => _selectedLanguage = value);
              _saveSetting('language', value);
              localeProvider.setLocale(Locale(value));
            }
          },
          activeColor: Theme.of(context).colorScheme.primary,
        );
      }).toList(),
    );
  }

  void _showAboutDialog(AppLocalizations l10n) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(l10n.aboutApp),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.aboutDescription),
            const SizedBox(height: 16),
            Text(l10n.aboutFeatures, style: const TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            Text('• ${l10n.featureMineralId}'),
            Text('• ${l10n.featurePriceCheck}'),
            Text('• ${l10n.featureOffline}'),
            Text('• ${l10n.featureReports}'),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.orange.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                l10n.aboutDisclaimer,
                style: const TextStyle(fontSize: 12),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(l10n.close),
          ),
        ],
      ),
    );
  }

  void _showHelpDialog(AppLocalizations l10n) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(l10n.help),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildHelpItem(l10n.howToTakePhoto, l10n.howToTakePhotoAnswer),
              _buildHelpItem(l10n.howToCheckPrices, l10n.howToCheckPricesAnswer),
              _buildHelpItem(l10n.howToViewReports, l10n.howToViewReportsAnswer),
              _buildHelpItem(l10n.howOfflineWorks, l10n.howOfflineWorksAnswer),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(l10n.close),
          ),
        ],
      ),
    );
  }

  Widget _buildHelpItem(String question, String answer) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(question, style: const TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          Text(answer),
        ],
      ),
    );
  }
}
