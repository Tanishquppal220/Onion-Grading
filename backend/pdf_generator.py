"""PDF Inspection Certificate Generator using ReportLab.

Generates official A4 audit certificates for DoCA Buffer-Stock Procurement
and AGMARK commercial onion grading.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Optional
import cv2
import numpy as np

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from training.common.schemas import LotReportSummary


def generate_lot_pdf_report(
    summary: LotReportSummary,
    annotated_image_bgr: Optional[np.ndarray] = None,
    output_path: Optional[str | Path] = None,
) -> bytes:
    """Generates an official A4 PDF quality assessment report.
    
    Returns:
        bytes of the PDF document
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontSize=16,
        leading=20,
        alignment=1,
        textColor=colors.HexColor("#1A365D"),
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        leading=13,
        alignment=1,
        textColor=colors.HexColor("#4A5568"),
    )
    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#2B6CB0"),
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#2D3748"),
    )
    table_hdr_style = ParagraphStyle(
        "TableHdr",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    story = []

    # 1. Official Header
    story.append(Paragraph("ONION QUALITY ASSESSMENT & GRADING CERTIFICATE", title_style))
    story.append(Paragraph("Procurement Center Digital Inspection Audit · Department of Consumer Affairs (DoCA) & AGMARK Standards", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2B6CB0"), spaceAfter=10))

    # 2. Calibration Banner
    if summary.calibration.mm_reliable:
        if summary.calibration.card_detected:
            calib_text = f"<b>CALIBRATION VERIFIED (In-Frame ArUco):</b> Reference marker detected ({summary.calibration.pixels_per_mm:.1f} px/mm, camera tilt: {summary.calibration.tilt_degrees or 0.0:.1f}°). True metric millimeters verified."
            calib_color = colors.HexColor("#C6F6D5")
            calib_border = colors.HexColor("#38A169")
            txt_color = colors.HexColor("#22543D")
        else:
            ppi_val = round(summary.calibration.pixels_per_mm * 25.4, 1)
            calib_text = f"<b>DEVICE PROFILE CALIBRATED (Session Burner Reference):</b> Verified scale ({summary.calibration.pixels_per_mm:.2f} px/mm, {ppi_val} PPI). True metric millimeters verified without in-frame card."
            calib_color = colors.HexColor("#EBF8FF")
            calib_border = colors.HexColor("#3182CE")
            txt_color = colors.HexColor("#2A4365")
    else:
        calib_text = "<b>WARNING — UNCALIBRATED LOT:</b> No optical reference marker detected. Measurements derived from 55 mm median bulb prior. Indicative estimates only."
        calib_color = colors.HexColor("#FEEBC8")
        calib_border = colors.HexColor("#DD6B20")
        txt_color = colors.HexColor("#7B341E")

    calib_p = Paragraph(f"<font color='{txt_color}'>{calib_text}</font>", body_style)
    calib_table = Table([[calib_p]], colWidths=[540])
    calib_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), calib_color),
        ("BOX", (0, 0), (-1, -1), 1, calib_border),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(calib_table)
    story.append(Spacer(1, 10))

    # 3. Lot Meta Information & Key Metrics Cards
    doca_grade_a_pct = summary.procurement_grade_distribution.get("Grade-A", 0.0)

    meta_data = [
        [
            Paragraph("<b>Lot Identifier:</b> " + summary.lot_id, body_style),
            Paragraph("<b>Procurement Center:</b> " + summary.center_id, body_style),
        ],
        [
            Paragraph("<b>Inspection Date:</b> " + summary.timestamp[:19].replace("T", " ") + " UTC", body_style),
            Paragraph("<b>Standard Enforced:</b> DoCA 45-65 mm Buffer Stock", body_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[270, 270])
    meta_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # KPI Summary Cards
    kpi_headers = ["Total Sampled", "Estimated Weight", "DoCA Grade-A", "Defect Rate", "Mean Diameter"]
    kpi_values = [
        f"{summary.total_onions_inspected} bulbs",
        f"{summary.estimated_lot_weight_kg or 0.0} kg",
        f"{doca_grade_a_pct:.1f}%",
        f"{summary.defective_percent:.1f}%",
        f"{summary.diameter_mean_mm:.1f} ± {summary.diameter_std_mm:.1f} mm",
    ]
    kpi_data = [
        [Paragraph(f"<b>{h}</b>", table_hdr_style) for h in kpi_headers],
        [Paragraph(f"<b><font size=11>{v}</font></b>", body_style) for v in kpi_values],
    ]
    kpi_table = Table(kpi_data, colWidths=[108, 108, 108, 108, 108])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#EDF2F7")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 12))

    # 4. Embedded Visual Inspection Image (if provided)
    if annotated_image_bgr is not None:
        # Resize image for PDF
        h_orig, w_orig = annotated_image_bgr.shape[:2]
        target_w = 540
        target_h = int((h_orig / w_orig) * target_w)
        if target_h > 240:
            target_h = 240
            target_w = int((w_orig / h_orig) * target_h)

        is_success, img_buf = cv2.imencode(".jpg", annotated_image_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if is_success:
            img_stream = io.BytesIO(img_buf.tobytes())
            story.append(Paragraph("Visual Inspection & Bounding Mask Overlays", section_style))
            rl_img = RLImage(img_stream, width=target_w, height=target_h)
            story.append(rl_img)
            story.append(Spacer(1, 10))

    # 5. Individual Onions Table (Sample up to 15)
    story.append(Paragraph("Individual Bulb Audit Log", section_style))
    tbl_headers = ["ID", "Diameter", "Weight", "Blemish %", "DoCA Grade", "AGMARK Grade", "Audit Remarks"]
    tbl_rows = [[Paragraph(h, table_hdr_style) for h in tbl_headers]]

    for o in summary.onions[:15]:
        tbl_rows.append([
            Paragraph(o.onion_id, body_style),
            Paragraph(f"{o.measurements.equatorial_diameter_mm} mm", body_style),
            Paragraph(f"{o.measurements.estimated_weight_g or 0.0} g", body_style),
            Paragraph(f"{o.measurements.defect_area_percent}%", body_style),
            Paragraph(o.grades.procurement_grade, body_style),
            Paragraph(o.grades.agmark_grade, body_style),
            Paragraph(o.grades.remarks[:38] + ("..." if len(o.grades.remarks) > 38 else ""), body_style),
        ])

    onions_table = Table(tbl_rows, colWidths=[38, 55, 50, 52, 95, 95, 155])
    onions_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
    ]))
    story.append(onions_table)
    story.append(Spacer(1, 12))

    # 6. Formal Compliance Statement & Signoff
    comp_data = [
        [
            Paragraph("<b>Regulatory Compliance Statement:</b><br/>" + summary.compliance_statement, body_style),
            Paragraph("<b>Inspection Officer Sign-off:</b><br/><br/>___________________________<br/>Procurement Assessor ID", body_style),
        ]
    ]
    comp_table = Table(comp_data, colWidths=[360, 180])
    comp_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EDF2F7")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E0")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(comp_table)

    # Build PDF
    doc.build(story)
    pdf_bytes = buffer.getvalue()

    if output_path is not None:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "wb") as f:
            f.write(pdf_bytes)

    return pdf_bytes
