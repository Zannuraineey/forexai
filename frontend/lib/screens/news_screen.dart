import 'dart:async';
import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../models/news_intelligence.dart';
import '../theme/app_theme.dart';

/// Professional Financial Trading-Terminal Market Intelligence Screen
/// Follows rigorous financial application design principles:
/// - Information-first, clean monospace & tabular numbers
/// - Neutral deep terminal background, subtle 1px dividers
/// - Zero generic "AI glow", zero futuristic illustrations, zero decorative emojis
/// - Color applied strictly to communicate market state (Green/Red/Amber/Neutral)
class NewsScreen extends StatefulWidget {
  final Function(String)? onSelectInstrumentForAnalysis;

  const NewsScreen({
    super.key,
    this.onSelectInstrumentForAnalysis,
  });

  @override
  State<NewsScreen> createState() => _NewsScreenState();
}

class _NewsScreenState extends State<NewsScreen> {
  Timer? _countdownTimer;
  bool _isLoading = true;
  String? _errorMessage;

  // Stream mode: 0 = Economic Calendar, 1 = Financial Wire / Breaking News
  int _activeStreamTab = 0;

  // Data states
  DXYMetricsModel? _dxyMetrics;
  List<EconomicEventModel> _events = [];
  List<BreakingNewsItemModel> _breakingNews = [];
  NewsIntelligenceReportModel? _intelligenceReport;
  String? _selectedEventId;
  String _selectedPair = 'EURUSD';

  // Filters
  String _selectedCurrencyFilter = 'ALL';
  String _selectedImpactFilter = 'ALL';

  // Research Query State
  final TextEditingController _queryCtrl = TextEditingController();
  bool _isQuerying = false;

  final List<String> _availablePairs = [
    'EURUSD',
    'GBPUSD',
    'USDJPY',
    'XAUUSD',
    'BTCUSD',
    'AUDUSD',
    'USDCAD',
    'USDCHF',
  ];

  final List<String> _currencyFilters = [
    'ALL',
    'USD',
    'EUR',
    'GBP',
    'CAD',
    'JPY',
    'AUD',
    'CHF',
  ];

  @override
  void initState() {
    super.initState();
    _loadNewsData();
    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _countdownTimer?.cancel();
    _queryCtrl.dispose();
    super.dispose();
  }

  String _formatEventCountdown(DateTime eventTimeUtc) {
    final diff = eventTimeUtc.difference(DateTime.now().toUtc());
    if (diff.isNegative) {
      final passed = diff.abs();
      if (passed.inMinutes < 15) {
        return 'ACTIVE RELEASE';
      } else if (passed.inHours < 1) {
        return 'T+${passed.inMinutes}m';
      } else {
        return 'T+${passed.inHours}h';
      }
    } else {
      final hours = diff.inHours.toString().padLeft(2, '0');
      final minutes = (diff.inMinutes % 60).toString().padLeft(2, '0');
      final seconds = (diff.inSeconds % 60).toString().padLeft(2, '0');
      return 'T-$hours:$minutes:$seconds';
    }
  }

  EconomicEventModel? get _activeEvent {
    if (_selectedEventId != null) {
      final match = _events.where((e) => e.id == _selectedEventId).toList();
      if (match.isNotEmpty) return match.first;
    }
    return _intelligenceReport?.event ?? (_events.isNotEmpty ? _events.first : null);
  }

  Future<void> _loadNewsData({bool forceRefresh = false}) async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final futures = await Future.wait([
        ApiService.getDxyMetrics().catchError((_) => DXYMetricsModel(
          value: 103.45,
          changePct: 0.24,
          trend: 'BULLISH',
          marketRegime: 'ACCUMULATION',
          smcStructure: 'Bullish order flow; testing 4H supply block.',
          rsi14: 54.2,
          ema200: 102.80,
          displacementActive: false,
          confirmationStatus: 'NEUTRAL',
          source: 'SYNTHETIC_BASKET_DXY',
        )),
        ApiService.getEconomicEvents(
          currency: _selectedCurrencyFilter == 'ALL' ? null : _selectedCurrencyFilter,
          impact: _selectedImpactFilter == 'ALL' ? null : _selectedImpactFilter,
        ).catchError((_) => <EconomicEventModel>[]),
        ApiService.getBreakingNews(
          currency: _selectedCurrencyFilter == 'ALL' ? null : _selectedCurrencyFilter,
          forceRefresh: forceRefresh,
        ).catchError((_) => <BreakingNewsItemModel>[]),
      ]);

      _dxyMetrics = futures[0] as DXYMetricsModel;
      _events = futures[1] as List<EconomicEventModel>;
      _breakingNews = futures[2] as List<BreakingNewsItemModel>;

      if (_events.isNotEmpty && _selectedEventId == null) {
        _selectedEventId = _events.first.id;
      }

      if (_selectedEventId != null) {
        await _fetchEventIntelligence(_selectedEventId!);
      }
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _fetchEventIntelligence(String eventId) async {
    try {
      final report = await ApiService.getNewsIntelligence(
        eventId: eventId,
        forceRefresh: false,
      );
      if (mounted) {
        setState(() {
          _intelligenceReport = report;
        });
      }
    } catch (e) {
      debugPrint('Failed to load event intelligence: $e');
    }
  }

  void _selectEvent(String eventId) {
    setState(() => _selectedEventId = eventId);
    _fetchEventIntelligence(eventId);
  }

  Future<void> _handleCustomQuerySubmit(String queryText) async {
    final query = queryText.trim();
    if (query.isEmpty) return;

    setState(() => _isQuerying = true);
    try {
      final response = await ApiService.askAiMacroAnalyst(
        query: query,
        userPairs: _availablePairs,
      );
      if (mounted) {
        setState(() => _isQuerying = false);
        _showQueryResultModal(response);
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isQuerying = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: AppTheme.surface,
            content: Text('Query Notice: $e', style: const TextStyle(color: AppTheme.downRed)),
          ),
        );
      }
    }
  }

  void _showQueryResultModal(AIQueryResponseModel res) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppTheme.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(8)),
      ),
      builder: (ctx) {
        return DraggableScrollableSheet(
          expand: false,
          initialChildSize: 0.85,
          maxChildSize: 0.95,
          minChildSize: 0.5,
          builder: (_, scrollCtrl) {
            return ListView(
              controller: scrollCtrl,
              padding: const EdgeInsets.all(16),
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: AppTheme.surfaceSubtle,
                        borderRadius: BorderRadius.circular(3),
                        border: Border.all(color: AppTheme.border),
                      ),
                      child: Text(
                        res.aiEngineUsed.toUpperCase(),
                        style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: AppTheme.textSecondary),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close, size: 18, color: AppTheme.textMuted),
                      onPressed: () => Navigator.pop(ctx),
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  res.query,
                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: AppTheme.textPrimary),
                ),
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppTheme.background,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: AppTheme.border),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'MACRO THESIS & LIQUIDITY EVALUATION',
                        style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AppTheme.textSecondary, letterSpacing: 0.5),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        res.aiAnalysis,
                        style: const TextStyle(fontSize: 12, height: 1.4, color: AppTheme.textPrimary),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                const Text('INSTITUTIONAL TAKEAWAYS', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AppTheme.textMuted, letterSpacing: 0.5)),
                const SizedBox(height: 6),
                ...res.keyTakeaways.map((t) => Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('• ', style: TextStyle(color: AppTheme.textSecondary)),
                      Expanded(child: Text(t, style: const TextStyle(fontSize: 12, color: AppTheme.textPrimary))),
                    ],
                  ),
                )),
                const SizedBox(height: 12),
                const Text('PAIR IMPACT MATRIX', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AppTheme.textMuted, letterSpacing: 0.5)),
                const SizedBox(height: 6),
                ...res.pairAnalyses.map((p) => Container(
                  margin: const EdgeInsets.only(bottom: 6),
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  decoration: BoxDecoration(
                    color: AppTheme.background,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: AppTheme.border),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(p.symbol, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12, color: AppTheme.textPrimary)),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: p.directionalBias == 'BULLISH'
                              ? AppTheme.upGreen.withValues(alpha: 0.12)
                              : (p.directionalBias == 'BEARISH' ? AppTheme.downRed.withValues(alpha: 0.12) : AppTheme.surfaceSubtle),
                          borderRadius: BorderRadius.circular(3),
                        ),
                        child: Text(
                          p.directionalBias,
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            color: p.directionalBias == 'BULLISH'
                                ? AppTheme.upGreen
                                : (p.directionalBias == 'BEARISH' ? AppTheme.downRed : AppTheme.textSecondary),
                          ),
                        ),
                      ),
                    ],
                  ),
                )),
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
        title: const Text('MARKET INTELLIGENCE & EVENT RADAR'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, size: 18),
            tooltip: 'Refresh Feed',
            onPressed: () => _loadNewsData(forceRefresh: true),
          ),
        ],
      ),
      body: _isLoading && _dxyMetrics == null
          ? const Center(child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.textSecondary))
          : RefreshIndicator(
              onRefresh: () => _loadNewsData(forceRefresh: true),
              color: AppTheme.textPrimary,
              backgroundColor: AppTheme.surface,
              child: ListView(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                children: [
                  if (_errorMessage != null) _buildErrorBanner(),

                  // 1. Terminal Scenario Simulator
                  _buildScenarioBar(),
                  const SizedBox(height: 10),

                  // 2. DXY Dollar Benchmark Card
                  if (_dxyMetrics != null) _buildDxyTerminalCard(_dxyMetrics!),
                  const SizedBox(height: 10),

                  // 3. Tab Stream Selector (Calendar vs News Wire)
                  _buildStreamSelectorTabs(),
                  const SizedBox(height: 8),

                  // 4. Currency & Impact Filters
                  _buildFilterChips(),
                  const SizedBox(height: 8),

                  // 5. Active Stream List
                  if (_activeStreamTab == 0) ...[
                    _buildEventsCarousel(),
                    if (_activeEvent != null) ...[
                      const SizedBox(height: 10),
                      _buildSelectedEventIntelligenceCard(_activeEvent!),
                    ],
                  ] else ...[
                    _buildBreakingNewsList(),
                  ],
                  const SizedBox(height: 14),

                  // 6. Macro Impact Synthesis Section
                  if (_intelligenceReport != null) ...[
                    _buildMacroSynthesisSection(_intelligenceReport!),
                    const SizedBox(height: 14),

                    // 7. Pair Specific Analysis Matrix
                    _buildPairAnalysisSection(_intelligenceReport!),
                  ],
                  const SizedBox(height: 24),
                ],
              ),
            ),
    );
  }

  Widget _buildErrorBanner() {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AppTheme.downRed.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: AppTheme.downRed.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, size: 14, color: AppTheme.downRed),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              _errorMessage!,
              style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
            ),
          ),
        ],
      ),
    );
  }

  // --- 1. Terminal Scenario Simulator ---
  Widget _buildScenarioBar() {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'MACRO SCENARIO SIMULATOR',
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textSecondary,
                  letterSpacing: 0.5,
                ),
              ),
              if (_intelligenceReport != null)
                Text(
                  _intelligenceReport!.aiEngineUsed.toUpperCase(),
                  style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w600, color: AppTheme.textMuted),
                ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _queryCtrl,
                  style: const TextStyle(fontSize: 12, color: AppTheme.textPrimary),
                  decoration: InputDecoration(
                    isDense: true,
                    filled: true,
                    fillColor: AppTheme.background,
                    hintText: "Simulate scenario (e.g. 'US Core CPI prints 3.1% YoY')...",
                    hintStyle: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(3),
                      borderSide: const BorderSide(color: AppTheme.border),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(3),
                      borderSide: const BorderSide(color: AppTheme.accent),
                    ),
                  ),
                  onSubmitted: _handleCustomQuerySubmit,
                ),
              ),
              const SizedBox(width: 6),
              OutlinedButton(
                style: OutlinedButton.styleFrom(
                  backgroundColor: AppTheme.surfaceSubtle,
                  foregroundColor: AppTheme.textPrimary,
                  side: const BorderSide(color: AppTheme.border),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(3)),
                ),
                onPressed: _isQuerying ? null : () => _handleCustomQuerySubmit(_queryCtrl.text),
                child: _isQuerying
                    ? const SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 1.5, color: AppTheme.textPrimary))
                    : const Text('RUN', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // --- 2. DXY Dollar Benchmark Card ---
  Widget _buildDxyTerminalCard(DXYMetricsModel dxy) {
    final isBullish = dxy.trend == 'BULLISH';
    final trendColor = isBullish ? AppTheme.upGreen : (dxy.trend == 'BEARISH' ? AppTheme.downRed : AppTheme.textSecondary);

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  const Text(
                    'DXY (US DOLLAR INDEX)',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.textPrimary,
                      letterSpacing: 0.5,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                    decoration: BoxDecoration(
                      color: trendColor.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(2),
                    ),
                    child: Text(
                      dxy.trend,
                      style: TextStyle(
                        fontSize: 9,
                        fontWeight: FontWeight.w700,
                        color: trendColor,
                      ),
                    ),
                  ),
                ],
              ),
              Text(
                'REGIME: ${dxy.marketRegime}',
                style: const TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.textSecondary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: 12,
            runSpacing: 4,
            children: [
              Row(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.baseline,
                textBaseline: TextBaseline.alphabetic,
                children: [
                  Text(
                    dxy.value.toStringAsFixed(2),
                    style: const TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    '${dxy.changePct >= 0 ? '+' : ''}${dxy.changePct.toStringAsFixed(2)}%',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: dxy.changePct >= 0 ? AppTheme.upGreen : AppTheme.downRed,
                    ),
                  ),
                ],
              ),
              Text(
                'RSI(14): ${dxy.rsi14.toStringAsFixed(1)}   |   200 EMA: ${dxy.ema200.toStringAsFixed(2)}',
                style: const TextStyle(fontSize: 10.5, color: AppTheme.textMuted),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
            decoration: BoxDecoration(
              color: AppTheme.background,
              borderRadius: BorderRadius.circular(3),
              border: Border.all(color: AppTheme.borderSubtle),
            ),
            child: Row(
              children: [
                const Text(
                  'STRUCTURE: ',
                  style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w700, color: AppTheme.textMuted),
                ),
                Expanded(
                  child: Text(
                    dxy.smcStructure,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 10.5, color: AppTheme.textPrimary),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // --- 3. Stream Selector Tabs ---
  Widget _buildStreamSelectorTabs() {
    return Row(
      children: [
        Expanded(
          child: GestureDetector(
            onTap: () => setState(() => _activeStreamTab = 0),
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 7),
              decoration: BoxDecoration(
                color: _activeStreamTab == 0 ? AppTheme.surfaceSubtle : AppTheme.surface,
                borderRadius: BorderRadius.circular(3),
                border: Border.all(
                  color: _activeStreamTab == 0 ? AppTheme.accent : AppTheme.border,
                ),
              ),
              alignment: Alignment.center,
              child: Text(
                'ECONOMIC CALENDAR (${_events.length})',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: _activeStreamTab == 0 ? AppTheme.textPrimary : AppTheme.textMuted,
                  letterSpacing: 0.3,
                ),
              ),
            ),
          ),
        ),
        const SizedBox(width: 6),
        Expanded(
          child: GestureDetector(
            onTap: () => setState(() => _activeStreamTab = 1),
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 7),
              decoration: BoxDecoration(
                color: _activeStreamTab == 1 ? AppTheme.surfaceSubtle : AppTheme.surface,
                borderRadius: BorderRadius.circular(3),
                border: Border.all(
                  color: _activeStreamTab == 1 ? AppTheme.accent : AppTheme.border,
                ),
              ),
              alignment: Alignment.center,
              child: Text(
                'FINANCIAL WIRE (${_breakingNews.length})',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: _activeStreamTab == 1 ? AppTheme.textPrimary : AppTheme.textMuted,
                  letterSpacing: 0.3,
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  // --- 4. Filters ---
  Widget _buildFilterChips() {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          const Text('CCY: ', style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w700, color: AppTheme.textMuted)),
          const SizedBox(width: 4),
          ..._currencyFilters.map((c) {
            final isSel = _selectedCurrencyFilter == c;
            return Padding(
              padding: const EdgeInsets.only(right: 4),
              child: GestureDetector(
                onTap: () {
                  setState(() => _selectedCurrencyFilter = c);
                  _loadNewsData(forceRefresh: false);
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                  decoration: BoxDecoration(
                    color: isSel ? AppTheme.surfaceSubtle : AppTheme.surface,
                    borderRadius: BorderRadius.circular(3),
                    border: Border.all(color: isSel ? AppTheme.accent : AppTheme.border),
                  ),
                  child: Text(
                    c,
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      color: isSel ? AppTheme.textPrimary : AppTheme.textMuted,
                    ),
                  ),
                ),
              ),
            );
          }),
          const SizedBox(width: 10),
          const Text('IMPACT: ', style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w700, color: AppTheme.textMuted)),
          const SizedBox(width: 4),
          ...['ALL', 'HIGH', 'MEDIUM'].map((imp) {
            final isSel = _selectedImpactFilter == imp;
            return Padding(
              padding: const EdgeInsets.only(right: 4),
              child: GestureDetector(
                onTap: () {
                  setState(() => _selectedImpactFilter = imp);
                  _loadNewsData(forceRefresh: false);
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                  decoration: BoxDecoration(
                    color: isSel ? AppTheme.surfaceSubtle : AppTheme.surface,
                    borderRadius: BorderRadius.circular(3),
                    border: Border.all(
                      color: isSel ? (imp == 'HIGH' ? AppTheme.downRed : AppTheme.accent) : AppTheme.border,
                    ),
                  ),
                  child: Text(
                    imp,
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      color: isSel
                          ? (imp == 'HIGH' ? AppTheme.downRed : AppTheme.textPrimary)
                          : AppTheme.textMuted,
                    ),
                  ),
                ),
              ),
            );
          }),
        ],
      ),
    );
  }

  // --- 5. Events Stream / Carousel ---
  Widget _buildEventsCarousel() {
    if (_events.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppTheme.surface,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: AppTheme.border),
        ),
        child: const Center(
          child: Text('No economic events found matching filter.', style: TextStyle(color: AppTheme.textMuted, fontSize: 11)),
        ),
      );
    }

    return SizedBox(
      height: 132,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: _events.length,
        separatorBuilder: (_, _) => const SizedBox(width: 8),
        itemBuilder: (ctx, i) {
          final ev = _events[i];
          final isSelected = ev.id == _selectedEventId;
          return _buildEventItem(ev, isSelected);
        },
      ),
    );
  }

  Widget _buildEventItem(EconomicEventModel ev, bool isSelected) {
    final hasActual = ev.actual != null;
    final isHigh = ev.impact == 'HIGH';
    final isBeat = ev.deviationBias == 'BEAT';
    final isMissed = ev.deviationBias == 'MISSED';
    final Color actualColor = isBeat
        ? AppTheme.upGreen
        : (isMissed ? AppTheme.downRed : (hasActual ? AppTheme.upGreen : AppTheme.textMuted));

    return GestureDetector(
      onTap: () => _selectEvent(ev.id),
      child: Container(
        width: 226,
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.surfaceSubtle : AppTheme.surface,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(
            color: isSelected ? AppTheme.accent : AppTheme.border,
            width: isSelected ? 1.5 : 1,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1.5),
                      decoration: BoxDecoration(
                        color: isHigh ? AppTheme.downRed.withValues(alpha: 0.15) : AppTheme.surfaceSubtle,
                        borderRadius: BorderRadius.circular(2),
                        border: Border.all(color: isHigh ? AppTheme.downRed.withValues(alpha: 0.3) : AppTheme.border),
                      ),
                      child: Text(
                        '${ev.currency}  ${ev.impact}',
                        style: TextStyle(
                          fontSize: 8.5,
                          fontWeight: FontWeight.w700,
                          color: isHigh ? AppTheme.downRed : AppTheme.textSecondary,
                        ),
                      ),
                    ),
                    if (ev.deviationBias != null) ...[
                      const SizedBox(width: 4),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1.5),
                        decoration: BoxDecoration(
                          color: isBeat
                              ? AppTheme.upGreen.withValues(alpha: 0.15)
                              : (isMissed ? AppTheme.downRed.withValues(alpha: 0.15) : AppTheme.surfaceSubtle),
                          borderRadius: BorderRadius.circular(2),
                          border: Border.all(
                            color: isBeat
                                ? AppTheme.upGreen.withValues(alpha: 0.3)
                                : (isMissed ? AppTheme.downRed.withValues(alpha: 0.3) : AppTheme.border),
                          ),
                        ),
                        child: Text(
                          ev.deviationBias!,
                          style: TextStyle(
                            fontSize: 7.5,
                            fontWeight: FontWeight.w700,
                            color: isBeat
                                ? AppTheme.upGreen
                                : (isMissed ? AppTheme.downRed : AppTheme.textMuted),
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
                Text(
                  _formatEventCountdown(ev.eventTimeUtc),
                  style: TextStyle(
                    fontSize: 9,
                    fontWeight: FontWeight.w700,
                    color: ev.eventTimeUtc.difference(DateTime.now().toUtc()).isNegative &&
                            ev.eventTimeUtc.difference(DateTime.now().toUtc()).abs().inMinutes < 15
                        ? AppTheme.downRed
                        : (hasActual ? AppTheme.upGreen : AppTheme.textSecondary),
                  ),
                ),
              ],
            ),
            Text(
              ev.title,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontSize: 11.5,
                fontWeight: FontWeight.w600,
                color: AppTheme.textPrimary,
                height: 1.25,
              ),
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _buildMetricCol('ACTUAL', ev.rawActual ?? (ev.actual != null ? '${ev.actual}${ev.unit}' : '--'), actualColor),
                _buildMetricCol('FORECAST', ev.rawForecast ?? (ev.forecast != null ? '${ev.forecast}${ev.unit}' : '--'), AppTheme.textSecondary),
                _buildMetricCol('PREVIOUS', ev.rawPrevious ?? (ev.previous != null ? '${ev.previous}${ev.unit}' : '--'), AppTheme.textMuted),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetricCol(String label, String val, Color valColor) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 7.5, fontWeight: FontWeight.w700, color: AppTheme.textMuted)),
        const SizedBox(height: 1.5),
        Text(val, style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: valColor)),
      ],
    );
  }

  // --- Selected Event Live Intelligence Card ---
  Widget _buildSelectedEventIntelligenceCard(EconomicEventModel ev) {
    final hasActual = ev.actual != null;
    final isBeat = ev.deviationBias == 'BEAT';
    final isMissed = ev.deviationBias == 'MISSED';
    final biasColor = isBeat
        ? AppTheme.upGreen
        : (isMissed ? AppTheme.downRed : (hasActual ? AppTheme.surfaceSubtle : AppTheme.accent));

    final actualDisplay = ev.rawActual ?? (ev.actual != null ? '${ev.actual}${ev.unit}' : '--');
    final forecastDisplay = ev.rawForecast ?? (ev.forecast != null ? '${ev.forecast}${ev.unit}' : '--');
    final previousDisplay = ev.rawPrevious ?? (ev.previous != null ? '${ev.previous}${ev.unit}' : '--');

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceSubtle,
                      borderRadius: BorderRadius.circular(2),
                      border: Border.all(color: AppTheme.border),
                    ),
                    child: Text(
                      '${ev.currency} • ${ev.impact} IMPACT',
                      style: const TextStyle(
                        fontSize: 9.5,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.textSecondary,
                      ),
                    ),
                  ),
                  if (ev.deviationBias != null) ...[
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                      decoration: BoxDecoration(
                        color: biasColor.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(2),
                        border: Border.all(color: biasColor.withValues(alpha: 0.3)),
                      ),
                      child: Text(
                        ev.deviationBias!,
                        style: TextStyle(
                          fontSize: 9,
                          fontWeight: FontWeight.w700,
                          color: biasColor,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
              Text(
                'TIME: ${_formatEventCountdown(ev.eventTimeUtc)}',
                style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w700, color: AppTheme.textMuted),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            ev.title,
            style: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w700,
              color: AppTheme.textPrimary,
            ),
          ),
          const SizedBox(height: 10),

          // 3-Column Metrics Comparison Grid
          Row(
            children: [
              Expanded(
                child: _buildValueBox(
                  'ACTUAL PRINT',
                  actualDisplay,
                  hasActual ? (isBeat ? AppTheme.upGreen : (isMissed ? AppTheme.downRed : AppTheme.textPrimary)) : AppTheme.textMuted,
                  isHighlighted: hasActual,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _buildValueBox(
                  'CONSENSUS FORECAST',
                  forecastDisplay,
                  AppTheme.textPrimary,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _buildValueBox(
                  'PREVIOUS BASELINE',
                  previousDisplay,
                  AppTheme.textSecondary,
                ),
              ),
            ],
          ),

          // Live Consensus Expectation
          if (ev.consensusExpectation != null && ev.consensusExpectation!.isNotEmpty) ...[
            const SizedBox(height: 10),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 7),
              decoration: BoxDecoration(
                color: AppTheme.background,
                borderRadius: BorderRadius.circular(3),
                border: Border.all(color: AppTheme.borderSubtle),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'LIVE CONSENSUS EXPECTATION',
                    style: TextStyle(
                      fontSize: 8.5,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.textMuted,
                      letterSpacing: 0.5,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    ev.consensusExpectation!,
                    style: const TextStyle(
                      fontSize: 10.5,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.textPrimary,
                      height: 1.3,
                    ),
                  ),
                ],
              ),
            ),
          ],

          // Directional Scenario Triggers
          if (ev.bullishTrigger != null || ev.bearishTrigger != null) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                if (ev.bullishTrigger != null)
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.all(7),
                      decoration: BoxDecoration(
                        color: AppTheme.upGreen.withValues(alpha: 0.06),
                        borderRadius: BorderRadius.circular(3),
                        border: Border.all(color: AppTheme.upGreen.withValues(alpha: 0.2)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            '▲ HAWKISH / BULLISH TRIGGER',
                            style: TextStyle(
                              fontSize: 8,
                              fontWeight: FontWeight.w700,
                              color: AppTheme.upGreen,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            ev.bullishTrigger!,
                            style: const TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                              color: AppTheme.textPrimary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                if (ev.bullishTrigger != null && ev.bearishTrigger != null) const SizedBox(width: 6),
                if (ev.bearishTrigger != null)
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.all(7),
                      decoration: BoxDecoration(
                        color: AppTheme.downRed.withValues(alpha: 0.06),
                        borderRadius: BorderRadius.circular(3),
                        border: Border.all(color: AppTheme.downRed.withValues(alpha: 0.2)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            '▼ DOVISH / BEARISH TRIGGER',
                            style: TextStyle(
                              fontSize: 8,
                              fontWeight: FontWeight.w700,
                              color: AppTheme.downRed,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            ev.bearishTrigger!,
                            style: const TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                              color: AppTheme.textPrimary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildValueBox(String label, String value, Color valueColor, {bool isHighlighted = false}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: BoxDecoration(
        color: isHighlighted ? AppTheme.surfaceSubtle : AppTheme.background,
        borderRadius: BorderRadius.circular(3),
        border: Border.all(
          color: isHighlighted ? AppTheme.accent.withValues(alpha: 0.3) : AppTheme.borderSubtle,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(
              fontSize: 7.5,
              fontWeight: FontWeight.w700,
              color: AppTheme.textMuted,
            ),
          ),
          const SizedBox(height: 3),
          Text(
            value,
            style: TextStyle(
              fontSize: 12.5,
              fontWeight: FontWeight.w700,
              color: valueColor,
            ),
          ),
        ],
      ),
    );
  }

  // --- Financial Wire / Breaking News ---
  Widget _buildBreakingNewsList() {
    if (_breakingNews.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppTheme.surface,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: AppTheme.border),
        ),
        child: const Center(
          child: Text('No wire stories available for active filter.', style: TextStyle(color: AppTheme.textMuted, fontSize: 11)),
        ),
      );
    }

    return Column(
      children: _breakingNews.take(5).map((n) {
        final isBull = n.sentiment == 'BULLISH';
        final isBear = n.sentiment == 'BEARISH';
        final sentColor = isBull ? AppTheme.upGreen : (isBear ? AppTheme.downRed : AppTheme.textMuted);

        return Container(
          margin: const EdgeInsets.only(bottom: 6),
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: AppTheme.surface,
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: AppTheme.border),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Text(n.source, style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w700, color: AppTheme.textSecondary)),
                      const SizedBox(width: 6),
                      Text('• ${n.currencies.join('/')}', style: const TextStyle(fontSize: 9.5, color: AppTheme.textMuted)),
                    ],
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                    decoration: BoxDecoration(
                      color: sentColor.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(2),
                    ),
                    child: Text(n.sentiment, style: TextStyle(fontSize: 8.5, fontWeight: FontWeight.w700, color: sentColor)),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text(n.title, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.textPrimary)),
              const SizedBox(height: 3),
              Text(n.summary, style: const TextStyle(fontSize: 10.5, color: AppTheme.textSecondary, height: 1.3), maxLines: 2, overflow: TextOverflow.ellipsis),
              const SizedBox(height: 6),
              Align(
                alignment: Alignment.centerRight,
                child: InkWell(
                  onTap: () => _handleCustomQuerySubmit('Analyze macroeconomic impact of wire story: ${n.title}'),
                  child: const Padding(
                    padding: EdgeInsets.symmetric(vertical: 2),
                    child: Text(
                      'SIMULATE IMPACT →',
                      style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w700, color: AppTheme.textSecondary),
                    ),
                  ),
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }

  // --- 6. Macro Impact Synthesis Section ---
  Widget _buildMacroSynthesisSection(NewsIntelligenceReportModel report) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'MACRO IMPACT SYNTHESIS',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textPrimary,
                  letterSpacing: 0.5,
                ),
              ),
              Text(
                report.aiEngineUsed.toUpperCase(),
                style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w600, color: AppTheme.textMuted),
              ),
            ],
          ),
          if (report.spikeWarning != null && report.spikeWarning!.isNotEmpty) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
              decoration: BoxDecoration(
                color: AppTheme.downRed.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(3),
                border: Border.all(color: AppTheme.downRed.withValues(alpha: 0.3)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.warning_amber_outlined, size: 14, color: AppTheme.downRed),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      report.spikeWarning!,
                      style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, color: AppTheme.downRed),
                    ),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 10),
          _buildSynthesisRow('DEVIATION ANALYSIS', report.deviationAnalysis),
          _buildSynthesisRow('HISTORICAL PRECEDENT', report.historicalComparison),
          _buildSynthesisRow('MACRO REGIME & DXY', report.macroRegimeSummary),
          _buildSynthesisRow('SMC TECHNICAL SYNTHESIS', report.smcTechnicalSynthesis),
          if (report.institutionalOrderSummary != null && report.institutionalOrderSummary!.isNotEmpty)
            _buildSynthesisRow('INSTITUTIONAL ORDERS', report.institutionalOrderSummary!),
          if (report.macroReversalWindow != null && report.macroReversalWindow!.isNotEmpty)
            _buildSynthesisRow('REVERSAL TIMING WINDOW', report.macroReversalWindow!),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: AppTheme.background,
              borderRadius: BorderRadius.circular(3),
              border: Border.all(color: AppTheme.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'ACTIONABLE DIRECTIVE',
                  style: TextStyle(
                    fontSize: 9.5,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textSecondary,
                    letterSpacing: 0.5,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  report.actionableConclusion,
                  style: const TextStyle(
                    fontSize: 11.5,
                    color: AppTheme.textPrimary,
                    height: 1.35,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSynthesisRow(String title, String body) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              fontSize: 9.5,
              fontWeight: FontWeight.w700,
              color: AppTheme.textMuted,
              letterSpacing: 0.4,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            body,
            style: const TextStyle(
              fontSize: 11,
              color: AppTheme.textPrimary,
              height: 1.35,
            ),
          ),
        ],
      ),
    );
  }

  // --- 7. Pair-Specific Impact Analysis Section ---
  Widget _buildPairAnalysisSection(NewsIntelligenceReportModel report) {
    final activeAnalysis = report.pairAnalyses.firstWhere(
      (p) => p.symbol == _selectedPair,
      orElse: () => report.pairAnalyses.isNotEmpty
          ? report.pairAnalyses.first
          : PairImpactAnalysisModel(
              symbol: _selectedPair,
              directionalBias: 'NEUTRAL',
              confidence: 0.5,
              correlationToUsd: 'INVERSE',
              smcConfluence: 'Structure aligning with dealing range.',
              keyLevels: {},
              tradeThesis: 'Accumulation in discount zone.',
            ),
    );

    final isBull = activeAnalysis.directionalBias == 'BULLISH';
    final isBear = activeAnalysis.directionalBias == 'BEARISH';
    final biasColor = isBull ? AppTheme.upGreen : (isBear ? AppTheme.downRed : AppTheme.textSecondary);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'PAIR SPECIFIC USD SENSITIVITY',
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w700,
                color: AppTheme.textMuted,
                letterSpacing: 0.8,
              ),
            ),
            Text(
              'CONFIDENCE: ${(activeAnalysis.confidence * 100).toInt()}%',
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w700,
                color: biasColor,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: _availablePairs.map((sym) {
              final isSel = sym == _selectedPair;
              return Padding(
                padding: const EdgeInsets.only(right: 5),
                child: GestureDetector(
                  onTap: () => setState(() => _selectedPair = sym),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: isSel ? AppTheme.surfaceSubtle : AppTheme.surface,
                      borderRadius: BorderRadius.circular(3),
                      border: Border.all(color: isSel ? AppTheme.accent : AppTheme.border),
                    ),
                    child: Text(
                      sym,
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: isSel ? AppTheme.textPrimary : AppTheme.textMuted,
                      ),
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        ),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppTheme.surface,
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: AppTheme.border),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                alignment: WrapAlignment.spaceBetween,
                crossAxisAlignment: WrapCrossAlignment.center,
                spacing: 8,
                runSpacing: 4,
                children: [
                  Text(
                    activeAnalysis.symbol,
                    style: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: biasColor.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(2),
                        ),
                        child: Text(
                          activeAnalysis.directionalBias,
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            color: biasColor,
                          ),
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        '${activeAnalysis.correlationToUsd} TO USD',
                        style: const TextStyle(
                          fontSize: 9.5,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.textMuted,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                activeAnalysis.tradeThesis,
                style: const TextStyle(
                  fontSize: 11.5,
                  color: AppTheme.textPrimary,
                  height: 1.35,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                activeAnalysis.smcConfluence,
                style: const TextStyle(
                  fontSize: 10.5,
                  color: AppTheme.textSecondary,
                  height: 1.3,
                ),
              ),
              if (activeAnalysis.keyLevels.isNotEmpty) ...[
                const SizedBox(height: 10),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppTheme.background,
                    borderRadius: BorderRadius.circular(3),
                    border: Border.all(color: AppTheme.borderSubtle),
                  ),
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: [
                        _buildKeyLevelItem('CURRENT', activeAnalysis.keyLevels['current']),
                        const SizedBox(width: 14),
                        _buildKeyLevelItem('SWING HIGH', activeAnalysis.keyLevels['swing_high']),
                        const SizedBox(width: 14),
                        _buildKeyLevelItem('SWING LOW', activeAnalysis.keyLevels['swing_low']),
                        const SizedBox(width: 14),
                        _buildKeyLevelItem('INVALIDATION', activeAnalysis.keyLevels['invalidation']),
                      ],
                    ),
                  ),
                ),
              ],
              _buildOrderDensityCard(activeAnalysis),
              _buildManipulationCard(activeAnalysis),
              _buildReversalTimingCard(activeAnalysis),
              _buildOrderBlueprintCard(activeAnalysis),
              _buildSpikeDetectionCard(activeAnalysis),
              const SizedBox(height: 10),
              if (widget.onSelectInstrumentForAnalysis != null)
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton(
                    style: OutlinedButton.styleFrom(
                      backgroundColor: AppTheme.surfaceSubtle,
                      foregroundColor: AppTheme.textPrimary,
                      side: const BorderSide(color: AppTheme.border),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(3)),
                      padding: const EdgeInsets.symmetric(vertical: 8),
                    ),
                    onPressed: () => widget.onSelectInstrumentForAnalysis!(activeAnalysis.symbol),
                    child: Text(
                      'INSPECT ${activeAnalysis.symbol} CHART →',
                      style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildOrderDensityCard(PairImpactAnalysisModel active) {
    final density = active.orderDensity;
    if (density == null) return const SizedBox.shrink();

    final digits = active.symbol.contains('JPY') ? 3 : 5;

    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppTheme.background,
        borderRadius: BorderRadius.circular(3),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'ORDER DENSITY & POOL CONCENTRATION',
                style: TextStyle(
                  fontSize: 9.5,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textSecondary,
                  letterSpacing: 0.4,
                ),
              ),
              Text(
                density.orderVolumeConcentration.replaceAll('_', ' '),
                style: const TextStyle(
                  fontSize: 9,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textMuted,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppTheme.surface,
                    borderRadius: BorderRadius.circular(2),
                    border: Border.all(color: AppTheme.borderSubtle),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'BUY-SIDE (BSL)',
                        style: TextStyle(fontSize: 8, fontWeight: FontWeight.w700, color: AppTheme.textMuted),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        density.buySideLiquidity.toStringAsFixed(digits),
                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppTheme.upGreen),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppTheme.surface,
                    borderRadius: BorderRadius.circular(2),
                    border: Border.all(color: AppTheme.borderSubtle),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'SELL-SIDE (SSL)',
                        style: TextStyle(fontSize: 8, fontWeight: FontWeight.w700, color: AppTheme.textMuted),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        density.sellSideLiquidity.toStringAsFixed(digits),
                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppTheme.downRed),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          if (density.orderBlockZone.isNotEmpty) ...[
            const SizedBox(height: 6),
            Row(
              children: [
                const Text(
                  'ORDER BLOCK ZONE: ',
                  style: TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: AppTheme.textMuted),
                ),
                Expanded(
                  child: Text(
                    density.orderBlockZone,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w600, color: AppTheme.textPrimary),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildManipulationCard(PairImpactAnalysisModel active) {
    final manip = active.manipulation;
    if (manip == null) return const SizedBox.shrink();

    final isHighJudas = manip.judasSwingRisk.toUpperCase() == 'HIGH';
    final judasColor = isHighJudas ? AppTheme.downRed : (manip.judasSwingRisk.toUpperCase() == 'MEDIUM' ? Colors.amber : AppTheme.upGreen);

    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppTheme.background,
        borderRadius: BorderRadius.circular(3),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'MANIPULATION & LIQUIDITY TRAP',
                style: TextStyle(
                  fontSize: 9.5,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textSecondary,
                  letterSpacing: 0.4,
                ),
              ),
              Text(
                'JUDAS RISK: ${manip.judasSwingRisk}',
                style: TextStyle(
                  fontSize: 9,
                  fontWeight: FontWeight.w700,
                  color: judasColor,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Wrap(
            spacing: 6,
            runSpacing: 4,
            children: [
              Text(
                'PATTERN: ${manip.trapType.replaceAll('_', ' ')}',
                style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w600, color: AppTheme.textMuted),
              ),
              if (manip.reversalExpected) ...[
                const Text('•', style: TextStyle(color: AppTheme.textMuted)),
                const Text(
                  'HIGH REVERSAL PROBABILITY',
                  style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w700, color: AppTheme.upGreen),
                ),
              ],
            ],
          ),
          const SizedBox(height: 6),
          Text(
            manip.manipulationThesis,
            style: const TextStyle(
              fontSize: 10.5,
              color: AppTheme.textPrimary,
              height: 1.35,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildReversalTimingCard(PairImpactAnalysisModel active) {
    final timing = active.reversalTiming;
    if (timing == null) return const SizedBox.shrink();

    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppTheme.background,
        borderRadius: BorderRadius.circular(3),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'DIRECTION REVERSAL TIMING PHASES',
            style: TextStyle(
              fontSize: 9.5,
              fontWeight: FontWeight.w700,
              color: AppTheme.textSecondary,
              letterSpacing: 0.4,
            ),
          ),
          const SizedBox(height: 6),
          _buildTimingPhaseRow('1. Initial Spike (Sweep)', timing.initialSpikeDuration, AppTheme.downRed),
          _buildTimingPhaseRow('2. Judas Inflection', timing.reversalInflectionWindow, Colors.amber),
          _buildTimingPhaseRow('3. Trend Expansion', timing.trueTrendExpansionTime, AppTheme.upGreen),
          const SizedBox(height: 4),
          Row(
            children: [
              const Text('ENTRY RULE: ', style: TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: AppTheme.textMuted)),
              Expanded(
                child: Text(
                  timing.safeEntryTime,
                  style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w600, color: AppTheme.textPrimary),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildTimingPhaseRow(String phase, String desc, Color color) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 4,
            height: 4,
            margin: const EdgeInsets.only(top: 5, right: 6),
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          Expanded(
            child: RichText(
              text: TextSpan(
                style: const TextStyle(fontSize: 9.5, color: AppTheme.textSecondary),
                children: [
                  TextSpan(
                    text: '$phase: ',
                    style: TextStyle(fontWeight: FontWeight.w700, color: color),
                  ),
                  TextSpan(text: desc),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOrderBlueprintCard(PairImpactAnalysisModel active) {
    final blueprint = active.orderBlueprint;
    if (blueprint == null) return const SizedBox.shrink();

    final isBuy = blueprint.action.toUpperCase().contains('BUY');
    final actionColor = isBuy ? AppTheme.upGreen : AppTheme.downRed;
    final digits = active.symbol.contains('JPY') ? 3 : 5;

    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppTheme.background,
        borderRadius: BorderRadius.circular(3),
        border: Border.all(color: actionColor.withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Text(
                    'ORDER DIRECTIVE: ${blueprint.action.replaceAll('_', ' ')}',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w800,
                      color: actionColor,
                      letterSpacing: 0.4,
                    ),
                  ),
                ],
              ),
              Text(
                'R:R ${blueprint.riskRewardRatio}',
                style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w700, color: AppTheme.textSecondary),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
            decoration: BoxDecoration(
              color: AppTheme.surface,
              borderRadius: BorderRadius.circular(2),
              border: Border.all(color: AppTheme.borderSubtle),
            ),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _buildBlueprintCol('ENTRY', blueprint.recommendedEntry.toStringAsFixed(digits), AppTheme.textPrimary),
                  const SizedBox(width: 14),
                  _buildBlueprintCol('STOP LOSS', blueprint.stopLoss.toStringAsFixed(digits), AppTheme.downRed),
                  const SizedBox(width: 14),
                  _buildBlueprintCol('TP1 (1:1.5)', blueprint.takeProfit1.toStringAsFixed(digits), AppTheme.upGreen),
                  const SizedBox(width: 14),
                  _buildBlueprintCol('TP2 (RUNNER)', blueprint.takeProfit2.toStringAsFixed(digits), AppTheme.upGreen),
                ],
              ),
            ),
          ),
          const SizedBox(height: 6),
          Text(
            blueprint.executionRule,
            style: const TextStyle(
              fontSize: 9.5,
              fontWeight: FontWeight.w500,
              color: AppTheme.textSecondary,
              height: 1.3,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBlueprintCol(String label, String val, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 7.5, fontWeight: FontWeight.w700, color: AppTheme.textMuted)),
        const SizedBox(height: 1.5),
        Text(val, style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: color)),
      ],
    );
  }

  Widget _buildSpikeDetectionCard(PairImpactAnalysisModel active) {
    final spike = active.spikeAnalysis;
    if (spike == null) return const SizedBox.shrink();

    final isBullish = spike.spikeDirection.contains('BULL');
    final dirColor = isBullish ? AppTheme.upGreen : (spike.spikeDirection.contains('BEAR') ? AppTheme.downRed : AppTheme.textMuted);

    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppTheme.background,
        borderRadius: BorderRadius.circular(3),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'VOLATILITY & DISPLACEMENT',
                style: TextStyle(
                  fontSize: 9.5,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textSecondary,
                  letterSpacing: 0.4,
                ),
              ),
              Text(
                '±${spike.estimatedVolatilityPips.toStringAsFixed(1)} PIPS',
                style: TextStyle(
                  fontSize: 9.5,
                  fontWeight: FontWeight.w700,
                  color: dirColor,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            spike.spikeStatus,
            style: const TextStyle(fontSize: 9.5, color: AppTheme.textSecondary),
          ),
        ],
      ),
    );
  }

  Widget _buildKeyLevelItem(String label, dynamic val) {
    final strVal = val != null ? val.toString() : '--';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 8, color: AppTheme.textMuted, fontWeight: FontWeight.w700)),
        const SizedBox(height: 1.5),
        Text(strVal, style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, color: AppTheme.textPrimary)),
      ],
    );
  }
}
