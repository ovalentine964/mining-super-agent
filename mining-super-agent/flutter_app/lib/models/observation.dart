/// Observation model — represents a miner's photo observation.
class Observation {
  final String id;
  final String? imagePath;
  final double? latitude;
  final double? longitude;
  final DateTime timestamp;
  final AnalysisResult? result;

  Observation({
    required this.id,
    this.imagePath,
    this.latitude,
    this.longitude,
    required this.timestamp,
    this.result,
  });

  Observation copyWith({
    String? imagePath,
    double? latitude,
    double? longitude,
    DateTime? timestamp,
    AnalysisResult? result,
  }) {
    return Observation(
      id: id,
      imagePath: imagePath ?? this.imagePath,
      latitude: latitude ?? this.latitude,
      longitude: longitude ?? this.longitude,
      timestamp: timestamp ?? this.timestamp,
      result: result ?? this.result,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'image_path': imagePath,
      'latitude': latitude,
      'longitude': longitude,
      'timestamp': timestamp.toIso8601String(),
      'result': result?.toJson(),
    };
  }

  factory Observation.fromJson(Map<String, dynamic> json) {
    return Observation(
      id: json['id'] as String,
      imagePath: json['image_path'] as String?,
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
      timestamp: DateTime.parse(json['timestamp'] as String),
      result: json['result'] != null
          ? AnalysisResult.fromJson(json['result'] as Map<String, dynamic>)
          : null,
    );
  }
}

/// Analysis result from the AI backend.
class AnalysisResult {
  final String mineralName;
  final String rockType;
  final double confidence;
  final String description;
  final bool isEconomic;

  AnalysisResult({
    required this.mineralName,
    required this.rockType,
    required this.confidence,
    required this.description,
    this.isEconomic = false,
  });

  Map<String, dynamic> toJson() {
    return {
      'mineral_name': mineralName,
      'rock_type': rockType,
      'confidence': confidence,
      'description': description,
      'is_economic': isEconomic,
    };
  }

  factory AnalysisResult.fromJson(Map<String, dynamic> json) {
    return AnalysisResult(
      mineralName: json['mineral_name'] as String? ?? 'Unknown',
      rockType: json['rock_type'] as String? ?? 'Unknown',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      description: json['description'] as String? ?? '',
      isEconomic: json['is_economic'] as bool? ?? false,
    );
  }
}
