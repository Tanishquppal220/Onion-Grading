"""Dataset Manifest and Licensing Attribution Builder.

Scans processed datasets, records hashes, assigned splits, and license metadata,
and exports data/manifests/dataset_manifest.csv and ATTRIBUTION.md.
Ref: Dataset Plan.md §4, §5, and §8.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

# Ensure repository root is in python path
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
from training.data_prep.deduplicate import compute_image_phash


LICENSES = {
    "D1A": {
        "dataset_name": "Instance Segmentation (Yolo Custom Object Detection)",
        "author": "Yolo Custom Object Detection",
        "license": "CC BY 4.0",
        "url": "https://universe.roboflow.com/yolo-custom-object-detection/instance-segmentation-wagk9",
    },
    "D1B": {
        "dataset_name": "onionthesis1",
        "author": "Paul Angelo Lavarias II",
        "license": "CC BY 4.0",
        "url": "https://universe.roboflow.com/paul-angelo-lavarias-ii/onionthesis1",
    },
    "D1C": {
        "dataset_name": "Image Dataset of Red and White Onion Bulbs and Leaves",
        "author": "Mendeley Data / Zenodo",
        "license": "CC BY 4.0",
        "url": "https://data.mendeley.com/datasets/42bcyncfhy/1",
    },
    "D2A": {
        "dataset_name": "onion-disease",
        "author": "Anas Kadiri",
        "license": "CC BY 4.0",
        "url": "https://universe.roboflow.com/anas-kadiri-ffnxr/onion-disease",
    },
    "D2C": {
        "dataset_name": "Vegetable Image Dataset for Classification Models: A Bangladeshi Perspective",
        "author": "Mendeley Data",
        "license": "CC BY 4.0",
        "url": "https://data.mendeley.com/datasets/b9rvg4f2st/4",
    },
}


def build_manifest_for_directory(
    root_dir: Path | str,
    source_dataset_key: str,
    output_csv: Path | str,
) -> pd.DataFrame:
    """Builds a manifest DataFrame for all images in root_dir."""
    root = Path(root_dir)
    lic_info = LICENSES.get(source_dataset_key, {
        "dataset_name": source_dataset_key,
        "author": "Unknown",
        "license": "Unspecified",
        "url": "",
    })

    extensions = {".jpg", ".jpeg", ".png"}
    images = [p for p in root.rglob("*") if p.suffix.lower() in extensions]
    records = []

    for img_p in images:
        rel = str(img_p.relative_to(root))
        # Derive split if inside a train/val/test directory
        parts = img_p.parts
        split = "train"
        if "val" in parts:
            split = "val"
        elif "test" in parts:
            split = "test"

        # Parent folder often denotes class in classification datasets
        cls_name = img_p.parent.name if split != img_p.parent.name else "onion"

        try:
            h = compute_image_phash(img_p)
        except Exception:
            h = ""

        records.append({
            "image_id": img_p.stem,
            "source_dataset": source_dataset_key,
            "relative_path": rel,
            "original_class": cls_name,
            "phash": h,
            "license": lic_info["license"],
            "author": lic_info["author"],
            "assigned_split": split,
        })

    df = pd.DataFrame(records)
    out = Path(output_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Manifest written with {len(df)} records to {output_csv}")
    return df


def generate_attribution_document(output_path: Path | str) -> None:
    """Generates ATTRIBUTION.md documenting source datasets and CC BY requirements."""
    content = ["# Dataset Attribution & Licensing\n", "This project utilizes public research datasets under CC BY 4.0 licenses.\n"]
    for key, info in LICENSES.items():
        content.append(f"## {key}: {info['dataset_name']}")
        content.append(f"- **Author / Origin**: {info['author']}")
        content.append(f"- **License**: {info['license']}")
        content.append(f"- **Source URL**: [{info['url']}]({info['url']})\n")

    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(content))
    print(f"Attribution document created at {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build dataset manifest and attribution document")
    parser.add_argument("--root-dir", type=str, default="data", help="Data directory root")
    parser.add_argument("--output-csv", type=str, default="data/manifests/dataset_manifest.csv")
    args = parser.parse_args()

    generate_attribution_document("data/manifests/ATTRIBUTION.md")
