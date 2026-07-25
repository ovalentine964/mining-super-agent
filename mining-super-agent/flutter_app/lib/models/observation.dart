class Observation {
  final String? id;
  final String? title;
  final String? description;
  final String? rockType;
  final String? color;
  final String? luster;
  final double? hardness;
  final double? latitude;
  final double? longitude;
  final String? photoPath;
  final DateTime observedAt;
  final bool synced;

  Observation({
    this.id,
    this.title,
    this.description,
    this.rockType,
    this.color,
    this.luster,
    this.hardness,
    this.latitude,
    this.longitude,
    this.photoPath,
    required this.observedAt,
    this.synced = false,
  });

  Map<String, dynamic> toJson() => {
    'id': id,
    'title': title,
    'description': description,
    'rock_type': rockType,
    'color': color,
    'luster': luster,
    'hardness': hardness,
    'latitude': latitude,
    'longitude': longitude,
    'photo_path': photoPath,
    'observed_at': observedAt.toIso8601String(),
    'synced': synced,
  };
}
