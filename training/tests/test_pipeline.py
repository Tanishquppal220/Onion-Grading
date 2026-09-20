"""Integration and Unit Tests for End-to-End Grading Pipeline, PDF Report, and FastAPI Endpoints.

Verifies:
  1. GradingPipeline inference on synthetic calibration scenes and sample onion imagery
  2. PDF inspection certificate generation and visual overlay embedding
  3. FastAPI REST API endpoints: health diagnostics, eval plots, grading, and PDF reports
"""

import io
from pathlib import Path
import cv2
from fastapi.testclient import TestClient
import numpy as np
import pytest

from backend.main import app
import backend.main as main_module
from backend.pdf_generator import generate_lot_pdf_report
from backend.pipeline import GradingPipeline
from training.calibration.generate_synthetic_set import generate_synthetic_scene
from training.common.schemas import CalibrationMode, LotReportSummary


@pytest.fixture(scope="module")
def pipeline_instance():
    """Initializes and caches the GradingPipeline for testing."""
    seg_weights = "runs/weights/model1_yolov8_seg.pt"
    cls_weights = "runs/weights/model2_defect_cls.pt"
    pipeline = GradingPipeline(
        seg_model_path=seg_weights,
        cls_model_path=cls_weights,
        device="cpu",
    )
    return pipeline


@pytest.fixture(scope="module")
def sample_onion_image():
    """Loads a real sample onion image from eval_plots or creates a fallback."""
    sample_path = Path("runs/eval_plots/d1b_sample_preds_sibuyas8_jpg.rf.e977df2b642a52ba8dffe2ae592f85a7.jpg")
    if sample_path.exists():
        img = cv2.imread(str(sample_path))
        if img is not None:
            return img
    # Fallback synthetic scene with onion
    scene, _ = generate_synthetic_scene(true_diameter_mm=55.0, tilt_degrees=0.0, camera_distance_mm=450.0)
    return scene


@pytest.fixture(scope="module")
def test_client(pipeline_instance):
    """Provides a TestClient with initialized pipeline."""
    main_module.pipeline = pipeline_instance
    with TestClient(app) as client:
        yield client


def test_pipeline_on_synthetic_aruco_scene(pipeline_instance):
    """Tests GradingPipeline on a synthetic scene with known ArUco marker."""
    scene, gt = generate_synthetic_scene(
        true_diameter_mm=50.0,
        marker_size_mm=50.0,
        camera_distance_mm=450.0,
        tilt_degrees=0.0,
    )
    summary, annotated_img = pipeline_instance.analyze_image(
        image_bgr=scene,
        lot_id="LOT-SYNTH-01",
        center_id="NAFED-Nashik-01",
    )

    assert isinstance(summary, LotReportSummary)
    assert summary.lot_id == "LOT-SYNTH-01"
    assert summary.center_id == "NAFED-Nashik-01"
    assert summary.calibration.card_detected is True
    assert summary.calibration.mm_reliable is True
    assert summary.calibration.mode == CalibrationMode.CALIBRATED_ARUCO
    assert annotated_img.shape == scene.shape
    assert annotated_img.dtype == np.uint8


def test_pipeline_on_real_onion_image(pipeline_instance, sample_onion_image):
    """Tests full pipeline on real onion imagery with segmentation and classification."""
    summary, annotated_img = pipeline_instance.analyze_image(
        image_bgr=sample_onion_image,
        lot_id="LOT-REAL-01",
        center_id="NCCF-Pune-02",
        conf_threshold=0.2,
    )

    assert isinstance(summary, LotReportSummary)
    assert summary.lot_id == "LOT-REAL-01"
    assert summary.total_onions_inspected > 0
    assert len(summary.onions) == summary.total_onions_inspected
    assert summary.diameter_mean_mm > 0.0
    assert summary.compliance_statement is not None
    assert len(summary.compliance_statement) > 0

    first_onion = summary.onions[0]
    assert first_onion.onion_id == "O-01"
    assert first_onion.measurements.equatorial_diameter_mm > 0.0
    assert first_onion.measurements.estimated_weight_g is not None
    assert first_onion.measurements.estimated_weight_g > 0.0
    assert any(
        first_onion.grades.procurement_grade.startswith(prefix)
        for prefix in ["Grade-A", "Non-Grade-A", "Reject"]
    )
    assert first_onion.grades.agmark_grade is not None


def test_discolouration_calculation(pipeline_instance):
    """Tests surface discolouration metric on synthetic uniform vs blemish patches."""
    h, w = 100, 100
    img = np.full((h, w, 3), (40, 60, 180), dtype=np.uint8)  # Reddish onion tint
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(mask, (50, 50), 30, 255, -1)

    # Uniform color should have low/zero discolouration
    pct_clean = pipeline_instance._measure_discolouration_percent(img, mask)
    assert pct_clean < 5.0

    # Introduce a black rot spot
    cv2.circle(img, (50, 50), 10, (10, 10, 10), -1)
    pct_blemish = pipeline_instance._measure_discolouration_percent(img, mask)
    assert pct_blemish > pct_clean


def test_pdf_report_generation(pipeline_instance, sample_onion_image, tmp_path):
    """Tests PDF inspection certificate creation with and without overlays."""
    summary, annotated_img = pipeline_instance.analyze_image(
        image_bgr=sample_onion_image,
        lot_id="LOT-PDF-TEST",
        center_id="NAFED-Lasalgaon",
    )

    pdf_file = tmp_path / "test_certificate.pdf"
    pdf_bytes = generate_lot_pdf_report(
        summary=summary,
        annotated_image_bgr=annotated_img,
        output_path=pdf_file,
    )

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 20000
    assert pdf_file.exists()
    assert pdf_file.stat().st_size == len(pdf_bytes)

    # Test without annotated image
    pdf_no_img = generate_lot_pdf_report(summary=summary, annotated_image_bgr=None)
    assert pdf_no_img.startswith(b"%PDF-")
    assert len(pdf_no_img) > 2000


def test_api_health(test_client):
    """Tests FastAPI /health and /api/v1/health endpoints."""
    resp = test_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["models_loaded"] is True
    assert "model1" in data
    assert "model2" in data
    assert "calibration" in data

    resp_v1 = test_client.get("/api/v1/health")
    assert resp_v1.status_code == 200
    assert resp_v1.json() == data


def test_api_eval_plots(test_client):
    """Tests listing and retrieving evaluation plots via API."""
    list_resp = test_client.get("/api/v1/eval-plots")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert "plots" in data
    assert data["total"] > 0
    first_plot = data["plots"][0]

    # Fetch specific plot
    plot_resp = test_client.get(f"/api/v1/eval-plots/{first_plot}")
    assert plot_resp.status_code == 200
    assert plot_resp.headers["content-type"] in ["image/png", "image/jpeg"]

    # Fetch non-existent plot
    missing_resp = test_client.get("/api/v1/eval-plots/non_existent_plot_12345.png")
    assert missing_resp.status_code == 404


def test_api_grade_image(test_client, sample_onion_image):
    """Tests POST /api/v1/grade/image with multipart file upload."""
    _, img_encoded = cv2.imencode(".jpg", sample_onion_image)
    file_bytes = img_encoded.tobytes()

    response = test_client.post(
        "/api/v1/grade/image",
        files={"file": ("test_onion.jpg", io.BytesIO(file_bytes), "image/jpeg")},
        params={"lot_id": "LOT-API-01", "center_id": "NAFED-Nashik-01"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "lot_report" in payload
    assert "annotated_image_base64" in payload
    assert payload["lot_report"]["lot_id"] == "LOT-API-01"
    assert payload["lot_report"]["center_id"] == "NAFED-Nashik-01"
    assert payload["annotated_image_base64"] is not None
    assert len(payload["annotated_image_base64"]) > 100


def test_api_grade_image_invalid_file(test_client):
    """Tests error handling for non-image uploads."""
    response = test_client.post(
        "/api/v1/grade/image",
        files={"file": ("corrupt.txt", io.BytesIO(b"This is not an image"), "text/plain")},
    )
    assert response.status_code == 400
    assert "not a valid image" in response.json()["detail"]


def test_api_grade_report_pdf(test_client, sample_onion_image):
    """Tests POST /api/v1/grade/report/pdf endpoint returning streaming PDF."""
    _, img_encoded = cv2.imencode(".jpg", sample_onion_image)
    file_bytes = img_encoded.tobytes()

    response = test_client.post(
        "/api/v1/grade/report/pdf",
        files={"file": ("test_onion.jpg", io.BytesIO(file_bytes), "image/jpeg")},
        params={"lot_id": "LOT-API-PDF", "center_id": "NAFED-Nashik-01"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert "inspection_report_LOT-API-PDF.pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) > 10000
