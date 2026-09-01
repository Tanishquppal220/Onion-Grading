import uuid
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.grader import OnionGrader

router = APIRouter()
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Initialize the model once
grader = OnionGrader("model/best.pt")

@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    unique_filename = f"{uuid.uuid4()}.{extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Could not save file")
    
    try:
        grading_result = grader.process_image(file_path, UPLOAD_DIR)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error grading image: {str(e)}")
    
    return {
        "status": "success",
        "filename": unique_filename,
        "message": "Image uploaded and graded successfully",
        "grading": grading_result.model_dump()
    }
