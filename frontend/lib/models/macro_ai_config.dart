class SupportedModel {
  final String id;
  final String name;
  final String description;
  final int contextWindow;
  final bool isDefault;

  SupportedModel({
    required this.id,
    required this.name,
    required this.description,
    this.contextWindow = 8192,
    this.isDefault = false,
  });

  factory SupportedModel.fromJson(Map<String, dynamic> json) {
    return SupportedModel(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      description: json['description'] as String? ?? '',
      contextWindow: json['context_window'] as int? ?? 8192,
      isDefault: json['is_default'] as bool? ?? false,
    );
  }
}

class SupportedProvider {
  final String id;
  final String name;
  final String description;
  final String defaultModel;
  final bool supportsCustomBaseUrl;
  final String? defaultBaseUrl;
  final List<SupportedModel> models;

  SupportedProvider({
    required this.id,
    required this.name,
    required this.description,
    required this.defaultModel,
    this.supportsCustomBaseUrl = false,
    this.defaultBaseUrl,
    this.models = const [],
  });

  factory SupportedProvider.fromJson(Map<String, dynamic> json) {
    return SupportedProvider(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      description: json['description'] as String? ?? '',
      defaultModel: json['default_model'] as String? ?? '',
      supportsCustomBaseUrl: json['supports_custom_base_url'] as bool? ?? false,
      defaultBaseUrl: json['default_base_url'] as String?,
      models: (json['models'] as List<dynamic>? ?? [])
          .map((m) => SupportedModel.fromJson(m as Map<String, dynamic>))
          .toList(),
    );
  }
}

class MacroAiConfigSafe {
  final String userId;
  final String provider;
  final String model;
  final bool isEnabled;
  final bool hasApiKey;
  final String? maskedKey;
  final String? apiBaseUrl;
  final String? lastTestedAt;
  final String? lastTestStatus;
  final int? lastTestLatencyMs;
  final String? lastTestError;
  final String? updatedAtUtc;

  MacroAiConfigSafe({
    required this.userId,
    required this.provider,
    required this.model,
    required this.isEnabled,
    required this.hasApiKey,
    this.maskedKey,
    this.apiBaseUrl,
    this.lastTestedAt,
    this.lastTestStatus,
    this.lastTestLatencyMs,
    this.lastTestError,
    this.updatedAtUtc,
  });

  factory MacroAiConfigSafe.fromJson(Map<String, dynamic> json) {
    return MacroAiConfigSafe(
      userId: json['user_id'] as String? ?? 'default_user',
      provider: json['provider'] as String? ?? 'groq',
      model: json['model'] as String? ?? 'llama-3.3-70b-versatile',
      isEnabled: json['is_enabled'] as bool? ?? true,
      hasApiKey: json['has_api_key'] as bool? ?? false,
      maskedKey: json['masked_key'] as String?,
      apiBaseUrl: json['api_base_url'] as String?,
      lastTestedAt: json['last_tested_at'] as String?,
      lastTestStatus: json['last_test_status'] as String?,
      lastTestLatencyMs: json['last_test_latency_ms'] as int?,
      lastTestError: json['last_test_error'] as String?,
      updatedAtUtc: json['updated_at_utc'] as String?,
    );
  }
}

class MacroAiTestResult {
  final String status;
  final String provider;
  final String model;
  final int latencyMs;
  final String message;
  final String? error;

  MacroAiTestResult({
    required this.status,
    required this.provider,
    required this.model,
    required this.latencyMs,
    required this.message,
    this.error,
  });

  factory MacroAiTestResult.fromJson(Map<String, dynamic> json) {
    return MacroAiTestResult(
      status: json['status'] as String? ?? 'FAILED',
      provider: json['provider'] as String? ?? '',
      model: json['model'] as String? ?? '',
      latencyMs: json['latency_ms'] as int? ?? 0,
      message: json['message'] as String? ?? '',
      error: json['error'] as String?,
    );
  }
}
