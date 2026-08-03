import 'package:flutter/material.dart';
import 'photo_screen.dart';
import 'price_screen.dart';
import 'report_screen.dart';
import 'settings_screen.dart';
import 'fair_deal_screen.dart';
import 'dao_screen.dart';
import 'agent_chat_screen.dart';
import 'voice_chat_screen.dart';
import 'blockchain_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Sovereign Resource DAO'),
        backgroundColor: const Color(0xFF8B6914),
      ),
      body: GridView.count(
        padding: const EdgeInsets.all(16),
        crossAxisCount: 2,
        mainAxisSpacing: 16,
        crossAxisSpacing: 16,
        children: [
          _MenuCard(
            icon: Icons.camera_alt,
            label: 'Tambua Madini\nIdentify Mineral',
            color: Colors.blue,
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const PhotoScreen()),
            ),
          ),
          _MenuCard(
            icon: Icons.trending_up,
            label: 'Bei za Soko\nMarket Prices',
            color: Colors.green,
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const PriceScreen()),
            ),
          ),
          _MenuCard(
            icon: Icons.calculate,
            label: 'Hakiki Ofa\nFair Deal',
            color: Colors.amber,
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const FairDealScreen()),
            ),
          ),
          _MenuCard(
            icon: Icons.how_to_vote,
            label: 'Uongozi\nDAO Governance',
            color: Colors.purple,
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const DaoScreen()),
            ),
          ),
          _MenuCard(
            icon: Icons.chat,
            label: 'Mazungumzo\nAgent Chat',
            color: Colors.teal,
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const AgentChatScreen()),
            ),
          ),
          _MenuCard(
            icon: Icons.record_voice_over,
            label: 'Sauti\nVoice Talk',
            color: Colors.red,
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const VoiceChatScreen()),
            ),
          ),
          _MenuCard(
            icon: Icons.link,
            label: 'Blockchain\nStatus',
            color: Colors.indigo,
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const BlockchainScreen()),
            ),
          ),
          _MenuCard(
            icon: Icons.description,
            label: 'Ripoti\nReports',
            color: Colors.orange,
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const ReportScreen()),
            ),
          ),
          _MenuCard(
            icon: Icons.settings,
            label: 'Mipangilio\nSettings',
            color: Colors.grey,
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
  final Color color;
  final VoidCallback onTap;

  const _MenuCard({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 4,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 40, color: color),
              const SizedBox(height: 8),
              Text(
                label,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
