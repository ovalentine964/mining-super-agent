# FINAL COUNCIL 3: AI/ML Pipeline — Full Repo Review

**Reviewed:** `/home/work/.openclaw/workspace/mining-super-agent/src/ml/`  
**Date:** 2026-07-25  
**Files reviewed:** 10 source files (mineral_classifier, clip_classifier, hallucination_prevention, rag_pipeline, satellite_analyzer, model_registry, eval_suite, dataset, train_mineral, preprocessing)

---

## Checklist Results

### 1. Mineral Classifier (EfficientNet-B4)? ✅
- `mineral_classifier.py` implements `MineralClassifier` using `torchvision.models.efficientnet_b4`
- Custom classifier head: Dropout(0.4) → Linear(in, 512) → ReLU → Dropout(0.2) → Linear(512, NUM_CLASSES)
- 20 mineral classes defined in `data/dataset.py`
- 3-phase transfer learning training in `training/train_mineral.py`
- Image quality assessment integrated into predict pipeline
- **Verdict: Fully implemented**

### 2. CLIP Fallback (65% cap)? ✅
- `clip_classifier.py` implements `CLIPMineralClassifier` using OpenAI CLIP (ViT-B-32)
- `IMAGE_ONLY_MAX_CONFIDENCE = 0.65` — hardcoded cap applied: `min(float(probs[top_indices[0]]), 0.65)`
- Multi-prompt encoding per mineral for robustness
- Returns disclaimers with every prediction
- **Verdict: Fully implemented with correct 65% cap**

### 3. Pyrite NEVER = Gold (hard assertion)? ❌
- **CRITICAL FAILURE** — No hard assertion exists. The logic in `mineral_classifier.py`:
  - If best=PYRITE and gold_prob > 0.05 → adds warning disclaimer only (pyrite stays as prediction — this is OK)
  - If best=GOLD and pyrite_prob > 0.1 → adds warning and caps confidence to 0.40 if pyrite_prob > 0.2
  - **BUT**: gold classification is NEVER blocked. When pyrite_prob is high (e.g., 0.35), the system still returns "gold" at 0.40 confidence instead of refusing to classify or forcing reclassification
- No `assert` statement, no hard gate, no "refuse to answer" path when pyrite ambiguity is detected
- **What's needed:** When pyrite_prob > some threshold (e.g., 0.2), the prediction MUST be blocked or forced to "ambiguous — physical testing required", NOT returned as gold with reduced confidence
- **Verdict: FAIL — soft warning only, no hard assertion**

### 4. Confidence Calibrated (not hardcoded 0.8)? ✅
- Confidence is **not** hardcoded to 0.8
- `IMAGE_ONLY_MAX_CONFIDENCE = 0.65` caps image-based predictions
- `hallucination_prevention.py` implements source-type-based caps: image=0.65, xrf=0.85, spectroscopy=0.90, lab=0.99
- Additional dynamic caps: gold with pyrite_prob > 0.2 gets capped to 0.40
- Evaluation suite computes Expected Calibration Error (ECE) with 15 bins
- **Note:** Caps are still fixed per source type rather than fully learned/calibrated, but the system does not use a naive 0.8 threshold
- **Verdict: Implemented — dynamic caps per source type with ECE evaluation**

### 5. Swahili Disclaimer on Every Prediction? ✅
- `mineral_classifier.py`: Every `MineralPrediction` includes `DISCLAIMER_SWAHILI = "Hii si uthibitisho wa maabara. Tafadhali thibitisha na mtihani wa kimwili."` plus English translation
- `clip_classifier.py`: Every `CLIPPrediction` includes the same Swahili disclaimer
- Disclaimers are appended to the `disclaimers` list unconditionally in the `predict()` method
- Additional contextual disclaimers added for economic minerals and look-alike warnings
- **Verdict: Present on every prediction path**

### 6. RAG Pipeline (BGE + Hybrid Retrieval + Re-ranking)? ✅
- `rag_pipeline.py` implements a complete RAG pipeline:
  - **BGE embeddings:** `DenseRetriever` using `BAAI/bge-large-en-v1.5` via sentence-transformers
  - **BM25 sparse retrieval:** Custom `BM25Index` implementation with k1=1.5, b=0.75
  - **Hybrid retrieval:** RRF (Reciprocal Rank Fusion, k=60) merging BM25 + dense results
  - **Cross-encoder re-ranking:** `CrossEncoderReranker` using `BAAI/bge-reranker-v2-m3`
  - **Cited generation:** `RAGResponse` includes citations, sources, confidence scores
  - Domain-aware chunking with sentence boundary detection (512 chars, 64 overlap)
- **Verdict: Fully implemented with all three retrieval stages**

### 7. Hallucination Prevention (5-layer)? ✅
- `hallucination_prevention.py` implements all 5 layers:
  - **Layer 1:** Structured confidence output with source-type caps and confidence levels (VERY_LOW through VERY_HIGH)
  - **Layer 2:** Multi-agent consistency checks with agreement ratio and conflict detection
  - **Layer 3:** NLI-based evidence grounding using `cross-encoder/nli-deberta-v3-base` (entailment threshold 0.70)
  - **Layer 4:** Chain-of-Verification with sub-questions and verification status
  - **Layer 5:** Domain-specific rules (image confidence cap, economic mineral expert requirement)
- `full_check()` orchestrates all 5 layers into a `HallucinationReport`
- Critical failures block `overall_safe` flag
- **Verdict: All 5 layers implemented**

### 8. Satellite Analyzer (Sentinel-2)? ✅
- `satellite_analyzer.py` implements Sentinel-2 spectral analysis:
  - **NDVI:** (NIR - Red) / (NIR + Red) — vegetation index
  - **Clay ratio:** SWIR1 / SWIR2 — clay mineral alteration detection
  - **Iron oxide ratio:** Red / Blue — iron oxide mapping
  - **Alteration zone detection:** Threshold-based masking for clay and iron oxide zones
  - Returns `AlterationZone` objects with confidence, area, bounding box
- Uses correct Sentinel-2 band naming (swir1, swir2, nir, red, blue)
- **Verdict: Implemented for Sentinel-2 bands**

### 9. Model Registry (versioning, A/B, rollback)? ❌
- `model_registry.py` implements **versioning** only:
  - `register()` — stores model versions with metadata, metrics, timestamps
  - `get_active()` / `set_active()` — active version management
  - `list_models()` — enumerate versions
- **Missing A/B testing:** No mechanism to split traffic between model versions, compare live performance, or route requests to different models
- **Missing rollback:** No `rollback()` method, no version history traversal, no automatic rollback on metric degradation
- Only stores a single "active" version per model name
- **Verdict: FAIL — versioning present but A/B testing and rollback not implemented**

### 10. Evaluation Suite? ✅
- `evaluation/eval_suite.py` implements comprehensive evaluation:
  - Overall accuracy, per-class precision/recall/F1
  - Look-alike confusion analysis (tracks misclassifications between known confusable pairs)
  - Expected Calibration Error (ECE) with 15 bins
  - Formatted report output (`print_report()`)
- Integrates with `LOOK_ALIKE_PAIRS` from dataset for domain-specific error analysis
- **Verdict: Fully implemented**

---

## Additional Findings

### Positive
- **Training pipeline:** 3-phase transfer learning (head-only → last blocks → full fine-tune) with cosine annealing — solid methodology
- **Image quality assessment:** Blur detection (Laplacian variance), brightness/contrast checks integrated into prediction pipeline
- **Economic mineral flagging:** Gold, copper, galena, sphalerite flagged for expert review with mandatory disclaimers
- **Look-alike pair handling:** 8 confusable mineral pairs defined and actively checked during prediction

### Concerns
1. **Pyrite/gold boundary is the #1 safety risk** — the current soft-warning approach could allow a miner to act on a "gold: 40%" prediction that is actually pyrite
2. **NLI model lazy-loaded** — first call to `check_nli_grounding()` will have high latency; no warm-up mechanism
3. **Satellite analyzer has no NDVI masking** — vegetation-covered areas could produce false alteration signals
4. **`NUM_CLASSES` imported but not visible in `dataset.py`** — likely defined via `len(MINERAL_CLASSES)` but not explicitly shown; could cause import errors if assumption breaks

---

## Score: 8 / 10

| # | Check | Status |
|---|-------|--------|
| 1 | Mineral classifier (EfficientNet-B4) | ✅ |
| 2 | CLIP fallback (65% cap) | ✅ |
| 3 | Pyrite NEVER = gold (hard assertion) | ❌ |
| 4 | Confidence calibrated (not hardcoded 0.8) | ✅ |
| 5 | Swahili disclaimer on every prediction | ✅ |
| 6 | RAG pipeline (BGE + hybrid + re-ranking) | ✅ |
| 7 | Hallucination prevention (5-layer) | ✅ |
| 8 | Satellite analyzer (Sentinel-2) | ✅ |
| 9 | Model registry (versioning, A/B, rollback) | ❌ |
| 10 | Evaluation suite | ✅ |

**Failures:**
- **#3 Pyrite→gold:** No hard assertion — gold is still returned when pyrite_prob is high, just with reduced confidence. Must block or refuse classification.
- **#9 Model registry:** Has versioning but lacks A/B testing (traffic splitting, live comparison) and rollback (automatic revert on degradation).
