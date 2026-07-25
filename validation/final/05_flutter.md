# Final Council 5: Flutter Mobile App — Full Repo Review

**Reviewed:** `/home/work/.openclaw/workspace/mining-super-agent/flutter_app/`
**Date:** 2026-07-25

---

## Criteria Assessment

| # | Criterion | Status | Details |
|---|-----------|--------|---------|
| 1 | Flutter/Dart (not React Native) | ✅ | Pure Flutter 3.2+ / Dart app. `pubspec.yaml` uses Flutter SDK, Material 3 design. No React Native contamination. |
| 2 | Offline-first (SQLite + sync) | ❌ **Partial** | `sqflite: ^2.3.0` is declared in pubspec but **never imported or used** in any `.dart` file. `OfflineSyncService` exists but uses an **in-memory `List<Observation>`** — data is lost on app restart. The `_syncPending()` method is a TODO stub that clears the queue after a 1s delay. No actual database schema, no persistence, no real sync. |
| 3 | Swahili-first (5 languages) | ❌ **Partial** | Default locale is Swahili ✅. ARB files exist for **3 languages** (English, Swahili, Luo) — not 5. Missing Kikuyu and Kalenjin (or other required Kenyan languages). `AppLocalizations` has a parallel hardcoded map that duplicates only 7 keys vs 80+ in ARB files — inconsistent. `flutter_localizations` is declared but never wired (no `localizationsDelegates` in `MaterialApp`). |
| 4 | Icon-driven (48dp+ for illiterate users) | ✅ | Home screen menu icons are **48dp** (`Icon(icon, size: 48)`). Photo placeholder is **64dp**. Report empty state is **64dp**. All interactive buttons use `ElevatedButton.icon` with icon+text. Good visual hierarchy for low-literacy users. |
| 5 | GPS auto-capture | ✅ | Uses `geolocator: ^11.0.0`. `PhotoScreen._takePhoto()` auto-requests permission and captures GPS coordinates after taking a photo. `Observation` model includes `latitude`/`longitude` fields. Graceful fallback if GPS unavailable. |
| 6 | Camera integration | ✅ | Uses `image_picker` + `camera` packages. `PhotoScreen` captures from camera with `ImageSource.camera`, maxWidth 1920. Image preview with `Image.file()`. |
| 7 | PDF viewer (lightweight) | ❌ | No PDF viewer dependency in `pubspec.yaml`. No PDF rendering code anywhere. `ReportScreen` is an empty stub — just "No reports yet" placeholder. The ARB files reference "View PDF" strings but no implementation exists. |
| 8 | CI/CD pipeline | ❌ | `.github/workflows/` directory exists but is **completely empty** — no workflow files. No `Fastfile`, no `codemagic.yaml`, no `bitrise.yml`, no build/release automation of any kind. |
| 9 | APK size target (<15MB) | ⚠️ **Indeterminate** | No build artifacts or size analysis available. Dependencies are lightweight (`sqflite`, `geolocator`, `image_picker`, `camera`), so target is achievable if `camera` plugin is properly configured. Cannot verify without actual build. |

---

## Code Quality Issues

1. **Dead code:** `sqflite` imported but unused. `camera` package declared but only `image_picker` is used for camera access.
2. **Localization broken:** `MaterialApp` has `supportedLocales` but no `localizationsDelegates` — ARB files are never loaded. Only the hardcoded `AppLocalizations` map works, and it covers just 7 strings.
3. **No data persistence:** Offline sync is in-memory only. App loses all data on restart. No SQLite tables created.
4. **Stub screens:** `ReportScreen` is non-functional. `PriceScreen` uses hardcoded mock data.
5. **No tests:** Zero test files found.
6. **Duplicate localization:** Both ARB files and hardcoded `_localizedValues` map exist — maintenance hazard.

---

## Verdict

This is a **well-structured scaffold** with the right architectural choices (Provider state management, proper model classes, service layer separation, Material 3 theming) but **insufficient implementation depth**. The framework is solid — GPS, camera, localization setup, and icon-driven UI are all correctly architected. However, critical features (offline persistence, PDF generation, real sync, CI/CD) remain unimplemented TODOs.

## Score: 4/10

**Breakdown:**
- Flutter/Dart: 1/1 ✅
- Offline-first (SQLite+sync): 0/1 (in-memory only, no SQLite)
- Swahili-first (5 langs): 0.5/1 (3/5 languages, broken l10n wiring)
- Icon-driven (48dp+): 1/1 ✅
- GPS auto-capture: 1/1 ✅
- Camera integration: 1/1 ✅
- PDF viewer: 0/1 (not implemented)
- CI/CD pipeline: 0/1 (empty directory)
- APK size: 0.5/1 (likely achievable but unverified)
- Code quality bonus: -1 (dead deps, broken l10n, no tests, stub screens)

**Final: 4/10** — Good skeleton, needs full implementation pass.
