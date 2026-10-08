class ConditionStatusItem {
  final String condition;
  final bool satisfied;
  final String evidence;
  final String? notes;

  ConditionStatusItem({
    required this.condition,
    required this.satisfied,
    required this.evidence,
    this.notes,
  });

  factory ConditionStatusItem.fromJson(Map<String, dynamic> json) {
    return ConditionStatusItem(
      condition: json['condition'] ?? '',
      satisfied: json['satisfied'] ?? false,
      evidence: json['evidence'] ?? '',
      notes: json['notes'],
    );
  }
}

class AmbiguityItemModel {
  final String textSnippet;
  final String reason;
  final String? suggestion;

  AmbiguityItemModel({
    required this.textSnippet,
    required this.reason,
    this.suggestion,
  });

  factory AmbiguityItemModel.fromJson(Map<String, dynamic> json) {
    return AmbiguityItemModel(
      textSnippet: json['text_snippet'] ?? '',
      reason: json['reason'] ?? '',
      suggestion: json['suggestion'],
    );
  }
}

class TradeTargetModel {
  final double price;
  final double rr;
  final String action;

  TradeTargetModel({
    required this.price,
    required this.rr,
    required this.action,
  });

  factory TradeTargetModel.fromJson(Map<String, dynamic> json) {
    return TradeTargetModel(
      price: (json['price'] as num?)?.toDouble() ?? 0.0,
      rr: (json['rr'] as num?)?.toDouble() ?? 0.0,
      action: json['action'] ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
    'price': price,
    'rr': rr,
    'action': action,
  };
}

class InvalidationRuleModel {
  final int expiryMinutes;
  final double? cancelIfTouched;
  final String? note;

  InvalidationRuleModel({
    this.expiryMinutes = 30,
    this.cancelIfTouched,
    this.note,
  });

  factory InvalidationRuleModel.fromJson(Map<String, dynamic> json) {
    return InvalidationRuleModel(
      expiryMinutes: json['expiry_minutes'] ?? 30,
      cancelIfTouched: (json['cancel_if_touched'] as num?)?.toDouble(),
      note: json['note'],
    );
  }

  Map<String, dynamic> toJson() => {
    'expiry_minutes': expiryMinutes,
    'cancel_if_touched': cancelIfTouched,
    'note': note,
  };
}

class TradeSetupModel {
  final String action;
  final double entryPrice;
  final double stopLoss;
  final double takeProfit;
  final double riskPips;
  final Map<String, TradeTargetModel> targets;
  final InvalidationRuleModel invalidation;
  final List<String> confluence;
  final String? grade;
  final String? session;
  final String? model;
  final double? rrRatio;
  final double? slBufferPips;

  TradeSetupModel({
    required this.action,
    required this.entryPrice,
    required this.stopLoss,
    required this.takeProfit,
    required this.riskPips,
    required this.targets,
    required this.invalidation,
    required this.confluence,
    this.grade,
    this.session,
    this.model,
    this.rrRatio,
    this.slBufferPips,
  });

  factory TradeSetupModel.fromJson(Map<String, dynamic> json) {
    final targetsMap = <String, TradeTargetModel>{};
    if (json['targets'] is Map) {
      (json['targets'] as Map).forEach((k, v) {
        if (v is Map<String, dynamic>) {
          targetsMap[k.toString()] = TradeTargetModel.fromJson(v);
        } else if (v is Map) {
          targetsMap[k.toString()] = TradeTargetModel.fromJson(Map<String, dynamic>.from(v));
        }
      });
    }

    final confList = (json['confluence'] as List<dynamic>? ?? [])
        .map((e) => e.toString())
        .toList();

    return TradeSetupModel(
      action: json['action'] ?? 'BUY LIMIT',
      entryPrice: (json['entry_price'] as num?)?.toDouble() ?? 0.0,
      stopLoss: (json['stop_loss'] as num?)?.toDouble() ?? 0.0,
      takeProfit: (json['take_profit'] as num?)?.toDouble() ?? 0.0,
      riskPips: (json['risk_pips'] as num?)?.toDouble() ?? 0.0,
      targets: targetsMap,
      invalidation: json['invalidation'] != null
          ? InvalidationRuleModel.fromJson(Map<String, dynamic>.from(json['invalidation'] as Map))
          : InvalidationRuleModel(),
      confluence: confList,
      grade: json['grade'],
      session: json['session'],
      model: json['model'],
      rrRatio: (json['rr_ratio'] as num?)?.toDouble(),
      slBufferPips: (json['sl_buffer_pips'] as num?)?.toDouble(),
    );
  }

  Map<String, dynamic> toJson() => {
    'action': action,
    'entry_price': entryPrice,
    'stop_loss': stopLoss,
    'take_profit': takeProfit,
    'risk_pips': riskPips,
    'targets': targets.map((k, v) => MapEntry(k, v.toJson())),
    'invalidation': invalidation.toJson(),
    'confluence': confluence,
    'grade': grade,
    'session': session,
    'model': model,
    'rr_ratio': rrRatio,
    'sl_buffer_pips': slBufferPips,
  };
}

class AIAnalysisRecord {
  final int id;
  final String symbol;
  final int instrumentId;
  final int? candleId;
  final String timeframe;
  final String timestampUtc;
  final String sessionName;
  final int? instructionVersionId;
  final String modelVersion;
  final String state;
  final String summary;
  final List<ConditionStatusItem> conditionBreakdown;
  final List<AmbiguityItemModel> ambiguitiesDetected;
  final String? fullReasoning;
  final TradeSetupModel? tradeSetup;
  final String createdAt;

  AIAnalysisRecord({
    required this.id,
    required this.symbol,
    required this.instrumentId,
    this.candleId,
    required this.timeframe,
    required this.timestampUtc,
    required this.sessionName,
    this.instructionVersionId,
    required this.modelVersion,
    required this.state,
    required this.summary,
    required this.conditionBreakdown,
    required this.ambiguitiesDetected,
    this.fullReasoning,
    this.tradeSetup,
    required this.createdAt,
  });

  factory AIAnalysisRecord.fromJson(Map<String, dynamic> json) {
    final conditions = (json['condition_breakdown'] as List<dynamic>? ?? [])
        .map((e) => ConditionStatusItem.fromJson(e as Map<String, dynamic>))
        .toList();

    final ambiguities = (json['ambiguities_detected'] as List<dynamic>? ?? [])
        .map((e) => AmbiguityItemModel.fromJson(e as Map<String, dynamic>))
        .toList();

    TradeSetupModel? setup;
    if (json['trade_setup'] != null && json['trade_setup'] is Map) {
      setup = TradeSetupModel.fromJson(Map<String, dynamic>.from(json['trade_setup'] as Map));
    }

    return AIAnalysisRecord(
      id: json['id'] ?? 0,
      symbol: json['symbol'] ?? '',
      instrumentId: json['instrument_id'] ?? 0,
      candleId: json['candle_id'],
      timeframe: json['timeframe'] ?? '15m',
      timestampUtc: json['timestamp_utc'] ?? '',
      sessionName: json['session_name'] ?? '',
      instructionVersionId: json['instruction_version_id'],
      modelVersion: json['model_version'] ?? 'deterministic-v1',
      state: json['state'] ?? 'NO_SETUP',
      summary: json['summary'] ?? '',
      conditionBreakdown: conditions,
      ambiguitiesDetected: ambiguities,
      fullReasoning: json['full_reasoning'],
      tradeSetup: setup,
      createdAt: json['created_at'] ?? '',
    );
  }
}
