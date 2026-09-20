"""Perceptual Hashing (pHash) and Cross-Source Deduplication.

Computes perceptual hashes across datasets (D1-A, D1-B, D1-C, D2-A, etc.) to detect near-duplicate
images (Hamming distance <= 6). Prevents cross-source train/test data leakage.
Ref: Dataset Plan.md §3 and §5.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple
import imagehash
from PIL import Image
import pandas as pd
from tqdm import tqdm


DEFAULT_HAMMING_THRESHOLD = 6


def compute_image_phash(image_path: Path | str) -> str:
    """Computes a 64-bit perceptual hash for the given image."""
    with Image.open(image_path) as img:
        return str(imagehash.phash(img))


def scan_directory_hashes(directory: Path | str, extensions: Tuple[str, ...] = (".jpg", ".jpeg", ".png")) -> Dict[str, str]:
    """Scans directory and returns mapping of relative_path -> phash_hex."""
    dir_path = Path(directory)
    if not dir_path.exists():
        return {}

    hashes: Dict[str, str] = {}
    image_files = [p for p in dir_path.rglob("*") if p.suffix.lower() in extensions]

    print(f"Scanning {len(image_files)} images in {dir_path}...")
    for img_path in tqdm(image_files, desc="Hashing"):
        try:
            h = compute_image_phash(img_path)
            rel = str(img_path.relative_to(dir_path))
            hashes[rel] = h
        except Exception as e:
            print(f"Warning: Failed to hash {img_path}: {e}")

    return hashes


def find_duplicate_clusters(
    hashes_dict: Dict[str, str],
    hamming_threshold: int = DEFAULT_HAMMING_THRESHOLD,
) -> List[Set[str]]:
    """Groups images into connected clusters where each pair has Hamming distance <= threshold."""
    items = list(hashes_dict.items())
    parsed = [(path, imagehash.hex_to_hash(h_str)) for path, h_str in items]
    n = len(parsed)

    # Graph adjacency for connected components
    adj = defaultdict(set)

    for i in range(n):
        p1, h1 = parsed[i]
        adj[p1].add(p1)
        for j in range(i + 1, n):
            p2, h2 = parsed[j]
            dist = h1 - h2
            if dist <= hamming_threshold:
                adj[p1].add(p2)
                adj[p2].add(p1)

    # Breadth-first search for components
    visited: Set[str] = set()
    clusters: List[Set[str]] = []

    for path in adj:
        if path not in visited:
            cluster: Set[str] = set()
            queue = [path]
            visited.add(path)
            while queue:
                curr = queue.pop(0)
                cluster.add(curr)
                for neighbor in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            if len(cluster) > 1:
                clusters.append(cluster)

    return clusters


def export_deduplication_report(
    clusters: List[Set[str]],
    hashes_dict: Dict[str, str],
    output_csv: Path | str,
) -> None:
    """Exports a CSV report listing all duplicate groups for audit and split assignment."""
    rows = []
    for cluster_id, cluster in enumerate(clusters):
        for path in cluster:
            rows.append({
                "cluster_id": cluster_id,
                "relative_path": path,
                "phash": hashes_dict.get(path, ""),
            })

    df = pd.DataFrame(rows)
    out_p = Path(output_csv)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_p, index=False)
    print(f"Exported {len(clusters)} duplicate clusters ({len(rows)} images) to {output_csv}")
