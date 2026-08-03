#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# build_apk.sh — Build a release APK for Sovereign Resource DAO
# Run from the repository root:  ./scripts/build_apk.sh
#
# Options:
#   --arm64       Build for arm64-v8a only (smaller APK, most modern phones)
#   --all         Build for all ABIs (default — universal APK)
#   --debug       Build debug APK instead of release
# ─────────────────────────────────────────────────────────────
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FLUTTER_DIR="$REPO_ROOT/mobile/flutter"

# Parse args
BUILD_MODE="release"
TARGET_PLATFORM=""
ABI_LABEL="all ABIs"

for arg in "$@"; do
    case "$arg" in
        --arm64)
            TARGET_PLATFORM="--target-platform android-arm64"
            ABI_LABEL="arm64-v8a only"
            ;;
        --all)
            TARGET_PLATFORM=""
            ABI_LABEL="all ABIs"
            ;;
        --debug)
            BUILD_MODE="debug"
            ;;
        -h|--help)
            echo "Usage: $0 [--arm64] [--all] [--debug]"
            echo ""
            echo "  --arm64   Build for arm64-v8a only (smaller APK, most modern phones)"
            echo "  --all     Build for all ABIs (default)"
            echo "  --debug   Build debug APK instead of release"
            exit 0
            ;;
    esac
done

if [ "$BUILD_MODE" = "debug" ]; then
    APK_OUTPUT="$FLUTTER_DIR/build/app/outputs/flutter-apk/app-debug.apk"
else
    APK_OUTPUT="$FLUTTER_DIR/build/app/outputs/flutter-apk/app-release.apk"
fi

echo "╔══════════════════════════════════════════════════════════╗"
echo "║   Sovereign Resource DAO — APK Builder v0.1.0           ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  Mode: $BUILD_MODE | Target: $ABI_LABEL"
echo ""

# ── 1. Check Flutter is installed ──────────────────────────
if ! command -v flutter &>/dev/null; then
    echo "❌ Flutter is not installed or not in PATH."
    echo ""
    echo "   Install Flutter:"
    echo "     macOS:   brew install flutter"
    echo "     Linux:   snap install flutter"
    echo "     Manual:  https://docs.flutter.dev/get-started/install"
    echo ""
    echo "   After install, make sure 'flutter' is in your PATH."
    exit 1
fi

FLUTTER_VER="$(flutter --version 2>/dev/null | head -1)"
echo "✅ Flutter: $FLUTTER_VER"

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

# ── 5. Build APK ──────────────────────────────────────────
echo "🔨 Building $BUILD_MODE APK ($ABI_LABEL)..."
BUILD_CMD="flutter build apk --$BUILD_MODE"
if [ -n "$TARGET_PLATFORM" ]; then
    BUILD_CMD="$BUILD_CMD $TARGET_PLATFORM"
fi
eval "$BUILD_CMD"
echo ""

# ── 6. Show result ─────────────────────────────────────────
if [ -f "$APK_OUTPUT" ]; then
    SIZE_BYTES=$(stat -c%s "$APK_OUTPUT" 2>/dev/null || stat -f%z "$APK_OUTPUT" 2>/dev/null)
    SIZE_MB=$(awk "BEGIN {printf \"%.1f\", $SIZE_BYTES / 1048576}")

    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║   ✅ BUILD SUCCESSFUL                                    ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo ""
    echo "   📱 APK:  $APK_OUTPUT"
    echo "   📏 Size: ${SIZE_MB} MB"
    echo "   📦 Mode: $BUILD_MODE | Target: $ABI_LABEL"
    echo ""
    echo "──────────────────────────────────────────────────────────"
    echo "   INSTALL ON YOUR PHONE:"
    echo "──────────────────────────────────────────────────────────"
    echo ""
    echo "   Option A — USB (fastest):"
    echo "     1. Connect phone via USB"
    echo "     2. Enable USB debugging on phone"
    echo "     3. Run:  adb install \"$APK_OUTPUT\""
    echo ""
    echo "   Option B — Transfer file:"
    echo "     1. Copy APK to phone (email, Google Drive, AirDroid, etc.)"
    echo "     2. On phone: Settings → Security → enable 'Unknown sources'"
    echo "     3. Open the APK file on phone to install"
    echo ""
    echo "   Option C — GitHub Release (for CI builds):"
    echo "     1. Push a tag:  git tag v0.1.0 && git push origin v0.1.0"
    echo "     2. Download APK from GitHub Releases page"
    echo ""
else
    echo "❌ Build failed — APK not found at expected path:"
    echo "   $APK_OUTPUT"
    echo ""
    echo "   Check the build output above for errors."
    echo "   Common fixes:"
    echo "     - Run 'flutter doctor' to check your setup"
    echo "     - Ensure Android SDK 34 is installed"
    echo "     - Ensure Java 17 is installed"
    exit 1
fi
