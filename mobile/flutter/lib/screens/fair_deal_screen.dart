import 'package:flutter/material.dart';
import '../services/api_client.dart';

/// Fair Deal Calculator Screen
/// Lets users enter a mining offer and see if it's fair or exploitative.
class FairDealScreen extends StatefulWidget {
  const FairDealScreen({super.key});

  @override
  State<FairDealScreen> createState() => _FairDealScreenState();
}

class _FairDealScreenState extends State<FairDealScreen> {
  final _offerController = TextEditingController(text: '1000000');
  final _apiClient = ApiClient();
  Map<String, dynamic>? _result;
  bool _loading = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Fair Deal Calculator'),
        backgroundColor: const Color(0xFF8B6914),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Explanation
            Card(
              color: Colors.amber.shade50,
              child: const Padding(
                padding: EdgeInsets.all(16),
                child: Column(
                  children: [
                    Icon(Icons.warning_amber, size: 48, color: Colors.amber),
                    SizedBox(height: 8),
                    Text(
                      'Hakiki Ofa ya Madini',
                      style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                    ),
                    SizedBox(height: 8),
                    Text(
                      'Enter the amount being offered for your land. '
                      'The system will tell you if the deal is fair or exploitative.',
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Offer amount input
            TextField(
              controller: _offerController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Ofa ya KES (Amount Offered)',
                hintText: 'e.g. 1000000',
                border: OutlineInputBorder(),
                prefixText: 'KES ',
              ),
            ),
            const SizedBox(height: 16),

            // Analyze button
            ElevatedButton.icon(
              onPressed: _loading ? null : _analyze,
              icon: _loading
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.analytics),
              label: Text(_loading ? 'Inachambua...' : 'Hakiki Ofa (Analyze Offer)'),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF8B6914),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
            ),
            const SizedBox(height: 24),

            // Results
            if (_result != null) ...[
              _buildResultCard(),
              const SizedBox(height: 16),
              _buildVerdictCard(),
              const SizedBox(height: 16),
              _buildActionsCard(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildResultCard() {
    final verdict = _result!['verdict'] ?? 'UNKNOWN';
    final color = verdict == 'FAIR' ? Colors.green : Colors.red;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Text(
              verdict,
              style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: color),
            ),
            const SizedBox(height: 8),
            Text(
              'Exploitation Ratio: ${(_result!['exploitation_ratio'] * 100).toStringAsFixed(1)}%',
              style: TextStyle(fontSize: 18, color: color),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildVerdictCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Uchambuzi (Analysis)', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text(_result!['explanation_sw'] ?? 'Hakuna uchambuzi'),
            const SizedBox(height: 16),
            Text(_result!['explanation_en'] ?? 'No analysis available'),
          ],
        ),
      ),
    );
  }

  Widget _buildActionsCard() {
    final actions = _result!['recommended_actions'] as List<dynamic>? ?? [];

    return Card(
      color: Colors.red.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Hatua Zinazopendekezwa (Recommended Actions)', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            ...actions.map((a) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.arrow_right, color: Colors.red),
                  const SizedBox(width: 8),
                  Expanded(child: Text(a)),
                ],
              ),
            )),
          ],
        ),
      ),
    );
  }

  Future<void> _analyze() async {
    setState(() { _loading = true; });
    try {
      final offer = int.tryParse(_offerController.text.replaceAll(',', '')) ?? 0;
      final result = await _apiClient.post('/fair-deal/evaluate', {
        'offer_amount_kes': offer,
        'minerals': [
          {'mineral': 'gold', 'estimated_kg': 50, 'confidence': 0.3},
          {'mineral': 'copper', 'estimated_kg': 5000, 'confidence': 0.4},
        ],
        'location': 'Nyatike, Migori County',
      });
      setState(() { _result = result; });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    } finally {
      setState(() { _loading = false; });
    }
  }
}
