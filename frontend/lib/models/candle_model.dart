class CandleModel {
  final int id;
  final DateTime timestamp;
  final double open;
  final double high;
  final double low;
  final double close;
  final double volume;

  CandleModel({
    required this.id,
    required this.timestamp,
    required this.open,
    required this.high,
    required this.low,
    required this.close,
    required this.volume,
  });

  bool get isBullish => close >= open;

  factory CandleModel.fromJson(Map<String, dynamic> json) {
    return CandleModel(
      id: json['id'] as int? ?? 0,
      timestamp: DateTime.tryParse(json['timestamp_utc']?.toString() ?? '') ?? DateTime.now(),
      open: (json['open'] as num).toDouble(),
      high: (json['high'] as num).toDouble(),
      low: (json['low'] as num).toDouble(),
      close: (json['close'] as num).toDouble(),
      volume: (json['volume'] as num?)?.toDouble() ?? 0.0,
    );
  }
}
