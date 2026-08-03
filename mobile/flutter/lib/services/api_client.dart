import 'dart:async' as dart_async;
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

// ── Environment Configuration ────────────────────────────────────────────────

enum Environment { development, staging, production }

class ApiConfig {
  static const Map<Environment, String> _baseUrls = {
    Environment.development: 'http://10.0.2.2:8000',    // Android emulator
    Environment.staging:     'https://staging-api.sovereign-dao.org',
    Environment.production:  'https://api.sovereign-dao.org',
  };

  static const Duration defaultTimeout = Duration(seconds: 30);
  static const Duration shortTimeout    = Duration(seconds: 10);
  static const Duration longTimeout     = Duration(seconds: 60);

  static Environment _environment = Environment.development;
  static Environment get environment => _environment;

  static void setEnvironment(Environment env) => _environment = env;

  static String get baseUrl => _baseUrls[_environment]!;
}

// ── Custom Exceptions ────────────────────────────────────────────────────────

class ApiException implements Exception {
  final String message;
  final int? statusCode;
  final dynamic data;

  ApiException(this.message, {this.statusCode, this.data});

  @override
  String toString() => 'ApiException($statusCode): $message';

  bool get isNetworkError => statusCode == null;
  bool get isServerError  => statusCode != null && statusCode! >= 500;
  bool get isClientError  => statusCode != null &&
      statusCode! >= 400 && statusCode! < 500;
  bool get isNotFound     => statusCode == 404;
  bool get isUnauthorized => statusCode == 401;
  bool get isForbidden    => statusCode == 403;
}

class NetworkException extends ApiException {
  NetworkException([String message = 'No network connection'])
      : super(message, statusCode: null);
}

class ApiTimeoutException extends ApiException {
  ApiTimeoutException([String message = 'Request timed out'])
      : super(message, statusCode: null);
}

// ── Cache Entry ──────────────────────────────────────────────────────────────

class _CacheEntry {
  final String body;
  final DateTime fetchedAt;
  final Duration ttl;

  _CacheEntry(this.body, {this.ttl = const Duration(minutes: 5)})
      : fetchedAt = DateTime.now();

  bool get isExpired => DateTime.now().difference(fetchedAt) > ttl;
}

// ── API Client ───────────────────────────────────────────────────────────────

class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;

  ApiClient._internal() {
    _loadBaseUrl();
  }

  // Configurable base URL — falls back to environment default
  String _baseUrl = ApiConfig.baseUrl;
  String get baseUrl => _baseUrl;
  set baseUrl(String url) {
    _baseUrl = url;
    _persistBaseUrl(url);
  }

  // Auth token
  String? _token;

  // In-memory response cache: path → _CacheEntry
  final Map<String, _CacheEntry> _cache = {};

  // HTTP client (connection pooling)
  final http.Client _httpClient = http.Client();

  // ── Environment / Persistence ─────────────────────────────────────────────

  static const _prefKeyBaseUrl = 'api_base_url';
  static const _prefKeyEnv     = 'api_environment';

  Future<void> _loadBaseUrl() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedUrl = prefs.getString(_prefKeyBaseUrl);
      final savedEnv = prefs.getString(_prefKeyEnv);

      if (savedEnv != null) {
        final env = Environment.values.firstWhere(
          (e) => e.name == savedEnv,
          orElse: () => Environment.development,
        );
        ApiConfig.setEnvironment(env);
      }

      _baseUrl = savedUrl ?? ApiConfig.baseUrl;
    } catch (_) {
      _baseUrl = ApiConfig.baseUrl;
    }
  }

  Future<void> _persistBaseUrl(String url) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_prefKeyBaseUrl, url);
      await prefs.setString(_prefKeyEnv, ApiConfig.environment.name);
    } catch (_) {}
  }

  /// Switch environment and persist the choice.
  Future<void> setEnvironment(Environment env) async {
    ApiConfig.setEnvironment(env);
    _baseUrl = ApiConfig.baseUrl;
    _cache.clear();
    await _persistBaseUrl(_baseUrl);
  }

  // ── Auth ──────────────────────────────────────────────────────────────────

  void setToken(String? token) {
    _token = token;
  }

  void clearToken() {
    _token = null;
  }

  // ── Headers ───────────────────────────────────────────────────────────────

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        if (_token != null) 'Authorization': 'Bearer $_token',
      };

  // ── Cache helpers ─────────────────────────────────────────────────────────

  void clearCache() => _cache.clear();

  void invalidateCache(String pathPrefix) {
    _cache.removeWhere((key, _) => key.startsWith(pathPrefix));
  }

  String? getCached(String path) {
    final entry = _cache[path];
    if (entry != null && !entry.isExpired) return entry.body;
    _cache.remove(path);
    return null;
  }

  void _putCache(String path, String body, {Duration ttl = const Duration(minutes: 5)}) {
    _cache[path] = _CacheEntry(body, ttl: ttl);
  }

  // ── Persistent offline cache (survives app restart) ───────────────────────

  static const _offlineCachePrefix = 'offline_cache_';

  Future<void> _persistOfflineCache(String path, String body) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('$_offlineCachePrefix$path', body);
    } catch (_) {}
  }

  Future<String?> _loadOfflineCache(String path) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      return prefs.getString('$_offlineCachePrefix$path');
    } catch (_) {
      return null;
    }
  }

  Future<void> clearOfflineCache() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final keys = prefs.getKeys().where((k) => k.startsWith(_offlineCachePrefix));
      for (final key in keys) {
        await prefs.remove(key);
      }
    } catch (_) {}
  }

  // ── Generic HTTP verbs ────────────────────────────────────────────────────

  Future<Map<String, dynamic>> get(
    String path, {
    Map<String, String>? queryParams,
    Duration timeout = ApiConfig.defaultTimeout,
    bool useCache = true,
    Duration cacheTtl = const Duration(minutes: 5),
    bool offlineFallback = true,
  }) async {
    final uri = _buildUri(path, queryParams);
    final cacheKey = uri.toString();

    // 1. Check in-memory cache
    if (useCache) {
      final cached = getCached(cacheKey);
      if (cached != null) return jsonDecode(cached) as Map<String, dynamic>;
    }

    try {
      final response = await _httpClient
          .get(uri, headers: _headers)
          .timeout(timeout);

      final body = _handleResponse(response);

      // Cache the response
      if (useCache) {
        _putCache(cacheKey, response.body, ttl: cacheTtl);
        await _persistOfflineCache(cacheKey, response.body);
      }

      return body;
    } on dart_async.TimeoutException {
      throw ApiTimeoutException();
    } on SocketException {
      // Offline fallback: return persisted cache if available
      if (offlineFallback) {
        final cached = await _loadOfflineCache(cacheKey);
        if (cached != null) return jsonDecode(cached) as Map<String, dynamic>;
      }
      throw NetworkException();
    }
  }

  Future<Map<String, dynamic>> post(
    String path,
    Map<String, dynamic> body, {
    Duration timeout = ApiConfig.defaultTimeout,
  }) async {
    final uri = _buildUri(path);
    try {
      final response = await _httpClient
          .post(uri, headers: _headers, body: jsonEncode(body))
          .timeout(timeout);
      return _handleResponse(response);
    } on dart_async.TimeoutException {
      throw ApiTimeoutException();
    } on SocketException {
      throw NetworkException();
    }
  }

  Future<Map<String, dynamic>> put(
    String path,
    Map<String, dynamic> body, {
    Duration timeout = ApiConfig.defaultTimeout,
  }) async {
    final uri = _buildUri(path);
    try {
      final response = await _httpClient
          .put(uri, headers: _headers, body: jsonEncode(body))
          .timeout(timeout);
      return _handleResponse(response);
    } on dart_async.TimeoutException {
      throw ApiTimeoutException();
    } on SocketException {
      throw NetworkException();
    }
  }

  Future<Map<String, dynamic>> delete(
    String path, {
    Duration timeout = ApiConfig.defaultTimeout,
  }) async {
    final uri = _buildUri(path);
    try {
      final response = await _httpClient
          .delete(uri, headers: _headers)
          .timeout(timeout);
      return _handleResponse(response);
    } on dart_async.TimeoutException {
      throw ApiTimeoutException();
    } on SocketException {
      throw NetworkException();
    }
  }

  // ── Multipart upload (for photo observations) ─────────────────────────────

  Future<Map<String, dynamic>> uploadFile(
    String path,
    String filePath, {
    String fieldName = 'file',
    Map<String, String>? fields,
    Duration timeout = ApiConfig.longTimeout,
  }) async {
    final uri = _buildUri(path);
    try {
      final request = http.MultipartRequest('POST', uri)
        ..headers.addAll(_headers)
        ..files.add(await http.MultipartFile.fromPath(fieldName, filePath));

      if (fields != null) request.fields.addAll(fields);

      final streamedResponse = await _httpClient.send(request).timeout(timeout);
      final response = await http.Response.fromStream(streamedResponse);
      return _handleResponse(response);
    } on dart_async.TimeoutException {
      throw ApiTimeoutException();
    } on SocketException {
      throw NetworkException();
    }
  }

  // ── Response handler ──────────────────────────────────────────────────────

  Map<String, dynamic> _handleResponse(http.Response response) {
    final statusCode = response.statusCode;

    if (statusCode >= 200 && statusCode < 300) {
      if (response.body.isEmpty) return {};
      try {
        return jsonDecode(response.body) as Map<String, dynamic>;
      } catch (e) {
        throw ApiException('Invalid JSON response', statusCode: statusCode);
      }
    }

    // Parse error body if possible
    dynamic errorData;
    try {
      errorData = jsonDecode(response.body);
    } catch (_) {
      errorData = response.body;
    }

    switch (statusCode) {
      case 401:
        throw ApiException('Unauthorized', statusCode: 401, data: errorData);
      case 403:
        throw ApiException('Forbidden', statusCode: 403, data: errorData);
      case 404:
        throw ApiException('Not found', statusCode: 404, data: errorData);
      case 422:
        throw ApiException('Validation error', statusCode: 422, data: errorData);
      default:
        throw ApiException(
          'API error: $statusCode',
          statusCode: statusCode,
          data: errorData,
        );
    }
  }

  // ── URI builder ───────────────────────────────────────────────────────────

  Uri _buildUri(String path, [Map<String, String>? queryParams]) {
    final uri = Uri.parse('$_baseUrl$path');
    if (queryParams != null && queryParams.isNotEmpty) {
      return uri.replace(queryParameters: queryParams);
    }
    return uri;
  }

  // ══════════════════════════════════════════════════════════════════════════
  //  DOMAIN-SPECIFIC ENDPOINTS
  // ══════════════════════════════════════════════════════════════════════════

  // ── Health & Status ───────────────────────────────────────────────────────

  /// Backend health check. Lightweight, no auth required.
  Future<Map<String, dynamic>> healthCheck() {
    return get('/health',
        timeout: ApiConfig.shortTimeout, offlineFallback: false);
  }

  /// System status: agent count, names, blockchain connection.
  Future<Map<String, dynamic>> getSystemStatus() {
    return get('/status', timeout: ApiConfig.shortTimeout);
  }

  // ── Sovereign Agents ──────────────────────────────────────────────────────

  /// List all five sovereign agents.
  Future<Map<String, dynamic>> getAgents() {
    return get('/agents', cacheTtl: const Duration(minutes: 15));
  }

  /// Chat with a specific agent by name.
  Future<Map<String, dynamic>> chatWithAgent(String agentName, String message) {
    return post('/agents/$agentName/chat', {'message': message});
  }

  // ── Fair Deal Calculator ──────────────────────────────────────────────────

  /// Valentine's specific analysis (Nyatike, Migori County).
  Future<Map<String, dynamic>> getValentineFairDeal() {
    return get('/fair-deal/valentine', cacheTtl: const Duration(hours: 1));
  }

  /// Evaluate any mining offer for fairness.
  ///
  /// [offerAmountKes] — the cash amount offered.
  /// [minerals] — list of mineral names involved.
  /// [location] — location description.
  Future<Map<String, dynamic>> evaluateFairDeal({
    required double offerAmountKes,
    required List<String> minerals,
    String location = 'Unknown',
  }) {
    return post('/fair-deal/evaluate', {
      'offer_amount_kes': offerAmountKes,
      'minerals': minerals,
      'location': location,
    });
  }

  // ── DAO Governance ────────────────────────────────────────────────────────

  /// List all active governance proposals.
  Future<Map<String, dynamic>> getDaoProposals() {
    return get('/dao/proposals');
  }

  /// Create a new governance proposal.
  ///
  /// [title], [description], [proposer] are required.
  /// [type] defaults to 'royalty_allocation'.
  Future<Map<String, dynamic>> createProposal({
    required String title,
    required String description,
    required String proposer,
    String type = 'royalty_allocation',
  }) {
    return post('/dao/proposals', {
      'title': title,
      'description': description,
      'proposer': proposer,
      'type': type,
    });
  }

  /// Cast a quadratic vote on a proposal.
  ///
  /// [proposalId] — target proposal.
  /// [voter] — voter identity.
  /// [tokens] — tokens committed to this vote.
  /// [support] — true = for, false = against.
  Future<Map<String, dynamic>> castVote({
    required String proposalId,
    required String voter,
    required int tokens,
    bool support = true,
  }) {
    return post('/dao/proposals/$proposalId/vote', {
      'voter': voter,
      'tokens': tokens,
      'support': support,
    });
  }

  /// Community-wide DAO statistics.
  Future<Map<String, dynamic>> getDaoStats() {
    return get('/dao/stats', cacheTtl: const Duration(minutes: 2));
  }

  // ── Blockchain / Oracle ───────────────────────────────────────────────────

  /// Check blockchain connection status.
  Future<Map<String, dynamic>> getChainStatus() {
    return get('/chain/status', timeout: ApiConfig.shortTimeout);
  }

  /// Submit an observation to the blockchain oracle.
  Future<Map<String, dynamic>> submitToChain(Map<String, dynamic> observation) {
    return post('/chain/submit', observation);
  }

  // ── Legacy / Backward-compatible ──────────────────────────────────────────

  /// Legacy price fetch — kept for backward compatibility.
  Future<List<dynamic>> getPrices(List<String> commodities) async {
    final result =
        await get('/api/v1/prices', queryParams: {'commodities': commodities.join(',')});
    return result['prices'] ?? [];
  }

  /// Legacy photo analysis — now uses multipart upload.
  Future<Map<String, dynamic>> analyzePhoto(
      String imagePath, double? lat, double? lon) async {
    return uploadFile('/api/v1/observations', imagePath, fields: {
      if (lat != null) 'latitude': lat.toString(),
      if (lon != null) 'longitude': lon.toString(),
    });
  }

  // ── Connectivity check ────────────────────────────────────────────────────

  /// Quick connectivity probe (returns true if backend reachable).
  Future<bool> isConnected() async {
    try {
      await healthCheck();
      return true;
    } catch (_) {
      return false;
    }
  }

  // ── Cleanup ───────────────────────────────────────────────────────────────

  void dispose() {
    _httpClient.close();
    _cache.clear();
  }
}
