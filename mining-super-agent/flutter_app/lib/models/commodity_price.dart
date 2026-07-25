/// Commodity price model for market data.
class CommodityPrice {
  final String symbol;
  final String name;
  final double priceUsd;
  final double priceKes;
  final double changePercent;
  final String unit;
  final List<double> history; // 7-day price history

  CommodityPrice({
    required this.symbol,
    required this.name,
    required this.priceUsd,
    required this.priceKes,
    required this.changePercent,
    required this.unit,
    this.history = const [],
  });

  factory CommodityPrice.fromJson(Map<String, dynamic> json) {
    return CommodityPrice(
      symbol: json['symbol'] as String? ?? '',
      name: json['name'] as String? ?? '',
      priceUsd: (json['price_usd'] as num?)?.toDouble() ?? 0.0,
      priceKes: (json['price_kes'] as num?)?.toDouble() ?? 0.0,
      changePercent: (json['change_percent'] as num?)?.toDouble() ?? 0.0,
      unit: json['unit'] as String? ?? 'oz',
      history: (json['history'] as List<dynamic>?)
              ?.map((e) => (e as num).toDouble())
              .toList() ??
          [],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'symbol': symbol,
      'name': name,
      'price_usd': priceUsd,
      'price_kes': priceKes,
      'change_percent': changePercent,
      'unit': unit,
      'history': history,
    };
  }
}
