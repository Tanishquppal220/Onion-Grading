# Implementation Plan: Onion Quality Assessment & Grading

## Overview
A handheld AI-driven onion quality grading system designed for procurement centers (NAFED/NCCF) and export compliance. The system takes a smartphone photo with an ArUco calibration card, detects and segments each bulb (Model 1: YOLOv8-seg), classifies defects (Model 2: MobileNetV3/EfficientNet), quantifies equatorial diameter in mm and surface discolouration %, and evaluates against multiple grading standards (DoCA Buffer-Stock 45–65 mm and AGMARK/Export bands), outputting instant JSON and PDF reports.

## Architecture Decisions (Locked)
1. **Split Multi-Model Design:** 2 ML models (Model 1: single-class `onion` YOLOv8-seg; Model 2: 4-class defect CNN on bulb crops) + OpenCV ArUco metric calibration + HSV/Lab color thresholding for discolouration.
2. **Core Defect Classes:** `healthy`, `sprouted`, `rotten`, `mechanical_damage`. (`double_bulb` dropped for v1; black smut excluded).
3. **Metric Calibration:** OpenCV ArUco detector (`DICT_4X4_50`) with homography tilt correction and focal-length height correction. Fallback prior = 55 mm median diameter with explicit "UNCALIBRATED" banner.
4. **Environment & Package Management:** `uv` with Python 3.12 for prebuilt PyTorch/OpenCV wheel compatibility.
5. **Training Execution:** Google Colab via VS Code extension, featuring programmatic dataset & model export cells (Drive sync + `transfer.sh` direct curl command).

## Phase Breakdown

### Phase 1: Architecture, Data Foundation & Calibration Scaffolding
- [ ] Task 1.1: Environment & Project Scaffolding (`uv`, `pyproject.toml`, directory structure)
- [ ] Task 1.2: Pydantic Data Contracts & Grade Rule Engine (`training/common/`)
- [ ] Task 1.3: ArUco Metric Calibration & Synthetic Test Suite (`training/calibration/`)
- [ ] Task 1.4: Dataset Ingestion, Inspection & pHash Deduplication Scripts (`training/data_prep/`)
- [ ] Task 1.5: Colab VSCode Training & Data Transfer Notebook (`training/notebooks/`)

### Phase 2: Model Training & Evaluation (Google Colab)
- [ ] Task 2.1: Dataset manifest freezing & verification (Step 0)
- [ ] Task 2.2: Model 1 (YOLOv8-seg) training on D1-A, pseudo-labelling D1-C, test on D1-B (Target: mAP@0.5 >= 85%)
- [ ] Task 2.3: Model 2 (Defect CNN) training on balanced crops (Target: F1 >= 90%)
- [ ] Task 2.4: Model export to ONNX / TFLite for handheld mobile deployment

### Phase 3: Backend API (FastAPI)
- [ ] Task 3.1: FastAPI application with grading endpoints (`POST /grade`, `POST /calibrate`)
- [ ] Task 3.2: Rule engine integration (DoCA + AGMARK + FSSAI remarks)
- [ ] Task 3.3: PDF report generation engine (tamper-evident audit trail, calibration badge)

### Phase 4: Frontend (ReactJS)
- [ ] Task 4.1: Handheld camera capture UI with ArUco alignment guides
- [ ] Task 4.2: Batch inspection view & grade distribution charts
- [ ] Task 4.3: JSON/PDF report export and offline caching
