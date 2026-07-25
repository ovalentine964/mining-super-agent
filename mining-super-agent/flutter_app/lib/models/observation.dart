class Observation {
  final int? id;
  final String? title;
  final String? description;
  final String? rockType;
  final String? color;
  final String? luster;
  final double? hardness;
  final double? latitude;
  final double? longitude;
  final String? photoPath;
  final String? mineral;
  final double? confidence;
  final String? pdfPath;
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
    this.mineral,
    this.confidence,
    this.pdfPath,
    required this.observedAt,
    this.synced = false,
  });

  Map<String, dynamic> toMap() => {
    if (id != null) 'id': id,
    'title': title ?? '',
    'description': description ?? '',
    'rock_type': rockType ?? '',
    'color': color ?? '',
    'luster': luster ?? '',
    'hardness': hardness ?? 0.0,
    'latitude': latitude ?? 0.0,
    'longitude': longitude ?? 0.0,
    'photo_path': photoPath ?? '',
    'mineral': mineral ?? '',
    'confidence': confidence ?? 0.0,
    'pdf_path': pdfPath ?? '',
    'observed_at': observedAt.toIso8601String(),
    'synced': synced ? 1 : 0,
  };

  factory Observation.fromMap(Map<String, dynamic> map) => Observation(
    id: map['id'] as int?,
    title: map['title'] as String?,
    description: map['description'] as String?,
    rockType: map['rock_type'] as String?,
    color: map['color'] as String?,
    luster: map['luster'] as String?,
    hardness: (map['hardness'] as num?)?.toDouble(),
    latitude: (map['latitude'] as num?)?.toDouble(),
    longitude: (map['longitude'] as num?)?.toDouble(),
    photoPath: map['photo_path'] as String?,
    mineral: map['mineral'] as String?,
    confidence: (map['confidence'] as num?)?.toDouble(),
    pdfPath: map['pdf_path'] as String?,
    observedAt: DateTime.parse(map['observed_at'] as String),
    synced: (map['synced'] as int?) == 1,
  );

  Map<String, dynamic> toJson() => toMap();

  Observation copyWith({
    int? id,
    String? title,
    String? description,
    String? rockType,
    String? mineral,
    double? confidence,
    String? pdfPath,
    bool? synced,
  }) => Observation(
    id: id ?? this.id,
    title: title ?? this.title,
    description: description ?? this.description,
    rockType: rockType ?? this.rockType,
    color: color,
    luster: luster,
    hardness: hardness,
    latitude: latitude,
    longitude: longitude,
    photoPath: photoPath,
    mineral: mineral ?? this.mineral,
    confidence: confidence ?? this.confidence,
    pdfPath: pdfPath ?? this.pdfPath,
    observedAt: observedAt,
    synced: synced ?? this.synced,
  );
}
