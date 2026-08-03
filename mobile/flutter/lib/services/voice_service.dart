/// Voice Service — On-device recording + NVIDIA cloud transcription
///
/// Handles:
/// - Recording voice messages (on-device)
/// - Sending to NVIDIA NIM Whisper for transcription (cloud)
/// - Text-to-speech for responses (cloud)
/// - Offline fallback (local Whisper model when available)

import 'dart:io';
import 'package:http/http.dart' as http;
import 'dart:convert';

class VoiceService {
  final String nvidiaApiKey;
  final String nvidiaBaseUrl;

  VoiceService({
    required this.nvidiaApiKey,
    this.nvidiaBaseUrl = 'https://integrate.api.nvidia.com/v1',
  });

  /// Transcribe audio using NVIDIA NIM Whisper
  Future<String> transcribe(String audioFilePath) async {
    final file = File(audioFilePath);
    final bytes = await file.readAsBytes();

    final request = http.MultipartRequest(
      'POST',
      Uri.parse('$nvidiaBaseUrl/audio/transcriptions'),
    );

    request.headers['Authorization'] = 'Bearer $nvidiaApiKey';
    request.fields['model'] = 'nvidia/whisper-large-v3';
    request.fields['language'] = 'sw'; // Swahili primary
    request.files.add(http.MultipartFile.fromBytes(
      'file',
      bytes,
      filename: 'audio.ogg',
    ));

    final response = await request.send();
    final body = await response.stream.bytesToString();

    if (response.statusCode == 200) {
      final data = jsonDecode(body);
      return data['text'] ?? '';
    } else {
      throw Exception('Transcription failed: ${response.statusCode} $body');
    }
  }

  /// Convert text to speech using NVIDIA NIM TTS
  Future<List<int>> synthesize(String text, {String language = 'sw'}) async {
    final response = await http.post(
      Uri.parse('$nvidiaBaseUrl/audio/speech'),
      headers: {
        'Authorization': 'Bearer $nvidiaApiKey',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'model': 'nvidia/tts-hifigan',
        'input': text,
        'voice': language == 'sw' ? 'sw-FK' : 'en-US',
      }),
    );

    if (response.statusCode == 200) {
      return response.bodyBytes;
    } else {
      throw Exception('TTS failed: ${response.statusCode}');
    }
  }

  /// Check if NVIDIA voice services are available
  Future<bool> isAvailable() async {
    try {
      final response = await http.get(
        Uri.parse('$nvidiaBaseUrl/models'),
        headers: {'Authorization': 'Bearer $nvidiaApiKey'},
      );
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
}
