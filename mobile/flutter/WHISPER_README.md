# Whisper Voice Transcription — Android Native Integration

On-device speech-to-text using [whisper.cpp](https://github.com/ggerganov/whisper.cpp) with the `whisper-tiny` model (~40 MB).

## Architecture

```
Flutter (Dart)
  └─ MethodChannel 'sovereign_resource_dao/whisper'
       └─ WhisperPlugin.kt          ← channel handler, threading
            └─ WhisperNative.kt     ← JNI bridge, model management
                 └─ whisper_jni.c   ← C JNI → whisper.cpp
                      └─ whisper.cpp (CMake subdirectory)
```

## Setup (one-time)

```bash
cd mobile/flutter
bash setup_whisper.sh
```

This clones `ggerganov/whisper.cpp` into `android/app/src/main/cpp/whisper.cpp/`.

## Build

```bash
cd mobile/flutter
flutter build apk --release
```

CMake builds `libwhisper.so` (including `libggml`) automatically during the Gradle build.

## Flutter Usage

```dart
import 'package:flutter/services.dart';

const _channel = MethodChannel('sovereign_resource_dao/whisper');

// 1. Initialise (downloads model on first run)
final initResult = await _channel.invokeMethod('initialize', {
  'modelSource': 'download',  // or 'asset' if bundled
});
print(initResult['message']); // "Whisper initialised (40000000 bytes)"

// 2. Transcribe 16kHz mono float PCM
final result = await _channel.invokeMethod('transcribe', {
  'pcmData': floatSamples,     // List<double>, 16 kHz, mono, [-1.0, 1.0]
  'language': 'sw',            // 'sw' (Swahili), 'en' (English), '' (auto-detect)
  'translate': false,          // true → translate to English
});
print(result['text']); // "Habari za leo"

// 3. Check status
final status = await _channel.invokeMethod('isAvailable');

// 4. Model info
final info = await _channel.invokeMethod('getModelInfo');

// 5. Release when done
await _channel.invokeMethod('release');
```

## API Reference

| Method         | Params                                    | Returns                                      |
|----------------|-------------------------------------------|----------------------------------------------|
| `initialize`   | `{modelSource: "download"\|"asset"}`      | `{success: bool, message: string}`           |
| `transcribe`   | `{pcmData: List<num>, language, translate}` | `{success, text, language, durationMs}`    |
| `isAvailable`  | `{}`                                      | `{available, modelOnDisk, initialized}`      |
| `getModelInfo` | `{}`                                      | `{name, language, modelPath, modelOnDisk, ...}` |
| `release`      | `{}`                                      | `{success: bool}`                            |

## Model Details

- **Model**: `whisper-tiny` (multilingual, 39M parameters)
- **Size**: ~40 MB
- **Languages**: 99 languages including English (`en`) and Swahili (`sw`)
- **Source**: Auto-downloaded from HuggingFace on first `initialize()` call
- **Storage**: `<app-files>/whisper_models/ggml-tiny.bin`

## Requirements

- **NDK**: 25.2.9519653 (set in build.gradle)
- **CMake**: 3.22.1+
- **Min SDK**: 21 (Android 5.0)
- **RAM**: ~150 MB during inference
