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
    required this.createdAt,
  });

  factory AIAnalysisRecord.fromJson(Map<String, dynamic> json) {
    final conditions = (json['condition_breakdown'] as List<dynamic>? ?? [])
        .map((e) => ConditionStatusItem.fromJson(e as Map<String, dynamic>))
        .toList();

    final ambiguities = (json['ambiguities_detected'] as List<dynamic>? ?? [])
        .map((e) => AmbiguityItemModel.fromJson(e as Map<String, dynamic>))
        .toList();

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
      createdAt: json['created_at'] ?? '',
    );
  }
}
