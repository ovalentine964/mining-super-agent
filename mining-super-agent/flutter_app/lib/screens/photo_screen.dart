import 'dart:io';
import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import 'package:uuid/uuid.dart';
import '../services/offline_sync.dart';
import '../services/api_client.dart';
import '../services/app_localizations.dart';
import '../models/observation.dart';

/// Photo analysis screen — camera capture with GPS, submit to API.
/// Shows preview, confidence results, mineral identification.
class PhotoScreen extends StatefulWidget {
  const PhotoScreen({super.key});

  @override
  State<PhotoScreen> createState() => _PhotoScreenState();
}

class _PhotoScreenState extends State<PhotoScreen> {
  File? _imageFile;
  Position? _position;
  bool _isAnalyzing = false;
  AnalysisResult? _result;
  String? _error;
  final _picker = ImagePicker();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.photoAnalysis),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Camera/Gallery buttons
            _buildSourceButtons(l10n),

            const SizedBox(height: 16),

            // Image preview
            if (_imageFile != null) ...[
              _buildImagePreview(),
              const SizedBox(height: 16),
              _buildLocationInfo(l10n),
              const SizedBox(height: 16),
              _buildAnalyzeButton(l10n),
            ] else
              _buildEmptyState(l10n),

            // Loading
            if (_isAnalyzing) ...[
              const SizedBox(height: 24),
              _buildAnalyzingIndicator(l10n),
            ],

            // Results
            if (_result != null) ...[
              const SizedBox(height: 24),
              _buildResults(l10n, theme),
            ],

            // Error
            if (_error != null) ...[
              const SizedBox(height: 16),
              _buildError(l10n),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildSourceButtons(AppLocalizations l10n) {
    return Row(
      children: [
        Expanded(
          child: _buildSourceButton(
            icon: Icons.camera_alt,
            label: l10n.takePhoto,
            onTap: () => _pickImage(ImageSource.camera),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildSourceButton(
            icon: Icons.photo_library,
            label: l10n.gallery,
            onTap: () => _pickImage(ImageSource.gallery),
          ),
        ),
      ],
    );
  }

  Widget _buildSourceButton({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
  }) {
    return SizedBox(
      height: 100,
      child: Card(
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(16),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 40, color: Theme.of(context).colorScheme.primary),
              const SizedBox(height: 8),
              Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildImagePreview() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: Image.file(
        _imageFile!,
        height: 250,
        width: double.infinity,
        fit: BoxFit.cover,
      ),
    );
  }

  Widget _buildLocationInfo(AppLocalizations l10n) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            const Icon(Icons.location_on, color: Colors.red, size: 28),
            const SizedBox(width: 12),
            Expanded(
              child: _position != null
                  ? Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${l10n.latitude}: ${_position!.latitude.toStringAsFixed(6)}',
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                        Text(
                          '${l10n.longitude}: ${_position!.longitude.toStringAsFixed(6)}',
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                        Text(
                          '${l10n.accuracy}: ±${_position!.accuracy.toStringAsFixed(1)}m',
                          style: const TextStyle(color: Colors.grey),
                        ),
                      ],
                    )
                  : Text(l10n.gettingLocation),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState(AppLocalizations l10n) {
    return Container(
      height: 300,
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Theme.of(context).colorScheme.outline.withOpacity(0.3),
          width: 2,
          style: BorderStyle.solid,
        ),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.add_a_photo,
            size: 64,
            color: Theme.of(context).colorScheme.primary.withOpacity(0.5),
          ),
          const SizedBox(height: 16),
          Text(
            l10n.takePhotoHint,
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          Text(
            l10n.takePhotoSubhint,
            style: Theme.of(context).textTheme.bodySmall,
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildAnalyzeButton(AppLocalizations l10n) {
    return ElevatedButton.icon(
      onPressed: _isAnalyzing ? null : _analyzeImage,
      icon: const Icon(Icons.analytics),
      label: Text(l10n.analyze),
      style: ElevatedButton.styleFrom(
        backgroundColor: Theme.of(context).colorScheme.primary,
        foregroundColor: Theme.of(context).colorScheme.onPrimary,
        minimumSize: const Size(double.infinity, 56),
      ),
    );
  }

  Widget _buildAnalyzingIndicator(AppLocalizations l10n) {
    return Column(
      children: [
        const LinearProgressIndicator(),
        const SizedBox(height: 12),
        Text(
          l10n.analyzing,
          style: Theme.of(context).textTheme.bodyLarge,
          textAlign: TextAlign.center,
        ),
      ],
    );
  }

  Widget _buildResults(AppLocalizations l10n, ThemeData theme) {
    final result = _result!;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                Icon(Icons.check_circle, color: Colors.green, size: 28),
                const SizedBox(width: 8),
                Text(
                  l10n.analysisComplete,
                  style: theme.textTheme.titleLarge,
                ),
              ],
            ),
            const Divider(height: 24),

            // Mineral identification
            _buildResultRow(
              l10n.identifiedMineral,
              result.mineralName,
              Icons.diamond,
            ),

            // Confidence
            _buildConfidenceBar(l10n, result.confidence),

            const SizedBox(height: 12),

            // Rock type
            _buildResultRow(
              l10n.rockType,
              result.rockType,
              Icons.landscape,
            ),

            // Description
            const SizedBox(height: 12),
            Text(
              l10n.description,
              style: theme.textTheme.titleSmall?.copyWith(color: Colors.grey),
            ),
            const SizedBox(height: 4),
            Text(result.description, style: theme.textTheme.bodyLarge),

            // Economic indicator
            if (result.isEconomic) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.green.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.green.withOpacity(0.3)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.attach_money, color: Colors.green),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        l10n.economicMineralFound,
                        style: const TextStyle(
                          color: Colors.green,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],

            // Disclaimer
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.orange.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.info_outline, color: Colors.orange, size: 20),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      l10n.analysisDisclaimer,
                      style: const TextStyle(fontSize: 12, color: Colors.orange),
                    ),
                  ),
                ],
              ),
            ),

            // Save report button
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: () => _saveReport(l10n),
              icon: const Icon(Icons.save),
              label: Text(l10n.saveReport),
              style: OutlinedButton.styleFrom(
                minimumSize: const Size(double.infinity, 48),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildResultRow(String label, String value, IconData icon) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(icon, size: 20, color: Theme.of(context).colorScheme.primary),
          const SizedBox(width: 8),
          Text('$label: ', style: const TextStyle(color: Colors.grey)),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildConfidenceBar(AppLocalizations l10n, double confidence) {
    final color = confidence > 0.7
        ? Colors.green
        : confidence > 0.4
            ? Colors.orange
            : Colors.red;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(l10n.confidence, style: const TextStyle(color: Colors.grey)),
            Text(
              '${(confidence * 100).toStringAsFixed(0)}%',
              style: TextStyle(
                fontWeight: FontWeight.w700,
                fontSize: 18,
                color: color,
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: confidence,
            minHeight: 8,
            backgroundColor: color.withOpacity(0.2),
            valueColor: AlwaysStoppedAnimation(color),
          ),
        ),
      ],
    );
  }

  Widget _buildError(AppLocalizations l10n) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.red.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.red.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: Colors.red),
          const SizedBox(width: 12),
          Expanded(child: Text(_error!, style: const TextStyle(color: Colors.red))),
          IconButton(
            icon: const Icon(Icons.close, color: Colors.red),
            onPressed: () => setState(() => _error = null),
          ),
        ],
      ),
    );
  }

  Future<void> _pickImage(ImageSource source) async {
    try {
      final picked = await _picker.pickImage(
        source: source,
        maxWidth: 1920,
        maxHeight: 1920,
        imageQuality: 85,
      );

      if (picked != null) {
        setState(() {
          _imageFile = File(picked.path);
          _result = null;
          _error = null;
        });
        await _getCurrentLocation();
      }
    } catch (e) {
      setState(() => _error = 'Failed to pick image: $e');
    }
  }

  Future<void> _getCurrentLocation() async {
    try {
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        setState(() => _error = 'Location services disabled');
        return;
      }

      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
        if (permission == LocationPermission.denied) {
          setState(() => _error = 'Location permission denied');
          return;
        }
      }

      if (permission == LocationPermission.deniedForever) {
        setState(() => _error = 'Location permanently denied. Enable in Settings.');
        return;
      }

      final position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      );

      setState(() => _position = position);
    } catch (e) {
      setState(() => _error = 'Could not get location: $e');
    }
  }

  Future<void> _analyzeImage() async {
    if (_imageFile == null) return;

    setState(() {
      _isAnalyzing = true;
      _result = null;
      _error = null;
    });

    try {
      final sync = context.read<OfflineSyncService>();
      final api = context.read<ApiClient>();

      final observation = Observation(
        id: const Uuid().v4(),
        imagePath: _imageFile!.path,
        latitude: _position?.latitude,
        longitude: _position?.longitude,
        timestamp: DateTime.now(),
      );

      if (sync.isOnline) {
        // Send to API for analysis
        final result = await api.analyzeImage(observation);
        setState(() {
          _result = result;
          _isAnalyzing = false;
        });

        // Save to local DB
        await sync.saveObservation(observation.copyWith(result: result));
      } else {
        // Queue for later sync
        await sync.queueObservation(observation);
        setState(() {
          _isAnalyzing = false;
          _error = 'Saved offline. Will analyze when connected.';
        });
      }
    } catch (e) {
      setState(() {
        _isAnalyzing = false;
        _error = 'Analysis failed: $e';
      });
    }
  }

  Future<void> _saveReport(AppLocalizations l10n) async {
    if (_result == null) return;

    try {
      final sync = context.read<OfflineSyncService>();
      final observation = Observation(
        id: const Uuid().v4(),
        imagePath: _imageFile!.path,
        latitude: _position?.latitude,
        longitude: _position?.longitude,
        timestamp: DateTime.now(),
        result: _result,
      );

      await sync.saveObservation(observation);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(l10n.reportSaved)),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    }
  }
}
