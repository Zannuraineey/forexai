import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
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
  // 1. Symbols
  List<String> _activeSymbols = [];
  bool _isLoadingSymbols = false;

  // 2. Sessions
  CurrentSessionState? _currentSession;

  // 3. Timeframes
  String _defaultTimeframe = '15m';
  bool _multiTimeframeConfirmation = true;

  // 4. Notifications & Device
  final TextEditingController _tokenCtrl = TextEditingController();
  bool _isLoadingFcm = false;
  bool _isRegisteringDevice = false;
  bool _isDeviceRegistered = false;
  bool _isSendingTestPush = false;

  // 5. Analysis Instructions
  StrategySessionsConfig? _strategyConfig;
  bool _isLoadingStrategy = false;

  // 6. Notification Preferences
  bool _notifyValid = true;
  bool _notifyPotential = true;
  bool _notifyWatch = false;
  bool _notifyInvalidated = false;
  int _cooldownMinutes = 15;

  // 7. Data Source
  final String _dataSourceName = 'Deriv Public WebSocket Gateway';
  final String _wsEndpoint = 'wss://api.derivws.com/trading/v1/options/ws/public';

  // 8. App Preferences
  final TextEditingController _urlCtrl =
      TextEditingController(text: ApiService.baseUrl);

  @override
  void initState() {
    super.initState();
    _loadAllSettingsData();
  }

  Future<void> _loadAllSettingsData() async {
    _loadActiveSymbols();
    _loadSessionInfo();
    _loadStrategyInfo();
    _loadFcmToken();
  }

  Future<void> _loadFcmToken() async {
    setState(() => _isLoadingFcm = true);
    try {
      final messaging = FirebaseMessaging.instance;
      await messaging.requestPermission(
        alert: true,
        badge: true,
        sound: true,
      );
      final token = await messaging.getToken();
      if (token != null && mounted) {
        setState(() {
          _tokenCtrl.text = token;
          _isLoadingFcm = false;
        });
        await _registerDevice(silent: true);
      } else {
        if (mounted) setState(() => _isLoadingFcm = false);
      }
    } catch (e) {
      debugPrint('FCM Token load note: $e');
      if (mounted) setState(() => _isLoadingFcm = false);
    }
  }

  Future<void> _loadActiveSymbols() async {
    setState(() => _isLoadingSymbols = true);
    try {
      final syms = await ApiService.getActiveSymbols();
      if (mounted) {
        setState(() {
          _activeSymbols = syms;
          _isLoadingSymbols = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _isLoadingSymbols = false);
    }
  }

  Future<void> _loadSessionInfo() async {
    try {
      final sess = await ApiService.getCurrentSession();
      if (mounted) setState(() => _currentSession = sess);
    } catch (_) {}
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

  void _saveApiUrl() {
    final url = _urlCtrl.text.trim();
    if (url.isNotEmpty) {
      setState(() => ApiService.baseUrl = url);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: AppTheme.surfaceSubtle,
          content: Text('Gateway URL set to: $url', style: const TextStyle(color: AppTheme.textPrimary)),
        ),
      );
    }
  }

  Future<void> _registerDevice({bool silent = false}) async {
    final token = _tokenCtrl.text.trim();
    if (token.isEmpty) return;
    setState(() => _isRegisteringDevice = true);
    try {
      await ApiService.registerDevice(
        fcmToken: token,
        platform: 'android',
      );
      if (mounted) {
        setState(() => _isDeviceRegistered = true);
        if (!silent) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              backgroundColor: AppTheme.surfaceSubtle,
              content: Text('Device push token registered with server', style: TextStyle(color: AppTheme.upGreen)),
            ),
          );
        }
      }
    } catch (e) {
      if (mounted && !silent) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: AppTheme.surfaceSubtle,
            content: Text('Registration error: $e', style: const TextStyle(color: AppTheme.downRed)),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isRegisteringDevice = false);
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
                  : 'Test alert submitted to backend.',
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
        borderRadius: BorderRadius.vertical(top: Radius.circular(14)),
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
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
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
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, size: 20),
            onPressed: _loadAllSettingsData,
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        children: [
          // 1. Symbols
          _buildSectionHeader('1. SYMBOLS & WATCHLIST'),
          _buildSymbolsCard(),
          const SizedBox(height: 18),

          // 2. Sessions
          _buildSectionHeader('2. TRADING SESSIONS'),
          _buildSessionsCard(),
          const SizedBox(height: 18),

          // 3. Timeframes
          _buildSectionHeader('3. TIMEFRAMES'),
          _buildTimeframesCard(),
          const SizedBox(height: 18),

          // 4. Notifications
          _buildSectionHeader('4. NOTIFICATIONS'),
          _buildNotificationsCard(),
          const SizedBox(height: 18),

          // 5. Analysis Instructions
          _buildSectionHeader('5. STRATEGY INSTRUCTIONS'),
          _buildInstructionsCard(),
          const SizedBox(height: 18),

          // 6. Notification Preferences
          _buildSectionHeader('6. NOTIFICATION PREFERENCES'),
          _buildNotificationPreferencesCard(),
          const SizedBox(height: 18),

          // 7. Data Source
          _buildSectionHeader('7. DATA SOURCE'),
          _buildDataSourceCard(),
          const SizedBox(height: 18),

          // 8. App Preferences
          _buildSectionHeader('8. APP PREFERENCES'),
          _buildAppPreferencesCard(),
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

  // --- 1. Symbols Card ---
  Widget _buildSymbolsCard() {
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
              const Text('Active Pairs', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.textPrimary)),
              Text(
                '${_activeSymbols.length} enabled',
                style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary, fontWeight: FontWeight.w500),
              ),
            ],
          ),
          const SizedBox(height: 10),
          _isLoadingSymbols
              ? const Center(child: Padding(padding: EdgeInsets.all(8.0), child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.textSecondary)))
              : Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: _activeSymbols.map((sym) {
                    return Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: AppTheme.surfaceSubtle,
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: AppTheme.border),
                      ),
                      child: Text(
                        sym,
                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppTheme.textPrimary),
                      ),
                    );
                  }).toList(),
                ),
          const SizedBox(height: 10),
          const Text(
            'To enable/disable pairs (Forex, Metals, Crash & Boom, Indices, Baskets), use the "+ Add Pairs" catalog drawer on the Markets tab.',
            style: TextStyle(fontSize: 11, color: AppTheme.textMuted, height: 1.3),
          ),
        ],
      ),
    );
  }

  // --- 2. Sessions Card ---
  Widget _buildSessionsCard() {
    final active = _currentSession?.activeSessions ?? [];

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        children: [
          _buildSessionRow('Asian Session', '00:00 - 08:00 UTC', active.contains('asian')),
          const Divider(height: 16, color: AppTheme.borderSubtle),
          _buildSessionRow('London Session', '08:00 - 16:00 UTC (DST Aware)', active.contains('london')),
          const Divider(height: 16, color: AppTheme.borderSubtle),
          _buildSessionRow('New York Session', '13:00 - 21:00 UTC (DST Aware)', active.contains('new_york')),
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

  // --- 3. Timeframes Card ---
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
                    Text('Combines 15m execution with 1H/4H structure', style: TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
                  ],
                ),
              ),
              Switch(
                value: _multiTimeframeConfirmation,
                activeColor: AppTheme.accent,
                onChanged: (v) => setState(() => _multiTimeframeConfirmation = v),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // --- 4. Notifications Card ---
  Widget _buildNotificationsCard() {
    final hasToken = _tokenCtrl.text.trim().isNotEmpty;
    final isConnected = hasToken && _isDeviceRegistered;

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
              const Text('Firebase Cloud Messaging (FCM)', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.textPrimary)),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: isConnected ? AppTheme.upGreen.withOpacity(0.15) : AppTheme.accent.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: isConnected ? AppTheme.upGreen.withOpacity(0.5) : AppTheme.accent.withOpacity(0.5)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.circle, size: 8, color: isConnected ? AppTheme.upGreen : AppTheme.accent),
                    const SizedBox(width: 4),
                    Text(
                      isConnected ? 'CONNECTED' : (hasToken ? 'READY' : (_isLoadingFcm ? 'FETCHING...' : 'DISCONNECTED')),
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        color: isConnected ? AppTheme.upGreen : AppTheme.accent,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          const Text(
            'Your device token allows the 24/7 background AI scanner to send instant push alerts before setup execution.',
            style: TextStyle(fontSize: 11, color: AppTheme.textSecondary, height: 1.3),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _tokenCtrl,
            maxLines: 2,
            readOnly: true,
            style: const TextStyle(fontSize: 11, fontFamily: 'monospace', color: AppTheme.textPrimary),
            decoration: InputDecoration(
              filled: true,
              fillColor: AppTheme.background,
              hintText: _isLoadingFcm ? 'Retrieving Firebase device token...' : 'No FCM Token found yet',
              hintStyle: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
              contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: const BorderSide(color: AppTheme.border)),
              suffixIcon: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  IconButton(
                    icon: const Icon(Icons.copy, size: 18, color: AppTheme.accent),
                    tooltip: 'Copy Token',
                    onPressed: hasToken
                        ? () {
                            Clipboard.setData(ClipboardData(text: _tokenCtrl.text.trim()));
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                backgroundColor: AppTheme.surfaceSubtle,
                                content: Text('FCM Token copied to clipboard', style: TextStyle(color: AppTheme.upGreen)),
                              ),
                            );
                          }
                        : null,
                  ),
                  IconButton(
                    icon: const Icon(Icons.refresh, size: 18, color: AppTheme.textSecondary),
                    tooltip: 'Refresh Token',
                    onPressed: _isLoadingFcm ? null : _loadFcmToken,
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  icon: const Icon(Icons.app_registration, size: 16),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.surfaceSubtle,
                    foregroundColor: AppTheme.textPrimary,
                    side: const BorderSide(color: AppTheme.border),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                    padding: const EdgeInsets.symmetric(vertical: 10),
                  ),
                  onPressed: (_isRegisteringDevice || !hasToken) ? null : () => _registerDevice(silent: false),
                  label: Text(_isRegisteringDevice ? 'Registering...' : 'Register Device', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: ElevatedButton.icon(
                  icon: const Icon(Icons.notifications_active, size: 16, color: AppTheme.upGreen),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.upGreen.withOpacity(0.12),
                    foregroundColor: AppTheme.upGreen,
                    side: BorderSide(color: AppTheme.upGreen.withOpacity(0.4)),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                    padding: const EdgeInsets.symmetric(vertical: 10),
                  ),
                  onPressed: _isSendingTestPush ? null : _sendTestPush,
                  label: Text(_isSendingTestPush ? 'Sending...' : 'Test Push Alert', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // --- 5. Analysis Instructions Card ---
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

  // --- 6. Notification Preferences Card ---
  Widget _buildNotificationPreferencesCard() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        children: [
          _buildPrefToggle('Notify on VALID SETUP', 'Criteria fully satisfied', _notifyValid, (v) => setState(() => _notifyValid = v)),
          const Divider(height: 12, color: AppTheme.borderSubtle),
          _buildPrefToggle('Notify on POTENTIAL SETUP', 'Partial criteria aligned', _notifyPotential, (v) => setState(() => _notifyPotential = v)),
          const Divider(height: 12, color: AppTheme.borderSubtle),
          _buildPrefToggle('Notify on WATCH', 'Early session liquidity sweep', _notifyWatch, (v) => setState(() => _notifyWatch = v)),
          const Divider(height: 12, color: AppTheme.borderSubtle),
          _buildPrefToggle('Notify on INVALIDATED', 'Criteria breached or cancelled', _notifyInvalidated, (v) => setState(() => _notifyInvalidated = v)),
          const Divider(height: 12, color: AppTheme.borderSubtle),
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
          activeColor: AppTheme.accent,
          onChanged: onChanged,
        ),
      ],
    );
  }

  // --- 7. Data Source Card ---
  Widget _buildDataSourceCard() {
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
              Text(_dataSourceName, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.textPrimary)),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: AppTheme.upGreen.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: const Text('STREAMING', style: TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: AppTheme.upGreen)),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(_wsEndpoint, style: const TextStyle(fontSize: 11, fontFamily: 'monospace', color: AppTheme.textSecondary)),
          const SizedBox(height: 10),
          const Text(
            'Live quotes and candles are received via WebSocket subscriptions. Missing historic bars are reconstructed automatically on backend launch.',
            style: TextStyle(fontSize: 11, color: AppTheme.textMuted, height: 1.3),
          ),
        ],
      ),
    );
  }

  // --- 8. App Preferences Card ---
  Widget _buildAppPreferencesCard() {
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
          const Text('Backend Gateway URL', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.textPrimary)),
          const SizedBox(height: 8),
          TextField(
            controller: _urlCtrl,
            style: const TextStyle(fontSize: 12, fontFamily: 'monospace', color: AppTheme.textPrimary),
            decoration: InputDecoration(
              filled: true,
              fillColor: AppTheme.background,
              contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: const BorderSide(color: AppTheme.border)),
            ),
          ),
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.surfaceSubtle,
                foregroundColor: AppTheme.textPrimary,
                side: const BorderSide(color: AppTheme.border),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                padding: const EdgeInsets.symmetric(vertical: 10),
              ),
              onPressed: _saveApiUrl,
              child: const Text('Update Base URL', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
            ),
          ),
        ],
      ),
    );
  }
}
