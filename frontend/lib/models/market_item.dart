class MarketItem {
  final String symbol;
  final String baseAsset;
  final String quoteAsset;
  final double? price;
  final double changePct;
  final String session;
  final String marketStatus;
  final double pipSize;

  MarketItem({
    required this.symbol,
    required this.baseAsset,
    required this.quoteAsset,
    this.price,
    required this.changePct,
    required this.session,
    required this.marketStatus,
    this.pipSize = 0.0001,
  });

  bool get isPositive => changePct >= 0;

  String get formattedPrice {
    if (price == null) return '—';
    if (symbol.startsWith('XAU') || symbol.startsWith('BTC') || symbol.contains('100') || symbol.contains('500')) {
      return price!.toStringAsFixed(2);
    }
    if (symbol.contains('JPY')) {
      return price!.toStringAsFixed(3);
    }
    return price!.toStringAsFixed(5);
  }

  String get formattedChange {
    final sign = changePct >= 0 ? '+' : '';
    return '$sign${changePct.toStringAsFixed(2)}%';
  }

  factory MarketItem.fromJson(Map<String, dynamic> json) {
    return MarketItem(
      symbol: json['symbol'] as String,
      baseAsset: json['base_asset'] as String? ?? '',
      quoteAsset: json['quote_asset'] as String? ?? '',
      price: json['price'] != null ? (json['price'] as num).toDouble() : null,
      changePct: (json['change_pct'] as num?)?.toDouble() ?? 0.0,
      session: json['session'] as String? ?? 'Off-Session',
      marketStatus: json['market_status'] as String? ?? 'Open',
      pipSize: (json['pip_size'] as num?)?.toDouble() ?? 0.0001,
    );
  }
}
