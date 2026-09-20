# Phase 1 Checklist & Todo

## Task 1.1: Environment & Project Scaffolding
- [x] Initialize `pyproject.toml` with `uv` (pinned to Python 3.12, dependencies: ultralytics, opencv-python-headless, numpy, pandas, imagehash, pillow, pydantic, pytest, requests, tqdm)
- [x] Initialize virtual environment using `uv venv --python 3.12` and test lock/sync
- [x] Add `.gitignore` for data, venv, model weights, checkpoints, caches

## Task 1.2: Pydantic Data Contracts & Grade Rule Engine
- [x] Create `training/common/schemas.py` defining `OnionMeasurement`, `QualityFlags`, `GradesResult`, `CalibrationMetadata`, `LotReportSummary`
- [x] Create `training/common/rule_engine.py` implementing DoCA buffer-stock (45–65 mm), AGMARK/export tiers, and FSSAI defect tolerance wording
- [x] Write unit tests in `training/tests/test_rule_engine.py` covering boundary conditions and remarks

## Task 1.3: ArUco Metric Calibration & Synthetic Test Engine
- [x] Implement `training/calibration/aruco_calibrator.py` with ArUco marker detection (`DICT_4X4_50`), homography tilt correction, and EXIF focal length height-above-plane correction
- [x] Implement `training/calibration/generate_synthetic_set.py` rendering synthetic ArUco + onion masks at angles 0–30° and distances 30–80 cm
- [x] Write unit tests in `training/tests/test_calibration_math.py` verifying diameter recovery within +/- 1.5 mm

## Task 1.4: Dataset Ingestion, Inspection & pHash Deduplication
- [x] Create `training/data_prep/download_datasets.py` supporting Roboflow API / manual zip unpacking for D1-A, D1-B, D1-C, D2-A, D2-C
- [x] Create `training/data_prep/audit_inspector.py` generating visualization samples (~50 images) with masks/boxes to inspect quality
- [x] Create `training/data_prep/deduplicate.py` using perceptual hashing (`imagehash` pHash, Hamming distance <= 6) to eliminate cross-source leakage between D1-A and D1-B
- [x] Create `training/data_prep/build_manifest.py` to freeze `data/manifests/dataset_manifest.csv` with attribution and split assignments

## Task 1.5: Colab VSCode Training & Data Transfer Notebook
- [x] Create `training/notebooks/colab_training_and_transfer.ipynb`
- [x] Add GPU verification, dependencies installation, and model training cells
- [x] Add non-Web-UI programmatic download cells (Google Drive sync + `transfer.sh` 1-line curl command) to pull data/models directly to local PC

## Checkpoint: Phase 1 Complete
- [x] All unit tests pass (`uv run pytest -v`) -> 9/9 tests passing
- [x] Calibration math verified on synthetic renders (15 benchmark scenes generated)
- [x] Notebook verified for VS Code Colab execution with working data transfer cell
- [x] Documentation updated in `Second Brain/` and ready for Phase 2 model training
