import 'package:flutter/material.dart';
import '../models/strategy_instruction.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class StrategyInstructionsScreen extends StatefulWidget {
  const StrategyInstructionsScreen({Key? key}) : super(key: key);

  @override
  State<StrategyInstructionsScreen> createState() => _StrategyInstructionsScreenState();
}

class _StrategyInstructionsScreenState extends State<StrategyInstructionsScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  StrategySessionsConfig? _config;
  bool _isLoading = true;
  String? _errorMessage;

  final Map<String, TextEditingController> _controllers = {
    'asian': TextEditingController(),
    'london': TextEditingController(),
    'new_york': TextEditingController(),
  };

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _loadConfig();
  }

  Future<void> _loadConfig() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final config = await ApiService.getStrategySessions();
      setState(() {
        _config = config;
        _controllers['asian']!.text = config.asian.instructions;
        _controllers['london']!.text = config.london.instructions;
        _controllers['new_york']!.text = config.newYork.instructions;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _saveCurrentSession(String sessionName) async {
    final text = _controllers[sessionName]!.text.trim();
    if (text.isEmpty) return;

    final summaryCtrl = TextEditingController(text: 'Updated $sessionName instructions');

    final bool? confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.surface,
        title: Text('Save New $sessionName Version'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Every update increments the version in PostgreSQL and preserves a permanent audit trail.',
              style: TextStyle(fontSize: 12, color: AppTheme.textSecondary),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: summaryCtrl,
              decoration: const InputDecoration(
                labelText: 'Change Summary',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primary),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Save & Increment Version'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await ApiService.updateSessionStrategy(
          sessionName: sessionName,
          instructions: text,
          changeSummary: summaryCtrl.text.trim(),
        );
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: AppTheme.validSetup,
            content: Text('Successfully created new $sessionName instruction version!'),
          ),
        );
        await _loadConfig();
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: AppTheme.invalidated,
            content: Text('Failed to save: $e'),
          ),
        );
      }
    }
  }

  Future<void> _showHistory(String sessionName) async {
    showModalBottomSheet(
      context: context,
      backgroundColor: AppTheme.surface,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return DraggableScrollableSheet(
          initialChildSize: 0.65,
          maxChildSize: 0.9,
          minChildSize: 0.4,
          expand: false,
          builder: (_, scrollController) {
            return FutureBuilder<List<InstructionVersionItem>>(
              future: ApiService.getSessionHistory(sessionName),
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator(color: AppTheme.primaryLight));
                }
                if (snapshot.hasError) {
                  return Center(child: Text('Error: ${snapshot.error}'));
                }
                final versions = snapshot.data ?? [];

                return ListView(
                  controller: scrollController,
                  padding: const EdgeInsets.all(16),
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          '${sessionName.toUpperCase()} VERSION AUDIT LOG',
                          style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, letterSpacing: 0.5),
                        ),
                        IconButton(
                          icon: const Icon(Icons.close),
                          onPressed: () => Navigator.pop(ctx),
                        ),
                      ],
                    ),
                    const Divider(),
                    ...versions.map((v) => Container(
                          margin: const EdgeInsets.only(bottom: 10),
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: AppTheme.surfaceLight,
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(color: AppTheme.border),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                    decoration: BoxDecoration(
                                      color: AppTheme.primary.withOpacity(0.2),
                                      borderRadius: BorderRadius.circular(6),
                                    ),
                                    child: Text(
                                      'Version #${v.version}',
                                      style: const TextStyle(
                                        color: AppTheme.primaryLight,
                                        fontWeight: FontWeight.w800,
                                        fontSize: 12,
                                      ),
                                    ),
                                  ),
                                  Text(
                                    v.createdAt.split('T').first,
                                    style: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 6),
                              Text(
                                v.promptContent,
                                maxLines: 3,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(fontSize: 13, height: 1.3),
                              ),
                              if (v.changeSummary != null) ...[
                                const SizedBox(height: 4),
                                Text(
                                  'Note: ${v.changeSummary}',
                                  style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary, fontStyle: FontStyle.italic),
                                ),
                              ],
                              const SizedBox(height: 8),
                              Align(
                                alignment: Alignment.centerRight,
                                child: TextButton.icon(
                                  style: TextButton.styleFrom(
                                    foregroundColor: Colors.amberAccent,
                                  ),
                                  icon: const Icon(Icons.history_rounded, size: 16),
                                  label: const Text('Rollback to this version', style: TextStyle(fontSize: 12)),
                                  onPressed: () async {
                                    Navigator.pop(ctx);
                                    await _rollback(sessionName, v.version);
                                  },
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
      },
    );
  }

  Future<void> _rollback(String sessionName, int targetVersion) async {
    try {
      await ApiService.rollbackSessionStrategy(
        sessionName: sessionName,
        targetVersion: targetVersion,
      );
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: AppTheme.validSetup,
          content: Text('Successfully rolled back $sessionName to version $targetVersion!'),
        ),
      );
      await _loadConfig();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(backgroundColor: AppTheme.invalidated, content: Text('Rollback failed: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Strategy Instruction Engine'),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: AppTheme.primaryLight,
          labelColor: AppTheme.primaryLight,
          unselectedLabelColor: AppTheme.textMuted,
          tabs: const [
            Tab(text: 'Asian Session'),
            Tab(text: 'London Session'),
            Tab(text: 'New York'),
          ],
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppTheme.primaryLight))
          : TabBarView(
              controller: _tabController,
              children: [
                _buildSessionEditor('asian', _config?.asian),
                _buildSessionEditor('london', _config?.london),
                _buildSessionEditor('new_york', _config?.newYork),
              ],
            ),
    );
  }

  Widget _buildSessionEditor(String sessionName, SessionConfigItem? item) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Status & Version Banner
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: AppTheme.surface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppTheme.border),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  const Icon(Icons.verified_rounded, color: AppTheme.primaryLight, size: 20),
                  const SizedBox(width: 8),
                  Text(
                    'Active Version: #${item?.version ?? 1}',
                    style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                  ),
                ],
              ),
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppTheme.textPrimary,
                  side: const BorderSide(color: AppTheme.border),
                ),
                icon: const Icon(Icons.history_rounded, size: 16),
                label: const Text('Version History', style: TextStyle(fontSize: 12)),
                onPressed: () => _showHistory(sessionName),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        const Text(
          'NATURAL LANGUAGE STRATEGY INSTRUCTIONS',
          style: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w700,
            color: AppTheme.textMuted,
            letterSpacing: 1.1,
          ),
        ),
        const SizedBox(height: 6),
        const Text(
          'Define rules for market structure, liquidity sweeps, session levels, or indicators. The AI evaluates these dynamically without hardcoded assumptions.',
          style: TextStyle(fontSize: 12, color: AppTheme.textSecondary, height: 1.3),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _controllers[sessionName],
          maxLines: 8,
          style: const TextStyle(fontSize: 13, height: 1.4),
          decoration: InputDecoration(
            hintText: 'Enter your natural language rules for $sessionName session...',
            filled: true,
            fillColor: AppTheme.surface,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: const BorderSide(color: AppTheme.border),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: const BorderSide(color: AppTheme.border),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: const BorderSide(color: AppTheme.primaryLight),
            ),
          ),
        ),
        const SizedBox(height: 16),
        SizedBox(
          height: 48,
          child: ElevatedButton.icon(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primary,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            icon: const Icon(Icons.save_rounded, size: 20),
            label: const Text(
              'Save New Instruction Version',
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
            ),
            onPressed: () => _saveCurrentSession(sessionName),
          ),
        ),
      ],
    );
  }
}
