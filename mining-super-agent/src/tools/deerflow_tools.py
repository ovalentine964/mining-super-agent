"""
DeerFlow Tool Adapters — Mining tools wrapped for DeerFlow's tool system.

Each tool is a LangChain BaseTool that DeerFlow can discover and use.
The actual implementation logic lives in the existing src/tools/* modules;
these adapters bridge them into DeerFlow's format.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional, Type

from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Input schemas for each tool
# ---------------------------------------------------------------------------

class GeologicalQueryInput(BaseModel):
    """Input for geological database query."""
    query: str = Field(description="Natural language query about geology, rock units, minerals, or structures")
    latitude: Optional[float] = Field(default=None, description="Latitude of the area of interest")
    longitude: Optional[float] = Field(default=None, description="Longitude of the area of interest")
    radius_km: float = Field(default=10.0, description="Search radius in kilometers")


class GemPyModelInput(BaseModel):
    """Input for GemPy 3D geological model."""
    latitude: float = Field(description="Center latitude")
    longitude: float = Field(description="Center longitude")
    extent_km: float = Field(default=5.0, description="Model extent in kilometers")
    depth_m: float = Field(default=500.0, description="Model depth in meters")


class MindatQueryInput(BaseModel):
    """Input for Mindat mineral occurrence query."""
    mineral: str = Field(description="Mineral name to search for")
    latitude: Optional[float] = Field(default=None, description="Center latitude")
    longitude: Optional[float] = Field(default=None, description="Center longitude")
    radius_km: float = Field(default=50.0, description="Search radius in kilometers")


class GeophysicalInversionInput(BaseModel):
    """Input for geophysical inversion."""
    latitude: float = Field(description="Center latitude")
    longitude: float = Field(description="Center longitude")
    method: str = Field(default="gravity", description="Inversion method: gravity, magnetic, or em")
    data_path: Optional[str] = Field(default=None, description="Path to geophysical data file")


class Sentinel2Input(BaseModel):
    """Input for Sentinel-2 satellite data query."""
    latitude: float = Field(description="Center latitude")
    longitude: float = Field(description="Center longitude")
    date_from: Optional[str] = Field(default=None, description="Start date (YYYY-MM-DD)")
    date_to: Optional[str] = Field(default=None, description="End date (YYYY-MM-DD)")
    cloud_cover_max: float = Field(default=20.0, description="Maximum cloud cover percentage")


class SpectralIndicesInput(BaseModel):
    """Input for spectral index calculation."""
    latitude: float = Field(description="Center latitude")
    longitude: float = Field(description="Center longitude")
    indices: list[str] = Field(default=["NDVI", "NDWI", "Ferric_Oxide"], description="Spectral indices to calculate")


class AlterationZonesInput(BaseModel):
    """Input for alteration zone detection."""
    latitude: float = Field(description="Center latitude")
    longitude: float = Field(description="Center longitude")
    extent_km: float = Field(default=10.0, description="Area extent in kilometers")


class MineralPhotoInput(BaseModel):
    """Input for mineral photo identification."""
    image_path: str = Field(description="Path to the mineral photo")
    location_hint: Optional[str] = Field(default=None, description="Location hint for context")


class ClipClassifyInput(BaseModel):
    """Input for CLIP-based mineral classification."""
    image_path: str = Field(description="Path to the image")
    candidate_labels: list[str] = Field(
        default=["quartz", "feldspar", "mica", "calcite", "pyrite", "galena", "magnetite", "hematite", "gold", "copper ore"],
        description="Candidate mineral labels"
    )


class CommodityPriceInput(BaseModel):
    """Input for commodity price lookup."""
    commodity: str = Field(description="Commodity name (gold, copper, silver, etc.)")
    currency: str = Field(default="USD", description="Price currency")


class PriceHistoryInput(BaseModel):
    """Input for price history."""
    commodity: str = Field(description="Commodity name")
    period: str = Field(default="1y", description="Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 5y, max)")


class PriceTrendInput(BaseModel):
    """Input for price trend analysis."""
    commodity: str = Field(description="Commodity name")
    period: str = Field(default="1y", description="Analysis period")


class LicenseRequirementsInput(BaseModel):
    """Input for license requirement check."""
    mineral: str = Field(description="Target mineral")
    project_type: str = Field(description="Project type: exploration, small_scale, large_scale")
    county: str = Field(default="Migori", description="County in Kenya")


class EIARequirementsInput(BaseModel):
    """Input for EIA requirement check."""
    project_type: str = Field(description="Project type")
    mineral: str = Field(description="Target mineral")
    area_hectares: float = Field(default=100.0, description="Project area in hectares")


class FPICRequirementsInput(BaseModel):
    """Input for FPIC requirement check."""
    project_type: str = Field(description="Project type")
    community_type: str = Field(default="rural", description="Community type: rural, urban, pastoral")


class ComplianceChecklistInput(BaseModel):
    """Input for compliance checklist generation."""
    project_type: str = Field(description="Project type")
    mineral: str = Field(description="Target mineral")
    county: str = Field(default="Migori", description="County")


class NPVIRRInput(BaseModel):
    """Input for NPV/IRR calculation."""
    capex: float = Field(description="Capital expenditure in USD")
    annual_revenue: float = Field(description="Annual revenue in USD")
    annual_opex: float = Field(description="Annual operating expenditure in USD")
    project_years: int = Field(default=10, description="Project duration in years")
    discount_rate: float = Field(default=0.1, description="Discount rate (0-1)")


class CapexInput(BaseModel):
    """Input for CAPEX estimation."""
    mine_type: str = Field(description="Mine type: open_pit, underground, alluvial")
    tonnage_per_day: float = Field(description="Processing tonnage per day")
    mineral: str = Field(description="Target mineral")


class SensitivityInput(BaseModel):
    """Input for sensitivity analysis."""
    capex: float = Field(description="Base CAPEX")
    annual_revenue: float = Field(description="Base annual revenue")
    annual_opex: float = Field(description="Base annual OPEX")
    variable: str = Field(default="gold_price", description="Variable to analyze")
    range_pct: float = Field(default=20.0, description="Variation range percentage")


class StakeholderInput(BaseModel):
    """Input for stakeholder analysis."""
    project_type: str = Field(description="Project type")
    location: str = Field(description="Project location")
    mineral: str = Field(description="Target mineral")


class FPICGuidanceInput(BaseModel):
    """Input for FPIC guidance."""
    community_type: str = Field(description="Community type")
    project_stage: str = Field(default="exploration", description="Project stage")


class DrillingInput(BaseModel):
    """Input for drilling program design."""
    latitude: float = Field(description="Center latitude")
    longitude: float = Field(description="Center longitude")
    target_depth_m: float = Field(default=200.0, description="Target depth in meters")
    num_holes: int = Field(default=5, description="Number of drill holes")
    drill_type: str = Field(default="diamond", description="Drill type: diamond, RC, RAB")


class SamplingInput(BaseModel):
    """Input for sampling strategy design."""
    latitude: float = Field(description="Center latitude")
    longitude: float = Field(description="Center longitude")
    area_km2: float = Field(default=1.0, description="Area in square kilometers")
    sample_type: str = Field(default="soil", description="Sample type: soil, rock, stream_sediment")


class CrossCheckInput(BaseModel):
    """Input for cross-checking results."""
    results_summary: str = Field(description="Summary of results to cross-check")
    agents_involved: list[str] = Field(description="List of agents whose results are being checked")


class ValidateConfidenceInput(BaseModel):
    """Input for confidence validation."""
    finding: str = Field(description="The finding to validate")
    evidence: str = Field(description="Supporting evidence")
    claimed_confidence: float = Field(description="Claimed confidence score (0-1)")


class MiningReportInput(BaseModel):
    """Input for mining report generation."""
    title: str = Field(description="Report title")
    findings: str = Field(description="Key findings text")
    language: str = Field(default="english", description="Report language: english or swahili")
    report_type: str = Field(default="exploration", description="Report type: exploration, compliance, financial")


# ---------------------------------------------------------------------------
# Tool implementations (lazy-loaded from existing modules)
# ---------------------------------------------------------------------------

def _get_tool_handler(module_path: str, func_name: str):
    """Lazy-load a tool handler from the existing mining tools."""
    import importlib
    try:
        mod = importlib.import_module(module_path)
        return getattr(mod, func_name, None)
    except ImportError as e:
        logger.warning("Could not import %s.%s: %s", module_path, func_name, e)
        return None


class MiningTool(BaseTool):
    """Base class for mining tools that bridges to existing implementations."""

    module_path: str = ""
    func_name: str = ""

    def _run(
        self,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> str:
        """Execute the tool synchronously."""
        handler = _get_tool_handler(self.module_path, self.func_name)
        if handler is None:
            return f"Error: Tool handler {self.module_path}.{self.func_name} not available"

        try:
            if asyncio.iscoroutinefunction(handler):
                result = asyncio.get_event_loop().run_until_complete(handler(**kwargs))
            else:
                result = handler(**kwargs)
            return str(result)
        except Exception as e:
            logger.error("Tool %s failed: %s", self.name, e, exc_info=True)
            return f"Error executing {self.name}: {e}"


# ---------------------------------------------------------------------------
# Geological Tools
# ---------------------------------------------------------------------------

class QueryGeologicalDatabaseTool(MiningTool):
    name: str = "query_geological_database"
    description: str = "Query the geological database for rock units, minerals, structures, and geological context around a location in Kenya's Migori Greenstone Belt."
    args_schema: Type[BaseModel] = GeologicalQueryInput
    module_path: str = "src.tools.geological"
    func_name: str = "query_geological_database"


class RunGemPyModelTool(MiningTool):
    name: str = "run_gempy_model"
    description: str = "Run a GemPy 3D geological model for a given location to visualize subsurface geology and potential ore bodies."
    args_schema: Type[BaseModel] = GemPyModelInput
    module_path: str = "src.tools.geological"
    func_name: str = "run_gempy_model"


class QueryMindatTool(MiningTool):
    name: str = "query_mindat"
    description: str = "Query Mindat.org for mineral occurrence records near a location. Returns known mineral finds in the area."
    args_schema: Type[BaseModel] = MindatQueryInput
    module_path: str = "src.tools.geological"
    func_name: str = "query_mindat"


class RunGeophysicalInversionTool(MiningTool):
    name: str = "run_geophysical_inversion"
    description: str = "Run geophysical inversion (gravity, magnetic, or EM) to model subsurface density/susceptibility variations."
    args_schema: Type[BaseModel] = GeophysicalInversionInput
    module_path: str = "src.tools.geological"
    func_name: str = "run_geophysical_inversion"


# ---------------------------------------------------------------------------
# Satellite Tools
# ---------------------------------------------------------------------------

class QuerySentinel2Tool(MiningTool):
    name: str = "query_sentinel2"
    description: str = "Query Sentinel-2 satellite imagery for a location. Returns available scenes with cloud cover info."
    args_schema: Type[BaseModel] = Sentinel2Input
    module_path: str = "src.tools.satellite"
    func_name: str = "query_sentinel2"


class CalculateSpectralIndicesTool(MiningTool):
    name: str = "calculate_spectral_indices"
    description: str = "Calculate spectral indices (NDVI, NDWI, ferric oxide, clay minerals) from Sentinel-2 imagery for mineral exploration."
    args_schema: Type[BaseModel] = SpectralIndicesInput
    module_path: str = "src.tools.satellite"
    func_name: str = "calculate_spectral_indices"


class DetectAlterationZonesTool(MiningTool):
    name: str = "detect_alteration_zones"
    description: str = "Detect hydrothermal alteration zones from satellite spectral data — indicators of mineralization."
    args_schema: Type[BaseModel] = AlterationZonesInput
    module_path: str = "src.tools.satellite"
    func_name: str = "detect_alteration_zones"


# ---------------------------------------------------------------------------
# Mineral Identification Tools
# ---------------------------------------------------------------------------

class IdentifyMineralPhotoTool(MiningTool):
    name: str = "identify_mineral_photo"
    description: str = "Identify a mineral from a photo using AI vision models. Returns mineral ID, confidence, and look-alikes."
    args_schema: Type[BaseModel] = MineralPhotoInput
    module_path: str = "src.tools.vision"
    func_name: str = "identify_mineral_photo"


class ClassifyWithClipTool(MiningTool):
    name: str = "classify_with_clip"
    description: str = "Classify an image against candidate mineral labels using CLIP zero-shot classification."
    args_schema: Type[BaseModel] = ClipClassifyInput
    module_path: str = "src.tools.vision"
    func_name: str = "classify_with_clip"


# ---------------------------------------------------------------------------
# Market Data Tools
# ---------------------------------------------------------------------------

class GetCommodityPriceTool(MiningTool):
    name: str = "get_commodity_price"
    description: str = "Get the current price of a commodity (gold, copper, silver, etc.) in the specified currency."
    args_schema: Type[BaseModel] = CommodityPriceInput
    module_path: str = "src.tools.market"
    func_name: str = "get_commodity_price"


class GetPriceHistoryTool(MiningTool):
    name: str = "get_price_history"
    description: str = "Get historical price data for a commodity over a specified time period."
    args_schema: Type[BaseModel] = PriceHistoryInput
    module_path: str = "src.tools.market"
    func_name: str = "get_price_history"


class AnalyzePriceTrendTool(MiningTool):
    name: str = "analyze_price_trend"
    description: str = "Analyze price trends for a commodity — returns trend direction, moving averages, and volatility."
    args_schema: Type[BaseModel] = PriceTrendInput
    module_path: str = "src.tools.market"
    func_name: str = "analyze_price_trend"


# ---------------------------------------------------------------------------
# Legal & Compliance Tools
# ---------------------------------------------------------------------------

class CheckLicenseRequirementsTool(MiningTool):
    name: str = "check_license_requirements"
    description: str = "Check mining license requirements for a specific mineral and project type in Kenya."
    args_schema: Type[BaseModel] = LicenseRequirementsInput
    module_path: str = "src.tools.legal"
    func_name: str = "check_license_requirements"


class CheckEIARequirementsTool(MiningTool):
    name: str = "check_eia_requirements"
    description: str = "Check Environmental Impact Assessment (EIA) requirements for a mining project."
    args_schema: Type[BaseModel] = EIARequirementsInput
    module_path: str = "src.tools.legal"
    func_name: str = "check_eia_requirements"


class CheckFPICRequirementsTool(MiningTool):
    name: str = "check_fpic_requirements"
    description: str = "Check Free, Prior, and Informed Consent (FPIC) requirements for community engagement."
    args_schema: Type[BaseModel] = FPICRequirementsInput
    module_path: str = "src.tools.legal"
    func_name: str = "check_fpic_requirements"


class GenerateComplianceChecklistTool(MiningTool):
    name: str = "generate_compliance_checklist"
    description: str = "Generate a comprehensive compliance checklist for a mining project in Kenya."
    args_schema: Type[BaseModel] = ComplianceChecklistInput
    module_path: str = "src.tools.legal"
    func_name: str = "generate_compliance_checklist"


# ---------------------------------------------------------------------------
# Financial Tools
# ---------------------------------------------------------------------------

class CalculateNPVIRRTool(MiningTool):
    name: str = "calculate_npv_irr"
    description: str = "Calculate Net Present Value (NPV) and Internal Rate of Return (IRR) for a mining project."
    args_schema: Type[BaseModel] = NPVIRRInput
    module_path: str = "src.tools.financial"
    func_name: str = "calculate_npv_irr"


class EstimateCapexTool(MiningTool):
    name: str = "estimate_capex"
    description: str = "Estimate capital expenditure (CAPEX) for a mining project based on mine type and capacity."
    args_schema: Type[BaseModel] = CapexInput
    module_path: str = "src.tools.financial"
    func_name: str = "estimate_capex"


class SensitivityAnalysisTool(MiningTool):
    name: str = "sensitivity_analysis"
    description: str = "Run sensitivity analysis on a mining project's financials by varying key parameters."
    args_schema: Type[BaseModel] = SensitivityInput
    module_path: str = "src.tools.financial"
    func_name: str = "sensitivity_analysis"


# ---------------------------------------------------------------------------
# Community & Stakeholder Tools
# ---------------------------------------------------------------------------

class StakeholderAnalysisTool(MiningTool):
    name: str = "stakeholder_analysis"
    description: str = "Analyze stakeholders for a mining project — identifies key groups, interests, and engagement strategies."
    args_schema: Type[BaseModel] = StakeholderInput
    module_path: str = "src.tools.reports"
    func_name: str = "stakeholder_analysis"


class FPICGuidanceTool(MiningTool):
    name: str = "fpic_guidance"
    description: str = "Provide guidance on Free, Prior, and Informed Consent (FPIC) process and best practices."
    args_schema: Type[BaseModel] = FPICGuidanceInput
    module_path: str = "src.tools.reports"
    func_name: str = "fpic_guidance"


# ---------------------------------------------------------------------------
# Exploration Planning Tools
# ---------------------------------------------------------------------------

class DesignDrillingProgramTool(MiningTool):
    name: str = "design_drilling_program"
    description: str = "Design a drilling program for mineral exploration — hole locations, depths, and estimated costs."
    args_schema: Type[BaseModel] = DrillingInput
    module_path: str = "src.tools.geological"
    func_name: str = "design_drilling_program"


class DesignSamplingStrategyTool(MiningTool):
    name: str = "design_sampling_strategy"
    description: str = "Design a sampling strategy for mineral exploration — sample locations, types, and spacing."
    args_schema: Type[BaseModel] = SamplingInput
    module_path: str = "src.tools.geological"
    func_name: str = "design_sampling_strategy"


# ---------------------------------------------------------------------------
# Quality Control Tools
# ---------------------------------------------------------------------------

class CrossCheckResultsTool(MiningTool):
    name: str = "cross_check_results"
    description: str = "Cross-check results from multiple analysis agents for consistency and conflicts."
    args_schema: Type[BaseModel] = CrossCheckInput
    module_path: str = "src.tools.reports"
    func_name: str = "cross_check_results"


class ValidateConfidenceTool(MiningTool):
    name: str = "validate_confidence"
    description: str = "Validate whether a claimed confidence score is supported by the available evidence."
    args_schema: Type[BaseModel] = ValidateConfidenceInput
    module_path: str = "src.tools.reports"
    func_name: str = "validate_confidence"


# ---------------------------------------------------------------------------
# Report Generation Tools
# ---------------------------------------------------------------------------

class GenerateMiningReportTool(MiningTool):
    name: str = "generate_mining_report"
    description: str = "Generate a formatted mining report (PDF) with findings, maps, and recommendations. Supports English and Swahili."
    args_schema: Type[BaseModel] = MiningReportInput
    module_path: str = "src.tools.reports"
    func_name: str = "generate_mining_report"


# ---------------------------------------------------------------------------
# Tool instances — these are what DeerFlow discovers via config.yaml `use:` paths
# ---------------------------------------------------------------------------

# Geological
query_geological_database_tool = QueryGeologicalDatabaseTool()
run_gempy_model_tool = RunGemPyModelTool()
query_mindat_tool = QueryMindatTool()
run_geophysical_inversion_tool = RunGeophysicalInversionTool()

# Satellite
query_sentinel2_tool = QuerySentinel2Tool()
calculate_spectral_indices_tool = CalculateSpectralIndicesTool()
detect_alteration_zones_tool = DetectAlterationZonesTool()

# Mineral ID
identify_mineral_photo_tool = IdentifyMineralPhotoTool()
classify_with_clip_tool = ClassifyWithClipTool()

# Market
get_commodity_price_tool = GetCommodityPriceTool()
get_price_history_tool = GetPriceHistoryTool()
analyze_price_trend_tool = AnalyzePriceTrendTool()

# Legal
check_license_requirements_tool = CheckLicenseRequirementsTool()
check_eia_requirements_tool = CheckEIARequirementsTool()
check_fpic_requirements_tool = CheckFPICRequirementsTool()
generate_compliance_checklist_tool = GenerateComplianceChecklistTool()

# Financial
calculate_npv_irr_tool = CalculateNPVIRRTool()
estimate_capex_tool = EstimateCapexTool()
sensitivity_analysis_tool = SensitivityAnalysisTool()

# Community
stakeholder_analysis_tool = StakeholderAnalysisTool()
fpic_guidance_tool = FPICGuidanceTool()

# Exploration
design_drilling_program_tool = DesignDrillingProgramTool()
design_sampling_strategy_tool = DesignSamplingStrategyTool()

# QC
cross_check_results_tool = CrossCheckResultsTool()
validate_confidence_tool = ValidateConfidenceTool()

# Reports
generate_mining_report_tool = GenerateMiningReportTool()
