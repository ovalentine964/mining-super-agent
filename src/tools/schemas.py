"""
Pydantic Schemas for All Tool Inputs and Outputs
=================================================

Provides runtime argument validation for every tool in the registry.
Each tool's handler receives validated input and returns validated output.
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


# =========================================================================
# GEOLOGICAL TOOLS
# =========================================================================

class GemPyInput(BaseModel):
    """Input for GemPy 3D geological model."""
    extent: list[float] = Field(..., description="[xmin, xmax, ymin, ymax, zmin, zmax]")
    resolution: list[int] = Field(default=[50, 50, 50], description="[nx, ny, nz]")
    surface_points: Optional[list[dict[str, Any]]] = None
    orientation_data: Optional[list[dict[str, Any]]] = None


class GemPyOutput(BaseModel):
    """Output from GemPy 3D model."""
    success: bool
    model_extent: Optional[list[float]] = None
    resolution: Optional[list[int]] = None
    lithological_units: Optional[list[dict[str, Any]]] = None
    note: Optional[str] = None
    error: Optional[str] = None
    mock_result: Optional[dict[str, Any]] = None


class SimPEGInput(BaseModel):
    """Input for SimPEG geophysical inversion."""
    data_type: str = Field(..., description="'magnetic', 'resistivity', or 'gravity'")
    data_path: Optional[str] = None
    mesh_size: int = 64
    inversion_type: str = "susceptibility"


class SimPEGOutput(BaseModel):
    """Output from SimPEG inversion."""
    success: bool
    data_type: Optional[str] = None
    inversion_type: Optional[str] = None
    mesh_cells: Optional[int] = None
    note: Optional[str] = None
    error: Optional[str] = None
    mock_result: Optional[dict[str, Any]] = None


class MindatInput(BaseModel):
    """Input for Mindat query."""
    latitude: float
    longitude: float
    radius_km: float = 25
    mineral: Optional[str] = None
    api_key: Optional[str] = None


class MindatOutput(BaseModel):
    """Output from Mindat query."""
    success: bool
    query: Optional[dict[str, Any]] = None
    results: Optional[list[dict[str, Any]]] = None
    total: Optional[int] = None
    source: Optional[str] = None
    error: Optional[str] = None
    fallback: Optional[str] = None


class USGSMRDSInput(BaseModel):
    """Input for USGS MRDS query."""
    latitude: float
    longitude: float
    radius_km: float = 50
    commodity: Optional[str] = None


class USGSMRDSOutput(BaseModel):
    """Output from USGS MRDS query."""
    success: bool
    query: Optional[dict[str, Any]] = None
    results: Optional[list[dict[str, Any]]] = None
    total: Optional[int] = None
    source: Optional[str] = None
    error: Optional[str] = None


class GeologicalDBInput(BaseModel):
    """Input for geological database query."""
    latitude: float
    longitude: float
    radius_km: float = 10
    query_type: str = "all"


class GeologicalDBOutput(BaseModel):
    """Output from geological database query."""
    success: bool
    location: Optional[dict[str, float]] = None
    radius_km: Optional[float] = None
    query_type: Optional[str] = None
    results: Optional[dict[str, Any]] = None
    data_sources: Optional[list[str]] = None


# =========================================================================
# SATELLITE TOOLS
# =========================================================================

class Sentinel2Input(BaseModel):
    """Input for Sentinel-2 download."""
    latitude: float
    longitude: float
    start_date: str
    end_date: str
    cloud_cover_max: float = 20
    buffer_km: float = 5


class Sentinel2Output(BaseModel):
    """Output from Sentinel-2 download."""
    success: bool
    imagery_id: Optional[str] = None
    date: Optional[str] = None
    cloud_cover: Optional[float] = None
    bands_available: Optional[list[str]] = None
    download_urls: Optional[dict[str, str]] = None
    total_results: Optional[int] = None
    source: Optional[str] = None
    error: Optional[str] = None
    install: Optional[str] = None


class NDVIInput(BaseModel):
    """Input for NDVI calculation."""
    nir_band: Any
    red_band: Any


class SpectralIndexOutput(BaseModel):
    """Output from any spectral index calculation."""
    index: str
    formula: str
    statistics: dict[str, float]
    interpretation: Optional[str] = None
    anomaly_threshold: Optional[float] = None


class CloudCoverInput(BaseModel):
    """Input for cloud cover check."""
    latitude: float
    longitude: float
    date: str


class CloudCoverOutput(BaseModel):
    """Output from cloud cover check."""
    success: bool
    date: Optional[str] = None
    cloud_cover_pct: Optional[float] = None
    usable: Optional[bool] = None
    assessment: Optional[str] = None
    error: Optional[str] = None
    install: Optional[str] = None


# =========================================================================
# VISION TOOLS (Mineral Photo ID, XRF)
# =========================================================================

class MineralPhotoInput(BaseModel):
    """Input for mineral identification from photo."""
    image_bytes: bytes
    description: str = ""
    location: Optional[dict[str, float]] = None


class MineralPhotoOutput(BaseModel):
    """Output from mineral photo identification."""
    mineral: str
    confidence: float
    method: str
    disclaimers: list[str]
    is_economic: bool
    requires_expert_review: bool = False
    look_alikes: list[str] = Field(default_factory=list)
    swahili_summary: str = ""


class XRFInput(BaseModel):
    """Input for XRF spectral analysis."""
    spectral_data: list[float]
    element_concentrations: Optional[dict[str, float]] = None


class XFROutput(BaseModel):
    """Output from XRF analysis."""
    mineral: Optional[str] = None
    confidence: Optional[float] = None
    method: str
    elements: Optional[dict[str, float]] = None
    disclaimers: list[str] = Field(default_factory=list)
    is_economic: Optional[bool] = None
    requires_expert_review: Optional[bool] = None
    raw_data: Optional[list[float]] = None
    note: Optional[str] = None


# =========================================================================
# MARKET TOOLS
# =========================================================================

class CommodityPriceInput(BaseModel):
    """Input for commodity price query."""
    commodity: str
    currency: str = "USD"


class CommodityPriceOutput(BaseModel):
    """Output from commodity price query."""
    success: bool
    commodity: Optional[str] = None
    symbol: Optional[str] = None
    price_usd: Optional[float] = None
    currency: Optional[str] = None
    source: Optional[str] = None
    timestamp: Optional[str] = None
    cached: Optional[bool] = None
    error: Optional[str] = None
    install: Optional[str] = None


class PriceHistoryInput(BaseModel):
    """Input for price history query."""
    commodity: str
    period: str = "1y"
    interval: str = "1mo"


class PriceHistoryOutput(BaseModel):
    """Output from price history query."""
    success: bool
    commodity: Optional[str] = None
    period: Optional[str] = None
    interval: Optional[str] = None
    data_points: Optional[list[dict[str, Any]]] = None
    summary: Optional[dict[str, Any]] = None
    error: Optional[str] = None


# =========================================================================
# LEGAL TOOLS
# =========================================================================

class MiningActInput(BaseModel):
    """Input for Mining Act query."""
    query: str


class MiningActOutput(BaseModel):
    """Output from Mining Act query."""
    act: str
    relevant_sections: list[dict[str, Any]]
    disclaimer: str
    swahili_summary: str


class LicensingInput(BaseModel):
    """Input for licensing info query."""
    license_type: str = "artisanal"


class LicensingOutput(BaseModel):
    """Output from licensing info query."""
    license_type: str
    details: dict[str, Any]
    disclaimer: str
    swahili_summary: str


# =========================================================================
# FINANCIAL TOOLS
# =========================================================================

class NPVInput(BaseModel):
    """Input for NPV/IRR calculation."""
    mineral: str
    annual_production_kg: float
    price_per_kg: float
    capex: float
    opex_annual: float
    mine_life_years: int = 10
    discount_rate: float = 0.15
    recovery_rate: float = 0.75


class NPVOutput(BaseModel):
    """Output from NPV/IRR calculation."""
    mineral: str
    npv: float
    irr: Optional[float] = None
    payback_years: Optional[float] = None
    annual_revenue: float
    annual_profit: float
    capex: float
    opex_annual: float
    mine_life_years: int
    discount_rate: float
    recovery_rate: float
    sensitivity: dict[str, float]
    assumptions: dict[str, str]
    disclaimer: str
    disclaimer_en: str
    swahili_summary: str


class ValueEstimateInput(BaseModel):
    """Input for mineral value estimation."""
    mineral: str
    estimated_kg: float
    price_per_kg: float
    confidence: float = 0.5


class ValueEstimateOutput(BaseModel):
    """Output from mineral value estimation."""
    mineral: str
    estimated_kg: float
    effective_kg: float
    confidence: float
    price_per_kg: float
    gross_value_usd: float
    gross_value_kes: float
    net_value_usd: float
    net_value_kes: float
    note: str
    disclaimer: str
    swahili_summary: str


# =========================================================================
# QUANTUM TOOLS
# =========================================================================

class QuantumKernelInput(BaseModel):
    """Input for quantum kernel classification."""
    data_point: list[float]
    reference_points: dict[str, list[float]]
    n_qubits: int = 4


class QuantumKernelOutput(BaseModel):
    """Output from quantum kernel classification."""
    success: bool
    method: Optional[str] = None
    n_qubits: Optional[int] = None
    probabilities: Optional[dict[str, float]] = None
    best_match: Optional[str] = None
    confidence: Optional[float] = None
    error: Optional[str] = None
    install: Optional[str] = None
    fallback: Optional[str] = None


class QAOAInput(BaseModel):
    """Input for QAOA optimization."""
    cost_matrix: list[list[float]]
    num_select: int
    p_layers: int = 2


class QAOAOutput(BaseModel):
    """Output from QAOA optimization."""
    success: bool
    method: Optional[str] = None
    n_qubits: Optional[int] = None
    p_layers: Optional[int] = None
    selected_indices: Optional[list[int]] = None
    total_score: Optional[float] = None
    shots: Optional[int] = None
    error: Optional[str] = None
    install: Optional[str] = None
    fallback: Optional[str] = None


class ClassicalMineralClassifyInput(BaseModel):
    """Input for classical mineral classification."""
    spectral_data: list[float]
    reference_spectra: dict[str, list[float]]


class ClassicalMineralClassifyOutput(BaseModel):
    """Output from classical mineral classification."""
    success: bool
    method: str
    probabilities: dict[str, float]
    best_match: str
    confidence: float
    note: Optional[str] = None


class GreedyOptimizeInput(BaseModel):
    """Input for greedy optimization."""
    items: list[dict[str, Any]]
    num_select: int


class GreedyOptimizeOutput(BaseModel):
    """Output from greedy optimization."""
    success: bool
    method: str
    selected: list[dict[str, Any]]
    total_score: float
    note: Optional[str] = None


# =========================================================================
# REPORT TOOLS
# =========================================================================

class ReportInput(BaseModel):
    """Input for PDF report generation."""
    title: str
    language: str = "sw"
    mineral_analysis: Optional[dict[str, Any]] = None
    geological_data: Optional[dict[str, Any]] = None
    market_data: Optional[dict[str, Any]] = None
    financial_data: Optional[dict[str, Any]] = None
    legal_data: Optional[dict[str, Any]] = None
    location: Optional[dict[str, float]] = None


class ReportOutput(BaseModel):
    """Output from PDF report generation."""
    pdf_bytes: Any
    title: str
    language: str
    sections: list[str]
    disclaimer: str
