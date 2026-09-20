"""Dataset Downloader and Archive Ingestion Utility.

Supports downloading Roboflow datasets via API key or ingesting manually downloaded
zips from data/raw/ for:
  - D1-A: instance-segmentation-wagk9 (Roboflow, YOLOv8-seg unaugmented)
  - D1-B: onionthesis1 (Roboflow, cross-source test set)
  - D1-C: Mendeley/Zenodo Red and White Onion Bulbs (smartphone multi-bulb)
  - D2-A: onion-disease (Roboflow, defect classification)
  - D2-C: Mendeley Bangladesh Vegetable dataset (onion healthy crops)

Ref: Dataset Plan.md §1–§5.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import zipfile


DATASET_SOURCES = {
    "D1A": {
        "name": "yolo-custom-object-detection/instance-segmentation-wagk9",
        "version": 12,
        "format": "yolov8",
        "description": "Primary YOLOv8-seg polygon mask dataset",
    },
    "D1B": {
        "name": "paul-angelo-lavarias-ii/onionthesis1",
        "version": 1,
        "format": "yolov8",
        "description": "Cross-source test set",
    },
    "D2A": {
        "name": "anas-kadiri-ffnxr/onion-disease",
        "version": 1,
        "format": "yolov8",
        "description": "Defect classification source (22 classes remapped to 4)",
    },
}


def extract_zip(zip_path: Path, target_dir: Path) -> None:
    """Safely extracts a zip archive to the target directory."""
    print(f"Extracting {zip_path.name} -> {target_dir}...")
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(target_dir)
    print(f"Done extracting {zip_path.name}")


def download_roboflow_dataset(
    dataset_key: str,
    api_key: str,
    raw_dir: Path,
) -> Path:
    """Downloads dataset from Roboflow Universe using official Roboflow Python SDK."""
    try:
        from roboflow import Roboflow
    except ImportError:
        raise ImportError(
            "Roboflow package not installed. Install with: uv pip install roboflow"
        )

    info = DATASET_SOURCES.get(dataset_key)
    if not info:
        raise ValueError(f"Unknown dataset key: {dataset_key}")

    print(f"Connecting to Roboflow for {dataset_key} ({info['name']})...")
    rf = Roboflow(api_key=api_key)
    workspace, project_name = info["name"].split("/")
    project = rf.workspace(workspace).project(project_name)
    version = project.version(info["version"])

    target_dir = raw_dir / f"{dataset_key}_{project_name}"
    dataset = version.download(info["format"], location=str(target_dir))
    return Path(dataset.location)


def ingest_local_zips(raw_dir: Path) -> list[Path]:
    """Scans data/raw/ for any zip archives dropped manually and unpacks them."""
    extracted = []
    zips = list(raw_dir.glob("*.zip"))
    for zp in zips:
        folder_name = zp.stem
        dest = raw_dir / folder_name
        if not dest.exists():
            extract_zip(zp, dest)
            extracted.append(dest)
        else:
            print(f"Directory {dest} already exists, skipping {zp.name}")
    return extracted


def main():
    parser = argparse.ArgumentParser(description="Download and unpack datasets for Onion Quality Assessment")
    parser.add_argument("--api-key", type=str, default=os.getenv("ROBOFLOW_API_KEY"), help="Roboflow API Key")
    parser.add_argument("--dataset", choices=["D1A", "D1B", "D2A", "all"], default=None, help="Dataset to download")
    parser.add_argument("--raw-dir", type=str, default="data/raw", help="Target raw directory")
    args = parser.parse_args()

    raw_path = Path(args.raw_dir).resolve()
    raw_path.mkdir(parents=True, exist_ok=True)

    # 1. Ingest any local zips first
    ingested = ingest_local_zips(raw_path)
    if ingested:
        print(f"Unpacked {len(ingested)} local archives.")

    # 2. Download via Roboflow API if key is present
    if args.api_key and args.dataset:
        targets = ["D1A", "D1B", "D2A"] if args.dataset == "all" else [args.dataset]
        for t in targets:
            download_roboflow_dataset(t, args.api_key, raw_path)
    elif not args.api_key:
        print("\nNote: No Roboflow API key provided.")
        print("You can either:")
        print("1. Set export ROBOFLOW_API_KEY='your_key' and run with --api-key")
        print("2. Or drop downloaded zip files into data/raw/ and run this script to unpack them.")


if __name__ == "__main__":
    main()
