"""Unit tests for the multi-standard onion grading rule engine.

Covers DoCA buffer-stock (45-65mm norm), AGMARK bands, defect priorities,
weight estimation, and lot aggregation compliance statements.
"""

import pytest
from app.common.schemas import (
    CalibrationMetadata,
    CalibrationMode,
    OnionMeasurements,
    OnionRecord,
    QualityFlags,
)
from app.common.rule_engine import (
    estimate_weight_grams,
    evaluate_onion_grades,
    summarize_lot,
)


def test_doca_grade_a_pass():
    measurements = OnionMeasurements(
        equatorial_diameter_mm=55.0,
        height_mm=54.0,
        estimated_weight_g=85.0,
        defect_area_percent=1.5,
    )
    flags = QualityFlags(sprouted=False, rotten=False, severe_damage=False)
    result = evaluate_onion_grades(measurements, flags)

    assert result.procurement_grade == "Grade-A"
    assert result.agmark_grade == "Grade-A (Large)"
    assert "Sound, mature, practically free from defects" in result.remarks
    assert "complies with DoCA 45-65 mm norm" in result.remarks


def test_doca_boundary_conditions():
    # Exactly 45.0 mm -> Grade-A
    res_45 = evaluate_onion_grades(
        OnionMeasurements(equatorial_diameter_mm=45.0, defect_area_percent=0.0),
        QualityFlags(),
    )
    assert res_45.procurement_grade == "Grade-A"

    # 44.9 mm -> Undersized
    res_44_9 = evaluate_onion_grades(
        OnionMeasurements(equatorial_diameter_mm=44.9, defect_area_percent=0.0),
        QualityFlags(),
    )
    assert res_44_9.procurement_grade == "Non-Grade-A (Undersized)"

    # Exactly 65.0 mm -> Grade-A
    res_65 = evaluate_onion_grades(
        OnionMeasurements(equatorial_diameter_mm=65.0, defect_area_percent=0.0),
        QualityFlags(),
    )
    assert res_65.procurement_grade == "Grade-A"

    # 65.1 mm -> Oversized
    res_65_1 = evaluate_onion_grades(
        OnionMeasurements(equatorial_diameter_mm=65.1, defect_area_percent=0.0),
        QualityFlags(),
    )
    assert res_65_1.procurement_grade == "Non-Grade-A (Oversized)"


def test_defect_rejections_and_priority():
    # Rotting takes priority and rejects
    res_rot = evaluate_onion_grades(
        OnionMeasurements(equatorial_diameter_mm=52.0, defect_area_percent=1.0),
        QualityFlags(rotten=True, sprouted=True),
    )
    assert res_rot.procurement_grade == "Reject (Rotten)"
    assert "rot/decay detected" in res_rot.remarks

    # Sprouting rejects
    res_sprout = evaluate_onion_grades(
        OnionMeasurements(equatorial_diameter_mm=52.0, defect_area_percent=1.0),
        QualityFlags(sprouted=True),
    )
    assert res_sprout.procurement_grade == "Reject (Sprouted)"

    # Mechanical damage rejects
    res_dam = evaluate_onion_grades(
        OnionMeasurements(equatorial_diameter_mm=52.0, defect_area_percent=1.0),
        QualityFlags(severe_damage=True),
    )
    assert res_dam.procurement_grade == "Reject (Damaged)"

    # Excessive discolouration (>5%) rejects Grade-A
    res_disc = evaluate_onion_grades(
        OnionMeasurements(equatorial_diameter_mm=52.0, defect_area_percent=8.0),
        QualityFlags(),
    )
    assert res_disc.procurement_grade == "Reject (Damaged)"
    assert "exceeds Grade-A 5% threshold" in res_disc.remarks


def test_agmark_size_tiers():
    # Premium: > 65mm
    p = evaluate_onion_grades(OnionMeasurements(equatorial_diameter_mm=70.0, defect_area_percent=0.0), QualityFlags())
    assert p.agmark_grade == "Premium / Extra Large"

    # Grade B: 35 - 45mm
    b = evaluate_onion_grades(OnionMeasurements(equatorial_diameter_mm=40.0, defect_area_percent=0.0), QualityFlags())
    assert b.agmark_grade == "Grade-B (Medium)"

    # Grade C: < 35mm
    c = evaluate_onion_grades(OnionMeasurements(equatorial_diameter_mm=30.0, defect_area_percent=0.0), QualityFlags())
    assert c.agmark_grade == "Grade-C (Small)"


def test_weight_estimation():
    # 55mm spherical bulb
    w55 = estimate_weight_grams(55.0)
    assert 80.0 <= w55 <= 95.0

    # 60mm bulb
    w60 = estimate_weight_grams(60.0)
    assert 105.0 <= w60 <= 120.0


def test_lot_summary_calibrated_and_uncalibrated():
    calib_ok = CalibrationMetadata(
        mode=CalibrationMode.CALIBRATED_ARUCO,
        scale_source="aruco_dict_0_50mm",
        mm_reliable=True,
        card_detected=True,
        tilt_degrees=5.0,
        pixels_per_mm=12.5,
    )

    onions = [
        OnionRecord(
            onion_id="ONION_1",
            bbox=[100, 100, 200, 200],
            confidence=0.95,
            measurements=OnionMeasurements(equatorial_diameter_mm=50.0, defect_area_percent=1.0, estimated_weight_g=80.0),
            quality_flags=QualityFlags(),
            grades=evaluate_onion_grades(OnionMeasurements(equatorial_diameter_mm=50.0, defect_area_percent=1.0), QualityFlags()),
        ),
        OnionRecord(
            onion_id="ONION_2",
            bbox=[300, 100, 400, 200],
            confidence=0.92,
            measurements=OnionMeasurements(equatorial_diameter_mm=60.0, defect_area_percent=2.0, estimated_weight_g=110.0),
            quality_flags=QualityFlags(),
            grades=evaluate_onion_grades(OnionMeasurements(equatorial_diameter_mm=60.0, defect_area_percent=2.0), QualityFlags()),
        ),
        OnionRecord(
            onion_id="ONION_3",
            bbox=[500, 100, 600, 200],
            confidence=0.88,
            measurements=OnionMeasurements(equatorial_diameter_mm=70.0, defect_area_percent=0.0, estimated_weight_g=170.0),
            quality_flags=QualityFlags(),
            grades=evaluate_onion_grades(OnionMeasurements(equatorial_diameter_mm=70.0, defect_area_percent=0.0), QualityFlags()),
        ),
    ]

    # Calibrated summary
    summary_ok = summarize_lot("LOT_001", "CENTER_NASHIK", "2026-09-20T10:00:00Z", calib_ok, onions)
    assert summary_ok.total_onions_inspected == 3
    assert summary_ok.diameter_mean_mm == 60.0
    assert summary_ok.procurement_grade_distribution["Grade-A"] == 66.7
    assert "qualifies as Grade-A for DoCA buffer-stock procurement" in summary_ok.compliance_statement

    # Uncalibrated summary
    calib_uncal = CalibrationMetadata(
        mode=CalibrationMode.ASSUMED_SCALE,
        scale_source="median_onion_prior_55mm",
        mm_reliable=False,
        card_detected=False,
        tilt_degrees=None,
        pixels_per_mm=10.0,
    )
    summary_uncal = summarize_lot("LOT_002", "CENTER_NASHIK", "2026-09-20T10:00:00Z", calib_uncal, onions)
    assert "UNCALIBRATED LOT (size estimates only)" in summary_uncal.compliance_statement
    assert "Indicative only" in summary_uncal.compliance_statement
