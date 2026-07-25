import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../models/observation.dart';
import '../models/commodity_price.dart';

/// API client for FastAPI backend.
/// Handles authentication (JWT), retry logic, error handling.
class ApiClient {
  static const String _baseUrl = 'https://api.mining-agent.ke/v1';
  static const Duration _timeout = Duration(seconds: 30);
  static const int _maxRetries = 3;

  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  String? _accessToken;
  String? _refreshToken;

  /// Analyze a mineral photo.
  Future<AnalysisResult> analyzeImage(Observation observation) async {
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('$_baseUrl/analyze'),
    );

    // Add image file
    if (observation.imagePath != null) {
      request.files.add(
        await http.MultipartFile.fromPath('image', observation.imagePath!),
      );
    }

    // Add GPS coordinates
    if (observation.latitude != null) {
      request.fields['latitude'] = observation.latitude!.toString();
    }
    if (observation.longitude != null) {
      request.fields['longitude'] = observation.longitude!.toString();
    }

    request.fields['observation_id'] = observation.id;

    // Add auth header
    final token = await _getAccessToken();
    if (token != null) {
      request.headers['Authorization'] = 'Bearer $token';
    }

    final streamedResponse = await request.send().timeout(_timeout);
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return AnalysisResult.fromJson(data);
    } else if (response.statusCode == 401) {
      await _refreshAccessToken();
      return analyzeImage(observation); // Retry with new token
    } else {
      throw ApiException(
        'Analysis failed: ${response.statusCode}',
        response.statusCode,
      );
    }
  }

  /// Get commodity prices (gold, copper, rare earths).
  Future<List<CommodityPrice>> getCommodityPrices() async {
    return _retryRequest(() async {
      final response = await _authenticatedGet('/prices');

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as List;
        return data.map((e) => CommodityPrice.fromJson(e)).toList();
      } else {
        throw ApiException(
          'Failed to load prices: ${response.statusCode}',
          response.statusCode,
        );
      }
    });
  }

  /// Get user's reports.
  Future<List<Map<String, dynamic>>> getReports() async {
    return _retryRequest(() async {
      final response = await _authenticatedGet('/reports');

      if (response.statusCode == 200) {
        return (jsonDecode(response.body) as List).cast<Map<String, dynamic>>();
      } else {
        throw ApiException(
          'Failed to load reports: ${response.statusCode}',
          response.statusCode,
        );
      }
    });
  }

  /// Generate PDF report.
  Future<String> generateReport(String observationId) async {
    return _retryRequest(() async {
      final response = await _authenticatedPost('/reports/generate', {
        'observation_id': observationId,
      });

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['pdf_url'] as String;
      } else {
        throw ApiException(
          'Failed to generate report: ${response.statusCode}',
          response.statusCode,
        );
      }
    });
  }

  /// Register a new user.
  Future<void> register(String phone, String name) async {
    final response = await http
        .post(
          Uri.parse('$_baseUrl/auth/register'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'phone': phone, 'name': name}),
        )
        .timeout(_timeout);

    if (response.statusCode == 201) {
      final data = jsonDecode(response.body);
      _accessToken = data['access_token'];
      _refreshToken = data['refresh_token'];
      await _saveTokens();
    } else {
      throw ApiException('Registration failed', response.statusCode);
    }
  }

  /// Login with phone.
  Future<void> login(String phone, String code) async {
    final response = await http
        .post(
          Uri.parse('$_baseUrl/auth/login'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'phone': phone, 'code': code}),
        )
        .timeout(_timeout);

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      _accessToken = data['access_token'];
      _refreshToken = data['refresh_token'];
      await _saveTokens();
    } else {
      throw ApiException('Login failed', response.statusCode);
    }
  }

  /// Authenticated GET request.
  Future<http.Response> _authenticatedGet(String path) async {
    final token = await _getAccessToken();
    return http.get(
      Uri.parse('$_baseUrl$path'),
      headers: {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      },
    ).timeout(_timeout);
  }

  /// Authenticated POST request.
  Future<http.Response> _authenticatedPost(
    String path,
    Map<String, dynamic> body,
  ) async {
    final token = await _getAccessToken();
    return http
        .post(
          Uri.parse('$_baseUrl$path'),
          headers: {
            'Content-Type': 'application/json',
            if (token != null) 'Authorization': 'Bearer $token',
          },
          body: jsonEncode(body),
        )
        .timeout(_timeout);
  }

  /// Retry logic with exponential backoff.
  Future<T> _retryRequest<T>(Future<T> Function() request) async {
    for (int attempt = 0; attempt < _maxRetries; attempt++) {
      try {
        return await request();
      } on SocketException {
        if (attempt == _maxRetries - 1) rethrow;
        await Future.delayed(Duration(seconds: (attempt + 1) * 2));
      } on TimeoutException {
        if (attempt == _maxRetries - 1) rethrow;
        await Future.delayed(Duration(seconds: (attempt + 1) * 2));
      } on ApiException catch (e) {
        if (e.statusCode == 401 && attempt < _maxRetries - 1) {
          await _refreshAccessToken();
        } else {
          rethrow;
        }
      }
    }
    throw ApiException('Max retries exceeded', 0);
  }

  /// Get access token (from memory or secure storage).
  Future<String?> _getAccessToken() async {
    _accessToken ??= await _storage.read(key: 'access_token');
    return _accessToken;
  }

  /// Refresh access token using refresh token.
  Future<void> _refreshAccessToken() async {
    _refreshToken ??= await _storage.read(key: 'refresh_token');
    if (_refreshToken == null) return;

    try {
      final response = await http
          .post(
            Uri.parse('$_baseUrl/auth/refresh'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'refresh_token': _refreshToken}),
          )
          .timeout(_timeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        _accessToken = data['access_token'];
        if (data['refresh_token'] != null) {
          _refreshToken = data['refresh_token'];
        }
        await _saveTokens();
      }
    } catch (_) {
      // Refresh failed — user needs to login again
      await _clearTokens();
    }
  }

  /// Save tokens to secure storage.
  Future<void> _saveTokens() async {
    if (_accessToken != null) {
      await _storage.write(key: 'access_token', value: _accessToken);
    }
    if (_refreshToken != null) {
      await _storage.write(key: 'refresh_token', value: _refreshToken);
    }
  }

  /// Clear tokens (logout).
  Future<void> _clearTokens() async {
    _accessToken = null;
    _refreshToken = null;
    await _storage.delete(key: 'access_token');
    await _storage.delete(key: 'refresh_token');
  }

  /// Logout.
  Future<void> logout() async {
    await _clearTokens();
  }
}

/// Custom API exception.
class ApiException implements Exception {
  final String message;
  final int statusCode;

  ApiException(this.message, this.statusCode);

  @override
  String toString() => 'ApiException($statusCode): $message';
}

class TimeoutException implements Exception {
  final String message;
  TimeoutException(this.message);
  @override
  String toString() => message;
}
