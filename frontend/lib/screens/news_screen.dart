import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../models/news_intelligence.dart';
import '../theme/app_theme.dart';

class NewsScreen extends StatefulWidget {
  final Function(String)? onSelectInstrumentForAnalysis;

  const NewsScreen({
    Key? key,
    this.onSelectInstrumentForAnalysis,
  }) : super(key: key);

  @override
  State<NewsScreen> createState() => _NewsScreenState();
}

class _NewsScreenState extends State<NewsScreen> {
  bool _isLoading = true;
  String? _errorMessage;

  DXYMetricsModel? _dxyMetrics;
  List<EconomicEventModel> _events = [];
  NewsIntelligenceReportModel? _intelligenceReport;
  String? _selectedEventId;
  String _selectedPair = 'EURUSD';

  final List<String> _availablePairs = [
    'EURUSD',
    'GBPUSD',
    'USDJPY',
    'XAUUSD',
    'BTCUSD',
    'AUDUSD',
    'USDCAD',
  ];

  @override
  void initState() {
    super.initState();
    _loadNewsData();
  }

  Future<void> _loadNewsData({bool forceRefresh = false}) async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final dxyFuture = ApiService.getDxyMetrics();
      final eventsFuture = ApiService.getEconomicEvents();
      final intelFuture = ApiService.getNewsIntelligence(
        eventId: _selectedEventId,
        forceRefresh: forceRefresh,
      );

      final results = await Future.wait([dxyFuture, eventsFuture, intelFuture]);

      if (mounted) {
        setState(() {
          _dxyMetrics = results[0] as DXYMetricsModel;
          _events = results[1] as List<EconomicEventModel>;
          _intelligenceReport = results[2] as NewsIntelligenceReportModel;
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: const Row(
          children: [
            Icon(Icons.feed_outlined, size: 20, color: AppTheme.accent),
            SizedBox(width: 8),
            Text('News Intelligence'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, size: 20),
            tooltip: 'Refresh Intelligence',
            onPressed: () => _loadNewsData(forceRefresh: true),
          ),
        ],
      ),
      body: _isLoading && _intelligenceReport == null
          ? const Center(
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: AppTheme.textSecondary,
              ),
            )
          : RefreshIndicator(
              onRefresh: () => _loadNewsData(forceRefresh: true),
              color: AppTheme.accent,
              backgroundColor: AppTheme.surface,
              child: ListView(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                children: [
                  if (_errorMessage != null) _buildErrorBanner(),
                  if (_dxyMetrics != null) _buildDxyCard(_dxyMetrics!),
                  const SizedBox(height: 16),
                  _buildEventsSection(),
                  const SizedBox(height: 16),
                  if (_intelligenceReport != null)
                    _buildIntelligenceSynthesisCard(_intelligenceReport!),
                  const SizedBox(height: 16),
                  if (_intelligenceReport != null)
                    _buildPairImpactSection(_intelligenceReport!),
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
              'Failed to refresh intelligence: $_errorMessage',
              style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
            ),
          ),
        ],
      ),
    );
  }

  // --- 1. DXY US Dollar Strength & SMC Regime Card ---
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

  // --- 2. Macro Economic Events List ---
  Widget _buildEventsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'High-Impact Macro Events',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w700,
                color: AppTheme.textPrimary,
              ),
            ),
            Text(
              'Tap event for intelligence',
              style: TextStyle(fontSize: 11, color: AppTheme.textMuted),
            ),
          ],
        ),
        const SizedBox(height: 8),
        SizedBox(
          height: 115,
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
        ),
      ],
    );
  }

  Widget _buildEventItem(EconomicEventModel ev, bool isSelected) {
    final hasActual = ev.actual != null;
    return GestureDetector(
      onTap: () => _selectEvent(ev.id),
      child: Container(
        width: 220,
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
                    ev.impact,
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
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                    color: hasActual ? AppTheme.upGreen : AppTheme.textMuted,
                  ),
                ),
              ],
            ),
            Text(
              ev.title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: isSelected ? AppTheme.accent : AppTheme.textPrimary,
              ),
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _buildValueChip('Actual', ev.actual, ev.unit, isPrimary: true),
                _buildValueChip('Fcast', ev.forecast, ev.unit),
                _buildValueChip('Prev', ev.previous, ev.unit),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildValueChip(String label, double? val, String unit, {bool isPrimary = false}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 9, color: AppTheme.textMuted)),
        Text(
          val != null ? '$val$unit' : '--',
          style: TextStyle(
            fontSize: 11,
            fontWeight: isPrimary ? FontWeight.w700 : FontWeight.w500,
            color: isPrimary ? AppTheme.textPrimary : AppTheme.textSecondary,
          ),
        ),
      ],
    );
  }

  // --- 3. News Intelligence Synthesis Card ---
  Widget _buildIntelligenceSynthesisCard(NewsIntelligenceReportModel report) {
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
            children: [
              const Icon(Icons.psychology, size: 20, color: AppTheme.accent),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  report.event.title,
                  style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textPrimary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            report.event.meaning,
            style: const TextStyle(
              fontSize: 12,
              color: AppTheme.textSecondary,
              height: 1.4,
            ),
          ),
          const Divider(height: 20, color: AppTheme.borderSubtle),
          _buildInfoRow(
            Icons.analytics_outlined,
            'Deviation Analysis',
            report.deviationAnalysis,
          ),
          const SizedBox(height: 10),
          _buildInfoRow(
            Icons.history_edu,
            'Historical Comparison',
            report.historicalComparison,
          ),
          const SizedBox(height: 10),
          _buildInfoRow(
            Icons.account_balance,
            'SMC Technical Confluence',
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
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 14, color: AppTheme.textMuted),
            const SizedBox(width: 6),
            Text(
              title,
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: AppTheme.textMuted,
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        Text(
          body,
          style: const TextStyle(
            fontSize: 12,
            color: AppTheme.textPrimary,
            height: 1.35,
          ),
        ),
      ],
    );
  }

  // --- 4. Pair-Specific Analysis for User-Selected Pairs ---
  Widget _buildPairImpactSection(NewsIntelligenceReportModel report) {
    final activeAnalysis = report.pairAnalyses.firstWhere(
      (p) => p.symbol == _selectedPair,
      orElse: () => report.pairAnalyses.isNotEmpty
          ? report.pairAnalyses[0]
          : PairImpactAnalysisModel(
              symbol: _selectedPair,
              directionalBias: 'NEUTRAL',
              confidence: 0.5,
              correlationToUsd: 'INVERSE',
              smcConfluence: '',
              keyLevels: {},
              tradeThesis: '',
            ),
    );

    final isBull = activeAnalysis.directionalBias == 'BULLISH';
    final biasColor = isBull
        ? AppTheme.upGreen
        : (activeAnalysis.directionalBias == 'BEARISH'
            ? AppTheme.downRed
            : AppTheme.textMuted);

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
              const Text(
                'Pair-Specific USD Confluence',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textPrimary,
                ),
              ),
              Text(
                '${report.pairAnalyses.length} Pairs Evaluated',
                style: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
              ),
            ],
          ),
          const SizedBox(height: 10),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: _availablePairs.map((pair) {
                final isSelected = pair == _selectedPair;
                return Padding(
                  padding: const EdgeInsets.only(right: 8.0),
                  child: ChoiceChip(
                    label: Text(pair),
                    selected: isSelected,
                    onSelected: (sel) {
                      if (sel) setState(() => _selectedPair = pair);
                    },
                    selectedColor: AppTheme.accent,
                    backgroundColor: AppTheme.surfaceSubtle,
                    labelStyle: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: isSelected ? Colors.black : AppTheme.textPrimary,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(6),
                      side: BorderSide(
                        color: isSelected ? AppTheme.accent : AppTheme.border,
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
          ),
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppTheme.surfaceSubtle,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppTheme.borderSubtle),
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
                    height: 1.3,
                  ),
                ),
                if (widget.onSelectInstrumentForAnalysis != null) ...[
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      icon: const Icon(Icons.analytics_rounded, size: 16),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppTheme.accent,
                        side: const BorderSide(color: AppTheme.accent),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(6),
                        ),
                        padding: const EdgeInsets.symmetric(vertical: 8),
                      ),
                      onPressed: () {
                        widget.onSelectInstrumentForAnalysis!(activeAnalysis.symbol);
                      },
                      label: Text('Open ${activeAnalysis.symbol} Analysis Chart'),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
