# Flutter-specific ProGuard rules
-keep class io.flutter.** { *; }
-keep class io.flutter.plugins.** { *; }
-keep class com.miningsuperagent.** { *; }

# Keep SQLite
-keep class org.sqlite.** { *; }
-keep class org.sqlite.database.** { *; }

# Keep geolocator
-keep class com.baseflow.geolocator.** { *; }

# Keep camera
-keep class io.flutter.plugins.camera.** { *; }
