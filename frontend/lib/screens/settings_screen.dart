import 'package:flutter/material.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../models/session_state.dart';
import '../models/strategy_instruction.dart';
import '../models/macro_ai_config.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({Key? key}) : super(key: key);

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  // 1. Sessions
  CurrentSessionState? _currentSession;
  bool _isLoadingSession = false;

  // 2. Timeframes
  String _defaultTimeframe = '15m';
  bool _multiTimeframeConfirmation = true;

  // 3. Strategy Instructions
  StrategySessionsConfig? _strategyConfig;
  bool _isLoadingStrategy = false;

  // 4. Notification Preferences
  bool _notifyValid = true;
  bool _notifyPotential = true;
  bool _notifyWatch = false;
  bool _notifyInvalidated = false;
  int _cooldownMinutes = 15;

  // 5. AI Reasoning Provider (SaaS)
  List<SupportedProvider> _supportedProviders = [];
  MacroAiConfigSafe? _macroAiConfig;
  bool _isLoadingAiConfig = false;
  bool _isSavingAiConfig = false;
  bool _isTestingAiConnection = false;
  MacroAiTestResult? _lastTestResult;

  bool _macroReasoningEnabled = true;
  String _selectedProviderId = 'groq';
  String _selectedModelId = 'llama-3.3-70b-versatile';
  final TextEditingController _apiKeyCtrl = TextEditingController();
  final TextEditingController _customBaseUrlCtrl = TextEditingController();
  final TextEditingController _customModelCtrl = TextEditingController();
  bool _obscureApiKey = true;
  bool _isCustomModel = false;

  // Device push registration state (kept completely silent and secure from end-user)
  bool _isDeviceRegistered = false;
  bool _isSendingTestPush = false;

  @override
  void initState() {
    super.initState();
    _loadAllSettingsData();
  }

  @override
  void dispose() {
    _apiKeyCtrl.dispose();
    _customBaseUrlCtrl.dispose();
    _customModelCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadAllSettingsData() async {
    _loadSessionInfo();
    _loadStrategyInfo();
    _loadMacroAiConfig();
    _silentlySyncDeviceToken();
  }

  Future<void> _silentlySyncDeviceToken() async {
    try {
      final messaging = FirebaseMessaging.instance;
      await messaging.requestPermission(
        alert: true,
        badge: true,
        sound: true,
      );
      final token = await messaging.getToken();
      if (token != null && mounted) {
        await ApiService.registerDevice(
          fcmToken: token,
          platform: 'android',
        );
        if (mounted) {
          setState(() => _isDeviceRegistered = true);
        }
      }
    } catch (e) {
      debugPrint('Device token sync notice: $e');
    }
  }

  Future<void> _loadSessionInfo() async {
    setState(() => _isLoadingSession = true);
    try {
      final sess = await ApiService.getCurrentSession();
      if (mounted) {
        setState(() {
          _currentSession = sess;
          _isLoadingSession = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _isLoadingSession = false);
    }
  }

  Future<void> _loadStrategyInfo() async {
    setState(() => _isLoadingStrategy = true);
    try {
      final cfg = await ApiService.getStrategySessions();
      if (mounted) {
        setState(() {
          _strategyConfig = cfg;
          _isLoadingStrategy = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _isLoadingStrategy = false);
    }
  }

  Future<void> _sendTestPush() async {
    setState(() => _isSendingTestPush = true);
    try {
      final res = await ApiService.testNotificationDispatch();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: AppTheme.surfaceSubtle,
            content: Text(
              res != null
                  ? '🎯 Test push alert sent! Check your notification bar.'
                  : 'Test alert submitted to backend scanner.',
              style: const TextStyle(color: AppTheme.upGreen),
            ),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: AppTheme.surfaceSubtle,
            content: Text('Test dispatch failed: $e', style: const TextStyle(color: AppTheme.downRed)),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isSendingTestPush = false);
    }
  }

  void _showInstructionEditorModal(String sessionName, String currentInstructions, int version) {
    final editCtrl = TextEditingController(text: currentInstructions);
    final summaryCtrl = TextEditingController();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppTheme.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) {
        return Padding(
          padding: EdgeInsets.only(
            left: 16,
            right: 16,
            top: 16,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 16,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      '${sessionName.toUpperCase()} STRATEGY INSTRUCTIONS (v$version)',
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.textPrimary,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  TextButton(
                    onPressed: () {
                      Navigator.pop(ctx);
                      _showVersionHistoryModal(sessionName);
                    },
                    child: const Text('Version History', style: TextStyle(fontSize: 12, color: AppTheme.accent)),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              TextField(
                controller: editCtrl,
                maxLines: 8,
                style: const TextStyle(fontSize: 13, height: 1.4, fontFamily: 'monospace', color: AppTheme.textPrimary),
                decoration: InputDecoration(
                  filled: true,
                  fillColor: AppTheme.background,
                  hintText: 'Enter structured session trading rules...',
                  hintStyle: const TextStyle(color: AppTheme.textMuted),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(6),
                    borderSide: const BorderSide(color: AppTheme.border),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(6),
                    borderSide: const BorderSide(color: AppTheme.accent),
                  ),
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: summaryCtrl,
                style: const TextStyle(fontSize: 12, color: AppTheme.textPrimary),
                decoration: InputDecoration(
                  filled: true,
                  fillColor: AppTheme.background,
                  labelText: 'Change summary (Audit Trail)',
                  labelStyle: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(6),
                    borderSide: const BorderSide(color: AppTheme.border),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.pop(ctx),
                    child: const Text('Cancel', style: TextStyle(color: AppTheme.textMuted)),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.surfaceSubtle,
                      foregroundColor: AppTheme.textPrimary,
                      side: const BorderSide(color: AppTheme.border),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                    ),
                    onPressed: () async {
                      final text = editCtrl.text.trim();
                      if (text.isNotEmpty) {
                        try {
                          await ApiService.updateSessionStrategy(
                            sessionName: sessionName,
                            instructions: text,
                            changeSummary: summaryCtrl.text.trim().isEmpty ? null : summaryCtrl.text.trim(),
                          );
                          Navigator.pop(ctx);
                          _loadStrategyInfo();
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              backgroundColor: AppTheme.surfaceSubtle,
                              content: Text('Updated $sessionName strategy rules', style: const TextStyle(color: AppTheme.upGreen)),
                            ),
                          );
                        } catch (e) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              backgroundColor: AppTheme.surfaceSubtle,
                              content: Text('Update failed: $e', style: const TextStyle(color: AppTheme.downRed)),
                            ),
                          );
                        }
                      }
                    },
                    child: const Text('Save & Increment Version', style: TextStyle(fontWeight: FontWeight.w600)),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  void _showVersionHistoryModal(String sessionName) async {
    showDialog(
      context: context,
      builder: (ctx) {
        return FutureBuilder<List<InstructionVersionItem>>(
          future: ApiService.getSessionHistory(sessionName),
          builder: (context, snapshot) {
            return AlertDialog(
              backgroundColor: AppTheme.surface,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              title: Text(
                '${sessionName.toUpperCase()} Version History',
                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: AppTheme.textPrimary),
              ),
              content: SizedBox(
                width: double.maxFinite,
                height: 320,
                child: snapshot.connectionState == ConnectionState.waiting
                    ? const Center(child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.textSecondary))
                    : (snapshot.hasError || snapshot.data == null || snapshot.data!.isEmpty)
                        ? const Center(child: Text('No historical revisions recorded', style: TextStyle(color: AppTheme.textMuted)))
                        : ListView.separated(
                            itemCount: snapshot.data!.length,
                            separatorBuilder: (_, __) => const Divider(height: 1, color: AppTheme.borderSubtle),
                            itemBuilder: (context, i) {
                              final item = snapshot.data![i];
                              final summaryText = item.changeSummary ?? 'No description';
                              return ListTile(
                                dense: true,
                                contentPadding: EdgeInsets.zero,
                                title: Text('Version ${item.version}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: AppTheme.textPrimary)),
                                subtitle: Text(summaryText.isEmpty ? 'No description' : summaryText, style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
                                trailing: TextButton(
                                  onPressed: () async {
                                    try {
                                      await ApiService.rollbackSessionStrategy(
                                        sessionName: sessionName,
                                        targetVersion: item.version,
                                        reason: 'User rollback to v${item.version}',
                                      );
                                      if (mounted) {
                                        Navigator.pop(ctx);
                                        _loadStrategyInfo();
                                        ScaffoldMessenger.of(context).showSnackBar(
                                          SnackBar(
                                            backgroundColor: AppTheme.surfaceSubtle,
                                            content: Text('Rolled back to v${item.version}', style: const TextStyle(color: AppTheme.upGreen)),
                                          ),
                                        );
                                      }
                                    } catch (e) {
                                      if (mounted) {
                                        ScaffoldMessenger.of(context).showSnackBar(
                                          SnackBar(
                                            backgroundColor: AppTheme.surfaceSubtle,
                                            content: Text('Rollback failed: $e', style: const TextStyle(color: AppTheme.downRed)),
                                          ),
                                        );
                                      }
                                    }
                                  },
                                  child: const Text('Rollback', style: TextStyle(fontSize: 11, color: AppTheme.accent)),
                                ),
                              );
                            },
                          ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(ctx),
                  child: const Text('Close', style: TextStyle(color: AppTheme.textMuted)),
                ),
              ],
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: const Text('Settings'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, size: 18),
          onPressed: () => Navigator.of(context).pop(),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, size: 20),
            tooltip: 'Reload Settings',
            onPressed: _loadAllSettingsData,
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        children: [
          // 1. Trading Sessions
          _buildSectionHeader('1. TRADING SESSIONS'),
          _buildSessionsCard(),
          const SizedBox(height: 18),

          // 2. Timeframes & Structure
          _buildSectionHeader('2. TIMEFRAME & EXECUTION'),
          _buildTimeframesCard(),
          const SizedBox(height: 18),

          // 3. Strategy Instructions
          _buildSectionHeader('3. STRATEGY INSTRUCTIONS'),
          _buildInstructionsCard(),
          const SizedBox(height: 18),

          // 4. Notification Preferences
          _buildSectionHeader('4. NOTIFICATION PREFERENCES'),
          _buildNotificationPreferencesCard(),
          const SizedBox(height: 18),

          // 5. AI Reasoning Engine (SaaS Model)
          _buildSectionHeader('5. AI MACRO REASONING ENGINE (SAAS)'),
          _buildAiEngineCard(),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        title,
        style: const TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w700,
          color: AppTheme.textMuted,
          letterSpacing: 1.0,
        ),
      ),
    );
  }

  // --- 1. Sessions Card ---
  Widget _buildSessionsCard() {
    final active = _currentSession?.activeSessions ?? [];

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.border),
      ),
      child: _isLoadingSession
          ? const Center(child: Padding(padding: EdgeInsets.all(8.0), child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.textSecondary)))
          : Column(
              children: [
                _buildSessionRow('Asian Session', '00:00 - 08:00 UTC (Tokyo/Sydney)', active.contains('asian')),
                const Divider(height: 16, color: AppTheme.borderSubtle),
                _buildSessionRow('London Session', '08:00 - 16:00 UTC (DST-Aware European)', active.contains('london')),
                const Divider(height: 16, color: AppTheme.borderSubtle),
                _buildSessionRow('New York Session', '13:00 - 21:00 UTC (US/Killzone Overlap)', active.contains('new_york')),
              ],
            ),
    );
  }

  Widget _buildSessionRow(String name, String timeUtc, bool isActive) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(name, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.textPrimary)),
              const SizedBox(height: 2),
              Text(timeUtc, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
            ],
          ),
        ),
        const SizedBox(width: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          decoration: BoxDecoration(
            color: isActive ? AppTheme.upGreen.withValues(alpha: 0.12) : AppTheme.surfaceSubtle,
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: isActive ? AppTheme.upGreen.withValues(alpha: 0.4) : AppTheme.border),
          ),
          child: Text(
            isActive ? 'ACTIVE' : 'CLOSED',
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w700,
              color: isActive ? AppTheme.upGreen : AppTheme.textMuted,
            ),
          ),
        ),
      ],
    );
  }

  // --- 2. Timeframes Card ---
  Widget _buildTimeframesCard() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Default Analysis Timeframe', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.textPrimary)),
              DropdownButton<String>(
                value: _defaultTimeframe,
                dropdownColor: AppTheme.surface,
                underline: const SizedBox(),
                items: ['1m', '5m', '15m', '1h', '4h', '1d'].map((tf) {
                  return DropdownMenuItem<String>(
                    value: tf,
                    child: Text(tf.toUpperCase(), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppTheme.textPrimary)),
                  );
                }).toList(),
                onChanged: (val) {
                  if (val != null) setState(() => _defaultTimeframe = val);
                },
              ),
            ],
          ),
          const Divider(height: 16, color: AppTheme.borderSubtle),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Higher Timeframe Trend Bias', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.textPrimary)),
                    SizedBox(height: 2),
                    Text('Combines 15m execution with 1H/4H market structure', style: TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
                  ],
                ),
              ),
              Switch(
                value: _multiTimeframeConfirmation,
                activeThumbColor: AppTheme.accent,
                onChanged: (v) => setState(() => _multiTimeframeConfirmation = v),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // --- 3. Analysis Instructions Card ---
  Widget _buildInstructionsCard() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.border),
      ),
      child: _isLoadingStrategy
          ? const Center(child: Padding(padding: EdgeInsets.all(8.0), child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.textSecondary)))
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Active session-specific trading guidelines with audit trail and rollback capabilities.',
                  style: TextStyle(fontSize: 11, color: AppTheme.textSecondary, height: 1.3),
                ),
                const SizedBox(height: 12),
                _buildInstructionRow('Asian', _strategyConfig?.asian),
                const Divider(height: 14, color: AppTheme.borderSubtle),
                _buildInstructionRow('London', _strategyConfig?.london),
                const Divider(height: 14, color: AppTheme.borderSubtle),
                _buildInstructionRow('New York', _strategyConfig?.newYork),
              ],
            ),
    );
  }

  Widget _buildInstructionRow(String sessionTitle, SessionConfigItem? item) {
    final vNum = item?.version ?? 1;
    final text = item?.instructions ?? 'No active rules defined';

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('$sessionTitle Session Rules', overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.textPrimary)),
              const SizedBox(height: 2),
              Text('Version $vNum', style: const TextStyle(fontSize: 11, color: AppTheme.textMuted)),
            ],
          ),
        ),
        const SizedBox(width: 8),
        TextButton(
          onPressed: () => _showInstructionEditorModal(sessionTitle.toLowerCase().replaceAll(' ', '_'), text, vNum),
          child: const Text('Edit / History', style: TextStyle(fontSize: 12, color: AppTheme.accent)),
        ),
      ],
    );
  }

  // --- 4. Notification Preferences Card ---
  Widget _buildNotificationPreferencesCard() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Instant Push Notification Delivery', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.textPrimary)),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: _isDeviceRegistered ? AppTheme.upGreen.withOpacity(0.12) : AppTheme.accent.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: _isDeviceRegistered ? AppTheme.upGreen.withOpacity(0.4) : AppTheme.accent.withOpacity(0.4)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.circle, size: 7, color: _isDeviceRegistered ? AppTheme.upGreen : AppTheme.accent),
                    const SizedBox(width: 4),
                    Text(
                      _isDeviceRegistered ? 'CONNECTED' : 'STANDBY',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        color: _isDeviceRegistered ? AppTheme.upGreen : AppTheme.accent,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          const Text(
            'The AI 24/7 background engine issues high-probability push notifications as soon as a setup aligns with your session rules.',
            style: TextStyle(fontSize: 11, color: AppTheme.textSecondary, height: 1.3),
          ),
          const Divider(height: 18, color: AppTheme.borderSubtle),
          _buildPrefToggle('Notify on VALID SETUP', 'Criteria fully confirmed (ICT displacement + FVG)', _notifyValid, (v) => setState(() => _notifyValid = v)),
          const Divider(height: 12, color: AppTheme.borderSubtle),
          _buildPrefToggle('Notify on POTENTIAL SETUP', 'Partial criteria aligned; liquidity run in progress', _notifyPotential, (v) => setState(() => _notifyPotential = v)),
          const Divider(height: 12, color: AppTheme.borderSubtle),
          _buildPrefToggle('Notify on WATCH', 'Early session sweep detected', _notifyWatch, (v) => setState(() => _notifyWatch = v)),
          const Divider(height: 12, color: AppTheme.borderSubtle),
          _buildPrefToggle('Notify on INVALIDATED', 'Criteria breached or structure broken', _notifyInvalidated, (v) => setState(() => _notifyInvalidated = v)),
          const Divider(height: 14, color: AppTheme.borderSubtle),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Alert Cooldown', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.textPrimary)),
              DropdownButton<int>(
                value: _cooldownMinutes,
                dropdownColor: AppTheme.surface,
                underline: const SizedBox(),
                items: [5, 15, 30, 60].map((m) {
                  return DropdownMenuItem<int>(
                    value: m,
                    child: Text('$m mins', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.textPrimary)),
                  );
                }).toList(),
                onChanged: (val) {
                  if (val != null) setState(() => _cooldownMinutes = val);
                },
              ),
            ],
          ),
          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              icon: const Icon(Icons.notifications_active_rounded, size: 16, color: AppTheme.upGreen),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.upGreen.withOpacity(0.12),
                foregroundColor: AppTheme.upGreen,
                side: BorderSide(color: AppTheme.upGreen.withOpacity(0.4)),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                padding: const EdgeInsets.symmetric(vertical: 10),
              ),
              onPressed: _isSendingTestPush ? null : _sendTestPush,
              label: Text(
                _isSendingTestPush ? 'Dispatching Test Notification...' : 'Send Test Push Alert',
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPrefToggle(String title, String subtitle, bool val, Function(bool) onChanged) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.textPrimary)),
              const SizedBox(height: 2),
              Text(subtitle, style: const TextStyle(fontSize: 11, color: AppTheme.textMuted)),
            ],
          ),
        ),
        const SizedBox(width: 8),
        Switch(
          value: val,
          activeThumbColor: AppTheme.accent,
          onChanged: onChanged,
        ),
      ],
    );
  }

  // --- 5. AI Reasoning Engine Methods & UI ---
  Future<void> _loadMacroAiConfig() async {
    setState(() => _isLoadingAiConfig = true);
    try {
      final providers = await ApiService.getMacroAiProviders();
      final config = await ApiService.getMacroAiConfig();
      if (mounted) {
        setState(() {
          _supportedProviders = providers;
          _macroAiConfig = config;
          _macroReasoningEnabled = config.isEnabled;
          _selectedProviderId = config.provider;
          _selectedModelId = config.model;
          if (config.apiBaseUrl != null) {
            _customBaseUrlCtrl.text = config.apiBaseUrl!;
          }

          final prov = _supportedProviders.firstWhere(
            (p) => p.id == _selectedProviderId,
            orElse: () => _supportedProviders.isNotEmpty
                ? _supportedProviders.first
                : SupportedProvider(
                    id: 'groq',
                    name: 'Groq',
                    description: '',
                    defaultModel: 'llama-3.3-70b-versatile',
                  ),
          );
          _isCustomModel = prov.models.isNotEmpty && !prov.models.any((m) => m.id == _selectedModelId);
          if (_isCustomModel) {
            _customModelCtrl.text = _selectedModelId;
          }
          _isLoadingAiConfig = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _isLoadingAiConfig = false);
    }
  }

  Future<void> _testAiConnection() async {
    setState(() => _isTestingAiConnection = true);
    try {
      final effModel = _isCustomModel && _customModelCtrl.text.trim().isNotEmpty
          ? _customModelCtrl.text.trim()
          : _selectedModelId;
      final result = await ApiService.testMacroAiConnection(
        provider: _selectedProviderId,
        model: effModel,
        apiKey: _apiKeyCtrl.text.trim().isNotEmpty ? _apiKeyCtrl.text.trim() : null,
        apiBaseUrl: _customBaseUrlCtrl.text.trim().isNotEmpty ? _customBaseUrlCtrl.text.trim() : null,
      );
      if (mounted) {
        setState(() {
          _lastTestResult = result;
          _isTestingAiConnection = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              result.status == 'SUCCESS'
                  ? 'Connection verified (${result.latencyMs}ms): ${result.message}'
                  : 'Connection test failed: ${result.message}',
            ),
            backgroundColor: result.status == 'SUCCESS' ? AppTheme.upGreen : AppTheme.downRed,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isTestingAiConnection = false;
          _lastTestResult = MacroAiTestResult(
            status: 'FAILED',
            provider: _selectedProviderId,
            model: _selectedModelId,
            latencyMs: 0,
            message: 'Network error: $e',
          );
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Connection test error: $e'),
            backgroundColor: AppTheme.downRed,
          ),
        );
      }
    }
  }

  Future<void> _saveAiConfig() async {
    setState(() => _isSavingAiConfig = true);
    try {
      final effModel = _isCustomModel && _customModelCtrl.text.trim().isNotEmpty
          ? _customModelCtrl.text.trim()
          : _selectedModelId;
      final updated = await ApiService.saveMacroAiConfig(
        provider: _selectedProviderId,
        model: effModel,
        isEnabled: _macroReasoningEnabled,
        apiKey: _apiKeyCtrl.text.trim().isNotEmpty ? _apiKeyCtrl.text.trim() : null,
        apiBaseUrl: _customBaseUrlCtrl.text.trim().isNotEmpty ? _customBaseUrlCtrl.text.trim() : null,
      );
      if (mounted) {
        setState(() {
          _macroAiConfig = updated;
          _isSavingAiConfig = false;
          _apiKeyCtrl.clear();
        });
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('AI Macro Reasoning configuration saved securely.'),
            backgroundColor: AppTheme.upGreen,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isSavingAiConfig = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to save configuration: $e'),
            backgroundColor: AppTheme.downRed,
          ),
        );
      }
    }
  }

  Future<void> _removeAiCredentials() async {
    try {
      await ApiService.removeMacroAiCredentials();
      if (mounted) {
        await _loadMacroAiConfig();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Stored API key credentials removed from server.'),
            backgroundColor: AppTheme.accent,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to remove credentials: $e'),
            backgroundColor: AppTheme.downRed,
          ),
        );
      }
    }
  }

  Widget _buildAiEngineCard() {
    if (_isLoadingAiConfig && _macroAiConfig == null) {
      return Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: AppTheme.surface,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: AppTheme.border),
        ),
        child: const Center(
          child: CircularProgressIndicator(color: AppTheme.accent),
        ),
      );
    }

    final activeProvider = _supportedProviders.firstWhere(
      (p) => p.id == _selectedProviderId,
      orElse: () => SupportedProvider(
        id: 'groq',
        name: 'Groq (Ultra-Fast Llama 3.3)',
        description: 'Ultra-low latency inference.',
        defaultModel: 'llama-3.3-70b-versatile',
        supportsCustomBaseUrl: true,
      ),
    );

    final statusText = _lastTestResult?.status ?? _macroAiConfig?.lastTestStatus ?? 'NOT_TESTED';
    final isSuccess = statusText == 'SUCCESS';
    final isFailed = statusText == 'FAILED';

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'AI Macro Reasoning Engine',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: isSuccess
                      ? AppTheme.upGreen.withOpacity(0.12)
                      : (isFailed ? AppTheme.downRed.withOpacity(0.12) : AppTheme.accent.withOpacity(0.12)),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(
                    color: isSuccess
                        ? AppTheme.upGreen.withOpacity(0.4)
                        : (isFailed ? AppTheme.downRed.withOpacity(0.4) : AppTheme.accent.withOpacity(0.4)),
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.circle,
                      size: 7,
                      color: isSuccess ? AppTheme.upGreen : (isFailed ? AppTheme.downRed : AppTheme.accent),
                    ),
                    const SizedBox(width: 4),
                    Text(
                      statusText.replaceAll('_', ' '),
                      style: TextStyle(
                        fontSize: 9,
                        fontWeight: FontWeight.w700,
                        color: isSuccess ? AppTheme.upGreen : (isFailed ? AppTheme.downRed : AppTheme.accent),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          const Text(
            'Configure an AI provider for macroeconomic research and market-context analysis.',
            style: TextStyle(fontSize: 11, color: AppTheme.textSecondary, height: 1.3),
          ),
          const Divider(height: 18, color: AppTheme.borderSubtle),

          // Enable / Disable Toggle
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Enable Macro Reasoning', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.textPrimary)),
                    SizedBox(height: 2),
                    Text('Synthesize DXY, calendar deviations, and SMC liquidity order flow', style: TextStyle(fontSize: 11, color: AppTheme.textMuted)),
                  ],
                ),
              ),
              Switch(
                value: _macroReasoningEnabled,
                activeThumbColor: AppTheme.accent,
                onChanged: (val) => setState(() => _macroReasoningEnabled = val),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Provider Dropdown
          DropdownButtonFormField<String>(
            isExpanded: true,
            value: _supportedProviders.any((p) => p.id == _selectedProviderId) ? _selectedProviderId : (_supportedProviders.isNotEmpty ? _supportedProviders.first.id : 'groq'),
            dropdownColor: AppTheme.surface,
            decoration: InputDecoration(
              isDense: true,
              filled: true,
              fillColor: AppTheme.background,
              labelText: 'AI Provider',
              labelStyle: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
              contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: const BorderSide(color: AppTheme.border)),
            ),
            items: _supportedProviders.isNotEmpty
                ? _supportedProviders.map((p) {
                    return DropdownMenuItem<String>(
                      value: p.id,
                      child: Text(p.name, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, color: AppTheme.textPrimary)),
                    );
                  }).toList()
                : [
                    const DropdownMenuItem(value: 'groq', child: Text('Groq (Ultra-Fast Llama 3.3)', style: TextStyle(fontSize: 12))),
                    const DropdownMenuItem(value: 'xai', child: Text('xAI Grok', style: TextStyle(fontSize: 12))),
                    const DropdownMenuItem(value: 'gemini', child: Text('Google Gemini', style: TextStyle(fontSize: 12))),
                    const DropdownMenuItem(value: 'openai', child: Text('OpenAI GPT', style: TextStyle(fontSize: 12))),
                    const DropdownMenuItem(value: 'deepseek', child: Text('DeepSeek AI', style: TextStyle(fontSize: 12))),
                  ],
            onChanged: (val) {
              if (val != null && val != _selectedProviderId) {
                setState(() {
                  _selectedProviderId = val;
                  final prov = _supportedProviders.firstWhere((p) => p.id == val, orElse: () => activeProvider);
                  _selectedModelId = prov.defaultModel;
                  _isCustomModel = false;
                  _customBaseUrlCtrl.text = prov.defaultBaseUrl ?? '';
                });
              }
            },
          ),
          const SizedBox(height: 10),

          // Model Selection Dropdown
          DropdownButtonFormField<String>(
            isExpanded: true,
            value: _isCustomModel ? 'CUSTOM_MODEL' : _selectedModelId,
            dropdownColor: AppTheme.surface,
            decoration: InputDecoration(
              isDense: true,
              filled: true,
              fillColor: AppTheme.background,
              labelText: 'Reasoning Model',
              labelStyle: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
              contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: const BorderSide(color: AppTheme.border)),
            ),
            items: [
              ...activeProvider.models.map((m) {
                return DropdownMenuItem<String>(
                  value: m.id,
                  child: Text('${m.name} (${m.id})', overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, color: AppTheme.textPrimary)),
                );
              }),
              const DropdownMenuItem<String>(
                value: 'CUSTOM_MODEL',
                child: Text('Custom Model ID...', style: TextStyle(fontSize: 12, color: AppTheme.accent)),
              ),
            ],
            onChanged: (val) {
              if (val != null) {
                setState(() {
                  if (val == 'CUSTOM_MODEL') {
                    _isCustomModel = true;
                  } else {
                    _isCustomModel = false;
                    _selectedModelId = val;
                  }
                });
              }
            },
          ),

          if (_isCustomModel) ...[
            const SizedBox(height: 10),
            TextField(
              controller: _customModelCtrl,
              style: const TextStyle(fontSize: 12, color: AppTheme.textPrimary),
              decoration: InputDecoration(
                isDense: true,
                filled: true,
                fillColor: AppTheme.background,
                labelText: 'Enter Custom Model ID',
                labelStyle: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
                hintText: 'e.g. llama-3.3-70b-versatile or grok-2',
                hintStyle: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
                contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: const BorderSide(color: AppTheme.border)),
              ),
            ),
          ],

          if (activeProvider.supportsCustomBaseUrl) ...[
            const SizedBox(height: 10),
            TextField(
              controller: _customBaseUrlCtrl,
              style: const TextStyle(fontSize: 12, fontFamily: 'monospace', color: AppTheme.textPrimary),
              decoration: InputDecoration(
                isDense: true,
                filled: true,
                fillColor: AppTheme.background,
                labelText: 'Custom API Base URL (Optional)',
                labelStyle: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
                hintText: activeProvider.defaultBaseUrl ?? 'https://api.openai.com/v1',
                hintStyle: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
                contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: const BorderSide(color: AppTheme.border)),
              ),
            ),
          ],
          const SizedBox(height: 10),

          // API Key Input with Eye Toggle & Secure Masking
          TextField(
            controller: _apiKeyCtrl,
            obscureText: _obscureApiKey,
            style: const TextStyle(fontSize: 12, fontFamily: 'monospace', color: AppTheme.textPrimary),
            decoration: InputDecoration(
              isDense: true,
              filled: true,
              fillColor: AppTheme.background,
              labelText: _macroAiConfig?.hasApiKey == true ? 'API Key (Configured)' : 'Provider API Key',
              labelStyle: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
              hintText: _macroAiConfig?.hasApiKey == true
                  ? (_macroAiConfig?.maskedKey ?? '••••••••••••••••')
                  : 'Paste your API key here',
              hintStyle: TextStyle(
                fontSize: 11,
                fontFamily: 'monospace',
                color: _macroAiConfig?.hasApiKey == true ? AppTheme.upGreen : AppTheme.textMuted,
              ),
              suffixIcon: IconButton(
                icon: Icon(_obscureApiKey ? Icons.visibility_outlined : Icons.visibility_off_outlined, size: 16, color: AppTheme.textMuted),
                onPressed: () => setState(() => _obscureApiKey = !_obscureApiKey),
              ),
              contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: const BorderSide(color: AppTheme.border)),
            ),
          ),
          const SizedBox(height: 4),
          const Text(
            'Keys are encrypted at rest with Fernet. They are never sent back to the client or logged.',
            style: TextStyle(fontSize: 10, color: AppTheme.textMuted),
          ),
          const SizedBox(height: 12),

          // Diagnostic Test Result Callout if available
          if (_lastTestResult != null) ...[
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: isSuccess ? AppTheme.upGreen.withOpacity(0.08) : AppTheme.downRed.withOpacity(0.08),
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: isSuccess ? AppTheme.upGreen.withOpacity(0.3) : AppTheme.downRed.withOpacity(0.3)),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    isSuccess ? Icons.check_circle_outline_rounded : Icons.error_outline_rounded,
                    size: 16,
                    color: isSuccess ? AppTheme.upGreen : AppTheme.downRed,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          isSuccess
                              ? 'Verified (${_lastTestResult!.latencyMs}ms)'
                              : 'Connection Diagnostic Failed',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                            color: isSuccess ? AppTheme.upGreen : AppTheme.downRed,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          _lastTestResult!.message,
                          style: TextStyle(
                            fontSize: 10,
                            color: isSuccess ? AppTheme.textPrimary : AppTheme.downRed,
                            height: 1.3,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
          ],

          // Action Buttons: Test Connection & Save Configuration
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  icon: _isTestingAiConnection
                      ? const SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.accent))
                      : const Icon(Icons.bolt_rounded, size: 15, color: AppTheme.accent),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppTheme.accent,
                    side: const BorderSide(color: AppTheme.border),
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                  ),
                  onPressed: _isTestingAiConnection ? null : _testAiConnection,
                  label: Text(
                    _isTestingAiConnection ? 'Testing...' : 'Test Connection',
                    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: ElevatedButton.icon(
                  icon: _isSavingAiConfig
                      ? const SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : const Icon(Icons.check_rounded, size: 15),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.accent,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                  ),
                  onPressed: _isSavingAiConfig ? null : _saveAiConfig,
                  label: Text(
                    _isSavingAiConfig ? 'Saving...' : 'Save Config',
                    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
                  ),
                ),
              ),
            ],
          ),

          // Remove Key Action if a key exists
          if (_macroAiConfig?.hasApiKey == true) ...[
            const SizedBox(height: 8),
            Center(
              child: TextButton.icon(
                icon: const Icon(Icons.delete_outline_rounded, size: 13, color: AppTheme.downRed),
                style: TextButton.styleFrom(foregroundColor: AppTheme.downRed),
                onPressed: _removeAiCredentials,
                label: const Text('Remove Stored API Key', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600)),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

