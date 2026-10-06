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
