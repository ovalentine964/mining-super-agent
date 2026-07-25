import 'dart:async';
import 'package:connectivity_plus/connectivity_plus.dart';
import '../models/observation.dart';
import 'local_db.dart';
import 'api_client.dart';

class OfflineSyncService {
  static final OfflineSyncService instance = OfflineSyncService._init();
  OfflineSyncService._init();

  Timer? _syncTimer;
  bool _isSyncing = false;
  final _db = LocalDatabase.instance;
  final _api = ApiClient();

  final StreamController<int> _pendingController = StreamController<int>.broadcast();
  Stream<int> get pendingCountStream => _pendingController.stream;

  void start() {
    // Listen for connectivity changes
    Connectivity().onConnectivityChanged.listen((result) {
      if (result != ConnectivityResult.none) {
        syncPending();
      }
    });

    // Periodic sync attempt
    _syncTimer = Timer.periodic(const Duration(minutes: 5), (_) => syncPending());

    // Initial count broadcast
    _broadcastPending();
  }

  void stop() {
    _syncTimer?.cancel();
  }

  Future<int> saveObservation(Observation obs) async {
    final id = await _db.insertObservation(obs);
    _broadcastPending();
    // Try to sync immediately
    syncPending();
    return id;
  }

  Future<List<Observation>> getAllObservations() async {
    return await _db.getAllObservations();
  }

  Future<int> getPendingCount() async {
    return await _db.getPendingCount();
  }

  Future<void> deleteObservation(int id) async {
    await _db.deleteObservation(id);
    _broadcastPending();
  }

  Future<void> syncPending() async {
    if (_isSyncing) return;
    _isSyncing = true;

    try {
      final connectivity = await Connectivity().checkConnectivity();
      if (connectivity == ConnectivityResult.none) {
        _isSyncing = false;
        return;
      }

      final pending = await _db.getUnsyncedObservations();
      for (final obs in pending) {
        try {
          // Upload observation to server
          await _api.post('/api/v1/observations', obs.toJson());
          await _db.markSynced(obs.id!);
        } catch (e) {
          // Upload failed — will retry next sync cycle
          break;
        }
      }

      _broadcastPending();
    } finally {
      _isSyncing = false;
    }
  }

  Future<void> _broadcastPending() async {
    final count = await _db.getPendingCount();
    _pendingController.add(count);
  }
}
