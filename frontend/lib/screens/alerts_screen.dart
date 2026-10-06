import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'instrument_screen.dart';

/// Clean model representing a chronological market alert event
class MarketAlertItem {
  final int id;
  final DateTime timestamp;
  final String symbol;
  final String session;
  final String state;
  final String message;
  final bool isTriggered;

  MarketAlertItem({
    required this.id,
    required this.timestamp,
    required this.symbol,
    required this.session,
    required this.state,
    required this.message,
    this.isTriggered = false,
  });

  factory MarketAlertItem.fromAnalysis(dynamic item) {
    // If it's an AIAnalysisRecord or JSON map
    DateTime time;
    if (item.timestamp is DateTime) {
      time = item.timestamp;
    } else {
      time = DateTime.tryParse(item.timestamp.toString()) ?? DateTime.now();
    }

    String stateStr = item.state.toString().toUpperCase().replaceAll('ANALYSISSTATEENUM.', '').replaceAll('_', ' ');
    String msg = item.summary.toString();
    if (msg.isEmpty || msg == 'null') {
      if (stateStr.contains('VALID')) {
        msg = 'Valid setup confirmed under session rules';
      } else if (stateStr.contains('POTENTIAL')) {
        msg = 'Potential setup detected';
      } else if (stateStr.contains('INVALID')) {
        msg = 'Condition invalidated';
      } else if (stateStr.contains('WATCH')) {
        msg = 'Watch condition flagged';
      } else {
        msg = 'Routine evaluation completed';
      }
    }

    return MarketAlertItem(
      id: item.id is int ? item.id : 0,
      timestamp: time,
      symbol: item.symbol.toString().toUpperCase(),
      session: item.sessionName.toString().isEmpty
          ? 'London'
          : '${item.sessionName[0].toUpperCase()}${item.sessionName.substring(1)}',
      state: stateStr,
      message: msg,
      isTriggered: stateStr.contains('VALID') || stateStr.contains('POTENTIAL'),
    );
  }

  factory MarketAlertItem.fromNotification(Map<String, dynamic> json) {
    DateTime time = DateTime.tryParse(json['created_at']?.toString() ?? '') ?? DateTime.now();
    final payload = (json['payload'] as Map<String, dynamic>?) ?? {};
    final sym = (payload['symbol'] ?? json['title'] ?? 'MARKET').toString().toUpperCase();
    final sess = (payload['session'] ?? 'Session').toString();
    final state = (payload['state'] ?? 'ALERT').toString().toUpperCase().replaceAll('_', ' ');

    return MarketAlertItem(
      id: json['id'] is int ? json['id'] : 0,
      timestamp: time,
      symbol: sym,
      session: sess.isEmpty ? 'Active' : '${sess[0].toUpperCase()}${sess.substring(1)}',
      state: state,
      message: json['body']?.toString() ?? 'Strategy rule triggered',
      isTriggered: true,
    );
  }
}

class AlertsScreen extends StatefulWidget {
  final Function(String symbol)? onSelectSymbol;

  const AlertsScreen({
    Key? key,
    this.onSelectSymbol,
  }) : super(key: key);

  @override
  State<AlertsScreen> createState() => _AlertsScreenState();
}

class _AlertsScreenState extends State<AlertsScreen> {
  List<MarketAlertItem> _alerts = [];
  bool _isLoading = true;
  String? _errorMessage;
  String _selectedFilter = 'ALL';
  List<String> _filterSymbols = ['ALL'];

  @override
  void initState() {
    super.initState();
    _loadAlerts();
  }

  Future<void> _loadAlerts() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final List<MarketAlertItem> collected = [];

      // 1. Fetch backend notifications
      try {
        final notificationsRaw = await ApiService.getNotifications();
        for (var n in notificationsRaw) {
          if (n is Map<String, dynamic>) {
            collected.add(MarketAlertItem.fromNotification(n));
          }
        }
      } catch (_) {}

      // 2. Fetch analysis history for alerts
      try {
        final analysisList = await ApiService.getAnalysisHistory(limit: 50);
        for (var a in analysisList) {
          collected.add(MarketAlertItem.fromAnalysis(a));
        }
      } catch (_) {}

      // Sort chronological descending (latest first)
      collected.sort((a, b) => b.timestamp.compareTo(a.timestamp));

      // Extract unique symbols for filtering
      final symSet = <String>{'ALL'};
      for (var a in collected) {
        if (a.symbol.isNotEmpty) symSet.add(a.symbol);
      }

      setState(() {
        _alerts = collected;
        _filterSymbols = symSet.toList();
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  void _onAlertTap(MarketAlertItem alert) {
    if (widget.onSelectSymbol != null) {
      widget.onSelectSymbol!(alert.symbol);
    } else {
      Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => InstrumentScreen(symbol: alert.symbol),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _selectedFilter == 'ALL'
        ? _alerts
        : _alerts.where((a) => a.symbol == _selectedFilter).toList();

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: const Text('Alerts'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, size: 20),
            onPressed: _loadAlerts,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: AppTheme.textSecondary,
              ),
            )
          : RefreshIndicator(
              onRefresh: _loadAlerts,
              color: AppTheme.textPrimary,
              backgroundColor: AppTheme.surface,
              child: ListView(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                children: [
                  // Filter Chips
                  if (_filterSymbols.length > 2) ...[
                    _buildFilterRow(),
                    const SizedBox(height: 14),
                  ],

                  if (_errorMessage != null) ...[
                    _buildNoticeBanner(_errorMessage!),
                    const SizedBox(height: 12),
                  ],

                  if (filtered.isEmpty)
                    _buildEmptyState()
                  else
                    _buildChronologicalTimeline(filtered),
                ],
              ),
            ),
    );
  }

  Widget _buildFilterRow() {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: _filterSymbols.map((sym) {
          final isSelected = _selectedFilter == sym;
          return Padding(
            padding: const EdgeInsets.only(right: 6),
            child: InkWell(
              borderRadius: BorderRadius.circular(4),
              onTap: () => setState(() => _selectedFilter = sym),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: isSelected ? AppTheme.surfaceSubtle : AppTheme.surface,
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(
                    color: isSelected ? AppTheme.accent : AppTheme.border,
                    width: 1,
                  ),
                ),
                child: Text(
                  sym,
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                    color: isSelected ? AppTheme.textPrimary : AppTheme.textMuted,
                  ),
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildChronologicalTimeline(List<MarketAlertItem> items) {
    return Container(
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.border),
      ),
      child: ListView.separated(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        itemCount: items.length,
        separatorBuilder: (_, __) => const Divider(
          height: 1,
          thickness: 1,
          color: AppTheme.borderSubtle,
        ),
        itemBuilder: (context, index) {
          final item = items[index];
          final timeStr = DateFormat('HH:mm').format(item.timestamp.toLocal());

          Color stateColor = AppTheme.textMuted;
          if (item.state.contains('VALID')) {
            stateColor = AppTheme.validSetup;
          } else if (item.state.contains('POTENTIAL')) {
            stateColor = AppTheme.potentialSetup;
          } else if (item.state.contains('INVALID')) {
            stateColor = AppTheme.invalidated;
          } else if (item.state.contains('WATCH')) {
            stateColor = AppTheme.watch;
          }

          return InkWell(
            onTap: () => _onAlertTap(item),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Meta Line: 10:42 | XAUUSD | London
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.baseline,
                    textBaseline: TextBaseline.alphabetic,
                    children: [
                      // Timestamp (10:42)
                      Text(
                        timeStr,
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                          color: AppTheme.textPrimary,
                          fontFamily: 'monospace',
                        ),
                      ),
                      const SizedBox(width: 14),
                      // Symbol (XAUUSD)
                      Text(
                        item.symbol,
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                          color: AppTheme.textPrimary,
                        ),
                      ),
                      const SizedBox(width: 12),
                      // Session (London)
                      Text(
                        item.session,
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppTheme.textSecondary,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      const Spacer(),
                      // Quiet state indicator tag
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: stateColor.withOpacity(0.12),
                          borderRadius: BorderRadius.circular(3),
                        ),
                        child: Text(
                          item.state,
                          style: TextStyle(
                            fontSize: 9,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 0.5,
                            color: stateColor,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  // Alert Message
                  Text(
                    item.message,
                    style: const TextStyle(
                      fontSize: 13,
                      height: 1.4,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildEmptyState() {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 48, horizontal: 24),
      alignment: Alignment.center,
      child: Column(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppTheme.surfaceSubtle,
              border: Border.all(color: AppTheme.border),
            ),
            child: const Icon(Icons.notifications_none_rounded, size: 22, color: AppTheme.textMuted),
          ),
          const SizedBox(height: 14),
          const Text(
            'No Alerts Recorded',
            style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppTheme.textPrimary),
          ),
          const SizedBox(height: 6),
          const Text(
            'Strategy conditions will trigger chronological timeline entries as the market progresses.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 12, height: 1.4, color: AppTheme.textMuted),
          ),
        ],
      ),
    );
  }

  Widget _buildNoticeBanner(String msg) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppTheme.border),
      ),
      child: Text(
        'Offline notice: $msg',
        style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
      ),
    );
  }
}
