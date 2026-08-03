class CommodityPrice {
  final String name;
  final String symbol;
  final double price;
  final String currency;
  final String unit;
  final double changePercent;
  final DateTime timestamp;

  CommodityPrice({
    required this.name,
    required this.symbol,
    required this.price,
    required this.currency,
    required this.unit,
    required this.changePercent,
    required this.timestamp,
  });

  factory CommodityPrice.fromJson(Map<String, dynamic> json) {
    return CommodityPrice(
      name: json['name'] ?? '',
      symbol: json['symbol'] ?? '',
      price: (json['price'] ?? 0).toDouble(),
      currency: json['currency'] ?? 'USD',
      unit: json['unit'] ?? '',
      changePercent: (json['change_percent'] ?? 0).toDouble(),
      timestamp: DateTime.parse(json['timestamp'] ?? DateTime.now().toIso8601String()),
    );
  }
}
