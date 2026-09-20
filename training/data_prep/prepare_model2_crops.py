"""Prepares Model 2 (Defect Classifier) dataset with 4 core classes.

Extracts padded onion crops from D2-A and remaps the 22 original classes into:
  1. healthy
  2. sprouted (includes sprouting & root growth)
  3. rotten (highest priority for multi-defect)
  4. mechanical_damage (cuts, punctures)

Excluded from v1 per locked decisions:
  - black smut (fungal disease excluded for v1)
  - stem (plant part, not defect)
  - discoloured (handled by thresholding, not classifier)
  - double_bulb (dropped from v1)

Ref: Dataset Plan.md §3 and locked decisions.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import random
import sys
import cv2
import numpy as np

# Ensure repository root is in python path
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


# 4-class locked mapping table
CLASS_MAPPING = {
    # Healthy
    "onion": "healthy",
    "healthy": "healthy",
    # Rotten
    "rotten": "rotten",
    "sprouted-rotten": "rotten",
    # Sprouted
    "sprouted": "sprouted",
    "sprouted-cuts": "sprouted",
    "sprouted-discoloured": "sprouted",
    "sprouted-blacksmutinfected": "sprouted",
    "sprouted-rooting": "sprouted",
    "rooted": "sprouted",
    "rooting": "sprouted",
    # Mechanical damage
    "cuts": "mechanical_damage",
    "blackmutinfected-cuts": "mechanical_damage",
}

EXCLUDED_CLASSES = {
    "stem",
    "Discoloured",
    "discoloured",
    "blackmutinfected",
    "blacksmutinfected",
    "double_bulb",
}


def crop_bulb(
    img: np.ndarray,
    cx: float,
    cy: float,
    bw: float,
    bh: float,
    target_size: tuple[int, int] = (224, 224),
    pad_ratio: float = 0.08,
) -> np.ndarray:
    """Crops bounding box from image with padding and resizes to target_size."""
    h, w = img.shape[:2]
    # Unnormalize coords
    x_center = cx * w
    y_center = cy * h
    box_w = bw * w * (1.0 + pad_ratio)
    box_h = bh * h * (1.0 + pad_ratio)

    x1 = max(0, int(x_center - box_w / 2.0))
    y1 = max(0, int(y_center - box_h / 2.0))
    x2 = min(w, int(x_center + box_w / 2.0))
    y2 = min(h, int(y_center + box_h / 2.0))

    if x2 <= x1 or y2 <= y1:
        return cv2.resize(img, target_size)

    crop = img[y1:y2, x1:x2]
    return cv2.resize(crop, target_size, interpolation=cv2.INTER_AREA)


def build_model2_dataset(
    d2a_raw_dir: Path | str,
    output_dir: Path | str,
    class_names: list[str] | None = None,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    seed: int = 42,
) -> dict[str, int]:
    """Crops and categorizes D2-A into data/model2/{train,val,test}/{healthy,sprouted,rotten,mechanical_damage}."""
    random.seed(seed)
    src = Path(d2a_raw_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Standard 4 classes
    target_classes = ["healthy", "sprouted", "rotten", "mechanical_damage"]
    for split in ["train", "val", "test"]:
        for cls in target_classes:
            (out / split / cls).mkdir(parents=True, exist_ok=True)

    img_extensions = {".jpg", ".jpeg", ".png"}
    images = [p for p in src.rglob("*") if p.suffix.lower() in img_extensions]

    crops_by_class: dict[str, list[tuple[np.ndarray, str]]] = {c: [] for c in target_classes}
    skipped_count = 0

    print(f"Scanning {len(images)} images in {src} for defect crops...")

    for img_p in images:
        lbl_p = img_p.with_suffix(".txt")
        if not lbl_p.exists():
            continue

        img = cv2.imread(str(img_p))
        if img is None:
            continue

        with open(lbl_p, "r") as f:
            lines = f.readlines()

        for line_idx, line in enumerate(lines):
            parts = line.strip().split()
            if len(parts) < 5:
                continue

            raw_cls_id = int(parts[0])
            raw_cls_name = class_names[raw_cls_id] if class_names and raw_cls_id < len(class_names) else str(raw_cls_id)

            # Check mapping
            target_cls = CLASS_MAPPING.get(raw_cls_name)
            if not target_cls:
                skipped_count += 1
                continue

            cx, cy, bw, bh = map(float, parts[1:5])
            cropped = crop_bulb(img, cx, cy, bw, bh)
            crop_name = f"{img_p.stem}_crop{line_idx}.jpg"
            crops_by_class[target_cls].append((cropped, crop_name))

    # Split crops and write to disk
    counts: dict[str, int] = {}
    for cls_name, crops in crops_by_class.items():
        random.shuffle(crops)
        n = len(crops)
        counts[cls_name] = n
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)

        train_set = crops[:n_train]
        val_set = crops[n_train : n_train + n_val]
        test_set = crops[n_train + n_val :]

        for c_img, c_name in train_set:
            cv2.imwrite(str(out / "train" / cls_name / c_name), c_img)
        for c_img, c_name in val_set:
            cv2.imwrite(str(out / "val" / cls_name / c_name), c_img)
        for c_img, c_name in test_set:
            cv2.imwrite(str(out / "test" / cls_name / c_name), c_img)

    print("\nModel 2 Dataset Crop Summary:")
    for c, cnt in counts.items():
        print(f"  - {c}: {cnt} crops")
    print(f"  - Skipped non-target crops (stems, discoloured, black smut): {skipped_count}")
    print(f"Dataset successfully saved to {out}")

    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare Model 2 Defect Classification crops")
    parser.add_argument("--d2a-dir", type=str, default="data/raw/D2A_onion_disease", help="Raw D2-A directory")
    parser.add_argument("--output-dir", type=str, default="data/model2", help="Output model2 directory")
    args = parser.parse_args()

    build_model2_dataset(args.d2a_dir, args.output_dir)
