# Free Mineral Detection Methods — Zero Budget Exploration Guide

**For Valentine's Land in Migori, Kenya**
**Cost: KES 0 (or near-zero) | Last Updated: July 2026**

---

## Table of Contents

1. [AI-Based Mineral Detection from Photos](#1-ai-based-mineral-detection-from-photos)
2. [DIY Spectroscopy](#2-diy-spectroscopy)
3. [Smartphone Sensors for Geology](#3-smartphone-sensors-for-geology)
4. [Free Satellite Analysis](#4-free-satellite-analysis)
5. [Free Geophysical Methods](#5-free-geophysical-methods)
6. [Free Online Mineral Databases](#6-free-online-mineral-databases)
7. [Biological Indicators](#7-biological-indicators)
8. [Community Knowledge & Historical Records](#8-community-knowledge--historical-records)
9. [Free Machine Learning for Mineral Estimation](#9-free-machine-learning-for-mineral-estimation)
10. [The Zero Budget Exploration Protocol](#10-the-zero-budget-exploration-protocol)

---

## 1. AI-Based Mineral Detection from Photos

### 1.1 Free Rock/Mineral Identification Apps

| App | Platform | Free Features | Accuracy |
|-----|----------|---------------|----------|
| **Stone Identifier Rock Scanner** | Android/iOS | Full ID free, no paywall | Best free option (ranked #1 by rockhounding.org, 2026) |
| **Rock Identifier by Photo** (Negroni) | Android | Free mineral ID from photos | Good for common minerals |
| **Rock Identifier: Stone ID** (PictureRock) | Android/iOS | Basic ID free, premium for details | Decent for common rocks |
| **Geology Toolkit** | Android | Full field toolkit | Best for professionals |
| **Mindat.org Photo ID** | Web browser | Free community-based ID | Expert-verified, very accurate |

**How to use for maximum accuracy:**
- Photograph in natural daylight (no flash)
- Include a coin or ruler for scale
- Photograph fresh/broken surface (not weathered)
- Capture multiple angles
- Note hardness (can you scratch it with a knife? a fingernail?)
- Note streak color (scratch on unglazed porcelain — a ceramic tile or toilet tank lid works)

### 1.2 Free AI Models on HuggingFace for Mineral Classification

**Ready-to-use models:**
- Search HuggingFace for "mineral classification" or "rock identification"
- Many pre-trained image classification models exist trained on geological datasets
- Use the HuggingFace Inference API (free tier) to classify mineral photos

**How to use (no coding required):**
1. Go to huggingface.co/models
2. Search for "mineral" or "geology" image classification
3. Upload your photo via the web interface
4. Get instant classification

**Build your own classifier (free):**
- Dataset: Search HuggingFace for mineral image datasets (e.g., "mineral thin section", "rock classification")
- Use Google Colab (free GPU) to train a model
- Framework: PyTorch or TensorFlow (both free)
- Architecture: ResNet, EfficientNet (pre-trained, fine-tune on minerals)
- Training time: ~30 minutes on free Colab GPU

### 1.3 Using General Vision AI for Mineral ID

You can also use free multimodal AI (like ChatGPT with image upload, Google Gemini, or open-source models) to identify minerals from photos:
- Upload a clear photo
- Ask: "What mineral is this? Consider: color, luster, crystal habit, hardness, associated minerals"
- Cross-reference with physical tests (streak, hardness)

**Limitations:** AI photo ID alone is NOT definitive. Always cross-reference with physical properties (streak, hardness, specific gravity) and geological context.

---

## 2. DIY Spectroscopy

### 2.1 Build a Smartphone Spectrometer from a DVD/CD

**Cost: Nearly free (old CD/DVD + cardboard + tape)**

**How it works:** A CD or DVD acts as a diffraction grating, splitting light into its component wavelengths. Each mineral reflects/absorbs light differently, creating a unique spectral "fingerprint."

**Materials needed (all free/already available):**
- 1 old CD or DVD (broken ones work)
- Cardboard (from any box)
- Black tape or dark cloth
- Razor blade or sharp knife
- Smartphone with camera

**Build instructions:**
1. Cut a small piece of DVD (the diffraction grating part — the shiny data side)
2. Cut a cardboard box to create a light-tight chamber
3. Make a narrow slit (~1mm wide) on one end for light entry
4. Mount the DVD piece at a 45° angle inside the box
5. Cut a viewing hole for the smartphone camera on the opposite end
6. Seal all gaps with black tape so only the slit lets light in

**How to use:**
1. Point the slit at a light source reflected off the mineral sample
2. Take a photo through the viewing hole
3. You'll see a spectrum (rainbow) with dark absorption bands
4. Compare the absorption bands to known mineral spectra

**Free spectral analysis software:**
- **ImageJ/FIJI** (free, open-source) — analyze spectral images
- **RSpec Explorer** (free version) — astronomical spectral analysis
- **VisualSpec** (free) — spectral analysis software
- **Spectroid** (Android, free) — real-time spectrum analyzer
- **Phyphox** (Android/iOS, free) — physics toolbox with spectral analysis

### 2.2 Smartphone Camera as Basic Spectrometer

**Without building anything:**
1. Download **Spectroid** (Android) or **Phyphox** (both free)
2. Use the phone's camera to capture reflected light from minerals
3. The app displays the spectral profile
4. Compare absorption features to known mineral spectra

**What to look for:**
- **Iron oxides** (hematite, goethite): Strong absorption in visible range, red/yellow colors
- **Copper minerals** (malachite, azurite): Green/blue absorption features
- **Gold**: High reflectance across visible spectrum, no absorption features
- **Quartz**: Transparent in visible, strong absorption in SWIR (~2200nm — beyond phone range)

**Limitations:** Smartphone cameras detect visible light (400-700nm). Many mineral diagnostic features are in SWIR (1000-2500nm), which requires specialized sensors. But visible spectroscopy can still distinguish many common minerals.

### 2.3 UV Fluorescence Detection (Free if you have a UV light)

Some minerals fluoresce under ultraviolet light:
- **Fluorite**: Purple/blue/white
- **Calcite**: Red/pink/orange
- **Willemite**: Green
- **Scheelite**: Blue-white (associated with tungsten deposits)

If you have a UV flashlight (even a cheap one), this is a powerful free field test.

---

## 3. Smartphone Sensors for Geology

### 3.1 Phone Magnetometer — Detecting Magnetic Minerals

**What it detects:** Magnetite, pyrrhotite, and other magnetic minerals. Magnetic anomalies can indicate subsurface geological structures, ore bodies, or structural features that control mineralization.

**Free apps:**
- **Physics Toolbox Magnetometer** (Android/iOS, free) — real-time magnetic field readings
- **Phyphox** (Android/iOS, free) — advanced magnetometer with data logging
- **Metal Detector - Gold Finder** (Android, free) — basic magnetic detection

**How to use for mineral exploration:**
1. Download Physics Toolbox Magnetometer
2. Hold phone flat, screen up
3. Walk a grid pattern over the area (e.g., every 10 meters)
4. Record the total magnetic field (in μT) at each point
5. Note any sudden spikes or anomalies
6. Map the readings — anomalies may indicate magnetic mineral concentrations

**What the readings mean:**
- Earth's background field in Kenya: ~30-40 μT
- Anomalies >5 μT above background: possible magnetic mineral concentration
- Strong anomalies (>20 μT above): likely magnetite-rich rock or metallic object
- Negative anomalies: may indicate demagnetized zone or different rock type

**Limitations:** Phone magnetometers are low-resolution (~0.1-1 μT sensitivity). Professional instruments have 0.001 nT sensitivity. But phone surveys can identify large, shallow anomalies.

### 3.2 Phone Accelerometer — Density/Weight Detection

**What it can detect:** Subtle changes in terrain that may indicate geological structures.

**Free apps:**
- **Phyphox** (free) — accelerometer with data logging
- **Physics Toolbox Sensor Suite** (free) — all phone sensors

**Applications:**
- Drop test: Drop a known weight onto soil; harder impact = more compact/different substrate
- Walking survey: Accelerometer data changes when walking over different substrates
- Not directly useful for mineral detection, but can indicate geological boundaries

### 3.3 Phone GPS — Geotagging Samples

**Essential for all exploration. Free and built into every smartphone.**

**How to use:**
1. Download **Google Maps** or **OsmAnd** (free, works offline)
2. At each sample point, record GPS coordinates
3. Take photos (automatically geotagged)
4. Create a sample map

**Free mapping apps:**
- **Google My Maps** (free) — create custom geological maps
- **QField** (free, open-source) — professional field data collection
- **ODK Collect** (free) — customizable field forms
- **Avenza Maps** (free tier) — geospatial PDF maps

### 3.4 LiDAR on Newer Phones (iPhone Pro, iPad Pro)

**If you have an iPhone 12 Pro or newer:**
- The LiDAR scanner can create 3D terrain models
- Free apps: **3D Scanner App**, **Polycam** (free tier), **Scaniverse** (free)
- Use for: mapping outcrop geometry, measuring vein orientations, creating terrain models
- Can detect subtle terrain features not visible to the naked eye

---

## 4. Free Satellite Analysis

### 4.1 Sentinel-2 Data (European Space Agency)

**Completely free, 13 spectral bands, 10m resolution**

**Key mineral detection band combinations:**
| Purpose | Band Combination (RGB) |
|---------|----------------------|
| Geology | B12, B4, B2 |
| Natural Color | B4, B3, B2 |
| Vegetation Stress (alteration) | B8, B4, B3 |
| Iron Oxide Detection | B4, B3, B2 (enhanced) |
| Clay/Alteration Minerals | B11, B8A, B4 |
| Regolith Ratio | B11/B12, B8A/B12, B8A/B3 |

**How to access (free):**
1. Register at **Copernicus Open Access Hub** (scihub.copernicus.eu) — free
2. Or use **Google Earth Engine** (earthengine.google.com) — free, no download needed
3. Or use **QGIS with Semi-Automatic Classification Plugin** (SCP) — free

**Step-by-step with QGIS (all free):**
1. Download QGIS (free, open-source): qgis.org
2. Install the SCP plugin (free)
3. Register at USGS EarthExplorer (free) or ESA Copernicus Hub (free)
4. Search for Sentinel-2 or ASTER imagery over Migori, Kenya
5. Download and process using band ratios

**Free QGIS tutorial for mineral exploration:**
- https://qgis-in-mineral-exploration.readthedocs.io/
- Complete step-by-step guide with video tutorials

### 4.2 ASTER Data (Advanced Spaceborne Thermal Emission and Reflection Radiometer)

**Free, 14 bands, specifically designed for mineral mapping**

**Critical note:** ASTER SWIR sensor (bands 4-9) became inoperable April 1, 2008. Only pre-2008 data is useful for mineral mapping. But TIR bands (10-14) still work for lithological mapping.

**ASTER Mineral Indices (Ninomiya, 2004):**
- **OH Minerals Index**: (Band7/Band6) × (Band4/Band6)
- **Kaolinite Index**: Band4/Band5 × Band8/Band6
- **Alunite Index**: Band7/Band5 × Band7/Band8
- **Calcite Index**: Band6/Band8 × Band9/Band8

**Key band ratios for mineral exploration:**
- **Ratio 4/7 (Red), 4/3 (Green), 2/1 (Blue)**: General geological discrimination — works well in most situations
- **AlOH/Advanced Argillic**: Detects alteration associated with porphyry copper mineralization
- **Alunite-Kaolinite-Pyrophyllite**: Enhanced for hydrothermal alteration
- **Abrams Ratio**: 5/7, 4/5, 3/1 in RGB

**How to access:**
1. Register at USGS EarthExplorer (earthexplorer.usgs.gov) — free
2. Search for ASTER L1T data over Migori County, Kenya
3. Download and process in QGIS with SCP plugin

### 4.3 Google Earth Engine (Free Cloud-Based Analysis)

**No software installation needed — runs in your browser**

**What you can do:**
- Access Sentinel-2, Landsat, ASTER data (all free)
- Calculate mineral indices (NDVI, clay indices, iron oxide indices)
- Perform time-series analysis (detect changes over time)
- Export processed images

**How to start:**
1. Go to earthengine.google.com
2. Sign in with Google account (free)
3. Request access (usually approved within 24-48 hours)
4. Use the JavaScript or Python API
5. Tutorials available at: developers.google.com/earth-engine

**Example code for mineral exploration:**
```javascript
// Load Sentinel-2 imagery over Migori
var s2 = ee.ImageCollection('COPERNICUS/S2_SR')
  .filterBounds(ee.Geometry.Point(34.47, -1.06)) // Migori coordinates
  .filterDate('2024-01-01', '2024-12-31')
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
  .median();

// Calculate clay mineral index (B11/B12)
var clayIndex = s2.normalizedDifference(['B11', 'B12']);

// Calculate iron oxide index (B4/B3)
var ironIndex = s2.normalizedDifference(['B4', 'B3']);

// Display
Map.addLayer(clayIndex, {min: -0.5, max: 0.5, palette: ['blue', 'white', 'red']}, 'Clay Index');
Map.addLayer(ironIndex, {min: -0.5, max: 0.5, palette: ['blue', 'white', 'yellow']}, 'Iron Oxide Index');
```

### 4.4 Landsat Data (USGS)

**Free, 30m resolution, continuous coverage since 1972**

**Band ratios for mineral mapping:**
- **Band 5/7**: Detects clay minerals (Al-OH absorption)
- **Band 3/1**: Detects iron oxides
- **Band 4/5**: Ferrous iron minerals

**Access:** USGS EarthExplorer (earthexplorer.usgs.gov) — free registration required

---

## 5. Free Geophysical Methods

### 5.1 DIY Magnetic Survey with Smartphone

**Equipment needed:** Just your smartphone (with magnetometer)

**Step-by-step survey protocol:**
1. Download **Physics Toolbox Magnetometer** or **Phyphox**
2. Create a grid over your 5-hectare area:
   - Mark lines every 25 meters (N-S)
   - Take readings every 10 meters along each line
3. At each point:
   - Hold phone flat, screen up
   - Record total magnetic field (μT)
   - Record GPS coordinates
   - Note any readings that spike
4. Enter data into a spreadsheet (Google Sheets — free)
5. Create a contour map of magnetic values

**What magnetic anomalies may indicate:**
- **Positive anomaly (high μT)**: Magnetite-rich rocks, possible iron ore, or magnetic minerals associated with gold
- **Negative anomaly (low μT)**: Demagnetized zone, possibly altered rock (hydrothermal alteration often destroys magnetite)
- **Linear anomalies**: May indicate faults or geological contacts — important structural controls for mineralization

**In Migori specifically:** The Migori Gold Belt is associated with sheared metavolcanic and metasedimentary rocks. Magnetic surveys can detect the structural features (shear zones, faults) that control gold mineralization.

### 5.2 DIY Gravity Survey (Conceptual)

**Principle:** Denser rocks (like those containing metallic minerals) exert slightly stronger gravitational pull.

**Free method (very approximate):**
1. Use smartphone barometer (if available) to measure atmospheric pressure at different points
2. Not a true gravity survey, but pressure variations can indicate elevation changes
3. For a proper gravity survey, you'd need a gravimeter ($$$)

**Alternative — Density estimation from hand samples:**
1. Collect rock samples from each grid point
2. Weigh them (use a kitchen scale if available)
3. Measure volume by water displacement (fill a cup, submerge sample, measure water rise)
4. Calculate density = mass/volume
5. Map density variations — denser samples may indicate metallic mineral content

### 5.3 Free Geophysical Software

**SimPEG (Simulation and Parameter Estimation in Geophysics)**
- Website: simpeg.xyz
- GitHub: github.com/simpeg/simpeg
- Capabilities: Gravity, magnetics, DC resistivity, IP, electromagnetics
- Free, open-source Python package
- Install: `pip install simpeg`
- Tutorials available at: simpeg.xyz/user-tutorials

**Fatiando a Terra**
- Website: fatiando.org
- GitHub: github.com/fatiando
- Capabilities: Gravity, magnetics, seismology, geothermal
- Free, open-source Python package
- Install: `pip install fatiando`

**How to use SimPEG for magnetic data:**
1. Collect magnetic data with smartphone (as described above)
2. Install SimPEG: `pip install simpeg`
3. Import your data (GPS coordinates + magnetic readings)
4. Run 3D magnetic inversion to find subsurface sources
5. Visualize the results

**Example Python code:**
```python
import numpy as np
import simpeg.potential_fields as pf

# Your smartphone magnetic data
locations = np.array([[x1, y1, z1], [x2, y2, z2], ...])  # GPS + elevation
magnetic_data = np.array([B1, B2, B3, ...])  # Your readings in μT

# Create inversion mesh and run
# (See SimPEG tutorials for complete workflow)
```

### 5.4 Free Resistivity Survey (DIY)

**Principle:** Different minerals and rocks have different electrical resistivities. Metallic minerals are highly conductive (low resistivity).

**DIY method (very basic):**
1. Get 4 metal rods (rebar, tent stakes — free if you have them)
2. Connect them with wire
3. Use a 9V battery as current source
4. Measure voltage drop with a multimeter (borrow or ~KES 500)
5. Calculate apparent resistivity

**Free software for resistivity inversion:**
- **Resistivity Inversion with SimPEG**: `pip install simpeg`
- **Bert** (Boundless Electrical Resistivity Tomography): free, open-source

---

## 6. Free Online Mineral Databases

### 6.1 Mindat.org — The World's Mineral Database

**URL:** mindat.org — completely free

**What it offers for Migori, Kenya:**
- Mineral occurrence database for Kenya
- Maps of known mineral localities
- Photos of minerals from the region
- Geological information for specific localities

**How to use:**
1. Go to mindat.org
2. Search for "Migori" or "Kenya"
3. View mineral occurrences in the area
4. Check what minerals have been found nearby
5. Look at photos for comparison with your samples

**Specific data for Migori:**
- Gold occurrences documented
- Macalder mine area (copper-gold)
- Historical mining data

### 6.2 USGS Mineral Resources Data

**URL:** mrdata.usgs.gov — free

**What's available:**
- MRDS (Mineral Resources Data System): worldwide mineral occurrences
- MAS/MILS: mineral industry data
- Searchable by location (Kenya/Migori)

**How to access:**
1. Go to mrdata.usgs.gov
2. Search for mineral occurrences in Kenya
3. Download data (free, no registration required)

### 6.3 Kenya Geological Survey

**What's available:**
- Geological maps of Kenya (some digitized, free online)
- Mineral occurrence records
- Mining license information

**How to access:**
- Kenya Ministry of Mining: mining.go.ke
- Geological maps may be available through the Mines & Geological Department
- Some maps digitized and available through BGS (British Geological Survey)

### 6.4 British Geological Survey (BGS) — East Africa Data

**URL:** bgs.ac.uk — some data free

**What's available:**
- GeoIndex: geological data for East Africa
- Historical geological maps of Kenya (colonial era)
- Mineral occurrence data
- Hydrogeology data

**Free resources:**
- BGS Earthwise: earthwise.bgs.ac.uk (Kenya geological information)
- BGS GeoIndex: bgs.ac.uk/data-and-services/data-access/geoindex
- Historical colonial geological reports (some digitized)

### 6.5 African Mineral Development Centre

- Geological data for African countries
- Mining cadastre information
- Some datasets freely available

### 6.6 OneGeology Portal

**URL:** portal.onegeology.org — free

- Global geological map viewer
- Geological maps from participating countries
- Includes Kenya geological data

---

## 7. Biological Indicators

### 7.1 Plants That Indicate Mineral Deposits (Geobotanical Prospecting)

**This is a REAL, scientifically validated method used by professional geologists.**

#### Gold Indicators:
- **Acacia/Thorn trees**: Often grow along shear zones (which host gold in Migori)
- **Euphorbia species**: Thrive in mineralized soils
- **Iron-stained vegetation**: Red/brown discoloration of leaves can indicate iron (and associated gold)
- **Stunted or abnormal growth**: Over mineralized zones, heavy metals can cause chlorosis (yellowing) or stunted growth
- **Sagebrush** (if present): Used as gold indicator plant in other regions

#### Copper Indicators:
- **Becium homblei** (formerly Ocimum homblei): Famous copper indicator plant in Central Africa (Zambia/Congo Copperbelt)
- **Copper-tolerant grasses**: Grasses that thrive in high-copper soils
- **Blue/green staining on rocks**: Copper minerals (malachite = green, azurite = blue)
- **Bare patches**: Copper toxicity can kill vegetation, creating "copper breaks"

#### General Mineral Indicators:
- **Vegetation anomalies**: Unusual plant communities in a small area
- **Color changes in leaves**: Heavy metals cause discoloration
- **Species distribution**: Certain plants only grow on specific rock types
- **Root depth**: Deep-rooted plants may access mineralized water

### 7.2 Soil Color and Texture Indicators

**Colors to look for:**
| Soil Color | Possible Minerals |
|------------|-------------------|
| **Red/Rust** | Iron oxides (hematite) — often associated with gold |
| **Yellow/Brown** | Iron hydroxides (goethite, limonite) — gossan indicator |
| **Green/Blue** | Copper minerals (malachite, azurite) |
| **Black** | Manganese oxides, magnetite |
| **White/Gray** | Silica (possible hydrothermal alteration) |
| **Purple/Red** | Manganese oxides |
| **Bright yellow** | Sulfur, jarosite (sulfide mineral indicator) |

**Gossan identification (critical for mineral exploration):**
A gossan is the oxidized, weathered cap of a sulfide mineral deposit. In Migori:
- Red/brown iron-stained soil
- Quartz fragments with iron staining
- Honeycomb textures (weathered sulfides leaving holes)
- Boxwork structures (iron oxide filling fractures)

### 7.3 Water Chemistry Indicators

**Free observations (no equipment needed):**
| Observation | Possible Indication |
|-------------|---------------------|
| **Orange/red precipitate** | Iron-rich water (near iron deposits) |
| **Blue/green staining** | Copper in water |
| **White precipitate** | Calcium carbonate (limestone) |
| **Black sediment** | Manganese or organic matter |
| **Metallic taste** | Dissolved metals |
| **Sulfur smell** | Sulfide minerals nearby |
| **pH < 5 (sour taste)** | Acidic — possible sulfide oxidation |
| **Oil sheen** | Hydrocarbons (unlikely in Migori) |
| **Turquoise color** | Copper sulfate |

**Free water testing:**
- **pH**: Litmus paper (very cheap, ~KES 100) or taste (sour = acidic)
- **TDS (Total Dissolved Solids)**: TDS meters are very cheap (~KES 300-500)
- **Color**: Visual observation
- **Smell**: Sulfur = sulfide minerals nearby

---

## 8. Community Knowledge & Historical Records

### 8.1 Local/Existing Knowledge

**Who to talk to:**
1. **Elderly residents**: They've lived on the land for decades, know what's under the surface
2. **Artisanal miners (local miners)**: The Migori area has active artisanal gold mining — these people have practical knowledge
3. **Well drillers**: Know the subsurface geology from drilling
4. **Farmers**: Know soil colors, what grows well, water table depth
5. **Previous landowners/tenants**: May know about past mining attempts

**Questions to ask:**
- Where have you seen colored rocks or soil?
- Where does water collect after rain? (low points may indicate geological structures)
- Have any wells been drilled? What was encountered?
- Are there any old mine shafts or trenches?
- Where do certain plants grow abundantly?
- Has anyone found unusual rocks or minerals?

### 8.2 Historical Mining Records (Free Online)

**Colonial-era records for Kenya:**
- **UK National Archives**: nationalarchives.gov.uk — search for "Kenya mining" or "Migori gold"
  - FCO 141 series: Colonial administration records including mines and geological surveys (1915-1939)
  - Many digitized, some free to view
- **British Online Archives**: britishonlinearchives.com
  - Kenya Under Colonial Rule, Government Reports 1907-1964
  - Mining & Geological Department reports
- **British Geological Survey (BGS)**: bgs.ac.uk
  - Historical geological maps of Kenya
  - Colonial-era mineral occurrence reports
  - NORA (NORA.nerc.ac.uk): Open-access research archive

**Specific Migori resources:**
- **Macalder Mine**: Well-documented colonial-era copper-gold mine
- **Migori Gold Belt**: Academic papers available on Google Scholar (many free)
- **Springer article**: "A Case Study in the Migori Gold Belt, Kenya" (link.springer.com)
- **BGS/NORA**: "Recovering the Lost Gold of the Developing World: Case Study in Migori, Kenya" — free PDF
- **Lyell Collection**: "Neoarchean Gold Grain Size and Artisanal Mining in Migori, Kenya" (2025)

### 8.3 Academic Papers (Many Free)

**Google Scholar (scholar.google.com) — search for:**
- "Migori gold belt geology"
- "Macalder mine Kenya"
- "Kenya mineral resources"
- "Nyanza series geology" (the geological formation in Migori)

**Free full-text sources:**
- Google Scholar (many papers have free PDFs)
- ResearchGate (request full text from authors)
- Academia.edu (many free papers)
- PubMed Central (for biogeochemistry papers)
- DOAJ (Directory of Open Access Journals)
- Preprints (arxiv.org, eartharxiv.org)

**Key papers for Migori geology:**
1. "Geology of the Migori Gold Belt" — geological survey reports
2. BGS studies on artisanal gold mining in Migori
3. University of Nairobi geology theses on the region
4. UN reports on artisanal mining in Kenya

---

## 9. Free Machine Learning for Mineral Estimation

### 9.1 Estimating Mineral Quantity from Surface Samples

**Free tools:**
- **Python** (free): numpy, pandas, scikit-learn, matplotlib
- **Google Colab** (free): Cloud-based Python with GPU
- **R** (free): Statistical computing

**Method:**
1. Collect surface samples at grid points
2. Weigh each sample
3. Visually estimate mineral percentage (or use AI photo analysis)
4. Enter data into spreadsheet
5. Use geostatistical methods to estimate total quantity

### 9.2 Geostatistical Estimation with Free Python Libraries

**PyKrige** (free, open-source):
- Install: `pip install pykrige`
- Kriging: Geostatistical interpolation method
- Estimate mineral grades between sample points
- Create grade maps

**scikit-learn** (free, open-source):
- Install: `pip install scikit-learn`
- Machine learning for mineral grade prediction
- Random forests, neural networks, SVM
- Cross-validation for accuracy estimation

**Example workflow:**
```python
import numpy as np
from pykrige.ok import OrdinaryKriging
import matplotlib.pyplot as plt

# Your sample data (GPS coordinates + mineral grade)
x = np.array([x1, x2, x3, ...])  # Easting
y = np.array([y1, y2, y3, ...])  # Northing
z = np.array([grade1, grade2, grade3, ...])  # Mineral grade/percentage

# Ordinary Kriging
OK = OrdinaryKriging(x, y, z, variogram_model='spherical')

# Predict on a grid
grid_x = np.linspace(min(x), max(x), 100)
grid_y = np.linspace(min(y), max(y), 100)
z_pred, ss = OK.execute('grid', grid_x, grid_y)

# Plot the estimated mineral grade map
plt.imshow(z_pred, origin='lower', extent=[min(x), max(x), min(y), max(y)])
plt.colorbar(label='Estimated Grade')
plt.title('Mineral Grade Estimation')
plt.savefig('mineral_grade_map.png')
```

**GStatSim** (free):
- GitHub: github.com/cgre-aachen/gstatsim
- Geostatistical simulation
- Conditional simulation for uncertainty estimation

**GSTools** (free):
- Install: `pip install gstools`
- Geostatistical tools for Python
- Variogram analysis, random field generation, kriging

### 9.3 Volume Estimation from Surface Data

**Method:**
1. Map surface mineral occurrences (outcrops, float, soil anomalies)
2. Estimate depth from geological reasoning (shear zone width, etc.)
3. Use the formula: Volume = Area × Average Depth × Mineralization Width
4. Apply a specific gravity factor for tonnage

**Free tools for 3D modeling:**
- **Blender** (free, open-source): 3D visualization
- **ParaView** (free): Scientific visualization
- **PyVista** (free): 3D plotting in Python

---

## 10. The Zero Budget Exploration Protocol

### Step-by-Step: Explore 5 Hectares with ZERO Budget

#### Phase 1: Desktop Study (Day 1-2, at home)

**Tools needed:** Smartphone/computer with internet (free)

1. **Satellite imagery analysis:**
   - Open Google Earth (free)
   - Navigate to your land in Migori
   - Note: vegetation patterns, drainage, topography, color variations
   - Take screenshots of interesting features

2. **Geological literature review:**
   - Search Google Scholar for "Migori geology" (free)
   - Check Mindat.org for mineral occurrences nearby (free)
   - Check USGS MRDS for mineral data (free)
   - Download BGS reports on Migori (free)

3. **Historical research:**
   - Search UK National Archives for colonial mining records (free)
   - Check if Macalder mine geology applies to your area
   - Look for geological maps of the Migori Gold Belt

4. **Free satellite analysis:**
   - Sign up for Google Earth Engine (free)
   - Calculate clay and iron oxide indices for your area
   - Note any spectral anomalies

#### Phase 2: Reconnaissance Survey (Day 3-4)

**Tools needed:** Smartphone (free), notebook (free if you have paper)

1. **Walk the entire property:**
   - Walk boundary lines and interior
   - Note terrain changes, rock exposures, soil colors
   - Photograph everything (geotagged with phone GPS)
   - Record observations in notebook

2. **Magnetic survey:**
   - Download Physics Toolbox Magnetometer (free)
   - Walk a grid (25m spacing lines, 10m readings)
   - Record magnetic readings at each point
   - Note any anomalies

3. **Biological indicators:**
   - Note vegetation patterns
   - Look for indicator plants
   - Observe soil colors (especially red/rust = iron, green/blue = copper)
   - Check water sources for color/smell

4. **Sample collection:**
   - Collect rock samples at each grid point
   - Note GPS coordinates for each sample
   - Number and label samples
   - Collect soil samples from different depths

#### Phase 3: Field Testing (Day 5-7)

**Tools needed:** Smartphone, samples from Phase 2, household items

1. **Physical property testing (free):**
   - **Hardness test:** Scratch with fingernail (2.5), coin (3.5), knife (5.5), glass (5.5)
   - **Streak test:** Scratch on unglazed porcelain (back of toilet tank, ceramic tile)
   - **Acid test:** Vinegar on carbonate minerals (fizz = calcite/dolomite)
   - **Magnet test:** Use phone magnetometer or actual magnet
   - **Density test:** Water displacement method
   - **Color/luster:** Visual identification

2. **Photo-based AI identification:**
   - Photograph each sample clearly
   - Use free rock ID apps (Stone Identifier Rock Scanner)
   - Upload to HuggingFace models
   - Cross-reference with physical tests

3. **Spectral analysis (if DVD spectrometer built):**
   - Analyze reflected light from samples
   - Compare to known mineral spectra
   - Note absorption features

#### Phase 4: Data Analysis (Day 8-10)

**Tools needed:** Computer/smartphone, free software

1. **Data entry:**
   - Enter all data into Google Sheets (free)
   - Columns: Sample ID, GPS X, GPS Y, Rock Type, Color, Hardness, Streak, Magnetic Reading, Mineral ID, Notes

2. **Geological mapping:**
   - Create a geological map in QGIS (free)
   - Plot sample locations, rock types, anomalies
   - Draw geological boundaries
   - Add satellite imagery as base layer

3. **Mineral estimation:**
   - Use PyKrige for grade estimation (free)
   - Create grade contour maps
   - Estimate tonnage from surface data

4. **Report preparation:**
   - Compile all findings into a professional report
   - Include: geological map, sample data, satellite analysis, mineral identification, grade estimates
   - Use free tools: Google Docs, LibreOffice

#### Phase 5: Professional Report (Day 11-14)

**Creating a report investors will take seriously — for FREE:**

1. **Report structure:**
   - Executive Summary
   - Location & Access (with map)
   - Geological Setting (reference academic literature)
   - Exploration Methods Used
   - Results (maps, tables, photos)
   - Mineral Inventory (estimated)
   - Recommendations for further work
   - Appendices (raw data, photos, references)

2. **Free tools for professional presentation:**
   - **Google Docs/Slides**: Word processing and presentations
   - **QGIS**: Professional geological maps
   - **GIMP**: Photo editing
   - **LibreOffice**: Office suite (free alternative to Microsoft Office)
   - **Canva**: Design tool (free tier) for report graphics

3. **What makes a report credible:**
   - GPS-referenced data points
   - Consistent methodology
   - Cross-referenced mineral identifications
   - Satellite imagery analysis
   - References to academic literature
   - Honest assessment of limitations
   - Clear recommendations for next steps

---

## Appendix A: Complete Free Software List

| Software | Purpose | Download |
|----------|---------|----------|
| **QGIS** | GIS, mapping, satellite analysis | qgis.org |
| **Python** | Data analysis, ML, geostatistics | python.org |
| **Google Earth Engine** | Cloud-based satellite analysis | earthengine.google.com |
| **Google Earth Pro** | 3D terrain visualization | google.com/earth |
| **SimPEG** | Geophysical inversion | `pip install simpeg` |
| **Fatiando** | Geophysical modeling | `pip install fatiando` |
| **PyKrige** | Kriging/geostatistics | `pip install pykrige` |
| **scikit-learn** | Machine learning | `pip install scikit-learn` |
| **GSTools** | Geostatistics | `pip install gstools` |
| **ImageJ/FIJI** | Image analysis, spectroscopy | fiji.sc |
| **GIMP** | Photo editing | gimp.org |
| **LibreOffice** | Office suite | libreoffice.org |
| **Blender** | 3D modeling | blender.org |
| **ParaView** | Scientific visualization | paraview.org |

## Appendix B: Free Apps Summary

| App | Platform | Use |
|-----|----------|-----|
| **Physics Toolbox Magnetometer** | Android/iOS | Magnetic field measurement |
| **Phyphox** | Android/iOS | All smartphone sensors |
| **Spectroid** | Android | Spectrum analysis |
| **Stone Identifier Rock Scanner** | Android/iOS | Mineral ID from photos |
| **QField** | Android/iOS | Field data collection |
| **OsmAnd** | Android/iOS | Offline maps & GPS |
| **Google My Maps** | Web | Custom map creation |
| **3D Scanner App** | iOS | LiDAR terrain scanning |

## Appendix C: Free Data Sources

| Source | URL | Data Available |
|--------|-----|----------------|
| **Mindat.org** | mindat.org | Mineral occurrences worldwide |
| **USGS EarthExplorer** | earthexplorer.usgs.gov | Landsat, ASTER satellite data |
| **Copernicus Hub** | scihub.copernicus.eu | Sentinel-2 satellite data |
| **Google Earth Engine** | earthengine.google.com | Multi-sensor satellite data |
| **USGS MRDS** | mrdata.usgs.gov | Mineral resources data |
| **BGS GeoIndex** | bgs.ac.uk | UK geological data (incl. colonial) |
| **OneGeology** | portal.onegeology.org | Global geological maps |
| **Kenya Mining** | mining.go.ke | Kenya mineral data |
| **Google Scholar** | scholar.google.com | Academic papers (many free) |
| **UK National Archives** | nationalarchives.gov.uk | Colonial mining records |

## Appendix D: Migori-Specific Geological Context

**The Migori Gold Belt** is part of the Nyanzian Supergroup (Archean greenstone belt) in western Kenya. Key geological features:

- **Host rocks:** Metavolcanic and metasedimentary rocks (schists, gneisses, banded iron formations)
- **Structural controls:** Shear zones, faults, fold hinges
- **Associated minerals:** Gold (primary), copper, pyrite, arsenopyrite
- **Alteration:** Silicification, sericitization, carbonatization
- **Known deposits:** Macalder (Cu-Au), various artisanal gold workings

**This geological context is critical** — it tells you what to look for and where to look. Gold in Migori is typically found in:
- Quartz veins within shear zones
- Banded iron formations (BIF)
- Along geological contacts between different rock types
- In weathered surface material (alluvial gold)

---

## Key Takeaway

**You do NOT need money to explore your land.** Every method described above is free or near-free. The combination of:
1. Free satellite data (Sentinel-2, ASTER, Landsat)
2. Smartphone sensors (magnetometer, GPS, camera)
3. Free AI identification apps
4. Biological indicators
5. Community knowledge
6. Free geostatistical software

...gives you a powerful exploration toolkit that can identify mineral potential, estimate quantities, and create professional reports — all for KES 0.

**The most important free resource is knowledge.** Read the academic papers about Migori geology. Talk to local miners. Walk your land carefully. The minerals have been there for billions of years — they're not going anywhere. You just need to find them.
