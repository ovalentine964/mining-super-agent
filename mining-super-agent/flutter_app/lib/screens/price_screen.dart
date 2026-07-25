import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:fl_chart/fl_chart.dart';
import '../services/api_client.dart';
import '../services/app_localizations.dart';
import '../models/commodity_price.dart';

/// Price checker screen — real-time gold, copper, rare earth prices.
/// Shows KES and USD with trend indicators.
class PriceScreen extends StatefulWidget {
  const PriceScreen({super.key});

  @override
  State<PriceScreen> createState() => _PriceScreenState();
}

class _PriceScreenState extends State<PriceScreen> {
  List<CommodityPrice> _prices = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadPrices();
  }

  Future<void> _loadPrices() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final api = context.read<ApiClient>();
      final prices = await api.getCommodityPrices();
      setState(() {
        _prices = prices;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _error = 'Failed to load prices: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.priceCheck),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadPrices,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _buildError(l10n)
              : RefreshIndicator(
                  onRefresh: _loadPrices,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      _buildHeader(l10n),
                      const SizedBox(height: 16),
                      ..._prices.map(_buildPriceCard),
                      const SizedBox(height: 16),
                      _buildDisclaimer(l10n),
                    ],
                  ),
                ),
    );
  }

  Widget _buildHeader(AppLocalizations l10n) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            Theme.of(context).colorScheme.primaryContainer,
            Theme.of(context).colorScheme.primaryContainer.withOpacity(0.6),
          ],
        ),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        children: [
          const Icon(Icons.trending_up, size: 40),
          const SizedBox(height: 8),
          Text(
            l10n.livePrices,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          Text(
            '${l10n.updated}: ${DateTime.now().toString().substring(0, 16)}',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }

  Widget _buildPriceCard(CommodityPrice price) {
    final isUp = price.changePercent >= 0;
    final trendColor = isUp ? Colors.green : Colors.red;
    final trendIcon = isUp ? Icons.trending_up : Icons.trending_down;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Row(
              children: [
                // Commodity icon
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    color: _getCommodityColor(price.symbol).withOpacity(0.15),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(
                    _getCommodityIcon(price.symbol),
                    color: _getCommodityColor(price.symbol),
                    size: 28,
                  ),
                ),
                const SizedBox(width: 12),

                // Name & symbol
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        price.name,
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      Text(
                        price.symbol,
                        style: const TextStyle(color: Colors.grey),
                      ),
                    ],
                  ),
                ),

                // Trend
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Icon(trendIcon, color: trendColor, size: 24),
                    Text(
                      '${isUp ? '+' : ''}${price.changePercent.toStringAsFixed(2)}%',
                      style: TextStyle(
                        color: trendColor,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ],
            ),

            const SizedBox(height: 12),
            const Divider(),
            const SizedBox(height: 8),

            // Prices in USD and KES
            Row(
              children: [
                _buildPriceColumn('USD', '\$${price.priceUsd.toStringAsFixed(2)}', price.unit),
                const SizedBox(width: 16),
                _buildPriceColumn('KES', 'KES ${price.priceKes.toStringAsFixed(0)}', price.unit),
              ],
            ),

            // Mini chart (7-day sparkline)
            if (price.history.isNotEmpty) ...[
              const SizedBox(height: 12),
              SizedBox(
                height: 60,
                child: _buildSparkline(price.history, trendColor),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildPriceColumn(String currency, String value, String unit) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            currency,
            style: const TextStyle(color: Colors.grey, fontSize: 12),
          ),
          Text(
            value,
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
          ),
          Text(
            '/$unit',
            style: const TextStyle(color: Colors.grey, fontSize: 12),
          ),
        ],
      ),
    );
  }

  Widget _buildSparkline(List<double> data, Color color) {
    return LineChart(
      LineChartData(
        gridData: const FlGridData(show: false),
        titlesData: const FlTitlesData(show: false),
        borderData: FlBorderData(show: false),
        lineBarsData: [
          LineChartBarData(
            spots: data.asMap().entries.map((e) {
              return FlSpot(e.key.toDouble(), e.value);
            }).toList(),
            isCurved: true,
            color: color,
            barWidth: 2,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(
              show: true,
              color: color.withOpacity(0.1),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDisclaimer(AppLocalizations l10n) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.orange.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.info_outline, color: Colors.orange, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              l10n.priceDisclaimer,
              style: const TextStyle(fontSize: 12),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildError(AppLocalizations l10n) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_outline, size: 64, color: Colors.red),
          const SizedBox(height: 16),
          Text(_error!, textAlign: TextAlign.center),
          const SizedBox(height: 16),
          ElevatedButton.icon(
            onPressed: _loadPrices,
            icon: const Icon(Icons.refresh),
            label: Text(l10n.retry),
          ),
        ],
      ),
    );
  }

  Color _getCommodityColor(String symbol) {
    switch (symbol.toUpperCase()) {
      case 'XAU':
        return const Color(0xFFFFD700); // Gold
      case 'CU':
        return const Color(0xFFB87333); // Copper
      case 'ND':
        return const Color(0xFF7B68EE); // Neodymium
      case 'LA':
        return const Color(0xFF4A7C59); // Lanthanum
      case 'CE':
        return const Color(0xFFFF6347); // Cerium
      default:
        return Colors.grey;
    }
  }

  IconData _getCommodityIcon(String symbol) {
    switch (symbol.toUpperCase()) {
      case 'XAU':
        return Icons.monetization_on;
      case 'CU':
        return Icons.hardware;
      case 'ND':
      case 'LA':
      case 'CE':
        return Icons.science;
      default:
        return Icons.show_chart;
    }
  }
}
