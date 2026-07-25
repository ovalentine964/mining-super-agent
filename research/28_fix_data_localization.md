# Fix Data Quality & Localization Issues — Solutions Document

**Date:** 2026-07-25  
**Purpose:** Implementable solutions for all 5 critical issues found in architecture review  
**Status:** READY FOR IMPLEMENTATION

---

## Table of Contents

1. [Problem 1: Geological Database Is Hardcoded](#problem-1-geological-database-is-hardcoded)
2. [Problem 2: Luo (Dholuo) Translations Are Wrong](#problem-2-luo-dholuo-translations-are-wrong)
3. [Problem 3: No Error Handling for Real-World Conditions](#problem-3-no-error-handling-for-real-world-conditions)
4. [Problem 4: CLIP Cannot Distinguish Similar Minerals](#problem-4-clip-cannot-distinguish-similar-minerals)
5. [Problem 5: No Human-in-the-Loop for Critical Decisions](#problem-5-no-human-in-the-loop-for-critical-decisions)

---

## Problem 1: Geological Database Is Hardcoded

### Current State
A hardcoded Python dictionary with 4 regions. No spatial data, no real geology, no query capability.

### Solution: PostGIS Spatial Geological Database

#### 1.1 Data Sources — Where to Get Real Geological Data

| Source | URL | Coverage | Format | License | Priority |
|--------|-----|----------|--------|---------|----------|
| **OneGeology Portal** | onegeology.org (now closed, but data archived at BGS) | Global/Kenya | WMS/WFS, Shapefile | Open | HIGH |
| **BGS OpenGeoscience** | bgs.ac.uk/geological-data/opengeoscience/ | East Africa (colonial-era maps) | WMS, CSV, Shapefile | Open (CC-BY) | HIGH |
| **USGS Mineral Resources Data** | mrdata.usgs.gov | Global mineral occurrences | WFS, Shapefile, CSV | Public Domain | HIGH |
| **Mindat.org API** | api.mindat.org | Global mineral occurrences | JSON API | Non-commercial | MEDIUM |
| **Kenya Geological Survey** | minesandgeology.go.ke | Kenya 1:50,000 & 1:100,000 maps | Shapefile, GeoTIFF | Government (request) | HIGH |
| **USGS ASTER VNIR** | earthexplorer.usgs.gov | Global satellite geology | GeoTIFF | Public Domain | MEDIUM |
| **OpenStreetMap Geology** | overpass-api.de | Community-contributed | GeoJSON | ODbL | LOW |
| **Africa Mining Vision** | au.int | Pan-African geological data | Various | Open | LOW |

#### 1.2 Specific Data to Acquire

**From BGS (British Geological Survey):**
- Colonial-era geological maps of western Kenya (1:100,000 scale)
- BGS Open Report OR/20/010: "ASGM field work, Migori County" — contains geochemical data
- BGS Open Report OR/21/012: "Groundwater quality in Migori artisanal mining districts"
- BGS GeoIndex WFS: `https://map.bgs.ac.uk/arcgis/services/GeoIndex/IGS/MapServer/WMSServer`

**From USGS:**
- Mineral occurrences for Kenya: `https://mrdata.usgs.gov/minerals/` (use WFS endpoint)
- USGS SGMC (State Geologic Map Compilation) for context — though focused on US, methodology applies
- USGS EarthExplorer for ASTER mineral mapping data over Migori

**From Kenya Geological Survey:**
- 1:50,000 geological maps covering Nyatike, Rongo, and Migori County
- Mineral occurrence records and prospecting reports
- Borehole and geochemical databases
- **Action:** Formal data request letter to Director of Mines and Geology, Nairobi

**From Mindat.org:**
- API endpoint: `https://api.mindat.org/v1/`
- Endpoints: `/localities`, `/minerals`, `/geomod`
- Query: `?loc_type=county&country=kenya&state=migori`
- Returns: mineral occurrences with coordinates, descriptions, references
- Requires API key (free for non-commercial research)

**From Academic Literature (already in research/05_migori_geology.md):**
- Shackleton (1946): Geological map of Migori Gold Belt
- Ogola (1982-2002): Macalder deposit geology, mineral distribution
- BGS/University of Nairobi (2025): Neoarchean gold grain data

#### 1.3 PostGIS Database Schema

```sql
-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_raster;

-- ==========================================
-- CORE TABLES
-- ==========================================

-- Geological regions/units (polygons)
CREATE TABLE geological_units (
    id SERIAL PRIMARY KEY,
    unit_code VARCHAR(50) UNIQUE NOT NULL,
    unit_name VARCHAR(200) NOT NULL,
    era VARCHAR(50),           -- Archean, Proterozoic, Phanerozoic
    period VARCHAR(50),        -- Neoarchean, Paleoproterozoic, etc.
    age_ma NUMERIC,            -- Age in millions of years
    lithology VARCHAR(200),    -- Metabasalt, BIF, Granite, etc.
    lithology_code VARCHAR(20),
    description TEXT,
    mineral_potential TEXT,     -- Gold-bearing, copper-bearing, etc.
    geom GEOMETRY(MultiPolygon, 4326),
    source VARCHAR(100),       -- 'BGS', 'KGS', 'USGS', etc.
    source_ref TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Mineral occurrences (points)
CREATE TABLE mineral_occurrences (
    id SERIAL PRIMARY KEY,
    occurrence_code VARCHAR(50) UNIQUE,
    name VARCHAR(200),
    mineral VARCHAR(100) NOT NULL,
    mineral_group VARCHAR(50), -- 'gold', 'copper', 'zinc', etc.
    occurrence_type VARCHAR(50), -- 'primary', 'alluvial', 'VMS', 'placer'
    grade NUMERIC,             -- g/t for gold, % for base metals
    grade_unit VARCHAR(10),
    host_rock VARCHAR(200),
    geological_setting TEXT,
    status VARCHAR(50),        -- 'active', 'historical', 'prospect'
    discovery_year INTEGER,
    production_records TEXT,
    geom GEOMETRY(Point, 4326),
    source VARCHAR(100),
    source_ref TEXT,
    confidence VARCHAR(20),    -- 'confirmed', 'reported', 'inferred'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Structural features (lines)
CREATE TABLE structural_features (
    id SERIAL PRIMARY KEY,
    feature_type VARCHAR(50),  -- 'fault', 'shear_zone', 'fold_axis', 'lineament'
    feature_name VARCHAR(200),
    trend VARCHAR(20),         -- 'NE-SW', 'NW-SE', etc.
    dip_direction VARCHAR(20),
    dip_angle NUMERIC,
    length_km NUMERIC,
    associated_minerals TEXT,
    geom GEOMETRY(MultiLineString, 4326),
    source VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Geochemical samples
CREATE TABLE geochemical_samples (
    id SERIAL PRIMARY KEY,
    sample_id VARCHAR(50) UNIQUE,
    sample_type VARCHAR(50),   -- 'soil', 'stream_sediment', 'rock', 'water'
    au_ppb NUMERIC,            -- Gold in parts per billion
    cu_ppm NUMERIC,            -- Copper in parts per million
    zn_ppm NUMERIC,
    pb_ppm NUMERIC,
    as_ppm NUMERIC,            -- Arsenic (pathfinder for gold)
    ag_ppm NUMERIC,
    fe_pct NUMERIC,
    analysis_method VARCHAR(50),
    collection_date DATE,
    collector VARCHAR(100),
    geom GEOMETRY(Point, 4326),
    source VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Artisanal mining sites
CREATE TABLE mining_sites (
    id SERIAL PRIMARY KEY,
    site_name VARCHAR(200),
    site_type VARCHAR(50),     -- 'artisanal', 'small_scale', 'large_scale', 'historical'
    minerals_targeted TEXT[],
    status VARCHAR(50),
    workers_estimate INTEGER,
    start_year INTEGER,
    geom GEOMETRY(Point, 4326),
    notes TEXT,
    source VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Rock type lookup
CREATE TABLE rock_types (
    id SERIAL PRIMARY KEY,
    rock_code VARCHAR(20) UNIQUE,
    rock_name VARCHAR(100),
    rock_class VARCHAR(50),    -- 'igneous', 'sedimentary', 'metamorphic'
    sub_class VARCHAR(50),
    mineral_associations TEXT[],
    gold_indicator BOOLEAN DEFAULT FALSE,
    copper_indicator BOOLEAN DEFAULT FALSE
);

-- ==========================================
-- INDEXES FOR PERFORMANCE
-- ==========================================
CREATE INDEX idx_geological_units_geom ON geological_units USING GIST(geom);
CREATE INDEX idx_mineral_occurrences_geom ON mineral_occurrences USING GIST(geom);
CREATE INDEX idx_structural_features_geom ON structural_features USING GIST(geom);
CREATE INDEX idx_geochemical_samples_geom ON geochemical_samples USING GIST(geom);
CREATE INDEX idx_mining_sites_geom ON mining_sites USING GIST(geom);
CREATE INDEX idx_mineral_occurrences_mineral ON mineral_occurrences(mineral);
CREATE INDEX idx_mineral_occurrences_group ON mineral_occurrences(mineral_group);
CREATE INDEX idx_geochemical_au ON geochemical_samples(au_ppb) WHERE au_ppb > 0;

-- ==========================================
-- VIEWS FOR COMMON QUERIES
-- ==========================================

-- Gold prospects: areas with gold occurrences near structural features
CREATE VIEW gold_prospects AS
SELECT 
    mo.name,
    mo.mineral,
    mo.grade,
    mo.host_rock,
    mo.status,
    mo.geom,
    sf.feature_name AS nearby_structure,
    sf.feature_type AS structure_type,
    ST_Distance(mo.geom::geography, sf.geom::geography) AS distance_to_structure_m
FROM mineral_occurrences mo
CROSS JOIN LATERAL (
    SELECT feature_name, feature_type, geom
    FROM structural_features
    WHERE ST_DWithin(mo.geom::geography, geom::geography, 5000)  -- within 5km
    ORDER BY mo.geom <-> geom
    LIMIT 1
) sf
WHERE mo.mineral_group = 'gold';

-- Mineral potential overlay: geological units with mineral indicators
CREATE VIEW mineral_potential_map AS
SELECT 
    gu.unit_name,
    gu.lithology,
    gu.era,
    gu.period,
    gu.mineral_potential,
    COUNT(mo.id) AS occurrence_count,
    ARRAY_AGG(DISTINCT mo.mineral) AS minerals_present,
    gu.geom
FROM geological_units gu
LEFT JOIN mineral_occurrences mo 
    ON ST_Intersects(gu.geom, mo.geom)
GROUP BY gu.id;
```

#### 1.4 Data Import Pipeline

```python
# scripts/import_geological_data.py
"""
Import geological data from multiple sources into PostGIS.
Run once, then update periodically.
"""

import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine
import requests
import json

DATABASE_URL = "postgresql://user:pass@localhost:5432/migori_mining"

def import_bgs_data():
    """Import BGS geological maps for western Kenya."""
    # BGS provides WFS at:
    # https://map.bgs.ac.uk/arcgis/services/GeoIndex/IGS/MapServer/WFSServer
    # Filter for Kenya region bbox: 33.5,-1.5 to 35.5,0.5
    wfs_url = (
        "https://map.bgs.ac.uk/arcgis/services/GeoIndex/IGS/MapServer/WFSServer"
        "?service=WFS&version=2.0.0&request=GetFeature"
        "&typeName=IGS:BGS_625k_Bedrock_Geology"
        "&bbox=-1.5,33.5,0.5,35.5,EPSG:4326"
        "&outputFormat=application/json"
    )
    # Download and load into PostGIS
    gdf = gpd.read_file(wfs_url)
    gdf = gdf.to_crs(epsg=4326)
    engine = create_engine(DATABASE_URL)
    gdf.to_postgis("geological_units_bgs", engine, if_exists="append")

def import_usgs_minerals():
    """Import USGS mineral occurrence data for Kenya."""
    # USGS provides WFS at:
    # https://mrdata.usgs.gov/services/wfs/mrds
    wfs_url = (
        "https://mrdata.usgs.gov/services/wfs/mrds"
        "?service=WFS&version=1.1.0&request=GetFeature"
        "&typeName=mrds:mrds"
        "&bbox=-1.5,33.5,0.5,35.5"
        "&outputFormat=application/json"
    )
    gdf = gpd.read_file(wfs_url)
    engine = create_engine(DATABASE_URL)
    gdf.to_postgis("mineral_occurrences_usgs", engine, if_exists="append")

def import_mindat_data(api_key: str):
    """Import mineral occurrences from Mindat.org API."""
    headers = {"Authorization": f"Bearer {api_key}"}
    base_url = "https://api.mindat.org/v1"
    
    # Search for localities in Migori area
    params = {
        "lat": -0.9,
        "lng": 34.5,
        "radius_km": 100,
        "format": "json"
    }
    resp = requests.get(f"{base_url}/localities", headers=headers, params=params)
    localities = resp.json()
    
    engine = create_engine(DATABASE_URL)
    for loc in localities.get("results", []):
        # Parse and insert each locality
        pass

def import_shackleton_1946():
    """
    Import digitized geological map from Shackleton (1946).
    This requires manual digitization of the scanned map first.
    Shapefiles should be prepared in QGIS, then imported here.
    """
    gdf = gpd.read_file("data/shackleton_1946_digitized.shp")
    engine = create_engine(DATABASE_URL)
    gdf.to_postgis("geological_units_shackleton", engine, if_exists="append")

def import_ogola_geochemistry():
    """Import geochemical data from Ogola's published tables."""
    # Data from Ogola (1986) "Distribution of Cu, Au, Ag in Macalder"
    # Manually transcribed from published tables
    df = pd.read_csv("data/ogola_1986_geochemistry.csv")
    gdf = gpd.GeoDataFrame(
        df, 
        geometry=gpd.points_from_xy(df.longitude, df.latitude),
        crs="EPSG:4326"
    )
    engine = create_engine(DATABASE_URL)
    gdf.to_postgis("geochemical_samples", engine, if_exists="append")
```

#### 1.5 Query API Layer

```python
# api/geology_api.py
"""
FastAPI service for geological queries.
Replaces the hardcoded dictionary with real spatial queries.
"""

from fastapi import FastAPI, Query
from sqlalchemy import create_engine, text
import json

app = FastAPI(title="Migori Geology API")
engine = create_engine(DATABASE_URL)

@app.get("/geology/at-point")
async def get_geology_at_point(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180)
):
    """What geology exists at this exact location?"""
    query = text("""
        SELECT unit_name, lithology, era, period, age_ma, 
               mineral_potential, source
        FROM geological_units
        WHERE ST_Intersects(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
        ORDER BY created_at DESC
        LIMIT 1
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"lat": lat, "lng": lng}).fetchone()
    if result:
        return {
            "location": {"lat": lat, "lng": lng},
            "geology": dict(result._mapping)
        }
    return {"location": {"lat": lat, "lng": lng}, "geology": None, "note": "No geological data for this point"}

@app.get("/minerals/nearby")
async def get_nearby_minerals(
    lat: float,
    lng: float,
    radius_km: float = 10,
    mineral_group: str = None
):
    """Find mineral occurrences near a point."""
    query = text("""
        SELECT name, mineral, mineral_group, grade, grade_unit,
               host_rock, status, confidence, source,
               ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography) as distance_m
        FROM mineral_occurrences
        WHERE ST_DWithin(
            geom::geography, 
            ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
            :radius_m
        )
        AND (:mineral_group IS NULL OR mineral_group = :mineral_group)
        ORDER BY distance_m
    """)
    with engine.connect() as conn:
        results = conn.execute(query, {
            "lat": lat, "lng": lng,
            "radius_m": radius_km * 1000,
            "mineral_group": mineral_group
        }).fetchall()
    return {"results": [dict(r._mapping) for r in results]}

@app.get("/geology/mineral-potential")
async def assess_mineral_potential(
    lat: float,
    lng: float,
    radius_km: float = 5
):
    """
    Assess mineral potential of an area by combining:
    - Geological unit type
    - Proximity to structural features
    - Known mineral occurrences
    - Geochemical anomalies
    """
    query = text("""
        WITH point AS (SELECT ST_SetSRID(ST_MakePoint(:lng, :lat), 4326) as geom),
        nearby_geology AS (
            SELECT lithology, mineral_potential, era
            FROM geological_units, point
            WHERE ST_DWithin(geological_units.geom::geography, point.geom::geography, :radius_m)
        ),
        nearby_structures AS (
            SELECT feature_type, feature_name,
                   ST_Distance(geom::geography, point.geom::geography) as dist
            FROM structural_features, point
            WHERE ST_DWithin(geom::geography, point.geom::geography, :radius_m)
            ORDER BY dist LIMIT 5
        ),
        nearby_occurrences AS (
            SELECT mineral, grade, status,
                   ST_Distance(geom::geography, point.geom::geography) as dist
            FROM mineral_occurrences, point
            WHERE ST_DWithin(geom::geography, point.geom::geography, :radius_m)
            ORDER BY dist LIMIT 10
        ),
        nearby_geochem AS (
            SELECT au_ppb, cu_ppm, as_ppm,
                   ST_Distance(geom::geography, point.geom::geography) as dist
            FROM geochemical_samples, point
            WHERE ST_DWithin(geom::geography, point.geom::geography, :radius_m)
            ORDER BY dist LIMIT 20
        )
        SELECT 
            json_build_object(
                'geology', (SELECT json_agg(t) FROM nearby_geology t),
                'structures', (SELECT json_agg(t) FROM nearby_structures t),
                'occurrences', (SELECT json_agg(t) FROM nearby_occurrences t),
                'geochemistry', (SELECT json_agg(t) FROM nearby_geochem t)
            ) as assessment
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {
            "lat": lat, "lng": lng,
            "radius_m": radius_km * 1000
        }).fetchone()
    return result[0] if result else {"error": "No data available"}

@app.get("/geology/gold-prospects")
async def find_gold_prospects(
    lat: float,
    lng: float,
    radius_km: float = 20
):
    """Find gold prospecting targets by combining multiple data layers."""
    query = text("""
        SELECT 
            gu.unit_name,
            gu.lithology,
            gu.mineral_potential,
            COUNT(DISTINCT mo.id) as gold_occurrences,
            COUNT(DISTINCT sf.id) as nearby_structures,
            MAX(gs.au_ppb) as max_gold_anomaly,
            ST_Centroid(ST_Union(gu.geom)) as centroid
        FROM geological_units gu
        LEFT JOIN mineral_occurrences mo 
            ON ST_DWithin(gu.geom::geography, mo.geom::geography, :radius_m)
            AND mo.mineral_group = 'gold'
        LEFT JOIN structural_features sf
            ON ST_DWithin(gu.geom::geography, sf.geom::geography, :radius_m)
        LEFT JOIN geochemical_samples gs
            ON ST_DWithin(gu.geom::geography, gs.geom::geography, :radius_m)
            AND gs.au_ppb > 10  -- above background
        WHERE ST_DWithin(
            gu.geom::geography,
            ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
            :radius_m
        )
        GROUP BY gu.id
        HAVING COUNT(DISTINCT mo.id) > 0 OR MAX(gs.au_ppb) > 50
        ORDER BY gold_occurrences DESC, max_gold_anomaly DESC
    """)
    with engine.connect() as conn:
        results = conn.execute(query, {
            "lat": lat, "lng": lng,
            "radius_m": radius_km * 1000
        }).fetchall()
    return {"prospects": [dict(r._mapping) for r in results]}
```

#### 1.6 Migration Plan

| Phase | Action | Timeline | Cost |
|-------|--------|----------|------|
| 1 | Set up PostGIS database | 1 day | Free (PostgreSQL + PostGIS) |
| 2 | Import BGS colonial-era maps via WFS | 1 day | Free |
| 3 | Import USGS mineral occurrence data | 1 day | Free |
| 4 | Request data from Kenya Geological Survey | 2-4 weeks | Free (formal request) |
| 5 | Digitize Shackleton (1946) map in QGIS | 1-2 weeks | Free (manual work) |
| 6 | Import Ogola's geochemical data | 2-3 days | Free (manual transcription) |
| 7 | Set up Mindat API integration | 1 day | Free (non-commercial key) |
| 8 | Build query API layer | 2-3 days | Free |
| 9 | Replace hardcoded dict with API calls | 1 day | Free |

**Total estimated time:** 3-6 weeks  
**Total estimated cost:** $0 (all open data sources)

---

## Problem 2: Luo (Dholuo) Translations Are Wrong

### Current State
The code has "Luo translations" that are mostly Swahili words written in Luo phonetics. This is misleading and disrespectful to Dholuo speakers.

### Analysis of the Problem

The Dholuo language (Luo proper, not Swahili) belongs to the Nilotic language family, completely different from Swahili (Bantu family). Key differences:

| Swahili (Bantu) | Dholuo (Nilotic) | English |
|------------------|-------------------|---------|
| Dhahabu | Min | Gold |
| Shaba | — | Copper (no traditional word) |
| Mawe | — | Stone/Rock (Dholuo: "ot") |
| Mgodi | — | Mine (Dholuo: "kilo" or borrowed) |
| Dunia | — | World |
| Mto | — | River (Dholuo: "aora") |

### Solution: Three-Tier Localization Strategy

#### 2.1 Language Tier System

**Tier 1: English (Primary)**
- All technical, scientific, and legal content
- Geological terms, mineral names, assay results
- API responses, data exports
- Financial documents
- **Rationale:** Mining is a technical field. English is Kenya's business language and the language of geology.

**Tier 2: Swahili (Secondary — Community Interface)**
- User-facing mining tool interface
- Community notifications and alerts
- Basic training materials
- Health and safety warnings
- **Rationale:** Swahili is Kenya's national lingua franca, understood by ~95% of Migori residents. It's the practical language for community engagement.

**Tier 3: Dholuo (Tertiary — Cultural Respect)**
- Greetings and community engagement phrases
- Cultural context notes
- Traditional knowledge integration
- Audio greetings for voice interface
- **Rationale:** Dholuo is the mother tongue of most Migori residents. Using it shows respect, but forcing technical translations into Dholuo creates confusion.

#### 2.2 Correct Dholuo Mining/Geological Vocabulary

**Verified Dholuo terms (to be reviewed by native speaker):**

| English | Swahili | Dholuo | Notes |
|---------|---------|--------|-------|
| Gold | Dhahabu | Min | Traditional Dholuo word for gold |
| Silver | Fedha | — | Use Swahili or English |
| Copper | Shaba | — | No traditional Dholuo word; use English |
| Iron | Chuma | — | Dholuo: "thing'o" (metal generally) |
| Stone/Rock | Mawe | Ot / Okuta | "Ot" = stone; context-dependent |
| River | Mto | Aora | Migori River = "Aora Migori" |
| Mine/Mining | Mgodi/Uchimbaji | Kilo / Chimb | Borrowed or adapted |
| Earth/Soil | Udongo | — | Use Swahili |
| Water | Maji | Pi / Piny | "Pi" = water |
| Mountain | Mlima | Got | |
| Gold dust | Vumbi la dhahabu | Min mot | |
| To dig | Kuchimba | Chimb | |
| Worker | Mfanyakazi | Jatelo | |
| Pit/Shaft | Shimo | Lang | |
| Ore | Madini | — | Use Swahili/English |

**⚠️ CRITICAL NOTE:** These Dholuo terms need verification by a native Dholuo speaker from Migori. Dholuo has dialectical variations. Do NOT use AI-generated Dholuo without human review.

#### 2.3 Implementation: i18n Framework

```python
# i18n/localization.py
"""
Localization framework for the mining tools.
Three-tier: English (primary), Swahili (secondary), Dholuo (tertiary with human review).
"""

from enum import Enum
from typing import Optional
import json

class Language(Enum):
    EN = "en"      # English - primary (technical/legal)
    SW = "sw"      # Swahili - secondary (community interface)
    LUO = "luo"    # Dholuo - tertiary (cultural, human-reviewed only)

class LocalizationManager:
    def __init__(self, locale_dir: str = "i18n/locales"):
        self.locale_dir = locale_dir
        self.translations = {}
        self._load_translations()
        self._human_reviewed = set()  # Track which Luo translations are verified
    
    def _load_translations(self):
        for lang in Language:
            filepath = f"{self.locale_dir}/{lang.value}.json"
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.translations[lang.value] = json.load(f)
            except FileNotFoundError:
                self.translations[lang.value] = {}
    
    def t(self, key: str, lang: Language = Language.EN, **kwargs) -> str:
        """
        Get translation. Falls back through tier system:
        1. Try requested language
        2. If Luo and not human-reviewed, fall back to Swahili
        3. If missing, fall back to English
        4. If still missing, return key
        """
        # Dholuo: only return if human-verified
        if lang == Language.LUO:
            if key not in self._human_reviewed:
                # Fall back to Swahili for unverified Dholuo
                lang = Language.SW
        
        text = self.translations.get(lang.value, {}).get(key)
        if text is None and lang != Language.EN:
            text = self.translations.get("en", {}).get(key)
        if text is None:
            text = key  # Return the key itself as last resort
        
        # Apply template variables
        if kwargs:
            text = text.format(**kwargs)
        return text
    
    def mark_human_reviewed(self, key: str):
        """Mark a Dholuo translation as verified by native speaker."""
        self._human_reviewed.add(key)
    
    def get_unreviewed_luo(self) -> list:
        """Get list of Dholuo translations needing human review."""
        luo_keys = set(self.translations.get("luo", {}).keys())
        return list(luo_keys - self._human_reviewed)
```

```json
// i18n/locales/en.json
{
    "mineral.gold": "Gold",
    "mineral.copper": "Copper",
    "mineral.pyrite": "Pyrite",
    "mineral.arsenopyrite": "Arsenopyrite",
    "geology.rock_type": "Rock Type",
    "geology.formation": "Geological Formation",
    "geology.greenstone_belt": "Greenstone Belt",
    "alert.high_mercury": "WARNING: High mercury levels detected in water samples",
    "alert.gold_detected": "Gold anomaly detected in this area",
    "action.collect_sample": "Collect Sample",
    "action.view_map": "View Geological Map",
    "status.pending_review": "Pending human review",
    "status.confirmed": "Confirmed by geologist"
}
```

```json
// i18n/locales/sw.json
{
    "mineral.gold": "Dhahabu",
    "mineral.copper": "Shaba",
    "mineral.pyrite": "Piriti",
    "mineral.arsenopyrite": "Arsenopiriti",
    "geology.rock_type": "Aina ya Mawe",
    "geology.formation": "Uundaji wa Kijiolojia",
    "geology.greenstone_belt": "Mkanda wa Mawe ya Kijani",
    "alert.high_mercury": "TAHADHARI: Viwango vya juu vya zebaki vimetambuliwa kwenye maji",
    "alert.gold_detected": "Dhahabu imegunduliwa katika eneo hili",
    "action.collect_sample": "Kusanya Sampuli",
    "action.view_map": "Tazama Ramani ya Kijiolojia",
    "status.pending_review": "Inasubiri ukaguzi wa binadamu",
    "status.confirmed": "Imethibitishwa na mtaalamu wa jiolojia"
}
```

```json
// i18n/locales/luo.json
{
    "mineral.gold": "Min",
    "mineral.copper": "Shaba",
    "mineral.pyrite": "Piriti",
    "geology.rock_type": "Nyanza ot",
    "geology.greenstone_belt": "Belt gi ot machuthi",
    "alert.high_mercury": "PARO: Pi en gi mercury mang'eny",
    "alert.gold_detected": "Min niwe ka e piny ni",
    "action.collect_sample": "Ket sampul",
    "action.view_map": "Nen map mar jioloji"
}
```

#### 2.4 Translation Review Process

```
┌─────────────────────────────────────────────────────┐
│              TRANSLATION REVIEW WORKFLOW              │
├─────────────────────────────────────────────────────┤
│                                                       │
│  1. English term defined (by developer)              │
│           ↓                                           │
│  2. Swahili translation (dictionary + Swahili speaker)│
│           ↓                                           │
│  3. Dholuo draft (AI-assisted, flagged as unverified)│
│           ↓                                           │
│  4. Native Dholuo speaker review                     │
│     - Verify meaning accuracy                        │
│     - Check dialect appropriateness                  │
│     - Confirm pronunciation guide                    │
│           ↓                                           │
│  5. Mark as human-reviewed in code                   │
│           ↓                                           │
│  6. Available for Dholuo UI display                  │
│                                                       │
└─────────────────────────────────────────────────────┘
```

#### 2.5 Hiring Native Reviewers

- **Budget:** $200-500 for a Dholuo language consultant (one-time)
- **Source:** University of Nairobi Linguistics Department, Maseno University (Kisumu, Luo-speaking region)
- **Alternative:** Migori County cultural officers, local radio presenters (e.g., Ramogi FM, Radio Lake Victoria)
- **Scope:** ~200 technical terms + 50 UI phrases
- **Timeline:** 1-2 weeks

---

## Problem 3: No Error Handling for Real-World Conditions

### Current State
No retry logic, no cloud cover handling, no offline mode, no graceful degradation.

### Solution: Resilient Multi-Source Architecture

#### 3.1 Multi-Source Satellite Strategy

Migori County (0.5°S-1.5°S, 33.5°E-35°E) has **persistent cloud cover** due to its location near Lake Victoria and the highlands. Average cloud-free days: ~90-120/year. Single-source satellite imagery is unreliable.

**Strategy: Cascade through multiple sources**

```
┌──────────────────────────────────────────────────────────┐
│                SATELLITE DATA CASCADE                     │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  SOURCE 1: Sentinel-2 (ESA)                               │
│  ├─ Resolution: 10m (visible), 20m (SWIR)                │
│  ├─ Revisit: 5 days                                       │
│  ├─ Cloud cover issue: HIGH (tropical)                    │
│  └─ API: Copernicus Data Space (dataspace.copernicus.eu)  │
│           ↓ FAIL (cloudy/no data)                         │
│                                                            │
│  SOURCE 2: Landsat 8/9 (USGS)                             │
│  ├─ Resolution: 30m                                       │
│  ├─ Revisit: 16 days                                      │
│  ├─ Cloud cover: better time coverage                     │
│  └─ API: USGS EarthExplorer (earthexplorer.usgs.gov)      │
│           ↓ FAIL (cloudy/no data)                         │
│                                                            │
│  SOURCE 3: Google Earth Engine                            │
│  ├─ Cloud-free composites from multi-year stacking        │
│  ├─ Processing: server-side                               │
│  └─ API: ee Python library                                │
│           ↓ FAIL (no access)                              │
│                                                            │
│  SOURCE 4: Planet Labs (commercial)                       │
│  ├─ Resolution: 3-5m                                      │
│  ├─ Daily revisit                                          │
│  └─ Cost: ~$0.05-0.20/km²                                │
│           ↓ FAIL (budget)                                 │
│                                                            │
│  SOURCE 5: Sentinel-1 SAR (all-weather)                   │
│  ├─ Radar: penetrates clouds                              │
│  ├─ Resolution: 10-20m                                    │
│  └─ Good for: surface change, moisture, structure         │
│           ↓ FAIL (no data)                                │
│                                                            │
│  FALLBACK: Cached last-good + local drone imagery         │
│                                                            │
└──────────────────────────────────────────────────────────┘
```

#### 3.2 Cloud Cover Detection & Filtering

```python
# satellite/cloud_filter.py
"""
Cloud cover detection and filtering for satellite imagery.
Handles Migori's persistent cloud cover.
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timedelta

@dataclass
class SatelliteScene:
    source: str
    scene_id: str
    date: datetime
    cloud_cover_pct: float
    bbox: tuple  # (min_lon, min_lat, max_lon, max_lat)
    bands: dict  # band_name -> array
    metadata: dict

class CloudFilter:
    """Multi-strategy cloud detection."""
    
    # Migori-specific thresholds
    MAX_CLOUD_COVER = 30  # Reject scenes with >30% cloud
    IDEAL_CLOUD_COVER = 10  # Prefer scenes with <10% cloud
    MIN_CLEAR_PIXELS_PCT = 50  # Minimum usable pixels
    
    @staticmethod
    def sentinel2_cloud_mask(scene: SatelliteScene) -> np.ndarray:
        """
        Cloud mask for Sentinel-2 using SCL (Scene Classification Layer).
        SCL values:
        0 = No data, 1 = Saturated, 2 = Dark features
        3 = Cloud shadows, 4 = Vegetation, 5 = Bare soil
        6 = Water, 7 = Cloud (low probability), 8 = Cloud (medium)
        9 = Cloud (high probability), 10 = Thin cirrus, 11 = Snow
        """
        if 'SCL' in scene.bands:
            scl = scene.bands['SCL']
            # Cloud + cloud shadow + no data = masked
            cloud_mask = np.isin(scl, [0, 1, 3, 7, 8, 9, 10])
            return cloud_mask
        return np.zeros(scene.bands[list(scene.bands.keys())[0]].shape, dtype=bool)
    
    @staticmethod
    def landsat_cloud_mask(scene: SatelliteScene) -> np.ndarray:
        """Cloud mask for Landsat using QA_PIXEL band."""
        if 'QA_PIXEL' in scene.bands:
            qa = scene.bands['QA_PIXEL']
            # Bit 3 = cloud, bit 4 = cloud shadow
            cloud = (qa & 0b00001000) > 0
            shadow = (qa & 0b00010000) > 0
            return cloud | shadow
        return np.zeros(scene.bands[list(scene.bands.keys())[0]].shape, dtype=bool)
    
    @staticmethod
    def ndvi_cloud_heuristic(scene: SatelliteScene) -> np.ndarray:
        """
        Heuristic cloud detection using spectral properties.
        Clouds are: high reflectance in visible + low NDVI.
        """
        if 'B04' in scene.bands and 'B08' in scene.bands:
            red = scene.bands['B04'].astype(float)
            nir = scene.bands['B08'].astype(float)
            ndvi = (nir - red) / (nir + red + 1e-10)
            
            # Bright + low NDVI = likely cloud
            bright = red > 2000  # Reflectance threshold
            low_ndvi = ndvi < 0.1
            return bright & low_ndvi
        return np.zeros(scene.bands[list(scene.bands.keys())[0]].shape, dtype=bool)


class SceneSelector:
    """Select best available scene from multiple sources."""
    
    def __init__(self, max_cloud_pct: float = 30, lookback_days: int = 90):
        self.max_cloud_pct = max_cloud_pct
        self.lookback_days = lookback_days
    
    def select_best(
        self, 
        scenes: List[SatelliteScene],
        target_date: Optional[datetime] = None
    ) -> Optional[SatelliteScene]:
        """
        Select best scene by:
        1. Filter by cloud cover threshold
        2. Prefer scenes closest to target date
        3. Among same-date scenes, prefer lowest cloud cover
        """
        if not scenes:
            return None
        
        # Filter by cloud cover
        usable = [s for s in scenes if s.cloud_cover_pct <= self.max_cloud_pct]
        if not usable:
            # Relax threshold and warn
            usable = sorted(scenes, key=lambda s: s.cloud_cover_pct)[:3]
            print(f"WARNING: No scene under {self.max_cloud_pct}% cloud. "
                  f"Best available: {usable[0].cloud_cover_pct:.1f}%")
        
        # Filter by date
        cutoff = datetime.now() - timedelta(days=self.lookback_days)
        recent = [s for s in usable if s.date >= cutoff]
        if not recent:
            recent = usable  # Use older scenes if nothing recent
        
        # Sort by: closest to target date, then lowest cloud
        if target_date:
            recent.sort(key=lambda s: (
                abs((s.date - target_date).days),
                s.cloud_cover_pct
            ))
        else:
            recent.sort(key=lambda s: s.cloud_cover_pct)
        
        return recent[0]
    
    def create_cloud_free_composite(
        self,
        scenes: List[SatelliteScene],
        method: str = "median"
    ) -> dict:
        """
        Create cloud-free composite from multiple scenes.
        Uses median pixel value to remove clouds.
        """
        # Stack all scenes, apply cloud masks, take median of clear pixels
        all_bands = {}
        cloud_masks = []
        
        for scene in scenes:
            mask = CloudFilter.sentinel2_cloud_mask(scene)
            cloud_masks.append(mask)
            for band_name, band_data in scene.bands.items():
                if band_name not in all_bands:
                    all_bands[band_name] = []
                # Mask cloudy pixels
                masked = band_data.copy().astype(float)
                masked[mask] = np.nan
                all_bands[band_name].append(masked)
        
        composite = {}
        for band_name, band_stack in all_bands.items():
            stacked = np.stack(band_stack)
            if method == "median":
                composite[band_name] = np.nanmedian(stacked, axis=0)
            elif method == "mean":
                composite[band_name] = np.nanmean(stacked, axis=0)
        
        return composite
```

#### 3.3 Retry Logic with Exponential Backoff

```python
# core/retry.py
"""
Retry logic with exponential backoff for all external API calls.
"""

import time
import random
import functools
import logging
from typing import Callable, Type, Tuple, Optional

logger = logging.getLogger(__name__)

class RetryConfig:
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Tuple[Type[Exception], ...] = (
            ConnectionError, TimeoutError, OSError
        ),
        retryable_status_codes: Tuple[int, ...] = (429, 500, 502, 503, 504)
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions
        self.retryable_status_codes = retryable_status_codes

def with_retry(config: Optional[RetryConfig] = None):
    """Decorator for retry logic."""
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    if attempt == config.max_retries:
                        logger.error(
                            f"{func.__name__} failed after {config.max_retries + 1} attempts: {e}"
                        )
                        raise
                    
                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )
                    if config.jitter:
                        delay *= (0.5 + random.random())
                    
                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1}/{config.max_retries + 1} "
                        f"failed: {e}. Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator

# Usage examples:
satellite_retry = RetryConfig(max_retries=3, base_delay=5.0, max_delay=120)
api_retry = RetryConfig(max_retries=5, base_delay=1.0, max_delay=30)
db_retry = RetryConfig(max_retries=2, base_delay=0.5, max_delay=5)

@with_retry(satellite_retry)
def fetch_sentinel2_scene(bbox, date_range):
    """Fetch satellite scene with automatic retry."""
    # Implementation using Copernicus API
    pass

@with_retry(api_retry)
def query_mindat_api(params):
    """Query Mindat.org API with retry."""
    pass

@with_retry(db_retry)
def query_postgis(sql, params):
    """Query PostGIS with retry."""
    pass
```

#### 3.4 Graceful Degradation Framework

```python
# core/degradation.py
"""
Graceful degradation: when primary tools fail, use fallbacks.
"""

from enum import Enum
from typing import Any, Callable, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

class ServiceLevel(Enum):
    FULL = "full"              # All features available
    REDUCED = "reduced"        # Some features unavailable
    MINIMAL = "minimal"        # Basic functionality only
    OFFLINE = "offline"        # Cached data only

@dataclass
class SystemState:
    level: ServiceLevel = ServiceLevel.FULL
    unavailable_services: list = field(default_factory=list)
    cache_hit_rate: float = 0.0
    last_online: Optional[str] = None

class GracefulDegradation:
    """
    Manages service levels and fallbacks.
    """
    
    def __init__(self):
        self.state = SystemState()
        self.cache = {}  # Simple in-memory cache; use Redis in production
    
    def check_service(self, service_name: str, health_check: Callable) -> bool:
        """Check if a service is available."""
        try:
            result = health_check()
            if result:
                if service_name in self.state.unavailable_services:
                    self.state.unavailable_services.remove(service_name)
                return True
        except Exception as e:
            logger.warning(f"Service {service_name} unavailable: {e}")
            if service_name not in self.state.unavailable_services:
                self.state.unavailable_services.append(service_name)
        
        self._update_service_level()
        return False
    
    def _update_service_level(self):
        """Update overall service level based on unavailable services."""
        n_unavailable = len(self.state.unavailable_services)
        
        if n_unavailable == 0:
            self.state.level = ServiceLevel.FULL
        elif n_unavailable <= 2:
            self.state.level = ServiceLevel.REDUCED
        elif n_unavailable <= 4:
            self.state.level = ServiceLevel.MINIMAL
        else:
            self.state.level = ServiceLevel.OFFLINE
        
        logger.info(f"Service level: {self.state.level.value} "
                    f"({n_unavailable} services down)")
    
    def with_fallback(
        self,
        primary: Callable,
        fallbacks: list,
        cache_key: Optional[str] = None
    ) -> Any:
        """
        Try primary function, then fallbacks in order.
        Cache successful results for offline use.
        """
        # Try from cache first if we're degraded
        if cache_key and cache_key in self.cache:
            if self.state.level in (ServiceLevel.MINIMAL, ServiceLevel.OFFLINE):
                logger.info(f"Using cached data for {cache_key}")
                return self.cache[cache_key]
        
        # Try primary
        try:
            result = primary()
            if cache_key:
                self.cache[cache_key] = result
            return result
        except Exception as e:
            logger.warning(f"Primary failed: {e}")
        
        # Try fallbacks
        for i, fallback in enumerate(fallbacks):
            try:
                result = fallback()
                if cache_key:
                    self.cache[cache_key] = result
                logger.info(f"Fallback {i+1} succeeded")
                return result
            except Exception as e:
                logger.warning(f"Fallback {i+1} failed: {e}")
        
        # All failed — try cache as last resort
        if cache_key and cache_key in self.cache:
            logger.warning(f"All sources failed. Using stale cache for {cache_key}")
            return self.cache[cache_key]
        
        raise RuntimeError(f"All sources failed for {cache_key or 'unknown'}")


# Example usage for satellite data:
def get_satellite_imagery(bbox, date_range):
    """Get satellite imagery with full fallback chain."""
    gd = GracefulDegradation()
    
    return gd.with_fallback(
        primary=lambda: fetch_sentinel2(bbox, date_range),
        fallbacks=[
            lambda: fetch_landsat(bbox, date_range),
            lambda: fetch_gee_composite(bbox, date_range),
            lambda: fetch_sentinel1_sar(bbox, date_range),  # All-weather radar
        ],
        cache_key=f"satellite_{bbox}_{date_range}"
    )
```

#### 3.5 Offline Mode

```python
# core/offline.py
"""
Offline mode for when internet is unavailable.
Critical for field use in rural Migori.
"""

import json
import os
from pathlib import Path
from datetime import datetime

class OfflineManager:
    """
    Manages offline capabilities:
    - Caches all API responses locally
    - Stores geological database locally
    - Queues write operations for sync when online
    """
    
    CACHE_DIR = Path("data/offline_cache")
    QUEUE_FILE = Path("data/offline_queue.json")
    
    def __init__(self):
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._load_queue()
    
    def _load_queue(self):
        if self.QUEUE_FILE.exists():
            with open(self.QUEUE_FILE) as f:
                self.queue = json.load(f)
        else:
            self.queue = []
    
    def cache_response(self, service: str, key: str, data: dict):
        """Cache an API response for offline use."""
        cache_file = self.CACHE_DIR / f"{service}_{key}.json"
        cached = {
            "data": data,
            "cached_at": datetime.now().isoformat(),
            "service": service,
            "key": key
        }
        with open(cache_file, 'w') as f:
            json.dump(cached, f)
    
    def get_cached(self, service: str, key: str) -> Optional[dict]:
        """Retrieve cached data."""
        cache_file = self.CACHE_DIR / f"{service}_{key}.json"
        if cache_file.exists():
            with open(cache_file) as f:
                cached = json.load(f)
            return cached["data"]
        return None
    
    def queue_operation(self, operation: dict):
        """Queue a write operation for when we're back online."""
        operation["queued_at"] = datetime.now().isoformat()
        self.queue.append(operation)
        self._save_queue()
    
    def _save_queue(self):
        with open(self.QUEUE_FILE, 'w') as f:
            json.dump(self.queue, f, indent=2)
    
    def sync_queue(self):
        """Sync queued operations when back online."""
        if not self.queue:
            return
        
        synced = []
        for op in self.queue:
            try:
                # Execute the queued operation
                self._execute_operation(op)
                synced.append(op)
            except Exception as e:
                print(f"Failed to sync operation: {e}")
        
        # Remove synced operations
        self.queue = [op for op in self.queue if op not in synced]
        self._save_queue()
        print(f"Synced {len(synced)} queued operations")
    
    def _execute_operation(self, operation: dict):
        """Execute a queued operation."""
        # Route to appropriate handler based on operation type
        op_type = operation.get("type")
        if op_type == "sample_submission":
            # Submit cached sample data to server
            pass
        elif op_type == "mineral_report":
            # Upload cached mineral report
            pass
```

---

## Problem 4: CLIP Cannot Distinguish Similar Minerals

### Current State
CLIP (vision-language model) is being used for mineral identification from photos alone. It cannot reliably distinguish:
- Gold vs pyrite (both gold-colored)
- Chalcopyrite vs pyrite (both brassy metallic)
- Quartz vs calcite (both white/clear crystals)

### Solution: Multi-Modal Mineral Identification System

#### 4.1 Why Visual-Only Identification Fails

| Mineral Pair | Visual Similarity | Distinguishing Properties |
|-------------|-------------------|--------------------------|
| Gold vs Pyrite | Both gold-colored | **Streak:** gold = yellow; pyrite = black. **Hardness:** gold = 2.5; pyrite = 6.5. **SG:** gold = 19.3; pyrite = 5.0 |
| Chalcopyrite vs Pyrite | Both brassy metallic | **Hardness:** chalcopyrite = 3.5; pyrite = 6.5. **Streak:** chalcopyrite = greenish-black; pyrite = black |
| Quartz vs Calcite | Both white/clear | **Hardness:** quartz = 7; calcite = 3. **Acid test:** calcite fizzes with HCl; quartz doesn't |

**Conclusion:** Visual-only ID is fundamentally insufficient for look-alike minerals. Need physical tests.

#### 4.2 Decision Tree for Common Migori Minerals

```
MINERAL IDENTIFICATION DECISION TREE
=====================================

STEP 1: VISUAL COLOR
├── GOLD/YELLOW
│   ├── Streak test → Yellow streak = GOLD ✓
│   ├── Streak test → Black streak = PYRITE
│   ├── SG test → Heavy (>10) = GOLD
│   └── SG test → Light (<6) = PYRITE
│
├── BRASS-YELLOW (metallic)
│   ├── Hardness test → Soft (<4) = CHALCOPYRITE
│   ├── Hardness test → Hard (>6) = PYRITE
│   └── Streak → Greenish-black = CHALCOPYRITE
│
├── WHITE/CLEAR (crystals)
│   ├── Acid test → Fizzes = CALCITE
│   ├── Acid test → No reaction = QUARTZ
│   ├── Hardness → Scratches glass (7) = QUARTZ
│   └── Hardness → Scratched by coin (3) = CALCITE
│
├── GREEN (coating)
│   ├── On copper rock = MALACHITE (copper indicator)
│   └── Earthy green = possibly EPIDOTE
│
├── BLUE (coating)
│   └── On copper rock = AZURITE (copper indicator)
│
├── BLACK (metallic)
│   ├── Soft, leaves marks = GRAPHITE
│   ├── Hard, submetallic = possibly GALENA (check SG)
│   └── Red-brown streak = HEMATITE
│
└── RED-BROWN (earthy)
    └── Iron staining = possible GOSSEN (indicator of sulphides below)
```

#### 4.3 Non-Visual Identification Methods

**Field-Portable Methods:**

| Method | Equipment | Cost | What It Identifies | Speed |
|--------|-----------|------|-------------------|-------|
| **Streak test** | Unglazed porcelain tile ($1) | $1 | Gold vs pyrite, hematite vs magnetite | 10 sec |
| **Hardness test** | Mohs hardness kit ($15) | $15 | Quartz vs calcite, all look-alikes | 30 sec |
| **Acid test** | Dilute HCl dropper ($10) | $10 | Calcite vs quartz, carbonate minerals | 10 sec |
| **Specific gravity** | Digital scale + water ($30) | $30 | Gold (19.3) vs pyrite (5.0) | 2 min |
| **Magnet test** | Rare earth magnet ($5) | $5 | Magnetite, some pyrrhotite | 5 sec |
| **Portable XRF** | Vanta, S1 Titan, XL3 | $15k-40k | ALL elements, definitive ID | 30 sec |
| **UV fluorescence** | UV lamp ($20) | $20 | Scheelite, some calcite, some fluorite | 10 sec |

**Portable XRF is the gold standard for field mineral ID.** It measures elemental composition directly:
- Gold vs pyrite: XRF shows Au (gold) vs Fe+S (pyrite). Definitive.
- Chalcopyrite vs pyrite: XRF shows Cu+Fe+S vs Fe+S. Definitive.
- Quartz vs calcite: XRF shows Si vs Ca. Definitive.

#### 4.4 Multi-Modal Identification Architecture

```python
# mineral_id/multi_modal.py
"""
Multi-modal mineral identification system.
Combines: photo + physical tests + location + context.
"""

from dataclasses import dataclass
from typing import Optional, Dict, List
from enum import Enum

class ConfidenceLevel(Enum):
    VERY_LOW = "very_low"    # Photo only
    LOW = "low"              # Photo + 1 physical test
    MEDIUM = "medium"        # Photo + 2+ physical tests
    HIGH = "high"            # Physical tests + XRF
    DEFINITIVE = "definitive"  # XRF + lab assay

@dataclass
class PhysicalProperties:
    """Physical test results for mineral identification."""
    streak_color: Optional[str] = None       # yellow, white, black, greenish-black, red-brown
    hardness_mohs: Optional[float] = None    # 1-10 scale
    specific_gravity: Optional[float] = None # g/cm³
    acid_reaction: Optional[bool] = None     # True = fizzes with HCl
    magnetic: Optional[bool] = None
    crystal_system: Optional[str] = None     # cubic, hexagonal, etc.
    luster: Optional[str] = None            # metallic, vitreous, adamantine
    cleavage: Optional[str] = None          # perfect, good, none
    fluorescence: Optional[str] = None      # color under UV

@dataclass
class XRFResult:
    """Portable XRF measurement results."""
    elements: Dict[str, float]  # element -> ppm or %
    detection_limit: float
    measurement_time_sec: int
    device_model: str

@dataclass
class LocationContext:
    """Geological context for the sample location."""
    latitude: float
    longitude: float
    geological_unit: Optional[str] = None
    host_rock: Optional[str] = None
    known_minerals_in_area: List[str] = None
    geological_setting: Optional[str] = None  # greenstone, VMS, alluvial

@dataclass
class MineralIDResult:
    """Final mineral identification result."""
    primary_id: str
    confidence: ConfidenceLevel
    alternative_ids: List[Dict]  # [{"mineral": "pyrite", "probability": 0.15}]
    evidence: Dict  # What contributed to the ID
    requires_lab_confirmation: bool
    notes: str


class MultiModalMineralIdentifier:
    """
    Identify minerals using multiple data sources.
    Never relies on photo alone for look-alike minerals.
    """
    
    # Minerals that MUST have physical tests (visual doppelgangers)
    LOOK_ALIKES = {
        "gold_group": ["gold", "pyrite", "chalcopyrite", "pyrrhotite", "mica"],
        "white_crystals": ["quartz", "calcite", "feldspar", "gypsum"],
        "brass_metallic": ["chalcopyrite", "pyrite", "pyrrhotite", "marcasite"],
        "black_metallic": ["galena", "magnetite", "hematite", "graphite"],
    }
    
    def identify(
        self,
        photo_analysis: Dict,  # CLIP/VLM result
        physical: Optional[PhysicalProperties] = None,
        xrf: Optional[XRFResult] = None,
        location: Optional[LocationContext] = None,
        user_description: Optional[str] = None
    ) -> MineralIDResult:
        """
        Multi-modal identification workflow:
        1. Start with photo analysis
        2. Check if it's a look-alike group
        3. If look-alike, REQUIRE physical tests
        4. If XRF available, use as primary ID
        5. Combine all evidence with location context
        """
        
        # Step 1: Photo analysis result
        photo_mineral = photo_analysis.get("top_prediction")
        photo_confidence = photo_analysis.get("confidence", 0)
        
        # Step 2: Check if this is a look-alike situation
        is_look_alike = self._check_look_alike(photo_mineral, photo_confidence)
        
        if is_look_alike and physical is None and xrf is None:
            # CRITICAL: Cannot ID look-alike from photo alone
            return MineralIDResult(
                primary_id="UNKNOWN - Requires physical tests",
                confidence=ConfidenceLevel.VERY_LOW,
                alternative_ids=[
                    {"mineral": m, "probability": 1.0/len(group)}
                    for group in self.LOOK_ALIKES.values()
                    if photo_mineral in group
                    for m in group
                ],
                evidence={"photo_only": True, "warning": "Look-alike minerals detected"},
                requires_lab_confirmation=True,
                notes=(
                    f"Photo suggests '{photo_mineral}' but this is a look-alike group. "
                    f"REQUIRED: Streak test (unglazed tile), hardness test, "
                    f"specific gravity measurement, or portable XRF analysis. "
                    f"DO NOT make decisions based on photo alone."
                )
            )
        
        # Step 3: XRF definitive identification
        if xrf:
            xrf_result = self._identify_from_xrf(xrf)
            if xrf_result["confidence"] == "definitive":
                return MineralIDResult(
                    primary_id=xrf_result["mineral"],
                    confidence=ConfidenceLevel.DEFINITIVE,
                    alternative_ids=[],
                    evidence={"xrf": xrf.elements, "photo_agrees": photo_mineral == xrf_result["mineral"]},
                    requires_lab_confirmation=False,
                    notes=f"XRF definitive identification. Elements: {xrf.elements}"
                )
        
        # Step 4: Physical tests identification
        if physical:
            phys_result = self._identify_from_physical(physical)
            # Combine with photo
            combined = self._combine_evidence(photo_mineral, photo_confidence, phys_result, location)
            return combined
        
        # Step 5: Photo + location context only
        if location:
            return self._identify_with_context(photo_mineral, photo_confidence, location)
        
        # Step 6: Photo only (lowest confidence)
        return MineralIDResult(
            primary_id=photo_mineral,
            confidence=ConfidenceLevel.VERY_LOW,
            alternative_ids=photo_analysis.get("alternatives", []),
            evidence={"photo_confidence": photo_confidence},
            requires_lab_confirmation=True,
            notes="Photo-only identification. Add physical tests for reliable ID."
        )
    
    def _check_look_alike(self, mineral: str, confidence: float) -> bool:
        """Check if mineral is in a look-alike group with low confidence."""
        if confidence > 0.9:
            return False  # High confidence photo ID is probably OK
        for group in self.LOOK_ALIKES.values():
            if mineral.lower() in [m.lower() for m in group]:
                return True
        return False
    
    def _identify_from_xrf(self, xrf: XRFResult) -> Dict:
        """Identify mineral from XRF elemental data."""
        elements = xrf.elements
        
        # Gold: high Au
        if elements.get("Au", 0) > 1000:  # >1000 ppm = 0.1%
            return {"mineral": "gold", "confidence": "definitive"}
        
        # Pyrite: high Fe + S, no Au
        if elements.get("Fe", 0) > 30 and elements.get("S", 0) > 30:
            if elements.get("Cu", 0) < 1:
                return {"mineral": "pyrite", "confidence": "definitive"}
        
        # Chalcopyrite: Cu + Fe + S
        if elements.get("Cu", 0) > 20 and elements.get("Fe", 0) > 20:
            return {"mineral": "chalcopyrite", "confidence": "definitive"}
        
        # Galena: high Pb + S
        if elements.get("Pb", 0) > 50:
            return {"mineral": "galena", "confidence": "definitive"}
        
        # Sphalerite: high Zn + S
        if elements.get("Zn", 0) > 40:
            return {"mineral": "sphalerite", "confidence": "definitive"}
        
        # Quartz: high Si, nothing else significant
        if elements.get("Si", 0) > 40 and sum(v for k, v in elements.items() if k != "Si") < 5:
            return {"mineral": "quartz", "confidence": "high"}
        
        # Calcite: high Ca
        if elements.get("Ca", 0) > 30:
            return {"mineral": "calcite", "confidence": "high"}
        
        return {"mineral": "unknown", "confidence": "low", "elements": elements}
    
    def _identify_from_physical(self, p: PhysicalProperties) -> Dict:
        """Identify from physical properties using decision tree."""
        results = []
        
        # Streak test is most diagnostic for metallic minerals
        if p.streak_color:
            if p.streak_color == "yellow":
                results.append({"mineral": "gold", "confidence": 0.95, "evidence": "yellow streak"})
            elif p.streak_color == "black":
                results.append({"mineral": "pyrite", "confidence": 0.7, "evidence": "black streak"})
            elif p.streak_color == "greenish-black":
                results.append({"mineral": "chalcopyrite", "confidence": 0.8, "evidence": "greenish-black streak"})
        
        # Hardness
        if p.hardness_mohs is not None:
            if p.hardness_mohs <= 3:
                results.append({"mineral": "calcite", "confidence": 0.6, "evidence": "soft (H=3)"})
            elif p.hardness_mohs >= 6:
                results.append({"mineral": "quartz", "confidence": 0.6, "evidence": "hard (H=7)"})
        
        # Specific gravity
        if p.specific_gravity:
            if p.specific_gravity > 15:
                results.append({"mineral": "gold", "confidence": 0.95, "evidence": f"SG={p.specific_gravity}"})
            elif 4.5 < p.specific_gravity < 5.5:
                results.append({"mineral": "pyrite", "confidence": 0.7, "evidence": f"SG={p.specific_gravity}"})
        
        # Acid test
        if p.acid_reaction is True:
            results.append({"mineral": "calcite", "confidence": 0.9, "evidence": "fizzes with HCl"})
        
        return {"candidates": results}
    
    def _combine_evidence(self, photo, photo_conf, physical, location) -> MineralIDResult:
        """Combine all evidence sources into a final ID."""
        # Weight: XRF > physical tests > location > photo
        # Implementation: Bayesian-style combination
        pass
    
    def _identify_with_context(self, photo, conf, location) -> MineralIDResult:
        """Use geological context to refine photo ID."""
        # If we know the geological unit, we can narrow possibilities
        # E.g., in Migori greenstone: gold, pyrite, chalcopyrite are expected
        # Calcite and quartz are common but not economically significant
        pass
```

#### 4.5 Required Equipment for Field Kit

| Item | Cost (USD) | Purpose | Priority |
|------|-----------|---------|----------|
| Mohs hardness kit | $15 | Mineral hardness | REQUIRED |
| Unglazed porcelain tile | $1 | Streak test | REQUIRED |
| Dilute HCl dropper | $10 | Acid test (calcite) | REQUIRED |
| Digital scale (0.01g) | $25 | Specific gravity | REQUIRED |
| Rare earth magnet | $5 | Magnetism test | REQUIRED |
| Hand lens (10x) | $15 | Crystal observation | REQUIRED |
| UV lamp (365nm) | $20 | Fluorescence | RECOMMENDED |
| **Portable XRF** | **$15,000-40,000** | **Elemental analysis** | **STRONGLY RECOMMENDED** |
| Reference mineral set | $50 | Comparison specimens | RECOMMENDED |

**Minimum field kit cost:** ~$90  
**Professional field kit with XRF:** ~$15,000-40,000

---

## Problem 5: No Human-in-the-Loop for Critical Decisions

### Current State
No approval workflow. AI outputs are treated as final decisions.

### Solution: Human-in-the-Loop (HITL) Framework

#### 5.1 Decision Classification

| Decision Type | Risk Level | Auto-Approve? | Human Required? |
|--------------|-----------|---------------|-----------------|
| Mineral ID from photo | LOW | Yes (with confidence flag) | Only if confidence < 0.7 |
| Mineral ID with XRF | LOW | Yes | No |
| Land valuation estimate | MEDIUM | No | Yes — licensed valuer |
| Purchase recommendation | **HIGH** | **NEVER** | **Yes — owner + legal** |
| Mining licence application | **HIGH** | **NEVER** | **Yes — lawyer + owner** |
| Environmental assessment | **HIGH** | **NEVER** | **Yes — environmental consultant** |
| Financial investment | **CRITICAL** | **NEVER** | **Yes — owner + financial advisor** |
| Community agreement | **CRITICAL** | **NEVER** | **Yes — owner + community leaders** |
| Water quality alert | MEDIUM | No | Yes — health officer |
| Safety hazard alert | MEDIUM | Auto-notify | Yes — safety officer |

#### 5.2 Confidence Thresholds

```python
# core/hitl.py
"""
Human-in-the-Loop framework for critical decisions.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Any, Callable
from datetime import datetime
import json

class DecisionRisk(Enum):
    LOW = "low"           # Auto-approve possible
    MEDIUM = "medium"     # Single human reviewer
    HIGH = "high"         # Multiple reviewers required
    CRITICAL = "critical" # Senior approval + documentation

class ApprovalStatus(Enum):
    PENDING = "pending"
    AUTO_APPROVED = "auto_approved"
    HUMAN_APPROVED = "human_approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    EXPIRED = "expired"

@dataclass
class Decision:
    decision_id: str
    decision_type: str
    risk_level: DecisionRisk
    description: str
    data: dict  # Supporting data
    confidence: float  # 0-1
    auto_approve_threshold: float  # Minimum confidence for auto-approve
    required_approvers: list  # Roles that must approve
    created_at: datetime
    expires_at: Optional[datetime] = None
    status: ApprovalStatus = ApprovalStatus.PENDING
    approvers_completed: list = None
    approval_notes: str = None

class HITLFramework:
    """
    Human-in-the-Loop decision framework.
    Routes decisions to appropriate reviewers based on risk level.
    """
    
    # Confidence thresholds for auto-approval
    AUTO_APPROVE_THRESHOLDS = {
        "mineral_id_visual": 0.90,      # Very high confidence for photo-only
        "mineral_id_with_tests": 0.80,   # Good confidence with physical tests
        "mineral_id_xrf": 0.95,          # Almost always auto-approve with XRF
        "geochemical_anomaly": 0.70,     # Flag for review if uncertain
        "satellite_analysis": 0.85,       # Auto-approve cloud-free analysis
    }
    
    # Required approvers by decision type
    REQUIRED_APPROVERS = {
        "land_purchase": ["owner", "legal_counsel", "geologist"],
        "mining_licence": ["owner", "legal_counsel", "environmental_officer"],
        "financial_investment": ["owner", "financial_advisor"],
        "community_agreement": ["owner", "community_liaison", "legal_counsel"],
        "environmental_action": ["environmental_officer", "geologist"],
        "safety_action": ["safety_officer", "site_manager"],
        "mineral_id_economic": ["geologist"],  # ID that triggers economic action
    }
    
    # Escalation rules
    ESCALATION_RULES = {
        DecisionRisk.LOW: {"timeout_hours": 72, "escalate_to": None},
        DecisionRisk.MEDIUM: {"timeout_hours": 48, "escalate_to": "site_manager"},
        DecisionRisk.HIGH: {"timeout_hours": 24, "escalate_to": "owner"},
        DecisionRisk.CRITICAL: {"timeout_hours": 12, "escalate_to": "board"},
    }
    
    def submit_decision(self, decision: Decision) -> Decision:
        """Submit a decision for approval."""
        # Check if auto-approve is possible
        if self._can_auto_approve(decision):
            decision.status = ApprovalStatus.AUTO_APPROVED
            decision.approval_notes = (
                f"Auto-approved: confidence {decision.confidence:.2f} "
                f"exceeds threshold {decision.auto_approve_threshold:.2f}"
            )
            self._log_decision(decision, "auto_approved")
            return decision
        
        # Route to human reviewers
        decision.status = ApprovalStatus.PENDING
        self._route_to_reviewers(decision)
        self._log_decision(decision, "submitted_for_review")
        return decision
    
    def _can_auto_approve(self, decision: Decision) -> bool:
        """Check if decision meets auto-approve criteria."""
        # NEVER auto-approve high/critical risk
        if decision.risk_level in (DecisionRisk.HIGH, DecisionRisk.CRITICAL):
            return False
        
        # Check confidence threshold
        if decision.confidence < decision.auto_approve_threshold:
            return False
        
        # Additional safety checks
        if decision.decision_type == "mineral_id_economic":
            # Mineral ID that triggers economic action always needs review
            # unless XRF-confirmed with confidence > 0.95
            if decision.confidence < 0.95:
                return False
        
        return True
    
    def _route_to_reviewers(self, decision: Decision):
        """Route decision to appropriate reviewers."""
        required = self.REQUIRED_APPROVERS.get(
            decision.decision_type, 
            ["owner"]  # Default: owner must review
        )
        decision.required_approvers = required
        decision.approvers_completed = []
        
        # In production: send notifications via email/SMS/WhatsApp
        for approver_role in required:
            self._send_notification(
                approver_role,
                f"Decision pending your approval: {decision.description}",
                decision
            )
    
    def approve_decision(
        self, 
        decision_id: str, 
        approver_role: str,
        approved: bool,
        notes: str = ""
    ) -> Decision:
        """Record an approval or rejection."""
        decision = self._get_decision(decision_id)
        
        if not approved:
            decision.status = ApprovalStatus.REJECTED
            decision.approval_notes = f"Rejected by {approver_role}: {notes}"
            self._log_decision(decision, "rejected")
            return decision
        
        decision.approvers_completed.append({
            "role": approver_role,
            "timestamp": datetime.now().isoformat(),
            "notes": notes
        })
        
        # Check if all required approvers have approved
        remaining = set(decision.required_approvers) - set(
            a["role"] for a in decision.approvers_completed
        )
        
        if not remaining:
            decision.status = ApprovalStatus.HUMAN_APPROVED
            decision.approval_notes = f"Approved by all required reviewers"
            self._log_decision(decision, "approved")
        else:
            decision.status = ApprovalStatus.PENDING
            self._log_decision(decision, f"partial_approval_{approver_role}")
        
        return decision
    
    def check_escalations(self):
        """Check for decisions that have timed out and need escalation."""
        pending = self._get_pending_decisions()
        for decision in pending:
            rule = self.ESCALATION_RULES[decision.risk_level]
            age_hours = (datetime.now() - decision.created_at).total_seconds() / 3600
            
            if age_hours > rule["timeout_hours"]:
                decision.status = ApprovalStatus.ESCALATED
                self._send_notification(
                    rule["escalate_to"],
                    f"ESCALATION: Decision {decision.decision_id} has been pending for {age_hours:.0f} hours",
                    decision
                )
                self._log_decision(decision, "escalated")
    
    def _log_decision(self, decision: Decision, action: str):
        """Audit log for all decisions."""
        log_entry = {
            "decision_id": decision.decision_id,
            "type": decision.decision_type,
            "risk": decision.risk_level.value,
            "action": action,
            "confidence": decision.confidence,
            "status": decision.status.value,
            "timestamp": datetime.now().isoformat(),
            "approvers": decision.approvers_completed
        }
        # Write to append-only audit log
        with open("logs/decisions.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    
    def _send_notification(self, role: str, message: str, decision: Decision):
        """Send notification to reviewer. In production: WhatsApp/SMS/Email."""
        # Implementation depends on communication channel
        print(f"NOTIFY [{role}]: {message}")
    
    def _get_decision(self, decision_id: str) -> Decision:
        """Retrieve decision from database."""
        # Implementation: query PostgreSQL
        pass
    
    def _get_pending_decisions(self) -> list:
        """Get all pending decisions."""
        # Implementation: query PostgreSQL
        pass
```

#### 5.3 Escalation Procedure

```
DECISION ESCALATION FLOW
==========================

┌─────────────────────────────────────────────────────┐
│  Decision submitted                                  │
│  ┌───────────────┐                                  │
│  │ Risk: LOW      │ → Auto-approve if confidence    │
│  │               │   > threshold                    │
│  └───────────────┘   → 72h timeout → escalate       │
│                                                       │
│  ┌───────────────┐                                  │
│  │ Risk: MEDIUM   │ → Single reviewer               │
│  │               │ → 48h timeout → escalate to       │
│  └───────────────┘   site manager                   │
│                                                       │
│  ┌───────────────┐                                  │
│  │ Risk: HIGH     │ → Multiple reviewers required    │
│  │               │ → 24h timeout → escalate to       │
│  └───────────────┘   owner                          │
│                                                       │
│  ┌───────────────┐                                  │
│  │ Risk: CRITICAL │ → Senior approval required       │
│  │               │ → 12h timeout → escalate to       │
│  └───────────────┘   board/advisor                   │
│                                                       │
│  ALL DECISIONS → Audit log (append-only)             │
│  ALL DECISIONS → Owner notification                  │
└─────────────────────────────────────────────────────┘
```

#### 5.4 Specific Approval Workflows

**Land Purchase Decision:**
```
1. AI identifies mineral potential of a plot
2. → Decision submitted (HIGH risk)
3. → Required: geologist reviews mineral assessment
4. → Required: legal_counsel reviews title, zoning, mineral rights
5. → Required: owner reviews financial terms
6. → ALL THREE must approve → Decision recorded
7. → If any reject → Decision blocked, reasons documented
8. → 24h timeout → Escalate to owner directly
```

**Mineral ID Triggering Economic Action:**
```
1. Photo analysis suggests gold (confidence: 0.72)
2. → LOW confidence → Cannot auto-approve
3. → Decision submitted (MEDIUM risk)
4. → Required: geologist reviews
5. → Geologist requests: "Do streak test"
6. → Streak test: yellow streak → gold confirmed
7. → Updated confidence: 0.95 → Auto-approve for ID
8. → BUT: any economic action (land offer, investment) 
     still requires owner + legal approval (HIGH risk)
```

#### 5.5 Notification Integration

```python
# core/notifications.py
"""
Notification system for HITL decisions.
Integrates with WhatsApp/Telegram/SMS.
"""

class Notifier:
    def notify_owner(self, decision: Decision, channel: str = "whatsapp"):
        """Send decision notification to owner."""
        message = self._format_decision_message(decision)
        # Use existing WhatsApp/Telegram integration
        if channel == "whatsapp":
            self._send_whatsapp(OWNER_PHONE, message)
        elif channel == "telegram":
            self._send_telegram(OWNER_TELEGRAM_ID, message)
    
    def _format_decision_message(self, d: Decision) -> str:
        return (
            f"🔔 DECISION REQUIRES YOUR APPROVAL\n\n"
            f"Type: {d.decision_type}\n"
            f"Risk: {d.risk_level.value.upper()}\n"
            f"Description: {d.description}\n"
            f"Confidence: {d.confidence:.0%}\n\n"
            f"Supporting data:\n{json.dumps(d.data, indent=2)}\n\n"
            f"Reply APPROVE or REJECT with comments."
        )
```

---

## Summary: Implementation Priority

| Priority | Problem | Solution | Effort | Cost |
|----------|---------|----------|--------|------|
| 🔴 P0 | Hardcoded geology DB | PostGIS + open data imports | 3-6 weeks | $0 |
| 🔴 P0 | Wrong Luo translations | 3-tier i18n + native review | 2-3 weeks | $200-500 |
| 🟡 P1 | No error handling | Retry + degradation + offline | 2-3 weeks | $0 |
| 🟡 P1 | CLIP mineral confusion | Multi-modal ID + field tests | 2-4 weeks | $90-40k |
| 🔴 P0 | No human-in-the-loop | HITL framework + approvals | 1-2 weeks | $0 |

**Minimum viable fix (P0 items):** ~6-10 weeks, $200-500  
**Full fix (all items):** ~10-16 weeks, $200-40,500 (depends on XRF budget)

---

*Document prepared: 2026-07-25*  
*Sources: BGS OpenGeoscience, USGS MRDATA, Mindat.org API documentation, research/05_migori_geology.md, i18n best practices, HITL design patterns.*
