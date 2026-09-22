"""End-to-End Inference Pipeline for Onion Quality Assessment and Grading.

Orchestrates:
  1. In-frame ArUco marker detection & metric scale calibration
  2. Model 1 (YOLOv8-seg) onion detection and polygon mask segmentation
  3. Geometric diameter extraction & height-above-plane focal compensation
  4. Model 2 (YOLOv8-cls) 4-class defect classification (healthy, sprouted, rotten, mechanical_damage)
  5. HSV/Lab surface discolouration thresholding (% blemish)
  6. Regulatory Rule Engine (DoCA buffer-stock 45-65mm norm, AGMARK tiers, FSSAI compliance remarks)
  7. Visual overlays rendering & lot statistics aggregation
"""

from __future__ import annotations

from datetime import datetime, timezone
import math
from pathlib import Path
from typing import List, Optional, Tuple
import cv2
import numpy as np
from ultralytics import YOLO

from training.calibration.aruco_calibrator import ArUcoCalibrator
from training.common.rule_engine import estimate_weight_grams, evaluate_onion_grades, summarize_lot
from training.common.schemas import (
    CalibrationMetadata,
    CalibrationMode,
    GradesResult,
    LotReportSummary,
    OnionMeasurements,
    OnionRecord,
    QualityFlags,
)


class GradingPipeline:
    def __init__(
        self,
        seg_model_path: str | Path = "runs/weights/model1_yolov8_seg.pt",
        cls_model_path: str | Path = "runs/weights/model2_defect_cls.pt",
        device: str = "cpu",
    ):
        self.seg_model_path = Path(seg_model_path)
        self.cls_model_path = Path(cls_model_path)
        self.device = device

        if not self.seg_model_path.exists():
            raise FileNotFoundError(f"Model 1 weights not found at: {self.seg_model_path}")
        if not self.cls_model_path.exists():
            raise FileNotFoundError(f"Model 2 weights not found at: {self.cls_model_path}")

        print(f"Loading Model 1 (seg) from {self.seg_model_path}...")
        self.model1 = YOLO(str(self.seg_model_path))
        print(f"Loading Model 2 (cls) from {self.cls_model_path}...")
        self.model2 = YOLO(str(self.cls_model_path))

        self.calibrator = ArUcoCalibrator()

    def _measure_discolouration_percent(
        self,
        image_bgr: np.ndarray,
        mask_binary: np.ndarray,
    ) -> float:
        """Measures surface blemish / discolouration area as % of visible bulb mask using Lab color distance."""
        mask_indices = np.where(mask_binary > 0)
        total_pixels = len(mask_indices[0])
        if total_pixels < 20:
            return 0.0

        lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
        bulb_pixels = lab[mask_indices]

        # Calculate median skin color from central region
        eroded_mask = cv2.erode(mask_binary, np.ones((7, 7), np.uint8))
        eroded_indices = np.where(eroded_mask > 0)
        if len(eroded_indices[0]) > 20:
            median_color = np.median(lab[eroded_indices], axis=0)
        else:
            median_color = np.median(bulb_pixels, axis=0)

        # Delta E approximation using true CIELAB scaling (L: 0-100, a,b: -128..127)
        # Weight L at 0.4 to prevent natural lighting/shadow gradients from falsely registering as blemishes
        delta_l = (bulb_pixels[:, 0].astype(np.float32) - median_color[0]) * (100.0 / 255.0)
        delta_a = bulb_pixels[:, 1].astype(np.float32) - median_color[1]
        delta_b = bulb_pixels[:, 2].astype(np.float32) - median_color[2]
        dist = np.sqrt((0.4 * delta_l) ** 2 + delta_a ** 2 + delta_b ** 2)

        # Pixels with significant color deviation (e.g. greening, black rot, thrips damage: Delta E > 40.0)
        discoloured_count = np.count_nonzero(dist > 40.0)
        pct = (discoloured_count / total_pixels) * 100.0
        return round(float(pct), 1)

    def analyze_image(
        self,
        image_bgr: np.ndarray,
        lot_id: str = "LOT-001",
        center_id: str = "NAFED-Nashik-01",
        focal_length_px: Optional[float] = None,
        conf_threshold: float = 0.25,
        custom_px_per_mm: Optional[float] = None,
    ) -> Tuple[LotReportSummary, np.ndarray]:
        """Runs end-to-end quality assessment on a single image.
        
        Returns:
            (LotReportSummary, annotated_image_bgr)
        """
        h_img, w_img = image_bgr.shape[:2]
        annotated_img = image_bgr.copy()

        # 1. Step 1: Detect ArUco Marker
        marker_found, marker_corners, tilt_deg = self.calibrator.detect_marker(image_bgr)

        # 2. Step 2: Run Model 1 Instance Segmentation
        seg_results = self.model1.predict(
            image_bgr,
            conf=conf_threshold,
            device=self.device,
            verbose=False,
        )

        detected_records: List[OnionRecord] = []
        raw_pixel_diameters: List[float] = []
        raw_onion_data: List[dict] = []

        res0 = seg_results[0]
        boxes = res0.boxes
        masks = res0.masks

        if boxes is not None and len(boxes) > 0:
            for i in range(len(boxes)):
                bbox = boxes.xyxy[i].cpu().numpy().tolist()
                conf = float(boxes.conf[i].cpu().numpy())

                # Get binary mask
                if masks is not None and len(masks.data) > i:
                    m_data = masks.data[i].cpu().numpy()
                    m_resized = cv2.resize(m_data, (w_img, h_img), interpolation=cv2.INTER_NEAREST)
                    mask_binary = (m_resized > 0.5).astype(np.uint8) * 255
                else:
                    # Fallback box mask
                    x1, y1, x2, y2 = [int(v) for v in bbox]
                    mask_binary = np.zeros((h_img, w_img), dtype=np.uint8)
                    mask_binary[max(0, y1):min(h_img, y2), max(0, x1):min(w_img, x2)] = 255

                # Find contour to extract diameter
                contours, _ = cv2.findContours(mask_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    cnt = max(contours, key=cv2.contourArea)
                    if len(cnt) >= 5:
                        (cx, cy), (d1, d2), angle = cv2.fitEllipse(cnt)
                        diam_px = max(d1, d2)
                        height_px = min(d1, d2)
                    else:
                        (cx, cy), radius = cv2.minEnclosingCircle(cnt)
                        diam_px = radius * 2.0
                        height_px = diam_px
                else:
                    bx_w = bbox[2] - bbox[0]
                    bx_h = bbox[3] - bbox[1]
                    diam_px = max(bx_w, bx_h)
                    height_px = min(bx_w, bx_h)
                    cnt = None

                raw_pixel_diameters.append(diam_px)
                raw_onion_data.append({
                    "bbox": bbox,
                    "conf": conf,
                    "mask_binary": mask_binary,
                    "contour": cnt,
                    "diam_px": diam_px,
                    "height_px": height_px,
                })

        # 3. Step 3: Calibrate Scale
        calib_metadata, px_per_mm = self.calibrator.calibrate(
            image_bgr,
            exif_focal_px=focal_length_px,
            detected_onion_pixel_diameters=raw_pixel_diameters,
        )

        if not calib_metadata.card_detected and custom_px_per_mm and custom_px_per_mm > 0:
            px_per_mm = float(custom_px_per_mm)
            calib_metadata = CalibrationMetadata(
                mode=CalibrationMode.CALIBRATED_ARUCO,
                scale_source=f"device_burner_calibrated_{custom_px_per_mm:.2f}px_per_mm",
                mm_reliable=True,
                card_detected=False,
                tilt_degrees=0.0,
                pixels_per_mm=round(float(custom_px_per_mm), 3),
            )

        # 4. Step 4: Process Each Onion (Defect Classification + Rule Evaluation)
        for idx, item in enumerate(raw_onion_data):
            onion_id = f"O-{idx+1:02d}"
            bbox = item["bbox"]
            conf = item["conf"]
            diam_px = item["diam_px"]
            height_px = item["height_px"]
            mask_binary = item["mask_binary"]
            cnt = item["contour"]

            # Apparent diameter in mm
            apparent_diam_mm = diam_px / max(px_per_mm, 1e-6)
            apparent_height_mm = height_px / max(px_per_mm, 1e-6)

            # Apply height-above-plane focal correction if calibrated
            if calib_metadata.mm_reliable:
                focal_px = focal_length_px or self.calibrator.default_focal_px
                corrected_diam_mm = self.calibrator.compensate_height_above_plane(
                    apparent_diam_mm,
                    bulb_height_above_plane_mm=apparent_diam_mm,
                    focal_px=focal_px,
                )
                corrected_height_mm = self.calibrator.compensate_height_above_plane(
                    apparent_height_mm,
                    bulb_height_above_plane_mm=apparent_height_mm,
                    focal_px=focal_px,
                )
            else:
                corrected_diam_mm = apparent_diam_mm
                corrected_height_mm = apparent_height_mm

            # Discolouration surface %
            defect_pct = self._measure_discolouration_percent(image_bgr, mask_binary)

            # Extract 8% padded crop for Model 2
            bx1, by1, bx2, by2 = bbox
            bw, bh = bx2 - bx1, by2 - by1
            cx, cy = (bx1 + bx2) / 2.0, (by1 + by2) / 2.0
            crop_x1 = max(0, int(cx - bw * 0.54))
            crop_y1 = max(0, int(cy - bh * 0.54))
            crop_x2 = min(w_img, int(cx + bw * 0.54))
            crop_y2 = min(h_img, int(cy + bh * 0.54))

            crop = image_bgr[crop_y1:crop_y2, crop_x1:crop_x2]
            if crop.size > 0:
                crop_resized = cv2.resize(crop, (224, 224), interpolation=cv2.INTER_AREA)
                cls_out = self.model2.predict(crop_resized, device=self.device, verbose=False)
                probs = cls_out[0].probs

                # Model 2 class order: {0: 'healthy', 1: 'mechanical_damage', 2: 'rotten', 3: 'sprouted'}
                p_healthy = float(probs.data[0]) if len(probs.data) > 0 else 1.0
                p_damage = float(probs.data[1]) if len(probs.data) > 1 else 0.0
                p_rotten = float(probs.data[2]) if len(probs.data) > 2 else 0.0
                p_sprouted = float(probs.data[3]) if len(probs.data) > 3 else 0.0

                # Calibrated confidence gating with CIELAB colorimetry verification:
                # - Sprouting requires clear vegetative shoot emergence (p_sprouted >= 0.65)
                # - Rot requires either high neural confidence (p_rotten >= 0.70)
                #   OR moderate confidence (>= 0.45) corroborated by surface blemish (defect_pct >= 15.0%)
                # - Mechanical cuts/bruises require high confidence or corroborated damage blemish
                is_sprouted = p_sprouted >= 0.65
                is_rotten = p_rotten >= 0.70 or (p_rotten >= 0.45 and defect_pct >= 15.0)
                is_damaged = p_damage >= 0.70 or (p_damage >= 0.45 and defect_pct >= 20.0)
            else:
                is_sprouted = False
                is_rotten = False
                is_damaged = False

            # Set quality flags
            flags = QualityFlags(
                sprouted=is_sprouted,
                rotten=is_rotten,
                severe_damage=is_damaged,
            )

            # Volumetric weight estimation
            weight_g = estimate_weight_grams(corrected_diam_mm, corrected_height_mm)

            # Build measurements object
            measurements = OnionMeasurements(
                equatorial_diameter_mm=round(corrected_diam_mm, 1),
                height_mm=round(corrected_height_mm, 1),
                estimated_weight_g=weight_g,
                defect_area_percent=defect_pct,
            )

            # Evaluate regulatory grades
            grades = evaluate_onion_grades(measurements, flags)

            record = OnionRecord(
                onion_id=onion_id,
                bbox=[round(v, 1) for v in bbox],
                confidence=round(conf, 3),
                measurements=measurements,
                quality_flags=flags,
                grades=grades,
            )
            detected_records.append(record)

            # 5. Render visual overlays
            # Color code based on grade/defect
            if flags.rotten or flags.severe_damage:
                color = (0, 0, 255)       # Red: Severe Defect / Rotten
                status_txt = "REJECT: " + ("ROTTEN" if flags.rotten else "DAMAGED")
            elif flags.sprouted:
                color = (0, 140, 255)     # Orange: Sprouted
                status_txt = "REJECT: SPROUT"
            elif "Non-Grade-A" in grades.procurement_grade:
                color = (0, 215, 255)     # Yellow: Size non-compliant
                status_txt = "NON-A"
            else:
                color = (0, 255, 0)       # Green: Grade-A
                status_txt = "GRADE-A"

            # Draw polygon or box
            if cnt is not None:
                cv2.drawContours(annotated_img, [cnt], -1, color, 2)
            cv2.rectangle(annotated_img, (int(bx1), int(by1)), (int(bx2), int(by2)), color, 1)

            # Label banner
            lbl = f"{onion_id}: {measurements.equatorial_diameter_mm}mm | {status_txt}"
            t_size, _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(
                annotated_img,
                (int(bx1), max(0, int(by1) - 18)),
                (int(bx1) + t_size[0] + 4, max(0, int(by1))),
                color,
                -1,
            )
            cv2.putText(
                annotated_img,
                lbl,
                (int(bx1) + 2, max(12, int(by1) - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 0, 0) if color == (0, 255, 0) or color == (0, 215, 255) else (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

        # 6. Render ArUco marker overlay if detected
        if marker_found and marker_corners is not None:
            c = marker_corners.astype(int)
            cv2.polylines(annotated_img, [c], True, (255, 0, 255), 2)
            m_txt = f"ArUco 50mm (tilt: {tilt_deg}deg)"
            cv2.putText(
                annotated_img,
                m_txt,
                (int(c[0][0]), max(15, int(c[0][1]) - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 0, 255),
                1,
                cv2.LINE_AA,
            )

        # 7. Step 7: Build Lot Summary Report
        ts = datetime.now(timezone.utc).isoformat()
        lot_summary = summarize_lot(
            lot_id=lot_id,
            center_id=center_id,
            timestamp=ts,
            calibration=calib_metadata,
            onions=detected_records,
        )

        return lot_summary, annotated_img
