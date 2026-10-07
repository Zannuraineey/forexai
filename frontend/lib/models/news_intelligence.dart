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

class InstitutionalOrderDensityModel {
  final double buySideLiquidity;
  final double sellSideLiquidity;
  final String orderBlockZone;
  final String orderVolumeConcentration;

  InstitutionalOrderDensityModel({
    required this.buySideLiquidity,
    required this.sellSideLiquidity,
    required this.orderBlockZone,
    required this.orderVolumeConcentration,
  });

  factory InstitutionalOrderDensityModel.fromJson(Map<String, dynamic> json) {
    return InstitutionalOrderDensityModel(
      buySideLiquidity: (json['buy_side_liquidity'] as num?)?.toDouble() ?? 0.0,
      sellSideLiquidity: (json['sell_side_liquidity'] as num?)?.toDouble() ?? 0.0,
      orderBlockZone: json['order_block_zone'] ?? '',
      orderVolumeConcentration: json['order_volume_concentration'] ?? '',
    );
  }
}

class InstitutionalManipulationModel {
  final String judasSwingRisk;
  final String trapType;
  final String manipulationThesis;
  final bool reversalExpected;

  InstitutionalManipulationModel({
    required this.judasSwingRisk,
    required this.trapType,
    required this.manipulationThesis,
    required this.reversalExpected,
  });

  factory InstitutionalManipulationModel.fromJson(Map<String, dynamic> json) {
    return InstitutionalManipulationModel(
      judasSwingRisk: json['judas_swing_risk'] ?? 'MEDIUM',
      trapType: json['trap_type'] ?? '',
      manipulationThesis: json['manipulation_thesis'] ?? '',
      reversalExpected: json['reversal_expected'] ?? true,
    );
  }
}

class DirectionChangeTimingModel {
  final String initialSpikeDuration;
  final String reversalInflectionWindow;
  final String trueTrendExpansionTime;
  final String safeEntryTime;

  DirectionChangeTimingModel({
    required this.initialSpikeDuration,
    required this.reversalInflectionWindow,
    required this.trueTrendExpansionTime,
    required this.safeEntryTime,
  });

  factory DirectionChangeTimingModel.fromJson(Map<String, dynamic> json) {
    return DirectionChangeTimingModel(
      initialSpikeDuration: json['initial_spike_duration'] ?? '',
      reversalInflectionWindow: json['reversal_inflection_window'] ?? '',
      trueTrendExpansionTime: json['true_trend_expansion_time'] ?? '',
      safeEntryTime: json['safe_entry_time'] ?? '',
    );
  }
}

class OrderPlacementBlueprintModel {
  final String action;
  final double recommendedEntry;
  final double stopLoss;
  final double takeProfit1;
  final double takeProfit2;
  final String riskRewardRatio;
  final String executionRule;

  OrderPlacementBlueprintModel({
    required this.action,
    required this.recommendedEntry,
    required this.stopLoss,
    required this.takeProfit1,
    required this.takeProfit2,
    required this.riskRewardRatio,
    required this.executionRule,
  });

  factory OrderPlacementBlueprintModel.fromJson(Map<String, dynamic> json) {
    return OrderPlacementBlueprintModel(
      action: json['action'] ?? '',
      recommendedEntry: (json['recommended_entry'] as num?)?.toDouble() ?? 0.0,
      stopLoss: (json['stop_loss'] as num?)?.toDouble() ?? 0.0,
      takeProfit1: (json['take_profit_1'] as num?)?.toDouble() ?? 0.0,
      takeProfit2: (json['take_profit_2'] as num?)?.toDouble() ?? 0.0,
      riskRewardRatio: json['risk_reward_ratio'] ?? '1:3.0',
      executionRule: json['execution_rule'] ?? '',
    );
  }
}

class NewsSpikeDetectionModel {
  final bool isSpikeActive;
  final String spikeDirection;
  final double estimatedVolatilityPips;
  final String spikeStatus;

  NewsSpikeDetectionModel({
    required this.isSpikeActive,
    required this.spikeDirection,
    required this.estimatedVolatilityPips,
    required this.spikeStatus,
  });

  factory NewsSpikeDetectionModel.fromJson(Map<String, dynamic> json) {
    return NewsSpikeDetectionModel(
      isSpikeActive: json['is_spike_active'] ?? false,
      spikeDirection: json['spike_direction'] ?? 'STABLE',
      estimatedVolatilityPips: (json['estimated_volatility_pips'] as num?)?.toDouble() ?? 0.0,
      spikeStatus: json['spike_status'] ?? '',
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
  final InstitutionalOrderDensityModel? orderDensity;
  final InstitutionalManipulationModel? manipulation;
  final DirectionChangeTimingModel? reversalTiming;
  final OrderPlacementBlueprintModel? orderBlueprint;
  final NewsSpikeDetectionModel? spikeAnalysis;

  PairImpactAnalysisModel({
    required this.symbol,
    required this.directionalBias,
    required this.confidence,
    required this.correlationToUsd,
    required this.smcConfluence,
    required this.keyLevels,
    required this.tradeThesis,
    this.orderDensity,
    this.manipulation,
    this.reversalTiming,
    this.orderBlueprint,
    this.spikeAnalysis,
  });

  // ignore: non_constant_identifier_names
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
      orderDensity: json['order_density'] != null ? InstitutionalOrderDensityModel.fromJson(json['order_density']) : null,
      manipulation: json['manipulation'] != null ? InstitutionalManipulationModel.fromJson(json['manipulation']) : null,
      reversalTiming: json['reversal_timing'] != null ? DirectionChangeTimingModel.fromJson(json['reversal_timing']) : null,
      orderBlueprint: json['order_blueprint'] != null ? OrderPlacementBlueprintModel.fromJson(json['order_blueprint']) : null,
      spikeAnalysis: json['spike_analysis'] != null ? NewsSpikeDetectionModel.fromJson(json['spike_analysis']) : null,
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
  final String? institutionalOrderSummary;
  final String? macroReversalWindow;
  final String? spikeWarning;

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
    this.institutionalOrderSummary,
    this.macroReversalWindow,
    this.spikeWarning,
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
      institutionalOrderSummary: json['institutional_order_summary'],
      macroReversalWindow: json['macro_reversal_window'],
      spikeWarning: json['spike_warning'],
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
