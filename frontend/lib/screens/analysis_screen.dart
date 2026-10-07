import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/ai_analysis.dart';
import '../models/market_context_model.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class AnalysisScreen extends StatefulWidget {
  final String initialSymbol;

  const AnalysisScreen({
    super.key,
    this.initialSymbol = 'EURUSD',
  });

  @override
  State<AnalysisScreen> createState() => _AnalysisScreenState();
}

class _AnalysisScreenState extends State<AnalysisScreen> {
  late String _selectedSymbol;
  String _selectedTimeframe = '15m';
  List<String> _availableSymbols = [];

  AIAnalysisRecord? _analysis;
  MarketContextData? _contextData;
  Map<String, dynamic>? _utBotData;
  bool _enableUtBot = false;
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _selectedSymbol = widget.initialSymbol;
    if (_selectedSymbol == 'R_75' || _selectedSymbol.contains('VOLATILITY') || _selectedSymbol.contains('75')) {
      _enableUtBot = true;
    }
    _initAndLoad();
  }

  Future<void> _initAndLoad() async {
    final syms = await ApiService.getActiveSymbols();
    if (mounted) {
      setState(() {
        _availableSymbols = syms;
        if (!_availableSymbols.contains(_selectedSymbol) && _availableSymbols.isNotEmpty) {
          _selectedSymbol = _availableSymbols.first;
        }
      });
      _runAnalysis();
    }
  }

  Future<void> _runAnalysis() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final analysisFuture = ApiService.evaluateMarket(
        symbol: _selectedSymbol,
        timeframe: _selectedTimeframe,
      );

      final contextFuture = ApiService.getMarketContext(
        _selectedSymbol,
        timeframe: _selectedTimeframe,
      ).catchError((_) => MarketContextData(
        symbol: _selectedSymbol,
        timeframe: _selectedTimeframe,
        trend: 'Neutral',
        volatility: 'Evaluating',
        structure: 'Rangebound',
        range: 'Neutral',
        rsi: 50.0,
        atr: 0.0,
      ));

      final utBotFuture = _enableUtBot
          ? ApiService.getUtBotAnalysis(_selectedSymbol, timeframe: _selectedTimeframe)
              .catchError((_) => <String, dynamic>{})
          : Future.value(<String, dynamic>{});

      final results = await Future.wait([analysisFuture, contextFuture, utBotFuture]);
      setState(() {
        _analysis = results[0] as AIAnalysisRecord;
        final utMap = results[2];
        _utBotData = (utMap is Map && utMap.isNotEmpty) ? (utMap as Map<String, dynamic>) : null;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: const Text('Analysis'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, size: 20),
            onPressed: _runAnalysis,
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        children: [
          // Symbol & Timeframe bar
          _buildSelectorHeader(),
          const SizedBox(height: 10),
          _buildStrategyToggleBar(),
          const SizedBox(height: 14),

          if (_errorMessage != null) _buildErrorNotice(),

          if (_isLoading)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 40),
              child: Center(child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.textSecondary)),
            )
          else ...[
            // 0. UT Bot Strategy Overlay (Optional / Volatility 75)
            if (_enableUtBot) ...[
              _buildSectionLabel('UT Bot Strategy (Anti-Repaint)'),
              const SizedBox(height: 6),
              _buildUtBotCard(),
              const SizedBox(height: 18),
            ],

            if (_analysis != null) ...[
              // Meta Row: Symbol | Session | Time | Instruction Version
              _buildMetaInfoBar(),
              const SizedBox(height: 18),

              // 1. Market Context
              _buildSectionLabel('Market Context'),
              const SizedBox(height: 6),
              _buildContextCard(),
              const SizedBox(height: 18),

              // 2. Analysis
              _buildSectionLabel('Analysis'),
              const SizedBox(height: 6),
              _buildAnalysisTextCard(),
              const SizedBox(height: 18),

              // 3. Conditions
              _buildSectionLabel('Conditions'),
              const SizedBox(height: 6),
              _buildConditionsCard(),
              const SizedBox(height: 18),

              // 4. Conclusion
              _buildSectionLabel('Conclusion'),
              const SizedBox(height: 6),
              _buildConclusionCard(),
              const SizedBox(height: 24),
            ],
          ],

          ElevatedButton(
            onPressed: _isLoading ? null : _runAnalysis,
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.surfaceSubtle,
              foregroundColor: AppTheme.textPrimary,
              elevation: 0,
              side: const BorderSide(color: AppTheme.border),
              padding: const EdgeInsets.symmetric(vertical: 14),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            ),
            child: const Text('Evaluate Latest Market State', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  Widget _buildSelectorHeader() {
    return Row(
      children: [
        // Symbol Dropdown
        Expanded(
          flex: 3,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
            decoration: BoxDecoration(
              color: AppTheme.surface,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: AppTheme.border),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: _availableSymbols.contains(_selectedSymbol) ? _selectedSymbol : null,
                dropdownColor: AppTheme.surface,
                icon: const Icon(Icons.keyboard_arrow_down_rounded, size: 18, color: AppTheme.textMuted),
                isExpanded: true,
                items: _availableSymbols.map((sym) {
                  return DropdownMenuItem<String>(
                    value: sym,
                    child: Text(sym, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: AppTheme.textPrimary)),
                  );
                }).toList(),
                onChanged: (val) {
                  if (val != null) {
                    setState(() {
                      _selectedSymbol = val;
                      if (val == 'R_75' || val.contains('VOLATILITY') || val.contains('75')) {
                        _enableUtBot = true;
                      }
                    });
                    _runAnalysis();
                  }
                },
              ),
            ),
          ),
        ),
        const SizedBox(width: 8),
        // Timeframe selector
        Expanded(
          flex: 2,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 2),
            decoration: BoxDecoration(
              color: AppTheme.surface,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: AppTheme.border),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: _selectedTimeframe,
                dropdownColor: AppTheme.surface,
                icon: const Icon(Icons.keyboard_arrow_down_rounded, size: 18, color: AppTheme.textMuted),
                isExpanded: true,
                items: ['1m', '5m', '15m', '1h', '4h', '1d'].map((tf) {
                  return DropdownMenuItem<String>(
                    value: tf,
                    child: Text(tf.toUpperCase(), style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12, color: AppTheme.textPrimary)),
                  );
                }).toList(),
                onChanged: (val) {
                  if (val != null) {
                    setState(() => _selectedTimeframe = val);
                    _runAnalysis();
                  }
                },
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildMetaInfoBar() {
    final parsedTime = DateTime.tryParse(_analysis?.timestampUtc ?? '') ?? DateTime.now();
    final timeStr = _analysis != null
        ? '${DateFormat('HH:mm:ss').format(parsedTime.toUtc())} UTC'
        : '—';
    final session = _analysis?.sessionName.toUpperCase() ?? 'OFF-SESSION';
    final version = 'v${_analysis?.instructionVersionId ?? 1}.0';

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
          _buildMetaItem('Symbol', _analysis?.symbol ?? _selectedSymbol),
          _buildMetaDivider(),
          _buildMetaItem('Session', session),
          _buildMetaDivider(),
          _buildMetaItem('Time', timeStr),
          _buildMetaDivider(),
          _buildMetaItem('Instruction', version),
        ],
      ),
    );
  }

  Widget _buildMetaItem(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 10, color: AppTheme.textMuted, fontWeight: FontWeight.w600)),
        const SizedBox(height: 2),
        Text(value, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppTheme.textPrimary)),
      ],
    );
  }

  Widget _buildMetaDivider() {
    return Container(width: 1, height: 20, color: AppTheme.border);
  }

  Widget _buildSectionLabel(String label) {
    return Text(
      label,
      style: const TextStyle(
        fontSize: 11,
        fontWeight: FontWeight.w700,
        color: AppTheme.textMuted,
        letterSpacing: 1.0,
      ),
    );
  }

  Widget _buildContextCard() {
    final ctx = _contextData;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        children: [
          _buildContextItem('Trend', ctx?.trend ?? '—'),
          const Divider(height: 14, color: AppTheme.borderSubtle),
          _buildContextItem('Volatility', ctx?.volatility ?? '—'),
          const Divider(height: 14, color: AppTheme.borderSubtle),
          _buildContextItem('Structure', ctx?.structure ?? '—'),
          const Divider(height: 14, color: AppTheme.borderSubtle),
          _buildContextItem('Range', ctx?.range ?? '—'),
        ],
      ),
    );
  }

  Widget _buildContextItem(String label, String value) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 85,
          child: Text(label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.textSecondary)),
        ),
        const Text('—  ', style: TextStyle(color: AppTheme.textMuted, fontSize: 12)),
        Expanded(
          child: Text(value, style: const TextStyle(fontSize: 12, color: AppTheme.textPrimary)),
        ),
      ],
    );
  }

  Widget _buildAnalysisTextCard() {
    final reasoning = (_analysis?.fullReasoning != null && _analysis!.fullReasoning!.isNotEmpty)
        ? _analysis!.fullReasoning!
        : (_analysis?.summary.isNotEmpty == true ? _analysis!.summary : 'No analysis reasoning returned for this candle.');

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.border),
      ),
      child: Text(
        reasoning,
        style: const TextStyle(fontSize: 13, height: 1.5, color: AppTheme.textPrimary),
      ),
    );
  }

  Widget _buildConditionsCard() {
    final conditions = _analysis?.conditionBreakdown ?? [];
    if (conditions.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppTheme.surface,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: AppTheme.border),
        ),
        child: const Text('No explicit conditional rules triggered.', style: TextStyle(fontSize: 12, color: AppTheme.textMuted)),
      );
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        children: conditions.map((cond) {
          final isSat = cond.satisfied;
          final isInvalidated = _analysis?.state.toUpperCase() == 'INVALIDATED' && !isSat;

          String iconChar;
          Color iconColor;

          if (isSat) {
            iconChar = '✓';
            iconColor = AppTheme.upGreen;
          } else if (isInvalidated) {
            iconChar = '×';
            iconColor = AppTheme.downRed;
          } else {
            iconChar = '—';
            iconColor = AppTheme.textMuted;
          }

          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  iconChar,
                  style: TextStyle(
                    fontWeight: FontWeight.w900,
                    fontSize: 14,
                    color: iconColor,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        cond.condition,
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: isSat ? AppTheme.textPrimary : AppTheme.textSecondary,
                        ),
                      ),
                      if (cond.evidence.isNotEmpty)
                        Text(
                          cond.evidence,
                          style: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildConclusionCard() {
    final state = _analysis?.state ?? 'NO_SETUP';
    final stateColor = AppTheme.getStateColor(state);
    final stateLabel = AppTheme.getStateLabel(state);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: stateColor.withValues(alpha: 0.5)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            children: [
              Container(
                width: 10,
                height: 10,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: stateColor,
                ),
              ),
              const SizedBox(width: 12),
              Text(
                stateLabel,
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.8,
                  color: stateColor,
                ),
              ),
            ],
          ),
          Text(
            'From Analysis Engine',
            style: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorNotice() {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.invalidated.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.invalidated.withValues(alpha: 0.3)),
      ),
      child: Text(
        'Unable to evaluate: $_errorMessage',
        style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
      ),
    );
  }

  Widget _buildStrategyToggleBar() {
    final isV75 = _selectedSymbol == 'R_75' || _selectedSymbol.contains('VOLATILITY') || _selectedSymbol.contains('75');
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: _enableUtBot ? const Color(0xFF10B981).withValues(alpha: 0.5) : AppTheme.border,
          width: 1.2,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(5),
                decoration: BoxDecoration(
                  color: _enableUtBot ? const Color(0xFF10B981).withValues(alpha: 0.15) : const Color(0xFF334155),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.bolt_rounded,
                  size: 16,
                  color: _enableUtBot ? const Color(0xFF10B981) : AppTheme.textMuted,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Text(
                          'UT Bot Strategy',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.textPrimary,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                          decoration: BoxDecoration(
                            color: const Color(0xFF0F172A),
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(color: const Color(0xFF10B981).withValues(alpha: 0.4)),
                          ),
                          child: const Text(
                            'ZERO REPAINT',
                            style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: Color(0xFF10B981)),
                          ),
                        ),
                      ],
                    ),
                    Text(
                      isV75 ? 'Recommended for Deriv Volatility 75' : 'Optional ATR trailing stop & momentum filter',
                      style: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
                    ),
                  ],
                ),
              ),
              Switch(
                value: _enableUtBot,
                activeThumbColor: const Color(0xFF10B981),
                onChanged: (val) {
                  setState(() {
                    _enableUtBot = val;
                  });
                  _runAnalysis();
                },
              ),
            ],
          ),
          if (isV75 && !_enableUtBot) ...[
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: const Color(0xFFF59E0B).withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(6),
              ),
              child: const Row(
                children: [
                  Icon(Icons.info_outline_rounded, size: 14, color: Color(0xFFF59E0B)),
                  SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      'Turn ON UT Bot for high-frequency synthetic volatility tracking.',
                      style: TextStyle(fontSize: 11, color: Color(0xFFF59E0B)),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildUtBotCard() {
    if (_utBotData == null) {
      return Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: AppTheme.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppTheme.border),
        ),
        child: const Center(
          child: Column(
            children: [
              CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF10B981)),
              SizedBox(height: 10),
              Text('Calculating non-repainting UT Bot levels...', style: TextStyle(color: AppTheme.textMuted, fontSize: 12)),
            ],
          ),
        ),
      );
    }

    final data = _utBotData!;
    final signal = data['signal']?.toString() ?? 'WAIT';
    final currentPrice = (data['current_price'] as num?)?.toDouble() ?? 0.0;
    final trail = (data['trailing_stop'] as num?)?.toDouble() ?? 0.0;
    final ema200 = (data['ema_200'] as num?)?.toDouble() ?? 0.0;
    final rsi = (data['rsi'] as num?)?.toDouble() ?? 50.0;
    final trend = data['trend']?.toString() ?? 'NEUTRAL';
    final summary = data['summary']?.toString() ?? '';
    final mtf = data['mtf'] as Map<String, dynamic>? ?? {};
    final conditions = data['conditions'] as List<dynamic>? ?? [];
    final sessionDirective = data['session_directive']?.toString() ?? '24/7 Algorithmic Market — Traditional bank sessions do not apply.';
    final validityStr = data['validity_window_str']?.toString() ?? '3 Minutes';
    final executionRule = data['execution_rule']?.toString() ?? '';
    final tp1 = (data['take_profit_1'] as num?)?.toDouble() ?? 0.0;
    final tp2 = (data['take_profit_2'] as num?)?.toDouble() ?? 0.0;
    final maxSlippage = (data['max_slippage_points'] as num?)?.toDouble() ?? 0.0;

    final isBuy = signal == 'BUY' || signal == 'BULLISH_HOLD';
    final isSell = signal == 'SELL' || signal == 'BEARISH_HOLD';
    final signalColor = isBuy
        ? const Color(0xFF10B981)
        : isSell
            ? const Color(0xFFEF4444)
            : const Color(0xFF94A3B8);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: signalColor.withValues(alpha: 0.5), width: 1.5),
        boxShadow: [
          BoxShadow(
            color: signalColor.withValues(alpha: 0.12),
            blurRadius: 16,
            spreadRadius: 1,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: 8,
            runSpacing: 6,
            children: [
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: signalColor.withValues(alpha: 0.15),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      isBuy
                          ? Icons.trending_up_rounded
                          : isSell
                              ? Icons.trending_down_rounded
                              : Icons.radar_rounded,
                      size: 16,
                      color: signalColor,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'UT BOT SIGNAL (${_selectedTimeframe.toUpperCase()})',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                      color: signalColor,
                      letterSpacing: 0.5,
                    ),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: const Color(0xFF0F172A),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: AppTheme.border),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.lock_outline_rounded, size: 11, color: Color(0xFF10B981)),
                    SizedBox(width: 4),
                    Text(
                      'LOCKED (CONFIRMED)',
                      style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF10B981)),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
            decoration: BoxDecoration(
              color: const Color(0xFF0F172A),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: const Color(0xFF38BDF8).withValues(alpha: 0.25)),
            ),
            child: Row(
              children: [
                const Icon(Icons.all_inclusive_rounded, size: 13, color: Color(0xFF38BDF8)),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    sessionDirective,
                    style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: Color(0xFF94A3B8)),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 10),

          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 14),
            decoration: BoxDecoration(
              color: signalColor.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: signalColor.withValues(alpha: 0.3)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  signal.replaceAll('_', ' '),
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w900,
                    color: signalColor,
                    letterSpacing: 0.5,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  summary,
                  style: const TextStyle(fontSize: 11.5, color: Color(0xFFCBD5E1), height: 1.3),
                ),
              ],
            ),
          ),
          if (executionRule.isNotEmpty) ...[
            Container(
              margin: const EdgeInsets.only(top: 8),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: AppTheme.background,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: signalColor.withValues(alpha: 0.35)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    alignment: WrapAlignment.spaceBetween,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    spacing: 6,
                    runSpacing: 4,
                    children: [
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.timer_outlined, size: 13, color: signalColor),
                          const SizedBox(width: 5),
                          Text(
                            'ACTION WINDOW: NEXT $validityStr'.toUpperCase(),
                            style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w800, color: signalColor),
                          ),
                        ],
                      ),
                      if (maxSlippage > 0)
                        Text(
                          'Max Slip: ±${maxSlippage.toStringAsFixed(3)}',
                          style: const TextStyle(fontSize: 9, color: AppTheme.textMuted, fontWeight: FontWeight.w600),
                        ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    executionRule,
                    style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w600, color: AppTheme.textPrimary, height: 1.35),
                  ),
                  if (tp1 > 0 || tp2 > 0) ...[
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        if (tp1 > 0)
                          Text('TP1: ${tp1.toStringAsFixed(4)}  ', style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF10B981))),
                        if (tp2 > 0)
                          Text('TP2: ${tp2.toStringAsFixed(4)}', style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF10B981))),
                      ],
                    ),
                  ],
                ],
              ),
            ),
          ],
          const SizedBox(height: 14),

          Row(
            children: [
              Expanded(
                child: _buildMetricTile(
                  label: 'Trailing Stop',
                  value: trail.toStringAsFixed(4),
                  subValue: currentPrice > trail ? 'Support' : 'Resistance',
                  color: signalColor,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _buildMetricTile(
                  label: 'EMA 200 Trend',
                  value: ema200.toStringAsFixed(4),
                  subValue: trend,
                  color: trend == 'BULLISH' ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: _buildMetricTile(
                  label: 'RSI (14)',
                  value: rsi.toStringAsFixed(1),
                  subValue: rsi >= 45 && rsi <= 55 ? 'Balanced' : (rsi > 55 ? 'Bullish' : 'Bearish'),
                  color: const Color(0xFFFBBF24),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _buildMetricTile(
                  label: 'UT Parameters',
                  value: 'Sens: ${data['sensitivity'] ?? 1.5}',
                  subValue: 'ATR: ${data['atr_period'] ?? 10}',
                  color: const Color(0xFF38BDF8),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),

          const Text('Multi-Timeframe Radar (Anti-Repaint)', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.textSecondary)),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(child: _buildMtfPill('5M', mtf['5m']?.toString() ?? 'WAIT')),
              const SizedBox(width: 6),
              Expanded(child: _buildMtfPill('15M', mtf['15m']?.toString() ?? 'WAIT')),
              const SizedBox(width: 6),
              Expanded(child: _buildMtfPill('1H', mtf['1h']?.toString() ?? 'WAIT')),
            ],
          ),
          const SizedBox(height: 12),

          if (conditions.isNotEmpty) ...[
            const Divider(color: AppTheme.border, height: 16),
            ...conditions.map((c) {
              final cMap = c as Map<String, dynamic>;
              final isPass = cMap['status'] == 'PASS' || cMap['status'] == 'CONFIRMED';
              return Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  children: [
                    Icon(
                      isPass ? Icons.check_circle_rounded : Icons.cancel_rounded,
                      size: 14,
                      color: isPass ? const Color(0xFF10B981) : const Color(0xFF64748B),
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        '${cMap['name']}: ${cMap['details']}',
                        style: TextStyle(
                          fontSize: 11,
                          color: isPass ? AppTheme.textPrimary : AppTheme.textMuted,
                        ),
                      ),
                    ),
                  ],
                ),
              );
            }),
          ],
        ],
      ),
    );
  }

  Widget _buildMetricTile({
    required String label,
    required String value,
    required String subValue,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: AppTheme.background,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 10, color: AppTheme.textMuted)),
          const SizedBox(height: 2),
          Text(value, style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: color)),
          Text(subValue, style: const TextStyle(fontSize: 10, color: AppTheme.textSecondary)),
        ],
      ),
    );
  }

  Widget _buildMtfPill(String tf, String status) {
    final isBuy = status.contains('BUY') || status.contains('BULLISH');
    final isSell = status.contains('SELL') || status.contains('BEARISH');
    final color = isBuy ? const Color(0xFF10B981) : isSell ? const Color(0xFFEF4444) : const Color(0xFF64748B);

    return Container(
      padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 8),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Column(
        children: [
          Text(tf, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppTheme.textSecondary)),
          const SizedBox(height: 2),
          Text(
            isBuy ? 'BUY' : isSell ? 'SELL' : 'WAIT',
            style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: color),
          ),
        ],
      ),
    );
  }
}
