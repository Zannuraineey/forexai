import 'package:flutter/material.dart';
import '../models/ai_analysis.dart';
import '../models/backtest_result.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class HistoryBacktestScreen extends StatefulWidget {
  const HistoryBacktestScreen({Key? key}) : super(key: key);

  @override
  State<HistoryBacktestScreen> createState() => _HistoryBacktestScreenState();
}

class _HistoryBacktestScreenState extends State<HistoryBacktestScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  List<AIAnalysisRecord> _history = [];
  bool _isLoadingHistory = true;

  // Backtest runner state
  String _btSymbol = 'EURUSD';
  String _btTimeframe = '15m';
  String _btSession = 'london';
  final TextEditingController _btPromptCtrl = TextEditingController(
    text: 'Price sweeps Asian high and RSI < 70.',
  );
  bool _isBacktesting = false;
  BacktestResultModel? _backtestResult;
  String? _btError;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    setState(() => _isLoadingHistory = true);
    try {
      final records = await ApiService.getAnalysisHistory(limit: 50);
      setState(() {
        _history = records;
        _isLoadingHistory = false;
      });
    } catch (e) {
      setState(() => _isLoadingHistory = false);
    }
  }

  Future<void> _runBacktest() async {
    setState(() {
      _isBacktesting = true;
      _btError = null;
    });

    try {
      final now = DateTime.now().toUtc();
      final res = await ApiService.runBacktest(
        symbol: _btSymbol,
        timeframe: _btTimeframe,
        sessionName: _btSession,
        customInstructions: _btPromptCtrl.text.trim(),
        startDate: now.subtract(const Duration(days: 7)),
        endDate: now,
      );

      setState(() {
        _backtestResult = res;
        _isBacktesting = false;
      });
    } catch (e) {
      setState(() {
        _btError = e.toString().replaceAll('Exception: ', '');
        _isBacktesting = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Analysis History & Backtesting'),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: AppTheme.primaryLight,
          labelColor: AppTheme.primaryLight,
          unselectedLabelColor: AppTheme.textMuted,
          tabs: const [
            Tab(text: 'Analysis History'),
            Tab(text: 'Backtesting Runner'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildHistoryTab(),
          _buildBacktestTab(),
        ],
      ),
    );
  }

  Widget _buildHistoryTab() {
    if (_isLoadingHistory) {
      return const Center(child: CircularProgressIndicator(color: AppTheme.primaryLight));
    }

    if (_history.isEmpty) {
      return const Center(
        child: Text('No historical analysis records found yet.'),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadHistory,
      color: AppTheme.primaryLight,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _history.length,
        itemBuilder: (context, index) {
          final r = _history[index];
          final stateColor = AppTheme.getStateColor(r.state);

          return Container(
            margin: const EdgeInsets.only(bottom: 12),
            padding: const EdgeInsets.all(14),
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
                      '${r.symbol} (${r.timeframe})',
                      style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: stateColor.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        r.state,
                        style: TextStyle(
                          color: stateColor,
                          fontWeight: FontWeight.w800,
                          fontSize: 11,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  r.summary,
                  style: const TextStyle(fontSize: 13, color: AppTheme.textPrimary, height: 1.3),
                ),
                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Session: ${r.sessionName.toUpperCase()} • Ver: #${r.instructionVersionId ?? 1}',
                      style: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
                    ),
                    Text(
                      r.timestampUtc.split('T').first,
                      style: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
                    ),
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildBacktestTab() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppTheme.surface,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppTheme.border),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'BACKTEST CONFIGURATION',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textMuted,
                  letterSpacing: 1.1,
                ),
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      decoration: const InputDecoration(
                        labelText: 'Symbol',
                        border: OutlineInputBorder(),
                        contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                      ),
                      controller: TextEditingController(text: _btSymbol),
                      onChanged: (v) => _btSymbol = v.toUpperCase(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextField(
                      decoration: const InputDecoration(
                        labelText: 'Timeframe',
                        border: OutlineInputBorder(),
                        contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                      ),
                      controller: TextEditingController(text: _btTimeframe),
                      onChanged: (v) => _btTimeframe = v,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _btPromptCtrl,
                maxLines: 3,
                style: const TextStyle(fontSize: 13),
                decoration: const InputDecoration(
                  labelText: 'Natural Language Instruction to Backtest',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                height: 46,
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primary,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  icon: const Icon(Icons.play_arrow_rounded),
                  label: const Text('Run Historical Replay & Evaluation', style: TextStyle(fontWeight: FontWeight.w700)),
                  onPressed: _isBacktesting ? null : _runBacktest,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        if (_isBacktesting)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 40),
            child: Center(
              child: Column(
                children: [
                  CircularProgressIndicator(color: AppTheme.primaryLight),
                  SizedBox(height: 14),
                  Text('Replaying historical bars & evaluating rules...'),
                ],
              ),
            ),
          )
        else if (_btError != null)
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppTheme.invalidated.withOpacity(0.12),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppTheme.invalidated.withOpacity(0.4)),
            ),
            child: Text(_btError!),
          )
        else if (_backtestResult != null)
          _buildBacktestResultsCard(_backtestResult!),
      ],
    );
  }

  Widget _buildBacktestResultsCard(BacktestResultModel res) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Backtest #${res.id} - ${res.symbol}',
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppTheme.validSetup.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  res.status,
                  style: const TextStyle(color: AppTheme.validSetup, fontWeight: FontWeight.w800, fontSize: 11),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'Total Bars Evaluated: ${res.totalCandlesAnalyzed}',
            style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13),
          ),
          const SizedBox(height: 12),
          const Text(
            'STATE DISTRIBUTION',
            style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppTheme.textMuted),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: res.stateDistribution.entries.map((e) {
              final color = AppTheme.getStateColor(e.key);
              return Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: color.withOpacity(0.4)),
                ),
                child: Text(
                  '${e.key}: ${e.value}',
                  style: TextStyle(color: color, fontWeight: FontWeight.w700, fontSize: 12),
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}
