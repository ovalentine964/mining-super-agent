# Team 21: Custom DeerFlow 2.0 for Mining — Domain-Specific Superagent Harness

**Date**: 2026-07-25
**Status**: Architecture Design Complete
**Key Decision**: Configuration + Plugin approach (NO forking)

---

## Executive Summary

This document defines how to customize ByteDance's **DeerFlow 2.0** — an open-source LangGraph-based superagent harness — into a **domain-specific mining superagent**. The approach uses DeerFlow's native configuration and extension points (YAML config, custom skills, MCP tools) rather than forking the codebase, ensuring we can pull upstream updates while maintaining a fully custom mining operation.

**Jensen Huang's Vision Applied:**
> "A company is really about a collection of proprietary, super important workflows... We create super sub-agents with Deep Agents... That super agent is not trying to book me travel appointments. It's just trying to optimize our supply chain."

Our mining superagent doesn't do generic tasks. It identifies minerals, analyzes geology, runs quantum optimizations on supply chains, and monitors Kenyan mining regulations. That's the moat.

---

## 1. DeerFlow 2.0 Architecture Deep Dive

### 1.1 System Architecture

DeerFlow 2.0 is a ground-up rewrite from the 1.x "Deep Research" tool into a generalized superagent harness. It's built on a multi-service architecture:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Frontend  │────▶│    Nginx     │◀────│   Gateway   │
│  (Port 3000)│     │  (Port 2026) │     │  API (8001) │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  LangGraph   │
                    │ Server (2024)│
                    └──────────────┘
```

**Four main components:**

| Component | Port | Technology | Purpose |
|-----------|------|------------|---------|
| LangGraph Server | 2024 | LangGraph + LangChain | Agent runtime, workflow execution, sub-agent orchestration |
| Gateway API | 8001 | FastAPI + Pydantic | REST API for config, skills, memory, uploads, artifacts |
| Frontend | 3000 | Next.js 16, React 19 | Chat UI, config, artifact preview |
| Nginx | 2026 | Nginx reverse proxy | Unified entry point, SSL termination, routing |

**Data flow:**
1. User sends message → Frontend → Nginx → LangGraph Server
2. LangGraph processes through middleware chain → Agent executes with tools/sub-agents
3. Streaming response via SSE → Frontend renders in real-time

### 1.2 LangGraph State Machine (Agent Orchestration)

The core is a **LangGraph state machine** with a lead agent that can fan-out to sub-agents:

**Agent creation** (`backend/src/agents/lead_agent/agent.py`):
```python
def make_lead_agent(config: RunnableConfig):
    model = create_chat_model(model_name, thinking_enabled)
    tools = get_available_tools(groups=config.tool_groups, ...)
    system_prompt = apply_prompt_template(config)
    agent = create_react_agent(model, tools, state_schema=ThreadState)
    return agent
```

**ThreadState** extends LangGraph's `AgentState`:
```python
class ThreadState(AgentState):
    messages: Annotated[list, add_messages]
    sandbox: Optional[Sandbox]
    thread_data: dict
    title: Optional[str]
    artifacts: Annotated[list[dict], merge_artifacts]
    todos: Optional[list[dict]]
    uploaded_files: list[str]
    viewed_images: Annotated[list[dict], merge_viewed_images]
```

**Middleware chain** (strict execution order):
1. ThreadDataMiddleware — Creates thread directories
2. UploadsMiddleware — Injects uploaded files
3. SandboxMiddleware — Acquires sandbox instance
4. DanglingToolCallMiddleware — Handles interrupted tool calls
5. SummarizationMiddleware — Context reduction (optional)
6. TodoListMiddleware — Task tracking (Plan Mode)
7. TitleMiddleware — Auto-generates thread title
8. MemoryMiddleware — Queues conversations for memory updates
9. ViewImageMiddleware — Injects image data for vision models
10. SubagentLimitMiddleware — Enforces concurrent subagent limits (max 3)
11. ClarificationMiddleware — Handles ask_clarification interrupts

### 1.3 Sub-Agent System

The lead agent uses a **fan-out/converge workflow** — decomposes objectives into tasks, spawns parallel sub-agents, then synthesizes results:

```python
task(
    description="Research TensorFlow",
    prompt="Research TensorFlow's architecture, key features, and use cases",
    subagent_type="general-purpose",  # or "bash"
    max_turns=20
)
```

**Sub-agent types:**
- **general-purpose**: Full capability — sandbox tools, research tools, skills, memory (read-only)
- **bash**: Command specialist — bash, read_file, write_file, ls only

**Concurrency**: Max 3 concurrent sub-agents enforced by SubagentLimitMiddleware.
**Timeout**: 15-minute limit per sub-agent.
**Context isolation**: Each sub-agent has its own conversation history, tool calls, and intermediate results. Sandbox filesystem and skills access are shared.

### 1.4 Memory System

**Storage**: `backend/.deer-flow/memory.json`

Three components:
- **User Context**: Work, personal context, top-of-mind
- **History**: Recent months, earlier context, long-term background
- **Facts**: Discrete facts with confidence scores (0.0–1.0), categories (preference/knowledge/context/behavior/goal)

**How it works:**
1. MemoryMiddleware filters relevant messages (HumanMessage + final AIMessage, excluding tool calls)
2. Debounced queue (30s default) batches updates
3. LLM extracts facts with confidence scores
4. Facts merged with existing memory (deduplication by content similarity)
5. Pruned to max_facts (100 default)
6. Top 15 facts injected into next system prompt

**Configuration:**
```yaml
memory:
  enabled: true
  storage_path: .deer-flow/memory.json
  debounce_seconds: 30
  max_facts: 100
  fact_confidence_threshold: 0.7
  injection_enabled: true
  max_injection_tokens: 2000
```

### 1.5 Sandbox Execution

Three providers:

| Provider | Isolation | Use Case |
|----------|-----------|----------|
| LocalSandboxProvider | None (host) | Local dev, trusted environments |
| AioSandboxProvider (Docker) | Container | Production-like isolation |
| Kubernetes Provisioner | Pod | Production at scale |

**Virtual path system:**
- Agent sees `/mnt/user-data/{workspace,uploads,outputs}` and `/mnt/skills/{public,custom}`
- Physically mapped to `backend/.deer-flow/threads/{thread-id}/user-data/` and `skills/`

**Sandbox interface:**
```python
class Sandbox(ABC):
    async def execute_command(self, command: str) -> dict
    async def read_file(self, path: str) -> str
    async def write_file(self, path: str, content: str) -> dict
    async def list_dir(self, path: str) -> list
```

### 1.6 Skills System

Skills are **structured capability modules** with progressive loading:

**Structure:**
```
skills/custom/data-analysis/
├── SKILL.md              # YAML frontmatter + Markdown instructions
├── scripts/analyze.py    # Executable code (optional)
├── references/schema.md  # Documentation (optional)
└── assets/template.html  # Templates (optional)
```

**SKILL.md format:**
```markdown
---
name: data-analysis
description: Analyze datasets with pandas, create visualizations...
license: MIT
allowed-tools:
  - bash
  - read_file
  - write_file
---

# Data Analysis Skill
## Overview
...
```

**Progressive loading:**
1. **Stage 1 (always loaded)**: List of skill names + descriptions (keeps context lean)
2. **Stage 2 (on-demand)**: Full SKILL.md content loaded when agent selects a skill

**Two categories:**
- **Public skills**: `skills/public/` — shipped with DeerFlow, version-controlled
- **Custom skills**: `skills/custom/` — user-created, gitignored by default

### 1.7 Tools System

**Tool sources (in order):**
1. Config-defined tools (via reflection from config.yaml)
2. MCP tools (from enabled MCP servers)
3. Built-in tools: `present_files`, `ask_clarification`, `view_image`
4. Sub-agent tool: `task()` for delegation

**Tool categories:**
- **Sandbox tools**: bash, ls, read_file, write_file, str_replace
- **Community tools**: web_search (Tavily), web_fetch (Tavily/Jina/Firecrawl), image_search (DuckDuckGo)
- **MCP tools**: External tools via Model Context Protocol (stdio or HTTP/SSE transport, OAuth support)
- **Custom tools**: User-defined via config.yaml

### 1.8 Context Compaction

Dual-layer context management:
- **Isolated sub-agent context**: Each sub-agent operates in strictly scoped context (prevents "contextual pollution")
- **Summarization and compression**: Aggressively manages context window by summarizing completed tasks, offloading intermediate data to filesystem, compressing irrelevant tokens

### 1.9 IM Channel Support

| Channel | Transport | Difficulty |
|---------|-----------|------------|
| Telegram | Bot API | Easy |
| Slack | Socket Mode | Moderate |
| Feishu/Lark | WebSocket | Moderate |

---

## 2. Jensen's Vision: Domain-Specific Superagents

### 2.1 The Core Philosophy

Jensen Huang (NVIDIA CEO) has articulated the vision for domain-specific superagents:

> "A company is really about a collection of proprietary, super important workflows."

> "We create super sub-agents with Deep Agents, LangChain Deep Agents with Nemotron 3 inside."

> "That super agent is not trying to book me travel appointments. It's just trying to optimize our supply chain."

> "I really do need to have LangChain. I really do need to have Nemotron 3 Ultra, and I connect it to a lot of proprietary knowledge and proprietary skills."

> "I've got a whole team who's just dedicated to refining that."

### 2.2 What This Means Architecturally

The domain-specific superagent is:
- **NOT a general-purpose assistant** — it doesn't book flights or write emails
- **A collection of specialized sub-agents** — each expert in one domain
- **Connected to proprietary knowledge** — geological data, market data, regulatory data
- **Connected to proprietary skills** — mineral identification, NPV calculation, quantum optimization
- **Continuously refined** — a dedicated team improves it over time
- **The competitive moat** — proprietary knowledge + proprietary skills = defensible advantage

### 2.3 The Flywheel

```
Miner sends photo → AI identifies mineral → Corrects if wrong → Model improves
       ↑                                                                    ↓
  Better predictions ← Model gets smarter ← More training data ← More miners use it
```

Every interaction generates training data. Every correction improves the model. Every deployment brings more users. This is the compounding advantage.

---

## 3. Mining Domain Customization

### 3.1 Custom Agents (Replace General-Purpose Sub-agents)

DeerFlow's sub-agent system uses `subagent_type` to select agent behavior. We extend this with mining-specific types:

| Mining Agent | Replaces | Purpose | Tools |
|-------------|----------|---------|-------|
| **Geological Analyst** | Generic research agent | Geological survey analysis, formation modeling | GemPy, SimPEG, Fatiando, web_search |
| **Satellite Interpreter** | Generic data agent | Sentinel-2 analysis, land-use change detection | Google Earth Engine, rasterio, GDAL |
| **Mineral Identifier** | Generic vision agent | Photo-based mineral identification | CLIP, YOLOv8, view_image |
| **Market Intelligence** | Generic finance agent | Commodity prices, market trends, forecasts | yfinance, Alpha Vantage, web_search |
| **Legal Compliance** | Generic legal agent | Kenya Mining Act 2016, regulatory compliance | Knowledge base, web_search |
| **Financial Modeler** | Generic analyst agent | NPV/IRR/DCF calculations, project economics | numpy-financial, pandas, custom models |
| **Community Relations** | Generic communication agent | Stakeholder engagement, cultural protocols | Templates, translation tools |
| **Exploration Planner** | Generic planning agent | Exploration program design, budget allocation | Scheduling, optimization tools |
| **Quantum Optimizer** | Generic optimization agent | Supply chain, logistics optimization | CUDA-Q, IBM Quantum, D-Wave |
| **Orchestrator** | Lead agent | Routes tasks to mining-specific agents | task() with mining subagent_types |

**Implementation — Custom subagent types in config.yaml:**
```yaml
subagent_types:
  geological-analyst:
    description: "Geological survey analysis, formation modeling, mineral deposit assessment"
    system_prompt_file: prompts/geological_analyst.md
    tool_groups: [sandbox, geological, research]
    max_turns: 30
    thinking_enabled: true

  satellite-interpreter:
    description: "Satellite imagery analysis, land-use change detection, vegetation indices"
    system_prompt_file: prompts/satellite_interpreter.md
    tool_groups: [sandbox, satellite, research]
    max_turns: 25

  mineral-identifier:
    description: "Mineral identification from photos using computer vision"
    system_prompt_file: prompts/mineral_identifier.md
    tool_groups: [sandbox, vision]
    max_turns: 15

  market-intelligence:
    description: "Commodity market analysis, price forecasting, trade intelligence"
    system_prompt_file: prompts/market_intelligence.md
    tool_groups: [sandbox, market, research]
    max_turns: 20

  legal-compliance:
    description: "Mining regulatory compliance, Kenya Mining Act 2016, permit requirements"
    system_prompt_file: prompts/legal_compliance.md
    tool_groups: [sandbox, research]
    knowledge_bases: [kenya-mining-act, eac-mining-regulations]
    max_turns: 20

  financial-modeler:
    description: "NPV/IRR/DCF calculations, project economics, investment analysis"
    system_prompt_file: prompts/financial_modeler.md
    tool_groups: [sandbox, financial]
    max_turns: 25

  quantum-optimizer:
    description: "Quantum computing optimization for supply chain, logistics, scheduling"
    system_prompt_file: prompts/quantum_optimizer.md
    tool_groups: [sandbox, quantum]
    max_turns: 20
```

### 3.2 Custom Tools (Mining-Specific)

#### 3.2.1 Geological Tools

**GemPy** — 3D structural geological modeling:
```python
# tools/geological/gempy_modeler.py
"""GemPy-based 3D geological model creation and visualization."""

def create_geological_model(formation_data: dict, extent: list) -> str:
    """Create a 3D geological model from formation data.
    
    Args:
        formation_data: Dict with formations, interfaces, orientations
        extent: [xmin, xmax, ymin, ymax, zmin, zmax]
    
    Returns:
        Path to exported model (VTK/HTML)
    """
    import gempy as gp
    import gempy_viewer as gpv
    
    geo_model = gp.create_geomodel(
        project_name='mining_model',
        extent=extent,
        resolution=[50, 50, 50]
    )
    # ... model creation logic
    gpv.plot_3d(geo_model)
    return output_path
```

**SimPEG** — Geophysical inversion:
```python
# tools/geophysical/simpeg_inversion.py
"""SimPEG-based geophysical data inversion."""

def invert_gravity_data(data_path: str, mesh_config: dict) -> dict:
    """Run gravity inversion on survey data.
    
    Args:
        data_path: Path to CSV with survey points and measurements
        mesh_config: Mesh generation parameters
    
    Returns:
        Dict with density model, convergence info, output files
    """
    import SimPEG
    from SimPEG import maps, data_misfit, regularization, optimization
    # ... inversion logic
    return {"model": model_path, "misfit": final_misfit}
```

**Fatiando a Terra** — Geophysical forward modeling:
```python
# tools/geophysical/fatiando_model.py
"""Fatiando-based forward modeling for geophysical data."""

def forward_model_gravity(prism_model: list, observation_points: list) -> dict:
    """Compute gravity forward model from prism geometry."""
    import harmonica as hm
    # ... forward modeling logic
```

**Register in config.yaml:**
```yaml
tools:
  - use: tools.geological.gempy_modeler:create_geological_model
    group: geological
    description: "Create 3D geological models from formation data"
    
  - use: tools.geophysical.simpeg_inversion:invert_gravity_data
    group: geological
    description: "Run gravity/magnetic inversion on geophysical survey data"
    
  - use: tools.geophysical.fatiando_model:forward_model_gravity
    group: geological
    description: "Compute forward gravity/magnetic models"
```

#### 3.2.2 Satellite Tools

**Sentinel-2 + Google Earth Engine:**
```python
# tools/satellite/gee_processor.py
"""Google Earth Engine satellite imagery processing."""

def analyze_sentinel2(
    aoi_geojson: dict,
    date_range: tuple,
    indices: list[str] = ["NDVI", "NDWI", "NDBI"]
) -> dict:
    """Analyze Sentinel-2 imagery for a given area of interest.
    
    Args:
        aoi_geojson: GeoJSON geometry defining the area
        date_range: (start_date, end_date) as "YYYY-MM-DD"
        indices: Spectral indices to compute
    
    Returns:
        Dict with computed indices, statistics, output rasters
    """
    import ee
    ee.Initialize()
    
    aoi = ee.Geometry(aoi_geojson)
    collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                  .filterBounds(aoi)
                  .filterDate(*date_range)
                  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)))
    
    # Compute indices
    results = {}
    for index_name in indices:
        if index_name == "NDVI":
            img = collection.median().normalizedDifference(['B8', 'B4'])
        elif index_name == "NDWI":
            img = collection.median().normalizedDifference(['B3', 'B8'])
        # ... more indices
        results[index_name] = img
    
    return results
```

#### 3.2.3 Vision Tools (Mineral Identification)

**CLIP + YOLOv8 mineral identification:**
```python
# tools/vision/mineral_identifier.py
"""Computer vision-based mineral identification."""

def identify_mineral(image_path: str, model_version: str = "latest") -> dict:
    """Identify minerals in a photograph.
    
    Args:
        image_path: Path to mineral photo
        model_version: Model version to use
    
    Returns:
        Dict with identified minerals, confidence scores, bounding boxes
    """
    from ultralytics import YOLO
    import clip
    import torch
    
    # Load fine-tuned YOLOv8 model
    model = YOLO(f"models/mineral_yolo_{model_version}.pt")
    
    # Run detection
    results = model(image_path)
    
    # CLIP for classification refinement
    clip_model, preprocess = clip.load("ViT-B/32")
    # ... classification logic
    
    return {
        "minerals": [
            {"name": "Chromite", "confidence": 0.92, "bbox": [x1, y1, x2, y2]},
            {"name": "Serpentine", "confidence": 0.87, "bbox": [x1, y1, x2, y2]}
        ],
        "image_analysis": "Dark metallic mineral with submetallic luster..."
    }
```

#### 3.2.4 Quantum Computing Tools

```python
# tools/quantum/optimizer.py
"""Quantum computing optimization for mining operations."""

def quantum_optimize_supply_chain(
    nodes: list,
    edges: list,
    constraints: dict,
    backend: str = "cudaq"
) -> dict:
    """Optimize supply chain routing using quantum computing.
    
    Args:
        nodes: Supply chain nodes (mines, processing, ports)
        edges: Connections with costs/capacities
        constraints: Capacity, time, budget constraints
        backend: "cudaq", "ibm", "dwave"
    
    Returns:
        Optimal routing, cost savings, execution metadata
    """
    if backend == "cudaq":
        import cudaq
        # CUDA-Q QAOA implementation
        # ...
    elif backend == "ibm":
        from qiskit import QuantumCircuit
        # IBM Quantum implementation
        # ...
    elif backend == "dwave":
        from dwave.system import DWaveSampler, EmbeddingComposite
        # D-Wave quantum annealing
        # ...
    
    return {"optimal_route": route, "cost_savings": savings_pct}
```

#### 3.2.5 Market Intelligence Tools

```python
# tools/market/commodity_tracker.py
"""Commodity price tracking and forecasting."""

def get_commodity_prices(commodities: list[str], period: str = "1y") -> dict:
    """Fetch current and historical commodity prices.
    
    Args:
        commodities: ["gold", "chromite", "titanium", "copper"]
        period: Historical period ("1d", "1mo", "1y", "5y")
    
    Returns:
        Current prices, historical data, basic forecasts
    """
    import yfinance as yf
    
    ticker_map = {
        "gold": "GC=F",
        "copper": "HG=F",
        "silver": "SI=F",
        "platinum": "PL=F",
    }
    
    results = {}
    for commodity in commodities:
        ticker = ticker_map.get(commodity)
        if ticker:
            data = yf.download(ticker, period=period)
            results[commodity] = {
                "current_price": float(data['Close'].iloc[-1]),
                "change_pct": float((data['Close'].iloc[-1] / data['Close'].iloc[0] - 1) * 100),
                "data": data.to_dict()
            }
    
    return results
```

#### 3.2.6 Communication Tools

```python
# tools/communication/telegram_bot.py
"""Telegram Bot API integration for field communication."""

def send_field_report(chat_id: str, report: dict) -> bool:
    """Send a formatted field report to Telegram.
    
    Args:
        chat_id: Telegram chat ID
        report: Dict with title, summary, images, location
    
    Returns:
        Success status
    """
    import requests
    
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    # ... send formatted message with images and location pins
```

### 3.3 Custom Knowledge Base

The proprietary knowledge base is the **competitive moat** — this is what makes YOUR superagent unique.

#### 3.3.1 Knowledge Structure

```
knowledge/
├── geology/
│   ├── migori_greenstone_belt/
│   │   ├── geological_survey_2024.pdf
│   │   ├── formation_maps/
│   │   ├── drill_core_data/
│   │   └── mineral_assays/
│   ├── kenya_geological_map/
│   │   ├── geological_units.geojson
│   │   ├── mineral_occurrences.geojson
│   │   └── structural_features.geojson
│   └── east_african_shield/
│       ├── tectonic_history.md
│       ├── metamorphic_grades.md
│       └── known_deposits.md
├── regulatory/
│   ├── kenya_mining_act_2016/
│   │   ├── full_text.md
│   │   ├── section_summaries.md
│   │   ├── permit_requirements.md
│   │   └── compliance_checklists/
│   ├── environmental_regulations/
│   │   ├── nema_requirements.md
│   │   ├── eia_process.md
│   │   └── water_act_2016.md
│   └── community_rights/
│       ├── land_act_2012.md
│       ├── community_land_act_2016.md
│       └── benefit_sharing.md
├── minerals/
│   ├── identification_guides/
│   │   ├── chromite_guide.md
│   │   ├── gold_guide.md
│   │   ├── titanium_guide.md
│   │   └── rare_earths_guide.md
│   ├── processing_methods/
│   │   ├── gravity_separation.md
│   │   ├── magnetic_separation.md
│   │   └── flotation.md
│   └── market_data/
│       ├── global_supply_demand.md
│       ├── price_history/
│       └── competitor_analysis/
├── financial/
│   ├── mining_financial_models/
│   │   ├── npv_template.xlsx
│   │   ├── irr_calculator.py
│   │   ├── dcf_model.py
│   │   └── sensitivity_analysis.py
│   ├── cost_databases/
│   │   ├── equipment_costs.md
│   │   ├── labor_costs_kenya.md
│   │   └── energy_costs.md
│   └── financing_options/
│       ├── kenya_development_finance.md
│       └── international_mining_finance.md
└── community/
    ├── engagement_protocols/
    │   ├── consultation_process.md
    │   ├── cultural_considerations.md
    │   └── grievance_mechanism.md
    └── templates/
        ├── community_meeting_agenda.md
        ├── benefit_sharing_agreement.md
        └── environmental_commitment.md
```

#### 3.3.2 Knowledge Integration Method

```yaml
# In system prompt template
knowledge_bases:
  - id: migori-geology
    source: knowledge/geology/migori_greenstone_belt/
    injection: summary  # Inject summary, full docs on demand
    
  - id: kenya-mining-act
    source: knowledge/regulatory/kenya_mining_act_2016/
    injection: always  # Always inject key sections
    
  - id: mineral-guides
    source: knowledge/minerals/identification_guides/
    injection: on-demand  # Load when mineral identification task
```

### 3.4 Custom Skills

#### 3.4.1 Mineral Identification Skill

```markdown
---
name: mineral-identification
description: Identify minerals from photographs using computer vision. Use when a user sends a rock/mineral photo or asks to identify a mineral sample.
license: Proprietary
allowed-tools:
  - bash
  - read_file
  - write_file
  - view_image
---

# Mineral Identification Skill

## Overview
Identify minerals from photographs using fine-tuned YOLOv8 + CLIP models.
Trained on Kenyan mineral samples from Migori, Homa Bay, and Transmara counties.

## Usage
1. Load the mineral photo using `view_image`
2. Run the identification script:
```bash
python /mnt/skills/custom/mineral-identification/scripts/identify.py \
  --image /mnt/user-data/uploads/sample.jpg \
  --output /mnt/user-data/outputs/identification.json
```

3. Present results with geological context from knowledge base

## Output Format
```json
{
  "minerals": [
    {"name": "Chromite", "confidence": 0.92, "description": "..."},
    {"name": "Serpentine", "confidence": 0.87, "description": "..."}
  ],
  "geological_context": "Found in ultramafic rocks of the Migori Greenstone Belt...",
  "economic_significance": "Chromite is the primary ore of chromium...",
  "next_steps": ["XRD confirmation", "Assay for Cr2O3 content"]
}
```

## Training Data
Model trained on 12,847 labeled mineral photos from:
- Migori Greenstone Belt field surveys
- University of Nairobi geology department collection
- USGS mineral photo database (augmented)
- Synthetic augmentations (rotation, lighting, scale)
```

#### 3.4.2 Geological Report Generation Skill

```markdown
---
name: geological-report
description: Generate comprehensive geological survey reports for mining exploration areas. Use when compiling field data, drill results, or exploration findings into professional reports.
license: Proprietary
allowed-tools:
  - bash
  - read_file
  - write_file
---

# Geological Report Generation Skill

## Overview
Generate NI 43-101 compliant geological reports from field data, assay results, and survey data.

## Report Sections
1. Executive Summary
2. Property Description & Location
3. Geology & Mineralization
4. Exploration History
5. Drilling & Sampling
6. Analytical Results
7. Mineral Resource Estimation
8. Environmental & Social
9. Conclusions & Recommendations

## Templates
- Full report: `assets/templates/ni43101_template.docx`
- Summary: `assets/templates/executive_summary.md`
- Maps: `assets/templates/geological_map.html`
```

#### 3.4.3 NPV/IRR Calculation Skill

```markdown
---
name: financial-analysis
description: Calculate NPV, IRR, and perform DCF analysis for mining projects. Use when evaluating project economics, comparing investment options, or preparing financial models.
license: Proprietary
allowed-tools:
  - bash
  - read_file
  - write_file
---

# Mining Financial Analysis Skill

## Quick NPV Calculation
```python
import numpy_financial as npf

cashflows = [-5000000, 800000, 1200000, 1500000, 1800000, 2000000, 2200000, 2500000]
discount_rate = 0.10  # 10%

npv = npf.npv(discount_rate, cashflows)
irr = npf.irr(cashflows)

print(f"NPV: ${npv:,.0f}")
print(f"IRR: {irr:.1%}")
```

## Sensitivity Analysis
Automatically run scenarios varying:
- Discount rate (8%, 10%, 12%, 15%)
- Commodity prices (±20%)
- Production rates (±15%)
- CAPEX (±25%)
- OPEX (±20%)
```

#### 3.4.4 Satellite Analysis Skill

```markdown
---
name: satellite-analysis
description: Analyze satellite imagery for mining exploration, environmental monitoring, and land-use change detection. Use when working with Sentinel-2, Landsat, or other satellite data.
license: Proprietary
allowed-tools:
  - bash
  - read_file
  - write_file
---

# Satellite Analysis Skill

## Capabilities
- **NDVI**: Vegetation health assessment
- **NDWI**: Water body detection
- **NDBI**: Built-up area detection
- **Change Detection**: Land-use change over time
- **Mineral Mapping**: Spectral mineral indices
- **Environmental Monitoring**: Disturbance tracking

## Usage
```python
# Analyze Sentinel-2 imagery for exploration area
result = analyze_sentinel2(
    aoi_geojson={"type": "Polygon", "coordinates": [...]},
    date_range=("2025-01-01", "2026-01-01"),
    indices=["NDVI", "NDWI", "mineral_index"]
)
```
```

#### 3.4.5 Quantum Optimization Skill

```markdown
---
name: quantum-optimization
description: Use quantum computing for supply chain optimization, logistics routing, and scheduling problems. Use when optimizing mine-to-port logistics, processing schedules, or resource allocation.
license: Proprietary
allowed-tools:
  - bash
  - read_file
  - write_file
---

# Quantum Optimization Skill

## Backends
- **CUDA-Q**: NVIDIA GPU-accelerated quantum simulation
- **IBM Quantum**: Cloud quantum computing (127+ qubits)
- **D-Wave**: Quantum annealing for combinatorial optimization

## Problem Types
1. **Vehicle Routing**: Mine-to-processing-to-port logistics
2. **Job Scheduling**: Processing plant scheduling
3. **Portfolio Optimization**: Investment allocation
4. **Supply Chain**: Multi-node supply chain optimization

## Usage
```python
result = quantum_optimize_supply_chain(
    nodes=[{"id": "mine_1", "capacity": 1000}, ...],
    edges=[{"from": "mine_1", "to": "port", "cost": 50}, ...],
    constraints={"max_budget": 1000000, "deadline": "2027-01-01"},
    backend="cudaq"
)
```
```

---

## 4. How to Customize Without Forking

### 4.1 The Three Options

#### Option A: Configuration-Based (No Code Changes)

Use DeerFlow's YAML configuration to define agents, tools, skills. Zero changes to DeerFlow core.

**Pros:**
- Cleanest separation
- Always compatible with upstream updates
- Simple to maintain

**Cons:**
- Limited to what config.yaml supports
- Can't modify core behavior

#### Option B: Plugin/Extension System

Create mining-specific plugins and register them with DeerFlow's extension points.

**Pros:**
- More powerful than config alone
- Still modular — plugins are separate from core
- Skills and MCP tools are the natural extension points

**Cons:**
- Some plugins may break on major updates
- Need to track DeerFlow API changes

#### Option C: Wrapper/Adapter Pattern

DeerFlow as the engine, mining-specific layer on top, custom API that routes to DeerFlow internally.

**Pros:**
- Full control over the interface
- Can add mining-specific middleware

**Cons:**
- Most coupling to DeerFlow internals
- Harder to update

### 4.2 Recommended Approach: Option A + B Combined

**Configuration** for agent definitions, tool groups, and knowledge bases.
**Custom skills** for mining-specific workflows.
**MCP servers** for specialized tools (geological, quantum, satellite).
**DeerFlow core stays untouched** — pull updates freely.

```
mining-deerflow/
├── deer-flow/                    # ← Git submodule (upstream, untouched)
├── config/
│   ├── config.yaml               # Mining-optimized DeerFlow config
│   ├── extensions_config.json    # MCP servers for mining tools
│   └── prompts/                  # Mining-specific system prompts
│       ├── lead_agent.md
│       ├── geological_analyst.md
│       ├── satellite_interpreter.md
│       ├── mineral_identifier.md
│       ├── market_intelligence.md
│       ├── legal_compliance.md
│       ├── financial_modeler.md
│       ├── quantum_optimizer.md
│       └── orchestrator.md
├── skills/
│   └── custom/                   # Mining-specific skills
│       ├── mineral-identification/
│       ├── geological-report/
│       ├── financial-analysis/
│       ├── satellite-analysis/
│       └── quantum-optimization/
├── tools/
│   ├── geological/               # GemPy, SimPEG, Fatiando wrappers
│   ├── satellite/                # GEE, rasterio processors
│   ├── vision/                   # CLIP, YOLOv8 mineral models
│   ├── quantum/                  # CUDA-Q, IBM, D-Wave adapters
│   ├── market/                   # yfinance, Alpha Vantage
│   └── communication/            # Telegram Bot API
├── knowledge/                    # Proprietary knowledge base
├── models/                       # Fine-tuned ML models
│   ├── mineral_yolo_v3.pt
│   ├── mineral_clip_v2.pt
│   └── geological_ner_v1.pt
├── mcp-servers/                  # Custom MCP tool servers
│   ├── geological-mcp/
│   ├── satellite-mcp/
│   └── quantum-mcp/
├── docker/
│   ├── Dockerfile.mining-sandbox # Custom sandbox with geo tools
│   └── docker-compose.yml
└── deploy/
    ├── k8s/
    └── terraform/
```

### 4.3 Detailed Implementation

#### Step 1: Fork-Free Configuration

**config.yaml** — Mining-optimized DeerFlow configuration:
```yaml
# Mining DeerFlow Configuration
# Based on DeerFlow 2.0, customized for mining operations

models:
  - name: deepseek-v3
    display_name: DeepSeek V3
    use: langchain_openai:ChatOpenAI
    model: deepseek-v3
    api_key: $DEEPSEEK_API_KEY
    max_tokens: 8192
    supports_vision: false
    
  - name: gpt-4o
    display_name: GPT-4o Vision
    use: langchain_openai:ChatOpenAI
    model: gpt-4o
    api_key: $OPENAI_API_KEY
    max_tokens: 4096
    supports_vision: true

  - name: nemotron-3-ultra
    display_name: Nemotron 3 Ultra
    use: langchain_openai:ChatOpenAI
    model: nvidia/nemotron-3-ultra
    api_key: $NVIDIA_API_KEY
    max_tokens: 16384
    base_url: https://integrate.api.nvidia.com/v1
    supports_vision: false

# Tool groups for mining
tools:
  # Sandbox tools (always available)
  - use: src.tools.bash:bash
    group: sandbox
  - use: src.tools.ls:ls
    group: sandbox
  - use: src.tools.read_file:read_file
    group: sandbox
  - use: src.tools.write_file:write_file
    group: sandbox

  # Geological tools
  - use: tools.geological.gempy_modeler:create_geological_model
    group: geological
    description: "Create 3D geological models"
  - use: tools.geophysical.simpeg_inversion:invert_gravity_data
    group: geological
    description: "Run gravity/magnetic inversion"
  - use: tools.geophysical.fatiando_model:forward_model_gravity
    group: geological
    description: "Compute forward geophysical models"

  # Satellite tools
  - use: tools.satellite.gee_processor:analyze_sentinel2
    group: satellite
    description: "Analyze Sentinel-2 satellite imagery"

  # Vision tools
  - use: tools.vision.mineral_identifier:identify_mineral
    group: vision
    description: "Identify minerals from photos"

  # Market tools
  - use: tools.market.commodity_tracker:get_commodity_prices
    group: market
    description: "Fetch commodity prices and forecasts"

  # Quantum tools
  - use: tools.quantum.optimizer:quantum_optimize_supply_chain
    group: quantum
    description: "Quantum computing optimization"

  # Communication tools
  - use: tools.communication.telegram_bot:send_field_report
    group: communication
    description: "Send reports via Telegram"

  # Research tools
  - use: src.community.tavily:web_search
    group: research
  - use: src.community.tavily:web_fetch
    group: research

# Memory configuration
memory:
  enabled: true
  storage_path: .deer-flow/memory.json
  debounce_seconds: 30
  max_facts: 200
  fact_confidence_threshold: 0.7
  injection_enabled: true
  max_injection_tokens: 3000

# Sandbox
sandbox:
  use: src.community.aio_sandbox:AioSandboxProvider
  aio_sandbox:
    host: unix:///var/run/docker.sock
    image: mining-deerflow-sandbox:latest
    keep_alive_seconds: 7200
    env_inherit:
      - OPENAI_API_KEY
      - DEEPSEEK_API_KEY
      - NVIDIA_API_KEY
      - GOOGLE_EARTH_ENGINE_CREDENTIALS
      - TELEGRAM_BOT_TOKEN

# Sub-agent concurrency
subagent:
  max_concurrent: 5  # Increased from default 3 for mining workflows
  timeout_seconds: 1800  # 30 minutes (longer for quantum jobs)
```

**extensions_config.json** — MCP servers for mining tools:
```json
{
  "mcpServers": {
    "geological-tools": {
      "enabled": true,
      "type": "stdio",
      "command": "python",
      "args": ["mcp-servers/geological-mcp/server.py"],
      "description": "Geological modeling and analysis tools"
    },
    "satellite-tools": {
      "enabled": true,
      "type": "stdio",
      "command": "python",
      "args": ["mcp-servers/satellite-mcp/server.py"],
      "description": "Satellite imagery processing tools"
    },
    "quantum-tools": {
      "enabled": true,
      "type": "stdio",
      "command": "python",
      "args": ["mcp-servers/quantum-mcp/server.py"],
      "description": "Quantum computing optimization tools"
    }
  }
}
```

#### Step 2: Custom Sandbox Image

**docker/Dockerfile.mining-sandbox:**
```dockerfile
FROM bytedance/deerflow-sandbox:latest

# Geological tools
RUN pip install gempy==2024.1 simpeg==0.23.0 fatiando==0.7.0 harmonica==0.7.0

# Satellite tools
RUN pip install earthengine-api rasterio GDAL shapely geopandas

# Vision tools
RUN pip install ultralytics==8.1.0 open-clip-torch torch torchvision

# Market tools
RUN pip install yfinance pandas-datareader alpha-vantage

# Financial tools
RUN pip install numpy-financial openpyxl xlsxwriter

# Quantum tools
RUN pip install cuda-quantum qiskit dwave-ocean-sdk

# Mining-specific Python packages
RUN pip install pykrige scikit-gstat gstools

# Set working directory
WORKDIR /mnt/user-data/workspace
```

#### Step 3: MCP Server for Geological Tools

**mcp-servers/geological-mcp/server.py:**
```python
"""MCP server exposing geological tools to DeerFlow."""

from mcp.server import Server
from mcp.types import Tool, TextContent
import json

server = Server("geological-tools")

@server.tool()
async def create_3d_model(
    formation_data: str,
    extent: str,
    output_format: str = "html"
) -> list[TextContent]:
    """Create a 3D geological model from formation data."""
    import gempy as gp
    import gempy_viewer as gpv
    
    formations = json.loads(formation_data)
    ext = json.loads(extent)
    
    geo_model = gp.create_geomodel(
        project_name='mining_model',
        extent=ext,
        resolution=[50, 50, 50]
    )
    
    # Add formations
    for f in formations:
        gp.add_structural_frame(
            geo_model,
            structural_frame_name=f["name"],
            elements=[...]
        )
    
    # Compute model
    gp.compute_model(geo_model)
    
    # Export
    output_path = f"/mnt/user-data/outputs/model_{geo_model.name}.{output_format}"
    if output_format == "html":
        gpv.plot_3d(geo_model, show=True)
    
    return [TextContent(type="text", text=f"Model saved to {output_path}")]

@server.tool()
async def run_inversion(
    data_path: str,
    method: str = "gravity"
) -> list[TextContent]:
    """Run geophysical inversion on survey data."""
    import SimPEG
    # ... inversion logic
    
    return [TextContent(type="text", text=json.dumps(result))]

if __name__ == "__main__":
    server.run(transport="stdio")
```

#### Step 4: System Prompt Templates

**prompts/orchestrator.md:**
```markdown
You are the Mining Operations Orchestrator — a domain-specific superagent for mining exploration and operations in Kenya's Migori Greenstone Belt.

Your role is to route tasks to specialized mining sub-agents:

## Available Sub-Agents

- **geological-analyst**: Geological survey analysis, formation modeling, deposit assessment
- **satellite-interpreter**: Satellite imagery analysis, land-use change, environmental monitoring
- **mineral-identifier**: Mineral identification from photographs
- **market-intelligence**: Commodity prices, market trends, trade intelligence
- **legal-compliance**: Kenya Mining Act 2016, regulatory compliance, permits
- **financial-modeler**: NPV/IRR/DCF calculations, project economics
- **community-relations**: Stakeholder engagement, cultural protocols
- **exploration-planner**: Exploration program design, budget allocation
- **quantum-optimizer**: Supply chain optimization, logistics routing

## Routing Rules

1. Geological questions → geological-analyst
2. Satellite/remote sensing → satellite-interpreter
3. "What mineral is this?" or photo analysis → mineral-identifier
4. Price/market questions → market-intelligence
5. Legal/regulatory questions → legal-compliance
6. Financial/economic analysis → financial-modeler
7. Community/stakeholder → community-relations
8. Planning/scheduling → exploration-planner
9. Optimization/logistics → quantum-optimizer
10. Complex multi-domain → fan-out to multiple agents

## Key Context

- Primary area: Migori County, Kenya
- Minerals of interest: Chromite, Gold, Titanium, Rare Earths
- Regulatory framework: Kenya Mining Act 2016, NEMA, Water Act 2016
- Community: Luo-speaking communities, agricultural + pastoral

## Memory Context
<memory>
{memory_context}
</memory>
```

---

## 5. Proprietary Knowledge Integration

### 5.1 Building the Knowledge Flywheel

The knowledge base is not static — it's a **living, growing competitive moat**:

```
┌──────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE FLYWHEEL                         │
│                                                              │
│   ┌─────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐│
│   │  Field  │───▶│   AI     │───▶│ Better   │───▶│  More  ││
│   │  Data   │    │ Identifies│    │ Predictions│   │ Users  ││
│   └─────────┘    └──────────┘    └──────────┘    └────────┘│
│       ▲                                              │       │
│       │              ┌──────────┐                    │       │
│       └──────────────│  More    │◀───────────────────┘       │
│                      │ Training │                            │
│                      │  Data    │                            │
│                      └──────────┘                            │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 Data Collection Points

| Data Type | Source | Storage | Training Value |
|-----------|--------|---------|----------------|
| Mineral photos | Field agents via Telegram | `knowledge/minerals/photos/` | Fine-tune YOLOv8 + CLIP |
| Geological observations | Field reports | `knowledge/geology/observations/` | Train geological NER |
| Assay results | Lab reports | `knowledge/geology/assays/` | Deposit model training |
| Market transactions | Trading data | `knowledge/market/transactions/` | Price prediction models |
| Community interactions | Meeting notes | `knowledge/community/interactions/` | Sentiment analysis |
| Regulatory updates | Government gazette | `knowledge/regulatory/updates/` | Compliance checker |
| Satellite imagery | Sentinel-2 archives | `knowledge/satellite/` | Change detection training |
| Exploration results | Drill logs, surveys | `knowledge/exploration/` | Deposit prediction |

### 5.3 Memory System Customization

Extend DeerFlow's memory system with mining-specific fact categories:

```yaml
memory:
  enabled: true
  max_facts: 500  # Higher for domain-specific use
  custom_categories:
    - geological: "Geological observations and findings"
    - regulatory: "Regulatory changes and compliance updates"
    - market: "Market intelligence and price observations"
    - community: "Community engagement outcomes"
    - exploration: "Exploration results and findings"
    - operational: "Operational learnings and optimizations"
```

---

## 6. Deployment Architecture

### 6.1 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        PRODUCTION                                │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────────┐│
│  │ Telegram │  │ Flutter  │  │   Web    │  │   API Gateway   ││
│  │   Bot    │  │   App    │  │   UI     │  │   (FastAPI)     ││
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───────┬─────────┘│
│       │              │              │                │          │
│       └──────────────┴──────────────┴────────────────┘          │
│                              │                                   │
│                              ▼                                   │
│                    ┌──────────────────┐                          │
│                    │   Nginx (2026)   │                          │
│                    └────────┬─────────┘                          │
│                             │                                    │
│              ┌──────────────┼──────────────┐                    │
│              ▼              ▼              ▼                     │
│     ┌──────────────┐ ┌──────────┐ ┌──────────────┐            │
│     │  LangGraph   │ │ Gateway  │ │   Frontend   │            │
│     │  Server      │ │  API     │ │   (Next.js)  │            │
│     │  (2024)      │ │  (8001)  │ │   (3000)     │            │
│     └──────┬───────┘ └──────────┘ └──────────────┘            │
│            │                                                     │
│            ▼                                                     │
│     ┌──────────────────────────────────────────┐               │
│     │         Mining Agent Orchestrator         │               │
│     │  ┌────────┐ ┌────────┐ ┌────────┐       │               │
│     │  │Geology │ │Satellite│ │Mineral │  ...  │               │
│     │  │Agent   │ │Agent   │ │Agent   │       │               │
│     │  └────────┘ └────────┘ └────────┘       │               │
│     └──────────────────┬───────────────────────┘               │
│                        │                                        │
│            ┌───────────┼───────────┐                           │
│            ▼           ▼           ▼                            │
│     ┌──────────┐ ┌──────────┐ ┌──────────┐                    │
│     │ Sandbox  │ │ Memory   │ │ Knowledge│                    │
│     │ (Docker) │ │ (JSON)   │ │ (Files)  │                    │
│     └──────────┘ └──────────┘ └──────────┘                    │
│                                                                  │
│     ┌──────────────────────────────────────────┐               │
│     │          Quantum Backends                 │               │
│     │  ┌────────┐ ┌────────┐ ┌────────┐       │               │
│     │  │CUDA-Q  │ │  IBM   │ │ D-Wave │       │               │
│     │  │(local) │ │(cloud) │ │(cloud) │       │               │
│     │  └────────┘ └────────┘ └────────┘       │               │
│     └──────────────────────────────────────────┘               │
│                                                                  │
│     ┌──────────────────────────────────────────┐               │
│     │          Data Layer                      │               │
│     │  ┌──────────────┐ ┌──────────────┐      │               │
│     │  │ PostgreSQL   │ │    Redis     │      │               │
│     │  │ + PostGIS    │ │  (caching)   │      │               │
│     │  └──────────────┘ └──────────────┘      │               │
│     │  ┌──────────────┐ ┌──────────────┐      │               │
│     │  │ MinIO/S3     │ │   Qdrant     │      │               │
│     │  │ (files)      │ │ (vector DB)  │      │               │
│     │  └──────────────┘ └──────────────┘      │               │
│     └──────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Component Details

| Component | Technology | Purpose | Scaling |
|-----------|------------|---------|---------|
| DeerFlow Core | Python, LangGraph | Agent orchestration | Horizontal (K8s pods) |
| Mining Sandbox | Docker (custom image) | Geo tools, quantum | Pod autoscaler |
| PostgreSQL + PostGIS | PostgreSQL 16 | Spatial data, metadata | Read replicas |
| Redis | Redis 7 | Session cache, pub/sub | Cluster mode |
| MinIO/S3 | MinIO | File storage (images, models) | Distributed mode |
| Qdrant | Qdrant | Vector search (knowledge) | Cluster mode |
| Telegram Bot | python-telegram-bot | Field communication | Webhook mode |
| Flutter App | Flutter/Dart | Mobile field app | CDN + API |
| FastAPI Gateway | FastAPI | External API | Horizontal |
| Quantum Backends | CUDA-Q, IBM, D-Wave | Optimization | Hybrid cloud |

### 6.3 Docker Compose (Development)

```yaml
version: '3.8'

services:
  # DeerFlow core (unchanged upstream)
  langgraph-server:
    build: ./deer-flow
    ports:
      - "2024:2024"
    volumes:
      - ./config/config.yaml:/app/config.yaml
      - ./config/prompts:/app/prompts
      - ./skills/custom:/app/skills/custom
      - ./knowledge:/app/knowledge
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}

  gateway-api:
    build: ./deer-flow
    command: python -m src.gateway
    ports:
      - "8001:8001"
    volumes:
      - ./config:/app/config

  # Mining sandbox (custom image with geo tools)
  mining-sandbox:
    build:
      context: .
      dockerfile: docker/Dockerfile.mining-sandbox
    privileged: true
    volumes:
      - sandbox-data:/mnt/user-data
      - ./skills/custom:/mnt/skills/custom
      - ./knowledge:/mnt/knowledge
      - ./models:/mnt/models

  # Data layer
  postgres:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_DB: mining_deerflow
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant-data:/qdrant/storage

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio-data:/data

  # Frontend
  frontend:
    build: ./deer-flow/frontend
    ports:
      - "3000:3000"

  # Reverse proxy
  nginx:
    image: nginx:alpine
    ports:
      - "2026:2026"
    volumes:
      - ./docker/nginx.conf:/etc/nginx/nginx.conf

  # Telegram bot
  telegram-bot:
    build: ./telegram-bot
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - LANGGRAPH_URL=http://langgraph-server:2024
    restart: unless-stopped

volumes:
  postgres-data:
  redis-data:
  qdrant-data:
  minio-data:
  sandbox-data:
```

### 6.4 Upstream Update Strategy

```bash
# Update DeerFlow core (no conflicts since we don't modify it)
cd deer-flow
git fetch upstream
git merge upstream/main

# Our customizations live OUTSIDE deer-flow/:
# - config/        (our configs)
# - skills/custom/ (our skills)
# - tools/         (our tool wrappers)
# - knowledge/     (our data)
# - models/        (our ML models)
# - mcp-servers/   (our MCP servers)
# - docker/        (our Dockerfiles)

# Rebuild and restart
docker compose build
docker compose up -d
```

---

## 7. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-4)
- [ ] Set up DeerFlow 2.0 as git submodule
- [ ] Create mining-optimized config.yaml
- [ ] Build custom sandbox Docker image with geological tools
- [ ] Create 3 core skills: mineral-identification, geological-report, financial-analysis
- [ ] Deploy Telegram bot integration
- [ ] Set up PostgreSQL + PostGIS for spatial data

### Phase 2: Domain Agents (Weeks 5-8)
- [ ] Implement 5 mining sub-agent types (geological, satellite, mineral, market, financial)
- [ ] Build MCP servers for geological and satellite tools
- [ ] Create knowledge base structure with Kenya Mining Act 2016
- [ ] Fine-tune YOLOv8 mineral identification model on initial dataset
- [ ] Implement memory customization with mining-specific categories

### Phase 3: Advanced Capality (Weeks 9-12)
- [ ] Integrate quantum computing backends (CUDA-Q, IBM, D-Wave)
- [ ] Build satellite analysis pipeline with GEE
- [ ] Implement GemPy/SimPEG geological modeling
- [ ] Create financial modeling templates (NPV/IRR/DCF)
- [ ] Deploy Flutter mobile app for field agents

### Phase 4: Flywheel (Weeks 13-16)
- [ ] Implement data collection pipeline (photos → labeled dataset)
- [ ] Set up model retraining pipeline
- [ ] Build community relations skill with templates
- [ ] Create exploration planning agent
- [ ] Implement legal compliance agent with full Kenya Mining Act

### Phase 5: Production (Weeks 17-20)
- [ ] Kubernetes deployment with autoscaling
- [ ] Monitoring and observability (LangSmith tracing)
- [ ] Security hardening (IP allowlisting, auth gateways)
- [ ] Performance optimization (context compaction tuning)
- [ ] Documentation and training for mining team

---

## 8. Key Architectural Decisions

### Decision 1: No Forking
**Rationale**: DeerFlow 2.0 is under active development (MIT license). Forking creates maintenance burden. All mining customization is done via configuration + plugins.
**Trade-off**: Some core behaviors can't be modified (e.g., middleware order). Acceptable because DeerFlow's architecture is already well-designed for extension.

### Decision 2: MCP for Complex Tools
**Rationale**: Geological modeling (GemPy), satellite processing (GEE), and quantum computing are complex Python ecosystems. Wrapping them as MCP servers keeps them isolated and independently deployable.
**Trade-off**: MCP adds a layer of indirection. But the isolation and standardization benefits outweigh this.

### Decision 3: Progressive Skill Loading for Domain Knowledge
**Rationale**: Mining knowledge is vast (geological surveys, regulatory texts, financial models). Progressive loading ensures only relevant knowledge enters the context window.
**Trade-off**: Agent must make good skill selection decisions. Mitigated by clear skill descriptions and orchestrator routing.

### Decision 4: Quantum as Sub-Agent, Not Core
**Rationale**: Quantum computing is experimental and slow. Running it as a sub-agent with extended timeout (30 min) keeps the main agent responsive.
**Trade-off**: Quantum results arrive asynchronously. Acceptable for optimization problems that aren't time-critical.

### Decision 5: Proprietary Knowledge as Files, Not Database
**Rationale**: DeerFlow's sandbox provides filesystem access. Storing knowledge as files (Markdown, JSON, GeoJSON) makes it accessible to agents without custom database queries. Vector search (Qdrant) provides semantic retrieval when needed.
**Trade-off**: File-based knowledge is less structured than database. Mitigated by consistent naming conventions and index files.

---

## 9. Competitive Moat Summary

| Moat Layer | What It Is | How It Compounds |
|-----------|-----------|-----------------|
| **Proprietary Data** | Geological surveys, mineral photos, assay results | More data → better models → more users → more data |
| **Domain Skills** | Mineral ID, geological modeling, NPV calculation | Refined by dedicated team over time |
| **Knowledge Base** | Kenya Mining Act, Migori geology, community protocols | Grows with every interaction |
| **Fine-tuned Models** | YOLOv8 mineral detector, geological NER | Improve with each correction |
| **Quantum Optimization** | Supply chain, logistics optimization | Unique capability competitors don't have |
| **Field Network** | Telegram-connected miners, geologists | Network effect — more users = more value |

**This is the flywheel. Every mineral photo identified makes the next one more accurate. Every geological observation enriches the knowledge base. Every market transaction sharpens the predictions. The superagent gets smarter with use — that's the competitive moat Jensen describes.**
