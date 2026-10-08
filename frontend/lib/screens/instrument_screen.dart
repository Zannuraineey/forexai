import 'dart:async';
import 'package:flutter/material.dart';
import '../models/candle_model.dart';
import '../models/market_context_model.dart';
import '../models/session_state.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/deriv_chart_widget.dart';

class InstrumentScreen extends StatefulWidget {
  final String symbol;
  final Function(String symbol)? onAnalyze;

  const InstrumentScreen({
    Key? key,
    required this.symbol,
    this.onAnalyze,
  }) : super(key: key);

  @override
  State<InstrumentScreen> createState() => _InstrumentScreenState();
}

class _InstrumentScreenState extends State<InstrumentScreen> {
  String _selectedTimeframe = '15m';
  final List<String> _timeframes = ['1m', '5m', '15m', '1h', '4h', '1d'];

  List<CandleModel> _candles = [];
  MarketContextData? _contextData;
  CurrentSessionState? _sessionState;
  bool _useDerivChart = true;

  bool _isLoading = true;
  String? _errorMessage;
  Timer? _refreshTimer;

  bool get _isSyntheticIndex {
    final s = widget.symbol.toUpperCase();
    return s.startsWith('R_') || s.startsWith('BOOM') || s.startsWith('CRASH') || s.startsWith('1HZ') || s.contains('VOLATILITY');
  }

  @override
  void initState() {
    super.initState();
    _useDerivChart = !_isSyntheticIndex;
    _loadAll();
    _refreshTimer = Timer.periodic(const Duration(seconds: 4), (_) {
      if (mounted) {
        _loadTimeframeData();
      }
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadAll() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final candlesFuture = ApiService.getCandles(widget.symbol, _selectedTimeframe, limit: 50);
      final sessionFuture = _sessionState != null
          ? Future.value(_sessionState!)
          : ApiService.getCurrentSession();
      final contextFuture = ApiService.getMarketContext(widget.symbol, timeframe: _selectedTimeframe).catchError((_) => MarketContextData(
        symbol: widget.symbol,
        timeframe: _selectedTimeframe,
        trend: 'Neutral',
        volatility: 'Evaluating',
        structure: 'Rangebound',
        range: 'Neutral',
        rsi: 50.0,
        atr: 0.0,
      ));

      final results = await Future.wait([candlesFuture, sessionFuture, contextFuture]);
      setState(() {
        _candles = results[0] as List<CandleModel>;
        _sessionState = results[1] as CurrentSessionState;
        _contextData = results[2] as MarketContextData;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _loadTimeframeData() async {
    try {
      final candlesFuture = ApiService.getCandles(widget.symbol, _selectedTimeframe, limit: 50);
      final contextFuture = ApiService.getMarketContext(widget.symbol, timeframe: _selectedTimeframe).catchError((_) => MarketContextData(
        symbol: widget.symbol,
        timeframe: _selectedTimeframe,
        trend: 'Neutral',
        volatility: 'Evaluating',
        structure: 'Rangebound',
        range: 'Neutral',
        rsi: 50.0,
        atr: 0.0,
      ));

      final results = await Future.wait([candlesFuture, contextFuture]);
      if (mounted) {
        setState(() {
          _candles = results[0] as List<CandleModel>;
          _contextData = results[1] as MarketContextData;
        });
      }
    } catch (_) {}
  }

  void _onTimeframeChanged(String tf) {
    if (_selectedTimeframe == tf) return;
    setState(() => _selectedTimeframe = tf);
    _loadTimeframeData();
  }

  @override
  Widget build(BuildContext context) {
    final latestCandle = _candles.isNotEmpty ? _candles.last : null;
    final firstCandle = _candles.isNotEmpty ? _candles.first : null;
    final price = latestCandle?.close;
    final prevClose = firstCandle?.open ?? (price ?? 1.0);
    final chgPct = price != null && prevClose > 0 ? ((price - prevClose) / prevClose) * 100 : 0.0;
    final isPos = chgPct >= 0;
    final chgColor = isPos ? AppTheme.upGreen : AppTheme.downRed;

    final activeSessions = _sessionState?.activeSessions ?? [];
    final sessionStr = activeSessions.isEmpty ? 'Off-Session' : '${activeSessions.join(' & ')} — Active';

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: Text(widget.symbol, style: const TextStyle(fontWeight: FontWeight.w700)),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, size: 20),
            onPressed: _loadAll,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.textSecondary))
          : ListView(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              children: [
                // Header: Symbol, Price, % Change
                Text(
                  widget.symbol,
                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppTheme.textSecondary),
                ),
                const SizedBox(height: 4),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.baseline,
                  textBaseline: TextBaseline.alphabetic,
                  children: [
                    Text(
                      price != null ? _formatPrice(price) : '—',
                      style: const TextStyle(
                        fontFamily: 'monospace',
                        fontSize: 28,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.textPrimary,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Text(
                      '${isPos ? '+' : ''}${chgPct.toStringAsFixed(2)}%',
                      style: TextStyle(
                        fontFamily: 'monospace',
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        color: chgColor,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),

                // Timeframe Selector: [1m] [5m] [15m] [1H] [4H] [1D]
                _buildTimeframeSelector(),
                const SizedBox(height: 16),

                // Candlestick Chart Area
                _buildChartCard(),
                const SizedBox(height: 20),

                // Session Information
                _buildSectionHeader('Session'),
                const SizedBox(height: 6),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                  decoration: BoxDecoration(
                    color: AppTheme.surface,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppTheme.border),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Text(
                          sessionStr,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.textPrimary),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(
                          color: activeSessions.isNotEmpty ? AppTheme.upGreen.withValues(alpha: 0.15) : AppTheme.surfaceSubtle,
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          activeSessions.isNotEmpty ? 'ACTIVE' : 'OFF-SESSION',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            color: activeSessions.isNotEmpty ? AppTheme.upGreen : AppTheme.textMuted,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),

                // Market Context
                _buildSectionHeader('Market Context'),
                const SizedBox(height: 6),
                _buildContextCard(),
                const SizedBox(height: 24),

                // Evaluate Button
                if (widget.onAnalyze != null)
                  ElevatedButton(
                    onPressed: () {
                      widget.onAnalyze!(widget.symbol);
                      Navigator.pop(context);
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.surfaceSubtle,
                      foregroundColor: AppTheme.textPrimary,
                      elevation: 0,
                      side: const BorderSide(color: AppTheme.border),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    child: Text('Evaluate Strategy on ${widget.symbol}', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                  ),
                const SizedBox(height: 16),
              ],
            ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Text(
      title,
      style: const TextStyle(
        fontSize: 11,
        fontWeight: FontWeight.w700,
        color: AppTheme.textMuted,
        letterSpacing: 1.0,
      ),
    );
  }

  Widget _buildTimeframeSelector() {
    return Row(
      children: _timeframes.map((tf) {
        final isSelected = _selectedTimeframe == tf;
        return Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 3),
            child: InkWell(
              onTap: () => _onTimeframeChanged(tf),
              borderRadius: BorderRadius.circular(6),
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 7),
                decoration: BoxDecoration(
                  color: isSelected ? AppTheme.surfaceSubtle : Colors.transparent,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(
                    color: isSelected ? AppTheme.textSecondary : AppTheme.border,
                  ),
                ),
                alignment: Alignment.center,
                child: Text(
                  tf.toUpperCase(),
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                    color: isSelected ? AppTheme.textPrimary : AppTheme.textMuted,
                  ),
                ),
              ),
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildChartCard() {
    if (_useDerivChart) {
      return DerivChartWidget(
        symbol: widget.symbol,
        timeframe: _selectedTimeframe,
        height: 350,
        onSwitchToNative: () => setState(() => _useDerivChart = false),
      );
    }
    return _buildNativeChartCard();
  }

  Widget _buildNativeChartCard() {
    return Container(
      height: 260,
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: const BoxDecoration(
              color: AppTheme.surfaceSubtle,
              border: Border(bottom: BorderSide(color: AppTheme.borderSubtle)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'NATIVE CANDLESTICK CHART',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textMuted,
                    letterSpacing: 0.5,
                  ),
                ),
                InkWell(
                  onTap: () => setState(() => _useDerivChart = true),
                  borderRadius: BorderRadius.circular(4),
                  child: const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    child: Row(
                      children: [
                        Icon(Icons.show_chart, size: 12, color: AppTheme.accent),
                        SizedBox(width: 4),
                        Text(
                          'Deriv Chart',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w600,
                            color: AppTheme.accent,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: _candles.isEmpty
                ? const Center(
                    child: Text(
                      'No candle data available for this timeframe',
                      style: TextStyle(color: AppTheme.textMuted, fontSize: 12),
                    ),
                  )
                : Padding(
                    padding: const EdgeInsets.fromLTRB(10, 10, 10, 10),
                    child: CustomPaint(
                      size: const Size(double.infinity, 220),
                      painter: _CandleChartPainter(candles: _candles),
                    ),
                  ),
          ),
        ],
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
          _buildContextRow('Trend', ctx?.trend ?? '—'),
          const Divider(height: 16, color: AppTheme.borderSubtle),
          _buildContextRow('Volatility', ctx?.volatility ?? '—'),
          const Divider(height: 16, color: AppTheme.borderSubtle),
          _buildContextRow('Structure', ctx?.structure ?? '—'),
          const Divider(height: 16, color: AppTheme.borderSubtle),
          _buildContextRow('Range', ctx?.range ?? '—'),
        ],
      ),
    );
  }

  Widget _buildContextRow(String label, String value) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 90,
          child: Text(
            label,
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.textSecondary),
          ),
        ),
        const Text('—  ', style: TextStyle(color: AppTheme.textMuted, fontSize: 12)),
        Expanded(
          child: Text(
            value,
            style: const TextStyle(fontSize: 12, color: AppTheme.textPrimary),
          ),
        ),
      ],
    );
  }

  String _formatPrice(double val) {
    if (widget.symbol.startsWith('XAU') || widget.symbol.contains('100') || widget.symbol.contains('500')) {
      return val.toStringAsFixed(2);
    }
    if (widget.symbol.contains('JPY')) {
      return val.toStringAsFixed(3);
    }
    return val.toStringAsFixed(5);
  }
}

/// Lightweight, clean Candlestick Chart Painter
class _CandleChartPainter extends CustomPainter {
  final List<CandleModel> candles;

  _CandleChartPainter({required this.candles});

  @override
  void paint(Canvas canvas, Size size) {
    if (candles.isEmpty) return;

    final visibleCandles = candles.length > 40 ? candles.sublist(candles.length - 40) : candles;
    double minPrice = visibleCandles.first.low;
    double maxPrice = visibleCandles.first.high;

    for (final c in visibleCandles) {
      if (c.low < minPrice) minPrice = c.low;
      if (c.high > maxPrice) maxPrice = c.high;
    }

    if (maxPrice == minPrice) maxPrice += 1.0;
    final priceRange = maxPrice - minPrice;

    // Draw horizontal grid lines
    final gridPaint = Paint()
      ..color = AppTheme.borderSubtle
      ..strokeWidth = 1.0;

    for (int i = 1; i <= 3; i++) {
      final y = size.height * (i / 4);
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }

    final candleWidth = (size.width - 45) / visibleCandles.length;
    final bodyWidth = (candleWidth * 0.7).clamp(2.0, 10.0);

    for (int i = 0; i < visibleCandles.length; i++) {
      final c = visibleCandles[i];
      final isBull = c.isBullish;
      final candleColor = isBull ? AppTheme.upGreen : AppTheme.downRed;

      final paint = Paint()
        ..color = candleColor
        ..strokeWidth = 1.0;

      final x = (i * candleWidth) + (candleWidth / 2);

      final highY = size.height - ((c.high - minPrice) / priceRange) * size.height;
      final lowY = size.height - ((c.low - minPrice) / priceRange) * size.height;
      final openY = size.height - ((c.open - minPrice) / priceRange) * size.height;
      final closeY = size.height - ((c.close - minPrice) / priceRange) * size.height;

      // Draw wick
      canvas.drawLine(Offset(x, highY), Offset(x, lowY), paint);

      // Draw body
      final topY = isBull ? closeY : openY;
      final bottomY = isBull ? openY : closeY;
      final height = (bottomY - topY).abs().clamp(1.0, size.height);

      canvas.drawRect(
        Rect.fromLTWH(x - (bodyWidth / 2), topY, bodyWidth, height),
        paint,
      );
    }

    // Draw Price Labels on the right
    final textPainterMax = TextPainter(
      text: TextSpan(
        text: maxPrice.toStringAsFixed(maxPrice > 100 ? 2 : 4),
        style: const TextStyle(fontSize: 9, color: AppTheme.textMuted, fontFamily: 'monospace'),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    textPainterMax.paint(canvas, Offset(size.width - 40, 2));

    final textPainterMin = TextPainter(
      text: TextSpan(
        text: minPrice.toStringAsFixed(minPrice > 100 ? 2 : 4),
        style: const TextStyle(fontSize: 9, color: AppTheme.textMuted, fontFamily: 'monospace'),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    textPainterMin.paint(canvas, Offset(size.width - 40, size.height - 12));
  }

  @override
  bool shouldRepaint(covariant _CandleChartPainter oldDelegate) => true;
}
