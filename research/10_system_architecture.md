# AI Mining Platform — Complete System Architecture

## Kenya, East Africa — First AI-Powered Mining Platform in Africa

**Document Version:** 1.0  
**Date:** 2026-07-25  
**Status:** Architecture Blueprint — Buildable  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Overall System Architecture](#2-overall-system-architecture)
3. [AI/ML Pipeline — Geological Data to Mineral Estimation](#3-aiml-pipeline)
4. [Multi-Agent System Design](#4-multi-agent-system-design)
5. [Data Collection Layer](#5-data-collection-layer)
6. [Processing Layer](#6-processing-layer)
7. [Knowledge Layer](#7-knowledge-layer)
8. [Decision Layer](#8-decision-layer)
9. [User Interface Layer](#9-user-interface-layer)
10. [NVIDIA Superagent Integration](#10-nvidia-superagent-integration)
11. [Flywheel Architecture — Self-Improving System](#11-flywheel-architecture)
12. [MVP & Phased Rollout](#12-mvp--phased-rollout)
13. [Technology Stack](#13-technology-stack)
14. [Quantum Computing Integration](#14-quantum-computing-integration)
15. [Security, Privacy & IP Protection](#15-security-privacy--ip-protection)
16. [Open-Source vs Proprietary Strategy](#16-open-source-vs-proprietary-strategy)
17. [Cost Estimates & Infrastructure](#17-cost-estimates--infrastructure)

---

## 1. Executive Summary

This document defines the complete system architecture for **PangaAI** — an AI-powered mineral exploration and mining intelligence platform designed to operate in Kenya and scale across East Africa. The platform combines drone-based geophysical surveys, smartphone field data collection, multi-agent AI analysis, and cloud-based processing to democratize mineral exploration.

**Core thesis:** Kenya has significant untapped mineral wealth (titanium, gold, rare earth elements, gemstones, soda ash, fluorspar) but lacks the exploration infrastructure to identify and quantify deposits efficiently. AI can compress a 5-year exploration timeline into 6 months at 1/10th the cost.

**What makes this buildable today:**
- All referenced AI models exist (NVIDIA Nemotron, Llama 3, Mistral, Gemma)
- Drone survey hardware is commercially available (DJI Matrice 350 + geophysical payloads)
- Cloud infrastructure is available via AWS Africa (Cape Town), Azure South Africa, and GCP
- Quantum APIs are live (IBM Qiskit Runtime, D-Wave Leap, Amazon Braket)
- Mobile penetration in Kenya is >90% — smartphone data collection is viable immediately

---

## 2. Overall System Architecture

### 2.1 Architecture Diagram (Text)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE LAYER                            │
│  ┌──────────┐  ┌──────────────┐  ┌────────────┐  ┌─────────────────┐  │
│  │ Mobile   │  │ Web          │  │ API        │  │ WhatsApp/       │  │
│  │ App      │  │ Dashboard    │  │ Gateway    │  │ Telegram Bot    │  │
│  └────┬─────┘  └──────┬───────┘  └─────┬──────┘  └───────┬─────────┘  │
│       └────────────────┼────────────────┼─────────────────┘            │
└────────────────────────┼────────────────┼──────────────────────────────┘
                         │                │
┌────────────────────────┼────────────────┼──────────────────────────────┐
│                    DECISION LAYER       │                              │
│  ┌──────────────┐ ┌────┴──────┐ ┌──────┴───────┐ ┌────────────────┐  │
│  │ Risk         │ │ Financial │ │ Recommend-   │ │ Regulatory     │  │
│  │ Assessment   │ │ Modeling  │ │ ation Engine │ │ Compliance     │  │
│  └──────┬───────┘ └─────┬─────┘ └──────┬───────┘ └───────┬────────┘  │
│         └───────────────┼──────────────┼─────────────────┘            │
└─────────────────────────┼──────────────┼──────────────────────────────┘
                          │              │
┌─────────────────────────┼──────────────┼──────────────────────────────┐
│                  PROCESSING LAYER      │                              │
│  ┌──────────────┐ ┌────┴──────┐ ┌─────┴────────┐ ┌───────────────┐  │
│  │ AI/ML        │ │ Quantum   │ │ Multi-Agent  │ │ Geospatial    │  │
│  │ Pipeline     │ │ Compute   │ │ Orchestrator │ │ Engine        │  │
│  └──────┬───────┘ └─────┬─────┘ └──────┬───────┘ └───────┬───────┘  │
│         └───────────────┼──────────────┼─────────────────┘            │
└─────────────────────────┼──────────────┼──────────────────────────────┘
                          │              │
┌─────────────────────────┼──────────────┼──────────────────────────────┐
│                  KNOWLEDGE LAYER       │                              │
│  ┌──────────────┐ ┌────┴──────┐ ┌─────┴────────┐ ┌───────────────┐  │
│  │ Geological   │ │ Historical│ │ Market Data  │ │ Regulatory    │  │
│  │ Database     │ │ Mining DB │ │ & Prices     │ │ Database      │  │
│  └──────┬───────┘ └─────┬─────┘ └──────┬───────┘ └───────┬───────┘  │
│         └───────────────┼──────────────┼─────────────────┘            │
└─────────────────────────┼──────────────┼──────────────────────────────┘
                          │              │
┌─────────────────────────┼──────────────┼──────────────────────────────┐
│                DATA COLLECTION LAYER   │                              │
│  ┌──────────┐ ┌────┴───┐ ┌─────┴────┐ ┌───────┐ ┌───────────────┐  │
│  │ Drones   │ │ Smart- │ │ Portable │ │ IoT   │ │ Satellite     │  │
│  │ & UAVs   │ │ phones │ │ Sensors  │ │ Nodes │ │ Imagery       │  │
│  └──────────┘ └────────┘ └──────────┘ └───────┘ └───────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow Summary

```
Field Collection → Edge Processing → Cloud Ingestion → AI Pipeline →
Knowledge Enrichment → Agent Analysis → Decision Engine → User Interface
                                                          ↓
                                                   Feedback Loop → Model Retraining
```

### 2.3 Core Design Principles

1. **Mobile-first** — The primary field interface is a smartphone, not a desktop
2. **Offline-capable** — Edge processing handles connectivity gaps in remote areas
3. **Agent-based** — No monolithic AI; specialized agents collaborate
4. **Data flywheel** — Every interaction improves the model
5. **API-first** — Every component exposes APIs; the platform is composable
6. **Kenya-contextualized** — Trained on East African geology, not generic models

---

## 3. AI/ML Pipeline — Geological Data to Mineral Estimation

### 3.1 Pipeline Stages

```
Stage 1: Data Ingestion          Stage 2: Feature Engineering
┌─────────────────────┐          ┌──────────────────────────┐
│ • Drone imagery     │          │ • Spectral signatures    │
│ • Geophysical data  │──────────│ • Magnetic anomalies     │
│ • Soil samples      │          │ • Geochemical vectors    │
│ • Historical maps   │          │ • Structural features    │
│ • Satellite data    │          │ • Terrain characteristics │
└─────────────────────┘          └────────────┬─────────────┘
                                              │
Stage 3: AI Analysis              Stage 4: Estimation
┌──────────────────────┐          ┌──────────────────────────┐
│ • CNN for imagery    │          │ • Resource estimation    │
│ • GNN for geology    │──────────│ • Confidence intervals   │
│ • Transformer for    │          │ • Grade-tonnage curves   │
│   time-series geo    │          │ • Economic viability     │
│ • Anomaly detection  │          │ • Risk scoring           │
└──────────────────────┘          └──────────────────────────┘
```

### 3.2 Model Architecture

| Model | Purpose | Architecture | Training Data |
|-------|---------|-------------|---------------|
| **GeoVision** | Drone/satellite image analysis for geological features | ResNet-152 + custom geological head | Sentinel-2, drone surveys, geological maps |
| **MagNet** | Magnetic anomaly interpretation | 3D U-Net | Aeromagnetic survey data, Kenya Geological Survey |
| **SpectraAI** | Hyperspectral mineral identification | 1D-CNN + Attention | USGS spectral library, field samples |
| **GeoChem Predictor** | Soil/rock geochemistry → mineral probability | XGBoost ensemble + Neural Network | NGDB geochemistry, field assay results |
| **DepositNet** | Multi-modal mineral deposit probability | Multi-modal Transformer | Combined geophysical, geochemical, structural data |
| **GradeEstimator** | Ore grade estimation from exploration data | Gaussian Process Regression | Historical mining data, drill results |

### 3.3 Model Training Strategy

**Phase 1 — Transfer Learning (Weeks 1-4):**
- Start with pre-trained models (ImageNet for vision, geological foundation models)
- Fine-tune on available Kenyan geological data from:
  - Kenya Geological Survey (KGS) archives
  - UNDP mining reports
  - Academic papers on Kenyan mineralization
  - Open geological databases (USGS, BGS, AGS)

**Phase 2 — Active Learning (Months 2-3):**
- Deploy models with uncertainty quantification
- Flag low-confidence predictions for expert review
- Expert annotations feed back into training loop
- Each field survey improves the model

**Phase 3 — Self-Supervised (Months 4-6):**
- Contrastive learning on unlabeled drone imagery
- Masked autoencoders for geophysical data
- Foundation model for East African geology

### 3.4 Mineral Estimation Methodology

The platform uses a **Bayesian resource estimation** approach:

```python
# Pseudocode for resource estimation
def estimate_mineral_resource(site_data):
    # Step 1: Multi-modal feature extraction
    geo_features = GeoVision.extract(drone_imagery)
    mag_features = MagNet.process(geophysical_data)
    chem_features = GeoChem.analyze(soil_samples)
    
    # Step 2: Deposit probability
    p_deposit = DepositNet.predict(geo_features, mag_features, chem_features)
    
    # Step 3: Grade estimation with uncertainty
    grade_dist = GradeEstimator.predict_distribution(
        features=combined_features,
        prior=geological_prior,
        n_samples=10000  # Monte Carlo sampling
    )
    
    # Step 4: Tonnage estimation
    tonnage = estimate_tonnage(
        surface_area=site_geometry.area,
        depth_estimate=mag_features.depth_model,
        density=rock_density_prior
    )
    
    # Step 5: Resource classification (JORC/CIM compliant)
    resource = classify_resource(
        confidence=p_deposit,
        grade_distribution=grade_dist,
        tonnage=tonnage,
        data_density=sampling_density
    )
    
    return resource  # Inferred → Indicated → Measured
```

---

## 4. Multi-Agent System Design

### 4.1 Agent Architecture Overview

The platform uses a **hierarchical multi-agent system** where specialized agents handle distinct domains and a supervisor agent coordinates their work.

```
                    ┌─────────────────────┐
                    │   SUPERVISOR AGENT   │
                    │  (Orchestrator)      │
                    │  Model: Nemotron 4   │
                    └──────────┬──────────┘
                               │
        ┌──────────┬───────────┼───────────┬──────────┐
        │          │           │           │          │
   ┌────┴────┐ ┌───┴───┐ ┌────┴────┐ ┌───┴───┐ ┌───┴────┐
   │ Geo     │ │ Data  │ │ Market  │ │ Risk  │ │Report  │
   │ Agent   │ │ Agent │ │ Agent   │ │ Agent │ │Agent   │
   └─────────┘ └───────┘ └─────────┘ └───────┘ └────────┘
```

### 4.2 Agent Specifications

#### 4.2.1 Supervisor Agent (Orchestrator)

| Property | Value |
|----------|-------|
| **Role** | Task decomposition, agent coordination, result synthesis |
| **Model** | NVIDIA Nemotron 4 Ultra (via NVIDIA NIM) |
| **Framework** | LangGraph (LangChain) for workflow orchestration |
| **Memory** | Long-term: PostgreSQL + pgvector; Short-term: Redis |
| **Communication** | Message queue (Redis Streams) between agents |

**Responsibilities:**
- Receive user queries and decompose into sub-tasks
- Route sub-tasks to appropriate specialist agents
- Resolve conflicts between agent outputs
- Maintain conversation context and project state
- Trigger autonomous workflows (e.g., "analyze new drone data")

#### 4.2.2 Geological Analysis Agent

| Property | Value |
|----------|-------|
| **Role** | Interpret geological data, identify mineralization patterns |
| **Model** | Llama 3.1 70B (geological fine-tune) + GeoVision CNN |
| **Tools** | QGIS integration, GDAL, rasterio, scikit-image |
| **Knowledge** | Kenya geological maps, mineralization models, structural geology |
| **Capabilities** | Lithological mapping, structural analysis, alteration detection |

**Example interaction:**
```
User: "What minerals might be in the area around Kwale?"
Geo Agent:
1. Queries geological database for Kwale county geology
2. Retrieves latest drone survey imagery
3. Runs GeoVision on imagery → identifies coastal sand deposits
4. Cross-references with known titanium-zircon mineralization
5. Returns: "High probability of ilmenite, rutile, zircon in 
   coastal sandstones. Similar geology to existing Base Titanium 
   deposit. Recommend magnetic survey to delineate extent."
```

#### 4.2.3 Data Ingestion Agent

| Property | Value |
|----------|-------|
| **Role** | Collect, clean, validate, and standardize incoming data |
| **Model** | Mistral 7B (for data parsing) + custom validation models |
| **Tools** | Apache Airflow, pandas, great_expectations |
| **Capabilities** | Format conversion, quality checks, anomaly flagging, data fusion |

**Handles:**
- Drone survey data (RGB, multispectral, LiDAR, magnetic)
- Smartphone field observations (photos, GPS, descriptions)
- Lab assay results (XRF, ICP-MS)
- Historical records (scanned maps, PDF reports → structured data)
- Satellite imagery (Sentinel-2, Landsat, Planet Labs)

#### 4.2.4 Market Intelligence Agent

| Property | Value |
|----------|-------|
| **Role** | Track commodity prices, market trends, offtake opportunities |
| **Model** | NVIDIA Nemotron 4 Mini (fast inference) |
| **Tools** | Web scraping, financial APIs, news analysis |
| **Data Sources** | LME, Bloomberg, Reuters, Mining.com, Kitco |
| **Capabilities** | Price forecasting, demand analysis, competitor tracking |

#### 4.2.5 Risk Assessment Agent

| Property | Value |
|----------|-------|
| **Role** | Evaluate geological, financial, regulatory, and environmental risks |
| **Model** | Gemma 2 27B (reasoning-focused) |
| **Tools** | Monte Carlo simulation, decision trees, scenario analysis |
| **Capabilities** | Risk scoring, mitigation strategies, compliance checking |

**Risk categories assessed:**
1. **Geological risk** — Confidence in resource estimate, geological complexity
2. **Financial risk** — Capital requirements, commodity price exposure, ROI uncertainty
3. **Regulatory risk** — Mining license status, environmental permits, community relations
4. **Environmental risk** — Water table impact, deforestation, rehabilitation costs
5. **Operational risk** — Infrastructure access, security, supply chain

#### 4.2.6 Report Generation Agent

| Property | Value |
|----------|-------|
| **Role** | Generate JORC/CIM-compliant reports, investor decks, regulatory filings |
| **Model** | Nemotron 4 Ultra + custom templates |
| **Tools** | LaTeX, WeasyPrint, Chart.js, D3.js |
| **Capabilities** | NI 43-101 reports, technical summaries, investor presentations |

### 4.3 Agent Communication Protocol

```python
# Agent message format (inspired by NVIDIA Agent Toolkit)
class AgentMessage:
    sender: str          # Agent ID
    receiver: str        # Agent ID or "broadcast"
    message_type: str    # "request", "response", "alert", "update"
    task_id: str         # Correlation ID for tracking
    payload: dict        # The actual content
    priority: int        # 0=critical, 1=high, 2=normal, 3=low
    timestamp: datetime
    confidence: float    # Agent's confidence in its output (0-1)
    requires_human: bool # Flag if human review is needed

# Communication bus: Redis Streams
# Each agent subscribes to its own channel + broadcast channel
# Supervisor monitors all channels for coordination
```

### 4.4 Agent Coordination Patterns

1. **Sequential Pipeline** — Data Agent → Geo Agent → Risk Agent → Report Agent
2. **Parallel Fan-out** — Geo Agent + Market Agent + Risk Agent work simultaneously
3. **Debate Pattern** — Two agents argue opposing interpretations; Supervisor judges
4. **Human-in-the-loop** — Agent flags uncertainty → routes to human expert → feeds back

---

## 5. Data Collection Layer

### 5.1 Drone-Based Survey System

**Primary Platform:** DJI Matrice 350 RTK (or equivalent)

| Sensor | Purpose | Product | Cost (USD) |
|--------|---------|---------|------------|
| RGB Camera | Surface mapping, structure identification | Zenmuse P1 | ~$7,000 |
| Multispectral | Vegetation stress, alteration mapping | MicaSense RedEdge-P | ~$6,500 |
| Hyperspectral | Mineral identification from spectral signatures | Headwall Nano-Hyperspec | ~$35,000 |
| Magnetometer | Magnetic anomaly detection for subsurface geology | Geometrics MagArrow | ~$25,000 |
| LiDAR | Terrain modeling, vegetation penetration | Zenmuse L2 | ~$15,000 |
| Thermal | Geothermal features, water seepage | Zenmuse H30T | ~$12,000 |

**Survey Protocol:**
- Grid spacing: 50m lines for detailed surveys, 200m for regional
- Flight altitude: 30-120m depending on sensor and resolution needs
- Coverage: Up to 5 km²/day with single drone team
- Data volume: ~50 GB/day raw → 5-10 GB processed

### 5.2 Smartphone Field Collection App

**Platform:** React Native (cross-platform iOS/Android)
**Offline-first:** SQLite local storage, sync when connectivity available

**Features:**
- **Photo geotagging** — Every photo auto-tagged with GPS, compass bearing, timestamp
- **Rock description wizard** — Structured input: color, hardness, grain size, mineralogy
- **Soil sample logging** — Sample ID, depth, color, description, photo
- **Voice notes** — Transcribed via Whisper, attached to location
- **Offline maps** — Cached topographic and geological base maps
- **QR code sample tracking** — Print labels, scan for chain-of-custody
- **AR overlay** — Point phone at outcrop, see geological interpretation

**Data flow:**
```
Phone → SQLite (local) → Sync Engine → API Gateway → Data Agent → PostgreSQL
```

### 5.3 Portable Field Instruments

| Instrument | Data Collected | Integration Method |
|------------|---------------|-------------------|
| **Portable XRF (pXRF)** — Olympus Vanta | Elemental composition (Mg-U) | Bluetooth → Phone app |
| **Portable VNIR Spectrometer** — ASD TerraSpec | Mineral identification | USB → Phone/ Laptop |
| **Magnetic Susceptibility Meter** — KT-10 | Rock magnetic properties | Bluetooth → Phone app |
| **GPS/GNSS** — Trimble R12i | Centimeter-accurate positioning | Bluetooth → Phone app |
| **Digital Geological Compass** — FieldMove | Structural measurements | App-based |

### 5.4 IoT Sensor Network

For ongoing monitoring at exploration/production sites:

- **Weather stations** — Rainfall, temperature, humidity (affects operations)
- **Water quality sensors** — pH, turbidity, heavy metals (environmental compliance)
- **Ground vibration sensors** — Seismic activity, blast monitoring
- **Soil moisture probes** — Water table monitoring
- **Solar-powered LoRaWAN gateways** — Long-range, low-power data transmission

### 5.5 Satellite Data Sources

| Source | Resolution | Revisit | Cost | Use Case |
|--------|-----------|---------|------|----------|
| Sentinel-2 (ESA) | 10m | 5 days | Free | Regional vegetation/alteration mapping |
| Landsat 9 (NASA) | 30m | 16 days | Free | Historical change detection |
| Planet Labs | 3m | Daily | ~$500/month | High-res monitoring |
| Maxar (WorldView) | 30cm | On-demand | ~$25/km² | Detailed site surveys |
| ASTER (NASA) | 30m | 16 days | Free | Thermal/alteration mapping |

---

## 6. Processing Layer

### 6.1 Cloud Architecture

**Primary cloud:** AWS (Africa — Cape Town region `af-south-1`)
**Secondary:** Azure South Africa (for enterprise clients needing Azure)

```
┌──────────────────────────────────────────────────────────┐
│                    AWS af-south-1                         │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │ S3           │  │ SageMaker    │  │ EKS            │ │
│  │ Data Lake    │  │ ML Training  │  │ Agent Runtime  │ │
│  │ (raw + proc) │  │ & Inference  │  │ (Kubernetes)   │ │
│  └──────┬───────┘  └──────┬───────┘  └───────┬────────┘ │
│         │                 │                   │          │
│  ┌──────┴─────────────────┴───────────────────┴────────┐ │
│  │              VPC (Private Network)                   │ │
│  └──────┬─────────────────┬───────────────────┬────────┘ │
│         │                 │                   │          │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌───────┴────────┐ │
│  │ RDS          │  │ ElastiCache  │  │ API Gateway    │ │
│  │ PostgreSQL   │  │ Redis        │  │ + CloudFront   │ │
│  │ + PostGIS    │  │ (agent msgs) │  │ (public API)   │ │
│  └──────────────┘  └──────────────┘  └────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### 6.2 Edge Processing

For areas with poor connectivity (common in rural Kenya):

- **NVIDIA Jetson Orin Nano** — Deployed at field base stations
  - Runs lightweight inference models (SpectraAI, basic image classification)
  - Processes drone data locally before uploading
  - SQLite local database, syncs to cloud when connected
- **Smartphone edge** — On-device TFLite models for basic mineral ID
- **Compression** — COG (Cloud Optimized GeoTIFF) for satellite/drone imagery

### 6.3 ML Training Infrastructure

| Component | Service | Spec | Cost/month |
|-----------|---------|------|------------|
| GPU Training | AWS SageMaker | ml.g5.4xlarge (A10G, 24GB) | ~$1,500 |
| GPU Inference | AWS SageMaker | ml.g5.2xlarge (A10G, 24GB) | ~$750 |
| Data Processing | AWS EMR / Glue | Spark cluster | ~$500 |
| Vector Database | pgvector on RDS | db.r6g.xlarge | ~$400 |
| Model Registry | MLflow on EKS | t3.xlarge | ~$150 |

### 6.4 NVIDIA NIM (NVIDIA Inference Microservices)

For production AI inference, use NVIDIA NIM:

```yaml
# Deploy Nemotron via NVIDIA NIM
services:
  nemotron-ultra:
    image: nvcr.io/nim/nvidia/nemotron-4-ultra-instruct:latest
    ports:
      - "8000:8000"
    environment:
      - NGC_API_KEY=${NGC_API_KEY}
      - NIM_MAX_MODEL_LEN=4096
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

**Why NIM:** Pre-optimized inference, 2-3x faster than vanilla vLLM, built-in LangChain integration.

---

## 7. Knowledge Layer

### 7.1 Geological Database

**Core schema (PostgreSQL + PostGIS):**

```sql
-- Sites and survey areas
CREATE TABLE survey_sites (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    county VARCHAR(100),
    geom GEOMETRY(POLYGON, 4326),
    status VARCHAR(50), -- 'prospect', 'exploration', 'advanced', 'production'
    created_at TIMESTAMP DEFAULT NOW()
);

-- Geological samples
CREATE TABLE samples (
    id UUID PRIMARY KEY,
    site_id UUID REFERENCES survey_sites(id),
    sample_type VARCHAR(50), -- 'rock', 'soil', 'stream_sediment', 'drill_core'
    geom GEOMETRY(POINT, 4326),
    depth_m DECIMAL(10,2),
    collected_at TIMESTAMP,
    collector_id UUID,
    photos TEXT[], -- S3 URLs
    description TEXT
);

-- Geochemical assays
CREATE TABLE assays (
    id UUID PRIMARY KEY,
    sample_id UUID REFERENCES samples(id),
    lab_name VARCHAR(100),
    method VARCHAR(50), -- 'XRF', 'ICP-MS', 'AAS'
    element VARCHAR(10),
    value_ppm DECIMAL(15,4),
    detection_limit DECIMAL(15,4),
    certified BOOLEAN DEFAULT FALSE
);

-- Drone survey data
CREATE TABLE drone_surveys (
    id UUID PRIMARY KEY,
    site_id UUID REFERENCES survey_sites(id),
    survey_type VARCHAR(50), -- 'RGB', 'multispectral', 'magnetic', 'LiDAR'
    flight_date DATE,
    area_km2 DECIMAL(10,4),
    resolution_m DECIMAL(6,3),
    data_url TEXT, -- S3 URL to processed data
    metadata JSONB
);

-- Mineral occurrences
CREATE TABLE mineral_occurrences (
    id UUID PRIMARY KEY,
    site_id UUID REFERENCES survey_sites(id),
    mineral_name VARCHAR(100),
    confidence DECIMAL(3,2), -- 0-1
    estimated_grade DECIMAL(10,4),
    grade_unit VARCHAR(20), -- 'ppm', '%', 'g/t'
    estimation_method VARCHAR(100),
    model_version VARCHAR(50),
    verified_by UUID, -- geologist who verified
    geom GEOMETRY(POLYGON, 4326)
);

-- Vector embeddings for RAG
CREATE TABLE knowledge_embeddings (
    id UUID PRIMARY KEY,
    content TEXT,
    embedding VECTOR(1536), -- pgvector
    source_type VARCHAR(50), -- 'report', 'paper', 'regulation', 'field_note'
    source_url TEXT,
    metadata JSONB
);
```

### 7.2 Knowledge Sources

| Source | Type | Volume | Access |
|--------|------|--------|--------|
| Kenya Geological Survey (KGS) | Geological maps, reports | ~5,000 documents | Public + partnership |
| Mining Cadastre (Kenya) | License boundaries, ownership | ~10,000 records | API / scrape |
| USGS Mineral Resources Data | Global mineral deposits | ~300,000 records | Public API |
| British Geological Survey | African geological maps | ~2,000 maps | Licensed |
| Academic papers (ResearchGate, Google Scholar) | Geological research | ~50,000 relevant | API + scraping |
| Historical colonial geological reports | Pre-independence surveys | ~500 documents | Archive scanning |
| Commodity market data | Prices, forecasts, demand | Real-time | Bloomberg/LME API |

### 7.3 RAG (Retrieval-Augmented Generation) Pipeline

```
User Query → Embedding Model (voyage-3) → Vector Search (pgvector)
    → Top-K Relevant Documents → Context Injection → LLM Response
```

**Use cases:**
- "What is the typical geology of the Mozambique Belt in Kenya?" → RAG from KGS reports
- "What are current rare earth prices?" → RAG from market data + live API
- "What permits do I need for titanium mining in Kwale?" → RAG from mining regulations

---

## 8. Decision Layer

### 8.1 Recommendation Engine

Generates actionable recommendations based on all available data:

```python
class RecommendationEngine:
    def generate_recommendations(self, site_id: str) -> List[Recommendation]:
        # Gather all data
        site = self.db.get_site(site_id)
        geo_data = self.geo_agent.analyze(site)
        market = self.market_agent.get_context(site.primary_mineral)
        risk = self.risk_agent.assess(site)
        
        recommendations = []
        
        # Geological recommendations
        if geo_data.confidence < 0.7:
            recommendations.append(Recommendation(
                type="SURVEY",
                priority="HIGH",
                action="Conduct ground magnetic survey to increase confidence",
                rationale=f"Current confidence {geo_data.confidence:.0%} is below 70% threshold",
                estimated_cost=estimate_survey_cost(site.area_km2),
                expected_value_of_information=self.voi.calculate(geo_data)
            ))
        
        # Financial recommendations
        if market.price_trend == "BULLISH" and geo_data.grade > site.economic_cutoff:
            recommendations.append(Recommendation(
                type="ADVANCE",
                priority="HIGH",
                action="Proceed to preliminary economic assessment (PEA)",
                rationale=f"{site.primary_mineral} price up {market.price_change_6m}% in 6 months",
                estimated_cost=50000,  # USD for PEA
                expected_roi=self.financial.projected_roi(site, market)
            ))
        
        return sorted(recommendations, key=lambda r: r.priority_score, reverse=True)
```

### 8.2 Financial Modeling

**Built-in models:**
- **NPV (Net Present Value)** — Discounted cash flow for mining projects
- **IRR (Internal Rate of Return)** — Return on investment calculation
- **Payback Period** — Time to recover initial investment
- **Sensitivity Analysis** — How price, grade, recovery rate changes affect viability
- **Monte Carlo Simulation** — Probability distributions for all key variables

```python
# Financial model example
def project_economics(resource, capex, opex_per_tonne, commodity_price, discount_rate=0.10):
    annual_production = resource.tonnes / mine_life_years
    annual_revenue = annual_production * resource.grade * recovery_rate * commodity_price
    annual_cost = annual_production * opex_per_tonne
    annual_cashflow = annual_revenue - annual_cost
    
    npv = sum(cf / (1 + discount_rate)**t for t, cf in enumerate(cashflows))
    irr = calculate_irr(cashflows, initial_investment=capex)
    
    return {
        "npv_usd": npv,
        "irr_percent": irr,
        "payback_years": payback_period,
        "mine_life_years": mine_life_years,
        "all_in_sustaining_cost": aisc
    }
```

### 8.3 Regulatory Compliance Engine

Tracks and checks against Kenyan mining regulations:

- **Mining Act 2016** — License types, requirements, timelines
- **Environmental Management and Coordination Act (EMCA)** — EIA requirements
- **Community Land Act** — Community consent requirements
- **County government regulations** — Local permits and levies

---

## 9. User Interface Layer

### 9.1 Mobile App (React Native)

**Primary users:** Field geologists, small-scale miners, community members

**Screens:**
1. **Map View** — Interactive map with geological overlays, survey sites, mineral occurrences
2. **Collect** — Field data collection (photos, samples, observations)
3. **Results** — AI analysis results for their collected data
4. **Market** — Commodity prices and market news
5. **Learn** — Educational content on geology and mining

**Offline capabilities:**
- Map tiles cached locally
- Data collection works fully offline
- Sync queue processes when connectivity returns
- Basic mineral ID via on-device TFLite model

### 9.2 Web Dashboard (Next.js + React)

**Primary users:** Exploration managers, investors, government regulators

**Dashboards:**
1. **Portfolio Overview** — All exploration sites, status, key metrics
2. **Site Detail** — Full geological data, AI analysis, resource estimate
3. **Financial** — Project economics, investment tracking, ROI projections
4. **Compliance** — Permit status, environmental monitoring, reporting deadlines
5. **Market Intelligence** — Price trends, demand forecasts, competitor analysis
6. **Agent Activity** — What the AI agents are doing, their confidence levels

### 9.3 API Gateway

RESTful + GraphQL API for third-party integration:

```yaml
# Key API endpoints
POST   /api/v1/sites                    # Create exploration site
POST   /api/v1/sites/{id}/surveys       # Upload survey data
POST   /api/v1/sites/{id}/samples       # Log field samples
GET    /api/v1/sites/{id}/analysis      # Get AI analysis
GET    /api/v1/sites/{id}/estimate      # Get resource estimate
GET    /api/v1/sites/{id}/report        # Generate report
GET    /api/v1/market/{mineral}          # Market data
POST   /api/v1/agent/chat               # Chat with AI assistant
WebSocket /api/v1/agent/stream           # Real-time agent updates
```

### 9.4 Reporting Engine

Automated report generation:

- **Technical Reports** — JORC/NI 43-101 compliant, PDF output
- **Investor Decks** — PowerPoint with charts, maps, financial projections
- **Regulatory Filings** — Formatted for Kenyan Mining Cadastre submission
- **Community Reports** — Simple language summaries for local communities (English + Swahili)

---

## 10. NVIDIA Superagent Integration

### 10.1 NVIDIA Agent Toolkit Architecture

The platform integrates with NVIDIA's agent ecosystem at three levels:

```
┌──────────────────────────────────────────────────────┐
│           NVIDIA Agent Toolkit Integration            │
│                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │ Nemotron    │  │ NeMo Guard   │  │ NVIDIA NIM  │ │
│  │ Models      │  │ Rails        │  │ Inference   │ │
│  │ (LLM Core)  │  │ (Safety)     │  │ (Optimized) │ │
│  └──────┬──────┘  └──────┬───────┘  └──────┬──────┘ │
│         └────────────────┼─────────────────┘        │
│                          │                           │
│  ┌───────────────────────┴────────────────────────┐  │
│  │           LangGraph Orchestration              │  │
│  │  • State machine for agent workflows           │  │
│  │  • Conditional routing between agents          │  │
│  │  • Human-in-the-loop checkpoints              │  │
│  └───────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

### 10.2 Model Selection Strategy

| Task | Model | Why |
|------|-------|-----|
| Supervisor/Orchestrator | Nemotron 4 Ultra | Best reasoning, instruction following |
| Geological Analysis | Llama 3.1 70B (custom fine-tune) | Need domain-specific fine-tuning |
| Data Processing | Mistral 7B | Fast, good at structured extraction |
| Market Analysis | Nemotron 4 Mini | Fast inference, good at numbers |
| Report Writing | Nemotron 4 Ultra | Best at long-form generation |
| Safety/Guardrails | NeMo Guard Rails | Prevents hallucination in financial estimates |

### 10.3 NeMo Guard Rails Integration

Critical for mining — wrong estimates can cost millions:

```python
from nemoguardrails import RailsConfig, LLMRails

config = RailsConfig.from_path("./guardrails_config")
rails = LLMRails(config)

# Guardrails enforce:
# 1. No specific investment advice without disclaimers
# 2. Resource estimates always include confidence intervals
# 3. Financial projections always include risk factors
# 4. No geological claims without citing data sources
# 5. Mandatory uncertainty communication for AI estimates

# Example guardrail action
@rails.action
def validate_resource_estimate(context):
    estimate = context.last_bot_message
    if "confidence" not in estimate.lower():
        return "I need to add: This estimate has significant uncertainty. " \
               "It should not be used for investment decisions without " \
               "independent geological verification."
    return estimate
```

### 10.4 LangChain / LangGraph Integration

```python
from langgraph.graph import StateGraph, END
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage

# Define the agent workflow as a state machine
workflow = StateGraph(ExplorerState)

# Add agent nodes
workflow.add_node("supervisor", supervisor_agent)
workflow.add_node("geologist", geology_agent)
workflow.add_node("data_processor", data_agent)
workflow.add_node("market_analyst", market_agent)
workflow.add_node("risk_assessor", risk_agent)
workflow.add_node("reporter", report_agent)

# Define routing logic
workflow.add_conditional_edges(
    "supervisor",
    route_to_agent,  # Function that decides which agent to call next
    {
        "geology": "geologist",
        "data": "data_processor",
        "market": "market_analyst",
        "risk": "risk_assessor",
        "report": "reporter",
        "done": END
    }
)

# All agents report back to supervisor
for agent in ["geologist", "data_processor", "market_analyst", "risk_assessor", "reporter"]:
    workflow.add_edge(agent, "supervisor")

workflow.set_entry_point("supervisor")
app = workflow.compile()

# Run
result = await app.ainvoke({
    "messages": [HumanMessage(content="Analyze the Kwale titanium deposit")],
    "site_id": "kwale-001",
    "context": {}
})
```

---

## 11. Flywheel Architecture — Self-Improving System

### 11.1 The Data Flywheel

```
More Users → More Field Data → Better AI Models → Better Results
    ↑                                                    │
    └────────────────── More Users ←─────────────────────┘
```

### 11.2 Flywheel Mechanisms

**1. Every survey improves the geological model:**
```
New drone survey → Processed by GeoVision → Compared to known deposits
→ Model accuracy measured → Retraining data added → Model improves
→ Next survey gets better interpretation automatically
```

**2. User corrections become training data:**
```
AI: "This appears to be granite"
Geologist: "No, this is gneiss — see the banding"
→ Correction logged → Added to training set → Model learns
→ Fewer granite/gneiss misclassifications going forward
```

**3. Exploration success validates predictions:**
```
AI predicted: "70% chance of gold mineralization at Site X"
Drilling confirmed: Gold deposit found
→ Prediction-outcome pair logged → Calibration improves
→ Future predictions are better calibrated
```

**4. Market feedback improves financial models:**
```
AI predicted: "NPV of $5M for this deposit"
Actual: Project achieved $4.2M NPV
→ Error logged → Financial model adjusted
→ Next estimate is more accurate
```

### 11.3 Flywheel Data Pipeline

```python
class FlywheelPipeline:
    """Captures every interaction for continuous improvement."""
    
    def log_prediction(self, prediction, actual_outcome=None):
        """Log prediction and later compare to actual outcome."""
        self.db.insert("predictions", {
            "model_version": prediction.model_version,
            "input_features": prediction.features,
            "prediction": prediction.value,
            "confidence": prediction.confidence,
            "actual": actual_outcome,  # Filled in later
            "error": actual_outcome - prediction.value if actual_outcome else None
        })
    
    def log_user_feedback(self, feedback):
        """Capture corrections and validations from users."""
        self.db.insert("feedback", {
            "prediction_id": feedback.prediction_id,
            "user_id": feedback.user_id,
            "correction": feedback.correction,
            "expertise_level": feedback.user_expertise,
            "timestamp": datetime.utcnow()
        })
    
    def retrain_trigger(self):
        """Check if model should be retrained."""
        recent_accuracy = self.calculate_recent_accuracy(window_days=30)
        if recent_accuracy < self.threshold:
            self.trigger_retraining()
    
    def calculate_model_calibration(self):
        """Are 70% confidence predictions correct 70% of the time?"""
        predictions = self.db.query("predictions WHERE actual IS NOT NULL")
        return calibration_score(predictions)
```

### 11.4 Flywheel Metrics Dashboard

Track the flywheel's effectiveness:

- **Data growth rate** — New samples/surveys per week
- **Model accuracy trend** — RMSE, MAE over time
- **Prediction calibration** — Confidence vs actual accuracy
- **User correction rate** — How often users correct AI (should decrease)
- **Coverage expansion** — Geographic area with AI analysis
- **Time-to-insight** — How fast new data produces actionable insights

---

## 12. MVP & Phased Rollout

### 12.1 MVP Definition (Phase 0 — Weeks 1-4)

**Goal:** Prove the concept works with minimal infrastructure.

**Must have:**
1. ✅ Smartphone app for field data collection (photos + GPS + description)
2. ✅ Basic AI mineral identification from photos (on-device TFLite model)
3. ✅ Cloud storage and simple web dashboard to view collected data
4. ✅ Integration with one geological database (KGS open data)
5. ✅ Basic commodity price display

**Must NOT have (yet):**
- ❌ Drone integration (too expensive for MVP)
- ❌ Multi-agent system (overkill for MVP)
- ❌ Quantum computing (no value yet)
- ❌ Financial modeling (need data first)

**MVP Tech Stack:**
```
Mobile: React Native + Expo
Backend: FastAPI (Python) + PostgreSQL + PostGIS
Cloud: AWS (S3 + EC2 + RDS)
AI: TFLite on-device + HuggingFace Inference API
Maps: Mapbox GL JS
Auth: Firebase Auth (easy, free tier)
```

**MVP Budget:** ~$2,000/month (cloud) + development time

### 12.2 Phase 1: Foundation (Weeks 1-4)

| Week | Deliverable | Details |
|------|------------|---------|
| 1 | Project setup, DB schema, API scaffold | FastAPI + PostGIS + S3 |
| 2 | Mobile app — data collection | Photo, GPS, sample logging |
| 3 | AI model — basic mineral ID | Train on mineral photo dataset |
| 4 | Web dashboard — view data | Map + data table + basic analysis |

**Phase 1 Team:** 2 developers, 1 geologist (part-time)

### 12.3 Phase 2: AI Analysis (Months 2-3)

| Deliverable | Timeline | Dependencies |
|-------------|----------|-------------|
| Drone data ingestion pipeline | Month 2 | Drone hardware acquired |
| GeoVision model v1 | Month 2 | Training data from Phase 1 |
| Spectral analysis pipeline | Month 2 | Hyperspectral data |
| Resource estimation engine v1 | Month 3 | GeoVision + GeoChem models |
| Basic report generation | Month 3 | Templates + data |
| Market data integration | Month 2 | API subscriptions |
| User authentication + roles | Month 2 | — |

**Phase 2 Team:** 3 developers, 1 ML engineer, 1 geologist, 1 data scientist

### 12.4 Phase 3: Multi-Agent Platform (Months 4-6)

| Deliverable | Timeline | Dependencies |
|-------------|----------|-------------|
| Supervisor Agent + LangGraph | Month 4 | NVIDIA API access |
| Geological Analysis Agent | Month 4 | GeoVision + knowledge base |
| Market Intelligence Agent | Month 4 | Market data pipeline |
| Risk Assessment Agent | Month 5 | All prior models |
| Report Generation Agent | Month 5 | Templates + agents |
| Financial modeling engine | Month 5 | Market data + resource estimates |
| Full mobile app with AR | Month 6 | On-device models |
| API for third-party integration | Month 6 | Full platform |

**Phase 3 Team:** 5 developers, 2 ML engineers, 1 geologist, 1 data scientist, 1 DevOps

### 12.5 Phase 4: Scale (Months 7-12)

- Quantum computing integration for complex optimization
- Multi-country expansion (Tanzania, Uganda, Ethiopia)
- Enterprise features (multi-tenant, SSO, audit logs)
- Marketplace for connecting miners with investors
- Community features (local community engagement)

---

## 13. Technology Stack

### 13.1 Complete Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend — Mobile** | React Native + Expo | Cross-platform mobile app |
| **Frontend — Web** | Next.js 14 + React | Dashboard, admin panel |
| **Frontend — Maps** | Mapbox GL JS + deck.gl | Geospatial visualization |
| **Backend — API** | FastAPI (Python 3.12) | REST API server |
| **Backend — GraphQL** | Strawberry (Python) | Complex data queries |
| **Database — Primary** | PostgreSQL 16 + PostGIS | Geospatial data storage |
| **Database — Vector** | pgvector | Embeddings for RAG |
| **Database — Cache** | Redis 7 | Agent messages, sessions |
| **Database — Time Series** | TimescaleDB | Sensor data, market prices |
| **Object Storage** | AWS S3 | Drone imagery, reports, models |
| **ML Framework** | PyTorch 2.x | Model training |
| **ML Serving** | NVIDIA NIM + Triton | Model inference |
| **ML Experiment** | MLflow | Experiment tracking |
| **ML Pipeline** | Apache Airflow | Data pipeline orchestration |
| **Agent Framework** | LangChain + LangGraph | Multi-agent orchestration |
| **Agent LLM** | NVIDIA NIM (Nemotron, Llama, Mistral) | LLM inference |
| **Agent Safety** | NeMo Guard Rails | Output validation |
| **Vector DB** | pgvector / Qdrant | Semantic search |
| **IoT** | MQTT + LoRaWAN | Sensor data transmission |
| **Edge** | NVIDIA Jetson Orin | Edge inference |
| **Container** | Docker + Kubernetes (EKS) | Deployment |
| **CI/CD** | GitHub Actions | Automated testing/deployment |
| **Monitoring** | Grafana + Prometheus | System monitoring |
| **Auth** | Keycloak | Authentication, SSO |
| **Queue** | Redis Streams / Kafka | Async processing |
| **GIS** | QGIS Server / GeoServer | Map tile serving |

### 13.2 Python Dependencies (Core)

```txt
# requirements.txt — Core dependencies

# Web framework
fastapi==0.115.*
uvicorn[standard]==0.32.*
strawberry-graphql[fastapi]==0.252.*

# Database
sqlalchemy[asyncio]==2.0.*
asyncpg==0.30.*
alembic==1.14.*
psycopg2-binary==2.9.*
geoalchemy2==0.15.*

# AI/ML
torch==2.5.*
torchvision==0.20.*
transformers==4.47.*
huggingface-hub==0.27.*
scikit-learn==1.6.*
xgboost==2.1.*
numpy==2.2.*
pandas==2.2.*
scipy==1.15.*

# Geospatial
rasterio==1.4.*
geopandas==1.0.*
shapely==2.0.*
fiona==1.10.*
pyproj==3.7.*
opencv-python==4.10.*

# Agent framework
langchain==0.3.*
langchain-nvidia-ai-endpoints==0.3.*
langgraph==0.2.*
nemoguardrails==0.11.*

# Data processing
apache-airflow==2.10.*
great-expectations==0.18.*

# Cloud
boto3==1.35.*
aiobotocore==2.15.*

# Quantum
qiskit==1.3.*
dwave-ocean-sdk==8.0.*
amazon-braket-sdk==1.86.*

# Utilities
redis==5.2.*
celery==5.4.*
pydantic==2.10.*
python-dotenv==1.0.*
whisper==20231117  # Voice transcription
```

---

## 14. Quantum Computing Integration

### 14.1 Where Quantum Adds Value

Quantum computing is **not** a replacement for classical computing. It excels at specific optimization and simulation problems relevant to mining:

| Problem | Classical Approach | Quantum Approach | Expected Speedup |
|---------|-------------------|-----------------|-----------------|
| **Resource estimation** — Optimal drill hole placement | Monte Carlo (hours) | QAOA on D-Wave | 10-100x for large grids |
| **Supply chain optimization** — Route planning for equipment | Linear programming | Quantum annealing | 5-10x for complex routes |
| **Geophysical inversion** — Convert magnetic data to 3D model | Iterative least squares | Variational Quantum Eigensolver | Potential 100x for large models |
| **Portfolio optimization** — Which sites to explore | Mixed-integer programming | QAOA | 10x for large portfolios |
| **Molecular simulation** — Mineral processing chemistry | DFT calculations | Quantum simulation | Exponential for complex molecules |

### 14.2 Quantum API Integration

```python
# quantum_integration.py

import asyncio
from qiskit import QuantumCircuit
from qiskit_ibm_runtime import QiskitRuntimeService, Sampler
from dwave.system import DWaveSampler, EmbeddingComposite
import amazon_braket.sdk as braket

class QuantumMineralOptimizer:
    """Quantum-enhanced optimization for mineral exploration."""
    
    def __init__(self):
        # Initialize quantum backends
        self.ibm_service = QiskitRuntimeService(channel="ibm_cloud")
        self.dwave_sampler = DWaveSampler()
        self.braket_device = braket.AwsDevice("arn:aws:braket:::device/qpu/d-wave")
    
    async def optimize_drill_holes(
        self, 
        grid_points: list, 
        budget: int, 
        uncertainty_map: dict
    ) -> list:
        """
        Find optimal drill hole locations to maximize information gain.
        Uses QAOA (Quantum Approximate Optimization Algorithm).
        """
        n_points = len(grid_points)
        
        # Build QUBO (Quadratic Unconstrained Binary Optimization) matrix
        # Minimize: -information_gain + constraint_penalty
        Q = self._build_qubo(grid_points, budget, uncertainty_map)
        
        # Solve on D-Wave quantum annealer
        response = await asyncio.to_thread(
            EmbeddingComposite(self.dwave_sampler).sample,
            Q,
            num_reads=1000
        )
        
        # Extract solution
        selected_holes = [
            grid_points[i] for i, bit in enumerate(response.first.sample.values())
            if bit == 1
        ]
        
        return selected_holes
    
    async def geophysical_inversion(
        self,
        magnetic_data: 'np.ndarray',
        model_grid: 'np.ndarray'
    ) -> 'np.ndarray':
        """
        Convert surface magnetic measurements to 3D subsurface model.
        Uses Variational Quantum Eigensolver (VQE) approach.
        """
        # Encode inversion problem as Hamiltonian
        hamiltonian = self._encode_inversion_hamiltonian(magnetic_data, model_grid)
        
        # Create variational circuit
        n_qubits = min(20, len(model_grid))  # Limit qubits for NISQ devices
        circuit = QuantumCircuit(n_qubits)
        # ... parameterized quantum circuit
        
        # Run on IBM Quantum
        backend = self.ibm_service.least_busy(simulator=False)
        sampler = Sampler(backend)
        
        # Optimization loop
        result = self._vqe_optimize(circuit, hamiltonian, sampler)
        
        return self._decode_to_3d_model(result)
    
    async def portfolio_optimization(
        self,
        sites: list,
        constraints: dict
    ) -> dict:
        """
        Optimize exploration portfolio: which sites to explore, in what order.
        Uses quantum annealing for combinatorial optimization.
        """
        # Build optimization problem
        Q = self._build_portfolio_qubo(sites, constraints)
        
        # Solve on D-Wave
        response = await asyncio.to_thread(
            EmbeddingComposite(self.dwave_sampler).sample,
            Q,
            num_reads=500
        )
        
        return self._decode_portfolio(response.first.sample, sites)

    # --- Amazon Braket integration for hybrid quantum-classical ---
    
    async def hybrid_optimization(self, problem_data: dict) -> dict:
        """
        Use Amazon Braket for hybrid quantum-classical optimization.
        Falls back to classical if quantum unavailable.
        """
        try:
            device = braket.AwsDevice("arn:aws:braket:::device/qpu/d-wave/Advantage_system6")
            
            # Build and submit quantum task
            task = device.run(
                self._create_braket_circuit(problem_data),
                shots=1000
            )
            
            result = task.result()
            return self._parse_braket_result(result)
            
        except Exception as e:
            # Fallback to classical
            logger.warning(f"Quantum unavailable, falling back to classical: {e}")
            return self._classical_fallback(problem_data)
```

### 14.3 Quantum Integration Architecture

```
┌─────────────────────────────────────────────────────┐
│                Quantum Service Layer                 │
│                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ Problem     │  │ Quantum      │  │ Result    │ │
│  │ Encoder     │→ │ Router       │→ │ Decoder   │ │
│  │ (Classical) │  │              │  │ (Classical│ │
│  └─────────────┘  └──────┬───────┘  └───────────┘ │
│                          │                          │
│         ┌────────────────┼────────────────┐         │
│         │                │                │         │
│  ┌──────┴──────┐  ┌─────┴──────┐  ┌─────┴──────┐  │
│  │ IBM Quantum │  │ D-Wave     │  │ Amazon     │  │
│  │ (Gate-based)│  │ (Annealing)│  │ Braket     │  │
│  │ Qiskit      │  │ Ocean      │  │ (Hybrid)   │  │
│  └─────────────┘  └────────────┘  └────────────┘  │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │ Classical Fallback (always available)        │   │
│  │ • Simulated annealing                        │   │
│  │ • Genetic algorithms                         │   │
│  │ • Gradient descent                           │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**Key principle:** Quantum is always optional. Every quantum algorithm has a classical fallback. The system degrades gracefully.

### 14.4 Quantum Cost Management

| Provider | Pricing Model | Typical Cost per Problem |
|----------|--------------|-------------------------|
| IBM Quantum | Per second of QPU time | $1-5 per optimization |
| D-Wave Leap | Per problem (minor-charge) | $0.00019 per minor embedding |
| Amazon Braket | Per shot + per task | $0.003 per shot (D-Wave) |

**Strategy:** Use quantum only for problems where it provides measurable advantage. Most optimization problems can start classical and upgrade to quantum as scale demands.

---

## 15. Security, Privacy & IP Protection

### 15.1 Data Classification

| Classification | Examples | Handling |
|---------------|---------|----------|
| **PUBLIC** | Published geological maps, market prices | No restrictions |
| **INTERNAL** | Survey data, AI analysis results | Encrypted at rest, role-based access |
| **CONFIDENTIAL** | Resource estimates, financial models | Encryption + audit log + IP restriction |
| **RESTRICTED** | Drill results before publication, M&A data | Encryption + MFA + legal NDA + air-gapped option |

### 15.2 Security Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Security Layers                    │
│                                                      │
│  Layer 1: Network                                    │
│  • AWS VPC with private subnets                      │
│  • WAF (Web Application Firewall)                    │
│  • DDoS protection (AWS Shield)                      │
│  • VPN for admin access                              │
│                                                      │
│  Layer 2: Authentication & Authorization             │
│  • Keycloak for SSO                                  │
│  • OAuth 2.0 + OpenID Connect                        │
│  • RBAC (Role-Based Access Control)                  │
│  • MFA for sensitive operations                      │
│                                                      │
│  Layer 3: Data Protection                            │
│  • AES-256 encryption at rest (S3, RDS)              │
│  • TLS 1.3 in transit                                │
│  • Field-level encryption for sensitive data         │
│  • Key management via AWS KMS                        │
│                                                      │
│  Layer 4: Application Security                       │
│  • Input validation (Pydantic)                       │
│  • SQL injection prevention (SQLAlchemy ORM)         │
│  • Rate limiting (FastAPI middleware)                 │
│  • CORS configuration                                │
│                                                      │
│  Layer 5: Monitoring & Audit                         │
│  • CloudTrail for API audit logging                  │
│  • GuardDuty for threat detection                    │
│  • Custom audit log for data access                  │
│  • Alerting via PagerDuty/SNS                        │
└──────────────────────────────────────────────────────┘
```

### 15.3 IP Protection Strategy

**What's proprietary:**
- Fine-tuned AI models (trained on proprietary field data)
- Geological knowledge base (curated from public + proprietary sources)
- Resource estimation algorithms and calibration
- Customer data and exploration results

**What's protected:**
- Model weights stored in encrypted S3 with access logging
- Training data versioned and access-controlled
- API keys rotated every 90 days
- Code repositories on private GitHub with branch protection

**Data sovereignty:**
- All data stored in AWS Africa (Cape Town) — data never leaves African region
- Compliant with Kenya Data Protection Act 2019
- GDPR-compliant for European investors/users

### 15.5 Agent Security

AI agents introduce unique security risks:

| Risk | Mitigation |
|------|-----------|
| **Prompt injection** | NeMo Guard Rails input filtering |
| **Data exfiltration via agent** | Agents have scoped permissions (principle of least privilege) |
| **Hallucinated financial advice** | Guard Rails enforce disclaimers and uncertainty |
| **Agent impersonation** | All agent messages signed and verified |
| **Unbounded computation** | Agent execution time limits, cost budgets |

---

## 16. Open-Source vs Proprietary Strategy

### 16.1 Recommended Split

| Component | License | Rationale |
|-----------|---------|-----------|
| **Mobile App (field collection)** | MIT | Encourage adoption, community contributions |
| **Data Collection SDK** | MIT | Lower barrier for field teams |
| **Geological Database Schema** | Apache 2.0 | Standard schema benefits ecosystem |
| **Basic AI Models (mineral ID)** | Apache 2.0 | Drive adoption, showcase capability |
| **Agent Framework (orchestration)** | Apache 2.0 | Community contributions, transparency |
| **Core Resource Estimation Engine** | Proprietary (BSL) | Core competitive advantage |
| **Financial Modeling Engine** | Proprietary | High value, protect IP |
| **Fine-tuned Domain Models** | Proprietary | Trained on proprietary data |
| **Customer Data & Analytics** | Proprietary | Never shared |
| **Quantum Optimization Algorithms** | Proprietary (patent pending) | Novel IP |

### 16.2 Open-Source Community Strategy

**GitHub organization:** `panga-ai`

**Repositories:**
1. `panga-ai/mobile-app` — React Native field app (MIT)
2. `panga-ai/data-sdk` — Data collection and processing SDK (Apache 2.0)
3. `panga-ai/geo-models` — Pre-trained geological AI models (Apache 2.0)
4. `panga-ai/agent-framework` — Multi-agent orchestration (Apache 2.0)
5. `panga-ai/geo-schema` — Database schema and migrations (Apache 2.0)

**Why open-source parts of it:**
1. **Adoption** — Lower barrier for small-scale miners and NGOs
2. **Trust** — Open algorithms build trust in estimates
3. **Talent** — Attract developers who want to work on impactful projects
4. **Data** — Community contributions improve models (flywheel)
5. **Government** — Open tools easier to get regulatory approval

**Why keep core proprietary:**
1. **Revenue** — Premium features fund the platform
2. **Investment** — Investors expect defensible IP
3. **Quality control** — Can't have unvetted code in financial estimates
4. **Liability** — Need to control what's labeled as "PangaAI estimate"

### 16.3 Revenue Model

| Tier | Price | Features |
|------|-------|----------|
| **Free** | $0 | Basic mineral ID, market prices, educational content |
| **Explorer** | $99/month | Full AI analysis, resource estimation, basic reports |
| **Enterprise** | $999/month | Multi-agent platform, financial modeling, priority support |
| **Custom** | Negotiable | White-label, custom models, on-premise deployment |

---

## 17. Cost Estimates & Infrastructure

### 17.1 Monthly Operating Costs by Phase

| Cost Category | MVP (Phase 0) | Phase 1-2 | Phase 3 |
|--------------|---------------|-----------|---------|
| AWS Infrastructure | $500 | $2,000 | $5,000 |
| NVIDIA NIM (inference) | $0 (free tier) | $500 | $2,000 |
| Satellite imagery | $0 (free Sentinel) | $500 | $1,000 |
| Domain data subscriptions | $100 | $500 | $1,000 |
| Quantum compute | $0 | $0 | $200 |
| Monitoring/logging | $50 | $100 | $300 |
| **Total** | **$650** | **$3,600** | **$9,500** |

### 17.2 Capital Costs (One-Time)

| Item | Cost (USD) |
|------|-----------|
| Drone + sensors (basic survey package) | $50,000 |
| Portable XRF rental (3 months) | $9,000 |
| Jetson Orin Nano edge devices (x3) | $3,000 |
| Initial data acquisition (satellite, geological) | $5,000 |
| Legal (IP, company formation) | $10,000 |
| **Total** | **$77,000** |

### 17.3 Team Structure (Phase 3)

| Role | Count | Location | Monthly Cost |
|------|-------|----------|-------------|
| CTO / Lead Architect | 1 | Nairobi | $6,000 |
| Senior ML Engineer | 2 | Remote/Nairobi | $4,000 each |
| Full-Stack Developer | 2 | Nairobi | $3,000 each |
| Geologist | 1 | Field/Nairobi | $3,500 |
| Data Scientist | 1 | Remote | $4,000 |
| DevOps Engineer | 1 | Remote | $3,500 |
| Product Manager | 1 | Nairobi | $3,500 |
| **Total (9 people)** | | | **$34,500/month** |

---

## Appendix A: Key Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Insufficient training data for Kenyan geology | High | Medium | Transfer learning from global models + partnership with KGS |
| Poor connectivity in field areas | Medium | High | Offline-first architecture, edge processing |
| Regulatory resistance to AI in mining | High | Low | Engage Ministry of Mining early, open-source approach |
| Commodity price crash | Medium | Medium | Diversified mineral coverage, financial hedging tools |
| Talent shortage (ML + geology) | Medium | High | Remote hiring, university partnerships (UoN, TUK) |
| Quantum compute not ready | Low | Medium | Classical fallbacks for all quantum algorithms |
| Data privacy breach | High | Low | Encryption, audit logs, compliance framework |

## Appendix B: Regulatory Framework (Kenya)

| Regulation | Relevance | Compliance Action |
|-----------|-----------|-------------------|
| Mining Act 2016 | License types, exploration rights | Regulatory compliance engine |
| Environmental Management Act | EIA requirements | Environmental monitoring module |
| Data Protection Act 2019 | Personal data handling | Encryption, consent, data minimization |
| Community Land Act | Community consent | Community engagement features |
| County Governments Act | Local permits and levies | County-specific compliance tracking |

## Appendix C: Competitive Landscape

| Competitor | Focus | Gap PangaAI Fills |
|-----------|-------|-------------------|
| **KoBold Metals** | AI exploration (cobalt, lithium) — Zambia, DRC | Not in Kenya; no mobile platform for small-scale |
| **Earth AI** | AI mineral exploration — Australia | No Africa presence; enterprise-only |
| **Goldspot (now DigiGeo)** | AI for gold exploration | Single-mineral focus; no multi-agent |
| **Seequent (Bentley)** | Geological modeling software | Desktop-only; no AI agents; expensive |
| **Micromine** | Mining software | Traditional; not AI-first |

**PangaAI's differentiation:**
1. Mobile-first (smartphones, not desktops)
2. Multi-agent AI (not single-model)
3. Built for East Africa (not adapted from Australia/Canada)
4. Accessible pricing (free tier exists)
5. Quantum-enhanced optimization
6. Community features for artisanal miners

---

*This architecture is designed to be built incrementally. Start with Phase 0 (MVP), prove value, then expand. Every component uses existing, production-ready technology. No vaporware. No "quantum will solve everything." Real tools, real constraints, real solutions.*

*The flywheel starts spinning from Day 1. Every photo collected, every sample logged, every correction made by a geologist makes the system smarter. That's the moat.*
