class EconomicEventModel {
  final String id;
  final String title;
  final String country;
  final String currency;
  final String impact;
  final DateTime eventTimeUtc;
  final double? actual;
  final double? forecast;
  final double? previous;
  final String unit;
  final String status;
  final String meaning;
  final String historicalContext;
  final List<dynamic> historicalReactions;
  final String? rawForecast;
  final String? rawPrevious;
  final String? rawActual;

  EconomicEventModel({
    required this.id,
    required this.title,
    required this.country,
    required this.currency,
    required this.impact,
    required this.eventTimeUtc,
    this.actual,
    this.forecast,
    this.previous,
    required this.unit,
    required this.status,
    required this.meaning,
    required this.historicalContext,
    required this.historicalReactions,
    this.rawForecast,
    this.rawPrevious,
    this.rawActual,
  });

  factory EconomicEventModel.fromJson(Map<String, dynamic> json) {
    return EconomicEventModel(
      id: json['id'] ?? '',
      title: json['title'] ?? '',
      country: json['country'] ?? 'USD',
      currency: json['currency'] ?? 'USD',
      impact: json['impact'] ?? 'HIGH',
      eventTimeUtc: DateTime.tryParse(json['event_time_utc'] ?? '') ?? DateTime.now(),
      actual: (json['actual'] as num?)?.toDouble(),
      forecast: (json['forecast'] as num?)?.toDouble(),
      previous: (json['previous'] as num?)?.toDouble(),
      unit: json['unit'] ?? '%',
      status: json['status'] ?? 'SCHEDULED',
      meaning: json['meaning'] ?? '',
      historicalContext: json['historical_context'] ?? '',
      historicalReactions: json['historical_reactions'] as List<dynamic>? ?? [],
      rawForecast: json['raw_forecast'],
      rawPrevious: json['raw_previous'],
      rawActual: json['raw_actual'],
    );
  }
}

class BreakingNewsItemModel {
  final String id;
  final String title;
  final String summary;
  final String source;
  final DateTime publishedAtUtc;
  final String? url;
  final List<String> currencies;
  final String sentiment;
  final String impact;

  BreakingNewsItemModel({
    required this.id,
    required this.title,
    required this.summary,
    required this.source,
    required this.publishedAtUtc,
    this.url,
    required this.currencies,
    required this.sentiment,
    required this.impact,
  });

  factory BreakingNewsItemModel.fromJson(Map<String, dynamic> json) {
    return BreakingNewsItemModel(
      id: json['id'] ?? '',
      title: json['title'] ?? '',
      summary: json['summary'] ?? '',
      source: json['source'] ?? 'Financial Wire',
      publishedAtUtc: DateTime.tryParse(json['published_at_utc'] ?? '') ?? DateTime.now(),
      url: json['url'],
      currencies: (json['currencies'] as List<dynamic>? ?? []).map((e) => e.toString()).toList(),
      sentiment: json['sentiment'] ?? 'NEUTRAL',
      impact: json['impact'] ?? 'MEDIUM',
    );
  }
}

class DXYMetricsModel {
  final double value;
  final double changePct;
  final String trend;
  final String marketRegime;
  final String smcStructure;
  final double rsi14;
  final double ema200;
  final bool displacementActive;
  final String confirmationStatus;
  final String source;

  DXYMetricsModel({
    required this.value,
    required this.changePct,
    required this.trend,
    required this.marketRegime,
    required this.smcStructure,
    required this.rsi14,
    required this.ema200,
    required this.displacementActive,
    required this.confirmationStatus,
    required this.source,
  });

  factory DXYMetricsModel.fromJson(Map<String, dynamic> json) {
    return DXYMetricsModel(
      value: (json['value'] as num?)?.toDouble() ?? 100.0,
      changePct: (json['change_pct'] as num?)?.toDouble() ?? 0.0,
      trend: json['trend'] ?? 'NEUTRAL',
      marketRegime: json['market_regime'] ?? 'NEUTRAL',
      smcStructure: json['smc_structure'] ?? '',
      rsi14: (json['rsi_14'] as num?)?.toDouble() ?? 50.0,
      ema200: (json['ema_200'] as num?)?.toDouble() ?? 100.0,
      displacementActive: json['displacement_active'] ?? false,
      confirmationStatus: json['confirmation_status'] ?? 'NEUTRAL',
      source: json['source'] ?? 'SYNTHETIC_BASKET_DXY',
    );
  }
}

class PairImpactAnalysisModel {
  final String symbol;
  final String directionalBias;
  final double confidence;
  final String correlationToUsd;
  final String smcConfluence;
  final Map<String, dynamic> keyLevels;
  final String tradeThesis;

  PairImpactAnalysisModel({
    required this.symbol,
    required this.directionalBias,
    required this.confidence,
    required this.correlationToUsd,
    required this.smcConfluence,
    required this.keyLevels,
    required this.tradeThesis,
  });

  String get directional_bias => directionalBias;

  factory PairImpactAnalysisModel.fromJson(Map<String, dynamic> json) {
    return PairImpactAnalysisModel(
      symbol: json['symbol'] ?? '',
      directionalBias: json['directional_bias'] ?? 'NEUTRAL',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.5,
      correlationToUsd: json['correlation_to_usd'] ?? 'INVERSE',
      smcConfluence: json['smc_confluence'] ?? '',
      keyLevels: (json['key_levels'] as Map<String, dynamic>?) ?? {},
      tradeThesis: json['trade_thesis'] ?? '',
    );
  }
}

class NewsIntelligenceReportModel {
  final String id;
  final DateTime generatedAtUtc;
  final EconomicEventModel event;
  final DXYMetricsModel dxyContext;
  final String deviationAnalysis;
  final String historicalComparison;
  final String macroRegimeSummary;
  final String smcTechnicalSynthesis;
  final List<PairImpactAnalysisModel> pairAnalyses;
  final String actionableConclusion;
  final String aiEngineUsed;

  NewsIntelligenceReportModel({
    required this.id,
    required this.generatedAtUtc,
    required this.event,
    required this.dxyContext,
    required this.deviationAnalysis,
    required this.historicalComparison,
    required this.macroRegimeSummary,
    required this.smcTechnicalSynthesis,
    required this.pairAnalyses,
    required this.actionableConclusion,
    required this.aiEngineUsed,
  });

  factory NewsIntelligenceReportModel.fromJson(Map<String, dynamic> json) {
    final pairsList = (json['pair_analyses'] as List<dynamic>? ?? [])
        .map((e) => PairImpactAnalysisModel.fromJson(e as Map<String, dynamic>))
        .toList();

    return NewsIntelligenceReportModel(
      id: json['id'] ?? '',
      generatedAtUtc: DateTime.tryParse(json['generated_at_utc'] ?? '') ?? DateTime.now(),
      event: EconomicEventModel.fromJson(json['event'] ?? {}),
      dxyContext: DXYMetricsModel.fromJson(json['dxy_context'] ?? {}),
      deviationAnalysis: json['deviation_analysis'] ?? '',
      historicalComparison: json['historical_comparison'] ?? '',
      macroRegimeSummary: json['macro_regime_summary'] ?? '',
      smcTechnicalSynthesis: json['smc_technical_synthesis'] ?? '',
      pairAnalyses: pairsList,
      actionableConclusion: json['actionable_conclusion'] ?? '',
      aiEngineUsed: json['ai_engine_used'] ?? 'QUANT_MACRO_SYNTHESIS',
    );
  }
}

class AIQueryResponseModel {
  final String query;
  final String aiAnalysis;
  final DXYMetricsModel dxyContext;
  final String marketRegime;
  final List<PairImpactAnalysisModel> pairAnalyses;
  final List<String> keyTakeaways;
  final DateTime timestampUtc;
  final String aiEngineUsed;

  AIQueryResponseModel({
    required this.query,
    required this.aiAnalysis,
    required this.dxyContext,
    required this.marketRegime,
    required this.pairAnalyses,
    required this.keyTakeaways,
    required this.timestampUtc,
    required this.aiEngineUsed,
  });

  factory AIQueryResponseModel.fromJson(Map<String, dynamic> json) {
    final pairsList = (json['pair_analyses'] as List<dynamic>? ?? [])
        .map((e) => PairImpactAnalysisModel.fromJson(e as Map<String, dynamic>))
        .toList();

    final takeaways = (json['key_takeaways'] as List<dynamic>? ?? [])
        .map((e) => e.toString())
        .toList();

    return AIQueryResponseModel(
      query: json['query'] ?? '',
      aiAnalysis: json['ai_analysis'] ?? '',
      dxyContext: DXYMetricsModel.fromJson(json['dxy_context'] ?? {}),
      marketRegime: json['market_regime'] ?? 'NEUTRAL',
      pairAnalyses: pairsList,
      keyTakeaways: takeaways,
      timestampUtc: DateTime.tryParse(json['timestamp_utc'] ?? '') ?? DateTime.now(),
      aiEngineUsed: json['ai_engine_used'] ?? 'QUANT_MACRO_SYNTHESIS',
    );
  }
}
