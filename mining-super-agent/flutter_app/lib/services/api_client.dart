import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiClient {
  final String baseUrl;
  String? _token;

  ApiClient({this.baseUrl = 'http://localhost:8000'});

  void setToken(String token) {
    _token = token;
  }

  Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    if (_token != null) 'Authorization': 'Bearer $_token',
  };

  Future<Map<String, dynamic>> get(String path) async {
    final response = await http.get(
      Uri.parse('$baseUrl$path'),
      headers: _headers,
    );
    return _handleResponse(response);
  }

  Future<Map<String, dynamic>> post(String path, Map<String, dynamic> body) async {
    final response = await http.post(
      Uri.parse('$baseUrl$path'),
      headers: _headers,
      body: jsonEncode(body),
    );
    return _handleResponse(response);
  }

  Future<Map<String, dynamic>> analyzePhoto(String imagePath, double? lat, double? lon) async {
    // TODO: Multipart upload
    return {'status': 'not_implemented'};
  }

  Future<List<dynamic>> getPrices(List<String> commodities) async {
    final result = await get('/api/v1/prices?commodities=${commodities.join(",")}');
    return result['prices'] ?? [];
  }

  Map<String, dynamic> _handleResponse(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return jsonDecode(response.body);
    }
    throw Exception('API error: ${response.statusCode} ${response.body}');
  }
}
