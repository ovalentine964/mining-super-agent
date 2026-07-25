import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/offline_sync.dart';
import '../services/app_localizations.dart';
import 'photo_screen.dart';
import 'price_screen.dart';
import 'report_screen.dart';
import 'settings_screen.dart';

/// Home screen with 4-tile icon grid.
/// Designed for illiterate users: icons are primary, text is secondary.
/// All touch targets ≥48dp. Swahili labels default.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final sync = context.watch<OfflineSyncService>();
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.appTitle),
        actions: [
          // Connectivity indicator
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Icon(
              sync.isOnline ? Icons.wifi : Icons.wifi_off,
              color: sync.isOnline ? Colors.green : Colors.red,
              size: 28,
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Welcome banner
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      colorScheme.primaryContainer,
                      colorScheme.primaryContainer.withOpacity(0.6),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Column(
                  children: [
                    Icon(
                      Icons.landscape,
                      size: 48,
                      color: colorScheme.onPrimaryContainer,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      l10n.welcomeMessage,
                      style: theme.textTheme.titleLarge?.copyWith(
                        color: colorScheme.onPrimaryContainer,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    if (!sync.isOnline) ...[
                      const SizedBox(height: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: Colors.orange.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.cloud_off, size: 16, color: Colors.orange),
                            const SizedBox(width: 4),
                            Text(
                              l10n.offlineMode,
                              style: const TextStyle(color: Colors.orange, fontWeight: FontWeight.w600),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ],
                ),
              ),

              const SizedBox(height: 24),

              // 4-tile grid
              Expanded(
                child: GridView.count(
                  crossAxisCount: 2,
                  mainAxisSpacing: 16,
                  crossAxisSpacing: 16,
                  childAspectRatio: 1.0,
                  children: [
                    _buildTile(
                      context,
                      icon: Icons.camera_alt,
                      label: l10n.photoAnalysis,
                      subtitle: l10n.photoAnalysisDesc,
                      color: Colors.blue,
                      onTap: () => _navigate(context, const PhotoScreen()),
                    ),
                    _buildTile(
                      context,
                      icon: Icons.trending_up,
                      label: l10n.priceCheck,
                      subtitle: l10n.priceCheckDesc,
                      color: Colors.green,
                      onTap: () => _navigate(context, const PriceScreen()),
                    ),
                    _buildTile(
                      context,
                      icon: Icons.description,
                      label: l10n.myReports,
                      subtitle: l10n.myReportsDesc,
                      color: Colors.orange,
                      onTap: () => _navigate(context, const ReportScreen()),
                    ),
                    _buildTile(
                      context,
                      icon: Icons.settings,
                      label: l10n.settings,
                      subtitle: l10n.settingsDesc,
                      color: Colors.grey,
                      onTap: () => _navigate(context, const SettingsScreen()),
                    ),
                  ],
                ),
              ),

              // Sync status
              if (sync.pendingCount > 0)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: colorScheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          '${sync.pendingCount} ${l10n.pendingSync}',
                          style: theme.textTheme.bodyMedium,
                        ),
                      ],
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTile(
    BuildContext context, {
    required IconData icon,
    required String label,
    required String subtitle,
    required Color color,
    required VoidCallback onTap,
  }) {
    final theme = Theme.of(context);

    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Large icon — primary visual cue for illiterate users
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Icon(icon, size: 48, color: color),
              ),
              const SizedBox(height: 12),
              // Label
              Text(
                label,
                style: theme.textTheme.titleMedium,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 4),
              // Subtitle
              Text(
                subtitle,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.textTheme.bodySmall?.color?.withOpacity(0.7),
                ),
                textAlign: TextAlign.center,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _navigate(BuildContext context, Widget screen) {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => screen),
    );
  }
}
