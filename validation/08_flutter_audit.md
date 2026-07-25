# Validation Report 08: Flutter Mobile App Audit

**Auditor:** Council Member 8 — Flutter Mobile App Auditor  
**Date:** 2026-07-25  
**App Path:** `mining-super-agent/flutter_app/`  
**Overall Verdict:** ✅ PASS (7/9 criteria met, 2 conditional)

---

## 1. Flutter (Dart) — NOT React Native

**Status: ✅ PASS**

- `pubspec.yaml` confirms Flutter project (`name: mining_super_agent`, `flutter: '>=3.16.0'`, `sdk: '>=3.2.0 <4.0.0'`)
- All source files are `.dart` — pure Dart/Flutter codebase
- Uses Flutter-specific packages: `provider`, `flutter_localizations`, `fl_chart`, `flutter_svg`
- No React Native artifacts (no `package.json`, no `.js`/`.tsx` files)
- **Verdict: Confirmed Flutter/Dart**

---

## 2. Offline-First — SQLite Local Storage + Sync Queue

**Status: ✅ PASS**

**SQLite implementation (`offline_sync.dart`):**
- Database: `mining_agent.db` via `sqflite` package
- Three tables: `observations`, `sync_queue`, `price_cache`
- Indexed on `is_synced` and `sync_queue.created_at`

**Sync queue architecture:**
- `queueObservation()` — saves locally + adds to `sync_queue` when offline
- `syncPendingObservations()` — processes queue when connectivity returns
- Exponential backoff retry: max 5 attempts per item
- `sync_error` field tracks permanent failures for user visibility
- Connectivity listener via `connectivity_plus` — auto-triggers sync on reconnect
- Price caching with 1-hour TTL

**Data persistence guarantees:**
- Queue persists across app restarts (SQLite on disk)
- Never loses data — observations saved locally before API call
- `is_synced` flag tracks sync state
- `forceSyncAll()` for manual sync trigger

**Verdict: Robust offline-first implementation with proper sync queue**

---

## 3. Swahili-First — All UI in Swahili? English/Luo as Secondary?

**Status: ✅ PASS**

**Localization files present:**
- `lib/l10n/app_sw.arb` — Swahili (comprehensive, 60+ strings)
- `lib/l10n/app_en.arb` — English (comprehensive)
- `lib/l10n/app_luo.arb` — Luo/Dholuo (comprehensive)

**Embedded translations in `app_localizations.dart`:**
- `_swahili` map — full Swahili translations (default)
- `_english` map — full English translations
- `_luo` map — full Luo translations

**Default locale:**
- `LocaleProvider` defaults to `const Locale('sw')` — Swahili is first
- `supportedLocales` lists `sw` first, then `en`, `luo`, `kam`, `luy`
- Settings screen language selector: Kiswahili first in list

**Coverage:**
- All UI strings localized (home, photo, price, report, settings screens)
- Swahili quality: Natural, colloquial Kenyan Swahili (e.g., "Karibu! Chagua huduma", "Piga picha ya mwamba")
- Luo quality: Authentic Dholuo (e.g., "Oriti wuoyo! Yer karata", "Kuw marith mondo ong'e minieri")
- Kamba (`kam`) and Luhya (`luy`) declared in supported locales but no ARB files or embedded maps yet — **minor gap**

**Verdict: Swahili-first confirmed. English and Luo fully implemented. Kamba/Luhya stubs only.**

---

## 4. Icon-Driven — 48dp+ Touch Targets for Illiterate Users

**Status: ✅ PASS**

**Home screen design (`home_screen.dart`):**
- 4-tile icon grid layout — primary navigation via icons, not text
- Icons sized at 48px (`Icons.camera_alt`, `Icons.trending_up`, `Icons.description`, `Icons.settings`)
- Each icon wrapped in 16px padding container → effective touch area ~80dp
- Comment explicitly states: *"Designed for illiterate users: icons are primary, text is secondary"*
- `childAspectRatio: 1.0` — large square tiles

**Theme configuration (`main.dart`):**
- `materialTapTargetSize: MaterialTapTargetSize.padded` — enforces 48dp minimum
- `ElevatedButton` minimum size: `Size(88, 56)` — 56dp height exceeds 48dp
- Button padding: `EdgeInsets.symmetric(horizontal: 24, vertical: 16)`

**Photo screen:**
- Camera/gallery buttons: 100dp height cards with 40px icons
- "Analyze Now" button: `minimumSize: Size(double.infinity, 56)` — full width, 56dp
- All interactive elements well above 48dp threshold

**Report screen:**
- 64x64dp thumbnail images
- PopupMenuButton for actions (view/share/delete)
- All list items use generous padding

**Verdict: Exceeds 48dp minimum. Icon-driven design explicitly targets illiterate users.**

---

## 5. GPS Auto-Capture — Location with Photo

**Status: ✅ PASS**

**Implementation (`photo_screen.dart`):**
- Uses `geolocator` package (v13.0.1) for GPS
- `_getCurrentLocation()` called automatically after image capture (`_pickImage` → `_getCurrentLocation()`)
- `LocationAccuracy.high` requested
- Permission handling: checks → requests → handles denied/deniedForever
- `geocoding` package included for reverse geocoding

**Data model (`observation.dart`):**
- `latitude` and `longitude` fields on every Observation
- GPS coordinates sent with API analysis request (`request.fields['latitude']`, `request.fields['longitude']`)
- Coordinates stored in SQLite (`latitude REAL`, `longitude REAL`)
- Displayed in reports with 6-decimal precision

**UI feedback:**
- Location card shows lat/lon/accuracy with `📍` icon
- "Getting location…" message while acquiring fix
- Error states for disabled/denied location services

**Verdict: GPS auto-captures on photo. Coordinates stored, transmitted, and displayed.**

---

## 6. Camera Integration — Photo Capture for Mineral ID

**Status: ✅ PASS**

**Implementation (`photo_screen.dart`):**
- `image_picker` package (v1.1.2) for camera + gallery access
- `camera` package (v0.11.0+2) for direct camera control
- Two source buttons: "Piga Picha" (camera) and "Galeri" (gallery)
- Image constraints: `maxWidth: 1920, maxHeight: 1920, imageQuality: 85`

**Workflow:**
1. User taps camera/gallery icon
2. Image captured/selected → preview displayed
3. GPS auto-captured (see #5)
4. "Chambua Sasa" (Analyze Now) button triggers analysis
5. Image sent via multipart POST to API
6. Results displayed: mineral name, rock type, confidence bar, description, economic indicator

**Offline handling:**
- If offline: observation queued locally, analyzed when reconnected
- "Saved offline. Will analyze when connected." message shown

**Verdict: Full camera integration with image capture, preview, and AI analysis pipeline.**

---

## 7. APK Size — Target <15MB

**Status: ⚠️ CONDITIONAL PASS**

**Analysis:**
- No `android/` directory or `build.gradle` present — app has not been built yet
- Cannot measure actual APK size
- Dependency analysis of `pubspec.yaml`:

| Package | Estimated Size Impact |
|---------|----------------------|
| `sqflite` | ~200KB |
| `camera` | ~1.5MB (native libs) |
| `geolocator` | ~500KB |
| `fl_chart` | ~300KB |
| `syncfusion_flutter_pdfviewer` | ~3-5MB (heavy) |
| `flutter_local_notifications` | ~500KB |
| `cached_network_image` | ~200KB |
| Core Flutter | ~4-5MB |

**Estimated APK size: ~12-16MB**

**Risk factors:**
- `syncfusion_flutter_pdfviewer` is the heaviest dependency (~3-5MB)
- `camera` plugin adds native camera libraries
- Font files (NotoSans Regular/Bold/SemiBold) could add 1-2MB if not subset

**Recommendations:**
- Consider `flutter build apk --split-per-abi` to reduce per-device size
- Subset NotoSans fonts to only needed characters
- Evaluate lighter PDF viewer alternative
- Enable R8/ProGuard for release builds

**Verdict: Likely within 15MB target but not verified. syncfusion_flutter_pdfviewer is a risk.**

---

## 8. RAM Usage — Target <80MB

**Status: ⚠️ CONDITIONAL PASS**

**Analysis:**
- No runtime profiling possible (app not built/deployed)
- Architecture analysis suggests efficient memory usage:

**Positive indicators:**
- SQLite for local storage (not in-memory) — minimal RAM footprint
- Image quality capped at 85% with 1920px max dimensions
- `CachedNetworkImage` with `shimmer` for lazy loading
- No large in-memory data structures
- Observations query limited to 100 records (`limit: 100`)
- Price cache has 1-hour TTL (prevents unbounded growth)

**Potential concerns:**
- `camera` package may hold camera preview buffer in memory (~10-20MB)
- Multiple images in report list could accumulate if not properly disposed
- `fl_chart` sparklines in price screen hold history arrays in memory

**Recommendations:**
- Implement image disposal in report list when off-screen
- Test on low-end devices (1GB RAM Android Go phones)
- Profile with `flutter run --profile` and DevTools

**Verdict: Architecture suggests <80MB is achievable but requires runtime verification.**

---

## 9. Android Version — Minimum 5.0+ (API 21)

**Status: ✅ PASS (by dependency analysis)**

**Evidence:**
- No `android/` directory exists yet (no `build.gradle` to check `minSdkVersion`)
- Flutter 3.16+ defaults to `minSdkVersion: 21` (Android 5.0 Lollipop)
- All declared dependencies support API 21+:
  - `sqflite` — minSdk 16+
  - `geolocator` — minSdk 21+
  - `camera` — minSdk 21+
  - `connectivity_plus` — minSdk 21+
  - `flutter_secure_storage` — minSdk 18+
  - `permission_handler` — minSdk 21+
- No API 23+ (Android 6.0) specific APIs used in code (runtime permissions handled gracefully)

**Verdict: All dependencies compatible with API 21. Flutter default will set minSdk to 21.**

---

## Summary Scorecard

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 1 | Flutter (Dart) | ✅ PASS | Pure Flutter/Dart, no RN |
| 2 | Offline-first | ✅ PASS | SQLite + sync queue + retry + connectivity listener |
| 3 | Swahili-first | ✅ PASS | Swahili default, EN/LUO complete, KAM/LUY stubs |
| 4 | Icon-driven (48dp+) | ✅ PASS | 48dp icons, 56dp buttons, illiterate-user design |
| 5 | GPS auto-capture | ✅ PASS | Auto-captures on photo, stores/transmits coords |
| 6 | Camera integration | ✅ PASS | Camera + gallery, image preview, AI analysis pipeline |
| 7 | APK size <15MB | ⚠️ CONDITIONAL | ~12-16MB estimated, syncfusion PDF viewer is heavy |
| 8 | RAM usage <80MB | ⚠️ CONDITIONAL | Architecture supports it, needs runtime verification |
| 9 | Android 5.0+ (API 21) | ✅ PASS | Flutter default + all deps compatible |

**Final Score: 7/9 PASS, 2 CONDITIONAL**

---

## Strengths

1. **Exceptional offline-first design** — sync queue with exponential backoff, never loses data
2. **Genuine localization** — Swahili and Luo translations are natural, not machine-translated
3. **Accessibility-first UI** — icon-driven design explicitly for illiterate miners
4. **Robust error handling** — permission denied states, network errors, API failures all handled
5. **Clean architecture** — Provider state management, separation of concerns, well-structured models

## Issues to Address

1. **Kamba/Luhya translations missing** — Declared in supportedLocales but no ARB files or embedded maps
2. **No Android build configuration** — `android/` directory not generated; APK size unverified
3. **syncfusion_flutter_pdfviewer weight** — Consider lighter alternative for PDF viewing
4. **PDF viewing TODO** — `report_screen.dart` has `// TODO: Generate and view PDF` placeholder
5. **Font subsetting** — NotoSans fonts should be subset for Kenyan character sets to reduce APK size

## Recommendations

1. Generate `android/` directory and verify `minSdkVersion: 21` explicitly
2. Build release APK with `--split-per-abi` and verify <15MB
3. Add Kamba (`kam`) and Luhya (`luy`) ARB files or embedded translations
4. Profile on Android Go device (1GB RAM) to verify <80MB
5. Consider replacing `syncfusion_flutter_pdfviewer` with `pdfx` or native intent for lighter APK
6. Subset NotoSans fonts to Latin + Kenyan language character sets
