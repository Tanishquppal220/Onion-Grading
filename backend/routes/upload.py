import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from grader import OnionGrader

router = APIRouter()
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Initialize the model once
grader = OnionGrader("model/best.pt")

@router.post("/upload")
async def upload_image(file: Annotated[UploadFile, File(...)]):
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
        grading_result = grader.process_image(file_path, UPLOAD_DIR)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Error grading image: {e!s}")
    
    return {
        "status": "success",
        "filename": unique_filename,
        "message": "Image uploaded and graded successfully",
        "grading": grading_result.model_dump()
    }
