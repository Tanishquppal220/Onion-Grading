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

# Run frontend development server (accessible on local network)
npm run dev

# Or run with HTTPS for real-time mobile camera viewfinder HUD:
npm run dev:https
```

## Mobile Phone Access (Local Wi-Fi / Hotspot)

To use the system on your mobile phone:

1. **Firewall (UFW on Linux)**: Ensure port 5173 is open:
   ```bash
   sudo ufw allow 5173/tcp
   ```

2. **1-Command Network Launcher**:
   ```bash
   ./start_network.sh
   # Or with HTTPS (enables live camera viewfinder on phone):
   ./start_network.sh --https
   ```

3. **Open on Phone**:
   Connect your phone to the same Wi-Fi/hotspot and open the URL printed in the terminal (e.g. `http://192.168.1.13:5173/`).
   - **Snap Photo**: Tap **`Snap Photo (Phone Camera)`** to capture directly with your phone's native camera.
   - **Live Viewfinder**: If using `--https`, tap **`Open Live Viewfinder HUD`** to stream real-time video with tray reticle and torch control.


