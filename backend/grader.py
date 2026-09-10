from pathlib import Path
from typing import Any, List, Literal
import cv2
from pydantic import BaseModel, Field
from ultralytics import YOLO


class QualityBreakdown(BaseModel):
    healthy: int = 0
    rotten: int = 0
    sprouted: int = 0
    damaged: int = 0  # Double-split / cut / mechanical damage


class QualityPercentages(BaseModel):
    healthy: float = 0.0
    rotten: float = 0.0
    sprouted: float = 0.0
    damaged: float = 0.0


class SizeBreakdown(BaseModel):
    small: int = 0    # < 40mm (Undersized defect in DoCA FAQ)
    medium: int = 0   # 40 - 70mm (Standard FAQ Procurement target)
    large: int = 0    # > 70mm


class SizePercentages(BaseModel):
    small: float = 0.0
    medium: float = 0.0
    large: float = 0.0


class ComplianceRule(BaseModel):
    name: str
    category: str
    actual_value: float
    threshold_value: float
    unit: str = "%"
    passed: bool
    status: Literal["pass", "warning", "fail"]
    description: str


class DecisionResult(BaseModel):
    grade: str
    status: Literal["accepted", "conditional", "rejected"]
    recommendation: str
    summary: str
    buffer_stock_fit: bool
    reasons: List[str]
    compliance_rules: List[ComplianceRule]


class CalibrationInfo(BaseModel):
    mode: str
    mm_per_pixel: float
    is_calibrated: bool
    label: str
    description: str


class AuditMetrics(BaseModel):
    total_detected: int
    raw_detections: int
    duplicates_suppressed: int
    avg_confidence: float
    nms_mode: str
    iou_threshold: float
    conf_threshold: float
    validation_passed: bool
    validation_message: str


class GradingResult(BaseModel):
    # Backward compatibility fields
    onion: int = 0
    double_split: int = 0
    rotten: int = 0
    sprout: int = 0
    small: int = 0
    medium: int = 0
    large: int = 0
    annotated_image_filename: str | None = None

    # Enhanced lot-level grading
    total_detected: int = 0
    quality_counts: QualityBreakdown = Field(default_factory=QualityBreakdown)
    quality_percentages: QualityPercentages = Field(default_factory=QualityPercentages)
    size_counts: SizeBreakdown = Field(default_factory=SizeBreakdown)
    size_percentages: SizePercentages = Field(default_factory=SizePercentages)

    decision: DecisionResult
    calibration: CalibrationInfo
    audit_metrics: AuditMetrics


class OnionGrader:
    DEFAULT_PPI = 40.0
    DEFAULT_MM_PER_PIXEL = 25.4 / DEFAULT_PPI  # ~0.635 mm/px

    def __init__(self, model_path: str | Path):
        """Initializes the YOLO model from the given path."""
        self.model = YOLO(str(model_path))
        self.names = self.model.names  # {0: 'double_split', 1: 'onion', 2: 'rotten', 3: 'sprout'}

    def process_image(
        self,
        image_path: Path,
        output_dir: Path,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        calibration_mode: str = "estimated",
        custom_mm_per_pixel: float | None = None,
        reference_dimension_mm: float | None = None,
        reference_pixels: float | None = None,
    ) -> GradingResult:
        """
        Runs YOLO inference on the image using Class-Agnostic NMS to eliminate duplicate
        or overlapping boxes on the same bulb, calculates physical size based on calibration,
        and computes lot-level grading metrics against DoCA / AGMARK FAQ standards.
        """
        # Determine scale calibration
        mm_per_pixel = self.DEFAULT_MM_PER_PIXEL
        is_calibrated = False
        calib_label = "Estimated Scale (~0.64 mm/px)"
        calib_desc = "Uncalibrated image. Size categories are estimated assuming standard 40 PPI camera working distance."

        if custom_mm_per_pixel and custom_mm_per_pixel > 0:
            mm_per_pixel = float(custom_mm_per_pixel)
            is_calibrated = True
            calib_label = f"Calibrated ({mm_per_pixel:.3f} mm/px)"
            calib_desc = f"Calibrated using custom scale of {mm_per_pixel:.3f} mm per pixel."
        elif reference_dimension_mm and reference_pixels and reference_pixels > 0:
            mm_per_pixel = float(reference_dimension_mm) / float(reference_pixels)
            is_calibrated = True
            calib_label = f"Calibrated ({mm_per_pixel:.3f} mm/px)"
            calib_desc = f"Calibrated using reference marker ({reference_dimension_mm:.1f} mm / {reference_pixels:.1f} px)."
        elif calibration_mode == "coin_25mm" and reference_pixels and reference_pixels > 0:
            mm_per_pixel = 25.0 / float(reference_pixels)
            is_calibrated = True
            calib_label = f"Coin Calibrated ({mm_per_pixel:.3f} mm/px)"
            calib_desc = "Calibrated using ₹10 reference coin (25 mm diameter)."

        # 1. Run raw inference without class-agnostic NMS to track suppressed duplicates
        raw_results: Any = self.model.predict(
            source=str(image_path),
            conf=conf_threshold,
            iou=0.7,
            agnostic_nms=False,
            verbose=False,
        )
        raw_boxes_count = len(raw_results[0].boxes) if raw_results and len(raw_results) > 0 else 0

        # 2. Run deduplicated inference with Class-Agnostic NMS
        # This prevents a single bulb from having multiple detections (e.g. 'onion' + 'rotten')
        results: Any = self.model.predict(
            source=str(image_path),
            conf=conf_threshold,
            iou=iou_threshold,
            agnostic_nms=True,
            verbose=False,
        )
        result = results[0]
        boxes = result.boxes
        total_detected = len(boxes)
        duplicates_suppressed = max(0, raw_boxes_count - total_detected)

        # Count classes & sizes
        counts = {"onion": 0, "double_split": 0, "rotten": 0, "sprout": 0}
        sizes = {"small": 0, "medium": 0, "large": 0}
        confidences: List[float] = []

        for box in boxes:
            class_id = int(box.cls[0].item())
            class_name = self.names.get(class_id, "unknown")
            if class_name in counts:
                counts[class_name] += 1

            conf = float(box.conf[0].item())
            confidences.append(conf)

            # Calculate size in mm
            # box.xywh[0] contains [x_center, y_center, width, height]
            width = box.xywh[0][2].item()
            height = box.xywh[0][3].item()
            diameter_px = max(width, height)
            diameter_mm = diameter_px * mm_per_pixel

            # Categorize size according to AGMARK / DoCA FAQ criteria
            if diameter_mm < 40.0:
                sizes["small"] += 1
            elif diameter_mm <= 70.0:
                sizes["medium"] += 1
            else:
                sizes["large"] += 1

        avg_conf = (sum(confidences) / len(confidences) * 100) if confidences else 0.0

        # Quality breakdown mapping
        # In DoCA standards: double_split represents structural / split damage
        healthy_count = counts["onion"]
        rotten_count = counts["rotten"]
        sprouted_count = counts["sprout"]
        damaged_count = counts["double_split"]

        quality_counts = QualityBreakdown(
            healthy=healthy_count,
            rotten=rotten_count,
            sprouted=sprouted_count,
            damaged=damaged_count,
        )

        size_counts = SizeBreakdown(
            small=sizes["small"],
            medium=sizes["medium"],
            large=sizes["large"],
        )

        # Percentages calculation
        if total_detected > 0:
            quality_pcts = QualityPercentages(
                healthy=round((healthy_count / total_detected) * 100, 1),
                rotten=round((rotten_count / total_detected) * 100, 1),
                sprouted=round((sprouted_count / total_detected) * 100, 1),
                damaged=round((damaged_count / total_detected) * 100, 1),
            )
            size_pcts = SizePercentages(
                small=round((sizes["small"] / total_detected) * 100, 1),
                medium=round((sizes["medium"] / total_detected) * 100, 1),
                large=round((sizes["large"] / total_detected) * 100, 1),
            )
        else:
            quality_pcts = QualityPercentages()
            size_pcts = SizePercentages()

        # 3. Rule-based evaluation against DoCA / AGMARK FAQ standards
        decision = self._evaluate_doca_standards(
            total_detected=total_detected,
            quality_counts=quality_counts,
            quality_percentages=quality_pcts,
            size_counts=size_counts,
            size_percentages=size_pcts,
        )

        # 4. Integrity check
        quality_sum = healthy_count + rotten_count + sprouted_count + damaged_count
        size_sum = sizes["small"] + sizes["medium"] + sizes["large"]
        validation_passed = (total_detected == quality_sum == size_sum)
        validation_message = (
            f"Verified: All {total_detected} detected onions are accounted for with zero double-counting."
            if validation_passed
            else f"Validation warning: Detected {total_detected}, Quality sum {quality_sum}, Size sum {size_sum}."
        )

        # 5. Save annotated image
        annotated_img = result.plot()
        annotated_filename = f"graded_{image_path.name}"
        annotated_path = output_dir / annotated_filename
        cv2.imwrite(str(annotated_path), annotated_img)

        return GradingResult(
            onion=counts["onion"],
            double_split=counts["double_split"],
            rotten=counts["rotten"],
            sprout=counts["sprout"],
            small=sizes["small"],
            medium=sizes["medium"],
            large=sizes["large"],
            annotated_image_filename=annotated_filename,
            total_detected=total_detected,
            quality_counts=quality_counts,
            quality_percentages=quality_pcts,
            size_counts=size_counts,
            size_percentages=size_pcts,
            decision=decision,
            calibration=CalibrationInfo(
                mode=calibration_mode,
                mm_per_pixel=round(mm_per_pixel, 4),
                is_calibrated=is_calibrated,
                label=calib_label,
                description=calib_desc,
            ),
            audit_metrics=AuditMetrics(
                total_detected=total_detected,
                raw_detections=raw_boxes_count,
                duplicates_suppressed=duplicates_suppressed,
                avg_confidence=round(avg_conf, 1),
                nms_mode="Class-Agnostic NMS",
                iou_threshold=iou_threshold,
                conf_threshold=conf_threshold,
                validation_passed=validation_passed,
                validation_message=validation_message,
            ),
        )

    def _evaluate_doca_standards(
        self,
        total_detected: int,
        quality_counts: QualityBreakdown,
        quality_percentages: QualityPercentages,
        size_counts: SizeBreakdown,
        size_percentages: SizePercentages,
    ) -> DecisionResult:
        """
        Evaluates detected onion statistics against DoCA (Department of Consumer Affairs)
        and AGMARK Fair Average Quality (FAQ) Procurement Specifications.
        """
        if total_detected == 0:
            return DecisionResult(
                grade="Inconclusive (No Bulbs Detected)",
                status="rejected",
                recommendation="Re-upload a clear photograph of sample tray",
                summary="The vision model did not detect any onion bulbs in the provided image.",
                buffer_stock_fit=False,
                reasons=["No onion bulbs were localized in the image. Please verify lighting and frame."],
                compliance_rules=[],
            )

        rules: List[ComplianceRule] = []
        reasons: List[str] = []

        # 1. Rotten check
        rotten_pct = quality_percentages.rotten
        rotten_pass_g1 = rotten_pct <= 2.0
        rotten_pass_g2 = rotten_pct <= 4.0
        rotten_status: Literal["pass", "warning", "fail"] = (
            "pass" if rotten_pass_g1 else ("warning" if rotten_pass_g2 else "fail")
        )
        rules.append(
            ComplianceRule(
                name="Rotten / Decay Tolerance",
                category="Quality Defect",
                actual_value=rotten_pct,
                threshold_value=2.0,
                passed=rotten_pass_g1,
                status=rotten_status,
                description="DoCA FAQ limit: Max 2.0% for Grade I; max 4.0% for Grade II.",
            )
        )
        if rotten_status == "fail":
            reasons.append(
                f"❌ Rotten bulb rate of {rotten_pct}% exceeds DoCA FAQ rejection limit (4.0%). High rot risk in buffer storage."
            )
        elif rotten_status == "warning":
            reasons.append(
                f"⚠️ Rotten rate of {rotten_pct}% is elevated above Grade I tolerance (2.0%), acceptable only under Grade II."
            )
        else:
            reasons.append(f"✅ Rotten rate is {rotten_pct}% (within strict 2.0% FAQ tolerance).")

        # 2. Sprouted check
        sprouted_pct = quality_percentages.sprouted
        sprouted_pass_g1 = sprouted_pct <= 3.0
        sprouted_pass_g2 = sprouted_pct <= 7.0
        sprouted_status: Literal["pass", "warning", "fail"] = (
            "pass" if sprouted_pass_g1 else ("warning" if sprouted_pass_g2 else "fail")
        )
        rules.append(
            ComplianceRule(
                name="Sprouted Bulbs Tolerance",
                category="Physiological Defect",
                actual_value=sprouted_pct,
                threshold_value=3.0,
                passed=sprouted_pass_g1,
                status=sprouted_status,
                description="DoCA FAQ limit: Max 3.0% for Grade I; max 7.0% for Grade II.",
            )
        )
        if sprouted_status == "fail":
            reasons.append(
                f"❌ Sprouted bulb rate of {sprouted_pct}% exceeds DoCA FAQ rejection limit (7.0%). Sprouted bulbs cannot be stored."
            )
        elif sprouted_status == "warning":
            reasons.append(
                f"⚠️ Sprouted rate of {sprouted_pct}% exceeds Grade I tolerance (3.0%), within Grade II conditional limit."
            )

        # 3. Damaged (Double Split) check
        damaged_pct = quality_percentages.damaged
        damaged_pass_g1 = damaged_pct <= 5.0
        damaged_pass_g2 = damaged_pct <= 10.0
        damaged_status: Literal["pass", "warning", "fail"] = (
            "pass" if damaged_pass_g1 else ("warning" if damaged_pass_g2 else "fail")
        )
        rules.append(
            ComplianceRule(
                name="Damaged (Double Split) Tolerance",
                category="Structural Defect",
                actual_value=damaged_pct,
                threshold_value=5.0,
                passed=damaged_pass_g1,
                status=damaged_status,
                description="DoCA FAQ limit: Max 5.0% for Grade I; max 10.0% for Grade II.",
            )
        )
        if damaged_status == "fail":
            reasons.append(
                f"❌ Damaged (double split) bulb rate of {damaged_pct}% exceeds maximum FAQ tolerance of 10.0%."
            )
        elif damaged_status == "warning":
            reasons.append(
                f"⚠️ Damaged (double split) rate of {damaged_pct}% is elevated above Grade I limit (5.0%)."
            )

        # 4. Undersized check (<40mm)
        undersized_pct = size_percentages.small
        undersized_pass_g1 = undersized_pct <= 5.0
        undersized_pass_g2 = undersized_pct <= 10.0
        undersized_status: Literal["pass", "warning", "fail"] = (
            "pass" if undersized_pass_g1 else ("warning" if undersized_pass_g2 else "fail")
        )
        rules.append(
            ComplianceRule(
                name="Undersized (< 40mm) Tolerance",
                category="Size Compliance",
                actual_value=undersized_pct,
                threshold_value=5.0,
                passed=undersized_pass_g1,
                status=undersized_status,
                description="DoCA FAQ specification requires bulb diameter >= 40mm. Max 5.0% undersized for Grade I.",
            )
        )
        if undersized_status == "fail":
            reasons.append(
                f"⚠️ Undersized bulb proportion ({undersized_pct}%) exceeds 10.0% FAQ tolerance. Requires size grading deduction."
            )

        # 5. Healthy / Sound bulb ratio
        sound_pct = quality_percentages.healthy
        sound_pass_g1 = sound_pct >= 85.0
        sound_pass_g2 = sound_pct >= 70.0
        sound_status: Literal["pass", "warning", "fail"] = (
            "pass" if sound_pass_g1 else ("warning" if sound_pass_g2 else "fail")
        )
        rules.append(
            ComplianceRule(
                name="Sound Bulbs Proportion (Grade A)",
                category="Quality Minimum",
                actual_value=sound_pct,
                threshold_value=85.0,
                passed=sound_pass_g1,
                status=sound_status,
                description="DoCA FAQ minimum: >= 85.0% for Grade I; >= 70.0% for Grade II.",
            )
        )
        if sound_status == "fail":
            reasons.append(
                f"❌ Sound Grade A proportion ({sound_pct}%) falls below minimum procurement threshold of 70.0%."
            )
        else:
            reasons.append(f"✅ Sound Grade A proportion is {sound_pct}%.")

        # Cumulative defect rate
        total_defects_pct = round(100.0 - sound_pct, 1)

        # Final Procurement Decision
        is_urs = (
            rotten_pct > 4.0
            or sprouted_pct > 7.0
            or damaged_pct > 10.0
            or sound_pct < 70.0
            or total_defects_pct > 25.0
        )

        is_grade_1 = (
            rotten_pass_g1
            and sprouted_pass_g1
            and damaged_pass_g1
            and undersized_pass_g1
            and sound_pass_g1
        )

        if is_urs:
            grade = "URS (Under Rejection Standard)"
            status = "rejected"
            recommendation = "Reject Lot - Unfit for Central Buffer Stock"
            summary = (
                f"Lot failed DoCA FAQ procurement standards (Defects: {total_defects_pct}%). "
                "High risk of rotting and shrinkage during warehouse storage."
            )
            buffer_fit = False
        elif is_grade_1:
            grade = "Grade I (FAQ - Accepted)"
            status = "accepted"
            recommendation = "Procure for Central Buffer Stock (NAFED / NCCF)"
            summary = (
                f"Lot fully satisfies DoCA Grade I FAQ standards with {sound_pct}% sound bulbs. "
                "Excellent storage viability for Price Stabilization Fund (PSF) buffer."
            )
            buffer_fit = True
        else:
            grade = "Grade II (FAQ - Conditional)"
            status = "conditional"
            recommendation = "Conditional Acceptance with FAQ Value Deduction"
            summary = (
                f"Lot meets Grade II FAQ specifications ({sound_pct}% sound). "
                "Recommended for immediate local market release rather than long-term buffer."
            )
            buffer_fit = False

        return DecisionResult(
            grade=grade,
            status=status,
            recommendation=recommendation,
            summary=summary,
            buffer_stock_fit=buffer_fit,
            reasons=reasons,
            compliance_rules=rules,
        )

