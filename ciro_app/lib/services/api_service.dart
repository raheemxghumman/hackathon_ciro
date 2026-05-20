import 'package:dio/dio.dart';

class ApiService {
  // Override at build time:
  //   flutter build web --dart-define=API_BASE_URL=https://your-cloud-run-url
  // Falls back to localhost for local development.
  static const String _baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  static final Dio _dio = Dio(
    BaseOptions(
      baseUrl: _baseUrl,
      connectTimeout: const Duration(seconds: 120),
      receiveTimeout: const Duration(seconds: 120),
      sendTimeout: const Duration(seconds: 120),
      headers: {'Content-Type': 'application/json'},
    ),
  );

  static Future<Map<String, dynamic>> analyzeCrisis(String text) async {
    try {
      final response = await _dio.post(
        '/analyze-adk',
        data: {'text': text},
      );
      return Map<String, dynamic>.from(response.data as Map);
    } on DioException catch (e) {
      throw Exception('Failed to analyze: ${e.message ?? e.toString()}');
    } catch (e) {
      throw Exception('Failed to analyze: $e');
    }
  }

  static Future<List<Map<String, dynamic>>> getLatestIncidents({int limit = 5}) async {
    try {
      final response = await _dio.get('/incidents', queryParameters: {'limit': limit});
      final data = response.data;
      if (data is Map) {
        final list = data['incidents'];
        if (list is List) {
          return list.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
        }
      }
      return [];
    } catch (_) {
      return [];
    }
  }

  static Future<Map<String, dynamic>> getLiveSignals() async {
    try {
      final response = await _dio.get('/signals');
      return Map<String, dynamic>.from(response.data as Map);
    } catch (_) {
      return {};
    }
  }
}
