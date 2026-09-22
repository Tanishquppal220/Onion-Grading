"""Rule Engine for Onion Quality Assessment and Multi-Standard Grading.

Encodes DoCA Buffer-Stock Procurement Norms (reinstated 45-65 mm norm),
AGMARK / Export size band standards, and FSSAI fruit & vegetable defect tolerance wording.
"""

from __future__ import annotations

import math
from typing import List, Tuple
from .schemas import (
    CalibrationMetadata,
    GradesResult,
    LotReportSummary,
    OnionMeasurements,
    OnionRecord,
    QualityFlags,
)


# Standard thresholds per Grade Definitions.md
DOCA_MIN_DIAMETER_MM = 45.0
DOCA_MAX_DIAMETER_MM = 65.0
GRADE_A_MAX_DEFECT_PERCENT = 5.0
AGMARK_PREMIUM_MIN_MM = 65.0
AGMARK_A_MIN_MM = 45.0
AGMARK_B_MIN_MM = 35.0


def estimate_weight_grams(diameter_mm: float, height_mm: float | None = None) -> float:
    """Estimates onion bulb weight in grams based on equatorial diameter and height.
    
    Uses standard prolate/oblate ellipsoid volumetric model with onion fresh density ~ 0.98 g/cm^3.
    Ref: PMC8146908 diameter-weight correlation.
    """
    if diameter_mm <= 0:
        return 0.0
    h = height_mm if (height_mm is not None and height_mm > 0) else diameter_mm
    # Volume in mm^3 = (pi / 6) * D^2 * H
    volume_mm3 = (math.pi / 6.0) * (diameter_mm ** 2) * h
    volume_cm3 = volume_mm3 / 1000.0
    density_g_cm3 = 0.98
    return round(volume_cm3 * density_g_cm3, 1)


def evaluate_onion_grades(
    measurements: OnionMeasurements,
    flags: QualityFlags,
) -> GradesResult:
    """Evaluates an individual onion against DoCA buffer-stock, AGMARK, and Export rules."""
    d = measurements.equatorial_diameter_mm
    defect_pct = measurements.defect_area_percent

    is_rotten = flags.rotten
    is_sprouted = flags.sprouted
    is_damaged = flags.severe_damage

    has_severe_defect = is_rotten or is_sprouted or is_damaged or (defect_pct > 15.0)

    # 1. Procurement Grade (DoCA Buffer-Stock)
    if is_rotten:
        procurement_grade = "Reject (Rotten)"
    elif is_sprouted:
        procurement_grade = "Reject (Sprouted)"
    elif is_damaged or defect_pct > GRADE_A_MAX_DEFECT_PERCENT:
        procurement_grade = "Reject (Damaged)"
    elif DOCA_MIN_DIAMETER_MM <= d <= DOCA_MAX_DIAMETER_MM:
        procurement_grade = "Grade-A"
    elif d < DOCA_MIN_DIAMETER_MM:
        procurement_grade = "Non-Grade-A (Undersized)"
    else:
        procurement_grade = "Non-Grade-A (Oversized)"

    # 2. AGMARK Grade
    if is_rotten or is_damaged:
        agmark_grade = "Reject"
    elif is_sprouted:
        agmark_grade = "Reject (Sprouted)"
    elif d >= AGMARK_PREMIUM_MIN_MM:
        agmark_grade = "Premium / Extra Large"
    elif d >= AGMARK_A_MIN_MM:
        agmark_grade = "Grade-A (Large)"
    elif d >= AGMARK_B_MIN_MM:
        agmark_grade = "Grade-B (Medium)"
    else:
        agmark_grade = "Grade-C (Small)"

    # 3. Export Grade (destination size band mapping)
    if has_severe_defect:
        export_grade = "Reject"
    elif 55.0 <= d <= 65.0:
        export_grade = "Export Grade-1 (55-65mm Premium)"
    elif 45.0 <= d < 55.0:
        export_grade = "Export Grade-2 (45-55mm Standard)"
    elif d > 65.0:
        export_grade = "Export Jumbo (>65mm)"
    else:
        export_grade = "Domestic Fresh (<45mm)"

    # 4. FSSAI-style remarks
    remarks_list = []
    if is_rotten:
        remarks_list.append("Defective: rot/decay detected; forbidden under procurement norms")
    elif is_sprouted:
        remarks_list.append("Defective: sprouted bulb; forbidden under buffer-stock procurement norms")
    elif is_damaged:
        remarks_list.append("Defective: mechanical cut/puncture noticeably affecting appearance")
    elif defect_pct > GRADE_A_MAX_DEFECT_PERCENT:
        remarks_list.append(f"Surface blemish ({defect_pct:.1f}%) exceeds Grade-A 5% threshold")
    else:
        remarks_list.append("Sound, mature, practically free from defects")

    if DOCA_MIN_DIAMETER_MM <= d <= DOCA_MAX_DIAMETER_MM:
        remarks_list.append(f"Equatorial diameter {d:.1f} mm complies with DoCA 45-65 mm norm")
    else:
        remarks_list.append(f"Equatorial diameter {d:.1f} mm outside DoCA 45-65 mm norm")

    return GradesResult(
        procurement_grade=procurement_grade,
        agmark_grade=agmark_grade,
        export_grade=export_grade,
        remarks="; ".join(remarks_list),
    )


def summarize_lot(
    lot_id: str,
    center_id: str,
    timestamp: str,
    calibration: CalibrationMetadata,
    onions: List[OnionRecord],
) -> LotReportSummary:
    """Aggregates per-onion evaluation records into a complete lot-level audit report."""
    total = len(onions)
    if total == 0:
        return LotReportSummary(
            lot_id=lot_id,
            center_id=center_id,
            timestamp=timestamp,
            calibration=calibration,
            total_onions_inspected=0,
            estimated_lot_weight_kg=0.0,
            procurement_grade_distribution={},
            agmark_grade_distribution={},
            diameter_mean_mm=0.0,
            diameter_std_mm=0.0,
            defective_count=0,
            defective_percent=0.0,
            compliance_statement="Lot is empty; no onions inspected.",
            onions=[],
        )

    diameters = [o.measurements.equatorial_diameter_mm for o in onions]
    mean_d = sum(diameters) / total
    variance = sum((x - mean_d) ** 2 for x in diameters) / total
    std_d = math.sqrt(variance)

    total_weight_g = sum(o.measurements.estimated_weight_g or 0.0 for o in onions)
    lot_weight_kg = round(total_weight_g / 1000.0, 2)

    proc_dist: dict[str, int] = {}
    agmark_dist: dict[str, int] = {}
    defective_count = 0

    for o in onions:
        pg = o.grades.procurement_grade
        proc_dist[pg] = proc_dist.get(pg, 0) + 1

        ag = o.grades.agmark_grade
        agmark_dist[ag] = agmark_dist.get(ag, 0) + 1

        if (
            o.quality_flags.rotten
            or o.quality_flags.sprouted
            or o.quality_flags.severe_damage
            or o.measurements.defect_area_percent > GRADE_A_MAX_DEFECT_PERCENT
        ):
            defective_count += 1

    proc_pct = {k: round((v / total) * 100.0, 1) for k, v in proc_dist.items()}
    agmark_pct = {k: round((v / total) * 100.0, 1) for k, v in agmark_dist.items()}
    defective_pct = round((defective_count / total) * 100.0, 1)

    grade_a_proc_pct = proc_pct.get("Grade-A", 0.0)

    if not calibration.mm_reliable:
        compliance = (
            f"UNCALIBRATED LOT (size estimates only). {grade_a_proc_pct}% of sample estimated as Grade-A "
            f"for DoCA buffer-stock. Defect rate: {defective_pct}%. Audit status: Indicative only."
        )
    else:
        compliance = (
            f"{grade_a_proc_pct}% of lot qualifies as Grade-A for DoCA buffer-stock procurement "
            f"(45-65 mm norm, practically free from defects). Total inspected: {total}, mean diameter: {mean_d:.1f} mm "
            f"(std: {std_d:.1f} mm), defect rate: {defective_pct}%."
        )

    return LotReportSummary(
        lot_id=lot_id,
        center_id=center_id,
        timestamp=timestamp,
        calibration=calibration,
        total_onions_inspected=total,
        estimated_lot_weight_kg=lot_weight_kg,
        procurement_grade_distribution=proc_pct,
        agmark_grade_distribution=agmark_pct,
        diameter_mean_mm=round(mean_d, 2),
        diameter_std_mm=round(std_d, 2),
        defective_count=defective_count,
        defective_percent=defective_pct,
        compliance_statement=compliance,
        onions=onions,
    )
