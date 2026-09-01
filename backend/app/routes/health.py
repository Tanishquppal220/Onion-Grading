from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint for the frontend status indicator."""
    return {"status": "online", "message": "DoCA Onion Grading API is running"}
