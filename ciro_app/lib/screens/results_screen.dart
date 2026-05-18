import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../services/history_service.dart';
import '../theme.dart';

class ResultsScreen extends StatefulWidget {
  const ResultsScreen({super.key, required this.data});
  final Map<String, dynamic> data;

  @override
  State<ResultsScreen> createState() => _ResultsScreenState();
}

class _ResultsScreenState extends State<ResultsScreen> {
  bool _archived = false;

  Map<String, dynamic> _asMap(dynamic v) {
    if (v is Map) return Map<String, dynamic>.from(v);
    return <String, dynamic>{};
  }

  Map<String, dynamic> get _ingestion => _asMap(widget.data['ingestion']);
  Map<String, dynamic> get _detection => _asMap(widget.data['detection']);
  Map<String, dynamic> get _plan => _asMap(widget.data['plan']);
  Map<String, dynamic> get _execution => _asMap(widget.data['execution']);
  Map<String, dynamic> get _signals => _asMap(widget.data['signals']);

  // Robust parsing — Dio returns Map<dynamic,dynamic> for nested JSON. The
  // .whereType<Map>() + Map.from coercion handles both shapes.
  List<Map<String, dynamic>> get _actions {
    final raw = _plan['actions'];
    if (raw is List) {
      return raw.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
    }
    return [];
  }

  List<String> get _impact {
    final raw = _detection['impact_analysis'];
    if (raw is List) return raw.map((e) => e.toString()).toList();
    return [];
  }

  List<Map<String, dynamic>> get _execLog {
    final raw = _execution['execution_log'];
    if (raw is List) {
      return raw.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
    }
    return [];
  }

  Map<String, dynamic> get _before => _asMap(_execution['before_state']);
  Map<String, dynamic> get _after => _asMap(_execution['after_state']);

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

  Color _priorityColor(String p) {
    switch (p) {
      case 'P1':
        return CiroColors.sevHigh;
      case 'P2':
        return CiroColors.sevMed;
      case 'P3':
        return CiroColors.sevLow;
      default:
        return CiroColors.inkSubtle;
    }
  }

  Color _priorityBg(String p) {
    switch (p) {
      case 'P1':
        return CiroColors.sevHighSoft;
      case 'P2':
        return CiroColors.sevMedSoft;
      case 'P3':
        return CiroColors.sevLowSoft;
      default:
        return CiroColors.surfaceAlt;
    }
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

  @override
  Widget build(BuildContext context) {
    final crisisType = (_detection['crisis_type'] as String?) ?? 'Unknown event';
    final severity = (_detection['severity'] as String?) ?? 'Unknown';
    final confidence = _detection['confidence_percent'] is int
        ? _detection['confidence_percent'] as int
        : 0;
    final location = (_ingestion['location'] as String?) ?? '—';

    return Scaffold(
      backgroundColor: CiroColors.canvas,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, size: 18),
          onPressed: () => Navigator.maybePop(context),
        ),
        title: Text('Incident report', style: CiroType.h2(CiroColors.inkStrong)),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Pill(
              text: 'RESOLVED',
              color: CiroColors.sevLow,
              background: CiroColors.sevLowSoft,
              dense: true,
              dot: true,
            ),
          ),
        ],
      ),
      body: SafeArea(
        top: false,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
          children: [
            _crisisHeader(crisisType, severity, confidence, location),
            const SizedBox(height: 16),
            if (_signals.isNotEmpty) ...[
              _signalsCard(),
              const SizedBox(height: 16),
            ],
            _actionsSection(),
            const SizedBox(height: 16),
            _metricsRow(),
            const SizedBox(height: 16),
            _executionLog(),
            const SizedBox(height: 16),
            _strategyCard(),
            const SizedBox(height: 20),
            _bottomActions(),
          ],
        ),
      ),
    );
  }

  // ============== HEADER ==============
  Widget _crisisHeader(String type, String severity, int confidence, String location) {
    final sev = _sevColor(severity);
    return Container(
      decoration: ciroCard(shadow: CiroShadow.pop),
      child: Stack(
        children: [
          Positioned(
            left: 0,
            top: 0,
            bottom: 0,
            child: Container(
              width: 4,
              decoration: BoxDecoration(
                color: sev,
                borderRadius:
                    const BorderRadius.only(topLeft: Radius.circular(16), bottomLeft: Radius.circular(16)),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 18, 18, 18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Pill(
                            text: severity.toUpperCase(),
                            color: sev,
                            background: _sevSoft(severity),
                            dot: true,
                          ),
                          const SizedBox(height: 10),
                          Text(
                            type,
                            style: CiroType.display(CiroColors.inkStrong),
                          ),
                          const SizedBox(height: 6),
                          Row(
                            children: [
                              const Icon(Icons.location_on_rounded,
                                  size: 15, color: CiroColors.inkMuted),
                              const SizedBox(width: 4),
                              Expanded(
                                child: Text(
                                  location,
                                  style: CiroType.body(CiroColors.inkBody),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 12),
                    _confidenceRing(confidence, sev),
                  ],
                ),
                if ((_detection['reasoning'] as String?)?.isNotEmpty == true) ...[
                  const SizedBox(height: 18),
                  Container(height: 1, color: CiroColors.hairlineSoft),
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      Icon(Icons.psychology_outlined,
                          size: 14, color: sev),
                      const SizedBox(width: 6),
                      Expanded(child: SectionLabel('AGENT REASONING')),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
                    decoration: BoxDecoration(
                      color: _sevSoft(severity).withValues(alpha: 0.45),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                          color: sev.withValues(alpha: 0.20)),
                    ),
                    child: Text(
                      _detection['reasoning'].toString(),
                      style: CiroType.bodyTight(CiroColors.inkBody),
                    ),
                  ),
                ],
                if (_impact.isNotEmpty) ...[
                  const SizedBox(height: 18),
                  Container(height: 1, color: CiroColors.hairlineSoft),
                  const SizedBox(height: 14),
                  SectionLabel('IMPACT ASSESSMENT'),
                  const SizedBox(height: 10),
                  ..._impact.map((s) => Padding(
                        padding: const EdgeInsets.only(bottom: 6),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              margin: const EdgeInsets.only(top: 7),
                              width: 6,
                              height: 6,
                              decoration:
                                  BoxDecoration(color: sev, shape: BoxShape.circle),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(s,
                                  style: CiroType.bodyTight(CiroColors.inkBody)),
                            ),
                          ],
                        ),
                      )),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _confidenceRing(int pct, Color sev) {
    final value = pct.clamp(0, 100) / 100;
    return SizedBox(
      width: 64,
      height: 64,
      child: Stack(
        alignment: Alignment.center,
        children: [
          SizedBox(
            width: 64,
            height: 64,
            child: CustomPaint(
              painter: _RingPainter(
                progress: value,
                color: sev,
                track: CiroColors.hairlineSoft,
                stroke: 5,
              ),
            ),
          ),
          Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('$pct%',
                  style: CiroType.h3(CiroColors.inkStrong)
                      .copyWith(fontSize: 15)),
              Text('CONF',
                  style: CiroType.mono(CiroColors.inkSubtle,
                      size: 8.5, w: FontWeight.w700)),
            ],
          ),
        ],
      ),
    );
  }

  // ============== SIGNALS ==============
  Widget _signalsCard() {
    final w = _asMap(_signals['weather']);
    final t = _asMap(_signals['traffic']);
    final q = _asMap(_signals['earthquake']);
    final wd = _asMap(w['data']);
    final td = _asMap(t['data']);
    final qd = _asMap(q['data']);

    final condition = (wd['condition'] as String?) ?? '—';
    final alert = (wd['alert_level'] as String?) ?? '';
    final temp = wd['temperature_c'];
    final congestion = (td['congestion_level'] as String?) ?? '—';
    final pct = td['congestion_percent'] is int
        ? td['congestion_percent'] as int
        : (td['congestion_percent'] is double
            ? (td['congestion_percent'] as double).round()
            : 0);
    final trafficLive = (t['source'] as String?)?.contains('Live') == true
        || td['is_real'] == true;
    final quakeCount = qd['event_count'] is int ? qd['event_count'] as int : 0;
    final quakeMag = qd['max_magnitude'];
    final live = (w['source'] as String?)?.contains('Live') == true || trafficLive;

    final quakeValue = quakeCount > 0
        ? (quakeMag is num
            ? 'M${quakeMag.toStringAsFixed(1)}'
            : '$quakeCount nearby')
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
              Icon(Icons.hub_outlined, size: 16, color: CiroColors.inkStrong),
              const SizedBox(width: 8),
              Expanded(
                child: Text('CORROBORATING SIGNALS',
                    style: CiroType.eyebrow(CiroColors.inkStrong)),
              ),
              if (live)
                Pill(
                  text: 'LIVE',
                  color: CiroColors.sevLow,
                  background: CiroColors.sevLowSoft,
                  dot: true,
                  dense: true,
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
                    main: condition,
                    sub: temp is num
                        ? '${temp.toStringAsFixed(0)}°C · $alert'
                        : alert,
                    accent: _sevColor(alert),
                  ),
                ),
                const VerticalDivider(width: 1, color: CiroColors.hairlineSoft),
                Expanded(
                  child: _signalTile(
                    icon: '🚦',
                    label: 'TRAFFIC',
                    main: congestion,
                    sub: '$pct% blocked',
                    accent: pct >= 75
                        ? CiroColors.sevHigh
                        : pct >= 50
                            ? CiroColors.sevMed
                            : CiroColors.sevLow,
                  ),
                ),
                const VerticalDivider(width: 1, color: CiroColors.hairlineSoft),
                Expanded(
                  child: _signalTile(
                    icon: '🌐',
                    label: 'SEISMIC',
                    main: quakeValue,
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
    required String main,
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
                child: Text(label,
                    style: CiroType.eyebrow(CiroColors.inkSubtle),
                    overflow: TextOverflow.ellipsis),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            main,
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

  // ============== ACTIONS ==============
  Widget _actionsSection() {
    final actions = _actions;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Expanded(
              child: SectionLabel('DISPATCHED ACTIONS',
                  color: CiroColors.inkStrong),
            ),
            Text(
              '${actions.length} total',
              style: CiroType.mono(CiroColors.inkMuted, size: 11),
            ),
          ],
        ),
        const SizedBox(height: 10),
        if (actions.isEmpty)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: ciroCard(),
            child: Text(
              'No actions were dispatched for this incident.',
              style: CiroType.bodyTight(CiroColors.inkMuted),
            ),
          )
        else
          ...actions.asMap().entries.map((e) => Padding(
                padding: EdgeInsets.only(bottom: e.key == actions.length - 1 ? 0 : 12),
                child: _actionCard(e.value, e.key),
              )),
      ],
    );
  }

  Widget _actionCard(Map<String, dynamic> a, int index) {
    final actionId = a['action_id']?.toString() ?? 'ACT-${(index + 1).toString().padLeft(3, '0')}';
    final type = (a['action_type']?.toString() ?? 'action')
        .replaceAll('_', ' ');
    final desc = a['description']?.toString() ?? '';
    final agency = a['responsible_agency']?.toString() ?? 'Unknown agency';
    final priority = a['priority']?.toString() ?? 'P2';
    final time = a['estimated_time_minutes']?.toString() ?? '—';
    final pc = _priorityColor(priority);

    return Container(
      decoration: ciroCard(),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: IntrinsicHeight(
          child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(width: 4, color: pc),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(14, 14, 14, 14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        Pill(
                          text: actionId,
                          color: pc,
                          background: _priorityBg(priority),
                          dense: true,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            _toTitle(type),
                            style: CiroType.h3(CiroColors.inkStrong)
                                .copyWith(fontSize: 14.5),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Pill(text: priority, color: pc, dense: true),
                      ],
                    ),
                    if (desc.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text(desc,
                          style: CiroType.bodyTight(CiroColors.inkBody)),
                    ],
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        _metaChip(Icons.business_outlined, agency),
                        _metaChip(Icons.timer_outlined, '$time min'),
                        Pill(
                          text: 'SIMULATED',
                          color: CiroColors.sevLow,
                          background: CiroColors.sevLowSoft,
                          icon: Icons.check_circle_rounded,
                          dense: true,
                        ),
                      ],
                    ),
                    if (_hasRoutes(a)) ...[
                      const SizedBox(height: 14),
                      _routePanel(a),
                    ],
                  ],
                ),
              ),
            ),
          ],
        ),
        ),
      ),
    );
  }

  Widget _staticMap(String url) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(10),
      child: AspectRatio(
        aspectRatio: 16 / 9,
        child: Image.network(
          url,
          fit: BoxFit.cover,
          loadingBuilder: (context, child, progress) {
            if (progress == null) return child;
            return Container(
              color: CiroColors.surface,
              alignment: Alignment.center,
              child: SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  valueColor: AlwaysStoppedAnimation(const Color(0xFF1A73E8)),
                ),
              ),
            );
          },
          errorBuilder: (_, __, ___) => Container(
            color: CiroColors.surface,
            alignment: Alignment.center,
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.map_outlined,
                      color: CiroColors.inkSubtle, size: 22),
                  const SizedBox(height: 6),
                  Text('Map preview unavailable',
                      style: CiroType.small(CiroColors.inkMuted)),
                  const SizedBox(height: 2),
                  Text('(enable Static Maps API in Google Cloud)',
                      style: CiroType.mono(CiroColors.inkSubtle,
                          size: 9.5, w: FontWeight.w500),
                      textAlign: TextAlign.center),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  bool _hasRoutes(Map<String, dynamic> a) {
    final rd = a['route_data'];
    if (rd is! Map) return false;
    final alts = rd['alternatives'];
    if (alts is! List || alts.isEmpty) return false;
    // Require at least one alternative with a real distance & ETA. Bogus
    // 0km / 0min loops from a same-origin-and-destination lookup are
    // filtered out so we don't render an empty map.
    for (final r in alts) {
      if (r is Map) {
        final d = r['distance_km'];
        final t = r['eta_min'];
        final dist = d is num ? d : 0;
        final eta = t is num ? t : 0;
        if (dist > 0.3 && eta > 0) return true;
      }
    }
    return false;
  }

  Widget _routePanel(Map<String, dynamic> a) {
    final rd = Map<String, dynamic>.from(a['route_data'] as Map);
    final altsRaw = rd['alternatives'];
    final alts = (altsRaw is List)
        ? altsRaw.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList()
        : <Map<String, dynamic>>[];
    final origin = a['route_origin']?.toString() ?? '—';
    final dest = a['route_destination']?.toString() ?? '—';
    final blocked = a['route_blocked_area']?.toString() ?? '';
    final staticMapUrl = rd['static_map_url']?.toString();
    final isLive = rd['is_live'] == true;

    return Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
      decoration: BoxDecoration(
        color: CiroColors.surfaceAlt,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: CiroColors.hairline),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 22,
                height: 22,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: const Color(0xFF1A73E8).withValues(alpha: 0.10),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: const Icon(Icons.alt_route_rounded,
                    size: 14, color: Color(0xFF1A73E8)),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text('GOOGLE MAPS · ${alts.length} ALT ROUTES',
                    style: CiroType.mono(const Color(0xFF1A73E8),
                        size: 10.5, w: FontWeight.w700)),
              ),
              Pill(
                text: isLive ? 'LIVE' : 'MOCK',
                color: isLive ? CiroColors.sevLow : CiroColors.inkSubtle,
                background: isLive
                    ? CiroColors.sevLowSoft
                    : CiroColors.surfaceAlt,
                dense: true,
                dot: true,
              ),
            ],
          ),
          if (staticMapUrl != null && staticMapUrl.isNotEmpty) ...[
            const SizedBox(height: 10),
            _staticMap(staticMapUrl),
          ],
          const SizedBox(height: 10),
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              const Icon(Icons.trip_origin_rounded,
                  size: 12, color: CiroColors.inkMuted),
              const SizedBox(width: 6),
              Expanded(
                child: Text(origin,
                    style: CiroType.small(CiroColors.inkBody),
                    overflow: TextOverflow.ellipsis),
              ),
              const SizedBox(width: 6),
              const Icon(Icons.arrow_forward_rounded,
                  size: 12, color: CiroColors.inkSubtle),
              const SizedBox(width: 6),
              Expanded(
                child: Text(dest,
                    style: CiroType.small(CiroColors.inkBody),
                    overflow: TextOverflow.ellipsis),
              ),
            ],
          ),
          if (blocked.isNotEmpty) ...[
            const SizedBox(height: 4),
            Row(
              children: [
                const Icon(Icons.block_rounded,
                    size: 11, color: CiroColors.sevHigh),
                const SizedBox(width: 6),
                Text('Bypassing $blocked',
                    style: CiroType.mono(CiroColors.sevHigh,
                        size: 10.5, w: FontWeight.w600)),
              ],
            ),
          ],
          const SizedBox(height: 10),
          ...alts.asMap().entries.map((e) {
            final i = e.key;
            final alt = e.value;
            final name = alt['route_name']?.toString() ?? 'Route ${i + 1}';
            final km = alt['distance_km'];
            final eta = alt['eta_min'];
            final desc = alt['description']?.toString() ?? '';
            final isFastest = i == 0;
            return Padding(
              padding: EdgeInsets.only(bottom: i == alts.length - 1 ? 0 : 8),
              child: Container(
                padding: const EdgeInsets.fromLTRB(10, 8, 10, 8),
                decoration: BoxDecoration(
                  color: CiroColors.surface,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: isFastest
                        ? const Color(0xFF1A73E8).withValues(alpha: 0.30)
                        : CiroColors.hairlineSoft,
                  ),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Container(
                      width: 28,
                      height: 28,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: isFastest
                            ? const Color(0xFF1A73E8)
                            : CiroColors.inkSubtle,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        '${i + 1}',
                        style: CiroType.mono(Colors.white,
                            size: 12, w: FontWeight.w700),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: Text(
                                  name,
                                  style: CiroType.h3(CiroColors.inkStrong)
                                      .copyWith(fontSize: 13),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                              if (isFastest)
                                Pill(
                                  text: 'FASTEST',
                                  color: const Color(0xFF1A73E8),
                                  background: const Color(0xFF1A73E8)
                                      .withValues(alpha: 0.10),
                                  dense: true,
                                ),
                            ],
                          ),
                          const SizedBox(height: 3),
                          Row(
                            children: [
                              if (eta != null) ...[
                                const Icon(Icons.schedule_rounded,
                                    size: 11, color: CiroColors.inkMuted),
                                const SizedBox(width: 3),
                                Text('$eta min',
                                    style: CiroType.mono(CiroColors.inkBody,
                                        size: 11, w: FontWeight.w600)),
                                const SizedBox(width: 10),
                              ],
                              if (km != null) ...[
                                const Icon(Icons.straighten_rounded,
                                    size: 11, color: CiroColors.inkMuted),
                                const SizedBox(width: 3),
                                Text('$km km',
                                    style: CiroType.mono(CiroColors.inkBody,
                                        size: 11, w: FontWeight.w600)),
                              ],
                            ],
                          ),
                          if (desc.isNotEmpty) ...[
                            const SizedBox(height: 4),
                            Text(
                              desc,
                              style: CiroType.small(CiroColors.inkMuted)
                                  .copyWith(fontSize: 11),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            );
          }),
        ],
      ),
    );
  }

  String _toTitle(String s) {
    if (s.isEmpty) return s;
    return s
        .split(' ')
        .map((w) => w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}')
        .join(' ');
  }

  Widget _metaChip(IconData icon, String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: CiroColors.surfaceAlt,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: CiroColors.inkMuted),
          const SizedBox(width: 5),
          Text(text,
              style: CiroType.small(CiroColors.inkBody).copyWith(fontSize: 11.5)),
        ],
      ),
    );
  }

  // ============== METRICS ==============
  Widget _metricsRow() {
    final beforeP = _before['traffic_congestion_percent'] is int
        ? _before['traffic_congestion_percent'] as int
        : 0;
    final afterP = _after['traffic_congestion_percent'] is int
        ? _after['traffic_congestion_percent'] as int
        : 0;
    final beforeAlerts = _before['public_alerts_sent'] is int
        ? _before['public_alerts_sent'] as int
        : 0;
    final afterAlerts = _after['public_alerts_sent'] is int
        ? _after['public_alerts_sent'] as int
        : 0;
    final beforeSvc = _before['emergency_services_deployed'] == true;
    final afterSvc = _after['emergency_services_deployed'] == true;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionLabel('SYSTEM IMPACT', color: CiroColors.inkStrong),
        const SizedBox(height: 10),
        IntrinsicHeight(
          child: Row(
            children: [
              Expanded(
                child: _metricsCard(
                  title: 'BEFORE',
                  accent: CiroColors.sevHigh,
                  marginRight: 8,
                  congestion: beforeP,
                  services: beforeSvc,
                  alerts: beforeAlerts,
                ),
              ),
              Expanded(
                child: _metricsCard(
                  title: 'AFTER',
                  accent: CiroColors.sevLow,
                  marginLeft: 8,
                  congestion: afterP,
                  services: afterSvc,
                  alerts: afterAlerts,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _metricsCard({
    required String title,
    required Color accent,
    required int congestion,
    required bool services,
    required int alerts,
    double marginLeft = 0,
    double marginRight = 0,
  }) {
    return Container(
      margin: EdgeInsets.only(left: marginLeft, right: marginRight),
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 14),
      decoration: ciroCard(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(color: accent, shape: BoxShape.circle),
              ),
              const SizedBox(width: 8),
              Text(title,
                  style: CiroType.mono(accent, size: 11, w: FontWeight.w700)),
            ],
          ),
          const SizedBox(height: 10),
          _metricRow('Congestion', '$congestion%', accent),
          _metricRow('Services', services ? 'Deployed' : 'Standby', accent),
          _metricRow('Alerts', _formatNum(alerts), accent),
        ],
      ),
    );
  }

  String _formatNum(int n) {
    if (n >= 1000) return '${(n / 1000).toStringAsFixed(1)}k';
    return n.toString();
  }

  Widget _metricRow(String label, String value, Color color) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              style: CiroType.mono(CiroColors.inkSubtle, size: 10, w: FontWeight.w600)),
          const SizedBox(height: 2),
          Text(value,
              style: CiroType.metric(color).copyWith(fontSize: 19)),
        ],
      ),
    );
  }

  // ============== EXECUTION LOG ==============
  Widget _executionLog() {
    final logs = _execLog;
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 14),
      decoration: BoxDecoration(
        color: const Color(0xFF1B2228),
        borderRadius: BorderRadius.circular(16),
        boxShadow: CiroShadow.card,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
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
                'EXECUTION LOG',
                style: CiroType.mono(const Color(0xFF6BE3B0),
                    size: 10.5, w: FontWeight.w700),
              ),
              const Spacer(),
              Text('${logs.length} entries',
                  style: CiroType.mono(const Color(0xFF9FB0B8), size: 10)),
            ],
          ),
          const SizedBox(height: 12),
          Container(height: 1, color: const Color(0xFF2A323A)),
          const SizedBox(height: 10),
          if (logs.isEmpty)
            Text(
              '> no entries recorded',
              style: CiroType.mono(const Color(0xFF9FB0B8), size: 11),
            )
          else
            ...logs.map((m) {
              final id = m['action_id']?.toString() ?? '';
              final ticket = m['ticket_id']?.toString() ?? '';
              final res = m['simulated_result']?.toString() ?? '';
              final alert = m['alert_message_body']?.toString() ?? '';
              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          '> $id  executed',
                          style: CiroType.mono(const Color(0xFFE6F0E9),
                              size: 11.5, w: FontWeight.w700),
                        ),
                        if (ticket.isNotEmpty) ...[
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: const Color(0xFF6BE3B0)
                                  .withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(4),
                              border: Border.all(
                                color: const Color(0xFF6BE3B0)
                                    .withValues(alpha: 0.30),
                              ),
                            ),
                            child: Text(
                              ticket,
                              style: CiroType.mono(const Color(0xFF6BE3B0),
                                  size: 9.5, w: FontWeight.w700),
                            ),
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 3),
                    Text(
                      '  └ $res',
                      style: CiroType.mono(const Color(0xFFB6C6BC), size: 11),
                    ),
                    if (alert.isNotEmpty) ...[
                      const SizedBox(height: 6),
                      Container(
                        margin: const EdgeInsets.only(left: 14),
                        padding: const EdgeInsets.fromLTRB(8, 6, 8, 8),
                        decoration: BoxDecoration(
                          color: const Color(0xFF1A2730),
                          borderRadius: BorderRadius.circular(6),
                          border: Border(
                            left: BorderSide(
                              color: const Color(0xFF6BE3B0)
                                  .withValues(alpha: 0.55),
                              width: 2,
                            ),
                          ),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(Icons.sms_outlined,
                                size: 11, color: Color(0xFF6BE3B0)),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'CITIZEN ALERT BROADCAST',
                                    style: CiroType.mono(
                                        const Color(0xFF6BE3B0),
                                        size: 8.5,
                                        w: FontWeight.w700),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    alert,
                                    style: CiroType.mono(
                                            const Color(0xFFE6F0E9),
                                            size: 10.5)
                                        .copyWith(height: 1.4),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ],
                ),
              );
            }),
          if ((_execution['simulation_summary'] as String?)?.isNotEmpty == true) ...[
            const SizedBox(height: 8),
            Container(height: 1, color: const Color(0xFF2A323A)),
            const SizedBox(height: 10),
            Text(
              _execution['simulation_summary'].toString(),
              style: CiroType.small(const Color(0xFFB6C6BC))
                  .copyWith(fontStyle: FontStyle.italic),
            ),
          ],
        ],
      ),
    );
  }

  // ============== STRATEGY ==============
  Widget _strategyCard() {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
      decoration: ciroCard(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SectionLabel('STRATEGY', color: CiroColors.inkStrong),
          const SizedBox(height: 10),
          Text(
            (_plan['overall_strategy']?.toString() ?? '—'),
            style: CiroType.body(CiroColors.inkStrong),
          ),
          if ((_plan['public_advisory'] as String?)?.isNotEmpty == true) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
              decoration: BoxDecoration(
                color: CiroColors.accentSoft,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: CiroColors.accent.withValues(alpha: 0.25)),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.campaign_outlined,
                      size: 18, color: CiroColors.accent),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'PUBLIC ADVISORY',
                          style: CiroType.mono(CiroColors.accent,
                              size: 10.5, w: FontWeight.w700),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          _plan['public_advisory'].toString(),
                          style: CiroType.bodyTight(CiroColors.inkStrong),
                        ),
                      ],
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

  Future<void> _onShare() async {
    try {
      await HistoryService.save(widget.data);
      if (!mounted) return;
      setState(() => _archived = true);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Report archived to CIRO-DB — open History to review.',
            style: CiroType.bodyTight(Colors.white),
          ),
          backgroundColor: CiroColors.brand,
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Could not archive: $e',
              style: CiroType.bodyTight(Colors.white)),
          backgroundColor: CiroColors.sevHigh,
        ),
      );
    }
  }

  // ============== BOTTOM BUTTONS ==============
  Widget _bottomActions() {
    return Row(
      children: [
        Expanded(
          child: SizedBox(
            height: 50,
            child: OutlinedButton.icon(
              onPressed: () => Navigator.popUntil(context, (r) => r.isFirst),
              style: OutlinedButton.styleFrom(
                foregroundColor: CiroColors.inkStrong,
                side: const BorderSide(color: CiroColors.hairline),
                backgroundColor: CiroColors.surface,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12)),
              ),
              icon: const Icon(Icons.replay_rounded, size: 16),
              label: Text('New signal',
                  style: CiroType.h3(CiroColors.inkStrong).copyWith(fontSize: 14)),
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          flex: 2,
          child: SizedBox(
            height: 50,
            child: FilledButton.icon(
              onPressed: _archived ? null : _onShare,
              style: FilledButton.styleFrom(
                backgroundColor: CiroColors.brand,
                foregroundColor: Colors.white,
                disabledBackgroundColor: CiroColors.brand.withValues(alpha: 0.4),
                disabledForegroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12)),
              ),
              icon: Icon(
                _archived ? Icons.check_rounded : Icons.ios_share_rounded,
                size: 16,
              ),
              label: Text(
                _archived ? 'Archived' : 'Share full report',
                style: CiroType.h3(Colors.white).copyWith(fontSize: 14),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _RingPainter extends CustomPainter {
  _RingPainter({
    required this.progress,
    required this.color,
    required this.track,
    required this.stroke,
  });
  final double progress;
  final Color color;
  final Color track;
  final double stroke;

  @override
  void paint(Canvas canvas, Size size) {
    final c = Offset(size.width / 2, size.height / 2);
    final r = math.min(size.width, size.height) / 2 - stroke / 2;
    final trackPaint = Paint()
      ..color = track
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..strokeCap = StrokeCap.round;
    final fgPaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawCircle(c, r, trackPaint);
    final start = -math.pi / 2;
    canvas.drawArc(
      Rect.fromCircle(center: c, radius: r),
      start,
      progress * math.pi * 2,
      false,
      fgPaint,
    );
  }

  @override
  bool shouldRepaint(covariant _RingPainter old) =>
      old.progress != progress || old.color != color;
}
