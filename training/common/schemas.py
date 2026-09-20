"""Data contracts and Pydantic models for Onion Quality Assessment and Grading.

Corresponds to Report Structure.md and Grade Definitions.md.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CalibrationMode(str, Enum):
    CALIBRATED_ARUCO = "calibrated_aruco"
    ASSUMED_SCALE = "assumed_scale"


class CalibrationMetadata(BaseModel):
    mode: CalibrationMode = Field(..., description="Calibration mode used")
    scale_source: str = Field(..., description="Source of scale reference")
    mm_reliable: bool = Field(..., description="Whether millimeter measurements are verified by in-frame reference")
    card_detected: bool = Field(..., description="Whether ArUco card was successfully detected")
    tilt_degrees: Optional[float] = Field(None, description="Estimated camera tilt angle relative to marker normal")
    pixels_per_mm: Optional[float] = Field(None, description="Calculated scale in pixels per mm")


class OnionMeasurements(BaseModel):
    equatorial_diameter_mm: float = Field(..., description="Maximum diameter perpendicular to stem-root axis in mm")
    height_mm: Optional[float] = Field(None, description="Height along stem-root axis in mm")
    estimated_weight_g: Optional[float] = Field(None, description="Estimated bulb weight derived from diameter in grams")
    defect_area_percent: float = Field(..., description="Discoloured or damaged surface area as % of visible surface")


class QualityFlags(BaseModel):
    sprouted: bool = Field(False, description="Flagged for green sprout or visible shoot")
    rotten: bool = Field(False, description="Flagged for wet rot, soft rot, or fungal decay")
    severe_damage: bool = Field(False, description="Mechanical cut, puncture, or deep bruise")
    # Note: double_bulb dropped from v1 per Dataset Plan §9


class GradesResult(BaseModel):
    procurement_grade: str = Field(..., description="DoCA buffer-stock grade ('A' or 'Non-Grade-A')")
    agmark_grade: str = Field(..., description="AGMARK commercial grade ('Premium', 'A', 'B', 'C', or 'Reject')")
    export_grade: str = Field(..., description="Export target grade classification")
    remarks: str = Field(..., description="Audit remarks using FSSAI fruit & vegetable standards wording")


class OnionRecord(BaseModel):
    onion_id: str = Field(..., description="Unique identifier for onion instance in lot")
    bbox: List[float] = Field(..., description="Bounding box [x1, y1, x2, y2] in image pixels")
    confidence: float = Field(..., description="Detection confidence score from Model 1")
    measurements: OnionMeasurements
    quality_flags: QualityFlags
    grades: GradesResult


class LotReportSummary(BaseModel):
    lot_id: str = Field(..., description="Unique inspection lot identifier")
    center_id: str = Field(..., description="Procurement center or packhouse ID")
    timestamp: str = Field(..., description="ISO 8601 inspection timestamp")
    calibration: CalibrationMetadata
    total_onions_inspected: int = Field(..., ge=0)
    estimated_lot_weight_kg: Optional[float] = None
    procurement_grade_distribution: Dict[str, float] = Field(
        ..., description="Percentage of lot meeting each procurement grade"
    )
    agmark_grade_distribution: Dict[str, float] = Field(
        ..., description="Percentage of lot meeting each AGMARK grade"
    )
    diameter_mean_mm: float = Field(..., ge=0)
    diameter_std_mm: float = Field(..., ge=0)
    defective_count: int = Field(..., ge=0)
    defective_percent: float = Field(..., ge=0, le=100)
    compliance_statement: str = Field(..., description="Human-auditable regulatory compliance statement")
    onions: List[OnionRecord] = Field(default_factory=list)
