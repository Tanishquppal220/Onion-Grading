"""FastAPI Backend Application for Onion Quality Assessment and Multi-Standard Grading.

Provides RESTful endpoints for:
  - Single-image quality assessment & lot grading
  - PDF inspection certificate generation
  - Training metrics and evaluation plots access
  - System health and loaded model diagnostics
"""

from __future__ import annotations

import base64
import io
import os
from pathlib import Path
from typing import Optional
import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from backend.pdf_generator import generate_lot_pdf_report
from backend.pipeline import GradingPipeline
from training.common.schemas import LotReportSummary

from contextlib import asynccontextmanager

# Global pipeline instance
pipeline: Optional[GradingPipeline] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline
    seg_weights = Path("runs/weights/model1_yolov8_seg.pt")
    cls_weights = Path("runs/weights/model2_defect_cls.pt")
    if pipeline is None and seg_weights.exists() and cls_weights.exists():
        pipeline = GradingPipeline(
            seg_model_path=seg_weights,
            cls_model_path=cls_weights,
            device="cpu",
        )
        print("GradingPipeline successfully initialized.")
    yield


app = FastAPI(
    title="Onion Quality Assessment & Grading API",
    description="Handheld AI-based Onion Grading & Multi-Standard Regulatory Compliance Service (DoCA & AGMARK)",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for React frontend (Phase 4)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GradeResponse(BaseModel):
    lot_report: LotReportSummary
    annotated_image_base64: Optional[str] = None


@app.get("/health", tags=["Diagnostics"])
@app.get("/api/v1/health", tags=["Diagnostics"])
def health_check():
    """Returns service health and loaded model metadata."""
    is_ready = pipeline is not None
    return {
        "status": "healthy" if is_ready else "degraded",
        "models_loaded": is_ready,
        "model1": {
            "name": "YOLOv8n-seg",
            "task": "instance_segmentation",
            "target": "single_class_onion",
            "weights": "runs/weights/model1_yolov8_seg.pt",
        },
        "model2": {
            "name": "YOLOv8n-cls",
            "task": "defect_classification",
            "classes": ["healthy", "mechanical_damage", "rotten", "sprouted"],
            "weights": "runs/weights/model2_defect_cls.pt",
        },
        "calibration": {
            "marker_type": "ArUco DICT_4X4_50",
            "reference_size_mm": 50.0,
            "fallback_median_prior_mm": 55.0,
        },
        "standards": [
            "DoCA Buffer-Stock (45-65 mm norm)",
            "AGMARK Commercial Size Bands",
            "FSSAI Defect Tolerance Wording",
        ],
    }


@app.post("/api/v1/grade/image", response_model=GradeResponse, tags=["Grading"])
async def grade_image(
    file: UploadFile = File(..., description="JPEG/PNG image of onions with optional ArUco card"),
    lot_id: str = Query("LOT-001", description="Lot identification code"),
    center_id: str = Query("NAFED-Nashik-01", description="Procurement center or packhouse name"),
    focal_length_px: Optional[float] = Query(None, description="Optional EXIF focal length in pixels"),
    include_image: bool = Query(True, description="Whether to include base64 annotated image in response"),
):
    """Performs full AI quality assessment and multi-standard grading on an uploaded photo."""
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Grading models are not loaded.")

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img_bgr is None:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.")

    lot_summary, annotated_bgr = pipeline.analyze_image(
        image_bgr=img_bgr,
        lot_id=lot_id,
        center_id=center_id,
        focal_length_px=focal_length_px,
    )

    img_b64 = None
    if include_image and annotated_bgr is not None:
        success, enc = cv2.imencode(".jpg", annotated_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if success:
            img_b64 = base64.b64encode(enc.tobytes()).decode("utf-8")

    return GradeResponse(
        lot_report=lot_summary,
        annotated_image_base64=img_b64,
    )


@app.post("/api/v1/grade/report/pdf", tags=["Reporting"])
async def generate_pdf_report(
    file: UploadFile = File(..., description="JPEG/PNG image of onions to grade and certify"),
    lot_id: str = Query("LOT-001", description="Lot identification code"),
    center_id: str = Query("NAFED-Nashik-01", description="Procurement center name"),
    focal_length_px: Optional[float] = Query(None, description="Optional EXIF focal length in pixels"),
):
    """Performs quality assessment and generates an official downloadable PDF inspection certificate."""
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Grading models are not loaded.")

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img_bgr is None:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.")

    lot_summary, annotated_bgr = pipeline.analyze_image(
        image_bgr=img_bgr,
        lot_id=lot_id,
        center_id=center_id,
        focal_length_px=focal_length_px,
    )

    pdf_bytes = generate_lot_pdf_report(
        summary=lot_summary,
        annotated_image_bgr=annotated_bgr,
    )

    safe_lot_id = "".join(c for c in lot_id if c.isalnum() or c in "-_")
    filename = f"inspection_report_{safe_lot_id}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/api/v1/eval-plots", tags=["Diagnostics"])
def list_eval_plots():
    """Lists all available model evaluation plots and curves."""
    eval_dir = Path("runs/eval_plots")
    if not eval_dir.exists():
        return {"plots": []}

    plots = [p.name for p in eval_dir.glob("*.*") if p.suffix.lower() in [".png", ".jpg"]]
    return {"total": len(plots), "plots": sorted(plots)}


@app.get("/api/v1/eval-plots/{plot_name}", tags=["Diagnostics"])
def get_eval_plot(plot_name: str):
    """Serves a specific model evaluation plot or training curve."""
    safe_name = Path(plot_name).name
    file_path = Path("runs/eval_plots") / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Evaluation plot not found.")
    return FileResponse(file_path)
