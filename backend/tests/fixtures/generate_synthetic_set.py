"""Synthetic Calibration Generator.

Renders realistic synthetic calibration scenes containing an ArUco marker and simulated
onion bulbs with known true millimeter diameters, applying camera tilt, perspective warp,
and distance scaling. Used to mathematically verify calibration accuracy without manual measuring.
Ref: Dataset Plan.md §6.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Tuple
import cv2
import numpy as np


def draw_synthetic_onion(
    canvas: np.ndarray,
    center_xy: Tuple[int, int],
    radius_px: int,
    color_bgr: Tuple[int, int, int] = (40, 70, 160),  # Red-onion tone
) -> None:
    """Draws a synthetic onion bulb with slight elliptical irregularity and shading."""
    cx, cy = center_xy
    r = int(radius_px)
    axes = (r, int(r * 0.95))
    angle = 15
    # Base bulb ellipse
    cv2.ellipse(canvas, (cx, cy), axes, angle, 0, 360, color_bgr, -1)
    # Highlight to simulate spherical 3D shape
    cv2.circle(canvas, (cx - int(r * 0.25), cy - int(r * 0.25)), int(r * 0.35), (60, 95, 190), -1)


def generate_synthetic_scene(
    true_diameter_mm: float,
    marker_size_mm: float = 50.0,
    camera_distance_mm: float = 450.0,
    focal_px: float = 3200.0,
    tilt_degrees: float = 0.0,
    canvas_size: Tuple[int, int] = (1280, 960),
) -> Tuple[np.ndarray, Dict[str, float]]:
    """Generates a complete scene with ArUco marker and an onion bulb of exact ground truth diameter."""
    w, h = canvas_size
    img = np.full((h, w, 3), 235, dtype=np.uint8)  # Light neutral desk background

    # Planar scale: scale_px_per_mm = focal_px / camera_distance_mm
    scale_px_per_mm = focal_px / camera_distance_mm
    marker_px = int(round(marker_size_mm * scale_px_per_mm))

    # 1. Render ArUco marker
    dict_4x4 = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker_img = cv2.aruco.generateImageMarker(dict_4x4, id=0, sidePixels=marker_px)
    marker_bgr = cv2.cvtColor(marker_img, cv2.COLOR_GRAY2BGR)

    # Place marker at center-left
    mx, my = int(w * 0.25), int(h * 0.4)
    img[my : my + marker_px, mx : mx + marker_px] = marker_bgr

    # 2. Render onion at center-right
    # Note: Elevation above plane increases apparent size by Z / (Z - r)
    true_r_mm = true_diameter_mm / 2.0
    apparent_diameter_mm = true_diameter_mm * (camera_distance_mm / (camera_distance_mm - true_r_mm))
    apparent_radius_px = int(round((apparent_diameter_mm / 2.0) * scale_px_per_mm))

    ox, oy = int(w * 0.7), int(h * 0.5)
    draw_synthetic_onion(img, (ox, oy), apparent_radius_px)

    # 3. Apply perspective warp for camera tilt if requested
    if abs(tilt_degrees) > 0.1:
        # Tilt around X-axis (top tilts away)
        theta = math.radians(tilt_degrees)
        d = w / 2.0
        src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        offset = math.tan(theta) * (h / 4.0)
        dst = np.float32([[offset, 0], [w - offset, 0], [w, h], [0, h]])
        M = cv2.getPerspectiveTransform(src, dst)
        img = cv2.warpPerspective(img, M, (w, h), borderValue=(235, 235, 235))

    ground_truth = {
        "true_diameter_mm": true_diameter_mm,
        "marker_size_mm": marker_size_mm,
        "camera_distance_mm": camera_distance_mm,
        "tilt_degrees": tilt_degrees,
        "focal_px": focal_px,
        "apparent_diameter_px": apparent_radius_px * 2.0,
    }

    return img, ground_truth


def create_synthetic_benchmark_dataset(
    output_dir: Path | str,
    test_diameters: List[float] = [38.0, 45.0, 52.0, 60.0, 68.0],
    test_tilts: List[float] = [0.0, 10.0, 20.0],
) -> List[Path]:
    """Builds a test suite of synthetic calibration images and saves ground-truth metadata."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    generated_files = []

    for d in test_diameters:
        for tilt in test_tilts:
            scene, gt = generate_synthetic_scene(true_diameter_mm=d, tilt_degrees=tilt)
            fname = f"synth_d{int(d)}_tilt{int(tilt)}"
            img_path = out / f"{fname}.png"
            json_path = out / f"{fname}.json"

            cv2.imwrite(str(img_path), scene)
            with open(json_path, "w") as f:
                json.dump(gt, f, indent=2)

            generated_files.append(img_path)

    return generated_files


if __name__ == "__main__":
    test_dir = Path(__file__).resolve().parents[2] / "data" / "synthetic_calibration"
    files = create_synthetic_benchmark_dataset(test_dir)
    print(f"Generated {len(files)} synthetic benchmark scenes in {test_dir}")
