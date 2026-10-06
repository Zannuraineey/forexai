import 'dart:async';
import 'package:flutter/material.dart';
import '../models/market_item.dart';
import '../models/session_state.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'instrument_screen.dart';

class MarketsScreen extends StatefulWidget {
  final Function(String symbol) onSelectInstrumentForAnalysis;

  const MarketsScreen({
    Key? key,
    required this.onSelectInstrumentForAnalysis,
  }) : super(key: key);

  @override
  State<MarketsScreen> createState() => _MarketsScreenState();
}

class _MarketsScreenState extends State<MarketsScreen> {
  List<MarketItem> _items = [];
  CurrentSessionState? _sessionState;
  bool _isLoading = true;
  String? _errorMessage;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _loadData();
    // Auto-refresh market prices every 4 seconds
    _refreshTimer = Timer.periodic(const Duration(seconds: 4), (_) {
      if (mounted) {
        _autoRefreshData();
      }
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _autoRefreshData() async {
    try {
      final items = await ApiService.getWatchlistSummary(forceRefresh: true);
      if (mounted) {
        setState(() {
          _items = items;
        });
      }
    } catch (_) {}
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final sessionFuture = ApiService.getCurrentSession();
      final watchlistFuture = ApiService.getWatchlistSummary();

      final results = await Future.wait([sessionFuture, watchlistFuture]);
      setState(() {
        _sessionState = results[0] as CurrentSessionState;
        _items = results[1] as List<MarketItem>;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  void _showCatalogModal() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppTheme.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) => _CatalogBottomSheet(
        onToggled: () => _loadData(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: const Text('Markets'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, size: 20),
            onPressed: _loadData,
          ),
          IconButton(
            icon: const Icon(Icons.add_rounded, size: 22),
            tooltip: 'Add / Remove Pairs',
            onPressed: _showCatalogModal,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.textSecondary))
          : RefreshIndicator(
              onRefresh: _loadData,
              color: AppTheme.textPrimary,
              backgroundColor: AppTheme.surface,
              child: ListView(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                children: [
                  if (_errorMessage != null) _buildOfflineBanner(),
                  _buildSessionBar(),
                  const SizedBox(height: 16),
                  _buildWatchlistTable(),
                ],
              ),
            ),
    );
  }

  Widget _buildOfflineBanner() {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppTheme.invalidated.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.invalidated.withOpacity(0.3)),
      ),
      child: Text(
        'Connecting to backend at ${ApiService.baseUrl}... Pull down to refresh.',
        style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
      ),
    );
  }

  Widget _buildSessionBar() {
    final active = _sessionState?.activeSessions ?? [];
    final activeStr = active.isEmpty ? 'Off-Session' : active.join(' • ').toUpperCase();
    final isOverlap = _sessionState?.isOverlap ?? false;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.border),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: active.isNotEmpty ? AppTheme.upGreen : AppTheme.textMuted,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                'Session: $activeStr',
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.textPrimary),
              ),
            ],
          ),
          if (isOverlap)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: AppTheme.accent.withOpacity(0.15),
                borderRadius: BorderRadius.circular(4),
              ),
              child: const Text(
                'OVERLAP WINDOW',
                style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AppTheme.accent),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildWatchlistTable() {
    if (_items.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: AppTheme.surface,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: AppTheme.border),
        ),
        child: Column(
          children: [
            const Text(
              'No active watchlist instruments',
              style: TextStyle(color: AppTheme.textSecondary, fontSize: 13),
            ),
            const SizedBox(height: 12),
            OutlinedButton(
              onPressed: _showCatalogModal,
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: AppTheme.border),
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              ),
              child: const Text('Browse Catalog & Add Pairs', style: TextStyle(color: AppTheme.textPrimary, fontSize: 12)),
            ),
          ],
        ),
      );
    }

    return Container(
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        children: [
          // Table Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: AppTheme.border)),
            ),
            child: const Row(
              children: [
                Expanded(
                  flex: 3,
                  child: Text('SYMBOL', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppTheme.textMuted)),
                ),
                Expanded(
                  flex: 2,
                  child: Text('STATUS', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppTheme.textMuted)),
                ),
                Expanded(
                  flex: 3,
                  child: Text('LAST', textAlign: TextAlign.right, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppTheme.textMuted)),
                ),
                Expanded(
                  flex: 2,
                  child: Text('CHG %', textAlign: TextAlign.right, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppTheme.textMuted)),
                ),
              ],
            ),
          ),
          // Rows
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: _items.length,
            separatorBuilder: (_, __) => const Divider(height: 1, color: AppTheme.borderSubtle),
            itemBuilder: (context, idx) {
              final item = _items[idx];
              final isPositive = item.isPositive;
              final chgColor = isPositive ? AppTheme.upGreen : AppTheme.downRed;

              return InkWell(
                onTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (ctx) => InstrumentScreen(
                        symbol: item.symbol,
                        onAnalyze: widget.onSelectInstrumentForAnalysis,
                      ),
                    ),
                  );
                },
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                  child: Row(
                    children: [
                      Expanded(
                        flex: 3,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              item.symbol,
                              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14, color: AppTheme.textPrimary),
                            ),
                            Text(
                              item.baseAsset.isNotEmpty && item.quoteAsset.isNotEmpty
                                  ? '${item.baseAsset}/${item.quoteAsset}'
                                  : item.symbol,
                              style: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
                            ),
                          ],
                        ),
                      ),
                      Expanded(
                        flex: 2,
                        child: Row(
                          children: [
                            Container(
                              width: 6,
                              height: 6,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: item.marketStatus == 'Open' ? AppTheme.upGreen : AppTheme.textMuted,
                              ),
                            ),
                            const SizedBox(width: 6),
                            Text(
                              item.marketStatus,
                              style: TextStyle(
                                fontSize: 11,
                                color: item.marketStatus == 'Open' ? AppTheme.textSecondary : AppTheme.textMuted,
                              ),
                            ),
                          ],
                        ),
                      ),
                      Expanded(
                        flex: 3,
                        child: Text(
                          item.formattedPrice,
                          textAlign: TextAlign.right,
                          style: const TextStyle(
                            fontFamily: 'monospace',
                            fontWeight: FontWeight.w600,
                            fontSize: 14,
                            color: AppTheme.textPrimary,
                          ),
                        ),
                      ),
                      Expanded(
                        flex: 2,
                        child: Text(
                          item.formattedChange,
                          textAlign: TextAlign.right,
                          style: TextStyle(
                            fontFamily: 'monospace',
                            fontWeight: FontWeight.w600,
                            fontSize: 13,
                            color: chgColor,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}

class _CatalogBottomSheet extends StatefulWidget {
  final VoidCallback onToggled;

  const _CatalogBottomSheet({Key? key, required this.onToggled}) : super(key: key);

  @override
  State<_CatalogBottomSheet> createState() => _CatalogBottomSheetState();
}

class _CatalogBottomSheetState extends State<_CatalogBottomSheet> {
  bool _isLoading = true;
  List<dynamic> _items = [];
  String _selectedCategory = 'all';

  final List<Map<String, String>> _categories = [
    {'id': 'all', 'label': 'All'},
    {'id': 'crash_boom', 'label': 'Crash & Boom (14)'},
    {'id': 'baskets', 'label': 'Baskets (5)'},
    {'id': 'range_break', 'label': 'Range Break'},
    {'id': 'daily_reset', 'label': 'Daily Indices'},
    {'id': 'volatility', 'label': 'Volatility'},
    {'id': 'indices', 'label': 'Stock Indices (12)'},
    {'id': 'metals', 'label': 'Metals'},
    {'id': 'major_pairs', 'label': 'Forex Majors'},
    {'id': 'crypto', 'label': 'Crypto'},
  ];

  @override
  void initState() {
    super.initState();
    _fetchCatalog();
  }

  Future<void> _fetchCatalog() async {
    setState(() => _isLoading = true);
    try {
      final res = await ApiService.getInstrumentCatalog();
      setState(() {
        _items = res['items'] ?? [];
        _isLoading = false;
      });
    } catch (_) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _toggle(String symbol) async {
    try {
      await ApiService.toggleInstrument(symbol);
      await _fetchCatalog();
      widget.onToggled();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to toggle: $e'), backgroundColor: AppTheme.downRed),
        );
      }
    }
  }

  List<dynamic> get _filteredItems {
    if (_selectedCategory == 'all') return _items;
    return _items.where((i) {
      return i['market'] == _selectedCategory || i['submarket'] == _selectedCategory;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.85,
      padding: const EdgeInsets.only(top: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Configure Watchlist', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                    Text('Toggle instruments to monitor and analyze', style: TextStyle(fontSize: 12, color: AppTheme.textSecondary)),
                  ],
                ),
                IconButton(
                  icon: const Icon(Icons.close_rounded, size: 20, color: AppTheme.textMuted),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            height: 34,
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              scrollDirection: Axis.horizontal,
              itemCount: _categories.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (context, idx) {
                final cat = _categories[idx];
                final isSelected = _selectedCategory == cat['id'];
                return InkWell(
                  onTap: () => setState(() => _selectedCategory = cat['id']!),
                  borderRadius: BorderRadius.circular(6),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: isSelected ? AppTheme.accent : AppTheme.surfaceSubtle,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: isSelected ? AppTheme.accent : AppTheme.border),
                    ),
                    child: Text(
                      cat['label']!,
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                        color: isSelected ? Colors.white : AppTheme.textSecondary,
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
          const Divider(color: AppTheme.border, height: 20),
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.textSecondary))
                : _filteredItems.isEmpty
                    ? const Center(child: Text('No instruments in this category', style: TextStyle(color: AppTheme.textMuted, fontSize: 13)))
                    : ListView.builder(
                        itemCount: _filteredItems.length,
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        itemBuilder: (context, idx) {
                          final item = _filteredItems[idx];
                          final sym = item['symbol'] as String;
                          final name = item['display_name'] as String;
                          final sub = item['submarket'] as String;
                          final isActive = item['is_active'] as bool? ?? false;

                          return Container(
                            margin: const EdgeInsets.only(bottom: 6),
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                            decoration: BoxDecoration(
                              color: AppTheme.surfaceSubtle,
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(color: isActive ? AppTheme.accent.withOpacity(0.4) : AppTheme.border),
                            ),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Text(sym, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: AppTheme.textPrimary)),
                                        if (sym == 'R_75' || sym.contains('VOLATILITY') || sym.contains('75')) ...[
                                          const SizedBox(width: 6),
                                          Container(
                                            padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                                            decoration: BoxDecoration(
                                              color: const Color(0xFF10B981).withValues(alpha: 0.15),
                                              borderRadius: BorderRadius.circular(4),
                                              border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.4)),
                                            ),
                                            child: const Text('⚡ UT BOT', style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: Color(0xFF10B981))),
                                          ),
                                        ],
                                      ],
                                    ),
                                    Text('$name • ${sub.toUpperCase()}', style: const TextStyle(fontSize: 11, color: AppTheme.textMuted)),
                                  ],
                                ),
                                Switch.adaptive(
                                  value: isActive,
                                  activeColor: AppTheme.accent,
                                  onChanged: (_) => _toggle(sym),
                                ),
                              ],
                            ),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}
