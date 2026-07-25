import 'package:flutter/material.dart';
import 'photo_screen.dart';
import 'price_screen.dart';
import 'report_screen.dart';
import 'settings_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mining Super-Agent'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: GridView.count(
        padding: const EdgeInsets.all(16),
        crossAxisCount: 2,
        mainAxisSpacing: 16,
        crossAxisSpacing: 16,
        children: [
          _MenuCard(
            icon: Icons.camera_alt,
            label: 'Identify Mineral',
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const PhotoScreen()),
            ),
          ),
          _MenuCard(
            icon: Icons.trending_up,
            label: 'Market Prices',
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const PriceScreen()),
            ),
          ),
          _MenuCard(
            icon: Icons.description,
            label: 'Reports',
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const ReportScreen()),
            ),
          ),
          _MenuCard(
            icon: Icons.settings,
            label: 'Settings',
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const SettingsScreen()),
            ),
          ),
        ],
      ),
    );
  }
}

class _MenuCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _MenuCard({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 48, color: Theme.of(context).colorScheme.primary),
            const SizedBox(height: 8),
            Text(
              label,
              style: Theme.of(context).textTheme.titleMedium,
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
