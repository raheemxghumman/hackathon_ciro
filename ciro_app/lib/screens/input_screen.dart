import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../services/api_service.dart';
import '../services/history_service.dart';
import '../theme.dart';
import 'history_screen.dart';
import 'results_screen.dart';
import 'trace_screen.dart';

class InputScreen extends StatefulWidget {
  const InputScreen({super.key});

  @override
  State<InputScreen> createState() => _InputScreenState();
}

class _InputScreenState extends State<InputScreen> {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focus = FocusNode();
  bool _isLoading = false;
  Map<String, dynamic> _liveSignals = {};
  Timer? _signalTimer;
  List<HistoryEntry> _history = [];

  @override
  void initState() {
    super.initState();
    _fetchSignals();
    _loadHistory();
    _signalTimer = Timer.periodic(const Duration(seconds: 30), (_) => _fetchSignals());
  }

  Future<void> _loadHistory() async {
    final list = await HistoryService.load();
    if (!mounted) return;
    setState(() => _history = list);
  }

  Future<void> _openHistory() async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const HistoryScreen()),
    );
    if (mounted) _loadHistory();
  }

  String _relativeTime(DateTime t) {
    final diff = DateTime.now().difference(t);
    if (diff.inMinutes < 1) return 'just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m';
    if (diff.inHours < 24) return '${diff.inHours}h';
    if (diff.inDays < 7) return '${diff.inDays}d';
    return '${t.month}/${t.day}';
  }

  @override
  void dispose() {
    _signalTimer?.cancel();
    _controller.dispose();
    _focus.dispose();
    super.dispose();
  }

  Future<void> _fetchSignals() async {
    final result = await ApiService.getLiveSignals();
    if (!mounted) return;
    setState(() => _liveSignals = result);
  }

  String _weatherEmoji(String c) {
    final s = c.toLowerCase();
    if (s.contains('thunder')) return '⛈';
    if (s.contains('rain') || s.contains('shower') || s.contains('drizzle')) return '🌧';
    if (s.contains('snow')) return '❄';
    if (s.contains('dust') || s.contains('sand')) return '🌪';
    if (s.contains('fog') || s.contains('mist')) return '🌫';
    if (s.contains('sunny') || s.contains('clear')) return '☀';
    if (s.contains('cloud') || s.contains('overcast')) return '⛅';
    return '🌤';
  }

  Color _alertColor(String level) {
    switch (level) {
      case 'Critical':
        return CiroColors.sevCritical;
      case 'High':
        return CiroColors.sevHigh;
      case 'Medium':
        return CiroColors.sevMed;
      case 'Low':
        return CiroColors.sevLow;
      default:
        return CiroColors.inkSubtle;
    }
  }

  Color _congestionColor(int pct) {
    if (pct >= 75) return CiroColors.sevHigh;
    if (pct >= 50) return CiroColors.sevMed;
    return CiroColors.sevLow;
  }

  void _setScenario(String text) {
    setState(() {
      _controller.text = text;
      _controller.selection = TextSelection.fromPosition(
        TextPosition(offset: _controller.text.length),
      );
    });
  }

  Future<void> _onAnalyze() async {
    final raw = _controller.text.trim();
    if (raw.isEmpty) {
      _focus.requestFocus();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Describe the crisis before transmitting.',
            style: CiroType.bodyTight(Colors.white),
          ),
          backgroundColor: CiroColors.sevHigh,
        ),
      );
      return;
    }
    setState(() => _isLoading = true);
    final future = ApiService.analyzeCrisis(raw);
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => TraceScreen(analysisFuture: future)),
    );
    if (mounted) setState(() => _isLoading = false);
  }

  @override
  Widget build(BuildContext context) {
    final weatherMap = (_liveSignals['weather'] is Map)
        ? Map<String, dynamic>.from(_liveSignals['weather'] as Map)
        : <String, dynamic>{};
    final trafficMap = (_liveSignals['traffic'] is Map)
        ? Map<String, dynamic>.from(_liveSignals['traffic'] as Map)
        : <String, dynamic>{};
    final quakeMap = (_liveSignals['earthquake'] is Map)
        ? Map<String, dynamic>.from(_liveSignals['earthquake'] as Map)
        : <String, dynamic>{};
    final weatherData = (weatherMap['data'] is Map)
        ? Map<String, dynamic>.from(weatherMap['data'] as Map)
        : <String, dynamic>{};
    final trafficData = (trafficMap['data'] is Map)
        ? Map<String, dynamic>.from(trafficMap['data'] as Map)
        : <String, dynamic>{};
    final quakeData = (quakeMap['data'] is Map)
        ? Map<String, dynamic>.from(quakeMap['data'] as Map)
        : <String, dynamic>{};

    final condition = (weatherData['condition'] as String?) ?? '—';
    final alert = (weatherData['alert_level'] as String?) ?? '';
    final temp = weatherData['temperature_c'];
    final congestion = (trafficData['congestion_level'] as String?) ?? '—';
    final pct = trafficData['congestion_percent'] is int
        ? trafficData['congestion_percent'] as int
        : (trafficData['congestion_percent'] is double
            ? (trafficData['congestion_percent'] as double).round()
            : 0);
    final trafficLive = (trafficMap['source'] as String?)?.contains('Live') == true
        || trafficData['is_real'] == true;
    final quakeCount = quakeData['event_count'] is int
        ? quakeData['event_count'] as int
        : 0;
    final quakeMag = quakeData['max_magnitude'];
    final quakeLive = quakeMap['is_real'] == true;

    return Scaffold(
      backgroundColor: CiroColors.canvas,
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            SliverToBoxAdapter(child: _header()),
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 28),
              sliver: SliverList(
                delegate: SliverChildListDelegate([
                  _liveSignalsPanel(
                    condition: condition,
                    alert: alert,
                    temp: temp,
                    congestion: congestion,
                    pct: pct,
                    trafficLive: trafficLive,
                    quakeCount: quakeCount,
                    quakeMag: quakeMag,
                    quakeLive: quakeLive,
                  ),
                  if (_history.isNotEmpty) ...[
                    const SizedBox(height: 20),
                    _recentIncidents(),
                  ],
                  const SizedBox(height: 20),
                  _inputCard(),
                  const SizedBox(height: 16),
                  _scenarioGrid(),
                  const SizedBox(height: 24),
                  _transmitButton(),
                  const SizedBox(height: 16),
                  _footerStats(),
                ]),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ---------- header ----------
  Widget _header() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 14, 20, 14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: CiroColors.brand,
              borderRadius: BorderRadius.circular(12),
              boxShadow: [
                BoxShadow(
                  color: CiroColors.brand.withValues(alpha: 0.25),
                  blurRadius: 14,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: const Icon(Icons.shield_moon_outlined, color: Colors.white, size: 22),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text('CIRO',
                    style: CiroType.h1(CiroColors.inkStrong)
                        .copyWith(fontSize: 19, letterSpacing: 0.2)),
                Text(
                  'Crisis Intelligence · Global',
                  style: CiroType.small(CiroColors.inkMuted),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: CiroColors.sevLowSoft,
              borderRadius: BorderRadius.circular(999),
              border: Border.all(color: CiroColors.sevLow.withValues(alpha: 0.35)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 7,
                  height: 7,
                  decoration: const BoxDecoration(
                    color: CiroColors.sevLow,
                    shape: BoxShape.circle,
                  ),
                )
                    .animate(onPlay: (c) => c.repeat())
                    .fadeOut(duration: 900.ms)
                    .then()
                    .fadeIn(duration: 900.ms),
                const SizedBox(width: 6),
                Text(
                  'OPERATIONAL',
                  style: CiroType.mono(CiroColors.sevLow, size: 10.5, w: FontWeight.w700),
                ),
              ],
            ),
          ),
          const SizedBox(width: 6),
          _headerIconButton(
            icon: Icons.history_rounded,
            badgeCount: _history.length,
            onTap: _openHistory,
          ),
        ],
      ),
    );
  }

  Widget _headerIconButton({
    required IconData icon,
    required VoidCallback onTap,
    int badgeCount = 0,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        width: 40,
        height: 40,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: CiroColors.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: CiroColors.hairline),
        ),
        child: Stack(
          clipBehavior: Clip.none,
          alignment: Alignment.center,
          children: [
            Icon(icon, size: 19, color: CiroColors.inkStrong),
            if (badgeCount > 0)
              Positioned(
                top: -4,
                right: -6,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                  decoration: BoxDecoration(
                    color: CiroColors.brand,
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(color: CiroColors.canvas, width: 1.5),
                  ),
                  child: Text(
                    badgeCount > 99 ? '99+' : '$badgeCount',
                    style: CiroType.mono(Colors.white, size: 9.5, w: FontWeight.w700),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  // ---------- signals ----------
  Widget _liveSignalsPanel({
    required String condition,
    required String alert,
    required dynamic temp,
    required String congestion,
    required int pct,
    required bool trafficLive,
    required int quakeCount,
    required dynamic quakeMag,
    required bool quakeLive,
  }) {
    final quakeValue = quakeCount > 0
        ? (quakeMag is num ? 'M${quakeMag.toStringAsFixed(1)}' : '$quakeCount nearby')
        : 'Stable';
    final quakeSub = quakeCount > 0
        ? '$quakeCount in 500km'
        : 'No recent quakes';
    final quakeAccent = quakeCount > 0 && quakeMag is num
        ? (quakeMag >= 5
            ? CiroColors.sevHigh
            : quakeMag >= 4
                ? CiroColors.sevMed
                : CiroColors.sevLow)
        : CiroColors.sevLow;

    return Container(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
      decoration: ciroCard(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.sensors_rounded, size: 16, color: CiroColors.brand),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'LIVE SIGNALS',
                  style: CiroType.eyebrow(CiroColors.inkStrong),
                ),
              ),
              if (trafficLive)
                Padding(
                  padding: const EdgeInsets.only(right: 6),
                  child: Pill(
                    text: 'LIVE',
                    color: CiroColors.sevLow,
                    background: CiroColors.sevLowSoft,
                    dot: true,
                    dense: true,
                  ),
                ),
              Text(
                'updates 30s',
                style: CiroType.mono(CiroColors.inkSubtle, size: 10.5),
              ),
            ],
          ),
          const SizedBox(height: 12),
          IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(
                  child: _signalTile(
                    icon: _weatherEmoji(condition),
                    label: 'WEATHER',
                    value: condition,
                    sub: temp is num ? '${temp.toStringAsFixed(0)}°C · $alert' : alert,
                    accent: _alertColor(alert),
                  ),
                ),
                const VerticalDivider(width: 1, color: CiroColors.hairlineSoft),
                Expanded(
                  child: _signalTile(
                    icon: '🚦',
                    label: 'TRAFFIC',
                    value: congestion,
                    sub: '$pct% blocked',
                    accent: _congestionColor(pct),
                  ),
                ),
                const VerticalDivider(width: 1, color: CiroColors.hairlineSoft),
                Expanded(
                  child: _signalTile(
                    icon: '🌐',
                    label: 'SEISMIC',
                    value: quakeValue,
                    sub: quakeSub,
                    accent: quakeAccent,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _signalTile({
    required String icon,
    required String label,
    required String value,
    required String sub,
    required Color accent,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Row(
            children: [
              Text(icon, style: const TextStyle(fontSize: 16)),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  label,
                  style: CiroType.eyebrow(CiroColors.inkSubtle),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            value,
            style: CiroType.h3(CiroColors.inkStrong).copyWith(
              fontSize: 14,
              height: 1.2,
            ),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 2),
          Text(
            sub,
            style: CiroType.mono(accent, size: 10, w: FontWeight.w600)
                .copyWith(height: 1.25),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  // ---------- recent incidents ----------
  Widget _recentIncidents() {
    final recent = _history.take(5).toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: SectionLabel('RECENT INCIDENTS',
                  color: CiroColors.inkStrong),
            ),
            InkWell(
              onTap: _openHistory,
              borderRadius: BorderRadius.circular(8),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      'View all',
                      style: CiroType.small(CiroColors.brand)
                          .copyWith(fontWeight: FontWeight.w600),
                    ),
                    const Icon(Icons.chevron_right_rounded,
                        color: CiroColors.brand, size: 16),
                  ],
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        SizedBox(
          height: 92,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            padding: EdgeInsets.zero,
            physics: const BouncingScrollPhysics(),
            itemCount: recent.length,
            separatorBuilder: (_, __) => const SizedBox(width: 10),
            itemBuilder: (_, i) => _historyTile(recent[i]),
          ),
        ),
      ],
    );
  }

  Widget _historyTile(HistoryEntry e) {
    final sev = _alertColor(e.severity);
    return InkWell(
      onTap: () async {
        await Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => ResultsScreen(data: e.data)),
        );
        if (mounted) _loadHistory();
      },
      borderRadius: BorderRadius.circular(14),
      child: Container(
        width: 220,
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
        decoration: BoxDecoration(
          color: CiroColors.surface,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: CiroColors.hairline),
          boxShadow: CiroShadow.card,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              children: [
                Container(
                  width: 7,
                  height: 7,
                  decoration: BoxDecoration(color: sev, shape: BoxShape.circle),
                ),
                const SizedBox(width: 6),
                Text(
                  e.severity.toUpperCase(),
                  style: CiroType.mono(sev, size: 9.5, w: FontWeight.w700),
                ),
                const Spacer(),
                Text(_relativeTime(e.savedAt),
                    style: CiroType.mono(CiroColors.inkSubtle, size: 9.5)),
              ],
            ),
            Text(
              e.crisisType,
              style: CiroType.h3(CiroColors.inkStrong).copyWith(fontSize: 13.5),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            Row(
              children: [
                const Icon(Icons.location_on_rounded,
                    size: 12, color: CiroColors.inkMuted),
                const SizedBox(width: 3),
                Expanded(
                  child: Text(
                    e.location,
                    style: CiroType.small(CiroColors.inkMuted).copyWith(fontSize: 11.5),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  // ---------- input ----------
  Widget _inputCard() {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
      decoration: ciroCard(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.report_outlined, size: 16, color: CiroColors.inkStrong),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'REPORT A SIGNAL',
                  style: CiroType.eyebrow(CiroColors.inkStrong),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: CiroColors.surfaceAlt,
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  'EN · UR · ROMAN',
                  style: CiroType.mono(CiroColors.inkMuted, size: 9.5, w: FontWeight.w700),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Container(
            decoration: BoxDecoration(
              color: CiroColors.surfaceMuted,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: CiroColors.hairline),
            ),
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
            child: TextField(
              controller: _controller,
              focusNode: _focus,
              maxLines: 6,
              minLines: 4,
              style: CiroType.body(CiroColors.inkStrong),
              cursorColor: CiroColors.brand,
              decoration: InputDecoration(
                isCollapsed: true,
                border: InputBorder.none,
                hintText:
                    'Describe what you’re seeing in any language.\nمثال: G-10 mein pani bhar gaya hai',
                hintStyle: CiroType.body(CiroColors.inkSubtle),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ---------- scenarios ----------
  Widget _scenarioGrid() {
    final items = [
      _ScenarioSpec(
        '🌊', 'Urban flood', 'G-10 area',
        CiroColors.dataInk,
        'G-10 mein pani bhar gaya hai, gaariyan phans gayi hain',
      ),
      _ScenarioSpec(
        '🚧', 'Road accident', 'Kashmir Hwy',
        CiroColors.sevHigh,
        'Major accident on Kashmir Highway near Golra Morr, road blocked',
      ),
      _ScenarioSpec(
        '🌡', 'Heatwave', 'I-8 sector',
        CiroColors.sevMed,
        'I-8 mein shadeed garmi ki wajah se loag behosh ho rahe hain',
      ),
      _ScenarioSpec(
        '⚡', 'Power line', 'F-6 sector',
        CiroColors.brand,
        'F-6 mein bijli ka khamba gir gaya hai, rasta band hai',
      ),
      _ScenarioSpec(
        '🌐', 'Earthquake', 'Tokyo, Japan',
        CiroColors.sevCritical,
        'Massive earthquake just hit Tokyo, buildings shaking, people running outside',
      ),
      _ScenarioSpec(
        '🏙', 'Global · Fire', 'Manhattan, NYC',
        CiroColors.sevHigh,
        'Major fire in a high-rise building on 5th Avenue Manhattan, smoke everywhere',
      ),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionLabel('QUICK SCENARIOS', color: CiroColors.inkSubtle),
        const SizedBox(height: 8),
        LayoutBuilder(builder: (context, c) {
          final w = (c.maxWidth - 12) / 2;
          return Wrap(
            spacing: 12,
            runSpacing: 12,
            children: items
                .map((s) => SizedBox(width: w, child: _scenarioTile(s)))
                .toList(),
          );
        }),
      ],
    );
  }

  Widget _scenarioTile(_ScenarioSpec s) {
    return InkWell(
      onTap: () => _setScenario(s.fill),
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.fromLTRB(12, 12, 12, 12),
        decoration: BoxDecoration(
          color: CiroColors.surface,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: CiroColors.hairline),
          boxShadow: CiroShadow.card,
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Container(
              width: 36,
              height: 36,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: s.accent.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(s.icon, style: const TextStyle(fontSize: 18)),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    s.title,
                    style: CiroType.h3(CiroColors.inkStrong).copyWith(fontSize: 14),
                    overflow: TextOverflow.ellipsis,
                  ),
                  Text(
                    s.sub,
                    style: CiroType.small(CiroColors.inkMuted),
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ---------- transmit ----------
  Widget _transmitButton() {
    return SizedBox(
      height: 56,
      child: Material(
        color: CiroColors.brand,
        elevation: 0,
        shadowColor: CiroColors.brand.withValues(alpha: 0.4),
        borderRadius: BorderRadius.circular(14),
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: _isLoading ? null : _onAnalyze,
          child: Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              boxShadow: [
                BoxShadow(
                  color: CiroColors.brand.withValues(alpha: 0.30),
                  blurRadius: 22,
                  offset: const Offset(0, 10),
                ),
              ],
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: _isLoading
                  ? [
                      const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          color: Colors.white,
                          strokeWidth: 2,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Text(
                        'Transmitting…',
                        style: CiroType.h3(Colors.white),
                      ),
                    ]
                  : [
                      const Icon(Icons.send_rounded, color: Colors.white, size: 18),
                      const SizedBox(width: 10),
                      Text(
                        'Transmit signal',
                        style: CiroType.h3(Colors.white),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.18),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          'GROQ',
                          style: CiroType.mono(Colors.white, size: 10, w: FontWeight.w700),
                        ),
                      ),
                    ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _footerStats() {
    return Column(
      children: [
        Center(
          child: Wrap(
            spacing: 8,
            runSpacing: 8,
            alignment: WrapAlignment.center,
            children: [
              _credChip(
                icon: Icons.auto_awesome_rounded,
                label: 'Antigravity',
                sub: 'orchestrated',
                color: const Color(0xFF6E59E0),
              ),
              _credChip(
                icon: Icons.alt_route_rounded,
                label: 'Google Maps',
                sub: 'live routing',
                color: const Color(0xFF1A73E8),
              ),
              _credChip(
                icon: Icons.cloud_outlined,
                label: 'WeatherAPI',
                sub: 'live signals',
                color: const Color(0xFFE8845E),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        Center(
          child: Wrap(
            spacing: 14,
            runSpacing: 6,
            alignment: WrapAlignment.center,
            children: [
              _foot('4 agents'),
              _dot(),
              _foot('Llama 3.3 70B'),
              _dot(),
              _foot('p50 6s'),
            ],
          ),
        ),
      ],
    );
  }

  Widget _credChip({
    required IconData icon,
    required String label,
    required String sub,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.fromLTRB(10, 7, 12, 7),
      decoration: BoxDecoration(
        color: CiroColors.surface,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.18)),
        boxShadow: CiroShadow.card,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 22,
            height: 22,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Icon(icon, size: 12, color: color),
          ),
          const SizedBox(width: 8),
          Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label,
                  style: CiroType.h3(CiroColors.inkStrong)
                      .copyWith(fontSize: 11.5)),
              Text(sub,
                  style: CiroType.mono(color, size: 9, w: FontWeight.w600)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _foot(String s) =>
      Text(s, style: CiroType.mono(CiroColors.inkSubtle, size: 10.5));

  Widget _dot() => Container(
        width: 3,
        height: 3,
        decoration: BoxDecoration(
          color: CiroColors.inkSubtle.withValues(alpha: 0.5),
          shape: BoxShape.circle,
        ),
      );
}

class _ScenarioSpec {
  _ScenarioSpec(this.icon, this.title, this.sub, this.accent, this.fill);
  final String icon;
  final String title;
  final String sub;
  final Color accent;
  final String fill;
}
