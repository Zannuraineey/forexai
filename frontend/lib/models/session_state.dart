class SessionWindowInfo {
  final String name;
  final String timezoneName;
  final bool isActive;
  final String localStartTime;
  final String localEndTime;
  final String currentLocalTime;
  final String startUtc;
  final String endUtc;
  final String status;

  SessionWindowInfo({
    required this.name,
    required this.timezoneName,
    required this.isActive,
    required this.localStartTime,
    required this.localEndTime,
    required this.currentLocalTime,
    required this.startUtc,
    required this.endUtc,
    required this.status,
  });

  factory SessionWindowInfo.fromJson(Map<String, dynamic> json) {
    return SessionWindowInfo(
      name: json['name'] ?? '',
      timezoneName: json['timezone_name'] ?? '',
      isActive: json['is_active'] ?? false,
      localStartTime: json['local_start_time'] ?? '',
      localEndTime: json['local_end_time'] ?? '',
      currentLocalTime: json['current_local_time'] ?? '',
      startUtc: json['start_utc'] ?? '',
      endUtc: json['end_utc'] ?? '',
      status: json['status'] ?? 'UPCOMING',
    );
  }
}

class SessionLevels {
  final String sessionName;
  final double? high;
  final double? low;
  final double? open;
  final double? close;
  final double? rangePips;
  final String status;
  final bool sweptHigh;
  final bool sweptLow;
  final int candleCount;

  SessionLevels({
    required this.sessionName,
    this.high,
    this.low,
    this.open,
    this.close,
    this.rangePips,
    required this.status,
    required this.sweptHigh,
    required this.sweptLow,
    required this.candleCount,
  });

  factory SessionLevels.fromJson(Map<String, dynamic> json) {
    return SessionLevels(
      sessionName: json['session_name'] ?? '',
      high: (json['high'] as num?)?.toDouble(),
      low: (json['low'] as num?)?.toDouble(),
      open: (json['open'] as num?)?.toDouble(),
      close: (json['close'] as num?)?.toDouble(),
      rangePips: (json['range_pips'] as num?)?.toDouble(),
      status: json['status'] ?? 'UPCOMING',
      sweptHigh: json['swept_high'] ?? false,
      sweptLow: json['swept_low'] ?? false,
      candleCount: json['candle_count'] ?? 0,
    );
  }
}

class CurrentSessionState {
  final String timestampUtc;
  final List<String> activeSessions;
  final bool isOverlap;
  final String? overlapName;
  final String? primarySession;
  final Map<String, SessionWindowInfo> sessionWindows;
  final Map<String, SessionLevels> sessionLevels;

  CurrentSessionState({
    required this.timestampUtc,
    required this.activeSessions,
    required this.isOverlap,
    this.overlapName,
    this.primarySession,
    required this.sessionWindows,
    required this.sessionLevels,
  });

  factory CurrentSessionState.fromJson(Map<String, dynamic> json) {
    final windows = <String, SessionWindowInfo>{};
    if (json['session_windows'] != null) {
      (json['session_windows'] as Map<String, dynamic>).forEach((k, v) {
        windows[k] = SessionWindowInfo.fromJson(v);
      });
    }

    final levels = <String, SessionLevels>{};
    if (json['session_levels'] != null) {
      (json['session_levels'] as Map<String, dynamic>).forEach((k, v) {
        levels[k] = SessionLevels.fromJson(v);
      });
    }

    return CurrentSessionState(
      timestampUtc: json['timestamp_utc'] ?? '',
      activeSessions: List<String>.from(json['active_sessions'] ?? []),
      isOverlap: json['is_overlap'] ?? false,
      overlapName: json['overlap_name'],
      primarySession: json['primary_session'],
      sessionWindows: windows,
      sessionLevels: levels,
    );
  }
}
