import 'dart:async';
import 'package:connectivity_plus/connectivity_plus.dart';
import '../models/observation.dart';

class OfflineSyncService {
  final List<Observation> _pendingQueue = [];
  Timer? _syncTimer;
  bool _isSyncing = false;

  List<Observation> get pendingObservations => List.unmodifiable(_pendingQueue);

  void start() {
    // Listen for connectivity changes
    Connectivity().onConnectivityChanged.listen((result) {
      if (result != ConnectivityResult.none) {
        _syncPending();
      }
    });

    // Periodic sync attempt
    _syncTimer = Timer.periodic(const Duration(minutes: 5), (_) => _syncPending());
  }

  void stop() {
    _syncTimer?.cancel();
  }

  void addToQueue(Observation observation) {
    _pendingQueue.add(observation);
    _syncPending();
  }

  Future<void> _syncPending() async {
    if (_isSyncing || _pendingQueue.isEmpty) return;
    _isSyncing = true;

    try {
      final connectivity = await Connectivity().checkConnectivity();
      if (connectivity == ConnectivityResult.none) {
        _isSyncing = false;
        return;
      }

      // TODO: Upload to server
      // For now, just clear the queue after a delay
      await Future.delayed(const Duration(seconds: 1));

      // In production: upload each observation, mark as synced on success
      // _pendingQueue.removeWhere((o) => uploadSuccess);

    } finally {
      _isSyncing = false;
    }
  }
}
