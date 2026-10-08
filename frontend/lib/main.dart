import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'services/api_service.dart';
import 'theme/app_theme.dart';
import 'screens/markets_screen.dart';
import 'screens/analysis_screen.dart';
import 'screens/alerts_screen.dart';
import 'screens/news_screen.dart';

@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
}

final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  try {
    await Firebase.initializeApp();
    FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);
  } catch (e) {
    debugPrint('Firebase initialize notice: $e');
  }

  runApp(const ForexAIApp());
  _initFCM();
}

final GlobalKey<MainNavigationShellState> shellKey = GlobalKey<MainNavigationShellState>();

void _handleNotificationOpen(RemoteMessage? message) {
  if (message == null) return;
  final type = message.data['type']?.toString();
  final screen = message.data['screen']?.toString();
  if (type == 'ECONOMIC_EVENT_UPCOMING' || type == 'ECONOMIC_EVENT_DAILY_BRIEFING' || screen == 'news') {
    final eventId = message.data['event_id']?.toString();
    shellKey.currentState?.navigateToNews(eventId);
    return;
  }

  final symbol = message.data['symbol']?.toString();
  if (symbol != null && symbol.isNotEmpty) {
    shellKey.currentState?.navigateToAnalysis(symbol);
    return;
  }
  // Fallback: search title or body for known symbol
  final text = '${message.notification?.title ?? ''} ${message.notification?.body ?? ''}'.toUpperCase();
  for (final s in ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCHF', 'USDCAD', 'XAGUSD']) {
    if (text.contains(s)) {
      shellKey.currentState?.navigateToAnalysis(s);
      return;
    }
  }
  if (text.contains('EVENT') || text.contains('CPI') || text.contains('MACRO') || text.contains('BRIEFING')) {
    shellKey.currentState?.navigateToNews();
    return;
  }
}

Future<void> _initFCM() async {
  try {
    final messaging = FirebaseMessaging.instance;
    await messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      provisional: false,
    );

    await messaging.setForegroundNotificationPresentationOptions(
      alert: true,
      badge: true,
      sound: true,
    );

    final token = await messaging.getToken();
    if (token != null) {
      debugPrint('FCM Token: $token');
      await ApiService.registerDevice(
        fcmToken: token,
        platform: 'android',
      );
    }

    try {
      await messaging.subscribeToTopic('economic_events');
      debugPrint('Subscribed to topic: economic_events');
    } catch (e) {
      debugPrint('Topic subscription notice: $e');
    }

    messaging.onTokenRefresh.listen((newToken) {
      ApiService.registerDevice(
        fcmToken: newToken,
        platform: 'android',
      );
    });

    // Check if app was opened from terminated state via notification click
    messaging.getInitialMessage().then((message) {
      if (message != null) {
        Future.delayed(const Duration(milliseconds: 600), () {
          _handleNotificationOpen(message);
        });
      }
    });

    // Handle notification click when app was in background
    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
      _handleNotificationOpen(message);
    });

    // Handle foreground alerts with a modern trading card banner
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      debugPrint('Foreground FCM received: ${message.notification?.title}');
      final ctx = navigatorKey.currentContext;
      if (ctx == null || !ctx.mounted) return;
      final messenger = ScaffoldMessenger.maybeOf(ctx);
      if (messenger == null) return;

      final title = message.notification?.title ?? message.data['title'] ?? 'AI Market Alert';
      final body = message.notification?.body ?? message.data['body'] ?? '';
      final symbol = message.data['symbol']?.toString();
      final state = message.data['state']?.toString() ?? 'ALERT';
      final type = message.data['type']?.toString();
      final action = message.data['action']?.toString() ?? '';
      final eventType = message.data['event_type']?.toString() ?? '';

      final isEconomicEvent = type == 'ECONOMIC_EVENT_UPCOMING' || type == 'ECONOMIC_EVENT_DAILY_BRIEFING';
      final isTradeSetup = type == 'TRADE_SETUP_ALERT';
      final isLifecycle = type == 'TRADE_LIFECYCLE_EVENT';
      final isHighEvent = message.data['impact'] == 'HIGH';

      Color accentColor;
      if (isEconomicEvent) {
        accentColor = isHighEvent ? const Color(0xFFEF4444) : const Color(0xFF3B82F6);
      } else if (isTradeSetup) {
        accentColor = action.contains('SELL') ? const Color(0xFFEF4444) : const Color(0xFF10B981);
      } else if (isLifecycle) {
        if (eventType.contains('TP') || eventType.contains('FILLED')) {
          accentColor = const Color(0xFF10B981);
        } else if (eventType.contains('CANCEL')) {
          accentColor = const Color(0xFFF59E0B);
        } else {
          accentColor = const Color(0xFFEF4444);
        }
      } else {
        final isBullish = state.contains('VALID') || title.contains('VALID');
        accentColor = isBullish ? const Color(0xFF10B981) : const Color(0xFFF59E0B);
      }

      messenger.hideCurrentSnackBar();
      messenger.showSnackBar(
        SnackBar(
          behavior: SnackBarBehavior.floating,
          backgroundColor: Colors.transparent,
          elevation: 0,
          margin: const EdgeInsets.fromLTRB(12, 0, 12, 16),
          duration: const Duration(seconds: 8),
          padding: EdgeInsets.zero,
          content: Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF0F172A), Color(0xFF1E293B)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: accentColor.withValues(alpha: 0.6), width: 1.5),
              boxShadow: [
                BoxShadow(
                  color: accentColor.withValues(alpha: 0.25),
                  blurRadius: 18,
                  spreadRadius: 2,
                  offset: const Offset(0, 4),
                ),
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.6),
                  blurRadius: 10,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: accentColor.withValues(alpha: 0.15),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(
                        isTradeSetup
                            ? (action.contains('SELL') ? Icons.trending_down_rounded : Icons.trending_up_rounded)
                            : (isLifecycle
                                ? (eventType.contains('TP') ? Icons.emoji_events_rounded : Icons.track_changes_rounded)
                                : (accentColor == const Color(0xFF10B981) ? Icons.trending_up_rounded : Icons.radar_rounded)),
                        color: accentColor,
                        size: 18,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        title,
                        style: TextStyle(
                          color: accentColor,
                          fontWeight: FontWeight.w700,
                          fontSize: 13,
                          letterSpacing: 0.2,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                      decoration: BoxDecoration(
                        color: const Color(0xFF334155),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        isTradeSetup
                            ? 'TRADE TICKET'
                            : (isLifecycle ? 'LIFECYCLE' : (isEconomicEvent ? 'MACRO' : 'LIVE')),
                        style: const TextStyle(
                          color: Color(0xFF94A3B8),
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
                if (body.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text(
                    body,
                    style: const TextStyle(
                      color: Color(0xFFE2E8F0),
                      fontSize: 12,
                      height: 1.35,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
                const SizedBox(height: 10),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    InkWell(
                      onTap: () {
                        ScaffoldMessenger.of(ctx).hideCurrentSnackBar();
                        _handleNotificationOpen(message);
                      },
                      borderRadius: BorderRadius.circular(8),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: accentColor.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: accentColor.withValues(alpha: 0.5)),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              isEconomicEvent
                                  ? (type == 'ECONOMIC_EVENT_DAILY_BRIEFING' ? 'VIEW CALENDAR' : 'VIEW EVENT')
                                  : (isTradeSetup
                                      ? (symbol != null ? 'VIEW $symbol TICKET' : 'VIEW TICKET')
                                      : (isLifecycle
                                          ? (symbol != null ? 'INSPECT $symbol' : 'INSPECT TICKET')
                                          : (symbol != null ? 'VIEW $symbol' : 'INSPECT SETUP'))),
                              style: TextStyle(
                                color: accentColor,
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(width: 4),
                            Icon(Icons.arrow_forward_rounded, size: 13, color: accentColor),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      );
    });
  } catch (e) {
    debugPrint('FCM setup note: $e');
  }
}

class ForexAIApp extends StatelessWidget {
  const ForexAIApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      navigatorKey: navigatorKey,
      title: 'Forex AI Market Platform',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme,
      home: MainNavigationShell(key: shellKey),
    );
  }
}

class MainNavigationShell extends StatefulWidget {
  const MainNavigationShell({super.key});

  @override
  State<MainNavigationShell> createState() => MainNavigationShellState();
}

class MainNavigationShellState extends State<MainNavigationShell> {
  int _currentIndex = 0;
  String _selectedSymbolForAnalysis = 'EURUSD';
  final Set<int> _loadedTabs = {0};

  void navigateToAnalysis(String symbol) {
    _onSelectInstrumentForAnalysis(symbol);
  }

  void navigateToNews([String? eventId]) {
    setState(() {
      _loadedTabs.add(3);
      _currentIndex = 3;
    });
  }

  void _onSelectInstrumentForAnalysis(String symbol) {
    setState(() {
      _selectedSymbolForAnalysis = symbol;
      _loadedTabs.add(1);
      _currentIndex = 1; // Switch to Analysis tab
    });
  }

  void _onTabTapped(int index) {
    setState(() {
      _loadedTabs.add(index);
      _currentIndex = index;
    });
  }

  @override
  Widget build(BuildContext context) {
    final List<Widget> screens = [
      MarketsScreen(
        onSelectInstrumentForAnalysis: _onSelectInstrumentForAnalysis,
      ),
      _loadedTabs.contains(1)
          ? AnalysisScreen(
              key: ValueKey(_selectedSymbolForAnalysis),
              initialSymbol: _selectedSymbolForAnalysis,
            )
          : const SizedBox.shrink(),
      _loadedTabs.contains(2)
          ? AlertsScreen(
              onSelectSymbol: _onSelectInstrumentForAnalysis,
            )
          : const SizedBox.shrink(),
      _loadedTabs.contains(3)
          ? NewsScreen(
              onSelectInstrumentForAnalysis: _onSelectInstrumentForAnalysis,
            )
          : const SizedBox.shrink(),
    ];

    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: screens,
      ),
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          border: Border(
            top: BorderSide(color: AppTheme.border, width: 1),
          ),
        ),
        child: BottomNavigationBar(
          currentIndex: _currentIndex,
          onTap: _onTabTapped,
          items: const [
            BottomNavigationBarItem(
              icon: Icon(Icons.candlestick_chart_outlined, size: 20),
              activeIcon: Icon(Icons.candlestick_chart_rounded, size: 20),
              label: 'Markets',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.query_stats_rounded, size: 20),
              activeIcon: Icon(Icons.query_stats_rounded, size: 20),
              label: 'Analysis',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.notifications_none_rounded, size: 20),
              activeIcon: Icon(Icons.notifications_rounded, size: 20),
              label: 'Alerts',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.feed_outlined, size: 20),
              activeIcon: Icon(Icons.feed_rounded, size: 20),
              label: 'News',
            ),
          ],
        ),
      ),
    );
  }
}
