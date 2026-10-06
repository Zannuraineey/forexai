import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../models/news_intelligence.dart';
import '../theme/app_theme.dart';

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
  bool _isLoading = true;
  String? _errorMessage;

  // Stream mode: 0 = Economic Calendar, 1 = Breaking Financial News
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

  // Interactive AI Query State
  final TextEditingController _queryCtrl = TextEditingController();
  bool _isQueryingAi = false;

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
  }

  @override
  void dispose() {
    _queryCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadNewsData({bool forceRefresh = false}) async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final dxyFuture = ApiService.getDxyMetrics();
      final eventsFuture = ApiService.getEconomicEvents(
        currency: _selectedCurrencyFilter,
        impact: _selectedImpactFilter,
        forceRefresh: forceRefresh,
      );
      final breakingFuture = ApiService.getBreakingNews(
        currency: _selectedCurrencyFilter,
        forceRefresh: forceRefresh,
      );
      final intelFuture = ApiService.getNewsIntelligence(
        eventId: _selectedEventId,
        forceRefresh: forceRefresh,
      );

      final results = await Future.wait([dxyFuture, eventsFuture, breakingFuture, intelFuture]);

      if (mounted) {
        setState(() {
          _dxyMetrics = results[0] as DXYMetricsModel;
          _events = results[1] as List<EconomicEventModel>;
          _breakingNews = results[2] as List<BreakingNewsItemModel>;
          _intelligenceReport = results[3] as NewsIntelligenceReportModel;
          _selectedEventId = _intelligenceReport?.event.id;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _selectEvent(String eventId) async {
    setState(() {
      _selectedEventId = eventId;
      _isLoading = true;
    });

    try {
      final report = await ApiService.evaluateNewsIntelligence(
        eventId: eventId,
        userPairs: _availablePairs,
      );
      if (mounted) {
        setState(() {
          _intelligenceReport = report;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _handleCustomQuerySubmit(String queryText) async {
    final query = queryText.trim();
    if (query.isEmpty) return;

    setState(() => _isQueryingAi = true);
    try {
      final response = await ApiService.askAiMacroAnalyst(
        query: query,
        userPairs: _availablePairs,
      );
      if (mounted) {
        setState(() => _isQueryingAi = false);
        _showAiQueryResultModal(response);
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isQueryingAi = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: AppTheme.surfaceSubtle,
            content: Text('AI Query Notice: $e', style: const TextStyle(color: AppTheme.downRed)),
          ),
        );
      }
    }
  }

  void _showAiQueryResultModal(AIQueryResponseModel res) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppTheme.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
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
              padding: const EdgeInsets.all(18),
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: AppTheme.accent.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: AppTheme.accent.withValues(alpha: 0.4)),
                      ),
                      child: Text(
                        res.aiEngineUsed,
                        style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AppTheme.accent),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close, size: 20, color: AppTheme.textMuted),
                      onPressed: () => Navigator.pop(ctx),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  res.query,
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: AppTheme.textPrimary),
                ),
                const SizedBox(height: 14),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppTheme.background,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppTheme.border),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'AI MACRO THESIS & LIQUIDITY EVALUATION',
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppTheme.accent, letterSpacing: 0.5),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        res.aiAnalysis,
                        style: const TextStyle(fontSize: 13, height: 1.45, color: AppTheme.textPrimary),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 14),
                const Text('KEY INSTITUTIONAL TAKEAWAYS', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppTheme.textMuted)),
                const SizedBox(height: 6),
                ...res.keyTakeaways.map((t) => Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.check_circle_outline, size: 14, color: AppTheme.upGreen),
                      const SizedBox(width: 6),
                      Expanded(child: Text(t, style: const TextStyle(fontSize: 12, color: AppTheme.textPrimary))),
                    ],
                  ),
                )),
                const SizedBox(height: 14),
                const Text('PAIR IMPACT SPECIFICATIONS', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppTheme.textMuted)),
                const SizedBox(height: 8),
                ...res.pairAnalyses.map((p) => Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppTheme.background,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: AppTheme.border),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(p.symbol, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: AppTheme.textPrimary)),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: p.directionalBias == 'BULLISH' ? AppTheme.upGreen.withValues(alpha: 0.12) : (p.directionalBias == 'BEARISH' ? AppTheme.downRed.withValues(alpha: 0.12) : AppTheme.surfaceSubtle),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(p.directionalBias, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: p.directionalBias == 'BULLISH' ? AppTheme.upGreen : (p.directionalBias == 'BEARISH' ? AppTheme.downRed : AppTheme.textSecondary))),
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
        title: const Text('News Intelligence'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, size: 20),
            tooltip: 'Pull Fresh Live Feeds',
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
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                children: [
                  if (_errorMessage != null) _buildErrorBanner(),

                  // 1. Interactive SaaS Query / Scenario Bar
                  _buildInteractiveQueryBar(),
                  const SizedBox(height: 14),

                  // 2. DXY US Dollar Strength & SMC Regime Card
                  if (_dxyMetrics != null) _buildDxyCard(_dxyMetrics!),
                  const SizedBox(height: 14),

                  // 3. Dual Stream Tab (Calendar vs Breaking News)
                  _buildStreamSelectorTabs(),
                  const SizedBox(height: 10),

                  // 4. Currency & Impact Filters
                  _buildFilterChips(),
                  const SizedBox(height: 12),

                  // 5. Active Stream List
                  if (_activeStreamTab == 0) ...[
                    _buildEventsCarousel(),
                  ] else ...[
                    _buildBreakingNewsList(),
                  ],
                  const SizedBox(height: 16),

                  // 6. 10-Layer Institutional Synthesis Card
                  if (_intelligenceReport != null) ...[
                    _buildIntelligenceReportCard(_intelligenceReport!),
                    const SizedBox(height: 16),

                    // 7. Interactive FX Pair Detail Selector & Analysis
                    _buildPairSpecificImpactSection(_intelligenceReport!),
                  ],
                  const SizedBox(height: 24),
                ],
              ),
            ),
    );
  }

  Widget _buildErrorBanner() {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppTheme.invalidated.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.invalidated.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          const Icon(Icons.info_outline, size: 16, color: AppTheme.downRed),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Notice: $_errorMessage',
              style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
            ),
          ),
        ],
      ),
    );
  }

  // --- 1. Interactive SaaS Query Bar ---
  Widget _buildInteractiveQueryBar() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            AppTheme.surface,
            AppTheme.surfaceSubtle,
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.accent.withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Row(
                children: [
                  Icon(Icons.auto_awesome, size: 14, color: AppTheme.accent),
                  SizedBox(width: 6),
                  Text(
                    'ASK AI MACRO ANALYST (LIVE)',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.accent,
                      letterSpacing: 0.5,
                    ),
                  ),
                ],
              ),
              if (_intelligenceReport != null)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: AppTheme.background,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: AppTheme.border),
                  ),
                  child: Text(
                    _intelligenceReport!.aiEngineUsed,
                    style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: AppTheme.textMuted),
                  ),
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
                    hintText: "Simulate a scenario (e.g. 'What if US CPI prints 3.1%?')...",
                    hintStyle: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(6),
                      borderSide: const BorderSide(color: AppTheme.border),
                    ),
                  ),
                  onSubmitted: _handleCustomQuerySubmit,
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.accent,
                  foregroundColor: Colors.black,
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                ),
                onPressed: _isQueryingAi ? null : () => _handleCustomQuerySubmit(_queryCtrl.text),
                child: _isQueryingAi
                    ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                    : const Text('Ask AI', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // --- 2. DXY Card ---
  Widget _buildDxyCard(DXYMetricsModel dxy) {
    final isBullish = dxy.trend == 'BULLISH';
    final trendColor = isBullish
        ? AppTheme.upGreen
        : (dxy.trend == 'BEARISH' ? AppTheme.downRed : AppTheme.accent);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(12),
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
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppTheme.accent.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: AppTheme.accent.withValues(alpha: 0.3)),
                    ),
                    child: const Row(
                      children: [
                        Icon(Icons.currency_exchange, size: 14, color: AppTheme.accent),
                        SizedBox(width: 4),
                        Text(
                          'DXY BENCHMARK',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.accent,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: trendColor.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      dxy.trend,
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        color: trendColor,
                      ),
                    ),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: AppTheme.surfaceSubtle,
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: AppTheme.border),
                ),
                child: Text(
                  'REGIME: ${dxy.marketRegime}',
                  style: const TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textPrimary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(
                dxy.value.toStringAsFixed(2),
                style: const TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.w800,
                  color: AppTheme.textPrimary,
                  letterSpacing: -0.5,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                '${dxy.changePct >= 0 ? '+' : ''}${dxy.changePct.toStringAsFixed(2)}%',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: dxy.changePct >= 0 ? AppTheme.upGreen : AppTheme.downRed,
                ),
              ),
              const Spacer(),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    'RSI(14): ${dxy.rsi14.toStringAsFixed(1)} | EMA200: ${dxy.ema200.toStringAsFixed(2)}',
                    style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: AppTheme.surfaceSubtle,
              borderRadius: BorderRadius.circular(6),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.bolt, size: 16, color: AppTheme.accent),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    dxy.smcStructure,
                    style: const TextStyle(
                      fontSize: 11,
                      color: AppTheme.textPrimary,
                      height: 1.35,
                    ),
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
              padding: const EdgeInsets.symmetric(vertical: 8),
              decoration: BoxDecoration(
                color: _activeStreamTab == 0 ? AppTheme.surfaceSubtle : AppTheme.surface,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: _activeStreamTab == 0 ? AppTheme.accent : AppTheme.border),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.calendar_month, size: 14, color: _activeStreamTab == 0 ? AppTheme.accent : AppTheme.textMuted),
                  const SizedBox(width: 6),
                  Text(
                    'Economic Calendar (${_events.length})',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: _activeStreamTab == 0 ? AppTheme.textPrimary : AppTheme.textMuted,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: GestureDetector(
            onTap: () => setState(() => _activeStreamTab = 1),
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 8),
              decoration: BoxDecoration(
                color: _activeStreamTab == 1 ? AppTheme.surfaceSubtle : AppTheme.surface,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: _activeStreamTab == 1 ? AppTheme.accent : AppTheme.border),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.feed_outlined, size: 14, color: _activeStreamTab == 1 ? AppTheme.accent : AppTheme.textMuted),
                  const SizedBox(width: 6),
                  Text(
                    'Live Breaking News (${_breakingNews.length})',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: _activeStreamTab == 1 ? AppTheme.textPrimary : AppTheme.textMuted,
                    ),
                  ),
                ],
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
          const Text('FILTER: ', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppTheme.textMuted)),
          const SizedBox(width: 4),
          ..._currencyFilters.map((c) {
            final isSel = _selectedCurrencyFilter == c;
            return Padding(
              padding: const EdgeInsets.only(right: 6),
              child: FilterChip(
                label: Text(c, style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: isSel ? Colors.black : AppTheme.textPrimary)),
                selected: isSel,
                selectedColor: AppTheme.accent,
                backgroundColor: AppTheme.surface,
                showCheckmark: false,
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 0),
                onSelected: (_) {
                  setState(() => _selectedCurrencyFilter = c);
                  _loadNewsData(forceRefresh: false);
                },
              ),
            );
          }),
          const SizedBox(width: 8),
          const Text('IMPACT: ', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppTheme.textMuted)),
          const SizedBox(width: 4),
          ...['ALL', 'HIGH', 'MEDIUM'].map((imp) {
            final isSel = _selectedImpactFilter == imp;
            return Padding(
              padding: const EdgeInsets.only(right: 6),
              child: FilterChip(
                label: Text(imp, style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: isSel ? Colors.black : AppTheme.textPrimary)),
                selected: isSel,
                selectedColor: imp == 'HIGH' ? AppTheme.downRed : AppTheme.accent,
                backgroundColor: AppTheme.surface,
                showCheckmark: false,
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 0),
                onSelected: (_) {
                  setState(() => _selectedImpactFilter = imp);
                  _loadNewsData(forceRefresh: false);
                },
              ),
            );
          }),
        ],
      ),
    );
  }

  // --- 5. Events Carousel ---
  Widget _buildEventsCarousel() {
    if (_events.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: AppTheme.surface,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: AppTheme.border),
        ),
        child: const Center(
          child: Text('No events found for this filter.', style: TextStyle(color: AppTheme.textMuted, fontSize: 12)),
        ),
      );
    }

    return SizedBox(
      height: 140,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: _events.length,
        separatorBuilder: (_, _) => const SizedBox(width: 10),
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
    return GestureDetector(
      onTap: () => _selectEvent(ev.id),
      child: Container(
        width: 230,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.accent.withValues(alpha: 0.08) : AppTheme.surface,
          borderRadius: BorderRadius.circular(10),
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
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: ev.impact == 'HIGH'
                        ? AppTheme.downRed.withValues(alpha: 0.15)
                        : AppTheme.accent.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    '${ev.currency} • ${ev.impact}',
                    style: TextStyle(
                      fontSize: 9,
                      fontWeight: FontWeight.w800,
                      color: ev.impact == 'HIGH' ? AppTheme.downRed : AppTheme.accent,
                    ),
                  ),
                ),
                Text(
                  ev.status,
                  style: TextStyle(
                    fontSize: 9,
                    fontWeight: FontWeight.w700,
                    color: hasActual ? AppTheme.upGreen : AppTheme.textMuted,
                  ),
                ),
              ],
            ),
            Text(
              ev.title,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: AppTheme.textPrimary,
                height: 1.25,
              ),
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _buildMetricCol('ACTUAL', ev.rawActual ?? (ev.actual != null ? '${ev.actual}${ev.unit}' : '--'), hasActual ? AppTheme.upGreen : AppTheme.textMuted),
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
        Text(label, style: const TextStyle(fontSize: 8, fontWeight: FontWeight.bold, color: AppTheme.textMuted)),
        const SizedBox(height: 2),
        Text(val, style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: valColor)),
      ],
    );
  }

  // --- Breaking News List ---
  Widget _buildBreakingNewsList() {
    if (_breakingNews.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: AppTheme.surface,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: AppTheme.border),
        ),
        child: const Center(child: Text('No breaking news found.', style: TextStyle(color: AppTheme.textMuted, fontSize: 12))),
      );
    }

    return Column(
      children: _breakingNews.take(5).map((n) {
        final isBull = n.sentiment == 'BULLISH';
        final isBear = n.sentiment == 'BEARISH';
        final sentColor = isBull ? AppTheme.upGreen : (isBear ? AppTheme.downRed : AppTheme.textMuted);

        return Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(12),
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
                  Row(
                    children: [
                      Text(n.source, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppTheme.accent)),
                      const SizedBox(width: 6),
                      Text('• ${n.currencies.join('/')}', style: const TextStyle(fontSize: 10, color: AppTheme.textMuted)),
                    ],
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: sentColor.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(n.sentiment, style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: sentColor)),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Text(n.title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppTheme.textPrimary)),
              const SizedBox(height: 4),
              Text(n.summary, style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary, height: 1.3), maxLines: 2, overflow: TextOverflow.ellipsis),
              const SizedBox(height: 6),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton.icon(
                  icon: const Icon(Icons.analytics_outlined, size: 14),
                  label: const Text('Analyze with AI', style: TextStyle(fontSize: 11)),
                  onPressed: () => _handleCustomQuerySubmit('Analyze impact of this breaking news headline on Forex majors: ${n.title}'),
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }

  // --- 6. 10-Layer Institutional Report Card ---
  Widget _buildIntelligenceReportCard(NewsIntelligenceReportModel report) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Row(
                children: [
                  Icon(Icons.insights, size: 16, color: AppTheme.accent),
                  SizedBox(width: 6),
                  Text(
                    '10-LAYER INSTITUTIONAL SYNTHESIS',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                      color: AppTheme.textPrimary,
                      letterSpacing: 0.5,
                    ),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: AppTheme.surfaceSubtle,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  report.aiEngineUsed,
                  style: const TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: AppTheme.accent),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _buildInfoRow(
            Icons.compare_arrows,
            'Deviation Impact',
            report.deviationAnalysis,
          ),
          const SizedBox(height: 10),
          _buildInfoRow(
            Icons.history_edu,
            'Historical Precedent',
            report.historicalComparison,
          ),
          const SizedBox(height: 10),
          _buildInfoRow(
            Icons.account_balance,
            'Macro Regime & DXY Confluence',
            report.macroRegimeSummary,
          ),
          const SizedBox(height: 10),
          _buildInfoRow(
            Icons.candlestick_chart,
            'SMC Technical Synthesis',
            report.smcTechnicalSynthesis,
          ),
          const Divider(height: 20, color: AppTheme.borderSubtle),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppTheme.accent.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppTheme.accent.withValues(alpha: 0.25)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.lightbulb, size: 16, color: AppTheme.accent),
                    SizedBox(width: 6),
                    Text(
                      'Actionable Institutional Conclusion',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.accent,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  report.actionableConclusion,
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppTheme.textPrimary,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoRow(IconData icon, String title, String body) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 16, color: AppTheme.accent),
        const SizedBox(width: 8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textSecondary,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                body,
                style: const TextStyle(
                  fontSize: 12,
                  color: AppTheme.textPrimary,
                  height: 1.35,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // --- 7. Pair-Specific Impact Section ---
  Widget _buildPairSpecificImpactSection(NewsIntelligenceReportModel report) {
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
    final biasColor = isBull
        ? AppTheme.upGreen
        : (isBear ? AppTheme.downRed : AppTheme.accent);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'PAIR SPECIFIC USD IMPACT',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w700,
                color: AppTheme.textMuted,
                letterSpacing: 1.0,
              ),
            ),
            Text(
              'Confidence: ${(activeAnalysis.confidence * 100).toInt()}%',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w700,
                color: biasColor,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: _availablePairs.map((sym) {
              final isSel = sym == _selectedPair;
              return Padding(
                padding: const EdgeInsets.only(right: 6),
                child: ChoiceChip(
                  label: Text(sym, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: isSel ? Colors.black : AppTheme.textPrimary)),
                  selected: isSel,
                  selectedColor: AppTheme.accent,
                  backgroundColor: AppTheme.surface,
                  onSelected: (_) => setState(() => _selectedPair = sym),
                ),
              );
            }).toList(),
          ),
        ),
        const SizedBox(height: 10),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppTheme.surface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppTheme.border),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    activeAnalysis.symbol,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: biasColor.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          activeAnalysis.directionalBias,
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            color: biasColor,
                          ),
                        ),
                      ),
                      const SizedBox(width: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: AppTheme.surface,
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: AppTheme.border),
                        ),
                        child: Text(
                          '${activeAnalysis.correlationToUsd} TO USD',
                          style: const TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w600,
                            color: AppTheme.textSecondary,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                activeAnalysis.tradeThesis,
                style: const TextStyle(
                  fontSize: 12,
                  color: AppTheme.textPrimary,
                  height: 1.4,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                activeAnalysis.smcConfluence,
                style: const TextStyle(
                  fontSize: 11,
                  color: AppTheme.textSecondary,
                  height: 1.35,
                ),
              ),
              if (activeAnalysis.keyLevels.isNotEmpty) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppTheme.surfaceSubtle,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _buildKeyLevelItem('Current', activeAnalysis.keyLevels['current']),
                      _buildKeyLevelItem('Swing High', activeAnalysis.keyLevels['swing_high']),
                      _buildKeyLevelItem('Swing Low', activeAnalysis.keyLevels['swing_low']),
                      _buildKeyLevelItem('Invalidation', activeAnalysis.keyLevels['invalidation']),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 12),
              if (widget.onSelectInstrumentForAnalysis != null)
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    icon: const Icon(Icons.analytics_rounded, size: 16),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.surfaceSubtle,
                      foregroundColor: AppTheme.accent,
                      side: const BorderSide(color: AppTheme.accent),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                      padding: const EdgeInsets.symmetric(vertical: 10),
                    ),
                    onPressed: () => widget.onSelectInstrumentForAnalysis!(activeAnalysis.symbol),
                    label: Text(
                      'Deep Dive Analysis for ${activeAnalysis.symbol}',
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildKeyLevelItem(String label, dynamic val) {
    final strVal = val != null ? val.toString() : '--';
    return Column(
      children: [
        Text(label, style: const TextStyle(fontSize: 9, color: AppTheme.textMuted, fontWeight: FontWeight.bold)),
        const SizedBox(height: 2),
        Text(strVal, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppTheme.textPrimary)),
      ],
    );
  }
}
