# Onion Quality Assessment & Grading System

Handheld AI-based onion quality grading system for procurement centers (NAFED/NCCF) and export compliance.

## Project Structure
- `data/`: Raw downloads, YOLOv8-seg formatted data, defect crops, synthetic calibration test cases, and manifests.
- `training/`:
  - `data_prep/`: Downloader scripts, inspection tools, pHash cross-source deduplication, manifest builder.
  - `calibration/`: OpenCV ArUco detector (`DICT_4X4_50`), homography tilt correction, and camera focal height correction.
  - `common/`: Pydantic data schemas, multi-standard deterministic rule engine (DoCA 45–65mm + AGMARK + FSSAI defect tolerances).
  - `notebooks/`: VS Code Google Colab training notebook with programmatic data & weight download cells.
- `backend/`: FastAPI service endpoints (Phase 3).
- `tasks/`: Implementation plan (`plan.md`) and task checklist (`todo.md`).

## Setup with `uv`
```bash
# Create Python 3.12 virtual environment
uv venv --python 3.12

# Sync dependencies
uv sync
```

## Running Tests
```bash
uv run pytest training/tests/ -v
```
