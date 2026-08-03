import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:geolocator/geolocator.dart';
import '../services/api_client.dart';

class PhotoScreen extends StatefulWidget {
  const PhotoScreen({super.key});

  @override
  State<PhotoScreen> createState() => _PhotoScreenState();
}

class _PhotoScreenState extends State<PhotoScreen> {
  File? _image;
  Position? _position;
  bool _loading = false;
  String? _result;
  final _apiClient = ApiClient();

  Future<void> _takePhoto() async {
    final picker = ImagePicker();
    final xfile = await picker.pickImage(source: ImageSource.camera, maxWidth: 1920);
    if (xfile == null) return;

    setState(() {
      _image = File(xfile.path);
      _loading = true;
      _result = null;
    });

    // Get GPS location
    try {
      final permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.always || permission == LocationPermission.whileInUse) {
        _position = await Geolocator.getCurrentPosition();
      }
    } catch (e) {
      // GPS not available
    }

    // Send photo to backend for mineral identification
    try {
      final result = await _apiClient.uploadFile(
        '/api/v1/minerals/identify',
        _image!.path,
        fieldName: 'image',
        fields: {
          if (_position != null) 'latitude': _position!.latitude.toString(),
          if (_position != null) 'longitude': _position!.longitude.toString(),
          'method': 'photo',
        },
        timeout: const Duration(seconds: 60),
      );

      final mineral = result['mineral'] ?? 'unknown';
      final confidence = result['confidence'] ?? 0;
      final disclaimers = (result['disclaimers'] as List<dynamic>?)?.join('\n') ?? '';
      final lookAlikes = (result['look_alikes'] as List<dynamic>?)?.join(', ') ?? 'none';
      final swahiliSummary = result['swahili_summary'] ?? '';
      final requiresExpert = result['requires_expert_review'] == true;

      setState(() {
        _loading = false;
        _result = '🪨 Mineral: ${mineral.toString().toUpperCase()}\n'
            '📊 Confidence: ${(confidence * 100).toStringAsFixed(0)}%\n'
            '${_position != null ? "📍 GPS: ${_position!.latitude}, ${_position!.longitude}\n" : ""}'
            '🔍 Look-alikes: $lookAlikes\n'
            '${requiresExpert ? "⚠️ Requires expert review\n" : ""}'
            '\n$swahiliSummary\n\n'
            '$disclaimers';
      });
    } catch (e) {
      setState(() {
        _loading = false;
        _result = '❌ Analysis failed: $e\n\n'
            'Photo captured. ${_position != null ? "GPS: ${_position!.latitude}, ${_position!.longitude}" : "No GPS signal."}';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Identify Mineral')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (_image != null)
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.file(_image!, height: 300, fit: BoxFit.cover),
              )
            else
              Container(
                height: 300,
                decoration: BoxDecoration(
                  color: Colors.grey[200],
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.camera_alt, size: 64, color: Colors.grey),
                    SizedBox(height: 8),
                    Text('Take a photo of your mineral sample'),
                  ],
                ),
              ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _loading ? null : _takePhoto,
              icon: const Icon(Icons.camera_alt),
              label: const Text('Take Photo'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
            ),
            if (_loading) ...[
              const SizedBox(height: 16),
              const Center(child: CircularProgressIndicator()),
              const SizedBox(height: 8),
              const Center(child: Text('Analyzing mineral...')),
            ],
            if (_result != null) ...[
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Text(_result!, style: const TextStyle(fontSize: 16)),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
