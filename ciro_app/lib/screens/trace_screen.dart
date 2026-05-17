import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../theme.dart';
import 'results_screen.dart';

class TraceScreen extends StatefulWidget {
  const TraceScreen({super.key, required this.analysisFuture});
  final Future<Map<String, dynamic>> analysisFuture;

  @override
  State<TraceScreen> createState() => _TraceScreenState();
}

class _TraceScreenState extends State<TraceScreen> {
  int _currentStep = -1;
  bool _analysisComplete = false;
  Map<String, dynamic>? _result;
  String? _error;
  double _progress = 0.0;
  final List<_LogEntry> _logs = [];
  late final String _crisisId;

  final List<_Step> _steps = const [
    _Step(Icons.bolt_outlined, 'Initializing response system', 'Boot'),
    _Step(Icons.sensors, 'Receiving multi-source signals', 'Ingest'),
    _Step(Icons.location_on_outlined, 'Extracting location & event type', 'Locate'),
    _Step(Icons.warning_amber_rounded, 'Running crisis detection engine', 'Detect'),
    _Step(Icons.analytics_outlined, 'Calculating severity & confidence', 'Score'),
    _Step(Icons.fork_right_rounded, 'Generating coordinated response plan', 'Plan'),
    _Step(Icons.play_circle_outline, 'Simulating action execution', 'Execute'),
    _Step(Icons.check_circle_outline, 'Response protocol complete', 'Done'),
  ];

  @override
  void initState() {
    super.initState();
    _crisisId =
        'CIRO-${DateTime.now().millisecondsSinceEpoch.toString().substring(7)}';
    _runPipeline();
  }

  String _ts() {
    final n = DateTime.now();
    return '${n.hour.toString().padLeft(2, '0')}:'
        '${n.minute.toString().padLeft(2, '0')}:'
        '${n.second.toString().padLeft(2, '0')}';
  }

  Future<void> _runPipeline() async {
    final apiFuture = widget.analysisFuture.then((res) {
      if (mounted) {
        setState(() {
          _result = res;
          _analysisComplete = true;
        });
      }
    }).catchError((e) {
      if (mounted) setState(() => _error = e.toString());
    });

    for (int i = 0; i < _steps.length; i++) {
      await Future.delayed(const Duration(milliseconds: 700));
      if (!mounted) return;
      setState(() {
        _currentStep = i;
        _progress = (i + 1) / _steps.length;
        _logs.add(_LogEntry(_ts(), _steps[i].tag, _steps[i].label));
      });
    }
    await apiFuture;
    await Future.delayed(const Duration(milliseconds: 400));
    if (!mounted) return;

    if (_error != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_error!, style: CiroType.bodyTight(Colors.white)),
          backgroundColor: CiroColors.sevHigh,
        ),
      );
      Navigator.pop(context);
    } else if (_result != null) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => ResultsScreen(data: _result!)),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: CiroColors.canvas,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, size: 18),
          onPressed: () => Navigator.maybePop(context),
        ),
        title: Text('Analysis pipeline', style: CiroType.h2(CiroColors.inkStrong)),
      ),
      body: SafeArea(
        top: false,
        child: Column(
          children: [
            _topMeta(),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(999),
                child: LinearProgressIndicator(
                  value: _progress,
                  minHeight: 6,
                  backgroundColor: CiroColors.surfaceAlt,
                  valueColor:
                      const AlwaysStoppedAnimation<Color>(CiroColors.brand),
                ),
              ),
            ),
            const SizedBox(height: 20),
            Expanded(
              child: ListView.builder(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
                itemCount: _steps.length,
                itemBuilder: (context, i) {
                  final isDone = i < _currentStep ||
                      (i == _steps.length - 1 && _analysisComplete);
                  final isActive = i == _currentStep && !isDone;
                  final isLast = i == _steps.length - 1;
                  return _timelineRow(i, isDone: isDone, isActive: isActive, isLast: isLast)
                      .animate()
                      .fadeIn(delay: Duration(milliseconds: i * 60), duration: 250.ms)
                      .slideY(begin: 0.1);
                },
              ),
            ),
            _logPanel(),
          ],
        ),
      ),
    );
  }

  Widget _topMeta() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('CRISIS ID',
                  style: CiroType.eyebrow(CiroColors.inkSubtle)),
              const SizedBox(height: 2),
              Text(
                _crisisId,
                style: CiroType.mono(CiroColors.inkStrong,
                    size: 13.5, w: FontWeight.w700),
              ),
            ],
          ),
          const Spacer(),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('PROGRESS',
                  style: CiroType.eyebrow(CiroColors.inkSubtle)),
              const SizedBox(height: 2),
              Text(
                '${(_progress * 100).toInt()}%',
                style: CiroType.mono(CiroColors.brand,
                    size: 13.5, w: FontWeight.w700),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _timelineRow(int i,
      {required bool isDone, required bool isActive, required bool isLast}) {
    final color = isDone
        ? CiroColors.sevLow
        : isActive
            ? CiroColors.brand
            : CiroColors.inkSubtle;
    final bg = isDone
        ? CiroColors.sevLowSoft
        : isActive
            ? CiroColors.brandSoft
            : CiroColors.surfaceAlt;

    return SizedBox(
      child: IntrinsicHeight(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // dot + connector column
            SizedBox(
              width: 28,
              child: Column(
                children: [
                  const SizedBox(height: 4),
                  Container(
                    width: 24,
                    height: 24,
                    decoration: BoxDecoration(
                      color: bg,
                      shape: BoxShape.circle,
                      border: Border.all(color: color.withValues(alpha: 0.5), width: 1.2),
                    ),
                    child: isDone
                        ? const Icon(Icons.check_rounded, size: 14, color: CiroColors.sevLow)
                        : isActive
                            ? Container(
                                margin: const EdgeInsets.all(5),
                                decoration: const BoxDecoration(
                                  color: CiroColors.brand,
                                  shape: BoxShape.circle,
                                ),
                              )
                                .animate(onPlay: (c) => c.repeat())
                                .scaleXY(begin: 0.5, end: 1, duration: 700.ms)
                                .then()
                                .scaleXY(begin: 1, end: 0.5, duration: 700.ms)
                            : null,
                  ),
                  if (!isLast)
                    Expanded(
                      child: Container(
                        width: 1.5,
                        margin: const EdgeInsets.symmetric(vertical: 4),
                        color: isDone
                            ? CiroColors.sevLow.withValues(alpha: 0.4)
                            : CiroColors.hairline,
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.only(bottom: 18),
                child: Container(
                  padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
                  decoration: BoxDecoration(
                    color: isActive ? CiroColors.brandSoft : CiroColors.surface,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: isActive
                          ? CiroColors.brand.withValues(alpha: 0.35)
                          : CiroColors.hairline,
                    ),
                    boxShadow: isActive ? CiroShadow.pop : CiroShadow.card,
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Container(
                        width: 32,
                        height: 32,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          color: bg,
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Icon(_steps[i].icon, size: 17, color: color),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Row(
                              children: [
                                Text(
                                  _steps[i].tag.toUpperCase(),
                                  style: CiroType.mono(color,
                                      size: 10, w: FontWeight.w700),
                                ),
                                const SizedBox(width: 8),
                                if (isActive)
                                  Text(
                                    'PROCESSING…',
                                    style: CiroType.mono(CiroColors.brand,
                                        size: 9.5, w: FontWeight.w700),
                                  )
                                      .animate(onPlay: (c) => c.repeat())
                                      .fadeOut(duration: 550.ms)
                                      .then()
                                      .fadeIn(duration: 550.ms),
                              ],
                            ),
                            const SizedBox(height: 2),
                            Text(
                              _steps[i].label,
                              style: CiroType.body(CiroColors.inkStrong)
                                  .copyWith(fontSize: 13.5),
                            ),
                          ],
                        ),
                      ),
                      if (isDone)
                        Padding(
                          padding: const EdgeInsets.only(left: 8),
                          child: Icon(Icons.check_circle_rounded,
                              color: CiroColors.sevLow, size: 18),
                        ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _logPanel() {
    final visible = _logs.reversed.take(3).toList();
    return Container(
      margin: const EdgeInsets.fromLTRB(20, 0, 20, 20),
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      decoration: BoxDecoration(
        color: const Color(0xFF1B2228),
        borderRadius: BorderRadius.circular(14),
        boxShadow: CiroShadow.card,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: const BoxDecoration(
                  color: Color(0xFF6BE3B0),
                  shape: BoxShape.circle,
                ),
              )
                  .animate(onPlay: (c) => c.repeat())
                  .fadeOut(duration: 800.ms)
                  .then()
                  .fadeIn(duration: 800.ms),
              const SizedBox(width: 8),
              Text(
                'SYSTEM LOG',
                style: CiroType.mono(const Color(0xFF6BE3B0),
                    size: 10.5, w: FontWeight.w700),
              ),
              const Spacer(),
              Text(
                '${_logs.length} ENTRIES',
                style: CiroType.mono(const Color(0xFF9FB0B8), size: 9.5),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ...visible.map((e) => Padding(
                padding: const EdgeInsets.only(bottom: 3),
                child: Text(
                  '${e.time}  ${e.tag.padRight(7)}  ${e.message}',
                  style: CiroType.mono(const Color(0xFFE6F0E9),
                      size: 10.5, w: FontWeight.w500),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              )),
        ],
      ),
    );
  }
}

class _Step {
  const _Step(this.icon, this.label, this.tag);
  final IconData icon;
  final String label;
  final String tag;
}

class _LogEntry {
  _LogEntry(this.time, this.tag, this.message);
  final String time;
  final String tag;
  final String message;
}
