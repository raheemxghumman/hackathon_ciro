import 'package:dio/dio.dart';

class ApiService {
  static final Dio _dio = Dio(
    BaseOptions(
      baseUrl: 'http://localhost:8000',
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 30),
      sendTimeout: const Duration(seconds: 30),
      headers: {'Content-Type': 'application/json'},
    ),
  );

  static Future<Map<String, dynamic>> analyzeCrisis(String text) async {
    try {
      final response = await _dio.post(
        '/analyze',
        data: {'text': text},
      );
      return Map<String, dynamic>.from(response.data as Map);
    } on DioException catch (e) {
      throw Exception('Failed to analyze: ${e.message ?? e.toString()}');
    } catch (e) {
      throw Exception('Failed to analyze: $e');
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
