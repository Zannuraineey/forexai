class InstructionVersionItem {
  final int id;
  final int instructionId;
  final int version;
  final String promptContent;
  final String? changeSummary;
  final String createdAt;

  InstructionVersionItem({
    required this.id,
    required this.instructionId,
    required this.version,
    required this.promptContent,
    this.changeSummary,
    required this.createdAt,
  });

  factory InstructionVersionItem.fromJson(Map<String, dynamic> json) {
    return InstructionVersionItem(
      id: json['id'] ?? 0,
      instructionId: json['instruction_id'] ?? 0,
      version: json['version'] ?? 1,
      promptContent: json['prompt_content'] ?? '',
      changeSummary: json['change_summary'],
      createdAt: json['created_at'] ?? '',
    );
  }
}

class SessionConfigItem {
  final bool enabled;
  final String instructions;
  final int? version;
  final String? updatedAt;

  SessionConfigItem({
    required this.enabled,
    required this.instructions,
    this.version,
    this.updatedAt,
  });

  factory SessionConfigItem.fromJson(Map<String, dynamic> json) {
    return SessionConfigItem(
      enabled: json['enabled'] ?? true,
      instructions: json['instructions'] ?? '',
      version: json['version'],
      updatedAt: json['updated_at'],
    );
  }
}

class StrategySessionsConfig {
  final SessionConfigItem asian;
  final SessionConfigItem london;
  final SessionConfigItem newYork;

  StrategySessionsConfig({
    required this.asian,
    required this.london,
    required this.newYork,
  });

  factory StrategySessionsConfig.fromJson(Map<String, dynamic> json) {
    return StrategySessionsConfig(
      asian: SessionConfigItem.fromJson(json['asian'] ?? {}),
      london: SessionConfigItem.fromJson(json['london'] ?? {}),
      newYork: SessionConfigItem.fromJson(json['new_york'] ?? {}),
    );
  }
}
