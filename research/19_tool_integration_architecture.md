# Team 19: Mining Super-Agent Tool Integration Architecture

> **Design Principle:** *"A super agent is a domain-specific agent connected to specialized tools."* — Jensen Huang, NVIDIA CEO

This document defines exactly how the Mining Super-Agent connects to, authenticates with, calls, and orchestrates **every tool** in its arsenal. Each tool specification includes: API endpoint, authentication, input/output formats, error handling, caching strategy, and performance characteristics.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Jensen's Tool Integration Vision — Applied to Mining](#2-jensens-tool-integration-vision--applied-to-mining)
3. [Tool Category 1: Geological Modeling](#3-tool-category-1-geological-modeling)
4. [Tool Category 2: Satellite & Remote Sensing](#4-tool-category-2-satellite--remote-sensing)
5. [Tool Category 3: Vision & AI](#5-tool-category-3-vision--ai)
6. [Tool Category 4: Quantum Computing](#6-tool-category-4-quantum-computing)
7. [Tool Category 5: Market & Financial Data](#7-tool-category-5-market--financial-data)
8. [Tool Category 6: Communication & Reporting](#8-tool-category-6-communication--reporting)
9. [Tool Category 7: Data Infrastructure](#9-tool-category-7-data-infrastructure)
10. [Tool Orchestration Engine](#10-tool-orchestration-engine)
11. [Authentication & Secrets Management](#11-authentication--secrets-management)
12. [Performance & Optimization](#12-performance--optimization)
13. [Error Handling & Fallback Matrix](#13-error-handling--fallback-matrix)
14. [Implementation Priority](#14-implementation-priority)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MINING SUPER-AGENT (DeerFlow 2.0)               │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ Planner  │  │ Executor │  │ Critic   │  │ Memory (Qdrant)  │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘   │
│       │              │              │                 │             │
│  ┌────┴──────────────┴──────────────┴─────────────────┴──────────┐  │
│  │                   TOOL REGISTRY & ROUTER                      │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐ │  │
│  │  │Geology  │ │Satellite│ │ Vision  │ │Quantum  │ │ Market │ │  │
│  │  │Adapter  │ │ Adapter │ │ Adapter │ │ Adapter │ │Adapter │ │  │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └───┬────┘ │  │
│  └───────┼──────────┼──────────┼──────────┼────────────┼───────┘  │
│          │          │          │          │            │           │
└──────────┼──────────┼──────────┼──────────┼────────────┼───────────┘
           │          │          │          │            │
    ┌──────┴──┐ ┌─────┴───┐ ┌───┴────┐ ┌───┴─────┐ ┌───┴──────┐
    │ GemPy   │ │ GEE     │ │ CLIP   │ │ CUDA-Q  │ │ yfinance │
    │ SimPEG  │ │Sentinel │ │ YOLOv8 │ │cuQuantum│ │ GoldAPI  │
    │ QGIS    │ │ Landsat │ │ OpenCV │ │PennyLane│ │AlphaVant.│
    │ Mindat  │ │ ASTER   │ │        │ │D-Wave   │ │          │
    └─────────┘ └─────────┘ └────────┘ └─────────┘ └──────────┘
```

### Core Design Principles

1. **Every tool is a Python class** implementing `ToolInterface` with `invoke()`, `validate()`, `health_check()`
2. **Tool Registry** — central catalog; agent discovers tools at runtime
3. **Adapter Pattern** — each tool wrapped in a uniform interface regardless of its native API
4. **Async-first** — all tool calls are async; parallel execution by default
5. **Fail gracefully** — every tool has fallback behavior defined

---

## 2. Jensen's Tool Integration Vision — Applied to Mining

| Jensen's Principle | Mining Implementation |
|---|---|
| *"Domain-specific agent"* | Mining geology, mineral exploration, resource estimation |
| *"Connected to specialized tools"* | 35+ tools across 7 categories |
| *"Harness wraps the model with planning, tool use, memory, routing, guardrails"* | DeerFlow 2.0 orchestrator with Planner → Executor → Critic loop |
| *"Access to design tools and programming tools"* | GemPy, QGIS, SimPEG for geological design |
| *"Access to certain parts of the network"* | Sentinel-2, Landsat, GEE for satellite data |
| *"Connect them to other agents"* | Sub-agents for satellite analysis, quantum optimization, market monitoring |

### Tool Connection Taxonomy

```
TOOLS
├── LOCAL LIBRARIES (pip install, run in-process)
│   ├── GemPy, SimPEG, Fatiando
│   ├── CLIP, YOLOv8, OpenCV
│   ├── CUDA-Q, cuQuantum, PennyLane
│   └── yfinance, pandas
│
├── CLOUD APIs (HTTP requests, API keys)
│   ├── Google Earth Engine
│   ├── Copernicus (Sentinel-2)
│   ├── USGS (Landsat, MRDS)
│   ├── GoldAPI, Alpha Vantage
│   └── Mindat.org
│
├── DATABASES (persistent connections)
│   ├── PostgreSQL + PostGIS
│   ├── Qdrant (vector store)
│   ├── Redis (cache)
│   └── MinIO (object storage)
│
└── APPLICATIONS (subprocess / IPC)
    ├── QGIS (headless via PyQGIS)
    └── Telegram Bot API (HTTP)
```

---

## 3. Tool Category 1: Geological Modeling

### 3.1 GemPy v3 — 3D Geological Modeling

**What it does:** Creates 3D structural geological models from sparse field data (boreholes, surface contacts, orientation measurements).

| Property | Detail |
|---|---|
| **Install** | `pip install gempy` |
| **Type** | Local Python library |
| **API** | Python classes: `gempy.create_geomodel()`, `gempy.compute_model()` |
| **Authentication** | None (open source) |
| **Version** | v3.x (latest: check PyPI) |

**Input Format:**
```python
import gempy as gp

# Define geo_model
geo_model = gp.create_geomodel(
    project_name='nyatike_gold',
    extent=[x_min, x_max, y_min, y_max, z_min, z_max],
    resolution=[50, 50, 50],
    structural_frame=structural_frame
)

# Add surface points (from field data / boreholes)
gp.add_surface_points(
    geo_model=geo_model,
    coord_x=..., coord_y=..., coord_z=...,
    surface_names=['granite', 'schist', 'quartz_vein']
)

# Add orientation measurements
gp.add_orientations(
    geo_model=geo_model,
    coord_x=..., coord_y=..., coord_z=...,
    pole_vector=(0, 0, 1),
    surface_names=['granite']
)

# Compute the model
gp.compute_model(geo_model)
```

**Output Format:**
```python
# Returns a Dataframe with:
# - Lithological block model (3D numpy array)
# - Surface meshes (vertices + faces for 3D visualization)
# - Geological cross-sections
# - Probability volumes (for stochastic models)

lith_block = geo_model.solutions.raw_arrays.lith_block  # shape: (n_cells,)
surface_mesh = gp.get_3D_interpolation(geo_model)  # vertices, simplices
```

**Error Handling:**
- `ConvergenceError` → reduce resolution, try different interpolation params
- `InputValidationError` → check coordinate ranges, surface name consistency
- `MemoryError` → reduce resolution from 100³ to 50³ or 25³

**Caching Strategy:**
- Cache computed models by `hash(extent + surface_points + orientations)`
- Store in MinIO as `.zip` (GemPy's native export format)
- TTL: 24 hours (recompute if input data changes)

**Performance:** 50³ grid = ~5 seconds. 100³ grid = ~30 seconds. 200³ = ~5 minutes.

---

### 3.2 SimPEG — Geophysical Inversion

**What it does:** Simulate and invert geophysical data (gravity, magnetics, EM, DC resistivity, IP).

| Property | Detail |
|---|---|
| **Install** | `pip install simpeg` |
| **Type** | Local Python library |
| **API** | Python classes per method: `simpeg.potential_fields.gravity`, `simpeg.potential_fields.magnetics` |
| **Authentication** | None (open source) |
| **Version** | 0.21.x+ |

**Input Format:**
```python
import simpeg
from simpeg import maps, data, data_misfit
from simpeg.potential_fields import gravity

# Define survey (receiver locations, source properties)
receivers = gravity.receivers.Point(receiver_locations)
survey = gravity.survey.Survey(source_field)

# Define mesh
mesh = discretize.TensorMesh([hx, hy, hz])

# Define forward simulation
simulation = gravity.simulation.Simulation3DIntegral(
    mesh=mesh,
    survey=survey,
    rhoMap=maps.IdentityMap(mesh)
)

# Run inversion
inv = inversion.BaseInversion(
    data_misfit=L2DataMisfit(simulation=simulation, data=observed_data),
    regularization= regularization.Tikhonov(mesh)
)
recovered_model = inv.run(initial_model)
```

**Output Format:**
```python
# recovered_model: numpy array of physical property values on mesh
# Each cell in the mesh has a value (density contrast for gravity,
# susceptibility for magnetics, conductivity for EM)
```

**Error Handling:**
- `SolverError` → increase regularization, try different solver (CG vs LU)
- Non-convergence → adjust beta cooling schedule
- Memory → use `simpeg.maps.SurjectFull` for parameter reduction

**Caching:** Cache inversion results by `hash(mesh + survey_data + regularization_params)`. TTL: 7 days.

**Performance:** Small survey (100 data points, 1000 cells) = ~30 seconds. Large survey (10k points, 100k cells) = ~30 minutes to hours.

---

### 3.3 Fatiando a Terra — Geophysical Processing

| Property | Detail |
|---|---|
| **Install** | `pip install fatiando` |
| **Type** | Local Python library |
| **Key modules** | `fatiando.gravmag`, `fatiando.gridder`, `fatiando.seismic` |
| **Authentication** | None (open source) |

**Key Operations:**
```python
from fatiando import gridder
from fatiando.gravmag import transform

# Upward continuation of gravity data
continued = transform.upcontinue(data, height_increase, shape)

# Reduction to the pole
rtp = transform.reduce_to_pole(data, shape, inc, dec)

# Derivative calculations
gz_deriv = transform.derivx(data, shape)
```

**Caching:** Grid processing results cached by `hash(input_grid + operation + params)`. TTL: 48 hours.

---

### 3.4 QGIS — GIS Analysis (Headless)

| Property | Detail |
|---|---|
| **Install** | System package: `apt install qgis python3-qgis` |
| **Type** | Desktop app with Python API (PyQGIS) |
| **API** | `qgis.core`, `qgis.analysis`, `processing` |
| **Authentication** | None (open source) |

**Headless Usage:**
```python
# Must initialize QGIS application first
from qgis.core import (
    QgsApplication, QgsVectorLayer, QgsRasterLayer,
    QgsProject, QgsProcessingFeedback
)

qgs = QgsApplication([], False)
qgs.initQgis()

# Load layers
vector_layer = QgsVectorLayer('/path/to/geology.shp', 'geology', 'ogr')
raster_layer = QgsRasterLayer('/path/to/dem.tif', 'dem', 'gdal')

# Run processing algorithms
import processing
result = processing.run('native:buffer', {
    'INPUT': vector_layer,
    'DISTANCE': 1000,
    'OUTPUT': 'memory:'
})
```

**Error Handling:**
- Layer load failure → check file path, format, CRS
- Processing algorithm error → check parameter types, try alternative algorithm

**Caching:** Pre-processed layers stored as GeoPackage in MinIO. TTL: 7 days.

---

### 3.5 Mindat.org — Mineral Database

| Property | Detail |
|---|---|
| **Endpoint** | `https://api.mindat.org/` |
| **Type** | REST API |
| **Authentication** | API key (free registration at mindat.org) |
| **Rate Limit** | 10 requests/second, 5000 requests/day (free tier) |

**API Calls:**
```python
import requests

MINDAT_API_KEY = os.environ['MINDAT_API_KEY']
headers = {'Authorization': f'Bearer {MINDAT_API_KEY}'}

# Search for minerals at a locality
response = requests.get(
    'https://api.mindat.org/v1/localities/',
    headers=headers,
    params={
        'lat': -1.05, 'lng': 34.5,
        'radius_km': 50,
        'format': 'json'
    }
)
# Returns: list of mineral localities with species, coordinates, references

# Get mineral properties
response = requests.get(
    'https://api.mindat.org/v1/minerals/gold',
    headers=headers
)
# Returns: hardness, crystal system, chemistry, occurrence data
```

**Output Format:** JSON with fields: `locality_name`, `latitude`, `longitude`, `minerals[]`, `rock_types[]`, `references[]`

**Error Handling:**
- `429 Too Many Requests` → exponential backoff (1s, 2s, 4s, max 30s)
- `401 Unauthorized` → refresh API key from env
- `404` → locality not in database, try broader search radius

**Caching:** Cache locality queries in Redis. Key: `mindat:locality:{lat}:{lng}:{radius}`. TTL: 7 days (data rarely changes).

---

### 3.6 USGS MRDS — Mineral Resource Data System

| Property | Detail |
|---|---|
| **Endpoint** | `https://mrdata.usgs.gov/mrds/` |
| **Type** | REST API + bulk download |
| **Authentication** | None (public data) |

**API Calls:**
```python
# Search by commodity and location
response = requests.get(
    'https://mrdata.usgs.gov/mrds/select/',
    params={
        'columns': 'commodity,latitude,longitude,site_name',
        'commodity': 'Gold',
        'lat': -1.05, 'lng': 34.5,
        'radius': 100,  # km
        'format': 'json'
    }
)

# Bulk download (shapefile)
# https://mrdata.usgs.gov/mrds/mrds.zip
```

**Caching:** Bulk data downloaded once, stored in PostgreSQL/PostGIS. Refresh monthly.

---

### 3.7 Kenya Geological Survey

| Property | Detail |
|---|---|
| **Access** | No public API available |
| **Data Sources** | Published geological maps (PDF/shapefile), KGS library, NEMA reports |
| **Strategy** | Web scraping of published reports + manual digitization of geological maps |

**Approach:**
1. Scrape `www.kgs.go.ke` for published geological maps and reports
2. Download PDF geological maps → extract spatial data using OCR + georeferencing
3. Store digitized data in PostGIS as `kgs_geology` table
4. Cross-reference with USGS MRDS and Mindat for validation

---

## 4. Tool Category 2: Satellite & Remote Sensing

### 4.1 Google Earth Engine (GEE)

| Property | Detail |
|---|---|
| **Endpoint** | `https://earthengine.googleapis.com/` |
| **Type** | Cloud platform (JavaScript/Python API) |
| **Install** | `pip install earthengine-api geemap` |
| **Authentication** | Google Cloud Service Account (JSON key) or OAuth2 |
| **Rate Limit** | Varies by operation; concurrent EE compute requests limited |

**Authentication:**
```python
import ee

# Option 1: Service Account (recommended for servers)
service_account = 'mining-agent@project.iam.gserviceaccount.com'
credentials = ee.ServiceAccountCredentials(
    service_account,
    key_file='/path/to/service-account-key.json'
)
ee.Initialize(credentials, project='mining-project-id')

# Option 2: OAuth2 (interactive)
ee.Authenticate()
ee.Initialize(project='mining-project-id')
```

**API Calls:**
```python
import ee

# Get Sentinel-2 imagery for Nyatike
point = ee.Geometry.Point([34.5, -1.05])
collection = (
    ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(point)
    .filterDate('2024-01-01', '2024-12-31')
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
    .sort('CLOUDY_PIXEL_PERCENTAGE')
)

# Get the least cloudy image
image = collection.first()

# Calculate NDVI
ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')

# Calculate mineral indices
# Ferrous iron ratio (SWIR/SWIR2)
ferrous = image.select('B11').divide(image.select('B12')).rename('ferrous_iron')

# Clay mineral index (SWIR1/NIR)
clay = image.select('B11').divide(image.select('B8')).rename('clay_index')

# Export to Google Drive or Cloud Storage
task = ee.batch.Export.image.toDrive(
    image=ndvi,
    description='nyatike_ndvi',
    scale=10,
    region=point.buffer(10000),
    fileFormat='GeoTIFF'
)
task.start()
```

**Output Format:** Raster images (GeoTIFF), feature collections (GeoJSON), or computed statistics (JSON)

**Error Handling:**
- `EEException: Computation timed out` → reduce region size or increase scale
- `EEException: User memory limit exceeded` → use `.clip()` before computation
- `403 Forbidden` → check service account permissions, project quota

**Caching:**
- Cache computed indices in MinIO as GeoTIFF
- Key: `gee:{collection}:{index}:{bounds}:{date_range}`
- TTL: 30 days (satellite data doesn't change for past dates)

**Performance:** Depends on region size and computation. Small AOI (10km²) = 10-30 seconds. Large export = minutes to hours.

---

### 4.2 Sentinel-2 via Copernicus Data Space

| Property | Detail |
|---|---|
| **Endpoint** | `https://catalogue.dataspace.copernicus.eu/odata/v1/` |
| **Type** | REST API (OData) |
| **Authentication** | Free registration at dataspace.copernicus.eu, OAuth2 token |
| **Rate Limit** | Generous; concurrent downloads limited |

**Authentication:**
```python
import requests

# Get OAuth2 token
token_response = requests.post(
    'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token',
    data={
        'client_id': 'cdse-public',
        'grant_type': 'password',
        'username': os.environ['COPERNICUS_USERNAME'],
        'password': os.environ['COPERNICUS_PASSWORD']
    }
)
access_token = token_response.json()['access_token']
```

**API Calls:**
```python
# Search for Sentinel-2 products
search_url = 'https://catalogue.dataspace.copernicus.eu/odata/v1/Products'
response = requests.get(search_url, params={
    '$filter': (
        "Collection/Name eq 'SENTINEL-2' and "
        "OData.CSC.Intersects(area=geography'SRID=4326;POINT(34.5 -1.05)') and "
        "ContentDate/Start gt 2024-01-01T00:00:00.000Z and "
        "ContentDate/Start lt 2024-12-31T00:00:00.000Z and "
        "Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.StringAttribute/Value lt '20')"
    ),
    '$top': 10
})

# Download product
product_id = response.json()['value'][0]['Id']
download_url = f'https://zipper.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value'
```

**Caching:** Store downloaded Sentinel-2 tiles in MinIO. Key: `sentinel2:{tile_id}:{date}`. TTL: permanent (historical data).

---

### 4.3 Landsat via USGS Earth Explorer

| Property | Detail |
|---|---|
| **Endpoint** | `https://m2m.cr.usgs.gov/api/api/json/stable/` |
| **Type** | REST API (Machine-to-Machine) |
| **Authentication** | USGS account (free registration) |

**API Calls:**
```python
# Login
login_response = requests.post(
    'https://m2m.cr.usgs.gov/api/api/json/stable/login',
    json={'username': USGS_USER, 'password': USGS_PASS}
)
api_key = login_response.json()['data']

# Search for Landsat 8/9
search_response = requests.post(
    'https://m2m.cr.usgs.gov/api/api/json/stable/scene-search',
    json={
        'datasetName': 'landsat_ot_c2_l2',
        'sceneFilter': {
            'spatialFilter': {
                'filterType': 'mbr',
                'lowerLeft': {'latitude': -1.5, 'longitude': 34.0},
                'upperRight': {'latitude': -0.5, 'longitude': 35.0}
            },
            'acquisitionFilter': {
                'start': '2024-01-01',
                'end': '2024-12-31'
            },
            'cloudCoverFilter': {'max': 20}
        }
    }
)
```

**Caching:** Store Landsat scenes in MinIO. Key: `landsat:{scene_id}`. TTL: permanent.

---

### 4.4 ASTER Mineral Indices

**What it does:** Calculate mineral alteration indices from ASTER SWIR/TIR bands.

**Calculation Method:**
```python
import numpy as np

def calc_aster_indices(band_data):
    """
    Calculate ASTER mineral indices.
    band_data: dict with keys 'B1'-'B9' as numpy arrays
    """
    # Clay minerals (Al-OH) = Band 5 / Band 6
    clay_index = band_data['B5'] / band_data['B6']

    # Ferrous iron = Band 5 / Band 4
    ferrous_iron = band_data['B5'] / band_data['B4']

    # Ferric iron = Band 4 / Band 3
    ferric_iron = band_data['B4'] / band_data['B3']

    # Silica index = Band 13 / Band 14
    silica_index = band_data['B13'] / band_data['B14']

    # Alunite/Kaolinite/Pyrophyllite = (Band 5 + Band 7) / Band 6
    akp_index = (band_data['B5'] + band_data['B7']) / band_data['B6']

    # Calcite/Dolomite = (Band 6 + Band 9) / (Band 7 + Band 8)
    calcite_index = (band_data['B6'] + band_data['B9']) / (band_data['B7'] + band_data['B8'])

    return {
        'clay': clay_index,
        'ferrous_iron': ferrous_iron,
        'ferric_iron': ferric_iron,
        'silica': silica_index,
        'akp': akp_index,
        'calcite': calcite_index
    }
```

**Data Source:** ASTER Global Emissivity Dataset (GED) available from NASA LP DAAC: `https://lpdaac.usgs.gov/products/astgtmv003/`

---

## 5. Tool Category 3: Vision & AI

### 5.1 CLIP — Zero-Shot Mineral Identification

| Property | Detail |
|---|---|
| **Install** | `pip install transformers torch Pillow` |
| **Model** | `openai/clip-vit-large-patch14` or `laion/CLIP-ViT-H-14-laion2B-s32B-b79K` |
| **Type** | Local model (HuggingFace Transformers) |
| **Authentication** | None (model weights are public) |
| **GPU** | Recommended (CUDA), works on CPU (slower) |

**Usage:**
```python
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import torch

model = CLIPModel.from_pretrained("openai/clip-vit-large-patch14")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-large-patch14")

def identify_mineral(image_path, candidate_minerals=None):
    """Zero-shot mineral identification from photo."""
    if candidate_minerals is None:
        candidate_minerals = [
            "gold ore", "quartz", "pyrite", "chalcopyrite",
            "galena", "magnetite", "hematite", "malachite",
            "azurite", "calcite", "feldspar", "mica",
            "granite rock", "basalt rock", "schist rock",
            "gneiss rock", "sandstone", "limestone"
        ]

    image = Image.open(image_path)
    text_inputs = [f"a photo of {m}" for m in candidate_minerals]

    inputs = processor(
        text=text_inputs,
        images=image,
        return_tensors="pt",
        padding=True
    )

    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits_per_image
        probs = logits.softmax(dim=-1)

    results = {
        mineral: prob.item()
        for mineral, prob in zip(candidate_minerals, probs[0])
    }
    return dict(sorted(results.items(), key=lambda x: -x[1]))
```

**Output Format:**
```python
{
    "gold ore": 0.45,
    "pyrite": 0.23,
    "chalcopyrite": 0.12,
    "quartz": 0.08,
    ...
}
```

**Error Handling:**
- `CUDA out of memory` → fall back to CPU, use smaller model
- Corrupt image → catch `PIL.UnidentifiedImageError`, return error

**Caching:** Cache results by `hash(image_file)`. Store in Redis. TTL: 7 days.

**Performance:** GPU: ~100ms per image. CPU: ~2 seconds per image.

---

### 5.2 YOLOv8 — Object Detection (Field Photos)

| Property | Detail |
|---|---|
| **Install** | `pip install ultralytics` |
| **Model** | `yolov8n.pt` (nano, fast) or `yolov8x.pt` (extra-large, accurate) |
| **Type** | Local model (Ultralytics) |
| **Authentication** | None |

**Usage:**
```python
from ultralytics import YOLO

model = YOLO('yolov8n.pt')  # or custom-trained model

def detect_rock_features(image_path):
    """Detect rock features, veins, structures in field photos."""
    results = model(image_path)

    detections = []
    for result in results:
        for box in result.boxes:
            detections.append({
                'class': result.names[int(box.cls)],
                'confidence': float(box.conf),
                'bbox': box.xyxy[0].tolist(),  # [x1, y1, x2, y2]
            })
    return detections
```

**Custom Training for Minerals:**
```python
# Train on mineral dataset
model = YOLO('yolov8n.pt')
model.train(
    data='mineral_dataset.yaml',  # dataset config
    epochs=100,
    imgsz=640,
    batch=16
)
```

**Caching:** Cache by `hash(image_file)`. TTL: 7 days.

**Performance:** Nano model: ~30ms per image (GPU), ~200ms (CPU).

---

### 5.3 Mineral Classification Models (HuggingFace)

**Pre-trained Models:**

| Model | HuggingFace ID | Purpose |
|---|---|---|
| Rock classifier | `D:/rock-classifier` (train custom) | Classify rock types |
| Mineral thin-section | Custom training needed | Thin-section analysis |
| Ore grade estimator | Custom training needed | Estimate grade from photos |

**Usage Pattern:**
```python
from transformers import pipeline

# Generic image classification
classifier = pipeline(
    "image-classification",
    model="custom-rock-classifier"
)

result = classifier("rock_sample.jpg")
# [{'label': 'granite', 'score': 0.92}, ...]
```

---

### 5.4 Image Preprocessing (OpenCV + Pillow)

| Property | Detail |
|---|---|
| **Install** | `pip install opencv-python Pillow numpy` |
| **Type** | Local libraries |

**Common Operations:**
```python
import cv2
import numpy as np

def preprocess_satellite_image(image_path):
    """Preprocess satellite imagery for analysis."""
    img = cv2.imread(image_path)

    # Resize to standard dimensions
    img = cv2.resize(img, (512, 512))

    # Normalize reflectance values
    img = img.astype(np.float32) / 255.0

    # Enhance contrast (CLAHE)
    lab = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lab[:,:,0] = clahe.apply(lab[:,:,0])
    enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    return enhanced

def extract_vein_features(image):
    """Extract quartz vein features from rock photo."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=50, maxLineGap=10)
    return lines
```

---

## 6. Tool Category 4: Quantum Computing

### 6.1 CUDA-Q — Hybrid Quantum-Classical

| Property | Detail |
|---|---|
| **Install** | `pip install cudaq` (v0.15.0+, Python ≥3.11) |
| **Type** | Local library (requires NVIDIA GPU with CUDA) |
| **Authentication** | None |
| **GPU** | Required (NVIDIA with CUDA 11 or 12) |

**Usage:**
```python
import cudaq

@cudaq.kernel
def quantum_mineral_kernel(n_qubits: int, params: list[float]):
    """Quantum kernel for mineral pattern recognition."""
    qubits = cudaq.qvector(n_qubits)

    # Create superposition
    h(qubits)

    # Parameterized rotations
    for i in range(n_qubits):
        ry(params[i], qubits[i])

    # Entanglement
    for i in range(n_qubits - 1):
        cx(qubits[i], qubits[i + 1])

    # Measurement
    mz(qubits)

# Execute
result = cudaq.sample(
    quantum_mineral_kernel,
    n_qubits=6,
    params=[0.5, 1.2, 0.8, 0.3, 1.5, 0.7],
    shots_count=1000
)
print(result)
```

**Error Handling:**
- `CUDA not available` → fall back to CPU simulator
- `Out of memory` → reduce qubit count

**Caching:** Cache circuit results by `hash(kernel + params + shots)`. TTL: 1 hour.

---

### 6.2 cuQuantum — GPU Quantum Simulation

| Property | Detail |
|---|---|
| **Install** | `pip install cuquantum` |
| **Type** | Local library (NVIDIA GPU) |
| **Authentication** | None |

**Usage:**
```python
from cuquantum import CircuitToEinsum, contract

# Convert quantum circuit to tensor network
# Useful for simulating larger circuits than CUDA-Q's default simulator
converter = CircuitToEinsum(circuit)
expression, operands = converter.state_vector()

# Contract using GPU-accelerated tensor network
result = contract(expression, operands)
```

**Caching:** Cache tensor contractions. TTL: 1 hour.

---

### 6.3 IBM Quantum — Cloud Quantum

| Property | Detail |
|---|---|
| **Install** | `pip install qiskit qiskit-ibm-runtime` |
| **Endpoint** | `https://auth.quantum-computing.ibm.com/api` |
| **Authentication** | IBM Quantum API token (free tier available) |
| **Rate Limit** | Free tier: limited queue priority, 10 minutes/month |

**Usage:**
```python
from qiskit_ibm_runtime import QiskitRuntimeService, Sampler, Estimator

# Connect to IBM Quantum
service = QiskitRuntimeService(
    channel='ibm_quantum',
    token=os.environ['IBM_QUANTUM_TOKEN']
)

# Get least busy backend
backend = service.least_busy(simulator=False, operational=True)

# Run circuit
sampler = Sampler(backend)
job = sampler.run(circuits, shots=1024)
result = job.result()
```

**Error Handling:**
- `IBMJobFailureError` → retry on different backend
- Queue timeout → switch to simulator
- `401` → refresh token

**Caching:** Cache by `hash(circuit + backend + shots)`. TTL: 1 hour.

---

### 6.4 D-Wave Leap — Quantum Annealing

| Property | Detail |
|---|---|
| **Install** | `pip install dwave-ocean-sdk` |
| **Endpoint** | `https://cloud.dwavesys.com/leap/` |
| **Authentication** | D-Wave API token (free tier: 1 min/month QPU time) |
| **Rate Limit** | Free tier: 1 minute QPU time per month |

**Usage:**
```python
from dwave.system import DWaveSampler, EmbeddingComposite
from dimod import BinaryQuadraticModel

# Define QUBO for mineral exploration optimization
# Example: optimal drilling locations
bqm = BinaryQuadraticModel('BINARY')

# Add variables for each candidate drill location
for i in range(n_locations):
    bqm.add_variable(i, -priority_scores[i])  # Linear bias

# Add interactions (locations too close together)
for i in range(n_locations):
    for j in range(i+1, n_locations):
        if distance[i][j] < min_drill_distance:
            bqm.add_interaction(i, j, 2.0)  # Penalty

# Solve on D-Wave QPU
sampler = EmbeddingComposite(DWaveSampler())
response = sampler.sample(bqm, num_reads=100)

# Best solution
best = response.first.sample
selected_locations = [i for i, v in best.items() if v == 1]
```

**Error Handling:**
- `SolverError` → fallback to simulated annealing (`dwave-neal`)
- QPU time exhausted → use `SimulatedAnnealingSampler`
- Embedding failure → reduce problem size

**Caching:** Cache by `hash(QUBO_matrix + num_reads)`. TTL: 1 hour.

---

### 6.5 PennyLane — Quantum ML

| Property | Detail |
|---|---|
| **Install** | `pip install pennylane` (v0.45+) |
| **Type** | Local library |
| **Authentication** | None |
| **Backends** | Default (NumPy), lightning.gpu (CUDA), or cloud backends |

**Usage:**
```python
import pennylane as qml
import numpy as np

dev = qml.device("default.qubit", wires=4)

@qml.qnode(dev)
def quantum_feature_map(features):
    """Encode geological features into quantum states."""
    # Angle encoding
    for i in range(4):
        qml.RY(features[i], wires=i)

    # Entangling layer
    qml.CNOT(wires=[0, 1])
    qml.CNOT(wires=[1, 2])
    qml.CNOT(wires=[2, 3])

    # Variational layer
    for i in range(4):
        qml.RZ(features[i] * 0.5, wires=i)

    return [qml.expval(qml.PauliZ(i)) for i in range(4)]

# Use for mineral prospectivity mapping
geological_features = np.array([0.3, 0.7, 0.2, 0.9])  # normalized features
result = quantum_feature_map(geological_features)
```

**Caching:** Cache by `hash(circuit + parameters)`. TTL: 1 hour.

---

## 7. Tool Category 5: Market & Financial Data

### 7.1 yfinance — Commodity Prices

| Property | Detail |
|---|---|
| **Install** | `pip install yfinance` (v1.5+) |
| **Type** | Local library (scrapes Yahoo Finance) |
| **Authentication** | None (free) |
| **Rate Limit** | Unofficial; ~2000 requests/hour recommended |

**Usage:**
```python
import yfinance as yf

def get_commodity_prices():
    """Get current prices for mining-relevant commodities."""
    tickers = {
        'GC=F': 'Gold (USD/oz)',
        'SI=F': 'Silver (USD/oz)',
        'HG=F': 'Copper (USD/lb)',
        'PL=F': 'Platinum (USD/oz)',
        'PA=F': 'Palladium (USD/oz)',
        'CL=F': 'Crude Oil (USD/bbl)',
    }

    prices = {}
    for ticker, name in tickers.items():
        data = yf.Ticker(ticker)
        hist = data.history(period='1d')
        if not hist.empty:
            prices[name] = {
                'price': float(hist['Close'].iloc[-1]),
                'change': float(hist['Close'].iloc[-1] - hist['Open'].iloc[0]),
                'change_pct': float((hist['Close'].iloc[-1] / hist['Open'].iloc[0] - 1) * 100)
            }
    return prices

def get_historical_prices(ticker='GC=F', period='5y'):
    """Get historical prices for financial modeling."""
    data = yf.Ticker(ticker)
    return data.history(period=period)
```

**Error Handling:**
- `YFRateLimitError` → exponential backoff
- `YFChartError` → try different period/format
- Empty data → ticker may be delisted, try alternative

**Caching:** Cache in Redis. Key: `yfinance:{ticker}:{period}`. TTL: 1 hour for current prices, 24 hours for historical.

---

### 7.2 Alpha Vantage — Market Data

| Property | Detail |
|---|---|
| **Endpoint** | `https://www.alphavantage.co/query` |
| **Type** | REST API |
| **Authentication** | API key (free: 25 requests/day, premium: 75+/min) |
| **Free Tier** | 25 requests/day |

**Usage:**
```python
import requests

API_KEY = os.environ['ALPHA_VANTAGE_KEY']

def get_commodity_price(commodity='WTI'):
    """Get commodity price from Alpha Vantage."""
    response = requests.get('https://www.alphavantage.co/query', params={
        'function': 'COMMODITY_PRICES',
        'commodity': commodity,  # WTI, BRENT, NATURAL_GAS, COPPER, etc.
        'apikey': API_KEY
    })
    return response.json()
```

**Caching:** Cache in Redis. Key: `av:{function}:{symbol}`. TTL: 1 hour.

---

### 7.3 GoldAPI.io — Gold Prices

| Property | Detail |
|---|---|
| **Endpoint** | `https://www.goldapi.io/api/` |
| **Type** | REST API |
| **Authentication** | API key in header (`x-access-token`) |
| **Free Tier** | 100 requests/month |

**Usage:**
```python
import requests

GOLDAPI_KEY = os.environ['GOLDAPI_KEY']

def get_gold_price(currency='USD'):
    """Get current gold price."""
    response = requests.get(
        f'https://www.goldapi.io/api/XAU/{currency}',
        headers={
            'x-access-token': GOLDAPI_KEY,
            'Content-Type': 'application/json'
        }
    )
    data = response.json()
    return {
        'price': data['price'],
        'price_gram_24k': data['price_gram_24k'],
        'price_gram_22k': data['price_gram_22k'],
        'timestamp': data['timestamp']
    }
```

**Caching:** Cache in Redis. Key: `goldapi:{currency}`. TTL: 10 minutes.

---

### 7.4 CoinGecko — Crypto Prices (if needed)

| Property | Detail |
|---|---|
| **Endpoint** | `https://api.coingecko.com/api/v3/` |
| **Type** | REST API |
| **Authentication** | None (free, no key needed) |
| **Rate Limit** | 10-30 requests/minute |

**Usage:**
```python
import requests

def get_crypto_price(coin_id='bitcoin'):
    response = requests.get(
        f'https://api.coingecko.com/api/v3/simple/price',
        params={'ids': coin_id, 'vs_currencies': 'usd'}
    )
    return response.json()
```

**Caching:** Redis. Key: `coingecko:{coin_id}`. TTL: 5 minutes.

---

## 8. Tool Category 6: Communication & Reporting

### 8.1 Telegram Bot API

| Property | Detail |
|---|---|
| **Endpoint** | `https://api.telegram.org/bot{TOKEN}/` |
| **Type** | REST API / Webhook |
| **Authentication** | Bot token (free, from @BotFather) |
| **Rate Limit** | 30 messages/second, 20 messages/minute per chat |

**Usage:**
```python
import requests

TELEGRAM_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
BASE_URL = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}'

def send_report(chat_id, report_text, document_path=None):
    """Send mining report to user via Telegram."""
    # Send text
    requests.post(f'{BASE_URL}/sendMessage', json={
        'chat_id': chat_id,
        'text': report_text,
        'parse_mode': 'Markdown'
    })

    # Send document (PDF report)
    if document_path:
        with open(document_path, 'rb') as f:
            requests.post(f'{BASE_URL}/sendDocument', data={
                'chat_id': chat_id,
                'caption': '📊 Mining Analysis Report'
            }, files={'document': f})

def send_map(chat_id, map_image_path):
    """Send map visualization."""
    with open(map_image_path, 'rb') as f:
        requests.post(f'{BASE_URL}/sendPhoto', data={
            'chat_id': chat_id,
            'caption': '🗺️ Geological Map'
        }, files={'photo': f})
```

**Error Handling:**
- `429 Too Many Requests` → respect `Retry-After` header
- `400 Bad Request` → check chat_id, message format
- Network error → retry 3 times with exponential backoff

---

### 8.2 DeerFlow 2.0 — Multi-Agent Orchestration

| Property | Detail |
|---|---|
| **Type** | Multi-agent framework (LangGraph-based) |
| **Install** | Clone from GitHub, `pip install -e .` |
| **Architecture** | Planner → Executor → Critic loop |

**Integration:**
```python
from deerflow.agent import DeerFlowAgent
from deerflow.tools import ToolRegistry

# Register tools
registry = ToolRegistry()
registry.register('gempy', GemPyTool())
registry.register('satellite', SatelliteTool())
registry.register('vision', VisionTool())
registry.register('quantum', QuantumTool())
registry.register('market', MarketTool())

# Create agent
agent = DeerFlowAgent(
    tools=registry,
    planner_model='gpt-4',
    executor_model='gpt-4',
    critic_model='gpt-4'
)

# Run task
result = agent.run(
    "Analyze the gold potential in Nyatike, Kenya. "
    "Use satellite imagery, geological data, and market prices."
)
```

---

### 8.3 Report Generation (PDF)

| Property | Detail |
|---|---|
| **Install** | `pip install reportlab matplotlib` |
| **Type** | Local library |

**Usage:** See skill `pdf-generator` for full reportlab integration.

---

## 9. Tool Category 7: Data Infrastructure

### 9.1 PostgreSQL + PostGIS

| Property | Detail |
|---|---|
| **Install** | `apt install postgresql postgis python3-psycopg2` |
| **Connection** | `postgresql://user:pass@host:5432/mining_db` |
| **Authentication** | Username/password |

**Schema:**
```sql
-- Core tables
CREATE TABLE geological_surveys (
    id SERIAL PRIMARY KEY,
    location GEOMETRY(Point, 4326),
    survey_date DATE,
    survey_type VARCHAR(50),
    data JSONB,
    source VARCHAR(100)
);

CREATE TABLE mineral_samples (
    id SERIAL PRIMARY KEY,
    location GEOMETRY(Point, 4326),
    mineral_type VARCHAR(100),
    grade FLOAT,
    confidence FLOAT,
    sample_date DATE,
    image_path VARCHAR(500)
);

CREATE TABLE satellite_analysis (
    id SERIAL PRIMARY KEY,
    area GEOMETRY(Polygon, 4326),
    analysis_date DATE,
    indices JSONB,  -- NDVI, clay, ferrous iron, etc.
    source VARCHAR(50),  -- 'sentinel2', 'landsat', 'aster'
    tile_id VARCHAR(100)
);

CREATE TABLE market_prices (
    id SERIAL PRIMARY KEY,
    commodity VARCHAR(50),
    price DECIMAL,
    currency VARCHAR(10),
    timestamp TIMESTAMPTZ,
    source VARCHAR(50)
);

-- Spatial indexes
CREATE INDEX idx_geological_location ON geological_surveys USING GIST(location);
CREATE INDEX idx_mineral_location ON mineral_samples USING GIST(location);
CREATE INDEX idx_satellite_area ON satellite_analysis USING GIST(area);
```

**Connection Pool:**
```python
from psycopg2 import pool

db_pool = pool.ThreadedConnectionPool(
    minconn=2, maxconn=20,
    dsn=os.environ['DATABASE_URL']
)
```

---

### 9.2 Qdrant — Vector Database

| Property | Detail |
|---|---|
| **Install** | `pip install qdrant-client` |
| **Endpoint** | `http://localhost:6333` (local) or `https://xxx.qdrant.io` (cloud) |
| **Authentication** | API key (for cloud) |

**Usage:**
```python
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

client = QdrantClient(url='http://localhost:6333')

# Create collection for mineral embeddings
client.create_collection(
    collection_name='mineral_embeddings',
    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
)

# Store mineral image embedding
client.upsert(
    collection_name='mineral_embeddings',
    points=[PointStruct(
        id=1,
        vector=embedding,  # 768-dim from CLIP
        payload={
            'mineral': 'gold',
            'location': {'lat': -1.05, 'lng': 34.5},
            'confidence': 0.95,
            'image_path': '/data/samples/gold_001.jpg'
        }
    )]
)

# Search for similar minerals
results = client.search(
    collection_name='mineral_embeddings',
    query_vector=new_image_embedding,
    limit=5
)
```

**Caching:** Qdrant IS the cache for embeddings. No additional caching needed.

---

### 9.3 MinIO — Object Storage

| Property | Detail |
|---|---|
| **Install** | `pip install minio` |
| **Endpoint** | `http://localhost:9000` (local) |
| **Authentication** | Access key + Secret key |

**Usage:**
```python
from minio import Minio

minio_client = Minio(
    'localhost:9000',
    access_key=os.environ['MINIO_ACCESS_KEY'],
    secret_key=os.environ['MINIO_SECRET_KEY'],
    secure=False
)

# Create buckets
for bucket in ['satellite-imagery', 'geological-models', 'reports', 'field-photos']:
    if not minio_client.bucket_exists(bucket):
        minio_client.make_bucket(bucket)

# Upload satellite tile
minio_client.fput_object(
    'satellite-imagery',
    'sentinel2/nyatike/2024-01-15/tile.tif',
    '/tmp/tile.tif'
)

# Upload GemPy model
minio_client.fput_object(
    'geological-models',
    'nyatike/gold_model_v1.zip',
    '/tmp/gold_model.zip'
)
```

---

### 9.4 Redis — Caching

| Property | Detail |
|---|---|
| **Install** | `pip install redis` |
| **Endpoint** | `redis://localhost:6379` |
| **Authentication** | Optional password |

**Usage:**
```python
import redis
import json

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def cache_set(key, value, ttl=3600):
    """Store value in cache with TTL."""
    r.setex(key, ttl, json.dumps(value))

def cache_get(key):
    """Retrieve value from cache."""
    val = r.get(key)
    return json.loads(val) if val else None
```

---

## 10. Tool Orchestration Engine

### How Multiple Tools Work Together

**Example: "Analyze gold potential in Nyatike"**

```
USER REQUEST: "Analyze gold potential in Nyatike, Kenya"

DEERFLOW PLANNER decomposes into:

Step 1: SATELLITE ANALYSIS (parallel)
├── Tool: Google Earth Engine
│   Input: {bounds: [34.0, -1.5, 35.0, -0.5], date_range: "2024-01-01:2024-12-31"}
│   Output: NDVI, clay index, ferrous iron index GeoTIFFs
│
├── Tool: Copernicus Sentinel-2
│   Input: Same bounds, low cloud cover
│   Output: Raw multispectral imagery
│
└── Tool: ASTER Mineral Indices
    Input: ASTER bands for region
    Output: Clay, iron, silica alteration maps

Step 2: GEOLOGICAL ANALYSIS (parallel with Step 1)
├── Tool: USGS MRDS
│   Input: {commodity: "Gold", bounds: Nyatike region}
│   Output: Known mineral occurrences, deposit types
│
├── Tool: Mindat.org
│   Input: {bounds: Nyatike, radius: 50km}
│   Output: Mineral localities, species reported
│
└── Tool: Kenya Geological Survey (cached data)
    Input: Nyatike quadrangle
    Output: Lithological map, structural features

Step 3: GEMOLOGICAL MODELING (depends on Step 2)
├── Tool: GemPy v3
│   Input: Surface points from geological survey, borehole data
│   Output: 3D geological model
│
└── Tool: SimPEG
    Input: Gravity/magnetic survey data
    Output: Subsurface density/susceptibility model

Step 4: VISION ANALYSIS (parallel with Steps 1-3)
├── Tool: CLIP
│   Input: Field photos from Nyatike
│   Output: Mineral identification (gold ore, pyrite, quartz, etc.)
│
└── Tool: YOLOv8
    Input: Field photos
    Output: Detected features (veins, alteration zones, structures)

Step 5: QUANTUM OPTIMIZATION (depends on Steps 1-4)
├── Tool: CUDA-Q
│   Input: Combined prospectivity layers
│   Output: Quantum-enhanced pattern recognition
│
└── Tool: D-Wave
    Input: QUBO for optimal drill locations
    Output: Selected drill locations

Step 6: MARKET ANALYSIS (parallel with everything)
├── Tool: yfinance
│   Input: GC=F (gold futures)
│   Output: Current gold price, 5-year history
│
└── Tool: GoldAPI
    Input: XAU/USD
    Output: Real-time gold price

Step 7: FINANCIAL MODELING (depends on Steps 5, 6)
├── Tool: NPV Calculator (internal)
│   Input: Resource estimate, gold price, CAPEX/OPEX
│   Output: NPV, IRR, payback period

Step 8: REPORT GENERATION (depends on all above)
├── Tool: ReportLab
│   Input: All analysis results
│   Output: PDF report with maps, charts, tables
│
└── Tool: Telegram Bot
    Input: PDF report
    Output: Sent to user
```

### Parallel Execution Engine

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class ToolOrchestrator:
    def __init__(self, tool_registry):
        self.registry = tool_registry
        self.executor = ThreadPoolExecutor(max_workers=8)

    async def execute_plan(self, plan):
        """Execute a plan with parallel steps."""
        results = {}

        for step_group in plan.steps:
            # Steps in same group run in parallel
            tasks = []
            for step in step_group:
                tool = self.registry.get(step.tool_name)
                task = asyncio.create_task(
                    self._run_tool(tool, step.input, results)
                )
                tasks.append((step.name, task))

            # Wait for all tasks in group
            for step_name, task in tasks:
                try:
                    results[step_name] = await asyncio.wait_for(task, timeout=step.timeout)
                except asyncio.TimeoutError:
                    results[step_name] = {'error': 'timeout', 'fallback': step.fallback}

        return results

    async def _run_tool(self, tool, input_data, context):
        """Run a single tool with error handling and caching."""
        cache_key = tool.compute_cache_key(input_data)

        # Check cache first
        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        # Run tool
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor, tool.invoke, input_data
            )
            await self.cache.set(cache_key, result, ttl=tool.cache_ttl)
            return result
        except Exception as e:
            if tool.fallback:
                return await tool.fallback(input_data, e)
            raise
```

---

## 11. Authentication & Secrets Management

### Tool Authentication Matrix

| Tool | Auth Method | Key/Token Required | Free Tier |
|---|---|---|---|
| **GemPy** | None | — | ✅ Fully free |
| **SimPEG** | None | — | ✅ Fully free |
| **Fatiando** | None | — | ✅ Fully free |
| **QGIS** | None | — | ✅ Fully free |
| **Mindat.org** | API Key | `MINDAT_API_KEY` | ✅ 5000 req/day |
| **USGS MRDS** | None | — | ✅ Public data |
| **Google Earth Engine** | Service Account | `GEE_SERVICE_ACCOUNT_JSON` | ✅ Free for research |
| **Copernicus** | OAuth2 | `COPERNICUS_USER`, `COPERNICUS_PASS` | ✅ Free |
| **USGS Landsat** | Account | `USGS_USER`, `USGS_PASS` | ✅ Free |
| **CLIP** | None | — | ✅ Open source |
| **YOLOv8** | None | — | ✅ Open source |
| **CUDA-Q** | None | — | ✅ Free (needs NVIDIA GPU) |
| **cuQuantum** | None | — | ✅ Free (needs NVIDIA GPU) |
| **IBM Quantum** | API Token | `IBM_QUANTUM_TOKEN` | ✅ 10 min/month |
| **D-Wave** | API Token | `DWAVE_API_TOKEN` | ✅ 1 min/month QPU |
| **PennyLane** | None | — | ✅ Fully free |
| **yfinance** | None | — | ✅ Fully free |
| **Alpha Vantage** | API Key | `ALPHA_VANTAGE_KEY` | ✅ 25 req/day |
| **GoldAPI** | API Key | `GOLDAPI_KEY` | ✅ 100 req/month |
| **CoinGecko** | None | — | ✅ 10-30 req/min |
| **Telegram Bot** | Bot Token | `TELEGRAM_BOT_TOKEN` | ✅ Fully free |
| **PostgreSQL** | User/Pass | `DATABASE_URL` | ✅ Self-hosted |
| **Qdrant** | API Key | `QDRANT_API_KEY` | ✅ Self-hosted / free cloud |
| **MinIO** | Access Key | `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` | ✅ Self-hosted |
| **Redis** | Password | `REDIS_PASSWORD` | ✅ Self-hosted |

### Secrets Management

```python
# Environment variables (primary method)
# Stored in .env file (never committed to git)

import os
from pathlib import Path

# Load .env file
def load_env():
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())

# Access pattern
MINDAT_KEY = os.environ.get('MINDAT_API_KEY', '')
GEE_SA = os.environ.get('GEE_SERVICE_ACCOUNT_JSON', '')
IBM_Q_TOKEN = os.environ.get('IBM_QUANTUM_TOKEN', '')
```

**`.env` template:**
```env
# Geological
MINDAT_API_KEY=

# Satellite
GEE_SERVICE_ACCOUNT_JSON=/path/to/service-account.json
COPERNICUS_USERNAME=
COPERNICUS_PASSWORD=
USGS_USER=
USGS_PASS=

# Quantum
IBM_QUANTUM_TOKEN=
DWAVE_API_TOKEN=

# Market
ALPHA_VANTAGE_KEY=
GOLDAPI_KEY=

# Communication
TELEGRAM_BOT_TOKEN=

# Database
DATABASE_URL=postgresql://mining:mining@localhost:5432/mining_db
REDIS_URL=redis://localhost:6379
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

---

## 12. Performance & Optimization

### Tool Performance Classification

| Speed Category | Tools | Response Time | Strategy |
|---|---|---|---|
| **Instant** (<100ms) | Redis cache hit, yfinance (cached), CoinGecko | <100ms | Always check cache first |
| **Fast** (100ms-5s) | CLIP (GPU), YOLOv8 (GPU), yfinance (live), GoldAPI | 100ms-5s | Run inline, no special handling |
| **Medium** (5s-60s) | GemPy (50³), SimPEG (small), GEE (small AOI), QGIS | 5s-60s | Background execution, progress callbacks |
| **Slow** (1-10min) | GemPy (100³), SimPEG (large), GEE (export), Sentinel download | 1-10min | Background task + polling |
| **Very Slow** (10min+) | Large inversions, full satellite tile downloads | 10min+ | Queue-based, notify on completion |

### Parallel Execution Strategy

```python
# Parallel tool execution plan for "Analyze gold in Nyatike"
PARALLEL_GROUPS = [
    # Group 1: All independent data gathering (parallel)
    [
        {"tool": "gee", "task": "ndvi_analysis"},
        {"tool": "copernicus", "task": "sentinel_download"},
        {"tool": "usgs_mrds", "task": "gold_occurrences"},
        {"tool": "mindat", "task": "mineral_localities"},
        {"tool": "yfinance", "task": "gold_price"},
        {"tool": "kgs_cache", "task": "geological_map"},
    ],
    # Group 2: Processing (depends on Group 1)
    [
        {"tool": "gempy", "task": "3d_model"},
        {"tool": "simpeg", "task": "gravity_inversion"},
        {"tool": "clip", "task": "mineral_id"},
        {"tool": "aster", "task": "alteration_indices"},
    ],
    # Group 3: Optimization (depends on Group 2)
    [
        {"tool": "cudaq", "task": "pattern_recognition"},
        {"tool": "dwave", "task": "drill_optimization"},
    ],
    # Group 4: Reporting (depends on all above)
    [
        {"tool": "reportlab", "task": "generate_pdf"},
    ],
]
```

### Caching Strategy Summary

| Data Type | Cache Store | TTL | Key Pattern |
|---|---|---|---|
| Current commodity prices | Redis | 5-10 min | `price:{commodity}:{currency}` |
| Historical prices | Redis | 24 hours | `hist:{ticker}:{period}` |
| Satellite indices | MinIO (GeoTIFF) | 30 days | `sat:{source}:{index}:{bounds}:{date}` |
| Geological models | MinIO (ZIP) | 7 days | `geo:{model}:{hash(inputs)}` |
| Vision results | Redis | 7 days | `vision:{tool}:{hash(image)}` |
| Quantum results | Redis | 1 hour | `quantum:{tool}:{hash(circuit)}` |
| API search results | Redis | 24 hours | `api:{source}:{hash(query)}` |
| GemPy computed models | PostgreSQL + MinIO | 7 days | `gempy:{hash(inputs)}` |

### Lazy Loading

```python
class LazyToolLoader:
    """Load heavy tools only when first needed."""

    def __init__(self):
        self._loaded = {}

    def get(self, tool_name):
        if tool_name not in self._loaded:
            self._loaded[tool_name] = self._load(tool_name)
        return self._loaded[tool_name]

    def _load(self, tool_name):
        loaders = {
            'gempy': lambda: __import__('gempy'),
            'simpeg': lambda: __import__('simpeg'),
            'clip': lambda: self._load_clip(),
            'yolo': lambda: self._load_yolo(),
            'cudaq': lambda: __import__('cudaq'),
        }
        return loaders[tool_name]()

    def _load_clip(self):
        from transformers import CLIPProcessor, CLIPModel
        model = CLIPModel.from_pretrained("openai/clip-vit-large-patch14")
        processor = CLIPProcessor.from_pretrained("openai/clip-vit-large-patch14")
        return {'model': model, 'processor': processor}
```

---

## 13. Error Handling & Fallback Matrix

| Tool | Primary Error | Fallback | Degraded Mode |
|---|---|---|---|
| **GemPy** | ConvergenceError | Reduce resolution | Use 2D cross-sections |
| **SimPEG** | SolverError | Increase regularization | Use forward modeling only |
| **Google Earth Engine** | Timeout/Quota | Use Copernicus direct | Use cached data |
| **Sentinel-2** | Download failure | Use Landsat | Use ASTER |
| **CLIP** | CUDA OOM | CPU inference | Use rule-based ID |
| **YOLOv8** | Model load fail | Use smaller model | Skip detection |
| **CUDA-Q** | No GPU | CPU simulator | Use classical ML |
| **D-Wave** | QPU time exhausted | Simulated annealing | Use classical optimizer |
| **IBM Quantum** | Queue timeout | Use local simulator | Skip quantum step |
| **yfinance** | Rate limit | Use Alpha Vantage | Use cached prices |
| **GoldAPI** | Monthly limit | Use yfinance | Use cached price |
| **Mindat** | 429 rate limit | Exponential backoff | Use USGS MRDS only |
| **PostgreSQL** | Connection fail | Reconnect pool | Use SQLite fallback |
| **Qdrant** | Connection fail | Reconnect | Use in-memory search |
| **Telegram** | 429 rate limit | Respect Retry-After | Queue messages |

### Error Handler Implementation

```python
class ToolErrorHandler:
    def __init__(self):
        self.retry_config = {
            'max_retries': 3,
            'base_delay': 1.0,
            'max_delay': 30.0,
            'exponential_base': 2
        }

    async def execute_with_retry(self, tool, input_data):
        last_error = None
        for attempt in range(self.retry_config['max_retries']):
            try:
                return await tool.invoke(input_data)
            except RateLimitError as e:
                delay = min(
                    self.retry_config['base_delay'] * (self.retry_config['exponential_base'] ** attempt),
                    self.retry_config['max_delay']
                )
                # Respect Retry-After header if present
                if hasattr(e, 'retry_after'):
                    delay = max(delay, e.retry_after)
                await asyncio.sleep(delay)
                last_error = e
            except ToolError as e:
                if tool.fallback:
                    return await tool.fallback(input_data, e)
                last_error = e
                break

        raise last_error
```

---

## 14. Implementation Priority

### Phase 1: Foundation (Week 1-2)
1. ✅ PostgreSQL + PostGIS setup
2. ✅ Redis cache
3. ✅ MinIO object storage
4. ✅ Tool Registry base class
5. ✅ Error handler

### Phase 2: Core Tools (Week 3-4)
1. ✅ yfinance (commodity prices) — instant value
2. ✅ CLIP (mineral identification) — wow factor
3. ✅ USGS MRDS (mineral data) — no auth needed
4. ✅ Mindat.org (mineral database)
5. ✅ Telegram Bot (communication)

### Phase 3: Advanced Tools (Week 5-8)
1. ✅ Google Earth Engine (satellite)
2. ✅ Copernicus Sentinel-2
3. ✅ GemPy (3D modeling)
4. ✅ ASTER mineral indices
5. ✅ QGIS (headless)

### Phase 4: Quantum & Optimization (Week 9-12)
1. ✅ CUDA-Q or PennyLane
2. ✅ D-Wave (if QPU time available)
3. ✅ IBM Quantum (backup)
4. ✅ SimPEG (geophysical inversion)

### Phase 5: Full Integration (Week 13-16)
1. ✅ DeerFlow 2.0 orchestration
2. ✅ Parallel execution engine
3. ✅ Full caching layer
4. ✅ All fallback paths tested
5. ✅ End-to-end workflow validation

---

## Summary

The Mining Super-Agent connects to **35+ tools** across 7 categories:

| Category | Tools | Auth Required | Free? |
|---|---|---|---|
| Geological | GemPy, SimPEG, Fatiando, QGIS, Mindat, USGS MRDS, KGS | Mindat only | ✅ All free |
| Satellite | GEE, Sentinel-2, Landsat, ASTER | GEE, Copernicus, USGS | ✅ All free |
| Vision/AI | CLIP, YOLOv8, OpenCV, HuggingFace | None | ✅ All free |
| Quantum | CUDA-Q, cuQuantum, IBM, D-Wave, PennyLane | IBM, D-Wave | ✅ Free tiers |
| Market | yfinance, Alpha Vantage, GoldAPI, CoinGecko | Alpha Vantage, GoldAPI | ✅ Free tiers |
| Communication | Telegram, DeerFlow 2.0, PDF reports | Telegram | ✅ All free |
| Data | PostgreSQL, Qdrant, MinIO, Redis | Self-hosted | ✅ All free |

**Total estimated monthly cost: $0** (all tools have free tiers sufficient for development and moderate usage).

Every tool is connected through a uniform `ToolInterface` with `invoke()`, `validate()`, `health_check()`, and `compute_cache_key()`. The DeerFlow 2.0 orchestrator handles planning, parallel execution, error recovery, and result aggregation. The result: a domain-specific super-agent that truly has access to specialized tools — exactly as Jensen Huang envisioned.
