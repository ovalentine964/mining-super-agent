package com.sovereignresourcedao

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.util.Log
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import io.flutter.plugin.common.MethodChannel.MethodCallHandler
import java.util.concurrent.Executors

/**
 * Flutter ↔ whisper.cpp bridge.
 *
 * Channel: `sovereign_resource_dao/whisper`
 *
 * Supported methods:
 *   initialize      → {modelSource: "asset"|"download"} → {success: bool, message: string}
 *   transcribe      → {pcmData: FloatArray, language: "en"|"sw"|"", translate: bool} → {text: string}
 *   isAvailable     → {} → {available: bool, modelOnDisk: bool, initialized: bool}
 *   getModelInfo    → {} → Map with model metadata
 *   release         → {} → {success: bool}
 */
class WhisperPlugin : FlutterPlugin, MethodCallHandler {

    companion object {
        private const val TAG = "WhisperPlugin"
        private const val CHANNEL_NAME = "sovereign_resource_dao/whisper"
    }

    private lateinit var channel: MethodChannel
    private lateinit var appContext: Context
    private var whisper: WhisperNative? = null

    private val bgExecutor = Executors.newSingleThreadExecutor { r ->
        Thread(r, "whisper-bg").apply { isDaemon = true }
    }
    private val mainHandler = Handler(Looper.getMainLooper())

    // ── FlutterPlugin lifecycle ─────────────────────────────────────────

    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        appContext = binding.applicationContext
        channel = MethodChannel(binding.binaryMessenger, CHANNEL_NAME)
        channel.setMethodCallHandler(this)
        Log.i(TAG, "WhisperPlugin attached, channel=$CHANNEL_NAME")
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        channel.setMethodCallHandler(null)
        whisper?.release()
        whisper = null
        bgExecutor.shutdownNow()
        Log.i(TAG, "WhisperPlugin detached")
    }

    // ── MethodChannel handler ───────────────────────────────────────────

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "initialize"    -> handleInitialize(call, result)
            "transcribe"    -> handleTranscribe(call, result)
            "isAvailable"   -> handleIsAvailable(result)
            "getModelInfo"  -> handleGetModelInfo(result)
            "release"       -> handleRelease(result)
            else            -> result.notImplemented()
        }
    }

    // ── initialize ──────────────────────────────────────────────────────

    private fun handleInitialize(call: MethodCall, result: MethodChannel.Result) {
        bgExecutor.execute {
            try {
                if (whisper == null) {
                    whisper = WhisperNative(appContext)
                }
                val w = whisper!!

                // Step 1: ensure model is on disk
                val modelReady = w.ensureModelAvailable()
                if (!modelReady) {
                    replyOnMain(result, mapOf(
                        "success" to false,
                        "message" to "Failed to download or locate whisper-tiny model. Check storage and network."
                    ))
                    return@execute
                }

                // Step 2: initialise native engine
                val ok = w.initialize()
                replyOnMain(result, mapOf(
                    "success" to ok,
                    "message" to if (ok) "Whisper initialised (${w.modelFile.length()} bytes)" else "nativeInit failed"
                ))
            } catch (e: Exception) {
                Log.e(TAG, "initialize failed", e)
                replyOnMain(result, mapOf(
                    "success" to false,
                    "message" to "Exception: ${e.message}"
                ))
            }
        }
    }

    // ── transcribe ──────────────────────────────────────────────────────

    private fun handleTranscribe(call: MethodCall, result: MethodChannel.Result) {
        val w = whisper
        if (w == null || !w.isInitialized()) {
            result.error("NOT_INITIALIZED", "Call initialize() first", null)
            return
        }

        // Accept both FloatArray and List<Double> (Flutter sends List<num>)
        val rawPcm = call.argument<Any>("pcmData")
        val pcmData: FloatArray? = when (rawPcm) {
            is FloatArray -> rawPcm
            is DoubleArray -> FloatArray(rawPcm.size) { rawPcm[it].toFloat() }
            is List<*> -> {
                try {
                    FloatArray(rawPcm.size) { (rawPcm[it] as Number).toFloat() }
                } catch (_: Exception) { null }
            }
            else -> null
        }

        if (pcmData == null || pcmData.isEmpty()) {
            result.error("INVALID_ARGS", "pcmData must be a non-empty list of numbers", null)
            return
        }

        val language = call.argument<String>("language") ?: "en"
        val translate = call.argument<Boolean>("translate") ?: false

        bgExecutor.execute {
            try {
                val text = w.transcribe(pcmData, language, translate)
                if (text.startsWith("ERROR:")) {
                    replyOnMain(result, mapOf(
                        "success" to false,
                        "text" to "",
                        "error" to text.removePrefix("ERROR: ").trim()
                    ))
                } else {
                    replyOnMain(result, mapOf(
                        "success" to true,
                        "text" to text,
                        "language" to language,
                        "durationMs" to (pcmData.size * 1000L / 16000) // 16 kHz assumed
                    ))
                }
            } catch (e: Exception) {
                Log.e(TAG, "transcribe failed", e)
                replyOnMain(result, mapOf(
                    "success" to false,
                    "text" to "",
                    "error" to e.message
                ))
            }
        }
    }

    // ── isAvailable ─────────────────────────────────────────────────────

    private fun handleIsAvailable(result: MethodChannel.Result) {
        val w = whisper
        replyOnMain(result, mapOf(
            "available" to (w != null && w.isInitialized()),
            "modelOnDisk" to (w?.isModelOnDisk() ?: WhisperNative(appContext).let {
                val onDisk = it.isModelOnDisk()
                it.release()
                onDisk
            }),
            "initialized" to (w?.isInitialized() ?: false)
        ))
    }

    // ── getModelInfo ────────────────────────────────────────────────────

    private fun handleGetModelInfo(result: MethodChannel.Result) {
        val w = whisper ?: WhisperNative(appContext).also {
            // lightweight – no native init needed
        }
        replyOnMain(result, w.getModelInfo())
    }

    // ── release ─────────────────────────────────────────────────────────

    private fun handleRelease(result: MethodChannel.Result) {
        whisper?.release()
        whisper = null
        replyOnMain(result, mapOf("success" to true))
    }

    // ── Helpers ─────────────────────────────────────────────────────────

    private fun replyOnMain(result: MethodChannel.Result, value: Any?) {
        mainHandler.post { result.success(value) }
    }
}
