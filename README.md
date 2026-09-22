# Onion Quality Assessment & Grading System

Handheld AI-based onion quality grading system for procurement centers (NAFED/NCCF) and export compliance.

## Monorepo Architecture
- **`backend/`**: Complete self-contained Python backend & ML subsystem.
  - `app/`: Application package (`app.main`, `app.pipeline`, `app.pdf_generator`, `app.calibration`, `app.common`).
  - `tests/`: Automated unit & integration tests (`test_calibration_math.py`, `test_pipeline.py`, `test_rule_engine.py`) and synthetic fixtures.
  - `runs/weights/`: Trained YOLOv8 segmentation and defect classification model weights.
  - `training/`: Canonical Google Colab GPU training workbook.
  - `scripts/`: Diagnostic and evaluation scripts (`test_demo_images.py`).
  - `pyproject.toml` & `uv.lock`: Dependency definitions.
- **`frontend/`**: Vite + React + TypeScript web application with Tailwind CSS and Live Viewfinder HUD.

## Development Setup

### Backend (Python 3.12 + `uv`)
```bash
cd backend
uv sync

# Run backend tests
uv run pytest tests/ -v

# Run backend API server
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (Node.js + React)
```bash
cd frontend
npm install

# Run frontend development server
npm run dev
```


