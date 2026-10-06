import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../theme/app_theme.dart';

class DerivChartWidget extends StatefulWidget {
  final String symbol;
  final String timeframe;
  final double height;
  final VoidCallback? onSwitchToNative;

  const DerivChartWidget({
    super.key,
    required this.symbol,
    required this.timeframe,
    this.height = 320,
    this.onSwitchToNative,
  });

  static String toTradingViewSymbol(String sym) {
    final clean = sym.toUpperCase().replaceAll('/', '').trim();
    const map = {
      'AUDUSD': 'FX:AUDUSD',
      'EURUSD': 'FX:EURUSD',
      'GBPUSD': 'FX:GBPUSD',
      'USDJPY': 'FX:USDJPY',
      'USDCHF': 'FX:USDCHF',
      'USDCAD': 'FX:USDCAD',
      'NZDUSD': 'FX:NZDUSD',
      'EURGBP': 'FX:EURGBP',
      'EURJPY': 'FX:EURJPY',
      'GBPJPY': 'FX:GBPJPY',
      'EURCHF': 'FX:EURCHF',
      'AUDJPY': 'FX:AUDJPY',
      'XAUUSD': 'OANDA:XAUUSD',
      'XAGUSD': 'OANDA:XAGUSD',
      'XPTUSD': 'OANDA:XPTUSD',
      'XPDUSD': 'OANDA:XPDUSD',
      'BTCUSD': 'BINANCE:BTCUSDT',
      'ETHUSD': 'BINANCE:ETHUSDT',
      'R_75': 'DERIV:R_75',
      'VOLATILITY_75': 'DERIV:R_75',
      '1HZ75V': 'DERIV:1HZ75V',
      'R_10': 'DERIV:R_10',
      'R_25': 'DERIV:R_25',
      'R_50': 'DERIV:R_50',
      'R_100': 'DERIV:R_100',
      'BOOM500': 'DERIV:BOOM500',
      'BOOM1000': 'DERIV:BOOM1000',
      'CRASH500': 'DERIV:CRASH500',
      'CRASH1000': 'DERIV:CRASH1000',
    };
    if (clean.startsWith('R_') || clean.startsWith('BOOM') || clean.startsWith('CRASH')) {
      return 'DERIV:$clean';
    }
    return map[clean] ?? 'FX:$clean';
  }

  static String toTradingViewInterval(String tf) {
    switch (tf.toLowerCase()) {
      case '1m':
        return '1';
      case '5m':
        return '5';
      case '15m':
        return '15';
      case '1h':
        return '60';
      case '4h':
        return '240';
      case '1d':
        return 'D';
      default:
        return '15';
    }
  }

  static String buildDerivChartUrl(String symbol, String timeframe) {
    final tvSym = Uri.encodeComponent(toTradingViewSymbol(symbol));
    final tvInterval = toTradingViewInterval(timeframe);
    return 'https://s.tradingview.com/widgetembed/?symbol=$tvSym&interval=$tvInterval&theme=dark&style=1&timezone=Etc%2FUTC&locale=en';
  }

  @override
  State<DerivChartWidget> createState() => _DerivChartWidgetState();
}

class _DerivChartWidgetState extends State<DerivChartWidget> {
  WebViewController? _controller;
  bool _isLoading = true;
  bool _platformUnavailable = false;
  String? _currentUrl;

  @override
  void initState() {
    super.initState();
    _initWebView();
  }

  void _initWebView() {
    // Check if the running APK has the native Android WebView plugin compiled in
    if (WebViewPlatform.instance == null) {
      setState(() {
        _platformUnavailable = true;
        _isLoading = false;
      });
      return;
    }

    try {
      final url = DerivChartWidget.buildDerivChartUrl(widget.symbol, widget.timeframe);
      _currentUrl = url;

      final controller = WebViewController()
        ..setJavaScriptMode(JavaScriptMode.unrestricted)
        ..setBackgroundColor(const Color(0xFF0E131D))
        ..setNavigationDelegate(
          NavigationDelegate(
            onPageStarted: (String url) {
              if (mounted) setState(() => _isLoading = true);
            },
            onPageFinished: (String url) {
              _injectCustomStyles();
              if (mounted) setState(() => _isLoading = false);
            },
          ),
        )
        ..loadRequest(Uri.parse(url));

      _controller = controller;
    } catch (_) {
      setState(() {
        _platformUnavailable = true;
        _isLoading = false;
      });
    }
  }

  void _injectCustomStyles() {
    // Hide website navigation/headers to make the TradingView chart feel completely native
    _controller?.runJavaScript('''
      (function() {
        const style = document.createElement('style');
        style.innerHTML = `
          header, .header, #deriv-header-container, .deriv-right-side-nav, #deriv-signup,
          .theme-toggle, #cookie-banner, .cookie-banner, .banner, [class*="signup"], [class*="header"] {
            display: none !important;
          }
          body, html {
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
            background: #0E131D !important;
          }
          #tv_chart_container, .chart-container {
            height: 100vh !important;
            width: 100vw !important;
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
          }
        `;
        document.head.appendChild(style);
      })();
    ''');
  }

  @override
  void didUpdateWidget(covariant DerivChartWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.symbol != widget.symbol || oldWidget.timeframe != widget.timeframe) {
      final newUrl = DerivChartWidget.buildDerivChartUrl(widget.symbol, widget.timeframe);
      if (newUrl != _currentUrl) {
        _currentUrl = newUrl;
        if (_controller != null) {
          setState(() => _isLoading = true);
          _controller!.loadRequest(Uri.parse(newUrl));
        }
      }
    }
  }

  void _openFullScreen() {
    if (_controller == null) return;
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (ctx) => Scaffold(
          backgroundColor: const Color(0xFF0E131D),
          appBar: AppBar(
            backgroundColor: AppTheme.surface,
            elevation: 0,
            leading: IconButton(
              icon: const Icon(Icons.arrow_back, color: AppTheme.textPrimary, size: 20),
              onPressed: () => Navigator.of(ctx).pop(),
            ),
            title: Text(
              '${widget.symbol} • ${widget.timeframe.toUpperCase()} (Deriv Chart)',
              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: AppTheme.textPrimary),
            ),
            actions: [
              IconButton(
                icon: const Icon(Icons.refresh, color: AppTheme.textSecondary, size: 18),
                tooltip: 'Reload chart',
                onPressed: () => _controller?.reload(),
              ),
            ],
          ),
          body: WebViewWidget(controller: _controller!),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: widget.height,
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.border),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        children: [
          // Sub-bar for Chart Controls & Status
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: const BoxDecoration(
              color: AppTheme.surfaceSubtle,
              border: Border(bottom: BorderSide(color: AppTheme.borderSubtle)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: const BoxDecoration(
                        color: AppTheme.upGreen,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      'LIVE TRADINGVIEW CHART (${DerivChartWidget.toTradingViewSymbol(widget.symbol)})',
                      style: const TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.textSecondary,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
                Row(
                  children: [
                    if (widget.onSwitchToNative != null)
                      InkWell(
                        onTap: widget.onSwitchToNative,
                        borderRadius: BorderRadius.circular(4),
                        child: const Padding(
                          padding: EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          child: Row(
                            children: [
                              Icon(Icons.candlestick_chart, size: 12, color: AppTheme.textMuted),
                              SizedBox(width: 4),
                              Text('Native', style: TextStyle(fontSize: 10, color: AppTheme.textMuted)),
                            ],
                          ),
                        ),
                      ),
                    const SizedBox(width: 6),
                    InkWell(
                      onTap: () => _controller?.reload(),
                      borderRadius: BorderRadius.circular(4),
                      child: const Padding(
                        padding: EdgeInsets.all(4),
                        child: Icon(Icons.refresh, size: 13, color: AppTheme.textMuted),
                      ),
                    ),
                    const SizedBox(width: 4),
                    InkWell(
                      onTap: _openFullScreen,
                      borderRadius: BorderRadius.circular(4),
                      child: const Padding(
                        padding: EdgeInsets.all(4),
                        child: Icon(Icons.fullscreen, size: 15, color: AppTheme.textSecondary),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          // WebView Body or Fallback
          Expanded(
            child: _platformUnavailable || _controller == null
                ? Container(
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                    color: AppTheme.surface,
                    alignment: Alignment.center,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.refresh, color: AppTheme.watch, size: 28),
                        const SizedBox(height: 10),
                        const Text(
                          'Full Rebuild Required for WebView',
                          style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppTheme.textPrimary),
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          'The app process in your terminal was running before webview_flutter was added.\n\nPress "q" in the Flutter terminal and run "flutter run" so Gradle compiles the Android WebView plugin.',
                          textAlign: TextAlign.center,
                          style: TextStyle(fontSize: 11, color: AppTheme.textSecondary, height: 1.4),
                        ),
                        const SizedBox(height: 14),
                        if (widget.onSwitchToNative != null)
                          ElevatedButton.icon(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppTheme.surfaceSubtle,
                              foregroundColor: AppTheme.textPrimary,
                              side: const BorderSide(color: AppTheme.border),
                              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                            ),
                            icon: const Icon(Icons.candlestick_chart, size: 14, color: AppTheme.accent),
                            label: const Text('View Native Candlestick Chart', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                            onPressed: widget.onSwitchToNative,
                          ),
                      ],
                    ),
                  )
                : Stack(
                    children: [
                      WebViewWidget(controller: _controller!),
                      if (_isLoading)
                        Container(
                          color: const Color(0xFF0E131D),
                          child: const Center(
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                SizedBox(
                                  width: 22,
                                  height: 22,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: AppTheme.textSecondary,
                                  ),
                                ),
                                SizedBox(height: 10),
                                Text(
                                  'Loading Deriv live chart...',
                                  style: TextStyle(fontSize: 11, color: AppTheme.textMuted),
                                ),
                              ],
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
}
