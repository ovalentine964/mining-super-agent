import 'dart:async';
import 'dart:io';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';

/// On-Device Voice Transcription using Whisper.cpp
///
/// Runs locally on the phone — no internet needed.
/// Uses Whisper tiny/base model (40-75MB).
/// Supports Swahili, English, and 97 other languages.
///
/// For complex reasoning, sends transcription to NVIDIA NIM cloud.
class OnDeviceVoiceService {
  static const _channel = MethodChannel('sovereign_resource_dao/whisper');
  bool _initialized = false;

  /// Initialize the on-device Whisper model
  /// Downloads model on first run (~40-75MB)
  Future<bool> initialize() async {
    if (_initialized) return true;

    try {
      final result = await _channel.invokeMethod('initialize', {
        'model': 'whisper-tiny', // 40MB, good quality for Swahili
        'language': 'sw',
      });
      _initialized = result == true;
      return _initialized;
    } catch (e) {
      // If native channel not available, fall back to cloud
      print('On-device Whisper not available: $e');
      return false;
    }
  }

  /// Transcribe audio file locally (no internet needed)
  Future<String> transcribe(String audioFilePath) async {
    if (!_initialized) {
      await initialize();
    }

    try {
      final result = await _channel.invokeMethod('transcribe', {
        'path': audioFilePath,
        'language': 'sw',
      });
      return result ?? '';
    } catch (e) {
      throw Exception('On-device transcription failed: $e');
    }
  }

  /// Check if on-device model is available
  Future<bool> isAvailable() async {
    try {
      final result = await _channel.invokeMethod('isAvailable');
      return result == true;
    } catch (e) {
      return false;
    }
  }

  /// Get model info (size, version)
  Future<Map<String, dynamic>> getModelInfo() async {
    try {
      final result = await _channel.invokeMethod('getModelInfo');
      return Map<String, dynamic>.from(result ?? {});
    } catch (e) {
      return {'available': false};
    }
  }
}
