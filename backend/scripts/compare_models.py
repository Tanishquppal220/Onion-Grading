"""Side-by-Side Model Comparison Utility.

Compares the legacy single-stage YOLOv8 detection model from Onion_grading_backup
against the modern two-stage decoupled YOLOv8-seg + YOLOv8-cls inspection pipeline
in Onion_grading_new across test images.

Outputs:
  - Visual side-by-side comparison images saved to runs/eval_plots/comparison_old_vs_new.png
  - Quantitative benchmark report (detections, latency, classification breakdown)
"""

from __future__ import annotations

import os
from pathlib import Path
import time
import cv2
import numpy as np
import torch
from ultralytics import YOLO

# Paths
OLD_MODEL_PATH = Path("/home/tanishq/Projects/Onion_grading_backup/backend/model/best.pt")
NEW_SEG_PATH = Path("/home/tanishq/Projects/Onion_grading_new/runs/weights/model1_yolov8_seg.pt")
NEW_CLS_PATH = Path("/home/tanishq/Projects/Onion_grading_new/runs/weights/model2_defect_cls.pt")
TEST_IMAGES_DIR = Path("/home/tanishq/Projects/Onion_grading_backup/test")
OUTPUT_PLOT_PATH = Path("/home/tanishq/Projects/Onion_grading_new/runs/eval_plots/comparison_old_vs_new.png")

# Palette for classes
OLD_COLORS = {
    "onion": (0, 200, 0),          # Green
    "rotten": (0, 0, 220),         # Red
    "sprout": (0, 165, 255),       # Orange
    "double_split": (255, 105, 180) # Pink
}

NEW_DEFECT_COLORS = {
    "healthy": (34, 139, 34),          # Forest Green
    "sprouted": (0, 140, 255),         # Bright Orange
    "rotten": (0, 0, 220),             # Crimson Red
    "mechanical_damage": (180, 105, 255) # Purple
}


def load_models():
    print(f"Loading Old Model from: {OLD_MODEL_PATH}")
    old_model = YOLO(str(OLD_MODEL_PATH))
    print(f"Loading New Seg Model from: {NEW_SEG_PATH}")
    m1_seg = YOLO(str(NEW_SEG_PATH))
    print(f"Loading New Cls Model from: {NEW_CLS_PATH}")
    m2_cls = YOLO(str(NEW_CLS_PATH))
    return old_model, m1_seg, m2_cls


def draw_label(img, text, pt, bg_color, text_color=(255, 255, 255), font_scale=0.45, thickness=1):
    x, y = pt
    (w, h), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
    cv2.rectangle(img, (x, y - h - 6), (x + w + 4, y + 2), bg_color, -1)
    cv2.putText(img, text, (x + 2, y - 2), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, thickness, cv2.LINE_AA)


def run_old_model(model, img_bgr, conf_thresh=0.25):
    t0 = time.perf_counter()
    results = model.predict(img_bgr, conf=conf_thresh, verbose=False)[0]
    lat_ms = (time.perf_counter() - t0) * 1000.0

    annotated = img_bgr.copy()
    detections = []

    if results.boxes is not None and len(results.boxes) > 0:
        for box in results.boxes:
            cls_id = int(box.cls[0].cpu().numpy())
            conf = float(box.conf[0].cpu().numpy())
            cname = model.names[cls_id]
            xyxy = [int(v) for v in box.xyxy[0].cpu().numpy().tolist()]
            color = OLD_COLORS.get(cname, (0, 255, 255))

            # Draw bounding box
            cv2.rectangle(annotated, (xyxy[0], xyxy[1]), (xyxy[2], xyxy[3]), color, 2)
            label = f"{cname} {conf:.2f}"
            draw_label(annotated, label, (xyxy[0], max(16, xyxy[1])), color)

            detections.append({
                "class": cname,
                "conf": conf,
                "box": xyxy
            })

    return annotated, detections, lat_ms


def run_new_pipeline(m1_seg, m2_cls, img_bgr, conf_thresh=0.25):
    t0 = time.perf_counter()
    h_img, w_img = img_bgr.shape[:2]

    # Stage 1: Segmentation
    seg_res = m1_seg.predict(img_bgr, conf=conf_thresh, verbose=False)[0]

    annotated = img_bgr.copy()
    overlay = img_bgr.copy()
    detections = []

    boxes = seg_res.boxes
    masks = seg_res.masks

    if boxes is not None and len(boxes) > 0:
        for i in range(len(boxes)):
            b_conf = float(boxes.conf[i].cpu().numpy())
            xyxy = [int(v) for v in boxes.xyxy[i].cpu().numpy().tolist()]
            x1, y1, x2, y2 = max(0, xyxy[0]), max(0, xyxy[1]), min(w_img, xyxy[2]), min(h_img, xyxy[3])

            # Extract mask
            has_mask = False
            diameter_px = max(x2 - x1, y2 - y1)
            center = ((x1 + x2) // 2, (y1 + y2) // 2)

            if masks is not None and len(masks.data) > i:
                m_data = masks.data[i].cpu().numpy()
                m_resized = cv2.resize(m_data, (w_img, h_img), interpolation=cv2.INTER_NEAREST)
                mask_binary = (m_resized > 0.5).astype(np.uint8) * 255

                contours, _ = cv2.findContours(mask_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    cnt = max(contours, key=cv2.contourArea)
                    has_mask = True
                    if len(cnt) >= 5:
                        (cx, cy), (d1, d2), angle = cv2.fitEllipse(cnt)
                        diameter_px = max(d1, d2)
                        center = (int(cx), int(cy))

            # Stage 2: Defect Classification on crop
            crop = img_bgr[y1:y2, x1:x2]
            if crop.size > 0:
                crop_resized = cv2.resize(crop, (224, 224), interpolation=cv2.INTER_AREA)
                cls_res = m2_cls.predict(crop_resized, verbose=False)[0]
                top1_idx = int(cls_res.probs.top1)
                defect_class = m2_cls.names[top1_idx]
                defect_conf = float(cls_res.probs.top1conf)
            else:
                defect_class = "healthy"
                defect_conf = 1.0

            color = NEW_DEFECT_COLORS.get(defect_class, (0, 255, 0))

            # Draw mask contour & fill
            if has_mask and contours:
                cv2.drawContours(overlay, [cnt], -1, color, -1)
                cv2.drawContours(annotated, [cnt], -1, color, 2)
            else:
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # Draw diameter axis dot/line
            cv2.circle(annotated, center, 3, (255, 255, 255), -1)

            # Label badge
            label = f"{defect_class} {defect_conf:.2f} ({int(diameter_px)}px)"
            draw_label(annotated, label, (x1, max(16, y1)), color)

            detections.append({
                "defect_class": defect_class,
                "defect_conf": defect_conf,
                "seg_conf": b_conf,
                "diameter_px": round(diameter_px, 1),
                "has_mask": has_mask
            })

    # Blend semi-transparent mask
    cv2.addWeighted(overlay, 0.25, annotated, 0.75, 0, annotated)
    lat_ms = (time.perf_counter() - t0) * 1000.0

    return annotated, detections, lat_ms


def build_comparison_panel(img_name, old_img, old_dets, old_lat, new_img, new_dets, new_lat, target_w=640, target_h=480):
    # Resize both sides to target uniform dimension
    p_old = cv2.resize(old_img, (target_w, target_h), interpolation=cv2.INTER_AREA)
    p_new = cv2.resize(new_img, (target_w, target_h), interpolation=cv2.INTER_AREA)

    # Add header bars
    bar_h = 44
    header_old = np.zeros((bar_h, target_w, 3), dtype=np.uint8)
    header_old[:] = (40, 40, 40)
    cv2.putText(header_old, f"OLD MODEL: YOLOv8n BBox Detect ({len(old_dets)} bulbs, {old_lat:.1f}ms)", (12, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)

    header_new = np.zeros((bar_h, target_w, 3), dtype=np.uint8)
    header_new[:] = (20, 50, 25)
    cv2.putText(header_new, f"NEW PIPELINE: YOLOv8n-seg + Cls ({len(new_dets)} bulbs, {new_lat:.1f}ms)", (12, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)

    col_old = np.vstack([header_old, p_old])
    col_new = np.vstack([header_new, p_new])

    # Side-by-side divider line
    divider = np.full((target_h + bar_h, 6, 3), 180, dtype=np.uint8)
    row = np.hstack([col_old, divider, col_new])

    # Add image title banner
    banner = np.zeros((30, row.shape[1], 3), dtype=np.uint8)
    banner[:] = (15, 15, 15)
    cv2.putText(banner, f"Sample: {img_name}", (14, 21),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 255), 1, cv2.LINE_AA)

    return np.vstack([banner, row])


def main():
    print("=" * 80)
    print(" ONION QUALITY ASSESSMENT - MODEL COMPARISON BENCHMARK")
    print(" Comparing Old Model (Onion_grading_backup) vs New Pipeline (Onion_grading_new)")
    print("=" * 80)

    old_model, m1_seg, m2_cls = load_models()

    img_paths = sorted(TEST_IMAGES_DIR.glob("*.*"))
    valid_paths = [p for p in img_paths if p.suffix.lower() in [".jpg", ".jpeg", ".png"]]

    print(f"\nFound {len(valid_paths)} test images in {TEST_IMAGES_DIR}")

    rows = []
    benchmark_data = []

    for idx, p in enumerate(valid_paths):
        img_bgr = cv2.imread(str(p))
        if img_bgr is None:
            continue

        print(f"\n[{idx+1}/{len(valid_paths)}] Processing {p.name}...")
        old_annotated, old_dets, old_lat = run_old_model(old_model, img_bgr)
        new_annotated, new_dets, new_lat = run_new_pipeline(m1_seg, m2_cls, img_bgr)

        # Defect breakdown
        old_counts = {}
        for d in old_dets:
            c = d["class"]
            old_counts[c] = old_counts.get(c, 0) + 1

        new_counts = {}
        for d in new_dets:
            c = d["defect_class"]
            new_counts[c] = new_counts.get(c, 0) + 1

        print(f"  Old Model: {len(old_dets)} detections | Classes: {old_counts} | Latency: {old_lat:.1f}ms")
        print(f"  New Model: {len(new_dets)} detections | Classes: {new_counts} | Latency: {new_lat:.1f}ms")

        benchmark_data.append({
            "image": p.name,
            "old_count": len(old_dets),
            "old_classes": old_counts,
            "old_lat_ms": old_lat,
            "new_count": len(new_dets),
            "new_classes": new_counts,
            "new_lat_ms": new_lat,
        })

        # Build comparison row
        panel = build_comparison_panel(p.name, old_annotated, old_dets, old_lat, new_annotated, new_dets, new_lat)
        rows.append(panel)

    # Stitch top-to-bottom montage
    if rows:
        montage = np.vstack(rows)
        OUTPUT_PLOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(OUTPUT_PLOT_PATH), montage)
        print("\n" + "=" * 80)
        print(f" SAVED SIDE-BY-SIDE VISUAL COMPARISON TO:")
        print(f" {OUTPUT_PLOT_PATH}")
        print("=" * 80)

    # Print summary benchmark table
    print("\n" + "=" * 80)
    print(" BENCHMARK SUMMARY TABLE")
    print("=" * 80)
    header = f"{'Image':<28} | {'Old Count':<10} | {'Old Defect Breakdown':<24} | {'New Count':<10} | {'New Defect Breakdown':<28} | {'Latency Old/New'}"
    print(header)
    print("-" * len(header))
    for b in benchmark_data:
        old_cls_str = ", ".join(f"{k}:{v}" for k, v in b['old_classes'].items()) if b['old_classes'] else "none"
        new_cls_str = ", ".join(f"{k}:{v}" for k, v in b['new_classes'].items()) if b['new_classes'] else "none"
        print(f"{b['image']:<28} | {b['old_count']:<10} | {old_cls_str:<24} | {b['new_count']:<10} | {new_cls_str:<28} | {b['old_lat_ms']:.1f}ms / {b['new_lat_ms']:.1f}ms")
    print("=" * 80)


if __name__ == "__main__":
    main()
