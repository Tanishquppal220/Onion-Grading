"""Audit Inspector for Dataset Quality & Annotation Verification.

Renders sample images with overlaid masks/bounding boxes to spot-check ~50 images per dataset.
Verifies annotation tightness, defect coverage (whole-bulb vs regional), and class distributions.
Ref: Dataset Plan.md §3 and §5.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import cv2
import numpy as np


CLASS_MAP_D2A = {
    # 22 classes remapped to the 4 locked classes (healthy, sprouted, rotten, mechanical_damage)
    "onion": "healthy",
    "healthy": "healthy",
    "rotten": "rotten",
    "sprouted": "sprouted",
    "sprouted-rotten": "rotten",  # Priority: rot > sprout > damage
    "sprouted-cuts": "sprouted",
    "sprouted-discoloured": "sprouted",
    "sprouted-blacksmutinfected": "sprouted",
    "sprouted-rooting": "sprouted",
    "cuts": "mechanical_damage",
    "blackmutinfected-cuts": "mechanical_damage",
    "rooted": "sprouted",  # Subject to visual check
    "rooting": "sprouted",
    "Discoloured": "discoloured_non_classifier",
    "discoloured": "discoloured_non_classifier",
    "stem": "drop_part_label",
    "blackmutinfected": "excluded_disease",
    "blacksmutinfected": "excluded_disease",
}


def render_yolo_sample(image_path: Path, label_path: Path, class_names: list[str]) -> np.ndarray:
    """Draws YOLO bounding boxes or polygon masks on an image."""
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Could not load image: {image_path}")

    h, w = img.shape[:2]
    if not label_path.exists():
        cv2.putText(img, "No Label File", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        return img

    with open(label_path, "r") as f:
        lines = f.readlines()

    for line in lines:
        parts = line.strip().split()
        if len(parts) < 5:
            continue

        cls_id = int(parts[0])
        cls_name = class_names[cls_id] if cls_id < len(class_names) else f"cls_{cls_id}"

        if len(parts) == 5:
            # Bounding box: class cx cy w h (normalized)
            cx, cy, bw, bh = map(float, parts[1:5])
            x1 = int((cx - bw / 2.0) * w)
            y1 = int((cy - bh / 2.0) * h)
            x2 = int((cx + bw / 2.0) * w)
            y2 = int((cy + bh / 2.0) * h)

            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(img, cls_name, (x1, max(20, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        elif len(parts) > 5:
            # Polygon mask: class x1 y1 x2 y2 ...
            coords = np.array([float(x) for x in parts[1:]]).reshape(-1, 2)
            pts = (coords * np.array([w, h])).astype(np.int32)
            cv2.polylines(img, [pts], isClosed=True, color=(0, 255, 255), thickness=2)
            cv2.putText(img, cls_name, tuple(pts[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    return img


def audit_dataset_folder(
    dataset_dir: Path | str,
    output_dir: Path | str,
    max_samples: int = 50,
    class_names: list[str] | None = None,
) -> int:
    """Audits up to max_samples images from a dataset directory and outputs rendered verification images."""
    src = Path(dataset_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    img_extensions = {".jpg", ".jpeg", ".png"}
    images = [p for p in src.rglob("*") if p.suffix.lower() in img_extensions][:max_samples]

    classes = class_names or ["onion"]
    saved_count = 0

    for idx, img_p in enumerate(images):
        # YOLO format label is typically .txt in parallel labels/ directory or same directory
        lbl_p = img_p.with_suffix(".txt")
        if not lbl_p.exists():
            lbl_alt = img_p.parents[1] / "labels" / f"{img_p.stem}.txt"
            if lbl_alt.exists():
                lbl_p = lbl_alt

        try:
            rendered = render_yolo_sample(img_p, lbl_p, classes)
            out_path = out / f"audit_{idx:03d}_{img_p.stem}.jpg"
            cv2.imwrite(str(out_path), rendered)
            saved_count += 1
        except Exception as e:
            print(f"Failed rendering {img_p}: {e}")

    print(f"Audited and rendered {saved_count} inspection images in {out}")
    return saved_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit and spot-check dataset annotations")
    parser.add_argument("--dataset-dir", type=str, required=True, help="Path to dataset")
    parser.add_argument("--output-dir", type=str, default="data/audit_samples", help="Output directory")
    parser.add_argument("--samples", type=int, default=50, help="Number of samples to audit")
    args = parser.parse_args()

    audit_dataset_folder(args.dataset_dir, args.output_dir, args.samples)
