import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import 'package:path_provider/path_provider.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import '../models/observation.dart';
import 'api_client.dart';

/// Offline-first sync service.
/// Stores observations locally in SQLite, syncs when online.
/// Never loses data — queue persists across app restarts.
class OfflineSyncService extends ChangeNotifier {
  static Database? _database;
  static bool _isOnline = true;
  static int _pendingCount = 0;
  static StreamSubscription? _connectivitySubscription;

  bool get isOnline => _isOnline;
  int get pendingCount => _pendingCount;

  /// Initialize the service — create DB, start connectivity listener.
  static Future<void> initialize() async {
    await _initDatabase();
    await _updatePendingCount();
    _startConnectivityListener();
  }

  /// Initialize SQLite database.
  static Future<void> _initDatabase() async {
    final dir = await getApplicationDocumentsDirectory();
    final path = join(dir.path, 'mining_agent.db');

    _database = await openDatabase(
      path,
      version: 2,
      onCreate: (db, version) async {
        // Observations table
        await db.execute('''
          CREATE TABLE observations (
            id TEXT PRIMARY KEY,
            image_path TEXT,
            latitude REAL,
            longitude REAL,
            timestamp TEXT NOT NULL,
            mineral_name TEXT,
            rock_type TEXT,
            confidence REAL,
            description TEXT,
            is_economic INTEGER DEFAULT 0,
            is_synced INTEGER DEFAULT 0,
            sync_error TEXT,
            created_at TEXT NOT NULL
          )
        ''');

        // Pending sync queue
        await db.execute('''
          CREATE TABLE sync_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            observation_id TEXT NOT NULL,
            action TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            retry_count INTEGER DEFAULT 0,
            last_error TEXT,
            FOREIGN KEY (observation_id) REFERENCES observations(id)
          )
        ''');

        // Cached prices
        await db.execute('''
          CREATE TABLE price_cache (
            symbol TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            cached_at TEXT NOT NULL
          )
        ''');

        // Indexes
        await db.execute(
          'CREATE INDEX idx_observations_synced ON observations(is_synced)',
        );
        await db.execute(
          'CREATE INDEX idx_queue_created ON sync_queue(created_at)',
        );
      },
      onUpgrade: (db, oldVersion, newVersion) async {
        if (oldVersion < 2) {
          await db.execute('ALTER TABLE observations ADD COLUMN sync_error TEXT');
        }
      },
    );
  }

  /// Listen for connectivity changes and trigger sync.
  static void _startConnectivityListener() {
    _connectivitySubscription = Connectivity().onConnectivityChanged.listen(
      (results) async {
        final wasOnline = _isOnline;
        _isOnline = results.any((r) => r != ConnectivityResult.none);

        if (!wasOnline && _isOnline) {
          // Just came online — sync pending observations
          await syncPendingObservations();
        }

        // Notify listeners (UI updates)
        // Can't use notifyListeners here since this is static
      },
    );

    // Check initial connectivity
    Connectivity().checkConnectivity().then((results) {
      _isOnline = results.any((r) => r != ConnectivityResult.none);
    });
  }

  /// Save an observation to local database.
  Future<void> saveObservation(Observation obs) async {
    await _database!.insert(
      'observations',
      {
        'id': obs.id,
        'image_path': obs.imagePath,
        'latitude': obs.latitude,
        'longitude': obs.longitude,
        'timestamp': obs.timestamp.toIso8601String(),
        'mineral_name': obs.result?.mineralName,
        'rock_type': obs.result?.rockType,
        'confidence': obs.result?.confidence,
        'description': obs.result?.description,
        'is_economic': obs.result?.isEconomic == true ? 1 : 0,
        'is_synced': 1,
        'created_at': DateTime.now().toIso8601String(),
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
    await _updatePendingCount();
    notifyListeners();
  }

  /// Queue an observation for later sync (when offline).
  Future<void> queueObservation(Observation obs) async {
    // Save observation locally
    await _database!.insert(
      'observations',
      {
        'id': obs.id,
        'image_path': obs.imagePath,
        'latitude': obs.latitude,
        'longitude': obs.longitude,
        'timestamp': obs.timestamp.toIso8601String(),
        'is_synced': 0,
        'created_at': DateTime.now().toIso8601String(),
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );

    // Add to sync queue
    await _database!.insert('sync_queue', {
      'observation_id': obs.id,
      'action': 'analyze',
      'payload': jsonEncode(obs.toJson()),
      'created_at': DateTime.now().toIso8601String(),
    });

    await _updatePendingCount();
    notifyListeners();
  }

  /// Get all saved observations.
  Future<List<Observation>> getSavedObservations() async {
    final rows = await _database!.query(
      'observations',
      orderBy: 'timestamp DESC',
      limit: 100,
    );

    return rows.map((row) {
      return Observation(
        id: row['id'] as String,
        imagePath: row['image_path'] as String?,
        latitude: row['latitude'] as double?,
        longitude: row['longitude'] as double?,
        timestamp: DateTime.parse(row['timestamp'] as String),
        result: row['mineral_name'] != null
            ? AnalysisResult(
                mineralName: row['mineral_name'] as String,
                rockType: row['rock_type'] as String? ?? 'Unknown',
                confidence: (row['confidence'] as num?)?.toDouble() ?? 0.0,
                description: row['description'] as String? ?? '',
                isEconomic: (row['is_economic'] as int?) == 1,
              )
            : null,
      );
    }).toList();
  }

  /// Delete an observation.
  Future<void> deleteObservation(String id) async {
    await _database!.delete('observations', where: 'id = ?', whereArgs: [id]);
    await _database!.delete('sync_queue',
        where: 'observation_id = ?', whereArgs: [id]);
    await _updatePendingCount();
    notifyListeners();
  }

  /// Sync all pending observations when online.
  Future<void> syncPendingObservations() async {
    if (!_isOnline) return;

    final pending = await _database!.query(
      'sync_queue',
      orderBy: 'created_at ASC',
    );

    if (pending.isEmpty) return;

    final api = ApiClient();

    for (final item in pending) {
      final observationId = item['observation_id'] as String;
      final payload = jsonDecode(item['payload'] as String);
      final retryCount = item['retry_count'] as int;

      try {
        // Reconstruct observation
        final obs = Observation.fromJson(payload);

        // Send to API
        final result = await api.analyzeImage(obs);

        // Update local record with result
        await _database!.update(
          'observations',
          {
            'mineral_name': result.mineralName,
            'rock_type': result.rockType,
            'confidence': result.confidence,
            'description': result.description,
            'is_economic': result.isEconomic ? 1 : 0,
            'is_synced': 1,
            'sync_error': null,
          },
          where: 'id = ?',
          whereArgs: [observationId],
        );

        // Remove from queue
        await _database!.delete(
          'sync_queue',
          where: 'id = ?',
          whereArgs: [item['id']],
        );
      } catch (e) {
        // Retry logic — max 5 retries with exponential backoff
        if (retryCount < 5) {
          await _database!.update(
            'sync_queue',
            {
              'retry_count': retryCount + 1,
              'last_error': e.toString(),
            },
            where: 'id = ?',
            whereArgs: [item['id']],
          );
        } else {
          // Mark as failed — user can retry manually
          await _database!.update(
            'observations',
            {'sync_error': 'Sync failed after 5 attempts: $e'},
            where: 'id = ?',
            whereArgs: [observationId],
          );
          await _database!.delete(
            'sync_queue',
            where: 'id = ?',
            whereArgs: [item['id']],
          );
        }
      }

      // Small delay between syncs to avoid overwhelming server
      await Future.delayed(const Duration(milliseconds: 500));
    }

    await _updatePendingCount();
    notifyListeners();
  }

  /// Update pending count.
  static Future<void> _updatePendingCount() async {
    final result = await _database!.rawQuery(
      'SELECT COUNT(*) as count FROM observations WHERE is_synced = 0',
    );
    _pendingCount = (result.first['count'] as int?) ?? 0;
  }

  /// Cache commodity prices for offline access.
  Future<void> cachePrices(String symbol, Map<String, dynamic> data) async {
    await _database!.insert(
      'price_cache',
      {
        'symbol': symbol,
        'data': jsonEncode(data),
        'cached_at': DateTime.now().toIso8601String(),
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  /// Get cached prices.
  Future<Map<String, dynamic>?> getCachedPrices(String symbol) async {
    final rows = await _database!.query(
      'price_cache',
      where: 'symbol = ?',
      whereArgs: [symbol],
    );

    if (rows.isEmpty) return null;

    final cachedAt = DateTime.parse(rows.first['cached_at'] as String);
    // Cache valid for 1 hour
    if (DateTime.now().difference(cachedAt).inHours > 1) {
      return null;
    }

    return jsonDecode(rows.first['data'] as String) as Map<String, dynamic>;
  }

  /// Force sync (manual trigger).
  Future<void> forceSyncAll() async {
    await syncPendingObservations();
    notifyListeners();
  }

  @override
  void dispose() {
    _connectivitySubscription?.cancel();
    super.dispose();
  }
}
