import 'package:flutter/material.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../models/session_state.dart';
import '../models/strategy_instruction.dart';

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

  // Device push registration state (kept completely silent and secure from end-user)
  bool _isDeviceRegistered = false;
  bool _isSendingTestPush = false;

  @override
  void initState() {
    super.initState();
    _loadAllSettingsData();
  }

  Future<void> _loadAllSettingsData() async {
    _loadSessionInfo();
    _loadStrategyInfo();
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
                  Text(
                    '${sessionName.toUpperCase()} STRATEGY INSTRUCTIONS (v$version)',
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.textPrimary,
                    ),
                  ),
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
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(name, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.textPrimary)),
            const SizedBox(height: 2),
            Text(timeUtc, style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
          ],
        ),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          decoration: BoxDecoration(
            color: isActive ? AppTheme.upGreen.withOpacity(0.12) : AppTheme.surfaceSubtle,
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: isActive ? AppTheme.upGreen.withOpacity(0.4) : AppTheme.border),
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
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('$sessionTitle Session Rules', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.textPrimary)),
            const SizedBox(height: 2),
            Text('Version $vNum', style: const TextStyle(fontSize: 11, color: AppTheme.textMuted)),
          ],
        ),
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
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.textPrimary)),
            const SizedBox(height: 2),
            Text(subtitle, style: const TextStyle(fontSize: 11, color: AppTheme.textMuted)),
          ],
        ),
        Switch(
          value: val,
          activeThumbColor: AppTheme.accent,
          onChanged: onChanged,
        ),
      ],
    );
  }
}
