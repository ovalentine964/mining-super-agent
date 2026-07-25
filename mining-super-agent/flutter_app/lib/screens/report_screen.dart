import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:share_plus/share_plus.dart';
import '../services/offline_sync.dart';
import '../services/api_client.dart';
import '../services/app_localizations.dart';
import '../models/observation.dart';

/// Report viewer — list of user's reports with PDF viewing and sharing.
class ReportScreen extends StatefulWidget {
  const ReportScreen({super.key});

  @override
  State<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends State<ReportScreen> {
  List<Observation> _observations = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadReports();
  }

  Future<void> _loadReports() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final sync = context.read<OfflineSyncService>();
      final reports = await sync.getSavedObservations();
      setState(() {
        _observations = reports;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _error = 'Failed to load reports: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.myReports),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadReports),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _buildError(l10n)
              : _observations.isEmpty
                  ? _buildEmptyState(l10n)
                  : RefreshIndicator(
                      onRefresh: _loadReports,
                      child: ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: _observations.length,
                        itemBuilder: (context, index) {
                          return _buildReportCard(_observations[index], l10n);
                        },
                      ),
                    ),
    );
  }

  Widget _buildEmptyState(AppLocalizations l10n) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.description_outlined,
            size: 80,
            color: Theme.of(context).colorScheme.primary.withOpacity(0.3),
          ),
          const SizedBox(height: 16),
          Text(
            l10n.noReports,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: Colors.grey,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            l10n.noReportsHint,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.grey,
                ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildReportCard(Observation obs, AppLocalizations l10n) {
    final result = obs.result;
    final hasResult = result != null;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: () => _showReportDetail(obs, l10n),
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              // Thumbnail
              Container(
                width: 64,
                height: 64,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  color: Theme.of(context).colorScheme.surfaceContainerHighest,
                ),
                child: obs.imagePath != null
                    ? ClipRRect(
                        borderRadius: BorderRadius.circular(12),
                        child: Image.file(
                          File(obs.imagePath!),
                          fit: BoxFit.cover,
                          errorBuilder: (_, __, ___) => const Icon(Icons.image, size: 32),
                        ),
                      )
                    : const Icon(Icons.landscape, size: 32),
              ),
              const SizedBox(width: 12),

              // Info
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      hasResult ? result!.mineralName : l10n.pendingAnalysis,
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 16,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _formatDate(obs.timestamp),
                      style: const TextStyle(color: Colors.grey, fontSize: 13),
                    ),
                    if (obs.latitude != null) ...[
                      const SizedBox(height: 2),
                      Text(
                        '📍 ${obs.latitude!.toStringAsFixed(4)}, ${obs.longitude!.toStringAsFixed(4)}',
                        style: const TextStyle(color: Colors.grey, fontSize: 12),
                      ),
                    ],
                    if (hasResult) ...[
                      const SizedBox(height: 4),
                      _buildConfidenceChip(result!.confidence),
                    ],
                  ],
                ),
              ),

              // Actions
              PopupMenuButton<String>(
                onSelected: (value) => _handleAction(value, obs, l10n),
                itemBuilder: (_) => [
                  PopupMenuItem(value: 'view', child: Text(l10n.view)),
                  PopupMenuItem(value: 'share', child: Text(l10n.share)),
                  PopupMenuItem(value: 'delete', child: Text(l10n.delete)),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildConfidenceChip(double confidence) {
    final color = confidence > 0.7
        ? Colors.green
        : confidence > 0.4
            ? Colors.orange
            : Colors.red;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        '${(confidence * 100).toStringAsFixed(0)}% confidence',
        style: TextStyle(
          color: color,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  Widget _buildError(AppLocalizations l10n) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_outline, size: 64, color: Colors.red),
          const SizedBox(height: 16),
          Text(_error!),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: _loadReports,
            child: Text(l10n.retry),
          ),
        ],
      ),
    );
  }

  void _showReportDetail(Observation obs, AppLocalizations l10n) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return DraggableScrollableSheet(
          initialChildSize: 0.7,
          maxChildSize: 0.95,
          minChildSize: 0.3,
          expand: false,
          builder: (context, scrollController) {
            return SingleChildScrollView(
              controller: scrollController,
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Handle
                  Center(
                    child: Container(
                      width: 40,
                      height: 4,
                      decoration: BoxDecoration(
                        color: Colors.grey[300],
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Image
                  if (obs.imagePath != null)
                    ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: Image.file(
                        File(obs.imagePath!),
                        height: 200,
                        width: double.infinity,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => Container(
                          height: 200,
                          color: Colors.grey[200],
                          child: const Center(child: Icon(Icons.broken_image, size: 48)),
                        ),
                      ),
                    ),

                  const SizedBox(height: 16),

                  // Result details
                  if (obs.result != null) ...[
                    Text(
                      obs.result!.mineralName,
                      style: Theme.of(context).textTheme.headlineMedium,
                    ),
                    const SizedBox(height: 8),
                    Text(obs.result!.description),
                    const SizedBox(height: 16),
                    _buildDetailRow(l10n.rockType, obs.result!.rockType),
                    _buildDetailRow(l10n.confidence,
                        '${(obs.result!.confidence * 100).toStringAsFixed(0)}%'),
                    if (obs.result!.isEconomic)
                      _buildDetailRow(l10n.economicValue, l10n.economicYes),
                  ] else ...[
                    Text(
                      l10n.pendingAnalysis,
                      style: Theme.of(context).textTheme.headlineMedium,
                    ),
                    const SizedBox(height: 8),
                    Text(l10n.reportWillAnalyze),
                  ],

                  // Location
                  if (obs.latitude != null) ...[
                    const SizedBox(height: 16),
                    _buildDetailRow(l10n.latitude,
                        obs.latitude!.toStringAsFixed(6)),
                    _buildDetailRow(l10n.longitude,
                        obs.longitude!.toStringAsFixed(6)),
                  ],

                  // Timestamp
                  const SizedBox(height: 8),
                  _buildDetailRow(l10n.date, _formatDate(obs.timestamp)),

                  // Actions
                  const SizedBox(height: 24),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () {
                            Share.share(
                              'Mining Report: ${obs.result?.mineralName ?? "Pending"}\n'
                              'Location: ${obs.latitude}, ${obs.longitude}\n'
                              'Date: ${_formatDate(obs.timestamp)}',
                            );
                          },
                          icon: const Icon(Icons.share),
                          label: Text(l10n.share),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: () {
                            // TODO: Generate and view PDF
                            Navigator.pop(context);
                          },
                          icon: const Icon(Icons.picture_as_pdf),
                          label: Text(l10n.viewPdf),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.grey)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }

  void _handleAction(String action, Observation obs, AppLocalizations l10n) {
    switch (action) {
      case 'view':
        _showReportDetail(obs, l10n);
        break;
      case 'share':
        Share.share(
          'Mining Report: ${obs.result?.mineralName ?? "Pending"}\n'
          'Date: ${_formatDate(obs.timestamp)}',
        );
        break;
      case 'delete':
        _confirmDelete(obs, l10n);
        break;
    }
  }

  void _confirmDelete(Observation obs, AppLocalizations l10n) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(l10n.deleteReport),
        content: Text(l10n.deleteReportConfirm),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(l10n.cancel),
          ),
          TextButton(
            onPressed: () async {
              Navigator.pop(context);
              final sync = context.read<OfflineSyncService>();
              await sync.deleteObservation(obs.id);
              _loadReports();
            },
            child: Text(l10n.delete, style: const TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }

  String _formatDate(DateTime date) {
    return '${date.day}/${date.month}/${date.year} ${date.hour}:${date.minute.toString().padLeft(2, '0')}';
  }
}
