import 'package:flutter/material.dart';

class PriceScreen extends StatefulWidget {
  const PriceScreen({super.key});

  @override
  State<PriceScreen> createState() => _PriceScreenState();
}

class _PriceScreenState extends State<PriceScreen> {
  bool _loading = true;
  List<Map<String, dynamic>> _prices = [];

  @override
  void initState() {
    super.initState();
    _loadPrices();
  }

  Future<void> _loadPrices() async {
    // TODO: Fetch from API
    await Future.delayed(const Duration(seconds: 1));
    setState(() {
      _loading = false;
      _prices = [
        {'name': 'Gold', 'symbol': 'Au', 'price': '2,650.00', 'unit': 'USD/oz', 'change': '+1.2%'},
        {'name': 'Copper', 'symbol': 'Cu', 'price': '9,450.00', 'unit': 'USD/ton', 'change': '-0.5%'},
        {'name': 'Silver', 'symbol': 'Ag', 'price': '31.50', 'unit': 'USD/oz', 'change': '+0.8%'},
      ];
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Market Prices'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              setState(() { _loading = true; });
              _loadPrices();
            },
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _prices.length,
              itemBuilder: (context, index) {
                final p = _prices[index];
                final isPositive = (p['change'] as String).startsWith('+');
                return Card(
                  child: ListTile(
                    leading: CircleAvatar(
                      child: Text(p['symbol']),
                    ),
                    title: Text(p['name'], style: const TextStyle(fontWeight: FontWeight.bold)),
                    subtitle: Text(p['unit']),
                    trailing: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text('\$${p['price']}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                        Text(
                          p['change'],
                          style: TextStyle(
                            color: isPositive ? Colors.green : Colors.red,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
    );
  }
}
