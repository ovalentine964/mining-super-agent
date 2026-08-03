import 'package:flutter/material.dart';
import '../services/api_client.dart';

/// DAO Governance Screen — Proposals, voting, community stats
class DaoScreen extends StatefulWidget {
  const DaoScreen({super.key});

  @override
  State<DaoScreen> createState() => _DaoScreenState();
}

class _DaoScreenState extends State<DaoScreen> {
  final _apiClient = ApiClient();
  List<dynamic> _proposals = [];
  Map<String, dynamic> _stats = {};
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    try {
      final proposals = await _apiClient.get('/dao/proposals');
      final stats = await _apiClient.get('/dao/stats');
      setState(() {
        _proposals = proposals['proposals'] ?? [];
        _stats = stats;
        _loading = false;
      });
    } catch (e) {
      setState(() { _loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('DAO Governance'),
        backgroundColor: const Color(0xFF8B6914),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadData,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  _buildStatsCard(),
                  const SizedBox(height: 16),
                  _buildSectionTitle('Mapendekezo (Proposals)'),
                  if (_proposals.isEmpty)
                    _buildEmptyState()
                  else
                    ..._proposals.map((p) => _buildProposalCard(p)),
                ],
              ),
            ),
    );
  }

  Widget _buildStatsCard() {
    return Card(
      color: const Color(0xFFF5F0E0),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            const Text('Jamii (Community)', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _statItem('Wananchi', '${_stats['total_members'] ?? 0}', Icons.people),
                _statItem('Mapendekezo', '${_stats['total_proposals'] ?? 0}', Icons.description),
                _statItem('Kura', '${_stats['passed_proposals'] ?? 0}', Icons.check_circle),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _statItem(String label, String value, IconData icon) {
    return Column(
      children: [
        Icon(icon, size: 32, color: const Color(0xFF8B6914)),
        const SizedBox(height: 4),
        Text(value, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
        Text(label, style: const TextStyle(fontSize: 12)),
      ],
    );
  }

  Widget _buildSectionTitle(String title) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Text(title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
    );
  }

  Widget _buildEmptyState() {
    return const Card(
      child: Padding(
        padding: EdgeInsets.all(32),
        child: Column(
          children: [
            Icon(Icons.inbox, size: 64, color: Colors.grey),
            SizedBox(height: 16),
            Text('Hakuna mapendekezo bado', style: TextStyle(color: Colors.grey)),
            Text('No proposals yet', style: TextStyle(color: Colors.grey, fontSize: 12)),
          ],
        ),
      ),
    );
  }

  Widget _buildProposalCard(Map<String, dynamic> proposal) {
    final forPower = proposal['for_power'] ?? 0;
    final againstPower = proposal['against_power'] ?? 0;
    final total = forPower + againstPower;
    final forPercent = total > 0 ? (forPower / total * 100) : 50;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.how_to_vote, color: Color(0xFF8B6914)),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    proposal['title'] ?? 'Untitled',
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(proposal['description'] ?? ''),
            const SizedBox(height: 12),
            // Vote progress bar
            LinearProgressIndicator(
              value: forPercent / 100,
              backgroundColor: Colors.red.shade200,
              valueColor: const AlwaysStoppedAnimation<Color>(Colors.green),
              minHeight: 8,
            ),
            const SizedBox(height: 4),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('Ndio (Yes): ${forPercent.toStringAsFixed(1)}%', style: const TextStyle(color: Colors.green)),
                Text('Hapana (No): ${(100 - forPercent).toStringAsFixed(1)}%', style: const TextStyle(color: Colors.red)),
              ],
            ),
            const SizedBox(height: 12),
            // Vote buttons
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _vote(proposal['id'], true),
                    icon: const Icon(Icons.thumb_up),
                    label: const Text('Ndio (Yes)'),
                    style: ElevatedButton.styleFrom(backgroundColor: Colors.green),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _vote(proposal['id'], false),
                    icon: const Icon(Icons.thumb_down),
                    label: const Text('Hapana (No)'),
                    style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _vote(String proposalId, bool support) async {
    try {
      await _apiClient.post('/dao/proposals/$proposalId/vote', {
        'voter': 'community_member',
        'tokens': 100,
        'support': support,
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(support ? 'Kura yako imesajiliwa!' : 'Kura yako imesajiliwa!')),
      );
      _loadData();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    }
  }
}
