import 'package:flutter/material.dart';
import '../models/ai_analysis.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class AIAnalysisScreen extends StatefulWidget {
  final String initialSymbol;

  const AIAnalysisScreen({Key? key, this.initialSymbol = 'EURUSD'}) : super(key: key);

  @override
  State<AIAnalysisScreen> createState() => _AIAnalysisScreenState();
}

class _AIAnalysisScreenState extends State<AIAnalysisScreen> {
  late String _selectedSymbol;
  String _selectedTimeframe = '15m';
  String _selectedSession = 'london';
  final TextEditingController _customInstructionsCtrl = TextEditingController();

  bool _isEvaluating = false;
  AIAnalysisRecord? _analysisResult;
  String? _errorMessage;

  final List<String> _symbols = [
    'XAUUSD', 'XAGUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCHF', 'USDCAD'
  ];

  final List<String> _timeframes = ['1m', '5m', '15m', '1h', '4h', '1d'];
  final List<String> _sessions = ['asian', 'london', 'new_york'];

  @override
  void initState() {
    super.initState();
    _selectedSymbol = widget.initialSymbol;
  }

  Future<void> _runAnalysis() async {
    setState(() {
      _isEvaluating = true;
      _errorMessage = null;
    });

    try {
      final custom = _customInstructionsCtrl.text.trim();
      final record = await ApiService.evaluateMarket(
        symbol: _selectedSymbol,
        timeframe: _selectedTimeframe,
        sessionName: _selectedSession,
        customInstructions: custom.isNotEmpty ? custom : null,
      );

      setState(() {
        _analysisResult = record;
        _isEvaluating = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString().replaceAll('Exception: ', '');
        _isEvaluating = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('AI Market Evaluation Engine'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          _buildControlPanel(),
          const SizedBox(height: 16),
          if (_isEvaluating)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 40),
              child: Center(
                child: Column(
                  children: [
                    CircularProgressIndicator(color: AppTheme.primaryLight),
                    SizedBox(height: 16),
                    Text(
                      'Assembling market context & evaluating session instructions...',
                      style: TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                    ),
                  ],
                ),
              ),
            )
          else if (_errorMessage != null)
            _buildErrorCard()
          else if (_analysisResult != null)
            _buildAnalysisOutput(_analysisResult!)
          else
            _buildEmptyState(),
        ],
      ),
    );
  }

  Widget _buildControlPanel() {
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
          const Text(
            'MARKET PARAMETERS',
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
                flex: 2,
                child: _buildDropdown(
                  label: 'Symbol',
                  value: _selectedSymbol,
                  items: _symbols,
                  onChanged: (v) => setState(() => _selectedSymbol = v!),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                flex: 1,
                child: _buildDropdown(
                  label: 'TF',
                  value: _selectedTimeframe,
                  items: _timeframes,
                  onChanged: (v) => setState(() => _selectedTimeframe = v!),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                flex: 2,
                child: _buildDropdown(
                  label: 'Session',
                  value: _selectedSession,
                  items: _sessions,
                  onChanged: (v) => setState(() => _selectedSession = v!),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          TextField(
            controller: _customInstructionsCtrl,
            maxLines: 2,
            style: const TextStyle(fontSize: 13),
            decoration: InputDecoration(
              hintText: 'Optional custom instructions override (leave blank to use active PostgreSQL instructions)',
              hintStyle: const TextStyle(color: AppTheme.textMuted, fontSize: 12),
              filled: true,
              fillColor: AppTheme.surfaceLight,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: const BorderSide(color: AppTheme.border),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: const BorderSide(color: AppTheme.border),
              ),
            ),
          ),
          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity,
            height: 46,
            child: ElevatedButton.icon(
              onPressed: _isEvaluating ? null : _runAnalysis,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              icon: const Icon(Icons.psychology_rounded, size: 20),
              label: const Text(
                'Evaluate User Instructions',
                style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDropdown({
    required String label,
    required String value,
    required List<String> items,
    required ValueChanged<String?> onChanged,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 2),
      decoration: BoxDecoration(
        color: AppTheme.surfaceLight,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppTheme.border),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: value,
          isExpanded: true,
          icon: const Icon(Icons.arrow_drop_down, color: AppTheme.textSecondary),
          dropdownColor: AppTheme.surfaceLight,
          items: items.map((i) => DropdownMenuItem(value: i, child: Text(i, style: const TextStyle(fontSize: 13)))).toList(),
          onChanged: onChanged,
        ),
      ),
    );
  }

  Widget _buildAnalysisOutput(AIAnalysisRecord record) {
    final stateColor = AppTheme.getStateColor(record.state);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // State Banner Card
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: stateColor.withOpacity(0.12),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: stateColor.withOpacity(0.5), width: 1.5),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: stateColor,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      record.state,
                      style: const TextStyle(
                        color: Colors.black,
                        fontWeight: FontWeight.w900,
                        fontSize: 13,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      '${record.symbol} • ${record.timeframe} • ${record.sessionName.toUpperCase()}',
                      textAlign: TextAlign.right,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary, fontWeight: FontWeight.w600),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                record.summary,
                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, height: 1.4),
              ),
              if (record.biasValidation != null || record.setupSnapshot != null) ...[
                const SizedBox(height: 10),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    if (record.biasValidation != null)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: Colors.black26,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          'Bias: ${record.biasValidation!.bias} (${(record.biasValidation!.confidence * 100).toStringAsFixed(0)}%)',
                          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
                        ),
                      ),
                    if (record.setupSnapshot?.profileState != null)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: Colors.black26,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          '7H Profile: ${record.setupSnapshot!.profileState}',
                          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
                        ),
                      ),
                  ],
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 16),

        // Ambiguities Alert if any
        if (record.ambiguitiesDetected.isNotEmpty) ...[
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.amber.withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.amber.withOpacity(0.4)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.warning_amber_rounded, color: Colors.amber, size: 20),
                    SizedBox(width: 8),
                    Text(
                      'INSTRUCTION AMBIGUITIES DETECTED',
                      style: TextStyle(color: Colors.amber, fontWeight: FontWeight.w800, fontSize: 12),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                ...record.ambiguitiesDetected.map((a) => Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text(
                    '• "${a.textSnippet}": ${a.reason} Suggestion: ${a.suggestion ?? ""}',
                    style: const TextStyle(fontSize: 12, color: AppTheme.textPrimary),
                  ),
                )),
              ],
            ),
          ),
          const SizedBox(height: 16),
        ],

        // Condition Breakdown List
        const Text(
          'INSTRUCTION CONDITION BREAKDOWN',
          style: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w700,
            color: AppTheme.textMuted,
            letterSpacing: 1.1,
          ),
        ),
        const SizedBox(height: 10),
        ...record.conditionBreakdown.map((c) => _buildConditionItem(c)),

        const SizedBox(height: 16),
        // Traceability Footer
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppTheme.surface,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: AppTheme.border),
          ),
          child: Row(
            children: [
              const Icon(Icons.fingerprint_rounded, size: 18, color: AppTheme.textMuted),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Traceability ID: #${record.id} • Model: ${record.modelVersion} • Instruction Ver: #${record.instructionVersionId ?? 1}',
                  style: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildConditionItem(ConditionStatusItem item) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: item.satisfied ? AppTheme.validSetup.withOpacity(0.4) : AppTheme.border,
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            item.satisfied ? Icons.check_circle_rounded : Icons.cancel_rounded,
            color: item.satisfied ? AppTheme.validSetup : AppTheme.invalidated,
            size: 20,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.condition,
                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                ),
                const SizedBox(height: 3),
                Text(
                  item.evidence,
                  style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: item.satisfied
                  ? AppTheme.validSetup.withOpacity(0.15)
                  : AppTheme.invalidated.withOpacity(0.15),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Text(
              item.satisfied ? 'SATISFIED' : 'NOT SATISFIED',
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w800,
                color: item.satisfied ? AppTheme.validSetup : AppTheme.invalidated,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorCard() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.invalidated.withOpacity(0.12),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.invalidated.withOpacity(0.4)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline_rounded, color: AppTheme.invalidated),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              _errorMessage!,
              style: const TextStyle(color: AppTheme.textPrimary, fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 40, horizontal: 20),
      child: const Center(
        child: Column(
          children: [
            Icon(Icons.search_rounded, size: 48, color: AppTheme.textMuted),
            SizedBox(height: 12),
            Text(
              'No active evaluation yet',
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
            ),
            SizedBox(height: 4),
            Text(
              'Select an instrument and timeframe above, then tap "Evaluate User Instructions".',
              textAlign: TextAlign.center,
              style: TextStyle(color: AppTheme.textSecondary, fontSize: 13),
            ),
          ],
        ),
      ),
    );
  }
}
