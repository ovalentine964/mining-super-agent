/*
 * whisper_jni.c — JNI bridge between Kotlin (WhisperNative.kt) and whisper.cpp
 *
 * Channel: sovereign_resource_dao/whisper
 *
 * Exposed JNI methods:
 *   nativeInit(String modelPath)              → long handle
 *   nativeFree(long ctx)
 *   nativeTranscribe(long ctx, float[] pcm, String lang, boolean translate) → String
 *   nativeVersion()                           → String
 */

#include <jni.h>
#include <string.h>
#include <stdlib.h>
#include <android/log.h>

#include "whisper.h"

#define TAG "WhisperJNI"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO,  TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, TAG, __VA_ARGS__)

/* ──────────────────────────────────────────────────────────────────────── */
/* Helpers                                                                 */
/* ──────────────────────────────────────────────────────────────────────── */

/* Simple callback – just log progress segments */
static void whisper_log_callback(enum ggml_log_level level, const char *text, void *user_data) {
    (void)user_data;
    if (level >= GGML_LOG_LEVEL_ERROR) {
        LOGE("whisper: %s", text);
    }
}

/* Map a language string to whisper language id.
 * Returns -1 for auto-detect (empty string). */
static int resolve_language(const char *lang) {
    if (!lang || lang[0] == '\0') return -1;  /* auto-detect */

    /* Common languages supported by whisper multilingual */
    struct { const char *code; int id; } langs[] = {
        {"en", 0}, {"sw", 79}, {"fr", 4}, {"es", 7}, {"de", 3},
        {"zh", 13}, {"ar", 12}, {"hi", 8}, {"pt", 18}, {"ru", 19},
        {"ja", 10}, {"ko", 11}, {"it", 9}, {"nl", 14}, {"pl", 17},
        {"tr", 23}, {"vi", 28}, {"th", 22}, {"sv", 20}, {"uk", 25},
        {NULL, -1}
    };
    for (int i = 0; langs[i].code != NULL; i++) {
        if (strcmp(lang, langs[i].code) == 0) return langs[i].id;
    }
    LOGE("Unknown language code '%s', using auto-detect", lang);
    return -1;
}

/* ──────────────────────────────────────────────────────────────────────── */
/* JNI exports                                                             */
/* ──────────────────────────────────────────────────────────────────────── */

JNIEXPORT jlong JNICALL
Java_com_sovereignresourcedao_WhisperNative_nativeInit(
        JNIEnv *env, jobject thiz, jstring modelPath) {

    const char *path = (*env)->GetStringUTFChars(env, modelPath, NULL);
    if (!path) return 0;

    LOGI("nativeInit: loading model from %s", path);

    struct whisper_context_params cparams = whisper_context_default_params();
    struct whisper_context *ctx = whisper_init_from_file_with_params(path, cparams);

    (*env)->ReleaseStringUTFChars(env, modelPath, path);

    if (ctx == NULL) {
        LOGE("nativeInit: whisper_init_from_file returned NULL");
        return 0;
    }

    LOGI("nativeInit: success, ctx=%p", (void *)ctx);
    return (jlong)(intptr_t)ctx;
}

JNIEXPORT void JNICALL
Java_com_sovereignresourcedao_WhisperNative_nativeFree(
        JNIEnv *env, jobject thiz, jlong ctxHandle) {

    if (ctxHandle == 0) return;
    struct whisper_context *ctx = (struct whisper_context *)(intptr_t)ctxHandle;
    whisper_free(ctx);
    LOGI("nativeFree: freed ctx=%p", (void *)ctx);
}

JNIEXPORT jstring JNICALL
Java_com_sovereignresourcedao_WhisperNative_nativeTranscribe(
        JNIEnv *env, jobject thiz,
        jlong ctxHandle, jfloatArray pcmData,
        jstring language, jboolean translate) {

    if (ctxHandle == 0) {
        LOGE("nativeTranscribe: null context");
        return (*env)->NewStringUTF(env, "ERROR: null context");
    }

    struct whisper_context *ctx = (struct whisper_context *)(intptr_t)ctxHandle;

    jsize n_samples = (*env)->GetArrayLength(env, pcmData);
    jfloat *samples = (*env)->GetFloatArrayElements(env, pcmData, NULL);
    if (!samples || n_samples == 0) {
        if (samples) (*env)->ReleaseFloatArrayElements(env, pcmData, samples, JNI_ABORT);
        return (*env)->NewStringUTF(env, "ERROR: empty PCM data");
    }

    const char *lang_cstr = (*env)->GetStringUTFChars(env, language, NULL);
    int lang_id = resolve_language(lang_cstr);
    if (lang_cstr) (*env)->ReleaseStringUTFChars(env, language, lang_cstr);

    /* ── Configure whisper parameters ───────────────────────────────── */
    struct whisper_full_params wparams = whisper_full_default_params(
        WHISPER_SAMPLING_GREEDY);

    wparams.print_progress   = 0;
    wparams.print_special    = 0;
    wparams.print_realtime   = 0;
    wparams.print_timestamps = 0;
    wparams.translate        = translate ? 1 : 0;
    wparams.single_segment   = 0;
    wparams.no_timestamps    = 1;
    wparams.n_threads        = 4;  /* reasonable default for mobile */

    /* Language */
    if (lang_id >= 0) {
        wparams.language = lang_id;
    } else {
        wparams.language = 0; /* default to English for auto */
        wparams.detect_language = 1;
    }

    /* Suppress non-speech tokens */
    wparams.suppress_blank    = 1;
    wparams.suppress_non_speech_tokens = 1;

    /* Greedy decoding defaults are fine for tiny model */

    LOGI("nativeTranscribe: %d samples, lang=%d, translate=%d",
         (int)n_samples, lang_id, translate ? 1 : 0);

    /* ── Run inference ──────────────────────────────────────────────── */
    int ret = whisper_full(ctx, wparams, samples, n_samples);

    (*env)->ReleaseFloatArrayElements(env, pcmData, samples, JNI_ABORT);

    if (ret != 0) {
        LOGE("nativeTranscribe: whisper_full returned %d", ret);
        return (*env)->NewStringUTF(env, "ERROR: whisper_full failed");
    }

    /* ── Collect result segments ────────────────────────────────────── */
    int n_segments = whisper_full_n_segments(ctx);
    LOGI("nativeTranscribe: %d segment(s)", n_segments);

    /* Build result string by concatenating segments */
    size_t total_len = 0;
    for (int i = 0; i < n_segments; i++) {
        const char *text = whisper_full_get_segment_text(ctx, i);
        if (text) total_len += strlen(text);
    }

    if (total_len == 0) {
        return (*env)->NewStringUTF(env, "");
    }

    /* +1 for null terminator */
    char *result = (char *)calloc(total_len + 1, 1);
    if (!result) {
        LOGE("nativeTranscribe: calloc failed for %zu bytes", total_len);
        return (*env)->NewStringUTF(env, "ERROR: memory allocation failed");
    }

    for (int i = 0; i < n_segments; i++) {
        const char *text = whisper_full_get_segment_text(ctx, i);
        if (text) strcat(result, text);
    }

    jstring jresult = (*env)->NewStringUTF(env, result);
    free(result);

    return jresult;
}

JNIEXPORT jstring JNICALL
Java_com_sovereignresourcedao_WhisperNative_nativeVersion(
        JNIEnv *env, jobject thiz) {
    (void)thiz;
    return (*env)->NewStringUTF(env, whisper_print_system_info());
}
