class BacktestResultModel {
  final int id;
  final String symbol;
  final int instrumentId;
  final String timeframe;
  final String sessionName;
  final int? instructionVersionId;
  final String startDate;
  final String endDate;
  final int totalCandlesAnalyzed;
  final Map<String, int> stateDistribution;
  final List<dynamic> identifiedSetups;
  final String status;
  final String createdAt;

  BacktestResultModel({
    required this.id,
    required this.symbol,
    required this.instrumentId,
    required this.timeframe,
    required this.sessionName,
    this.instructionVersionId,
    required this.startDate,
    required this.endDate,
    required this.totalCandlesAnalyzed,
    required this.stateDistribution,
    required this.identifiedSetups,
    required this.status,
    required this.createdAt,
  });

  factory BacktestResultModel.fromJson(Map<String, dynamic> json) {
    final dist = <String, int>{};
    if (json['state_distribution'] != null) {
      (json['state_distribution'] as Map<String, dynamic>).forEach((k, v) {
        dist[k] = (v as num).toInt();
      });
    }

    return BacktestResultModel(
      id: json['id'] ?? 0,
      symbol: json['symbol'] ?? '',
      instrumentId: json['instrument_id'] ?? 0,
      timeframe: json['timeframe'] ?? '15m',
      sessionName: json['session_name'] ?? 'london',
      instructionVersionId: json['instruction_version_id'],
      startDate: json['start_date'] ?? '',
      endDate: json['end_date'] ?? '',
      totalCandlesAnalyzed: json['total_candles_analyzed'] ?? 0,
      stateDistribution: dist,
      identifiedSetups: json['identified_setups'] ?? [],
      status: json['status'] ?? 'COMPLETED',
      createdAt: json['created_at'] ?? '',
    );
  }
}

class NotificationSettingsModel {
  bool notifyOnValidSetup;
  bool notifyOnPotentialSetup;
  bool notifyOnWatch;
  bool notifyOnInvalidation;
  int cooldownMinutes;

  NotificationSettingsModel({
    this.notifyOnValidSetup = true,
    this.notifyOnPotentialSetup = false,
    this.notifyOnWatch = false,
    this.notifyOnInvalidation = false,
    this.cooldownMinutes = 15,
  });

  factory NotificationSettingsModel.fromJson(Map<String, dynamic> json) {
    return NotificationSettingsModel(
      notifyOnValidSetup: json['notify_on_valid_setup'] ?? true,
      notifyOnPotentialSetup: json['notify_on_potential_setup'] ?? false,
      notifyOnWatch: json['notify_on_watch'] ?? false,
      notifyOnInvalidation: json['notify_on_invalidation'] ?? false,
      cooldownMinutes: json['cooldown_minutes'] ?? 15,
    );
  }
}
