# AI/ML Engineering Plan

> **Council Member 3: AI/ML Lead**
> Date: 2026-07-25
> Status: ACTIVE
> Budget Constraint: $0 (all free tiers — NVIDIA NIM, PennyLane, Qiskit Aer)

---

## 1. Model Engineering — What Models, What Data

### 1.1 Model Inventory

| Model | Purpose | Training Data Required | Approach | Inference Cost |
|-------|---------|----------------------|----------|----------------|
| **EfficientNet-B4** | Mineral identification from thin-section / hand-sample images | 500+ images per mineral class, ≥20 classes | Transfer learning (ImageNet weights) | Local GPU / CPU |
| **CLIP (ViT-B/32)** | General geological vision — zero-shot image-text matching | Pre-trained; fine-tune on mineral image-caption pairs | Zero-shot + domain fine-tuning | Local GPU |
| **Nemotron 3 Ultra** | Geological reasoning, report generation, QA | Geological textbooks, papers, field logs | RAG + prompt engineering (no fine-tune on NIM) | NVIDIA NIM API (free tier) |
| **Llama 405B** | Complex multi-step geological reasoning, chain-of-thought | Same RAG corpus as Nemotron | RAG + LangGraph orchestration | NVIDIA NIM API (free tier) |
| **YOLOv8 (nano/small)** | Mineral grain detection in field photos & thin sections | Bounding-box annotated mineral images (1000+ instances) | Custom training from pre-trained COCO weights | Local GPU / CPU |
| **PennyLane QML** | Quantum-enhanced mineral classification from spectral data | Raman / XRF / LIBS spectral vectors (200+ per class) | Quantum kernel methods, variational circuits | Qiskit Aer simulator (free) |
| **Whisper (base/small)** | Field voice-note transcription for hands-free logging | Pre-trained; optional fine-tune on geological vocabulary | Zero-shot + custom vocabulary injection | Local CPU |

### 1.2 Model Dependency Graph

```
Field Input
  │
  ├─ Photo ──→ YOLOv8 (detect grains) ──→ EfficientNet-B4 (classify mineral)
  │                                            │
  │                                            └─→ CLIP (cross-reference with text descriptions)
  │
  ├─ Voice ──→ Whisper (transcribe) ──→ Nemotron 3 Ultra (reason + report)
  │                                         │
  │                                         └─→ Llama 405B (complex reasoning fallback)
  │
  ├─ Spectral ──→ PennyLane QML (quantum classification)
  │                    │
  │                    └─→ EfficientNet-B4 (multimodal fusion)
  │
  └─ Text Query ──→ RAG Pipeline (Nemotron + LangGraph + DeerFlow 2.0)
```

---

## 2. Data Pipeline — Field Data to Models

### 2.1 Data Sources

| Source | Type | Volume Target | Collection Method |
|--------|------|---------------|-------------------|
| Field photos | Images (JPG/PNG) | 10,000+ images | Mobile app / camera upload |
| Thin-section micrographs | High-res images | 2,000+ images | Petrographic microscope + camera |
| Spectral readings | CSV/JSON vectors | 5,000+ spectra | Raman / XRF / LIBS instruments |
| Voice field notes | Audio (WAV/MP3) | 500+ hours | Whisper transcription → text |
| Geological literature | PDF / HTML | 500+ papers | Web scraping, PDF extraction |
| Expert annotations | JSON labels | All images labeled | Label Studio (self-hosted) |

### 2.2 Pipeline Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    DATA INGESTION LAYER                  │
│                                                         │
│  Field App ──┐                                          │
│  Microscope ─┤──→ FastAPI Ingest ──→ MinIO (S3-compat) │
│  Spectrometer┤         │                                │
│  Voice Notes ┘         ▼                                │
│              PostgreSQL (metadata + labels)              │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   PROCESSING LAYER                      │
│                                                         │
│  MinIO ──→ Preprocessing Pipeline (Python)              │
│              ├─ Image: resize, augment, normalize        │
│              ├─ Audio: Whisper transcription             │
│              ├─ Spectral: baseline correction, scaling   │
│              └─ Text: chunking, embedding (CLIP)        │
│                                                         │
│  Output ──→ Feature Store (SQLite / Parquet files)      │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   TRAINING LAYER                        │
│                                                         │
│  Feature Store ──→ Training Jobs (local GPU / Colab)    │
│                     ├─ EfficientNet-B4 fine-tune         │
│                     ├─ YOLOv8 custom train               │
│                     ├─ CLIP domain adaptation             │
│                     ├─ PennyLane QML circuits             │
│                     └─ RAG index build (embeddings)      │
│                                                         │
│  Artifacts ──→ Model Registry (MLflow local / DVC)      │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   SERVING LAYER                          │
│                                                         │
│  Model Registry ──→ FastAPI Inference Server             │
│                      ├─ /classify (EfficientNet)         │
│                      ├─ /detect (YOLOv8)                 │
│                      ├─ /match (CLIP)                    │
│                      ├─ /spectral (QML)                  │
│                      ├─ /reason (Nemotron via NIM)       │
│                      └─ /transcribe (Whisper)            │
│                                                         │
│  LangGraph orchestrates multi-model workflows            │
│  DeerFlow 2.0 manages async data flows                  │
└─────────────────────────────────────────────────────────┘
```

### 2.3 Data Storage Strategy

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Raw files | MinIO (S3-compatible) | Images, audio, spectral files |
| Metadata | PostgreSQL | Labels, provenance, timestamps |
| Feature vectors | Parquet / SQLite | Pre-computed embeddings, spectral features |
| Model artifacts | DVC + Git | Version-controlled model weights |
| RAG index | ChromaDB / FAISS | Document embeddings for Nemotron/Llama |

---

## 3. Training Strategy

### 3.1 EfficientNet-B4 — Mineral Identification

```
Strategy: Transfer Learning (frozen backbone → progressive unfreezing)

Phase 1: Frozen backbone
  - Load ImageNet pre-trained weights
  - Replace classifier head: 1000 → N_classes (20+ minerals)
  - Train head only: 20 epochs, lr=1e-3, AdamW
  - Batch size: 32, Image size: 380×380

Phase 2: Partial unfreeze
  - Unfreeze last 2 blocks (blocks 6-7)
  - Fine-tune: 30 epochs, lr=1e-4, cosine annealing
  - Heavy augmentation: rotation, flip, color jitter, CutMix

Phase 3: Full unfreeze (if needed)
  - Unfreeze all layers
  - lr=1e-5, 10 epochs, early stopping (patience=5)

Data Augmentation Pipeline:
  - Random horizontal/vertical flip
  - Random rotation (±30°)
  - Color jitter (brightness, contrast, saturation ±0.2)
  - Random erasing (p=0.3)
  - Mixup (α=0.2)
  - CutMix (α=1.0)

Class Imbalance Handling:
  - Weighted cross-entropy loss (inverse frequency)
  - Oversampling rare minerals via augmentation
  - SMOTE for feature-space balancing (optional)
```

### 3.2 CLIP — Geological Vision-Language

```
Strategy: Zero-shot first, then domain fine-tuning

Phase 1: Zero-shot deployment
  - Use pre-trained CLIP ViT-B/32 as-is
  - Build geological text prompt templates:
    "a photo of [mineral] in [context]"
    "thin section micrograph showing [texture]"
    "hand sample of [rock type] with [feature]"
  - Evaluate zero-shot accuracy on test set

Phase 2: Domain fine-tuning (if zero-shot < 70% accuracy)
  - Linear probe: train linear layer on frozen CLIP features
  - Then: prompt tuning with learned context vectors
  - Dataset: 2000+ mineral image-caption pairs
  - Contrastive loss with temperature scaling

Phase 3: Full fine-tuning (only if critical)
  - LoRA adapters on vision and text encoders
  - Rank=16, α=32, dropout=0.1
  - 10 epochs, lr=2e-5, warmup 500 steps
```

### 3.3 YOLOv8 — Grain Detection

```
Strategy: Transfer learning from COCO pre-trained weights

Model: YOLOv8s (small) — balance of speed and accuracy

Training:
  - Pre-trained: COCO (80 classes → custom mineral classes)
  - Input size: 640×640
  - Epochs: 100, early stopping patience=20
  - lr0=0.01, lrf=0.01, momentum=0.937
  - Augmentation: mosaic (1.0), mixup (0.1), copy-paste (0.1)

Annotation Tool: Label Studio (self-hosted)
  - Bounding boxes for each mineral grain
  - Export in YOLO format
  - Target: 1000+ annotated instances per class

Validation:
  - mAP@0.5 (primary metric)
  - mAP@0.5:0.95 (strict metric)
  - Per-class AP for rare minerals
```

### 3.4 PennyLane QML — Quantum Mineral Classification

```
Strategy: Quantum kernel methods on spectral data

Data Preparation:
  - Input: Raman/XRF/LIBS spectral vectors (1024+ dimensions)
  - Dimensionality reduction: PCA → 16-32 features
  - Normalize to [0, π] range for angle encoding

Quantum Circuit Design (PennyLane):
  ┌─────────────────────────────────────────────┐
  │  Quantum Kernel Circuit (n_qubits=8)        │
  │                                             │
  │  |0⟩ ── Ry(x₁) ── ●── Rz(θ₁) ── Measure  │
  │  |0⟩ ── Ry(x₂) ── X── Ry(θ₂) ── Measure   │
  │  ...                                        │
  │  |0⟩ ── Ry(x₈) ── ●── Rx(θ₈) ── Measure   │
  │                                             │
  │  Entangling layers: 3 (StronglyEntangling)  │
  └─────────────────────────────────────────────┘

Training:
  - Quantum kernel SVM (scikit-learn SVC with precomputed kernel)
  - OR: Variational quantum classifier (VQC)
  - Optimizer: Adam, lr=0.01
  - 200 training iterations
  - Simulator: Qiskit Aer (unlimited, noiseless + noisy)

Benchmark:
  - Classical baseline: Random Forest, SVM (RBF kernel)
  - Quantum advantage target: +2-5% accuracy on spectral data
  - If no advantage: document honestly, use as feature extractor
```

### 3.5 Nemotron 3 Ultra / Llama 405B — Geological Reasoning

```
Strategy: RAG (Retrieval-Augmented Generation) — no fine-tuning

RAG Pipeline (LangGraph + DeerFlow 2.0):

  1. Document Ingestion
     - Geological textbooks → PDF extraction (PyMuPDF)
     - Research papers → structured extraction
     - Field logs → text normalization
     - Chunk: 512 tokens, 50 token overlap

  2. Embedding & Indexing
     - Embedding model: all-MiniLM-L6-v2 (local, free)
     - Vector store: ChromaDB (local)
     - Metadata: source, page, topic, mineral type

  3. Query Pipeline (LangGraph)
     User Query
       → Embed query
       → Retrieve top-k (k=5) relevant chunks
       → Rerank with cross-encoder (ms-marco-MiniLM)
       → Construct prompt with context
       → Nemotron 3 Ultra generates answer
       → Fallback to Llama 405B for complex reasoning

  4. Prompt Engineering Templates:
     - "Based on the following geological context: {context}\n\nQuestion: {query}\n\nProvide a detailed geological analysis:"
     - "You are an expert geologist. Using the reference materials below, identify the mineral assemblage and interpret the petrogenesis:\n{context}\n\nObservation: {query}"

  5. DeerFlow 2.0 Integration:
     - Async document processing pipeline
     - Incremental index updates
     - Multi-source aggregation
```

### 3.6 Whisper — Voice Transcription

```
Strategy: Zero-shot with custom vocabulary

Base model: whisper-base (74M params) — runs on CPU

Custom Vocabulary Injection:
  - Geological terms: feldspar, pyroxene, amphibole, plagioclase...
  - Location names from field sites
  - Rock classification terms
  - Custom G2P (grapheme-to-phoneme) for unusual terms

Post-processing:
  - Whisper output → text normalization
  - Domain-specific spell correction
  - Entity extraction (mineral names, measurements)
  - Feed to Nemotron RAG pipeline for structured logging
```

---

## 4. Evaluation Strategy

### 4.1 Metrics per Model

| Model | Primary Metric | Secondary Metrics | Target | Evaluation Set |
|-------|---------------|-------------------|--------|----------------|
| EfficientNet-B4 | Top-1 Accuracy | Top-3, F1 per class, Confusion matrix | ≥85% | 20% held-out, stratified |
| CLIP | Retrieval Recall@K | Zero-shot accuracy, mAP | Recall@5 ≥ 70% | Curated test pairs |
| YOLOv8 | mAP@0.5 | mAP@0.5:0.95, inference latency | mAP@0.5 ≥ 0.75 | Hold-out images |
| QML | Classification accuracy | F1, comparison vs classical | ≥ classical baseline | Cross-validation (5-fold) |
| Nemotron/Llama | RAG faithfulness | Answer relevance, context precision | Faithfulness ≥ 0.8 | 100 expert-verified QA pairs |
| Whisper | WER (Word Error Rate) | CER, keyword accuracy | WER ≤ 15% | 50 field recordings |

### 4.2 Evaluation Protocols

```python
# EfficientNet Evaluation Protocol
eval_protocol = {
    "split": "stratified 80/10/10 (train/val/test)",
    "cross_validation": "5-fold stratified CV on full dataset",
    "per_class_analysis": "classification_report with precision/recall/f1",
    "confusion_analysis": "top-5 confused mineral pairs",
    "robustness": "test with different lighting, angles, scales",
    "failure_analysis": "manual review of misclassified samples"
}

# YOLOv8 Evaluation Protocol
yolo_eval = {
    "metrics": ["mAP@0.5", "mAP@0.5:0.95", "precision", "recall"],
    "per_class": True,
    "confusion_matrix": True,
    "speed_benchmark": "inference time per image (target: <100ms)",
    "edge_cases": "overlapping grains, partial occlusions, small objects"
}

# QML Evaluation Protocol
qml_eval = {
    "comparison": "quantum vs classical (RF, SVM, MLP)",
    "statistical_test": "paired t-test on 5-fold CV scores",
    "noise_analysis": "performance under simulated quantum noise",
    "scalability": "accuracy vs number of qubits (4, 8, 16)"
}

# RAG Evaluation Protocol
rag_eval = {
    "faithfulness": "LLM-as-judge: does answer follow from context?",
    "relevance": "does answer address the question?",
    "groundedness": "are claims supported by retrieved documents?",
    "test_set": "100 expert-verified geological QA pairs",
    "metrics": ["faithfulness_score", "answer_relevancy", "context_precision"]
}
```

### 4.3 Continuous Evaluation

- **Weekly**: Run evaluation suite on latest models
- **Monthly**: Full re-evaluation with new field data
- **Per-deploy**: Automated regression tests before model updates
- **Human-in-the-loop**: Geologist review of 10% of predictions

---

## 5. MLOps — Deploy, Monitor, Update

### 5.1 Model Registry & Versioning

```
Tool: DVC (Data Version Control) + Git

Model Artifact Structure:
  models/
  ├── efficientnet-b4/
  │   ├── v1.0.0/
  │   │   ├── model.pt
  │   │   ├── config.yaml
  │   │   ├── metrics.json
  │   │   └── dvc.lock
  │   └── latest → v1.0.0
  ├── yolov8s/
  │   ├── v1.0.0/
  │   │   ├── best.pt
  │   │   └── metrics.json
  │   └── latest → v1.0.0
  ├── qml/
  │   ├── v1.0.0/
  │   │   ├── circuit_params.pkl
  │   │   └── kernel_matrix.npy
  │   └── latest → v1.0.0
  └── rag/
      ├── v1.0.0/
      │   ├── chromadb/
      │   └── embedding_model/
      └── latest → v1.0.0
```

### 5.2 Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│              FastAPI Inference Server                    │
│                                                         │
│  Endpoints:                                             │
│  POST /api/v1/classify     → EfficientNet-B4            │
│  POST /api/v1/detect       → YOLOv8                     │
│  POST /api/v1/match        → CLIP                       │
│  POST /api/v1/spectral     → PennyLane QML              │
│  POST /api/v1/reason       → Nemotron/Llama via NIM     │
│  POST /api/v1/transcribe   → Whisper                    │
│  POST /api/v1/pipeline     → Full multi-model pipeline  │
│  GET  /api/v1/health       → Health check               │
│  GET  /api/v1/models       → List loaded models         │
│                                                         │
│  Middleware:                                             │
│  - Request validation (Pydantic)                        │
│  - Rate limiting (10 req/s per client)                  │
│  - Response caching (Redis, TTL=1h)                     │
│  - Logging (structured JSON)                            │
│  - Prometheus metrics export                            │
└─────────────────────────────────────────────────────────┘
```

### 5.3 Monitoring Stack

| Component | Tool | What It Tracks |
|-----------|------|---------------|
| Model performance | Custom metrics endpoint | Accuracy, latency, throughput |
| Data drift | Evidently AI (open-source) | Feature distribution shifts |
| Prediction drift | Evidently AI | Output distribution changes |
| Infrastructure | Prometheus + Grafana | CPU, GPU, memory, disk |
| Logging | Structured JSON logs | Request/response, errors |
| Alerts | Grafana alerts | Accuracy drop > 5%, latency > 500ms |

### 5.4 Update & Retraining Strategy

```
Trigger-based retraining:

1. DATA TRIGGER: New labeled data > 500 samples
   → Run automated training pipeline
   → Compare new model vs current (A/B on holdout)
   → Auto-deploy if improvement > 2%

2. DRIFT TRIGGER: Evidently detects significant drift
   → Alert team
   → Investigate root cause
   → Retrain with recent data if warranted

3. SCHEDULED: Monthly full retraining
   → Incorporate all new field data
   → Full evaluation suite
   → Staged rollout (10% → 50% → 100%)

4. MANUAL: Geologist flags systematic errors
   → Investigate failure cases
   → Add corrections to training data
   → Priority retrain

CI/CD Pipeline (GitHub Actions):
  push to main → lint → unit tests → integration tests
  → train (if data changed) → evaluate → deploy (if better)
  → smoke tests → health check → done
```

---

## 6. Big Tech Standards — How They Do ML Engineering

### 6.1 Google's ML Engineering Practice

| Google Principle | Our Implementation |
|-----------------|-------------------|
| **Feature Store** (Vertex AI Feature Store) | Local Parquet-based feature store with versioning |
| **ML Metadata (MLMD)** | DVC + Git for full experiment lineage |
| **Continuous Training** | Trigger-based retraining pipeline |
| **Model Cards** | Document every model: intended use, limitations, fairness |
| **A/B Testing** | Shadow deployment + comparison on holdout |
| **TFX Pipelines** | Our equivalent: DeerFlow 2.0 + FastAPI pipelines |

### 6.2 OpenAI's Approach

| OpenAI Practice | Our Implementation |
|----------------|-------------------|
| **RLHF / RLAIF** | Geologist feedback loop for RAG quality |
| **Red-teaming** | Adversarial testing of mineral identification edge cases |
| **Evals framework** | Custom eval suite per model (see Section 4) |
| **Structured outputs** | Pydantic response models for all API endpoints |
| **Safety testing** | Confidence thresholds, fallback to "unknown" class |

### 6.3 Anthropic's Approach

| Anthropic Practice | Our Implementation |
|-------------------|-------------------|
| **Constitutional AI** | RAG prompt guardrails: "only answer from provided context" |
| **Interpretability** | GradCAM for EfficientNet, attention maps for CLIP |
| **Harmlessness** | Confidence scoring, refuse to identify below threshold |
| **Scaling laws** | Track loss curves, determine if more data helps |

### 6.4 Our Engineering Standards (Derived)

```
MINIMUM STANDARDS (non-negotiable):
  ✓ Every model has a Model Card (purpose, data, limitations, metrics)
  ✓ Every model version is tracked in DVC + Git
  ✓ Every deployment has automated smoke tests
  ✓ Every prediction is logged with confidence score
  ✓ Every model has a fallback ("I don't know" > wrong answer)
  ✓ Data provenance is tracked end-to-end

QUALITY GATES:
  ✓ Model cannot deploy if eval metrics drop > 2% vs previous
  ✓ RAG cannot deploy if faithfulness < 0.7 on test set
  ✓ All endpoints must respond < 500ms (p95)
  ✓ All endpoints must handle concurrent requests (10+)
```

---

## 7. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-4)
- [ ] Set up MinIO, PostgreSQL, ChromaDB
- [ ] Build FastAPI server skeleton
- [ ] Deploy Whisper (zero-shot) for voice transcription
- [ ] Deploy Nemotron 3 Ultra via NIM API with basic RAG
- [ ] Begin data collection & annotation (Label Studio)

### Phase 2: Core Models (Weeks 5-8)
- [ ] Train EfficientNet-B4 on initial mineral dataset (Phase 1 + 2)
- [ ] Train YOLOv8 on annotated grain images
- [ ] Deploy CLIP zero-shot, evaluate baseline
- [ ] Build LangGraph orchestration pipeline

### Phase 3: Advanced Models (Weeks 9-12)
- [ ] Implement PennyLane QML circuit, benchmark vs classical
- [ ] Fine-tune CLIP domain adaptation (if needed)
- [ ] Full RAG pipeline with reranking
- [ ] Integrate DeerFlow 2.0 for async data flows

### Phase 4: Production Hardening (Weeks 13-16)
- [ ] MLOps pipeline: DVC, CI/CD, monitoring
- [ ] Evidently AI drift detection
- [ ] Performance optimization (model quantization, caching)
- [ ] Load testing, security audit
- [ ] Model cards for all models

---

## 8. Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Insufficient training data | High | Transfer learning, augmentation, few-shot techniques |
| NIM free tier rate limits | Medium | Caching, batch inference, fallback to local models |
| Quantum simulation slow | Low | Use small circuits (8 qubits), optimize gate count |
| Model accuracy below target | High | Ensemble methods, collect more data, expert review loop |
| Data quality issues | Medium | Automated validation, outlier detection, expert QC |
| Single point of failure | Medium | Model fallbacks, graceful degradation |

---

## Appendix A: Key Libraries & Versions

```yaml
core:
  python: "3.11+"
  pytorch: "2.x"
  torchvision: "latest compatible"
  ultralytics: "8.x"          # YOLOv8
  transformers: "4.x"         # CLIP, Whisper
  pennylane: "0.38+"
  qiskit: "1.x"
  qiskit-aer: "0.14+"

serving:
  fastapi: "0.110+"
  uvicorn: "0.29+"
  pydantic: "2.x"

data:
  minio: "7.x"
  psycopg2: "2.9+"
  chromadb: "0.5+"
  dvc: "3.x"

monitoring:
  evidently: "0.4+"
  prometheus-client: "0.20+"

orchestration:
  langgraph: "0.2+"
  langchain: "0.3+"
  deerflow: "2.0"
```

---

*Council Member 3 — AI/ML Engineering Plan — Complete*
*Next review: After Phase 1 completion*
