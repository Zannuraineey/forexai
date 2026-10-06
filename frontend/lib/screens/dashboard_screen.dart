import 'dart:async';
import 'package:flutter/material.dart';
import '../models/session_state.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class DashboardScreen extends StatefulWidget {
  final Function(String symbol) onSelectInstrument;

  const DashboardScreen({Key? key, required this.onSelectInstrument}) : super(key: key);

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  CurrentSessionState? _sessionState;
  bool _isLoading = true;
  String? _errorMessage;
  Timer? _refreshTimer;

  List<String> _instruments = [
    'XAUUSD',
    'XAGUSD',
    'EURUSD',
    'GBPUSD',
    'USDJPY',
    'AUDUSD',
    'USDCHF',
    'USDCAD',
  ];

  @override
  void initState() {
    super.initState();
    _loadSessionState();
    _refreshTimer = Timer.periodic(const Duration(seconds: 10), (_) {
      if (mounted) {
        _autoRefreshSessionState();
      }
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _autoRefreshSessionState() async {
    try {
      final state = await ApiService.getCurrentSession(forceRefresh: true);
      final activeSyms = await ApiService.getActiveSymbols(forceRefresh: true);
      if (mounted) {
        setState(() {
          _sessionState = state;
          if (activeSyms.isNotEmpty) {
            _instruments = activeSyms;
          }
        });
      }
    } catch (_) {}
  }

  Future<void> _loadSessionState() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final state = await ApiService.getCurrentSession();
      final activeSyms = await ApiService.getActiveSymbols();
      setState(() {
        _sessionState = state;
        if (activeSyms.isNotEmpty) {
          _instruments = activeSyms;
        }
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
      backgroundColor: AppTheme.background,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => _CatalogBottomSheet(
        onToggled: () => _loadSessionState(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Row(
          children: [
            Icon(Icons.auto_graph_rounded, color: AppTheme.primaryLight, size: 24),
            SizedBox(width: 10),
            Text(
              'Forex AI Market Platform',
              style: TextStyle(fontWeight: FontWeight.w700, letterSpacing: -0.5),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, color: AppTheme.textSecondary),
            onPressed: _loadSessionState,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppTheme.primaryLight))
          : RefreshIndicator(
              onRefresh: _loadSessionState,
              color: AppTheme.primaryLight,
              child: ListView(
                padding: const EdgeInsets.all(16.0),
                children: [
                  if (_errorMessage != null) _buildBackendOfflineBanner(),
                  _buildOverlapBanner(),
                  const SizedBox(height: 16),
                  const Text(
                    'TRADING SESSIONS (DST-AWARE)',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.textMuted,
                      letterSpacing: 1.2,
                    ),
                  ),
                  const SizedBox(height: 10),
                  _buildSessionCards(),
                  const SizedBox(height: 24),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Expanded(
                        child: Text(
                          'WATCHLIST & PAIRS',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.textMuted,
                            letterSpacing: 1.2,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      TextButton.icon(
                        style: TextButton.styleFrom(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          minimumSize: Size.zero,
                          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        ),
                        onPressed: _showCatalogModal,
                        icon: const Icon(Icons.add_circle_outline_rounded, size: 15, color: AppTheme.primaryLight),
                        label: const Text(
                          'Add Pairs',
                          style: TextStyle(fontSize: 12, color: AppTheme.primaryLight, fontWeight: FontWeight.w600),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  _buildInstrumentsGrid(),
                ],
              ),
            ),
    );
  }

  Widget _buildBackendOfflineBanner() {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.invalidated.withOpacity(0.12),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.invalidated.withOpacity(0.4)),
      ),
      child: Row(
        children: [
          const Icon(Icons.info_outline, color: AppTheme.invalidated),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              'Backend API connection notice:\n$_errorMessage\n(Check API server URL in Settings)',
              style: const TextStyle(color: AppTheme.textPrimary, fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOverlapBanner() {
    final isOverlap = _sessionState?.isOverlap ?? false;
    final active = _sessionState?.activeSessions ?? [];

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: isOverlap
              ? [const Color(0xFF1E1B4B), const Color(0xFF312E81)]
              : [AppTheme.surface, AppTheme.surfaceLight],
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isOverlap ? AppTheme.primaryLight : AppTheme.border,
          width: 1.5,
        ),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: isOverlap
                  ? AppTheme.primary.withOpacity(0.3)
                  : AppTheme.surfaceLight,
              shape: BoxShape.circle,
            ),
            child: Icon(
              isOverlap ? Icons.electric_bolt_rounded : Icons.schedule_rounded,
              color: isOverlap ? Colors.amberAccent : AppTheme.textSecondary,
              size: 24,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  isOverlap
                      ? 'SESSION OVERLAP ACTIVE'
                      : (active.isEmpty ? 'OFF-SESSION' : '${active.first.toUpperCase()} SESSION ACTIVE'),
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w800,
                    color: isOverlap ? Colors.amberAccent : AppTheme.textPrimary,
                    letterSpacing: 0.5,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  isOverlap
                      ? 'High institutional liquidity window: ${active.join(' & ').toUpperCase()}'
                      : 'Active sessions: ${active.isEmpty ? "None (Waiting for Tokyo open)" : active.join(", ")}',
                  style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSessionCards() {
    final windows = _sessionState?.sessionWindows ?? {};

    return Column(
      children: [
        _buildSingleSessionCard('Asian', windows['asian'], Icons.temple_buddhist_rounded),
        const SizedBox(height: 8),
        _buildSingleSessionCard('London', windows['london'], Icons.apartment_rounded),
        const SizedBox(height: 8),
        _buildSingleSessionCard('New York', windows['new_york'], Icons.location_city_rounded),
      ],
    );
  }

  Widget _buildSingleSessionCard(String label, SessionWindowInfo? info, IconData icon) {
    final isActive = info?.isActive ?? false;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isActive ? AppTheme.validSetup : AppTheme.border,
          width: isActive ? 1.5 : 1.0,
        ),
      ),
      child: Row(
        children: [
          Icon(icon, color: isActive ? AppTheme.validSetup : AppTheme.textMuted, size: 22),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '$label Session',
                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                ),
                Text(
                  info != null ? '${info.timezoneName} (${info.localStartTime} - ${info.localEndTime})' : 'Loading...',
                  style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: isActive
                  ? AppTheme.validSetup.withOpacity(0.15)
                  : AppTheme.surfaceLight,
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text(
              isActive ? 'ACTIVE' : (info?.status ?? 'UPCOMING'),
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w700,
                color: isActive ? AppTheme.validSetup : AppTheme.textMuted,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInstrumentsGrid() {
    return GridView.builder(
      physics: const NeverScrollableScrollPhysics(),
      shrinkWrap: true,
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        crossAxisSpacing: 10,
        mainAxisSpacing: 10,
        childAspectRatio: 2.2,
      ),
      itemCount: _instruments.length,
      itemBuilder: (context, index) {
        final sym = _instruments[index];
        final isGoldOrSilver = sym.startsWith('XA');

        return InkWell(
          onTap: () => widget.onSelectInstrument(sym),
          borderRadius: BorderRadius.circular(12),
          child: Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppTheme.surface,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppTheme.border),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      sym,
                      style: TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 15,
                        color: isGoldOrSilver ? Colors.amberAccent : AppTheme.textPrimary,
                      ),
                    ),
                    Text(
                      isGoldOrSilver ? 'Commodity Metal' : 'Forex Major',
                      style: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
                    ),
                  ],
                ),
                const Icon(Icons.arrow_forward_ios_rounded, size: 14, color: AppTheme.textMuted),
              ],
            ),
          ),
        );
      },
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
    {'id': 'all', 'label': 'All Pairs'},
    {'id': 'volatility', 'label': 'Volatility (15)'},
    {'id': 'crash_boom', 'label': 'Crash & Boom (14)'},
    {'id': 'jump_step', 'label': 'Jump & Step (6)'},
    {'id': 'dex', 'label': 'DEX Indices (6)'},
    {'id': 'baskets', 'label': 'Baskets (5)'},
    {'id': 'range_break', 'label': 'Range Break'},
    {'id': 'daily_reset', 'label': 'Daily Indices'},
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
          SnackBar(content: Text('Failed to toggle: $e'), backgroundColor: Colors.redAccent),
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
                    Text(
                      'Instrument Catalog',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                    Text(
                      'Activate pairs to analyze, backtest & receive alerts',
                      style: TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                    ),
                  ],
                ),
                IconButton(
                  icon: const Icon(Icons.close_rounded, color: AppTheme.textMuted),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            height: 38,
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              scrollDirection: Axis.horizontal,
              itemCount: _categories.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (context, idx) {
                final cat = _categories[idx];
                final isSelected = _selectedCategory == cat['id'];
                return ChoiceChip(
                  label: Text(cat['label']!),
                  selected: isSelected,
                  selectedColor: AppTheme.primary,
                  backgroundColor: AppTheme.surfaceLight,
                  labelStyle: TextStyle(
                    fontSize: 12,
                    fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                    color: isSelected ? Colors.white : AppTheme.textSecondary,
                  ),
                  onSelected: (_) {
                    setState(() => _selectedCategory = cat['id']!);
                  },
                );
              },
            ),
          ),
          const Divider(color: AppTheme.border, height: 24),
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator(color: AppTheme.primaryLight))
                : _filteredItems.isEmpty
                    ? const Center(child: Text('No instruments in this category.'))
                    : ListView.builder(
                        itemCount: _filteredItems.length,
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                        itemBuilder: (context, idx) {
                          final item = _filteredItems[idx];
                          final sym = item['symbol'] as String;
                          final name = item['display_name'] as String;
                          final sub = item['submarket'] as String;
                          final isActive = item['is_active'] as bool? ?? false;

                          return Container(
                            margin: const EdgeInsets.only(bottom: 8),
                            decoration: BoxDecoration(
                              color: AppTheme.surface,
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(
                                color: isActive ? AppTheme.primaryLight.withOpacity(0.4) : AppTheme.border,
                              ),
                            ),
                            child: ListTile(
                              title: Text(
                                sym,
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                              ),
                              subtitle: Text(
                                '$name • ${sub.toUpperCase()}',
                                style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                              ),
                              trailing: Switch.adaptive(
                                value: isActive,
                                activeColor: AppTheme.primaryLight,
                                onChanged: (_) => _toggle(sym),
                              ),
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

