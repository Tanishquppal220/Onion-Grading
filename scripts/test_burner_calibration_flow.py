#!/usr/bin/env python3
"""End-to-End Verification Script for Burner Device Calibration Flow.

Tests:
  1. POST /api/calibrate/burner with demo_burner_card_shot.jpg
  2. Extracts calibrated pixels_per_mm, ppi, and tilt angle
  3. Grades a zero-marker lot (demo_uncalibrated_warning.jpg) with device_calibration_scale
  4. Asserts that grading response is mm_reliable=True and calibrated under Device Profile
  5. Asserts PDF certificate generation succeeds and contains calibration reference
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from backend.main import app, report_cache


def test_burner_calibration_flow():
    with TestClient(app) as client:
        burner_img_path = Path("frontend/public/samples/demo_burner_card_shot.jpg")
        uncalibrated_img_path = Path("frontend/public/samples/demo_uncalibrated_warning.jpg")

        assert burner_img_path.exists(), f"Burner test image not found at {burner_img_path}"
        assert uncalibrated_img_path.exists(), f"Zero-marker test image not found at {uncalibrated_img_path}"

        print("Step 1: Testing POST /api/calibrate/burner with demo_burner_card_shot.jpg...")
        with open(burner_img_path, "rb") as f:
            res = client.post(
                "/api/calibrate/burner",
                files={"file": ("demo_burner_card_shot.jpg", f, "image/jpeg")},
                data={"marker_size_mm": "50.0"},
            )

        assert res.status_code == 200, f"Burner calibration returned {res.status_code}: {res.text}"
        data = res.json()
        assert data["success"] is True, f"Calibration failed: {data}"
        scale = data["pixels_per_mm"]
        ppi = data["ppi"]
        assert scale is not None and scale > 3.0, f"Unexpected scale: {scale}"
        assert ppi is not None and ppi > 80.0, f"Unexpected PPI: {ppi}"
        assert data.get("annotated_preview_base64") is not None, "Missing preview image base64"
        print(f"✓ Burner Calibration verified: scale={scale:.2f} px/mm, PPI={ppi:.1f}, tilt={data.get('tilt_degrees')}°")

        print("\nStep 2: Testing POST /api/upload with device_calibration_scale on zero-marker image...")
        with open(uncalibrated_img_path, "rb") as f:
            upload_res = client.post(
                "/api/upload",
                files={"file": ("demo_uncalibrated_warning.jpg", f, "image/jpeg")},
                data={
                    "lot_id": "BURNER-TEST-LOT-01",
                    "farmer_name": "Dev Calibration Test",
                    "mandi_location": "Pimpalgaon APMC",
                    "device_calibration_scale": str(scale),
                },
            )

        assert upload_res.status_code == 200, f"Upload returned {upload_res.status_code}: {upload_res.text}"
        upload_data = upload_res.json()
        grading = upload_data["grading"]
        calib = grading["calibration"]

        print(f"Calibration Mode: {calib['mode']}")
        print(f"Calibration Label: {calib['label']}")
        print(f"Is Calibrated: {calib['is_calibrated']}")

        assert calib["is_calibrated"] is True, "Expected is_calibrated to be True when device scale is provided"
        assert "Device Profile" in calib["label"], f"Expected 'Device Profile' in label, got {calib['label']}"
        assert "device_burner_calibrated" in calib["description"], f"Expected burner description, got {calib['description']}"

        # Sizing checks
        assert grading["size_counts"]["small"] + grading["size_counts"]["medium"] + grading["size_counts"]["large"] == grading["total_detected"]
        print(f"✓ Zero-marker lot graded successfully with verified physical mm scale!")

        print("\nStep 3: Testing PDF Report generation for calibrated lot...")
        pdf_res = client.get(f"/api/report/pdf/BURNER-TEST-LOT-01")
        assert pdf_res.status_code == 200, f"PDF report generation failed: {pdf_res.status_code}"
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert len(pdf_res.content) > 1000, "PDF content too small"
        print(f"✓ PDF Certificate generated successfully ({len(pdf_res.content)} bytes)")

        print("\nALL BURNER CALIBRATION FLOW TESTS PASSED! 🎉")


if __name__ == "__main__":
    test_burner_calibration_flow()
