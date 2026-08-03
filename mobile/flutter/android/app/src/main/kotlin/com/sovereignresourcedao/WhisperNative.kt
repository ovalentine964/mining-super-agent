package com.sovereignresourcedao

import android.content.Context
import android.util.Log
import java.io.File
import java.io.FileOutputStream
import java.io.IOException

/**
 * JNI bridge to whisper.cpp native library.
 *
 * Provides on-device speech-to-text transcription using the Whisper tiny model (~40MB).
 * Supports English and Swahili out of the box.
 */
class WhisperNative(private val context: Context) {

    companion object {
        private const val TAG = "WhisperNative"
        private const val MODEL_ASSET_NAME = "ggml-tiny.bin"
        private const val MODEL_DIR_NAME = "whisper_models"
        private const val MODEL_FILENAME = "ggml-tiny.bin"
        private const val MODEL_URL =
            "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin"
        private const val MODEL_SIZE_BYTES = 40_000_000L // ~40MB approximate check

        init {
            try {
                System.loadLibrary("whisper")
                Log.i(TAG, "whisper native library loaded")
            } catch (e: UnsatisfiedLinkError) {
                Log.e(TAG, "Failed to load whisper native library", e)
            }
        }
    }

    // ── Native JNI methods ──────────────────────────────────────────────

    /**
     * Initialise the whisper context from a GGML model file.
     * Returns an opaque context handle (>0) on success, 0 on failure.
     */
    external fun nativeInit(modelPath: String): Long

    /** Free a previously-initialised context. */
    external fun nativeFree(ctx: Long)

    /**
     * Run full inference on 16 kHz mono float PCM.
     * @param ctx      context handle from nativeInit
     * @param pcmData  normalised float samples, 16 kHz mono
     * @param language "en", "sw", or "" for auto-detect
     * @param translate  if true, translate to English
     * @return transcribed text, or null on failure
     */
    external fun nativeTranscribe(
        ctx: Long,
        pcmData: FloatArray,
        language: String,
        translate: Boolean
    ): String?

    /** Return the whisper.cpp library version string. */
    external fun nativeVersion(): String

    // ── Kotlin helpers ──────────────────────────────────────────────────

    @Volatile private var ctxHandle: Long = 0L
    private val modelDir: File by lazy {
        File(context.filesDir, MODEL_DIR_NAME).also { it.mkdirs() }
    }

    /** Path where the model is expected to live. */
    val modelFile: File get() = File(modelDir, MODEL_FILENAME)

    /** Whether the model is already present on disk. */
    fun isModelOnDisk(): Boolean = modelFile.exists() && modelFile.length() > 1_000_000

    /**
     * Ensure the model file exists. Tries, in order:
     * 1. Previously downloaded file
     * 2. Asset bundled in the APK
     * 3. Download from HuggingFace
     */
    fun ensureModelAvailable(): Boolean {
        if (isModelOnDisk()) return true

        // Try copying from assets
        if (copyModelFromAssets()) return true

        // Download from remote
        return downloadModel()
    }

    /**
     * Initialise the whisper engine.  Must be called after [ensureModelAvailable].
     * Returns true on success.
     */
    fun initialize(): Boolean {
        if (ctxHandle != 0L) return true
        if (!isModelOnDisk()) {
            Log.e(TAG, "Model file missing – call ensureModelAvailable first")
            return false
        }
        ctxHandle = nativeInit(modelFile.absolutePath)
        if (ctxHandle == 0L) {
            Log.e(TAG, "nativeInit returned 0 – initialisation failed")
            return false
        }
        Log.i(TAG, "Whisper initialised, handle=$ctxHandle")
        return true
    }

    /**
     * Transcribe 16 kHz mono float PCM audio.
     * @param pcmData  float samples in [-1, 1]
     * @param language BCP-47-ish code ("en", "sw", "" for auto)
     * @param translate true → always translate to English
     * @return transcribed text, or error string starting with "ERROR:"
     */
    fun transcribe(pcmData: FloatArray, language: String, translate: Boolean): String {
        if (ctxHandle == 0L) return "ERROR: Whisper not initialised"
        if (pcmData.isEmpty()) return "ERROR: Empty audio data"

        return try {
            nativeTranscribe(ctxHandle, pcmData, language, translate) ?: "ERROR: Transcription returned null"
        } catch (e: Exception) {
            Log.e(TAG, "transcribe failed", e)
            "ERROR: ${e.message}"
        }
    }

    /** Release native resources. Safe to call multiple times. */
    fun release() {
        if (ctxHandle != 0L) {
            nativeFree(ctxHandle)
            ctxHandle = 0L
        }
    }

    fun isInitialized(): Boolean = ctxHandle != 0L

    /** Return basic model metadata as a map for Flutter. */
    fun getModelInfo(): Map<String, Any> {
        val info = mutableMapOf<String, Any>(
            "name" to "whisper-tiny",
            "language" to "multilingual",
            "modelPath" to modelFile.absolutePath,
            "modelOnDisk" to isModelOnDisk(),
            "initialized" to isInitialized(),
            "nativeVersion" to try { nativeVersion() } catch (_: Throwable) { "unknown" }
        )
        if (isModelOnDisk()) {
            info["modelSizeBytes"] = modelFile.length()
        }
        return info
    }

    // ── Internal helpers ────────────────────────────────────────────────

    private fun copyModelFromAssets(): Boolean {
        return try {
            context.assets.open(MODEL_ASSET_NAME).use { input ->
                FileOutputStream(modelFile).use { output ->
                    input.copyTo(output, bufferSize = 8192)
                }
            }
            Log.i(TAG, "Model copied from assets → ${modelFile.absolutePath}")
            true
        } catch (e: IOException) {
            Log.d(TAG, "Model not in assets (${e.message}), will try download")
            false
        }
    }

    private fun downloadModel(): Boolean {
        return try {
            val url = java.net.URL(MODEL_URL)
            val conn = url.openConnection() as java.net.HttpURLConnection
            conn.connectTimeout = 30_000
            conn.readTimeout = 60_000
            conn.requestMethod = "GET"
            conn.connect()

            if (conn.responseCode != 200) {
                Log.e(TAG, "Download failed: HTTP ${conn.responseCode}")
                conn.disconnect()
                return false
            }

            val tmpFile = File(modelDir, "$MODEL_FILENAME.tmp")
            conn.inputStream.use { input ->
                FileOutputStream(tmpFile).use { output ->
                    input.copyTo(output, bufferSize = 16384)
                }
            }
            conn.disconnect()

            // Rename into place atomically
            tmpFile.renameTo(modelFile)
            Log.i(TAG, "Model downloaded → ${modelFile.absolutePath} (${modelFile.length()} bytes)")
            true
        } catch (e: Exception) {
            Log.e(TAG, "Model download failed", e)
            false
        }
    }
}
