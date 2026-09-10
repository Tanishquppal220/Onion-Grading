import datetime
import uuid
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from grader import OnionGrader

router = APIRouter()
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Initialize the model once
grader = OnionGrader("model/best.pt")

@router.post("/upload")
async def upload_image(
    file: Annotated[UploadFile, File(...)],
    calibration_mode: Annotated[str, Form()] = "estimated",
    custom_mm_per_pixel: Annotated[Optional[float], Form()] = None,
    reference_dimension_mm: Annotated[Optional[float], Form()] = None,
    reference_pixels: Annotated[Optional[float], Form()] = None,
    conf_threshold: Annotated[float, Form()] = 0.25,
    iou_threshold: Annotated[float, Form()] = 0.45,
    lot_id: Annotated[Optional[str], Form()] = None,
    farmer_name: Annotated[Optional[str], Form()] = None,
    mandi_location: Annotated[Optional[str], Form()] = None,
    lot_weight_kg: Annotated[Optional[float], Form()] = None,
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    extension = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
    unique_filename = f"{uuid.uuid4()}.{extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    try:
        content = await file.read()
        file_path.write_bytes(content)
    except OSError:
        raise HTTPException(status_code=500, detail="Could not save file")
    
    try:
        grading_result = grader.process_image(
            image_path=file_path,
            output_dir=UPLOAD_DIR,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            calibration_mode=calibration_mode,
            custom_mm_per_pixel=custom_mm_per_pixel,
            reference_dimension_mm=reference_dimension_mm,
            reference_pixels=reference_pixels,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Error grading image: {e!s}")
    
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    generated_lot_id = lot_id.strip() if lot_id and lot_id.strip() else f"DOCA-{uuid.uuid4().hex[:8].upper()}"

    return {
        "status": "success",
        "filename": unique_filename,
        "message": "Image uploaded and graded successfully against DoCA FAQ standards",
        "lot_metadata": {
            "lot_id": generated_lot_id,
            "farmer_name": farmer_name.strip() if farmer_name and farmer_name.strip() else "Mandi Lot / Registered Grower",
            "mandi_location": mandi_location.strip() if mandi_location and mandi_location.strip() else "Lasalgaon APMC, Nashik",
            "lot_weight_kg": lot_weight_kg if lot_weight_kg is not None else 50.0,
            "timestamp": now,
        },
        "grading": grading_result.model_dump()
    }

