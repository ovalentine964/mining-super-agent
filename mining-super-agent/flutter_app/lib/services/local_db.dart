import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import '../models/observation.dart';

class LocalDatabase {
  static final LocalDatabase instance = LocalDatabase._init();
  static Database? _database;

  LocalDatabase._init();

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDB('mining_agent.db');
    return _database!;
  }

  Future<Database> _initDB(String filePath) async {
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, filePath);
    return await openDatabase(path, version: 1, onCreate: _createDB);
  }

  Future<void> _createDB(Database db, int version) async {
    await db.execute('''
      CREATE TABLE observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL DEFAULT '',
        description TEXT NOT NULL DEFAULT '',
        rock_type TEXT NOT NULL DEFAULT '',
        color TEXT NOT NULL DEFAULT '',
        luster TEXT NOT NULL DEFAULT '',
        hardness REAL NOT NULL DEFAULT 0.0,
        latitude REAL NOT NULL DEFAULT 0.0,
        longitude REAL NOT NULL DEFAULT 0.0,
        photo_path TEXT NOT NULL DEFAULT '',
        mineral TEXT NOT NULL DEFAULT '',
        confidence REAL NOT NULL DEFAULT 0.0,
        pdf_path TEXT NOT NULL DEFAULT '',
        observed_at TEXT NOT NULL,
        synced INTEGER NOT NULL DEFAULT 0
      )
    ''');
  }

  // --- CRUD ---

  Future<int> insertObservation(Observation obs) async {
    final db = await database;
    return await db.insert('observations', obs.toMap());
  }

  Future<List<Observation>> getAllObservations() async {
    final db = await database;
    final maps = await db.query('observations', orderBy: 'observed_at DESC');
    return maps.map((m) => Observation.fromMap(m)).toList();
  }

  Future<Observation?> getObservation(int id) async {
    final db = await database;
    final maps = await db.query('observations', where: 'id = ?', whereArgs: [id]);
    if (maps.isEmpty) return null;
    return Observation.fromMap(maps.first);
  }

  Future<int> updateObservation(Observation obs) async {
    final db = await database;
    return await db.update(
      'observations',
      obs.toMap(),
      where: 'id = ?',
      whereArgs: [obs.id],
    );
  }

  Future<int> deleteObservation(int id) async {
    final db = await database;
    return await db.delete('observations', where: 'id = ?', whereArgs: [id]);
  }

  Future<List<Observation>> getUnsyncedObservations() async {
    final db = await database;
    final maps = await db.query(
      'observations',
      where: 'synced = ?',
      whereArgs: [0],
      orderBy: 'observed_at ASC',
    );
    return maps.map((m) => Observation.fromMap(m)).toList();
  }

  Future<void> markSynced(int id) async {
    final db = await database;
    await db.update(
      'observations',
      {'synced': 1},
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  Future<int> getPendingCount() async {
    final db = await database;
    final result = await db.rawQuery('SELECT COUNT(*) as cnt FROM observations WHERE synced = 0');
    return Sqflite.firstIntValue(result) ?? 0;
  }

  Future<void> close() async {
    final db = await database;
    db.close();
  }
}
