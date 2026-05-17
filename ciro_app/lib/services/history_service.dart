import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class HistoryEntry {
  HistoryEntry({
    required this.id,
    required this.crisisType,
    required this.location,
    required this.severity,
    required this.confidence,
    required this.savedAt,
    required this.data,
  });

  final String id;
  final String crisisType;
  final String location;
  final String severity;
  final int confidence;
  final DateTime savedAt;
  final Map<String, dynamic> data;

  Map<String, dynamic> toJson() => {
        'id': id,
        'crisisType': crisisType,
        'location': location,
        'severity': severity,
        'confidence': confidence,
        'savedAt': savedAt.toIso8601String(),
        'data': data,
      };

  static HistoryEntry fromJson(Map<String, dynamic> j) => HistoryEntry(
        id: j['id'] as String,
        crisisType: (j['crisisType'] as String?) ?? 'Unknown',
        location: (j['location'] as String?) ?? '—',
        severity: (j['severity'] as String?) ?? 'Unknown',
        confidence: (j['confidence'] is int) ? j['confidence'] as int : 0,
        savedAt: DateTime.tryParse(j['savedAt'] as String? ?? '') ?? DateTime.now(),
        data: Map<String, dynamic>.from((j['data'] as Map?) ?? {}),
      );
}

class HistoryService {
  static const _key = 'ciro_history_v1';
  static const _maxEntries = 50;

  static Future<List<HistoryEntry>> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null || raw.isEmpty) return [];
    try {
      final list = jsonDecode(raw) as List;
      return list
          .whereType<Map>()
          .map((e) => HistoryEntry.fromJson(Map<String, dynamic>.from(e)))
          .toList();
    } catch (_) {
      return [];
    }
  }

  static Future<HistoryEntry> save(Map<String, dynamic> analysis) async {
    final detection = (analysis['detection'] is Map)
        ? Map<String, dynamic>.from(analysis['detection'] as Map)
        : <String, dynamic>{};
    final ingestion = (analysis['ingestion'] is Map)
        ? Map<String, dynamic>.from(analysis['ingestion'] as Map)
        : <String, dynamic>{};

    final entry = HistoryEntry(
      id: 'CIRO-${DateTime.now().millisecondsSinceEpoch}',
      crisisType: (detection['crisis_type'] as String?) ?? 'Unknown event',
      location: (ingestion['location'] as String?) ?? '—',
      severity: (detection['severity'] as String?) ?? 'Unknown',
      confidence: (detection['confidence_percent'] is int)
          ? detection['confidence_percent'] as int
          : 0,
      savedAt: DateTime.now(),
      data: analysis,
    );

    final existing = await load();
    final updated = [entry, ...existing].take(_maxEntries).toList();

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, jsonEncode(updated.map((e) => e.toJson()).toList()));
    return entry;
  }

  static Future<void> remove(String id) async {
    final existing = await load();
    final filtered = existing.where((e) => e.id != id).toList();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, jsonEncode(filtered.map((e) => e.toJson()).toList()));
  }

  static Future<void> clear() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_key);
  }
}
