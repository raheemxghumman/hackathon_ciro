import 'package:flutter/material.dart';

import '../services/history_service.dart';
import '../theme.dart';
import 'results_screen.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<HistoryEntry>? _entries;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final list = await HistoryService.load();
    if (!mounted) return;
    setState(() => _entries = list);
  }

  Color _sevColor(String s) {
    switch (s) {
      case 'Low':
        return CiroColors.sevLow;
      case 'Medium':
        return CiroColors.sevMed;
      case 'High':
        return CiroColors.sevHigh;
      case 'Critical':
        return CiroColors.sevCritical;
      default:
        return CiroColors.inkSubtle;
    }
  }

  Color _sevSoft(String s) {
    switch (s) {
      case 'Low':
        return CiroColors.sevLowSoft;
      case 'Medium':
        return CiroColors.sevMedSoft;
      case 'High':
        return CiroColors.sevHighSoft;
      case 'Critical':
        return CiroColors.sevCriticalSoft;
      default:
        return CiroColors.surfaceAlt;
    }
  }

  String _relative(DateTime t) {
    final diff = DateTime.now().difference(t);
    if (diff.inMinutes < 1) return 'just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    if (diff.inDays < 7) return '${diff.inDays}d ago';
    return '${t.year}-${t.month.toString().padLeft(2, '0')}-${t.day.toString().padLeft(2, '0')}';
  }

  Future<void> _confirmClear() async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: CiroColors.surface,
        title: Text('Clear all history?', style: CiroType.h2(CiroColors.inkStrong)),
        content: Text(
          'This will remove every archived incident report from this device. The action cannot be undone.',
          style: CiroType.bodyTight(CiroColors.inkBody),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: Text('Cancel', style: CiroType.h3(CiroColors.inkBody).copyWith(fontSize: 14)),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: CiroColors.sevHigh),
            onPressed: () => Navigator.pop(ctx, true),
            child: Text('Clear all',
                style: CiroType.h3(Colors.white).copyWith(fontSize: 14)),
          ),
        ],
      ),
    );
    if (yes == true) {
      await HistoryService.clear();
      await _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    final entries = _entries;
    return Scaffold(
      backgroundColor: CiroColors.canvas,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, size: 18),
          onPressed: () => Navigator.maybePop(context),
        ),
        title: Text('History', style: CiroType.h2(CiroColors.inkStrong)),
        actions: [
          if (entries != null && entries.isNotEmpty)
            IconButton(
              tooltip: 'Clear all',
              icon: const Icon(Icons.delete_outline_rounded, size: 20),
              onPressed: _confirmClear,
            ),
        ],
      ),
      body: SafeArea(
        top: false,
        child: entries == null
            ? const Center(child: CircularProgressIndicator(color: CiroColors.brand))
            : entries.isEmpty
                ? _empty()
                : ListView.separated(
                    padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
                    itemCount: entries.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 12),
                    itemBuilder: (_, i) => _entryCard(entries[i]),
                  ),
      ),
    );
  }

  Widget _empty() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 64,
              height: 64,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: CiroColors.surfaceAlt,
                borderRadius: BorderRadius.circular(20),
              ),
              child: const Icon(Icons.inbox_outlined, color: CiroColors.inkSubtle, size: 28),
            ),
            const SizedBox(height: 16),
            Text(
              'No reports yet',
              style: CiroType.h2(CiroColors.inkStrong),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 6),
            Text(
              'Archived incident reports will appear here after you tap “Share full report”.',
              style: CiroType.bodyTight(CiroColors.inkMuted),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _entryCard(HistoryEntry e) {
    final sev = _sevColor(e.severity);
    return InkWell(
      onTap: () {
        Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => ResultsScreen(data: e.data)),
        );
      },
      borderRadius: BorderRadius.circular(16),
      child: Container(
        decoration: ciroCard(),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Container(width: 4, color: sev),
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(14, 13, 14, 13),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                color: _sevSoft(e.severity),
                                borderRadius: BorderRadius.circular(999),
                                border: Border.all(
                                    color: sev.withValues(alpha: 0.35)),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Container(
                                    width: 6,
                                    height: 6,
                                    decoration: BoxDecoration(
                                        color: sev, shape: BoxShape.circle),
                                  ),
                                  const SizedBox(width: 5),
                                  Text(
                                    e.severity.toUpperCase(),
                                    style: CiroType.mono(sev,
                                        size: 10, w: FontWeight.w700),
                                  ),
                                ],
                              ),
                            ),
                            const Spacer(),
                            Text(_relative(e.savedAt),
                                style: CiroType.mono(CiroColors.inkSubtle,
                                    size: 10.5)),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(
                          e.crisisType,
                          style: CiroType.h3(CiroColors.inkStrong)
                              .copyWith(fontSize: 15),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            const Icon(Icons.location_on_rounded,
                                size: 13, color: CiroColors.inkMuted),
                            const SizedBox(width: 4),
                            Expanded(
                              child: Text(
                                e.location,
                                style: CiroType.small(CiroColors.inkMuted),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            const SizedBox(width: 8),
                            Text('${e.confidence}% conf',
                                style: CiroType.mono(CiroColors.inkSubtle,
                                    size: 10.5)),
                            const SizedBox(width: 6),
                            const Icon(Icons.chevron_right_rounded,
                                color: CiroColors.inkSubtle, size: 18),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
