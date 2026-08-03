#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# build_apk.sh — Build a release APK for Sovereign Resource DAO
# Run from the repository root:  ./scripts/build_apk.sh
# ─────────────────────────────────────────────────────────────
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FLUTTER_DIR="$REPO_ROOT/mobile/flutter"
APK_OUTPUT="$FLUTTER_DIR/build/app/outputs/flutter-apk/app-release.apk"

echo "╔══════════════════════════════════════════════╗"
echo "║   Sovereign Resource DAO — APK Builder       ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── 1. Check Flutter is installed ──────────────────────────
if ! command -v flutter &>/dev/null; then
    echo "❌ Flutter is not installed or not in PATH."
    echo ""
    echo "   Install Flutter: https://docs.flutter.dev/get-started/install"
    echo "   Make sure 'flutter' is in your PATH after installation."
    exit 1
fi

FLUTTER_VER="$(flutter --version 2>/dev/null | head -1)"
echo "✅ Flutter found: $FLUTTER_VER"
echo ""

# ── 2. Check Android SDK ───────────────────────────────────
if [ -z "${ANDROID_HOME:-}" ] && [ -z "${ANDROID_SDK_ROOT:-}" ]; then
    echo "⚠️  ANDROID_HOME / ANDROID_SDK_ROOT not set."
    echo "   The build may still work if Android SDK is in a standard location."
    echo ""
fi

# ── 3. Enter Flutter project directory ─────────────────────
cd "$FLUTTER_DIR"
echo "📂 Working directory: $FLUTTER_DIR"
echo ""

# ── 4. flutter pub get ─────────────────────────────────────
echo "📦 Installing dependencies (flutter pub get)..."
flutter pub get
echo ""

# ── 5. Build release APK ──────────────────────────────────
echo "🔨 Building release APK..."
flutter build apk --release
echo ""

# ── 6. Show result ─────────────────────────────────────────
if [ -f "$APK_OUTPUT" ]; then
    SIZE_BYTES=$(stat -c%s "$APK_OUTPUT" 2>/dev/null || stat -f%z "$APK_OUTPUT" 2>/dev/null)
    SIZE_MB=$(awk "BEGIN {printf \"%.1f\", $SIZE_BYTES / 1048576}")

    echo "╔══════════════════════════════════════════════╗"
    echo "║   ✅ BUILD SUCCESSFUL                        ║"
    echo "╚══════════════════════════════════════════════╝"
    echo ""
    echo "   📱 APK:  $APK_OUTPUT"
    echo "   📏 Size: ${SIZE_MB} MB"
    echo ""
    echo "   Install on device:"
    echo "     adb install \"$APK_OUTPUT\""
    echo ""
else
    echo "❌ Build failed — APK not found at expected path:"
    echo "   $APK_OUTPUT"
    echo ""
    echo "   Check the build output above for errors."
    exit 1
fi
