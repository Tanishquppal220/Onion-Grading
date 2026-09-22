"""Demo Asset Generator.

Generates and stages official demonstration imagery for the Automated Onion Quality Assessment System:
  1. `aruco_marker_50mm.png`: High-resolution printable/displayable fiducial marker standard
  2. `demo_calibrated_doca_pass.jpg`: Calibrated inspection tray yielding 100% DoCA Grade-A pass
  3. `demo_defective_lot_reject.jpg`: Calibrated tray with sprouted, rotten, and damaged bulbs yielding DoCA rejection
  4. `demo_commercial_crate_36bulbs.jpg`: High-density commercial crate showcasing 36-bulb instance segmentation
  5. `demo_uncalibrated_warning.jpg`: Uncalibrated image demonstrating graceful fallback to 55mm prior
"""

import sys
from pathlib import Path
import shutil
import cv2
import numpy as np


def generate_aruco_card(output_path: Path) -> np.ndarray:
    """Generates an official ArUco 50mm fiducial card with calibration metadata and border."""
    card_w, card_h = 800, 800
    card = np.full((card_h, card_w, 3), 255, dtype=np.uint8)

    # 1. Outer border
    cv2.rectangle(card, (20, 20), (card_w - 20, card_h - 20), (40, 40, 40), 3)

    # 2. Header
    header_title = "GOVT OF INDIA / NAFED / NCCF INSPECTION STANDARD"
    cv2.putText(card, header_title, (45, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 120), 2, cv2.LINE_AA)
    sub_title = "Optical Fiducial Reference Standard (50.0 mm x 50.0 mm)"
    cv2.putText(card, sub_title, (45, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (80, 80, 80), 1, cv2.LINE_AA)
    cv2.line(card, (30, 115), (card_w - 30, 115), (180, 180, 180), 1)

    # 3. ArUco Marker (DICT_4X4_50, ID: 0)
    dict_4x4 = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker_size = 500
    marker_img = cv2.aruco.generateImageMarker(dict_4x4, id=0, sidePixels=marker_size)
    marker_bgr = cv2.cvtColor(marker_img, cv2.COLOR_GRAY2BGR)

    mx = (card_w - marker_size) // 2
    my = 145
    card[my : my + marker_size, mx : mx + marker_size] = marker_bgr

    # Marker bounding border
    cv2.rectangle(card, (mx - 2, my - 2), (mx + marker_size + 2, my + marker_size + 2), (0, 0, 0), 2)

    # 4. Dimension callouts
    cv2.putText(card, "<--- 50.0 mm --->", (card_w // 2 - 110, my + marker_size + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2, cv2.LINE_AA)

    # 5. Footer Instructions
    footer1 = "Dictionary: DICT_4X4_50 | Marker ID: 0 | Calibrated Scale: 50.0 mm"
    cv2.putText(card, footer1, (45, 715), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (50, 50, 50), 1, cv2.LINE_AA)
    footer2 = "Instructions: Print at 100% scale or display on phone screen next to onions."
    cv2.putText(card, footer2, (45, 745), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 100, 0), 1, cv2.LINE_AA)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), card)
    print(f"[OK] Generated ArUco card: {output_path}")
    return card


def generate_calibrated_pass_scene(output_path: Path, card_img: np.ndarray) -> None:
    """Generates an inspection scene with ArUco marker + sound Grade-A onions (45-65mm)."""
    canvas_w, canvas_h = 1280, 850
    canvas = np.full((canvas_h, canvas_w, 3), (242, 242, 242), dtype=np.uint8)

    # Place resized ArUco card at top-left
    card_size = 260
    card_resized = cv2.resize(card_img, (card_size, card_size))
    canvas[40 : 40 + card_size, 40 : 40 + card_size] = card_resized

    # Draw label next to marker
    cv2.putText(canvas, "NAFED Procurement Quality Intake Tray (Grade-A Buffer-Stock Lot)", (325, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 120, 0), 2, cv2.LINE_AA)
    cv2.putText(canvas, "Standard: DoCA Reinstated 45-65 mm Norm | Fiducial Scale: 50.0 mm ArUco (ID 0)", (325, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (90, 90, 90), 1, cv2.LINE_AA)

    # Scale: Marker in 260 card is (500/800)*260 = 162.5 px. Since marker is 50 mm, scale ~ 3.25 px/mm
    scale = (500.0 / 800.0) * card_size / 50.0

    # Load healthy onion crop from images2.jpg
    img2 = cv2.imread("frontend/public/samples/images2.jpg")
    crop = img2[100:560, 80:450]
    ch, cw = crop.shape[:2]

    # Create smooth elliptical mask around onion flesh to avoid boundary contrast
    ellipse_mask = np.zeros((ch, cw), dtype=np.uint8)
    cv2.ellipse(ellipse_mask, (cw // 2, ch // 2), (cw // 2 - 12, ch // 2 - 12), 0, 0, 360, 255, -1)
    crop_masked = crop.copy()
    crop_masked[ellipse_mask == 0] = (242, 242, 242)

    # Desired equatorial diameters in mm: all inside 45-65mm Grade-A band
    target_diameters_mm = [51.5, 54.0, 52.8, 55.2, 53.0, 54.5, 53.8]
    grid_coords = [
        (280, 480), (280, 780), (280, 1080),
        (580, 180), (580, 480), (580, 780), (580, 1080),
    ]

    for d_mm, (cy, cx) in zip(target_diameters_mm, grid_coords):
        target_w = int(d_mm * scale)
        target_h = int(crop.shape[0] * (target_w / crop.shape[1]))
        resized_crop = cv2.resize(crop_masked, (target_w, target_h))

        y1 = cy - target_h // 2
        y2 = y1 + target_h
        x1 = cx - target_w // 2
        x2 = x1 + target_w

        if 0 <= y1 and y2 <= canvas_h and 0 <= x1 and x2 <= canvas_w:
            canvas[y1:y2, x1:x2] = resized_crop

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), canvas)
    print(f"[OK] Generated Calibrated Pass Scene: {output_path}")


def generate_defective_reject_scene(output_path: Path, card_img: np.ndarray) -> None:
    """Generates an inspection scene with ArUco marker + sprouted and damaged onions."""
    canvas_w, canvas_h = 1280, 850
    canvas = np.full((canvas_h, canvas_w, 3), (238, 238, 238), dtype=np.uint8)

    card_size = 260
    card_resized = cv2.resize(card_img, (card_size, card_size))
    canvas[40 : 40 + card_size, 40 : 40 + card_size] = card_resized

    cv2.putText(canvas, "APMC Mandi Incoming Intake Tray (Rejected Lot - High Spoilage Risk)", (325, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 150), 2, cv2.LINE_AA)
    cv2.putText(canvas, "Defects Present: Vegetative Sprouting & Mechanical Damage | Lot: LOT-REJECT-04", (325, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (90, 90, 90), 1, cv2.LINE_AA)

    scale = (500.0 / 800.0) * card_size / 50.0

    # Load sprouted onion from images3.jpg
    img3 = cv2.imread("frontend/public/samples/images3.jpg")
    crop_sprout = img3[50:600, 100:540]

    # Load damaged onion from images.jpg
    img_dmg = cv2.imread("frontend/public/samples/images.jpg")
    crop_dmg = img_dmg[40:220, 40:220]

    items = [
        (crop_sprout, 55.0, (280, 480)),
        (crop_sprout, 54.0, (280, 800)),
        (crop_dmg, 48.0, (580, 260)),
        (crop_dmg, 52.0, (580, 600)),
        (crop_sprout, 56.0, (580, 940)),
    ]

    for crop_src, d_mm, (cy, cx) in items:
        target_w = int(d_mm * scale)
        target_h = int(crop_src.shape[0] * (target_w / crop_src.shape[1]))
        resized = cv2.resize(crop_src, (target_w, target_h))

        y1 = cy - target_h // 2
        y2 = y1 + target_h
        x1 = cx - target_w // 2
        x2 = x1 + target_w

        if 0 <= y1 and y2 <= canvas_h and 0 <= x1 and x2 <= canvas_w:
            canvas[y1:y2, x1:x2] = resized

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), canvas)
    print(f"[OK] Generated Defective Reject Scene: {output_path}")


def main():
    samples_dir = Path("frontend/public/samples")
    uploads_dir = Path("runs/uploads")
    public_dir = Path("frontend/public")

    samples_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    # 1. Printable ArUco Marker
    aruco_png = public_dir / "aruco_marker_50mm.png"
    card_img = generate_aruco_card(aruco_png)
    shutil.copy2(aruco_png, samples_dir / "aruco_marker_50mm.png")
    shutil.copy2(aruco_png, uploads_dir / "aruco_marker_50mm.png")

    # 2. Preset 1: Calibrated DoCA Pass Scene
    pass_jpg = samples_dir / "demo_calibrated_doca_pass.jpg"
    generate_calibrated_pass_scene(pass_jpg, card_img)
    shutil.copy2(pass_jpg, uploads_dir / "demo_calibrated_doca_pass.jpg")

    # 3. Preset 2: Defective Lot Reject Scene
    reject_jpg = samples_dir / "demo_defective_lot_reject.jpg"
    generate_defective_reject_scene(reject_jpg, card_img)
    shutil.copy2(reject_jpg, uploads_dir / "demo_defective_lot_reject.jpg")

    # 4. Preset 3: Commercial Crate (36 Bulbs Multi-Instance Segmentation)
    src_36 = samples_dir / "images.jpg"
    dest_36 = samples_dir / "demo_commercial_crate_36bulbs.jpg"
    if src_36.exists():
        shutil.copy2(src_36, dest_36)
        shutil.copy2(src_36, uploads_dir / "demo_commercial_crate_36bulbs.jpg")
        print(f"[OK] Staged 36-bulb commercial crate: {dest_36}")

    # 5. Preset 4: Uncalibrated Warning Scene
    src_uncal = samples_dir / "images1.jpg"
    dest_uncal = samples_dir / "demo_uncalibrated_warning.jpg"
    if src_uncal.exists():
        shutil.copy2(src_uncal, dest_uncal)
        shutil.copy2(src_uncal, uploads_dir / "demo_uncalibrated_warning.jpg")
        print(f"[OK] Staged uncalibrated scene: {dest_uncal}")

    print("\nAll demo assets generated and staged successfully!")


if __name__ == "__main__":
    main()
