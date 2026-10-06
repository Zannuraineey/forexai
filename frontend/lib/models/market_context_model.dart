class MarketContextData {
  final String symbol;
  final String timeframe;
  final String trend;
  final String volatility;
  final String structure;
  final String range;
  final double rsi;
  final double atr;

  MarketContextData({
    required this.symbol,
    required this.timeframe,
    required this.trend,
    required this.volatility,
    required this.structure,
    required this.range,
    required this.rsi,
    required this.atr,
  });

  factory MarketContextData.fromJson(Map<String, dynamic> json) {
    final indicators = json['indicators'] as Map<String, dynamic>? ?? {};
    final struct = json['structure'] as Map<String, dynamic>? ?? {};
    final rsiVal = (indicators['rsi'] as num?)?.toDouble() ?? 50.0;
    final atrVal = (indicators['atr'] as num?)?.toDouble() ?? 0.0;
    final adxVal = (indicators['adx'] as num?)?.toDouble() ?? 20.0;

    // Trend interpretation
    final ema9 = (indicators['ema_9'] as num?)?.toDouble() ?? 0;
    final ema21 = (indicators['ema_21'] as num?)?.toDouble() ?? 0;
    final ema50 = (indicators['ema_50'] as num?)?.toDouble() ?? 0;
    String trendStr = 'Neutral';
    if (ema9 > ema21 && ema21 > ema50) {
      trendStr = 'Bullish (EMA 9 > 21 > 50, ADX: ${adxVal.toStringAsFixed(1)})';
    } else if (ema9 < ema21 && ema21 < ema50) {
      trendStr = 'Bearish (EMA 9 < 21 < 50, ADX: ${adxVal.toStringAsFixed(1)})';
    } else {
      trendStr = 'Consolidation (ADX: ${adxVal.toStringAsFixed(1)})';
    }

    // Volatility
    String volStr = 'Normal (ATR: ${atrVal.toStringAsFixed(4)})';

    // Structure
    final fvgs = struct['active_fvgs'] as List<dynamic>? ?? [];
    final sweeps = struct['sweeps'] as List<dynamic>? ?? [];
    List<String> structParts = [];
    if (sweeps.isNotEmpty) structParts.add('Liquidity Swept');
    if (fvgs.isNotEmpty) structParts.add('${fvgs.length} Active FVG');
    final lastSwing = struct['last_swing_type']?.toString();
    if (lastSwing != null) structParts.add(lastSwing);
    String structStr = structParts.isEmpty ? 'Rangebound' : structParts.join(' • ');

    // Range
    String rangeStr = rsiVal > 70
        ? 'Overbought (RSI: ${rsiVal.toStringAsFixed(1)})'
        : rsiVal < 30
            ? 'Oversold (RSI: ${rsiVal.toStringAsFixed(1)})'
            : 'Neutral (RSI: ${rsiVal.toStringAsFixed(1)})';

    return MarketContextData(
      symbol: json['symbol'] as String? ?? '',
      timeframe: json['timeframe'] as String? ?? '15m',
      trend: trendStr,
      volatility: volStr,
      structure: structStr,
      range: rangeStr,
      rsi: rsiVal,
      atr: atrVal,
    );
  }
}
