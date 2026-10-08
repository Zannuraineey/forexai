import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
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
              const SizedBox(height: 18),

              // 5. Actionable Trade Execution Ticket
              if (_analysis?.tradeSetup != null || _analysis?.state == 'VALID_SETUP') ...[
                _buildSectionLabel('Actionable Trade Ticket (3-Tier Targets)'),
                const SizedBox(height: 6),
                _buildTradeTicketCard(),
                const SizedBox(height: 24),
              ],
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

  // ---------------------------------------------------------------------------
  // Actionable Trade Ticket Card & 3-Tier Scaling Implementation
  // ---------------------------------------------------------------------------

  Widget _buildTradeTicketCard() {
    final setup = _analysis?.tradeSetup;
    final isShort = setup?.action.contains('SELL') ?? (_analysis?.summary.contains('SELL') ?? false);
    final action = setup?.action ?? (isShort ? 'SELL LIMIT' : 'BUY LIMIT');
    final actionColor = isShort ? AppTheme.downRed : AppTheme.upGreen;
    final entry = (setup?.entryPrice != null && setup!.entryPrice > 0)
        ? setup.entryPrice
        : (_extractSummaryPrice('Entry') ?? 0.0);
    final sl = (setup?.stopLoss != null && setup!.stopLoss > 0)
        ? setup.stopLoss
        : (_extractSummaryPrice('SL') ?? 0.0);
    final tp1 = (setup?.targets['tp1']?.price != null && setup!.targets['tp1']!.price > 0)
        ? setup.targets['tp1']!.price
        : (_extractSummaryPrice('TP1') ?? 0.0);
    final tp2 = (setup?.targets['tp2']?.price != null && setup!.targets['tp2']!.price > 0)
        ? setup.targets['tp2']!.price
        : ((setup?.takeProfit != null && setup!.takeProfit > 0)
            ? setup.takeProfit
            : (_extractSummaryPrice('TP2') ?? 0.0));
    final tp3 = (setup?.targets['tp3']?.price != null && setup!.targets['tp3']!.price > 0)
        ? setup.targets['tp3']!.price
        : (_extractSummaryPrice('TP3') ?? 0.0);
    final rr = setup?.rrRatio ?? 3.5;
    final riskPips = setup?.riskPips ?? 0.0;
    final grade = setup?.grade ?? 'Grade A+';
    final slBuffer = setup?.slBufferPips ?? 15.0;

    void copyToClipboard(String text, String label) {
      Clipboard.setData(ClipboardData(text: text));
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('$label copied to clipboard ($text)'),
          duration: const Duration(seconds: 2),
          backgroundColor: AppTheme.surfaceSubtle,
          behavior: SnackBarBehavior.floating,
        ),
      );
    }

    final masterParams =
        '${_analysis?.symbol ?? _selectedSymbol} $action @ ${entry > 0 ? entry.toStringAsFixed(2) : "--"} | SL: ${sl > 0 ? sl.toStringAsFixed(2) : "--"} | TP1: ${tp1 > 0 ? tp1.toStringAsFixed(2) : "--"} | TP2: ${tp2 > 0 ? tp2.toStringAsFixed(2) : "--"} | TP3: ${tp3 > 0 ? tp3.toStringAsFixed(2) : "--"}';

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: actionColor.withValues(alpha: 0.4),
          width: 1.2,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: actionColor.withValues(alpha: 0.08),
              borderRadius: const BorderRadius.vertical(top: Radius.circular(9)),
              border: Border(
                bottom: BorderSide(color: actionColor.withValues(alpha: 0.2)),
              ),
            ),
            child: Wrap(
              spacing: 8,
              runSpacing: 6,
              alignment: WrapAlignment.spaceBetween,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: actionColor.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: actionColor),
                      ),
                      child: Text(
                        action,
                        style: TextStyle(
                          color: actionColor,
                          fontSize: 12,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      '${_analysis?.symbol ?? _selectedSymbol} • ${_analysis?.timeframe.toUpperCase() ?? _selectedTimeframe.toUpperCase()}',
                      style: const TextStyle(
                        color: AppTheme.textPrimary,
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
                Wrap(
                  spacing: 6,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: AppTheme.surfaceSubtle,
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: AppTheme.border),
                      ),
                      child: Text(
                        grade,
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.textPrimary,
                        ),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: AppTheme.surfaceSubtle,
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: AppTheme.border),
                      ),
                      child: Text(
                        '1:${rr.toStringAsFixed(1)} R:R',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: actionColor,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Quick Master Copy Bar
                InkWell(
                  onTap: () => copyToClipboard(masterParams, 'Order Parameters'),
                  borderRadius: BorderRadius.circular(6),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceSubtle,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: AppTheme.border),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.copy_rounded, size: 14, color: AppTheme.textSecondary),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            masterParams,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: 11,
                              fontFamily: 'monospace',
                              color: AppTheme.textSecondary,
                            ),
                          ),
                        ),
                        const SizedBox(width: 6),
                        const Text(
                          'COPY ALL',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.accent,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 14),

                // Core Geometry Matrix: Entry | Stop Loss | Target 2
                LayoutBuilder(
                  builder: (context, constraints) {
                    final itemWidth = (constraints.maxWidth - 16) / 3;
                    return Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        _buildGeometryBox(
                          label: 'ENTRY LIMIT',
                          value: entry > 0 ? entry.toStringAsFixed(2) : '--',
                          subtext: 'FVG Midpoint Retest',
                          color: AppTheme.textPrimary,
                          width: constraints.maxWidth > 340 ? itemWidth : double.infinity,
                          onCopy: entry > 0 ? () => copyToClipboard(entry.toStringAsFixed(2), 'Entry') : null,
                        ),
                        _buildGeometryBox(
                          label: 'STOP LOSS',
                          value: sl > 0 ? sl.toStringAsFixed(2) : '--',
                          subtext: riskPips > 0 ? '-$riskPips pips (+${slBuffer}p ATR)' : '+${slBuffer}p ATR Buffer',
                          color: AppTheme.downRed,
                          width: constraints.maxWidth > 340 ? itemWidth : double.infinity,
                          onCopy: sl > 0 ? () => copyToClipboard(sl.toStringAsFixed(2), 'Stop Loss') : null,
                        ),
                        _buildGeometryBox(
                          label: 'TARGET 2 (TP2)',
                          value: tp2 > 0 ? tp2.toStringAsFixed(2) : '--',
                          subtext: '1:${rr.toStringAsFixed(1)} R:R Liquidity',
                          color: AppTheme.upGreen,
                          width: constraints.maxWidth > 340 ? itemWidth : double.infinity,
                          onCopy: tp2 > 0 ? () => copyToClipboard(tp2.toStringAsFixed(2), 'Take Profit 2') : null,
                        ),
                      ],
                    );
                  },
                ),
                const SizedBox(height: 14),

                // 3-Tier Scaling Targets
                const Text(
                  '3-TIER SCALING EXECUTION BLUEPRINT',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textMuted,
                    letterSpacing: 0.8,
                  ),
                ),
                const SizedBox(height: 8),

                _buildTargetTierRow(
                  tier: 'TP1',
                  rr: '1:1.5 R:R',
                  price: tp1 > 0 ? tp1.toStringAsFixed(2) : '--',
                  actionLabel: 'CLOSE 40% & MOVE SL TO BREAK-EVEN',
                  note: 'Crucial milestone: locks in profit and immunizes position against market reversal.',
                  isMilestone: true,
                  onCopy: tp1 > 0 ? () => copyToClipboard(tp1.toStringAsFixed(2), 'TP1') : null,
                ),
                const SizedBox(height: 6),
                _buildTargetTierRow(
                  tier: 'TP2',
                  rr: '1:${rr.toStringAsFixed(1)} R:R',
                  price: tp2 > 0 ? tp2.toStringAsFixed(2) : '--',
                  actionLabel: 'CLOSE 40% AT STRUCTURAL LIQUIDITY',
                  note: 'Opposite session dealing range extreme / target liquidity pool.',
                  isMilestone: false,
                  onCopy: tp2 > 0 ? () => copyToClipboard(tp2.toStringAsFixed(2), 'TP2') : null,
                ),
                const SizedBox(height: 6),
                _buildTargetTierRow(
                  tier: 'TP3',
                  rr: '1:5.0 R:R',
                  price: tp3 > 0 ? tp3.toStringAsFixed(2) : '--',
                  actionLabel: 'TRAIL 20% RUNNER',
                  note: 'Leave runner position with trailing stop behind swing structure.',
                  isMilestone: false,
                  onCopy: tp3 > 0 ? () => copyToClipboard(tp3.toStringAsFixed(2), 'TP3') : null,
                ),
                const SizedBox(height: 14),

                // Invalidation & Front-Run Rule
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF59E0B).withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: const Color(0xFFF59E0B).withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.shield_outlined, size: 15, color: Color(0xFFF59E0B)),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'FRONT-RUN & INVALIDATION RULE',
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w700,
                                color: Color(0xFFF59E0B),
                                letterSpacing: 0.5,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              setup?.invalidation.note ??
                                  'Cancel pending limit order if price reaches TP1 (${tp1 > 0 ? tp1.toStringAsFixed(2) : "target"}) before entry is filled (30m validity window).',
                              style: const TextStyle(
                                fontSize: 11,
                                color: AppTheme.textSecondary,
                                height: 1.3,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 14),

                // Confluences Checklist
                if (setup != null && setup.confluence.isNotEmpty) ...[
                  const Text(
                    'VERIFIED TECHNICAL CONFLUENCES',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.textMuted,
                      letterSpacing: 0.8,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: setup.confluence.map((c) {
                      return Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: AppTheme.surfaceSubtle,
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: AppTheme.border),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.check_circle_rounded, size: 12, color: AppTheme.upGreen),
                            const SizedBox(width: 5),
                            Flexible(
                              child: Text(
                                c,
                                style: const TextStyle(fontSize: 11, color: AppTheme.textPrimary),
                              ),
                            ),
                          ],
                        ),
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 14),
                ],

                // Interactive Lifecycle Triggers
                const Text(
                  'NOTIFY LIFECYCLE MILESTONES',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textMuted,
                    letterSpacing: 0.8,
                  ),
                ),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    _buildLifecycleButton(
                      label: 'Order Filled',
                      icon: Icons.check_circle_outline_rounded,
                      color: AppTheme.accent,
                      onTap: () => _triggerLifecycleAlert('ENTRY_FILLED', entry, action),
                    ),
                    _buildLifecycleButton(
                      label: 'TP1 Hit (Move BE)',
                      icon: Icons.emoji_events_outlined,
                      color: AppTheme.upGreen,
                      onTap: () => _triggerLifecycleAlert('TP1_HIT_MOVE_TO_BE', tp1, action),
                    ),
                    _buildLifecycleButton(
                      label: 'TP2 Hit',
                      icon: Icons.military_tech_outlined,
                      color: AppTheme.upGreen,
                      onTap: () => _triggerLifecycleAlert('TP2_HIT', tp2, action),
                    ),
                    _buildLifecycleButton(
                      label: 'Cancel Front-Run',
                      icon: Icons.cancel_outlined,
                      color: const Color(0xFFF59E0B),
                      onTap: () => _triggerLifecycleAlert('SETUP_CANCELLED', entry, action),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildGeometryBox({
    required String label,
    required String value,
    required String subtext,
    required Color color,
    required double width,
    VoidCallback? onCopy,
  }) {
    return Container(
      width: width,
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
      decoration: BoxDecoration(
        color: AppTheme.surfaceSubtle,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                label,
                style: const TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textMuted,
                  letterSpacing: 0.5,
                ),
              ),
              if (onCopy != null)
                InkWell(
                  onTap: onCopy,
                  child: const Padding(
                    padding: EdgeInsets.all(2.0),
                    child: Icon(Icons.copy_rounded, size: 12, color: AppTheme.textMuted),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w800,
              fontFamily: 'monospace',
              color: color,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            subtext,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              fontSize: 10,
              color: AppTheme.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTargetTierRow({
    required String tier,
    required String rr,
    required String price,
    required String actionLabel,
    required String note,
    required bool isMilestone,
    VoidCallback? onCopy,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: isMilestone ? const Color(0xFF10B981).withValues(alpha: 0.06) : AppTheme.surfaceSubtle,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(
          color: isMilestone ? const Color(0xFF10B981).withValues(alpha: 0.3) : AppTheme.border,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                decoration: BoxDecoration(
                  color: isMilestone ? const Color(0xFF10B981).withValues(alpha: 0.2) : AppTheme.surface,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  tier,
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    color: isMilestone ? const Color(0xFF10B981) : AppTheme.textPrimary,
                  ),
                ),
              ),
              const SizedBox(width: 6),
              Text(
                rr,
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textSecondary,
                ),
              ),
              const Spacer(),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    price,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w800,
                      fontFamily: 'monospace',
                      color: isMilestone ? const Color(0xFF10B981) : AppTheme.textPrimary,
                    ),
                  ),
                  if (onCopy != null) ...[
                    const SizedBox(width: 6),
                    InkWell(
                      onTap: onCopy,
                      child: const Icon(Icons.copy_rounded, size: 12, color: AppTheme.textMuted),
                    ),
                  ],
                ],
              ),
            ],
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                decoration: BoxDecoration(
                  color: isMilestone ? const Color(0xFF10B981).withValues(alpha: 0.15) : AppTheme.surface,
                  borderRadius: BorderRadius.circular(3),
                  border: Border.all(
                    color: isMilestone ? const Color(0xFF10B981).withValues(alpha: 0.3) : AppTheme.border,
                  ),
                ),
                child: Text(
                  actionLabel,
                  style: TextStyle(
                    fontSize: 9,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.3,
                    color: isMilestone ? const Color(0xFF10B981) : AppTheme.textSecondary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 2),
          Text(
            note,
            style: const TextStyle(
              fontSize: 10,
              color: AppTheme.textMuted,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLifecycleButton({
    required String label,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: color.withValues(alpha: 0.3)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 12, color: color),
            const SizedBox(width: 4),
            Text(
              label,
              style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: color),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _triggerLifecycleAlert(String eventType, double price, String action) async {
    final sym = _analysis?.symbol ?? _selectedSymbol;
    final tf = _analysis?.timeframe ?? _selectedTimeframe;
    final ok = await ApiService.reportTradeLifecycleEvent(
      symbol: sym,
      eventType: eventType,
      price: price > 0 ? price : 0.0,
      timeframe: tf,
      action: action,
      analysisId: _analysis?.id,
    );
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(ok
            ? 'Lifecycle milestone dispatched: $eventType ($sym)'
            : 'Milestone recorded locally.'),
        duration: const Duration(seconds: 2),
        backgroundColor: ok ? AppTheme.surfaceSubtle : AppTheme.invalidated.withValues(alpha: 0.8),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  double? _extractSummaryPrice(String key) {
    final text = _analysis?.summary ?? '';
    final reg = RegExp('$key:\\s*([0-9.]+)');
    final m = reg.firstMatch(text);
    if (m != null) {
      return double.tryParse(m.group(1) ?? '');
    }
    return null;
  }
}

