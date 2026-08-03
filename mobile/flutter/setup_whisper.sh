#!/usr/bin/env bash
# setup_whisper.sh — Clone whisper.cpp into the Android JNI source tree
# Run once before building the APK.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WHISPER_DIR="$SCRIPT_DIR/android/app/src/main/cpp/whisper.cpp"

if [ -d "$WHISPER_DIR" ]; then
    echo "whisper.cpp already cloned at $WHISPER_DIR"
    exit 0
fi

echo "Cloning whisper.cpp → $WHISPER_DIR"
git clone --depth 1 https://github.com/ggerganov/whisper.cpp.git "$WHISPER_DIR"

echo "Done. Build the APK normally — CMake will pick up whisper.cpp automatically."
