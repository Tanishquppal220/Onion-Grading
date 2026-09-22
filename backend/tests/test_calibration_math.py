"""Unit tests for the ArUco metric calibration module and mathematical correction.

Verifies ArUco marker detection, tilt estimation, height-above-plane compensation,
and fallback mode using synthetic benchmark scenes.
"""

import numpy as np
import pytest
from app.calibration.aruco_calibrator import ArUcoCalibrator
from app.common.schemas import CalibrationMode
from tests.fixtures.generate_synthetic_set import generate_synthetic_scene


def test_aruco_detection_and_scale():
    calibrator = ArUcoCalibrator(marker_size_mm=50.0)
    # Generate scene with 50mm diameter, 0 tilt, 450mm distance
    scene, gt = generate_synthetic_scene(true_diameter_mm=50.0, tilt_degrees=0.0, camera_distance_mm=450.0)

    found, corners, tilt_deg = calibrator.detect_marker(scene)
    assert found is True
    assert corners is not None
    assert corners.shape == (4, 2)
    assert tilt_deg is not None
    assert tilt_deg < 5.0  # Planar view


def test_recovered_diameter_accuracy():
    calibrator = ArUcoCalibrator(marker_size_mm=50.0)
    test_diameters = [45.0, 55.0, 65.0]

    for true_d in test_diameters:
        scene, gt = generate_synthetic_scene(
            true_diameter_mm=true_d,
            marker_size_mm=50.0,
            camera_distance_mm=450.0,
            tilt_degrees=0.0,
        )

        metadata, scale_px_per_mm = calibrator.calibrate(scene)
        assert metadata.card_detected is True
        assert metadata.mm_reliable is True

        apparent_px = gt["apparent_diameter_px"]
        recovered_d = calibrator.compute_corrected_diameter_mm(
            pixel_diameter=apparent_px,
            planar_scale_px_per_mm=scale_px_per_mm,
            camera_distance_mm=450.0,
        )

        # Allow small tolerance for discrete pixel rasterization (+/- 1.5 mm)
        error_mm = abs(recovered_d - true_d)
        assert error_mm <= 1.5, f"Expected ~{true_d} mm, got {recovered_d} mm (error {error_mm:.2f} mm)"


def test_calibration_fallback_mode():
    calibrator = ArUcoCalibrator(marker_size_mm=50.0)
    # Blank image with no marker
    blank_img = np.full((600, 800, 3), 200, dtype=np.uint8)

    # Simulated onion pixel diameters (e.g. median ~ 550 px)
    simulated_px_diameters = [520.0, 550.0, 580.0]

    metadata, scale = calibrator.calibrate(blank_img, detected_onion_pixel_diameters=simulated_px_diameters)

    assert metadata.card_detected is False
    assert metadata.mm_reliable is False
    assert metadata.mode == CalibrationMode.ASSUMED_SCALE
    assert "median_onion_prior_55.0mm" in metadata.scale_source
    # scale should be median_px / 55.0 = 550 / 55 = 10.0
    assert abs(scale - 10.0) < 0.1
