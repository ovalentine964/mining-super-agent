import 'package:flutter/material.dart';
import '../services/api_client.dart';

/// Blockchain Status Screen — Polygon connection, extraction records, royalties
class BlockchainScreen extends StatefulWidget {
  const BlockchainScreen({super.key});

  @override
  State<BlockchainScreen> createState() => _BlockchainScreenState();
}

class _BlockchainScreenState extends State<BlockchainScreen> {
  final _apiClient = ApiClient();
  Map<String, dynamic> _status = {};
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadStatus();
  }

  Future<void> _loadStatus() async {
    try {
      final status = await _apiClient.get('/chain/status');
      setState(() {
        _status = status;
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
        title: const Text('Blockchain Status'),
        backgroundColor: const Color(0xFF8B6914),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadStatus,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  _buildConnectionCard(),
                  const SizedBox(height: 16),
                  _buildContractCard(),
                  const SizedBox(height: 16),
                  _buildExtractionCard(),
                  const SizedBox(height: 16),
                  _buildRoyaltyCard(),
                ],
              ),
            ),
    );
  }

  Widget _buildConnectionCard() {
    final connected = _status['connected'] ?? false;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Icon(
              connected ? Icons.check_circle : Icons.error,
              size: 48,
              color: connected ? Colors.green : Colors.red,
            ),
            const SizedBox(height: 8),
            Text(
              connected ? 'Imeunganishwa (Connected)' : 'Haijaunganishwa (Disconnected)',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: connected ? Colors.green : Colors.red,
              ),
            ),
            const SizedBox(height: 8),
            Text('Chain ID: ${_status['chain_id'] ?? 'Unknown'}'),
            Text('Block: ${_status['latest_block'] ?? 'Unknown'}'),
            Text('Balance: ${_status['balance_matic'] ?? '0'} MATIC'),
          ],
        ),
      ),
    );
  }

  Widget _buildContractCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Smart Contracts', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            _contractRow('RoyaltyDistributor', '0x...'),
            _contractRow('ExtractionTracker', '0x...'),
            _contractRow('GovernanceToken', '0x...'),
            _contractRow('QuadraticVoting', '0x...'),
            _contractRow('MiningOracle', '0x...'),
          ],
        ),
      ),
    );
  }

  Widget _contractRow(String name, String address) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          const Icon(Icons.circle, size: 8, color: Colors.green),
          const SizedBox(width: 8),
          Text(name, style: const TextStyle(fontWeight: FontWeight.w500)),
          const Spacer(),
          Text(address, style: const TextStyle(fontSize: 12, color: Colors.grey)),
        ],
      ),
    );
  }

  Widget _buildExtractionCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Extraction Records', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            const Center(
              child: Column(
                children: [
                  Icon(Icons.inventory_2, size: 48, color: Colors.grey),
                  SizedBox(height: 8),
                  Text('Hakuna rekodi bado', style: TextStyle(color: Colors.grey)),
                  Text('No extraction records yet', style: TextStyle(color: Colors.grey, fontSize: 12)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRoyaltyCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Royalty Distributions', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            const Center(
              child: Column(
                children: [
                  Icon(Icons.account_balance_wallet, size: 48, color: Colors.grey),
                  SizedBox(height: 8),
                  Text('Hakuna malipo bado', style: TextStyle(color: Colors.grey)),
                  Text('No royalty distributions yet', style: TextStyle(color: Colors.grey, fontSize: 12)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
