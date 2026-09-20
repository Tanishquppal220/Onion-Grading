"""Prepares Model 1 (YOLOv8-seg) dataset with unified single-class 'onion'.

Converts raw segmentation labels from D1-A and D1-B:
1. Re-indexes all 'onion' polygon annotations to class 0.
2. In D1-B ('onionthesis1'), drops polygons labelled 'Not Onion'.
3. Generates the standard YOLOv8 data.yaml pointing to train, val, and test splits.
Ref: Dataset Plan.md §3 (Model 1 recipe).
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys
import yaml

# Ensure repository root is in python path
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def sanitize_and_copy_split(
    src_images_dir: Path,
    src_labels_dir: Path,
    dst_images_dir: Path,
    dst_labels_dir: Path,
    target_class_indices: list[int] = [0],
) -> int:
    """Copies images and converts segmentation labels to single class 0 (onion)."""
    dst_images_dir.mkdir(parents=True, exist_ok=True)
    dst_labels_dir.mkdir(parents=True, exist_ok=True)

    img_extensions = {".jpg", ".jpeg", ".png"}
    images = [p for p in src_images_dir.glob("*") if p.suffix.lower() in img_extensions]
    processed_count = 0

    for img_p in images:
        lbl_p = src_labels_dir / f"{img_p.stem}.txt"
        dest_img_p = dst_images_dir / img_p.name
        dest_lbl_p = dst_labels_dir / f"{img_p.stem}.txt"

        if not lbl_p.exists():
            # Image without label -> background negative example
            shutil.copy2(img_p, dest_img_p)
            dest_lbl_p.touch()
            processed_count += 1
            continue

        with open(lbl_p, "r") as f:
            lines = f.readlines()

        valid_lines = []
        for line in lines:
            parts = line.strip().split()
            if len(parts) < 6:  # Polygon mask requires at least class + 5 coords
                continue

            cls_id = int(parts[0])
            # If target class or default onion class
            if cls_id in target_class_indices or len(target_class_indices) == 0:
                # Force class id to 0 ('onion')
                new_line = "0 " + " ".join(parts[1:]) + "\n"
                valid_lines.append(new_line)

        # Copy image and write unified label
        shutil.copy2(img_p, dest_img_p)
        with open(dest_lbl_p, "w") as f:
            f.writelines(valid_lines)

        processed_count += 1

    return processed_count


def build_model1_dataset(
    d1a_raw_dir: Path | str,
    d1b_raw_dir: Path | str | None,
    output_dir: Path | str,
) -> Path:
    """Organizes D1-A and D1-B into model1/train, model1/val, and model1/test."""
    d1a = Path(d1a_raw_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 1. Process D1-A train and val splits
    for split in ["train", "valid", "val"]:
        src_split = d1a / split
        if not src_split.exists():
            continue
        dst_split_name = "val" if split == "valid" else split
        print(f"Processing D1-A {split} -> {dst_split_name}...")
        sanitize_and_copy_split(
            src_images_dir=src_split / "images",
            src_labels_dir=src_split / "labels",
            dst_images_dir=out / dst_split_name / "images",
            dst_labels_dir=out / dst_split_name / "labels",
        )

    # 2. Process D1-B as cross-source test set if provided
    if d1b_raw_dir:
        d1b = Path(d1b_raw_dir)
        print(f"Processing D1-B as cross-source benchmark -> test split...")
        # Check if D1-B has test/ or valid/ or flat images
        d1b_test_img = d1b / "test" / "images"
        d1b_test_lbl = d1b / "test" / "labels"
        if not d1b_test_img.exists():
            d1b_test_img = d1b / "train" / "images"
            d1b_test_lbl = d1b / "train" / "labels"

        if d1b_test_img.exists():
            # In D1-B, class 0 is Onion, class 1 is Not Onion -> target [0]
            sanitize_and_copy_split(
                src_images_dir=d1b_test_img,
                src_labels_dir=d1b_test_lbl,
                dst_images_dir=out / "test" / "images",
                dst_labels_dir=out / "test" / "labels",
                target_class_indices=[0],
            )

    # 3. Write data.yaml
    data_yaml = {
        "path": str(out.resolve()),
        "train": "train/images",
        "val": "val/images",
        "test": "test/images",
        "names": {
            0: "onion",
        },
    }

    yaml_path = out / "data.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(data_yaml, f, sort_keys=False)

    print(f"\nModel 1 dataset prepared successfully at {out}")
    print(f"data.yaml generated at {yaml_path}")
    return yaml_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare Model 1 YOLOv8-seg dataset")
    parser.add_argument("--d1a-dir", type=str, default="data/raw/D1A_instance_seg", help="Raw D1-A directory")
    parser.add_argument("--d1b-dir", type=str, default=None, help="Raw D1-B directory (test set)")
    parser.add_argument("--output-dir", type=str, default="data/model1", help="Output model1 directory")
    args = parser.parse_args()

    build_model1_dataset(args.d1a_dir, args.d1b_dir, args.output_dir)
