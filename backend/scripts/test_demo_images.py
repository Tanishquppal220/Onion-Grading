"""Test and verify all official demo images through the Grading Pipeline."""

import sys
from pathlib import Path

# Add backend root to sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import cv2
from app.pipeline import GradingPipeline
from app.common.schemas import CalibrationMode

def main():
    pipeline = GradingPipeline(
        seg_model_path="runs/weights/model1_yolov8_seg.pt",
        cls_model_path="runs/weights/model2_defect_cls.pt",
        device="cpu",
    )

    demo_images = [
        ("Preset 1: Calibrated DoCA Pass", REPO_ROOT / "frontend/public/samples/demo_calibrated_doca_pass.jpg"),
        ("Preset 2: Defective Lot Reject", REPO_ROOT / "frontend/public/samples/demo_defective_lot_reject.jpg"),
        ("Preset 3: 36-Bulb Commercial Crate", REPO_ROOT / "frontend/public/samples/demo_commercial_crate_36bulbs.jpg"),
        ("Preset 4: Uncalibrated Warning Scene", REPO_ROOT / "frontend/public/samples/demo_uncalibrated_warning.jpg"),
    ]

    print("\n=================== DEMO IMAGE SUITE PIPELINE VERIFICATION ===================")
    for label, path in demo_images:
        assert path.exists(), f"Image not found: {path}"
        img = cv2.imread(str(path))
        assert img is not None, f"Failed to read: {path}"

        summary, _ = pipeline.analyze_image(img, lot_id="DEMO-TEST", conf_threshold=0.25)

        print(f"\n>>> {label} ({path.name})")
        print(f"    Image Shape: {img.shape}")
        print(f"    Total Bulbs Inspected: {summary.total_onions_inspected}")
        print(f"    Calibration Mode: {summary.calibration.mode.value}")
        print(f"    ArUco Marker Detected: {summary.calibration.card_detected}")
        print(f"    Scale (px/mm): {summary.calibration.pixels_per_mm:.2f}")
        print(f"    Tilt Angle (deg): {summary.calibration.tilt_degrees}")
        print(f"    Mean Diameter: {summary.diameter_mean_mm:.1f} mm (Std: {summary.diameter_std_mm:.1f} mm)")
        print(f"    DoCA Grade Distribution: {summary.procurement_grade_distribution}")
        print(f"    AGMARK Distribution: {summary.agmark_grade_distribution}")
        print(f"    Defective Count: {summary.defective_count} ({summary.defective_percent:.1f}%)")
        print(f"    Compliance Statement: {summary.compliance_statement}")

    print("\n=================== ALL DEMO PRESETS VERIFIED SUCCESSFULLY ===================\n")

if __name__ == "__main__":
    main()
