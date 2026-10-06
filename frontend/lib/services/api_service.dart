import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/session_state.dart';
import '../models/strategy_instruction.dart';
import '../models/ai_analysis.dart';
import '../models/backtest_result.dart';
import '../models/candle_model.dart';
import '../models/market_item.dart';
import '../models/market_context_model.dart';

class _CacheEntry {
  final dynamic data;
  final DateTime timestamp;
  _CacheEntry(this.data, this.timestamp);
}

class ApiService {
  static String baseUrl = 'http://192.168.0.3:8000';

  static final List<String> candidateUrls = [
    'http://192.168.120.88:8000',
    'http://192.168.0.3:8000',
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'http://10.0.2.2:8000',
  ];

  static final Map<String, Future<dynamic>> _inFlight = {};
  static final Map<String, _CacheEntry> _cache = {};

  static void invalidateCache() {
    _cache.clear();
  }

  static Future<T> _dedupedGet<T>(
    String path,
    T Function(dynamic json) parser, {
    Duration ttl = const Duration(seconds: 20),
    bool forceRefresh = false,
  }) async {
    final now = DateTime.now();
    if (!forceRefresh && _cache.containsKey(path)) {
      final entry = _cache[path]!;
      if (now.difference(entry.timestamp) < ttl) {
        return entry.data as T;
      }
    }

    if (_inFlight.containsKey(path)) {
      return await _inFlight[path] as T;
    }

    final future = () async {
      try {
        final res = await _get(path);
        if (res.statusCode == 200) {
          final parsed = parser(jsonDecode(res.body));
          _cache[path] = _CacheEntry(parsed, DateTime.now());
          return parsed;
        }
        throw Exception('Request failed [$path]: ${res.statusCode}');
      } finally {
        _inFlight.remove(path);
      }
    }();

    _inFlight[path] = future;
    return await future;
  }

  /// Internal resilient GET wrapper that automatically falls back across candidates
  static Future<http.Response> _get(
    String path, {
    Duration timeout = const Duration(seconds: 4),
  }) async {
    // 1. Try current baseUrl
    try {
      final res = await http.get(Uri.parse('$baseUrl$path')).timeout(timeout);
      return res;
    } catch (_) {
      // 2. Try candidate fallback URLs
      for (final candidate in candidateUrls) {
        if (candidate == baseUrl) continue;
        try {
          final res = await http
              .get(Uri.parse('$candidate$path'))
              .timeout(const Duration(seconds: 2));
          if (res.statusCode == 200 || res.statusCode == 404) {
            baseUrl = candidate; // auto-switch to active responsive bridge
            return res;
          }
        } catch (_) {}
      }
      rethrow;
    }
  }

  /// Internal resilient POST wrapper
  static Future<http.Response> _post(
    String path, {
    Map<String, String>? headers,
    Object? body,
    Duration timeout = const Duration(seconds: 6),
  }) async {
    try {
      final res = await http
          .post(Uri.parse('$baseUrl$path'), headers: headers, body: body)
          .timeout(timeout);
      return res;
    } catch (_) {
      for (final candidate in candidateUrls) {
        if (candidate == baseUrl) continue;
        try {
          final res = await http
              .post(Uri.parse('$candidate$path'), headers: headers, body: body)
              .timeout(const Duration(seconds: 3));
          baseUrl = candidate;
          return res;
        } catch (_) {}
      }
      rethrow;
    }
  }

  /// Internal resilient PUT wrapper
  static Future<http.Response> _put(
    String path, {
    Map<String, String>? headers,
    Object? body,
    Duration timeout = const Duration(seconds: 6),
  }) async {
    try {
      final res = await http
          .put(Uri.parse('$baseUrl$path'), headers: headers, body: body)
          .timeout(timeout);
      return res;
    } catch (_) {
      for (final candidate in candidateUrls) {
        if (candidate == baseUrl) continue;
        try {
          final res = await http
              .put(Uri.parse('$candidate$path'), headers: headers, body: body)
              .timeout(const Duration(seconds: 3));
          baseUrl = candidate;
          return res;
        } catch (_) {}
      }
      rethrow;
    }
  }

  // 1. Session APIs
  static Future<CurrentSessionState> getCurrentSession({
    bool forceRefresh = false,
  }) async {
    return _dedupedGet<CurrentSessionState>(
      '/api/v1/sessions/current',
      (json) => CurrentSessionState.fromJson(json),
      ttl: const Duration(seconds: 30),
      forceRefresh: forceRefresh,
    );
  }

  static Future<CurrentSessionState> getSessionLevels(String symbol) async {
    final response = await _get('/api/v1/sessions/levels/$symbol');
    if (response.statusCode == 200) {
      return CurrentSessionState.fromJson(jsonDecode(response.body));
    }
    throw Exception('Failed to fetch session levels: ${response.statusCode}');
  }

  // 2. Strategy Instruction APIs
  static Future<StrategySessionsConfig> getStrategySessions({
    bool forceRefresh = false,
  }) async {
    return _dedupedGet<StrategySessionsConfig>(
      '/api/v1/strategy/sessions',
      (json) => StrategySessionsConfig.fromJson(json),
      ttl: const Duration(seconds: 30),
      forceRefresh: forceRefresh,
    );
  }

  static Future<Map<String, dynamic>> updateSessionStrategy({
    required String sessionName,
    required String instructions,
    String? changeSummary,
  }) async {
    final response = await _put(
      '/api/v1/strategy/sessions/$sessionName',
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'instructions': instructions,
        'change_summary': changeSummary ?? 'Updated via Flutter mobile client',
      }),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('Failed to update strategy: ${response.statusCode}');
  }

  static Future<List<InstructionVersionItem>> getSessionHistory(
    String sessionName,
  ) async {
    final response = await _get(
      '/api/v1/strategy/sessions/$sessionName/history',
    );
    if (response.statusCode == 200) {
      final list = jsonDecode(response.body) as List<dynamic>;
      return list.map((e) => InstructionVersionItem.fromJson(e)).toList();
    }
    throw Exception('Failed to fetch history: ${response.statusCode}');
  }

  static Future<Map<String, dynamic>> rollbackSessionStrategy({
    required String sessionName,
    required int targetVersion,
    String? reason,
  }) async {
    final response = await _post(
      '/api/v1/strategy/sessions/$sessionName/rollback',
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'target_version': targetVersion,
        'reason': reason ?? 'Rollback via Flutter mobile client',
      }),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('Failed to rollback strategy: ${response.statusCode}');
  }

  // 3. AI Analysis APIs
  static Future<AIAnalysisRecord> evaluateMarket({
    required String symbol,
    String timeframe = '15m',
    String? sessionName,
    String? customInstructions,
  }) async {
    final response = await _post(
      '/api/v1/analysis/evaluate',
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'symbol': symbol,
        'timeframe': timeframe,
        'session_name': sessionName,
        'custom_instructions': customInstructions,
      }),
    );
    if (response.statusCode == 200) {
      return AIAnalysisRecord.fromJson(jsonDecode(response.body));
    }
    throw Exception('Failed to evaluate AI market analysis: ${response.body}');
  }

  static Future<Map<String, dynamic>> getUtBotAnalysis(
    String symbol, {
    String timeframe = '15m',
    double? sensitivity,
    int atrPeriod = 10,
  }) async {
    var url = '/api/v1/analysis/ut-bot/$symbol?timeframe=$timeframe&atr_period=$atrPeriod';
    if (sensitivity != null) {
      url += '&sensitivity=$sensitivity';
    }
    final response = await _get(url);
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    throw Exception('Failed to fetch UT Bot analysis: ${response.statusCode}');
  }

  static Future<List<AIAnalysisRecord>> getAnalysisHistory({
    String? symbol,
    String? timeframe,
    String? sessionName,
    int limit = 50,
  }) async {
    var url = '/api/v1/analysis/history?limit=$limit';
    if (symbol != null && symbol.isNotEmpty) url += '&symbol=$symbol';
    if (timeframe != null && timeframe.isNotEmpty) {
      url += '&timeframe=$timeframe';
    }
    if (sessionName != null && sessionName.isNotEmpty) {
      url += '&session_name=$sessionName';
    }

    final response = await _get(url);
    if (response.statusCode == 200) {
      final list = jsonDecode(response.body) as List<dynamic>;
      return list.map((e) => AIAnalysisRecord.fromJson(e)).toList();
    }
    throw Exception('Failed to fetch analysis history: ${response.statusCode}');
  }

  // 4. Backtest APIs
  static Future<BacktestResultModel> runBacktest({
    required String symbol,
    required String timeframe,
    required String sessionName,
    String? customInstructions,
    required DateTime startDate,
    required DateTime endDate,
  }) async {
    final response = await _post(
      '/api/v1/analysis/backtest',
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'symbol': symbol,
        'timeframe': timeframe,
        'session_name': sessionName,
        'custom_instructions': customInstructions,
        'start_date': startDate.toUtc().toIso8601String(),
        'end_date': endDate.toUtc().toIso8601String(),
      }),
    );
    if (response.statusCode == 200) {
      return BacktestResultModel.fromJson(jsonDecode(response.body));
    }
    throw Exception('Failed to run backtest: ${response.body}');
  }

  // 5. Device & Notification APIs
  static Future<void> registerDevice({
    required String fcmToken,
    required String platform,
  }) async {
    final response = await _post(
      '/api/v1/devices/register',
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'fcm_token': fcmToken,
        'device_platform': platform,
        'user_id': 1,
      }),
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to register device: ${response.statusCode}');
    }
  }

  static Future<List<dynamic>> getNotifications() async {
    final response = await _get('/api/v1/notifications');
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as List<dynamic>;
    }
    throw Exception('Failed to get notifications');
  }

  static Future<Map<String, dynamic>> getScannerStatus() async {
    final response = await _get('/api/v1/analysis/scanner/status');
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('Failed to get scanner status');
  }

  static Future<Map<String, dynamic>> triggerScannerRun() async {
    final response = await _post('/api/v1/analysis/scanner/run-once');
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('Failed to trigger scanner run');
  }

  static Future<Map<String, dynamic>?> testNotificationDispatch({
    String symbol = 'EURUSD',
    String timeframe = '15m',
  }) async {
    final response = await _post(
      '/api/v1/notifications/test-dispatch?symbol=$symbol&timeframe=$timeframe',
    );
    if (response.statusCode == 200) {
      if (response.body.isNotEmpty && response.body != 'null') {
        return jsonDecode(response.body);
      }
      return null;
    }
    throw Exception(
      'Failed to dispatch test notification: ${response.statusCode}',
    );
  }

  // 6. Instrument Catalog & Management APIs
  static Future<Map<String, dynamic>> getInstrumentCatalog([
    String? category,
  ]) async {
    var url = '/api/v1/instruments/catalog';
    if (category != null) url += '?category=$category';
    final response = await _get(url);
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception(
      'Failed to fetch instrument catalog: ${response.statusCode}',
    );
  }

  static Future<Map<String, dynamic>> toggleInstrument(String symbol) async {
    final response = await _post('/api/v1/instruments/$symbol/toggle');
    if (response.statusCode == 200) {
      invalidateCache();
      return jsonDecode(response.body);
    }
    throw Exception('Failed to toggle instrument: ${response.statusCode}');
  }

  static Future<List<String>> getActiveSymbols({
    bool forceRefresh = false,
  }) async {
    try {
      return await _dedupedGet<List<String>>(
        '/api/v1/instruments?active_only=true',
        (json) =>
            (json as List<dynamic>).map((e) => e['symbol'].toString()).toList(),
        ttl: const Duration(seconds: 30),
        forceRefresh: forceRefresh,
      );
    } catch (_) {
      return [
        'XAUUSD',
        'EURUSD',
        'GBPUSD',
        'USDJPY',
        'AUDUSD',
        'USDCHF',
        'USDCAD',
        'XAGUSD',
      ];
    }
  }

  // 7. Watchlist & Candlestick APIs
  static Future<List<MarketItem>> getWatchlistSummary({
    bool forceRefresh = false,
  }) async {
    return _dedupedGet<List<MarketItem>>(
      '/api/v1/candles/summary/watchlist',
      (json) =>
          (json as List<dynamic>).map((e) => MarketItem.fromJson(e)).toList(),
      ttl: const Duration(seconds: 2),
      forceRefresh: forceRefresh,
    );
  }

  static Future<List<CandleModel>> getCandles(
    String symbol,
    String timeframe, {
    int limit = 60,
  }) async {
    final response = await _get(
      '/api/v1/candles/$symbol?timeframe=$timeframe&limit=$limit',
    );
    if (response.statusCode == 200) {
      final list = jsonDecode(response.body) as List<dynamic>;
      return list.map((e) => CandleModel.fromJson(e)).toList();
    }
    throw Exception('Failed to fetch candles: ${response.statusCode}');
  }

  static Future<MarketContextData> getMarketContext(
    String symbol, {
    String timeframe = '15m',
    bool forceRefresh = false,
  }) async {
    return _dedupedGet<MarketContextData>(
      '/api/v1/context/$symbol?timeframe=$timeframe',
      (json) => MarketContextData.fromJson(json),
      ttl: const Duration(seconds: 20),
      forceRefresh: forceRefresh,
    );
  }
}
